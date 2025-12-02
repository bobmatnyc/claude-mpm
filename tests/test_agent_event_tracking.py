#!/usr/bin/env python3
"""
Test script to verify agent event tracking in the dashboard.

This script tests:
1. Socket.IO connection reliability
2. Agent event emission (subagent_start/stop)
3. Event tracking and counting in dashboard
"""

import os
import sys
import time
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Set debug mode
os.environ["CLAUDE_MPM_HOOK_DEBUG"] = "true"


def test_socket_connection():
    """Test Socket.IO connection from hook handler."""
    print("\n=== Testing Socket.IO Connection ===")

    try:
        from claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()
        client = handler._get_socketio_client()

        if client and client.connected:
            print("✅ Socket.IO connection successful")
            return True
        print("❌ Socket.IO connection failed")
        return False

    except Exception as e:
        print(f"❌ Error testing connection: {e}")
        return False


def test_agent_event_emission():
    """Test agent event emission through hook handler."""
    print("\n=== Testing Agent Event Emission ===")

    try:
        from claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()

        # Test SubagentStart event
        print("\n1. Testing SubagentStart event...")
        start_event = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Task",
            "tool_input": {
                "subagent_type": "research",
                "prompt": "Test research task",
                "description": "Testing agent event tracking",
            },
            "session_id": "test_session_123",
            "cwd": os.getcwd(),
        }

        # Process the event
        handler._handle_pre_tool_fast(start_event)
        print("✅ SubagentStart event emitted")

        # Wait a bit
        time.sleep(1)

        # Test SubagentStop event
        print("\n2. Testing SubagentStop event...")
        stop_event = {
            "hook_event_name": "SubagentStop",
            "agent_type": "research",
            "session_id": "test_session_123",
            "reason": "completed",
            "cwd": os.getcwd(),
        }

        handler._handle_subagent_stop_fast(stop_event)
        print("✅ SubagentStop event emitted")

        return True

    except Exception as e:
        print(f"❌ Error testing event emission: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_multiple_agent_delegations():
    """Test multiple agent delegations to verify counting."""
    print("\n=== Testing Multiple Agent Delegations ===")

    try:
        from claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()

        agents = [
            ("research", "Analyze the codebase structure"),
            ("engineer", "Implement the fix"),
            ("qa", "Test the implementation"),
            ("documentation", "Update the documentation"),
        ]

        for i, (agent_type, task) in enumerate(agents):
            session_id = f"test_session_{i + 1:03d}"

            print(f"\n{i + 1}. Delegating to {agent_type} agent...")

            # Start event
            start_event = {
                "hook_event_name": "PreToolUse",
                "tool_name": "Task",
                "tool_input": {
                    "subagent_type": agent_type,
                    "prompt": task,
                    "description": f"Test delegation {i + 1}",
                },
                "session_id": session_id,
                "cwd": os.getcwd(),
            }
            handler._handle_pre_tool_fast(start_event)

            # Simulate some work
            time.sleep(0.5)

            # Stop event
            stop_event = {
                "hook_event_name": "SubagentStop",
                "agent_type": agent_type,
                "session_id": session_id,
                "reason": "completed",
                "cwd": os.getcwd(),
            }
            handler._handle_subagent_stop_fast(stop_event)

            print(f"✅ {agent_type} agent delegation complete")

        print("\n✅ All agent delegations tested successfully")
        return True

    except Exception as e:
        print(f"❌ Error testing multiple delegations: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Agent Event Tracking Test Suite")
    print("=" * 60)

    results = []

    # Test 1: Socket connection
    results.append(("Socket.IO Connection", test_socket_connection()))

    # Test 2: Agent event emission
    results.append(("Agent Event Emission", test_agent_event_emission()))

    # Test 3: Multiple delegations
    results.append(("Multiple Agent Delegations", test_multiple_agent_delegations()))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name}: {status}")

    all_passed = all(passed for _, passed in results)

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ All tests passed!")
        print("\nNow check the dashboard at http://localhost:8080 to verify:")
        print("1. Navigate to the Agents tab")
        print(
            "2. You should see events for Research, Engineer, QA, and Documentation agents"
        )
        print("3. Each agent should show event counts > 0")
    else:
        print("❌ Some tests failed. Please check the errors above.")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
