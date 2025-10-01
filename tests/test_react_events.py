#!/usr/bin/env python3
"""
Test script for React Events Dashboard
Sends test events to verify the React EventViewer integration works correctly.
"""

import asyncio
import json
import random
import time
from typing import Any, Dict, Optional

import socketio


class EventTester:
    def __init__(self, server_url: str = "http://localhost:8765"):
        self.server_url = server_url
        self.sio = socketio.AsyncClient()

    async def connect(self):
        """Connect to the SocketIO server"""
        try:
            await self.sio.connect(self.server_url)
            print(f"✅ Connected to server at {self.server_url}")
            return True
        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            return False

    async def disconnect(self):
        """Disconnect from the server"""
        await self.sio.disconnect()
        print("🔌 Disconnected from server")

    def create_test_event(
        self, event_type: str, subtype: Optional[str] = None, **kwargs
    ) -> Dict[str, Any]:
        """Create a test event with consistent structure"""
        event = {
            "type": event_type,
            "timestamp": int(time.time() * 1000),  # milliseconds
            "source": "test_script",
            "data": kwargs,
        }

        if subtype:
            event["subtype"] = subtype

        return event

    async def send_event(self, event: Dict[str, Any]):
        """Send an event to the server"""
        try:
            await self.sio.emit("claude_event", event)
            print(
                f"📤 Sent {event['type']}"
                + (f".{event.get('subtype', '')}" if event.get("subtype") else "")
            )
        except Exception as e:
            print(f"❌ Failed to send event: {e}")

    async def run_basic_test(self):
        """Run basic test with various event types"""
        print("\n🧪 Running basic event test...")

        test_events = [
            # Agent events
            self.create_test_event(
                "agent", "loaded", agent_type="Engineer", name="Test Engineer"
            ),
            self.create_test_event(
                "agent", "executed", agent_type="QA", task="Running tests"
            ),
            # Tool events
            self.create_test_event(
                "tool", "start", tool_name="Read", file_path="/test/file.py"
            ),
            self.create_test_event(
                "tool", "complete", tool_name="Read", success=True, duration_ms=120
            ),
            self.create_test_event(
                "tool", "start", tool_name="Write", file_path="/test/output.txt"
            ),
            self.create_test_event(
                "tool", "complete", tool_name="Write", success=True, lines_written=25
            ),
            # File events
            self.create_test_event("file", "read", path="/src/main.py", size=1024),
            self.create_test_event(
                "file", "write", path="/src/output.log", operation="create"
            ),
            self.create_test_event("file", "edit", path="/src/config.json", changes=3),
            # Session events
            self.create_test_event("session", "started", session_id="test-session-001"),
            self.create_test_event(
                "session", "ended", session_id="test-session-001", duration=45.2
            ),
            # Error events
            self.create_test_event(
                "error",
                "tool_failure",
                tool_name="Bash",
                error="Command not found",
                command="invalid_cmd",
            ),
            # Info events
            self.create_test_event(
                "info", "status", message="System running normally", cpu_usage=15.2
            ),
            self.create_test_event(
                "info", "metric", events_processed=1000, uptime="2h 15m"
            ),
        ]

        for event in test_events:
            await self.send_event(event)
            await asyncio.sleep(0.5)  # Small delay between events

    async def run_stream_test(self, duration: int = 30):
        """Run continuous stream test"""
        print(f"\n📊 Running stream test for {duration} seconds...")

        event_types = [
            ("agent", "activity", {"agent_type": "PM", "action": "delegating"}),
            ("tool", "execution", {"tool_name": "Grep", "pattern": "TODO"}),
            (
                "file",
                "access",
                {"path": "/src/components/test.js", "operation": "read"},
            ),
            ("session", "update", {"active_connections": random.randint(1, 5)}),
            ("info", "heartbeat", {"timestamp": time.time(), "status": "healthy"}),
        ]

        start_time = time.time()
        event_count = 0

        while time.time() - start_time < duration:
            # Pick random event type
            event_type, subtype, data = random.choice(event_types)

            # Add some randomization to data
            test_data = data.copy()
            test_data["sequence"] = event_count
            test_data["random_value"] = random.randint(1, 100)

            event = self.create_test_event(event_type, subtype, **test_data)
            await self.send_event(event)

            event_count += 1

            # Variable delay to simulate realistic event patterns
            delay = random.uniform(0.1, 2.0)
            await asyncio.sleep(delay)

        print(f"✅ Sent {event_count} events in {duration} seconds")

    async def run_complex_test(self):
        """Run test with complex nested data structures"""
        print("\n🔬 Running complex data test...")

        complex_events = [
            self.create_test_event(
                "claude",
                "request",
                prompt="Create a new React component for displaying user profiles",
                context={
                    "files": ["/src/components/UserProfile.tsx", "/src/types/User.ts"],
                    "requirements": [
                        "responsive design",
                        "accessibility",
                        "TypeScript",
                    ],
                    "previous_messages": [
                        {"role": "user", "content": "I need help with React"},
                        {"role": "assistant", "content": "I'd be happy to help!"},
                    ],
                },
            ),
            self.create_test_event(
                "claude",
                "response",
                response="I'll help you create a React component for user profiles...",
                metadata={
                    "tokens_used": 245,
                    "model": "claude-3-sonnet",
                    "completion_time": 1.8,
                    "tools_used": ["Write", "Edit"],
                },
            ),
            self.create_test_event(
                "memory",
                "operation",
                operation="store",
                key="project_context",
                value={
                    "project_type": "React + TypeScript",
                    "current_task": "User profile component",
                    "file_structure": {
                        "src/": {
                            "components/": ["Header.tsx", "Footer.tsx"],
                            "types/": ["User.ts", "Profile.ts"],
                            "utils/": ["api.ts", "validation.ts"],
                        }
                    },
                },
            ),
            self.create_test_event(
                "todo",
                "updated",
                todos=[
                    {
                        "content": "Create UserProfile component",
                        "status": "in_progress",
                        "activeForm": "Creating UserProfile component",
                    },
                    {
                        "content": "Add TypeScript types",
                        "status": "completed",
                        "activeForm": "Adding TypeScript types",
                    },
                    {
                        "content": "Implement responsive design",
                        "status": "pending",
                        "activeForm": "Implementing responsive design",
                    },
                    {
                        "content": "Add accessibility features",
                        "status": "pending",
                        "activeForm": "Adding accessibility features",
                    },
                ],
            ),
        ]

        for event in complex_events:
            await self.send_event(event)
            await asyncio.sleep(1.0)


async def main():
    """Main test function"""
    print("🚀 React EventViewer Test Script")
    print("=" * 50)

    tester = EventTester()

    # Try to connect
    if not await tester.connect():
        print("💡 Make sure the Claude MPM dashboard server is running on port 8765")
        return

    try:
        # Run tests
        await tester.run_basic_test()
        await asyncio.sleep(2)

        await tester.run_complex_test()
        await asyncio.sleep(2)

        # Ask user if they want streaming test
        print("\n" + "=" * 50)
        response = input("🎯 Run streaming test? (y/N): ").lower().strip()
        if response in ["y", "yes"]:
            duration = input("Duration in seconds (default 30): ").strip()
            try:
                duration = int(duration) if duration else 30
            except ValueError:
                duration = 30

            await tester.run_stream_test(duration)

        print("\n✅ Test completed successfully!")
        print(
            "🌐 Check the React EventViewer at: http://localhost:8765/static/events.html"
        )

    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
    finally:
        await tester.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
