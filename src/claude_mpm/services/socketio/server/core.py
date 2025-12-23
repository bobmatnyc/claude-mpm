"""
SocketIO Server Core for claude-mpm.

WHY: This module contains the core server management functionality extracted from
the monolithic socketio_server.py file. It handles server lifecycle, static file
serving, and basic server setup.

DESIGN DECISION: Separated core server logic from event handling and broadcasting
to create focused, maintainable modules.
"""

import asyncio
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Set

try:
    import aiohttp
    import socketio
    from aiohttp import web

    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False
    socketio = None
    aiohttp = None
    web = None

# Import VersionService for dynamic version retrieval
import contextlib

from claude_mpm.services.version_service import VersionService

from ....core.constants import SystemLimits, TimeoutConfig
from ....core.logging_config import get_logger
from ....core.unified_paths import get_project_root, get_scripts_dir
from ...exceptions import SocketIOServerError as MPMConnectionError


class SocketIOServerCore:
    """Core server management functionality for SocketIO server.

    WHY: This class handles the basic server lifecycle, static file serving,
    and core server setup. It's separated from event handling to reduce complexity.
    """

    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.logger = get_logger(__name__ + ".SocketIOServer")
        self.running = False
        self.server_thread = None
        self.loop = None
        self.app = None
        self.runner = None
        self.site = None

        # Socket.IO server instance
        self.sio = None

        # Connection tracking
        self.connected_clients: Set[str] = set()
        self.client_info: Dict[str, Dict[str, Any]] = {}

        # Event buffering for reliability
        self.event_buffer = deque(
            maxlen=getattr(SystemLimits, "MAX_EVENTS_BUFFER", 1000)
        )
        self.buffer_lock = threading.Lock()

        # Performance tracking
        self.stats = {
            "events_sent": 0,
            "events_buffered": 0,
            "connections_total": 0,
            "start_time": None,
        }

        # Static files path
        self.static_path = None

        # Heartbeat task
        self.heartbeat_task = None
        self.heartbeat_interval = 60  # seconds
        self.main_server = None  # Reference to main server for session data

    def start_sync(self):
        """Start the Socket.IO server in a background thread (synchronous version)."""
        if not SOCKETIO_AVAILABLE:
            self.logger.warning("Socket.IO not available - server not started")
            return

        if self.running:
            self.logger.warning("Socket.IO server already running")
            return

        self.logger.info(f"Starting Socket.IO server on {self.host}:{self.port}")

        # Start server in background thread
        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()

        # Wait for server to start
        max_wait = getattr(TimeoutConfig, "SERVER_START_TIMEOUT", 30)
        wait_time = 0
        while not self.running and wait_time < max_wait:
            time.sleep(0.1)
            wait_time += 0.1

        if not self.running:
            raise MPMConnectionError(
                f"Failed to start Socket.IO server within {max_wait}s"
            )

        self.logger.info(
            f"Socket.IO server started successfully on {self.host}:{self.port}"
        )

    def stop_sync(self):
        """Stop the Socket.IO server (synchronous version)."""
        if not self.running:
            return

        self.logger.info("Stopping Socket.IO server...")
        self.running = False

        # Stop the server gracefully
        if self.loop and not self.loop.is_closed():
            asyncio.run_coroutine_threadsafe(self._stop_server(), self.loop)

    def _run_server(self):
        """Run the server event loop."""
        try:
            # Create new event loop for this thread
            # WHY: We create and assign the loop immediately to minimize the race
            # condition window where other threads might try to access it.
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

            self.logger.debug("Event loop created and set for background thread")

            # Run the server
            self.loop.run_until_complete(self._start_server())

        except Exception as e:
            self.logger.error(f"Socket.IO server error: {e}")
            self.running = False
        finally:
            if self.loop and not self.loop.is_closed():
                self.loop.close()

    async def _start_server(self):
        """Start the Socket.IO server with aiohttp."""
        try:
            # Import centralized configuration for consistency
            from ....config.socketio_config import CONNECTION_CONFIG

            # Create Socket.IO server with centralized configuration
            # CRITICAL: These values MUST match client settings to prevent disconnections
            self.sio = socketio.AsyncServer(
                cors_allowed_origins="*",
                logger=False,  # Disable Socket.IO's own logging
                engineio_logger=False,
                ping_interval=CONNECTION_CONFIG[
                    "ping_interval"
                ],  # 45 seconds from config
                ping_timeout=CONNECTION_CONFIG[
                    "ping_timeout"
                ],  # 20 seconds from config
                max_http_buffer_size=CONNECTION_CONFIG[
                    "max_http_buffer_size"
                ],  # 100MB from config
            )

            # Create aiohttp application
            self.app = web.Application()
            self.sio.attach(self.app)

            # CRITICAL: Register event handlers BEFORE starting the server
            # This ensures handlers are ready when clients connect
            if self.main_server and hasattr(self.main_server, "_register_events_async"):
                self.logger.info(
                    "Registering Socket.IO event handlers before server start"
                )
                await self.main_server._register_events_async()
            else:
                self.logger.warning("Main server not available for event registration")

            # Setup HTTP API endpoints for receiving events from hook handlers
            self._setup_http_api()

            # Setup simple directory API
            self._setup_directory_api()

            # Find and serve static files
            self._setup_static_files()

            # Create and start the server
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()

            self.site = web.TCPSite(
                self.runner, self.host, self.port, reuse_address=True, reuse_port=True
            )
            await self.site.start()

            self.running = True
            self.stats["start_time"] = datetime.now(timezone.utc)

            self.logger.info(
                f"Socket.IO server listening on http://{self.host}:{self.port}"
            )
            if self.static_path:
                self.logger.info(f"Serving static files from: {self.static_path}")

            # Conditionally start heartbeat task based on configuration
            from ....config.socketio_config import CONNECTION_CONFIG

            if CONNECTION_CONFIG.get("enable_extra_heartbeat", False):
                self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                self.logger.info("Started system heartbeat task")
            else:
                self.logger.info(
                    "System heartbeat disabled (using Socket.IO ping/pong instead)"
                )

            # Keep the server running
            while self.running:
                await asyncio.sleep(1)

        except Exception as e:
            self.logger.error(f"Failed to start Socket.IO server: {e}")
            self.running = False
            raise

    async def _stop_server(self):
        """Stop the server gracefully."""
        try:
            # Cancel heartbeat task
            if self.heartbeat_task and not self.heartbeat_task.done():
                self.heartbeat_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self.heartbeat_task
                self.logger.info("Stopped system heartbeat task")

            if self.site:
                await self.site.stop()
                self.site = None

            if self.runner:
                await self.runner.cleanup()
                self.runner = None

            self.logger.info("Socket.IO server stopped")

        except Exception as e:
            self.logger.error(f"Error stopping Socket.IO server: {e}")

    def _setup_http_api(self):
        """Setup HTTP API endpoints for receiving events from hook handlers.

        WHY: Hook handlers are ephemeral processes that spawn and die quickly.
        Using HTTP POST allows them to send events without managing persistent
        connections, eliminating disconnection issues.
        """

        async def api_events_handler(request):
            """Handle POST /api/events from hook handlers."""
            try:
                # Parse JSON payload
                payload = await request.json()

                # Extract event data from payload (handles both direct and wrapped formats)
                # ConnectionManagerService sends: {"namespace": "...", "event": "...", "data": {...}}
                # Direct hook events may send data directly
                # CRITICAL: Check if payload has the expected event structure (type, subtype, timestamp)
                # If it does, use it directly. Only extract 'data' field if it's a wrapper object.
                if "type" in payload and "subtype" in payload:
                    # Payload is already in normalized format, use it directly
                    event_data = payload
                elif "data" in payload and isinstance(payload.get("data"), dict):
                    # Payload is a wrapper with 'data' field (from ConnectionManagerService)
                    event_data = payload["data"]
                else:
                    # Fallback: use entire payload
                    event_data = payload

                # Log receipt with more detail
                event_type = (
                    event_data.get("subtype")
                    or event_data.get("hook_event_name")
                    or "unknown"
                )
                self.logger.info(f"📨 Received HTTP event: {event_type}")
                self.logger.debug(f"Event data keys: {list(event_data.keys())}")
                self.logger.debug(f"Connected clients: {len(self.connected_clients)}")

                # Transform hook event format to claude_event format if needed
                if "hook_event_name" in event_data and "event" not in event_data:
                    # This is a raw hook event, transform it
                    from claude_mpm.services.socketio.event_normalizer import (
                        EventNormalizer,
                    )

                    normalizer = EventNormalizer()

                    # Map hook event names to dashboard subtypes
                    # Comprehensive mapping of all known Claude Code hook event types
                    subtype_map = {
                        # User interaction events
                        "UserPromptSubmit": "user_prompt_submit",
                        "UserPromptCancel": "user_prompt_cancel",
                        # Tool execution events
                        "PreToolUse": "pre_tool_use",
                        "PostToolUse": "post_tool_use",
                        "ToolStart": "tool_start",
                        "ToolUse": "tool_use",
                        # Assistant events
                        "AssistantResponse": "assistant_response",
                        # Session lifecycle events
                        "Start": "start",
                        "Stop": "stop",
                        "SessionStart": "session_start",
                        # Subagent events
                        "SubagentStart": "subagent_start",
                        "SubagentStop": "subagent_stop",
                        "SubagentEvent": "subagent_event",
                        # Task events
                        "Task": "task",
                        "TaskStart": "task_start",
                        "TaskComplete": "task_complete",
                        # File operation events
                        "FileWrite": "file_write",
                        "Write": "write",
                        # System events
                        "Notification": "notification",
                    }

                    # Helper function to convert PascalCase to snake_case
                    def to_snake_case(name: str) -> str:
                        """Convert PascalCase event names to snake_case.

                        Examples:
                            UserPromptSubmit → user_prompt_submit
                            PreToolUse → pre_tool_use
                            TaskComplete → task_complete
                        """
                        import re

                        return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()

                    # Get hook event name and map to subtype
                    hook_event_name = event_data.get("hook_event_name", "unknown")
                    subtype = subtype_map.get(
                        hook_event_name, to_snake_case(hook_event_name)
                    )

                    # Debug log for unmapped events to discover new event types
                    if (
                        hook_event_name not in subtype_map
                        and hook_event_name != "unknown"
                    ):
                        self.logger.debug(
                            f"Unmapped hook event: {hook_event_name} → {subtype}"
                        )

                    # Create the format expected by normalizer
                    raw_event = {
                        "type": "hook",
                        "subtype": subtype,
                        "timestamp": event_data.get("timestamp"),
                        "data": event_data.get("hook_input_data", {}),
                        "source": "claude_hooks",
                        "session_id": event_data.get("session_id"),
                    }

                    normalized = normalizer.normalize(raw_event, source="hook")
                    event_data = normalized.to_dict()
                    self.logger.debug(
                        f"Normalized event: type={event_data.get('type')}, subtype={event_data.get('subtype')}"
                    )

                # Publish to EventBus for cross-component communication
                # WHY: This allows other parts of the system to react to hook events
                # without coupling to Socket.IO directly
                try:
                    from claude_mpm.services.event_bus import EventBus

                    event_bus = EventBus.get_instance()
                    event_type = f"hook.{event_data.get('subtype', 'unknown')}"
                    event_bus.publish(event_type, event_data)
                    self.logger.debug(f"Published to EventBus: {event_type}")
                except Exception as e:
                    # Non-fatal: EventBus publication failure shouldn't break event flow
                    self.logger.warning(f"Failed to publish to EventBus: {e}")

                # Broadcast to all connected dashboard clients via SocketIO
                if self.sio:
                    # CRITICAL: Use the main server's broadcaster for proper event handling
                    # The broadcaster handles retries, connection management, and buffering
                    if (
                        self.main_server
                        and hasattr(self.main_server, "broadcaster")
                        and self.main_server.broadcaster
                    ):
                        # The broadcaster expects raw event data and will normalize it
                        # Since we already normalized it, we need to pass it in a way that won't double-normalize
                        # We'll emit directly through the broadcaster's sio with proper handling

                        # Add to event buffer and history
                        with self.buffer_lock:
                            self.event_buffer.append(event_data)
                            self.stats["events_buffered"] = len(self.event_buffer)

                        # Add to main server's event history UNCONDITIONALLY
                        # WHY: event_history is always initialized in SocketIOServer.__init__
                        # This ensures events persist for new clients who connect later
                        if self.main_server and hasattr(
                            self.main_server, "event_history"
                        ):
                            self.main_server.event_history.append(event_data)
                            self.logger.debug(
                                f"Added to history (total: {len(self.main_server.event_history)})"
                            )
                        else:
                            # CRITICAL: Log warning if event_history is not available
                            # This indicates a configuration or initialization problem
                            self.logger.warning(
                                "event_history not initialized on main_server! "
                                "Events will not persist for new clients."
                            )

                        # Use the broadcaster's sio to emit (it's the same as self.sio)
                        # This ensures the event goes through the proper channels
                        await self.sio.emit("claude_event", event_data)

                        # Update broadcaster stats
                        if hasattr(self.main_server.broadcaster, "stats"):
                            self.main_server.broadcaster.stats["events_sent"] = (
                                self.main_server.broadcaster.stats.get("events_sent", 0)
                                + 1
                            )

                        self.logger.info(
                            f"✅ Event broadcasted: {event_data.get('subtype', 'unknown')} to {len(self.connected_clients)} clients"
                        )
                        self.logger.debug(
                            f"Connected client IDs: {list(self.connected_clients) if self.connected_clients else 'None'}"
                        )
                    else:
                        # Fallback: Direct emit if broadcaster not available (shouldn't happen)
                        self.logger.warning(
                            "Broadcaster not available, using direct emit"
                        )
                        await self.sio.emit("claude_event", event_data)

                        # Update stats manually if using fallback
                        self.stats["events_sent"] = self.stats.get("events_sent", 0) + 1

                        # Add to event buffer for late-joining clients
                        with self.buffer_lock:
                            self.event_buffer.append(event_data)
                            self.stats["events_buffered"] = len(self.event_buffer)

                        # Add to main server's event history (fallback path)
                        # WHY: Ensure events persist even when broadcaster is unavailable
                        if self.main_server and hasattr(
                            self.main_server, "event_history"
                        ):
                            self.main_server.event_history.append(event_data)
                            self.logger.debug(
                                f"Added to history via fallback (total: {len(self.main_server.event_history)})"
                            )
                        else:
                            self.logger.warning(
                                "event_history not initialized on main_server (fallback path)! "
                                "Events will not persist for new clients."
                            )

                # Return 204 No Content for success
                self.logger.debug(f"✅ HTTP event processed successfully: {event_type}")
                return web.Response(status=204)

            except Exception as e:
                self.logger.error(f"Error handling HTTP event: {e}")
                return web.Response(status=500, text=str(e))

        # Register the HTTP POST endpoint
        self.app.router.add_post("/api/events", api_events_handler)
        self.logger.info("✅ HTTP API endpoint registered at /api/events")

        # Add health check endpoint
        async def health_handler(request):
            """Handle GET /api/health for health checks."""
            try:
                # Get server status
                uptime_seconds = 0
                if self.stats.get("start_time"):
                    uptime_seconds = int(
                        (
                            datetime.now(timezone.utc) - self.stats["start_time"]
                        ).total_seconds()
                    )

                health_data = {
                    "status": "healthy",
                    "service": "claude-mpm-socketio",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "uptime_seconds": uptime_seconds,
                    "connected_clients": len(self.connected_clients),
                    "total_events": self.stats.get("events_sent", 0),
                    "buffered_events": self.stats.get("events_buffered", 0),
                }

                return web.json_response(health_data)
            except Exception as e:
                self.logger.error(f"Error in health check: {e}")
                return web.json_response(
                    {
                        "status": "unhealthy",
                        "service": "claude-mpm-socketio",
                        "error": str(e),
                    },
                    status=503,
                )

        self.app.router.add_get("/api/health", health_handler)
        self.app.router.add_get("/health", health_handler)  # Alias for convenience
        self.logger.info(
            "✅ Health check endpoints registered at /api/health and /health"
        )

        # Add working directory endpoint
        async def working_directory_handler(request):
            """Handle GET /api/working-directory to provide current working directory."""
            from pathlib import Path

            try:
                working_dir = str(Path.cwd())
                home_dir = str(Path.home())

                return web.json_response(
                    {
                        "working_directory": working_dir,
                        "home_directory": home_dir,
                        "process_cwd": working_dir,
                        "session_id": getattr(self, "session_id", None),
                    }
                )
            except Exception as e:
                self.logger.error(f"Error getting working directory: {e}")
                return web.json_response(
                    {
                        "working_directory": "/Users/masa/Projects/claude-mpm",
                        "home_directory": "/Users/masa",
                        "error": str(e),
                    },
                    status=500,
                )

        self.app.router.add_get("/api/working-directory", working_directory_handler)
        self.logger.info(
            "✅ Working directory endpoint registered at /api/working-directory"
        )

        # Add file reading endpoint for source viewer
        async def file_read_handler(request):
            """Handle GET /api/file/read for reading source files."""

            file_path = request.query.get("path", "")

            if not file_path:
                return web.json_response({"error": "No path provided"}, status=400)

            abs_path = Path(Path(file_path).resolve().expanduser())

            # Security check - ensure file is within the project
            try:
                project_root = Path.cwd()
                if not abs_path.startswith(project_root):
                    return web.json_response({"error": "Access denied"}, status=403)
            except Exception:
                pass

            if not Path(abs_path).exists():
                return web.json_response({"error": "File not found"}, status=404)

            if not Path(abs_path).is_file():
                return web.json_response({"error": "Not a file"}, status=400)

            try:
                # Read file with appropriate encoding
                encodings = ["utf-8", "latin-1", "cp1252"]
                content = None

                for encoding in encodings:
                    try:
                        with Path(abs_path).open(
                            encoding=encoding,
                        ) as f:
                            content = f.read()
                        break
                    except UnicodeDecodeError:
                        continue

                if content is None:
                    return web.json_response(
                        {"error": "Could not decode file"}, status=400
                    )

                return web.json_response(
                    {
                        "path": abs_path,
                        "name": Path(abs_path).name,
                        "content": content,
                        "lines": len(content.splitlines()),
                        "size": Path(abs_path).stat().st_size,
                    }
                )

            except PermissionError:
                return web.json_response({"error": "Permission denied"}, status=403)
            except Exception as e:
                return web.json_response({"error": str(e)}, status=500)

        self.app.router.add_get("/api/file/read", file_read_handler)
        self.logger.info("✅ File reading API registered at /api/file/read")

        # Add files listing endpoint for file browser
        async def files_list_handler(request):
            """Handle GET /api/files for listing files in working directory."""

            try:
                # Get working directory from query params or use current directory
                working_dir = request.query.get("path", str(Path.cwd()))
                abs_working_dir = Path(working_dir).resolve().expanduser()

                # Security check - ensure directory is accessible
                if not abs_working_dir.exists():
                    return web.json_response(
                        {"error": "Directory not found"}, status=404
                    )

                if not abs_working_dir.is_dir():
                    return web.json_response(
                        {"error": "Path is not a directory"}, status=400
                    )

                # Collect files and directories
                files = []
                directories = []

                # Common patterns to exclude
                exclude_patterns = {
                    ".git",
                    ".venv",
                    "venv",
                    "node_modules",
                    "__pycache__",
                    ".pytest_cache",
                    ".mypy_cache",
                    "dist",
                    "build",
                    ".next",
                    "coverage",
                    ".coverage",
                    ".tox",
                    ".eggs",
                    "*.egg-info",
                }

                for entry in abs_working_dir.iterdir():
                    # Skip hidden files and excluded patterns
                    if entry.name.startswith("."):
                        # Allow .py, .ts, .md, etc. files but skip directories like .git
                        if entry.is_dir():
                            continue

                    # Skip excluded directories
                    if entry.name in exclude_patterns:
                        continue

                    try:
                        stat_info = entry.stat()
                        entry_data = {
                            "name": entry.name,
                            "path": str(entry),
                            "type": "directory" if entry.is_dir() else "file",
                            "size": stat_info.st_size if entry.is_file() else 0,
                            "modified": stat_info.st_mtime,
                        }

                        if entry.is_dir():
                            directories.append(entry_data)
                        else:
                            # Add file extension for syntax highlighting
                            entry_data["extension"] = entry.suffix.lower()
                            files.append(entry_data)
                    except (PermissionError, OSError):
                        # Skip files we can't access
                        continue

                # Sort directories and files alphabetically
                directories.sort(key=lambda x: x["name"].lower())
                files.sort(key=lambda x: x["name"].lower())

                return web.json_response(
                    {
                        "success": True,
                        "path": str(abs_working_dir),
                        "directories": directories,
                        "files": files,
                        "total_files": len(files),
                        "total_directories": len(directories),
                    }
                )

            except Exception as e:
                self.logger.error(f"Error listing files: {e}")
                return web.json_response({"error": str(e)}, status=500)

        self.app.router.add_get("/api/files", files_list_handler)
        self.logger.info("✅ Files listing API registered at /api/files")

        # Add git history endpoint
        async def git_history_handler(request):
            """Handle POST /api/git-history for getting file git history."""
            import subprocess

            try:
                # Parse JSON body
                data = await request.json()
                file_path = data.get("path", "")
                limit = data.get("limit", 10)

                if not file_path:
                    return web.json_response(
                        {"success": False, "error": "No path provided", "commits": []},
                        status=400,
                    )

                abs_path = Path(Path(file_path).resolve().expanduser())

                if not Path(abs_path).exists():
                    return web.json_response(
                        {"success": False, "error": "File not found", "commits": []},
                        status=404,
                    )

                # Get git log for file
                result = subprocess.run(
                    [
                        "git",
                        "log",
                        f"-{limit}",
                        "--pretty=format:%H|%an|%ar|%s",
                        "--",
                        abs_path,
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                    cwd=Path(abs_path).parent,
                )

                commits = []
                if result.returncode == 0 and result.stdout:
                    for line in result.stdout.strip().split("\n"):
                        if line:
                            parts = line.split("|", 3)
                            if len(parts) == 4:
                                commits.append(
                                    {
                                        "hash": parts[0][:7],  # Short hash
                                        "author": parts[1],
                                        "date": parts[2],
                                        "message": parts[3],
                                    }
                                )

                return web.json_response({"success": True, "commits": commits})

            except Exception as e:
                self.logger.error(f"Error getting git history: {e}")
                return web.json_response(
                    {"success": False, "error": str(e), "commits": []}, status=500
                )

        self.app.router.add_post("/api/git-history", git_history_handler)
        self.logger.info("✅ Git history API registered at /api/git-history")

    def _setup_directory_api(self):
        """Setup simple directory listing API.

        WHY: Provides a dead-simple way to list directory contents via HTTP GET
        without complex WebSocket interactions.
        """
        try:
            from claude_mpm.dashboard.api.simple_directory import register_routes

            register_routes(self.app)
            self.logger.info(
                "✅ Simple directory API registered at /api/directory/list"
            )
        except Exception as e:
            self.logger.error(f"Failed to setup directory API: {e}")

    def _setup_static_files(self):
        """Setup static file serving for the Svelte dashboard."""
        try:
            # Add debug logging for deployment context
            try:
                from ....core.unified_paths import PathContext

                deployment_context = PathContext.detect_deployment_context()
                self.logger.debug(
                    f"Setting up static files in {deployment_context.value} mode"
                )
            except Exception as e:
                self.logger.debug(f"Could not detect deployment context: {e}")

            # Find Svelte build directory
            svelte_build_path = self._find_static_path()

            if svelte_build_path and svelte_build_path.exists():
                self.logger.info(f"✅ Svelte dashboard found at: {svelte_build_path}")
                self.dashboard_path = svelte_build_path

                # Serve Svelte index.html at root
                async def index_handler(request):
                    index_file = svelte_build_path / "index.html"
                    if index_file.exists():
                        self.logger.debug(
                            f"Serving Svelte dashboard from: {index_file}"
                        )
                        return web.FileResponse(index_file)
                    self.logger.warning(f"Svelte index.html not found at: {index_file}")
                    return web.Response(text="Dashboard not available", status=404)

                self.app.router.add_get("/", index_handler)

                # Serve Svelte app assets at /_app/ (needed for SvelteKit builds)
                svelte_app_path = svelte_build_path / "_app"
                if svelte_app_path.exists():
                    self.app.router.add_static(
                        "/_app/", svelte_app_path, name="svelte_app"
                    )
                    self.logger.info(
                        f"✅ Svelte dashboard available at http://{self.host}:{self.port}/ (build: {svelte_build_path})"
                    )
                else:
                    self.logger.warning(
                        f"⚠️  Svelte _app directory not found at: {svelte_app_path}"
                    )

                # Serve version.json from Svelte build directory
                async def version_handler(request):
                    version_file = svelte_build_path / "version.json"
                    if version_file.exists():
                        self.logger.debug(f"Serving version.json from: {version_file}")
                        return web.FileResponse(version_file)
                    # Return default version info if file doesn't exist
                    return web.json_response(
                        {
                            "version": "1.0.0",
                            "build": 1,
                            "formatted_build": "0001",
                            "full_version": "v1.0.0-0001",
                        }
                    )

                self.app.router.add_get("/version.json", version_handler)

            else:
                self.logger.warning(
                    "⚠️  Svelte dashboard not found, serving fallback response"
                )

                # Fallback handler
                async def fallback_handler(request):
                    return web.Response(
                        text="Socket.IO server running - Dashboard not available",
                        status=200,
                    )

                self.app.router.add_get("/", fallback_handler)

        except Exception as e:
            self.logger.error(f"❌ Error setting up static files: {e}")
            import traceback

            self.logger.debug(f"Static file setup traceback: {traceback.format_exc()}")

            # Ensure we always have a basic handler
            async def error_handler(request):
                return web.Response(
                    text="Socket.IO server running - Static files unavailable",
                    status=200,
                )

            self.app.router.add_get("/", error_handler)

    def _find_static_path(self):
        """Find the Svelte build directory using multiple approaches.

        WHY: The dashboard is now pure Svelte, located at dashboard/static/svelte-build/.
        We search for this specific structure across different deployment contexts.
        """
        # Get deployment-context-aware paths
        try:
            from ....core.unified_paths import get_path_manager

            path_manager = get_path_manager()

            # Use package root for installed packages (including pipx)
            package_root = path_manager.package_root
            self.logger.debug(f"Package root: {package_root}")

            # Use project root for development
            project_root = get_project_root()
            self.logger.debug(f"Project root: {project_root}")

        except Exception as e:
            self.logger.debug(f"Could not get path manager: {e}")
            package_root = None
            project_root = get_project_root()

        # Try multiple possible locations for Svelte build directory
        possible_paths = [
            # Package-based paths (for pipx and pip installations)
            package_root / "dashboard" / "static" / "svelte-build"
            if package_root
            else None,
            # Project-based paths (for development)
            project_root
            / "src"
            / "claude_mpm"
            / "dashboard"
            / "static"
            / "svelte-build",
            project_root / "dashboard" / "static" / "svelte-build",
            # Package installation locations (fallback)
            Path(__file__).parent.parent.parent
            / "dashboard"
            / "static"
            / "svelte-build",
            # Scripts directory (for standalone installations)
            get_scripts_dir() / "dashboard" / "static" / "svelte-build",
            # Current working directory
            Path.cwd() / "src" / "claude_mpm" / "dashboard" / "static" / "svelte-build",
            Path.cwd() / "dashboard" / "static" / "svelte-build",
        ]

        # Filter out None values
        possible_paths = [p for p in possible_paths if p is not None]
        self.logger.debug(
            f"Searching {len(possible_paths)} possible Svelte build locations"
        )

        for path in possible_paths:
            self.logger.debug(f"Checking for Svelte build at: {path}")
            try:
                if path.exists() and path.is_dir():
                    # Check if it contains expected Svelte build files
                    if (path / "index.html").exists():
                        self.logger.info(f"✅ Found Svelte build at: {path}")
                        return path
                    self.logger.debug(f"Directory exists but no index.html: {path}")
                else:
                    self.logger.debug(f"Path does not exist: {path}")
            except Exception as e:
                self.logger.debug(f"Error checking path {path}: {e}")

        self.logger.warning(
            "⚠️  Svelte build not found - dashboard will not be available"
        )
        self.logger.debug(f"Searched paths: {[str(p) for p in possible_paths]}")
        return None

    def get_connection_count(self) -> int:
        """Get number of connected clients.

        WHY: Provides interface compliance for monitoring.

        Returns:
            Number of connected clients
        """
        return len(self.connected_clients)

    def is_running(self) -> bool:
        """Check if server is running.

        WHY: Provides interface compliance for status checking.

        Returns:
            True if server is active
        """
        return self.running

    async def _heartbeat_loop(self):
        """Send periodic heartbeat events to connected clients.

        WHY: This provides a way to verify the event flow is working and
        track server health and active sessions without relying on hook events.
        """
        while self.running:
            try:
                # Wait for the interval
                await asyncio.sleep(self.heartbeat_interval)

                if not self.sio:
                    continue

                # Calculate uptime
                uptime_seconds = 0
                if self.stats.get("start_time"):
                    uptime_seconds = int(
                        (
                            datetime.now(timezone.utc) - self.stats["start_time"]
                        ).total_seconds()
                    )

                # Get active sessions from main server if available
                active_sessions = []
                if self.main_server and hasattr(
                    self.main_server, "get_active_sessions"
                ):
                    try:
                        active_sessions = self.main_server.get_active_sessions()
                    except Exception as e:
                        self.logger.debug(f"Could not get active sessions: {e}")

                # Prepare heartbeat data (using new schema)
                heartbeat_data = {
                    "type": "system",
                    "subtype": "heartbeat",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source": "server",
                    "data": {
                        "uptime_seconds": uptime_seconds,
                        "connected_clients": len(self.connected_clients),
                        "total_events": self.stats.get("events_sent", 0),
                        "active_sessions": active_sessions,
                        "server_info": {
                            "version": VersionService().get_version(),
                            "port": self.port,
                        },
                    },
                }

                # Add to event history UNCONDITIONALLY
                # WHY: Heartbeat events should persist for new clients too
                if self.main_server and hasattr(self.main_server, "event_history"):
                    self.main_server.event_history.append(heartbeat_data)
                    self.logger.debug(
                        f"Heartbeat added to history (total: {len(self.main_server.event_history)})"
                    )
                else:
                    self.logger.warning("event_history not initialized for heartbeat!")

                # Emit heartbeat to all connected clients (already using new schema)
                await self.sio.emit("system_event", heartbeat_data)

                self.logger.info(
                    f"System heartbeat sent - clients: {len(self.connected_clients)}, "
                    f"uptime: {uptime_seconds}s, events: {self.stats.get('events_sent', 0)}, "
                    f"sessions: {len(active_sessions)}"
                )

            except asyncio.CancelledError:
                # Task was cancelled, exit gracefully
                break
            except Exception as e:
                self.logger.error(f"Error in heartbeat loop: {e}")
                # Continue running even if one heartbeat fails
                await asyncio.sleep(5)  # Short delay before retry
