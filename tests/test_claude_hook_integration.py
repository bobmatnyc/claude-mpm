#!/usr/bin/env python3
"""Test Claude hook integration with Socket.IO server.

WHY: This script simulates the hook service sending events to the Socket.IO server,
mimicking how real Claude hooks would send events.
"""

import pytest

# Skip entire module - event_service module was removed in refactoring
pytestmark = pytest.mark.skip(
    reason="event_service module was removed in refactoring - needs rewrite"
)

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# from claude_mpm.hooks.claude_hooks.event_service import EventService  # Module removed
# from claude_mpm.hooks.claude_hooks.hook_handler import HookHandler  # May need update


@pytest.mark.asyncio
async def test_hook_service():
    """Test that hook service properly sends events to Socket.IO."""

    # Initialize event service (this connects to Socket.IO)
    event_service = EventService()

    # Start the event service
    await event_service.start()
    print("✅ Event service started and connected to Socket.IO")

    # Wait for connection to stabilize
    await asyncio.sleep(1)

    # Create test hook events like Claude would generate
    test_events = [
        {
            "event": "UserPrompt",
            "data": {
                "session_id": "test-session-001",
                "prompt_text": "Fix the authentication bug in the login module",
                "working_directory": "/Users/test/project",
                "timestamp": datetime.now().isoformat(),
            },
        },
        {
            "event": "SubagentStart",
            "data": {
                "session_id": "test-session-001",
                "agent_type": "engineer",
                "prompt": "Fix the authentication bug",
                "timestamp": datetime.now().isoformat(),
            },
        },
        {
            "event": "ToolCall",
            "data": {
                "session_id": "test-session-001",
                "tool_name": "Read",
                "parameters": {"file_path": "/src/auth.py"},
                "timestamp": datetime.now().isoformat(),
            },
        },
        {
            "event": "ToolCall",
            "data": {
                "session_id": "test-session-001",
                "tool_name": "Edit",
                "parameters": {
                    "file_path": "/src/auth.py",
                    "old_string": "bug",
                    "new_string": "fix",
                },
                "timestamp": datetime.now().isoformat(),
            },
        },
        {
            "event": "SubagentStop",
            "data": {
                "session_id": "test-session-001",
                "agent_type": "engineer",
                "status": "completed",
                "timestamp": datetime.now().isoformat(),
            },
        },
    ]

    print(f"\n📤 Sending {len(test_events)} hook events through event service...")

    for i, event in enumerate(test_events, 1):
        print(f"\n{i}. Sending {event['event']}")

        # Send through event service as hook events would
        await event_service.send_event(event["event"], event["data"])
        print("   ✅ Sent successfully")

        # Small delay between events
        await asyncio.sleep(0.5)

    print("\n⏳ Waiting 3 seconds for events to process...")
    await asyncio.sleep(3)

    print("\n✅ Test complete! Check the dashboard at http://localhost:8766/dashboard")
    print("   You should see the hook events in the event feed.")

    # Stop the event service
    await event_service.stop()
    print("Event service stopped")


async def main():
    """Main test function."""
    print("🔍 Testing Claude Hook Integration with Socket.IO")
    print("=" * 50)

    try:
        await test_hook_service()
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
