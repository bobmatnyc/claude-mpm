#!/usr/bin/env python3
"""
Test script to verify that hook events do NOT appear in Browser Logs tab.
This script will:
1. Trigger some hook events by using tools
2. Check what events are emitted
3. Verify browser log isolation
"""

import asyncio
import json
from datetime import datetime, timezone

import socketio

# Create a Socket.IO client
sio = socketio.AsyncClient()

# Track received events
received_events = {"browser_log": [], "claude_event": [], "hook:event": []}


@sio.event
async def connect():
    print("✅ Connected to monitor server")


@sio.event
async def disconnect():
    print("❌ Disconnected from monitor server")


@sio.on("browser_log")
async def on_browser_log(data):
    """Handler for browser_log events"""
    received_events["browser_log"].append(data)

    # Check if this is a hook event (should NOT happen)
    if isinstance(data, dict):
        if "type" in data and "hook" in str(data.get("type", "")):
            print(f"❌ ERROR: Hook event received on browser_log channel: {data}")
        elif "browser_id" not in data:
            print(f"⚠️ WARNING: Event without browser_id on browser_log channel: {data}")
        else:
            print(f"✅ Valid browser log received: browser_id={data.get('browser_id')}")


@sio.on("claude_event")
async def on_claude_event(data):
    """Handler for claude_event events"""
    received_events["claude_event"].append(data)

    if isinstance(data, dict) and data.get("type"):
        event_type = data.get("type")
        if "hook" in event_type:
            print(f"✅ Hook event correctly on claude_event channel: {event_type}")


@sio.on("hook:event")
async def on_hook_event(data):
    """Handler for hook:event events"""
    received_events["hook:event"].append(data)
    print(f"✅ Hook event on hook:event channel: {data.get('type', 'unknown')}")


async def emit_test_browser_log():
    """Emit a valid browser log"""
    browser_log = {
        "browser_id": f"test-browser-{datetime.now(timezone.utc).timestamp()}",
        "level": "INFO",
        "message": "Test browser console log - should appear in Browser Logs",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "url": "http://test.example.com",
    }

    print("\n📤 Emitting valid browser log...")
    await sio.emit("browser_log", browser_log)
    await asyncio.sleep(0.5)


async def emit_fake_hook_as_browser_log():
    """Try to emit a hook event as browser_log (should be rejected)"""
    fake_hook = {
        "type": "hook.pre_tool",
        "source": "hook",
        "tool_name": "TestTool",
        "message": "Fake hook event - should NOT appear in Browser Logs",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    print("\n📤 Emitting fake hook event on browser_log channel...")
    await sio.emit("browser_log", fake_hook)
    await asyncio.sleep(0.5)


async def main():
    """Main test function"""
    print("🧪 Browser Log Isolation Test")
    print("=" * 50)

    # Connect to the monitor server
    try:
        await sio.connect("http://localhost:8765")
        await asyncio.sleep(1)  # Wait for connection

        # Run tests
        await emit_test_browser_log()
        await emit_fake_hook_as_browser_log()

        # Wait a bit for events to be processed
        await asyncio.sleep(2)

        # Analyze results
        print("\n" + "=" * 50)
        print("📊 Test Results:")
        print(f"  - browser_log events received: {len(received_events['browser_log'])}")
        print(
            f"  - claude_event events received: {len(received_events['claude_event'])}"
        )
        print(f"  - hook:event events received: {len(received_events['hook:event'])}")

        # Check for contamination
        contaminated = False
        for event in received_events["browser_log"]:
            if isinstance(event, dict):
                if "browser_id" not in event:
                    print(f"  ❌ browser_log event without browser_id: {event}")
                    contaminated = True
                if "type" in event and "hook" in str(event.get("type", "")):
                    print(f"  ❌ Hook event on browser_log channel: {event}")
                    contaminated = True

        if not contaminated:
            print("  ✅ No hook contamination in browser_log channel!")

        print("\n✅ Test complete!")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await sio.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
