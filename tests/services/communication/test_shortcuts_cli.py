"""
Tests for message shortcut CLI integration.

Covers:
- shortcut add/list/remove/resolve via the MessagesCommand handler
- message send using a shortcut name instead of a full path
- Error case: unknown shortcut name in send
"""

import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.cli.commands.messages import MessagesCommand
from claude_mpm.cli.shared.base_command import CommandResult
from claude_mpm.services.communication.shortcuts_service import ShortcutsService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_args(**kwargs) -> argparse.Namespace:
    """Build a minimal Namespace with sensible defaults."""
    defaults = {
        "message_command": None,
        "shortcut_command": None,
        "debug": False,
        "verbose": False,
        "quiet": False,
        "config": None,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


@pytest.fixture
def tmp_shortcuts_file(tmp_path) -> Path:
    return tmp_path / "shortcuts.json"


@pytest.fixture
def shortcuts_service(tmp_shortcuts_file) -> ShortcutsService:
    return ShortcutsService(shortcuts_file=tmp_shortcuts_file)


@pytest.fixture
def command(shortcuts_service) -> MessagesCommand:
    """Return a MessagesCommand with patched dependencies."""
    with (
        patch("claude_mpm.cli.commands.messages.UnifiedPathManager"),
        patch("claude_mpm.cli.commands.messages.MessageService"),
        patch(
            "claude_mpm.cli.commands.messages.ShortcutsService",
            return_value=shortcuts_service,
        ),
    ):
        cmd = MessagesCommand()
    return cmd


# ---------------------------------------------------------------------------
# ShortcutsService unit tests
# ---------------------------------------------------------------------------


class TestShortcutsService:
    def test_add_and_resolve(self, tmp_path, tmp_shortcuts_file):
        svc = ShortcutsService(shortcuts_file=tmp_shortcuts_file)
        assert svc.add_shortcut("myproj", str(tmp_path))
        assert svc.get_shortcut_path("myproj") == str(tmp_path)

    def test_list_shortcuts(self, tmp_path, tmp_shortcuts_file):
        svc = ShortcutsService(shortcuts_file=tmp_shortcuts_file)
        svc.add_shortcut("a", str(tmp_path))
        shortcuts = svc.list_shortcuts()
        assert "a" in shortcuts

    def test_remove_shortcut(self, tmp_path, tmp_shortcuts_file):
        svc = ShortcutsService(shortcuts_file=tmp_shortcuts_file)
        svc.add_shortcut("proj", str(tmp_path))
        assert svc.remove_shortcut("proj")
        assert svc.get_shortcut_path("proj") is None

    def test_remove_nonexistent(self, tmp_shortcuts_file):
        svc = ShortcutsService(shortcuts_file=tmp_shortcuts_file)
        assert not svc.remove_shortcut("does-not-exist")

    def test_add_invalid_name(self, tmp_path, tmp_shortcuts_file):
        svc = ShortcutsService(shortcuts_file=tmp_shortcuts_file)
        assert not svc.add_shortcut("bad name!", str(tmp_path))

    def test_add_nonexistent_path(self, tmp_shortcuts_file):
        svc = ShortcutsService(shortcuts_file=tmp_shortcuts_file)
        assert not svc.add_shortcut("proj", "/does/not/exist/at/all")

    def test_resolve_unknown_returns_none(self, tmp_shortcuts_file):
        svc = ShortcutsService(shortcuts_file=tmp_shortcuts_file)
        assert svc.get_shortcut_path("unknown") is None


# ---------------------------------------------------------------------------
# CLI handler tests (via MessagesCommand._handle_shortcut)
# ---------------------------------------------------------------------------


class TestShortcutCLIHandlers:
    def test_shortcut_add_success(self, command, tmp_path):
        args = _make_args(
            message_command="shortcut",
            shortcut_command="add",
            name="myapp",
            path=str(tmp_path),
        )
        result = command._handle_shortcut(args)
        assert result.success
        assert command.shortcuts_service.get_shortcut_path("myapp") == str(tmp_path)

    def test_shortcut_add_bad_path(self, command):
        args = _make_args(
            message_command="shortcut",
            shortcut_command="add",
            name="myapp",
            path="/this/does/not/exist",
        )
        result = command._handle_shortcut(args)
        assert not result.success

    def test_shortcut_list_empty(self, command):
        args = _make_args(
            message_command="shortcut",
            shortcut_command="list",
        )
        result = command._handle_shortcut(args)
        assert result.success
        assert "No shortcuts" in result.message

    def test_shortcut_list_with_entries(self, command, tmp_path):
        command.shortcuts_service.add_shortcut("proj1", str(tmp_path))
        args = _make_args(
            message_command="shortcut",
            shortcut_command="list",
        )
        result = command._handle_shortcut(args)
        assert result.success
        assert "1" in result.message

    def test_shortcut_remove_existing(self, command, tmp_path):
        command.shortcuts_service.add_shortcut("removeme", str(tmp_path))
        args = _make_args(
            message_command="shortcut",
            shortcut_command="remove",
            name="removeme",
        )
        result = command._handle_shortcut(args)
        assert result.success
        assert command.shortcuts_service.get_shortcut_path("removeme") is None

    def test_shortcut_remove_nonexistent(self, command):
        args = _make_args(
            message_command="shortcut",
            shortcut_command="remove",
            name="ghost",
        )
        result = command._handle_shortcut(args)
        assert not result.success

    def test_shortcut_resolve_existing(self, command, tmp_path):
        command.shortcuts_service.add_shortcut("web", str(tmp_path))
        args = _make_args(
            message_command="shortcut",
            shortcut_command="resolve",
            name="web",
        )
        result = command._handle_shortcut(args)
        assert result.success
        assert result.message == str(tmp_path)

    def test_shortcut_resolve_unknown(self, command):
        args = _make_args(
            message_command="shortcut",
            shortcut_command="resolve",
            name="nope",
        )
        result = command._handle_shortcut(args)
        assert not result.success

    def test_shortcut_no_subcommand(self, command):
        args = _make_args(
            message_command="shortcut",
            shortcut_command=None,
        )
        result = command._handle_shortcut(args)
        assert not result.success

    def test_shortcut_unknown_subcommand(self, command):
        args = _make_args(
            message_command="shortcut",
            shortcut_command="fly",
        )
        result = command._handle_shortcut(args)
        assert not result.success


# ---------------------------------------------------------------------------
# message send with shortcut resolution
# ---------------------------------------------------------------------------


class TestSendWithShortcut:
    """Test that _send_message resolves shortcuts when to_project is not absolute."""

    def _make_send_args(self, to_project, body="Hello"):
        return _make_args(
            message_command="send",
            to_project=to_project,
            body=body,
            body_file=None,
            subject="Test",
            to_agent="pm",
            type="task",
            priority="normal",
            from_agent="pm",
            attachments=None,
        )

    def test_send_with_shortcut_name(self, command, tmp_path):
        """send resolves a registered shortcut and proceeds with the real path."""
        # Create an MPM project directory
        mpm_dir = tmp_path / ".claude-mpm"
        mpm_dir.mkdir()

        command.shortcuts_service.add_shortcut("target", str(tmp_path))

        # Mock message_service.send_message to avoid real I/O
        fake_message = MagicMock()
        fake_message.id = "msg-001"
        fake_message.to_agent = "pm"
        fake_message.priority = "normal"
        command.message_service.send_message.return_value = fake_message

        args = self._make_send_args("target")
        result = command._send_message(args)

        assert result.success
        # Verify the service was called with the resolved path
        call_kwargs = command.message_service.send_message.call_args
        assert call_kwargs is not None
        assert str(tmp_path) in call_kwargs[1].get(
            "to_project", call_kwargs[0][0] if call_kwargs[0] else ""
        ) or any(str(tmp_path) in str(a) for a in call_kwargs[0])

    def test_send_with_unknown_shortcut(self, command):
        """send returns error when to_project is not absolute and not a known shortcut."""
        args = self._make_send_args("unknownshortcut")
        result = command._send_message(args)
        assert not result.success
        assert "unknownshortcut" in result.message

    def test_send_with_absolute_path(self, command, tmp_path):
        """send with an absolute path bypasses shortcut resolution entirely."""
        mpm_dir = tmp_path / ".claude-mpm"
        mpm_dir.mkdir()

        fake_message = MagicMock()
        fake_message.id = "msg-002"
        fake_message.to_agent = "pm"
        fake_message.priority = "normal"
        command.message_service.send_message.return_value = fake_message

        args = self._make_send_args(str(tmp_path))
        result = command._send_message(args)
        assert result.success

    def test_send_shortcut_name_relative_path_rejected(self, command):
        """A relative path that is not a shortcut name is rejected."""
        args = self._make_send_args("relative/path")
        result = command._send_message(args)
        assert not result.success
