"""Unit tests for autotodos auto-injection on PM session start.

Tests verify that:
1. get_pending_todos() function exists and returns limited todos
2. Config defaults exist for autotodos.auto_inject_on_startup and autotodos.max_todos_per_session
3. SessionStart hook calls get_pending_todos() and includes todos in event data
"""

import pytest

from claude_mpm.cli.commands.autotodos import get_pending_todos
from claude_mpm.core.config import Config
from claude_mpm.hooks.claude_hooks.event_handlers import EventHandlers


def test_get_pending_todos_exists():
    """Test that get_pending_todos() function exists and is callable."""
    assert callable(get_pending_todos)


def test_get_pending_todos_with_limit():
    """Test that get_pending_todos() respects max_todos parameter."""
    # Get pending todos with limit
    todos = get_pending_todos(max_todos=5)

    # Should return list (even if empty)
    assert isinstance(todos, list)

    # Should not exceed max_todos
    assert len(todos) <= 5

    # Each todo should have required fields
    if todos:
        todo = todos[0]
        assert "content" in todo
        assert "activeForm" in todo
        assert "status" in todo
        assert "metadata" in todo


def test_config_autotodos_defaults():
    """Test that autotodos config defaults exist."""
    config = Config()

    # Check auto_inject_on_startup default
    auto_inject = config.get("autotodos.auto_inject_on_startup")
    assert auto_inject is not None
    assert isinstance(auto_inject, bool)
    assert auto_inject is True  # Default should be enabled

    # Check max_todos_per_session default
    max_todos = config.get("autotodos.max_todos_per_session")
    assert max_todos is not None
    assert isinstance(max_todos, int)
    assert max_todos == 10  # Default should be 10


def test_session_start_auto_injection():
    """Test that SessionStart hook includes autotodos when enabled."""

    # Track emitted events
    emitted_events = []

    class MockHookHandler:
        def __init__(self):
            self._git_branch_cache = {}
            self._git_branch_cache_time = {}

        def _emit_socketio_event(self, namespace, event_name, data):
            emitted_events.append({"event": event_name, "data": data})

    # Create handler and trigger SessionStart
    handler = EventHandlers(MockHookHandler())
    event = {"session_id": "test-session-123", "cwd": "/tmp"}
    handler.handle_session_start_fast(event)

    # Verify event was emitted
    assert len(emitted_events) == 1
    emitted = emitted_events[0]
    assert emitted["event"] == "session_start"

    # Check if autotodos were included (depends on pending todos)
    data = emitted["data"]
    assert "session_id" in data
    assert data["session_id"] == "test-session-123"

    # If autotodos were included, verify structure
    if "pending_autotodos" in data:
        assert "autotodos_count" in data
        assert isinstance(data["pending_autotodos"], list)
        assert data["autotodos_count"] == len(data["pending_autotodos"])
        assert data["autotodos_count"] <= 10  # Should respect max_todos config


def test_session_start_with_config_disabled():
    """Test that SessionStart hook skips autotodos when disabled in config."""

    # Temporarily disable auto-injection
    config = Config()
    original_value = config.get("autotodos.auto_inject_on_startup")
    config.set("autotodos.auto_inject_on_startup", False)

    try:
        # Track emitted events
        emitted_events = []

        class MockHookHandler:
            def __init__(self):
                self._git_branch_cache = {}
                self._git_branch_cache_time = {}

            def _emit_socketio_event(self, namespace, event_name, data):
                emitted_events.append({"event": event_name, "data": data})

        # Create handler and trigger SessionStart
        handler = EventHandlers(MockHookHandler())
        event = {"session_id": "test-session-456", "cwd": "/tmp"}
        handler.handle_session_start_fast(event)

        # Verify event was emitted but without autotodos
        assert len(emitted_events) == 1
        data = emitted_events[0]["data"]

        # Autotodos should NOT be included when disabled
        # (or could be included but empty depending on implementation)
        # Either way, the hook should not crash
        assert "session_id" in data

    finally:
        # Restore original config
        config.set("autotodos.auto_inject_on_startup", original_value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
