"""Standalone Socket.IO server with independent versioning and deployment agnostic design.

This server is designed to run independently of claude-mpm and maintain its own versioning.
It provides a persistent Socket.IO service that can handle multiple claude-mpm client connections.

KEY DESIGN PRINCIPLES:
1. Single server per machine - Only one instance should run
2. Persistent across sessions - Server keeps running when code is pushed  
3. Separate versioning - Server has its own version schema independent of claude-mpm
4. Version compatibility mapping - Track which server versions work with which claude-mpm versions
5. Deployment agnostic - Works with local script, PyPI, npm installations

WHY standalone architecture:
- Allows server evolution independent of claude-mpm releases
- Enables persistent monitoring across multiple claude-mpm sessions
- Provides better resource management (one server vs multiple)
- Simplifies debugging and maintenance
- Supports different installation methods (PyPI, local, Docker, etc.)
"""

import asyncio
import json
import logging
import os
import signal
import socket
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Set
from collections import deque
import importlib.metadata

try:
    import socketio
    from aiohttp import web
    SOCKETIO_AVAILABLE = True
    
    # Get Socket.IO version
    try:
        SOCKETIO_VERSION = importlib.metadata.version('python-socketio')
    except Exception:
        SOCKETIO_VERSION = 'unknown'
        
except ImportError:
    SOCKETIO_AVAILABLE = False
    socketio = None
    web = None
    SOCKETIO_VERSION = 'not-installed'

# Standalone server version - independent of claude-mpm
STANDALONE_SERVER_VERSION = "1.0.0"

# Compatibility matrix - which server versions work with which claude-mpm versions
COMPATIBILITY_MATRIX = {
    "1.0.0": {
        "claude_mpm_versions": [">=0.7.0"],
        "min_python": "3.8",
        "socketio_min": "5.11.0",
        "features": [
            "persistent_server",
            "version_compatibility",
            "process_isolation",
            "health_monitoring",
            "event_namespacing"
        ]
    }
}


class StandaloneSocketIOServer:
    """Standalone Socket.IO server with independent lifecycle and versioning.
    
    This server runs independently of claude-mpm processes and provides:
    - Version compatibility checking
    - Process isolation and management
    - Persistent operation across claude-mpm sessions
    - Health monitoring and diagnostics
    - Event namespacing and routing
    """
    
    def __init__(self, host: str = "localhost", port: int = 8765, 
                 server_id: Optional[str] = None):
        self.server_version = STANDALONE_SERVER_VERSION
        self.server_id = server_id or f"socketio-{uuid.uuid4().hex[:8]}"
        self.host = host
        self.port = port
        self.start_time = datetime.utcnow()
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Server state
        self.running = False
        self.clients: Set[str] = set()
        self.event_history: deque = deque(maxlen=10000)  # Larger history for standalone server
        self.client_versions: Dict[str, str] = {}  # Track client claude-mpm versions
        self.health_stats = {
            "events_processed": 0,
            "clients_served": 0,
            "errors": 0,
            "last_activity": None
        }
        
        # Asyncio components
        self.loop = None
        self.app = None
        self.sio = None
        self.runner = None
        self.site = None
        
        # Process management
        self.pid = os.getpid()
        self.pidfile_path = self._get_pidfile_path()
        
        if not SOCKETIO_AVAILABLE:
            self.logger.error("Socket.IO dependencies not available. Install with: pip install python-socketio aiohttp")
            return
        
        self.logger.info(f"Standalone Socket.IO server v{self.server_version} initialized")
        self.logger.info(f"Server ID: {self.server_id}, PID: {self.pid}")
        self.logger.info(f"Using python-socketio v{SOCKETIO_VERSION}")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup dedicated logging for standalone server."""
        logger = logging.getLogger(f"socketio_standalone_{self.server_id}")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                f'%(asctime)s - StandaloneSocketIO[{self.server_id}] - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        
        return logger
    
    def _get_pidfile_path(self) -> Path:
        """Get path for PID file to track running server."""
        # Use system temp directory or user home
        if os.name == 'nt':  # Windows
            temp_dir = Path(os.environ.get('TEMP', os.path.expanduser('~')))
        else:  # Unix-like
            temp_dir = Path('/tmp') if Path('/tmp').exists() else Path.home()
        
        return temp_dir / f"claude_mpm_socketio_{self.port}.pid"
    
    def check_compatibility(self, client_version: str) -> Dict[str, Any]:
        """Check if client version is compatible with this server version.
        
        Returns compatibility info including warnings and supported features.
        """
        server_compat = COMPATIBILITY_MATRIX.get(self.server_version, {})
        
        result = {
            "compatible": False,
            "server_version": self.server_version,
            "client_version": client_version,
            "warnings": [],
            "supported_features": server_compat.get("features", []),
            "requirements": {
                "min_python": server_compat.get("min_python", "3.8"),
                "socketio_min": server_compat.get("socketio_min", "5.11.0")
            }
        }
        
        # Simple version compatibility check
        # In production, you'd use proper semantic versioning
        try:
            if client_version >= "0.7.0":  # Minimum supported
                result["compatible"] = True
            else:
                result["warnings"].append(f"Client version {client_version} may not be fully supported")
                result["compatible"] = False
        except Exception as e:
            result["warnings"].append(f"Could not parse client version: {e}")
            result["compatible"] = False
        
        return result
    
    def is_already_running(self) -> bool:
        """Check if another server instance is already running on this port."""
        try:
            # Check PID file
            if self.pidfile_path.exists():
                with open(self.pidfile_path, 'r') as f:
                    old_pid = int(f.read().strip())
                
                # Check if process is still running
                try:
                    os.kill(old_pid, 0)  # Signal 0 just checks if process exists
                    self.logger.info(f"Found existing server with PID {old_pid}")
                    return True
                except OSError:
                    # Process doesn't exist, remove stale PID file
                    self.pidfile_path.unlink()
            
            # Check if port is in use
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1.0)
                result = s.connect_ex((self.host, self.port))
                if result == 0:
                    self.logger.info(f"Port {self.port} is already in use")
                    return True
                    
        except Exception as e:
            self.logger.debug(f"Error checking for existing server: {e}")
        
        return False
    
    def create_pidfile(self):
        """Create PID file to track this server instance."""
        try:
            self.pidfile_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.pidfile_path, 'w') as f:
                f.write(str(self.pid))
            self.logger.info(f"Created PID file: {self.pidfile_path}")
        except Exception as e:
            self.logger.error(f"Failed to create PID file: {e}")
    
    def remove_pidfile(self):
        """Remove PID file on shutdown."""
        try:
            if self.pidfile_path.exists():
                self.pidfile_path.unlink()
                self.logger.info(f"Removed PID file: {self.pidfile_path}")
        except Exception as e:
            self.logger.error(f"Failed to remove PID file: {e}")
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating shutdown...")
            self.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        if hasattr(signal, 'SIGHUP'):
            signal.signal(signal.SIGHUP, signal_handler)
    
    async def start_async(self):
        """Start the server asynchronously."""
        if not SOCKETIO_AVAILABLE:
            raise RuntimeError("Socket.IO dependencies not available")
        
        self.logger.info(f"Starting standalone Socket.IO server v{self.server_version}")
        
        # Create Socket.IO server with production settings
        self.sio = socketio.AsyncServer(
            cors_allowed_origins="*",  # Configure appropriately for production
            async_mode='aiohttp',
            ping_timeout=60,
            ping_interval=25,
            max_http_buffer_size=1000000,
            logger=False,  # Use our own logger
            engineio_logger=False
        )
        
        # Create aiohttp application
        self.app = web.Application()
        self.sio.attach(self.app)
        
        # Setup routes and event handlers
        self._setup_routes()
        self._setup_event_handlers()
        
        # Start the server
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        
        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()
        
        self.running = True
        self.create_pidfile()
        
        self.logger.info(f"🚀 Standalone Socket.IO server STARTED on http://{self.host}:{self.port}")
        self.logger.info(f"🔧 Server ID: {self.server_id}")
        self.logger.info(f"💾 PID file: {self.pidfile_path}")
    
    def start(self):
        """Start the server in the main thread (for standalone execution)."""
        if self.is_already_running():
            self.logger.error("Server is already running. Use stop() first or choose a different port.")
            return False
        
        self.setup_signal_handlers()
        
        # Run in main thread for standalone operation
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self._run_forever())
        except KeyboardInterrupt:
            self.logger.info("Received KeyboardInterrupt, shutting down...")
        except Exception as e:
            self.logger.error(f"Server error: {e}")
            raise
        finally:
            self.stop()
        
        return True
    
    async def _run_forever(self):
        """Run the server until stopped."""
        await self.start_async()
        
        try:
            # Keep server running with periodic health checks
            last_health_check = time.time()
            
            while self.running:
                await asyncio.sleep(1)
                
                # Periodic health check and stats update
                now = time.time()
                if now - last_health_check > 30:  # Every 30 seconds
                    self._update_health_stats()
                    last_health_check = now
                    
        except Exception as e:
            self.logger.error(f"Error in server loop: {e}")
            raise
    
    def stop(self):
        """Stop the server gracefully."""
        self.logger.info("Stopping standalone Socket.IO server...")
        self.running = False
        
        if self.loop and self.loop.is_running():
            # Schedule shutdown in the event loop
            self.loop.create_task(self._shutdown_async())
        else:
            # Direct shutdown
            asyncio.run(self._shutdown_async())
        
        self.remove_pidfile()
        self.logger.info("Server stopped")
    
    async def _shutdown_async(self):
        """Async shutdown process."""
        try:
            # Close all client connections
            if self.sio:
                await self.sio.shutdown()
            
            # Stop the web server
            if self.site:
                await self.site.stop()
            if self.runner:
                await self.runner.cleanup()
                
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
    
    def _setup_routes(self):
        """Setup HTTP routes for health checks and admin endpoints."""
        
        async def version_endpoint(request):
            """Version discovery endpoint."""
            compatibility_info = {
                "server_version": self.server_version,
                "server_id": self.server_id,
                "socketio_version": SOCKETIO_VERSION,
                "compatibility_matrix": COMPATIBILITY_MATRIX,
                "supported_client_versions": COMPATIBILITY_MATRIX[self.server_version].get("claude_mpm_versions", []),
                "features": COMPATIBILITY_MATRIX[self.server_version].get("features", [])
            }
            return web.json_response(compatibility_info)
        
        async def health_endpoint(request):
            """Health check endpoint with detailed diagnostics."""
            uptime = (datetime.utcnow() - self.start_time).total_seconds()
            
            health_info = {
                "status": "healthy" if self.running else "stopped",
                "server_version": self.server_version,
                "server_id": self.server_id,
                "pid": self.pid,
                "uptime_seconds": uptime,
                "start_time": self.start_time.isoformat() + "Z",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "clients_connected": len(self.clients),
                "client_versions": dict(self.client_versions),
                "health_stats": dict(self.health_stats),
                "port": self.port,
                "host": self.host,
                "dependencies": {
                    "socketio_version": SOCKETIO_VERSION,
                    "python_version": sys.version.split()[0]
                }
            }
            return web.json_response(health_info)
        
        async def compatibility_check(request):
            """Check compatibility with a specific client version."""
            data = await request.json()
            client_version = data.get("client_version", "unknown")
            
            compatibility = self.check_compatibility(client_version)
            return web.json_response(compatibility)
        
        async def stats_endpoint(request):
            """Server statistics endpoint."""
            stats = {
                "server_info": {
                    "version": self.server_version,
                    "id": self.server_id,
                    "uptime": (datetime.utcnow() - self.start_time).total_seconds()
                },
                "connections": {
                    "current_clients": len(self.clients),
                    "total_served": self.health_stats["clients_served"],
                    "client_versions": dict(self.client_versions)
                },
                "events": {
                    "total_processed": self.health_stats["events_processed"],
                    "history_size": len(self.event_history),
                    "last_activity": self.health_stats["last_activity"]
                },
                "errors": self.health_stats["errors"]
            }
            return web.json_response(stats)
        
        # Register routes
        self.app.router.add_get('/version', version_endpoint)
        self.app.router.add_get('/health', health_endpoint)
        self.app.router.add_get('/status', health_endpoint)  # Alias
        self.app.router.add_post('/compatibility', compatibility_check)
        self.app.router.add_get('/stats', stats_endpoint)
        
        # Serve Socket.IO client library
        self.app.router.add_static('/socket.io/', 
                                 path=Path(__file__).parent / 'static', 
                                 name='socketio_static')
    
    def _setup_event_handlers(self):
        """Setup Socket.IO event handlers."""
        
        @self.sio.event
        async def connect(sid, environ, auth):
            """Handle client connection with version compatibility checking."""
            self.clients.add(sid)
            client_addr = environ.get('REMOTE_ADDR', 'unknown')
            
            # Extract client version from auth if provided
            client_version = "unknown"
            if auth and isinstance(auth, dict):
                client_version = auth.get('claude_mpm_version', 'unknown')
            
            self.client_versions[sid] = client_version
            self.health_stats["clients_served"] += 1
            self.health_stats["last_activity"] = datetime.utcnow().isoformat() + "Z"
            
            self.logger.info(f"🔗 Client {sid} connected from {client_addr}")
            self.logger.info(f"📋 Client version: {client_version}")
            self.logger.info(f"📊 Total clients: {len(self.clients)}")
            
            # Check version compatibility
            compatibility = self.check_compatibility(client_version)
            
            # Send connection acknowledgment with compatibility info
            await self.sio.emit('connection_ack', {
                "server_version": self.server_version,
                "server_id": self.server_id,
                "compatibility": compatibility,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }, room=sid)
            
            # Send current server status
            await self._send_server_status(sid)
            
            if not compatibility["compatible"]:
                self.logger.warning(f"⚠️ Client {sid} version {client_version} has compatibility issues")
                await self.sio.emit('compatibility_warning', compatibility, room=sid)
        
        @self.sio.event
        async def disconnect(sid):
            """Handle client disconnection."""
            if sid in self.clients:
                self.clients.remove(sid)
            if sid in self.client_versions:
                del self.client_versions[sid]
            
            self.logger.info(f"🔌 Client {sid} disconnected")
            self.logger.info(f"📊 Remaining clients: {len(self.clients)}")
        
        @self.sio.event
        async def ping(sid, data=None):
            """Handle ping requests."""
            await self.sio.emit('pong', {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "server_id": self.server_id
            }, room=sid)
        
        @self.sio.event
        async def get_version(sid):
            """Handle version info requests."""
            version_info = {
                "server_version": self.server_version,
                "server_id": self.server_id,
                "socketio_version": SOCKETIO_VERSION,
                "compatibility_matrix": COMPATIBILITY_MATRIX
            }
            await self.sio.emit('version_info', version_info, room=sid)
        
        @self.sio.event
        async def claude_event(sid, data):
            """Handle events from claude-mpm clients and broadcast to other clients."""
            try:
                # Add server metadata
                enhanced_data = {
                    **data,
                    "server_id": self.server_id,
                    "received_at": datetime.utcnow().isoformat() + "Z"
                }
                
                # Store in event history
                self.event_history.append(enhanced_data)
                self.health_stats["events_processed"] += 1
                self.health_stats["last_activity"] = datetime.utcnow().isoformat() + "Z"
                
                # Broadcast to all other clients
                await self.sio.emit('claude_event', enhanced_data, skip_sid=sid)
                
                self.logger.debug(f"📤 Broadcasted claude_event from {sid} to {len(self.clients)-1} clients")
                
            except Exception as e:
                self.logger.error(f"Error handling claude_event: {e}")
                self.health_stats["errors"] += 1
        
        @self.sio.event
        async def get_history(sid, data=None):
            """Handle event history requests."""
            params = data or {}
            limit = min(params.get("limit", 100), len(self.event_history))
            
            history = list(self.event_history)[-limit:] if limit > 0 else []
            
            await self.sio.emit('event_history', {
                "events": history,
                "total_available": len(self.event_history),
                "returned": len(history)
            }, room=sid)
    
    async def _send_server_status(self, sid: str):
        """Send current server status to a client."""
        status = {
            "server_version": self.server_version,
            "server_id": self.server_id,
            "uptime": (datetime.utcnow() - self.start_time).total_seconds(),
            "clients_connected": len(self.clients),
            "events_processed": self.health_stats["events_processed"],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        await self.sio.emit('server_status', status, room=sid)
    
    def _update_health_stats(self):
        """Update health statistics."""
        self.logger.debug(f"🏥 Health check - Clients: {len(self.clients)}, "
                         f"Events: {self.health_stats['events_processed']}, "
                         f"Errors: {self.health_stats['errors']}")


def main():
    """Main entry point for standalone server execution."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Standalone Claude MPM Socket.IO Server")
    parser.add_argument("--host", default="localhost", help="Host to bind to")  
    parser.add_argument("--port", type=int, default=8765, help="Port to bind to")
    parser.add_argument("--server-id", help="Custom server ID")
    parser.add_argument("--check-running", action="store_true", 
                       help="Check if server is already running and exit")
    parser.add_argument("--stop", action="store_true", help="Stop running server")
    parser.add_argument("--version", action="store_true", help="Show version info")
    
    args = parser.parse_args()
    
    if args.version:
        print(f"Standalone Socket.IO Server v{STANDALONE_SERVER_VERSION}")
        print(f"Socket.IO v{SOCKETIO_VERSION}")
        print(f"Compatibility: {COMPATIBILITY_MATRIX[STANDALONE_SERVER_VERSION]['claude_mpm_versions']}")
        return
    
    server = StandaloneSocketIOServer(
        host=args.host,
        port=args.port,
        server_id=args.server_id
    )
    
    if args.check_running:
        if server.is_already_running():
            print(f"Server is running on {args.host}:{args.port}")
            sys.exit(0)
        else:
            print(f"No server running on {args.host}:{args.port}")
            sys.exit(1)
    
    if args.stop:
        if server.is_already_running():
            # Send termination signal to running server
            try:
                with open(server.pidfile_path, 'r') as f:
                    pid = int(f.read().strip())
                os.kill(pid, signal.SIGTERM)
                print(f"Sent stop signal to server (PID: {pid})")
            except Exception as e:
                print(f"Error stopping server: {e}")
                sys.exit(1)
        else:
            print("No server running to stop")
            sys.exit(1)
        return
    
    # Start the server
    try:
        server.start()
    except Exception as e:
        print(f"Failed to start server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()