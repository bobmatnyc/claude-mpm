#!/usr/bin/env python3
"""Monitor dashboard events to verify HTTP event flow is working.

This script connects to the SocketIO server and displays all events
being broadcast to the dashboard. Useful for debugging event flow issues.
"""

import sys
import time
from collections import defaultdict
from datetime import datetime, timezone

import socketio

# Statistics tracking
stats = defaultdict(int)
start_time = datetime.now(timezone.utc)
last_event_time = None


def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    print("\n\n📊 Final Statistics:")
    print("=" * 60)

    total_events = sum(stats.values())
    duration = (datetime.now(timezone.utc) - start_time).total_seconds()

    print(f"Total events: {total_events}")
    print(f"Duration: {duration:.1f} seconds")
    print(f"Events per second: {total_events/duration:.2f}")

    if stats:
        print("\nEvent breakdown:")
        for event_type, count in sorted(
            stats.items(), key=lambda x: x[1], reverse=True
        ):
            percentage = (count / total_events) * 100
            print(f"  {event_type:20} {count:5} ({percentage:.1f}%)")

    print("\n✅ Monitoring stopped")
    sys.exit(0)


def monitor_dashboard_events(server_url="http://localhost:8765"):
    """Monitor events being sent to the dashboard."""
    print("\n🔍 Dashboard Event Monitor")
    print("="*40)

    client = connect_and_monitor(server_url, stats)
    if not client:
        return

    try:
        print("\n⏳ Monitoring... Press Ctrl+C to stop\n")
        while True:
            time.sleep(1)
            check_idle_time()
    except KeyboardInterrupt:
        print("\n\n📊 Session Statistics:")
        print_statistics()
        client.disconnect()


def create_event_handlers(client, stats):
    """Create and register all event handlers for the client."""

    @client.on("connect")
    def on_connect():
        print(f"✅ Connected to server at {datetime.now(timezone.utc).isoformat()}")
        print("Monitoring events...\n")

    @client.on("disconnect")
    def on_disconnect():
        print(f"\n⚠️ Disconnected from server at {datetime.now(timezone.utc).isoformat()}")

    @client.on("claude_event")
    def on_claude_event(data):
        """Handle claude_event from server."""
        global last_event_time

        now = datetime.now(timezone.utc)
        last_event_time = now

        handle_claude_event(data, now, stats)

    @client.on("system_event")
    def on_system_event(data):
        """Handle system events (like heartbeats)."""
        global last_event_time

        now = datetime.now(timezone.utc)
        last_event_time = now

        handle_system_event(data, now, stats)


def handle_claude_event(data, timestamp, stats):
    """Process a claude_event."""
    event_type = data.get("type", "unknown")
    subtype = data.get("subtype", "")

    # Update statistics
    stats[event_type] += 1
    if subtype:
        stats[f"{event_type}.{subtype}"] += 1

    # Display event details
    print(f"\n{'='*60}")
    print(f"📊 Event: {event_type}")
    if subtype:
        print(f"   Subtype: {subtype}")
    print(f"   Time: {timestamp.strftime('%H:%M:%S')}")

    # Show event data
    event_data = data.get("data", {})
    if event_data:
        print("   Data:")
        for key, value in list(event_data.items())[:5]:
            value_str = str(value)[:100]
            print(f"     {key}: {value_str}")

    print(f"{'='*60}")


def handle_system_event(data, timestamp, stats):
    """Process a system_event."""
    event_type = data.get("type", "system")

    # Update statistics
    stats["system"] += 1

    # Only show non-heartbeat system events
    if "heartbeat" not in str(data).lower():
        print(f"\n🔧 System Event: {event_type}")
        print(f"   Time: {timestamp.strftime('%H:%M:%S')}")


def connect_and_monitor(server_url, stats):
    """Connect to server and set up monitoring."""

    client = socketio.Client()
    create_event_handlers(client, stats)

    try:
        print(f"\n🔌 Connecting to {server_url}...")
        client.connect(server_url, namespaces=["/"])
        print("✅ Connection established\n")
        return client
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return None


if __name__ == "__main__":
    # Allow custom server URL
    server_url = "http://localhost:8765"
    if len(sys.argv) > 1:
        server_url = sys.argv[1]

    print(
        f"""
╔════════════════════════════════════════════════════════════╗
║            Dashboard Event Monitor for Claude MPM          ║
╠════════════════════════════════════════════════════════════╣
║  This tool monitors events being sent to the dashboard     ║
║  via the new HTTP POST mechanism from hook handlers.       ║
║                                                             ║
║  Usage: {sys.argv[0]} [server_url]              ║
║  Default: http://localhost:8765                            ║
╚════════════════════════════════════════════════════════════╝
"""
    )

    try:
        success = monitor_dashboard_events(server_url)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Monitor failed: {e}")
        sys.exit(1)
