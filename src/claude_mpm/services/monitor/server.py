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
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import socketio
from aiohttp import web

from ...core.logging_config import get_logger
from ...dashboard.api.simple_directory import list_directory
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


class UnifiedMonitorServer:
    """Unified server that combines HTTP dashboard and Socket.IO functionality.

    WHY: Provides a single server process that handles all monitoring needs.
    Replaces multiple competing server implementations with one stable solution.
    """

    def __init__(self, host: str = "localhost", port: int = 8765):
        """Initialize the unified monitor server.

        Args:
            host: Host to bind to
            port: Port to bind to
        """
        self.host = host
        self.port = port
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
            # Create Socket.IO server
            self.sio = socketio.AsyncServer(
                cors_allowed_origins="*", logger=False, engineio_logger=False
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
                if "Address already in use" in str(e) or "[Errno 48]" in str(e) or "[Errno 98]" in str(e):
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

    def _setup_http_routes(self):
        """Setup HTTP routes for the dashboard."""
        try:
            # Dashboard static files
            dashboard_dir = Path(__file__).parent.parent.parent / "dashboard"

            # Main dashboard route
            async def dashboard_index(request):
                template_path = dashboard_dir / "templates" / "index.html"
                if template_path.exists():
                    with open(template_path) as f:
                        content = f.read()
                    return web.Response(text=content, content_type="text/html")
                return web.Response(text="Dashboard not found", status=404)

            # Health check
            async def health_check(request):
                # Get version from VERSION file
                version = "1.0.0"
                try:
                    version_file = (
                        Path(__file__).parent.parent.parent.parent.parent / "VERSION"
                    )
                    if version_file.exists():
                        version = version_file.read_text().strip()
                except Exception:
                    pass

                return web.json_response(
                    {
                        "status": "healthy",
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
                    namespace = data.get("namespace", "hook")
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
                import os

                try:
                    data = await request.json()
                    file_path = data.get("path", "")

                    # Security check: ensure path is absolute and exists
                    if not file_path or not os.path.isabs(file_path):
                        return web.json_response(
                            {"success": False, "error": "Invalid file path"}, status=400
                        )

                    # Check if file exists and is readable
                    if not os.path.exists(file_path):
                        return web.json_response(
                            {"success": False, "error": "File not found"}, status=404
                        )

                    if not os.path.isfile(file_path):
                        return web.json_response(
                            {"success": False, "error": "Path is not a file"},
                            status=400,
                        )

                    # Read file content (with size limit for safety)
                    max_size = 10 * 1024 * 1024  # 10MB limit
                    file_size = os.path.getsize(file_path)

                    if file_size > max_size:
                        return web.json_response(
                            {
                                "success": False,
                                "error": f"File too large (>{max_size} bytes)",
                            },
                            status=413,
                        )

                    try:
                        with open(file_path, encoding="utf-8") as f:
                            content = f.read()
                            lines = content.count("\n") + 1
                    except UnicodeDecodeError:
                        # Try reading as binary if UTF-8 fails
                        return web.json_response(
                            {"success": False, "error": "File is not a text file"},
                            status=415,
                        )

                    # Get file extension for type detection
                    file_ext = os.path.splitext(file_path)[1].lstrip(".")

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
                import os
                import subprocess

                config = {
                    "workingDirectory": os.getcwd(),
                    "gitBranch": "Unknown",
                    "serverTime": datetime.utcnow().isoformat() + "Z",
                    "service": "unified-monitor",
                }

                # Try to get current git branch
                try:
                    result = subprocess.run(
                        ["git", "branch", "--show-current"],
                        capture_output=True,
                        text=True,
                        timeout=2,
                        cwd=os.getcwd(),
                        check=False,
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        config["gitBranch"] = result.stdout.strip()
                except Exception:
                    pass  # Keep default "Unknown" value

                return web.json_response(config)

            # Register routes
            self.app.router.add_get("/", dashboard_index)
            self.app.router.add_get("/health", health_check)
            self.app.router.add_get("/version.json", version_handler)
            self.app.router.add_get("/api/config", config_handler)
            self.app.router.add_get("/api/directory", list_directory)
            self.app.router.add_post("/api/events", api_events_handler)
            self.app.router.add_post("/api/file", api_file_handler)

            # Static files
            static_dir = dashboard_dir / "static"
            if static_dir.exists():
                self.app.router.add_static("/static/", static_dir)

            # Templates
            templates_dir = dashboard_dir / "templates"
            if templates_dir.exists():
                self.app.router.add_static("/templates/", templates_dir)

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
                    "timestamp": datetime.utcnow().isoformat() + "Z",
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
            # Cancel heartbeat task if running
            if self.heartbeat_task and not self.heartbeat_task.done():
                self.heartbeat_task.cancel()
                try:
                    await self.heartbeat_task
                except asyncio.CancelledError:
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
