"""
Dashboard Event Handler for Unified Monitor
===========================================

WHY: This handler manages dashboard-specific Socket.IO events for the unified
monitor daemon. It handles client connections, status updates, and dashboard
state management.

DESIGN DECISIONS:
- Manages client connections and session state
- Provides dashboard status and health information
- Handles real-time dashboard updates
- Integrates with the unified monitor architecture
"""

import asyncio
from typing import Dict, Set

import socketio

from ....core.logging_config import get_logger


class DashboardHandler:
    """Event handler for dashboard-specific functionality.

    WHY: Manages dashboard client connections and provides real-time updates
    for the unified monitor daemon.
    """

    def __init__(self, sio: socketio.AsyncServer):
        """Initialize the dashboard handler.

        Args:
            sio: Socket.IO server instance
        """
        self.sio = sio
        self.logger = get_logger(__name__)

        # Client management
        self.connected_clients: Set[str] = set()
        self.client_info: Dict[str, Dict] = {}

    def register(self):
        """Register Socket.IO event handlers."""
        try:
            # Connection events
            self.sio.on("connect", self.handle_connect)
            self.sio.on("disconnect", self.handle_disconnect)

            # Dashboard events
            self.sio.on("dashboard:status", self.handle_get_status)
            self.sio.on("dashboard:info", self.handle_get_info)
            self.sio.on("dashboard:ping", self.handle_ping)

            # Client management
            self.sio.on("client:register", self.handle_client_register)
            self.sio.on("client:list", self.handle_client_list)

            self.logger.info("Dashboard event handlers registered")

        except Exception as e:
            self.logger.error(f"Error registering dashboard handlers: {e}")
            raise

    async def handle_connect(self, sid: str, environ: Dict):
        """Handle client connection.

        Args:
            sid: Socket.IO session ID
            environ: Connection environment
        """
        try:
            self.connected_clients.add(sid)

            # Extract client info
            client_info = {
                "connected_at": asyncio.get_event_loop().time(),
                "user_agent": environ.get("HTTP_USER_AGENT", "Unknown"),
                "remote_addr": environ.get("REMOTE_ADDR", "Unknown"),
            }
            self.client_info[sid] = client_info

            self.logger.info(f"Dashboard client connected: {sid}")

            # Send welcome message
            await self.sio.emit(
                "dashboard:welcome",
                {
                    "message": "Connected to Claude MPM Unified Monitor",
                    "session_id": sid,
                    "server_info": {"service": "unified-monitor", "version": "1.0.0"},
                },
                room=sid,
            )

            # Broadcast client count update
            await self._broadcast_client_count()

        except Exception as e:
            self.logger.error(f"Error handling client connection: {e}")

    async def handle_disconnect(self, sid: str):
        """Handle client disconnection.

        Args:
            sid: Socket.IO session ID
        """
        try:
            self.connected_clients.discard(sid)
            self.client_info.pop(sid, None)

            self.logger.info(f"Dashboard client disconnected: {sid}")

            # Broadcast client count update
            await self._broadcast_client_count()

        except Exception as e:
            self.logger.error(f"Error handling client disconnection: {e}")

    async def handle_get_status(self, sid: str, data: Dict):
        """Handle dashboard status request.

        Args:
            sid: Socket.IO session ID
            data: Request data
        """
        try:
            status = {
                "service": "unified-monitor",
                "status": "running",
                "clients_connected": len(self.connected_clients),
                "uptime": asyncio.get_event_loop().time(),
                "features": {
                    "code_analysis": True,
                    "real_ast": True,
                    "file_monitoring": True,
                    "dashboard": True,
                },
            }

            await self.sio.emit("dashboard:status:response", status, room=sid)

        except Exception as e:
            self.logger.error(f"Error getting dashboard status: {e}")
            await self.sio.emit(
                "dashboard:error", {"error": f"Status error: {e!s}"}, room=sid
            )

    async def handle_get_info(self, sid: str, data: Dict):
        """Handle dashboard info request.

        Args:
            sid: Socket.IO session ID
            data: Request data
        """
        try:
            info = {
                "service_name": "Claude MPM Unified Monitor",
                "description": "Single stable daemon for all monitoring functionality",
                "features": [
                    "Real AST Analysis",
                    "Code Tree Visualization",
                    "File System Monitoring",
                    "Socket.IO Events",
                    "HTTP Dashboard",
                ],
                "endpoints": {"dashboard": "/", "health": "/health", "api": "/api/*"},
                "events": {
                    "code_analysis": [
                        "code:analyze:file",
                        "code:analyze:directory",
                        "code:get:tree",
                    ],
                    "dashboard": [
                        "dashboard:status",
                        "dashboard:info",
                        "dashboard:ping",
                    ],
                },
            }

            await self.sio.emit("dashboard:info:response", info, room=sid)

        except Exception as e:
            self.logger.error(f"Error getting dashboard info: {e}")
            await self.sio.emit(
                "dashboard:error", {"error": f"Info error: {e!s}"}, room=sid
            )

    async def handle_ping(self, sid: str, data: Dict):
        """Handle ping request.

        Args:
            sid: Socket.IO session ID
            data: Request data
        """
        try:
            timestamp = data.get("timestamp", asyncio.get_event_loop().time())

            await self.sio.emit(
                "dashboard:pong",
                {
                    "timestamp": timestamp,
                    "server_time": asyncio.get_event_loop().time(),
                },
                room=sid,
            )

        except Exception as e:
            self.logger.error(f"Error handling ping: {e}")

    async def handle_client_register(self, sid: str, data: Dict):
        """Handle client registration.

        Args:
            sid: Socket.IO session ID
            data: Client registration data
        """
        try:
            client_name = data.get("name", f"Client-{sid[:8]}")
            client_type = data.get("type", "dashboard")

            # Update client info
            if sid in self.client_info:
                self.client_info[sid].update(
                    {"name": client_name, "type": client_type, "registered": True}
                )

            self.logger.info(f"Client registered: {client_name} ({client_type})")

            await self.sio.emit(
                "client:registered",
                {"name": client_name, "type": client_type, "session_id": sid},
                room=sid,
            )

        except Exception as e:
            self.logger.error(f"Error registering client: {e}")
            await self.sio.emit(
                "dashboard:error", {"error": f"Registration error: {e!s}"}, room=sid
            )

    async def handle_client_list(self, sid: str, data: Dict):
        """Handle client list request.

        Args:
            sid: Socket.IO session ID
            data: Request data
        """
        try:
            client_list = []
            for client_sid, info in self.client_info.items():
                client_list.append(
                    {
                        "session_id": client_sid,
                        "name": info.get("name", f"Client-{client_sid[:8]}"),
                        "type": info.get("type", "unknown"),
                        "connected_at": info.get("connected_at"),
                        "registered": info.get("registered", False),
                    }
                )

            await self.sio.emit(
                "client:list:response",
                {"clients": client_list, "total": len(client_list)},
                room=sid,
            )

        except Exception as e:
            self.logger.error(f"Error getting client list: {e}")
            await self.sio.emit(
                "dashboard:error", {"error": f"Client list error: {e!s}"}, room=sid
            )

    async def _broadcast_client_count(self):
        """Broadcast client count update to all connected clients."""
        try:
            await self.sio.emit(
                "dashboard:client:count", {"count": len(self.connected_clients)}
            )

        except Exception as e:
            self.logger.error(f"Error broadcasting client count: {e}")

    def get_stats(self) -> Dict:
        """Get handler statistics.

        Returns:
            Dictionary with handler stats
        """
        return {
            "connected_clients": len(self.connected_clients),
            "registered_clients": sum(
                1 for info in self.client_info.values() if info.get("registered", False)
            ),
            "client_types": {},
        }
