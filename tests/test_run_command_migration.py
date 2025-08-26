"""
Test for the migrated RunCommand class.

WHY: Verify that the migration to BaseCommand pattern works correctly
and maintains backward compatibility.
"""

from argparse import Namespace
from unittest.mock import Mock, patch

import pytest

from claude_mpm.cli.commands.run import RunCommand
from claude_mpm.cli.shared.base_command import CommandResult


class TestRunCommandMigration:
    """Test the migrated RunCommand class."""

    def setup_method(self):
        """Setup test fixtures."""
        self.command = RunCommand()

    def test_command_initialization():
        """Test that RunCommand initializes correctly."""
        assert self.command.command_name == "run"
        assert self.command.logger is not None

    def test_validate_args_minimal():
        """Test argument validation with minimal args."""
        args = Namespace()
        result = self.command.validate_args(args)
        assert result is None  # No validation errors

    @patch("claude_mpm.cli.commands.run.RunCommand._execute_run_session")
    def test_run_success(self):
        """Test successful run execution."""
        self.return_value = True
        args = Namespace(logging="OFF")

        result = self.command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is True
        assert result.exit_code == 0
        assert "successfully" in result.message

    @patch("claude_mpm.cli.commands.run.RunCommand._execute_run_session")
    def test_run_failure(self):
        """Test failed run execution."""
        self.return_value = False
        args = Namespace(logging="OFF")

        result = self.command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is False
        assert result.exit_code == 1
        assert "failed" in result.message

    @patch("claude_mpm.cli.commands.run.RunCommand._execute_run_session")
    def test_run_keyboard_interrupt(self):
        """Test handling of keyboard interrupt."""
        self.side_effect = KeyboardInterrupt()
        args = Namespace(logging="OFF")

        result = self.command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is False
        assert result.exit_code == 130
        assert "cancelled" in result.message

    @patch("claude_mpm.cli.commands.run.run_session_legacy")
    def test_execute_run_session_delegates_to_legacy(self):
        """Test that _execute_run_session delegates to legacy function."""
        args = Namespace(logging="OFF")
        self.return_value = None

        result = self.command._execute_run_session(args)

        assert result is True
        self.assert_called_once_with(args)

    @patch("claude_mpm.cli.commands.run.run_session_legacy")
    def test_execute_run_session_handles_legacy_exception(self):
        """Test that _execute_run_session handles legacy function exceptions."""
        args = Namespace(logging="OFF")
        self.side_effect = Exception("Legacy error")

        result = self.command._execute_run_session(args)

        assert result is False

    def test_backward_compatibility_function():
        """Test that the run_session function maintains backward compatibility."""
        from claude_mpm.cli.commands.run import run_session

        with patch.object(RunCommand, "execute") as mock_execute:
            mock_result = CommandResult.success_result("Test success")
            mock_execute.return_value = mock_result

            args = Namespace(logging="OFF")
            exit_code = run_session(args)

            assert exit_code == 0
            mock_execute.assert_called_once_with(args)


class TestRunCommandHelperMethods:
    """Test the helper methods in RunCommand."""

    def setup_method(self):
        """Setup test fixtures."""
        self.command = RunCommand()

    @patch("claude_mpm.cli.commands.run_config_checker.RunConfigChecker")
    def test_check_configuration_health(self):
        """Test configuration health check."""
        mock_checker = Mock()
        self.return_value = mock_checker

        self.command._check_configuration_health()

        self.assert_called_once_with(self.command.logger)
        mock_checker.check_configuration_health.assert_called_once()

    @patch("claude_mpm.cli.commands.run_config_checker.RunConfigChecker")
    def test_check_claude_json_memory(self):
        """Test Claude JSON memory check."""
        mock_checker = Mock()
        self.return_value = mock_checker
        args = Namespace()

        self.command._check_claude_json_memory(args)

        self.assert_called_once_with(self.command.logger)
        mock_checker.check_claude_json_memory.assert_called_once_with(args)

    @patch("claude_mpm.core.session_manager.SessionManager")
    def test_setup_session_management_no_resume(self):
        """Test session management setup without resume."""
        mock_session_manager = Mock()
        self.return_value = mock_session_manager
        args = Namespace()

        result = self.command._setup_session_management(args)

        session_manager, resume_session_id, resume_context = result
        assert session_manager == mock_session_manager
        assert resume_session_id is None
        assert resume_context is None

    def test_setup_monitoring_disabled():
        """Test monitoring setup when disabled."""
        args = Namespace()

        monitor_mode, websocket_port = self.command._setup_monitoring(args)

        assert monitor_mode is False
        assert websocket_port == 8765

    @patch("claude_mpm.core.claude_runner.ClaudeRunner")
    def test_setup_claude_runner(self):
        """Test Claude runner setup."""
        mock_runner = Mock()
        self.return_value = mock_runner
        args = Namespace(logging="OFF")

        result = self.command._setup_claude_runner(args, False, 8765)

        assert result == mock_runner
        self.assert_called_once()

    def test_is_socketio_server_running_false():
        """Test Socket.IO server running check when not running."""
        result = self.command._is_socketio_server_running(9999)  # Unlikely to be used
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__])
