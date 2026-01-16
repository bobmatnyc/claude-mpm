"""Tests for SessionContext."""

from datetime import datetime

import pytest

from claude_mpm.commander.session.context import Message, SessionContext


def test_session_context_initial_state():
    """Test that SessionContext initializes with correct defaults."""
    context = SessionContext()

    assert context.connected_instance is None
    assert context.messages == []
    assert not context.is_connected
    assert isinstance(context.session_id, str)
    assert isinstance(context.created_at, datetime)


def test_session_context_connect():
    """Test connecting to an instance."""
    context = SessionContext()

    context.connect_to("myapp")

    assert context.connected_instance == "myapp"
    assert context.is_connected


def test_session_context_disconnect():
    """Test disconnecting from an instance."""
    context = SessionContext()
    context.connect_to("myapp")

    context.disconnect()

    assert context.connected_instance is None
    assert not context.is_connected


def test_session_context_add_message():
    """Test adding messages to conversation history."""
    context = SessionContext()

    context.add_message("user", "Hello")
    context.add_message("assistant", "Hi there")

    assert len(context.messages) == 2
    assert context.messages[0].role == "user"
    assert context.messages[0].content == "Hello"
    assert context.messages[1].role == "assistant"
    assert context.messages[1].content == "Hi there"


def test_session_context_get_messages_for_llm():
    """Test converting messages to LLM format."""
    context = SessionContext()
    context.add_message("user", "Hello")
    context.add_message("assistant", "Hi")

    messages = context.get_messages_for_llm()

    assert len(messages) == 2
    assert messages[0] == {"role": "user", "content": "Hello"}
    assert messages[1] == {"role": "assistant", "content": "Hi"}


def test_session_context_clear_history():
    """Test clearing conversation history."""
    context = SessionContext()
    context.add_message("user", "Hello")
    context.add_message("assistant", "Hi")

    context.clear_history()

    assert len(context.messages) == 0


def test_message_creation():
    """Test Message dataclass creation."""
    msg = Message(role="user", content="Test message")

    assert msg.role == "user"
    assert msg.content == "Test message"
    assert isinstance(msg.timestamp, datetime)
