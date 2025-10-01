#!/usr/bin/env python3
"""Test complete event flow from hook to dashboard."""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    import aiohttp
except ImportError:
    print("Please install aiohttp: pip install aiohttp")
    sys.exit(1)


async def test_http_endpoint():
    """Test direct HTTP POST to dashboard."""
    print("\n" + "=" * 60)
    print("1. Testing Direct HTTP POST to Dashboard")
    print("=" * 60)

    # Test event in Claude's format
    test_events = [
        {
            "hook_event_name": "PreToolUse",
            "hook_event_type": "PreToolUse",
            "session_id": "test-session-001",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "hook_input_data": {"tool_name": "Bash", "params": {"command": "ls"}},
        },
        {
            "hook_event_name": "UserPromptSubmit",
            "hook_event_type": "UserPromptSubmit",
            "session_id": "test-session-001",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "hook_input_data": {"prompt": "Test user prompt"},
        },
        {
            "hook_event_name": "PostToolUse",
            "hook_event_type": "PostToolUse",
            "session_id": "test-session-001",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "hook_input_data": {
                "tool_name": "Bash",
                "success": True,
                "result": "Command executed",
            },
        },
    ]

    async with aiohttp.ClientSession() as session:
        for event in test_events:
            try:
                # The connection manager transforms this to claude_event format
                url = "http://localhost:8765/api/events"

                print(f"\n📤 Sending {event['hook_event_name']}...")
                print(f"   Payload: {json.dumps(event, indent=2)}")

                async with session.post(url, json=event) as response:
                    if response.status == 204:
                        print("   ✅ Success: Server returned 204 No Content")
                    else:
                        text = await response.text()
                        print(f"   ❌ Error: Server returned {response.status}: {text}")

                await asyncio.sleep(1)  # Give dashboard time to process

            except Exception as e:
                print(f"   ❌ Failed to send: {e}")


async def test_socketio_client():
    """Test SocketIO client connection and event monitoring."""
    print("\n" + "=" * 60)
    print("2. Testing SocketIO Client Connection")
    print("=" * 60)

    try:
        import socketio  # noqa: F401
    except ImportError:
        print("⚠️ python-socketio not installed, skipping SocketIO test")
        return

    sio = socketio.AsyncClient()
    received_events = []

    @sio.event
    async def connect():
        print("✅ Connected to SocketIO server")

    @sio.event
    async def disconnect():
        print("❌ Disconnected from SocketIO server")

    @sio.on("claude_event")
    async def on_claude_event(data):
        print(f"📨 Received claude_event: {data.get('subtype', 'unknown')}")
        received_events.append(data)

    try:
        await sio.connect("http://localhost:8765")
        print("Listening for events for 5 seconds...")
        await asyncio.sleep(5)

        if received_events:
            print(f"\n✅ Received {len(received_events)} events via SocketIO")
            for event in received_events[:3]:  # Show first 3
                print(
                    f"   - {event.get('subtype', 'unknown')}: {event.get('type', 'unknown')}"
                )
        else:
            print("\n⚠️ No events received via SocketIO")

        await sio.disconnect()

    except Exception as e:
        print(f"❌ SocketIO connection failed: {e}")


async def check_dashboard_health():
    """Check dashboard health endpoint."""
    print("\n" + "=" * 60)
    print("3. Checking Dashboard Health")
    print("=" * 60)

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("http://localhost:8765/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ Dashboard is healthy:")
                    print(f"   - Status: {data.get('status', 'unknown')}")
                    print(f"   - Connected clients: {data.get('connected_clients', 0)}")
                    print(
                        f"   - Events sent: {data.get('stats', {}).get('events_sent', 0)}"
                    )
                    print(
                        f"   - Events buffered: {data.get('stats', {}).get('events_buffered', 0)}"
                    )
                else:
                    print(f"⚠️ Health check returned status {response.status}")
        except Exception as e:
            print(f"❌ Health check failed: {e}")


def check_hook_configuration():
    """Check if hooks are properly configured."""
    print("\n" + "=" * 60)
    print("4. Checking Hook Configuration")
    print("=" * 60)

    hook_path = Path.home() / ".claude/hooks/claude-mpm-hook.sh"
    if hook_path.exists():
        print(f"✅ Hook script exists: {hook_path}")

        # Check if it's executable
        import os

        if os.access(hook_path, os.X_OK):
            print("✅ Hook script is executable")
        else:
            print("⚠️ Hook script is not executable")

        # Check last modification time
        mtime = datetime.fromtimestamp(hook_path.stat().st_mtime)
        print(f"   Last modified: {mtime}")
    else:
        print(f"❌ Hook script not found at {hook_path}")

    # Check error log
    error_log = Path("/tmp/claude-mpm-hook-error.log")
    if error_log.exists():
        print(f"\n📋 Hook error log exists: {error_log}")
        mtime = datetime.fromtimestamp(error_log.stat().st_mtime)
        print(f"   Last modified: {mtime}")

        # Show last few lines
        lines = error_log.read_text().split("\n")[-5:]
        if any(line.strip() for line in lines):
            print("   Recent entries:")
            for line in lines:
                if line.strip():
                    print(f"      {line}")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Complete Event Flow Test")
    print("=" * 60)
    print("\nThis test verifies the complete event flow from hooks to dashboard.")

    # Check dashboard health first
    await check_dashboard_health()

    # Check hook configuration
    check_hook_configuration()

    # Test HTTP endpoint
    await test_http_endpoint()

    # Test SocketIO connection
    await test_socketio_client()

    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)
    print("\n✅ Next Steps:")
    print("1. Check if dashboard at http://localhost:8765 shows the test events")
    print("2. Use Claude tools to generate real hook events")
    print("3. Check /tmp/claude-mpm-hook-error.log for any hook handler issues")
    print(
        "4. If events still don't appear, the issue is likely with Claude's event format"
    )


if __name__ == "__main__":
    asyncio.run(main())
