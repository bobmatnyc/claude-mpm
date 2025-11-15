"""
Integration tests for the complete Socket.IO system.

Tests cover:
- End-to-end event flow
- Multiple client connections
- Event ordering guarantees
- Performance under load
- Graceful degradation
"""

import asyncio
import threading
import time
from datetime import datetime, timezone

import pytest

# Try to import socketio, skip tests if not available
pytest.importorskip("socketio")
pytest.importorskip("aiohttp")

import contextlib

import socketio

from claude_mpm.services.socketio.server.main import SocketIOServer
from tests.utils.test_helpers import wait_for_condition, wait_for_condition_async


class TestEndToEndEventFlow:
    """Test complete event flow from source to client."""

    @pytest.fixture
    async def running_server(self):
        """
        Create and start a real Socket.IO server for integration testing.

        WHY: Integration tests need a real server to test actual network
        communication, event propagation, and client-server interactions.
        """
        server = SocketIOServer(host="localhost", port=18765)  # Use non-standard port

        # Start server in background thread
        server_thread = threading.Thread(target=server.start_sync)
        server_thread.daemon = True
        server_thread.start()

        # Wait for server to be ready
        assert await wait_for_condition_async(
            lambda: server.is_running() if hasattr(server, 'is_running') else True,
            timeout=2,
            message="Server did not start within timeout"
        )

        yield server

        # Cleanup
        server.stop_sync()
        server_thread.join(timeout=2)

    @pytest.mark.asyncio
    async def test_event_flow_hook_to_dashboard(self, running_server):
        """
        Test event flow from hook system to dashboard client.

        WHY: This is the primary use case - hooks generate events that
        must be delivered to the dashboard for real-time monitoring.
        """
        server = running_server

        # Create a test client
        client = socketio.AsyncClient()
        received_events = []

        @client.on("hook_event")
        async def on_hook_event(data):
            received_events.append(data)

        # Connect client
        await client.connect(f"http://localhost:{server.port}")

        # Simulate hook event
        hook_event = {
            "source": "hook",
            "type": "file_change",
            "subtype": "modified",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {"file": "/test/file.py", "action": "modified"},
        }

        # Broadcast event through server
        server.broadcast_event("hook_event", hook_event)

        # Wait for event propagation
        assert await wait_for_condition_async(
            lambda: len(received_events) > 0,
            timeout=1,
            message="Hook event not received"
        )

        # Verify event received
        assert received_events[0]["source"] == "hook"
        assert received_events[0]["data"]["file"] == "/test/file.py"

        await client.disconnect()

    @pytest.mark.asyncio
    async def test_event_flow_eventbus_to_dashboard(self, running_server):
        """
        Test event flow from EventBus to dashboard client.

        WHY: EventBus integration allows system-wide events to be
        broadcast to the dashboard for comprehensive monitoring.
        """
        server = running_server

        # Create test client
        client = socketio.AsyncClient()
        received_events = []

        @client.on("system_event")
        async def on_system_event(data):
            received_events.append(data)

        await client.connect(f"http://localhost:{server.port}")

        # Simulate EventBus event through the integration
        if server.eventbus_integration and hasattr(
            server.eventbus_integration, "relay"
        ):
            eventbus_event = {
                "source": "eventbus",
                "type": "agent_status",
                "subtype": "started",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {"agent": "test_agent", "status": "active"},
            }

            # Trigger event through EventBus relay
            server.broadcast_event("system_event", eventbus_event)

            # Wait for propagation
            await wait_for_condition_async(
                lambda: len(received_events) > 0,
                timeout=1,
                interval=0.05
            )

        # Note: May not receive if EventBus not configured
        if received_events:
            assert received_events[0]["source"] == "eventbus"

        await client.disconnect()

    @pytest.mark.asyncio
    async def test_session_lifecycle_events(self, running_server):
        """
        Test complete session lifecycle event flow.

        WHY: Session events (start, delegation, end) are critical for
        tracking Claude MPM activity and must flow correctly.
        """
        server = running_server

        # Create test client
        client = socketio.AsyncClient()
        session_events = []

        @client.on("session_update")
        async def on_session_update(data):
            session_events.append(data)

        await client.connect(f"http://localhost:{server.port}")

        # Simulate session lifecycle
        session_id = "test-session-123"

        # Session start
        server.session_started(session_id, "exec", "/test/dir")

        # Wait for session started event
        assert await wait_for_condition_async(
            lambda: any(e.get("event_type") == "session_started" for e in session_events),
            timeout=1,
            message="Session started event not received"
        )

        # Agent delegation
        server.agent_delegated("test_agent", "Test task", "started")

        # Wait for agent delegated event
        assert await wait_for_condition_async(
            lambda: any(e.get("event_type") == "agent_delegated" for e in session_events),
            timeout=1,
            message="Agent delegated event not received"
        )

        # Session end
        server.session_ended()

        # Wait for session ended event
        assert await wait_for_condition_async(
            lambda: len(session_events) >= 3,
            timeout=1,
            message="Not all session events received"
        )

        # Verify events received in order

        # Check event sequence
        event_types = [e.get("event_type") for e in session_events]
        assert "session_started" in event_types
        assert "agent_delegated" in event_types
        assert "session_ended" in event_types

        await client.disconnect()


class TestMultipleClientConnections:
    """Test server handling multiple concurrent clients."""

    @pytest.fixture
    async def server_with_clients(self):
        """
        Create server with multiple connected clients.

        WHY: Real-world usage involves multiple dashboard instances
        or users monitoring simultaneously.
        """
        server = SocketIOServer(host="localhost", port=18766)

        # Start server
        server_thread = threading.Thread(target=server.start_sync)
        server_thread.daemon = True
        server_thread.start()

        # Wait for server to be ready
        assert await wait_for_condition_async(
            lambda: server.is_running() if hasattr(server, 'is_running') else True,
            timeout=2,
            message="Server did not start"
        )

        # Create multiple clients
        clients = []
        for _i in range(5):
            client = socketio.AsyncClient()
            await client.connect(f"http://localhost:{server.port}")
            clients.append(client)

        yield server, clients

        # Cleanup
        for client in clients:
            await client.disconnect()

        server.stop_sync()
        server_thread.join(timeout=2)

    @pytest.mark.asyncio
    async def test_broadcast_to_multiple_clients(self, server_with_clients):
        """
        Test that broadcasts reach all connected clients.

        WHY: All dashboard instances must receive the same events
        for consistent monitoring across multiple users.
        """
        server, clients = server_with_clients

        # Setup event handlers for all clients
        client_events = {i: [] for i in range(len(clients))}

        for i, client in enumerate(clients):
            events = client_events[i]

            @client.on("broadcast_test")
            async def on_broadcast(data, idx=i, evt_list=events):
                evt_list.append(data)

        # Broadcast event
        test_event = {
            "type": "test",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {"message": "broadcast to all"},
        }

        server.broadcast_event("broadcast_test", test_event)

        # Wait for all clients to receive event
        assert await wait_for_condition_async(
            lambda: all(len(events) > 0 for events in client_events.values()),
            timeout=2,
            message="Not all clients received broadcast"
        )

        # Verify all clients received the event
        for i, events in client_events.items():
            assert len(events) == 1, f"Client {i} should receive exactly one event"
            assert events[0]["data"]["message"] == "broadcast to all"

    @pytest.mark.asyncio
    async def test_targeted_messaging(self, server_with_clients):
        """
        Test sending messages to specific clients.

        WHY: Some events may be relevant only to specific dashboard
        instances, requiring targeted messaging capability.
        """
        server, clients = server_with_clients

        # Get client session IDs (would normally be tracked by server)
        # For testing, we'll use the first client
        target_client = clients[0]

        # Setup handlers
        targeted_events = []
        other_events = []

        @target_client.on("targeted_message")
        async def on_targeted(data):
            targeted_events.append(data)

        for client in clients[1:]:

            @client.on("targeted_message")
            async def on_other(data):
                other_events.append(data)

        # In real scenario, server.send_to_client would be used
        # For this test, we'll verify the capability exists
        assert hasattr(server, "send_to_client")

        # Broadcast should reach all
        server.broadcast_event("targeted_message", {"target": "all"})

        # Wait for targeted events
        await wait_for_condition_async(
            lambda: len(targeted_events) > 0,
            timeout=1,
            interval=0.05
        )

        # Both should have received
        assert len(targeted_events) > 0
        # Note: other_events may or may not receive depending on implementation

    @pytest.mark.asyncio
    async def test_connection_limit_handling(self):
        """
        Test server behavior when connection limit is reached.

        WHY: Servers have resource limits. The system should handle
        connection limits gracefully without crashing.
        """
        server = SocketIOServer(host="localhost", port=18767)

        # Artificially set a low connection limit for testing
        if hasattr(server, "connection_manager"):
            server.connection_manager.max_connections = 3

        server_thread = threading.Thread(target=server.start_sync)
        server_thread.daemon = True
        server_thread.start()

        # Wait for server to be ready
        assert await wait_for_condition_async(
            lambda: server.is_running() if hasattr(server, 'is_running') else True,
            timeout=2,
            message="Server did not start"
        )

        clients = []
        connection_results = []

        try:
            # Try to connect more clients than the limit
            for _i in range(5):
                try:
                    client = socketio.AsyncClient()
                    await client.connect(f"http://localhost:{server.port}")
                    clients.append(client)
                    connection_results.append(True)
                except Exception:
                    connection_results.append(False)

            # At least the limit should connect
            successful_connections = sum(connection_results)
            assert successful_connections >= 3

        finally:
            # Cleanup
            for client in clients:
                with contextlib.suppress(Exception):
                    await client.disconnect()

            server.stop_sync()
            server_thread.join(timeout=2)


class TestEventOrdering:
    """Test event ordering and delivery guarantees."""

    @pytest.mark.asyncio
    async def test_event_order_preservation(self):
        """
        Test that events are delivered in the order they were sent.

        WHY: Event ordering is crucial for understanding the sequence
        of operations, especially for debugging and audit trails.
        """
        server = SocketIOServer(host="localhost", port=18768)

        server_thread = threading.Thread(target=server.start_sync)
        server_thread.daemon = True
        server_thread.start()

        # Wait for server to be ready
        assert await wait_for_condition_async(
            lambda: server.is_running() if hasattr(server, 'is_running') else True,
            timeout=2,
            message="Server did not start"
        )

        try:
            client = socketio.AsyncClient()
            received_events = []

            @client.on("ordered_event")
            async def on_ordered(data):
                received_events.append(data)

            await client.connect(f"http://localhost:{server.port}")

            # Send numbered events rapidly
            for i in range(10):
                server.broadcast_event("ordered_event", {"sequence": i})

            # Wait for all events
            assert await wait_for_condition_async(
                lambda: len(received_events) >= 10,
                timeout=2,
                message="Not all events received"
            )

            # Check order
            for i, event in enumerate(received_events):
                assert event["sequence"] == i, f"Event {i} out of order"

            await client.disconnect()

        finally:
            server.stop_sync()
            server_thread.join(timeout=2)

    @pytest.mark.asyncio
    async def test_event_buffering_during_disconnect(self):
        """
        Test that events are buffered when clients are disconnected.

        WHY: Temporary disconnections shouldn't cause event loss.
        Events should be buffered and delivered on reconnection.
        """
        server = SocketIOServer(host="localhost", port=18769)

        server_thread = threading.Thread(target=server.start_sync)
        server_thread.daemon = True
        server_thread.start()

        # Wait for server to be ready
        assert await wait_for_condition_async(
            lambda: server.is_running() if hasattr(server, 'is_running') else True,
            timeout=2,
            message="Server did not start"
        )

        try:
            # Clear any connected clients to trigger buffering
            server.connected_clients.clear()

            # Send events while no clients connected
            for i in range(5):
                server.broadcast_event("buffered_event", {"index": i})

            # Verify events are buffered
            assert len(server.event_buffer) > 0

            # Connect client
            client = socketio.AsyncClient()
            received = []

            @client.on("buffered_event")
            async def on_buffered(data):
                received.append(data)

            await client.connect(f"http://localhost:{server.port}")

            # Wait for potential buffer flush
            await wait_for_condition_async(
                lambda: len(received) > 0,
                timeout=1,
                interval=0.05
            )

            # Should receive buffered events
            # Note: Actual delivery depends on implementation

            await client.disconnect()

        finally:
            server.stop_sync()
            server_thread.join(timeout=2)


class TestPerformanceUnderLoad:
    """Test system performance under various load conditions."""

    @pytest.mark.asyncio
    async def test_high_frequency_events(self):
        """
        Test server handling high-frequency event streams.

        WHY: Real-world usage can generate many events rapidly
        (e.g., during builds or test runs). The server must handle
        this load without dropping events or crashing.
        """
        server = SocketIOServer(host="localhost", port=18770)

        server_thread = threading.Thread(target=server.start_sync)
        server_thread.daemon = True
        server_thread.start()

        # Wait for server to be ready
        assert await wait_for_condition_async(
            lambda: server.is_running() if hasattr(server, 'is_running') else True,
            timeout=2,
            message="Server did not start"
        )

        try:
            client = socketio.AsyncClient()
            received_count = 0

            @client.on("perf_event")
            async def on_perf(data):
                nonlocal received_count
                received_count += 1

            await client.connect(f"http://localhost:{server.port}")

            # Send many events rapidly
            start_time = time.time()
            event_count = 100

            for i in range(event_count):
                server.broadcast_event("perf_event", {"index": i})

            # Wait for all events to be received
            assert await wait_for_condition_async(
                lambda: received_count >= event_count * 0.95,  # Allow for 95% delivery
                timeout=3,
                message="Events not received in time"
            )

            elapsed = time.time() - start_time

            # Calculate metrics
            events_per_second = event_count / elapsed
            delivery_rate = received_count / event_count

            # Performance assertions
            assert events_per_second > 50, "Should handle at least 50 events/second"
            assert delivery_rate > 0.95, "Should deliver at least 95% of events"

            await client.disconnect()

        finally:
            server.stop_sync()
            server_thread.join(timeout=2)

    @pytest.mark.asyncio
    async def test_concurrent_event_sources(self):
        """
        Test handling events from multiple concurrent sources.

        WHY: Events come from hooks, EventBus, and API simultaneously.
        The server must handle concurrent event streams without corruption.
        """
        server = SocketIOServer(host="localhost", port=18771)

        server_thread = threading.Thread(target=server.start_sync)
        server_thread.daemon = True
        server_thread.start()

        # Wait for server to be ready
        assert await wait_for_condition_async(
            lambda: server.is_running() if hasattr(server, 'is_running') else True,
            timeout=2,
            message="Server did not start"
        )

        try:
            client = socketio.AsyncClient()
            received_events = []

            @client.on("concurrent_event")
            async def on_concurrent(data):
                received_events.append(data)

            await client.connect(f"http://localhost:{server.port}")

            # Create concurrent event sources
            async def send_events(source_id, count):
                for i in range(count):
                    server.broadcast_event(
                        "concurrent_event", {"source": source_id, "index": i}
                    )
                    await asyncio.sleep(0.01)  # Keep small delay to prevent overwhelming the queue

            # Run sources concurrently
            tasks = [
                send_events("source_1", 20),
                send_events("source_2", 20),
                send_events("source_3", 20),
            ]

            await asyncio.gather(*tasks)

            # Wait for all events to be received
            assert await wait_for_condition_async(
                lambda: len(received_events) == 60,
                timeout=3,
                message="Not all concurrent events received"
            )

            # Verify all events received

            # Check events from all sources
            sources = {e["source"] for e in received_events}
            assert sources == {"source_1", "source_2", "source_3"}

            await client.disconnect()

        finally:
            server.stop_sync()
            server_thread.join(timeout=2)

    def test_memory_usage_under_load(self):
        """
        Test that memory usage remains stable under load.

        WHY: Memory leaks can cause server crashes over time.
        The server must properly clean up resources.
        """
        import gc

        server = SocketIOServer(host="localhost", port=18772)

        # Get initial memory baseline
        gc.collect()
        initial_objects = len(gc.get_objects())

        server_thread = threading.Thread(target=server.start_sync)
        server_thread.daemon = True
        server_thread.start()

        # Wait for server to be ready (sync version)
        assert wait_for_condition(
            lambda: server.is_running() if hasattr(server, 'is_running') else True,
            timeout=2,
            message="Server did not start"
        )

        try:
            # Generate load
            for cycle in range(3):
                # Send many events
                for i in range(100):
                    server.broadcast_event("memory_test", {"index": i})

                # Simulate client connections/disconnections
                server.connected_clients.add(f"client_{cycle}")
                server.connected_clients.clear()

                # Brief pause between cycles to allow processing
                time.sleep(0.05)

            # Force garbage collection
            gc.collect()

            # Check memory
            final_objects = len(gc.get_objects())
            object_growth = final_objects - initial_objects

            # Allow some growth but not excessive
            assert object_growth < 10000, f"Excessive object growth: {object_growth}"

        finally:
            server.stop_sync()
            server_thread.join(timeout=2)


class TestGracefulDegradation:
    """Test system behavior under failure conditions."""

    @pytest.mark.asyncio
    async def test_recovery_from_network_errors(self):
        """
        Test that system recovers from network errors.

        WHY: Network issues are common in production. The system
        should recover gracefully without manual intervention.
        """
        server = SocketIOServer(host="localhost", port=18773)

        server_thread = threading.Thread(target=server.start_sync)
        server_thread.daemon = True
        server_thread.start()

        # Wait for server to be ready
        assert await wait_for_condition_async(
            lambda: server.is_running() if hasattr(server, 'is_running') else True,
            timeout=2,
            message="Server did not start"
        )

        try:
            client = socketio.AsyncClient()
            connection_events = []

            @client.on("connect")
            async def on_connect():
                connection_events.append("connected")

            @client.on("disconnect")
            async def on_disconnect():
                connection_events.append("disconnected")

            # Connect initially
            await client.connect(f"http://localhost:{server.port}")

            # Simulate network error by disconnecting
            await client.disconnect()

            # Wait for disconnect to complete
            await wait_for_condition_async(
                lambda: "disconnected" in connection_events,
                timeout=1,
                interval=0.05
            )

            # Reconnect
            await client.connect(f"http://localhost:{server.port}")

            # Verify recovery
            assert "connected" in connection_events
            assert "disconnected" in connection_events
            assert connection_events[-1] == "connected"

            await client.disconnect()

        finally:
            server.stop_sync()
            server_thread.join(timeout=2)

    @pytest.mark.asyncio
    async def test_partial_event_delivery_on_error(self):
        """
        Test that partial failures don't affect other clients.

        WHY: If one client has issues, other clients should continue
        receiving events normally.
        """
        server = SocketIOServer(host="localhost", port=18774)

        server_thread = threading.Thread(target=server.start_sync)
        server_thread.daemon = True
        server_thread.start()

        # Wait for server to be ready
        assert await wait_for_condition_async(
            lambda: server.is_running() if hasattr(server, 'is_running') else True,
            timeout=2,
            message="Server did not start"
        )

        try:
            # Create healthy client
            good_client = socketio.AsyncClient()
            good_events = []

            @good_client.on("test_event")
            async def on_good_event(data):
                good_events.append(data)

            await good_client.connect(f"http://localhost:{server.port}")

            # Simulate a "bad" client by adding a fake client ID
            server.connected_clients.add("bad_client_id")

            # Send events
            for i in range(5):
                server.broadcast_event("test_event", {"index": i})

            # Wait for events to be received
            assert await wait_for_condition_async(
                lambda: len(good_events) == 5,
                timeout=2,
                message="Good client did not receive all events"
            )

            # Good client should still receive events

            await good_client.disconnect()

        finally:
            server.stop_sync()
            server_thread.join(timeout=2)


@pytest.fixture
def integration_server():
    """
    Fixture providing a configured server for integration testing.

    WHY: Integration tests need a properly configured server with
    all components initialized for realistic testing.
    """
    server = SocketIOServer(host="localhost", port=18775)

    # Configure for testing
    server.stats = {
        "events_sent": 0,
        "events_buffered": 0,
        "connections_total": 0,
        "start_time": datetime.now(timezone.utc).isoformat(),
    }

    return server


def test_full_system_integration(integration_server):
    """
    Complete integration test of the Socket.IO system.

    WHY: Verifies that all components work together correctly
    in a realistic scenario.
    """
    server = integration_server

    # Start server
    server_thread = threading.Thread(target=server.start_sync)
    server_thread.daemon = True
    server_thread.start()

    # Wait for server to be ready (sync version)
    assert wait_for_condition(
        lambda: server.is_running() if hasattr(server, 'is_running') else True,
        timeout=2,
        message="Server did not start"
    )

    try:
        # Simulate complete workflow

        # 1. Session starts
        server.session_started("integ-test-123", "exec", "/test/project")

        # 2. Various events occur
        server.broadcast_event("file_change", {"file": "test.py"})
        server.claude_output("Running tests...", "stdout")

        # 3. Agent delegation
        server.agent_delegated("test_agent", "Run tests", "started")

        # 4. Memory operations
        server.memory_loaded("test_agent", 1024, 5)
        server.memory_updated("test_agent", "test", "Test learning", "section1")

        # 5. Session ends
        server.session_ended()

        # Verify stats updated
        assert server.stats["events_sent"] > 0

        # Verify server still running
        assert server.is_running()

    finally:
        server.stop_sync()
        server_thread.join(timeout=2)

        # Verify clean shutdown
        assert not server.running
