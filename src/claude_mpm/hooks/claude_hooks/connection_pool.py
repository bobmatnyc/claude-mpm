#!/usr/bin/env python3
"""Socket.IO connection pool for Claude Code hook handler.

This module provides connection pooling for Socket.IO clients to reduce
connection overhead and implement circuit breaker patterns.
"""

import time
from typing import Any, Dict, List, Optional

# Import constants for configuration
try:
    from claude_mpm.core.constants import NetworkConfig
except ImportError:
    # Fallback values if constants module not available
    class NetworkConfig:
        SOCKETIO_PORT_RANGE = (8080, 8099)
        RECONNECTION_DELAY = 0.5
        SOCKET_WAIT_TIMEOUT = 1.0


# Socket.IO import
try:
    import socketio

    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False
    socketio = None


class SocketIOConnectionPool:
    """Connection pool for Socket.IO clients to prevent connection leaks."""

    def __init__(self, max_connections: int = 3):
        self.max_connections = max_connections
        self.connections: List[Dict[str, Any]] = []
        self.last_cleanup = time.time()

    def get_connection(self, port: int) -> Optional[Any]:
        """Get or create a connection to the specified port."""
        if time.time() - self.last_cleanup > 60:
            self._cleanup_dead_connections()
            self.last_cleanup = time.time()

        for conn in self.connections:
            if conn.get("port") == port and conn.get("client"):
                client = conn["client"]
                if self._is_connection_alive(client):
                    return client
                else:
                    self.connections.remove(conn)

        if len(self.connections) < self.max_connections:
            client = self._create_connection(port)
            if client:
                self.connections.append({"port": port, "client": client, "created": time.time()})
                return client

        if self.connections:
            oldest = min(self.connections, key=lambda x: x["created"])
            self._close_connection(oldest["client"])
            oldest["client"] = self._create_connection(port)
            oldest["port"] = port
            oldest["created"] = time.time()
            return oldest["client"]

        return None

    def _create_connection(self, port: int) -> Optional[Any]:
        """Create a new Socket.IO connection."""
        if not SOCKETIO_AVAILABLE:
            return None
        try:
            client = socketio.Client(
                reconnection=False, logger=False, engineio_logger=False  # Disable auto-reconnect
            )
            client.connect(
                f"http://localhost:{port}",
                wait=True,
                wait_timeout=NetworkConfig.SOCKET_WAIT_TIMEOUT,
            )
            if client.connected:
                return client
        except Exception:
            pass
        return None

    def _is_connection_alive(self, client: Any) -> bool:
        """Check if a connection is still alive."""
        try:
            return client and client.connected
        except:
            return False

    def _close_connection(self, client: Any) -> None:
        """Safely close a connection."""
        try:
            if client:
                client.disconnect()
        except:
            pass

    def _cleanup_dead_connections(self) -> None:
        """Remove dead connections from the pool."""
        self.connections = [
            conn for conn in self.connections if self._is_connection_alive(conn.get("client"))
        ]

    def close_all(self) -> None:
        """Close all connections in the pool."""
        for conn in self.connections:
            self._close_connection(conn.get("client"))
        self.connections.clear()
