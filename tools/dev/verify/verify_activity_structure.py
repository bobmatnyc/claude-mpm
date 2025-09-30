#!/usr/bin/env python3
"""
Verification script to check Activity view structure after fixes.
"""

import time
from datetime import datetime

import socketio


def verify_activity_structure():
    print("🔍 MANUAL VERIFICATION CHECKLIST")
    print("=" * 60)
    print()
    print("Please verify the following in the dashboard:")
    print("🌐 http://localhost:8765 → Activity tab")
    print()
    print("✅ STRUCTURE VERIFICATION:")
    print("1. [] NO duplicate PM agent under PM Session rows")
    print("2. [] User instructions display with 💬 icon")
    print("3. [] TODOs show as expandable checklist with ☑️ icon")
    print("4. [] Individual TODO items show status icons (✅🔄⏳)")
    print("5. [] NO raw JSON visible in tree view")
    print("6. [] Each user instruction creates separate PM row")
    print("7. [] Agents grouped correctly under sessions")
    print("8. [] Tools grouped correctly under agents")
    print("9. [] Click items to view details in left pane")
    print("10. [] Expand/collapse functionality works")
    print()
    print("✅ EXPECTED SESSIONS:")
    print("• PM Session 1: Authentication system (6 TODOs, 3 agents)")
    print("• PM Session 2: Rate limiting (3 TODOs, 1 agent)")
    print("• PM Session 3: Bug fix (2 TODOs)")
    print()
    print("✅ AGENT TYPES TO VERIFY:")
    print("• 🔬 research agent (with WebFetch, Read, Grep tools)")
    print("• 🔒 security agent (with Read, Bash tools)")
    print("• 👷 engineer agent (with Write, Edit, MultiEdit tools)")
    print("• ⚙️ ops agent (with Bash, Write tools)")
    print()
    print("❌ ISSUES TO CHECK FOR:")
    print("• NO duplicate 'PM agent' entries under sessions")
    print('• NO raw JSON like {"content": "...", "status": "..."}')
    print("• NO broken icons or missing status indicators")
    print("• NO sessions without user instructions")
    print()
    print("🔧 INTERACTION TESTS:")
    print("• Expand PM Session → Should show user instruction + TODOs + agents")
    print("• Expand TODOs → Should show individual checklist items")
    print("• Click TODO item → Should show details in left pane (no raw JSON)")
    print("• Expand agent → Should show tools used by that agent")
    print("• Click agent → Should show agent details in left pane")
    print("• Click tool → Should show tool parameters (formatted, not raw JSON)")
    print()


def send_additional_test_data():
    """Send one more test session to verify real-time updates work."""

    sio = socketio.Client()

    @sio.event
    def connect():
        print("🔄 Sending additional test session...")

        session_id = "verify-session-004"

        # User instruction
        user_event = {
            "type": "user_prompt",
            "data": {"prompt": "Optimize database queries and add caching layer"},
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
        }
        sio.emit("hook_event", user_event)
        print("💬 Sent optimization instruction")

        # TODOs
        todo_event = {
            "type": "todo",
            "subtype": "updated",
            "data": {
                "todos": [
                    {
                        "content": "Profile slow database queries",
                        "activeForm": "Profiling database queries",
                        "status": "in_progress",
                    },
                    {
                        "content": "Implement Redis caching layer",
                        "activeForm": "Implementing Redis caching",
                        "status": "pending",
                    },
                ]
            },
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
        }
        sio.emit("hook_event", todo_event)
        print("☑️ Sent optimization TODOs")

        # QA agent
        agent_event = {
            "type": "subagent",
            "subtype": "started",
            "agent_name": "qa",
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
        }
        sio.emit("hook_event", agent_event)
        print("🤖 Sent QA agent")

        # QA tools
        qa_tools = [
            (
                "Bash",
                {
                    "command": "npm run test:performance",
                    "description": "Run performance tests",
                },
            ),
            ("Read", {"file_path": "/logs/slow_queries.log", "limit": 100}),
        ]

        for tool_name, params in qa_tools:
            tool_event = {
                "hook_event_name": "PreToolUse",
                "tool_name": tool_name,
                "tool_parameters": params,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
            }
            sio.emit("hook_event", tool_event)
            print(f"  🔧 Sent {tool_name} tool")
            time.sleep(0.2)

        print("✅ Additional test session sent")
        print("📊 Check dashboard for new PM Session 4: Optimization")

        time.sleep(2)
        sio.disconnect()

    try:
        sio.connect("http://localhost:8765")
        sio.wait()
    except Exception as e:
        print(f"❌ Could not send additional test data: {e}")


if __name__ == "__main__":
    print("🧪 Activity Structure Verification Tool")
    print("=" * 60)

    # Send additional test data
    send_additional_test_data()
    print()

    # Show verification checklist
    verify_activity_structure()

    print("🎯 SUMMARY OF FIXES APPLIED:")
    print("=" * 60)
    print("✅ 1. Removed duplicate PM agent creation in processEvent")
    print("✅ 2. Added user instruction processing with 💬 icon")
    print("✅ 3. Implemented TODO checklist with ☑️ icon and expansion")
    print("✅ 4. Added proper status icons (✅🔄⏳) for TODO items")
    print("✅ 5. Implemented clean data parsing (no raw JSON display)")
    print("✅ 6. Ensured separate PM rows for each user instruction")
    print("✅ 7. Fixed agent/tool hierarchy and grouping")
    print("✅ 8. Added click handlers for item details display")
    print("✅ 9. Implemented expand/collapse for all tree levels")
    print("✅ 10. Added proper data formatting in left pane")
    print()
    print("🚀 Open dashboard and verify all items above!")
