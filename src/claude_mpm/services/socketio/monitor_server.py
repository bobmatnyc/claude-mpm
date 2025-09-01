"""
Lightweight MonitorServer for claude-mpm.

WHY: This module provides a minimal, independent monitoring service that:
- Runs as a stable background service on port 8766
- Only handles event collection and relay (no UI components)
- Has minimal dependencies and resource usage
- Can run as always-on background service
- Includes event buffering capabilities
- Acts as a bridge between hooks and dashboard(s)

DESIGN DECISIONS:
- Minimal Socket.IO server with only essential features
- Event buffering for reliable delivery to dashboard clients
- Independent lifecycle from dashboard service
- Configurable port with sensible defaults
- Health monitoring and status endpoints
"""

import asyncio
import threading
import time
from collections import deque
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

try:
    import socketio
    from aiohttp import web

    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False
    socketio = None
    web = None

from ...core.config import Config
from ...core.constants import SystemLimits
from ...core.logging_config import get_logger
from ..core.interfaces.communication import SocketIOServiceInterface


class MonitorServer(SocketIOServiceInterface):
    """Lightweight Socket.IO server for monitoring and event relay.

    WHY: This server acts as a stable, lightweight background service that:
    - Collects events from hooks and other system components
    - Buffers events for reliable delivery
    - Relays events to connected dashboard clients
    - Maintains minimal resource footprint
    - Can run independently of dashboard services

    This separation allows the monitor to be a stable always-on service
    while dashboards can come and go without affecting event collection.
    """

    def __init__(self, host: str = None, port: int = None):
        # Load configuration
        config = Config()
        monitor_config = config.get("monitor_server", {})

        self.host = host or monitor_config.get("host", "localhost")
        self.port = port or monitor_config.get("port", 8766)
        self.logger = get_logger(__name__ + ".MonitorServer")

        # Configuration-based settings
        self.event_buffer_size = monitor_config.get(
            "event_buffer_size", SystemLimits.MAX_EVENTS_BUFFER * 2
        )
        self.client_timeout = monitor_config.get("client_timeout", 60)
        self.health_monitoring_enabled = monitor_config.get(
            "enable_health_monitoring", True
        )

        # Server state
        self.running = False
        self.sio = None
        self.app = None
        self.runner = None
        self.site = None
        self.thread = None
        self.loop = None

        # Client management
        self.connected_clients: Set[str] = set()
        self.client_info: Dict[str, Dict[str, Any]] = {}

        # Event buffering - configurable buffer size for monitor server
        self.event_buffer = deque(maxlen=self.event_buffer_size)
        self.buffer_lock = threading.Lock()

        # Statistics
        self.stats = {
            "events_received": 0,
            "events_relayed": 0,
            "events_buffered": 0,
            "connections_total": 0,
            "start_time": None,
            "clients_connected": 0,
        }

        # Session tracking for compatibility
        self.session_id = None
        self.claude_status = "unknown"
        self.claude_pid = None
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

    def start_sync(self):
        """Start the monitor server in a background thread."""
        if not SOCKETIO_AVAILABLE:
            self.logger.error("Socket.IO not available - monitor server cannot start")
            return False

        if self.running:
            self.logger.info("Monitor server already running")
            return True

        self.logger.info(
            f"Starting lightweight monitor server on {self.host}:{self.port}"
        )

        # Start server in background thread
        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()

        # Wait for server to start
        max_wait = 10.0
        wait_interval = 0.1
        waited = 0.0

        while not self.running and waited < max_wait:
            time.sleep(wait_interval)
            waited += wait_interval

        if self.running:
            self.stats["start_time"] = datetime.now().isoformat()
            self.logger.info(
                f"Monitor server started successfully on {self.host}:{self.port}"
            )
            return True
        self.logger.error(f"Monitor server failed to start within {max_wait}s")
        return False

    def stop_sync(self):
        """Stop the monitor server."""
        if not self.running:
            return

        self.logger.info("Stopping monitor server...")
        self.running = False

        # Stop the server
        if self.loop and self.runner:
            try:
                # Schedule cleanup in the event loop
                asyncio.run_coroutine_threadsafe(self._stop_server(), self.loop)

                # Wait for thread to finish
                if self.thread and self.thread.is_alive():
                    self.thread.join(timeout=5)

            except Exception as e:
                self.logger.error(f"Error stopping monitor server: {e}")

        self.logger.info("Monitor server stopped")

    def _run_server(self):
        """Run the server in its own event loop."""
        try:
            # Create new event loop for this thread
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

            # Start the server
            self.loop.run_until_complete(self._start_server())

        except Exception as e:
            self.logger.error(f"Error in monitor server thread: {e}")
            self.running = False

    async def _start_server(self):
        """Start the Socket.IO server with minimal configuration."""
        try:
            # Create Socket.IO server with minimal configuration
            self.sio = socketio.AsyncServer(
                cors_allowed_origins="*",
                logger=False,  # Minimize logging overhead
                engineio_logger=False,
            )

            # Create minimal aiohttp application
            self.app = web.Application()
            self.sio.attach(self.app)

            # Register minimal event handlers
            self._register_events()

            # Add health check endpoint
            self.app.router.add_get("/health", self._health_check)
            self.app.router.add_get("/status", self._status_check)

            # Start the HTTP server
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()

            self.site = web.TCPSite(
                self.runner, self.host, self.port, shutdown_timeout=1.0  # Fast shutdown
            )

            await self.site.start()
            self.running = True

            self.logger.info(f"Monitor server running on {self.host}:{self.port}")

            # Keep the server running
            while self.running:
                await asyncio.sleep(1)

        except Exception as e:
            self.logger.error(f"Failed to start monitor server: {e}")
            self.running = False

    async def _stop_server(self):
        """Stop the server components."""
        try:
            if self.site:
                await self.site.stop()
            if self.runner:
                await self.runner.cleanup()
        except Exception as e:
            self.logger.error(f"Error stopping server components: {e}")

    def _register_events(self):
        """Register minimal Socket.IO events for monitoring."""

        @self.sio.event
        async def connect(sid, environ):
            """Handle client connection."""
            self.connected_clients.add(sid)
            self.client_info[sid] = {
                "connected_at": datetime.now().isoformat(),
                "client_type": "dashboard",  # Assume dashboard clients
            }
            self.stats["connections_total"] += 1
            self.stats["clients_connected"] = len(self.connected_clients)

            self.logger.info(f"Dashboard client connected: {sid}")

            # Send buffered events to new client
            await self._send_buffered_events(sid)

        @self.sio.event
        async def disconnect(sid):
            """Handle client disconnection."""
            self.connected_clients.discard(sid)
            self.client_info.pop(sid, None)
            self.stats["clients_connected"] = len(self.connected_clients)

            self.logger.info(f"Dashboard client disconnected: {sid}")

        @self.sio.event
        async def get_status(sid):
            """Handle status request from client."""
            status_data = {
                "server_type": "monitor",
                "running": self.running,
                "port": self.port,
                "connected_clients": len(self.connected_clients),
                "stats": self.stats,
                "active_sessions": list(self.active_sessions.values()),
            }
            await self.sio.emit("status_response", status_data, room=sid)

    async def _send_buffered_events(self, client_id: str):
        """Send buffered events to a newly connected client."""
        with self.buffer_lock:
            if self.event_buffer:
                self.logger.info(
                    f"Sending {len(self.event_buffer)} buffered events to {client_id}"
                )
                for event in list(self.event_buffer):
                    try:
                        await self.sio.emit(
                            event["type"], event["data"], room=client_id
                        )
                    except Exception as e:
                        self.logger.error(
                            f"Error sending buffered event to {client_id}: {e}"
                        )

    async def _health_check(self, request):
        """Health check endpoint."""
        return web.json_response(
            {
                "status": "healthy" if self.running else "unhealthy",
                "service": "monitor-server",
                "port": self.port,
                "clients": len(self.connected_clients),
            }
        )

    async def _status_check(self, request):
        """Detailed status endpoint."""
        return web.json_response(
            {
                "running": self.running,
                "port": self.port,
                "host": self.host,
                "clients_connected": len(self.connected_clients),
                "stats": self.stats,
                "active_sessions": list(self.active_sessions.values()),
                "buffer_size": len(self.event_buffer),
            }
        )

    # SocketIOServiceInterface implementation
    def broadcast_event(self, event_type: str, data: Dict[str, Any]):
        """Broadcast an event to all connected dashboard clients."""
        self.stats["events_received"] += 1

        # Buffer the event
        event_data = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }

        with self.buffer_lock:
            self.event_buffer.append(event_data)
            self.stats["events_buffered"] += 1

        # Relay to connected clients if server is running
        if self.loop and self.sio and self.connected_clients:
            asyncio.run_coroutine_threadsafe(
                self._relay_event(event_type, data), self.loop
            )

    async def _relay_event(self, event_type: str, data: Dict[str, Any]):
        """Relay event to all connected dashboard clients."""
        if not self.connected_clients:
            return

        try:
            await self.sio.emit(event_type, data)
            self.stats["events_relayed"] += 1
        except Exception as e:
            self.logger.error(f"Error relaying event {event_type}: {e}")

    def send_to_client(
        self, client_id: str, event_type: str, data: Dict[str, Any]
    ) -> bool:
        """Send an event to a specific dashboard client."""
        if not self.loop or client_id not in self.connected_clients:
            return False

        try:
            asyncio.run_coroutine_threadsafe(
                self.sio.emit(event_type, data, room=client_id), self.loop
            )
            return True
        except Exception as e:
            self.logger.error(f"Error sending to client {client_id}: {e}")
            return False

    def get_connection_count(self) -> int:
        """Get number of connected dashboard clients."""
        return len(self.connected_clients)

    def is_running(self) -> bool:
        """Check if monitor server is running."""
        return self.running

    def get_stats(self) -> Dict[str, Any]:
        """Get monitor server statistics."""
        return {
            **self.stats,
            "clients_connected": len(self.connected_clients),
            "buffer_size": len(self.event_buffer),
            "uptime": (
                (
                    datetime.now() - datetime.fromisoformat(self.stats["start_time"])
                ).total_seconds()
                if self.stats["start_time"]
                else 0
            ),
        }

    # Session tracking methods for compatibility with existing hooks
    def session_started(self, session_id: str, launch_method: str, working_dir: str):
        """Track session start."""
        self.session_id = session_id
        self.active_sessions[session_id] = {
            "session_id": session_id,
            "start_time": datetime.now().isoformat(),
            "agent": "pm",
            "status": "active",
            "launch_method": launch_method,
            "working_dir": working_dir,
        }

        self.broadcast_event(
            "session_started",
            {
                "session_id": session_id,
                "launch_method": launch_method,
                "working_dir": working_dir,
            },
        )

    def session_ended(self):
        """Track session end."""
        if self.session_id and self.session_id in self.active_sessions:
            session_data = self.active_sessions.pop(self.session_id)
            self.broadcast_event("session_ended", {"session_id": self.session_id})

    def claude_status_changed(
        self, status: str, pid: Optional[int] = None, message: str = ""
    ):
        """Track Claude status changes."""
        self.claude_status = status
        self.claude_pid = pid
        self.broadcast_event(
            "claude_status", {"status": status, "pid": pid, "message": message}
        )

    def claude_output(self, content: str, stream: str = "stdout"):
        """Relay Claude output."""
        self.broadcast_event("claude_output", {"content": content, "stream": stream})

    def agent_delegated(self, agent: str, task: str, status: str = "started"):
        """Track agent delegation."""
        if self.session_id and self.session_id in self.active_sessions:
            self.active_sessions[self.session_id]["agent"] = agent
            self.active_sessions[self.session_id]["status"] = status

        self.broadcast_event(
            "agent_delegated", {"agent": agent, "task": task, "status": status}
        )

    def todo_updated(self, todos: List[Dict[str, Any]]):
        """Relay todo updates."""
        self.broadcast_event("todos_updated", {"todos": todos})

    def ticket_created(self, ticket_id: str, title: str, priority: str = "medium"):
        """Relay ticket creation."""
        self.broadcast_event(
            "ticket_created",
            {"ticket_id": ticket_id, "title": title, "priority": priority},
        )

    def memory_loaded(self, agent_id: str, memory_size: int, sections_count: int):
        """Relay memory loaded event."""
        self.broadcast_event(
            "memory_loaded",
            {
                "agent_id": agent_id,
                "memory_size": memory_size,
                "sections_count": sections_count,
            },
        )

    def memory_created(self, agent_id: str, template_type: str):
        """Relay memory created event."""
        self.broadcast_event(
            "memory_created", {"agent_id": agent_id, "template_type": template_type}
        )

    def memory_updated(
        self, agent_id: str, learning_type: str, content: str, section: str
    ):
        """Relay memory update event."""
        self.broadcast_event(
            "memory_updated",
            {
                "agent_id": agent_id,
                "learning_type": learning_type,
                "content": content,
                "section": section,
            },
        )

    def memory_injected(self, agent_id: str, context_size: int):
        """Relay memory injection event."""
        self.broadcast_event(
            "memory_injected", {"agent_id": agent_id, "context_size": context_size}
        )

    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Get list of active sessions."""
        # Clean up old sessions (older than 1 hour)
        cutoff_time = datetime.now().timestamp() - 3600
        sessions_to_remove = []

        for session_id, session_data in self.active_sessions.items():
            try:
                start_time = datetime.fromisoformat(session_data["start_time"])
                if start_time.timestamp() < cutoff_time:
                    sessions_to_remove.append(session_id)
            except:
                pass

        for session_id in sessions_to_remove:
            del self.active_sessions[session_id]

        return list(self.active_sessions.values())
