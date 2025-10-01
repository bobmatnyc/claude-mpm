#!/usr/bin/env python3
"""Send a test event to the monitor server"""

import json
import time
from datetime import datetime, timezone

import socketio

# Create a Socket.IO client
sio = socketio.Client()


@sio.event
def connect():
    print("✅ Connected to monitor server")

    # Send a test event
    test_event = {
        "type": "SubagentStart",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": "test-123",
        "session_id": "session-test-456",
        "agent_name": "TestAgent",
        "event_id": f"evt-{int(time.time())}",
        "context": {
            "user_instruction": "This is a test event from the debug script",
            "working_directory": "/test/path",
        },
    }

    print(f"📤 Sending test event: {test_event['type']}")
    sio.emit("event", test_event)

    # Send another event after a moment
    time.sleep(1)

    test_event2 = {
        "type": "ToolStart",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": "test-123",
        "session_id": "session-test-456",
        "agent_name": "TestAgent",
        "tool_name": "TestTool",
        "event_id": f"evt-{int(time.time())}",
        "context": {"command": "echo 'Testing activity dashboard'"},
    }

    print(f"📤 Sending test event: {test_event2['type']}")
    sio.emit("event", test_event2)

    time.sleep(1)

    # Send completion event
    test_event3 = {
        "type": "SubagentStop",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": "test-123",
        "session_id": "session-test-456",
        "agent_name": "TestAgent",
        "event_id": f"evt-{int(time.time())}",
        "context": {"status": "completed", "duration": 2.5},
    }

    print(f"📤 Sending test event: {test_event3['type']}")
    sio.emit("event", test_event3)

    print("✅ Test events sent successfully")


@sio.event
def disconnect():
    print("❌ Disconnected from monitor server")


@sio.event
def connect_error(data):
    print(f"Connection error: {data}")


if __name__ == "__main__":
    try:
        print("🚀 Connecting to monitor server at http://localhost:8765...")
        sio.connect("http://localhost:8765")

        # Keep connection alive briefly
        time.sleep(3)

        sio.disconnect()
        print("✅ Test completed")

    except Exception as e:
        print(f"❌ Error: {e}")
