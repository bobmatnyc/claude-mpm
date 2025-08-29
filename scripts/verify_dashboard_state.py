#!/usr/bin/env python3
# verify_dashboard_state.py
import json
import time
from datetime import datetime

import socketio


class DashboardVerifier:
    def __init__(self):
        self.sio = socketio.Client()
        self.events_received = []
        self.verification_results = {}

    def setup_handlers(self):
        @self.sio.event
        def connect():
            print("🔗 Connected to dashboard")
            # Request current state
            self.sio.emit("get_events")

        @self.sio.event
        def events_update(data):
            print(f"📥 Received events update: {len(data)} events")
            self.events_received = data
            self.verify_structure()

        @self.sio.event
        def disconnect():
            print("🔌 Disconnected from dashboard")

    def verify_structure(self):
        print("\n🔍 Verifying dashboard structure...")
        results = {
            "agent_uniqueness": False,
            "todo_under_pm": False,
            "tool_grouping": False,
            "no_duplicates": False,
        }

        # Group events by session and type
        sessions = {}
        agents_per_session = {}
        tools_per_session = {}
        todo_events = []

        for event in self.events_received:
            session_id = event.get("session_id", "default")

            # Initialize session tracking
            if session_id not in sessions:
                sessions[session_id] = []
                agents_per_session[session_id] = set()
                tools_per_session[session_id] = {}

            sessions[session_id].append(event)

            # Track agents
            if event.get("type") == "subagent" and event.get("subtype") == "started":
                agent_name = event.get("agent_name", "unknown")
                agents_per_session[session_id].add(agent_name)

            # Track tools
            if event.get("hook_event_name") == "PreToolUse":
                tool_name = event.get("tool_name")
                if tool_name:
                    if session_id not in tools_per_session:
                        tools_per_session[session_id] = {}
                    if tool_name not in tools_per_session[session_id]:
                        tools_per_session[session_id][tool_name] = 0
                    tools_per_session[session_id][tool_name] += 1

            # Track TODOs
            if (
                event.get("type") == "todo"
                or event.get("hook_event_name") == "TodoWrite"
            ):
                todo_events.append(event)

        print(f"📊 Found {len(sessions)} session(s)")
        for session_id, session_events in sessions.items():
            print(f"  Session {session_id}: {len(session_events)} events")
            if session_id in agents_per_session:
                agents = list(agents_per_session[session_id])
                print(f"    Agents: {', '.join(agents)} ({len(agents)} unique)")

                # Check for agent uniqueness
                if len(agents) == len(set(agents)):
                    results["agent_uniqueness"] = True
                    print("    ✅ All agents are unique")
                else:
                    print("    ❌ Duplicate agents detected")

            if session_id in tools_per_session:
                tools = tools_per_session[session_id]
                total_tools = sum(tools.values())
                print(f"    Tools: {total_tools} total, {len(tools)} unique types")
                for tool, count in tools.items():
                    print(f"      {tool}: {count}")

                results["tool_grouping"] = total_tools > 0

        # Check TODO events
        print(f"📝 Found {len(todo_events)} TODO event(s)")
        if todo_events:
            results["todo_under_pm"] = True
            print("✅ TODO events present (should appear under PM agent)")

            for todo_event in todo_events:
                if "data" in todo_event and "todos" in todo_event["data"]:
                    todos = todo_event["data"]["todos"]
                    print(f"  📋 TODO set with {len(todos)} items:")
                    for todo in todos:
                        status = todo.get("status", "unknown")
                        content = todo.get("content", "No content")
                        print(f"    {self.get_status_icon(status)} {content}")
        else:
            print("❌ No TODO events found")

        # Overall verification
        results["no_duplicates"] = results["agent_uniqueness"]

        print("\n📋 Verification Results:")
        for check, passed in results.items():
            icon = "✅" if passed else "❌"
            print(
                f"{icon} {check.replace('_', ' ').title()}: {'PASS' if passed else 'FAIL'}"
            )

        self.verification_results = results

        # Disconnect after verification
        self.sio.disconnect()

    def get_status_icon(self, status):
        return {"pending": "⏸️", "in_progress": "🔄", "completed": "✅"}.get(
            status, "❓"
        )

    def run_verification(self):
        try:
            self.setup_handlers()
            print("🚀 Starting dashboard verification...")
            self.sio.connect("http://localhost:8765")

            # Wait for events to be processed
            start_time = time.time()
            timeout = 10

            while not self.events_received and (time.time() - start_time) < timeout:
                time.sleep(0.5)

            if not self.events_received:
                print("⏰ Timeout waiting for events")
                return False

            self.sio.wait()
            return all(self.verification_results.values())

        except Exception as e:
            print(f"❌ Verification failed: {e}")
            return False


if __name__ == "__main__":
    verifier = DashboardVerifier()
    success = verifier.run_verification()

    print(f"\n🏁 Overall verification: {'✅ PASSED' if success else '❌ FAILED'}")
    exit(0 if success else 1)
