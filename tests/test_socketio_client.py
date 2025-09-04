#!/usr/bin/env python3
"""
Simple Socket.IO client to test for duplicate events.
"""

import sys
import time

import socketio

# Create a Socket.IO client
sio = socketio.Client()

# Event counters
event_counts = {}


@sio.event
def connect():
    print("✅ Connected to Socket.IO server")


@sio.event
def disconnect():
    print("❌ Disconnected from Socket.IO server")


@sio.event
def hook_event(data):
    """Handle hook:event messages"""
    event_type = data.get("type", "unknown")
    timestamp = data.get("timestamp", "no-timestamp")

    # Count events
    if event_type not in event_counts:
        event_counts[event_type] = 0
    event_counts[event_type] += 1

    print(
        f"🪝 [hook:event] {event_type} (count: {event_counts[event_type]}) - {timestamp}"
    )


@sio.event
def claude_event(data):
    """Handle claude_event messages"""
    event_type = data.get("type", "unknown")
    timestamp = data.get("timestamp", "no-timestamp")

    print(f"🤖 [claude_event] {event_type} - {timestamp}")


@sio.event
def connect_error(data):
    print(f"❌ Connection failed: {data}")


def main():
    try:
        print("🔌 Connecting to Socket.IO server at localhost:8765...")
        sio.connect("http://localhost:8765")

        print("👂 Listening for events... (Press Ctrl+C to stop)")
        print("📊 Event counts will be displayed for each hook event")
        print()

        # Keep the client running
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n🛑 Stopping client...")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if sio.connected:
            sio.disconnect()

        # Print final statistics
        print("\n📊 Final Event Counts:")
        for event_type, count in event_counts.items():
            print(f"  {event_type}: {count}")


if __name__ == "__main__":
    main()
