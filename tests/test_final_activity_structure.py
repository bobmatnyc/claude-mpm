#!/usr/bin/env python3
"""
Comprehensive test script for final Activity view structure verification.

Tests:
1. No duplicate PM agent under PM Session
2. User instructions displayed with 💬 icon
3. TODOs shown as checklist with ☑️ icon
4. No raw JSON in tree view
5. Clean data parsing and display
"""

import json
import time
from datetime import datetime, timezone

import socketio

# Setup the socket client
sio = socketio.Client()


@sio.event
def connect():
    print("✅ Connected - Testing final Activity structure")
    print("=" * 70)

    # Test Session 1 - Complete workflow
    session1 = "final-test-session-001"

    print("🎯 Session 1: Complete Authentication Workflow")
    print("-" * 50)

    # Send user instruction
    user_event1 = {
        "type": "user_prompt",
        "data": {
            "prompt": "Build a secure authentication system with JWT tokens, refresh tokens, and proper session management"
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session1,
    }
    sio.emit("hook_event", user_event1)
    print("💬 Sent user instruction: 'Build authentication system'")
    time.sleep(0.5)

    # Send TODOs (should appear as checklist under session)
    todo_event1 = {
        "type": "todo",
        "subtype": "updated",
        "data": {
            "todos": [
                {
                    "content": "Research JWT best practices and security considerations",
                    "activeForm": "Researching JWT security",
                    "status": "completed",
                },
                {
                    "content": "Design authentication architecture with microservices",
                    "activeForm": "Designing auth architecture",
                    "status": "completed",
                },
                {
                    "content": "Implement JWT service with proper encryption",
                    "activeForm": "Implementing JWT service",
                    "status": "in_progress",
                },
                {
                    "content": "Add refresh token logic and blacklist management",
                    "activeForm": "Adding refresh token logic",
                    "status": "in_progress",
                },
                {
                    "content": "Write comprehensive authentication tests",
                    "activeForm": "Writing auth tests",
                    "status": "pending",
                },
                {
                    "content": "Set up session cleanup and monitoring",
                    "activeForm": "Setting up session monitoring",
                    "status": "pending",
                },
            ]
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session1,
    }
    sio.emit("hook_event", todo_event1)
    print("☑️ Sent TODO checklist (2 completed, 2 in_progress, 2 pending)")
    time.sleep(0.5)

    # Send multiple agents with various tools
    agents_data = [
        (
            "research",
            [
                (
                    "WebFetch",
                    {
                        "url": "https://jwt.io/introduction/",
                        "prompt": "Extract JWT best practices and security recommendations",
                    },
                ),
                ("Read", {"file_path": "/src/existing_auth.js", "limit": 50}),
                (
                    "Grep",
                    {
                        "pattern": "authentication",
                        "glob": "**/*.js",
                        "output_mode": "files_with_matches",
                    },
                ),
            ],
        ),
        (
            "security",
            [
                ("Read", {"file_path": "/config/security.yml"}),
                (
                    "Bash",
                    {
                        "command": "openssl rand -base64 32",
                        "description": "Generate secure JWT secret",
                    },
                ),
            ],
        ),
        (
            "engineer",
            [
                (
                    "Write",
                    {
                        "file_path": "/src/auth/jwt_service.js",
                        "content": "// JWT Service Implementation\nconst jwt = require('jsonwebtoken');\n\nclass JWTService {\n  // Implementation...\n}",
                    },
                ),
                (
                    "Edit",
                    {
                        "file_path": "/src/config/database.js",
                        "old_string": "const secret = 'dev-secret'",
                        "new_string": "const secret = process.env.JWT_SECRET",
                    },
                ),
                (
                    "MultiEdit",
                    {
                        "file_path": "/src/routes/auth.js",
                        "edits": [
                            {
                                "old_string": "// TODO: Add auth routes",
                                "new_string": "// Auth routes implementation",
                            },
                            {
                                "old_string": "app.get('/login')",
                                "new_string": "app.post('/login')",
                            },
                        ],
                    },
                ),
            ],
        ),
    ]

    for agent_name, tools in agents_data:
        # Start agent
        agent_event = {
            "type": "subagent",
            "subtype": "started",
            "agent_name": agent_name,
            "session_id": session1,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        sio.emit("hook_event", agent_event)
        print(f"🤖 Sent {agent_name} agent")

        # Send tools for this agent
        for tool_name, params in tools:
            tool_event = {
                "hook_event_name": "PreToolUse",
                "tool_name": tool_name,
                "tool_parameters": params,
                "session_id": session1,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            sio.emit("hook_event", tool_event)
            print(f"  🔧 Sent {tool_name} tool with params: {list(params.keys())}")
            time.sleep(0.2)

        time.sleep(0.3)

    print("\n" + "=" * 70)

    # Test Session 2 - New user instruction (should create new PM row)
    session2 = "final-test-session-002"

    print("🎯 Session 2: Rate Limiting Implementation")
    print("-" * 50)

    user_event2 = {
        "type": "user_prompt",
        "data": {
            "prompt": "Add rate limiting to prevent API abuse and implement DDoS protection with Redis"
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session2,
    }
    sio.emit("hook_event", user_event2)
    print("💬 Sent new user instruction (should create new PM row)")
    time.sleep(0.3)

    todo_event2 = {
        "type": "todo",
        "subtype": "updated",
        "data": {
            "todos": [
                {
                    "content": "Research rate limiting strategies and algorithms",
                    "activeForm": "Researching rate limiting strategies",
                    "status": "in_progress",
                },
                {
                    "content": "Implement Redis-based rate limiter with sliding window",
                    "activeForm": "Implementing Redis rate limiter",
                    "status": "pending",
                },
                {
                    "content": "Add DDoS protection middleware",
                    "activeForm": "Adding DDoS protection",
                    "status": "pending",
                },
            ]
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session2,
    }
    sio.emit("hook_event", todo_event2)
    print("☑️ Sent TODO checklist for session 2")

    # Add ops agent for session 2
    agent_event2 = {
        "type": "subagent",
        "subtype": "started",
        "agent_name": "ops",
        "session_id": session2,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    sio.emit("hook_event", agent_event2)
    print("🤖 Sent ops agent")

    # Add tools for ops agent
    ops_tools = [
        (
            "Bash",
            {
                "command": "docker run -d redis:alpine",
                "description": "Start Redis container",
            },
        ),
        (
            "Write",
            {
                "file_path": "/config/redis.yml",
                "content": "redis:\n  host: localhost\n  port: 6379\n  db: 0",
            },
        ),
    ]

    for tool_name, params in ops_tools:
        tool_event = {
            "hook_event_name": "PreToolUse",
            "tool_name": tool_name,
            "tool_parameters": params,
            "session_id": session2,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        sio.emit("hook_event", tool_event)
        print(f"  🔧 Sent {tool_name} tool")
        time.sleep(0.2)

    print("\n" + "=" * 70)

    # Test Session 3 - Quick single instruction
    session3 = "final-test-session-003"

    print("🎯 Session 3: Simple Bug Fix")
    print("-" * 50)

    user_event3 = {
        "type": "user_prompt",
        "data": {"prompt": "Fix the memory leak in user session cleanup"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session3,
    }
    sio.emit("hook_event", user_event3)
    print("💬 Sent simple bug fix instruction")

    # Just one TODO for this session
    todo_event3 = {
        "type": "todo",
        "subtype": "updated",
        "data": {
            "todos": [
                {
                    "content": "Identify memory leak in session cleanup code",
                    "activeForm": "Identifying memory leak",
                    "status": "completed",
                },
                {
                    "content": "Fix memory leak and add monitoring",
                    "activeForm": "Fixing memory leak",
                    "status": "in_progress",
                },
            ]
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session3,
    }
    sio.emit("hook_event", todo_event3)
    print("☑️ Sent simple TODO checklist")

    print("\n" + "=" * 70)
    print("✅ EXPECTED ACTIVITY STRUCTURE:")
    print("=" * 70)
    print("📁 Project Root")
    print("├── 🎯 PM Session 1 (Authentication)")
    print("│   ├── 💬 User: 'Build a secure authentication system...'")
    print("│   ├── ☑️ TODOs (6 items - expandable checklist)")
    print("│   │   ├── ✅ Research JWT best practices")
    print("│   │   ├── ✅ Design authentication architecture")
    print("│   │   ├── 🔄 Implement JWT service")
    print("│   │   ├── 🔄 Add refresh token logic")
    print("│   │   ├── ⏳ Write comprehensive tests")
    print("│   │   └── ⏳ Set up session cleanup")
    print("│   ├── 🔬 research agent")
    print("│   │   ├── 🔧 WebFetch (JWT best practices)")
    print("│   │   ├── 🔧 Read (existing auth file)")
    print("│   │   └── 🔧 Grep (find auth patterns)")
    print("│   ├── 🔒 security agent")
    print("│   │   ├── 🔧 Read (security config)")
    print("│   │   └── 🔧 Bash (generate JWT secret)")
    print("│   └── 👷 engineer agent")
    print("│       ├── 🔧 Write (JWT service)")
    print("│       ├── 🔧 Edit (database config)")
    print("│       └── 🔧 MultiEdit (auth routes)")
    print("├── 🎯 PM Session 2 (Rate Limiting)")
    print("│   ├── 💬 User: 'Add rate limiting...'")
    print("│   ├── ☑️ TODOs (3 items)")
    print("│   │   ├── 🔄 Research rate limiting")
    print("│   │   ├── ⏳ Implement Redis limiter")
    print("│   │   └── ⏳ Add DDoS protection")
    print("│   └── ⚙️ ops agent")
    print("│       ├── 🔧 Bash (start Redis)")
    print("│       └── 🔧 Write (Redis config)")
    print("└── 🎯 PM Session 3 (Bug Fix)")
    print("    ├── 💬 User: 'Fix the memory leak...'")
    print("    └── ☑️ TODOs (2 items)")
    print("        ├── ✅ Identify memory leak")
    print("        └── 🔄 Fix memory leak")

    print("\n" + "=" * 70)
    print("🔍 VERIFICATION CHECKLIST:")
    print("=" * 70)
    print("1. ❌ NO duplicate PM agent under PM sessions")
    print("2. ✅ User instructions visible with 💬 icon")
    print("3. ✅ TODOs as expandable checklist with ☑️ icon")
    print("4. ✅ Individual TODO items show correct status icons")
    print("5. ✅ Clean data display (no raw JSON)")
    print("6. ✅ Each user instruction creates new PM row")
    print("7. ✅ Agents grouped correctly under their sessions")
    print("8. ✅ Tools grouped correctly under their agents")
    print("9. ✅ Click items to view details in left pane")
    print("10. ✅ Expand/collapse functionality works")

    print("\n🌐 Open: http://localhost:8765 → Activity tab")
    print("⏰ Test events will be visible for 10 seconds...")

    # Keep connection alive for manual verification
    time.sleep(10)
    print("\n✅ Test complete - disconnecting")
    sio.disconnect()


@sio.event
def connect_error(data):
    print(f"❌ Connection failed: {data}")


@sio.event
def disconnect():
    print("🔌 Disconnected from server")


def main():
    print("🚀 Starting comprehensive Activity structure test")
    print("📊 Dashboard should be running on http://localhost:8765")
    print("🔗 Attempting to connect...")

    try:
        sio.connect("http://localhost:8765")
        sio.wait()
    except Exception as e:
        print(f"❌ Error: {e}")
        print("💡 Make sure dashboard is running: ./scripts/claude-mpm dashboard start")


if __name__ == "__main__":
    main()
