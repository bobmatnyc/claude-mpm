#!/usr/bin/env python3
"""
Test script to verify SocketIO event broadcasting is working.

This script:
1. Starts the SocketIO server
2. Connects a SocketIO client
3. Sends an event via HTTP endpoint
4. Verifies the client receives the broadcasted event
"""

import os
import sys
import time
from datetime import datetime, timezone

import requests
import socketio as socketio_client

# Add the src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from claude_mpm.services.socketio.server.main import SocketIOServer


def test_socketio_broadcast():
    """Test complete event flow from HTTP to SocketIO broadcast."""

    print("\n=== Testing SocketIO Event Broadcasting ===\n")

    # Start the SocketIO server
    print("1. Starting SocketIO server on port 8765...")
    server = SocketIOServer(host="localhost", port=8765)
    server.start_sync()

    # Give server time to fully initialize
    time.sleep(2)

    # Create SocketIO client
    print("2. Creating SocketIO client...")
    client = socketio_client.Client(logger=False, engineio_logger=False)

    # Track received events
    received_events = []

    @client.on("connect")
    def on_connect():
        print("   ✅ Client connected to SocketIO server")

    @client.on("claude_event")
    def on_claude_event(data):
        print(f"   📨 Client received claude_event: {data.get('subtype', 'unknown')}")
        received_events.append(data)

    @client.on("system_event")
    def on_system_event(data):
        print(f"   📨 Client received system_event: {data.get('subtype', 'unknown')}")

    @client.on("disconnect")
    def on_disconnect():
        print("   ⚠️ Client disconnected")

    # Connect client
    print("3. Connecting client to server...")
    try:
        client.connect("http://localhost:8765", wait_timeout=5)
        time.sleep(1)  # Let connection establish
    except Exception as e:
        print(f"   ❌ Failed to connect client: {e}")
        server.stop_sync()
        return False

    # Send test event via HTTP endpoint
    print("4. Sending test event via HTTP endpoint...")
    test_event = {
        "hook_event_name": "UserPromptSubmit",
        "hook_input_data": {"query": "Test query from broadcast test"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": "test-session-123",
    }

    try:
        response = requests.post(
            "http://localhost:8765/api/events", json=test_event, timeout=5
        )
        print(f"   HTTP Response: {response.status_code}")

        if response.status_code != 204:
            print(f"   ❌ Unexpected status code: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ❌ Failed to send HTTP event: {e}")

    # Wait for event to be received
    print("5. Waiting for client to receive broadcasted event...")
    time.sleep(2)

    # Check if event was received
    success = False
    if received_events:
        print(f"\n   ✅ SUCCESS! Client received {len(received_events)} event(s)")
        for event in received_events:
            print(f"      - Type: {event.get('type')}, Subtype: {event.get('subtype')}")
        success = True
    else:
        print("\n   ❌ FAILURE! Client did not receive any events")
        print("   This indicates the broadcasting is not working properly")

    # Send another test via direct broadcast (if available)
    if hasattr(server, "broadcaster") and server.broadcaster:
        print("\n6. Testing direct broadcast via server.broadcaster...")
        server.broadcaster.broadcast_event("test", {"message": "Direct broadcast test"})
        time.sleep(1)

        if len(received_events) > 1:
            print("   ✅ Direct broadcast also working")
        else:
            print("   ⚠️ Direct broadcast may not be working")

    # Cleanup
    print("\n7. Cleaning up...")
    client.disconnect()
    server.stop_sync()

    return success


if __name__ == "__main__":
    # Kill any existing processes on port 8765
    print("Killing any existing processes on port 8765...")
    os.system("lsof -ti:8765 | xargs kill -9 2>/dev/null")
    time.sleep(1)

    # Run the test
    success = test_socketio_broadcast()

    if success:
        print("\n✅ SocketIO broadcasting is working correctly!")
        sys.exit(0)
    else:
        print("\n❌ SocketIO broadcasting is NOT working!")
        print("\nPossible issues:")
        print("1. The sio.emit() call in the HTTP handler is not reaching clients")
        print("2. The SocketIO server instance is not properly initialized")
        print("3. Event handlers are not registered correctly")
        print("4. Connection between components is broken")
        sys.exit(1)
