#!/usr/bin/env python3
"""Verify that events are reaching the dashboard via WebSocket connection."""

import asyncio
import json
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, "/Users/masa/Projects/claude-mpm/src")

try:
    import socketio

    SOCKETIO_AVAILABLE = True
except ImportError:
    print("❌ python-socketio not installed. Install with: pip install python-socketio")
    sys.exit(1)


async def monitor_dashboard_events():
    """Connect to the SocketIO server as a dashboard client and monitor events."""

    print("\n" + "=" * 60)
    print("Dashboard Event Monitor")
    print("=" * 60)

    # Create a SocketIO client
    sio = socketio.AsyncClient()

    events_received = []

    @sio.event
    async def connect():
        print(f"\n✅ Connected to SocketIO server at {datetime.now(timezone.utc).isoformat()}")
        print("Monitoring for events...")
        print("-" * 40)

    @sio.event
    async def disconnect():
        print(f"\n❌ Disconnected from server at {datetime.now(timezone.utc).isoformat()}")

    @sio.event
    async def claude_event(data):
        """Handle Claude events from the server."""
        events_received.append(data)

        # Display the event
        event_type = data.get("type", "unknown")
        subtype = data.get("subtype", "")
        timestamp = data.get("timestamp", "")

        print(f"\n📨 Event Received [{timestamp}]")
        print(f"   Type: {event_type}")
        print(f"   Subtype: {subtype}")

        # Show specific details based on event type
        if event_type == "hook" and "data" in data:
            event_data = data["data"]
            if isinstance(event_data, dict):
                if "tool_name" in event_data:
                    print(f"   Tool: {event_data['tool_name']}")
                if "agent_type" in event_data:
                    print(f"   Agent: {event_data['agent_type']}")
                if "sessionId" in event_data:
                    print(f"   Session: {event_data['sessionId']}")
        elif event_type == "heartbeat":
            print("   💓 Server heartbeat")

    @sio.event
    async def server_status(data):
        """Handle server status updates."""
        print(f"\n📊 Server Status Update: {json.dumps(data, indent=2)}")

    try:
        # Connect to the server
        print("\nConnecting to SocketIO server at ws://localhost:8765...")
        await sio.connect("http://localhost:8765")

        # Wait and monitor for events
        print("\nMonitoring for 30 seconds...")
        print("(Hook events should appear here when Claude Code runs)")

        await asyncio.sleep(30)

        # Summary
        print("\n" + "=" * 60)
        print("Summary")
        print("=" * 60)
        print(f"Total events received: {len(events_received)}")

        # Count by type
        event_types = {}
        for event in events_received:
            event_type = (
                f"{event.get('type', 'unknown')}.{event.get('subtype', 'unknown')}"
            )
            event_types[event_type] = event_types.get(event_type, 0) + 1

        if event_types:
            print("\nEvent breakdown:")
            for event_type, count in sorted(event_types.items()):
                print(f"   - {event_type}: {count}")

        # Check for hook events
        hook_events = [e for e in events_received if e.get("type") == "hook"]
        if hook_events:
            print(f"\n✅ SUCCESS: Received {len(hook_events)} hook events!")
            print("The dashboard is receiving hook events correctly.")
        else:
            print("\n⚠️  No hook events received during monitoring period.")
            print("Try running Claude Code commands while this monitor is active.")

    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        await sio.disconnect()


def start_server_and_monitor():
    """Start the SocketIO server and then monitor for events."""

    from claude_mpm.hooks.claude_hooks.services.connection_manager import (
        ConnectionManagerService,
    )
    from claude_mpm.services.socketio.server.main import SocketIOServer

    print("\n" + "=" * 60)
    print("Starting Server and Event Monitor")
    print("=" * 60)

    # Start the server
    print("\n1. Starting SocketIO server...")
    server = SocketIOServer(port=8765)
    server.start_sync()
    time.sleep(2)

    # Verify EventBus integration
    if (
        hasattr(server, "eventbus_integration")
        and server.eventbus_integration.is_active()
    ):
        print("✅ EventBus integration is active")

    # Create a connection manager to simulate events
    print("\n2. Simulating some hook events...")
    conn_manager = ConnectionManagerService()

    # Simulate a few events
    for i in range(3):
        event_data = {
            "tool_name": ["Read", "Write", "Bash"][i],
            "sessionId": "monitor-test",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "parameters": {"test": f"event_{i}"},
        }
        conn_manager.emit_event(None, "pre_tool", event_data)
        time.sleep(0.5)

    conn_manager.cleanup()

    print("\n3. Starting dashboard monitor...")
    print("   (Events should appear below)")

    # Monitor for events
    try:
        asyncio.run(monitor_dashboard_events())
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user.")

    # Stop the server
    print("\n4. Stopping server...")
    server.stop_sync()

    print("\nComplete!")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--with-server":
        # Start server and monitor
        start_server_and_monitor()
    else:
        # Just monitor existing server
        print("Usage:")
        print("  python verify_dashboard_events.py          # Monitor existing server")
        print(
            "  python verify_dashboard_events.py --with-server  # Start server and monitor"
        )
        print("")
        print("Starting monitor for existing server...")

        try:
            asyncio.run(monitor_dashboard_events())
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped by user.")
