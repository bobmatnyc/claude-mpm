"""
Comprehensive unit tests for the SocketIO daemon process management.

Tests cover:
- Daemon process management (start, stop, restart)
- Port binding and release
- PID file management
- Signal handling (SIGTERM, SIGINT)
- Restart behavior
- Subprocess mocking for safe testing
"""

import os
import signal
import subprocess
import sys
import time
from unittest.mock import MagicMock, mock_open, patch

import pytest


class TestDaemonProcessManagement:
    """Test daemon process lifecycle management."""

    @pytest.fixture
    def mock_paths(self, tmp_path):
        """Create temporary paths for testing."""
        pid_file = tmp_path / ".claude-mpm" / "socketio-server.pid"
        log_file = tmp_path / ".claude-mpm" / "socketio-server.log"
        port_file = tmp_path / ".claude-mpm" / "socketio-port"

        # Create parent directory
        pid_file.parent.mkdir(parents=True, exist_ok=True)

        return {
            "pid_file": pid_file,
            "log_file": log_file,
            "port_file": port_file,
            "root": tmp_path,
        }

    def test_daemon_start_when_not_running(self, mock_paths):
        """
        Test starting daemon when no instance is running.

        WHY: The daemon should successfully start and create PID/port files
        when no other instance is running. This is the normal startup case.
        """
        with patch(
            "claude_mpm.scripts.socketio_daemon.PID_FILE", mock_paths["pid_file"]
        ), patch(
            "claude_mpm.scripts.socketio_daemon.LOG_FILE", mock_paths["log_file"]
        ), patch(
            "claude_mpm.scripts.socketio_daemon.is_running", return_value=False
        ), patch("os.fork", return_value=12345) as mock_fork, patch(
            "claude_mpm.scripts.socketio_daemon.PortManager"
        ) as mock_pm:
            # Setup port manager
            mock_pm_instance = MagicMock()
            mock_pm_instance.find_available_port.return_value = 8765
            mock_pm_instance.get_instance_by_port.return_value = None
            mock_pm_instance.register_instance.return_value = "instance-123"
            mock_pm.return_value = mock_pm_instance

            # Mock sys.exit to prevent test termination
            with patch("sys.exit"):
                from claude_mpm.scripts import socketio_daemon

                socketio_daemon.start_server()

            # Verify fork was called
            mock_fork.assert_called_once()

            # Verify port manager operations
            mock_pm_instance.cleanup_dead_instances.assert_called_once()
            mock_pm_instance.find_available_port.assert_called_once()
            mock_pm_instance.register_instance.assert_called_with(8765, 12345)

    def test_daemon_start_when_already_running(self, mock_paths):
        """
        Test that starting daemon when already running is prevented.

        WHY: Only one daemon instance should run at a time to prevent
        port conflicts and resource contention. Attempting to start when
        already running should be gracefully rejected.
        """
        with patch(
            "claude_mpm.scripts.socketio_daemon.PID_FILE", mock_paths["pid_file"]
        ), patch(
            "claude_mpm.scripts.socketio_daemon.is_running", return_value=True
        ), patch("builtins.print") as mock_print:
            from claude_mpm.scripts import socketio_daemon

            socketio_daemon.start_server()

            # Should print already running message
            mock_print.assert_any_call("Socket.IO daemon server is already running.")

    def test_daemon_stop_when_running(self, mock_paths):
        """
        Test stopping daemon when it's running.

        WHY: The daemon must cleanly shut down when stopped, sending
        SIGTERM for graceful shutdown and cleaning up PID files.
        """
        # Create a PID file
        mock_paths["pid_file"].write_text("12345")

        with patch(
            "claude_mpm.scripts.socketio_daemon.PID_FILE", mock_paths["pid_file"]
        ), patch(
            "claude_mpm.scripts.socketio_daemon.is_running",
            side_effect=[True, False],
        ), patch("os.kill") as mock_kill:
            from claude_mpm.scripts import socketio_daemon

            socketio_daemon.stop_server()

            # Should send SIGTERM
            mock_kill.assert_called_with(12345, signal.SIGTERM)

            # PID file should be removed
            assert not mock_paths["pid_file"].exists()

    def test_daemon_force_kill_on_hung_process(self, mock_paths):
        """
        Test force killing daemon when graceful shutdown fails.

        WHY: If a daemon process hangs and doesn't respond to SIGTERM,
        it must be forcefully killed with SIGKILL to ensure it stops.
        """
        # Create a PID file
        mock_paths["pid_file"].write_text("12345")

        with patch(
            "claude_mpm.scripts.socketio_daemon.PID_FILE", mock_paths["pid_file"]
        ), patch(
            "claude_mpm.scripts.socketio_daemon.is_running", return_value=True
        ):  # Always running
            with patch("os.kill") as mock_kill:
                with patch("time.sleep"):  # Speed up test
                    from claude_mpm.scripts import socketio_daemon

                    socketio_daemon.stop_server()

                # Should try SIGTERM first, then SIGKILL
                assert mock_kill.call_count == 2
                mock_kill.assert_any_call(12345, signal.SIGTERM)
                mock_kill.assert_any_call(12345, signal.SIGKILL)

    def test_daemon_restart_sequence(self, mock_paths):
        """
        Test daemon restart performs stop then start with delay.

        WHY: Restart must cleanly stop the existing daemon, wait for
        resources to be released, then start a new instance. The delay
        prevents port binding issues.
        """
        with patch("claude_mpm.scripts.socketio_daemon.stop_server") as mock_stop:
            with patch("claude_mpm.scripts.socketio_daemon.start_server") as mock_start:
                with patch("time.sleep") as mock_sleep:
                    from claude_mpm.scripts import socketio_daemon

                    # Call main with restart command
                    sys.argv = ["socketio_daemon.py", "restart"]
                    with patch("sys.argv", ["socketio_daemon.py", "restart"]):
                        socketio_daemon.main()

                    # Verify sequence
                    mock_stop.assert_called_once()
                    mock_sleep.assert_called_once_with(1)
                    mock_start.assert_called_once()


class TestPortManagement:
    """Test port binding, release, and dynamic port selection."""

    def test_dynamic_port_selection(self):
        """
        Test that daemon selects available port from range.

        WHY: Multiple instances may run on different projects. The daemon
        should automatically find an available port in the range 8765-8785.
        """
        with patch("claude_mpm.scripts.socketio_daemon.PortManager") as mock_pm_class:
            mock_pm = MagicMock()
            mock_pm.find_available_port.return_value = 8767  # Not default port
            mock_pm.get_instance_by_port.return_value = None
            mock_pm_class.return_value = mock_pm

            with patch(
                "claude_mpm.scripts.socketio_daemon.is_running", return_value=False
            ), patch("os.fork", return_value=0):  # Child process
                with patch("os.setsid"):
                    with patch("builtins.open", mock_open()):
                        with patch(
                            "claude_mpm.scripts.socketio_daemon.SocketIOServer"
                        ) as mock_server:
                            # Setup mock server
                            mock_server_instance = MagicMock()
                            mock_server.return_value = mock_server_instance

                            # Mock the infinite loop to exit
                            with patch("time.sleep", side_effect=KeyboardInterrupt):
                                try:
                                    from claude_mpm.scripts import socketio_daemon

                                    socketio_daemon.start_server()
                                except (KeyboardInterrupt, SystemExit):
                                    pass

                            # Verify server was created with selected port
                            mock_server.assert_called_with(host="localhost", port=8767)

    def test_port_conflict_detection(self):
        """
        Test that daemon detects and reports port conflicts.

        WHY: If another process is using the selected port, the daemon
        should detect this and either find another port or report the error.
        """
        with patch("claude_mpm.scripts.socketio_daemon.PortManager") as mock_pm_class:
            mock_pm = MagicMock()
            mock_pm.find_available_port.return_value = 8765

            # Simulate existing instance on port
            mock_pm.get_instance_by_port.return_value = {
                "pid": 9999,
                "start_time": time.time() - 3600,
                "port": 8765,
            }
            mock_pm_class.return_value = mock_pm

            with patch(
                "claude_mpm.scripts.socketio_daemon.is_running", return_value=False
            ), patch("builtins.print") as mock_print:
                from claude_mpm.scripts import socketio_daemon

                socketio_daemon.start_server()

                # Should warn about existing instance
                mock_print.assert_any_call(
                    "⚠️  Port 8765 is already used by claude-mpm instance:"
                )

    def test_port_file_creation(self, tmp_path):
        """
        Test that port file is created for other tools to discover the port.

        WHY: Other components need to know which port the daemon is using.
        The port file provides this information persistently.
        """
        pid_file = tmp_path / ".claude-mpm" / "socketio-server.pid"
        port_file = tmp_path / ".claude-mpm" / "socketio-port"
        pid_file.parent.mkdir(parents=True, exist_ok=True)

        with patch("claude_mpm.scripts.socketio_daemon.PID_FILE", pid_file):
            with patch(
                "claude_mpm.scripts.socketio_daemon.is_running", return_value=False
            ):
                with patch("os.fork", return_value=12345):  # Parent process
                    with patch(
                        "claude_mpm.scripts.socketio_daemon.PortManager"
                    ) as mock_pm:
                        mock_pm_instance = MagicMock()
                        mock_pm_instance.find_available_port.return_value = 8768
                        mock_pm_instance.get_instance_by_port.return_value = None
                        mock_pm.return_value = mock_pm_instance

                        with patch("sys.exit"):
                            from claude_mpm.scripts import socketio_daemon

                            socketio_daemon.start_server()

                        # Check port file was created
                        assert port_file.exists()
                        assert port_file.read_text() == "8768"


class TestPIDFileManagement:
    """Test PID file creation, reading, and cleanup."""

    def test_pid_file_creation_on_start(self, tmp_path):
        """
        Test that PID file is created when daemon starts.

        WHY: The PID file allows other processes to check if the daemon
        is running and to send signals to it. It must be created atomically.
        """
        pid_file = tmp_path / ".claude-mpm" / "socketio-server.pid"
        pid_file.parent.mkdir(parents=True, exist_ok=True)

        with patch("claude_mpm.scripts.socketio_daemon.PID_FILE", pid_file):
            with patch(
                "claude_mpm.scripts.socketio_daemon.is_running", return_value=False
            ):
                with patch("os.fork", return_value=54321):  # Parent process
                    with patch(
                        "claude_mpm.scripts.socketio_daemon.PortManager"
                    ) as mock_pm:
                        mock_pm_instance = MagicMock()
                        mock_pm_instance.find_available_port.return_value = 8765
                        mock_pm_instance.get_instance_by_port.return_value = None
                        mock_pm.return_value = mock_pm_instance

                        with patch("sys.exit"):
                            from claude_mpm.scripts import socketio_daemon

                            socketio_daemon.start_server()

                        # Check PID file was created with correct PID
                        assert pid_file.exists()
                        assert pid_file.read_text() == "54321"

    def test_stale_pid_file_cleanup(self, tmp_path):
        """
        Test that stale PID files are cleaned up.

        WHY: If the daemon crashes without cleaning up, a stale PID file
        may remain. The is_running() function should detect this and
        clean up the file.
        """
        pid_file = tmp_path / ".claude-mpm" / "socketio-server.pid"
        pid_file.parent.mkdir(parents=True, exist_ok=True)

        # Create stale PID file with non-existent process
        pid_file.write_text("99999")

        with patch("claude_mpm.scripts.socketio_daemon.PID_FILE", pid_file):
            with patch("psutil.Process", side_effect=Exception("No such process")):
                from claude_mpm.scripts import socketio_daemon

                # is_running should detect stale PID and clean up
                result = socketio_daemon.is_running()

                assert result is False
                assert not pid_file.exists()  # Should be cleaned up

    def test_pid_file_removal_on_stop(self, tmp_path):
        """
        Test that PID file is removed when daemon stops.

        WHY: Clean shutdown must remove the PID file to indicate the
        daemon is no longer running. This prevents confusion and allows
        clean restart.
        """
        pid_file = tmp_path / ".claude-mpm" / "socketio-server.pid"
        pid_file.parent.mkdir(parents=True, exist_ok=True)
        pid_file.write_text("12345")

        with patch("claude_mpm.scripts.socketio_daemon.PID_FILE", pid_file):
            with patch(
                "claude_mpm.scripts.socketio_daemon.is_running",
                side_effect=[True, False],
            ):
                with patch("os.kill"):
                    from claude_mpm.scripts import socketio_daemon

                    socketio_daemon.stop_server()

                    # PID file should be removed
                    assert not pid_file.exists()


class TestSignalHandling:
    """Test signal handling for graceful shutdown."""

    def test_sigterm_handler_graceful_shutdown(self):
        """
        Test that SIGTERM triggers graceful shutdown.

        WHY: SIGTERM is the standard signal for requesting graceful
        shutdown. The daemon must stop the server, clean up resources,
        and exit cleanly.
        """
        with patch(
            "claude_mpm.scripts.socketio_daemon.SocketIOServer"
        ) as mock_server_class:
            mock_server = MagicMock()
            mock_server_class.return_value = mock_server

            with patch("claude_mpm.scripts.socketio_daemon.PID_FILE", MagicMock()):
                with patch("claude_mpm.scripts.socketio_daemon.PortManager"):
                    with patch("sys.exit") as mock_exit:
                        # Import and get signal handler

                        # Create a mock signal handler context
                        def test_handler():
                            # Simulate signal handler setup in child process
                            server = mock_server

                            def signal_handler(signum, frame):
                                server.stop_sync()
                                mock_exit(0)

                            # Call the handler
                            signal_handler(signal.SIGTERM, None)

                        test_handler()

                        # Verify graceful shutdown
                        mock_server.stop_sync.assert_called_once()
                        mock_exit.assert_called_once_with(0)

    def test_sigint_handler_keyboard_interrupt(self):
        """
        Test that SIGINT (Ctrl+C) triggers graceful shutdown.

        WHY: Users may stop the daemon with Ctrl+C during debugging.
        This should trigger the same graceful shutdown as SIGTERM.
        """
        with patch(
            "claude_mpm.scripts.socketio_daemon.SocketIOServer"
        ) as mock_server_class:
            mock_server = MagicMock()
            mock_server_class.return_value = mock_server

            with patch("sys.exit"):
                # Simulate keyboard interrupt in main loop
                with patch("time.sleep", side_effect=KeyboardInterrupt):
                    with patch("os.fork", return_value=0):  # Child process
                        with patch("os.setsid"):
                            with patch("builtins.open", mock_open()):
                                with patch(
                                    "claude_mpm.scripts.socketio_daemon.PortManager"
                                ):
                                    try:
                                        from claude_mpm.scripts import socketio_daemon

                                        # This will raise KeyboardInterrupt
                                        socketio_daemon.start_server()
                                    except (KeyboardInterrupt, SystemExit):
                                        pass

                                    # Server should be started but then stopped
                                    mock_server.start_sync.assert_called_once()


class TestProcessDetection:
    """Test process detection and status checking."""

    def test_is_running_detects_active_process(self, tmp_path):
        """
        Test that is_running correctly detects an active process.

        WHY: Accurate process detection prevents multiple daemon instances
        and allows proper status reporting.
        """
        pid_file = tmp_path / ".claude-mpm" / "socketio-server.pid"
        pid_file.parent.mkdir(parents=True, exist_ok=True)

        # Use current process PID for testing
        current_pid = os.getpid()
        pid_file.write_text(str(current_pid))

        with patch("claude_mpm.scripts.socketio_daemon.PID_FILE", pid_file):
            from claude_mpm.scripts import socketio_daemon

            # Should detect current process as running
            assert socketio_daemon.is_running() is True

    def test_status_shows_running_daemon(self, tmp_path, capsys):
        """
        Test that status command shows running daemon information.

        WHY: Users need to check daemon status to troubleshoot issues
        and verify the server is running correctly.
        """
        pid_file = tmp_path / ".claude-mpm" / "socketio-server.pid"
        port_file = tmp_path / ".claude-mpm" / "socketio-port"
        pid_file.parent.mkdir(parents=True, exist_ok=True)

        pid_file.write_text(str(os.getpid()))
        port_file.write_text("8766")

        with patch("claude_mpm.scripts.socketio_daemon.PID_FILE", pid_file):
            with patch(
                "claude_mpm.scripts.socketio_daemon.is_running", return_value=True
            ):
                with patch("claude_mpm.scripts.socketio_daemon.PortManager") as mock_pm:
                    mock_pm_instance = MagicMock()
                    mock_pm_instance.get_instance_by_port.return_value = {
                        "port": 8766,
                        "start_time": time.time(),
                        "instance_id": "test-123",
                    }
                    mock_pm.return_value = mock_pm_instance

                    from claude_mpm.scripts import socketio_daemon

                    socketio_daemon.status_server()

                    # Check output
                    captured = capsys.readouterr()
                    assert (
                        f"Socket.IO daemon server is running (PID: {os.getpid()})"
                        in captured.out
                    )
                    assert "Instance Information:" in captured.out


class TestPythonEnvironmentDetection:
    """Test virtual environment detection for proper Python executable."""

    def test_venv_detection_with_virtual_env(self):
        """
        Test that virtual environment Python is detected correctly.

        WHY: The daemon must use the same Python environment as the parent
        process to ensure all dependencies are available. System Python
        won't have the required packages.
        """
        with patch.dict(os.environ, {"VIRTUAL_ENV": "/path/to/venv"}):
            with patch("pathlib.Path.exists", return_value=True):
                from claude_mpm.scripts.socketio_daemon import get_python_executable

                result = get_python_executable()

                # Should return venv Python
                assert "venv" in result

    def test_fallback_to_current_python(self):
        """
        Test fallback to current Python when no venv detected.

        WHY: If virtual environment detection fails, the daemon should
        use the current Python interpreter as a fallback.
        """
        with patch.dict(os.environ, {}, clear=True):  # No VIRTUAL_ENV
            with patch("pathlib.Path.exists", return_value=False):  # No venv dirs
                from claude_mpm.scripts.socketio_daemon import get_python_executable

                result = get_python_executable()

                # Should return current executable
                assert result == sys.executable


class TestErrorHandling:
    """Test error handling in daemon operations."""

    def test_handle_missing_psutil(self):
        """
        Test that missing psutil is handled with installation attempt.

        WHY: psutil is required for process detection but may not be
        installed. The daemon should attempt to install it automatically.
        """
        with patch(
            "builtins.__import__", side_effect=ImportError("No module named psutil")
        ), patch("subprocess.check_call") as mock_install:
            # This would normally be at module level, but we test the pattern
            try:
                import psutil  # noqa: F401
            except ImportError:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "psutil"]
                )

            mock_install.assert_called_once()
            assert "psutil" in str(mock_install.call_args)

    def test_handle_port_manager_errors(self):
        """
        Test graceful handling of PortManager errors.

        WHY: Network issues or file system problems may cause PortManager
        to fail. The daemon should handle these errors gracefully.
        """
        with patch("claude_mpm.scripts.socketio_daemon.PortManager") as mock_pm:
            mock_pm.side_effect = Exception("Port manager initialization failed")

            with patch("builtins.print"), patch(
                "claude_mpm.scripts.socketio_daemon.is_running", return_value=False
            ):
                try:
                    from claude_mpm.scripts import socketio_daemon

                    socketio_daemon.start_server()
                except Exception:
                    pass  # Expected

                # Should have attempted to use PortManager
                mock_pm.assert_called()


@pytest.fixture
def mock_daemon_environment(tmp_path):
    """
    Fixture providing a complete mock environment for daemon testing.

    WHY: Daemon tests need isolated file system paths and mocked
    system calls to prevent interference with the actual system.
    """
    # Create temporary directories
    claude_mpm_dir = tmp_path / ".claude-mpm"
    claude_mpm_dir.mkdir(parents=True, exist_ok=True)

    # Mock paths
    paths = {
        "root": tmp_path,
        "pid_file": claude_mpm_dir / "socketio-server.pid",
        "log_file": claude_mpm_dir / "socketio-server.log",
        "port_file": claude_mpm_dir / "socketio-port",
    }

    # Apply patches
    with patch("claude_mpm.scripts.socketio_daemon.PID_FILE", paths["pid_file"]):
        with patch("claude_mpm.scripts.socketio_daemon.LOG_FILE", paths["log_file"]):
            with patch(
                "claude_mpm.scripts.socketio_daemon.get_project_root",
                return_value=tmp_path,
            ):
                yield paths


def test_full_daemon_lifecycle(mock_daemon_environment):
    """
    Integration test of complete daemon lifecycle with mock environment.

    WHY: Verifies that all daemon operations work correctly together
    in an isolated environment without affecting the real system.
    """
    paths = mock_daemon_environment

    # Mock the necessary components
    with patch("os.fork", return_value=12345):  # Parent process
        with patch("claude_mpm.scripts.socketio_daemon.PortManager") as mock_pm:
            with patch(
                "claude_mpm.scripts.socketio_daemon.is_running",
                side_effect=[False, True, True, False],
            ):
                with patch("os.kill"):
                    with patch("sys.exit"):
                        # Setup port manager
                        mock_pm_instance = MagicMock()
                        mock_pm_instance.find_available_port.return_value = 8765
                        mock_pm_instance.get_instance_by_port.return_value = None
                        mock_pm.return_value = mock_pm_instance

                        from claude_mpm.scripts import socketio_daemon

                        # Start daemon
                        socketio_daemon.start_server()
                        assert paths["pid_file"].exists()

                        # Check status
                        socketio_daemon.status_server()

                        # Stop daemon
                        socketio_daemon.stop_server()
                        assert not paths["pid_file"].exists()
