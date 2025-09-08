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
from datetime import datetime
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

from ....core.constants import (
    SystemLimits,
    TimeoutConfig,
)
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
            self.stats["start_time"] = datetime.now()

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
                event_data = await request.json()

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

                    # Create the format expected by normalizer
                    raw_event = {
                        "type": "hook",
                        "subtype": event_data.get("hook_event_name", "unknown")
                        .lower()
                        .replace("submit", "")
                        .replace("use", "_use"),
                        "timestamp": event_data.get("timestamp"),
                        "data": event_data.get("hook_input_data", {}),
                        "source": "claude_hooks",
                        "session_id": event_data.get("session_id"),
                    }

                    # Map hook event names to dashboard subtypes
                    subtype_map = {
                        "UserPromptSubmit": "user_prompt",
                        "PreToolUse": "pre_tool",
                        "PostToolUse": "post_tool",
                        "Stop": "stop",
                        "SubagentStop": "subagent_stop",
                        "AssistantResponse": "assistant_response",
                    }
                    raw_event["subtype"] = subtype_map.get(
                        event_data.get("hook_event_name"), "unknown"
                    )

                    normalized = normalizer.normalize(raw_event, source="hook")
                    event_data = normalized.to_dict()
                    self.logger.debug(
                        f"Normalized event: type={event_data.get('type')}, subtype={event_data.get('subtype')}"
                    )

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

                        # Add to main server's event history
                        if hasattr(self.main_server, "event_history"):
                            self.main_server.event_history.append(event_data)

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

                # Return 204 No Content for success
                self.logger.debug(f"✅ HTTP event processed successfully: {event_type}")
                return web.Response(status=204)

            except Exception as e:
                self.logger.error(f"Error handling HTTP event: {e}")
                return web.Response(status=500, text=str(e))

        # Register the HTTP POST endpoint
        self.app.router.add_post("/api/events", api_events_handler)
        self.logger.info("✅ HTTP API endpoint registered at /api/events")

        # Add working directory endpoint
        async def working_directory_handler(request):
            """Handle GET /api/working-directory to provide current working directory."""
            import os
            from pathlib import Path

            try:
                working_dir = os.getcwd()
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
            import os

            file_path = request.query.get("path", "")

            if not file_path:
                return web.json_response({"error": "No path provided"}, status=400)

            abs_path = os.path.abspath(os.path.expanduser(file_path))

            # Security check - ensure file is within the project
            try:
                project_root = os.getcwd()
                if not abs_path.startswith(project_root):
                    return web.json_response({"error": "Access denied"}, status=403)
            except Exception:
                pass

            if not os.path.exists(abs_path):
                return web.json_response({"error": "File not found"}, status=404)

            if not os.path.isfile(abs_path):
                return web.json_response({"error": "Not a file"}, status=400)

            try:
                # Read file with appropriate encoding
                encodings = ["utf-8", "latin-1", "cp1252"]
                content = None

                for encoding in encodings:
                    try:
                        with open(abs_path, encoding=encoding) as f:
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
                        "name": os.path.basename(abs_path),
                        "content": content,
                        "lines": len(content.splitlines()),
                        "size": os.path.getsize(abs_path),
                    }
                )

            except PermissionError:
                return web.json_response({"error": "Permission denied"}, status=403)
            except Exception as e:
                return web.json_response({"error": str(e)}, status=500)

        self.app.router.add_get("/api/file/read", file_read_handler)
        self.logger.info("✅ File reading API registered at /api/file/read")

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
        """Setup static file serving for the dashboard."""
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

            self.dashboard_path = self._find_static_path()

            if self.dashboard_path and self.dashboard_path.exists():
                self.logger.info(f"✅ Dashboard found at: {self.dashboard_path}")

                # Serve index.html at root
                async def index_handler(request):
                    index_file = self.dashboard_path / "index.html"
                    if index_file.exists():
                        self.logger.debug(f"Serving dashboard index from: {index_file}")
                        return web.FileResponse(index_file)
                    self.logger.warning(
                        f"Dashboard index.html not found at: {index_file}"
                    )
                    return web.Response(text="Dashboard not available", status=404)

                self.app.router.add_get("/", index_handler)

                # Serve the actual dashboard template at /dashboard
                async def dashboard_handler(request):
                    dashboard_template = (
                        self.dashboard_path.parent / "templates" / "index.html"
                    )
                    if dashboard_template.exists():
                        self.logger.debug(
                            f"Serving dashboard template from: {dashboard_template}"
                        )
                        return web.FileResponse(dashboard_template)
                    # Fallback to the main index if template doesn't exist
                    self.logger.warning(
                        f"Dashboard template not found at: {dashboard_template}, falling back to index"
                    )
                    return await index_handler(request)

                self.app.router.add_get("/dashboard", dashboard_handler)

                # Serve simple code view template at /code-simple
                async def code_simple_handler(request):
                    code_simple_template = (
                        self.dashboard_path.parent / "templates" / "code_simple.html"
                    )
                    if code_simple_template.exists():
                        self.logger.debug(
                            f"Serving code simple template from: {code_simple_template}"
                        )
                        return web.FileResponse(code_simple_template)
                    # Return error if template doesn't exist
                    self.logger.warning(
                        f"Code simple template not found at: {code_simple_template}"
                    )
                    return web.Response(
                        text="Simple code view not available", status=404
                    )

                self.app.router.add_get("/code-simple", code_simple_handler)

                # Serve version.json from dashboard directory
                async def version_handler(request):
                    version_file = self.dashboard_path / "version.json"
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

                # Serve static assets (CSS, JS) from the dashboard static directory
                dashboard_static_path = (
                    get_project_root() / "src" / "claude_mpm" / "dashboard" / "static"
                )
                if dashboard_static_path.exists():
                    self.app.router.add_static(
                        "/static/", dashboard_static_path, name="dashboard_static"
                    )
                    self.logger.info(
                        f"✅ Static assets available at: {dashboard_static_path}"
                    )
                else:
                    self.logger.warning(
                        f"⚠️  Static assets directory not found at: {dashboard_static_path}"
                    )

            else:
                self.logger.warning("⚠️  No dashboard found, serving fallback response")

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
        """Find the static files directory using multiple approaches.

        WHY: The static files location varies depending on how the application
        is installed and run. We try multiple common locations to find them.
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

        # Try multiple possible locations for static files and dashboard
        possible_paths = [
            # Package-based paths (for pipx and pip installations)
            package_root / "dashboard" / "templates" if package_root else None,
            package_root / "services" / "socketio" / "static" if package_root else None,
            package_root / "static" if package_root else None,
            # Project-based paths (for development)
            project_root / "src" / "claude_mpm" / "dashboard" / "templates",
            project_root / "dashboard" / "templates",
            project_root / "src" / "claude_mpm" / "services" / "static",
            project_root / "src" / "claude_mpm" / "services" / "socketio" / "static",
            project_root / "static",
            project_root / "src" / "static",
            # Package installation locations (fallback)
            Path(__file__).parent.parent / "static",
            Path(__file__).parent / "static",
            # Scripts directory (for standalone installations)
            get_scripts_dir() / "static",
            get_scripts_dir() / "socketio" / "static",
            # Current working directory
            Path.cwd() / "static",
            Path.cwd() / "socketio" / "static",
        ]

        # Filter out None values
        possible_paths = [p for p in possible_paths if p is not None]
        self.logger.debug(
            f"Searching {len(possible_paths)} possible static file locations"
        )

        for path in possible_paths:
            self.logger.debug(f"Checking for static files at: {path}")
            try:
                if path.exists() and path.is_dir():
                    # Check if it contains expected files
                    if (path / "index.html").exists():
                        self.logger.info(f"✅ Found static files at: {path}")
                        return path
                    self.logger.debug(f"Directory exists but no index.html: {path}")
                else:
                    self.logger.debug(f"Path does not exist: {path}")
            except Exception as e:
                self.logger.debug(f"Error checking path {path}: {e}")

        self.logger.warning(
            "⚠️  Static files not found - dashboard will not be available"
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
                        (datetime.now() - self.stats["start_time"]).total_seconds()
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
                    "timestamp": datetime.now().isoformat(),
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

                # Add to event history if main server is available
                if self.main_server and hasattr(self.main_server, "event_history"):
                    self.main_server.event_history.append(heartbeat_data)

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
