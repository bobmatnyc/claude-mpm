"""
Comprehensive tests for the RunCommand class.

WHY: The run command is the most important user-facing command in claude-mpm.
It starts Claude sessions and needs thorough testing for all modes and options.

DESIGN DECISIONS:
- Test both interactive and non-interactive modes
- Mock external dependencies (subprocess, webbrowser)
- Test error handling and validation
- Verify backward compatibility
- Test all command-line options
"""

import subprocess
from argparse import Namespace
from pathlib import Path
from unittest.mock import Mock, patch

from claude_mpm.cli.commands.run import RunCommand, filter_claude_mpm_args
from claude_mpm.cli.shared.base_command import CommandResult


class TestRunCommand:
    """Test RunCommand functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.command = RunCommand()

    def test_initialization():
        """Test RunCommand initialization."""
        assert self.command.command_name == "run"
        assert self.command.logger is not None

    def test_validate_args_basic():
        """Test basic validation with minimal args."""
        args = Namespace(
            claude_args=[],
            monitor=False,
            websocket_port=None,
            no_hooks=False,
            no_tickets=False,
            intercept_commands=False,
            no_native_agents=False,
            launch_method="default",
            mpm_resume=False,
            input=None,
            non_interactive=False,
        )
        error = self.command.validate_args(args)
        assert error is None

    def test_validate_args_with_input_file():
        """Test validation with input file specified."""
        args = Namespace(
            claude_args=[], input="/path/to/input.txt", non_interactive=False
        )
        error = self.command.validate_args(args)
        # No specific validation for input file in validate_args
        assert error is None

    def test_validate_args_non_interactive_without_input():
        """Test validation for non-interactive mode without input."""
        args = Namespace(claude_args=[], input=None, non_interactive=True)
        # This should still be valid as claude_args might have input
        error = self.command.validate_args(args)
        assert error is None

    @patch("claude_mpm.cli.commands.run.subprocess.run")
    @patch("claude_mpm.cli.commands.run.Config")
    def test_run_basic_interactive(self, mock_subprocess):
        """Test running basic interactive Claude session."""
        mock_config = Mock()
        mock_config.ensure_paths.return_value = None
        mock_config.claude_desktop_config_dir = Path("/mock/claude/config")
        self.return_value = mock_config

        mock_subprocess.return_value = Mock(returncode=0)

        args = Namespace(
            claude_args=[],
            monitor=False,
            websocket_port=None,
            no_hooks=False,
            no_tickets=False,
            intercept_commands=False,
            no_native_agents=False,
            launch_method="default",
            mpm_resume=False,
            input=None,
            non_interactive=False,
            debug=False,
            logging="INFO",
            log_dir=None,
            framework_path=None,
            agents_dir=None,
        )

        result = self.command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is True
        mock_subprocess.assert_called_once()

    @patch("claude_mpm.cli.commands.run.subprocess.run")
    @patch("claude_mpm.cli.commands.run.Config")
    @patch("claude_mpm.cli.commands.run.Path.exists")
    def test_run_with_input_file(self, mock_config_class, mock_subprocess):
        """Test running with input file."""
        self.return_value = True
        mock_config = Mock()
        mock_config.ensure_paths.return_value = None
        mock_config.claude_desktop_config_dir = Path("/mock/claude/config")
        mock_config_class.return_value = mock_config

        mock_subprocess.return_value = Mock(returncode=0)

        args = Namespace(
            claude_args=[],
            input="/path/to/input.txt",
            non_interactive=True,
            monitor=False,
            websocket_port=None,
            no_hooks=False,
            no_tickets=False,
            intercept_commands=False,
            no_native_agents=False,
            launch_method="default",
            mpm_resume=False,
            debug=False,
            logging="INFO",
            log_dir=None,
            framework_path=None,
            agents_dir=None,
        )

        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = (
                "Test input"
            )
            result = self.command.run(args)

        assert isinstance(result, CommandResult)
        # The command should handle the input file

    @patch("claude_mpm.cli.commands.run.subprocess.run")
    @patch("claude_mpm.core.config.Config")
    @patch("claude_mpm.cli.commands.run.DashboardLauncher")
    @patch("claude_mpm.cli.commands.run.ensure_socketio_dependencies")
    @patch("claude_mpm.cli.commands.run.PortManager")
    def test_run_with_monitor(
        self,
        mock_port_manager,
        mock_ensure_deps,
        mock_dashboard_launcher_class,
        mock_config_class,
        mock_subprocess,
    ):
        """Test running with monitor enabled."""
        mock_config = Mock()
        mock_config.ensure_paths.return_value = None
        mock_config.claude_desktop_config_dir = Path("/mock/claude/config")
        mock_config.no_prompt = False
        mock_config.force_prompt = False
        mock_config.force_check_dependencies = False
        mock_config.no_check_dependencies = False
        mock_config_class.return_value = mock_config

        mock_port_manager.return_value.get_available_port.return_value = 8080
        mock_ensure_deps.return_value = True
        mock_subprocess.return_value = Mock(returncode=0)

        # Mock DashboardLauncher
        mock_dashboard_launcher = Mock()
        mock_dashboard_launcher.launch_dashboard.return_value = (True, True)
        mock_dashboard_launcher.get_dashboard_url.return_value = "http://localhost:8080"
        mock_dashboard_launcher_class.return_value = mock_dashboard_launcher

        args = Namespace(
            claude_args=[],
            monitor=True,
            websocket_port=None,
            no_hooks=False,
            no_tickets=False,
            intercept_commands=False,
            no_native_agents=False,
            launch_method="browser",
            mpm_resume=False,
            input=None,
            non_interactive=False,
            debug=False,
            logging="INFO",
            log_dir=None,
            framework_path=None,
            agents_dir=None,
        )

        result = self.command.run(args)

        assert isinstance(result, CommandResult)
        mock_ensure_deps.assert_called_once()
        mock_dashboard_launcher.launch_dashboard.assert_called_once_with(
            port=8080, monitor_mode=True
        )

    @patch("claude_mpm.cli.commands.run.subprocess.run")
    @patch("claude_mpm.core.config.Config")
    def test_run_with_claude_args(self, mock_config_class, mock_subprocess):
        """Test passing arguments through to Claude CLI."""
        mock_config = Mock()
        mock_config.ensure_paths.return_value = None
        mock_config.claude_desktop_config_dir = Path("/mock/claude/config")
        mock_config_class.return_value = mock_config

        mock_subprocess.return_value = Mock(returncode=0)

        args = Namespace(
            claude_args=["--model", "claude-3", "--temperature", "0.7"],
            monitor=False,
            websocket_port=None,
            no_hooks=False,
            no_tickets=False,
            intercept_commands=False,
            no_native_agents=False,
            launch_method="default",
            mpm_resume=False,
            input=None,
            non_interactive=False,
            debug=False,
            logging="INFO",
            log_dir=None,
            framework_path=None,
            agents_dir=None,
        )

        result = self.command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is True
        # Verify Claude args were passed through
        call_args = mock_subprocess.call_args[0][0]
        assert "--model" in call_args
        assert "claude-3" in call_args

    @patch("claude_mpm.cli.commands.run.subprocess.run")
    def test_run_subprocess_error(self):
        """Test handling of subprocess errors."""
        self.side_effect = subprocess.CalledProcessError(1, "claude")

        args = Namespace(
            claude_args=[],
            monitor=False,
            websocket_port=None,
            no_hooks=False,
            no_tickets=False,
            intercept_commands=False,
            no_native_agents=False,
            launch_method="default",
            mpm_resume=False,
            input=None,
            non_interactive=False,
            debug=False,
            logging="INFO",
            log_dir=None,
            framework_path=None,
            agents_dir=None,
        )

        result = self.command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is False
        assert "Failed to run Claude" in result.message

    def test_filter_claude_mpm_args():
        """Test filtering of MPM-specific arguments."""
        # Test with MPM-specific flags that should be filtered
        claude_args = ["--monitor", "--debug", "actual-arg", "--input", "file.txt"]
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

    @patch("claude_mpm.cli.commands.run.list_agent_versions_at_startup")
    @patch("claude_mpm.cli.commands.run.subprocess.run")
    @patch("claude_mpm.cli.commands.run.Config")
    def test_run_with_no_native_agents(
        self, mock_subprocess, mock_list_agents
    ):
        """Test running with native agents disabled."""
        mock_config = Mock()
        mock_config.ensure_paths.return_value = None
        mock_config.claude_desktop_config_dir = Path("/mock/claude/config")
        self.return_value = mock_config

        mock_subprocess.return_value = Mock(returncode=0)

        args = Namespace(
            claude_args=[],
            monitor=False,
            websocket_port=None,
            no_hooks=False,
            no_tickets=False,
            intercept_commands=False,
            no_native_agents=True,  # Disable native agents
            launch_method="default",
            mpm_resume=False,
            input=None,
            non_interactive=False,
            debug=False,
            logging="INFO",
            log_dir=None,
            framework_path=None,
            agents_dir=None,
        )

        result = self.command.run(args)

        assert isinstance(result, CommandResult)
        # Agent versions should not be listed when disabled
        mock_list_agents.assert_not_called()

    @patch("claude_mpm.cli.commands.run.subprocess.run")
    @patch("claude_mpm.cli.commands.run.Config")
    def test_run_with_resume(self, mock_subprocess):
        """Test running with resume flag."""
        mock_config = Mock()
        mock_config.ensure_paths.return_value = None
        mock_config.claude_desktop_config_dir = Path("/mock/claude/config")
        self.return_value = mock_config

        mock_subprocess.return_value = Mock(returncode=0)

        args = Namespace(
            claude_args=[],
            monitor=False,
            websocket_port=None,
            no_hooks=False,
            no_tickets=False,
            intercept_commands=False,
            no_native_agents=False,
            launch_method="default",
            mpm_resume=True,  # Enable resume
            input=None,
            non_interactive=False,
            debug=False,
            logging="INFO",
            log_dir=None,
            framework_path=None,
            agents_dir=None,
        )

        result = self.command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is True
        # Verify resume flag was handled
        call_args = mock_subprocess.call_args[0][0]
        assert "--resume" in call_args

    @patch("claude_mpm.cli.commands.run.subprocess.run")
    @patch("claude_mpm.cli.commands.run.Config")
    def test_run_with_custom_websocket_port(self, mock_subprocess):
        """Test running with custom websocket port."""
        mock_config = Mock()
        mock_config.ensure_paths.return_value = None
        mock_config.claude_desktop_config_dir = Path("/mock/claude/config")
        self.return_value = mock_config

        mock_subprocess.return_value = Mock(returncode=0)

        args = Namespace(
            claude_args=[],
            monitor=False,
            websocket_port=9090,  # Custom port
            no_hooks=False,
            no_tickets=False,
            intercept_commands=False,
            no_native_agents=False,
            launch_method="default",
            mpm_resume=False,
            input=None,
            non_interactive=False,
            debug=False,
            logging="INFO",
            log_dir=None,
            framework_path=None,
            agents_dir=None,
        )

        with patch.dict("os.environ"):
            result = self.command.run(args)

            assert isinstance(result, CommandResult)
            assert result.success is True
            # Verify port was set in environment
            import os

            assert os.environ.get("WEBSOCKET_PORT") == "9090"
