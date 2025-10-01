import pytest

#!/usr/bin/env python3
"""
Test script to verify the file-tool-tracker.js fix for undefined subtype handling.

This script sends various event types to the dashboard to ensure the JavaScript
error handling properly deals with events that have undefined or missing subtype fields.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict

import socketio


class DashboardEventTester:
    """Test dashboard event handling with various event shapes."""

    def __init__(self, dashboard_url: str = "http://localhost:8080"):
        self.dashboard_url = dashboard_url
        self.sio = socketio.AsyncClient()
        self.connected = False

    async def connect(self) -> bool:
        """Connect to the dashboard."""
        try:
            await self.sio.connect(self.dashboard_url)
            self.connected = True
            print(f"✓ Connected to dashboard at {self.dashboard_url}")
            return True
        except Exception as e:
            print(f"✗ Failed to connect: {e}")
            return False

    async def send_event(self, event: Dict[str, Any]) -> None:
        """Send an event to the dashboard."""
        if not self.connected:
            print("Not connected to dashboard")
            return

        try:
            await self.sio.emit("event", event)
            print(
                f"  → Sent event: type={event.get('type')}, subtype={event.get('subtype', 'UNDEFINED')}"
            )
        except Exception as e:
            print(f"  ✗ Error sending event: {e}")

    @pytest.mark.asyncio
    async def test_undefined_subtype_handling(self) -> None:
        """Test that the dashboard properly handles events with undefined subtypes."""
        print("\n=== Testing Undefined Subtype Handling ===\n")

        # Test 1: Normal event with subtype
        print("1. Normal event with subtype (should work):")
        await self.send_event(
            {
                "type": "hook",
                "subtype": "pre_tool",
                "tool_name": "Read",
                "tool_parameters": {"file_path": "/test/file1.txt"},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": "test-session-1",
            }
        )
        await asyncio.sleep(0.5)

        # Test 2: Event with missing subtype (previously caused error)
        print("\n2. Event with missing subtype (previously caused error):")
        await self.send_event(
            {
                "type": "hook",
                # 'subtype' is intentionally missing
                "tool_name": "Write",
                "tool_parameters": {"file_path": "/test/file2.txt"},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": "test-session-1",
            }
        )
        await asyncio.sleep(0.5)

        # Test 3: Event with null subtype
        print("\n3. Event with null subtype:")
        await self.send_event(
            {
                "type": "hook",
                "subtype": None,
                "tool_name": "Edit",
                "tool_parameters": {"file_path": "/test/file3.txt"},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": "test-session-1",
            }
        )
        await asyncio.sleep(0.5)

        # Test 4: Event with empty string subtype
        print("\n4. Event with empty string subtype:")
        await self.send_event(
            {
                "type": "hook",
                "subtype": "",
                "tool_name": "Grep",
                "tool_parameters": {"pattern": "test", "path": "/test"},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": "test-session-1",
            }
        )
        await asyncio.sleep(0.5)

        # Test 5: Event with numeric subtype (wrong type)
        print("\n5. Event with numeric subtype (wrong type):")
        await self.send_event(
            {
                "type": "hook",
                "subtype": 123,  # Wrong type - should be string
                "tool_name": "Bash",
                "tool_parameters": {"command": "ls -la"},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": "test-session-1",
            }
        )
        await asyncio.sleep(0.5)

        # Test 6: Post tool event with proper subtype
        print("\n6. Post tool event with proper subtype:")
        await self.send_event(
            {
                "type": "hook",
                "subtype": "post_tool",
                "tool_name": "Read",
                "tool_parameters": {"file_path": "/test/file1.txt"},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": "test-session-1",
                "success": True,
                "duration_ms": 150,
            }
        )
        await asyncio.sleep(0.5)

        # Test 7: Complex event with nested data structure
        print("\n7. Complex event with nested data structure:")
        await self.send_event(
            {
                "type": "hook",
                "subtype": "pre_tool",
                "data": {
                    "tool_name": "MultiEdit",
                    "tool_parameters": {
                        "file_path": "/test/complex.py",
                        "edits": [
                            {"old": "foo", "new": "bar"},
                            {"old": "baz", "new": "qux"},
                        ],
                    },
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": "test-session-2",
            }
        )
        await asyncio.sleep(0.5)

        print("\n=== Test Complete ===")
        print("\nCheck the browser console for any errors.")
        print("If no errors appear, the fix is working correctly!")

    async def disconnect(self) -> None:
        """Disconnect from the dashboard."""
        if self.connected:
            await self.sio.disconnect()
            self.connected = False
            print("\nDisconnected from dashboard")

    async def run_tests(self) -> None:
        """Run all tests."""
        if await self.connect():
            await self.test_undefined_subtype_handling()
            await self.disconnect()
        else:
            print("Could not connect to dashboard. Is it running?")
            print("Start it with: claude-mpm socketio-dashboard")


async def main():
    """Main entry point."""
    print("File Tool Tracker Fix Test")
    print("=" * 50)
    print("\nThis test verifies that the dashboard properly handles events")
    print("with missing or undefined subtype fields without throwing errors.")

    tester = DashboardEventTester()
    await tester.run_tests()


if __name__ == "__main__":
    asyncio.run(main())
