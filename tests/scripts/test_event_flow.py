import pytest

#!/usr/bin/env python3
"""Test script to verify event flow from hook handler to dashboard."""

import asyncio
import sys
from datetime import datetime

import socketio


@pytest.mark.asyncio
async def test_event_flow():
    """Test that events flow properly through the system."""

    print("Testing Claude MPM Event Flow")
    print("=" * 50)

    # Create Socket.IO client
    sio = socketio.Client()
    events_received = []
    history_received = False

    @sio.event
    def connect():
        print("✅ Connected to Socket.IO server")

    @sio.event
    def disconnect():
        print("🔌 Disconnected from server")

    @sio.event
    def claude_event(data):
        """Handle claude_event from server."""
        events_received.append(data)
        event_type = data.get("type", "unknown")
        if event_type == "hook":
            hook_event = data.get("event", "unknown")
            print(f"📨 Received hook event: {hook_event}")
        else:
            print(f"📨 Received event: {event_type}")

    @sio.event
    def history(data):
        """Handle history event from server."""
        nonlocal history_received
        history_received = True
        count = data.get("count", 0)
        total = data.get("total_available", 0)
        print(f"📚 Received event history: {count} events (total available: {total})")
        if data.get("events"):
            for event in data["events"][:5]:  # Show first 5
                event_type = event.get("type", "unknown")
                timestamp = event.get("timestamp", "")
                print(f"   - {event_type} at {timestamp}")

    @sio.event
    def welcome(data):
        """Handle welcome message."""
        print(f"👋 Welcome message: {data.get('message', '')}")

    @sio.event
    def status(data):
        """Handle status message."""
        clients = data.get("clients_connected", 0)
        print(f"📊 Server status: {clients} clients connected")

    try:
        # Connect to server
        print("\n1. Connecting to Socket.IO server...")
        sio.connect("http://localhost:8765")

        # Wait for connection and history
        await asyncio.sleep(2)

        if history_received:
            print("✅ Event history replay is working!")
        else:
            print("⚠️  No event history received on connection")

        # Send a test hook event
        print("\n2. Sending test hook event...")
        test_event = {
            "type": "hook",
            "event": "user_prompt",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "session_id": "test-session-123",
                "prompt_text": "Test prompt from event flow test",
                "working_directory": "/test/dir",
            },
        }

        sio.emit("claude_event", test_event)
        print(f"   Sent: {test_event['event']}")

        # Wait for the event to be processed
        await asyncio.sleep(1)

        # Send another test event
        print("\n3. Sending test subagent_stop event...")
        test_event2 = {
            "type": "hook",
            "event": "subagent_stop",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "session_id": "test-session-123",
                "agent_type": "research",
                "reason": "completed",
            },
        }

        sio.emit("claude_event", test_event2)
        print(f"   Sent: {test_event2['event']}")

        # Wait for processing
        await asyncio.sleep(1)

        # Disconnect and reconnect to test history
        print("\n4. Testing reconnection and history replay...")
        sio.disconnect()
        await asyncio.sleep(1)

        # Reset history flag
        history_received = False
        events_before = len(events_received)

        # Reconnect
        sio.connect("http://localhost:8765")
        await asyncio.sleep(2)

        if history_received:
            print("✅ History replay on reconnection is working!")
        else:
            print("⚠️  No history received on reconnection")

        # Summary
        print("\n" + "=" * 50)
        print("TEST SUMMARY:")
        print(f"  Total events received: {len(events_received)}")
        print(f"  History replay working: {'✅ Yes' if history_received else '❌ No'}")

        hook_events = [e for e in events_received if e.get("type") == "hook"]
        print(f"  Hook events received: {len(hook_events)}")

        if len(hook_events) > 0:
            print("✅ Event flow is working!")
        else:
            print("❌ No hook events received - event flow may be broken")

    except Exception as e:
        print(f"❌ Error during test: {e}")
        return False
    finally:
        if sio.connected:
            sio.disconnect()

    return True


if __name__ == "__main__":
    # Check if server is running
    try:
        import requests

        response = requests.get("http://localhost:8765/", timeout=1)
        print("✅ Socket.IO server is running")
    except:
        print("❌ Socket.IO server is not running on port 8765")
        print("   Please start it with: claude-mpm monitor --start")
        sys.exit(1)

    # Run the async test
    success = asyncio.run(test_event_flow())
    sys.exit(0 if success else 1)
