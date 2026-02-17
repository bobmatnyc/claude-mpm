"""
Comprehensive tests for the AggregateCommand class.

WHY: The aggregate command manages event aggregation for monitoring and analytics.
This is important for system observability and debugging.

DESIGN DECISIONS:
- Test the actual AggregateCommand implementation
- Mock the legacy command functions that do the real work
- Test validation and routing logic
- Verify CommandResult handling
"""

from argparse import Namespace
from unittest.mock import patch

import pytest

from claude_mpm.cli.commands.aggregate import AggregateCommand
from claude_mpm.cli.shared.base_command import CommandResult


class TestAggregateCommand:
    """Test AggregateCommand functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.command = AggregateCommand()

    def test_init(self):
        """Test command initialization."""
        assert self.command.command_name == "aggregate"

    def test_validate_args_missing_subcommand(self):
        """Test validation when subcommand is missing."""
        args = Namespace()
        error = self.command.validate_args(args)
        assert error == "No aggregate subcommand specified"

    def test_validate_args_none_subcommand(self):
        """Test validation when subcommand is None."""
        args = Namespace(aggregate_subcommand=None)
        error = self.command.validate_args(args)
        assert error == "No aggregate subcommand specified"

    def test_validate_args_valid_subcommands(self):
        """Test validation with valid aggregate subcommands."""
        valid_commands = ["start", "stop", "status", "sessions", "view", "export"]

        for cmd in valid_commands:
            args = Namespace(aggregate_subcommand=cmd)
            error = self.command.validate_args(args)
            assert error is None, f"Command {cmd} should be valid"

    def test_validate_args_invalid_subcommand(self):
        """Test validation with invalid subcommand."""
        args = Namespace(aggregate_subcommand="invalid")
        error = self.command.validate_args(args)
        assert "Unknown aggregate command: invalid" in error
        assert "Valid commands:" in error

    @patch("claude_mpm.cli.commands.aggregate.start_command_legacy")
    def test_run_start_command_success(self, mock_start):
        """Test running the start subcommand successfully."""
        mock_start.return_value = 0
        args = Namespace(aggregate_subcommand="start")

        result = self.command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is True
        assert "start completed successfully" in result.message
        mock_start.assert_called_once_with(args)

    @patch("claude_mpm.cli.commands.aggregate.start_command_legacy")
    def test_run_start_command_failure(self, mock_start):
        """Test running the start subcommand with failure."""
        mock_start.return_value = 1
        args = Namespace(aggregate_subcommand="start")

        result = self.command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is False
        assert "start failed" in result.message

    @patch("claude_mpm.cli.commands.aggregate.stop_command_legacy")
    def test_run_stop_command_success(self, mock_stop):
        """Test running the stop subcommand successfully."""
        mock_stop.return_value = 0
        args = Namespace(aggregate_subcommand="stop")

        result = self.command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is True
        assert "stop completed successfully" in result.message
        mock_stop.assert_called_once_with(args)

    @patch("claude_mpm.cli.commands.aggregate.status_command_legacy")
    def test_run_status_command_success(self, mock_status):
        """Test running the status subcommand successfully."""
        mock_status.return_value = 0
        args = Namespace(aggregate_subcommand="status")

        result = self.command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is True
        assert "status completed successfully" in result.message
        mock_status.assert_called_once_with(args)

    @patch("claude_mpm.cli.commands.aggregate.sessions_command_legacy")
    def test_run_sessions_command_success(self, mock_sessions):
        """Test running the sessions subcommand successfully."""
        mock_sessions.return_value = 0
        args = Namespace(aggregate_subcommand="sessions")

        result = self.command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is True
        assert "sessions completed successfully" in result.message
        mock_sessions.assert_called_once_with(args)

    @patch("claude_mpm.cli.commands.aggregate.view_command_legacy")
    def test_run_view_command_success(self, mock_view):
        """Test running the view subcommand successfully."""
        mock_view.return_value = 0
        args = Namespace(aggregate_subcommand="view", session_id="test123")

        result = self.command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is True
        assert "view completed successfully" in result.message
        mock_view.assert_called_once_with(args)

    @patch("claude_mpm.cli.commands.aggregate.view_command_legacy")
    def test_run_view_command_not_found(self, mock_view):
        """Test running view when session is not found."""
        mock_view.return_value = 1
        args = Namespace(aggregate_subcommand="view", session_id="nonexistent")

        result = self.command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is False
        assert "view failed" in result.message

    @patch("claude_mpm.cli.commands.aggregate.export_command_legacy")
    def test_run_export_command_success(self, mock_export):
        """Test running the export subcommand successfully."""
        mock_export.return_value = 0
        args = Namespace(
            aggregate_subcommand="export",
            session_id="test123",
            output="/tmp/export.json",
            format="json",
        )

        result = self.command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is True
        assert "export completed successfully" in result.message
        mock_export.assert_called_once_with(args)

    def test_run_unknown_subcommand(self):
        """Test running with an unknown subcommand."""
        args = Namespace(aggregate_subcommand="unknown")

        result = self.command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is False
        assert "Unknown aggregate command" in result.message

    @patch("claude_mpm.cli.commands.aggregate.start_command_legacy")
    def test_run_handles_exception(self, mock_start):
        """Test that run handles exceptions gracefully."""
        mock_start.side_effect = Exception("Test error")
        args = Namespace(aggregate_subcommand="start")

        result = self.command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is False
        assert "Error executing aggregate command" in result.message


class TestAggregateCommandFunction:
    """Test the aggregate_command entry point function."""

    @patch("claude_mpm.cli.commands.aggregate.AggregateCommand")
    def test_aggregate_command_function(self, mock_command_class):
        """Test the aggregate_command function."""
        from claude_mpm.cli.commands.aggregate import aggregate_command

        mock_instance = mock_command_class.return_value
        mock_result = CommandResult.success_result("Success")
        mock_instance.execute.return_value = mock_result

        args = Namespace(aggregate_subcommand="status", format="text")

        exit_code = aggregate_command(args)

        assert exit_code == 0
        mock_instance.execute.assert_called_once_with(args)


class TestLegacyCommandDispatcher:
    """Test the legacy command dispatcher function."""

    @patch("claude_mpm.cli.commands.aggregate.start_command_legacy")
    def test_legacy_dispatcher_start(self, mock_start):
        """Test legacy dispatcher routes to start command."""
        from claude_mpm.cli.commands.aggregate import aggregate_command_legacy

        mock_start.return_value = 0
        args = Namespace(aggregate_subcommand="start")

        result = aggregate_command_legacy(args)

        assert result == 0
        mock_start.assert_called_once_with(args)

    @patch("claude_mpm.cli.commands.aggregate.stop_command_legacy")
    def test_legacy_dispatcher_stop(self, mock_stop):
        """Test legacy dispatcher routes to stop command."""
        from claude_mpm.cli.commands.aggregate import aggregate_command_legacy

        mock_stop.return_value = 0
        args = Namespace(aggregate_subcommand="stop")

        result = aggregate_command_legacy(args)

        assert result == 0
        mock_stop.assert_called_once_with(args)

    @patch("claude_mpm.cli.commands.aggregate.status_command_legacy")
    def test_legacy_dispatcher_status(self, mock_status):
        """Test legacy dispatcher routes to status command."""
        from claude_mpm.cli.commands.aggregate import aggregate_command_legacy

        mock_status.return_value = 0
        args = Namespace(aggregate_subcommand="status")

        result = aggregate_command_legacy(args)

        assert result == 0
        mock_status.assert_called_once_with(args)

    def test_legacy_dispatcher_unknown(self, capsys):
        """Test legacy dispatcher handles unknown subcommand."""
        from claude_mpm.cli.commands.aggregate import aggregate_command_legacy

        args = Namespace(aggregate_subcommand="unknown")

        result = aggregate_command_legacy(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Unknown subcommand: unknown" in captured.err
