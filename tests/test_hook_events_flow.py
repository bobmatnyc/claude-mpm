#!/usr/bin/env python3
"""Test hook events flow from generation to dashboard display.

This script simulates hook events and verifies they:
1. Are sent to the Socket.IO server
2. Are properly broadcasted
3. Appear correctly in the dashboard
"""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import socketio


def simulate_hook_event(event_type: str, data: dict) -> dict:
    """Create a properly formatted hook event."""
    return {
        "type": f"hook.{event_type}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }


async def send_hook_events(port: int = 8765):
    """Send various hook events to test the pipeline."""

    # Create Socket.IO client
    sio = socketio.Client()

    @sio.event
    def connect():
        print(f"✅ Connected to Socket.IO server on port {port}")

    @sio.event
    def disconnect():
        print("🔌 Disconnected from Socket.IO server")

    @sio.event
    def claude_event(data):
        print(f"📥 Received broadcasted event: {json.dumps(data, indent=2)}")

    # Connect to server
    try:
        print(f"🔄 Connecting to Socket.IO server at http://localhost:{port}")
        sio.connect(f"http://localhost:{port}")

        # Wait for connection
        await asyncio.sleep(1)

        if not sio.connected:
            print("❌ Failed to connect to Socket.IO server")
            return

        # Test various hook events
        test_events = [
            # 1. User Prompt Event
            simulate_hook_event(
                "user_prompt",
                {
                    "session_id": "test-session-001",
                    "prompt_text": "Test user prompt from hook test",
                    "working_directory": "/test/dir",
                    "git_branch": "main",
                },
            ),
            # 2. Pre-Tool Event (Task delegation)
            simulate_hook_event(
                "pre_tool",
                {
                    "session_id": "test-session-001",
                    "tool_name": "Task",
                    "delegation_details": {
                        "agent_type": "engineer",
                        "prompt": "Test delegation to engineer",
                        "description": "Fix a bug in authentication",
                    },
                },
            ),
            # 3. Subagent Stop Event
            simulate_hook_event(
                "subagent_stop",
                {
                    "session_id": "test-session-001",
                    "agent_type": "engineer",
                    "agent_id": "eng-123",
                    "reason": "completed",
                    "working_directory": "/test/dir",
                    "git_branch": "main",
                    "is_successful_completion": True,
                    "has_results": True,
                    "hook_event_name": "SubagentStop",
                },
            ),
            # 4. Post-Tool Event
            simulate_hook_event(
                "post_tool",
                {
                    "session_id": "test-session-001",
                    "tool_name": "Edit",
                    "success": True,
                    "files_modified": ["test.py"],
                },
            ),
            # 5. Assistant Response Event
            simulate_hook_event(
                "assistant_response",
                {
                    "session_id": "test-session-001",
                    "response_text": "I've completed the task successfully",
                    "agent_type": "pm",
                },
            ),
        ]

        print("\n📤 Sending test hook events...\n")

        for i, event in enumerate(test_events, 1):
            print(f"Event {i}: {event['type']}")
            print(f"  Session: {event['data'].get('session_id', 'N/A')}")

            # Send as claude_event (how the hook handler sends it)
            sio.emit("claude_event", event)

            # Give some time for processing
            await asyncio.sleep(0.5)

        print("\n✅ All test events sent!")
        print("\n🔍 Check the dashboard to verify events are displayed correctly")
        print("📝 Expected to see:")
        print("  - User prompt event")
        print("  - Task delegation to engineer")
        print("  - Subagent stop event")
        print("  - Tool usage events")
        print("  - Assistant response")

        # Keep connection open to receive broadcasts
        print("\n⏳ Keeping connection open for 5 seconds to receive broadcasts...")
        await asyncio.sleep(5)

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if sio.connected:
            sio.disconnect()
        print("\n🏁 Test complete")


async def check_server_running(port: int = 8765) -> bool:
    """Check if Socket.IO server is running."""
    sio = socketio.Client()
    try:
        sio.connect(f"http://localhost:{port}", wait_timeout=2)
        if sio.connected:
            sio.disconnect()
            return True
    except:
        pass
    return False


async def main():
    """Main test function."""
    port = 8765

    print("=" * 60)
    print("Hook Events Flow Test")
    print("=" * 60)

    # Check if server is running
    print(f"\n🔍 Checking if Socket.IO server is running on port {port}...")
    if not await check_server_running(port):
        print(f"❌ Socket.IO server is not running on port {port}")
        print("💡 Start the server with: claude-mpm socketio start")
        return

    print(f"✅ Socket.IO server is running on port {port}")

    # Send test events
    await send_hook_events(port)


if __name__ == "__main__":
    asyncio.run(main())
