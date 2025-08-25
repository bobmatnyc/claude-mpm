#!/usr/bin/env python3
"""Combined test for system heartbeat functionality.

WHY: This script starts both the Socket.IO server and a client monitor
to verify that system heartbeat events are working correctly.
"""

import sys
import time
from pathlib import Path

# Add the src directory to the path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from claude_mpm.services.socketio_server import SocketIOServer

try:
    import socketio
except ImportError:
    print("Error: socketio-client not installed")
    print("Install with: pip install python-socketio[client]")
    sys.exit(1)


class HeartbeatClient:
    """Simple client to monitor heartbeats."""

    def __init__(self):
        self.sio = socketio.Client()
        self.heartbeats_received = 0
        self.system_events_received = 0

        @self.sio.on("connect")
        def on_connect():
            print("   ✅ Client connected to server")

        @self.sio.on("system_event")
        def on_system_event(data):
            self.system_events_received += 1
            if data.get("type") == "system" and data.get("event") == "heartbeat":
                self.heartbeats_received += 1
                hb_data = data.get("data", {})
                sessions = hb_data.get("active_sessions", [])
                print(f"\n   🫀 HEARTBEAT #{self.heartbeats_received}:")
                print(f"      - Uptime: {hb_data.get('uptime_seconds', 0)}s")
                print(f"      - Clients: {hb_data.get('connected_clients', 0)}")
                print(f"      - Events: {hb_data.get('total_events', 0)}")
                print(f"      - Sessions: {len(sessions)}")
                if sessions:
                    for sess in sessions[:3]:  # Show first 3 sessions
                        print(
                            f"        • {sess.get('session_id', '')[:8]}... [{sess.get('agent')}] - {sess.get('status')}"
                        )
            else:
                print(f"   📢 System Event: {data.get('event', 'unknown')}")

        @self.sio.on("claude_event")
        def on_claude_event(data):
            # Just count these, don't print
            pass

    def connect(self, port=8765):
        """Connect to the server."""
        try:
            self.sio.connect(f"http://localhost:{port}")
            return True
        except Exception as e:
            print(f"   ❌ Client connection failed: {e}")
            return False

    def disconnect(self):
        """Disconnect from server."""
        if self.sio.connected:
            self.sio.disconnect()


def main():
    """Run combined test."""
    print("🧪 Socket.IO System Heartbeat Combined Test")
    print("=" * 60)

    # Start server
    print("\n1️⃣  Starting Socket.IO server...")
    server = SocketIOServer(port=8765)

    # Set heartbeat interval to 3 seconds for faster testing
    if hasattr(server.core, "heartbeat_interval"):
        server.core.heartbeat_interval = 3
        print("   ⏰ Heartbeat interval set to 3 seconds")

    try:
        server.start_sync()
        print("   ✅ Server started on port 8765")

        # Wait a moment for server to fully initialize
        time.sleep(1)

        # Start client
        print("\n2️⃣  Starting heartbeat monitor client...")
        client = HeartbeatClient()
        if not client.connect():
            print("   ❌ Failed to connect client")
            return

        # Create test sessions
        print("\n3️⃣  Creating test sessions...")
        server.session_started("session-001", "cli", "/project/dir")
        print("   📝 Created PM session: session-001")

        time.sleep(1)
        server.agent_delegated("engineer", "Implement feature X", "started")
        print("   🤖 Delegated to engineer")

        time.sleep(1)
        server.session_started("session-002", "api", "/another/dir")
        print("   📝 Created session: session-002")
        server.agent_delegated("research", "Analyze codebase", "started")
        print("   🔍 Delegated to research")

        # Wait for heartbeats
        print("\n4️⃣  Waiting for heartbeats (12 seconds)...")
        print("-" * 60)

        for i in range(12):
            time.sleep(1)
            if i % 3 == 2:
                print(f"   ⏱️  {i+1} seconds elapsed...")

        # Summary
        print("\n" + "=" * 60)
        print("📊 Test Summary:")
        print(f"   • Heartbeats received: {client.heartbeats_received}")
        print(f"   • System events received: {client.system_events_received}")
        print(f"   • Active sessions tracked: {len(server.get_active_sessions())}")

        if client.heartbeats_received >= 3:
            print("\n✅ TEST PASSED: Heartbeat system working correctly!")
        else:
            print(
                f"\n⚠️  TEST WARNING: Only {client.heartbeats_received} heartbeats received (expected 3+)"
            )

    except KeyboardInterrupt:
        print("\n🛑 Test interrupted")
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        print("\n5️⃣  Cleaning up...")
        client.disconnect()
        print("   👋 Client disconnected")
        server.stop_sync()
        print("   👋 Server stopped")
        print("\n🏁 Test completed")


if __name__ == "__main__":
    main()
