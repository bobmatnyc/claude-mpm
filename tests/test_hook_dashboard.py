#!/usr/bin/env python3
"""Test hook events in dashboard by simulating hook service behavior.

WHY: This script tests that hook events properly flow from the hook service
to the Socket.IO server and appear in the dashboard.
"""

import asyncio
import time
from datetime import datetime, timezone

import socketio


async def simulate_hook_service():
    """Simulate hook service sending events."""
    client = socketio.AsyncClient()

    try:
        # Connect to Socket.IO server
        await client.connect("http://localhost:8766")
        print("✅ Connected to Socket.IO server as hook service simulator")

        # Wait for connection to stabilize
        await asyncio.sleep(1)

        # Simulate a complete Claude session with hook events
        session_id = f"test-session-{int(time.time())}"

        hook_events = [
            # User starts a conversation
            {
                "type": "hook",
                "event": "UserPrompt",
                "data": {
                    "session_id": session_id,
                    "prompt_text": "Fix the authentication bug in the login module",
                    "working_directory": "/Users/test/project",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            },
            # PM delegates to Engineer
            {
                "type": "hook",
                "event": "SubagentStart",
                "data": {
                    "session_id": session_id,
                    "agent_type": "engineer",
                    "prompt": "Fix the authentication bug",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            },
            # Engineer reads file
            {
                "type": "hook",
                "event": "ToolCall",
                "data": {
                    "session_id": session_id,
                    "tool_name": "Read",
                    "parameters": {"file_path": "/src/auth.py"},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            },
            # Engineer edits file
            {
                "type": "hook",
                "event": "ToolCall",
                "data": {
                    "session_id": session_id,
                    "tool_name": "Edit",
                    "parameters": {
                        "file_path": "/src/auth.py",
                        "old_string": "if password == stored_password:",
                        "new_string": "if bcrypt.checkpw(password, stored_password):",
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            },
            # Engineer tests the fix
            {
                "type": "hook",
                "event": "ToolCall",
                "data": {
                    "session_id": session_id,
                    "tool_name": "Bash",
                    "parameters": {"command": "python -m pytest tests/test_auth.py"},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            },
            # Engineer completes
            {
                "type": "hook",
                "event": "SubagentStop",
                "data": {
                    "session_id": session_id,
                    "agent_type": "engineer",
                    "status": "completed",
                    "result": "Fixed authentication bug by using bcrypt for password comparison",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            },
            # PM delegates to QA
            {
                "type": "hook",
                "event": "SubagentStart",
                "data": {
                    "session_id": session_id,
                    "agent_type": "qa",
                    "prompt": "Test the authentication fix",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            },
            # QA runs tests
            {
                "type": "hook",
                "event": "ToolCall",
                "data": {
                    "session_id": session_id,
                    "tool_name": "Bash",
                    "parameters": {"command": "python -m pytest tests/ -v"},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            },
            # QA completes
            {
                "type": "hook",
                "event": "SubagentStop",
                "data": {
                    "session_id": session_id,
                    "agent_type": "qa",
                    "status": "completed",
                    "result": "All tests pass. Authentication fix verified.",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            },
        ]

        print(
            f"\n📤 Simulating complete Claude session with {len(hook_events)} hook events..."
        )
        print(f"   Session ID: {session_id}")

        for i, event in enumerate(hook_events, 1):
            event_name = event.get("event", "unknown")
            agent = event.get("data", {}).get("agent_type", "")
            tool = event.get("data", {}).get("tool_name", "")

            if agent:
                desc = f"{event_name} ({agent})"
            elif tool:
                desc = f"{event_name} ({tool})"
            else:
                desc = event_name

            print(f"\n{i}. {desc}")

            # Send as claude_event (how hook service sends them)
            await client.emit("claude_event", event)
            print("   ✅ Sent")

            # Realistic timing between events
            if i < len(hook_events):
                await asyncio.sleep(0.8)

        print("\n⏳ Waiting 3 seconds for events to appear in dashboard...")
        await asyncio.sleep(3)

        # Request history to verify events were stored
        history_future = asyncio.Future()

        @client.on("history")
        async def on_history(data):
            history_future.set_result(data)

        await client.emit("get_history", {"limit": 20})

        try:
            history_data = await asyncio.wait_for(history_future, timeout=5)
            hook_events_count = sum(
                1 for e in history_data.get("events", []) if e.get("type") == "hook"
            )
            print(f"\n📊 Server has {hook_events_count} hook events in history")

            # Show last few hook events
            recent_hooks = [
                e
                for e in history_data.get("events", [])[-15:]
                if e.get("type") == "hook"
            ]
            if recent_hooks:
                print("\n📖 Recent hook events in server:")
                for event in recent_hooks[-5:]:
                    event_name = event.get("event", "unnamed")
                    data = event.get("data", {})
                    if "agent_type" in data:
                        print(f"   - {event_name}: {data['agent_type']} agent")
                    elif "tool_name" in data:
                        print(f"   - {event_name}: {data['tool_name']} tool")
                    else:
                        print(f"   - {event_name}")

        except asyncio.TimeoutError:
            print("❌ Timeout waiting for history response")

        print("\n" + "=" * 60)
        print("✅ TEST COMPLETE!")
        print("=" * 60)
        print("\n📌 Next Steps:")
        print("1. Open dashboard: http://localhost:8766/dashboard")
        print("2. You should see:")
        print("   - UserPrompt event")
        print("   - SubagentStart/Stop events for engineer and qa")
        print("   - ToolCall events for Read, Edit, and Bash")
        print("3. Events should show in the event feed with proper types")
        print("4. Filter by 'hook' type to see only hook events")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await client.disconnect()


async def main():
    """Main test function."""
    print("🔍 Testing Hook Events in Dashboard")
    print("=" * 60)

    # Check server is running
    test_client = socketio.AsyncClient()
    try:
        await test_client.connect("http://localhost:8766")
        print("✅ Socket.IO server is running")
        await test_client.disconnect()
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        print("\n⚠️  Please start the Socket.IO server first:")
        print("   claude-mpm monitor start")
        return

    # Run the simulation
    await simulate_hook_service()


if __name__ == "__main__":
    asyncio.run(main())
