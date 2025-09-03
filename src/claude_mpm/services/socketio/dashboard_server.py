"""
Dashboard Server with Monitor Client Integration for claude-mpm.

WHY: This module provides a dashboard server that connects to the independent
monitor server as a client, enabling decoupled architecture where:
- Dashboard provides UI on port 8765
- Dashboard connects to monitor server on port 8766 for events
- Dashboard can restart without affecting event collection
- Multiple dashboards can connect to the same monitor

DESIGN DECISIONS:
- Extends existing SocketIOServer with monitor client integration
- Provides UI functionality (HTTP server, static files, dashboard endpoints)
- Graceful degradation when monitor server is unavailable
- Event relay from monitor client to dashboard clients
- Maintains backward compatibility with existing dashboard clients
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

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

from ...core.config import Config
from ...core.logging_config import get_logger
from ..core.interfaces.communication import SocketIOServiceInterface
from .monitor_client import MonitorClient
from .server.main import SocketIOServer


class DashboardServer(SocketIOServiceInterface):
    """Dashboard server that connects to monitor server and provides UI.

    WHY: This server provides the dashboard UI while staying connected to
    the monitor server for event data. This decoupling allows:
    - Stable event collection in monitor server
    - Dashboard can be restarted for updates without losing events
    - Multiple dashboard instances can share the same monitor
    - Dashboard focuses on UI, monitor focuses on event collection
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        monitor_host: Optional[str] = None,
        monitor_port: Optional[int] = None,
    ):
        # Load configuration
        config = Config()
        dashboard_config = config.get("dashboard_server", {})

        self.host = host or dashboard_config.get("host", "localhost")
        self.port = port or dashboard_config.get("port", 8765)
        self.monitor_host = monitor_host or dashboard_config.get(
            "monitor_host", "localhost"
        )
        self.monitor_port = monitor_port or dashboard_config.get("monitor_port", 8766)

        # Configuration-based settings
        self.auto_connect_monitor = dashboard_config.get("auto_connect_monitor", True)
        self.monitor_reconnect = dashboard_config.get("monitor_reconnect", True)
        self.fallback_standalone = dashboard_config.get("fallback_standalone", True)

        self.logger = get_logger(__name__ + ".DashboardServer")

        # Dashboard server (provides UI and serves dashboard clients)
        self.dashboard_server = SocketIOServer(host=self.host, port=self.port)

        # Monitor client (connects to monitor server for events)
        self.monitor_client = MonitorClient(
            monitor_host=self.monitor_host,
            monitor_port=self.monitor_port,
            auto_reconnect=self.monitor_reconnect,
        )

        # Server state
        self.running = False
        self.stats = {
            "start_time": None,
            "dashboard_clients": 0,
            "monitor_connected": False,
            "events_relayed": 0,
        }

        # Setup event relay from monitor client to dashboard clients
        self._setup_event_relay()

    def start_sync(self):
        """Start the dashboard server and connect to monitor."""
        if not SOCKETIO_AVAILABLE:
            self.logger.error("SocketIO not available - dashboard server cannot start")
            return False

        self.logger.info(f"Starting dashboard server on {self.host}:{self.port}")
        self.logger.info(
            f"Connecting to monitor server at {self.monitor_host}:{self.monitor_port}"
        )

        # Start the dashboard server (UI server)
        self.dashboard_server.start_sync()

        # Connect to monitor server for events (if auto-connect enabled)
        monitor_connected = False
        if self.auto_connect_monitor:
            monitor_connected = self.monitor_client.start()
        else:
            self.logger.info("Auto-connect to monitor disabled by configuration")

        if not monitor_connected:
            self.logger.warning(
                "Could not connect to monitor server - dashboard will run in standalone mode"
            )

        # Update state
        self.running = self.dashboard_server.is_running()
        if self.running:
            self.stats["start_time"] = datetime.now().isoformat()
            self.stats["monitor_connected"] = monitor_connected

        self.logger.info(
            f"Dashboard server started successfully on {self.host}:{self.port} "
            f"(monitor connected: {monitor_connected})"
        )
        return self.running

    def stop_sync(self):
        """Stop the dashboard server and disconnect from monitor."""
        self.logger.info("Stopping dashboard server")

        # Stop monitor client first
        self.monitor_client.stop()

        # Stop dashboard server
        self.dashboard_server.stop_sync()

        self.running = False
        self.logger.info("Dashboard server stopped")

    def _setup_event_relay(self):
        """Setup event relay from monitor client to dashboard clients."""

        # Register handlers for all events we want to relay from monitor to dashboard
        relay_events = [
            "session_started",
            "session_ended",
            "claude_status",
            "claude_output",
            "agent_delegated",
            "todos_updated",
            "ticket_created",
            "memory_loaded",
            "memory_created",
            "memory_updated",
            "memory_injected",
            "file_changed",
            "git_status_changed",
            "project_analyzed",
            "connection_status",
            "heartbeat",
        ]

        for event_name in relay_events:
            self.monitor_client.add_event_handler(
                event_name, self._create_relay_handler(event_name)
            )

    def _create_relay_handler(self, event_name: str):
        """Create a relay handler for a specific event."""

        def relay_handler(data):
            """Relay event from monitor to dashboard clients."""
            self.stats["events_relayed"] += 1
            self.logger.debug(f"Relaying event from monitor to dashboard: {event_name}")

            # Broadcast to all dashboard clients
            self.dashboard_server.broadcast_event(event_name, data)

        return relay_handler

    # Delegate SocketIOServiceInterface methods to dashboard server
    def broadcast_event(self, event_type: str, data: Dict[str, Any]):
        """Broadcast an event to all connected dashboard clients."""
        self.dashboard_server.broadcast_event(event_type, data)

    def send_to_client(
        self, client_id: str, event_type: str, data: Dict[str, Any]
    ) -> bool:
        """Send an event to a specific dashboard client."""
        return self.dashboard_server.send_to_client(client_id, event_type, data)

    def get_connection_count(self) -> int:
        """Get number of connected dashboard clients."""
        return self.dashboard_server.get_connection_count()

    def is_running(self) -> bool:
        """Check if dashboard server is running."""
        return self.running

    def get_stats(self) -> Dict[str, Any]:
        """Get dashboard server statistics."""
        dashboard_stats = (
            self.dashboard_server.get_stats()
            if hasattr(self.dashboard_server, "get_stats")
            else {}
        )
        monitor_stats = self.monitor_client.get_stats()

        return {
            **self.stats,
            "dashboard_clients": self.get_connection_count(),
            "monitor_connected": self.monitor_client.is_connected(),
            "dashboard_stats": dashboard_stats,
            "monitor_stats": monitor_stats,
            "uptime": (
                (
                    datetime.now() - datetime.fromisoformat(self.stats["start_time"])
                ).total_seconds()
                if self.stats["start_time"]
                else 0
            ),
        }

    # Session tracking methods - these now send events to monitor server
    def session_started(self, session_id: str, launch_method: str, working_dir: str):
        """Track session start - send to monitor server."""
        # Send to monitor server if connected
        self.monitor_client.send_to_monitor(
            "session_started",
            {
                "session_id": session_id,
                "launch_method": launch_method,
                "working_dir": working_dir,
            },
        )

        # Also update dashboard server for local tracking
        self.dashboard_server.session_started(session_id, launch_method, working_dir)

    def session_ended(self):
        """Track session end - send to monitor server."""
        self.monitor_client.send_to_monitor("session_ended", {})
        self.dashboard_server.session_ended()

    def claude_status_changed(
        self, status: str, pid: Optional[int] = None, message: str = ""
    ):
        """Track Claude status changes - send to monitor server."""
        self.monitor_client.send_to_monitor(
            "claude_status", {"status": status, "pid": pid, "message": message}
        )
        self.dashboard_server.claude_status_changed(status, pid, message)

    def claude_output(self, content: str, stream: str = "stdout"):
        """Relay Claude output - send to monitor server."""
        self.monitor_client.send_to_monitor(
            "claude_output", {"content": content, "stream": stream}
        )
        self.dashboard_server.claude_output(content, stream)

    def agent_delegated(self, agent: str, task: str, status: str = "started"):
        """Track agent delegation - send to monitor server."""
        self.monitor_client.send_to_monitor(
            "agent_delegated", {"agent": agent, "task": task, "status": status}
        )
        self.dashboard_server.agent_delegated(agent, task, status)

    def todo_updated(self, todos: List[Dict[str, Any]]):
        """Relay todo updates - send to monitor server."""
        self.monitor_client.send_to_monitor("todos_updated", {"todos": todos})
        self.dashboard_server.todo_updated(todos)

    def ticket_created(self, ticket_id: str, title: str, priority: str = "medium"):
        """Relay ticket creation - send to monitor server."""
        self.monitor_client.send_to_monitor(
            "ticket_created",
            {"ticket_id": ticket_id, "title": title, "priority": priority},
        )
        self.dashboard_server.ticket_created(ticket_id, title, priority)

    def memory_loaded(self, agent_id: str, memory_size: int, sections_count: int):
        """Relay memory loaded event - send to monitor server."""
        self.monitor_client.send_to_monitor(
            "memory_loaded",
            {
                "agent_id": agent_id,
                "memory_size": memory_size,
                "sections_count": sections_count,
            },
        )
        self.dashboard_server.memory_loaded(agent_id, memory_size, sections_count)

    def memory_created(self, agent_id: str, template_type: str):
        """Relay memory created event - send to monitor server."""
        self.monitor_client.send_to_monitor(
            "memory_created", {"agent_id": agent_id, "template_type": template_type}
        )
        self.dashboard_server.memory_created(agent_id, template_type)

    def memory_updated(
        self, agent_id: str, learning_type: str, content: str, section: str
    ):
        """Relay memory update event - send to monitor server."""
        self.monitor_client.send_to_monitor(
            "memory_updated",
            {
                "agent_id": agent_id,
                "learning_type": learning_type,
                "content": content,
                "section": section,
            },
        )
        self.dashboard_server.memory_updated(agent_id, learning_type, content, section)

    def memory_injected(self, agent_id: str, context_size: int):
        """Relay memory injection event - send to monitor server."""
        self.monitor_client.send_to_monitor(
            "memory_injected", {"agent_id": agent_id, "context_size": context_size}
        )
        self.dashboard_server.memory_injected(agent_id, context_size)

    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Get list of active sessions from dashboard server."""
        return self.dashboard_server.get_active_sessions()

    # Provide access to underlying dashboard server properties
    @property
    def sio(self):
        """Access to the dashboard Socket.IO server instance."""
        return self.dashboard_server.sio

    @property
    def clients(self):
        """Access to connected dashboard clients."""
        return getattr(self.dashboard_server, "connected_clients", set())

    @property
    def connected_clients(self):
        """Access to connected dashboard clients set."""
        return getattr(self.dashboard_server, "connected_clients", set())

    @property
    def file_handler(self):
        """Access to file handler for HTTP endpoints."""
        return getattr(self.dashboard_server, "file_handler", None)

    @property
    def git_handler(self):
        """Access to git handler for HTTP endpoints."""
        return getattr(self.dashboard_server, "git_handler", None)
