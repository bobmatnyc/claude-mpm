"""
Fixed tests for the RunCommand class with proper mocking.

WHY: The original tests were failing because they weren't properly mocking
the run_session_legacy function and other dependencies.

DESIGN DECISIONS:
- Mock at the correct level (run_session_legacy instead of subprocess)
- Use proper namespace for arguments
- Mock all external dependencies
- Focus on unit testing the command logic
"""

from argparse import Namespace
from unittest.mock import Mock, patch

from claude_mpm.cli.commands.run import RunCommand, filter_claude_mpm_args
from claude_mpm.cli.shared.base_command import CommandResult


class TestRunCommandFixed:
    """Fixed tests for RunCommand functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.command = RunCommand()

    def test_validate_args_basic():
        """Test basic validation with minimal args."""
        args = Namespace()
        error = self.command.validate_args(args)
        assert error is None

    @patch("claude_mpm.cli.commands.run.run_session_legacy")
    def test_execute_run_session_success(self):
        """Test successful run session execution."""
        # Mock the legacy function to not actually run
        self.return_value = None

        # Test the internal method
        result = self.command._execute_run_session(Namespace())

        assert result is True
        self.assert_called_once()

    @patch("claude_mpm.cli.commands.run.run_session_legacy")
    def test_execute_run_session_failure(self):
        """Test run session execution with failure."""
        # Mock the legacy function to raise an exception
        self.side_effect = Exception("Test error")

        # Test the internal method
        result = self.command._execute_run_session(Namespace())

        assert result is False

    @patch("claude_mpm.cli.commands.run.run_session_legacy")
    def test_run_command_success(self):
        """Test complete run command execution."""
        self.return_value = None

        args = Namespace(
            logging="INFO",
            claude_args=[],
            monitor=False,
            no_tickets=False,
            no_native_agents=False,
            mpm_resume=False,
            input=None,
            non_interactive=False,
        )

        result = self.command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is True
        assert "completed successfully" in result.message

    @patch("claude_mpm.cli.commands.run.run_session_legacy")
    def test_run_command_keyboard_interrupt(self):
        """Test handling of keyboard interrupt."""
        self.side_effect = KeyboardInterrupt()

        args = Namespace()

        result = self.command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is False
        assert result.exit_code == 130
        assert "cancelled by user" in result.message

    @patch("claude_mpm.cli.commands.run.run_session_legacy")
    def test_run_command_general_exception(self):
        """Test handling of general exceptions."""
        self.side_effect = RuntimeError("Test error")

        args = Namespace()

        result = self.command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is False
        assert "Test error" in result.message

    def test_filter_claude_mpm_args():
        """Test filtering of MPM-specific arguments."""
        # Test with MPM-specific flags that should be filtered
        claude_args = [
            "--monitor",
            "--debug",
            "actual-arg",
            "--input",
            "file.txt",
            "--websocket-port",
            "8765",
        ]
        filtered = filter_claude_mpm_args(claude_args)
        assert filtered == ["actual-arg"]

        # Test with separator
        claude_args = ["--", "arg1", "arg2"]
        filtered = filter_claude_mpm_args(claude_args)
        assert filtered == ["arg1", "arg2"]

        # Test with empty list
        assert filter_claude_mpm_args([]) == []
        assert filter_claude_mpm_args(None) == []

        # Test with only valid Claude args
        claude_args = ["--model", "claude-3", "--temperature", "0.7"]
        filtered = filter_claude_mpm_args(claude_args)
        assert filtered == claude_args

        # Test with mixed args
        claude_args = ["--monitor", "--model", "claude-3", "--no-hooks", "chat"]
        filtered = filter_claude_mpm_args(claude_args)
        assert filtered == ["--model", "claude-3", "chat"]

    @patch("claude_mpm.cli.commands.run.RunConfigChecker")
    def test_check_configuration_health(self):
        """Test configuration health check."""
        mock_checker = Mock()
        self.return_value = mock_checker

        self.command._check_configuration_health()

        self.assert_called_once()
        mock_checker.check_configuration_health.assert_called_once()

    @patch("claude_mpm.cli.commands.run.RunConfigChecker")
    def test_check_claude_json_memory(self):
        """Test Claude JSON memory check."""
        mock_checker = Mock()
        self.return_value = mock_checker

        args = Namespace(mpm_resume=True)

        self.command._check_claude_json_memory(args)

        self.assert_called_once()
        mock_checker.check_claude_json_memory.assert_called_once_with(args)

    @patch("claude_mpm.cli.commands.run.SessionManager")
    def test_setup_session_management_no_resume(self):
        """Test session management setup without resume."""
        mock_manager = Mock()
        self.return_value = mock_manager

        args = Namespace(mpm_resume=False)

        manager, session_id, context = self.command._setup_session_management(args)

        assert manager == mock_manager
        assert session_id is None
        assert context is None

    @patch("claude_mpm.cli.commands.run.SessionManager")
    def test_setup_session_management_resume_last(self):
        """Test session management setup with resume last."""
        mock_manager = Mock()
        mock_manager.get_last_interactive_session.return_value = "session123"
        mock_manager.get_session_by_id.return_value = {
            "context": "test-context",
            "created_at": "2024-01-01",
        }
        self.return_value = mock_manager

        args = Namespace(mpm_resume="last")

        manager, session_id, context = self.command._setup_session_management(args)

        assert manager == mock_manager
        assert session_id == "session123"
        assert context == "test-context"

    @patch("claude_mpm.cli.commands.run.ensure_socketio_dependencies")
    @patch("claude_mpm.cli.commands.run.PortManager")
    def test_setup_monitoring_disabled(self, mock_ensure_deps):
        """Test monitoring setup when disabled."""
        args = Namespace(monitor=False)

        monitor_mode, port = self.command._setup_monitoring(args)

        assert monitor_mode is False
        assert port == 8765  # Default port
        mock_ensure_deps.assert_not_called()

    @patch("claude_mpm.cli.commands.run.ensure_socketio_dependencies")
    @patch("claude_mpm.cli.commands.run.PortManager")
    @patch("claude_mpm.cli.commands.run._start_socketio_server")
    @patch("claude_mpm.cli.commands.run.webbrowser")
    def test_setup_monitoring_enabled(
        self, mock_start_server, mock_port_manager_class, mock_ensure_deps
    ):
        """Test monitoring setup when enabled."""
        mock_ensure_deps.return_value = True
        mock_port_manager = Mock()
        mock_port_manager.get_available_port.return_value = 8080
        mock_port_manager_class.return_value = mock_port_manager
        mock_start_server.return_value = True

        # Mock the server check
        with patch.object(
            self.command, "_is_socketio_server_running", return_value=False
        ):
            args = Namespace(monitor=True, _browser_opened_by_cli=False)

            monitor_mode, port = self.command._setup_monitoring(args)

        assert monitor_mode is True
        assert port == 8080
        mock_ensure_deps.assert_called_once()
        self.open.assert_called_once_with("http://localhost:8080")

    def test_filter_claude_mpm_args_with_values():
        """Test filtering arguments that take values."""
        # Test websocket-port with value
        claude_args = ["--websocket-port", "9090", "chat"]
        filtered = filter_claude_mpm_args(claude_args)
        assert filtered == ["chat"]

        # Test input with value
        claude_args = ["--input", "test.txt", "other"]
        filtered = filter_claude_mpm_args(claude_args)
        assert filtered == ["other"]

        # Test optional value flag (mpm-resume)
        claude_args = ["--mpm-resume", "session123", "chat"]
        filtered = filter_claude_mpm_args(claude_args)
        assert filtered == ["chat"]

        # Test optional value flag without value
        claude_args = ["--mpm-resume", "--other-flag"]
        filtered = filter_claude_mpm_args(claude_args)
        assert filtered == ["--other-flag"]
