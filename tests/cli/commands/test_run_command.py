"""
Comprehensive tests for the RunCommand class.

WHY: The run command is the most important user-facing command in claude-mpm.
It starts Claude sessions and needs thorough testing for all modes and options.

DESIGN DECISIONS:
- Test both interactive and non-interactive modes
- Mock external dependencies (subprocess, webbrowser)
- Test error handling and validation
- Verify backward compatibility
- Test all command-line options
"""

from argparse import Namespace
from unittest.mock import Mock, patch

import pytest

from claude_mpm.cli.commands.run import RunCommand, filter_claude_mpm_args
from claude_mpm.cli.shared.base_command import CommandResult


class TestRunCommand:
    """Test RunCommand functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.command = RunCommand()

    def test_init(self):
        """Test RunCommand initialization."""
        assert self.command.command_name == "run"
        assert self.command.logger is not None

    def test_validate_args_returns_none(self):
        """Test that validate_args returns None (no validation errors)."""
        args = Namespace(
            claude_args=[],
            monitor=False,
            websocket_port=None,
            no_hooks=False,
            no_tickets=False,
        )
        error = self.command.validate_args(args)
        assert error is None

    def test_validate_args_with_input_file(self):
        """Test validation with input file specified."""
        args = Namespace(
            claude_args=[], input="/path/to/input.txt", non_interactive=False
        )
        error = self.command.validate_args(args)
        assert error is None

    def test_validate_args_non_interactive_without_input(self):
        """Test validation for non-interactive mode without input."""
        args = Namespace(claude_args=[], input=None, non_interactive=True)
        error = self.command.validate_args(args)
        assert error is None

    @patch("claude_mpm.cli.commands.run.run_session_legacy")
    def test_run_success(self, mock_run_session_legacy):
        """Test successful run command execution."""
        mock_run_session_legacy.return_value = None

        args = Namespace(
            claude_args=[],
            monitor=False,
            websocket_port=None,
            no_hooks=False,
            no_tickets=False,
            intercept_commands=False,
            no_native_agents=False,
            launch_method="default",
            mpm_resume=False,
            input=None,
            non_interactive=False,
            debug=False,
            logging="OFF",
        )

        result = self.command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is True
        mock_run_session_legacy.assert_called_once_with(args)

    @patch("claude_mpm.cli.commands.run.run_session_legacy")
    def test_run_failure(self, mock_run_session_legacy):
        """Test run command when session fails."""
        mock_run_session_legacy.side_effect = Exception("Session failed")

        args = Namespace(
            claude_args=[],
            monitor=False,
            no_tickets=False,
            logging="OFF",
        )

        result = self.command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is False

    @patch("claude_mpm.cli.commands.run.run_session_legacy")
    def test_run_keyboard_interrupt(self, mock_run_session_legacy):
        """Test handling of KeyboardInterrupt."""
        mock_run_session_legacy.side_effect = KeyboardInterrupt()

        args = Namespace(
            claude_args=[],
            monitor=False,
            no_tickets=False,
            logging="OFF",
        )

        result = self.command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is False
        assert result.exit_code == 130


class TestFilterClaudeMpmArgs:
    """Test filter_claude_mpm_args function."""

    def test_filter_mpm_specific_flags(self):
        """Test filtering of MPM-specific arguments."""
        claude_args = ["--monitor", "--debug", "actual-arg", "--input", "file.txt"]
        filtered = filter_claude_mpm_args(claude_args)
        assert filtered == ["actual-arg"]

    def test_filter_separator(self):
        """Test filtering with -- separator."""
        claude_args = ["--", "arg1", "arg2"]
        filtered = filter_claude_mpm_args(claude_args)
        assert filtered == ["arg1", "arg2"]

    def test_filter_empty_list(self):
        """Test filtering empty list."""
        assert filter_claude_mpm_args([]) == []

    def test_filter_none(self):
        """Test filtering None."""
        assert filter_claude_mpm_args(None) == []

    def test_filter_only_valid_claude_args(self):
        """Test with only valid Claude args (no filtering needed)."""
        claude_args = ["--model", "claude-3", "--temperature", "0.7"]
        filtered = filter_claude_mpm_args(claude_args)
        assert filtered == claude_args

    def test_filter_websocket_port_with_value(self):
        """Test filtering --websocket-port with its value."""
        claude_args = ["--websocket-port", "9090", "--model", "claude-3"]
        filtered = filter_claude_mpm_args(claude_args)
        assert filtered == ["--model", "claude-3"]

    def test_filter_logging_with_value(self):
        """Test filtering --logging with its value."""
        claude_args = ["--logging", "DEBUG", "--model", "claude-3"]
        filtered = filter_claude_mpm_args(claude_args)
        assert filtered == ["--model", "claude-3"]

    def test_filter_input_short_flag(self):
        """Test filtering -i (short for --input) with value."""
        claude_args = ["-i", "input.txt", "--model", "claude-3"]
        filtered = filter_claude_mpm_args(claude_args)
        assert filtered == ["--model", "claude-3"]

    def test_filter_mpm_resume_without_value(self):
        """Test filtering --mpm-resume without value."""
        claude_args = ["--mpm-resume", "--model", "claude-3"]
        filtered = filter_claude_mpm_args(claude_args)
        assert filtered == ["--model", "claude-3"]

    def test_filter_mpm_resume_with_value(self):
        """Test filtering --mpm-resume with optional value."""
        claude_args = ["--mpm-resume", "session-id", "--model", "claude-3"]
        filtered = filter_claude_mpm_args(claude_args)
        assert filtered == ["--model", "claude-3"]

    def test_filter_headless_flag(self):
        """Test filtering --headless flag."""
        claude_args = ["--headless", "--model", "claude-3"]
        filtered = filter_claude_mpm_args(claude_args)
        assert filtered == ["--model", "claude-3"]

    def test_filter_multiple_mpm_flags(self):
        """Test filtering multiple MPM flags at once."""
        claude_args = [
            "--monitor",
            "--no-tickets",
            "--debug",
            "--model",
            "claude-3",
            "--intercept-commands",
        ]
        filtered = filter_claude_mpm_args(claude_args)
        assert filtered == ["--model", "claude-3"]


class TestRunCommandIntegration:
    """Integration tests for RunCommand."""

    def setup_method(self):
        """Set up test fixtures."""
        self.command = RunCommand()

    @patch("claude_mpm.cli.commands.run.run_session_legacy")
    def test_execute_calls_run(self, mock_run_session_legacy):
        """Test that execute properly calls run method."""
        mock_run_session_legacy.return_value = None

        args = Namespace(
            claude_args=[],
            monitor=False,
            no_tickets=False,
            logging="OFF",
            debug=False,
            config=None,
        )

        result = self.command.execute(args)

        assert isinstance(result, CommandResult)
        mock_run_session_legacy.assert_called_once()

    @patch("claude_mpm.cli.commands.run.run_session_legacy")
    def test_run_with_claude_args_passthrough(self, mock_run_session_legacy):
        """Test that Claude args are passed through correctly."""
        mock_run_session_legacy.return_value = None

        args = Namespace(
            claude_args=["--model", "claude-3", "--temperature", "0.7"],
            monitor=False,
            no_tickets=False,
            logging="OFF",
        )

        result = self.command.run(args)

        assert result.success is True
        # Verify the args were passed to run_session_legacy
        call_args = mock_run_session_legacy.call_args[0][0]
        assert call_args.claude_args == ["--model", "claude-3", "--temperature", "0.7"]
