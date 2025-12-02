"""Tests for SubprocessLauncherService.

Tests the extracted subprocess launcher service to ensure it maintains
the same behavior as the original ClaudeRunner methods.
"""

import subprocess
import sys
from unittest.mock import Mock, patch

import pytest

from claude_mpm.services.subprocess_launcher_service import SubprocessLauncherService


class TestSubprocessLauncherService:
    """Test the SubprocessLauncherService class."""

    @pytest.fixture
    def service(self):
        """Create a SubprocessLauncherService instance for testing."""
        return SubprocessLauncherService()

    @pytest.fixture
    def service_with_logger_and_websocket(self):
        """Create a SubprocessLauncherService with mock logger and websocket."""
        mock_logger = Mock()
        mock_websocket = Mock()
        return SubprocessLauncherService(
            project_logger=mock_logger, websocket_server=mock_websocket
        )

    def test_is_subprocess_mode_available(self):
        """Test checking if subprocess mode is available."""
        # This should return True on most Unix-like systems
        result = self.is_subprocess_mode_available()

        # The result depends on the platform, but the method should not crash
        assert isinstance(result, bool)

    def test_create_subprocess_command_basic(self):
        """Test creating a basic subprocess command."""
        base_cmd = ["python", "-m", "claude"]

        result = self.create_subprocess_command(base_cmd)

        assert result == base_cmd
        assert result is not base_cmd  # Should be a copy

    def test_create_subprocess_command_with_additional_args(self):
        """Test creating subprocess command with additional arguments."""
        base_cmd = ["python", "-m", "claude"]
        additional_args = ["--verbose", "--debug"]

        result = self.create_subprocess_command(base_cmd, additional_args)

        expected = ["python", "-m", "claude", "--verbose", "--debug"]
        assert result == expected

    def test_prepare_subprocess_environment_basic(self):
        """Test preparing basic subprocess environment."""
        result = self.prepare_subprocess_environment()

        # Should include current environment
        assert isinstance(result, dict)
        assert len(result) > 0
        # Should include some common environment variables
        assert any(key in result for key in ["PATH", "HOME", "USER"])

    def test_prepare_subprocess_environment_with_base_env(self):
        """Test preparing subprocess environment with base environment."""
        base_env = {"CUSTOM_VAR": "custom_value", "PATH": "/custom/path"}

        result = self.prepare_subprocess_environment(base_env)

        # Should include custom variables
        assert result["CUSTOM_VAR"] == "custom_value"
        # Should override PATH
        assert result["PATH"] == "/custom/path"
        # Should still include other environment variables
        assert len(result) > 2

    @patch("pty.openpty")
    @patch("subprocess.Popen")
    @patch("os.close")
    @patch("sys.stdin.isatty", return_value=False)
    def test_launch_subprocess_interactive_basic(
        self,
        mock_isatty,
        mock_close,
        mock_popen,
        mock_openpty,
        service_with_logger_and_websocket,
    ):
        """Test basic subprocess launching."""
        # Mock PTY creation
        mock_openpty.return_value = (10, 11)  # master_fd, slave_fd

        # Mock process
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = 0  # Process completed
        mock_process.wait.return_value = None
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        cmd = ["python", "-m", "claude"]
        env = {"PATH": "/usr/bin"}

        with patch.object(
            service_with_logger_and_websocket, "_handle_subprocess_io"
        ) as mock_io:
            service_with_logger_and_websocket.launch_subprocess_interactive(cmd, env)

        # Verify subprocess was created correctly
        mock_popen.assert_called_once_with(
            cmd,
            stdin=11,
            stdout=11,
            stderr=11,
            env=env,  # slave_fd
        )

        # Verify PTY was set up
        mock_openpty.assert_called_once()
        # Note: The service closes both slave_fd (11) and master_fd (10) in finally block
        assert mock_close.call_count >= 1

        # Verify I/O handling was called
        mock_io.assert_called_once_with(10, mock_process)  # master_fd, process

        # Verify logging
        service_with_logger_and_websocket.project_logger.log_system.assert_called()

        # Verify WebSocket notifications
        service_with_logger_and_websocket.websocket_server.claude_status_changed.assert_called()

    @patch("pty.openpty")
    @patch("subprocess.Popen")
    @patch("os.close")
    @patch("sys.stdin.isatty", return_value=True)
    @patch("termios.tcgetattr")
    @patch("termios.tcsetattr")
    @patch("tty.setraw")
    def test_launch_subprocess_interactive_with_tty(
        self,
        mock_setraw,
        mock_tcsetattr,
        mock_tcgetattr,
        mock_isatty,
        mock_close,
        mock_popen,
        mock_openpty,
        service,
    ):
        """Test subprocess launching with TTY handling."""
        # Mock PTY creation
        mock_openpty.return_value = (10, 11)

        # Mock terminal settings
        mock_original_tty = {"some": "settings"}
        mock_tcgetattr.return_value = mock_original_tty

        # Mock process
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = 0
        mock_process.wait.return_value = None
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        cmd = ["python", "-m", "claude"]
        env = {"PATH": "/usr/bin"}

        with patch.object(service, "_handle_subprocess_io"):
            service.launch_subprocess_interactive(cmd, env)

        # Verify terminal settings were saved and restored
        mock_tcgetattr.assert_called_with(sys.stdin)
        mock_setraw.assert_called_with(sys.stdin)
        # The actual implementation uses termios.TCSADRAIN (which is 1)
        mock_tcsetattr.assert_called_with(sys.stdin, 1, mock_original_tty)

    @patch("select.select")
    @patch("os.read")
    @patch("os.write")
    def test_handle_subprocess_io(self, mock_read, mock_select, service):
        """Test subprocess I/O handling."""
        master_fd = 10
        mock_process = Mock()

        # Simulate process completion after one iteration
        mock_process.poll.side_effect = [None, 0]  # Running, then completed

        # Mock select to return master_fd has data
        mock_select.return_value = ([master_fd], [], [])

        # Mock reading data from subprocess
        mock_read.return_value = b"Hello from subprocess\n"

        service._handle_subprocess_io(master_fd, mock_process)

        # Verify data was read and written
        mock_read.assert_called_with(master_fd, 4096)
        self.assert_called_with(sys.stdout.fileno(), b"Hello from subprocess\n")

    @patch("select.select")
    @patch("os.read")
    def test_handle_subprocess_io_eof(self, mock_select, service):
        """Test subprocess I/O handling with EOF."""
        master_fd = 10
        mock_process = Mock()
        mock_process.poll.return_value = None  # Still running

        # Mock select to return master_fd has data
        mock_select.return_value = ([master_fd], [], [])

        # Mock EOF (empty read)
        self.return_value = b""

        service._handle_subprocess_io(master_fd, mock_process)

        # Should break on EOF
        self.assert_called_once_with(master_fd, 4096)

    @patch("select.select")
    @patch("os.read")
    def test_handle_subprocess_io_os_error(self, mock_select, service):
        """Test subprocess I/O handling with OS error."""
        master_fd = 10
        mock_process = Mock()
        mock_process.poll.return_value = None  # Still running

        # Mock select to return master_fd has data
        mock_select.return_value = ([master_fd], [], [])

        # Mock OS error
        self.side_effect = OSError("Broken pipe")

        service._handle_subprocess_io(master_fd, mock_process)

        # Should handle the error gracefully
        self.assert_called_once_with(master_fd, 4096)

    @patch("pty.openpty")
    @patch("subprocess.Popen")
    @patch("os.close")
    @patch("sys.stdin.isatty", return_value=False)
    def test_launch_subprocess_interactive_process_cleanup(
        self, mock_isatty, mock_close, mock_popen, mock_openpty, service
    ):
        """Test subprocess cleanup when process doesn't terminate gracefully."""
        # Mock PTY creation
        mock_openpty.return_value = (10, 11)

        # Mock process that doesn't terminate gracefully
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = 0  # Process completed normally for main wait()
        mock_process.returncode = 0

        # Mock the cleanup scenario in finally block
        def mock_poll_side_effect():
            # First call returns None (still running), second call returns 0 (completed)
            if not hasattr(mock_poll_side_effect, "call_count"):
                mock_poll_side_effect.call_count = 0
            mock_poll_side_effect.call_count += 1
            if mock_poll_side_effect.call_count <= 1:
                return None  # Still running during cleanup
            return 0  # Completed

        # Set up the process to simulate cleanup scenario
        mock_process.poll.side_effect = mock_poll_side_effect
        mock_process.wait.side_effect = [
            None,
            subprocess.TimeoutExpired("cmd", 2),
            None,
        ]
        mock_popen.return_value = mock_process

        cmd = ["python", "-m", "claude"]
        env = {"PATH": "/usr/bin"}

        with patch.object(service, "_handle_subprocess_io"):
            service.launch_subprocess_interactive(cmd, env)

        # The process should have been created
        mock_popen.assert_called_once()

    def test_launch_subprocess_interactive_websocket_integration(
        self, service_with_logger_and_websocket
    ):
        """Test WebSocket integration during subprocess launch."""
        with patch("pty.openpty", return_value=(10, 11)), patch(
            "subprocess.Popen"
        ) as mock_popen, patch("os.close"), patch(
            "sys.stdin.isatty", return_value=False
        ), patch.object(
            service_with_logger_and_websocket, "_handle_subprocess_io"
        ):
            # Mock process
            mock_process = Mock()
            mock_process.pid = 12345
            mock_process.poll.return_value = 0
            mock_process.returncode = 0
            mock_popen.return_value = mock_process

            cmd = ["python", "-m", "claude"]
            env = {"PATH": "/usr/bin"}

            service_with_logger_and_websocket.launch_subprocess_interactive(cmd, env)

            # Verify WebSocket status updates
            websocket = service_with_logger_and_websocket.websocket_server

            # Should notify about process start
            websocket.claude_status_changed.assert_any_call(
                status="running", pid=12345, message="Claude subprocess started"
            )

            # Should notify about process end
            websocket.claude_status_changed.assert_any_call(
                status="stopped", message="Claude subprocess exited with code 0"
            )

            # Should end session
            websocket.session_ended.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
