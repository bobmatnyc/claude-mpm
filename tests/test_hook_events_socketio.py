#!/usr/bin/env python3
"""Test if hook events are being sent to Socket.IO server"""

import subprocess
import sys
import time


def test_hook_events():
    print("Testing Claude hook events with Socket.IO server...")

    # Check if Socket.IO server is running
    status_result = subprocess.run(
        ["python", "src/claude_mpm/scripts/socketio_daemon.py", "status"],
        capture_output=True,
        text=True,
        check=False,
    )

    if "is running" not in status_result.stdout:
        print("❌ Socket.IO server is not running. Starting it...")
        subprocess.run(
            ["python", "src/claude_mpm/scripts/socketio_daemon.py", "start"],
            check=False,
        )
        time.sleep(2)
    else:
        print("✅ Socket.IO server is running")

    # Create a test hook data structure
    {
        "action": "hook",
        "hook": {
            "type": "test",
            "name": "test_hook",
            "data": {
                "message": "Testing Socket.IO hook broadcast",
                "timestamp": time.time(),
            },
        },
    }

    # Test direct hook handler
    print("\nTesting direct hook handler...")
    sys.path.insert(0, "src")

    try:
        from claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()
        print("✅ Hook handler created")

        # Test emitting an event
        test_event = {
            "type": "user_prompt_submitted",
            "prompt": "Test prompt for Socket.IO",
            "timestamp": time.time(),
        }

        handler._handle_prompt_fast(test_event)
        print("✅ Sent test prompt event")

        # Test tool event
        tool_event = {
            "type": "tool_use",
            "tool_name": "test_tool",
            "tool_input": {"param": "value"},
            "timestamp": time.time(),
        }

        handler._handle_pre_tool_fast(tool_event)
        print("✅ Sent test tool event")

    except Exception as e:
        print(f"❌ Error testing hook handler: {e}")
        import traceback

        traceback.print_exc()

    # Check server logs
    print("\nChecking server logs...")
    try:
        with open("/Users/masa/.claude-mpm/socketio-server.log") as f:
            lines = f.readlines()
            recent_lines = lines[-20:]
            print("Recent server log entries:")
            for line in recent_lines:
                if "event" in line.lower() or "hook" in line.lower():
                    print(f"  {line.strip()}")
    except Exception as e:
        print(f"Could not read server logs: {e}")


if __name__ == "__main__":
    test_hook_events()
