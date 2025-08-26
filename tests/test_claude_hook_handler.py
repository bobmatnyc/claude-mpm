#!/usr/bin/env python3
"""Tests for Claude hook handler security features."""

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

# Add src to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler


class TestClaudeHookHandlerSecurity(unittest.TestCase):
    """Test security features of the Claude hook handler."""

    def setUp(self):
        """Set up test environment."""
        self.handler = ClaudeHookHandler()
        self.working_dir = "/Users/test/project"

    def create_event(self, hook_type, tool_name=None, tool_input=None):
        """Create a test event."""
        event = {
            "hook_event_name": hook_type,
            "cwd": self.working_dir,
            "session_id": "test-session-123",
        }
        if tool_name:
            event["tool_name"] = tool_name
        if tool_input:
            event["tool_input"] = tool_input
        return event

    @patch("builtins.print")
    @patch("sys.exit")
    def test_write_within_working_dir_allowed(self, mock_print):
        """Test that writes within working directory are allowed."""
        event = self.create_event(
            "PreToolUse",
            "Write",
            {"file_path": f"{self.working_dir}/test.txt", "content": "test"},
        )
        self.handler.event = event
        self.handler.hook_type = "PreToolUse"

        self.handler._handle_pre_tool_use()

        # Should call continue
        mock_print.assert_called_once()
        output = json.loads(mock_print.call_args[0][0])
        self.assertEqual(output["action"], "continue")
        self.assert_called_with(0)

    @patch("builtins.print")
    @patch("sys.exit")
    @patch("claude_mpm.hooks.claude_hooks.hook_handler.logger")
    def test_write_outside_working_dir_blocked(
        self, mock_logger, mock_exit, mock_print
    ):
        """Test that writes outside working directory are blocked."""
        event = self.create_event(
            "PreToolUse", "Write", {"file_path": "/etc/passwd", "content": "malicious"}
        )
        self.handler.event = event
        self.handler.hook_type = "PreToolUse"

        self.handler._handle_pre_tool_use()

        # Should call block
        mock_print.assert_called_once()
        output = json.loads(mock_print.call_args[0][0])
        self.assertEqual(output["action"], "block")
        self.assertIn("Security Policy", output["error"])
        self.assertIn("Cannot write to files outside", output["error"])
        mock_logger.warning.assert_called()
        mock_exit.assert_called_with(0)

    @patch("builtins.print")
    @patch("sys.exit")
    @patch("claude_mpm.hooks.claude_hooks.hook_handler.logger")
    def test_path_traversal_blocked(self, mock_exit, mock_print):
        """Test that path traversal attempts are blocked."""
        event = self.create_event(
            "PreToolUse",
            "Edit",
            {
                "file_path": f"{self.working_dir}/../../../etc/passwd",
                "old_string": "root",
                "new_string": "hacked",
            },
        )
        self.handler.event = event
        self.handler.hook_type = "PreToolUse"

        self.handler._handle_pre_tool_use()

        # Should call block
        mock_print.assert_called_once()
        output = json.loads(mock_print.call_args[0][0])
        self.assertEqual(output["action"], "block")
        self.assertIn("Path traversal attempts are not allowed", output["error"])
        self.warning.assert_called()
        mock_exit.assert_called_with(0)

    @patch("builtins.print")
    @patch("sys.exit")
    @patch("claude_mpm.hooks.claude_hooks.hook_handler.logger")
    def test_multiedit_outside_working_dir_blocked(
        self, mock_logger, mock_exit, mock_print
    ):
        """Test that MultiEdit outside working directory is blocked."""
        event = self.create_event(
            "PreToolUse",
            "MultiEdit",
            {
                "file_path": "/tmp/dangerous.txt",
                "edits": [{"old_string": "safe", "new_string": "dangerous"}],
            },
        )
        self.handler.event = event
        self.handler.hook_type = "PreToolUse"

        self.handler._handle_pre_tool_use()

        # Should call block
        mock_print.assert_called_once()
        output = json.loads(mock_print.call_args[0][0])
        self.assertEqual(output["action"], "block")
        self.assertIn("Security Policy", output["error"])
        mock_exit.assert_called_with(0)

    @patch("builtins.print")
    @patch("sys.exit")
    @patch("claude_mpm.hooks.claude_hooks.hook_handler.logger")
    def test_notebook_edit_outside_working_dir_blocked(
        self, mock_logger, mock_exit, mock_print
    ):
        """Test that NotebookEdit outside working directory is blocked."""
        event = self.create_event(
            "PreToolUse",
            "NotebookEdit",
            {
                "notebook_path": "/home/user/sensitive.ipynb",
                "new_source": "malicious code",
            },
        )
        self.handler.event = event
        self.handler.hook_type = "PreToolUse"

        self.handler._handle_pre_tool_use()

        # Should call block
        mock_print.assert_called_once()
        output = json.loads(mock_print.call_args[0][0])
        self.assertEqual(output["action"], "block")
        self.assertIn("Security Policy", output["error"])
        mock_exit.assert_called_with(0)

    @patch("builtins.print")
    @patch("sys.exit")
    def test_read_operations_allowed_anywhere(self, mock_print):
        """Test that read operations are allowed from anywhere."""
        # Test Read tool
        event = self.create_event("PreToolUse", "Read", {"file_path": "/etc/hosts"})
        self.handler.event = event
        self.handler.hook_type = "PreToolUse"

        self.handler._handle_pre_tool_use()

        # Should call continue
        mock_print.assert_called_once()
        output = json.loads(mock_print.call_args[0][0])
        self.assertEqual(output["action"], "continue")
        self.assert_called_with(0)

        # Reset mocks
        mock_print.reset_mock()
        self.reset_mock()

        # Test Grep tool
        event = self.create_event(
            "PreToolUse", "Grep", {"pattern": "password", "path": "/etc"}
        )
        self.handler.event = event

        self.handler._handle_pre_tool_use()

        # Should call continue
        mock_print.assert_called_once()
        output = json.loads(mock_print.call_args[0][0])
        self.assertEqual(output["action"], "continue")
        self.assert_called_with(0)

    @patch("builtins.print")
    @patch("sys.exit")
    def test_relative_path_resolution(self, mock_print):
        """Test that relative paths are resolved correctly."""
        event = self.create_event(
            "PreToolUse",
            "Write",
            {"file_path": "test.txt", "content": "test"},  # Relative path
        )
        self.handler.event = event
        self.handler.hook_type = "PreToolUse"

        # Mock Path.resolve to simulate resolution
        with patch.object(Path, "resolve") as mock_resolve:
            # First call resolves working dir
            # Second call resolves the relative path to within working dir
            mock_resolve.side_effect = [
                Path(self.working_dir),
                Path(f"{self.working_dir}/test.txt"),
            ]

            self.handler._handle_pre_tool_use()

        # Should call continue (allowed)
        mock_print.assert_called_once()
        output = json.loads(mock_print.call_args[0][0])
        self.assertEqual(output["action"], "continue")
        self.assert_called_with(0)

    @patch("builtins.print")
    @patch("sys.exit")
    @patch("claude_mpm.hooks.claude_hooks.hook_handler.logger")
    def test_symlink_resolution(self, mock_exit, mock_print):
        """Test that symlinks are resolved properly."""
        # This tests that if someone tries to use a symlink that points outside
        # the working directory, it's still blocked
        event = self.create_event(
            "PreToolUse",
            "Write",
            {"file_path": f"{self.working_dir}/evil_link", "content": "test"},
        )
        self.handler.event = event
        self.handler.hook_type = "PreToolUse"

        # Mock Path.resolve to simulate a symlink pointing outside
        with patch.object(Path, "resolve") as mock_resolve:
            # First call resolves working dir
            # Second call resolves the symlink to outside working dir
            mock_resolve.side_effect = [
                Path(self.working_dir),
                Path("/etc/passwd"),  # Symlink points here
            ]

            self.handler._handle_pre_tool_use()

        # Should call block
        mock_print.assert_called_once()
        output = json.loads(mock_print.call_args[0][0])
        self.assertEqual(output["action"], "block")
        self.assertIn("Security Policy", output["error"])
        self.warning.assert_called()
        mock_exit.assert_called_with(0)

    @patch("builtins.print")
    @patch("sys.exit")
    @patch("claude_mpm.hooks.claude_hooks.hook_handler.logger")
    def test_invalid_path_blocked(self, mock_exit, mock_print):
        """Test that invalid paths are blocked."""
        event = self.create_event(
            "PreToolUse",
            "Write",
            {"file_path": "\x00/etc/passwd", "content": "test"},  # Null byte injection
        )
        self.handler.event = event
        self.handler.hook_type = "PreToolUse"

        self.handler._handle_pre_tool_use()

        # Should call block due to error
        mock_print.assert_called_once()
        output = json.loads(mock_print.call_args[0][0])
        self.assertEqual(output["action"], "block")
        self.assertIn("Error validating file path", output["error"])
        self.error.assert_called()
        mock_exit.assert_called_with(0)


if __name__ == "__main__":
    unittest.main()
