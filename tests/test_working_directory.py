#!/usr/bin/env python3
"""
Test script to verify dynamic working directory detection
"""

import asyncio
import os
from pathlib import Path

import socketio


async def test_working_directory():
    """Test that the server uses the actual current working directory"""

    # Get the actual current working directory
    actual_cwd = os.getcwd()
    print(f"Current working directory: {actual_cwd}")

    # Create a Socket.IO client
    sio = socketio.AsyncClient()

    received_event = False

    @sio.on("connect")
    async def on_connect():
        print("Connected to server")
        # Emit a test event to trigger working directory detection
        await sio.emit(
            "claude_event",
            {
                "type": "test",
                "subtype": "working_dir_check",
                "data": {
                    "cwd": actual_cwd,
                    "working_directory": actual_cwd,
                    "message": "Testing working directory detection",
                },
            },
        )

    @sio.on("hook:event")
    async def on_hook_event(data):
        nonlocal received_event
        received_event = True
        print("\nReceived hook event:")
        if "data" in data and "working_directory" in data["data"]:
            wd = data["data"]["working_directory"]
            print(f"  Working directory in event: {wd}")
            if wd == actual_cwd:
                print("  ✅ SUCCESS: Working directory matches actual CWD")
            else:
                print("  ⚠️ WARNING: Working directory doesn't match")
                print(f"     Expected: {actual_cwd}")
                print(f"     Got: {wd}")

    @sio.on("claude_event")
    async def on_claude_event(data):
        print("\nReceived claude_event:")
        if "data" in data:
            if "working_directory" in data["data"]:
                print(f"  Working directory: {data['data']['working_directory']}")
            if "cwd" in data["data"]:
                print(f"  CWD: {data['data']['cwd']}")

    try:
        print("\nConnecting to Socket.IO server at http://localhost:8765...")
        await sio.connect("http://localhost:8765")

        # Wait a moment for events
        await asyncio.sleep(2)

        # Test from different directory
        test_dir = Path.home()
        print(f"\nChanging to directory: {test_dir}")
        os.chdir(test_dir)

        # Send another event from new directory
        await sio.emit(
            "claude_event",
            {
                "type": "test",
                "subtype": "working_dir_check_2",
                "data": {
                    "cwd": str(test_dir),
                    "working_directory": str(test_dir),
                    "message": "Testing from different directory",
                },
            },
        )

        await asyncio.sleep(2)

        # Change back
        os.chdir(actual_cwd)

        await sio.disconnect()

        if received_event:
            print("\n✅ Working directory events are being processed")
        else:
            print(
                "\n⚠️ No events received - check if server is processing events correctly"
            )

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\nMake sure the Socket.IO server is running:")
        print("  ./scripts/claude-mpm monitor --start")


if __name__ == "__main__":
    print("=" * 60)
    print("Dynamic Working Directory Test")
    print("=" * 60)
    print("\nThis script verifies that the dashboard uses the actual")
    print("current working directory instead of a hardcoded path.\n")

    asyncio.run(test_working_directory())
