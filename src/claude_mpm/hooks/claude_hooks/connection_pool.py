#!/usr/bin/env python3
"""[DEPRECATED] Socket.IO connection pool for Claude Code hook handler.

DEPRECATION NOTICE: As of v4.0.35, this module is deprecated.
All event emission now goes through the EventBus, which handles
Socket.IO connections via its relay component. This provides:
- Single event path (no duplicates)
- Better separation of concerns
- Centralized connection management
- More resilient architecture

This module is kept for backward compatibility but will be removed in v5.0.0.
Please use EventBus.publish() instead of direct Socket.IO emission.

Original purpose: Provided connection pooling for Socket.IO clients to reduce
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
        SOCKETIO_PORT_RANGE = (8765, 8785)
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
                self.connections.remove(conn)

        if len(self.connections) < self.max_connections:
            client = self._create_connection(port)
            if client:
                self.connections.append(
                    {"port": port, "client": client, "created": time.time()}
                )
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
        """Create a new Socket.IO connection with persistent keep-alive.

        WHY persistent connections:
        - Maintains connection throughout handler lifecycle
        - Automatic reconnection on disconnect
        - Reduced connection overhead for multiple events
        - Better reliability for event delivery
        """
        if not SOCKETIO_AVAILABLE:
            return None
        try:
            client = socketio.Client(
                reconnection=True,  # Enable automatic reconnection
                reconnection_attempts=5,  # Try to reconnect up to 5 times
                reconnection_delay=0.5,  # Wait 0.5s between reconnection attempts
                reconnection_delay_max=2.0,  # Max delay between attempts
                logger=False,
                engineio_logger=False,
            )

            # Set up event handlers for connection lifecycle
            @client.on("connect")
            def on_connect():
                pass  # Connection established

            @client.on("disconnect")
            def on_disconnect():
                pass  # Will automatically try to reconnect

            client.connect(
                f"http://localhost:{port}",
                wait=True,  # Wait for connection to establish
                wait_timeout=NetworkConfig.SOCKET_WAIT_TIMEOUT,
                transports=[
                    "websocket",
                    "polling",
                ],  # Try WebSocket first, fall back to polling
            )

            if client.connected:
                # Send a keep-alive ping to establish the connection
                try:
                    client.emit(
                        "ping",
                        {
                            "type": "system",
                            "subtype": "ping",
                            "timestamp": time.time(),
                            "source": "connection_pool",
                        },
                    )
                except:
                    pass  # Ignore ping errors
                return client
        except Exception:
            pass
        return None

    def _is_connection_alive(self, client: Any) -> bool:
        """Check if a connection is still alive.

        WHY enhanced check:
        - Verifies actual connection state
        - Attempts to ping server for liveness check
        - More reliable than just checking connected flag
        """
        try:
            if not client:
                return False

            # Check basic connection state
            if not client.connected:
                return False

            # Try a quick ping to verify connection is truly alive
            # This helps detect zombie connections
            try:
                # Just emit a ping, don't wait for response (faster)
                client.emit(
                    "ping",
                    {
                        "type": "system",
                        "subtype": "ping",
                        "timestamp": time.time(),
                        "source": "connection_pool",
                    },
                )
                return True
            except:
                # If ping fails, connection might be dead
                return client.connected  # Fall back to basic check
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
        """Remove dead connections from the pool and attempt reconnection.

        WHY proactive reconnection:
        - Maintains pool health
        - Ensures connections are ready when needed
        - Reduces latency for event emission
        """
        alive_connections = []
        for conn in self.connections:
            client = conn.get("client")
            if self._is_connection_alive(client):
                alive_connections.append(conn)
            else:
                # Try to reconnect dead connections
                self._close_connection(client)
                new_client = self._create_connection(conn.get("port", 8765))
                if new_client:
                    conn["client"] = new_client
                    conn["created"] = time.time()
                    alive_connections.append(conn)
        self.connections = alive_connections

    def close_all(self) -> None:
        """Close all connections in the pool."""
        for conn in self.connections:
            self._close_connection(conn.get("client"))
        self.connections.clear()

    def emit(self, event: str, data: Dict[str, Any]) -> bool:
        """Emit an event through the connection pool.

        This method provides backward compatibility for the deprecated
        connection pool. It attempts to send events directly to the
        Socket.IO server.

        Args:
            event: Event name (e.g., "claude_event")
            data: Event data dictionary

        Returns:
            bool: True if event was sent successfully
        """
        if not SOCKETIO_AVAILABLE:
            return False

        # Try multiple ports in the range
        for port in range(
            NetworkConfig.SOCKETIO_PORT_RANGE[0],
            NetworkConfig.SOCKETIO_PORT_RANGE[1] + 1,
        ):
            client = self.get_connection(port)
            if client:
                try:
                    # Emit the event
                    client.emit(event, data)
                    return True
                except Exception:
                    # Try next port
                    continue

        return False

    def cleanup(self) -> None:
        """Cleanup all connections (alias for close_all)."""
        self.close_all()
