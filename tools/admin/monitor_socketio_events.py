#!/usr/bin/env python3
"""
Monitor Socket.IO events while running a Claude session
"""

import json
import time

import socketio


def monitor_events():
    print("🔌 Starting Socket.IO event monitor...")

    # Create a Socket.IO client
    sio = socketio.Client()

    events_received = []

    @sio.event
    def connect():
        print("✅ Monitor connected to Socket.IO server!")
        print(f"Socket ID: {sio.sid}")

        # Request status and history
        sio.emit("get_status")
        sio.emit("get_history", {"limit": 10, "event_types": []})

    @sio.event
    def disconnect():
        print("❌ Monitor disconnected from Socket.IO server")

    @sio.event
    def connect_error(data):
        print(f"❌ Monitor connection error: {data}")

    @sio.event
    def status(data):
        print(f"📊 Server status: {json.dumps(data, indent=2)}")

    @sio.event
    def claude_event(data):
        events_received.append(data)
        print(f"📨 NEW EVENT #{len(events_received)}: {data.get('type', 'unknown')}")
        print(f"   Data: {json.dumps(data.get('data', {}), indent=4)}")
        print("-" * 50)

    @sio.event
    def history(data):
        if data.get("events"):
            print(f"📚 Received {len(data['events'])} historical events")
            for i, event in enumerate(data["events"][-5:]):  # Show last 5
                print(
                    f"   {i + 1}. {event.get('type', 'unknown')} - {event.get('timestamp', 'no timestamp')}"
                )
        else:
            print("📚 No historical events found")

    try:
        # Connect to the server
        sio.connect("http://localhost:8765")

        print("\n🎯 Monitor is running. Waiting for events...")
        print("   Run a Claude session in another terminal to see events")
        print("   Press Ctrl+C to stop monitoring\n")

        # Keep monitoring
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print(
                f"\n🛑 Stopping monitor. Received {len(events_received)} events total."
            )

            if events_received:
                print("\n📊 Event Summary:")
                event_types = {}
                for event in events_received:
                    event_type = event.get("type", "unknown")
                    event_types[event_type] = event_types.get(event_type, 0) + 1

                for event_type, count in event_types.items():
                    print(f"   {event_type}: {count}")

        finally:
            sio.disconnect()

    except Exception as e:
        print(f"❌ Monitor failed: {e}")
        return False

    return True


if __name__ == "__main__":
    success = monitor_events()
    if success:
        print("\n✅ Socket.IO monitoring completed")
    else:
        print("\n❌ Socket.IO monitoring failed")
