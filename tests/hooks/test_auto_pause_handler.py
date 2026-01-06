#!/usr/bin/env python3
"""Tests for AutoPauseHandler component.

WHY: Validate auto-pause behavior, threshold detection, action recording,
and integration with ContextUsageTracker and IncrementalPauseManager.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.hooks.claude_hooks.auto_pause_handler import (
    THRESHOLD_WARNINGS,
    AutoPauseHandler,
)
from claude_mpm.services.infrastructure.context_usage_tracker import (
    ContextUsageTracker,
)


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create temporary project directory for tests."""
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()
    return project_dir


@pytest.fixture
def handler(temp_project_dir):
    """Create AutoPauseHandler instance for testing."""
    return AutoPauseHandler(project_path=temp_project_dir)


@pytest.fixture
def tracker(temp_project_dir):
    """Create ContextUsageTracker instance for validation."""
    return ContextUsageTracker(project_path=temp_project_dir)


class TestAutoPauseHandlerInitialization:
    """Test handler initialization and state loading."""

    def test_init_creates_required_directories(self, temp_project_dir):
        """Handler should create .claude-mpm/state and sessions directories."""
        handler = AutoPauseHandler(project_path=temp_project_dir)

        state_dir = temp_project_dir / ".claude-mpm" / "state"
        sessions_dir = temp_project_dir / ".claude-mpm" / "sessions"

        assert state_dir.exists()
        assert sessions_dir.exists()

    def test_init_loads_existing_state(self, temp_project_dir, tracker):
        """Handler should load existing context usage state."""
        # Create some usage history
        tracker.update_usage(input_tokens=50000, output_tokens=20000)

        # Initialize handler - should load existing state
        handler = AutoPauseHandler(project_path=temp_project_dir)

        status = handler.get_status()
        assert status["context_percentage"] == 35.0  # 70k/200k = 35%
        assert status["threshold_reached"] is None  # Below 70%

    def test_init_with_default_path(self, tmp_path):
        """Handler should use current directory if no path provided."""
        with patch("pathlib.Path.cwd") as mock_cwd:
            mock_cwd.return_value = tmp_path
            handler = AutoPauseHandler()

            assert handler.project_path == tmp_path


class TestUsageUpdateAndThresholds:
    """Test token usage updates and threshold detection."""

    def test_update_usage_below_threshold(self, handler, tracker):
        """Updating usage below 70% should not trigger any threshold."""
        usage = {
            "input_tokens": 10000,
            "output_tokens": 5000,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        }

        threshold = handler.on_usage_update(usage)

        assert threshold is None
        assert not handler.is_pause_active()

        status = handler.get_status()
        assert status["context_percentage"] == 7.5  # 15k/200k

    def test_update_usage_crosses_caution_threshold(self, handler):
        """Crossing 70% threshold should return 'caution'."""
        usage = {
            "input_tokens": 100000,
            "output_tokens": 50000,  # 150k total = 75%
        }

        threshold = handler.on_usage_update(usage)

        assert threshold == "caution"
        assert not handler.is_pause_active()  # No pause yet

    def test_update_usage_crosses_warning_threshold(self, handler):
        """Crossing 85% threshold should return 'warning'."""
        usage = {
            "input_tokens": 120000,
            "output_tokens": 60000,  # 180k total = 90%
        }

        # First update to 75% (caution)
        handler.on_usage_update({"input_tokens": 100000, "output_tokens": 50000})

        # Second update crosses warning (85%)
        threshold = handler.on_usage_update(
            {"input_tokens": 10000, "output_tokens": 10000}
        )

        assert threshold == "warning"
        assert not handler.is_pause_active()  # Still no pause

    def test_update_usage_crosses_auto_pause_threshold(self, handler):
        """Crossing 90% threshold should return 'auto_pause' and trigger pause."""
        # Update to 91% context
        usage = {
            "input_tokens": 130000,
            "output_tokens": 52000,  # 182k total = 91%
        }

        threshold = handler.on_usage_update(usage)

        assert threshold == "auto_pause"
        assert handler.is_pause_active()

        # Verify pause session was created
        sessions_dir = handler.project_path / ".claude-mpm" / "sessions"
        active_pause = sessions_dir / "ACTIVE-PAUSE.jsonl"
        assert active_pause.exists()

    def test_update_usage_crosses_critical_threshold(self, handler):
        """Crossing 95% threshold should return 'critical' and trigger pause."""
        # Update to 96% context
        usage = {
            "input_tokens": 140000,
            "output_tokens": 52000,  # 192k total = 96%
        }

        threshold = handler.on_usage_update(usage)

        assert threshold == "critical"
        assert handler.is_pause_active()

    def test_update_usage_multiple_times_only_new_thresholds(self, handler):
        """Should only return threshold when crossing NEW threshold."""
        # First update: cross caution (70%) - 75% total
        threshold1 = handler.on_usage_update(
            {"input_tokens": 100000, "output_tokens": 50000}
        )
        assert threshold1 == "caution"

        # Second update: still in caution range, no new threshold - 80% total
        threshold2 = handler.on_usage_update(
            {"input_tokens": 5000, "output_tokens": 5000}
        )
        assert threshold2 is None  # No new threshold crossed

        # Third update: cross warning (85%) - 87.5% total
        threshold3 = handler.on_usage_update(
            {"input_tokens": 10000, "output_tokens": 5000}
        )
        assert threshold3 == "warning"

    def test_update_usage_with_cache_tokens(self, handler):
        """Cache tokens should be included in usage calculation."""
        usage = {
            "input_tokens": 50000,
            "output_tokens": 20000,
            "cache_creation_input_tokens": 30000,
            "cache_read_input_tokens": 10000,  # Cache read is "free" but tracked
        }

        handler.on_usage_update(usage)

        status = handler.get_status()
        # Total effective tokens: 50k input + 20k output = 70k (35%)
        assert status["context_percentage"] == 35.0

    def test_update_usage_invalid_tokens_negative(self, handler):
        """Negative token counts should return None (graceful error handling)."""
        usage = {
            "input_tokens": -1000,  # Invalid
            "output_tokens": 5000,
        }

        threshold = handler.on_usage_update(usage)

        assert threshold is None  # Error handled gracefully


class TestActionRecording:
    """Test action recording during pause mode."""

    def test_record_tool_call_when_pause_active(self, handler):
        """Should record tool calls when pause is active."""
        # Trigger auto-pause
        handler.on_usage_update({"input_tokens": 130000, "output_tokens": 52000})

        # Record tool call
        handler.on_tool_call(
            tool_name="Read",
            tool_args={"file_path": "/test/file.py", "limit": 100},
        )

        # Verify action was recorded
        actions = handler.pause_manager.get_recorded_actions()
        tool_actions = [a for a in actions if a.type == "tool_call"]

        assert len(tool_actions) == 1
        assert tool_actions[0].data["tool"] == "Read"
        assert "args_summary" in tool_actions[0].data

    def test_record_tool_call_when_pause_not_active(self, handler):
        """Should not record tool calls when pause is not active."""
        # No pause triggered
        handler.on_tool_call(
            tool_name="Read",
            tool_args={"file_path": "/test/file.py"},
        )

        # Pause should not be active
        assert not handler.is_pause_active()

    def test_record_assistant_response_when_pause_active(self, handler):
        """Should record assistant responses when pause is active."""
        # Trigger auto-pause
        handler.on_usage_update({"input_tokens": 130000, "output_tokens": 52000})

        # Record response
        response = "This is a test response from the assistant."
        handler.on_assistant_response(response)

        # Verify action was recorded
        actions = handler.pause_manager.get_recorded_actions()
        response_actions = [a for a in actions if a.type == "assistant_response"]

        assert len(response_actions) == 1
        assert response_actions[0].data["summary"] == response

    def test_record_assistant_response_truncates_long_text(self, handler):
        """Should truncate long assistant responses."""
        # Trigger auto-pause
        handler.on_usage_update({"input_tokens": 130000, "output_tokens": 52000})

        # Record very long response
        long_response = "A" * 1000  # 1000 characters
        handler.on_assistant_response(long_response)

        # Verify truncation
        actions = handler.pause_manager.get_recorded_actions()
        response_actions = [a for a in actions if a.type == "assistant_response"]

        summary = response_actions[0].data["summary"]
        assert len(summary) <= 500  # MAX_SUMMARY_LENGTH
        assert summary.endswith("...")

    def test_record_user_message_when_pause_active(self, handler):
        """Should record user messages when pause is active."""
        # Trigger auto-pause
        handler.on_usage_update({"input_tokens": 130000, "output_tokens": 52000})

        # Record user message
        message = "Please fix the bug in authentication."
        handler.on_user_message(message)

        # Verify action was recorded
        actions = handler.pause_manager.get_recorded_actions()
        message_actions = [a for a in actions if a.type == "user_message"]

        assert len(message_actions) == 1
        assert message_actions[0].data["summary"] == message

    def test_record_multiple_actions(self, handler):
        """Should record multiple actions in sequence."""
        # Trigger auto-pause
        handler.on_usage_update({"input_tokens": 130000, "output_tokens": 52000})

        # Record multiple actions
        handler.on_tool_call("Read", {"file": "test.py"})
        handler.on_assistant_response("Reading file...")
        handler.on_tool_call("Edit", {"file": "test.py", "old": "a", "new": "b"})
        handler.on_assistant_response("File edited.")

        # Verify all actions recorded
        actions = handler.pause_manager.get_recorded_actions()

        # First action is pause_started
        assert actions[0].type == "pause_started"

        # Subsequent actions
        action_types = [a.type for a in actions[1:]]
        assert action_types == [
            "tool_call",
            "assistant_response",
            "tool_call",
            "assistant_response",
        ]


class TestSessionFinalization:
    """Test session end handling and finalization."""

    def test_session_end_with_no_active_pause(self, handler):
        """Should return None if no pause is active."""
        session_file = handler.on_session_end()

        assert session_file is None

    def test_session_end_with_active_pause(self, handler):
        """Should finalize pause and return session file path."""
        # Trigger auto-pause and record actions
        handler.on_usage_update({"input_tokens": 130000, "output_tokens": 52000})
        handler.on_tool_call("Read", {"file": "test.py"})
        handler.on_assistant_response("Processing...")

        # End session
        session_file = handler.on_session_end()

        assert session_file is not None
        assert session_file.exists()
        assert session_file.suffix == ".json"

        # Verify ACTIVE-PAUSE.jsonl was archived
        sessions_dir = handler.project_path / ".claude-mpm" / "sessions"
        active_pause = sessions_dir / "ACTIVE-PAUSE.jsonl"
        assert not active_pause.exists()  # Should be archived/removed

    def test_session_end_creates_all_formats(self, handler):
        """Should create JSON, YAML, and MD files."""
        # Trigger auto-pause
        handler.on_usage_update({"input_tokens": 130000, "output_tokens": 52000})
        handler.on_tool_call("Read", {"file": "test.py"})

        # End session
        session_file = handler.on_session_end()

        # Extract session ID
        session_id = session_file.stem

        # Verify all formats exist
        sessions_dir = handler.project_path / ".claude-mpm" / "sessions"
        json_file = sessions_dir / f"{session_id}.json"
        yaml_file = sessions_dir / f"{session_id}.yaml"
        md_file = sessions_dir / f"{session_id}.md"

        assert json_file.exists()
        assert yaml_file.exists()
        assert md_file.exists()


class TestStatusAndWarnings:
    """Test status reporting and warning messages."""

    def test_get_status_initial_state(self, handler):
        """Should return initial state with 0% context."""
        status = handler.get_status()

        assert status["context_percentage"] == 0.0
        assert status["threshold_reached"] is None
        assert status["auto_pause_active"] is False
        assert status["pause_active"] is False
        assert status["total_tokens"] == 0
        assert status["budget"] == 200000

    def test_get_status_after_usage_update(self, handler):
        """Should reflect updated context usage."""
        handler.on_usage_update({"input_tokens": 50000, "output_tokens": 25000})

        status = handler.get_status()

        assert status["context_percentage"] == 37.5  # 75k/200k
        assert status["threshold_reached"] is None  # Below 70%
        assert status["total_tokens"] == 75000

    def test_get_status_with_active_pause(self, handler):
        """Should include pause details when pause is active."""
        # Trigger pause
        handler.on_usage_update({"input_tokens": 130000, "output_tokens": 52000})
        handler.on_tool_call("Read", {"file": "test.py"})

        status = handler.get_status()

        assert status["pause_active"] is True
        assert "pause_details" in status
        assert status["pause_details"]["action_count"] >= 1

    def test_emit_threshold_warning_caution(self, handler):
        """Should emit caution warning at 70%."""
        warning = handler.emit_threshold_warning("caution")

        assert "70%" in warning
        assert "Consider wrapping up" in warning

    def test_emit_threshold_warning_auto_pause(self, handler):
        """Should emit auto-pause warning at 90%."""
        warning = handler.emit_threshold_warning("auto_pause")

        assert "90%" in warning
        assert "Auto-pause activated" in warning

    def test_emit_threshold_warning_includes_percentage(self, handler):
        """Warning should include actual context percentage."""
        # Set context to specific percentage
        handler.on_usage_update({"input_tokens": 100000, "output_tokens": 50000})

        warning = handler.emit_threshold_warning("caution")

        # Should include actual percentage (75%)
        assert "75.0%" in warning


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_multiple_threshold_crossings_in_one_update(self, handler):
        """Should only return highest threshold when jumping multiple levels."""
        # Jump directly from 0% to 92% (skipping caution and warning)
        usage = {
            "input_tokens": 130000,
            "output_tokens": 54000,  # 184k = 92%
        }

        threshold = handler.on_usage_update(usage)

        # Should return auto_pause (highest threshold crossed)
        assert threshold == "auto_pause"
        assert handler.is_pause_active()

    def test_usage_update_with_missing_fields(self, handler):
        """Should handle missing usage fields gracefully."""
        usage = {
            "input_tokens": 10000,
            # output_tokens missing
        }

        threshold = handler.on_usage_update(usage)

        # Should default missing fields to 0
        status = handler.get_status()
        assert status["total_tokens"] == 10000

    def test_pause_already_active_no_duplicate_trigger(self, handler):
        """Should not create duplicate pause sessions."""
        # Trigger pause
        handler.on_usage_update({"input_tokens": 130000, "output_tokens": 52000})

        # Try to trigger again
        handler.on_usage_update({"input_tokens": 5000, "output_tokens": 5000})

        # Should only have one pause session
        sessions_dir = handler.project_path / ".claude-mpm" / "sessions"
        active_pause = sessions_dir / "ACTIVE-PAUSE.jsonl"
        assert active_pause.exists()

        # Should have exactly one pause_started action
        actions = handler.pause_manager.get_recorded_actions()
        pause_starts = [a for a in actions if a.type == "pause_started"]
        assert len(pause_starts) == 1

    def test_summarize_dict_limits_items(self, handler):
        """Should limit dictionary summaries to max items."""
        large_dict = {f"key_{i}": f"value_{i}" for i in range(20)}

        summary = handler._summarize_dict(large_dict, max_items=5)

        # Should only have 5 items + "..." marker
        assert len(summary) == 6
        assert "..." in summary

    def test_truncate_text_preserves_short_text(self, handler):
        """Should not truncate text shorter than max length."""
        short_text = "This is a short string"

        truncated = handler._truncate_text(short_text, max_length=100)

        assert truncated == short_text

    def test_truncate_text_adds_ellipsis(self, handler):
        """Should add ellipsis when truncating long text."""
        long_text = "A" * 100

        truncated = handler._truncate_text(long_text, max_length=50)

        assert len(truncated) == 50
        assert truncated.endswith("...")
        assert truncated.startswith("AAA")


class TestConcurrency:
    """Test thread-safety and concurrent access patterns."""

    def test_multiple_handler_instances_share_state(self, temp_project_dir):
        """Multiple handler instances should share state via file persistence."""
        # First handler updates usage
        handler1 = AutoPauseHandler(project_path=temp_project_dir)
        handler1.on_usage_update({"input_tokens": 50000, "output_tokens": 25000})

        # Second handler should see the update
        handler2 = AutoPauseHandler(project_path=temp_project_dir)
        status = handler2.get_status()

        assert status["total_tokens"] == 75000
        assert status["context_percentage"] == 37.5

    def test_pause_state_persists_across_instances(self, temp_project_dir):
        """Pause state should persist across handler instances."""
        # First handler triggers pause
        handler1 = AutoPauseHandler(project_path=temp_project_dir)
        handler1.on_usage_update({"input_tokens": 130000, "output_tokens": 52000})

        # Second handler should see active pause
        handler2 = AutoPauseHandler(project_path=temp_project_dir)
        assert handler2.is_pause_active()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
