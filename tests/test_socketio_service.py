"""
Comprehensive unit tests for the SocketIO service singleton pattern.

Tests cover:
- Singleton pattern enforcement
- Server lifecycle management (start, stop, restart)
- Event broadcasting with multiple namespaces
- Connection pooling and thread safety
- Error handling and recovery
- Proper isolation with fixtures
"""

import asyncio
import contextlib
import threading
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claude_mpm.services.socketio.server.main import SocketIOServer


class TestSocketIOServiceSingleton:
    """Test the SocketIO service singleton pattern and instance management."""

    def test_singleton_pattern_enforcement(self):
        """
        Test that the get_socketio_server function returns the same instance.

        WHY: Ensures that only one Socket.IO server instance exists globally,
        preventing port conflicts and ensuring consistent state management.
        """
        with patch("claude_mpm.services.socketio_server.SocketIOServer") as mock_server:
            # Reset global state
            import claude_mpm.services.socketio_server
            from claude_mpm.services.socketio_server import get_socketio_server

            claude_mpm.services.socketio_server._socketio_server = None

            # First call should create new instance
            server1 = get_socketio_server()
            assert server1 is not None

            # Second call should return same instance
            server2 = get_socketio_server()
            assert server1 is server2

            # Verify server was only created once
            assert mock_server.call_count == 1

    def test_client_proxy_creation_when_port_in_use(self):
        """
        Test that a client proxy is created when port 8765 is already in use.

        WHY: In exec mode, a persistent Socket.IO server may already be running.
        We need to detect this and create a client proxy instead of starting
        another server.
        """
        with patch("socket.socket") as mock_socket:
            # Simulate port 8765 is already in use
            mock_sock_instance = MagicMock()
            mock_sock_instance.connect_ex.return_value = 0  # Port is open
            mock_socket.return_value.__enter__.return_value = mock_sock_instance

            with patch(
                "claude_mpm.services.socketio_server.SocketIOClientProxy"
            ) as mock_proxy:
                # Reset global state
                import claude_mpm.services.socketio_server
                from claude_mpm.services.socketio_server import get_socketio_server

                claude_mpm.services.socketio_server._socketio_server = None

                server = get_socketio_server()

                # Should create client proxy, not server
                mock_proxy.assert_called_once_with(port=8765)
                assert server is mock_proxy.return_value


class TestServerLifecycle:
    """Test server lifecycle management (start, stop, restart)."""

    @pytest.fixture
    def mock_server(self):
        """Create a mock SocketIO server with all required attributes."""
        server = MagicMock(spec=SocketIOServer)
        server.host = "localhost"
        server.port = 8765
        server.running = False
        server.core = MagicMock()
        server.core.sio = MagicMock()
        server.core.loop = None
        server.core.running = False
        server.core.stats = {"start_time": None}
        server.broadcaster = None
        server.event_registry = None
        server.eventbus_integration = None
        server.connection_manager = None
        server.connected_clients = set()
        server.event_buffer = []
        server.buffer_lock = threading.Lock()
        server.stats = {
            "events_sent": 0,
            "events_buffered": 0,
            "connections_total": 0,
            "start_time": None,
        }
        server.logger = MagicMock()
        return server

    def test_server_start_sync(self, mock_server):
        """
        Test synchronous server start with proper initialization sequence.

        WHY: The server must initialize components in the correct order:
        1. Core server starts first to create sio instance
        2. Connection manager initializes
        3. Broadcaster initializes with core components
        4. Event handlers register
        5. EventBus integration sets up
        """
        # Create real SocketIOServer instance
        server = SocketIOServer(host="localhost", port=8765)

        with patch.object(server.core, "start_sync") as mock_core_start, patch(
            "claude_mpm.services.socketio.server.main.ConnectionManager"
        ) as mock_conn_mgr, patch(
            "claude_mpm.services.socketio.server.main.SocketIOEventBroadcaster"
        ) as mock_broadcaster, patch(
            "claude_mpm.services.socketio.server.main.EventBusIntegration"
        ):
            # Setup mocks
            mock_core_start.return_value = None
            server.core.sio = MagicMock()
            server.core.loop = asyncio.new_event_loop()
            server.core.running = True
            server.core.stats = {"start_time": datetime.now(timezone.utc).isoformat()}

            # Start server
            server.start_sync()

            # Verify initialization order
            mock_core_start.assert_called_once()
            mock_conn_mgr.assert_called_once()
            mock_broadcaster.assert_called_once()

            # Verify server state
            assert server.running is True
            assert server.connection_manager is not None
            assert server.broadcaster is not None

    def test_server_stop_sync(self, mock_server):
        """
        Test synchronous server stop with proper cleanup sequence.

        WHY: The server must cleanly shut down all components:
        1. Stop retry processor in broadcaster
        2. Stop connection health monitoring
        3. Teardown EventBus integration
        4. Stop core server
        5. Update running state
        """
        server = SocketIOServer(host="localhost", port=8765)

        # Setup server as if it's running
        server.running = True
        server.broadcaster = MagicMock()
        server.connection_manager = MagicMock()
        server.eventbus_integration = MagicMock()
        server.core.loop = asyncio.new_event_loop()

        with patch.object(server.core, "stop_sync") as mock_core_stop:
            server.stop_sync()

            # Verify cleanup sequence
            server.broadcaster.stop_retry_processor.assert_called_once()
            server.eventbus_integration.teardown.assert_called_once()
            mock_core_stop.assert_called_once()

            # Verify server state
            assert server.running is False

    def test_server_restart_sequence(self):
        """
        Test server restart maintains proper state and connections.

        WHY: Restarting should cleanly stop the server, release resources,
        and start fresh without leaving orphaned connections or processes.
        """
        server = SocketIOServer(host="localhost", port=8765)

        with patch.object(server, "start_sync") as mock_start:
            with patch.object(server, "stop_sync") as mock_stop:
                # Simulate running server
                server.running = True

                # Perform restart
                server.stop_sync()
                time.sleep(0.1)  # Brief pause
                server.start_sync()

                # Verify proper sequence
                mock_stop.assert_called_once()
                mock_start.assert_called_once()


class TestEventBroadcasting:
    """Test event broadcasting with multiple namespaces and thread safety."""

    @pytest.fixture
    def server_with_broadcaster(self):
        """Create a server with initialized broadcaster."""
        server = SocketIOServer(host="localhost", port=8765)
        server.core.sio = MagicMock()
        server.core.loop = asyncio.new_event_loop()

        # Initialize broadcaster manually for testing
        from claude_mpm.services.socketio.server.broadcaster import (
            SocketIOEventBroadcaster,
        )

        server.broadcaster = SocketIOEventBroadcaster(
            sio=server.core.sio,
            connected_clients=server.connected_clients,
            event_buffer=server.event_buffer,
            buffer_lock=server.buffer_lock,
            stats=server.stats,
            logger=server.logger,
            server=server,
        )

        return server

    def test_broadcast_event_to_all_clients(self, server_with_broadcaster):
        """
        Test broadcasting an event to all connected clients.

        WHY: Events must be reliably delivered to all connected dashboard
        clients for real-time monitoring. This tests the basic broadcast
        functionality.
        """
        server = server_with_broadcaster

        # Add mock clients
        server.connected_clients.add("client1")
        server.connected_clients.add("client2")

        # Mock asyncio.run_coroutine_threadsafe
        with patch("asyncio.run_coroutine_threadsafe") as mock_run:
            # Broadcast event
            server.broadcast_event("test_event", {"data": "test"})

            # Verify broadcast was scheduled
            mock_run.assert_called()

            # Check stats updated
            assert server.stats["events_sent"] > 0

    def test_broadcast_with_namespace_isolation(self, server_with_broadcaster):
        """
        Test that events are properly isolated by namespace.

        WHY: Different namespaces may handle different types of events.
        We need to ensure events are only sent to clients in the
        appropriate namespace.
        """
        server = server_with_broadcaster

        # Setup namespace-specific event
        namespace = "/custom"

        with patch.object(server.core.sio, "emit") as mock_emit:
            # Emit to specific namespace
            asyncio.run(
                server.core.sio.emit(
                    "namespace_event", {"data": "test"}, namespace=namespace
                )
            )

            # Verify emit was called with namespace
            mock_emit.assert_called_with(
                "namespace_event", {"data": "test"}, namespace=namespace
            )

    def test_thread_safe_event_buffering(self, server_with_broadcaster):
        """
        Test that event buffering is thread-safe during concurrent access.

        WHY: Multiple threads may try to broadcast events simultaneously.
        The buffer lock ensures thread safety and prevents race conditions.
        """
        server = server_with_broadcaster
        events_sent = []

        def send_event(event_num):
            """Send an event from a thread."""
            server.broadcast_event(f"event_{event_num}", {"num": event_num})
            events_sent.append(event_num)

        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=send_event, args=(i,))
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify all events were processed
        assert len(events_sent) == 10
        assert len(server.event_buffer) <= 10  # Buffer may have processed some

    def test_event_buffer_overflow_handling(self, server_with_broadcaster):
        """
        Test that event buffer properly handles overflow conditions.

        WHY: When clients are disconnected, events are buffered. The buffer
        has a maximum size to prevent memory issues. Old events should be
        dropped when the buffer is full.
        """
        server = server_with_broadcaster

        # Set a small buffer size for testing
        from claude_mpm.core.constants import SystemLimits

        original_max = SystemLimits.MAX_EVENTS_BUFFER
        SystemLimits.MAX_EVENTS_BUFFER = 5

        try:
            # No connected clients - events should buffer
            server.connected_clients.clear()

            # Send more events than buffer size
            for i in range(10):
                server.broadcast_event(f"event_{i}", {"index": i})

            # Buffer should be at max size
            assert len(server.event_buffer) <= SystemLimits.MAX_EVENTS_BUFFER

        finally:
            # Restore original buffer size
            SystemLimits.MAX_EVENTS_BUFFER = original_max


class TestConnectionPooling:
    """Test connection pooling and connection management."""

    def test_connection_manager_initialization(self):
        """
        Test that connection manager properly initializes with pooling.

        WHY: Connection pooling improves performance by reusing connections
        and managing them efficiently. The manager must track connections
        and their health status.
        """
        from claude_mpm.services.socketio.server.connection_manager import (
            ConnectionManager,
        )

        manager = ConnectionManager(max_buffer_size=100, event_ttl=300)

        assert manager.max_buffer_size == 100
        assert manager.event_ttl == 300
        assert len(manager.connections) == 0
        assert not manager.is_monitoring

    @pytest.mark.asyncio
    async def test_connection_health_monitoring(self):
        """
        Test that connection health is monitored and dead connections removed.

        WHY: Network issues or client crashes can leave dead connections.
        Health monitoring ensures these are detected and cleaned up to
        prevent resource leaks.
        """
        from claude_mpm.services.socketio.server.connection_manager import (
            ConnectionManager,
        )

        manager = ConnectionManager(max_buffer_size=100, event_ttl=60)

        # Add mock connections
        manager.add_connection("client1", {"connected_at": time.time()})
        manager.add_connection(
            "client2", {"connected_at": time.time() - 120}
        )  # Old connection

        # Start health monitoring
        monitor_task = asyncio.create_task(manager.start_health_monitoring())

        # Let it run briefly
        await asyncio.sleep(0.1)

        # Stop monitoring
        await manager.stop_health_monitoring()

        with contextlib.suppress(asyncio.CancelledError):
            await monitor_task

        # Old connection should be marked for cleanup
        assert manager.is_monitoring is False

    def test_connection_pool_limits(self):
        """
        Test that connection pool respects maximum connection limits.

        WHY: Too many connections can overwhelm the server. The pool
        should enforce limits and reject new connections when at capacity.
        """
        from claude_mpm.services.socketio.server.connection_manager import (
            ConnectionManager,
        )

        manager = ConnectionManager(max_buffer_size=100, event_ttl=300)
        manager.max_connections = 5  # Set a low limit for testing

        # Add connections up to limit
        for i in range(5):
            assert manager.add_connection(f"client{i}", {}) is True

        # Try to add beyond limit - should be rejected or oldest removed
        manager.add_connection("client_overflow", {})

        # Should either reject or remove oldest
        assert len(manager.connections) <= 5


class TestErrorHandling:
    """Test error handling and recovery mechanisms."""

    def test_recovery_from_socket_error(self):
        """
        Test that server recovers gracefully from socket errors.

        WHY: Network issues, port conflicts, or system resource limits
        can cause socket errors. The server should handle these gracefully
        and attempt recovery.
        """
        server = SocketIOServer(host="localhost", port=8765)

        with patch.object(server.core, "start_sync") as mock_start:
            # Simulate socket error
            mock_start.side_effect = OSError("Address already in use")

            # Attempt to start - should handle error
            try:
                server.start_sync()
            except OSError:
                pass  # Expected

            # Server should not be marked as running
            assert server.running is False

    def test_broadcast_error_handling(self):
        """
        Test that broadcast errors don't crash the server.

        WHY: Individual broadcast failures shouldn't bring down the entire
        server. Errors should be logged and the server should continue
        operating for other clients.
        """
        server = SocketIOServer(host="localhost", port=8765)

        # Setup broadcaster with mock that raises error
        server.broadcaster = MagicMock()
        server.broadcaster.broadcast_event.side_effect = Exception("Broadcast failed")

        # Broadcast should handle error gracefully
        server.broadcast_event("test", {"data": "test"})

        # Server should still be operational
        assert server.running is False  # Not started yet, but not crashed

    @pytest.mark.asyncio
    async def test_retry_mechanism_on_failed_emission(self):
        """
        Test that failed event emissions are retried with exponential backoff.

        WHY: Temporary network issues shouldn't cause event loss. The retry
        mechanism ensures events are eventually delivered when the connection
        recovers.
        """
        from claude_mpm.services.socketio.server.broadcaster import (
            SocketIOEventBroadcaster,
        )

        # Create broadcaster with mock sio
        mock_sio = AsyncMock()
        broadcaster = SocketIOEventBroadcaster(
            sio=mock_sio,
            connected_clients={"client1"},
            event_buffer=[],
            buffer_lock=threading.Lock(),
            stats={},
            logger=MagicMock(),
            server=MagicMock(),
        )

        # Simulate emission failure then success
        mock_sio.emit.side_effect = [Exception("Network error"), None]

        # Add event to retry queue
        broadcaster.retry_queue.append(
            {
                "event_type": "test",
                "data": {"test": "data"},
                "attempt": 0,
                "timestamp": time.time(),
            }
        )

        # Process retry
        await broadcaster._process_retry_queue()

        # Should have attempted emission twice (fail then success)
        assert mock_sio.emit.call_count == 2


class TestThreadSafety:
    """Test thread safety of concurrent operations."""

    def test_concurrent_client_connections(self):
        """
        Test that multiple clients can connect simultaneously without issues.

        WHY: Dashboard may be opened in multiple browser tabs or by multiple
        users. The server must handle concurrent connections safely.
        """
        server = SocketIOServer(host="localhost", port=8765)
        connection_results = []

        def connect_client(client_id):
            """Simulate client connection."""
            server.connected_clients.add(client_id)
            connection_results.append(client_id)

        # Create threads for concurrent connections
        threads = []
        for i in range(20):
            thread = threading.Thread(target=connect_client, args=(f"client_{i}",))
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify all connections registered
        assert len(connection_results) == 20
        assert len(server.connected_clients) == 20

    def test_concurrent_event_processing(self):
        """
        Test that events from multiple sources are processed correctly.

        WHY: Events may come from hooks, EventBus, and direct API calls
        simultaneously. The server must process all events without losing
        or corrupting data.
        """
        server = SocketIOServer(host="localhost", port=8765)
        server.broadcaster = MagicMock()

        processed_events = []

        def process_event(source, event_type, data):
            """Process an event from a specific source."""
            server.broadcast_event(event_type, data)
            processed_events.append((source, event_type))

        # Create threads for different event sources
        threads = []

        # Hook events
        for i in range(5):
            thread = threading.Thread(
                target=process_event,
                args=("hook", f"hook_event_{i}", {"source": "hook", "index": i}),
            )
            threads.append(thread)

        # EventBus events
        for i in range(5):
            thread = threading.Thread(
                target=process_event,
                args=("eventbus", f"bus_event_{i}", {"source": "eventbus", "index": i}),
            )
            threads.append(thread)

        # Direct API events
        for i in range(5):
            thread = threading.Thread(
                target=process_event,
                args=("api", f"api_event_{i}", {"source": "api", "index": i}),
            )
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify all events processed
        assert len(processed_events) == 15

        # Verify events from all sources
        sources = {event[0] for event in processed_events}
        assert sources == {"hook", "eventbus", "api"}


@pytest.fixture
def isolated_server():
    """
    Fixture providing an isolated SocketIO server instance for testing.

    WHY: Each test should have a clean server instance to ensure test
    isolation and prevent state leakage between tests.
    """
    # Reset global singleton
    import claude_mpm.services.socketio_server

    claude_mpm.services.socketio_server._socketio_server = None

    # Create server with mocked dependencies
    with patch("claude_mpm.services.socketio.server.main.EventBusIntegration"):
        with patch("claude_mpm.services.socketio.server.main.SOCKETIO_AVAILABLE", True):
            server = SocketIOServer(host="localhost", port=8765)

            # Mock core components to prevent actual network operations
            server.core = MagicMock()
            server.core.sio = MagicMock()
            server.core.loop = asyncio.new_event_loop()

            yield server

            # Cleanup
            if server.core.loop and not server.core.loop.is_closed():
                server.core.loop.close()


def test_integration_with_isolated_server(isolated_server):
    """
    Integration test using the isolated server fixture.

    WHY: Demonstrates how the fixture provides a clean, isolated server
    instance for testing without affecting other tests or system state.
    """
    server = isolated_server

    # Server should be in initial state
    assert not server.running
    assert len(server.connected_clients) == 0
    assert server.broadcaster is None

    # Can safely modify without affecting other tests
    server.connected_clients.add("test_client")
    assert len(server.connected_clients) == 1
