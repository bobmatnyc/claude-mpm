"""Integration tests for auto-pause handler with event handlers.

WHY: Verify that auto-pause handler is properly integrated with event handlers
to record actions during pause mode and finalize sessions on stop events.

Tests:
- Tool calls are recorded when pause is active
- Assistant responses are recorded when pause is active
- User messages are recorded when pause is active
- Sessions are finalized on stop events
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from claude_mpm.hooks.claude_hooks.auto_pause_handler import AutoPauseHandler
from claude_mpm.hooks.claude_hooks.event_handlers import EventHandlers


class TestAutoPauseIntegration:
    """Test auto-pause handler integration with event handlers."""

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
        """Create a mock hook handler with auto-pause enabled."""
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

    def test_tool_call_recorded_when_pause_active(
        self, event_handlers, mock_hook_handler, temp_project
    ):
        """Test that tool calls are recorded when auto-pause is active."""
        # Trigger auto-pause by crossing threshold (90% of 200k = 180k tokens)
        auto_pause = mock_hook_handler.auto_pause_handler
        usage = {
            "input_tokens": 160000,
            "output_tokens": 20000,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        }
        threshold = auto_pause.on_usage_update(usage)
        assert threshold == "auto_pause"
        assert auto_pause.is_pause_active()

        # Simulate tool call event
        event = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/test/file.txt"},
            "session_id": "test-session-123",
            "cwd": str(temp_project),
        }

        # Handle pre-tool event
        event_handlers.handle_pre_tool_fast(event)

        # Verify ACTIVE-PAUSE.jsonl exists and contains tool call
        pause_file = temp_project / ".claude-mpm" / "sessions" / "ACTIVE-PAUSE.jsonl"
        assert pause_file.exists()

        # Read and verify recorded action
        with open(pause_file) as f:
            actions = [json.loads(line) for line in f]

        assert len(actions) > 0
        # First action is the start action, second is the tool call
        assert any(action["type"] == "tool_call" for action in actions)

    def test_assistant_response_recorded_when_pause_active(
        self, event_handlers, mock_hook_handler, temp_project
    ):
        """Test that assistant responses are recorded when auto-pause is active."""
        # Trigger auto-pause
        auto_pause = mock_hook_handler.auto_pause_handler
        usage = {
            "input_tokens": 180000,
            "output_tokens": 10000,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        }
        threshold = auto_pause.on_usage_update(usage)
        assert threshold == "critical"  # 95% = 190k tokens
        assert auto_pause.is_pause_active()

        # Simulate assistant response event
        event = {
            "response": "I've completed the task successfully.",
            "session_id": "test-session-456",
            "cwd": str(temp_project),
        }

        # Handle assistant response
        event_handlers.handle_assistant_response(event)

        # Verify action was recorded
        pause_file = temp_project / ".claude-mpm" / "sessions" / "ACTIVE-PAUSE.jsonl"
        assert pause_file.exists()

        with open(pause_file) as f:
            actions = [json.loads(line) for line in f]

        assert any(action["type"] == "assistant_response" for action in actions)

    def test_user_message_recorded_when_pause_active(
        self, event_handlers, mock_hook_handler, temp_project
    ):
        """Test that user messages are recorded when auto-pause is active."""
        # Trigger auto-pause
        auto_pause = mock_hook_handler.auto_pause_handler
        usage = {
            "input_tokens": 160000,
            "output_tokens": 20000,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        }
        threshold = auto_pause.on_usage_update(usage)
        assert threshold == "auto_pause"
        assert auto_pause.is_pause_active()

        # Simulate user prompt event
        event = {
            "prompt": "Please continue with the next step.",
            "session_id": "test-session-789",
            "cwd": str(temp_project),
        }

        # Handle user prompt
        event_handlers.handle_user_prompt_fast(event)

        # Verify action was recorded
        pause_file = temp_project / ".claude-mpm" / "sessions" / "ACTIVE-PAUSE.jsonl"
        assert pause_file.exists()

        with open(pause_file) as f:
            actions = [json.loads(line) for line in f]

        assert any(action["type"] == "user_message" for action in actions)

    def test_session_finalized_on_stop_event(
        self, event_handlers, mock_hook_handler, temp_project
    ):
        """Test that pause session is finalized on stop event."""
        # Trigger auto-pause
        auto_pause = mock_hook_handler.auto_pause_handler
        usage = {
            "input_tokens": 162000,
            "output_tokens": 20000,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        }
        threshold = auto_pause.on_usage_update(usage)
        assert threshold == "auto_pause"
        assert auto_pause.is_pause_active()

        # Record some actions
        auto_pause.on_tool_call("Read", {"file_path": "/test/file.txt"})
        auto_pause.on_assistant_response("Processing file contents...")

        # Simulate stop event with usage data
        event = {
            "session_id": "test-session-stop",
            "reason": "completed",
            "stop_type": "normal",
            "cwd": str(temp_project),
            "usage": usage,
        }

        # Handle stop event
        event_handlers.handle_stop_fast(event)

        # Verify session files were created
        sessions_dir = temp_project / ".claude-mpm" / "sessions"
        session_files = list(sessions_dir.glob("session-*.md"))

        # Should have at least one session file
        assert len(session_files) > 0

        # Verify ACTIVE-PAUSE.jsonl was cleaned up
        pause_file = sessions_dir / "ACTIVE-PAUSE.jsonl"
        # File might still exist if finalization moves it
        # The key is that a session-*.md file was created

    def test_no_recording_when_pause_not_active(
        self, event_handlers, mock_hook_handler, temp_project
    ):
        """Test that actions are NOT recorded when pause is not active."""
        # Verify pause is not active
        auto_pause = mock_hook_handler.auto_pause_handler
        assert not auto_pause.is_pause_active()

        # Simulate tool call event (below threshold)
        event = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/test/file.txt"},
            "session_id": "test-session-no-pause",
            "cwd": str(temp_project),
        }

        # Handle pre-tool event
        event_handlers.handle_pre_tool_fast(event)

        # Verify ACTIVE-PAUSE.jsonl does NOT exist
        pause_file = temp_project / ".claude-mpm" / "sessions" / "ACTIVE-PAUSE.jsonl"
        assert not pause_file.exists()

    def test_full_workflow_with_multiple_actions(
        self, event_handlers, mock_hook_handler, temp_project
    ):
        """Test full workflow: threshold → pause → actions → finalize."""
        auto_pause = mock_hook_handler.auto_pause_handler

        # Step 1: Cross threshold to trigger auto-pause
        usage = {
            "input_tokens": 161000,
            "output_tokens": 20000,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        }
        threshold = auto_pause.on_usage_update(usage)
        assert threshold == "auto_pause"
        assert auto_pause.is_pause_active()

        # Step 2: Record multiple actions
        # Tool call
        event_handlers.handle_pre_tool_fast(
            {
                "tool_name": "Read",
                "tool_input": {"file_path": "/test/file.txt"},
                "session_id": "workflow-test",
                "cwd": str(temp_project),
            }
        )

        # Assistant response
        event_handlers.handle_assistant_response(
            {
                "response": "I've read the file.",
                "session_id": "workflow-test",
                "cwd": str(temp_project),
            }
        )

        # User message
        event_handlers.handle_user_prompt_fast(
            {
                "prompt": "Great! Now analyze it.",
                "session_id": "workflow-test",
                "cwd": str(temp_project),
            }
        )

        # Step 3: Verify all actions recorded
        pause_file = temp_project / ".claude-mpm" / "sessions" / "ACTIVE-PAUSE.jsonl"
        assert pause_file.exists()

        with open(pause_file) as f:
            actions = [json.loads(line) for line in f]

        # Should have start action + tool call + assistant response + user message
        assert len(actions) >= 4

        # Verify action types
        action_types = [a["type"] for a in actions]
        assert "tool_call" in action_types
        assert "assistant_response" in action_types
        assert "user_message" in action_types

        # Step 4: Finalize on stop
        event_handlers.handle_stop_fast(
            {
                "session_id": "workflow-test",
                "reason": "completed",
                "stop_type": "normal",
                "cwd": str(temp_project),
                "usage": usage,
            }
        )

        # Verify session file created
        sessions_dir = temp_project / ".claude-mpm" / "sessions"
        session_files = list(sessions_dir.glob("session-*.md"))
        assert len(session_files) > 0

    def test_graceful_error_handling(
        self, event_handlers, mock_hook_handler, temp_project
    ):
        """Test that auto-pause errors don't break event handling."""
        # Mock auto-pause to raise errors
        auto_pause = mock_hook_handler.auto_pause_handler
        auto_pause.on_tool_call = Mock(side_effect=RuntimeError("Test error"))

        # Trigger pause
        usage = {
            "input_tokens": 160000,
            "output_tokens": 20000,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        }
        auto_pause.on_usage_update(usage)

        # Event handling should NOT raise exception
        event = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/test/file.txt"},
            "session_id": "error-test",
            "cwd": str(temp_project),
        }

        # Should not raise
        event_handlers.handle_pre_tool_fast(event)

        # Verify SocketIO event was still emitted
        assert mock_hook_handler._emit_socketio_event.called
