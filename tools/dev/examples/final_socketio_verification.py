#!/usr/bin/env python3
"""
Final verification script to confirm Socket.IO hook integration is working.
This script tests the complete hook handler -> Socket.IO server -> dashboard flow.
"""

import asyncio
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


def run_final_verification():
    """Run the final end-to-end verification."""
    print("🎯 Final Socket.IO Hook Integration Verification")
    print("=" * 60)

    # Step 1: Verify server is running
    print("📡 Step 1: Checking if Socket.IO server is running...")
    try:
        import requests

        response = requests.get("http://localhost:8765/health", timeout=2)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Server running: {data['server']} on port {data['port']}")
            print(f"   Connected clients: {data['clients_connected']}")
        else:
            print(f"❌ Server health check failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Server not accessible: {e}")
        print("💡 Start the server with: python -m claude_mpm.services.socketio_server")
        return False

    # Step 2: Start event monitor
    print(f"\n📊 Step 2: Starting event monitor...")
    events_received = []
    monitor_connected = False

    try:
        import socketio

        async def monitor_events():
            nonlocal monitor_connected
            client = socketio.AsyncClient()

            @client.event
            async def connect():
                print("✅ Event monitor connected to Socket.IO server")
                nonlocal monitor_connected
                monitor_connected = True

            @client.event
            async def claude_event(data):
                event_type = data.get("data", {}).get("event_type", "unknown")
                print(f"📨 Received event: {event_type}")
                events_received.append(data)

            @client.event
            async def disconnect():
                print("🔌 Event monitor disconnected")

            try:
                await client.connect("http://localhost:8765")
                # Monitor for 15 seconds
                await asyncio.sleep(15)
                await client.disconnect()
            except Exception as e:
                print(f"❌ Monitor error: {e}")

        def run_monitor():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(monitor_events())

        monitor_thread = threading.Thread(target=run_monitor, daemon=True)
        monitor_thread.start()
        time.sleep(2)  # Give monitor time to connect

        if not monitor_connected:
            print("❌ Monitor failed to connect")
            return False

    except ImportError:
        print("⚠️ Socket.IO client not available - proceeding without event monitoring")
        monitor_thread = None

    # Step 3: Test hook handler events
    print(f"\n🧪 Step 3: Testing hook handler events...")

    # Set up environment
    env = os.environ.copy()
    env["CLAUDE_MPM_HOOK_DEBUG"] = "true"
    env["CLAUDE_MPM_SOCKETIO_PORT"] = "8765"
    env["PYTHONPATH"] = str(project_root / "src")

    # Test different hook events
    test_events = [
        {
            "hook_event_name": "UserPromptSubmit",
            "prompt": "Testing Socket.IO integration - user prompt",
            "session_id": "final_test_001",
            "cwd": str(Path.cwd()),
            "timestamp": datetime.now().isoformat(),
        },
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "echo 'Socket.IO test'"},
            "session_id": "final_test_002",
            "cwd": str(Path.cwd()),
            "timestamp": datetime.now().isoformat(),
        },
        {
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
            "exit_code": 0,
            "output": "Socket.IO test output",
            "session_id": "final_test_003",
            "cwd": str(Path.cwd()),
            "timestamp": datetime.now().isoformat(),
        },
    ]

    hook_handler_path = (
        project_root
        / "src"
        / "claude_mpm"
        / "hooks"
        / "claude_hooks"
        / "hook_handler.py"
    )
    successful_hooks = 0

    for i, event in enumerate(test_events, 1):
        print(f"   Testing {event['hook_event_name']}...")
        hook_json = json.dumps(event)

        try:
            result = subprocess.run(
                [sys.executable, str(hook_handler_path)],
                input=hook_json,
                text=True,
                capture_output=True,
                env=env,
                timeout=5,
            )

            if result.returncode == 0:
                successful_hooks += 1
                print(f"   ✅ Hook {i}/3 executed successfully")
            else:
                print(f"   ❌ Hook {i}/3 failed with code {result.returncode}")

            time.sleep(1)  # Small delay between events

        except Exception as e:
            print(f"   ❌ Hook {i}/3 error: {e}")

    # Step 4: Wait for event processing and check results
    print(f"\n⏳ Step 4: Waiting for event processing...")
    time.sleep(5)  # Wait for batch processing

    if monitor_thread:
        monitor_thread.join(timeout=2)

    # Step 5: Check connection pool stats
    print(f"\n📊 Step 5: Checking connection pool statistics...")
    try:
        from claude_mpm.core.socketio_pool import get_connection_pool

        pool = get_connection_pool()
        stats = pool.get_stats()

        print(f"   Events sent: {stats.get('total_events_sent', 0)}")
        print(f"   Errors: {stats.get('total_errors', 0)}")
        print(f"   Circuit state: {stats.get('circuit_state', 'unknown')}")
        print(f"   Active connections: {stats.get('active_connections', 0)}")

        pool_working = (
            stats.get("total_errors", 0) == 0 and stats.get("active_connections", 0) > 0
        )

    except Exception as e:
        print(f"   ❌ Error getting pool stats: {e}")
        pool_working = False

    # Final assessment
    print(f"\n" + "=" * 60)
    print(f"🎯 FINAL RESULTS:")
    print(f"   Server running: ✅")
    print(f"   Monitor connected: {'✅' if monitor_connected else '❌'}")
    print(f"   Hook handlers: {successful_hooks}/3 successful")
    print(f"   Events received: {len(events_received)}")
    print(f"   Connection pool: {'✅ Working' if pool_working else '❌ Issues'}")

    overall_success = (
        successful_hooks == 3
        and pool_working  # All hooks worked
        and (  # Connection pool working
            len(events_received) > 0 or not monitor_connected
        )  # Events received or monitor unavailable
    )

    print(
        f"\n🎉 OVERALL STATUS: {'✅ SUCCESS' if overall_success else '❌ NEEDS ATTENTION'}"
    )

    if overall_success:
        print(f"\n✅ Socket.IO hook integration is WORKING!")
        print(f"\nTo use with Claude:")
        print(f"1. Ensure Socket.IO server is running:")
        print(f"   python -m claude_mpm.services.socketio_server &")
        print(f"")
        print(f"2. Set environment variables (if needed):")
        print(f"   export CLAUDE_MPM_HOOK_DEBUG=true")
        print(f"   export CLAUDE_MPM_SOCKETIO_PORT=8765")
        print(f"")
        print(f"3. Run Claude with monitoring:")
        print(f"   ./scripts/claude-mpm run -i 'your prompt' --monitor")
        print(f"")
        print(f"4. View events in dashboard:")
        print(f"   http://localhost:8765/dashboard")

    else:
        print(f"\n❌ Some issues remain:")
        if successful_hooks < 3:
            print(f"   - Hook handlers not executing properly")
        if not pool_working:
            print(f"   - Connection pool has issues")
        if len(events_received) == 0 and monitor_connected:
            print(f"   - Events not reaching Socket.IO server")

    return overall_success


def main():
    """Run final verification."""
    try:
        return run_final_verification()
    except KeyboardInterrupt:
        print(f"\n⚠️ Verification interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Verification failed: {e}")
        import traceback

        print(f"Stack trace: {traceback.format_exc()}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
