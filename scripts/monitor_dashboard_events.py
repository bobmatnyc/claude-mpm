#!/usr/bin/env python3
"""Monitor dashboard events to verify HTTP event flow is working.

This script connects to the SocketIO server and displays all events
being broadcast to the dashboard. Useful for debugging event flow issues.
"""

import signal
import sys
import time
from collections import defaultdict
from datetime import datetime

import socketio

# Statistics tracking
stats = defaultdict(int)
start_time = datetime.now()
last_event_time = None


def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    print("\n\n📊 Final Statistics:")
    print("=" * 60)

    total_events = sum(stats.values())
    duration = (datetime.now() - start_time).total_seconds()

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
    print("=" * 60)
    print(f"Connecting to: {server_url}")
    print("Press Ctrl+C to stop monitoring\n")

    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create SocketIO client
    client = socketio.Client()

    @client.on("connect")
    def on_connect():
        print(f"✅ Connected to server at {datetime.now().isoformat()}")
        print("Monitoring events...\n")

    @client.on("disconnect")
    def on_disconnect():
        print(f"\n⚠️ Disconnected from server at {datetime.now().isoformat()}")

    @client.on("claude_event")
    def on_claude_event(data):
        """Handle claude_event from server."""
        global last_event_time

        now = datetime.now()
        last_event_time = now

        # Extract event details
        event_type = data.get("subtype", "unknown")
        source = data.get("source", "unknown")
        timestamp = data.get("timestamp", "")

        # Update statistics
        stats[event_type] += 1

        # Format and display event
        time_str = now.strftime("%H:%M:%S.%f")[:-3]

        # Color coding for different event types
        if "error" in event_type.lower():
            emoji = "❌"
        elif "subagent" in event_type.lower():
            emoji = "🤖"
        elif "tool" in event_type.lower():
            emoji = "🔧"
        elif "prompt" in event_type.lower():
            emoji = "💬"
        elif "heartbeat" in event_type.lower():
            emoji = "💓"
        else:
            emoji = "📨"

        print(f"[{time_str}] {emoji} {event_type:20} (source: {source:15}) {timestamp}")

        # Show details for specific events
        if event_type in ["subagent_stop", "pre_tool"]:
            event_data = data.get("data", {})
            if event_type == "subagent_stop":
                agent_type = event_data.get("agent_type", "unknown")
                print(f"           └─ Agent: {agent_type}")
            elif event_type == "pre_tool":
                tool_name = event_data.get("tool_name", "unknown")
                print(f"           └─ Tool: {tool_name}")
                if tool_name == "Task":
                    delegation = event_data.get("delegation_details", {})
                    if delegation:
                        delegated_to = delegation.get("agent_type", "unknown")
                        print(f"           └─ Delegating to: {delegated_to}")

    @client.on("system_event")
    def on_system_event(data):
        """Handle system events (like heartbeats)."""
        global last_event_time

        now = datetime.now()
        last_event_time = now

        event_type = data.get("subtype", "system")
        stats[f"system_{event_type}"] += 1

        if event_type == "heartbeat":
            event_data = data.get("data", {})
            uptime = event_data.get("uptime_seconds", 0)
            clients = event_data.get("connected_clients", 0)
            total_events = event_data.get("total_events", 0)

            time_str = now.strftime("%H:%M:%S")
            print(
                f"[{time_str}] 💓 System heartbeat - uptime: {uptime}s, clients: {clients}, events: {total_events}"
            )

    # Connect to server
    try:
        client.connect(server_url)

        # Monitor loop
        print(
            "\nMonitoring dashboard events. Statistics will update as events arrive..."
        )
        print(
            "(If you don't see events, make sure Claude Code is running with hooks enabled)\n"
        )

        while True:
            time.sleep(10)

            # Show periodic status
            if last_event_time:
                seconds_since_last = (datetime.now() - last_event_time).total_seconds()
                if seconds_since_last > 30:
                    print(f"\n⏳ No events for {seconds_since_last:.0f} seconds...")

    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False
    finally:
        client.disconnect()

    return True


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
