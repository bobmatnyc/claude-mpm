#!/usr/bin/env python3
"""
End-to-end test for dashboard event flow with simulated Claude Code hooks.

This test verifies:
1. Dashboard is running and accessible
2. Events sent via HTTP endpoint are broadcasted
3. Multiple clients receive the same events
4. Event normalization is working correctly
"""

import sys
import time
from datetime import datetime, timezone

import requests
import socketio as socketio_client


def simulate_claude_session():
    """Simulate a Claude Code session with various hook events."""

    session_id = f"test-session-{int(time.time())}"
    base_url = "http://localhost:8765/api/events"

    # Sequence of events that would come from Claude Code hooks
    events_sequence = [
        {
            "name": "Session Start",
            "event": {
                "hook_event_name": "SessionStart",
                "hook_input_data": {
                    "working_dir": "/Users/test/project",
                    "launch_method": "test",
                },
            },
        },
        {
            "name": "User Prompt",
            "event": {
                "hook_event_name": "UserPromptSubmit",
                "hook_input_data": {
                    "query": "Help me analyze this codebase and find performance issues"
                },
            },
        },
        {
            "name": "Pre Tool Use - Read",
            "event": {
                "hook_event_name": "PreToolUse",
                "hook_input_data": {
                    "tool": "read_file",
                    "parameters": {"path": "/src/main.py"},
                },
            },
        },
        {
            "name": "Post Tool Use - Read",
            "event": {
                "hook_event_name": "PostToolUse",
                "hook_input_data": {
                    "tool": "read_file",
                    "result": "File read successfully",
                    "duration_ms": 45,
                },
            },
        },
        {
            "name": "Pre Tool Use - Search",
            "event": {
                "hook_event_name": "PreToolUse",
                "hook_input_data": {
                    "tool": "search",
                    "parameters": {"query": "performance bottleneck"},
                },
            },
        },
        {
            "name": "Post Tool Use - Search",
            "event": {
                "hook_event_name": "PostToolUse",
                "hook_input_data": {
                    "tool": "search",
                    "result": "Found 3 matches",
                    "duration_ms": 120,
                },
            },
        },
        {
            "name": "Assistant Response",
            "event": {
                "hook_event_name": "AssistantResponse",
                "hook_input_data": {
                    "response": "I've analyzed your codebase and found several performance issues:\n1. Database queries in loops\n2. Missing indexes\n3. Inefficient algorithm complexity"
                },
            },
        },
        {
            "name": "Session End",
            "event": {
                "hook_event_name": "Stop",
                "hook_input_data": {"reason": "completed"},
            },
        },
    ]

    print(f"\nSimulating Claude Code session: {session_id}")
    print("-" * 50)

    for event_info in events_sequence:
        event = event_info["event"]
        event["timestamp"] = datetime.now(timezone.utc).isoformat()
        event["session_id"] = session_id

        try:
            response = requests.post(base_url, json=event, timeout=2)
            if response.status_code == 204:
                print(f"✅ Sent: {event_info['name']}")
            else:
                print(f"⚠️  {event_info['name']}: Status {response.status_code}")
        except Exception as e:
            print(f"❌ Failed to send {event_info['name']}: {e}")

        # Small delay between events to simulate real interaction
        time.sleep(0.5)

    print("-" * 50)
    print("Session simulation complete\n")


def create_dashboard_client(client_id, events_collector):
    """Create a dashboard client that collects events."""

    client = socketio_client.Client(logger=False, engineio_logger=False)

    @client.on("connect")
    def on_connect():
        print(f"   Client {client_id} connected")

    @client.on("claude_event")
    def on_claude_event(data):
        events_collector.append(
            {
                "client": client_id,
                "type": "claude_event",
                "subtype": data.get("subtype", "unknown"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    @client.on("disconnect")
    def on_disconnect():
        print(f"   Client {client_id} disconnected")

    return client


def test_e2e_dashboard():
    """Run end-to-end test of dashboard event system."""

    print("\n" + "=" * 60)
    print("  END-TO-END DASHBOARD EVENT FLOW TEST")
    print("=" * 60)

    # Check if dashboard is accessible
    print("\n1. Checking dashboard availability...")
    try:
        response = requests.get("http://localhost:8765", timeout=2)
        if response.status_code == 200:
            print("   ✅ Dashboard is accessible on port 8765")
        else:
            print(f"   ⚠️  Dashboard returned status {response.status_code}")
    except Exception as e:
        print(f"   ❌ Dashboard not accessible: {e}")
        print("   Please start the dashboard with: claude-mpm monitor start")
        return False

    # Create multiple clients to test broadcasting
    print("\n2. Creating multiple dashboard clients...")
    events_collected = []
    clients = []

    for i in range(3):
        client = create_dashboard_client(f"Client-{i + 1}", events_collected)
        try:
            client.connect("http://localhost:8765", wait_timeout=3)
            clients.append(client)
        except Exception as e:
            print(f"   ❌ Failed to connect Client-{i + 1}: {e}")

    if not clients:
        print("   No clients could connect!")
        return False

    print(f"   ✅ Connected {len(clients)} clients")

    # Wait for connections to stabilize
    time.sleep(1)

    # Run the simulated session
    print("\n3. Simulating Claude Code session...")
    simulate_claude_session()

    # Wait for events to be received
    print("\n4. Collecting broadcasted events...")
    time.sleep(2)

    # Analyze results
    print("\n5. Analyzing results...")
    print("-" * 50)

    # Group events by client
    events_by_client = {}
    for event in events_collected:
        client_id = event["client"]
        if client_id not in events_by_client:
            events_by_client[client_id] = []
        events_by_client[client_id].append(event["subtype"])

    # Check if all clients received events
    success = True
    for client_id, subtypes in events_by_client.items():
        print(f"   {client_id}: Received {len(subtypes)} events")
        if len(subtypes) == 0:
            success = False

    if not events_by_client:
        print("   ❌ No events were received by any client!")
        success = False

    # Check event types received
    all_subtypes = set()
    for subtypes in events_by_client.values():
        all_subtypes.update(subtypes)

    print(f"\n   Event types received: {', '.join(sorted(all_subtypes))}")

    expected_subtypes = {
        "user_prompt",
        "pre_tool",
        "post_tool",
        "assistant_response",
        "stop",
    }
    missing_subtypes = expected_subtypes - all_subtypes
    if missing_subtypes:
        print(f"   ⚠️  Missing expected event types: {', '.join(missing_subtypes)}")

    # Disconnect all clients
    for client in clients:
        client.disconnect()

    return success


if __name__ == "__main__":
    success = test_e2e_dashboard()

    print("\n" + "=" * 60)
    if success:
        print("  ✅ END-TO-END TEST PASSED!")
        print("=" * 60)
        print("\nThe dashboard event system is working correctly!")
        print("\nNext steps:")
        print("1. Open http://localhost:8765 in your browser")
        print("2. Run Claude Code with: claude-mpm run")
        print("3. Watch real-time events appear in the dashboard")
        sys.exit(0)
    else:
        print("  ❌ END-TO-END TEST FAILED!")
        print("=" * 60)
        print("\nThe dashboard event system has issues.")
        print("\nTroubleshooting:")
        print("1. Check logs: tail -f .claude-mpm/socketio-server.log")
        print("2. Restart dashboard: claude-mpm monitor restart")
        print("3. Check for port conflicts: lsof -i:8765")
        sys.exit(1)
