"""
Comprehensive tests for run.py refactoring safety net.

WHY: The run command is critical user-facing functionality. These tests provide
comprehensive coverage to ensure safe refactoring of the 1369-line file into
smaller, focused services.

DESIGN DECISIONS:
- Test all major code paths and edge cases
- Mock external dependencies for isolation
- Test configuration validation and error handling
- Verify session management behaviors
- Test monitoring and Socket.IO integration
- Cover dependency checking logic
"""

from argparse import Namespace
from unittest.mock import Mock, patch

import pytest

from claude_mpm.cli.commands.run import (RunCommand, create_session_context,
                                         filter_claude_mpm_args, run_session,
                                         run_session_legacy)
from claude_mpm.cli.shared.base_command import CommandResult
from claude_mpm.constants import LogLevel


class TestFilterClaudeMPMArgs:
    """Test argument filtering functionality."""

    def test_filters_mpm_specific_flags(self):
        """Test that MPM-specific flags are filtered out."""
        args = [
            "--monitor",
            "--websocket-port",
            "8080",
            "--no-hooks",
            "--actual-claude-arg",
            "--no-tickets",
            "--intercept-commands",
        ]

        filtered = filter_claude_mpm_args(args)

        assert filtered == ["--actual-claude-arg"]

    def test_handles_short_flags(self):
        """Test filtering of short MPM flags."""
        args = ["-i", "input.txt", "-d", "--claude-arg"]
        filtered = filter_claude_mpm_args(args)
        assert filtered == ["--claude-arg"]

    def test_removes_separator(self):
        """Test that -- separator is removed."""
        args = ["--", "--claude-arg", "value"]
        filtered = filter_claude_mpm_args(args)
        assert filtered == ["--claude-arg", "value"]

    def test_handles_optional_value_flags(self):
        """Test flags with optional values like --mpm-resume."""
        # With value
        args = ["--mpm-resume", "session-id", "--claude-arg"]
        filtered = filter_claude_mpm_args(args)
        assert filtered == ["--claude-arg"]

        # Without value
        args = ["--mpm-resume", "--claude-arg"]
        filtered = filter_claude_mpm_args(args)
        assert filtered == ["--claude-arg"]

    def test_empty_and_none_inputs(self):
        """Test edge cases with empty or None inputs."""
        assert filter_claude_mpm_args([]) == []
        assert filter_claude_mpm_args(None) == []

    def test_preserves_claude_cli_args(self):
        """Test that actual Claude CLI args are preserved."""
        args = ["--model", "claude-3", "--temperature", "0.7", "--max-tokens", "1000"]
        filtered = filter_claude_mpm_args(args)
        assert filtered == args


class TestCreateSessionContext:
    """Test session context creation functionality."""

    @patch("claude_mpm.core.claude_runner.create_simple_context")
    def test_creates_base_context_when_no_session(self, mock_create_context):
        """Test base context creation when session not found."""
        mock_create_context.return_value = "base context"
        mock_manager = Mock()
        mock_manager.get_session_by_id.return_value = None

        result = create_session_context("session-123", mock_manager)

        assert result == "base context"
        mock_manager.get_session_by_id.assert_called_once_with("session-123")

    @patch("claude_mpm.core.claude_runner.create_simple_context")
    def test_enhances_context_with_session_info(self, mock_create_context):
        """Test context enhancement with session information."""
        mock_create_context.return_value = "base context"
        mock_manager = Mock()
        mock_manager.get_session_by_id.return_value = {
            "created_at": "2024-01-01T10:00:00",
            "last_used": "2024-01-01T11:00:00",
            "context": "test-context",
            "use_count": 5,
            "agents_run": [
                {"agent": "agent1", "task": "Task 1"},
                {"agent": "agent2", "task": "Task 2"},
            ],
        }

        result = create_session_context("session-123", mock_manager)

        assert "base context" in result
        assert "Session Resumption" in result
        assert "session-12" in result  # First 8 chars
        assert "Created: 2024-01-01T10:00:00" in result
        assert "Use count: 5" in result
        assert "agent1: Task 1" in result
        assert "agent2: Task 2" in result


class TestRunCommand:
    """Test RunCommand class functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.command = RunCommand()

    def test_initialization(self):
        """Test command initialization."""
        assert self.command.command_name == "run"
        assert self.command.logger is not None

    def test_validate_args_accepts_valid_args(self):
        """Test that validation accepts valid arguments."""
        args = Namespace(
            logging=LogLevel.INFO.value,
            monitor=False,
            no_tickets=False,
            non_interactive=False,
            input=None,
        )

        error = self.command.validate_args(args)
        assert error is None

    @patch("claude_mpm.cli.commands.run.run_session_legacy")
    def test_run_delegates_to_legacy(self, mock_legacy):
        """Test that run delegates to legacy implementation."""
        args = Namespace(logging=LogLevel.INFO.value)

        result = self.command.run(args)

        mock_legacy.assert_called_once_with(args)
        assert isinstance(result, CommandResult)
        assert result.success is True

    @patch("claude_mpm.cli.commands.run.run_session_legacy")
    def test_run_handles_keyboard_interrupt(self, mock_legacy):
        """Test handling of keyboard interrupt."""
        mock_legacy.side_effect = KeyboardInterrupt()
        args = Namespace(logging=LogLevel.INFO.value)

        result = self.command.run(args)

        assert result.success is False
        assert result.exit_code == 130
        assert "cancelled by user" in result.message

    @patch("claude_mpm.cli.commands.run.run_session_legacy")
    def test_run_handles_exceptions(self, mock_legacy):
        """Test handling of general exceptions."""
        mock_legacy.side_effect = RuntimeError("Test error")
        args = Namespace(logging=LogLevel.INFO.value)

        result = self.command.run(args)

        assert result.success is False
        # The command logs the error but returns a generic message
        assert "Claude session" in result.message


class TestConfigurationChecking:
    """Test configuration health checking functionality."""

    @patch("claude_mpm.cli.commands.run.RunConfigChecker")
    def test_check_configuration_health(self, mock_checker_class):
        """Test configuration health checking."""
        command = RunCommand()
        mock_checker = Mock()
        mock_checker_class.return_value = mock_checker

        command._check_configuration_health()

        mock_checker_class.assert_called_once_with(command.logger)
        mock_checker.check_configuration_health.assert_called_once()

    @patch("claude_mpm.cli.commands.run.RunConfigChecker")
    def test_check_claude_json_memory(self, mock_checker_class):
        """Test .claude.json memory checking."""
        command = RunCommand()
        mock_checker = Mock()
        mock_checker_class.return_value = mock_checker
        args = Namespace(mpm_resume=True)

        command._check_claude_json_memory(args)

        mock_checker.check_claude_json_memory.assert_called_once_with(args)


class TestSessionManagement:
    """Test session management functionality."""

    @patch("claude_mpm.core.session_manager.SessionManager")
    def test_setup_session_no_resume(self, mock_manager_class):
        """Test session setup without resume."""
        command = RunCommand()
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager

        args = Namespace(mpm_resume=None)

        manager, session_id, context = command._setup_session_management(args)

        assert manager == mock_manager
        assert session_id is None
        assert context is None

    @patch("claude_mpm.core.session_manager.SessionManager")
    def test_setup_session_resume_last(self, mock_manager_class):
        """Test resuming last session."""
        command = RunCommand()
        mock_manager = Mock()
        mock_manager.get_last_interactive_session.return_value = "session-123"
        mock_manager.get_session_by_id.return_value = {
            "context": "test-context",
            "created_at": "2024-01-01",
        }
        mock_manager_class.return_value = mock_manager

        args = Namespace(mpm_resume="last")

        _manager, session_id, context = command._setup_session_management(args)

        assert session_id == "session-123"
        assert context == "test-context"
        mock_manager.get_last_interactive_session.assert_called_once()

    @patch("claude_mpm.core.session_manager.SessionManager")
    def test_setup_session_resume_specific(self, mock_manager_class):
        """Test resuming specific session by ID."""
        command = RunCommand()
        mock_manager = Mock()
        mock_manager.get_session_by_id.return_value = {"context": "specific-context"}
        mock_manager_class.return_value = mock_manager

        args = Namespace(mpm_resume="session-456")

        _manager, session_id, context = command._setup_session_management(args)

        assert session_id == "session-456"
        assert context == "specific-context"
        mock_manager.get_session_by_id.assert_called_with("session-456")

    @patch("claude_mpm.core.session_manager.SessionManager")
    def test_setup_session_not_found_raises(self, mock_manager_class):
        """Test that missing session raises error."""
        command = RunCommand()
        mock_manager = Mock()
        mock_manager.get_session_by_id.return_value = None
        mock_manager_class.return_value = mock_manager

        args = Namespace(mpm_resume="missing-session")

        with pytest.raises(RuntimeError, match="Session missing-session not found"):
            command._setup_session_management(args)


class TestDependencyChecking:
    """Test dependency checking functionality."""

    @patch("claude_mpm.utils.agent_dependency_loader.AgentDependencyLoader")
    @patch("claude_mpm.utils.dependency_cache.SmartDependencyChecker")
    @patch("claude_mpm.utils.environment_context.should_prompt_for_dependencies")
    def test_handle_dependencies_no_check_needed(
        self, mock_should_prompt, mock_checker_class, mock_loader_class
    ):
        """Test when no dependency check is needed."""
        command = RunCommand()
        mock_checker = Mock()
        mock_checker.should_check_dependencies.return_value = (False, "cached")
        mock_checker_class.return_value = mock_checker

        mock_loader = Mock()
        mock_loader.has_agents_changed.return_value = (False, "hash123")
        mock_loader_class.return_value = mock_loader

        args = Namespace(check_dependencies=True, force_check_dependencies=False)

        command._handle_dependency_checking(args)

        mock_checker.should_check_dependencies.assert_called_once()
        mock_checker.update_cache.assert_not_called()

    @patch("claude_mpm.utils.agent_dependency_loader.AgentDependencyLoader")
    @patch("claude_mpm.utils.dependency_cache.SmartDependencyChecker")
    @patch("claude_mpm.utils.environment_context.should_prompt_for_dependencies")
    @patch("builtins.input", return_value="y")
    def test_handle_dependencies_with_missing_and_prompt(
        self, mock_input, mock_should_prompt, mock_checker_class, mock_loader_class
    ):
        """Test handling missing dependencies with user prompt."""
        command = RunCommand()

        mock_checker = Mock()
        mock_checker.should_check_dependencies.return_value = (True, "agents changed")
        mock_checker_class.return_value = mock_checker

        mock_loader = Mock()
        mock_loader.has_agents_changed.return_value = (True, "hash456")
        mock_loader.check_dependencies.return_value = ["package1", "package2"]
        mock_loader_class.return_value = mock_loader

        mock_should_prompt.return_value = True

        args = Namespace(check_dependencies=True, force_check_dependencies=False)

        with patch("builtins.print"):
            command._handle_dependency_checking(args)

        mock_loader.check_dependencies.assert_called_once()
        mock_loader.install_dependencies.assert_called_once_with(
            ["package1", "package2"]
        )
        mock_checker.update_cache.assert_called_once_with("hash456")


class TestMonitoringSetup:
    """Test monitoring and Socket.IO setup."""

    @patch("claude_mpm.cli.commands.run.ensure_socketio_dependencies")
    @patch("claude_mpm.cli.commands.run.PortManager")
    @patch("claude_mpm.cli.commands.run.webbrowser")
    @patch("claude_mpm.cli.commands.run.time.sleep")
    def test_setup_monitoring_enabled(
        self, mock_sleep, mock_browser, mock_port_class, mock_ensure_deps
    ):
        """Test monitoring setup when enabled."""
        command = RunCommand()
        mock_ensure_deps.return_value = True

        mock_port_manager = Mock()
        mock_port_manager.get_available_port.return_value = 8080
        mock_port_class.return_value = mock_port_manager

        # Mock server as running
        command._is_socketio_server_running = Mock(return_value=True)

        args = Namespace(monitor=True, _browser_opened_by_cli=False)

        monitor_mode, port = command._setup_monitoring(args)

        assert monitor_mode is True
        assert port == 8080
        mock_browser.open.assert_called_once_with("http://localhost:8080")
        assert args._browser_opened_by_cli is True

    @patch("claude_mpm.cli.commands.run.ensure_socketio_dependencies")
    def test_setup_monitoring_disabled_no_deps(self, mock_ensure_deps):
        """Test monitoring disabled when dependencies missing."""
        command = RunCommand()
        mock_ensure_deps.return_value = False

        args = Namespace(monitor=True)

        monitor_mode, port = command._setup_monitoring(args)

        assert monitor_mode is False
        assert port == 8765  # Default port


class TestClaudeRunnerSetup:
    """Test Claude runner setup and configuration."""

    @patch("claude_mpm.core.claude_runner.ClaudeRunner")
    def test_setup_claude_runner_basic(self, mock_runner_class):
        """Test basic Claude runner setup."""
        command = RunCommand()
        mock_runner = Mock()
        mock_runner_class.return_value = mock_runner

        args = Namespace(
            no_tickets=False,
            subprocess=False,
            logging=LogLevel.INFO.value,
            claude_args=["--model", "claude-3"],
        )

        runner = command._setup_claude_runner(
            args, monitor_mode=False, websocket_port=8765
        )

        assert runner == mock_runner
        mock_runner_class.assert_called_once_with(
            enable_tickets=True,
            log_level=LogLevel.INFO.value,
            claude_args=["--model", "claude-3"],
            launch_method="exec",
            enable_websocket=False,
            websocket_port=8765,
        )

    @patch("claude_mpm.core.claude_runner.ClaudeRunner")
    def test_setup_claude_runner_with_monitor(self, mock_runner_class):
        """Test Claude runner setup with monitoring."""
        command = RunCommand()
        mock_runner = Mock()
        mock_runner_class.return_value = mock_runner

        args = Namespace(
            no_tickets=True,
            subprocess=True,
            logging=LogLevel.DEBUG.value,
            claude_args=[],
            _browser_opened_by_cli=True,
        )

        runner = command._setup_claude_runner(
            args, monitor_mode=True, websocket_port=9090
        )

        assert runner._should_open_monitor_browser is True
        assert runner._browser_opened_by_cli is True
        mock_runner_class.assert_called_once_with(
            enable_tickets=False,
            log_level=LogLevel.DEBUG.value,
            claude_args=[],
            launch_method="subprocess",
            enable_websocket=True,
            websocket_port=9090,
        )


class TestSessionExecution:
    """Test session execution logic."""

    @patch("claude_mpm.cli.commands.run.get_user_input")
    def test_execute_session_non_interactive(self, mock_get_input):
        """Test non-interactive session execution."""
        command = RunCommand()
        mock_get_input.return_value = "test input"

        mock_runner = Mock()
        mock_runner.run_oneshot.return_value = True

        args = Namespace(
            non_interactive=True, input="input.txt", intercept_commands=False
        )

        result = command._execute_session(args, mock_runner, "context")

        assert result is True
        mock_runner.run_oneshot.assert_called_once_with("test input", "context")

    def test_execute_session_interactive(self):
        """Test interactive session execution."""
        command = RunCommand()

        mock_runner = Mock()

        args = Namespace(non_interactive=False, input=None, intercept_commands=False)

        result = command._execute_session(args, mock_runner, "context")

        assert result is True
        mock_runner.run_interactive.assert_called_once_with("context")

    @patch("claude_mpm.cli.commands.run.subprocess.run")
    @patch("claude_mpm.cli.commands.run.get_scripts_dir")
    def test_execute_session_with_intercept(self, mock_get_scripts, mock_subprocess):
        """Test session with command interception."""
        command = RunCommand()

        mock_scripts_dir = Mock()
        wrapper_path = Mock()
        wrapper_path.exists.return_value = True
        mock_scripts_dir.__truediv__ = Mock(return_value=wrapper_path)
        mock_get_scripts.return_value = mock_scripts_dir

        args = Namespace(non_interactive=False, input=None, intercept_commands=True)

        mock_runner = Mock()

        result = command._execute_session(args, mock_runner, "context")

        assert result is True
        mock_subprocess.run.assert_called_once()
        mock_runner.run_interactive.assert_not_called()


class TestLegacyRunSession:
    """Test legacy run_session function."""

    @patch("claude_mpm.cli.startup_logging.setup_startup_logging")
    @patch("claude_mpm.cli.startup_logging.cleanup_old_startup_logs")
    @patch("claude_mpm.cli.startup_logging.log_startup_status")
    @patch("claude_mpm.cli.commands.run._check_configuration_health")
    @patch("claude_mpm.cli.commands.run._check_claude_json_memory")
    @patch("claude_mpm.core.session_manager.SessionManager")
    @patch("claude_mpm.services.command_deployment_service.deploy_commands_on_startup")
    @patch("claude_mpm.cli.utils.list_agent_versions_at_startup")
    @patch("claude_mpm.core.claude_runner.ClaudeRunner")
    def test_run_session_legacy_basic_flow(
        self,
        mock_runner_class,
        mock_list_agents,
        mock_deploy_commands,
        mock_session_class,
        mock_check_memory,
        mock_check_health,
        mock_log_status,
        mock_cleanup_logs,
        mock_setup_logging,
    ):
        """Test basic flow of legacy run_session."""
        mock_runner = Mock()
        mock_runner.run_interactive.return_value = True
        mock_runner_class.return_value = mock_runner

        mock_session_manager = Mock()
        mock_session_manager.create_session.return_value = "new-session"
        mock_session_class.return_value = mock_session_manager

        args = Namespace(
            logging=LogLevel.INFO.value,
            monitor=False,
            websocket_port=8765,
            mpm_resume=None,
            no_native_agents=False,
            check_dependencies=False,
            no_tickets=False,
            resume=False,
            claude_args=[],
            launch_method="exec",
            non_interactive=False,
            input=None,
            intercept_commands=False,
        )

        run_session_legacy(args)

        mock_setup_logging.assert_called_once()
        mock_cleanup_logs.assert_called_once()
        mock_check_health.assert_called_once()
        mock_check_memory.assert_called_once()
        mock_deploy_commands.assert_called_once()
        mock_list_agents.assert_called_once()
        mock_runner.run_interactive.assert_called_once()


class TestSocketIOServerManagement:
    """Test Socket.IO server management functions."""

    def test_is_socketio_server_running(self):
        """Test checking if Socket.IO server is running."""
        command = RunCommand()

        with patch("socket.socket") as mock_socket_class:
            mock_socket = Mock()
            mock_socket.__enter__ = Mock(return_value=mock_socket)
            mock_socket.__exit__ = Mock(return_value=None)
            mock_socket.connect_ex.return_value = 0  # Success
            mock_socket.settimeout = Mock()
            mock_socket_class.return_value = mock_socket

            result = command._is_socketio_server_running(8765)
            assert result is True

            mock_socket.connect_ex.return_value = 1  # Failed
            result = command._is_socketio_server_running(8765)
            assert result is False


class TestRunSessionEntryPoint:
    """Test the main entry point function."""

    @patch("claude_mpm.cli.commands.run.RunCommand")
    def test_run_session_entry_point(self, mock_command_class):
        """Test run_session entry point function."""
        mock_command = Mock()
        mock_result = Mock()
        mock_result.exit_code = 0
        mock_command.execute.return_value = mock_result
        mock_command_class.return_value = mock_command

        args = Namespace(test="args")

        exit_code = run_session(args)

        assert exit_code == 0
        mock_command.execute.assert_called_once_with(args)


class TestErrorHandling:
    """Test error handling and edge cases."""

    @patch("claude_mpm.core.claude_runner.ClaudeRunner")
    def test_session_failure_handling(self, mock_runner_class):
        """Test handling of session execution failures."""
        command = RunCommand()

        mock_runner = Mock()
        mock_runner.run_oneshot.return_value = False
        mock_runner_class.return_value = mock_runner

        args = Namespace(non_interactive=True, input="test", intercept_commands=False)

        with patch("claude_mpm.cli.commands.run.get_user_input", return_value="input"):
            result = command._execute_session(args, mock_runner, "context")

        assert result is False

    @patch("claude_mpm.cli.commands.run.AgentDependencyLoader")
    @patch("claude_mpm.cli.commands.run.SmartDependencyChecker")
    def test_dependency_check_import_error(self, mock_checker_class, mock_loader_class):
        """Test handling of import errors in dependency checking."""
        command = RunCommand()

        # Simulate ImportError
        mock_loader_class.side_effect = ImportError("Module not found")

        args = Namespace(check_dependencies=True)

        # Should not raise, just log warning
        command._handle_dependency_checking(args)

        # Verify it handled the error gracefully
        assert True  # If we get here, error was handled

    @patch("claude_mpm.cli.commands.run.SessionManager")
    def test_session_management_with_missing_module(self, mock_manager_class):
        """Test session management when SessionManager import fails."""
        command = RunCommand()

        # First import fails, fallback import succeeds
        with patch(
            "claude_mpm.cli.commands.run.SessionManager",
            side_effect=[ImportError, mock_manager_class],
        ):
            args = Namespace(mpm_resume=None)

            # Should still work with fallback import
            manager, _session_id, _context = command._setup_session_management(args)

            assert manager is not None


class TestIntegrationScenarios:
    """Test integrated scenarios combining multiple features."""

    @patch("claude_mpm.cli.commands.run.RunConfigChecker")
    @patch("claude_mpm.cli.commands.run.SessionManager")
    @patch("claude_mpm.cli.commands.run.ensure_socketio_dependencies")
    @patch("claude_mpm.cli.commands.run.PortManager")
    @patch("claude_mpm.core.claude_runner.ClaudeRunner")
    @patch("claude_mpm.core.claude_runner.create_simple_context")
    def test_full_monitoring_session_flow(
        self,
        mock_context,
        mock_runner_class,
        mock_port_class,
        mock_ensure_deps,
        mock_session_class,
        mock_checker_class,
    ):
        """Test complete flow with monitoring enabled."""
        command = RunCommand()

        # Setup mocks
        mock_checker = Mock()
        mock_checker_class.return_value = mock_checker

        mock_session = Mock()
        mock_session.create_session.return_value = "session-id"
        mock_session_class.return_value = mock_session

        mock_ensure_deps.return_value = True

        mock_port_manager = Mock()
        mock_port_manager.get_available_port.return_value = 8080
        mock_port_class.return_value = mock_port_manager

        mock_runner = Mock()
        mock_runner.run_interactive.return_value = True
        mock_runner_class.return_value = mock_runner

        mock_context.return_value = "test context"

        # Mock server running check
        command._is_socketio_server_running = Mock(return_value=True)

        args = Namespace(
            logging=LogLevel.INFO.value,
            monitor=True,
            mpm_resume=None,
            check_dependencies=False,
            no_tickets=False,
            subprocess=False,
            claude_args=[],
            non_interactive=False,
            input=None,
            intercept_commands=False,
        )

        # Execute new pattern flow
        with patch("claude_mpm.cli.commands.run.webbrowser"):
            result = command._execute_run_session_new(args)

        assert result is True
        mock_checker.check_configuration_health.assert_called_once()
        mock_session.create_session.assert_called_once()
        mock_runner.run_interactive.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
