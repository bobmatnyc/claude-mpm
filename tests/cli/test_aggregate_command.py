"""
Comprehensive tests for the migrated AggregateCommand class.

WHY: Verify that the aggregate command migration to BaseCommand pattern
works correctly and maintains backward compatibility.
"""

import pytest
from argparse import Namespace
from unittest.mock import Mock, patch

from claude_mpm.cli.commands.aggregate import AggregateCommand, aggregate_command
from claude_mpm.cli.shared.command_base import CommandResult


class TestAggregateCommand:
    """Test AggregateCommand functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.command = AggregateCommand()

    def test_initialization(self):
        """Test AggregateCommand initialization."""
        assert self.command.command_name == "aggregate"
        assert self.command.logger is not None

    def test_validate_args_no_subcommand(self):
        """Test validation with no aggregate subcommand."""
        args = Namespace()
        error = self.command.validate_args(args)
        assert "No aggregate subcommand specified" in error

    def test_validate_args_invalid_subcommand(self):
        """Test validation with invalid aggregate subcommand."""
        args = Namespace(aggregate_subcommand="invalid")
        error = self.command.validate_args(args)
        assert "Unknown aggregate command" in error

    def test_validate_args_valid_subcommand(self):
        """Test validation with valid aggregate subcommand."""
        valid_commands = ["start", "stop", "status", "sessions", "view", "export"]
        for cmd in valid_commands:
            args = Namespace(aggregate_subcommand=cmd)
            error = self.command.validate_args(args)
            assert error is None

    @patch.object(AggregateCommand, '_start_command')
    def test_run_start_command_success(self, mock_start):
        """Test running start command successfully."""
        mock_start.return_value = 0
        
        args = Namespace(aggregate_subcommand="start")
        result = self.command.run(args)
        
        assert isinstance(result, CommandResult)
        assert result.success is True
        assert "start completed successfully" in result.message
        mock_start.assert_called_once_with(args)

    @patch.object(AggregateCommand, '_start_command')
    def test_run_start_command_failure(self, mock_start):
        """Test running start command with failure."""
        mock_start.return_value = 1
        
        args = Namespace(aggregate_subcommand="start")
        result = self.command.run(args)
        
        assert isinstance(result, CommandResult)
        assert result.success is False
        assert "start failed" in result.message
        mock_start.assert_called_once_with(args)

    @patch.object(AggregateCommand, '_stop_command')
    def test_run_stop_command_success(self, mock_stop):
        """Test running stop command successfully."""
        mock_stop.return_value = 0
        
        args = Namespace(aggregate_subcommand="stop")
        result = self.command.run(args)
        
        assert isinstance(result, CommandResult)
        assert result.success is True
        assert "stop completed successfully" in result.message
        mock_stop.assert_called_once_with(args)

    @patch.object(AggregateCommand, '_status_command')
    def test_run_status_command_success(self, mock_status):
        """Test running status command successfully."""
        mock_status.return_value = 0
        
        args = Namespace(aggregate_subcommand="status")
        result = self.command.run(args)
        
        assert isinstance(result, CommandResult)
        assert result.success is True
        assert "status completed successfully" in result.message
        mock_status.assert_called_once_with(args)

    @patch.object(AggregateCommand, '_sessions_command')
    def test_run_sessions_command_success(self, mock_sessions):
        """Test running sessions command successfully."""
        mock_sessions.return_value = 0
        
        args = Namespace(aggregate_subcommand="sessions")
        result = self.command.run(args)
        
        assert isinstance(result, CommandResult)
        assert result.success is True
        assert "sessions completed successfully" in result.message
        mock_sessions.assert_called_once_with(args)

    @patch.object(AggregateCommand, '_view_command')
    def test_run_view_command_success(self, mock_view):
        """Test running view command successfully."""
        mock_view.return_value = 0
        
        args = Namespace(aggregate_subcommand="view")
        result = self.command.run(args)
        
        assert isinstance(result, CommandResult)
        assert result.success is True
        assert "view completed successfully" in result.message
        mock_view.assert_called_once_with(args)

    @patch.object(AggregateCommand, '_export_command')
    def test_run_export_command_success(self, mock_export):
        """Test running export command successfully."""
        mock_export.return_value = 0
        
        args = Namespace(aggregate_subcommand="export")
        result = self.command.run(args)
        
        assert isinstance(result, CommandResult)
        assert result.success is True
        assert "export completed successfully" in result.message
        mock_export.assert_called_once_with(args)

    def test_run_unknown_subcommand(self):
        """Test running unknown aggregate subcommand."""
        args = Namespace(aggregate_subcommand="unknown")
        result = self.command.run(args)
        
        assert isinstance(result, CommandResult)
        assert result.success is False
        assert "Unknown aggregate command" in result.message

    @patch('claude_mpm.cli.commands.aggregate.start_command_legacy')
    def test_start_command_delegates_to_legacy(self, mock_start_legacy):
        """Test that _start_command delegates to legacy implementation."""
        mock_start_legacy.return_value = 0
        
        args = Namespace()
        result = self.command._start_command(args)
        
        assert result == 0
        mock_start_legacy.assert_called_once_with(args)

    @patch('claude_mpm.cli.commands.aggregate.stop_command_legacy')
    def test_stop_command_delegates_to_legacy(self, mock_stop_legacy):
        """Test that _stop_command delegates to legacy implementation."""
        mock_stop_legacy.return_value = 0
        
        args = Namespace()
        result = self.command._stop_command(args)
        
        assert result == 0
        mock_stop_legacy.assert_called_once_with(args)

    @patch('claude_mpm.cli.commands.aggregate.status_command_legacy')
    def test_status_command_delegates_to_legacy(self, mock_status_legacy):
        """Test that _status_command delegates to legacy implementation."""
        mock_status_legacy.return_value = 0
        
        args = Namespace()
        result = self.command._status_command(args)
        
        assert result == 0
        mock_status_legacy.assert_called_once_with(args)

    @patch('claude_mpm.cli.commands.aggregate.sessions_command_legacy')
    def test_sessions_command_delegates_to_legacy(self, mock_sessions_legacy):
        """Test that _sessions_command delegates to legacy implementation."""
        mock_sessions_legacy.return_value = 0
        
        args = Namespace()
        result = self.command._sessions_command(args)
        
        assert result == 0
        mock_sessions_legacy.assert_called_once_with(args)

    @patch('claude_mpm.cli.commands.aggregate.view_command_legacy')
    def test_view_command_delegates_to_legacy(self, mock_view_legacy):
        """Test that _view_command delegates to legacy implementation."""
        mock_view_legacy.return_value = 0
        
        args = Namespace()
        result = self.command._view_command(args)
        
        assert result == 0
        mock_view_legacy.assert_called_once_with(args)

    @patch('claude_mpm.cli.commands.aggregate.export_command_legacy')
    def test_export_command_delegates_to_legacy(self, mock_export_legacy):
        """Test that _export_command delegates to legacy implementation."""
        mock_export_legacy.return_value = 0
        
        args = Namespace()
        result = self.command._export_command(args)
        
        assert result == 0
        mock_export_legacy.assert_called_once_with(args)


class TestAggregateCommandFunction:
    """Test aggregate_command backward compatibility function."""

    @patch.object(AggregateCommand, 'execute')
    def test_aggregate_command_success(self, mock_execute):
        """Test aggregate_command function with success."""
        mock_result = CommandResult.success_result("Aggregate completed")
        mock_execute.return_value = mock_result
        
        args = Namespace(aggregate_subcommand="status")
        exit_code = aggregate_command(args)
        
        assert exit_code == 0
        mock_execute.assert_called_once_with(args)

    @patch.object(AggregateCommand, 'execute')
    def test_aggregate_command_error(self, mock_execute):
        """Test aggregate_command function with error."""
        mock_result = CommandResult.error_result("Aggregate error", exit_code=2)
        mock_execute.return_value = mock_result
        
        args = Namespace(aggregate_subcommand="start")
        exit_code = aggregate_command(args)
        
        assert exit_code == 2
        mock_execute.assert_called_once_with(args)

    @patch.object(AggregateCommand, 'execute')
    @patch.object(AggregateCommand, 'print_result')
    def test_aggregate_command_structured_output(self, mock_print, mock_execute):
        """Test aggregate_command with structured output format."""
        mock_result = CommandResult.success_result("Aggregate completed", {"sessions": []})
        mock_execute.return_value = mock_result
        
        args = Namespace(aggregate_subcommand="sessions", format="json")
        exit_code = aggregate_command(args)
        
        assert exit_code == 0
        mock_execute.assert_called_once_with(args)
        mock_print.assert_called_once_with(mock_result, args)

    @patch.object(AggregateCommand, 'execute')
    def test_aggregate_command_no_structured_output(self, mock_execute):
        """Test aggregate_command without structured output format."""
        mock_result = CommandResult.success_result("Aggregate completed")
        mock_execute.return_value = mock_result
        
        args = Namespace(aggregate_subcommand="status", format="text")
        
        with patch.object(AggregateCommand, 'print_result') as mock_print:
            exit_code = aggregate_command(args)
            
            assert exit_code == 0
            mock_execute.assert_called_once_with(args)
            # Should not call print_result for text format
            mock_print.assert_not_called()


class TestAggregateCommandIntegration:
    """Integration tests for AggregateCommand."""

    def test_full_execution_flow(self):
        """Test full execution flow with mocked dependencies."""
        command = AggregateCommand()
        
        with patch('claude_mpm.cli.commands.aggregate.status_command_legacy') as mock_status:
            mock_status.return_value = 0
            
            args = Namespace(aggregate_subcommand="status")
            
            result = command.execute(args)
            
            assert isinstance(result, CommandResult)
            assert result.success is True
            assert "status completed successfully" in result.message

    def test_error_handling_in_execution(self):
        """Test error handling during execution."""
        command = AggregateCommand()
        
        with patch('claude_mpm.cli.commands.aggregate.start_command_legacy') as mock_start:
            mock_start.side_effect = Exception("Start command failed")
            
            args = Namespace(aggregate_subcommand="start")
            
            result = command.execute(args)
            
            assert isinstance(result, CommandResult)
            assert result.success is False
            assert "Start command failed" in result.message

    def test_keyboard_interrupt_handling(self):
        """Test keyboard interrupt handling during execution."""
        command = AggregateCommand()
        
        with patch('claude_mpm.cli.commands.aggregate.start_command_legacy') as mock_start:
            mock_start.side_effect = KeyboardInterrupt()
            
            args = Namespace(aggregate_subcommand="start")
            
            result = command.execute(args)
            
            assert isinstance(result, CommandResult)
            assert result.success is False
            assert result.exit_code == 130
            assert "cancelled by user" in result.message


class TestAggregateCommandLegacyCompatibility:
    """Test backward compatibility with legacy aggregate command."""

    @patch('claude_mpm.cli.commands.aggregate.start_command_legacy')
    @patch('claude_mpm.cli.commands.aggregate.stop_command_legacy')
    @patch('claude_mpm.cli.commands.aggregate.status_command_legacy')
    @patch('claude_mpm.cli.commands.aggregate.sessions_command_legacy')
    @patch('claude_mpm.cli.commands.aggregate.view_command_legacy')
    @patch('claude_mpm.cli.commands.aggregate.export_command_legacy')
    def test_all_legacy_commands_called(self, mock_export, mock_view, mock_sessions, 
                                       mock_status, mock_stop, mock_start):
        """Test that all legacy command functions are properly called."""
        command = AggregateCommand()
        
        # Set all mocks to return success
        for mock_func in [mock_export, mock_view, mock_sessions, mock_status, mock_stop, mock_start]:
            mock_func.return_value = 0
        
        # Test each subcommand
        subcommands = ["start", "stop", "status", "sessions", "view", "export"]
        mocks = [mock_start, mock_stop, mock_status, mock_sessions, mock_view, mock_export]
        
        for subcommand, mock_func in zip(subcommands, mocks):
            args = Namespace(aggregate_subcommand=subcommand)
            result = command.run(args)
            
            assert result.success is True
            mock_func.assert_called_with(args)

    def test_legacy_function_compatibility(self):
        """Test that the legacy aggregate_command_legacy function still works."""
        from claude_mpm.cli.commands.aggregate import aggregate_command_legacy
        
        with patch('claude_mpm.cli.commands.aggregate.start_command_legacy') as mock_start:
            mock_start.return_value = 0
            
            args = Namespace(aggregate_subcommand="start")
            result = aggregate_command_legacy(args)
            
            assert result == 0
            mock_start.assert_called_once_with(args)

    def test_legacy_function_unknown_subcommand(self):
        """Test legacy function with unknown subcommand."""
        from claude_mpm.cli.commands.aggregate import aggregate_command_legacy
        
        args = Namespace(aggregate_subcommand="unknown")
        
        with patch('sys.stderr') as mock_stderr:
            result = aggregate_command_legacy(args)
            
            assert result == 1
