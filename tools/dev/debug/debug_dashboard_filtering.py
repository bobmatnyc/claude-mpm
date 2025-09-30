#!/usr/bin/env python3
"""
Debug Dashboard Filtering
Sends various event types to test the filtering logic
"""

import time
from datetime import datetime

import socketio

# Connect to the dashboard WebSocket
sio = socketio.Client()

@sio.event
def connect():
    print("✅ Connected to dashboard WebSocket")

@sio.event
def disconnect():
    print("❌ Disconnected from dashboard WebSocket")

def send_test_events():
    """Send a variety of event types to test filtering"""

    # Test events with different structures
    test_events = [
        # Standard hook event (should work)
        {
            "type": "hook",
            "subtype": "pre_tool",
            "tool_name": "Read",
            "tool_parameters": {"file_path": "/test/file1.txt"},
            "timestamp": datetime.now().isoformat(),
            "session_id": "test-session-1"
        },

        # Tool_use event (should work with new filtering)
        {
            "type": "tool_use",
            "tool_name": "Write",
            "tool_parameters": {"file_path": "/test/file2.txt", "content": "test"},
            "timestamp": datetime.now().isoformat(),
            "session_id": "test-session-1"
        },

        # Agent event with tool info (should work with new filtering)
        {
            "type": "agent",
            "subtype": "engineer",
            "tool_name": "Edit",
            "tool_parameters": {"file_path": "/test/file3.txt"},
            "agent_type": "Engineer Agent",
            "timestamp": datetime.now().isoformat(),
            "session_id": "test-session-1"
        },

        # Response event with tool info (should work with new filtering)
        {
            "type": "response",
            "tool_name": "Bash",
            "tool_parameters": {"command": "ls -la"},
            "timestamp": datetime.now().isoformat(),
            "session_id": "test-session-1"
        },

        # Event with tool info in data field
        {
            "type": "custom",
            "data": {
                "tool_name": "Grep",
                "tool_parameters": {"pattern": "test", "path": "/test/"},
            },
            "timestamp": datetime.now().isoformat(),
            "session_id": "test-session-1"
        },

        # Event without type but with tool_name (edge case)
        {
            "tool_name": "Read",
            "tool_parameters": {"file_path": "/test/edge_case.txt"},
            "timestamp": datetime.now().isoformat(),
            "session_id": "test-session-1"
        }
    ]

    print(f"\n📤 Sending {len(test_events)} test events with various structures...")

    for i, event in enumerate(test_events):
        print(f"   Event {i+1}: type='{event.get('type', 'none')}', tool='{event.get('tool_name', event.get('data', {}).get('tool_name', 'none'))}'")
        sio.emit('event', event)
        time.sleep(0.1)  # Small delay between events

    print("\n✅ All test events sent!")

def main():
    print("=" * 60)
    print("Dashboard Filtering Debug Test")
    print("=" * 60)

    try:
        # Connect to the dashboard WebSocket
        print("\n🔌 Connecting to dashboard WebSocket on port 8765...")
        sio.connect('http://localhost:8765',
                    socketio_path='/socket.io/',
                    transports=['websocket', 'polling'])

        # Send test events
        send_test_events()

        # Give some time for processing
        time.sleep(2)

        print("\n" + "=" * 60)
        print("📊 Check your dashboard at http://localhost:5173/dashboard.html")
        print("\nExpected results with fixed filtering:")
        print("  ✅ Events tab: Should show all 6 events")
        print("  ✅ Tools tab: Should show 6 tool operations")
        print("  ✅ Files tab: Should show 5 file operations (not Bash)")
        print("  ✅ Agents tab: Should show Engineer Agent from event 3")
        print("\nIf tabs are still empty, check browser console for errors.")
        print("=" * 60)

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        sio.disconnect()

if __name__ == "__main__":
    main()
