#!/usr/bin/env python3
"""Monitor real-time events from the dashboard."""

import asyncio
import json
import signal
import sys
from datetime import datetime

try:
    import socketio
except ImportError:
    print("Please install python-socketio: pip install python-socketio")
    sys.exit(1)


class EventMonitor:
    def __init__(self):
        self.sio = socketio.AsyncClient()
        self.running = True
        self.event_count = 0

    async def connect(self):
        """Connect and monitor events."""

        @self.sio.event
        async def connect():
            print(f"✅ Connected to dashboard at {datetime.now().isoformat()}")
            print("Monitoring for events...")
            print("-" * 60)

        @self.sio.event
        async def disconnect():
            print(f"\n❌ Disconnected at {datetime.now().isoformat()}")

        @self.sio.on("*")
        async def catch_all(event, data=None):
            """Catch all events."""
            self.event_count += 1
            print(f"\n[{datetime.now().isoformat()}] Event #{self.event_count}")
            print(f"  Type: {event}")
            if data:
                print(f"  Data: {json.dumps(data, indent=2)[:500]}")
            print("-" * 60)

        @self.sio.on("claude_event")
        async def on_claude_event(data):
            """Handle claude_event specifically."""
            self.event_count += 1
            print(
                f"\n🎯 CLAUDE EVENT #{self.event_count} at {datetime.now().isoformat()}"
            )
            print(f"  Type: {data.get('type', 'unknown')}")
            print(f"  Subtype: {data.get('subtype', 'unknown')}")
            print(f"  Source: {data.get('source', 'unknown')}")
            if "data" in data:
                print(f"  Data: {json.dumps(data['data'], indent=2)[:300]}")
            print("-" * 60)

        # Connect
        try:
            print("Connecting to http://localhost:8765...")
            await self.sio.connect("http://localhost:8765")

            # Send a test event after connecting
            await asyncio.sleep(1)
            print("\n📤 Sending test event via HTTP POST...")

            import aiohttp

            test_event = {
                "hook_event_name": "TestMonitorEvent",
                "timestamp": datetime.now().isoformat(),
                "session_id": "monitor-test",
                "hook_input_data": {
                    "message": "Test from monitor",
                    "monitor_pid": sys.argv[0],
                },
            }

            async with aiohttp.ClientSession() as session, session.post(
                "http://localhost:8765/api/events", json=test_event
            ) as response:
                if response.status == 204:
                    print("✅ Test event sent successfully")
                else:
                    print(f"❌ Test event failed: {response.status}")

            # Keep monitoring
            while self.running:
                await asyncio.sleep(1)

        except Exception as e:
            print(f"❌ Connection error: {e}")
        finally:
            if self.sio.connected:
                await self.sio.disconnect()

    def stop(self):
        self.running = False


async def main():
    monitor = EventMonitor()

    # Handle Ctrl+C
    def signal_handler(sig, frame):
        print("\n\nStopping monitor...")
        monitor.stop()

    signal.signal(signal.SIGINT, signal_handler)

    await monitor.connect()

    print(f"\nTotal events received: {monitor.event_count}")


if __name__ == "__main__":
    print("=" * 60)
    print("Real-time Event Monitor")
    print("=" * 60)
    print("This monitor will:")
    print("1. Connect to the dashboard via SocketIO")
    print("2. Send a test event via HTTP")
    print("3. Display any events received")
    print("\nPress Ctrl+C to stop\n")

    asyncio.run(main())
