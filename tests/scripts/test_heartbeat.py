#!/usr/bin/env python3
"""Test script for system heartbeat events.

WHY: This script verifies that the Socket.IO server is sending system heartbeat
events every minute as expected, separate from hook events.
"""

import signal
import sys
import time
from datetime import UTC, datetime, timezone

try:
    import socketio
except ImportError:
    print("Error: socketio-client not installed")
    print("Install with: pip install python-socketio[client]")
    sys.exit(1)


class HeartbeatMonitor:
    """Monitor for system heartbeat events."""

    def __init__(self, port=8765):
        self.port = port
        self.sio = socketio.Client()
        self.heartbeats_received = 0
        self.last_heartbeat = None
        self.running = True

        # Register event handlers
        self.sio.on("connect", self.on_connect)
        self.sio.on("disconnect", self.on_disconnect)
        self.sio.on("system_event", self.on_system_event)
        self.sio.on("claude_event", self.on_claude_event)

    def on_connect(self):
        """Handle connection to server."""
        print(f"✅ Connected to Socket.IO server on port {self.port}")
        print("⏰ Waiting for system heartbeat events (every 60 seconds)...")
        print("-" * 60)

    def on_disconnect(self):
        """Handle disconnection from server."""
        print("❌ Disconnected from Socket.IO server")

    def on_system_event(self, data):
        """Handle system events."""
        if data.get("type") == "system" and data.get("event") == "heartbeat":
            self.heartbeats_received += 1
            self.last_heartbeat = datetime.now(UTC)

            heartbeat_data = data.get("data", {})

            print(f"\n🫀 SYSTEM HEARTBEAT #{self.heartbeats_received}")
            print(f"   Timestamp: {data.get('timestamp')}")
            print(f"   Uptime: {heartbeat_data.get('uptime_seconds', 0)} seconds")
            print(f"   Connected Clients: {heartbeat_data.get('connected_clients', 0)}")
            print(f"   Total Events: {heartbeat_data.get('total_events', 0)}")

            sessions = heartbeat_data.get("active_sessions", [])
            if sessions:
                print(f"   Active Sessions ({len(sessions)}):")
                for session in sessions:
                    print(
                        f"      - {session.get('session_id', '')[:8]}... "
                        f"[{session.get('agent', 'unknown')}] "
                        f"Status: {session.get('status', 'unknown')}"
                    )
            else:
                print("   Active Sessions: None")

            server_info = heartbeat_data.get("server_info", {})
            print(f"   Server Version: {server_info.get('version', 'unknown')}")
            print(f"   Server Port: {server_info.get('port', 'unknown')}")
            print("-" * 60)

    def on_claude_event(self, data):
        """Handle claude events (for comparison)."""
        event_type = data.get("type")
        if event_type == "hook":
            hook_event = data.get("event")
            print(f"📌 Hook Event: {hook_event}")
        elif event_type != "system":
            # Only show non-system claude events
            print(f"📢 Claude Event: {event_type}")

    def run(self):
        """Connect and monitor heartbeats."""
        try:
            # Connect to server
            url = f"http://localhost:{self.port}"
            print(f"🔗 Connecting to {url}...")
            self.sio.connect(url)

            # Run until interrupted
            while self.running:
                time.sleep(1)

                # Print status every 30 seconds
                if self.heartbeats_received > 0 and int(time.time()) % 30 == 0:
                    if self.last_heartbeat:
                        elapsed = (
                            datetime.now(UTC) - self.last_heartbeat
                        ).total_seconds()
                        print(f"⏱️  {elapsed:.0f} seconds since last heartbeat")

        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped by user")
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            self.disconnect()

    def disconnect(self):
        """Disconnect from server."""
        self.running = False
        if self.sio.connected:
            self.sio.disconnect()
            print("👋 Disconnected from server")
        print(f"\n📊 Total heartbeats received: {self.heartbeats_received}")


def main():
    """Main entry point."""
    print("🫀 Socket.IO System Heartbeat Monitor")
    print("=" * 60)

    # Check command line arguments
    port = 8765
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port: {sys.argv[1]}")
            sys.exit(1)

    # Create and run monitor
    monitor = HeartbeatMonitor(port)

    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        monitor.running = False

    signal.signal(signal.SIGINT, signal_handler)

    # Run the monitor
    monitor.run()


if __name__ == "__main__":
    main()
