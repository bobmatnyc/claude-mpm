"""
Comprehensive tests for the MonitorCommand class.

WHY: The monitor command provides management of the unified monitoring daemon.
This is crucial for debugging and observability.

DESIGN DECISIONS:
- Test monitor daemon start/stop/restart/status operations
- Mock UnifiedMonitorDaemon to avoid side effects
- Test argument validation
- Verify proper command routing
"""

from argparse import Namespace
from unittest.mock import Mock, patch

from claude_mpm.cli.commands.monitor import MonitorCommand
from claude_mpm.cli.shared.base_command import CommandResult


class TestMonitorCommand:
    """Test MonitorCommand functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.command = MonitorCommand()

    def test_validate_args_default(self):
        """Test validation with default args (no monitor_command)."""
        args = Namespace(port=8080, filter=None, output="console")
        error = self.command.validate_args(args)
        assert error is None

    def test_validate_args_with_valid_command(self):
        """Test validation with valid monitor command."""
        args = Namespace(monitor_command="start")
        error = self.command.validate_args(args)
        assert error is None

    def test_validate_args_with_invalid_command(self):
        """Test validation with invalid monitor command."""
        args = Namespace(monitor_command="invalid_command")
        error = self.command.validate_args(args)
        assert error is not None
        assert "Unknown monitor command" in error

    @patch("claude_mpm.cli.commands.monitor.UnifiedMonitorDaemon")
    def test_run_default_status(self, mock_daemon_class):
        """Test running monitor without subcommand defaults to status."""
        mock_daemon = Mock()
        mock_daemon_class.return_value = mock_daemon
        mock_daemon.status.return_value = {
            "running": True,
            "host": "localhost",
            "port": 8765,
            "pid": 12345,
        }

        args = Namespace()
        # No monitor_command attribute means default to status

        result = self.command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is True
        mock_daemon.status.assert_called_once()

    @patch("claude_mpm.cli.commands.monitor.UnifiedMonitorDaemon")
    def test_run_start_command(self, mock_daemon_class):
        """Test starting the monitor daemon."""
        mock_daemon = Mock()
        mock_daemon_class.return_value = mock_daemon
        mock_daemon.lifecycle.is_running.return_value = False
        mock_daemon.start.return_value = True

        args = Namespace(
            monitor_command="start", port=8765, host="localhost", foreground=True
        )

        result = self.command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is True
        mock_daemon.start.assert_called_once()

    @patch("claude_mpm.cli.commands.monitor.UnifiedMonitorDaemon")
    def test_run_start_already_running(self, mock_daemon_class):
        """Test starting when daemon is already running."""
        mock_daemon = Mock()
        mock_daemon_class.return_value = mock_daemon
        mock_daemon.lifecycle.is_running.return_value = True
        mock_daemon.lifecycle.get_pid.return_value = 12345

        args = Namespace(
            monitor_command="start", port=8765, host="localhost", force=False
        )

        result = self.command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is True
        assert "already running" in result.message

    @patch("claude_mpm.cli.commands.monitor.UnifiedMonitorDaemon")
    def test_run_stop_command(self, mock_daemon_class):
        """Test stopping the monitor daemon."""
        mock_daemon = Mock()
        mock_daemon_class.return_value = mock_daemon
        mock_daemon.lifecycle.is_running.return_value = True
        mock_daemon.stop.return_value = True

        args = Namespace(monitor_command="stop", port=8765, host="localhost")

        result = self.command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is True
        mock_daemon.stop.assert_called_once()

    @patch("claude_mpm.cli.commands.monitor.UnifiedMonitorDaemon")
    def test_run_stop_not_running(self, mock_daemon_class):
        """Test stopping when daemon is not running."""
        mock_daemon = Mock()
        mock_daemon_class.return_value = mock_daemon
        mock_daemon.lifecycle.is_running.return_value = False

        args = Namespace(monitor_command="stop", port=8765, host="localhost")

        result = self.command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is True
        assert "No unified monitor daemon running" in result.message

    @patch("claude_mpm.cli.commands.monitor.UnifiedMonitorDaemon")
    def test_run_restart_command(self, mock_daemon_class):
        """Test restarting the monitor daemon."""
        mock_daemon = Mock()
        mock_daemon_class.return_value = mock_daemon
        mock_daemon.restart.return_value = True

        args = Namespace(monitor_command="restart", port=8765, host="localhost")

        result = self.command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is True
        mock_daemon.restart.assert_called_once()

    @patch("claude_mpm.cli.commands.monitor.UnifiedMonitorDaemon")
    def test_run_status_command(self, mock_daemon_class):
        """Test getting status of monitor daemon."""
        mock_daemon = Mock()
        mock_daemon_class.return_value = mock_daemon
        mock_daemon.status.return_value = {
            "running": True,
            "host": "localhost",
            "port": 8765,
            "pid": 12345,
        }

        args = Namespace(monitor_command="status")

        result = self.command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is True
        assert result.data["running"] is True
        mock_daemon.status.assert_called_once()

    @patch("claude_mpm.cli.commands.monitor.UnifiedMonitorDaemon")
    def test_run_status_not_running(self, mock_daemon_class):
        """Test status when daemon is not running."""
        mock_daemon = Mock()
        mock_daemon_class.return_value = mock_daemon
        mock_daemon.status.return_value = {
            "running": False,
            "host": "localhost",
            "port": 8765,
        }

        args = Namespace(monitor_command="status")

        result = self.command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is True
        assert "not running" in result.message

    def test_run_unknown_command(self):
        """Test handling of unknown monitor command."""
        args = Namespace(monitor_command="unknown")

        # First validate will fail
        error = self.command.validate_args(args)
        assert error is not None
