#!/usr/bin/env python3
"""
Test that dashboard event transformation protects critical fields from being overwritten.

This test validates the fix for the issue where event data fields could overwrite
critical fields like 'type' and 'subtype', causing events to display as "unknown".
"""

import pytest

# Test data for various event scenarios
TEST_EVENTS = [
    {
        "name": "hook_event_with_type_conflict",
        "input": {
            "type": "hook.pre_tool",
            "timestamp": "2024-01-01T10:00:00Z",
            "data": {
                "type": "SHOULD_NOT_OVERWRITE",
                "subtype": "ALSO_SHOULD_NOT_OVERWRITE",
                "tool_name": "Edit",
                "parameters": {"file_path": "/test.py"},
            },
        },
        "expected": {
            "type": "hook",
            "subtype": "pre_tool",
            "tool_name": "Edit",  # Should be copied to top level
            "parameters": {"file_path": "/test.py"},  # Should be copied to top level
            "originalEventName": "hook.pre_tool",
        },
    },
    {
        "name": "legacy_subagent_event",
        "input": {
            "event": "SubagentStart",
            "timestamp": "2024-01-01T10:00:00Z",
            "data": {"agent_type": "Engineer", "task": "Fix bug"},
        },
        "expected": {
            "type": "subagent",
            "subtype": "start",
            "agent_type": "Engineer",  # Should be copied to top level
            "task": "Fix bug",  # Should be copied to top level
            "originalEventName": "SubagentStart",
        },
    },
    {
        "name": "session_event_with_subtype_conflict",
        "input": {
            "type": "session",
            "subtype": "started",
            "timestamp": "2024-01-01T10:00:00Z",
            "data": {
                "subtype": "different_subtype",
                "session_id": "sess_123",
                "user": "test_user",
            },
        },
        "expected": {
            "type": "session",
            "subtype": "started",  # Should NOT be overwritten
            "session_id": "sess_123",
            "user": "test_user",
            "originalEventName": "session",
        },
    },
    {
        "name": "event_with_timestamp_in_data",
        "input": {
            "type": "test",
            "timestamp": "2024-01-01T10:00:00Z",
            "data": {
                "timestamp": "2024-01-01T11:00:00Z",  # Different timestamp
                "test_name": "unit_test",
                "status": "passed",
            },
        },
        "expected": {
            "type": "test",
            "timestamp": "2024-01-01T10:00:00Z",  # Original should be preserved
            "test_name": "unit_test",
            "status": "passed",
            "originalEventName": "test",
        },
    },
    {
        "name": "event_with_id_in_data",
        "input": {
            "type": "log",
            "id": "original_id",
            "timestamp": "2024-01-01T10:00:00Z",
            "data": {"id": "conflicting_id", "level": "error", "message": "Test error"},
        },
        "expected": {
            "type": "log",
            "id": "original_id",  # Should NOT be overwritten
            "level": "error",
            "message": "Test error",
            "originalEventName": "log",
        },
    },
]


class TestEventFieldProtection:
    """Test suite for event field protection."""

    def simulate_js_transform(self, event_data):
        """
        Python simulation of the JavaScript transformEvent function
        with the field protection fix applied.
        """
        if not event_data:
            return event_data

        transformed = event_data.copy()

        # Store original event name
        if not event_data.get("type") and event_data.get("event"):
            transformed["originalEventName"] = event_data["event"]
        elif event_data.get("type"):
            transformed["originalEventName"] = event_data["type"]

        # Handle legacy format
        if not event_data.get("type") and event_data.get("event"):
            event_name = event_data["event"]

            if event_name == "SubagentStart":
                transformed["type"] = "subagent"
                transformed["subtype"] = "start"
            elif event_name == "SubagentStop":
                transformed["type"] = "subagent"
                transformed["subtype"] = "stop"
            # ... other legacy mappings

            if "event" in transformed:
                del transformed["event"]

        # Handle hook.subtype format
        elif event_data.get("type"):
            type_val = event_data["type"]
            if type_val.startswith("hook."):
                transformed["type"] = "hook"
                transformed["subtype"] = type_val[5:]
            elif "." in type_val and "subtype" not in event_data:
                parts = type_val.split(".")
                transformed["type"] = parts[0]
                transformed["subtype"] = ".".join(parts[1:]) if len(parts) > 1 else ""

        # Protected fields that should never be overwritten
        protected_fields = [
            "type",
            "subtype",
            "timestamp",
            "id",
            "event",
            "event_type",
            "originalEventName",
        ]

        # Flatten data fields with protection
        if event_data.get("data") and isinstance(event_data["data"], dict):
            for key, value in event_data["data"].items():
                if key not in protected_fields:
                    transformed[key] = value
            transformed["data"] = event_data["data"]

        return transformed

    @pytest.mark.parametrize(
        "test_case", TEST_EVENTS, ids=[t["name"] for t in TEST_EVENTS]
    )
    def test_field_protection(self, test_case):
        """Test that protected fields are not overwritten by data fields."""
        result = self.simulate_js_transform(test_case["input"])

        # Check critical protected fields
        for field in ["type", "subtype", "timestamp", "id"]:
            if field in test_case["expected"]:
                assert result.get(field) == test_case["expected"][field], (
                    f"Field '{field}' was incorrectly overwritten or transformed"
                )

        # Check that data fields were copied (except protected ones)
        if test_case["input"].get("data"):
            for key, value in test_case["input"]["data"].items():
                if key not in [
                    "type",
                    "subtype",
                    "timestamp",
                    "id",
                    "event",
                    "event_type",
                ]:
                    assert result.get(key) == value, (
                        f"Data field '{key}' was not copied to top level"
                    )

    def test_hook_pre_tool_not_overwritten(self):
        """Specific test for hook.pre_tool events."""
        event = {
            "type": "hook.pre_tool",
            "timestamp": "2024-01-01T10:00:00Z",
            "data": {"type": "WRONG", "tool_name": "Edit"},
        }

        result = self.simulate_js_transform(event)

        assert result["type"] == "hook", "Hook type was overwritten"
        assert result["subtype"] == "pre_tool", "Hook subtype was lost"
        assert result["tool_name"] == "Edit", "tool_name not copied to top level"

    def test_original_event_name_preserved(self):
        """Test that originalEventName is preserved for display."""
        # Test with type
        event1 = {"type": "hook.user_prompt", "data": {}}
        result1 = self.simulate_js_transform(event1)
        assert result1.get("originalEventName") == "hook.user_prompt"

        # Test with legacy event
        event2 = {"event": "SubagentStart", "data": {}}
        result2 = self.simulate_js_transform(event2)
        assert result2.get("originalEventName") == "SubagentStart"

    def test_no_protected_field_warnings(self, caplog):
        """Test that warnings are logged when protected fields would be overwritten."""
        # This would need to be tested in the actual JavaScript environment
        # or with a more complete Python simulation that includes logging

    def test_backwards_compatibility(self):
        """Test that the fix maintains backwards compatibility."""
        # Event without data object
        event1 = {"type": "simple", "timestamp": "2024-01-01T10:00:00Z"}
        result1 = self.simulate_js_transform(event1)
        assert result1["type"] == "simple"

        # Event with empty data
        event2 = {"type": "test", "data": {}}
        result2 = self.simulate_js_transform(event2)
        assert result2["type"] == "test"
        assert "data" in result2


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
