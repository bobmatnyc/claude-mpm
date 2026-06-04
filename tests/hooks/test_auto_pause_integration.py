"""Integration tests confirming context auto-pause is DISABLED end-to-end.

WHY: Auto-pause used to abort active work (including in-flight sub-agent
delegations) once context usage crossed 90%/95%. That behavior was removed.
Token usage is still metered, but crossing a threshold must NEVER start a pause,
write ACTIVE-PAUSE.jsonl, or record actions through the event-handler path.

Tests:
- Crossing the threshold reports it but never activates a pause
- No actions are recorded through the event handlers (pause never active)
- No ACTIVE-PAUSE.jsonl is ever created
- Event handling still flows normally (SocketIO events emitted)
"""

from unittest.mock import MagicMock, Mock

import pytest

from claude_mpm.hooks.claude_hooks.auto_pause_handler import AutoPauseHandler
from claude_mpm.hooks.claude_hooks.event_handlers import EventHandlers


class TestAutoPauseDisabledIntegration:
    """Confirm threshold crossings never pause through the event-handler path."""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary project directory."""
        project_path = tmp_path / "test_project"
        project_path.mkdir()
        (project_path / ".claude-mpm").mkdir()
        (project_path / ".claude-mpm" / "state").mkdir()
        (project_path / ".claude-mpm" / "sessions").mkdir()
        return project_path

    @pytest.fixture
    def mock_hook_handler(self, temp_project):
        """Create a mock hook handler with an auto-pause handler attached."""
        handler = MagicMock()
        handler.auto_pause_handler = AutoPauseHandler(temp_project)
        handler._git_branch_cache = {}
        handler._git_branch_cache_time = {}
        handler._emit_socketio_event = MagicMock()
        handler.pending_prompts = {}
        handler.delegation_requests = {}
        return handler

    @pytest.fixture
    def event_handlers(self, mock_hook_handler):
        """Create event handlers instance."""
        return EventHandlers(mock_hook_handler)

    def test_threshold_crossing_never_activates_pause(
        self, event_handlers, mock_hook_handler, temp_project
    ):
        """Crossing 90% reports the threshold but never activates a pause."""
        auto_pause = mock_hook_handler.auto_pause_handler
        usage = {
            "input_tokens": 160000,
            "output_tokens": 20000,  # 180k = 90%
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        }
        threshold = auto_pause.on_usage_update(usage)

        # Metering still reports the crossing...
        assert threshold == "auto_pause"
        # ...but the pause is never activated.
        assert not auto_pause.is_pause_active()

        pause_file = temp_project / ".claude-mpm" / "sessions" / "ACTIVE-PAUSE.jsonl"
        assert not pause_file.exists()

    def test_no_recording_through_event_handlers_above_threshold(
        self, event_handlers, mock_hook_handler, temp_project
    ):
        """Even above 95%, event handlers record nothing (pause never active)."""
        auto_pause = mock_hook_handler.auto_pause_handler
        usage = {
            "input_tokens": 180000,
            "output_tokens": 10000,  # 190k = 95%
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        }
        threshold = auto_pause.on_usage_update(usage)
        assert threshold == "critical"
        assert not auto_pause.is_pause_active()

        # Drive a tool call, assistant response, and user prompt through handlers.
        event_handlers.handle_pre_tool_fast(
            {
                "tool_name": "Read",
                "tool_input": {"file_path": "/test/file.txt"},
                "session_id": "test-session-123",
                "cwd": str(temp_project),
            }
        )
        event_handlers.handle_assistant_response(
            {
                "response": "I've completed the task.",
                "session_id": "test-session-123",
                "cwd": str(temp_project),
            }
        )
        event_handlers.handle_user_prompt_fast(
            {
                "prompt": "Please continue.",
                "session_id": "test-session-123",
                "cwd": str(temp_project),
            }
        )

        # No ACTIVE-PAUSE.jsonl is ever created.
        pause_file = temp_project / ".claude-mpm" / "sessions" / "ACTIVE-PAUSE.jsonl"
        assert not pause_file.exists()

    def test_no_recording_when_below_threshold(
        self, event_handlers, mock_hook_handler, temp_project
    ):
        """Below threshold, actions are NOT recorded (pause never active)."""
        auto_pause = mock_hook_handler.auto_pause_handler
        assert not auto_pause.is_pause_active()

        event_handlers.handle_pre_tool_fast(
            {
                "tool_name": "Read",
                "tool_input": {"file_path": "/test/file.txt"},
                "session_id": "test-session-no-pause",
                "cwd": str(temp_project),
            }
        )

        pause_file = temp_project / ".claude-mpm" / "sessions" / "ACTIVE-PAUSE.jsonl"
        assert not pause_file.exists()

    def test_stop_event_creates_no_pause_session(
        self, event_handlers, mock_hook_handler, temp_project
    ):
        """A Stop event above threshold finalizes no pause (none was started)."""
        auto_pause = mock_hook_handler.auto_pause_handler
        usage = {
            "input_tokens": 162000,
            "output_tokens": 20000,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        }
        auto_pause.on_usage_update(usage)
        assert not auto_pause.is_pause_active()

        event_handlers.handle_stop_fast(
            {
                "session_id": "test-session-stop",
                "reason": "completed",
                "stop_type": "normal",
                "cwd": str(temp_project),
                "usage": usage,
            }
        )

        # No pause was active, so no ACTIVE-PAUSE.jsonl exists.
        pause_file = temp_project / ".claude-mpm" / "sessions" / "ACTIVE-PAUSE.jsonl"
        assert not pause_file.exists()

    def test_event_handling_still_flows(
        self, event_handlers, mock_hook_handler, temp_project
    ):
        """Disabling auto-pause must not break normal event handling."""
        auto_pause = mock_hook_handler.auto_pause_handler
        # Even if a recording call would raise, the handler must not break.
        auto_pause.on_tool_call = Mock(side_effect=RuntimeError("Test error"))

        usage = {
            "input_tokens": 160000,
            "output_tokens": 20000,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        }
        auto_pause.on_usage_update(usage)

        event_handlers.handle_pre_tool_fast(
            {
                "tool_name": "Read",
                "tool_input": {"file_path": "/test/file.txt"},
                "session_id": "error-test",
                "cwd": str(temp_project),
            }
        )

        # SocketIO event was still emitted (event flow intact).
        assert mock_hook_handler._emit_socketio_event.called
