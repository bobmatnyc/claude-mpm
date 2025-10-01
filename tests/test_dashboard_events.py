#!/usr/bin/env python3
"""
Dashboard Event Generator for Testing
Generates various test events to verify dashboard functionality
"""

import asyncio
import json
import random
import time
from datetime import datetime, timezone

import socketio


class DashboardEventTester:
    def __init__(self, url="http://localhost:8765"):
        self.url = url
        self.sio = socketio.AsyncClient()
        self.connected = False

    async def connect(self):
        """Connect to the dashboard WebSocket"""
        try:
            await self.sio.connect(self.url)
            self.connected = True
            print(f"✅ Connected to dashboard at {self.url}")
            return True
        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            return False

    async def disconnect(self):
        """Disconnect from dashboard"""
        if self.connected:
            await self.sio.disconnect()
            self.connected = False
            print("🔌 Disconnected from dashboard")

    async def send_test_event(self, event_type="test_event", data=None):
        """Send a test event to the dashboard"""
        if not self.connected:
            print("❌ Not connected to dashboard")
            return False

        if data is None:
            data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "test_id": random.randint(1000, 9999),
                "message": f"Test event generated at {time.time()}",
            }

        try:
            await self.sio.emit(event_type, data)
            print(
                f"📤 Sent event: {event_type} with data: {json.dumps(data, indent=2)}"
            )
            return True
        except Exception as e:
            print(f"❌ Failed to send event: {e}")
            return False

    async def generate_agent_events(self, count=5):
        """Generate agent-related test events"""
        events = [
            ("agent_started", {"agent_name": "QA_Agent", "pid": 12345}),
            ("agent_stopped", {"agent_name": "PM_Agent", "pid": 12346}),
            ("agent_error", {"agent_name": "DEV_Agent", "error": "Connection timeout"}),
            (
                "agent_message",
                {"agent_name": "QA_Agent", "message": "Running tests..."},
            ),
            (
                "agent_complete",
                {"agent_name": "QA_Agent", "result": "All tests passed"},
            ),
        ]

        for i in range(count):
            event_type, data = events[i % len(events)]
            data["sequence"] = i + 1
            await self.send_test_event(event_type, data)
            await asyncio.sleep(0.5)  # Small delay between events

    async def generate_file_events(self, count=3):
        """Generate file operation test events"""
        events = [
            ("file_created", {"path": "/test/file1.py", "size": 1024}),
            ("file_modified", {"path": "/test/file2.js", "changes": 15}),
            ("file_deleted", {"path": "/test/old_file.txt"}),
        ]

        for i in range(count):
            event_type, data = events[i % len(events)]
            data["sequence"] = i + 1
            await self.send_test_event(event_type, data)
            await asyncio.sleep(0.3)

    async def generate_tool_events(self, count=4):
        """Generate tool usage test events"""
        events = [
            ("tool_start", {"tool": "grep", "args": ["test_pattern", "*.py"]}),
            ("tool_output", {"tool": "grep", "output": "Found 5 matches"}),
            ("tool_error", {"tool": "bash", "error": "Permission denied"}),
            ("tool_complete", {"tool": "grep", "duration": 0.25}),
        ]

        for i in range(count):
            event_type, data = events[i % len(events)]
            data["sequence"] = i + 1
            await self.send_test_event(event_type, data)
            await asyncio.sleep(0.4)

    async def load_test(self, events_per_second=10, duration=5):
        """Generate high-volume events for load testing"""
        print(
            f"🔥 Starting load test: {events_per_second} events/sec for {duration} seconds"
        )

        total_events = events_per_second * duration
        interval = 1.0 / events_per_second

        for i in range(total_events):
            event_data = {
                "load_test": True,
                "event_num": i + 1,
                "total_events": total_events,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "performance_data": {
                    "cpu_usage": random.uniform(10, 90),
                    "memory_mb": random.randint(100, 1000),
                    "response_time": random.uniform(0.1, 2.0),
                },
            }

            await self.send_test_event("performance_metric", event_data)

            if i % 10 == 0:
                print(f"📊 Sent {i + 1}/{total_events} events")

            await asyncio.sleep(interval)

        print(f"✅ Load test complete: {total_events} events sent")


async def main():
    """Main test function"""
    print("🚀 Starting Dashboard Event Testing")

    tester = DashboardEventTester()

    # Connect to dashboard
    if not await tester.connect():
        return

    try:
        # Test different event types
        print("\n📋 Generating agent events...")
        await tester.generate_agent_events(5)

        print("\n📁 Generating file events...")
        await tester.generate_file_events(3)

        print("\n🔧 Generating tool events...")
        await tester.generate_tool_events(4)

        # Small load test
        print("\n⚡ Running load test...")
        await tester.load_test(events_per_second=20, duration=3)

        print("\n✅ All test events generated successfully!")
        print("🌐 Check dashboard at http://localhost:8765/static/events.html")

    except Exception as e:
        print(f"❌ Error during testing: {e}")
    finally:
        await tester.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
