#!/usr/bin/env python3
"""Test script to verify HTTP event flow from hook handlers to dashboard.

This script:
1. Starts the SocketIO server
2. Sends test events via HTTP POST
3. Verifies the events are broadcast to dashboard clients
"""

import os
import sys
import threading
import time
from datetime import datetime, timezone

import requests
import socketio

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from claude_mpm.services.socketio.server.main import SocketIOServer


def test_http_event_flow():
    """Test the HTTP POST event flow."""
    print("\n🧪 Testing HTTP Event Flow for Dashboard Stability")
    print("=" * 60)

    # 1. Start the SocketIO server
    print("\n1️⃣ Starting SocketIO server...")
    server = SocketIOServer(host="localhost", port=8765)
    server.start_sync()
    print("✅ Server started on http://localhost:8765")

    # Wait for server to be ready
    time.sleep(2)

    # 2. Create a SocketIO client to receive events (simulating dashboard)
    print("\n2️⃣ Connecting dashboard client...")
    client = socketio.Client()
    received_events = []

    @client.on("claude_event")
    def on_claude_event(data):
        """Handle received claude_event."""
        received_events.append(data)
        print(f"   📨 Dashboard received: {data.get('subtype', 'unknown')} event")

    @client.on("connect")
    def on_connect():
        print("   ✅ Dashboard client connected")

    # Connect the client
    try:
        client.connect("http://localhost:8765")
        time.sleep(1)  # Wait for connection to establish
    except Exception as e:
        print(f"   ❌ Failed to connect dashboard client: {e}")
        server.stop_sync()
        return False

    # 3. Send test events via HTTP POST (simulating hook handlers)
    print("\n3️⃣ Sending test events via HTTP POST...")

    test_events = [
        {
            "event": "claude_event",
            "type": "hook",
            "subtype": "user_prompt",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {"sessionId": "test-session-1", "prompt": "Test prompt from HTTP"},
        },
        {
            "event": "claude_event",
            "type": "hook",
            "subtype": "pre_tool",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "sessionId": "test-session-1",
                "tool_name": "Task",
                "delegation_details": {"agent_type": "engineer"},
            },
        },
        {
            "event": "claude_event",
            "type": "hook",
            "subtype": "subagent_stop",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "sessionId": "test-session-1",
                "agent_type": "engineer",
                "response": "Task completed",
            },
        },
    ]

    for event in test_events:
        try:
            response = requests.post(
                "http://localhost:8765/api/events",
                json=event,
                timeout=1.0,
                headers={"Content-Type": "application/json"},
            )
            if response.status_code == 204:
                print(f"   ✅ Sent {event['subtype']} event via HTTP POST")
            else:
                print(f"   ⚠️ HTTP POST returned status {response.status_code}")
        except requests.exceptions.Timeout:
            print(f"   ⚠️ HTTP POST timed out for {event['subtype']}")
        except Exception as e:
            print(f"   ❌ Failed to send {event['subtype']}: {e}")

        time.sleep(0.5)  # Small delay between events

    # 4. Wait and verify events were received
    print("\n4️⃣ Verifying event reception...")
    time.sleep(2)  # Wait for events to be processed

    success = len(received_events) == len(test_events)

    if success:
        print(f"   ✅ All {len(test_events)} events received by dashboard!")
        print("\n   📊 Event Summary:")
        for i, event in enumerate(received_events, 1):
            print(
                f"      {i}. {event.get('subtype', 'unknown')} - {event.get('timestamp', 'no timestamp')}"
            )
    else:
        print(f"   ❌ Only {len(received_events)}/{len(test_events)} events received")
        if received_events:
            print("\n   📊 Received Events:")
            for event in received_events:
                print(f"      - {event.get('subtype', 'unknown')}")

    # 5. Test rapid-fire events (simulating multiple hook handlers)
    print("\n5️⃣ Testing rapid-fire events (simulating ephemeral processes)...")
    rapid_events_sent = 0
    rapid_events_start_count = len(received_events)

    def send_rapid_event(event_num):
        """Send a single event simulating an ephemeral hook handler."""
        try:
            event = {
                "event": "claude_event",
                "type": "hook",
                "subtype": f"rapid_event_{event_num}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {"event_num": event_num},
            }
            response = requests.post(
                "http://localhost:8765/api/events",
                json=event,
                timeout=0.5,  # Short timeout for fire-and-forget
            )
            return response.status_code == 204
        except:
            return True  # Fire-and-forget, timeout is OK

    # Send 10 rapid events from different "processes" (threads)
    threads = []
    for i in range(10):
        t = threading.Thread(target=lambda n=i: send_rapid_event(n))
        threads.append(t)
        t.start()
        rapid_events_sent += 1
        time.sleep(0.05)  # 50ms between spawns

    # Wait for all threads to complete
    for t in threads:
        t.join(timeout=1.0)

    print(f"   ✅ Sent {rapid_events_sent} rapid-fire events")

    # Wait and check reception
    time.sleep(2)
    rapid_events_received = len(received_events) - rapid_events_start_count

    if rapid_events_received == rapid_events_sent:
        print(f"   ✅ All {rapid_events_sent} rapid events received!")
    else:
        print(f"   ⚠️ {rapid_events_received}/{rapid_events_sent} rapid events received")

    # 6. Cleanup
    print("\n6️⃣ Cleaning up...")
    client.disconnect()
    server.stop_sync()
    print("   ✅ Test completed")

    # Final result
    print("\n" + "=" * 60)
    if success and rapid_events_received > 0:
        print("✅ HTTP EVENT FLOW TEST PASSED!")
        print(
            "The dashboard can now receive events reliably from ephemeral hook handlers."
        )
        return True
    print("❌ HTTP EVENT FLOW TEST FAILED")
    return False


if __name__ == "__main__":
    try:
        success = test_http_event_flow()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
