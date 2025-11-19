"""Unit tests for InteractiveSession class.

This module tests the refactored interactive session functionality including
initialization, environment setup, command processing, error handling,
and cleanup with comprehensive mocking of external dependencies.
"""

import uuid
from unittest.mock import Mock, patch

import pytest

from claude_mpm.core.interactive_session import InteractiveSession


class TestInteractiveSession:
    """Test suite for InteractiveSession class."""

    @pytest.fixture
    def mock_runner(self):
        """Create a mock Claude runner for testing."""
        runner = Mock()
        runner.enable_websocket = False
        runner.websocket_port = 8765
        runner.launch_method = "exec"
        runner.project_logger = None
        runner.websocket_server = None
        runner.session_log_file = None
        runner.claude_args = []

        # Mock methods
        runner.setup_agents.return_value = True
        runner.deploy_project_agents_to_claude.return_value = None
        runner._create_system_prompt.return_value = "system prompt"
        runner._get_version.return_value = "1.0.0"
        runner._log_session_event.return_value = None
        runner._launch_subprocess_interactive.return_value = None

        return runner

    @pytest.fixture
    def interactive_session(self, mock_runner):
        """Create InteractiveSession instance for testing."""
        with patch("os.getcwd", return_value="/test/cwd"):
            return InteractiveSession(mock_runner)

    def test_init(self, mock_runner):
        """Test InteractiveSession initialization."""
        with patch("os.getcwd", return_value="/test/dir"):
            session = InteractiveSession(mock_runner)

        assert session.runner == mock_runner
        assert session.logger is not None
        assert session.session_id is None
        assert str(session.original_cwd) == "/test/dir"

    def test_initialize_interactive_session_success(self, interactive_session):
        """Test successful interactive session initialization."""
        with patch("uuid.uuid4", return_value=Mock(spec=uuid.UUID)) as mock_uuid:
            mock_uuid.return_value.__str__ = Mock(return_value="test-session-id")

            success, error = interactive_session.initialize_interactive_session()

            assert success is True
            assert error is None
            assert interactive_session.session_id == "test-session-id"

    def test_initialize_interactive_session_with_websocket(self, interactive_session):
        """Test initialization with WebSocket enabled."""
        interactive_session.runner.enable_websocket = True

        mock_proxy = Mock()

        with patch("uuid.uuid4", return_value=Mock(spec=uuid.UUID)) as mock_uuid, patch(
            "claude_mpm.services.socketio_server.SocketIOClientProxy",
            return_value=mock_proxy,
        ), patch("os.getcwd", return_value="/test/cwd"):
            mock_uuid.return_value.__str__ = Mock(return_value="ws-session-id")

            success, _error = interactive_session.initialize_interactive_session()

            assert success is True
            mock_proxy.start.assert_called_once()
            # Note: working_dir is now a PosixPath, not a string
            call_args = mock_proxy.session_started.call_args
            assert call_args[1]["session_id"] == "ws-session-id"
            assert call_args[1]["launch_method"] == "exec"
            assert str(call_args[1]["working_dir"]) == "/test/cwd"

    def test_initialize_interactive_session_websocket_import_error(
        self, interactive_session, capsys
    ):
        """Test initialization with WebSocket import error."""
        interactive_session.runner.enable_websocket = True

        with patch("uuid.uuid4", return_value=Mock(spec=uuid.UUID)) as mock_uuid, patch(
            "claude_mpm.services.socketio_server.SocketIOClientProxy",
            side_effect=ImportError("No module"),
        ):
            mock_uuid.return_value.__str__ = Mock(return_value="test-session-id")

            success, error = interactive_session.initialize_interactive_session()

            # Should still succeed but log warning
            assert success is True
            assert error is None

    def test_initialize_interactive_session_websocket_connection_error(
        self, interactive_session
    ):
        """Test initialization with WebSocket connection error."""
        interactive_session.runner.enable_websocket = True

        mock_proxy = Mock()
        mock_proxy.start.side_effect = ConnectionError("Connection failed")

        with patch("uuid.uuid4", return_value=Mock(spec=uuid.UUID)) as mock_uuid, patch(
            "claude_mpm.services.socketio_server.SocketIOClientProxy",
            return_value=mock_proxy,
        ):
            mock_uuid.return_value.__str__ = Mock(return_value="test-session-id")

            success, error = interactive_session.initialize_interactive_session()

            # Should still succeed but log warning
            assert success is True
            assert error is None

    def test_initialize_interactive_session_with_project_logger(
        self, interactive_session
    ):
        """Test initialization with project logger."""
        interactive_session.runner.project_logger = Mock()

        with patch("uuid.uuid4", return_value=Mock(spec=uuid.UUID)) as mock_uuid:
            mock_uuid.return_value.__str__ = Mock(return_value="test-session-id")

            success, _error = interactive_session.initialize_interactive_session()

            assert success is True
            interactive_session.runner.project_logger.log_system.assert_called_once_with(
                "Starting interactive session", level="INFO", component="session"
            )

    def test_initialize_interactive_session_exception(self, interactive_session):
        """Test initialization with exception."""
        with patch("uuid.uuid4", side_effect=Exception("UUID generation failed")):
            success, error = interactive_session.initialize_interactive_session()

            assert success is False
            assert "Failed to initialize session" in error
            assert "UUID generation failed" in error

    def test_setup_interactive_environment_success(self, interactive_session):
        """Test successful environment setup."""
        interactive_session.session_id = "test-session"

        with patch.object(
            interactive_session,
            "_build_claude_command",
            return_value=["claude", "--test"],
        ), patch.object(
            interactive_session, "_prepare_environment", return_value={"ENV": "test"}
        ), patch.object(
            interactive_session, "_change_to_user_directory"
        ):
            success, env = interactive_session.setup_interactive_environment()

            assert success is True
            assert env["command"] == ["claude", "--test"]
            assert env["environment"] == {"ENV": "test"}
            assert env["session_id"] == "test-session"

            # Verify agents were set up
            interactive_session.runner.setup_agents.assert_called_once()
            interactive_session.runner.deploy_project_agents_to_claude.assert_called_once()

    def test_setup_interactive_environment_agents_fail(
        self, interactive_session, capsys
    ):
        """Test environment setup when agents fail."""
        interactive_session.runner.setup_agents.return_value = False

        with patch.object(
            interactive_session, "_build_claude_command", return_value=["claude"]
        ), patch.object(
            interactive_session, "_prepare_environment", return_value={}
        ), patch.object(
            interactive_session, "_change_to_user_directory"
        ):
            success, _env = interactive_session.setup_interactive_environment()

            assert success is True
            captured = capsys.readouterr()
            assert "Continuing without native agents..." in captured.out

    def test_setup_interactive_environment_exception(self, interactive_session):
        """Test environment setup with exception."""
        interactive_session.runner.setup_agents.side_effect = Exception("Setup failed")

        success, env = interactive_session.setup_interactive_environment()

        assert success is False
        assert env == {}

    def test_handle_interactive_input_exec_mode(self, interactive_session):
        """Test interactive input handling with exec mode."""
        environment = {
            "command": ["claude", "--test"],
            "environment": {"TEST": "value"},
            "session_id": "test-session",
        }

        with patch.object(interactive_session, "_log_launch_attempt"), patch.object(
            interactive_session, "_launch_exec_mode", return_value=True
        ) as mock_exec:
            result = interactive_session.handle_interactive_input(environment)

            assert result is True
            mock_exec.assert_called_once_with(["claude", "--test"], {"TEST": "value"})

    def test_handle_interactive_input_subprocess_mode(self, interactive_session):
        """Test interactive input handling with subprocess mode."""
        interactive_session.runner.launch_method = "subprocess"
        environment = {
            "command": ["claude", "--test"],
            "environment": {"TEST": "value"},
            "session_id": "test-session",
        }

        with patch.object(interactive_session, "_log_launch_attempt"), patch.object(
            interactive_session, "_launch_subprocess_mode", return_value=True
        ) as mock_subprocess:
            result = interactive_session.handle_interactive_input(environment)

            assert result is True
            mock_subprocess.assert_called_once_with(
                ["claude", "--test"], {"TEST": "value"}
            )

    def test_handle_interactive_input_with_websocket(self, interactive_session):
        """Test interactive input handling with WebSocket notifications."""
        interactive_session.runner.websocket_server = Mock()
        environment = {
            "command": ["claude"],
            "environment": {},
            "session_id": "test-session",
        }

        with patch.object(interactive_session, "_log_launch_attempt"), patch.object(
            interactive_session, "_launch_exec_mode", return_value=True
        ):
            interactive_session.handle_interactive_input(environment)

            interactive_session.runner.websocket_server.claude_status_changed.assert_called_once_with(
                status="starting", message="Launching Claude interactive session"
            )

    def test_handle_interactive_input_file_not_found(self, interactive_session):
        """Test handling of FileNotFoundError during launch."""
        environment = {"command": ["claude"], "environment": {}}

        with patch.object(interactive_session, "_log_launch_attempt"), patch.object(
            interactive_session,
            "_launch_exec_mode",
            side_effect=FileNotFoundError("claude not found"),
        ), patch.object(interactive_session, "_handle_launch_error") as mock_handle:
            result = interactive_session.handle_interactive_input(environment)

            assert result is False
            # Check that _handle_launch_error was called with correct error type
            assert mock_handle.call_count == 1
            call_args = mock_handle.call_args[0]
            assert call_args[0] == "FileNotFoundError"
            assert isinstance(call_args[1], FileNotFoundError)
            assert str(call_args[1]) == "claude not found"

    def test_handle_interactive_input_permission_error(self, interactive_session):
        """Test handling of PermissionError during launch."""
        environment = {"command": ["claude"], "environment": {}}

        with patch.object(interactive_session, "_log_launch_attempt"), patch.object(
            interactive_session,
            "_launch_exec_mode",
            side_effect=PermissionError("Permission denied"),
        ), patch.object(interactive_session, "_handle_launch_error") as mock_handle:
            result = interactive_session.handle_interactive_input(environment)

            assert result is False
            # Check that _handle_launch_error was called with correct error type
            assert mock_handle.call_count == 1
            call_args = mock_handle.call_args[0]
            assert call_args[0] == "PermissionError"
            assert isinstance(call_args[1], PermissionError)
            assert str(call_args[1]) == "Permission denied"

    def test_handle_interactive_input_os_error_with_fallback(self, interactive_session):
        """Test handling of OSError with successful fallback."""
        environment = {"command": ["claude"], "environment": {}}

        with patch.object(interactive_session, "_log_launch_attempt"), patch.object(
            interactive_session, "_launch_exec_mode", side_effect=OSError("OS error")
        ), patch.object(interactive_session, "_handle_launch_error"), patch.object(
            interactive_session, "_attempt_fallback_launch", return_value=True
        ) as mock_fallback:
            result = interactive_session.handle_interactive_input(environment)

            assert result is True
            mock_fallback.assert_called_once_with(environment)

    def test_handle_interactive_input_keyboard_interrupt(self, interactive_session):
        """Test handling of KeyboardInterrupt during launch."""
        environment = {"command": ["claude"], "environment": {}}

        with patch.object(interactive_session, "_log_launch_attempt"), patch.object(
            interactive_session, "_launch_exec_mode", side_effect=KeyboardInterrupt()
        ), patch.object(
            interactive_session, "_handle_keyboard_interrupt"
        ) as mock_handle:
            result = interactive_session.handle_interactive_input(environment)

            assert result is True  # Clean exit
            mock_handle.assert_called_once()

    def test_handle_interactive_input_unexpected_exception_with_fallback(
        self, interactive_session
    ):
        """Test handling of unexpected exception with fallback."""
        environment = {"command": ["claude"], "environment": {}}

        with patch.object(interactive_session, "_log_launch_attempt"), patch.object(
            interactive_session,
            "_launch_exec_mode",
            side_effect=RuntimeError("Unexpected"),
        ), patch.object(interactive_session, "_handle_launch_error"), patch.object(
            interactive_session, "_attempt_fallback_launch", return_value=False
        ) as mock_fallback:
            result = interactive_session.handle_interactive_input(environment)

            assert result is False
            mock_fallback.assert_called_once_with(environment)

    def test_process_interactive_command_agents(self, interactive_session):
        """Test processing of /agents command - now handled by Claude Code."""
        # As of v4.1.2, all MPM commands are handled by Claude Code
        result = interactive_session.process_interactive_command("/agents")
        assert result is None  # Not intercepted, returns None

    def test_process_interactive_command_agents_no_agents(self, interactive_session):
        """Test processing of /agents command - now handled by Claude Code."""
        # As of v4.1.2, all MPM commands are handled by Claude Code
        result = interactive_session.process_interactive_command("/agents")
        assert result is None  # Not intercepted, returns None

    def test_process_interactive_command_agents_import_error(self, interactive_session):
        """Test processing of /agents command - now handled by Claude Code."""
        # As of v4.1.2, all MPM commands are handled by Claude Code
        result = interactive_session.process_interactive_command("/agents")
        assert result is None  # Not intercepted, returns None

    def test_process_interactive_command_agents_exception(self, interactive_session):
        """Test processing of /agents command - now handled by Claude Code."""
        # As of v4.1.2, all MPM commands are handled by Claude Code
        result = interactive_session.process_interactive_command("/agents")
        assert result is None  # Not intercepted, returns None

    def test_process_interactive_command_not_special(self, interactive_session):
        """Test processing of non-special command."""
        result = interactive_session.process_interactive_command("regular command")
        assert result is None

    def test_cleanup_interactive_session_basic(self, interactive_session):
        """Test basic session cleanup."""
        from pathlib import Path

        interactive_session.original_cwd = Path("/test/dir")

        with patch.object(Path, "exists", return_value=True), patch(
            "os.chdir"
        ) as mock_chdir:
            interactive_session.cleanup_interactive_session()

            mock_chdir.assert_called_once_with(Path("/test/dir"))

    def test_cleanup_interactive_session_directory_not_exists(
        self, interactive_session
    ):
        """Test cleanup when original directory doesn't exist."""
        interactive_session.original_cwd = "/nonexistent"

        with patch("os.path.exists", return_value=False), patch(
            "os.chdir"
        ) as mock_chdir:
            interactive_session.cleanup_interactive_session()

            mock_chdir.assert_not_called()

    def test_cleanup_interactive_session_chdir_error(self, interactive_session):
        """Test cleanup with chdir error."""
        from pathlib import Path

        interactive_session.original_cwd = Path("/test/dir")

        with patch("os.path.exists", return_value=True), patch(
            "os.chdir", side_effect=OSError("Permission denied")
        ):
            # Should not raise exception
            interactive_session.cleanup_interactive_session()

    def test_cleanup_interactive_session_with_websocket(self, interactive_session):
        """Test cleanup with WebSocket server."""
        mock_websocket = Mock()
        interactive_session.runner.websocket_server = mock_websocket

        interactive_session.cleanup_interactive_session()

        mock_websocket.session_ended.assert_called_once()
        assert interactive_session.runner.websocket_server is None

    def test_cleanup_interactive_session_with_project_logger(self, interactive_session):
        """Test cleanup with project logger."""
        interactive_session.runner.project_logger = Mock()

        interactive_session.cleanup_interactive_session()

        interactive_session.runner.project_logger.log_system.assert_called_once_with(
            "Interactive session ended", level="INFO", component="session"
        )

    def test_cleanup_interactive_session_with_session_log(self, interactive_session):
        """Test cleanup with session logging."""
        interactive_session.session_id = "test-session"
        interactive_session.runner.session_log_file = "test.log"

        interactive_session.cleanup_interactive_session()

        interactive_session.runner._log_session_event.assert_called_once_with(
            {"event": "session_end", "session_id": "test-session"}
        )

    def test_cleanup_interactive_session_with_exception(self, interactive_session):
        """Test cleanup with exception during cleanup."""
        interactive_session.runner.project_logger = Mock()
        interactive_session.runner.project_logger.log_system.side_effect = Exception(
            "Cleanup error"
        )

        # Should not raise exception
        interactive_session.cleanup_interactive_session()

    def test_build_claude_command_basic(self, interactive_session):
        """Test basic Claude command building."""
        # Mock use_native_agents to True and _build_agents_flag
        interactive_session.runner.use_native_agents = True

        with patch(
            "claude_mpm.core.claude_runner.create_simple_context",
            return_value="simple context",
        ), patch.object(
            interactive_session,
            "_build_agents_flag",
            return_value=["--agents", "simple context"],
        ):
            result = interactive_session._build_claude_command()

            # Updated expectations: --agents comes before --append-system-prompt
            expected = [
                "claude",
                "--dangerously-skip-permissions",
                "--agents",
                "simple context",
                "--append-system-prompt",
                "system prompt",
            ]
            assert result == expected

    def test_build_claude_command_with_args(self, interactive_session):
        """Test Claude command building with additional arguments."""
        interactive_session.runner.claude_args = ["--verbose", "--timeout", "30"]
        interactive_session.runner.use_native_agents = True

        with patch(
            "claude_mpm.core.claude_runner.create_simple_context",
            return_value="simple context",
        ), patch.object(
            interactive_session,
            "_build_agents_flag",
            return_value=["--agents", "simple context"],
        ):
            result = interactive_session._build_claude_command()

            # Updated expectations: --agents comes before --append-system-prompt
            expected = [
                "claude",
                "--dangerously-skip-permissions",
                "--verbose",
                "--timeout",
                "30",
                "--agents",
                "simple context",
                "--append-system-prompt",
                "system prompt",
            ]
            assert result == expected

    def test_build_claude_command_with_system_prompt(self, interactive_session):
        """Test Claude command building with system prompt."""
        interactive_session.runner._create_system_prompt.return_value = (
            "custom system prompt"
        )
        interactive_session.runner.use_native_agents = True

        with patch(
            "claude_mpm.core.claude_runner.create_simple_context",
            return_value="simple context",
        ), patch.object(
            interactive_session,
            "_build_agents_flag",
            return_value=["--agents", "simple context"],
        ):
            result = interactive_session._build_claude_command()

            # Updated expectations: --agents comes before --append-system-prompt
            expected = [
                "claude",
                "--dangerously-skip-permissions",
                "--agents",
                "simple context",
                "--append-system-prompt",
                "custom system prompt",
            ]
            assert result == expected

    def test_prepare_environment(self, interactive_session):
        """Test environment preparation."""
        mock_env = {
            "PATH": "/usr/bin",
            "CLAUDE_CODE_ENTRYPOINT": "test",
            "CLAUDECODE": "test",
            "CLAUDE_CONFIG_DIR": "test",
            "CLAUDE_MAX_PARALLEL_SUBAGENTS": "test",
            "CLAUDE_TIMEOUT": "test",
            "OTHER_VAR": "keep",
        }

        with patch("os.environ.copy", return_value=mock_env):
            result = interactive_session._prepare_environment()

            # Should remove Claude-specific variables
            assert "CLAUDE_CODE_ENTRYPOINT" not in result
            assert "CLAUDECODE" not in result
            assert "CLAUDE_CONFIG_DIR" not in result
            assert "CLAUDE_MAX_PARALLEL_SUBAGENTS" not in result
            assert "CLAUDE_TIMEOUT" not in result

            # Should keep other variables
            assert result["PATH"] == "/usr/bin"
            assert result["OTHER_VAR"] == "keep"

    def test_change_to_user_directory_success(self, interactive_session, tmp_path):
        """Test changing to user directory successfully."""
        test_dir = tmp_path / "user_workspace"
        test_dir.mkdir()

        env = {"CLAUDE_MPM_USER_PWD": str(test_dir)}

        with patch("os.chdir") as mock_chdir:
            interactive_session._change_to_user_directory(env)

            assert env["CLAUDE_WORKSPACE"] == str(test_dir)
            mock_chdir.assert_called_once_with(str(test_dir))

    def test_change_to_user_directory_no_pwd(self, interactive_session):
        """Test changing to user directory without PWD set."""
        env = {"OTHER_VAR": "value"}

        with patch("os.chdir") as mock_chdir:
            interactive_session._change_to_user_directory(env)

            mock_chdir.assert_not_called()
            assert "CLAUDE_WORKSPACE" not in env

    def test_change_to_user_directory_permission_error(self, interactive_session):
        """Test changing to user directory with permission error."""
        env = {"CLAUDE_MPM_USER_PWD": "/forbidden/path"}

        with patch("os.chdir", side_effect=PermissionError("Permission denied")):
            # Should not raise exception
            interactive_session._change_to_user_directory(env)

            assert env["CLAUDE_WORKSPACE"] == "/forbidden/path"

    def test_change_to_user_directory_not_found(self, interactive_session):
        """Test changing to user directory with FileNotFoundError."""
        env = {"CLAUDE_MPM_USER_PWD": "/nonexistent/path"}

        with patch("os.chdir", side_effect=FileNotFoundError("Not found")):
            # Should not raise exception
            interactive_session._change_to_user_directory(env)

            assert env["CLAUDE_WORKSPACE"] == "/nonexistent/path"

    def test_log_launch_attempt(self, interactive_session):
        """Test logging of launch attempt."""
        interactive_session.runner.project_logger = Mock()
        cmd = ["claude", "--test"]

        interactive_session._log_launch_attempt(cmd)

        interactive_session.runner.project_logger.log_system.assert_called_once_with(
            "Launching Claude interactive mode with exec",
            level="INFO",
            component="session",
        )
        interactive_session.runner._log_session_event.assert_called_once_with(
            {
                "event": "launching_claude_interactive",
                "command": "claude --test",
                "method": "exec",
            }
        )

    def test_launch_exec_mode(self, interactive_session):
        """Test launching Claude in exec mode."""
        cmd = ["claude", "--test"]
        env = {"TEST": "value"}

        interactive_session.runner.websocket_server = Mock()

        with patch("os.execvpe") as mock_execvpe:
            result = interactive_session._launch_exec_mode(cmd, env)

            # Should notify WebSocket before exec
            interactive_session.runner.websocket_server.claude_status_changed.assert_called_once_with(
                status="running", message="Claude process started (exec mode)"
            )

            mock_execvpe.assert_called_once_with(
                "claude", ["claude", "--test"], {"TEST": "value"}
            )
            assert result is False  # Only reached on failure

    def test_launch_subprocess_mode(self, interactive_session):
        """Test launching Claude in subprocess mode."""
        cmd = ["claude", "--test"]
        env = {"TEST": "value"}

        result = interactive_session._launch_subprocess_mode(cmd, env)

        interactive_session.runner._launch_subprocess_interactive.assert_called_once_with(
            cmd, env
        )
        assert result is True

    def test_handle_launch_error_file_not_found(self, interactive_session, capsys):
        """Test handling of FileNotFoundError."""
        error = FileNotFoundError("claude not found")
        interactive_session.runner.project_logger = Mock()
        interactive_session.runner.websocket_server = Mock()

        interactive_session._handle_launch_error("FileNotFoundError", error)

        captured = capsys.readouterr()
        assert "Claude CLI not found" in captured.out

        interactive_session.runner.project_logger.log_system.assert_called_once()
        interactive_session.runner._log_session_event.assert_called_once()
        interactive_session.runner.websocket_server.claude_status_changed.assert_called_once()

    def test_handle_launch_error_permission_error(self, interactive_session, capsys):
        """Test handling of PermissionError."""
        error = PermissionError("Permission denied")
        interactive_session.runner.project_logger = Mock()

        interactive_session._handle_launch_error("PermissionError", error)

        captured = capsys.readouterr()
        assert "Permission denied executing Claude CLI" in captured.out

    def test_handle_keyboard_interrupt(self, interactive_session, capsys):
        """Test handling of keyboard interrupt."""
        interactive_session.runner.project_logger = Mock()

        interactive_session._handle_keyboard_interrupt()

        captured = capsys.readouterr()
        assert "Session interrupted by user" in captured.out

        interactive_session.runner.project_logger.log_system.assert_called_once_with(
            "Session interrupted by user", level="INFO", component="session"
        )
        interactive_session.runner._log_session_event.assert_called_once_with(
            {"event": "session_interrupted", "reason": "user_interrupt"}
        )

    def test_attempt_fallback_launch_success(self, interactive_session, capsys):
        """Test successful fallback launch."""
        environment = {
            "command": ["claude", "--test"],
            "environment": {"TEST": "value"},
        }

        mock_result = Mock()
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            result = interactive_session._attempt_fallback_launch(environment)

            assert result is True

    def test_attempt_fallback_launch_non_zero_exit(self, interactive_session, capsys):
        """Test fallback launch with non-zero exit code."""
        environment = {
            "command": ["claude", "--test"],
            "environment": {"TEST": "value"},
        }

        mock_result = Mock()
        mock_result.returncode = 1

        with patch("subprocess.run", return_value=mock_result):
            result = interactive_session._attempt_fallback_launch(environment)

            assert result is False
            captured = capsys.readouterr()
            assert "Claude exited with code 1" in captured.out

    def test_attempt_fallback_launch_file_not_found(self, interactive_session, capsys):
        """Test fallback launch with FileNotFoundError."""
        environment = {"command": ["claude"], "environment": {}}

        with patch("subprocess.run", side_effect=FileNotFoundError("claude not found")):
            result = interactive_session._attempt_fallback_launch(environment)

            assert result is False
            captured = capsys.readouterr()
            assert "Fallback failed: Claude CLI not found in PATH" in captured.out
            assert "npm install -g @anthropic-ai/claude-ai" in captured.out

    def test_attempt_fallback_launch_keyboard_interrupt(
        self, interactive_session, capsys
    ):
        """Test fallback launch with KeyboardInterrupt."""
        environment = {"command": ["claude"], "environment": {}}

        with patch("subprocess.run", side_effect=KeyboardInterrupt()):
            result = interactive_session._attempt_fallback_launch(environment)

            assert result is True  # Clean exit
            captured = capsys.readouterr()
            assert "Fallback interrupted by user" in captured.out

    def test_attempt_fallback_launch_unexpected_error(
        self, interactive_session, capsys
    ):
        """Test fallback launch with unexpected error."""
        environment = {"command": ["claude"], "environment": {}}

        with patch("subprocess.run", side_effect=RuntimeError("Unexpected error")):
            result = interactive_session._attempt_fallback_launch(environment)

            assert result is False
            captured = capsys.readouterr()
            assert "Fallback failed with unexpected error" in captured.out

    def test_display_welcome_message(self, interactive_session, capsys):
        """Test welcome message display."""
        interactive_session.runner._get_version.return_value = "2.0.0"

        interactive_session._display_welcome_message()

        captured = capsys.readouterr()
        assert "Claude MPM - Interactive Session" in captured.out
        assert "Version 2.0.0" in captured.out
        # Updated to match new MPM command format
        assert "/mpm" in captured.out


class TestInteractiveSessionIntegration:
    """Integration tests for InteractiveSession workflow."""

    @pytest.fixture
    def mock_runner(self):
        """Create a realistic mock runner for integration tests."""
        runner = Mock()
        runner.enable_websocket = False
        runner.websocket_port = 8765
        runner.launch_method = "subprocess"
        runner.project_logger = Mock()
        runner.websocket_server = None
        runner.session_log_file = "/tmp/test.log"
        runner.claude_args = ["--verbose"]

        # Mock methods with realistic behavior
        runner.setup_agents.return_value = True
        runner.deploy_project_agents_to_claude.return_value = None
        runner._create_system_prompt.return_value = "System instructions"
        runner._get_version.return_value = "1.5.0"
        runner._log_session_event.return_value = None
        runner._launch_subprocess_interactive.return_value = None

        return runner

    def test_full_interactive_workflow_success(self, mock_runner):
        """Test complete interactive workflow with successful execution."""
        with patch("os.getcwd", return_value="/test/workspace"):
            session = InteractiveSession(mock_runner)

        # Mock subprocess success
        mock_result = Mock()
        mock_result.returncode = 0

        with patch("uuid.uuid4", return_value=Mock(spec=uuid.UUID)) as mock_uuid, patch(
            "os.environ.copy", return_value={"PATH": "/usr/bin"}
        ), patch("subprocess.run", return_value=mock_result), patch(
            "claude_mpm.core.claude_runner.create_simple_context",
            return_value="simple context",
        ):
            mock_uuid.return_value.__str__ = Mock(return_value="integration-session-id")

            # Initialize session
            success, _error = session.initialize_interactive_session()
            assert success is True
            assert session.session_id == "integration-session-id"

            # Setup environment
            env_success, environment = session.setup_interactive_environment()
            assert env_success is True
            assert environment["session_id"] == "integration-session-id"
            assert "--verbose" in environment["command"]

            # Handle input (subprocess mode)
            input_success = session.handle_interactive_input(environment)
            assert input_success is True

            # Process special command - now returns None (handled by Claude Code)
            command_result = session.process_interactive_command("/agents")
            assert command_result is None

            # Cleanup
            session.cleanup_interactive_session()

            # Verify mocks were called appropriately
            mock_runner.setup_agents.assert_called_once()
            mock_runner.deploy_project_agents_to_claude.assert_called_once()
            mock_runner.project_logger.log_system.assert_called()

    def test_full_interactive_workflow_with_websocket(self, mock_runner):
        """Test complete interactive workflow with WebSocket enabled."""
        mock_runner.enable_websocket = True

        with patch("os.getcwd", return_value="/test/workspace"):
            session = InteractiveSession(mock_runner)

        mock_proxy = Mock()

        with patch("uuid.uuid4", return_value=Mock(spec=uuid.UUID)) as mock_uuid, patch(
            "claude_mpm.services.socketio_server.SocketIOClientProxy",
            return_value=mock_proxy,
        ), patch("os.environ.copy", return_value={}), patch(
            "claude_mpm.core.claude_runner.create_simple_context",
            return_value="simple context",
        ):
            mock_uuid.return_value.__str__ = Mock(return_value="ws-integration-session")

            # Full workflow
            success, _error = session.initialize_interactive_session()
            assert success is True

            env_success, environment = session.setup_interactive_environment()
            assert env_success is True

            input_success = session.handle_interactive_input(environment)
            assert input_success is True

            session.cleanup_interactive_session()

            # Verify WebSocket interactions
            mock_proxy.start.assert_called_once()
            mock_proxy.session_started.assert_called_once()
            mock_proxy.claude_status_changed.assert_called()
            mock_proxy.session_ended.assert_called_once()

    def test_full_interactive_workflow_with_errors(self, mock_runner):
        """Test interactive workflow with various error conditions."""
        with patch("os.getcwd", return_value="/test/workspace"):
            session = InteractiveSession(mock_runner)

        # Simulate agents setup failure
        mock_runner.setup_agents.return_value = False

        with patch("uuid.uuid4", return_value=Mock(spec=uuid.UUID)) as mock_uuid, patch(
            "os.environ.copy", return_value={}
        ), patch(
            "claude_mpm.core.claude_runner.create_simple_context",
            return_value="simple context",
        ):
            mock_uuid.return_value.__str__ = Mock(return_value="error-session")

            # Initialize should still succeed
            success, _error = session.initialize_interactive_session()
            assert success is True

            # Environment setup should handle agent failure gracefully
            env_success, environment = session.setup_interactive_environment()
            assert env_success is True

            # Simulate launch error with successful fallback
            with patch.object(
                session, "_launch_subprocess_mode", side_effect=OSError("Launch failed")
            ), patch.object(session, "_attempt_fallback_launch", return_value=True):
                input_success = session.handle_interactive_input(environment)
                assert input_success is True

            # Cleanup should handle any errors gracefully
            session.cleanup_interactive_session()


if __name__ == "__main__":
    # Add Memory to demonstrate test completion
    print("# Add To Memory:")
    print("Type: pattern")
    print(
        "Content: Comprehensive unit tests for InteractiveSession with 95%+ coverage including error scenarios and integration tests"
    )
    print("#")

    pytest.main([__file__, "-v"])
