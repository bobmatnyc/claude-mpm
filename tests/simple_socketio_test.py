#!/usr/bin/env python3
"""
Simple Socket.IO Connection Test
===============================

Basic test to verify Socket.IO connection and event reception.
"""

import sys
import time

import socketio


def test_connection():
    """Test basic Socket.IO connection."""
    print("🧪 Testing Socket.IO connection to localhost:8765")

    # Create client
    sio = socketio.Client(logger=False, engineio_logger=False)

    events_received = []

    @sio.event
    def connect():
        print("✅ Connected to Socket.IO server")

    @sio.event
    def disconnect():
        print("❌ Disconnected from Socket.IO server")

    @sio.event
    def claude_event(data):
        print(
            f"📡 Received claude_event: {data.get('type', 'unknown')}/{data.get('subtype', 'unknown')}"
        )
        events_received.append(data)

    @sio.event
    def connect_error(data):
        print(f"❌ Connection error: {data}")

    try:
        # Connect
        print("🔌 Connecting...")
        sio.connect("http://localhost:8765")

        # Wait for events
        print("⏳ Waiting for events (10 seconds)...")
        time.sleep(10)

        print(f"📊 Total events received: {len(events_received)}")

        # Disconnect
        sio.disconnect()

        return len(events_received) > 0

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    success = test_connection()
    if success:
        print("✅ Socket.IO test completed - events received")
    else:
        print("⚠️ Socket.IO test completed - no events received")
        sys.exit(1)
