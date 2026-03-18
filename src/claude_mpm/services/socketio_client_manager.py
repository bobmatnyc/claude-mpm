"""Socket.IO client manager for connecting to standalone servers.

This module provides intelligent client management that:
1. Detects existing standalone servers
2. Performs version compatibility checks
3. Handles graceful fallback to embedded servers
4. Manages connection lifecycle and reconnection

WHY this approach:
- Enables seamless integration with standalone servers
- Provides compatibility checking before connection
- Handles both local and remote server scenarios
- Maintains backward compatibility with embedded servers
"""

import asyncio
import importlib.metadata
import socket
import threading
import time
from datetime import UTC, datetime
from typing import Any

from claude_mpm.core.constants import NetworkConfig, PerformanceConfig, TimeoutConfig

try:
    import requests
    import socketio

    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False
    requests = None
    socketio = None

import contextlib

from ..core.logger import get_logger

# Get claude-mpm version for compatibility checking
try:
    CLAUDE_MPM_VERSION = importlib.metadata.version("claude-mpm")
except Exception:
    # Fallback for development
    CLAUDE_MPM_VERSION = "0.7.0-dev"


class ServerInfo:
    """Information about a detected Socket.IO server."""

    def __init__(self, host: str, port: int, response_data: dict[str, Any]):
        """Populate ServerInfo from the raw version-endpoint response payload.

        WHY: Centralises extraction of server metadata from the HTTP response dict so
        callers never need to know the exact key names returned by the server.
        WHAT: Stores host, port, and extracts server_version, server_id, socketio_version,
        features, supported_client_versions, and compatibility_matrix from response_data
        with safe .get() defaults; records detected_at timestamp.
        TEST: Call with host="localhost", port=8768, and a dict containing known keys;
        assert all attributes match the dict values and detected_at is set.
        """
        self.host = host
        self.port = port
        self.server_version = response_data.get("server_version", "unknown")
        self.server_id = response_data.get("server_id", "unknown")
        self.socketio_version = response_data.get("socketio_version", "unknown")
        self.features = response_data.get("features", [])
        self.supported_client_versions = response_data.get(
            "supported_client_versions", []
        )
        self.compatibility_matrix = response_data.get("compatibility_matrix", {})
        self.detected_at = datetime.now(UTC)

    @property
    def url(self) -> str:
        """Build and return the HTTP base URL for this server.

        WHY: Callers need a full URL string for connection and HTTP requests; computing
        it here avoids duplicating the host/port formatting across multiple call sites.
        WHAT: Returns ``http://{self.host}:{self.port}`` as a string.
        TEST: Create ServerInfo("localhost", 8768, {}); assert url == "http://localhost:8768".
        """
        return f"http://{self.host}:{self.port}"

    def is_compatible(
        self, client_version: str = CLAUDE_MPM_VERSION
    ) -> tuple[bool, list[str]]:
        """Check if this server is compatible with the client version."""
        warnings = []

        try:
            # Simple version comparison - in production use proper semver
            if client_version >= "0.7.0":
                return True, warnings
            warnings.append(
                f"Client version {client_version} may not be fully supported"
            )
            return False, warnings
        except Exception as e:
            warnings.append(f"Could not parse version: {e}")
            return False, warnings


class SocketIOClientManager:
    """Manages Socket.IO client connections with server discovery and compatibility checking."""

    def __init__(self, client_version: str = CLAUDE_MPM_VERSION):
        """Initialise the client manager with version tracking and empty connection state.

        WHY: Captures the client version used for server compatibility checks and sets
        up all connection-state attributes to their initial disconnected values.
        WHAT: Stores client_version, creates logger, initialises connection state
        (current_server, client, connected, thread, running) to None/False, and
        initialises the server discovery dict; warns if dependencies are missing.
        TEST: Instantiate SocketIOClientManager(); assert connected is False, client
        is None, and client_version matches CLAUDE_MPM_VERSION.
        """
        self.client_version = client_version
        self.logger = get_logger("socketio_client_manager")

        # Connection state
        self.current_server: ServerInfo | None = None
        self.client: socketio.AsyncClient | None = None
        self.connected = False
        self.connection_thread: threading.Thread | None = None
        self.running = False

        # Server discovery
        self.known_servers: dict[str, ServerInfo] = {}
        self.last_discovery = None

        if not DEPENDENCIES_AVAILABLE:
            self.logger.warning("Socket.IO client dependencies not available")

    def discover_servers(
        self, ports: list[int] | None = None, hosts: list[str] | None = None
    ) -> list[ServerInfo]:
        """Discover available Socket.IO servers.

        Args:
            ports: List of ports to check (default: [8765, 8766, 8767])
            hosts: List of hosts to check (default: ['localhost', '127.0.0.1'])

        Returns:
            List of discovered server info objects
        """
        if not DEPENDENCIES_AVAILABLE:
            return []

        ports = ports or [8765, 8766, 8767]
        hosts = hosts or ["localhost", "127.0.0.1"]

        discovered = []

        for host in hosts:
            for port in ports:
                try:
                    # Quick port check first
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(0.5)
                        if s.connect_ex((host, port)) != 0:
                            continue

                    # Try to get server version info
                    try:
                        response = requests.get(
                            f"http://{host}:{port}/version",
                            timeout=TimeoutConfig.QUICK_TIMEOUT,
                        )
                        if response.status_code == 200:
                            data = response.json()
                            server_info = ServerInfo(host, port, data)
                            discovered.append(server_info)

                            server_key = f"{host}:{port}"
                            self.known_servers[server_key] = server_info

                            self.logger.info(
                                f"🔍 Discovered server: {server_info.server_id} "
                                f"v{server_info.server_version} at {server_info.url}"
                            )

                    except requests.RequestException:
                        # Not a standalone server, might be another service
                        continue

                except Exception as e:
                    self.logger.debug(f"Error checking {host}:{port}: {e}")
                    continue

        self.last_discovery = datetime.now(UTC)
        return discovered

    def find_best_server(
        self, discovered_servers: list[ServerInfo] | None = None
    ) -> ServerInfo | None:
        """Find the best compatible server from discovered servers."""
        if discovered_servers is None:
            discovered_servers = self.discover_servers()

        if not discovered_servers:
            return None

        # Score servers based on compatibility and features
        scored_servers = []

        for server in discovered_servers:
            compatible, warnings = server.is_compatible(self.client_version)

            if not compatible:
                self.logger.debug(
                    f"Server {server.server_id} not compatible: {warnings}"
                )
                continue

            # Simple scoring: newer versions and more features get higher scores
            score = 0

            # Version scoring (basic semantic versioning)
            try:
                version_parts = server.server_version.split(".")
                score += int(version_parts[0]) * PerformanceConfig.VERSION_SCORE_MAJOR
                score += int(version_parts[1]) * PerformanceConfig.VERSION_SCORE_MINOR
                score += int(version_parts[2]) * PerformanceConfig.VERSION_SCORE_PATCH
            except (ValueError, IndexError):
                pass

            # Feature scoring
            score += len(server.features) * 5

            scored_servers.append((score, server))

        if not scored_servers:
            self.logger.warning("No compatible servers found")
            return None

        # Return highest scored server
        scored_servers.sort(key=lambda x: x[0], reverse=True)
        best_server = scored_servers[0][1]

        self.logger.info(
            f"🎯 Selected best server: {best_server.server_id} "
            f"v{best_server.server_version} at {best_server.url}"
        )

        return best_server

    async def connect_to_server(self, server_info: ServerInfo) -> bool:
        """Connect to a specific server with compatibility verification."""
        if not DEPENDENCIES_AVAILABLE:
            return False

        try:
            # Perform compatibility check via HTTP first
            compat_response = requests.post(
                f"{server_info.url}/compatibility",
                json={"client_version": self.client_version},
                timeout=TimeoutConfig.FILE_OPERATION_TIMEOUT,
            )

            if compat_response.status_code == 200:
                compatibility = compat_response.json()
                if not compatibility.get("compatible", False):
                    self.logger.error(
                        f"Server {server_info.server_id} rejected client version {self.client_version}"
                    )
                    return False

            # Create Socket.IO client
            self.client = socketio.AsyncClient(
                reconnection=True,
                reconnection_attempts=0,  # Infinite
                reconnection_delay=NetworkConfig.RECONNECTION_DELAY,
                reconnection_delay_max=5,
                randomization_factor=0.5,
                logger=False,
                engineio_logger=False,
            )

            # Setup event handlers
            self._setup_client_event_handlers()

            # Connect with authentication
            auth = {
                "claude_mpm_version": self.client_version,
                "client_id": f"claude-mpm-{time.time()}",
            }

            await self.client.connect(server_info.url, auth=auth)

            self.current_server = server_info
            self.connected = True

            self.logger.info(
                f"✅ Connected to server {server_info.server_id} at {server_info.url}"
            )
            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to connect to server {server_info.url}: {e}")
            if self.client:
                with contextlib.suppress(Exception):
                    await self.client.disconnect()
                self.client = None
            return False

    def _setup_client_event_handlers(self):
        """Setup event handlers for the Socket.IO client."""

        @self.client.event
        async def connect():
            """Handle Socket.IO connect event; update connection state.

            WHY: The client must track its own connection state so emit_event() can
            gate on self.connected rather than querying the socketio client each time.
            WHAT: Logs the connection at INFO level and sets self.connected = True.
            TEST: Mock client; fire connect event; assert self.connected is True.
            """
            self.logger.info("🔗 Socket.IO client connected")
            self.connected = True

        @self.client.event
        async def disconnect():
            """Handle Socket.IO disconnect event; update connection state.

            WHY: Keeping self.connected accurate prevents emit_event() from attempting
            sends on a broken connection, which would produce spurious errors.
            WHAT: Logs the disconnection at INFO level and sets self.connected = False.
            TEST: Mock client; fire disconnect event; assert self.connected is False.
            """
            self.logger.info("🔌 Socket.IO client disconnected")
            self.connected = False

        @self.client.event
        async def connection_ack(data):
            """Handle server connection acknowledgment and log any compatibility issues.

            WHY: The server sends an ack with compatibility metadata; logging warnings
            here alerts operators to version mismatches before runtime failures occur.
            WHAT: Logs the ack at INFO; checks data["compatibility"]["compatible"] and
            warns if False.
            TEST: Provide data={"compatibility": {"compatible": False, "warnings": ["x"]}};
            assert a warning log is emitted.
            """
            self.logger.info("🤝 Received connection acknowledgment")
            compatibility = data.get("compatibility", {})
            if not compatibility.get("compatible", True):
                self.logger.warning(
                    f"⚠️ Server compatibility warning: {compatibility.get('warnings', [])}"
                )

        @self.client.event
        async def compatibility_warning(data):
            """Handle explicit compatibility-warning event from server.

            WHY: The server may push compatibility warnings asynchronously after the
            initial ack; logging them here ensures they are always surfaced to operators.
            WHAT: Logs data at WARNING level.
            TEST: Fire event with data={"msg": "old client"}; assert warning log contains it.
            """
            self.logger.warning(f"⚠️ Server compatibility warning: {data}")

        @self.client.event
        async def server_status(data):
            """Handle periodic server-status update from server.

            WHY: Server status events provide operational visibility (e.g., client count)
            without requiring active polling from the client.
            WHAT: Logs the connected-client count at DEBUG level.
            TEST: Fire event with data={"clients_connected": 3}; assert debug log contains "3".
            """
            self.logger.debug(
                f"📊 Server status: {data.get('clients_connected', 0)} clients"
            )

        @self.client.event
        async def claude_event(data):
            """Handle events broadcasted from other clients."""
            event_type = data.get("type", "unknown")
            self.logger.debug(f"📥 Received claude_event: {event_type}")

    async def emit_event(self, event_type: str, data: dict[str, Any]) -> bool:
        """Emit an event to the connected server."""
        if not self.connected or not self.client:
            return False

        try:
            event_data = {
                "type": event_type,
                "timestamp": datetime.now(UTC).isoformat() + "Z",
                "data": data,
                "client_version": self.client_version,
            }

            await self.client.emit("claude_event", event_data)
            self.logger.debug(f"📤 Emitted event: {event_type}")
            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to emit event {event_type}: {e}")
            return False

    def start_connection_manager(self):
        """Start the connection manager in a background thread."""
        if self.running:
            return

        self.running = True
        self.connection_thread = threading.Thread(
            target=self._run_connection_manager, daemon=True
        )
        self.connection_thread.start()
        self.logger.info("🚀 Connection manager started")

    def stop_connection_manager(self):
        """Stop the connection manager."""
        self.running = False

        if self.connection_thread:
            self.connection_thread.join(timeout=TimeoutConfig.THREAD_JOIN_TIMEOUT)

        if self.client and self.connected:
            try:
                # Disconnect from server
                loop = asyncio.new_event_loop()
                loop.run_until_complete(self.client.disconnect())
                loop.close()
            except Exception as e:
                self.logger.error(f"Error disconnecting client: {e}")

        self.logger.info("🛑 Connection manager stopped")

    def _run_connection_manager(self):
        """Run the connection manager loop."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(self._connection_manager_loop())
        except Exception as e:
            self.logger.error(f"Connection manager error: {e}")
        finally:
            loop.close()

    async def _connection_manager_loop(self):
        """Main connection manager loop."""
        connection_attempts = 0
        max_connection_attempts = 3

        while self.running:
            try:
                if not self.connected:
                    if connection_attempts < max_connection_attempts:
                        # Try to find and connect to a server
                        best_server = self.find_best_server()

                        if best_server:
                            success = await self.connect_to_server(best_server)
                            if success:
                                connection_attempts = (
                                    0  # Reset on successful connection
                                )
                            else:
                                connection_attempts += 1
                        else:
                            self.logger.info(
                                "📡 No Socket.IO servers found, will retry..."
                            )
                            connection_attempts += 1
                    else:
                        # Too many failed attempts, wait longer
                        self.logger.warning(
                            "⏳ Max connection attempts reached, waiting 30s..."
                        )
                        await asyncio.sleep(30)
                        connection_attempts = 0  # Reset after longer wait

                # Periodic health check
                if self.connected and self.client:
                    try:
                        await self.client.emit("ping")
                    except Exception as e:
                        self.logger.warning(f"Health check failed: {e}")
                        self.connected = False

                await asyncio.sleep(5)  # Check every 5 seconds

            except Exception as e:
                self.logger.error(f"Error in connection manager loop: {e}")
                await asyncio.sleep(5)

    # Compatibility methods for existing WebSocket server interface

    def broadcast_event(self, event_type: str, data: dict[str, Any]):
        """Legacy compatibility method for broadcasting events."""
        if self.connected:
            # Schedule emit in the connection thread
            try:
                loop = asyncio.new_event_loop()
                loop.run_until_complete(self.emit_event(event_type, data))
                loop.close()
            except Exception as e:
                self.logger.error(f"Error broadcasting event {event_type}: {e}")

    def session_started(self, session_id: str, launch_method: str, working_dir: str):
        """Compatibility method for session start events."""
        self.broadcast_event(
            "session.start",
            {
                "session_id": session_id,
                "launch_method": launch_method,
                "working_directory": working_dir,
            },
        )

    def session_ended(self):
        """Compatibility method for session end events."""
        self.broadcast_event("session.end", {})

    def claude_status_changed(
        self, status: str, pid: int | None = None, message: str = ""
    ):
        """Compatibility method for Claude status events."""
        self.broadcast_event(
            "claude.status", {"status": status, "pid": pid, "message": message}
        )

    def agent_delegated(self, agent: str, task: str, status: str = "started"):
        """Compatibility method for agent delegation events."""
        self.broadcast_event(
            "agent.delegation", {"agent": agent, "task": task, "status": status}
        )

    def todo_updated(self, todos: list[dict[str, Any]]):
        """Compatibility method for todo update events."""
        self.broadcast_event("todo.update", {"todos": todos})

    @property
    def running_status(self) -> bool:
        """Compatibility property."""
        return self.running


# Global instance for easy access
_client_manager: SocketIOClientManager | None = None


def get_client_manager() -> SocketIOClientManager:
    """Get or create the global client manager instance."""
    global _client_manager
    if _client_manager is None:
        _client_manager = SocketIOClientManager()
    return _client_manager


def start_client_manager():
    """Start the global client manager."""
    manager = get_client_manager()
    manager.start_connection_manager()
    return manager


def stop_client_manager():
    """Stop the global client manager."""
    global _client_manager
    if _client_manager:
        _client_manager.stop_connection_manager()
        _client_manager = None
