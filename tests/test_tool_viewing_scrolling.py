# test_tool_viewing_scrolling.py
import time
from datetime import datetime, timezone

import socketio

sio = socketio.Client()


@sio.event
def connect():
    print("Connected - Testing tool viewing and scrolling")

    # Create multiple sessions to test scrolling
    for session_num in range(1, 4):
        session_id = f"scroll-test-{session_num:03d}"

        # User instruction
        user_event = {
            "type": "user_prompt",
            "data": {
                "prompt": f"Test session {session_num}: Implement feature {session_num}"
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
        }
        sio.emit("hook_event", user_event)
        print(f"💬 Sent user instruction for session {session_num}")

        # TODOs
        todo_event = {
            "type": "todo",
            "subtype": "updated",
            "data": {
                "todos": [
                    {
                        "content": f"Task {i} for session {session_num}",
                        "activeForm": f"Working on task {i}",
                        "status": ["completed", "in_progress", "pending"][i % 3],
                    }
                    for i in range(1, 4)
                ]
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
        }
        sio.emit("hook_event", todo_event)

        # Multiple agents with tools to test scrolling
        agents = ["research", "engineer", "qa", "documentation", "security"]

        for agent_name in agents[: session_num + 1]:  # Varying number of agents
            agent_event = {
                "type": "subagent",
                "subtype": "started",
                "agent_name": agent_name,
                "session_id": session_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            sio.emit("hook_event", agent_event)

            # Add tools with rich parameters to test data viewer
            tools = [
                (
                    "Read",
                    {
                        "file_path": f"/src/{agent_name}/module_{session_num}.js",
                        "limit": 500,
                        "offset": 0,
                    },
                ),
                (
                    "Write",
                    {
                        "file_path": f"/docs/{agent_name}_doc_{session_num}.md",
                        "content": f"# Documentation for {agent_name}\\n\\nThis is a long content string that should be properly displayed in the data viewer when the tool is clicked. It contains multiple lines and should be formatted nicely.",
                    },
                ),
                (
                    "Bash",
                    {
                        "command": f"npm test -- --coverage --agent={agent_name}",
                        "timeout": 30000,
                        "working_dir": f"/project/session_{session_num}",
                    },
                ),
                (
                    "Edit",
                    {
                        "file_path": f"/src/config_{session_num}.json",
                        "old_string": '{"enabled": false}',
                        "new_string": '{"enabled": true, "agent": "{agent_name}"}',
                        "replace_all": True,
                    },
                ),
            ]

            for tool_name, params in tools[:2]:  # 2 tools per agent
                tool_event = {
                    "hook_event_name": "PreToolUse",
                    "tool_name": tool_name,
                    "tool_parameters": params,
                    "session_id": session_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                sio.emit("hook_event", tool_event)
                print(f"  🔧 Sent {tool_name} for {agent_name}")
                time.sleep(0.1)

        time.sleep(0.5)

    print("\\n✅ Test data sent!")
    print("\\n🔍 Testing checklist:")
    print("1. Open http://localhost:8765 → Activity tab")
    print("2. Verify Activity tree is SCROLLABLE (3 sessions should require scrolling)")
    print("3. Check tools are NOT expandable (no arrows)")
    print("4. Click on any tool - should show details in LEFT PANE")
    print("5. Verify data viewer shows:")
    print("   - Tool icon and name")
    print("   - Status badge")
    print("   - Formatted parameters (not raw JSON)")
    print("   - Long text properly truncated/scrollable")
    print("6. Test clicking different tools")
    print("7. Verify scrolling is smooth")

    time.sleep(10)
    sio.disconnect()


try:
    sio.connect("http://localhost:8765")
    sio.wait()
except Exception as e:
    print(f"Error: {e}")
