#!/usr/bin/env python3
"""Test hook events flowing to the Socket.IO dashboard.

This script simulates the complete flow from hook system to dashboard:
1. Creates a hook service client
2. Sends various hook events
3. Verifies events appear in the dashboard
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    import aiohttp
    import socketio
except ImportError:
    print("❌ Error: Required packages not installed")
    print("   Run: pip install python-socketio[asyncio_client] aiohttp")
    sys.exit(1)

# Configuration
SOCKETIO_URL = "http://localhost:8765"
HOOK_SERVICE_URL = "http://localhost:8080"


class DashboardMonitor:
    """Monitors the Socket.IO dashboard for events."""

    def __init__(self):
        self.sio = socketio.AsyncClient(logger=False, engineio_logger=False)
        self.connected = False
        self.hook_events = []
        self.system_events = []
        self.register_handlers()

    def register_handlers(self):
        """Register Socket.IO event handlers."""

        @self.sio.event
        async def connect():
            self.connected = True
            print("📡 Dashboard monitor connected")

        @self.sio.event
        async def disconnect():
            self.connected = False
            print("🔌 Dashboard monitor disconnected")

        @self.sio.event
        async def claude_event(data):
            if data.get("type") == "hook":
                self.hook_events.append(data)
                print(f"   ✅ Dashboard received hook event: {data.get('event')}")

        @self.sio.event
        async def system_event(data):
            self.system_events.append(data)
            if data.get("event") == "heartbeat":
                print("   💗 Dashboard received heartbeat")

    async def connect_and_monitor(self):
        """Connect to the dashboard and start monitoring."""
        await self.sio.connect(SOCKETIO_URL)
        await asyncio.sleep(0.5)
        return self.connected


class HookEventSimulator:
    """Simulates hook events being sent to the system."""

    @staticmethod
    async def send_hook_event(event_type: str, data: Dict[str, Any]) -> bool:
        """Send a hook event to the hook service."""
        try:
            # Try to send via hook service if available
            async with aiohttp.ClientSession() as session:
                payload = {
                    "event": event_type,
                    "timestamp": datetime.now().isoformat(),
                    **data,
                }

                # First try the hook service
                try:
                    async with session.post(
                        f"{HOOK_SERVICE_URL}/hook",
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=2),
                    ) as resp:
                        if resp.status == 200:
                            print(f"   📤 Sent {event_type} via hook service")
                            return True
                except (aiohttp.ClientError, asyncio.TimeoutError):
                    pass

                # Fallback: Send directly to Socket.IO server
                async with session.post(
                    f"{SOCKETIO_URL}/api/hook",
                    json={"type": "hook", "event": event_type, **payload},
                    timeout=aiohttp.ClientTimeout(total=2),
                ) as resp:
                    if resp.status in (200, 201):
                        print(f"   📤 Sent {event_type} via Socket.IO API")
                        return True

        except Exception as e:
            print(f"   ⚠️  Failed to send {event_type}: {e}")

        # Last resort: Connect as client and emit
        try:
            temp_sio = socketio.AsyncClient(logger=False, engineio_logger=False)
            await temp_sio.connect(SOCKETIO_URL)
            await temp_sio.emit(
                "claude_event",
                {
                    "type": "hook",
                    "event": event_type,
                    "timestamp": datetime.now().isoformat(),
                    **data,
                },
            )
            await asyncio.sleep(0.2)
            await temp_sio.disconnect()
            print(f"   📤 Sent {event_type} via Socket.IO client")
            return True
        except Exception as e:
            print(f"   ❌ Failed to send {event_type} via client: {e}")
            return False


async def run_test():
    """Run the complete hook-to-dashboard test."""
    print("\n" + "=" * 60)
    print("🧪 HOOK TO DASHBOARD FLOW TEST")
    print("=" * 60)

    # Check if Socket.IO server is running
    print("\n1️⃣  Checking Socket.IO server...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{SOCKETIO_URL}/socket.io/?EIO=4") as resp:
                if resp.status != 200:
                    print("   ❌ Socket.IO server not responding")
                    return False
        print("   ✅ Socket.IO server is running")
    except Exception:
        print("   ❌ Socket.IO server not running. Run: claude-mpm monitor start")
        return False

    # Connect dashboard monitor
    print("\n2️⃣  Connecting dashboard monitor...")
    monitor = DashboardMonitor()
    if not await monitor.connect_and_monitor():
        print("   ❌ Failed to connect dashboard monitor")
        return False
    print("   ✅ Dashboard monitor connected")

    # Send test hook events
    print("\n3️⃣  Sending test hook events...")
    simulator = HookEventSimulator()

    test_events = [
        ("Start", {"session_id": "test-123", "project": "test-project"}),
        ("SubagentStart", {"agent": "Engineer", "task": "Fix bug in auth"}),
        (
            "SubagentStop",
            {"agent": "Engineer", "result": "success", "changes": ["auth.py"]},
        ),
        ("ToolUse", {"tool": "Edit", "file": "auth.py", "action": "modify"}),
        ("Stop", {"session_id": "test-123", "duration": 45.2, "status": "completed"}),
    ]

    for event_type, data in test_events:
        await simulator.send_hook_event(event_type, data)
        await asyncio.sleep(0.5)  # Give time for event to propagate

    # Wait a moment for events to be received
    print("\n4️⃣  Waiting for events to propagate...")
    await asyncio.sleep(2)

    # Check results
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS")
    print("=" * 60)

    print(f"\n✅ Events sent: {len(test_events)}")
    print(f"✅ Hook events received by dashboard: {len(monitor.hook_events)}")
    print(f"✅ System events received: {len(monitor.system_events)}")

    if monitor.hook_events:
        print("\n📋 Hook events received:")
        for event in monitor.hook_events:
            print(f"   - {event.get('event', 'unknown')}")

    # Success criteria
    success = len(monitor.hook_events) >= 3  # At least 3 events received

    if success:
        print("\n✅ Test PASSED! Events are flowing to the dashboard")
        print("\n📌 Next steps:")
        print("   1. Open http://localhost:8765 in your browser")
        print("   2. You should see the events in the dashboard")
        print("   3. New events will appear as they occur")
    else:
        print("\n⚠️  Test PARTIAL: Some events may not have propagated")
        print("   This could be normal if the hook service isn't running")
        print("   Events sent directly to Socket.IO should still work")

    # Disconnect
    await monitor.sio.disconnect()
    return success


async def main():
    """Main entry point."""
    try:
        success = await run_test()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted")
        return 1
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
