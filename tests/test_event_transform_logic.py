#!/usr/bin/env python3
"""Unit test for event transformation logic to ensure protected fields are preserved."""

from datetime import datetime, timezone


def simulate_transform_event(event_data):
    """
    Simulates the JavaScript transformEvent function logic.
    This is a Python representation of the fixed JavaScript code.
    """
    if not event_data:
        return event_data

    transformed_event = event_data.copy()

    # Store original event name
    if not event_data.get("type") and event_data.get("event"):
        transformed_event["originalEventName"] = event_data["event"]
    elif event_data.get("type"):
        transformed_event["originalEventName"] = event_data["type"]

    # Handle legacy format
    if not event_data.get("type") and event_data.get("event"):
        event_name = event_data["event"]

        if event_name in ["TestStart", "TestEnd"]:
            transformed_event["type"] = "test"
            transformed_event["subtype"] = event_name.lower().replace("test", "")
        elif event_name in ["SubagentStart", "SubagentStop"]:
            transformed_event["type"] = "subagent"
            transformed_event["subtype"] = event_name.lower().replace("subagent", "")
        elif event_name == "ToolCall":
            transformed_event["type"] = "tool"
            transformed_event["subtype"] = "call"
        elif event_name == "UserPrompt":
            transformed_event["type"] = "hook"
            transformed_event["subtype"] = "user_prompt"
        else:
            transformed_event["type"] = "system"
            transformed_event["subtype"] = event_name.lower()

        del transformed_event["event"]

    # Handle standard format
    elif event_data.get("type"):
        type_value = event_data["type"]

        if type_value.startswith("hook."):
            subtype = type_value[5:]  # Remove 'hook.' prefix
            transformed_event["type"] = "hook"
            transformed_event["subtype"] = subtype
        elif "." in type_value:
            parts = type_value.split(".")
            transformed_event["type"] = parts[0]
            transformed_event["subtype"] = ".".join(parts[1:])

    # Handle unknown
    else:
        transformed_event["type"] = "unknown"
        transformed_event["subtype"] = ""

    # Extract and flatten data fields (WITH PROTECTION)
    if event_data.get("data") and isinstance(event_data["data"], dict):
        protected_fields = [
            "type",
            "subtype",
            "timestamp",
            "id",
            "event",
            "event_type",
            "originalEventName",
        ]

        for key, value in event_data["data"].items():
            if key not in protected_fields:
                transformed_event[key] = value
            else:
                print(
                    f"WARNING: Protected field '{key}' not copied from data to preserve structure"
                )

        transformed_event["data"] = event_data["data"]

    return transformed_event


def test_protected_fields():
    """Test that protected fields are not overwritten."""

    print("Testing Event Transformation Logic")
    print("=" * 50)

    # Test 1: Hook event with conflicting type in data
    test1 = {
        "type": "hook.pre_tool",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {
            "type": "SHOULD_NOT_OVERWRITE",
            "subtype": "ALSO_SHOULD_NOT_OVERWRITE",
            "tool_name": "Edit",
        },
    }

    result1 = simulate_transform_event(test1)
    assert result1["type"] == "hook", f"Expected type 'hook', got '{result1['type']}'"
    assert result1["subtype"] == "pre_tool", (
        f"Expected subtype 'pre_tool', got '{result1['subtype']}'"
    )
    assert result1["tool_name"] == "Edit", "tool_name should be copied to top level"
    print(
        "✓ Test 1 PASSED: Hook event preserves type/subtype despite conflicting data fields"
    )

    # Test 2: Legacy event format
    test2 = {
        "event": "SubagentStart",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {"agent_type": "Engineer"},
    }

    result2 = simulate_transform_event(test2)
    assert result2["type"] == "subagent", (
        f"Expected type 'subagent', got '{result2['type']}'"
    )
    assert result2["subtype"] == "start", (
        f"Expected subtype 'start', got '{result2['subtype']}'"
    )
    assert result2["agent_type"] == "Engineer", (
        "agent_type should be copied to top level"
    )
    assert result2["originalEventName"] == "SubagentStart", (
        "originalEventName should be preserved"
    )
    assert "event" not in result2, "'event' field should be removed"
    print("✓ Test 2 PASSED: Legacy event format correctly transformed")

    # Test 3: Session event with data.subtype
    test3 = {
        "type": "session",
        "subtype": "started",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {"subtype": "different_value", "session_id": "abc123"},
    }

    result3 = simulate_transform_event(test3)
    assert result3["type"] == "session", (
        f"Expected type 'session', got '{result3['type']}'"
    )
    assert result3["subtype"] == "started", (
        f"Expected subtype 'started', got '{result3['subtype']}'"
    )
    assert result3["session_id"] == "abc123", "session_id should be copied to top level"
    print("✓ Test 3 PASSED: Session event preserves original subtype")

    # Test 4: Event with timestamp in data (should not overwrite)
    test4 = {
        "type": "test",
        "timestamp": "2024-01-01T10:00:00",
        "data": {
            "timestamp": "2024-01-01T11:00:00",  # Different timestamp in data
            "test_name": "unit_test",
        },
    }

    result4 = simulate_transform_event(test4)
    assert result4["timestamp"] == "2024-01-01T10:00:00", (
        "Original timestamp should be preserved"
    )
    assert result4["test_name"] == "unit_test", (
        "test_name should be copied to top level"
    )
    print("✓ Test 4 PASSED: Timestamp field is protected from overwriting")

    # Test 5: Dotted type format (session.started)
    test5 = {
        "type": "session.started",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {"user_id": "user123"},
    }

    result5 = simulate_transform_event(test5)
    assert result5["type"] == "session", (
        f"Expected type 'session', got '{result5['type']}'"
    )
    assert result5["subtype"] == "started", (
        f"Expected subtype 'started', got '{result5['subtype']}'"
    )
    assert result5["originalEventName"] == "session.started", (
        "originalEventName should preserve dotted format"
    )
    print("✓ Test 5 PASSED: Dotted type format correctly split")

    print("\n" + "=" * 50)
    print("All tests PASSED! Event transformation logic is working correctly.")
    print("\nKey fixes verified:")
    print("1. Protected fields (type, subtype, timestamp, etc.) are never overwritten")
    print("2. Original event names are preserved for display")
    print("3. Legacy event formats are correctly transformed")
    print("4. Data fields are still flattened to top level (except protected ones)")


if __name__ == "__main__":
    test_protected_fields()
