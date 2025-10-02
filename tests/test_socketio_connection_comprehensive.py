import pytest

#!/usr/bin/env python3
"""
Comprehensive Socket.IO connection test with detailed diagnostics.
"""

import asyncio
import contextlib
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import aiohttp
import socketio

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


class SocketIOConnectionTester:
    def __init__(self, server_url="http://localhost:8765"):
        self.server_url = server_url
        self.sio = socketio.AsyncClient(
            logger=True,
            engineio_logger=True,
            reconnection=True,
            reconnection_attempts=3,
            reconnection_delay=1,
            reconnection_delay_max=5,
        )
        self.connected = False
        self.events_received = []
        self.connection_start = None
        self.setup_handlers()

    def setup_handlers(self):
        """Set up event handlers."""

        @self.sio.event
        async def connect():
            self.connected = True
            connection_time = (
                time.time() - self.connection_start if self.connection_start else 0
            )
            print(f"✅ Connected to Socket.IO server in {connection_time:.2f}s")
            print(f"   Transport: {self.sio.transport()}")
            print(f"   Session ID: {self.sio.sid}")

        @self.sio.event
        async def connect_error(data):
            print(f"❌ Connection error: {data}")

        @self.sio.event
        async def disconnect():
            self.connected = False
            print("🔌 Disconnected from Socket.IO server")

        @self.sio.event
        async def error(data):
            print(f"❌ Socket.IO error: {data}")

        # Handle custom events
        @self.sio.on("*")
        async def catch_all(event, *args):
            timestamp = datetime.now(timezone.utc).isoformat()
            self.events_received.append(
                {"timestamp": timestamp, "event": event, "data": args}
            )
            print(f"📨 Event received: {event} - {args}")

    @pytest.mark.asyncio
    async def test_connection():
        """Test basic connection."""
        print(f"\n🔍 Testing connection to {self.server_url}")
        self.connection_start = time.time()

        try:
            await self.sio.connect(self.server_url, namespaces=["/"])
            await asyncio.sleep(1)  # Give connection time to stabilize

            if self.connected:
                print("✅ Connection test PASSED")
                return True
            print("❌ Connection test FAILED - Not connected")
            return False

        except Exception as e:
            print(f"❌ Connection test FAILED with error: {e}")
            return False

    @pytest.mark.asyncio
    async def test_emit_event():
        """Test emitting an event."""
        if not self.connected:
            print("⚠️  Cannot test emit - not connected")
            return False

        print("\n🔍 Testing event emission")
        test_data = {
            "test": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "Test event from connection tester",
        }

        try:
            await self.sio.emit("test_event", test_data)
            print(f"✅ Successfully emitted test_event with data: {test_data}")
            return True
        except Exception as e:
            print(f"❌ Failed to emit event: {e}")
            return False

    @pytest.mark.asyncio
    async def test_request_response():
        """Test request/response pattern."""
        if not self.connected:
            print("⚠️  Cannot test request/response - not connected")
            return False

        print("\n🔍 Testing request/response pattern")

        try:
            # Emit a request and wait for response
            response = await self.sio.call("echo", {"message": "Hello, server!"})
            print(f"✅ Received response: {response}")
            return True
        except asyncio.TimeoutError:
            print("❌ Request timed out - server may not support 'echo' event")
            return False
        except Exception as e:
            print(f"❌ Request/response test failed: {e}")
            return False

    @pytest.mark.asyncio
    async def test_namespace_connection():
        """Test connecting to different namespaces."""
        print("\n🔍 Testing namespace connections")
        namespaces = ["/hooks", "/dashboard", "/api"]
        results = {}

        for namespace in namespaces:
            print(f"\n  Testing namespace: {namespace}")
            ns_sio = socketio.AsyncClient()

            try:
                await ns_sio.connect(self.server_url, namespaces=[namespace])
                await asyncio.sleep(0.5)

                if ns_sio.connected:
                    print(f"  ✅ Connected to {namespace}")
                    results[namespace] = True
                else:
                    print(f"  ❌ Failed to connect to {namespace}")
                    results[namespace] = False

                await ns_sio.disconnect()

            except Exception as e:
                print(f"  ❌ Error connecting to {namespace}: {e}")
                results[namespace] = False

        return results

    async def check_server_health(self):
        """Check if server is healthy via HTTP."""
        print("\n🔍 Checking server health")

        async with aiohttp.ClientSession() as session:
            # Test root endpoint
            try:
                async with session.get(self.server_url) as resp:
                    print(f"  Root endpoint status: {resp.status}")
                    if resp.status == 200:
                        content = await resp.text()
                        print(f"  Response preview: {content[:100]}...")
            except Exception as e:
                print(f"  ❌ Failed to reach root endpoint: {e}")

            # Test dashboard endpoint
            try:
                async with session.get(f"{self.server_url}/dashboard") as resp:
                    print(f"  Dashboard endpoint status: {resp.status}")
            except Exception as e:
                print(f"  ❌ Failed to reach dashboard: {e}")

            # Test Socket.IO endpoint
            try:
                async with session.get(f"{self.server_url}/socket.io/") as resp:
                    print(f"  Socket.IO endpoint status: {resp.status}")
            except Exception as e:
                print(f"  ❌ Failed to reach Socket.IO endpoint: {e}")

    async def run_all_tests(self):
        """Run all connection tests."""
        print("🚀 Starting comprehensive Socket.IO connection tests")
        print("=" * 60)

        # Check server health first
        await self.check_server_health()

        # Test basic connection
        connection_ok = await self.test_connection()

        if connection_ok:
            # Run additional tests
            await self.test_emit_event()
            await self.test_request_response()

        # Test namespaces (separate connections)
        namespace_results = await self.test_namespace_connection()

        # Print summary
        print("\n" + "=" * 60)
        print("📊 Test Summary:")
        print(f"  Basic connection: {'✅ PASSED' if connection_ok else '❌ FAILED'}")
        print(f"  Events received: {len(self.events_received)}")

        if namespace_results:
            print("\n  Namespace connections:")
            for ns, result in namespace_results.items():
                print(f"    {ns}: {'✅ PASSED' if result else '❌ FAILED'}")

        # Disconnect
        if self.connected:
            await self.sio.disconnect()

        return connection_ok


async def main():
    """Main test runner."""
    import argparse

    parser = argparse.ArgumentParser(description="Test Socket.IO connection")
    parser.add_argument(
        "--url",
        default="http://localhost:8765",
        help="Socket.IO server URL (default: http://localhost:8765)",
    )
    parser.add_argument(
        "--start-server",
        action="store_true",
        help="Start the Socket.IO server before testing",
    )
    args = parser.parse_args()

    if args.start_server:
        # Start server in background
        print("🚀 Starting Socket.IO server...")
        from claude_mpm.services.socketio_server import SocketIOServer

        server = SocketIOServer(host="localhost", port=8765)

        # Start server in background task (stored to prevent GC)
        server_task = asyncio.create_task(asyncio.to_thread(server.start))
        await asyncio.sleep(2)  # Give server time to start

        print("✅ Server started, running tests...")

    # Run tests
    tester = SocketIOConnectionTester(args.url)
    success = await tester.run_all_tests()

    if args.start_server:
        print("\n🛑 Stopping server...")
        server.stop()
        # Cancel server task to clean up properly
        if "server_task" in locals():
            server_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await server_task

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
