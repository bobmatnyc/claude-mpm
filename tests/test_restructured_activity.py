# test_restructured_activity.py
import time
from datetime import UTC, datetime, timezone

import socketio

sio = socketio.Client()


@sio.event
def connect():
    print("Connected - Testing restructured Activity view")

    session_id = "restructured-test-001"

    # Send TODO events (should appear under PM agent)
    todo_event = {
        "type": "todo",
        "subtype": "updated",
        "data": {
            "todos": [
                {
                    "content": "Research existing patterns",
                    "activeForm": "Researching patterns",
                    "status": "completed",
                },
                {
                    "content": "Design new architecture",
                    "activeForm": "Designing architecture",
                    "status": "in_progress",
                },
                {
                    "content": "Implement solution",
                    "activeForm": "Implementing solution",
                    "status": "in_progress",
                },
                {
                    "content": "Write tests",
                    "activeForm": "Writing tests",
                    "status": "pending",
                },
                {
                    "content": "Update documentation",
                    "activeForm": "Updating documentation",
                    "status": "pending",
                },
            ]
        },
        "timestamp": datetime.now(UTC).isoformat(),
        "session_id": session_id,
    }
    sio.emit("hook_event", todo_event)
    print("✅ Sent 5 TODOs (should appear as TodoWrite tool)")
    time.sleep(1)

    # Send multiple agent events (each should appear only once)
    agents = ["research", "engineer", "qa", "documentation"]

    for agent_name in agents:
        # Start agent
        agent_event = {
            "type": "subagent",
            "subtype": "started",
            "agent_name": agent_name,
            "session_id": session_id,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        sio.emit("hook_event", agent_event)
        print(f"✅ Started {agent_name} agent")

        # Send multiple tools for each agent
        if agent_name == "research":
            tools = [
                ("Read", {"file_path": "/src/patterns.js"}),
                ("Grep", {"pattern": "TODO", "path": "/src"}),
                ("WebFetch", {"url": "https://example.com/docs"}),
            ]
        elif agent_name == "engineer":
            tools = [
                ("Write", {"file_path": "/src/new_feature.js"}),
                ("Edit", {"file_path": "/src/main.js", "old": "old", "new": "new"}),
                ("Bash", {"command": "npm install"}),
            ]
        elif agent_name == "qa":
            tools = [
                ("Bash", {"command": "npm test"}),
                ("Read", {"file_path": "/test/results.log"}),
            ]
        else:  # documentation
            tools = [
                ("Write", {"file_path": "/docs/README.md"}),
                ("Edit", {"file_path": "/docs/API.md", "old": "v1", "new": "v2"}),
            ]

        for tool_name, params in tools:
            tool_event = {
                "hook_event_name": "PreToolUse",
                "tool_name": tool_name,
                "tool_parameters": params,
                "session_id": session_id,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            sio.emit("hook_event", tool_event)
            print(f"  🔧 Sent {tool_name} tool for {agent_name}")
            time.sleep(0.2)

    # Test duplicate agent (should NOT create new entry)
    print("\n🧪 Testing duplicate agent handling...")
    duplicate_event = {
        "type": "subagent",
        "subtype": "started",
        "agent_name": "research",  # Already exists
        "session_id": session_id,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    sio.emit("hook_event", duplicate_event)
    print("✅ Sent duplicate research agent (should NOT create new node)")

    # Send another tool for existing agent
    tool_event = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Read",
        "tool_parameters": {"file_path": "/src/duplicate_test.js"},
        "session_id": session_id,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    sio.emit("hook_event", tool_event)
    print("✅ Sent additional tool for research agent")

    print("\n📊 Expected structure:")
    print("📁 Project Root")
    print("└── 🎯 PM Session")
    print("    ├── 🎯 PM Agent")
    print("    │   └── 📝 TodoWrite (2 completed, 2 in_progress, 1 pending)")
    print("    │       ├── ✅ Research existing patterns")
    print("    │       ├── 🔄 Design new architecture")
    print("    │       └── ... (3 more todos)")
    print("    ├── 🔬 research agent (4 tools)")
    print("    ├── 👷 engineer agent (3 tools)")
    print("    ├── 🧪 qa agent (2 tools)")
    print("    └── 📚 documentation agent (2 tools)")

    print("\n🔍 Check that:")
    print("1. Each agent appears ONLY ONCE")
    print("2. TodoWrite appears under PM Agent")
    print("3. All tools appear under correct agents")
    print("4. No duplicate agents created")

    time.sleep(10)
    sio.disconnect()


try:
    sio.connect("http://localhost:8765")
    sio.wait()
except Exception as e:
    print(f"Error: {e}")
