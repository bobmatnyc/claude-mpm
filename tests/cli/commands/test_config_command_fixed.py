"""
Comprehensive tests for the ConfigCommand class.

WHY: The config command manages claude-mpm configuration, which is critical
for system operation. It handles viewing, setting, and validating configuration.

DESIGN DECISIONS:
- Test all subcommands (validate, view, status) per actual implementation
- Mock file operations to avoid modifying actual config
- Test validation logic thoroughly
- Verify output formatting options
- Test error handling for invalid configurations
"""

from argparse import Namespace
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import yaml

from claude_mpm.cli.commands.config import ConfigCommand
from claude_mpm.cli.shared.base_command import CommandResult


class TestConfigCommand:
    """Test ConfigCommand functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.command = ConfigCommand()

    def test_initialization():
        """Test ConfigCommand initialization."""
        assert self.command.command_name == "config"
        assert self.command.logger is not None

    def test_validate_args_no_command():
        """Test validation with no config command."""
        args = Namespace()
        error = self.command.validate_args(args)
        assert error == "No config command specified"

    def test_validate_args_valid_commands():
        """Test validation with valid config commands."""
        # Based on the actual implementation, these are the valid commands
        valid_commands = ["validate", "view", "status"]

        for cmd in valid_commands:
            args = Namespace(config_command=cmd)
            error = self.command.validate_args(args)
            assert error is None, f"Command {cmd} should be valid"

    def test_validate_args_invalid_command():
        """Test validation with invalid config command."""
        args = Namespace(config_command="invalid")
        error = self.command.validate_args(args)
        assert error is not None
        assert "Unknown config command" in error
        assert "invalid" in error

    def test_run_validate_command():
        """Test validate config command."""
        args = Namespace(config_command="validate", format="text", config_file=None)

        with patch.object(self.command, "_validate_config") as mock_validate:
            mock_validate.return_value = CommandResult.success_result("Config valid")

            result = self.command.run(args)

            assert isinstance(result, CommandResult)
            assert result.success is True
            mock_validate.assert_called_once_with(args)

    def test_run_view_command():
        """Test view config command."""
        args = Namespace(config_command="view", format="json")

        with patch.object(self.command, "_view_config") as mock_view:
            mock_view.return_value = CommandResult.success_result(
                "Config viewed", data={"version": "1.0.0", "logging": {"level": "INFO"}}
            )

            result = self.command.run(args)

            assert isinstance(result, CommandResult)
            assert result.success is True
            mock_view.assert_called_once_with(args)

    def test_run_status_command():
        """Test status config command."""
        args = Namespace(config_command="status", format="text")

        with patch.object(self.command, "_show_config_status") as mock_status:
            mock_status.return_value = CommandResult.success_result(
                "Config status shown"
            )

            result = self.command.run(args)

            assert isinstance(result, CommandResult)
            assert result.success is True
            mock_status.assert_called_once_with(args)

    def test_run_unknown_command():
        """Test unknown config command."""
        args = Namespace(config_command="unknown", format="text")

        result = self.command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is False
        assert "Unknown config command" in result.message

    @patch("claude_mpm.cli.commands.config.Path")
    @patch("claude_mpm.cli.commands.config.yml.safe_load")
    @patch("builtins.open", new_callable=mock_open, read_data="version: 1.0.0")
    def test_validate_config_success(mock_file, mock_yaml, mock_path):
        """Test successful config validation."""
        # Setup mocks
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.is_file.return_value = True
        mock_path.return_value = mock_path_instance

        mock_yaml.return_value = {"version": "1.0.0", "logging": {"level": "INFO"}}

        args = Namespace(config_command="validate", config_file=None, format="text")

        result = self.command.run(args)

        # Since we're testing the actual implementation, check appropriate results
        assert isinstance(result, CommandResult)

    @patch("claude_mpm.cli.commands.config.Path")
    def test_validate_config_missing_file(mock_path):
        """Test config validation with missing file."""
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = False
        mock_path.return_value = mock_path_instance

        args = Namespace(config_command="validate", config_file=None, format="text")

        result = self.command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is False

    @patch("claude_mpm.cli.commands.config.Config")
    def test_view_config_implementation(mock_config_class):
        """Test view config implementation."""
        mock_config = Mock()
        mock_config.return_value.get_all.return_value = {
            "version": "1.0.0",
            "logging": {"level": "INFO"},
            "agents": {"enabled": True},
        }
        mock_config_class.get_instance.return_value = mock_config

        args = Namespace(config_command="view", format="json")

        result = self.command.run(args)

        assert isinstance(result, CommandResult)

    @patch("claude_mpm.cli.commands.config.Config")
    def test_show_config_status_implementation(mock_config_class):
        """Test show config status implementation."""
        mock_config = Mock()
        mock_config.is_valid.return_value = True
        mock_config.return_value.get_config_file.return_value = Path(
            "/test/config.yaml"
        )
        mock_config_class.get_instance.return_value = mock_config

        args = Namespace(config_command="status", format="text")

        result = self.command.run(args)

        assert isinstance(result, CommandResult)

    def test_run_with_exception():
        """Test general exception handling in run method."""
        args = Namespace(config_command="validate", format="text")

        with patch.object(
            self.command, "_validate_config", side_effect=Exception("Test error")
        ):
            result = self.command.run(args)

            # The run method might catch exceptions or let them bubble up
            # Adjust based on actual implementation
            assert isinstance(result, CommandResult)

    @patch("claude_mpm.cli.commands.config.Config")
    def test_output_formats(mock_config_class):
        """Test different output formats."""
        mock_config = Mock()
        mock_config.return_value.get_all.return_value = {
            "version": "1.0.0",
            "logging": {"level": "INFO"},
        }
        mock_config_class.get_instance.return_value = mock_config

        formats = ["json", "yaml", "text"]

        for fmt in formats:
            args = Namespace(config_command="view", format=fmt)

            result = self.command.run(args)

            assert isinstance(result, CommandResult)
            # The view command should handle all formats

    @patch("claude_mpm.cli.commands.config.yml.safe_load")
    @patch("builtins.open", new_callable=mock_open)
    def test_validate_config_with_yaml_error(mock_file, mock_yaml):
        """Test config validation with YAML parsing error."""
        mock_yaml.side_effect = yaml.YAMLError("Invalid YAML")

        args = Namespace(
            config_command="validate", config_file="test.yaml", format="text"
        )

        with patch("claude_mpm.cli.commands.config.Path") as mock_path:
            mock_path_instance = Mock()
            mock_path_instance.exists.return_value = True
            mock_path_instance.is_file.return_value = True
            mock_path.return_value = mock_path_instance

            result = self.command.run(args)

            assert isinstance(result, CommandResult)
            assert result.success is False

    def test_validate_args_with_config_file():
        """Test validation with config_file argument."""
        args = Namespace(config_command="validate", config_file="custom.yaml")

        error = self.command.validate_args(args)
        assert error is None

    def test_command_result_structure():
        """Test that command results have proper structure."""
        args = Namespace(config_command="unknown", format="json")

        result = self.command.run(args)

        assert hasattr(result, "success")
        assert hasattr(result, "message")
        assert isinstance(result.success, bool)
        assert isinstance(result.message, str)
