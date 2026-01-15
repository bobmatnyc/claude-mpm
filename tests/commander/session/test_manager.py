"""Tests for SessionManager."""

import pytest

from claude_mpm.commander.session.manager import SessionManager


def test_session_manager_initialization():
    """Test that SessionManager initializes with fresh context."""
    manager = SessionManager()

    assert manager.context is not None
    assert not manager.context.is_connected
    assert len(manager.context.messages) == 0


def test_session_manager_connect():
    """Test connecting to an instance."""
    manager = SessionManager()

    manager.connect_to("myapp")

    assert manager.context.is_connected
    assert manager.context.connected_instance == "myapp"


def test_session_manager_disconnect():
    """Test disconnecting from an instance."""
    manager = SessionManager()
    manager.connect_to("myapp")

    manager.disconnect()

    assert not manager.context.is_connected
    assert manager.context.connected_instance is None


def test_session_manager_add_user_message():
    """Test adding user messages."""
    manager = SessionManager()

    manager.add_user_message("Hello")

    assert len(manager.context.messages) == 1
    assert manager.context.messages[0].role == "user"
    assert manager.context.messages[0].content == "Hello"


def test_session_manager_add_assistant_message():
    """Test adding assistant messages."""
    manager = SessionManager()

    manager.add_assistant_message("Hi there")

    assert len(manager.context.messages) == 1
    assert manager.context.messages[0].role == "assistant"
    assert manager.context.messages[0].content == "Hi there"


def test_session_manager_clear_history():
    """Test clearing conversation history."""
    manager = SessionManager()
    manager.add_user_message("Hello")
    manager.add_assistant_message("Hi")

    manager.clear_history()

    assert len(manager.context.messages) == 0


def test_session_manager_reset():
    """Test resetting session to initial state."""
    manager = SessionManager()
    manager.connect_to("myapp")
    manager.add_user_message("Hello")

    old_context = manager.context
    manager.reset()

    assert manager.context is not old_context
    assert not manager.context.is_connected
    assert len(manager.context.messages) == 0
