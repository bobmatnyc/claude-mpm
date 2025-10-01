#!/usr/bin/env python3
"""
Test script to verify events flow to the dashboard.

This script:
1. Connects to the running dashboard
2. Simulates a hook event
3. Verifies the dashboard receives the event
"""

import sys
import time
from datetime import datetime, timezone

import requests
import socketio as socketio_client


def test_dashboard_event_flow():
    """Test that events flow to the dashboard."""

    print("\n=== Testing Dashboard Event Flow ===\n")

    # Create SocketIO client to monitor dashboard
    print("1. Connecting to dashboard on port 8765...")
    client = socketio_client.Client(logger=False, engineio_logger=False)

    # Track received events
    received_events = []

    @client.on("connect")
    def on_connect():
        print("   ✅ Connected to dashboard")

    @client.on("claude_event")
    def on_claude_event(data):
        print(
            f"   📨 Dashboard received event - Type: {data.get('type')}, Subtype: {data.get('subtype')}"
        )
        received_events.append(data)

    @client.on("system_event")
    def on_system_event(data):
        print(f"   📨 Dashboard received system event: {data.get('subtype')}")

    @client.on("disconnect")
    def on_disconnect():
        print("   ⚠️ Disconnected from dashboard")

    # Connect to dashboard
    try:
        client.connect("http://localhost:8765", wait_timeout=5)
        time.sleep(1)  # Let connection establish
    except Exception as e:
        print(f"   ❌ Failed to connect to dashboard: {e}")
        print("   Make sure the dashboard is running on port 8765")
        return False

    # Send a simulated hook event
    print("\n2. Sending simulated hook event to dashboard...")
    hook_event = {
        "hook_event_name": "UserPromptSubmit",
        "hook_input_data": {
            "query": "This is a test prompt to verify dashboard events are working"
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": "test-dashboard-" + str(int(time.time())),
    }

    try:
        response = requests.post(
            "http://localhost:8765/api/events", json=hook_event, timeout=5
        )
        print(f"   Sent event, HTTP Response: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Failed to send event: {e}")
        client.disconnect()
        return False

    # Wait for event to be received
    print("\n3. Waiting for dashboard to receive event...")
    time.sleep(2)

    # Check results
    if received_events:
        print(f"\n   ✅ SUCCESS! Dashboard received {len(received_events)} event(s):")
        for event in received_events:
            print(f"      - Type: {event.get('type')}, Subtype: {event.get('subtype')}")
            if event.get("data"):
                data_preview = (
                    str(event["data"])[:100] + "..."
                    if len(str(event["data"])) > 100
                    else str(event["data"])
                )
                print(f"        Data: {data_preview}")

        # Send more events to test continuous flow
        print("\n4. Sending additional test events...")
        test_events = [
            {
                "hook_event_name": "PreToolUse",
                "hook_input_data": {"tool": "read_file", "path": "/test/file.txt"},
            },
            {
                "hook_event_name": "PostToolUse",
                "hook_input_data": {"tool": "read_file", "result": "success"},
            },
            {
                "hook_event_name": "AssistantResponse",
                "hook_input_data": {"response": "Test response"},
            },
        ]

        for test_event in test_events:
            test_event["timestamp"] = datetime.now(timezone.utc).isoformat()
            test_event["session_id"] = hook_event["session_id"]

            try:
                response = requests.post(
                    "http://localhost:8765/api/events", json=test_event, timeout=2
                )
                print(
                    f"   Sent {test_event['hook_event_name']}: {response.status_code}"
                )
            except Exception as e:
                print(f"   Failed to send {test_event['hook_event_name']}: {e}")

        time.sleep(2)

        print(f"\n5. Total events received by dashboard: {len(received_events)}")

        success = (
            len(received_events) >= 1
        )  # At least the first event should be received
    else:
        print("\n   ❌ FAILURE! Dashboard did not receive any events")
        success = False

    # Cleanup
    client.disconnect()

    return success


if __name__ == "__main__":
    success = test_dashboard_event_flow()

    if success:
        print("\n" + "=" * 50)
        print("✅ Dashboard is receiving events correctly!")
        print("=" * 50)
        print("\nYou can now:")
        print("1. Open http://localhost:8765 in your browser")
        print("2. Run Claude Code with hooks enabled")
        print("3. See real-time events in the dashboard")
        sys.exit(0)
    else:
        print("\n" + "=" * 50)
        print("❌ Dashboard is NOT receiving events!")
        print("=" * 50)
        print("\nTroubleshooting steps:")
        print("1. Check if dashboard is running: claude-mpm monitor status")
        print("2. Check logs: tail -f .claude-mpm/socketio-server.log")
        print("3. Restart dashboard: claude-mpm monitor restart")
        sys.exit(1)
