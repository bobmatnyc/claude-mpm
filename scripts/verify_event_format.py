#!/usr/bin/env python3
"""Verify and document the correct Claude event format.

This script shows the CORRECT format that Claude uses for hook events
and provides a simple way to test individual events.
"""

import asyncio
import json
import sys
from datetime import datetime
from typing import Optional

try:
    import aiohttp
except ImportError:
    print("Please install aiohttp: pip install aiohttp")
    sys.exit(1)


# CORRECT Claude Event Format Documentation
CLAUDE_EVENT_FORMAT = """
CRITICAL: Claude sends events with these key fields:

1. **hook_event_name** (REQUIRED) - The event type identifier
   - This is the PRIMARY field Claude uses
   - Values: UserPromptSubmit, PreToolUse, PostToolUse, Stop, SubagentStop, etc.

2. **hook_event_type** - Usually same as hook_event_name

3. **hook_input_data** - Contains the actual event data

4. **sessionId** - Session identifier

5. **timestamp** - ISO format timestamp

WRONG formats that were causing issues:
- Using "event" field instead of "hook_event_name" ❌
- Using "type" field instead of "hook_event_name" ❌
- Missing hook_input_data wrapper ❌
"""


def create_correct_event(event_name: str, data: Optional[dict] = None) -> dict:
    """Create a properly formatted Claude event."""
    return {
        "hook_event_name": event_name,  # CRITICAL: Must be hook_event_name!
        "hook_event_type": event_name,
        "hook_input_data": data or {},
        "sessionId": f"test-{datetime.now().strftime('%H%M%S')}",
        "timestamp": datetime.now().isoformat(),
    }


async def send_test_event(event_name: str, data: Optional[dict] = None, port: int = 8765):
    """Send a single test event to verify format."""
    event = create_correct_event(event_name, data)

    print(f"\n📤 Sending {event_name} event...")
    print(f"Format: {json.dumps(event, indent=2)}")

    url = f"http://localhost:{port}/api/events"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=event) as response:
                if response.status == 204:
                    print("✅ Event sent successfully!")
                else:
                    text = await response.text()
                    print(f"❌ Failed: {response.status} - {text}")
    except Exception as e:
        print(f"❌ Error: {e}")


async def main():
    """Main entry point."""
    print("=" * 60)
    print("Claude Event Format Verification")
    print("=" * 60)
    print(CLAUDE_EVENT_FORMAT)
    print("=" * 60)

    if len(sys.argv) > 1:
        # Test specific event type from command line
        event_type = sys.argv[1]

        # Example data for different event types
        event_data = {
            "UserPromptSubmit": {"prompt": "Test prompt"},
            "PreToolUse": {"tool_name": "Bash", "params": {"command": "ls"}},
            "PostToolUse": {"tool_name": "Bash", "success": True},
            "Stop": {"reason": "task_completed"},
            "SubagentStop": {"agent_type": "engineer", "reason": "completed"},
        }

        data = event_data.get(event_type, {})
        await send_test_event(event_type, data)
    else:
        print("\nUsage:")
        print("  python verify_event_format.py [EventType]")
        print("\nExample:")
        print("  python verify_event_format.py UserPromptSubmit")
        print("  python verify_event_format.py PreToolUse")
        print("  python verify_event_format.py SubagentStop")
        print("\nThis will send a test event with the CORRECT format.")

        # Show example of correct vs wrong format
        print("\n" + "=" * 60)
        print("Format Comparison:")
        print("=" * 60)

        print("\n✅ CORRECT Format (what Claude sends):")
        correct = create_correct_event("PreToolUse", {"tool_name": "Bash"})
        print(json.dumps(correct, indent=2))

        print("\n❌ WRONG Format (what tests were sending):")
        wrong = {
            "event": "PreToolUse",  # WRONG: should be hook_event_name
            "type": "pre_tool",  # WRONG: should be hook_event_name
            "tool_name": "Bash",  # WRONG: should be in hook_input_data
            "timestamp": datetime.now().isoformat(),
        }
        print(json.dumps(wrong, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
