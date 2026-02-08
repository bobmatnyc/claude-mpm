#!/usr/bin/env python3
"""
Live Token Tracking Test
========================

Comprehensive real-time test that:
1. Monitors server logs
2. Sends test event
3. Captures exact server response
4. Verifies Socket.IO broadcast
"""

import json
import subprocess
import sys
import time
from datetime import datetime
from threading import Event, Thread

import socketio


class ServerLogMonitor:
    """Monitor server logs in real-time"""

    def __init__(self):
        self.logs = []
        self.stop_event = Event()

    def start(self):
        """Start monitoring logs"""
        print("📡 Starting server log monitor...")
        # Note: Server is already running, we'll capture events via socket

    def stop(self):
        """Stop monitoring"""
        self.stop_event.set()


class SocketIOTestClient:
    """Test Socket.IO connection and events"""

    def __init__(self):
        self.sio = socketio.Client()
        self.events_received = []
        self.connected = False
        self.setup_handlers()

    def setup_handlers(self):
        """Setup Socket.IO event handlers"""

        @self.sio.on("connect")
        def on_connect():
            self.connected = True
            print(
                f"✅ Connected to Socket.IO server at {datetime.now().strftime('%H:%M:%S')}"
            )

        @self.sio.on("disconnect")
        def on_disconnect():
            self.connected = False
            print(
                f"❌ Disconnected from Socket.IO server at {datetime.now().strftime('%H:%M:%S')}"
            )

        @self.sio.on("session_event")
        def on_session_event(data):
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"\n📥 Received session_event at {timestamp}")
            print(f"   Event type: {data.get('type', 'UNKNOWN')}")
            print(f"   Event subtype: {data.get('subtype', 'UNKNOWN')}")

            if (
                data.get("type") == "token_usage_updated"
                or data.get("subtype") == "token_usage_updated"
            ):
                print("   🎯 TOKEN USAGE EVENT!")
                print(f"   Data: {json.dumps(data.get('data', {}), indent=6)}")

            self.events_received.append(
                {"timestamp": timestamp, "event": "session_event", "data": data}
            )

        @self.sio.on("claude_event")
        def on_claude_event(data):
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"\n📥 Received claude_event at {timestamp}")
            print(f"   Event type: {data.get('type', 'UNKNOWN')}")
            print(f"   Event subtype: {data.get('subtype', 'UNKNOWN')}")

            if (
                data.get("type") == "token_usage_updated"
                or data.get("subtype") == "token_usage_updated"
            ):
                print("   🎯 TOKEN USAGE EVENT!")
                print(f"   Data: {json.dumps(data.get('data', {}), indent=6)}")

            self.events_received.append(
                {"timestamp": timestamp, "event": "claude_event", "data": data}
            )

        @self.sio.on("mpm_event")
        def on_mpm_event(data):
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"\n📥 Received mpm_event at {timestamp}")
            print(f"   Event type: {data.get('type', 'UNKNOWN')}")
            print(f"   Event subtype: {data.get('subtype', 'UNKNOWN')}")

            if (
                data.get("type") == "token_usage_updated"
                or data.get("subtype") == "token_usage_updated"
            ):
                print("   🎯 TOKEN USAGE EVENT!")
                print(f"   Data: {json.dumps(data.get('data', {}), indent=6)}")

            self.events_received.append(
                {"timestamp": timestamp, "event": "mpm_event", "data": data}
            )

        @self.sio.on("*")
        def catch_all(event, data):
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"\n📥 Received event '{event}' at {timestamp}")
            print(f"   Data: {json.dumps(data, indent=6)}")
            self.events_received.append(
                {"timestamp": timestamp, "event": event, "data": data}
            )

    def connect(self, url="http://localhost:8765"):
        """Connect to Socket.IO server"""
        try:
            print(f"🔌 Connecting to {url}...")
            self.sio.connect(url, transports=["websocket"])
            time.sleep(0.5)  # Give it time to connect
            return self.connected
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False

    def disconnect(self):
        """Disconnect from server"""
        if self.connected:
            self.sio.disconnect()

    def send_test_event(self):
        """Send test token_usage_updated event"""
        test_event = {
            "type": "token_usage_updated",
            "subtype": "token_usage_updated",
            "session_id": "test-session-123",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "input_tokens": 1234,
                "output_tokens": 567,
                "cache_creation_tokens": 89,
                "cache_read_tokens": 42,
                "total_tokens": 1932,
                "session_id": "test-session-123",
            },
        }

        print(
            f"\n📤 Sending test event at {datetime.now().strftime('%H:%M:%S.%f')[:-3]}"
        )
        print(f"   Event: {json.dumps(test_event, indent=6)}")

        # Send via Socket.IO emit using correct event name (claude_event)
        print("\n   Trying 'claude_event' event name...")
        self.sio.emit("claude_event", test_event)
        print("   ✅ Event sent via Socket.IO as 'claude_event'")

        return test_event


def check_server_health():
    """Check if monitoring server is running"""
    import subprocess

    result = subprocess.run(
        ["lsof", "-i", ":8765"], check=False, capture_output=True, text=True
    )

    if result.returncode == 0 and "python" in result.stdout:
        print("✅ Monitoring server is running on port 8765")
        return True
    print("❌ Monitoring server is NOT running on port 8765")
    print("   Please start it with: python -m src.claude_mpm.services.monitor.server")
    return False


def check_build_version():
    """Check what JavaScript build is being served"""
    import os

    build_dir = "src/claude_mpm/dashboard/static/svelte-build/_app/immutable"

    print("\n📦 Checking build version...")

    # Check entry files
    entry_dir = os.path.join(build_dir, "entry")
    if os.path.exists(entry_dir):
        files = os.listdir(entry_dir)
        print(f"   Entry files: {files}")

    # Check for token_usage_updated in chunks
    chunks_dir = os.path.join(build_dir, "chunks")
    if os.path.exists(chunks_dir):
        result = subprocess.run(
            ["grep", "-r", "token_usage_updated", chunks_dir],
            check=False,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            count = len(result.stdout.splitlines())
            print(f"   ✅ Found 'token_usage_updated' in {count} chunk files")
        else:
            print("   ❌ 'token_usage_updated' NOT found in chunk files")

    # Check version.json
    version_file = "src/claude_mpm/dashboard/static/svelte-build/_app/version.json"
    if os.path.exists(version_file):
        with open(version_file) as f:
            version = json.load(f)
            print(f"   Build version: {version}")


def main():
    """Run comprehensive live test"""

    print("=" * 70)
    print("LIVE TOKEN TRACKING TEST")
    print("=" * 70)
    print()

    # Step 1: Check server health
    if not check_server_health():
        sys.exit(1)

    # Step 2: Check build version
    check_build_version()

    # Step 3: Connect Socket.IO client
    print("\n" + "=" * 70)
    print("CONNECTING TO SERVER")
    print("=" * 70)
    print()

    client = SocketIOTestClient()
    if not client.connect():
        print("❌ Failed to connect to server")
        sys.exit(1)

    # Step 4: Wait for connection to stabilize
    print("\n⏳ Waiting 2 seconds for connection to stabilize...")
    time.sleep(2)

    # Step 5: Send test event
    print("\n" + "=" * 70)
    print("SENDING TEST EVENT")
    print("=" * 70)

    test_event = client.send_test_event()

    # Step 6: Wait for response
    print("\n⏳ Waiting 3 seconds for server to process and broadcast...")
    time.sleep(3)

    # Step 7: Report results
    print("\n" + "=" * 70)
    print("TEST RESULTS")
    print("=" * 70)
    print()

    print(f"📊 Total events received: {len(client.events_received)}")

    if client.events_received:
        print("\n📥 Events received:")
        for i, event in enumerate(client.events_received, 1):
            print(f"\n   {i}. {event['event']} at {event['timestamp']}")
            if event["event"] == "session_event":
                data = event["data"]
                print(f"      Type: {data.get('type', 'N/A')}")
                print(f"      Subtype: {data.get('subtype', 'N/A')}")
                if data.get("type") == "token_usage_updated":
                    print("      ✅ Token usage event received!")
                    print(f"      Data: {json.dumps(data.get('data', {}), indent=9)}")
    else:
        print("❌ NO EVENTS RECEIVED")
        print("\n🔍 Possible issues:")
        print("   1. Server is not broadcasting events")
        print("   2. Client not subscribed to correct event type")
        print("   3. Event routing is broken")
        print("   4. Socket.IO namespace mismatch")

    # Step 8: Cleanup
    print("\n🔌 Disconnecting...")
    client.disconnect()

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
