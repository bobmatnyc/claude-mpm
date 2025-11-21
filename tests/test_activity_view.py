#!/usr/bin/env python3
"""
Test script for the new linear tree Activity view.
Simulates multiple PM sessions with todos, agents, and tools.
"""

import json
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone

import socketio


def generate_session_id():
    """Generate a unique session ID"""
    return f"session-{str(uuid.uuid4())[:8]}"


def create_test_session(session_num, base_time):
    """Create a test session with realistic data"""
    session_id = generate_session_id()

    sessions_data = [
        {
            "name": "Authentication System Refactor",
            "todos": [
                {
                    "content": "Research existing authentication patterns",
                    "status": "completed",
                },
                {"content": "Design new authentication flow", "status": "completed"},
                {"content": "Implement JWT token system", "status": "in_progress"},
                {"content": "Update user registration flow", "status": "pending"},
                {"content": "Write comprehensive tests", "status": "pending"},
            ],
            "agents": ["research", "architect", "engineer", "qa"],
        },
        {
            "name": "Dashboard Performance Optimization",
            "todos": [
                {
                    "content": "Profile dashboard loading performance",
                    "status": "completed",
                },
                {"content": "Optimize API response times", "status": "completed"},
                {"content": "Implement caching layer", "status": "in_progress"},
                {"content": "Update frontend components", "status": "pending"},
            ],
            "agents": ["performance", "backend", "frontend"],
        },
        {
            "name": "Security Audit Implementation",
            "todos": [
                {
                    "content": "Review codebase for security vulnerabilities",
                    "status": "completed",
                },
                {"content": "Implement input validation", "status": "in_progress"},
                {"content": "Add rate limiting", "status": "pending"},
                {"content": "Update security documentation", "status": "pending"},
            ],
            "agents": ["security", "engineer", "documentation"],
        },
    ]

    # Select session data based on session number
    session_data = sessions_data[session_num % len(sessions_data)]

    return {
        "session_id": session_id,
        "name": session_data["name"],
        "todos": session_data["todos"],
        "agents": session_data["agents"],
        "start_time": base_time + timedelta(minutes=session_num * 30),
    }


def main():
    print("🧪 Starting Activity View Test")
    print("=" * 50)

    sio = socketio.Client(logger=False, engineio_logger=False)

    @sio.event
    def connect():
        print("✅ Connected to dashboard")

        # Generate base time for realistic timestamps
        base_time = datetime.now(timezone.utc) - timedelta(hours=2)

        # Create multiple test sessions
        sessions = []
        for i in range(3):
            session = create_test_session(i, base_time)
            sessions.append(session)
            print(f"📝 Created session {i + 1}: {session['name']}")

        print("\n🚀 Sending test events...")

        # Send events for each session
        for i, session in enumerate(sessions):
            print(f"\n📊 Processing Session {i + 1}: {session['name']}")

            # Send PM session start event
            pm_start_event = {
                "type": "session",
                "subtype": "started",
                "data": {
                    "session_id": session["session_id"],
                    "session_name": session["name"],
                },
                "timestamp": session["start_time"].isoformat(),
                "session_id": session["session_id"],
            }
            sio.emit("hook_event", pm_start_event)
            print("  ✓ Sent PM session start")

            # Send TodoWrite event
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
                "timestamp": (session["start_time"] + timedelta(minutes=5)).isoformat(),
                "session_id": session["session_id"],
            }
            sio.emit("hook_event", todo_event)
            print(f"  ✓ Sent {len(session['todos'])} todos")

            # Send agent events and tools
            for j, agent in enumerate(session["agents"]):
                agent_start_time = session["start_time"] + timedelta(
                    minutes=10 + j * 15
                )

                # Send subagent started event
                agent_event = {
                    "type": "subagent",
                    "subtype": "started",
                    "agent_name": agent,
                    "session_id": session["session_id"],
                    "timestamp": agent_start_time.isoformat(),
                }
                sio.emit("hook_event", agent_event)

                # Send tool events for each agent
                tools_for_agent = {
                    "research": ["Read", "Grep", "WebSearch"],
                    "architect": ["Read", "Write", "Edit"],
                    "engineer": ["Write", "Edit", "Bash"],
                    "qa": ["Read", "Bash", "Grep"],
                    "performance": ["Read", "Bash", "WebFetch"],
                    "backend": ["Edit", "Write", "Bash"],
                    "frontend": ["Edit", "Write", "Read"],
                    "security": ["Grep", "Read", "Bash"],
                    "documentation": ["Read", "Write", "Edit"],
                }

                agent_tools = tools_for_agent.get(agent, ["Read", "Write"])

                for k, tool in enumerate(agent_tools):
                    tool_time = agent_start_time + timedelta(minutes=k * 2)

                    # Tool parameters based on tool type
                    tool_params = {
                        "Read": {"file_path": f"/src/modules/{agent}_module.py"},
                        "Write": {
                            "file_path": f"/src/output/{agent}_output.py",
                            "content": "# Generated code",
                        },
                        "Edit": {
                            "file_path": f"/src/config/{agent}_config.py",
                            "old_string": "old_value",
                            "new_string": "new_value",
                        },
                        "Grep": {"pattern": f"{agent}_pattern", "path": "/src"},
                        "Bash": {"command": f"pytest tests/test_{agent}.py"},
                        "WebSearch": {"query": f"{agent} best practices"},
                        "WebFetch": {
                            "url": f"https://docs.example.com/{agent}",
                            "prompt": "Extract key information",
                        },
                    }

                    tool_event = {
                        "hook_event_name": "PreToolUse",
                        "tool_name": tool,
                        "tool_parameters": tool_params.get(tool, {"param": "value"}),
                        "session_id": session["session_id"],
                        "timestamp": tool_time.isoformat(),
                    }
                    sio.emit("hook_event", tool_event)

                print(f"  ✓ Sent {agent} agent with {len(agent_tools)} tools")

            # Send session completion event
            completion_time = session["start_time"] + timedelta(hours=1)
            session_end_event = {
                "type": "session",
                "subtype": "completed",
                "data": {
                    "session_id": session["session_id"],
                    "session_name": session["name"],
                },
                "timestamp": completion_time.isoformat(),
                "session_id": session["session_id"],
            }
            sio.emit("hook_event", session_end_event)
            print("  ✓ Sent session completion")

            time.sleep(0.5)  # Small delay between sessions

        print(f"\n✅ Successfully sent events for {len(sessions)} PM sessions!")
        print("\n📋 Test Summary:")
        print(f"  • Sessions created: {len(sessions)}")
        print(f"  • Total todos: {sum(len(s['todos']) for s in sessions)}")
        print(f"  • Total agents: {sum(len(s['agents']) for s in sessions)}")
        print(
            f"  • Total tools: {sum(len(tools_for_agent.get(agent, ['Read', 'Write'])) for s in sessions for agent in s['agents'])}"
        )

        print("\n🌐 Now open http://localhost:8765 and check the Activity tab!")
        print("   Features to test:")
        print("   ✓ Project root display with session count")
        print("   ✓ PM session grouping with expand/collapse")
        print("   ✓ TODO list with state indicators")
        print("   ✓ Agent hierarchy under todos")
        print("   ✓ Tool nesting under agents")
        print("   ✓ Session filtering dropdown")
        print("   ✓ Statistics display")

        time.sleep(3)
        sio.disconnect()

    @sio.event
    def connect_error(data):
        print(f"❌ Connection failed: {data}")

    @sio.event
    def disconnect():
        print("📡 Disconnected from dashboard")

    try:
        print("🔗 Connecting to dashboard...")
        sio.connect("http://localhost:8765")
        sio.wait()
    except Exception as e:
        print(f"❌ Error connecting to dashboard: {e}")
        print("\n💡 Make sure the dashboard is running:")
        print("   ./scripts/claude-mpm dashboard start --background")
        sys.exit(1)


# Add tools mapping at module level
tools_for_agent = {
    "research": ["Read", "Grep", "WebSearch"],
    "architect": ["Read", "Write", "Edit"],
    "engineer": ["Write", "Edit", "Bash"],
    "qa": ["Read", "Bash", "Grep"],
    "performance": ["Read", "Bash", "WebFetch"],
    "backend": ["Edit", "Write", "Bash"],
    "frontend": ["Edit", "Write", "Read"],
    "security": ["Grep", "Read", "Bash"],
    "documentation": ["Read", "Write", "Edit"],
}

if __name__ == "__main__":
    main()
