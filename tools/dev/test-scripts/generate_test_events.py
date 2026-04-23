#!/usr/bin/env python3
"""
Generate test events for Claude MPM Dashboard
This will create file operations, tool calls, and agent events
"""

import asyncio
from datetime import datetime

import socketio

# Create a Socket.IO client
sio = socketio.AsyncClient()


async def connect_and_send():
    """Connect to the dashboard and send test events"""
    try:
        # Connect to the dashboard WebSocket server
        print("Connecting to dashboard WebSocket on port 8765...")
        await sio.connect("http://localhost:8765")
        print("✅ Connected successfully!")

        # Wait a moment for connection to stabilize
        await asyncio.sleep(1)

        # Create a batch of test events
        test_events = []
        base_time = datetime.now().isoformat()

        # 1. File Read operation
        test_events.append(
            {
                "type": "hook",
                "subtype": "pre_tool",
                "tool_name": "Read",
                "tool_parameters": {
                    "file_path": "/Users/masa/Projects/claude-mpm/README.md"
                },
                "data": {
                    "tool_name": "Read",
                    "tool_parameters": {
                        "file_path": "/Users/masa/Projects/claude-mpm/README.md"
                    },
                },
                "timestamp": base_time,
                "session_id": "test-session-001",
                "agent_type": "Engineer Agent",
                "working_directory": "/Users/masa/Projects/claude-mpm",
            }
        )

        # 2. File Write operation
        test_events.append(
            {
                "type": "hook",
                "subtype": "pre_tool",
                "tool_name": "Write",
                "tool_parameters": {
                    "file_path": "/Users/masa/Projects/claude-mpm/test_output.txt",
                    "content": "Test content",
                },
                "data": {
                    "tool_name": "Write",
                    "tool_parameters": {
                        "file_path": "/Users/masa/Projects/claude-mpm/test_output.txt"
                    },
                },
                "timestamp": base_time,
                "session_id": "test-session-001",
                "agent_type": "Engineer Agent",
            }
        )

        # 3. File Edit operation
        test_events.append(
            {
                "type": "hook",
                "subtype": "pre_tool",
                "tool_name": "Edit",
                "tool_parameters": {
                    "file_path": "/Users/masa/Projects/claude-mpm/src/main.py",
                    "old_string": "old code",
                    "new_string": "new code",
                },
                "data": {
                    "tool_name": "Edit",
                    "tool_parameters": {
                        "file_path": "/Users/masa/Projects/claude-mpm/src/main.py"
                    },
                },
                "timestamp": base_time,
                "session_id": "test-session-001",
                "agent_type": "Engineer Agent",
            }
        )

        # 4. Bash command (file operation)
        test_events.append(
            {
                "type": "hook",
                "subtype": "pre_tool",
                "tool_name": "Bash",
                "tool_parameters": {
                    "command": "ls -la /Users/masa/Projects/claude-mpm"
                },
                "data": {
                    "tool_name": "Bash",
                    "tool_parameters": {
                        "command": "ls -la /Users/masa/Projects/claude-mpm"
                    },
                },
                "timestamp": base_time,
                "session_id": "test-session-001",
                "agent_type": "QA Agent",
            }
        )

        # 5. Grep search operation
        test_events.append(
            {
                "type": "hook",
                "subtype": "pre_tool",
                "tool_name": "Grep",
                "tool_parameters": {
                    "pattern": "TODO",
                    "path": "/Users/masa/Projects/claude-mpm",
                },
                "data": {
                    "tool_name": "Grep",
                    "tool_parameters": {
                        "pattern": "TODO",
                        "path": "/Users/masa/Projects/claude-mpm",
                    },
                },
                "timestamp": base_time,
                "session_id": "test-session-001",
                "agent_type": "Research Agent",
            }
        )

        # 6. Task delegation (non-file operation for Tools tab)
        test_events.append(
            {
                "type": "hook",
                "subtype": "pre_tool",
                "tool_name": "Task",
                "tool_parameters": {
                    "description": "Test task delegation",
                    "agent": "Engineer",
                },
                "data": {
                    "tool_name": "Task",
                    "tool_parameters": {"description": "Test task delegation"},
                },
                "timestamp": base_time,
                "session_id": "test-session-001",
                "agent_type": "PM",
            }
        )

        # Add corresponding post_tool events for each pre_tool
        post_events = []
        for event in test_events:
            post_event = {
                **event,
                "subtype": "post_tool",
                "success": True,
                "duration_ms": 150,
                "result": "Operation completed successfully",
            }
            post_events.append(post_event)

        # Combine all events
        all_events = test_events + post_events

        print(f"\n📤 Sending {len(all_events)} test events to dashboard...")

        # Send events to the dashboard
        await sio.emit("claude_event_batch", all_events)
        print("✅ Events sent successfully!")

        # Wait to see results
        await asyncio.sleep(2)

        print("\n📊 Dashboard should now show:")
        print(
            "  - Files tab: 5 file operations (README.md, test_output.txt, main.py, ls command, grep search)"
        )
        print("  - Tools tab: 6 tool calls (Read, Write, Edit, Bash, Grep, Task)")
        print("  - Agents tab: 3 agents (Engineer Agent, QA Agent, Research Agent)")
        print("  - File Tree tab: Same files as Files tab in tree format")

        # Disconnect
        await sio.disconnect()
        print("\n✅ Test complete! Check your dashboard at http://localhost:5173")

    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure the dashboard is running: claude-mpm monitor")
        print("2. Check that port 8765 is accessible")
        print("3. Try refreshing the dashboard page")


if __name__ == "__main__":
    print("Claude MPM Dashboard Test Event Generator")
    print("=" * 50)
    asyncio.run(connect_and_send())
