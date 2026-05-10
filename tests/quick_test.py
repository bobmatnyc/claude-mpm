#!/usr/bin/env python3
import time
from datetime import UTC, datetime, timedelta, timezone


def main():
    import socketio

    # Instantiate the client inside main() so that pytest collection of this
    # file does not create a socketio.Client at import time (which can install
    # signal handlers or start threads at construction time in xdist workers).
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
            "timestamp": datetime.now(UTC).isoformat(),
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


if __name__ == "__main__":
    main()
