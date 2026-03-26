"""Unit tests for channel data models."""

from __future__ import annotations

import time
import unittest

from claude_mpm.services.channels.models import (
    ChannelMessage,
    ChannelSession,
    MessageRole,
    SessionEvent,
    SessionState,
)


class TestSessionState(unittest.TestCase):
    """Tests for SessionState enum."""

    def test_all_states_have_string_values(self) -> None:
        expected = {"starting", "idle", "processing", "stopped"}
        actual = {s.value for s in SessionState}
        self.assertEqual(actual, expected)

    def test_stopped_state_value(self) -> None:
        self.assertEqual(SessionState.STOPPED.value, "stopped")

    def test_enum_members_accessible(self) -> None:
        self.assertIs(SessionState("idle"), SessionState.IDLE)


class TestMessageRole(unittest.TestCase):
    """Tests for MessageRole enum."""

    def test_roles(self) -> None:
        self.assertEqual(MessageRole.USER.value, "user")
        self.assertEqual(MessageRole.ASSISTANT.value, "assistant")
        self.assertEqual(MessageRole.SYSTEM.value, "system")
        self.assertEqual(MessageRole.TOOL.value, "tool")


class TestChannelMessage(unittest.TestCase):
    """Tests for ChannelMessage dataclass."""

    def _make_message(self, **kwargs) -> ChannelMessage:
        defaults = {
            "text": "hello",
            "session_name": "main",
            "channel": "terminal",
            "user_id": "user1",
            "user_display": "User One",
        }
        defaults.update(kwargs)
        return ChannelMessage(**defaults)

    def test_default_timestamp_is_set(self) -> None:
        before = time.time()
        msg = self._make_message()
        after = time.time()
        self.assertGreaterEqual(msg.timestamp, before)
        self.assertLessEqual(msg.timestamp, after)

    def test_optional_fields_default_to_none(self) -> None:
        msg = self._make_message()
        self.assertIsNone(msg.thread_id)
        self.assertIsNone(msg.message_id)
        self.assertIsNone(msg.reply_fn)

    def test_custom_thread_id(self) -> None:
        msg = self._make_message(thread_id="t123")
        self.assertEqual(msg.thread_id, "t123")


class TestChannelSession(unittest.TestCase):
    """Tests for ChannelSession dataclass."""

    def _make_session(self, **kwargs) -> ChannelSession:
        defaults = {
            "name": "testsession",
            "cwd": "/tmp",
            "created_by_channel": "terminal",
            "created_by_user": "user1",
        }
        defaults.update(kwargs)
        return ChannelSession(**defaults)

    def test_default_state_is_starting(self) -> None:
        sess = self._make_session()
        self.assertEqual(sess.state, SessionState.STARTING)

    def test_kuzu_namespace_auto_computed(self) -> None:
        sess = self._make_session()
        self.assertTrue(sess.kuzu_namespace.startswith("channel_terminal_"))

    def test_kuzu_namespace_deterministic(self) -> None:
        sess1 = self._make_session()
        sess2 = self._make_session()
        self.assertEqual(sess1.kuzu_namespace, sess2.kuzu_namespace)

    def test_add_participant(self) -> None:
        sess = self._make_session()
        sess.add_participant("telegram", "tg_user")
        self.assertIn("telegram:tg_user", sess.participants)

    def test_add_participant_no_duplicates(self) -> None:
        sess = self._make_session()
        sess.add_participant("terminal", "user1")
        sess.add_participant("terminal", "user1")
        count = sess.participants.count("terminal:user1")
        self.assertEqual(count, 1)

    def test_has_participant(self) -> None:
        sess = self._make_session()
        sess.add_participant("slack", "S001")
        self.assertTrue(sess.has_participant("slack", "S001"))
        self.assertFalse(sess.has_participant("slack", "S999"))

    def test_session_id_defaults_to_none(self) -> None:
        sess = self._make_session()
        self.assertIsNone(sess.session_id)

    def test_github_context_defaults_to_none(self) -> None:
        sess = self._make_session()
        self.assertIsNone(sess.github_context)


class TestSessionEvent(unittest.TestCase):
    """Tests for SessionEvent dataclass."""

    def test_basic_event(self) -> None:
        event = SessionEvent(
            session_name="main",
            event_type="user_message",
            data={"text": "hello"},
        )
        self.assertEqual(event.session_name, "main")
        self.assertEqual(event.event_type, "user_message")
        self.assertEqual(event.data["text"], "hello")

    def test_default_channel_and_user_id_empty(self) -> None:
        event = SessionEvent(
            session_name="s",
            event_type="state_change",
            data={},
        )
        self.assertEqual(event.channel, "")
        self.assertEqual(event.user_id, "")

    def test_timestamp_auto_set(self) -> None:
        before = time.time()
        event = SessionEvent(session_name="s", event_type="t", data={})
        self.assertGreaterEqual(event.timestamp, before)


if __name__ == "__main__":
    unittest.main()
