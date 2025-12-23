"""
Unified Monitor Server for Claude MPM
====================================

WHY: This server combines HTTP dashboard serving and Socket.IO event handling
into a single, stable process. It uses real AST analysis instead of mock data
and provides all monitoring functionality on a single port.

DESIGN DECISIONS:
- Combines aiohttp HTTP server with Socket.IO server
- Uses real CodeTreeAnalyzer for AST analysis
- Single port (8765) for all functionality
- Event-driven architecture with proper handler registration
- Built for stability and daemon operation
"""

import asyncio
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

import socketio
from aiohttp import web
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from ...core.enums import ServiceState
from ...core.logging_config import get_logger
from .event_emitter import get_event_emitter
from .handlers.code_analysis import CodeAnalysisHandler
from .handlers.dashboard import DashboardHandler
from .handlers.file import FileHandler
from .handlers.hooks import HookHandler

# EventBus integration
try:
    from ...services.event_bus import EventBus

    EVENTBUS_AVAILABLE = True
except ImportError:
    EventBus = None
    EVENTBUS_AVAILABLE = False


class SvelteBuildWatcher(FileSystemEventHandler):
    """File watcher for Svelte build directory changes.

    Watches for file changes in svelte-build directory and triggers
    hot reload via Socket.IO event emission.

    STABILITY FIX: Added thread lock and stop() method to prevent timer leaks.
    """

    def __init__(
        self, sio: socketio.AsyncServer, loop: asyncio.AbstractEventLoop, logger
    ):
        """Initialize the file watcher.

        Args:
            sio: Socket.IO server instance for emitting events
            loop: Event loop for async operations
            logger: Logger instance
        """
        super().__init__()
        self.sio = sio
        self.loop = loop
        self.logger = logger
        self.debounce_timer = None
        self.debounce_delay = 0.5  # Wait 500ms after last change
        self._timer_lock = threading.Lock()  # STABILITY FIX: Prevent race condition

    def stop(self):
        """Stop the watcher and cancel any pending timers.

        STABILITY FIX: Ensures timer is cancelled on shutdown.
        """
        with self._timer_lock:
            if self.debounce_timer:
                self.debounce_timer.cancel()
                self.debounce_timer = None

    def on_any_event(self, event):
        """Handle any file system event.

        Args:
            event: File system event from watchdog
        """
        # Ignore directory events and temporary files
        if event.is_directory or event.src_path.endswith((".tmp", ".swp", "~")):
            return

        self.logger.debug(
            f"File change detected: {event.event_type} - {event.src_path}"
        )

        # STABILITY FIX: Use lock to prevent timer race condition
        with self._timer_lock:
            # Cancel existing timer
            if self.debounce_timer:
                self.debounce_timer.cancel()

            # Schedule reload after debounce delay
            self.debounce_timer = threading.Timer(
                self.debounce_delay, self._trigger_reload
            )
            self.debounce_timer.start()

    def _trigger_reload(self):
        """Trigger hot reload by emitting Socket.IO event."""
        try:
            # Schedule the async emit in the event loop
            asyncio.run_coroutine_threadsafe(self._emit_reload_event(), self.loop)
            self.logger.info("Hot reload triggered - Svelte build changed")
        except Exception as e:
            self.logger.error(f"Error triggering reload: {e}")

    async def _emit_reload_event(self):
        """Emit the reload event to all connected clients."""
        if self.sio:
            await self.sio.emit(
                "reload",
                {
                    "type": "reload",
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                    "reason": "svelte-build-updated",
                },
            )


class UnifiedMonitorServer:
    """Unified server that combines HTTP dashboard and Socket.IO functionality.

    WHY: Provides a single server process that handles all monitoring needs.
    Replaces multiple competing server implementations with one stable solution.
    """

    def __init__(
        self, host: str = "localhost", port: int = 8765, enable_hot_reload: bool = False
    ):
        """Initialize the unified monitor server.

        Args:
            host: Host to bind to
            port: Port to bind to
            enable_hot_reload: Enable file watching and hot reload for development
        """
        self.host = host
        self.port = port
        self.enable_hot_reload = enable_hot_reload
        self.logger = get_logger(__name__)

        # Core components
        self.app = None
        self.sio = None
        self.runner = None
        self.site = None

        # Event handlers
        self.code_analysis_handler = None
        self.dashboard_handler = None
        self.file_handler = None
        self.hook_handler = None

        # High-performance event emitter
        self.event_emitter = None

        # File watching (optional for dev mode)
        self.file_observer: Optional[Observer] = None
        self.file_watcher: Optional[SvelteBuildWatcher] = None

        # State
        self.running = False
        self.loop = None
        self.server_thread = None
        self.startup_error = None  # Track startup errors

        # Heartbeat tracking
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.server_start_time = time.time()
        self.heartbeat_count = 0

    def start(self) -> bool:
        """Start the unified monitor server.

        Returns:
            True if started successfully, False otherwise
        """
        try:
            self.logger.info(
                f"Starting unified monitor server on {self.host}:{self.port}"
            )

            # Start in a separate thread to avoid blocking
            self.server_thread = threading.Thread(target=self._run_server, daemon=True)
            self.server_thread.start()

            # Wait for server to start
            import time

            for _ in range(50):  # Wait up to 5 seconds
                if self.running:
                    break
                if self.startup_error:
                    # Server thread reported an error
                    self.logger.error(f"Server startup failed: {self.startup_error}")
                    return False
                time.sleep(0.1)

            if not self.running:
                error_msg = (
                    self.startup_error or "Server failed to start within timeout"
                )
                self.logger.error(error_msg)
                return False

            self.logger.info("Unified monitor server started successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to start unified monitor server: {e}")
            return False

    def _run_server(self):
        """Run the server in its own event loop."""
        loop = None
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.loop = loop

            # Run the async server
            loop.run_until_complete(self._start_async_server())

        except OSError as e:
            # Specific handling for port binding errors
            if "Address already in use" in str(e) or "[Errno 48]" in str(e):
                self.logger.error(f"Port {self.port} is already in use: {e}")
                self.startup_error = f"Port {self.port} is already in use"
            else:
                self.logger.error(f"OS error in server thread: {e}")
                self.startup_error = str(e)
        except Exception as e:
            self.logger.error(f"Error in server thread: {e}")
            self.startup_error = str(e)
        finally:
            # Always ensure loop cleanup happens
            if loop is not None:
                try:
                    # Cancel all pending tasks first
                    self._cancel_all_tasks(loop)

                    # Give tasks a moment to cancel gracefully
                    if not loop.is_closed():
                        try:
                            loop.run_until_complete(asyncio.sleep(0.1))
                        except RuntimeError:
                            # Loop might be stopped already, that's ok
                            pass

                except Exception as e:
                    self.logger.debug(f"Error during task cancellation: {e}")
                finally:
                    try:
                        # Clear the loop reference from the instance first
                        self.loop = None

                        # Stop the loop if it's still running
                        if loop.is_running():
                            loop.stop()

                        # CRITICAL: Wait a moment for the loop to stop
                        import time

                        time.sleep(0.1)

                        # STABILITY FIX: Give tasks more time to clean up before closing
                        time.sleep(0.5)

                        # Clear the event loop from the thread BEFORE closing
                        # This prevents other code from accidentally using it
                        asyncio.set_event_loop(None)

                        # Now close the loop - this is critical to prevent the kqueue error
                        if not loop.is_closed():
                            loop.close()
                            # Wait for the close to complete
                            time.sleep(0.05)

                    except Exception as e:
                        self.logger.debug(f"Error during event loop cleanup: {e}")

    async def _start_async_server(self):
        """Start the async server components."""
        try:
            # Create Socket.IO server with proper ping configuration
            self.sio = socketio.AsyncServer(
                cors_allowed_origins="*",
                logger=True,  # Enable to see Socket.IO events and connection lifecycle
                engineio_logger=True,  # Enable to see Engine.IO protocol handshake details
                ping_interval=30,  # 30 seconds ping interval (matches client expectation)
                ping_timeout=60,  # 60 seconds ping timeout (generous for stability)
            )

            # Create aiohttp application
            self.app = web.Application()

            # Attach Socket.IO to the app
            self.sio.attach(self.app)

            # Setup event handlers
            self._setup_event_handlers()

            # Setup high-performance event emitter
            await self._setup_event_emitter()

            self.logger.info(
                "Using high-performance async event architecture with direct calls"
            )

            # Start heartbeat task
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            self.logger.info("Heartbeat task started (3-minute interval)")

            # Setup file watching for hot reload (if enabled)
            if self.enable_hot_reload:
                self._setup_file_watcher()

            # Setup HTTP routes
            self._setup_http_routes()

            # Create and start the server
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()

            try:
                self.site = web.TCPSite(self.runner, self.host, self.port)
                await self.site.start()

                self.running = True
                self.logger.info(f"Server running on http://{self.host}:{self.port}")
            except OSError as e:
                # Port binding error - make sure it's reported clearly
                # Check for common port binding errors
                if (
                    "Address already in use" in str(e)
                    or "[Errno 48]" in str(e)
                    or "[Errno 98]" in str(e)
                ):
                    error_msg = f"Port {self.port} is already in use. Another process may be using this port."
                    self.logger.error(error_msg)
                    self.startup_error = error_msg
                    raise OSError(error_msg) from e
                self.logger.error(f"Failed to bind to {self.host}:{self.port}: {e}")
                self.startup_error = str(e)
                raise

            # Keep the server running
            while self.running:
                await asyncio.sleep(1)

        except Exception as e:
            self.logger.error(f"Error starting async server: {e}")
            raise
        finally:
            await self._cleanup_async()

    def _setup_event_handlers(self):
        """Setup Socket.IO event handlers."""
        try:
            # Create event handlers
            self.code_analysis_handler = CodeAnalysisHandler(self.sio)
            self.dashboard_handler = DashboardHandler(self.sio)
            self.file_handler = FileHandler(self.sio)
            self.hook_handler = HookHandler(self.sio)

            # Register handlers
            self.code_analysis_handler.register()
            self.dashboard_handler.register()
            self.file_handler.register()
            self.hook_handler.register()

            self.logger.info("Event handlers registered successfully")

        except Exception as e:
            self.logger.error(f"Error setting up event handlers: {e}")
            raise

    async def _setup_event_emitter(self):
        """Setup high-performance event emitter."""
        try:
            # Get the global event emitter instance
            self.event_emitter = await get_event_emitter()

            # Register this Socket.IO server for direct event emission
            self.event_emitter.register_socketio_server(self.sio)

            self.logger.info("Event emitter setup complete - direct calls enabled")

        except Exception as e:
            self.logger.error(f"Error setting up event emitter: {e}")
            raise

    def _setup_file_watcher(self):
        """Setup file watcher for Svelte build directory.

        Watches for changes in svelte-build and triggers hot reload.
        Only enabled when enable_hot_reload is True.
        """
        try:
            dashboard_dir = Path(__file__).resolve().parent.parent.parent / "dashboard"
            svelte_build_dir = dashboard_dir / "static" / "svelte-build"

            if not svelte_build_dir.exists():
                self.logger.warning(
                    f"Svelte build directory not found: {svelte_build_dir}. "
                    "Hot reload disabled."
                )
                return

            # Create file watcher with Socket.IO reference
            self.file_watcher = SvelteBuildWatcher(
                sio=self.sio, loop=self.loop, logger=self.logger
            )

            # Create observer and schedule watching
            self.file_observer = Observer()
            self.file_observer.schedule(
                self.file_watcher, str(svelte_build_dir), recursive=True
            )
            self.file_observer.start()

            self.logger.info(f"🔥 Hot reload enabled - watching {svelte_build_dir}")

        except Exception as e:
            self.logger.error(f"Error setting up file watcher: {e}")
            # Don't raise - hot reload is optional

    def _setup_http_routes(self):
        """Setup HTTP routes for the dashboard."""
        try:
            # Dashboard static files - use .resolve() for absolute path
            dashboard_dir = Path(__file__).resolve().parent.parent.parent / "dashboard"
            static_dir = dashboard_dir / "static"

            # Main dashboard route - serve Svelte dashboard
            async def dashboard_index(request):
                svelte_index = static_dir / "svelte-build" / "index.html"
                if svelte_index.exists():
                    with svelte_index.open(encoding="utf-8") as f:
                        content = f.read()
                    return web.Response(text=content, content_type="text/html")

                # Log error with path details for debugging
                self.logger.error(
                    f"Dashboard index.html not found at: {svelte_index.resolve()}"
                )
                return web.Response(
                    text=f"Dashboard not found. Expected location: {svelte_index.resolve()}",
                    status=404,
                )

            # Health check
            async def health_check(request):
                # Get version from VERSION file
                version = "1.0.0"
                try:
                    version_file = (
                        Path(__file__).resolve().parent.parent.parent.parent.parent
                        / "VERSION"
                    )
                    if version_file.exists():
                        version = version_file.read_text().strip()
                except Exception:
                    pass

                return web.json_response(
                    {
                        "status": ServiceState.RUNNING,
                        "service": "claude-mpm-monitor",  # Important: must match what is_our_service() checks
                        "version": version,
                        "port": self.port,
                        "pid": os.getpid(),
                        "uptime": int(time.time() - self.server_start_time),
                    }
                )

            # Event ingestion endpoint for hook handlers
            async def api_events_handler(request):
                """Handle HTTP POST events from hook handlers."""
                try:
                    data = await request.json()

                    # Extract event data
                    data.get("namespace", "hook")
                    event = data.get("event", "claude_event")
                    event_data = data.get("data", {})

                    # Emit to Socket.IO clients via the appropriate event
                    if self.sio:
                        await self.sio.emit(event, event_data)
                        self.logger.debug(f"HTTP event forwarded to Socket.IO: {event}")

                    return web.Response(status=204)  # No content response

                except Exception as e:
                    self.logger.error(f"Error handling HTTP event: {e}")
                    return web.Response(text=f"Error: {e!s}", status=500)

            # File content endpoint for file viewer
            async def api_file_handler(request):
                """Handle file content requests."""
                import json

                try:
                    data = await request.json()
                    file_path = data.get("path", "")

                    # Security check: ensure path is absolute and exists
                    if not file_path or not Path(file_path).is_absolute():
                        return web.json_response(
                            {"success": False, "error": "Invalid file path"}, status=400
                        )

                    # Check if file exists and is readable
                    if not Path(file_path).exists():
                        return web.json_response(
                            {"success": False, "error": "File not found"}, status=404
                        )

                    if not Path(file_path).is_file():
                        return web.json_response(
                            {"success": False, "error": "Path is not a file"},
                            status=400,
                        )

                    # Read file content (with size limit for safety)
                    max_size = 10 * 1024 * 1024  # 10MB limit
                    file_size = Path(file_path).stat().st_size

                    if file_size > max_size:
                        return web.json_response(
                            {
                                "success": False,
                                "error": f"File too large (>{max_size} bytes)",
                            },
                            status=413,
                        )

                    try:
                        with Path(file_path).open(
                            encoding="utf-8",
                        ) as f:
                            content = f.read()
                            lines = content.count("\n") + 1
                    except UnicodeDecodeError:
                        # Try reading as binary if UTF-8 fails
                        return web.json_response(
                            {"success": False, "error": "File is not a text file"},
                            status=415,
                        )

                    # Get file extension for type detection
                    file_ext = Path(file_path).suffix.lstrip(".")

                    return web.json_response(
                        {
                            "success": True,
                            "content": content,
                            "lines": lines,
                            "size": file_size,
                            "type": file_ext or "text",
                        }
                    )

                except json.JSONDecodeError:
                    return web.json_response(
                        {"success": False, "error": "Invalid JSON in request"},
                        status=400,
                    )
                except Exception as e:
                    self.logger.error(f"Error reading file: {e}")
                    return web.json_response(
                        {"success": False, "error": str(e)}, status=500
                    )

            # File listing endpoint for file browser
            async def api_files_handler(request):
                """List files in a directory for the file browser."""
                try:
                    # Get path from query param, default to working directory
                    path = request.query.get("path", str(Path.cwd()))
                    dir_path = Path(path)

                    if not dir_path.exists():
                        return web.json_response(
                            {"success": False, "error": "Directory not found"},
                            status=404,
                        )

                    if not dir_path.is_dir():
                        return web.json_response(
                            {"success": False, "error": "Path is not a directory"},
                            status=400,
                        )

                    # Patterns to exclude
                    exclude_patterns = {
                        ".git",
                        "node_modules",
                        "__pycache__",
                        ".svelte-kit",
                        "venv",
                        ".venv",
                        "dist",
                        "build",
                        ".next",
                        ".cache",
                        ".pytest_cache",
                        ".mypy_cache",
                        ".ruff_cache",
                        "eggs",
                        "*.egg-info",
                        ".tox",
                        ".nox",
                        "htmlcov",
                        ".coverage",
                    }

                    entries = []
                    try:
                        for entry in sorted(
                            dir_path.iterdir(),
                            key=lambda x: (not x.is_dir(), x.name.lower()),
                        ):
                            # Skip hidden files and excluded patterns
                            if entry.name.startswith(".") and entry.name not in {
                                ".env",
                                ".gitignore",
                            }:
                                if entry.name in {".git", ".svelte-kit", ".cache"}:
                                    continue
                            if entry.name in exclude_patterns:
                                continue
                            if any(
                                entry.name.endswith(p.replace("*", ""))
                                for p in exclude_patterns
                                if "*" in p
                            ):
                                continue

                            try:
                                stat = entry.stat()
                                entries.append(
                                    {
                                        "name": entry.name,
                                        "path": str(entry),
                                        "type": "directory"
                                        if entry.is_dir()
                                        else "file",
                                        "size": stat.st_size if entry.is_file() else 0,
                                        "modified": stat.st_mtime,
                                        "extension": entry.suffix.lstrip(".")
                                        if entry.is_file()
                                        else None,
                                    }
                                )
                            except (PermissionError, OSError):
                                continue

                    except PermissionError:
                        return web.json_response(
                            {"success": False, "error": "Permission denied"},
                            status=403,
                        )

                    # Separate directories and files
                    directories = [e for e in entries if e["type"] == "directory"]
                    files = [e for e in entries if e["type"] == "file"]

                    return web.json_response(
                        {
                            "success": True,
                            "path": str(dir_path),
                            "directories": directories,
                            "files": files,
                            "total_directories": len(directories),
                            "total_files": len(files),
                        }
                    )

                except Exception as e:
                    self.logger.error(f"Error listing directory: {e}")
                    return web.json_response(
                        {"success": False, "error": str(e)}, status=500
                    )

            # File read endpoint (GET) for file browser
            async def api_file_read_handler(request):
                """Read file content via GET request."""
                import base64

                try:
                    file_path = request.query.get("path", "")

                    if not file_path:
                        return web.json_response(
                            {"success": False, "error": "Path parameter required"},
                            status=400,
                        )

                    path = Path(file_path)

                    if not path.exists():
                        return web.json_response(
                            {"success": False, "error": "File not found"},
                            status=404,
                        )

                    if not path.is_file():
                        return web.json_response(
                            {"success": False, "error": "Path is not a file"},
                            status=400,
                        )

                    # Get file info
                    file_size = path.stat().st_size
                    file_ext = path.suffix.lstrip(".").lower()

                    # Define image extensions
                    image_extensions = {
                        "png",
                        "jpg",
                        "jpeg",
                        "gif",
                        "svg",
                        "webp",
                        "ico",
                        "bmp",
                    }

                    # Check if file is an image
                    if file_ext in image_extensions:
                        # Read as binary and encode to base64
                        try:
                            binary_content = path.read_bytes()
                            base64_content = base64.b64encode(binary_content).decode(
                                "utf-8"
                            )

                            # Map extension to MIME type
                            mime_types = {
                                "png": "image/png",
                                "jpg": "image/jpeg",
                                "jpeg": "image/jpeg",
                                "gif": "image/gif",
                                "svg": "image/svg+xml",
                                "webp": "image/webp",
                                "ico": "image/x-icon",
                                "bmp": "image/bmp",
                            }
                            mime_type = mime_types.get(file_ext, "image/png")

                            return web.json_response(
                                {
                                    "success": True,
                                    "path": str(path),
                                    "content": base64_content,
                                    "size": file_size,
                                    "type": "image",
                                    "mime": mime_type,
                                    "extension": file_ext,
                                }
                            )
                        except Exception as e:
                            self.logger.error(f"Error reading image file: {e}")
                            return web.json_response(
                                {
                                    "success": False,
                                    "error": f"Failed to read image: {e!s}",
                                },
                                status=500,
                            )

                    # Read text file content
                    try:
                        content = path.read_text(encoding="utf-8")
                        lines = content.count("\n") + 1
                    except UnicodeDecodeError:
                        return web.json_response(
                            {"success": False, "error": "File is not a text file"},
                            status=415,
                        )

                    return web.json_response(
                        {
                            "success": True,
                            "path": str(path),
                            "content": content,
                            "lines": lines,
                            "size": file_size,
                            "type": file_ext or "text",
                        }
                    )

                except Exception as e:
                    self.logger.error(f"Error reading file: {e}")
                    return web.json_response(
                        {"success": False, "error": str(e)}, status=500
                    )

            # Favicon handler
            async def favicon_handler(request):
                """Serve favicon.svg from static directory."""
                from aiohttp.web_fileresponse import FileResponse

                favicon_path = static_dir / "svelte-build" / "favicon.svg"
                if favicon_path.exists():
                    return FileResponse(
                        favicon_path, headers={"Content-Type": "image/svg+xml"}
                    )
                raise web.HTTPNotFound()

            # Version endpoint for dashboard build tracker
            async def version_handler(request):
                """Serve version information for dashboard build tracker."""
                try:
                    # Try to get version from version service
                    from claude_mpm.services.version_service import VersionService

                    version_service = VersionService()
                    version_info = version_service.get_version_info()

                    return web.json_response(
                        {
                            "version": version_info.get("base_version", "1.0.0"),
                            "build": version_info.get("build_number", 1),
                            "formatted_build": f"{version_info.get('build_number', 1):04d}",
                            "full_version": version_info.get("version", "v1.0.0-0001"),
                            "service": "unified-monitor",
                        }
                    )
                except Exception as e:
                    self.logger.warning(f"Error getting version info: {e}")
                    # Return default version info if service fails
                    return web.json_response(
                        {
                            "version": "1.0.0",
                            "build": 1,
                            "formatted_build": "0001",
                            "full_version": "v1.0.0-0001",
                            "service": "unified-monitor",
                        }
                    )

            # Configuration endpoint for dashboard initialization
            async def config_handler(request):
                """Return configuration for dashboard initialization."""
                import subprocess

                config = {
                    "workingDirectory": Path.cwd(),
                    "gitBranch": "Unknown",
                    "serverTime": datetime.now(timezone.utc).isoformat() + "Z",
                    "service": "unified-monitor",
                }

                # Try to get current git branch
                try:
                    result = subprocess.run(
                        ["git", "branch", "--show-current"],
                        capture_output=True,
                        text=True,
                        timeout=2,
                        cwd=Path.cwd(),
                        check=False,
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        config["gitBranch"] = result.stdout.strip()
                except Exception:
                    pass  # Keep default "Unknown" value

                return web.json_response(config)

            # Working directory endpoint
            async def working_directory_handler(request):
                """Return the current working directory."""
                return web.json_response(
                    {"working_directory": str(Path.cwd()), "success": True}
                )

            # Monitor page routes
            async def monitor_page_handler(request):
                """Serve monitor HTML pages."""
                page_name = request.match_info.get("page", "agents")
                static_dir = dashboard_dir / "static"
                file_path = static_dir / f"{page_name}.html"

                if file_path.exists() and file_path.is_file():
                    with Path(file_path).open(
                        encoding="utf-8",
                    ) as f:
                        content = f.read()
                    return web.Response(text=content, content_type="text/html")
                return web.Response(text="Page not found", status=404)

            # Git history handler
            async def git_history_handler(request: web.Request) -> web.Response:
                """Get git history for a file."""
                import subprocess

                try:
                    data = await request.json()
                    file_path = data.get("path", "")
                    limit = data.get("limit", 10)

                    if not file_path:
                        return web.json_response(
                            {
                                "success": False,
                                "error": "No path provided",
                                "commits": [],
                            },
                            status=400,
                        )

                    path = Path(file_path)
                    if not path.exists():
                        return web.json_response(
                            {
                                "success": False,
                                "error": "File not found",
                                "commits": [],
                            },
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
                            str(path),
                        ],
                        check=False,
                        capture_output=True,
                        text=True,
                        cwd=str(path.parent),
                    )

                    commits = []
                    if result.returncode == 0 and result.stdout:
                        for line in result.stdout.strip().split("\n"):
                            if line:
                                parts = line.split("|", 3)
                                if len(parts) == 4:
                                    commits.append(
                                        {
                                            "hash": parts[0][:7],
                                            "author": parts[1],
                                            "date": parts[2],
                                            "message": parts[3],
                                        }
                                    )

                    return web.json_response({"success": True, "commits": commits})
                except Exception as e:
                    return web.json_response(
                        {"success": False, "error": str(e), "commits": []}, status=500
                    )

            # Git diff handler
            async def git_diff_handler(request: web.Request) -> web.Response:
                """Get git diff for a file with optional commit selection."""
                import subprocess

                try:
                    file_path = request.query.get("path", "")
                    commit_hash = request.query.get(
                        "commit", ""
                    )  # Optional commit hash

                    if not file_path:
                        return web.json_response(
                            {
                                "success": False,
                                "error": "No path provided",
                                "diff": "",
                                "has_changes": False,
                            },
                            status=400,
                        )

                    path = Path(file_path)
                    if not path.exists():
                        return web.json_response(
                            {
                                "success": False,
                                "error": "File not found",
                                "diff": "",
                                "has_changes": False,
                            },
                            status=404,
                        )

                    # Find git repository root
                    git_root_result = subprocess.run(
                        ["git", "rev-parse", "--show-toplevel"],
                        check=False,
                        capture_output=True,
                        text=True,
                        cwd=str(path.parent),
                    )

                    if git_root_result.returncode != 0:
                        # Not in a git repository
                        return web.json_response(
                            {
                                "success": True,
                                "diff": "",
                                "has_changes": False,
                                "tracked": False,
                                "history": [],
                                "has_uncommitted": False,
                            }
                        )

                    git_root = Path(git_root_result.stdout.strip())

                    # Check if file is tracked by git
                    ls_files_result = subprocess.run(
                        ["git", "ls-files", "--error-unmatch", str(path)],
                        check=False,
                        capture_output=True,
                        text=True,
                        cwd=str(git_root),
                    )

                    if ls_files_result.returncode != 0:
                        # File is not tracked by git
                        return web.json_response(
                            {
                                "success": True,
                                "diff": "",
                                "has_changes": False,
                                "tracked": False,
                                "history": [],
                                "has_uncommitted": False,
                            }
                        )

                    # Get commit history for this file (last 5 commits)
                    history_result = subprocess.run(
                        [
                            "git",
                            "log",
                            "-5",
                            "--pretty=format:%H|%s|%ar",
                            "--",
                            str(path),
                        ],
                        check=False,
                        capture_output=True,
                        text=True,
                        cwd=str(git_root),
                    )

                    history = []
                    if history_result.returncode == 0 and history_result.stdout:
                        for line in history_result.stdout.strip().split("\n"):
                            if line:
                                parts = line.split("|", 2)
                                if len(parts) == 3:
                                    history.append(
                                        {
                                            "hash": parts[0][:7],  # Short hash
                                            "full_hash": parts[0],  # Full hash for API
                                            "message": parts[1],
                                            "time_ago": parts[2],
                                        }
                                    )

                    # Check for uncommitted changes
                    uncommitted_result = subprocess.run(
                        ["git", "diff", "HEAD", str(path)],
                        check=False,
                        capture_output=True,
                        text=True,
                        cwd=str(git_root),
                    )

                    has_uncommitted = bool(uncommitted_result.stdout.strip())

                    # Get diff based on commit parameter
                    if commit_hash:
                        # Get diff for specific commit
                        result = subprocess.run(
                            ["git", "show", commit_hash, "--", str(path)],
                            check=False,
                            capture_output=True,
                            text=True,
                            cwd=str(git_root),
                        )
                        diff_output = result.stdout if result.returncode == 0 else ""
                        has_changes = bool(diff_output.strip())
                    else:
                        # Get uncommitted diff (default behavior)
                        diff_output = uncommitted_result.stdout
                        has_changes = has_uncommitted

                    return web.json_response(
                        {
                            "success": True,
                            "diff": diff_output,
                            "has_changes": has_changes,
                            "tracked": True,
                            "history": history,
                            "has_uncommitted": has_uncommitted,
                        }
                    )
                except Exception as e:
                    return web.json_response(
                        {
                            "success": False,
                            "error": str(e),
                            "diff": "",
                            "has_changes": False,
                            "history": [],
                            "has_uncommitted": False,
                        },
                        status=500,
                    )

            # Register routes
            self.app.router.add_get("/", dashboard_index)
            self.app.router.add_get("/favicon.svg", favicon_handler)
            self.app.router.add_get("/health", health_check)
            self.app.router.add_get("/version.json", version_handler)
            self.app.router.add_get("/api/config", config_handler)
            self.app.router.add_get("/api/working-directory", working_directory_handler)
            self.app.router.add_get("/api/files", api_files_handler)
            self.app.router.add_get("/api/file/read", api_file_read_handler)
            self.app.router.add_get("/api/file/diff", git_diff_handler)
            self.app.router.add_post("/api/events", api_events_handler)
            self.app.router.add_post("/api/file", api_file_handler)
            self.app.router.add_post("/api/git-history", git_history_handler)

            # Monitor page routes
            self.app.router.add_get("/monitor", lambda r: monitor_page_handler(r))
            self.app.router.add_get(
                "/monitor/agents", lambda r: monitor_page_handler(r)
            )
            self.app.router.add_get("/monitor/tools", lambda r: monitor_page_handler(r))
            self.app.router.add_get("/monitor/files", lambda r: monitor_page_handler(r))
            self.app.router.add_get(
                "/monitor/events", lambda r: monitor_page_handler(r)
            )

            # Serve Svelte _app assets (compiled JS/CSS)
            svelte_build_dir = static_dir / "svelte-build"
            if svelte_build_dir.exists():
                svelte_app_dir = svelte_build_dir / "_app"
                if svelte_app_dir.exists():
                    # Serve _app assets with proper caching
                    async def app_assets_handler(request):
                        """Serve Svelte _app assets."""
                        from aiohttp.web_fileresponse import FileResponse

                        rel_path = request.match_info["filepath"]
                        file_path = svelte_app_dir / rel_path

                        if not file_path.exists() or not file_path.is_file():
                            raise web.HTTPNotFound()

                        response = FileResponse(file_path)

                        # Add cache headers for immutable assets
                        if "/immutable/" in str(rel_path):
                            response.headers["Cache-Control"] = (
                                "public, max-age=31536000, immutable"
                            )
                        else:
                            response.headers["Cache-Control"] = (
                                "no-cache, no-store, must-revalidate"
                            )

                        return response

                    self.app.router.add_get("/_app/{filepath:.*}", app_assets_handler)

            # Legacy static files (for backward compatibility)
            if static_dir.exists():

                async def static_handler(request):
                    """Serve legacy static files with cache-control headers for development."""

                    from aiohttp.web_fileresponse import FileResponse

                    # Get the relative path from the request
                    rel_path = request.match_info["filepath"]
                    file_path = static_dir / rel_path

                    if not file_path.exists() or not file_path.is_file():
                        raise web.HTTPNotFound()

                    # Create file response
                    response = FileResponse(file_path)

                    # Add cache-busting headers for development
                    response.headers["Cache-Control"] = (
                        "no-cache, no-store, must-revalidate"
                    )
                    response.headers["Pragma"] = "no-cache"
                    response.headers["Expires"] = "0"

                    return response

                self.app.router.add_get("/static/{filepath:.*}", static_handler)

            # Log dashboard availability
            if svelte_build_dir.exists():
                self.logger.info(
                    f"✅ Svelte dashboard available at / (root) (build: {svelte_build_dir})"
                )
            else:
                self.logger.warning(f"Svelte build not found at: {svelte_build_dir}")

            self.logger.info("HTTP routes registered successfully")

        except Exception as e:
            self.logger.error(f"Error setting up HTTP routes: {e}")
            raise

    def stop(self):
        """Stop the unified monitor server."""
        try:
            self.logger.info("Stopping unified monitor server")

            # Signal shutdown first
            self.running = False

            # If we have a loop, schedule the cleanup
            if self.loop and not self.loop.is_closed():
                try:
                    # Use call_soon_threadsafe to schedule cleanup from another thread
                    future = asyncio.run_coroutine_threadsafe(
                        self._graceful_shutdown(), self.loop
                    )
                    # Wait for cleanup to complete (with timeout)
                    future.result(timeout=3)
                except Exception as e:
                    self.logger.debug(f"Error during graceful shutdown: {e}")

            # Wait for server thread to finish with a reasonable timeout
            if self.server_thread and self.server_thread.is_alive():
                self.server_thread.join(timeout=5)

                # If thread is still alive after timeout, log a warning
                if self.server_thread.is_alive():
                    self.logger.warning("Server thread did not stop within timeout")

            # Clear all references to help with cleanup
            self.server_thread = None
            self.app = None
            self.sio = None
            self.runner = None
            self.site = None
            self.event_emitter = None

            # Give the system a moment to cleanup resources
            import time

            time.sleep(0.2)

            self.logger.info("Unified monitor server stopped")

        except Exception as e:
            self.logger.error(f"Error stopping unified monitor server: {e}")

    async def _heartbeat_loop(self):
        """Send heartbeat events every 3 minutes."""
        try:
            while self.running:
                # Wait 3 minutes (180 seconds)
                await asyncio.sleep(180)

                if not self.running:
                    break

                # Increment heartbeat count
                self.heartbeat_count += 1

                # Calculate server uptime
                uptime_seconds = int(time.time() - self.server_start_time)
                uptime_minutes = uptime_seconds // 60
                uptime_hours = uptime_minutes // 60

                # Format uptime string
                if uptime_hours > 0:
                    uptime_str = f"{uptime_hours}h {uptime_minutes % 60}m"
                else:
                    uptime_str = f"{uptime_minutes}m {uptime_seconds % 60}s"

                # Get connected client count
                connected_clients = 0
                if self.dashboard_handler:
                    connected_clients = len(self.dashboard_handler.connected_clients)

                # Create heartbeat data
                heartbeat_data = {
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                    "type": "heartbeat",
                    "server_uptime": uptime_seconds,
                    "server_uptime_formatted": uptime_str,
                    "connected_clients": connected_clients,
                    "heartbeat_number": self.heartbeat_count,
                    "message": f"Server heartbeat #{self.heartbeat_count} - Socket.IO connection active",
                    "service": "unified-monitor",
                    "port": self.port,
                }

                # Emit heartbeat event
                if self.sio:
                    await self.sio.emit("heartbeat", heartbeat_data)
                    self.logger.debug(
                        f"Heartbeat #{self.heartbeat_count} sent - "
                        f"{connected_clients} clients connected, uptime: {uptime_str}"
                    )

        except asyncio.CancelledError:
            self.logger.debug("Heartbeat task cancelled")
        except Exception as e:
            self.logger.error(f"Error in heartbeat loop: {e}")

    async def _cleanup_async(self):
        """Cleanup async resources."""
        try:
            # Stop file observer if running
            # STABILITY FIX: Ensure watcher is stopped and verify observer termination
            if self.file_observer:
                try:
                    # Stop the watcher first to cancel pending timers
                    if self.file_watcher:
                        self.file_watcher.stop()

                    # Stop the observer
                    self.file_observer.stop()
                    self.file_observer.join(timeout=2)

                    # Verify observer actually stopped
                    if self.file_observer.is_alive():
                        self.logger.warning("File observer did not stop cleanly")

                    self.logger.debug("File observer stopped")
                except Exception as e:
                    self.logger.debug(f"Error stopping file observer: {e}")
                finally:
                    self.file_observer = None
                    self.file_watcher = None

            # Cancel heartbeat task if running
            # STABILITY FIX: Add timeout to prevent infinite wait on cancellation
            if self.heartbeat_task and not self.heartbeat_task.done():
                self.heartbeat_task.cancel()
                try:
                    await asyncio.wait_for(self.heartbeat_task, timeout=2.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
                self.logger.debug("Heartbeat task cancelled")

            # Close the Socket.IO server first to stop accepting new connections
            if self.sio:
                try:
                    await self.sio.shutdown()
                    self.logger.debug("Socket.IO shutdown complete")
                except Exception as e:
                    self.logger.debug(f"Error shutting down Socket.IO: {e}")
                finally:
                    self.sio = None

            # Cleanup event emitter
            if self.event_emitter:
                try:
                    if self.sio:
                        self.event_emitter.unregister_socketio_server(self.sio)

                    # Use the global cleanup function to ensure proper cleanup
                    from .event_emitter import cleanup_event_emitter

                    await cleanup_event_emitter()

                    self.logger.info("Event emitter cleaned up")
                except Exception as e:
                    self.logger.warning(f"Error cleaning up event emitter: {e}")
                finally:
                    self.event_emitter = None

            # Stop the site (must be done before runner cleanup)
            if self.site:
                try:
                    await self.site.stop()
                    self.logger.debug("Site stopped")
                except Exception as e:
                    self.logger.debug(f"Error stopping site: {e}")
                finally:
                    self.site = None

            # Cleanup the runner (after site is stopped)
            if self.runner:
                try:
                    await self.runner.cleanup()
                    self.logger.debug("Runner cleaned up")
                except Exception as e:
                    self.logger.debug(f"Error cleaning up runner: {e}")
                finally:
                    self.runner = None

            # Clear app reference
            self.app = None

        except Exception as e:
            self.logger.error(f"Error during async cleanup: {e}")

    def get_status(self) -> Dict:
        """Get server status information.

        Returns:
            Dictionary with server status
        """
        return {
            "server_running": self.running,
            "host": self.host,
            "port": self.port,
            "handlers": {
                "code_analysis": self.code_analysis_handler is not None,
                "dashboard": self.dashboard_handler is not None,
                "file": self.file_handler is not None,
                "hooks": self.hook_handler is not None,
            },
        }

    def _cancel_all_tasks(self, loop=None):
        """Cancel all pending tasks in the event loop."""
        if loop is None:
            loop = self.loop

        if not loop or loop.is_closed():
            return

        try:
            # Get all tasks in the loop
            pending = asyncio.all_tasks(loop)

            # Count tasks to cancel
            tasks_to_cancel = [task for task in pending if not task.done()]

            if tasks_to_cancel:
                # Cancel each task
                for task in tasks_to_cancel:
                    task.cancel()

                # Wait for all tasks to complete cancellation
                gather = asyncio.gather(*tasks_to_cancel, return_exceptions=True)
                try:
                    loop.run_until_complete(gather)
                except Exception:
                    # Some tasks might fail to cancel, that's ok
                    pass

                self.logger.debug(f"Cancelled {len(tasks_to_cancel)} pending tasks")
        except Exception as e:
            self.logger.debug(f"Error cancelling tasks: {e}")

    async def _graceful_shutdown(self):
        """Perform graceful shutdown of async resources."""
        try:
            # Stop accepting new connections
            self.running = False

            # Give ongoing operations a moment to complete
            await asyncio.sleep(0.5)

            # Then cleanup resources
            await self._cleanup_async()

        except Exception as e:
            self.logger.debug(f"Error in graceful shutdown: {e}")
