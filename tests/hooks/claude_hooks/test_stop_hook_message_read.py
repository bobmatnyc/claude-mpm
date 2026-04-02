"""Tests for stop hook marking unread messages as read after notification.

Verifies the fix for #413: Stop hook recounts same stale messages as unread
on every session stop.
"""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _make_fake_message(msg_id: str, from_project: str = "/projects/aria"):
    """Create a minimal fake message object for testing."""
    msg = MagicMock()
    msg.id = msg_id
    msg.from_project = from_project
    msg.priority = "normal"
    msg.type = "notification"
    msg.subject = "Test message"
    msg.body = "Test body"
    msg.status = "unread"
    msg.created_at = datetime.now(UTC)
    return msg


class TestStopHookMarksMessagesRead:
    """Verify that handle_stop_fast marks notified messages as read."""

    @patch("claude_mpm.core.unified_paths.UnifiedPathManager")
    @patch("claude_mpm.services.communication.message_service.MessageService")
    def test_stop_hook_marks_unread_messages_as_read(
        self, MockMessageService, MockPathManager
    ):
        """After notifying about unread messages, they should be marked read."""
        from src.claude_mpm.hooks.claude_hooks.event_handlers import EventHandlers

        # Setup mocks
        mock_path_mgr = MockPathManager.return_value
        mock_path_mgr.project_root = Path("/projects/test-project")

        msg1 = _make_fake_message("msg-001", "/projects/aria")
        msg2 = _make_fake_message("msg-002", "/projects/mcp-services")

        mock_service = MockMessageService.return_value
        mock_service.list_messages.return_value = [msg1, msg2]
        mock_service.read_message.return_value = None

        # Create EventHandlers with a mock hook_handler
        mock_hook_handler = MagicMock()
        handlers = EventHandlers(mock_hook_handler)

        # Build a stop event (not re-triggered)
        event = {
            "session_id": "test-session",
            "reason": "completed",
            "cwd": "/projects/test-project",
        }

        # Call handle_stop_fast
        result = handlers.handle_stop_fast(event)

        # Should block the stop
        assert result is not None
        assert result["decision"] == "block"
        assert "2 unread" in result["reason"]

        # Crucially: read_message should have been called for both messages
        assert mock_service.read_message.call_count == 2
        mock_service.read_message.assert_any_call("msg-001")
        mock_service.read_message.assert_any_call("msg-002")

    @patch("claude_mpm.core.unified_paths.UnifiedPathManager")
    @patch("claude_mpm.services.communication.message_service.MessageService")
    def test_stop_hook_no_block_when_no_unread_messages(
        self, MockMessageService, MockPathManager
    ):
        """When there are no unread messages, stop should not be blocked."""
        from src.claude_mpm.hooks.claude_hooks.event_handlers import EventHandlers

        mock_path_mgr = MockPathManager.return_value
        mock_path_mgr.project_root = Path("/projects/test-project")

        mock_service = MockMessageService.return_value
        mock_service.list_messages.return_value = []

        mock_hook_handler = MagicMock()
        handlers = EventHandlers(mock_hook_handler)

        event = {
            "session_id": "test-session",
            "reason": "completed",
            "cwd": "/projects/test-project",
        }

        result = handlers.handle_stop_fast(event)

        # Should not block
        assert result is None
        # read_message should NOT have been called
        mock_service.read_message.assert_not_called()

    @patch("claude_mpm.core.unified_paths.UnifiedPathManager")
    @patch("claude_mpm.services.communication.message_service.MessageService")
    def test_stop_hook_skips_when_stop_hook_active(
        self, MockMessageService, MockPathManager
    ):
        """When stop_hook_active is set, messages should not be re-checked."""
        from src.claude_mpm.hooks.claude_hooks.event_handlers import EventHandlers

        mock_path_mgr = MockPathManager.return_value
        mock_path_mgr.project_root = Path("/projects/test-project")

        msg1 = _make_fake_message("msg-001")
        mock_service = MockMessageService.return_value
        mock_service.list_messages.return_value = [msg1]

        mock_hook_handler = MagicMock()
        handlers = EventHandlers(mock_hook_handler)

        event = {
            "session_id": "test-session",
            "reason": "completed",
            "cwd": "/projects/test-project",
            "stop_hook_active": True,  # Re-triggered stop
        }

        result = handlers.handle_stop_fast(event)

        # Should not block (stop_hook_active prevents infinite loop)
        assert result is None
        # read_message should NOT have been called
        mock_service.read_message.assert_not_called()

    @patch("claude_mpm.core.unified_paths.UnifiedPathManager")
    @patch("claude_mpm.services.communication.message_service.MessageService")
    def test_stop_hook_resilient_to_read_message_failure(
        self, MockMessageService, MockPathManager
    ):
        """If marking messages as read fails, the stop should still be blocked."""
        from src.claude_mpm.hooks.claude_hooks.event_handlers import EventHandlers

        mock_path_mgr = MockPathManager.return_value
        mock_path_mgr.project_root = Path("/projects/test-project")

        msg1 = _make_fake_message("msg-001")
        mock_service = MockMessageService.return_value
        mock_service.list_messages.return_value = [msg1]
        mock_service.read_message.side_effect = Exception("DB error")

        mock_hook_handler = MagicMock()
        handlers = EventHandlers(mock_hook_handler)

        event = {
            "session_id": "test-session",
            "reason": "completed",
            "cwd": "/projects/test-project",
        }

        result = handlers.handle_stop_fast(event)

        # Should still block despite read_message failure
        assert result is not None
        assert result["decision"] == "block"

    @patch("claude_mpm.core.unified_paths.UnifiedPathManager")
    @patch("claude_mpm.services.communication.message_service.MessageService")
    def test_second_stop_does_not_recount_after_messages_marked_read(
        self, MockMessageService, MockPathManager
    ):
        """Simulate two stops: first finds unread, second finds none.

        This is the core regression test for #413.
        """
        from src.claude_mpm.hooks.claude_hooks.event_handlers import EventHandlers

        mock_path_mgr = MockPathManager.return_value
        mock_path_mgr.project_root = Path("/projects/test-project")

        msg1 = _make_fake_message("msg-001")
        msg2 = _make_fake_message("msg-002")

        mock_service = MockMessageService.return_value
        # First call returns unread messages, second call returns empty
        # (because they were marked as read by the first stop)
        mock_service.list_messages.side_effect = [
            [msg1, msg2],  # First stop: 2 unread
            [],  # Second stop: 0 unread (marked read)
        ]

        mock_hook_handler = MagicMock()
        handlers = EventHandlers(mock_hook_handler)

        event = {
            "session_id": "test-session",
            "reason": "completed",
            "cwd": "/projects/test-project",
        }

        # First stop: should block with unread messages
        result1 = handlers.handle_stop_fast(event)
        assert result1 is not None
        assert result1["decision"] == "block"
        assert mock_service.read_message.call_count == 2

        # Second stop: should NOT block (messages were marked read)
        result2 = handlers.handle_stop_fast(event)
        assert result2 is None
