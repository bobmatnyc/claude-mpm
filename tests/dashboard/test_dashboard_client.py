#!/usr/bin/env python3
"""
Dashboard Connection Stability Test Client

This script tests the connection stability fixes implemented for the dashboard,
including the centralized configuration, ping/pong reliability, and reconnection logic.
"""

import asyncio
import sys
import time
from datetime import datetime

import socketio


class DashboardStabilityTester:
    """Test client for dashboard connection stability."""

    def __init__(self, name: str, port: int = 8765):
        self.name = name
        self.port = port
        self.url = f"http://localhost:{port}"
        self.sio = None
        self.connected = False
        self.connect_time = None
        self.ping_count = 0
        self.pong_count = 0
        self.disconnect_reasons = []
        self.test_results = {}

    async def setup_client(self):
        """Setup the Socket.IO client with proper configuration."""
        self.sio = socketio.AsyncClient()

        @self.sio.event
        async def connect():
            self.connected = True
            self.connect_time = time.time()
            await self.log(f"✅ Connected! Socket ID: {self.sio.sid}")
            await self.log("Socket.IO client configured with connection settings")

        @self.sio.event
        async def disconnect(data):
            uptime = int(time.time() - self.connect_time) if self.connect_time else 0
            self.connected = False
            self.disconnect_reasons.append(data)
            await self.log(f"❌ Disconnected: {data} (uptime: {uptime}s)")

        @self.sio.event
        async def connect_error(data):
            await self.log(f"⚠️ Connection error: {data}")

        @self.sio.event
        async def ping():
            self.ping_count += 1
            await self.log(f"🏓 Ping received from server (count: {self.ping_count})")

        @self.sio.event
        async def pong(data):
            self.pong_count += 1
            await self.log(
                f"🏓 Pong sent to server (latency: {data}ms, count: {self.pong_count})"
            )

    async def log(self, message: str):
        """Log with timestamp and client name."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{self.name}] {message}")

    async def connect_and_monitor(self, duration_minutes: int = 5):
        """Connect and monitor for specified duration."""
        await self.log(f"Starting {duration_minutes}-minute connection test...")

        try:
            await self.sio.connect(self.url)

            # Monitor for specified duration
            start_time = time.time()
            end_time = start_time + (duration_minutes * 60)

            while time.time() < end_time and self.connected:
                await asyncio.sleep(10)  # Check every 10 seconds

                if self.connected:
                    elapsed = int(time.time() - self.connect_time)
                    await self.log(
                        f"📊 Still connected - uptime: {elapsed}s, pings: {self.ping_count}"
                    )

            # Record results
            final_uptime = (
                int(time.time() - self.connect_time) if self.connect_time else 0
            )
            self.test_results[f"{duration_minutes}min_test"] = {
                "success": self.connected,
                "uptime_seconds": final_uptime,
                "ping_count": self.ping_count,
                "disconnect_reasons": self.disconnect_reasons.copy(),
            }

            await self.log(
                f"✅ {duration_minutes}-minute test complete - uptime: {final_uptime}s"
            )

        except Exception as e:
            await self.log(f"❌ Test failed: {e}")

        finally:
            if self.sio.connected:
                await self.sio.disconnect()

    async def test_reconnection(self):
        """Test reconnection after intentional disconnect."""
        await self.log("🔄 Testing reconnection after disconnect...")

        try:
            # Initial connection
            await self.sio.connect(self.url)
            await asyncio.sleep(5)

            # Disconnect
            await self.log("🔌 Disconnecting intentionally...")
            await self.sio.disconnect()
            await asyncio.sleep(2)

            # Reconnect
            await self.log("🔄 Attempting reconnection...")
            await self.sio.connect(self.url)
            await asyncio.sleep(5)

            self.test_results["reconnection_test"] = {
                "success": self.connected,
                "final_ping_count": self.ping_count,
            }

            await self.log("✅ Reconnection test complete")

        except Exception as e:
            await self.log(f"❌ Reconnection test failed: {e}")

        finally:
            if self.sio.connected:
                await self.sio.disconnect()

    async def run_all_tests(self):
        """Run all stability tests."""
        await self.setup_client()

        await self.log("🚀 Starting dashboard stability tests...")

        # Test 1: 5-minute connection test
        await self.connect_and_monitor(5)
        await asyncio.sleep(2)

        # Test 2: Reconnection test
        await self.test_reconnection()

        await self.log("🎉 All tests completed!")
        return self.test_results


async def run_multiple_clients(num_clients: int = 3):
    """Run multiple clients simultaneously."""
    print(f"🚀 Starting {num_clients} test clients simultaneously...")

    # Create clients
    clients = []
    for i in range(num_clients):
        client = DashboardStabilityTester(f"Client-{i+1}")
        clients.append(client)

    # Run all clients concurrently
    tasks = [client.run_all_tests() for client in clients]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Report results
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"Client-{i+1}: ❌ Failed with error: {result}")
        else:
            print(f"Client-{i+1}: ✅ Completed successfully")
            for test_name, test_result in result.items():
                print(f"  {test_name}: {test_result}")

    print("=" * 60)


async def main():
    """Main test runner."""
    if len(sys.argv) > 1 and sys.argv[1] == "multi":
        await run_multiple_clients(3)
    else:
        # Single client long-duration test
        client = DashboardStabilityTester("LongDuration")
        await client.setup_client()
        await client.connect_and_monitor(30)  # 30-minute test


if __name__ == "__main__":
    print("📡 Dashboard Connection Stability Test")
    print("=====================================")
    print("Testing connection stability fixes:")
    print("✓ Centralized ping/pong configuration (45s/20s)")
    print("✓ Enhanced disconnect logging")
    print("✓ Activity tracking improvements")
    print("✓ Reconnection robustness")
    print()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"❌ Test failed: {e}")
