"""Tests for the Messaging MCP server."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claude_mpm.mcp.messaging_server import MessagingMCPServer, _message_to_dict

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_message(**kwargs):
    """Return a mock Message object."""
    msg = MagicMock()
    msg.id = kwargs.get("id", "msg-001")
    msg.from_project = kwargs.get("from_project", "/src")
    msg.from_agent = kwargs.get("from_agent", "pm")
    msg.to_project = kwargs.get("to_project", "/dst")
    msg.to_agent = kwargs.get("to_agent", "engineer")
    msg.type = kwargs.get("type", "task")
    msg.priority = kwargs.get("priority", "normal")
    msg.created_at = kwargs.get("created_at", "2024-01-01T00:00:00")
    msg.status = kwargs.get("status", "unread")
    msg.reply_to = kwargs.get("reply_to")
    msg.subject = kwargs.get("subject", "Test subject")
    msg.body = kwargs.get("body", "Test body")
    msg.attachments = kwargs.get("attachments", [])
    msg.metadata = kwargs.get("metadata", {})
    # make asdict-like work via __dict__
    msg.__dict__.update(
        {
            "id": msg.id,
            "from_project": msg.from_project,
            "from_agent": msg.from_agent,
            "to_project": msg.to_project,
            "to_agent": msg.to_agent,
            "type": msg.type,
            "priority": msg.priority,
            "created_at": msg.created_at,
            "status": msg.status,
            "reply_to": msg.reply_to,
            "subject": msg.subject,
            "body": msg.body,
            "attachments": msg.attachments,
            "metadata": msg.metadata,
        }
    )
    return msg


@pytest.fixture()
def server():
    """Return a MessagingMCPServer with mocked services."""
    with (
        patch("claude_mpm.mcp.messaging_server.UnifiedPathManager") as mock_upm,
        patch("claude_mpm.mcp.messaging_server.MessageService") as mock_ms,
        patch("claude_mpm.mcp.messaging_server.ShortcutsService") as mock_ss,
    ):
        mock_upm.return_value.project_root = Path("/fake/project")
        srv = MessagingMCPServer()
        yield srv


# ---------------------------------------------------------------------------
# _message_to_dict
# ---------------------------------------------------------------------------


class TestMessageToDict:
    def test_converts_mock_message(self):
        msg = _make_message(id="abc", subject="hello")
        d = _message_to_dict(msg)
        assert d["id"] == "abc"
        assert d["subject"] == "hello"

    def test_isoformat_dates_converted(self):
        from datetime import datetime

        msg = _make_message()
        dt = datetime(2024, 6, 1, 12, 0, 0)
        msg.__dict__["created_at"] = dt
        d = _message_to_dict(msg)
        assert d["created_at"] == "2024-06-01T12:00:00"


# ---------------------------------------------------------------------------
# list_tools
# ---------------------------------------------------------------------------


class TestListTools:
    @pytest.mark.asyncio
    async def test_returns_ten_tools(self, server):
        expected = {
            "message_send",
            "message_list",
            "message_read",
            "message_archive",
            "message_reply",
            "message_check",
            "shortcut_add",
            "shortcut_list",
            "shortcut_remove",
            "shortcut_resolve",
        }
        # Verify each expected tool name has a corresponding handler method
        for name in expected:
            assert hasattr(server, f"_{name}"), f"Missing handler: _{name}"
        assert len(expected) == 10


# ---------------------------------------------------------------------------
# message_send
# ---------------------------------------------------------------------------


class TestMessageSend:
    @pytest.mark.asyncio
    async def test_send_with_absolute_path(self, server):
        msg = _make_message()
        server.messages.send_message = MagicMock(return_value=msg)

        result = await server._message_send(
            {
                "to_project": "/dst/project",
                "to_agent": "engineer",
                "message_type": "task",
                "subject": "Do work",
                "body": "Details here",
            }
        )

        assert result["ok"] is True
        server.messages.send_message.assert_called_once_with(
            "/dst/project",
            "engineer",
            "task",
            "Do work",
            "Details here",
            "normal",
            "pm",
        )

    @pytest.mark.asyncio
    async def test_send_with_shortcut_name(self, server):
        msg = _make_message()
        server.messages.send_message = MagicMock(return_value=msg)
        server.shortcuts.resolve_shortcut = MagicMock(return_value="/resolved/path")

        result = await server._message_send(
            {
                "to_project": "myproject",
                "to_agent": "qa",
                "message_type": "notification",
                "subject": "Hello",
                "body": "World",
            }
        )

        server.shortcuts.resolve_shortcut.assert_called_once_with("myproject")
        server.messages.send_message.assert_called_once_with(
            "/resolved/path",
            "qa",
            "notification",
            "Hello",
            "World",
            "normal",
            "pm",
        )
        assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_send_with_custom_priority_and_agent(self, server):
        msg = _make_message(priority="high")
        server.messages.send_message = MagicMock(return_value=msg)

        result = await server._message_send(
            {
                "to_project": "/dst",
                "to_agent": "devops",
                "message_type": "alert",
                "subject": "Urgent",
                "body": "Fix now",
                "priority": "high",
                "from_agent": "monitor",
            }
        )

        assert result["ok"] is True
        server.messages.send_message.assert_called_once_with(
            "/dst",
            "devops",
            "alert",
            "Urgent",
            "Fix now",
            "high",
            "monitor",
        )


# ---------------------------------------------------------------------------
# message_list
# ---------------------------------------------------------------------------


class TestMessageList:
    @pytest.mark.asyncio
    async def test_list_all(self, server):
        msgs = [_make_message(id=f"m{i}") for i in range(3)]
        server.messages.list_messages = MagicMock(return_value=msgs)

        result = await server._message_list({})

        assert result["count"] == 3
        assert len(result["messages"]) == 3
        server.messages.list_messages.assert_called_once_with(None, None)

    @pytest.mark.asyncio
    async def test_list_with_filters(self, server):
        server.messages.list_messages = MagicMock(return_value=[])

        await server._message_list({"status": "unread", "agent": "engineer"})

        server.messages.list_messages.assert_called_once_with("unread", "engineer")


# ---------------------------------------------------------------------------
# message_read
# ---------------------------------------------------------------------------


class TestMessageRead:
    @pytest.mark.asyncio
    async def test_read_existing(self, server):
        msg = _make_message(id="abc")
        server.messages.read_message = MagicMock(return_value=msg)

        result = await server._message_read({"message_id": "abc"})

        assert "message" in result
        assert result["message"]["id"] == "abc"

    @pytest.mark.asyncio
    async def test_read_missing(self, server):
        server.messages.read_message = MagicMock(return_value=None)

        result = await server._message_read({"message_id": "nonexistent"})

        assert "error" in result
        assert "nonexistent" in result["error"]


# ---------------------------------------------------------------------------
# message_archive
# ---------------------------------------------------------------------------


class TestMessageArchive:
    @pytest.mark.asyncio
    async def test_archive_success(self, server):
        server.messages.archive_message = MagicMock(return_value=True)

        result = await server._message_archive({"message_id": "msg-001"})

        assert result["ok"] is True
        assert result["message_id"] == "msg-001"

    @pytest.mark.asyncio
    async def test_archive_not_found(self, server):
        server.messages.archive_message = MagicMock(return_value=False)

        result = await server._message_archive({"message_id": "missing"})

        assert result["ok"] is False


# ---------------------------------------------------------------------------
# message_reply
# ---------------------------------------------------------------------------


class TestMessageReply:
    @pytest.mark.asyncio
    async def test_reply_success(self, server):
        msg = _make_message(id="reply-001")
        server.messages.reply_to_message = MagicMock(return_value=msg)

        result = await server._message_reply(
            {
                "original_message_id": "orig-001",
                "subject": "Re: Test",
                "body": "Got it",
            }
        )

        assert result["ok"] is True
        server.messages.reply_to_message.assert_called_once_with(
            "orig-001", "Re: Test", "Got it", "pm"
        )

    @pytest.mark.asyncio
    async def test_reply_original_not_found(self, server):
        server.messages.reply_to_message = MagicMock(return_value=None)

        result = await server._message_reply(
            {
                "original_message_id": "gone",
                "subject": "Re:",
                "body": "...",
            }
        )

        assert "error" in result
        assert "gone" in result["error"]


# ---------------------------------------------------------------------------
# message_check
# ---------------------------------------------------------------------------


class TestMessageCheck:
    @pytest.mark.asyncio
    async def test_check_returns_counts(self, server):
        server.messages.get_unread_count = MagicMock(return_value=5)
        server.messages.get_high_priority_messages = MagicMock(
            return_value=[_make_message(priority="high")]
        )

        result = await server._message_check({})

        assert result["unread_count"] == 5
        assert result["high_priority_count"] == 1
        server.messages.get_unread_count.assert_called_once_with(None)

    @pytest.mark.asyncio
    async def test_check_with_agent_filter(self, server):
        server.messages.get_unread_count = MagicMock(return_value=2)
        server.messages.get_high_priority_messages = MagicMock(return_value=[])

        await server._message_check({"agent": "engineer"})

        server.messages.get_unread_count.assert_called_once_with("engineer")


# ---------------------------------------------------------------------------
# shortcut_add
# ---------------------------------------------------------------------------


class TestShortcutAdd:
    @pytest.mark.asyncio
    async def test_add_success(self, server):
        server.shortcuts.add_shortcut = MagicMock(return_value=True)

        result = await server._shortcut_add({"name": "myproj", "path": "/some/path"})

        assert result["ok"] is True
        assert result["name"] == "myproj"

    @pytest.mark.asyncio
    async def test_add_failure(self, server):
        server.shortcuts.add_shortcut = MagicMock(return_value=False)

        result = await server._shortcut_add({"name": "bad!", "path": "/nope"})

        assert result["ok"] is False


# ---------------------------------------------------------------------------
# shortcut_list
# ---------------------------------------------------------------------------


class TestShortcutList:
    @pytest.mark.asyncio
    async def test_list_returns_dict(self, server):
        server.shortcuts.list_shortcuts = MagicMock(
            return_value={"a": "/path/a", "b": "/path/b"}
        )

        result = await server._shortcut_list({})

        assert result["count"] == 2
        assert result["shortcuts"]["a"] == "/path/a"


# ---------------------------------------------------------------------------
# shortcut_remove
# ---------------------------------------------------------------------------


class TestShortcutRemove:
    @pytest.mark.asyncio
    async def test_remove_success(self, server):
        server.shortcuts.remove_shortcut = MagicMock(return_value=True)

        result = await server._shortcut_remove({"name": "myproj"})

        assert result["ok"] is True
        assert result["name"] == "myproj"

    @pytest.mark.asyncio
    async def test_remove_not_found(self, server):
        server.shortcuts.remove_shortcut = MagicMock(return_value=False)

        result = await server._shortcut_remove({"name": "ghost"})

        assert result["ok"] is False


# ---------------------------------------------------------------------------
# shortcut_resolve
# ---------------------------------------------------------------------------


class TestShortcutResolve:
    @pytest.mark.asyncio
    async def test_resolve_known_shortcut(self, server):
        server.shortcuts.resolve_shortcut = MagicMock(return_value="/real/path")
        server.shortcuts.is_shortcut = MagicMock(return_value=True)

        result = await server._shortcut_resolve({"name_or_path": "myproj"})

        assert result["resolved"] == "/real/path"
        assert result["was_shortcut"] is True

    @pytest.mark.asyncio
    async def test_resolve_direct_path(self, server):
        server.shortcuts.resolve_shortcut = MagicMock(return_value="/direct/path")
        server.shortcuts.is_shortcut = MagicMock(return_value=False)

        result = await server._shortcut_resolve({"name_or_path": "/direct/path"})

        assert result["resolved"] == "/direct/path"
        assert result["was_shortcut"] is False


# ---------------------------------------------------------------------------
# dispatch_tool error path
# ---------------------------------------------------------------------------


class TestDispatchTool:
    @pytest.mark.asyncio
    async def test_unknown_tool_raises(self, server):
        with pytest.raises(ValueError, match="Unknown tool"):
            await server._dispatch_tool("nonexistent_tool", {})
