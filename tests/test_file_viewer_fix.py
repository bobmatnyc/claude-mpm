#!/usr/bin/env python3
"""
Test script to verify file viewer fixes for bash command parsing.

This script tests:
1. Proper extraction of file paths from bash commands with flags
2. Correct display of file details instead of [object Object]
"""

import time

import socketio

# Create a Socket.IO client
sio = socketio.Client()


@sio.event
def connect():
    print("✅ Connected to Socket.IO server")


@sio.event
def disconnect():
    print("❌ Disconnected from Socket.IO server")


def emit_bash_event(command, file_path_expected):
    """Emit a bash tool event with the given command."""
    print(f"\n📤 Testing command: {command}")
    print(f"   Expected file path: {file_path_expected}")

    # Emit pre_tool event
    pre_event = {
        "type": "hook",
        "subtype": "pre_tool",
        "tool_name": "Bash",
        "tool_parameters": {"command": command},
        "timestamp": time.time() * 1000,
        "session_id": "test-session",
        "agent_type": "Engineer",
    }

    sio.emit("event", pre_event)
    time.sleep(0.1)

    # Emit post_tool event with results
    post_event = {
        "type": "hook",
        "subtype": "post_tool",
        "tool_name": "Bash",
        "tool_parameters": {"command": command},
        "result_summary": {
            "has_output": True,
            "output_preview": f"Sample output from {command}",
            "exit_code": 0,
        },
        "success": True,
        "exit_code": 0,
        "duration_ms": 45,
        "timestamp": time.time() * 1000,
        "session_id": "test-session",
        "agent_type": "Engineer",
    }

    sio.emit("event", post_event)
    time.sleep(0.1)


def main():
    print("🧪 File Viewer Fix Test Script")
    print("=" * 50)

    try:
        # Connect to Socket.IO server
        print("🔌 Connecting to Socket.IO server at http://localhost:8765...")
        sio.connect("http://localhost:8765")

        # Wait for connection
        time.sleep(1)

        # Test various bash commands with flags
        test_cases = [
            # Command with numeric flag
            (
                "tail -50 /Users/masa/Projects/claude-mpm/.claude-mpm/socketio-server.log",
                "/Users/masa/Projects/claude-mpm/.claude-mpm/socketio-server.log",
            ),
            # Command with -n flag
            ("head -n 100 /var/log/system.log", "/var/log/system.log"),
            # Command without flags
            ("cat /etc/hosts", "/etc/hosts"),
            # Command with multiple flags
            (
                "grep -r -i 'error' /Users/masa/Projects/logs/app.log",
                "/Users/masa/Projects/logs/app.log",
            ),
            # Command with flag and value
            ("tail -f /var/log/messages", "/var/log/messages"),
            # Complex command with pipes (should extract first file)
            ("cat /tmp/data.txt | grep 'pattern'", "/tmp/data.txt"),
        ]

        print("\n📊 Running test cases...")
        for command, expected_path in test_cases:
            emit_bash_event(command, expected_path)
            time.sleep(0.5)

        print("\n✅ All test events sent!")
        print("\n📋 Check the dashboard to verify:")
        print("1. Files tab shows correct file paths (not '-50' or other flags)")
        print("2. File details show the full command and proper formatting")
        print("3. No '[object Object]' appears in the details view")

        # Keep connection alive for a bit
        print("\n⏳ Keeping connection alive for 5 seconds...")
        time.sleep(5)

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if sio.connected:
            sio.disconnect()
        print("\n🏁 Test complete!")


if __name__ == "__main__":
    main()
