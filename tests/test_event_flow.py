#!/usr/bin/env python3
"""Test script to verify event flow from hooks to dashboard."""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# Set debug mode
os.environ["CLAUDE_MPM_HOOK_DEBUG"] = "true"
os.environ["CLAUDE_MPM_RELAY_DEBUG"] = "true"

from claude_mpm.services.event_bus import EventBus
from claude_mpm.services.socketio.server.main import SocketIOServer


def test_event_flow():
    """Test that events flow from hooks through EventBus to Socket.IO."""

    print("\n" + "=" * 60)
    print("Testing Event Flow from Hooks to Dashboard")
    print("=" * 60)

    # Start Socket.IO server with EventBus integration
    print("\n1. Starting Socket.IO server...")
    server = SocketIOServer(port=8765)
    server.start_sync()
    time.sleep(2)  # Wait for server to fully start

    # Get EventBus instance
    print("\n2. Getting EventBus instance...")
    event_bus = EventBus.get_instance()
    event_bus.set_debug(True)

    # Test different event types
    test_events = [
        {
            "event_type": "hook.pre_tool",
            "data": {
                "tool_name": "Bash",
                "session_id": "test-session-123",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "working_directory": "/test/dir",
                "git_branch": "main",
                "hook_event_name": "PreToolUse",
            },
        },
        {
            "event_type": "hook.subagent_start",
            "data": {
                "agent_type": "research",
                "session_id": "test-session-123",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "prompt": "Test research task",
                "hook_event_name": "SubagentStart",
            },
        },
        {
            "event_type": "hook.subagent_stop",
            "data": {
                "agent_type": "research",
                "session_id": "test-session-123",
                "reason": "completed",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "hook_event_name": "SubagentStop",
            },
        },
        {
            "event_type": "hook.post_tool",
            "data": {
                "tool_name": "Bash",
                "exit_code": 0,
                "session_id": "test-session-123",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "hook_event_name": "PostToolUse",
            },
        },
    ]

    print("\n3. Publishing test events to EventBus...")
    for test_event in test_events:
        print(f"\n   Publishing: {test_event['event_type']}")
        print(f"   Data: {json.dumps(test_event['data'], indent=2)}")

        # Publish to EventBus
        success = event_bus.publish(test_event["event_type"], test_event["data"])
        print(f"   Result: {'✅ Published' if success else '❌ Failed'}")

        time.sleep(0.5)  # Small delay between events

    # Check EventBus stats
    print("\n4. EventBus Statistics:")
    stats = event_bus.get_stats()
    print(f"   Events published: {stats.get('events_published', 0)}")
    print(f"   Events filtered: {stats.get('events_filtered', 0)}")
    print(f"   Events failed: {stats.get('events_failed', 0)}")

    # Check relay stats if available
    if hasattr(server, "eventbus_integration") and server.eventbus_integration:
        print("\n5. Relay Statistics:")
        relay_stats = server.eventbus_integration.get_stats()
        if "relay" in relay_stats:
            print(f"   Events relayed: {relay_stats['relay'].get('events_relayed', 0)}")
            print(f"   Events failed: {relay_stats['relay'].get('events_failed', 0)}")
            print(
                f"   Connection failures: {relay_stats['relay'].get('connection_failures', 0)}"
            )

    # Check server event history
    print(f"\n6. Server Event History: {len(server.event_history)} events")
    for event in list(server.event_history)[-5:]:  # Show last 5 events
        print(
            f"   - {event.get('type', 'unknown')}.{event.get('subtype', 'unknown')} at {event.get('timestamp', 'unknown')}"
        )

    print("\n7. Test Complete!")
    print("   Check the dashboard at http://localhost:8765/dashboard")
    print("   You should see the test events in the event viewer.")
    print("\n   Press Ctrl+C to stop the server...")

    try:
        # Keep server running for manual inspection
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nStopping server...")
        server.stop_sync()
        print("Server stopped.")


if __name__ == "__main__":
    test_event_flow()
