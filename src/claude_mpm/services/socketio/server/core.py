"""
SocketIO Server Core for claude-mpm.

WHY: This module contains the core server management functionality extracted from
the monolithic socketio_server.py file. It handles server lifecycle, static file
serving, and basic server setup.

DESIGN DECISION: Separated core server logic from event handling and broadcasting
to create focused, maintainable modules.
"""

import asyncio
import logging
import os
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

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
from claude_mpm.services.version_service import VersionService

from ....core.constants import (
    NetworkConfig,
    PerformanceConfig,
    SystemLimits,
    TimeoutConfig,
)
from ....core.interfaces import SocketIOServiceInterface
from ....core.logging_config import get_logger, log_operation, log_performance_context
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
            # Create Socket.IO server with proper ping/pong configuration
            self.sio = socketio.AsyncServer(
                cors_allowed_origins="*",
                logger=False,  # Disable Socket.IO's own logging
                engineio_logger=False,
                ping_interval=25,  # Send ping every 25 seconds
                ping_timeout=60,   # Wait 60 seconds for pong response
                max_http_buffer_size=1e8,  # 100MB max buffer
            )

            # Create aiohttp application
            self.app = web.Application()
            self.sio.attach(self.app)

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

            # Start heartbeat task
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            self.logger.info("Started system heartbeat task")

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
                try:
                    await self.heartbeat_task
                except asyncio.CancelledError:
                    pass
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

    def _setup_static_files(self):
        """Setup static file serving for the dashboard."""
        try:
            # Add debug logging for deployment context
            try:
                from ....core.unified_paths import PathContext
                deployment_context = PathContext.detect_deployment_context()
                self.logger.debug(f"Setting up static files in {deployment_context.value} mode")
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
                    else:
                        self.logger.warning(f"Dashboard index.html not found at: {index_file}")
                        return web.Response(text="Dashboard not available", status=404)

                self.app.router.add_get("/", index_handler)
                
                # Serve version.json from dashboard directory
                async def version_handler(request):
                    version_file = self.dashboard_path / "version.json"
                    if version_file.exists():
                        self.logger.debug(f"Serving version.json from: {version_file}")
                        return web.FileResponse(version_file)
                    else:
                        # Return default version info if file doesn't exist
                        return web.json_response({
                            "version": "1.0.0",
                            "build": 1,
                            "formatted_build": "0001",
                            "full_version": "v1.0.0-0001"
                        })
                
                self.app.router.add_get("/version.json", version_handler)

                # Serve static assets (CSS, JS) from the dashboard static directory
                dashboard_static_path = (
                    get_project_root() / "src" / "claude_mpm" / "dashboard" / "static"
                )
                if dashboard_static_path.exists():
                    self.app.router.add_static(
                        "/static/", dashboard_static_path, name="dashboard_static"
                    )
                    self.logger.info(f"✅ Static assets available at: {dashboard_static_path}")
                else:
                    self.logger.warning(f"⚠️  Static assets directory not found at: {dashboard_static_path}")

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
        self.logger.debug(f"Searching {len(possible_paths)} possible static file locations")

        for path in possible_paths:
            self.logger.debug(f"Checking for static files at: {path}")
            try:
                if path.exists() and path.is_dir():
                    # Check if it contains expected files
                    if (path / "index.html").exists():
                        self.logger.info(f"✅ Found static files at: {path}")
                        return path
                    else:
                        self.logger.debug(f"Directory exists but no index.html: {path}")
                else:
                    self.logger.debug(f"Path does not exist: {path}")
            except Exception as e:
                self.logger.debug(f"Error checking path {path}: {e}")

        self.logger.warning("⚠️  Static files not found - dashboard will not be available")
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
                    uptime_seconds = int((datetime.now() - self.stats["start_time"]).total_seconds())
                
                # Get active sessions from main server if available
                active_sessions = []
                if self.main_server and hasattr(self.main_server, 'get_active_sessions'):
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
                if self.main_server and hasattr(self.main_server, 'event_history'):
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
