#!/usr/bin/env python3
"""Test SubagentStart event handling fix.

This test verifies that SubagentStart events are correctly handled
with agent_type field and emitted as "subagent_start" events.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, call

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from claude_mpm.hooks.claude_hooks.event_handlers import EventHandlers


def test_subagent_start_handler():
    """Test that SubagentStart events include agent_type and correct event name."""
    print("\n" + "=" * 60)
    print("🧪 Testing SubagentStart Event Handler Fix")
    print("=" * 60)

    # Create mock hook handler
    mock_handler = MagicMock()
    mock_handler._git_branch_cache = {}
    mock_handler._git_branch_cache_time = {}

    # Mock the _emit_socketio_event method to capture calls
    emitted_events = []

    def capture_emit(namespace, event_name, data):
        emitted_events.append(
            {"namespace": namespace, "event": event_name, "data": data}
        )

    mock_handler._emit_socketio_event = capture_emit

    # Create EventHandlers instance
    event_handlers = EventHandlers(mock_handler)

    # Test 1: SubagentStart event with agent_type
    print("\n1️⃣  Test SubagentStart with agent_type field...")
    test_event = {
        "session_id": "test-session-12345678",
        "agent_type": "engineer",
        "cwd": "/Users/test/project",
    }

    event_handlers.handle_subagent_start_fast(test_event)

    # Verify the emitted event
    assert len(emitted_events) == 1, "Should emit exactly one event"
    emitted = emitted_events[0]

    print(f"   ✅ Event emitted: {emitted['event']}")
    print(f"   ✅ Data: {emitted['data']}")

    # Assertions
    assert emitted["event"] == "subagent_start", "Event name should be 'subagent_start'"
    assert (
        emitted["data"]["agent_type"] == "engineer"
    ), "Should preserve agent_type field"
    assert (
        emitted["data"]["hook_event_name"] == "SubagentStart"
    ), "Should preserve hook_event_name"
    assert "agent_id" in emitted["data"], "Should include agent_id field"
    assert (
        "session_id" in emitted["data"]
    ), "Should include session_id field (not lost!)"

    print("   ✅ All assertions passed!")

    # Test 2: SubagentStart event with subagent_type (fallback)
    print("\n2️⃣  Test SubagentStart with subagent_type field (fallback)...")
    emitted_events.clear()

    test_event_2 = {
        "session_id": "test-session-87654321",
        "subagent_type": "research",
        "cwd": "/Users/test/project",
    }

    event_handlers.handle_subagent_start_fast(test_event_2)

    assert len(emitted_events) == 1, "Should emit exactly one event"
    emitted_2 = emitted_events[0]

    print(f"   ✅ Event emitted: {emitted_2['event']}")
    print(f"   ✅ Agent type extracted: {emitted_2['data']['agent_type']}")

    assert (
        emitted_2["data"]["agent_type"] == "research"
    ), "Should extract from subagent_type field"

    print("   ✅ Fallback field extraction works!")

    # Test 3: Compare with SessionStart (should be different)
    print("\n3️⃣  Test SessionStart handler (should NOT have agent_type)...")
    emitted_events.clear()

    test_session_event = {
        "session_id": "test-session-99999999",
        "cwd": "/Users/test/project",
    }

    event_handlers.handle_session_start_fast(test_session_event)

    assert len(emitted_events) == 1, "Should emit exactly one event"
    session_emitted = emitted_events[0]

    print(f"   ✅ Event emitted: {session_emitted['event']}")
    print(f"   ✅ Data keys: {list(session_emitted['data'].keys())}")

    assert (
        session_emitted["event"] == "session_start"
    ), "SessionStart should emit 'session_start'"
    assert (
        "agent_type" not in session_emitted["data"]
    ), "SessionStart should NOT have agent_type"
    assert (
        session_emitted["data"]["hook_event_name"] == "SessionStart"
    ), "Should preserve SessionStart hook name"

    print("   ✅ SessionStart correctly different from SubagentStart!")

    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print("✅ SubagentStart events now include agent_type field")
    print("✅ SubagentStart events emit as 'subagent_start' (not 'session_start')")
    print("✅ SessionStart and SubagentStart are properly separated")
    print("✅ Fallback field extraction (subagent_type) works")
    print("\n✨ All tests PASSED! Fix is working correctly.")

    return True


def test_expected_output_format():
    """Test that the output matches the expected format from the task description."""
    print("\n" + "=" * 60)
    print("🧪 Testing Expected Output Format")
    print("=" * 60)

    mock_handler = MagicMock()
    mock_handler._git_branch_cache = {}
    mock_handler._git_branch_cache_time = {}

    emitted_events = []

    def capture_emit(namespace, event_name, data):
        emitted_events.append(
            {"namespace": namespace, "event": event_name, "data": data}
        )

    mock_handler._emit_socketio_event = capture_emit

    event_handlers = EventHandlers(mock_handler)

    # Simulate SubagentStart event
    test_event = {
        "session_id": "abc123456789",
        "agent_type": "engineer",
        "cwd": "/Users/test/project",
    }

    event_handlers.handle_subagent_start_fast(test_event)

    # Verify output format matches expected
    assert len(emitted_events) == 1
    emitted = emitted_events[0]

    print("\n📤 Emitted Event:")
    print(f"   Event Name: {emitted['event']}")
    print(f"   Data Keys: {list(emitted['data'].keys())}")
    print(f"   Agent Type: {emitted['data']['agent_type']}")
    print(f"   Agent ID: {emitted['data']['agent_id']}")
    print(f"   Session ID: {emitted['data']['session_id']}")

    # Verify all expected fields are present
    expected_fields = [
        "session_id",
        "agent_type",
        "agent_id",
        "timestamp",
        "hook_event_name",
        "working_directory",
        "git_branch",
    ]

    for field in expected_fields:
        assert field in emitted["data"], f"Missing required field: {field}"
        print(f"   ✅ Field present: {field}")

    print("\n✅ Output format matches expected specification!")

    return True


if __name__ == "__main__":
    try:
        test_subagent_start_handler()
        print("\n")
        test_expected_output_format()
        print("\n🎉 All tests completed successfully!\n")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}\n")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}\n")
        import traceback

        traceback.print_exc()
        sys.exit(1)
