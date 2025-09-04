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
import threading
from pathlib import Path
from typing import Dict

import socketio
from aiohttp import web

from ...core.logging_config import get_logger
from ...dashboard.api.simple_directory import list_directory
from .event_emitter import get_event_emitter
from .handlers.code_analysis import CodeAnalysisHandler
from .handlers.dashboard import DashboardHandler
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
        self.hook_handler = None

        # High-performance event emitter
        self.event_emitter = None

        # State
        self.running = False
        self.loop = None
        self.server_thread = None

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
                time.sleep(0.1)

            if not self.running:
                self.logger.error("Server failed to start within timeout")
                return False

            self.logger.info("Unified monitor server started successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to start unified monitor server: {e}")
            return False

    def _run_server(self):
        """Run the server in its own event loop."""
        try:
            # Create new event loop for this thread
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

            # Run the async server
            self.loop.run_until_complete(self._start_async_server())

        except Exception as e:
            self.logger.error(f"Error in server thread: {e}")
        finally:
            if self.loop:
                self.loop.close()

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

            # Setup HTTP routes
            self._setup_http_routes()

            # Create and start the server
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()

            self.site = web.TCPSite(self.runner, self.host, self.port)
            await self.site.start()

            self.running = True
            self.logger.info(f"Server running on http://{self.host}:{self.port}")

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
            self.hook_handler = HookHandler(self.sio)

            # Register handlers
            self.code_analysis_handler.register()
            self.dashboard_handler.register()
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
                return web.json_response(
                    {
                        "status": "healthy",
                        "service": "unified-monitor",
                        "version": "1.0.0",
                        "port": self.port,
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

            # Register routes
            self.app.router.add_get("/", dashboard_index)
            self.app.router.add_get("/health", health_check)
            self.app.router.add_get("/api/directory", list_directory)
            self.app.router.add_post("/api/events", api_events_handler)

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

            self.running = False

            # Wait for server thread to finish
            if self.server_thread and self.server_thread.is_alive():
                self.server_thread.join(timeout=5)

            self.logger.info("Unified monitor server stopped")

        except Exception as e:
            self.logger.error(f"Error stopping unified monitor server: {e}")

    async def _cleanup_async(self):
        """Cleanup async resources."""
        try:
            # Cleanup event emitter
            if self.event_emitter:
                try:
                    self.event_emitter.unregister_socketio_server(self.sio)
                    await self.event_emitter.close()
                    self.logger.info("Event emitter cleaned up")
                except Exception as e:
                    self.logger.warning(f"Error cleaning up event emitter: {e}")

            if self.site:
                await self.site.stop()

            if self.runner:
                await self.runner.cleanup()

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
                "hooks": self.hook_handler is not None,
            },
        }
