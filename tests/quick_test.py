#!/usr/bin/env python3
import time
from datetime import datetime, timedelta, timezone

import socketio

sio = socketio.Client()


@sio.event
def connect():
    print("🔌 Connected - sending quick test data")

    # Simple test event
    test_event = {
        "type": "todo",
        "subtype": "updated",
        "data": {
            "todos": [
                {
                    "content": "Quick test todo",
                    "activeForm": "Working on quick test",
                    "status": "in_progress",
                }
            ]
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": "test-session-quick",
    }

    sio.emit("hook_event", test_event)
    print("✅ Sent quick test event")
    time.sleep(2)
    sio.disconnect()


try:
    sio.connect("http://localhost:8765")
    sio.wait()
except Exception as e:
    print(f"❌ Error: {e}")
