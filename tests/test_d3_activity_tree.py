#!/usr/bin/env python3
"""
D3.js Activity Tree Test Script
Tests the new linear graph tree implementation for the Activity view.
"""

import contextlib
import json
import time
from datetime import datetime, timedelta, timezone

import socketio


def main():
    sio = socketio.Client()

    @sio.event
    def connect():
        print("🔌 Connected to dashboard - sending D3 tree test data")

        # Create multiple sessions with varied data
        sessions = [
            {
                "id": "session-d3-001",
                "time": datetime.now(timezone.utc) - timedelta(hours=2),
                "todos": [
                    {"content": "Analyze D3 tree layouts", "status": "completed"},
                    {"content": "Implement linear tree", "status": "in_progress"},
                    {"content": "Add zoom and pan", "status": "pending"},
                ],
                "agents": ["research", "engineer", "qa"],
            },
            {
                "id": "session-d3-002",
                "time": datetime.now(timezone.utc) - timedelta(hours=1),
                "todos": [
                    {"content": "Test D3 transitions", "status": "in_progress"},
                    {"content": "Optimize performance", "status": "pending"},
                ],
                "agents": ["qa", "engineer"],
            },
            {
                "id": "session-d3-003",
                "time": datetime.now(timezone.utc),
                "todos": [
                    {"content": "Document D3 implementation", "status": "pending"}
                ],
                "agents": ["documentation"],
            },
        ]

        for session in sessions:
            print(f"\n📤 Processing session: {session['id']}")

            # Send TODO events
            todo_event = {
                "type": "todo",
                "subtype": "updated",
                "data": {
                    "todos": [
                        {
                            "content": todo["content"],
                            "activeForm": f"Working on: {todo['content']}",
                            "status": todo["status"],
                        }
                        for todo in session["todos"]
                    ]
                },
                "timestamp": session["time"].isoformat(),
                "session_id": session["id"],
            }
            sio.emit("hook_event", todo_event)
            print(f"  ✅ Sent {len(session['todos'])} todos for {session['id']}")

            # Send agent and tool events
            for i, agent_name in enumerate(session["agents"]):
                # Agent start
                agent_event = {
                    "type": "subagent",
                    "subtype": "started",
                    "agent_name": agent_name,
                    "session_id": session["id"],
                    "timestamp": (
                        session["time"] + timedelta(seconds=i * 10)
                    ).isoformat(),
                }
                sio.emit("hook_event", agent_event)

                # Tool events for different agent types
                tools = {
                    "research": [
                        ("Read", {"file_path": "/src/d3_tree.js"}),
                        ("Grep", {"pattern": "d3.tree", "path": "/src"}),
                    ],
                    "engineer": [
                        (
                            "Write",
                            {
                                "file_path": "/src/new_tree.js",
                                "content": "// D3 tree implementation",
                            },
                        ),
                        (
                            "Edit",
                            {
                                "file_path": "/src/activity.js",
                                "old": "HTML tree",
                                "new": "D3 tree",
                            },
                        ),
                    ],
                    "qa": [
                        ("Bash", {"command": "npm test"}),
                        ("Bash", {"command": "npm run build"}),
                    ],
                    "documentation": [
                        (
                            "Write",
                            {
                                "file_path": "/docs/d3_tree.md",
                                "content": "# D3 Tree Documentation",
                            },
                        )
                    ],
                }

                if agent_name in tools:
                    for j, (tool_name, params) in enumerate(tools[agent_name]):
                        # Pre-tool event
                        tool_event = {
                            "hook_event_name": "PreToolUse",
                            "tool_name": tool_name,
                            "tool_parameters": params,
                            "session_id": session["id"],
                            "timestamp": (
                                session["time"] + timedelta(seconds=i * 10 + j * 2 + 1)
                            ).isoformat(),
                            "id": f"tool-{session['id']}-{i}-{j}",
                        }
                        sio.emit("hook_event", tool_event)

                        # Post-tool event (completion)
                        post_tool_event = {
                            "hook_event_name": "PostToolUse",
                            "tool_name": tool_name,
                            "tool_parameters": params,
                            "session_id": session["id"],
                            "timestamp": (
                                session["time"] + timedelta(seconds=i * 10 + j * 2 + 2)
                            ).isoformat(),
                            "id": f"tool-{session['id']}-{i}-{j}",
                            "result": f"Successfully executed {tool_name}",
                        }
                        sio.emit("hook_event", post_tool_event)

                # Agent stop
                agent_stop_event = {
                    "type": "subagent",
                    "subtype": "stopped",
                    "agent_name": agent_name,
                    "session_id": session["id"],
                    "timestamp": (
                        session["time"] + timedelta(seconds=i * 10 + 20)
                    ).isoformat(),
                }
                sio.emit("hook_event", agent_stop_event)

                print(
                    f"  🤖 Sent {agent_name} agent with {len(tools.get(agent_name, []))} tools"
                )

            time.sleep(0.8)  # Small delay between sessions

        print("\n🎉 Test data sent successfully!")
        print("\n🧪 D3 Activity Tree Testing Checklist:")
        print("=" * 60)
        print("1. ✅ Open http://localhost:8765 → Activity tab")
        print("2. 🔍 Verify D3 tree renders with circles and connecting lines")
        print("3. 🖱️ Click circles to expand/collapse (smooth 750ms transitions)")
        print("4. 📝 Click node labels to view data in left pane")
        print("5. 🔎 Use zoom (mouse scroll) and pan (drag background)")
        print("6. 🔄 Test 'Reset Zoom' button functionality")
        print("7. 📋 Use session filter dropdown to show/hide sessions")
        print("8. 🎨 Check node colors:")
        print("   - Blue: Project root")
        print("   - Green: Sessions")
        print("   - Orange: Todos")
        print("   - Purple: Agents")
        print("   - Red: Tools")
        print("9. 🖱️ Test hover tooltips on nodes")
        print("10. 🎯 Check selected node highlighting")
        print("\n📊 Expected Tree Structure:")
        print("Project Root")
        print("├── Session 1 (2 hours ago) - 3 todos, 3 agents")
        print("│   ├── TODO: Analyze D3 tree layouts [completed]")
        print("│   ├── TODO: Implement linear tree [in_progress]")
        print("│   │   ├── AGENT: research")
        print("│   │   │   ├── TOOL: Read")
        print("│   │   │   └── TOOL: Grep")
        print("│   │   ├── AGENT: engineer")
        print("│   │   │   ├── TOOL: Write")
        print("│   │   │   └── TOOL: Edit")
        print("│   │   └── AGENT: qa")
        print("│   │       ├── TOOL: Bash (npm test)")
        print("│   │       └── TOOL: Bash (npm run build)")
        print("│   └── TODO: Add zoom and pan [pending]")
        print("├── Session 2 (1 hour ago) - 2 todos, 2 agents")
        print("└── Session 3 (now) - 1 todo, 1 agent")
        print("\n⏱️  Waiting 15 seconds before disconnecting...")

        time.sleep(15)
        print("🔌 Disconnecting from dashboard")
        sio.disconnect()

    @sio.event
    def disconnect():
        print("🔌 Disconnected from dashboard")

    @sio.event
    def connect_error(data):
        print(f"❌ Connection error: {data}")

    try:
        print("🚀 Starting D3 Activity Tree test...")
        print("🔌 Connecting to http://localhost:8765...")
        sio.connect("http://localhost:8765")
        sio.wait()
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
        sio.disconnect()
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        with contextlib.suppress(Exception):
            sio.disconnect()


if __name__ == "__main__":
    main()
