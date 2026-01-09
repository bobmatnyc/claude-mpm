"""Unit tests for autotodos working_dir parameter fix.

Tests verify that:
1. get_pending_todos() accepts working_dir parameter
2. working_dir is used to construct event log path correctly
3. SessionStart hook passes working_dir from event to get_pending_todos()
"""

import tempfile
from pathlib import Path

import pytest

from claude_mpm.cli.commands.autotodos import get_pending_todos
from claude_mpm.hooks.claude_hooks.event_handlers import EventHandlers
from claude_mpm.services.event_log import EventLog


def test_get_pending_todos_accepts_working_dir():
    """Test that get_pending_todos() accepts working_dir parameter."""
    # Should not raise an error
    todos = get_pending_todos(max_todos=5, working_dir=None)
    assert isinstance(todos, list)


def test_get_pending_todos_uses_working_dir():
    """Test that working_dir is used to construct event log path."""
    # Create a temporary directory with event log
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        event_log_dir = tmpdir_path / ".claude-mpm"
        event_log_dir.mkdir(parents=True)
        event_log_path = event_log_dir / "event_log.json"

        # Create an event log with a test error
        event_log = EventLog(log_file=event_log_path)
        event_log.append_event(
            event_type="autotodo.error",
            payload={
                "error_type": "test_error",
                "hook_type": "SessionStart",
                "details": "Test error for working_dir test",
                "full_message": "This is a test error",
                "suggested_fix": "Fix the test error",
            },
            status="pending",
        )

        # Get pending todos using working_dir parameter
        todos = get_pending_todos(max_todos=10, working_dir=tmpdir_path)

        # Should find the test error
        assert len(todos) > 0
        assert todos[0]["content"].startswith("Fix SessionStart hook error")
        assert "test_error" in todos[0]["metadata"]["error_type"]


def test_session_start_passes_working_dir():
    """Test that SessionStart hook passes working_dir to get_pending_todos()."""
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        event_log_dir = tmpdir_path / ".claude-mpm"
        event_log_dir.mkdir(parents=True)
        event_log_path = event_log_dir / "event_log.json"

        # Create an event log with a test error
        event_log = EventLog(log_file=event_log_path)
        event_log.append_event(
            event_type="autotodo.error",
            payload={
                "error_type": "hook_error",
                "hook_type": "SessionStart",
                "details": "Test hook error",
                "full_message": "Test error message",
            },
            status="pending",
        )

        # Track emitted events
        emitted_events = []

        class MockHookHandler:
            def __init__(self):
                self._git_branch_cache = {}
                self._git_branch_cache_time = {}

            def _emit_socketio_event(self, namespace, event_name, data):
                emitted_events.append({"event": event_name, "data": data})

        # Create handler and trigger SessionStart with working directory
        handler = EventHandlers(MockHookHandler())
        event = {"session_id": "test-session-working-dir", "cwd": str(tmpdir_path)}
        handler.handle_session_start_fast(event)

        # Verify event was emitted with autotodos from the correct directory
        assert len(emitted_events) == 1
        data = emitted_events[0]["data"]

        # Check if autotodos were included
        assert "pending_autotodos" in data
        assert len(data["pending_autotodos"]) > 0
        assert data["pending_autotodos"][0]["content"].startswith(
            "Fix SessionStart hook error"
        )


def test_working_dir_none_uses_cwd():
    """Test that working_dir=None falls back to Path.cwd()."""
    # Should not raise an error and should use current working directory
    todos = get_pending_todos(max_todos=5, working_dir=None)
    assert isinstance(todos, list)
    # Result may vary depending on whether event log exists in current directory


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
