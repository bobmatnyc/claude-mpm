#!/usr/bin/env python3
"""
Test script to verify that the dashboard receives events correctly.

This script uses a Socket.IO client to connect to the server and verify
that events sent via HTTP POST are properly received by connected clients.
"""

import asyncio
import sys
import time
from pathlib import Path

import requests

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

try:
    import socketio

    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False
    print("❌ python-socketio not available - cannot run client test")
    sys.exit(1)


class TestClient:
    """Test client to verify event reception."""

    def __init__(self, server_url="http://localhost:8765"):
        self.server_url = server_url
        self.received_events = []
        self.sio = None
        self.connected_namespaces = []

    async def connect_and_test(self):
        """Connect to server and test event reception."""

        print(f"🔌 Connecting to Socket.IO server at {self.server_url}")

        # Create Socket.IO client
        self.sio = socketio.AsyncClient(
            reconnection=True,
            reconnection_attempts=3,
            reconnection_delay=1,
            logger=False,
        )

        # Setup event handlers
        await self._setup_event_handlers()

        # Connect to all namespaces (same as dashboard)
        namespaces = [
            "/system",
            "/session",
            "/claude",
            "/agent",
            "/hook",
            "/todo",
            "/memory",
            "/log",
        ]

        for namespace in namespaces:
            try:
                # Create a new client for each namespace (python-socketio limitation)
                namespace_client = socketio.AsyncClient(logger=False)

                # Set up event handlers for this namespace
                await self._setup_namespace_handlers(namespace_client, namespace)

                # Connect to the namespace
                await namespace_client.connect(self.server_url + namespace)
                self.connected_namespaces.append((namespace, namespace_client))
                print(f"✅ Connected to {namespace}")

            except Exception as e:
                print(f"❌ Failed to connect to {namespace}: {e}")

        # Wait a moment for connections to stabilize
        await asyncio.sleep(1)

        print(f"🎯 Connected to {len(self.connected_namespaces)} namespaces")

        # Send test events via HTTP
        await self._send_test_events()

        # Wait for events to be received
        print("⏳ Waiting for events to be received...")
        await asyncio.sleep(3)

        # Report results
        self._report_results()

        # Cleanup
        await self._cleanup()

    async def _setup_event_handlers(self):
        """Setup main event handlers."""

        @self.sio.event
        async def connect():
            print("🟢 Main client connected")

        @self.sio.event
        async def disconnect():
            print("🔴 Main client disconnected")

    async def _setup_namespace_handlers(self, client, namespace):
        """Setup event handlers for a specific namespace."""

        @client.event
        async def connect():
            print(f"🟢 Connected to {namespace}")

        @client.event
        async def disconnect():
            print(f"🔴 Disconnected from {namespace}")

        # Listen for all possible events
        event_types = [
            "start",
            "end",
            "status_changed",
            "output",
            "task_delegated",
            "user_prompt",
            "pre_tool",
            "post_tool",
            "updated",
            "loaded",
            "created",
            "injected",
            "message",
            "status",
        ]

        for event_type in event_types:
            # Create closure to capture event_type and namespace
            def make_handler(evt, ns):
                async def handler(data):
                    event_info = {
                        "namespace": ns,
                        "event": evt,
                        "data": data,
                        "timestamp": time.time(),
                    }
                    self.received_events.append(event_info)
                    print(f"📨 Received {ns}/{evt}: {str(data)[:100]}...")

                return handler

            client.on(event_type, make_handler(event_type, namespace))

    async def _send_test_events(self):
        """Send test events via HTTP POST."""

        test_events = [
            {
                "namespace": "/hook",
                "event": "pre_tool",
                "data": {"tool_name": "test_broadcast_fix", "session_id": "test_123"},
            },
            {
                "namespace": "/session",
                "event": "start",
                "data": {"session_id": "test_123", "launch_method": "test"},
            },
            {
                "namespace": "/memory",
                "event": "updated",
                "data": {"agent_id": "test_agent", "learning_type": "success"},
            },
        ]

        print("📤 Sending test events via HTTP...")

        for event in test_events:
            try:
                response = requests.post(
                    f"{self.server_url}/emit", json=event, timeout=2.0
                )

                if response.status_code == 200:
                    print(f"✅ Sent {event['namespace']}/{event['event']}")
                else:
                    print(
                        f"❌ Failed to send {event['namespace']}/{event['event']}: {response.status_code}"
                    )

            except Exception as e:
                print(f"❌ Error sending event: {e}")

            # Small delay between events
            await asyncio.sleep(0.5)

    def _report_results(self):
        """Report test results."""

        print("\n📊 TEST RESULTS:")
        print(f"🔌 Connected namespaces: {len(self.connected_namespaces)}")
        print(f"📨 Events received: {len(self.received_events)}")

        if self.received_events:
            print("\n✅ RECEIVED EVENTS:")
            for event in self.received_events:
                print(f"   - {event['namespace']}/{event['event']}")
        else:
            print("\n❌ NO EVENTS RECEIVED - Broadcasting may still be broken!")

        # Expected vs received
        expected_events = 3  # We sent 3 test events
        if len(self.received_events) >= expected_events:
            print(
                f"\n🎉 SUCCESS: Received {len(self.received_events)}/{expected_events} events"
            )
            print("✅ Socket.IO broadcasting is working correctly!")
        else:
            print(
                f"\n⚠️ PARTIAL SUCCESS: Received {len(self.received_events)}/{expected_events} events"
            )
            print("🔧 Some events may not be reaching clients properly")

    async def _cleanup(self):
        """Cleanup connections."""

        print("\n🧹 Cleaning up connections...")

        for namespace, client in self.connected_namespaces:
            try:
                await client.disconnect()
            except Exception as e:
                print(f"Error disconnecting from {namespace}: {e}")

        if self.sio:
            try:
                await self.sio.disconnect()
            except Exception as e:
                print(f"Error disconnecting main client: {e}")


async def main():
    """Main test function."""

    print("🧪 Testing Socket.IO event reception (dashboard simulation)")
    print("=" * 60)

    # Check if server is running
    try:
        response = requests.get("http://localhost:8765/health", timeout=2)
        if response.status_code == 200:
            print("✅ Socket.IO server is running")
        else:
            print("❌ Socket.IO server returned error")
            return
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Socket.IO server on port 8765")
        print("💡 Make sure the server is running first")
        return

    # Run the test
    client = TestClient()
    await client.connect_and_test()

    print("\n✅ Test completed!")


if __name__ == "__main__":
    asyncio.run(main())
