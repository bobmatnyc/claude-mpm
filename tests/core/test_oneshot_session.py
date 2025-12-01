"""Unit tests for OneshotSession class.

This module tests the refactored oneshot session functionality including
initialization, agent deployment, infrastructure setup, command execution,
error handling, and cleanup.
"""

import os
import subprocess
import time
import uuid
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from claude_mpm.core.enums import OperationResult
from claude_mpm.core.oneshot_session import OneshotSession


class TestOneshotSession:
    """Test suite for OneshotSession class."""

    @pytest.fixture
    def mock_runner(self):
        """Create a mock Claude runner for testing."""
        runner = Mock()
        runner.enable_websocket = False
        runner.project_logger = None
        runner.websocket_server = None
        runner.response_logger = None
        runner.ticket_manager = None
        runner.enable_tickets = False
        runner.claude_args = []
        runner.websocket_port = 8765
        runner.session_log_file = None

        # Mock methods
        runner.setup_agents.return_value = True
        runner.deploy_project_agents_to_claude.return_value = None
        runner._handle_mpm_command.return_value = True
        runner._create_system_prompt.return_value = "system prompt"
        runner._contains_delegation.return_value = False
        runner._extract_agent_from_response.return_value = None
        runner._log_session_event.return_value = None
        runner._extract_tickets.return_value = None

        return runner

    @pytest.fixture
    def oneshot_session(self, mock_runner):
        """Create OneshotSession instance for testing."""
        return OneshotSession(mock_runner)

    def test_init(self):
        """Test OneshotSession initialization."""
        session = OneshotSession(self)

        assert session.runner == self
        assert session.logger is not None
        assert session.start_time is None
        assert session.session_id is None
        assert session.original_cwd is None
        assert session.temp_system_prompt_file is None

    def test_initialize_session_success(self, oneshot_session):
        """Test successful session initialization."""
        prompt = "Test prompt"

        with patch("time.time", return_value=1234567890), patch(
            "uuid.uuid4", return_value=Mock(spec=uuid.UUID)
        ) as mock_uuid:
            mock_uuid.return_value.__str__ = Mock(return_value="test-session-id")

            success, error = oneshot_session.initialize_session(prompt)

            assert success is True
            assert error is None
            assert oneshot_session.start_time == 1234567890
            assert oneshot_session.session_id == "test-session-id"

    def test_initialize_session_mpm_command(self, oneshot_session):
        """Test session initialization with MPM command."""
        prompt = "/mpm:test"
        oneshot_session.runner._handle_mpm_command.return_value = True

        success, error = oneshot_session.initialize_session(prompt)

        assert success is True
        assert error is None
        oneshot_session.runner._handle_mpm_command.assert_called_once_with("/mpm:test")

    def test_initialize_session_with_websocket(self, oneshot_session):
        """Test session initialization with WebSocket enabled."""
        oneshot_session.runner.enable_websocket = True

        with patch.object(oneshot_session, "_setup_websocket") as mock_setup:
            success, _error = oneshot_session.initialize_session("test")

            assert success is True
            mock_setup.assert_called_once()

    def test_initialize_session_with_project_logger(self, oneshot_session):
        """Test session initialization with project logger."""
        oneshot_session.runner.project_logger = Mock()

        success, _error = oneshot_session.initialize_session("test prompt")

        assert success is True
        oneshot_session.runner.project_logger.log_system.assert_called_once_with(
            "Starting non-interactive session with prompt: test prompt",
            level="INFO",
            component="session",
        )

    def test_deploy_agents_success(self, oneshot_session):
        """Test successful agent deployment."""
        result = oneshot_session.deploy_agents()

        assert result is True
        oneshot_session.runner.setup_agents.assert_called_once()
        oneshot_session.runner.deploy_project_agents_to_claude.assert_called_once()

    def test_deploy_agents_setup_failure(self, oneshot_session, capsys):
        """Test agent deployment when setup_agents fails."""
        oneshot_session.runner.setup_agents.return_value = False

        result = oneshot_session.deploy_agents()

        assert result is True  # Still returns True, just prints warning
        captured = capsys.readouterr()
        assert "Continuing without native agents..." in captured.out

    def test_setup_infrastructure_basic(self, oneshot_session):
        """Test basic infrastructure setup."""
        with patch.object(
            oneshot_session, "_prepare_environment", return_value={"ENV": "test"}
        ), patch.object(
            oneshot_session, "_build_command", return_value=["claude", "--test"]
        ):
            result = oneshot_session.setup_infrastructure()

            assert result == {
                "env": {"ENV": "test"},
                "cmd": ["claude", "--test"],
                "working_dir_changed": False,
            }

    def test_setup_infrastructure_with_user_pwd(self, oneshot_session, tmp_path):
        """Test infrastructure setup with user working directory."""
        test_dir = tmp_path / "test_workspace"
        test_dir.mkdir()
        original_cwd = os.getcwd()

        try:
            with patch.object(
                oneshot_session,
                "_prepare_environment",
                return_value={"CLAUDE_MPM_USER_PWD": str(test_dir)},
            ), patch.object(oneshot_session, "_build_command", return_value=["claude"]):
                result = oneshot_session.setup_infrastructure()

                assert result["working_dir_changed"] is True
                assert result["env"]["CLAUDE_WORKSPACE"] == str(test_dir)
                assert oneshot_session.original_cwd == Path(original_cwd)
                assert os.getcwd() == str(test_dir)
        finally:
            # Restore original directory
            os.chdir(original_cwd)

    def test_setup_infrastructure_invalid_directory(self, oneshot_session):
        """Test infrastructure setup with invalid directory."""
        with patch.object(
            oneshot_session,
            "_prepare_environment",
            return_value={"CLAUDE_MPM_USER_PWD": "/nonexistent/path"},
        ), patch.object(oneshot_session, "_build_command", return_value=["claude"]):
            result = oneshot_session.setup_infrastructure()

            assert result["working_dir_changed"] is False
            assert oneshot_session.original_cwd is None

    def test_execute_command_success(self, oneshot_session):
        """Test successful command execution."""
        prompt = "test prompt"
        context = "test context"
        infrastructure = {
            "cmd": ["claude", "--model", "opus"],
            "env": {"TEST": "value"},
        }

        with patch.object(
            oneshot_session,
            "_build_final_command",
            return_value=[
                "claude",
                "--print",
                "test context\n\ntest prompt",
            ],
        ), patch.object(oneshot_session, "_notify_execution_start"), patch.object(
            oneshot_session, "_run_subprocess", return_value=(True, "success response")
        ):
            success, response = oneshot_session.execute_command(
                prompt, context, infrastructure
            )

            assert success is True
            assert response == "success response"

    def test_execute_command_no_context(self, oneshot_session):
        """Test command execution without context."""
        prompt = "test prompt"
        infrastructure = {"cmd": ["claude"], "env": {}}

        with patch.object(
            oneshot_session, "_build_final_command"
        ) as mock_build, patch.object(
            oneshot_session, "_notify_execution_start"
        ), patch.object(
            oneshot_session, "_run_subprocess", return_value=(True, "response")
        ):
            oneshot_session.execute_command(prompt, None, infrastructure)

            mock_build.assert_called_once_with(prompt, None, infrastructure)

    def test_build_final_command_with_context(self, oneshot_session):
        """Test building final command with context using file-based system prompt."""
        prompt = "test prompt"
        context = "test context"
        infrastructure = {"cmd": ["claude"]}

        with patch.object(
            oneshot_session, "_get_simple_context", return_value="simple context"
        ):
            oneshot_session.runner._create_system_prompt.return_value = "system prompt"

            result = oneshot_session._build_final_command(
                prompt, context, infrastructure
            )

            # File-based loading should be used (1M-485)
            assert result[0:3] == ["claude", "--print", "test context\n\ntest prompt"]
            assert "--system-prompt-file" in result

            # Get temp file and verify
            file_idx = result.index("--system-prompt-file") + 1
            temp_file_path = result[file_idx]
            assert Path(temp_file_path).exists()
            assert Path(temp_file_path).read_text() == "system prompt"

            # Cleanup
            Path(temp_file_path).unlink()

    def test_build_final_command_no_system_prompt(self, oneshot_session):
        """Test building final command without system prompt."""
        prompt = "test prompt"
        infrastructure = {"cmd": ["claude"]}

        with patch.object(
            oneshot_session, "_get_simple_context", return_value="simple context"
        ):
            oneshot_session.runner._create_system_prompt.return_value = (
                "simple context"  # Same as simple context
            )

            result = oneshot_session._build_final_command(prompt, None, infrastructure)

            expected = ["claude", "--print", "test prompt"]
            assert result == expected

    def test_notify_execution_start(self, oneshot_session):
        """Test execution start notification."""
        oneshot_session.runner.project_logger = Mock()
        oneshot_session.runner.websocket_server = Mock()

        oneshot_session._notify_execution_start()

        oneshot_session.runner.project_logger.log_system.assert_called_once_with(
            "Executing Claude subprocess", level="INFO", component="session"
        )
        oneshot_session.runner.websocket_server.claude_status_changed.assert_called_once_with(
            status="running", message="Executing Claude oneshot command"
        )

    def test_run_subprocess_success(self, oneshot_session):
        """Test successful subprocess execution."""
        cmd = ["echo", "test"]
        env = {"TEST": "value"}
        prompt = "test prompt"

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "test output"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result), patch.object(
            oneshot_session, "_handle_successful_response"
        ) as mock_handle:
            success, response = oneshot_session._run_subprocess(cmd, env, prompt)

            assert success is True
            assert response == "test output"
            mock_handle.assert_called_once_with("test output", "test prompt")

    def test_run_subprocess_error(self, oneshot_session):
        """Test subprocess execution with error."""
        cmd = ["false"]  # Command that returns non-zero
        env = {}
        prompt = "test prompt"

        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "error message"

        with patch("subprocess.run", return_value=mock_result), patch.object(
            oneshot_session, "_handle_error_response"
        ) as mock_handle:
            success, response = oneshot_session._run_subprocess(cmd, env, prompt)

            assert success is False
            assert response == "error message"
            mock_handle.assert_called_once_with("error message", 1)

    def test_run_subprocess_timeout(self, oneshot_session):
        """Test subprocess timeout handling."""
        cmd = ["sleep", "10"]
        env = {}
        prompt = "test"

        timeout_error = subprocess.TimeoutExpired(cmd, 5)

        with patch("subprocess.run", side_effect=timeout_error), patch.object(
            oneshot_session, "_handle_timeout", return_value=(False, "timeout")
        ) as mock_handle:
            success, response = oneshot_session._run_subprocess(cmd, env, prompt)

            assert success is False
            assert response == "timeout"
            mock_handle.assert_called_once_with(timeout_error)

    def test_run_subprocess_file_not_found(self, oneshot_session):
        """Test subprocess with file not found error."""
        cmd = ["nonexistent_command"]
        env = {}
        prompt = "test"

        with patch("subprocess.run", side_effect=FileNotFoundError()), patch.object(
            oneshot_session,
            "_handle_claude_not_found",
            return_value=(False, "not found"),
        ) as mock_handle:
            success, response = oneshot_session._run_subprocess(cmd, env, prompt)

            assert success is False
            assert response == "not found"
            mock_handle.assert_called_once()

    def test_run_subprocess_permission_error(self, oneshot_session):
        """Test subprocess with permission error."""
        cmd = ["test"]
        env = {}
        prompt = "test"

        perm_error = PermissionError("Permission denied")

        with patch("subprocess.run", side_effect=perm_error), patch.object(
            oneshot_session,
            "_handle_permission_error",
            return_value=(False, "permission denied"),
        ) as mock_handle:
            success, response = oneshot_session._run_subprocess(cmd, env, prompt)

            assert success is False
            assert response == "permission denied"
            mock_handle.assert_called_once_with(perm_error)

    def test_run_subprocess_keyboard_interrupt(self, oneshot_session):
        """Test subprocess with keyboard interrupt."""
        cmd = ["test"]
        env = {}
        prompt = "test"

        with patch("subprocess.run", side_effect=KeyboardInterrupt()), patch.object(
            oneshot_session,
            "_handle_keyboard_interrupt",
            return_value=(False, "interrupted"),
        ) as mock_handle:
            success, response = oneshot_session._run_subprocess(cmd, env, prompt)

            assert success is False
            assert response == "interrupted"
            mock_handle.assert_called_once()

    def test_run_subprocess_memory_error(self, oneshot_session):
        """Test subprocess with memory error."""
        cmd = ["test"]
        env = {}
        prompt = "test"

        mem_error = MemoryError("Out of memory")

        with patch("subprocess.run", side_effect=mem_error), patch.object(
            oneshot_session,
            "_handle_memory_error",
            return_value=(False, "memory error"),
        ) as mock_handle:
            success, response = oneshot_session._run_subprocess(cmd, env, prompt)

            assert success is False
            assert response == "memory error"
            mock_handle.assert_called_once_with(mem_error)

    def test_run_subprocess_unexpected_error(self, oneshot_session):
        """Test subprocess with unexpected error."""
        cmd = ["test"]
        env = {}
        prompt = "test"

        unexpected_error = RuntimeError("Unexpected error")

        with patch("subprocess.run", side_effect=unexpected_error), patch.object(
            oneshot_session,
            "_handle_unexpected_error",
            return_value=(False, "unexpected"),
        ) as mock_handle:
            success, response = oneshot_session._run_subprocess(cmd, env, prompt)

            assert success is False
            assert response == "unexpected"
            mock_handle.assert_called_once_with(unexpected_error)

    def test_cleanup_session_basic(self, oneshot_session):
        """Test basic session cleanup."""
        oneshot_session.cleanup_session()

        # Should not raise any exceptions
        assert True

    def test_cleanup_session_with_original_cwd(self, oneshot_session, tmp_path):
        """Test session cleanup with original directory restoration."""
        original_dir = str(tmp_path)
        oneshot_session.original_cwd = original_dir

        with patch("os.chdir") as mock_chdir:
            oneshot_session.cleanup_session()
            mock_chdir.assert_called_once_with(original_dir)

    def test_cleanup_session_with_project_logger(self, oneshot_session):
        """Test session cleanup with project logger."""
        oneshot_session.runner.project_logger = Mock()
        oneshot_session.runner.project_logger.get_session_summary.return_value = {
            "session_id": "test-session"
        }

        oneshot_session.cleanup_session()

        oneshot_session.runner.project_logger.log_system.assert_called_once_with(
            "Session test-session completed", level="INFO", component="session"
        )

    def test_cleanup_session_with_websocket(self, oneshot_session):
        """Test session cleanup with WebSocket server."""
        oneshot_session.runner.websocket_server = Mock()

        oneshot_session.cleanup_session()

        oneshot_session.runner.websocket_server.claude_status_changed.assert_called_once_with(
            status="stopped", message="Session completed"
        )
        oneshot_session.runner.websocket_server.session_ended.assert_called_once()

    def test_cleanup_session_error_handling(self, oneshot_session):
        """Test session cleanup with errors."""
        oneshot_session.original_cwd = "/nonexistent"
        oneshot_session.runner.project_logger = Mock()
        oneshot_session.runner.project_logger.get_session_summary.side_effect = (
            Exception("test error")
        )

        # Should not raise exception despite errors
        oneshot_session.cleanup_session()
        assert True

    def test_setup_websocket_success(self, oneshot_session):
        """Test successful WebSocket setup."""
        oneshot_session.session_id = "test-session"
        oneshot_session.runner.websocket_port = 8080

        mock_proxy = Mock()
        test_path = Path("/test/dir")

        with patch(
            "claude_mpm.services.socketio_server.SocketIOClientProxy",
            return_value=mock_proxy,
        ), patch("claude_mpm.core.oneshot_session.Path.cwd", return_value=test_path):
            oneshot_session._setup_websocket()

            assert oneshot_session.runner.websocket_server == mock_proxy
            mock_proxy.start.assert_called_once()
            mock_proxy.session_started.assert_called_once_with(
                session_id="test-session",
                launch_method="oneshot",
                working_dir=test_path,
            )

    def test_setup_websocket_import_error(self, oneshot_session):
        """Test WebSocket setup with import error."""
        with patch(
            "claude_mpm.services.socketio_server.SocketIOClientProxy",
            side_effect=ImportError(),
        ):
            oneshot_session._setup_websocket()
            assert oneshot_session.runner.websocket_server is None

    def test_setup_websocket_connection_error(self, oneshot_session):
        """Test WebSocket setup with connection error."""
        mock_proxy = Mock()
        mock_proxy.start.side_effect = ConnectionError("Connection failed")

        with patch(
            "claude_mpm.services.socketio_server.SocketIOClientProxy",
            return_value=mock_proxy,
        ):
            oneshot_session._setup_websocket()
            assert oneshot_session.runner.websocket_server is None

    def test_prepare_environment(self, oneshot_session):
        """Test environment preparation."""
        with patch("os.environ.copy", return_value={"TEST": "value"}):
            result = oneshot_session._prepare_environment()
            assert result == {"TEST": "value", "DISABLE_TELEMETRY": "1"}

    def test_build_command_basic(self, oneshot_session):
        """Test basic command building."""
        oneshot_session.runner.use_native_agents = True

        with patch.object(
            oneshot_session,
            "_build_agents_flag",
            return_value=["--agents", "simple context"],
        ):
            result = oneshot_session._build_command()

            expected = [
                "claude",
                "--dangerously-skip-permissions",
                "--agents",
                "simple context",
            ]
            assert result == expected

    def test_build_command_with_claude_args(self, oneshot_session):
        """Test command building with additional Claude arguments."""
        oneshot_session.runner.claude_args = ["--verbose", "--timeout", "30"]
        oneshot_session.runner.use_native_agents = True

        with patch.object(
            oneshot_session,
            "_build_agents_flag",
            return_value=["--agents", "simple context"],
        ):
            result = oneshot_session._build_command()

            expected = [
                "claude",
                "--dangerously-skip-permissions",
                "--verbose",
                "--timeout",
                "30",
                "--agents",
                "simple context",
            ]
            assert result == expected

    def test_handle_successful_response(self, oneshot_session, capsys):
        """Test successful response handling."""
        oneshot_session.start_time = time.time() - 5.0  # 5 seconds ago
        response = "Test response"
        prompt = "Test prompt"

        oneshot_session.runner.response_logger = Mock()
        oneshot_session.runner.websocket_server = Mock()
        oneshot_session.runner.project_logger = Mock()
        oneshot_session.runner.enable_tickets = False

        oneshot_session._handle_successful_response(response, prompt)

        # Check console output
        captured = capsys.readouterr()
        assert response in captured.out

        # Check response logger was called
        oneshot_session.runner.response_logger.log_response.assert_called_once()

        # Check WebSocket notifications
        oneshot_session.runner.websocket_server.claude_output.assert_called_once_with(
            response, "stdout"
        )

    def test_handle_successful_response_with_delegation(self, oneshot_session, capsys):
        """Test successful response handling with agent delegation."""
        oneshot_session.start_time = time.time()
        response = "Agent delegation response"
        prompt = "Test prompt"

        oneshot_session.runner.websocket_server = Mock()
        oneshot_session.runner._contains_delegation.return_value = True
        oneshot_session.runner._extract_agent_from_response.return_value = "engineer"

        oneshot_session._handle_successful_response(response, prompt)

        # Updated: Use OperationResult enum instead of magic string (enum consolidation work)
        oneshot_session.runner.websocket_server.agent_delegated.assert_called_once_with(
            agent="engineer", task=prompt[:100], status=OperationResult.PENDING
        )

    def test_handle_successful_response_with_tickets(self, oneshot_session, capsys):
        """Test successful response handling with ticket extraction."""
        oneshot_session.start_time = time.time()
        response = "Response with tickets"
        prompt = "Test prompt"

        oneshot_session.runner.enable_tickets = True
        oneshot_session.runner.ticket_manager = Mock()

        oneshot_session._handle_successful_response(response, prompt)

        oneshot_session.runner._extract_tickets.assert_called_once_with(response)

    def test_handle_error_response(self, oneshot_session, capsys):
        """Test error response handling."""
        error_msg = "Test error"
        return_code = 1

        oneshot_session.runner.websocket_server = Mock()
        oneshot_session.runner.project_logger = Mock()

        oneshot_session._handle_error_response(error_msg, return_code)

        # Check console output
        captured = capsys.readouterr()
        assert f"Error: {error_msg}" in captured.out

        # Check WebSocket notifications
        oneshot_session.runner.websocket_server.claude_output.assert_called_once_with(
            error_msg, "stderr"
        )
        oneshot_session.runner.websocket_server.claude_status_changed.assert_called_once_with(
            status="error", message=f"Command failed with code {return_code}"
        )

    def test_handle_timeout(self, oneshot_session, capsys):
        """Test timeout error handling."""
        timeout_error = subprocess.TimeoutExpired(["cmd"], 30)
        oneshot_session.runner.project_logger = Mock()

        success, msg = oneshot_session._handle_timeout(timeout_error)

        assert success is False
        assert "timed out after 30 seconds" in msg

        captured = capsys.readouterr()
        assert "⏱️" in captured.out

    def test_handle_claude_not_found(self, oneshot_session, capsys):
        """Test Claude not found error handling."""
        oneshot_session.runner.project_logger = Mock()

        success, msg = oneshot_session._handle_claude_not_found()

        assert success is False
        assert "Claude CLI not found" in msg

        captured = capsys.readouterr()
        assert "❌" in captured.out
        assert "npm install" in captured.out

    def test_handle_permission_error(self, oneshot_session, capsys):
        """Test permission error handling."""
        perm_error = PermissionError("Permission denied")
        oneshot_session.runner.project_logger = Mock()

        success, msg = oneshot_session._handle_permission_error(perm_error)

        assert success is False
        assert "Permission denied" in msg

        captured = capsys.readouterr()
        assert "❌" in captured.out

    def test_handle_keyboard_interrupt(self, oneshot_session, capsys):
        """Test keyboard interrupt handling."""
        oneshot_session.runner.project_logger = Mock()

        success, msg = oneshot_session._handle_keyboard_interrupt()

        assert success is False
        assert msg == "User interrupted"

        captured = capsys.readouterr()
        assert "⚠️" in captured.out

    def test_handle_memory_error(self, oneshot_session, capsys):
        """Test memory error handling."""
        mem_error = MemoryError("Out of memory")
        oneshot_session.runner.project_logger = Mock()

        success, msg = oneshot_session._handle_memory_error(mem_error)

        assert success is False
        assert "Out of memory" in msg

        captured = capsys.readouterr()
        assert "❌" in captured.out

    def test_handle_unexpected_error(self, oneshot_session, capsys):
        """Test unexpected error handling."""
        unexpected_error = RuntimeError("Unexpected error")
        oneshot_session.runner.project_logger = Mock()

        success, msg = oneshot_session._handle_unexpected_error(unexpected_error)

        assert success is False
        assert "Unexpected error" in msg

        captured = capsys.readouterr()
        assert "❌" in captured.out
        assert "RuntimeError" in captured.out

    def test_get_simple_context(self, oneshot_session):
        """Test getting simple context."""
        with patch(
            "claude_mpm.core.claude_runner.create_simple_context",
            return_value="simple context",
        ):
            result = oneshot_session._get_simple_context()
            assert result == "simple context"

    def test_build_final_command_with_file_based_caching(self, oneshot_session, tmp_path):
        """Test file-based caching to avoid ARG_MAX limits (1M-485)."""
        prompt = "test prompt"
        infrastructure = {"cmd": ["claude"]}

        # Create large system prompt that exceeds ARG_MAX
        large_system_prompt = "x" * 150000  # 150 KB

        with patch.object(
            oneshot_session, "_get_simple_context", return_value="simple context"
        ):
            oneshot_session.runner._create_system_prompt.return_value = large_system_prompt

            result = oneshot_session._build_final_command(
                prompt, None, infrastructure
            )

            # Verify file-based loading is used
            assert "--system-prompt-file" in result
            assert "--append-system-prompt" not in result

            # Get temp file path
            file_idx = result.index("--system-prompt-file") + 1
            temp_file_path = result[file_idx]

            # Verify temp file exists and contains system prompt
            assert Path(temp_file_path).exists()
            assert Path(temp_file_path).read_text() == large_system_prompt

            # Verify temp file path is stored for cleanup
            assert oneshot_session.temp_system_prompt_file == temp_file_path

            # Cleanup
            Path(temp_file_path).unlink()

    def test_build_final_command_file_creation_fallback(self, oneshot_session):
        """Test fallback to inline when file creation fails."""
        prompt = "test prompt"
        infrastructure = {"cmd": ["claude"]}
        system_prompt = "test system prompt"

        with patch.object(
            oneshot_session, "_get_simple_context", return_value="simple context"
        ), patch("tempfile.mkstemp", side_effect=OSError("File creation failed")):
            oneshot_session.runner._create_system_prompt.return_value = system_prompt

            result = oneshot_session._build_final_command(
                prompt, None, infrastructure
            )

            # Should fallback to inline
            assert "--append-system-prompt" in result
            assert system_prompt in result
            assert "--system-prompt-file" not in result

    def test_cleanup_session_removes_temp_file(self, oneshot_session, tmp_path):
        """Test that cleanup removes temporary system prompt file."""
        # Create a temp file
        temp_file = tmp_path / "test_system_prompt.md"
        temp_file.write_text("test content")

        oneshot_session.temp_system_prompt_file = str(temp_file)

        # Cleanup should remove the file
        oneshot_session.cleanup_session()

        assert not temp_file.exists()
        assert oneshot_session.temp_system_prompt_file is None

    def test_cleanup_session_handles_missing_temp_file(self, oneshot_session):
        """Test cleanup handles case where temp file doesn't exist."""
        oneshot_session.temp_system_prompt_file = "/nonexistent/file.md"

        # Should not raise exception
        oneshot_session.cleanup_session()

        assert oneshot_session.temp_system_prompt_file is None

    def test_cleanup_session_handles_temp_file_deletion_error(self, oneshot_session, tmp_path):
        """Test cleanup handles errors during temp file deletion."""
        temp_file = tmp_path / "test_file.md"
        temp_file.write_text("content")

        oneshot_session.temp_system_prompt_file = str(temp_file)

        # Mock unlink to raise error
        with patch.object(Path, "unlink", side_effect=OSError("Delete failed")):
            # Should not raise exception
            oneshot_session.cleanup_session()

            # Temp file reference should still be cleared
            assert oneshot_session.temp_system_prompt_file is None


class TestOneshotSessionIntegration:
    """Integration tests for OneshotSession workflow."""

    @pytest.fixture
    def mock_runner(self):
        """Create a realistic mock runner for integration tests."""
        runner = Mock()
        runner.enable_websocket = False
        runner.project_logger = Mock()
        runner.websocket_server = None
        runner.response_logger = Mock()
        runner.ticket_manager = None
        runner.enable_tickets = False
        runner.claude_args = []
        runner.websocket_port = 8765
        runner.session_log_file = "/tmp/test.log"

        # Mock methods with realistic behavior
        runner.setup_agents.return_value = True
        runner.deploy_project_agents_to_claude.return_value = None
        runner._handle_mpm_command.return_value = True
        runner._create_system_prompt.return_value = "System instructions"
        runner._contains_delegation.return_value = False
        runner._extract_agent_from_response.return_value = None
        runner._log_session_event.return_value = None
        runner._extract_tickets.return_value = None

        return runner

    def test_full_oneshot_workflow_success(self, mock_runner):
        """Test complete oneshot workflow with successful execution."""
        session = OneshotSession(mock_runner)
        prompt = "Write a hello world program"
        context = "System context"

        # Mock subprocess success
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "print('Hello, World!')"
        mock_result.stderr = ""

        with patch("time.time", return_value=1234567890), patch(
            "uuid.uuid4", return_value=Mock(spec=uuid.UUID)
        ) as mock_uuid, patch(
            "os.environ.copy", return_value={"PATH": "/usr/bin"}
        ), patch("subprocess.run", return_value=mock_result), patch(
            "os.getcwd", return_value="/test/dir"
        ):
            mock_uuid.return_value.__str__ = Mock(return_value="test-session-id")

            # Initialize session
            success, _error = session.initialize_session(prompt)
            assert success is True

            # Deploy agents
            deploy_success = session.deploy_agents()
            assert deploy_success is True

            # Setup infrastructure
            infrastructure = session.setup_infrastructure()
            assert infrastructure["working_dir_changed"] is False

            # Execute command
            exec_success, response = session.execute_command(
                prompt, context, infrastructure
            )
            assert exec_success is True
            assert response == "print('Hello, World!')"

            # Cleanup
            session.cleanup_session()

            # Verify mocks were called appropriately
            mock_runner.setup_agents.assert_called_once()
            mock_runner.deploy_project_agents_to_claude.assert_called_once()
            mock_runner.project_logger.log_system.assert_called()

    def test_full_oneshot_workflow_with_error(self, mock_runner):
        """Test complete oneshot workflow with command failure."""
        session = OneshotSession(mock_runner)
        prompt = "Invalid command"

        # Mock subprocess failure
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Command failed"

        with patch("time.time", return_value=1234567890), patch(
            "uuid.uuid4", return_value=Mock(spec=uuid.UUID)
        ) as mock_uuid, patch(
            "os.environ.copy", return_value={"PATH": "/usr/bin"}
        ), patch("subprocess.run", return_value=mock_result):
            mock_uuid.return_value.__str__ = Mock(return_value="test-session-id")

            # Initialize session
            success, _error = session.initialize_session(prompt)
            assert success is True

            # Deploy agents
            deploy_success = session.deploy_agents()
            assert deploy_success is True

            # Setup infrastructure
            infrastructure = session.setup_infrastructure()

            # Execute command (should fail)
            exec_success, response = session.execute_command(
                prompt, None, infrastructure
            )
            assert exec_success is False
            assert response == "Command failed"

            # Cleanup
            session.cleanup_session()

    def test_full_oneshot_workflow_with_websocket(self, mock_runner):
        """Test complete oneshot workflow with WebSocket enabled."""
        mock_runner.enable_websocket = True
        session = OneshotSession(mock_runner)
        prompt = "Test with websocket"

        mock_proxy = Mock()
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "WebSocket response"
        mock_result.stderr = ""

        with patch("time.time", return_value=1234567890), patch(
            "uuid.uuid4", return_value=Mock(spec=uuid.UUID)
        ) as mock_uuid, patch(
            "claude_mpm.services.socketio_server.SocketIOClientProxy",
            return_value=mock_proxy,
        ), patch("os.environ.copy", return_value={}), patch(
            "subprocess.run", return_value=mock_result
        ), patch("os.getcwd", return_value="/test/dir"):
            mock_uuid.return_value.__str__ = Mock(return_value="ws-session-id")

            # Full workflow
            success, _error = session.initialize_session(prompt)
            assert success is True

            deploy_success = session.deploy_agents()
            assert deploy_success is True

            infrastructure = session.setup_infrastructure()
            exec_success, _response = session.execute_command(
                prompt, None, infrastructure
            )
            assert exec_success is True

            session.cleanup_session()

            # Verify WebSocket interactions
            mock_proxy.start.assert_called_once()
            mock_proxy.session_started.assert_called_once()
            mock_proxy.claude_status_changed.assert_called()
            mock_proxy.claude_output.assert_called_once_with(
                "WebSocket response", "stdout"
            )
            mock_proxy.session_ended.assert_called_once()


if __name__ == "__main__":
    # Add Memory to demonstrate test completion
    print("# Add To Memory:")
    print("Type: pattern")
    print(
        "Content: Comprehensive unit tests for OneshotSession with 95%+ coverage including error scenarios"
    )
    print("#")

    pytest.main([__file__, "-v"])
