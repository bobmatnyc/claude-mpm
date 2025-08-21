"""
Comprehensive tests for the migrated ConfigCommand class.

WHY: Verify that the config command migration to BaseCommand pattern
works correctly and maintains backward compatibility.
"""

import pytest
import tempfile
import json
import yaml
from argparse import Namespace
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from claude_mpm.cli.commands.config import ConfigCommand, manage_config
from claude_mpm.cli.shared.command_base import CommandResult
from claude_mpm.core.config import Config


class TestConfigCommand:
    """Test ConfigCommand functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.command = ConfigCommand()

    def test_initialization(self):
        """Test ConfigCommand initialization."""
        assert self.command.command_name == "config"
        assert self.command.logger is not None

    def test_validate_args_no_command(self):
        """Test validation with no config command."""
        args = Namespace()
        error = self.command.validate_args(args)
        assert error == "No config command specified"

    def test_validate_args_invalid_command(self):
        """Test validation with invalid config command."""
        args = Namespace(config_command="invalid")
        error = self.command.validate_args(args)
        assert "Unknown config command" in error

    def test_validate_args_valid_command(self):
        """Test validation with valid config command."""
        args = Namespace(config_command="view")
        error = self.command.validate_args(args)
        assert error is None

    @patch('claude_mpm.cli.commands.config.Config')
    def test_validate_config_success(self, mock_config_class):
        """Test successful config validation."""
        mock_config = Mock()
        mock_config.validate_configuration.return_value = (True, [], [])
        mock_config_class.return_value = mock_config

        # Create a temporary config file to avoid file not found error
        with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as tmp:
            tmp.write(b'test: value\n')
            tmp.flush()

            args = Namespace(config_command="validate", config_file=Path(tmp.name))
            result = self.command.run(args)

            assert isinstance(result, CommandResult)
            assert result.success is True
            assert "valid" in result.message.lower()

    @patch('claude_mpm.cli.commands.config.Config')
    def test_validate_config_failure(self, mock_config_class):
        """Test config validation failure."""
        mock_config = Mock()
        mock_config.validate_configuration.side_effect = Exception("Validation error")
        mock_config_class.return_value = mock_config

        # Create a temporary config file to avoid file not found error
        with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as tmp:
            tmp.write(b'test: value\n')
            tmp.flush()

            args = Namespace(config_command="validate", config_file=Path(tmp.name))
            result = self.command.run(args)

            assert isinstance(result, CommandResult)
            assert result.success is False
            assert "Validation error" in result.message

    @patch('claude_mpm.cli.commands.config.Config')
    def test_view_config_text_format(self, mock_config_class):
        """Test viewing config in text format."""
        mock_config = Mock()
        mock_config.to_dict.return_value = {"key": "value", "nested": {"inner": "data"}}
        mock_config_class.return_value = mock_config
        
        args = Namespace(config_command="view", config_file=None, format="text")
        
        with patch('claude_mpm.cli.commands.config.console') as mock_console:
            result = self.command.run(args)
            
            assert isinstance(result, CommandResult)
            assert result.success is True
            mock_console.print.assert_called()

    @patch('claude_mpm.cli.commands.config.Config')
    def test_view_config_json_format(self, mock_config_class):
        """Test viewing config in JSON format."""
        mock_config = Mock()
        mock_config.to_dict.return_value = {"key": "value"}
        mock_config_class.return_value = mock_config
        
        args = Namespace(config_command="view", config_file=None, format="json", output=None)
        
        with patch('claude_mpm.cli.commands.config.console') as mock_console:
            result = self.command.run(args)
            
            assert isinstance(result, CommandResult)
            assert result.success is True
            assert result.data == {"key": "value"}

    @patch('claude_mpm.cli.commands.config.Config')
    def test_view_config_yaml_format(self, mock_config_class):
        """Test viewing config in YAML format."""
        mock_config = Mock()
        mock_config.to_dict.return_value = {"key": "value"}
        mock_config_class.return_value = mock_config
        
        args = Namespace(config_command="view", config_file=None, format="yaml", output=None)
        
        with patch('claude_mpm.cli.commands.config.console') as mock_console:
            result = self.command.run(args)
            
            assert isinstance(result, CommandResult)
            assert result.success is True

    @patch('claude_mpm.cli.commands.config.Config')
    def test_view_config_with_output_file(self, mock_config_class):
        """Test viewing config with output to file."""
        mock_config = Mock()
        mock_config.to_dict.return_value = {"key": "value"}
        mock_config_class.return_value = mock_config
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
            args = Namespace(config_command="view", config_file=None, format="json", output=tmp.name)
            
            result = self.command.run(args)
            
            assert isinstance(result, CommandResult)
            assert result.success is True
            assert result.data == {"key": "value"}

    @patch('claude_mpm.cli.commands.config.Config')
    def test_view_config_table_format(self, mock_config_class):
        """Test viewing config in table format."""
        mock_config = Mock()
        mock_config.to_dict.return_value = {"key": "value", "nested": {"inner": "data"}}
        mock_config_class.return_value = mock_config
        
        args = Namespace(config_command="view", config_file=None, format="table")
        
        with patch.object(self.command, '_display_config_table') as mock_display:
            result = self.command.run(args)
            
            assert isinstance(result, CommandResult)
            assert result.success is True
            mock_display.assert_called_once()

    @patch('claude_mpm.cli.commands.config.Config')
    def test_show_config_status(self, mock_config_class):
        """Test showing config status."""
        mock_config = Mock()
        mock_status = {
            "loaded_from": "/test/config.yaml",
            "valid": True,
            "last_modified": "2023-01-01T00:00:00",
            "size": 1024
        }
        mock_config.get_configuration_status.return_value = mock_status
        mock_config_class.return_value = mock_config
        
        args = Namespace(config_command="status", config_file=None, format="text")
        
        with patch('claude_mpm.cli.commands.config.console') as mock_console:
            result = self.command.run(args)
            
            assert isinstance(result, CommandResult)
            assert result.success is True
            mock_console.print.assert_called()

    @patch('claude_mpm.cli.commands.config.Config')
    def test_show_config_status_json(self, mock_config_class):
        """Test showing config status in JSON format."""
        mock_config = Mock()
        mock_status = {"loaded_from": "/test/config.yaml", "valid": True}
        mock_config.get_configuration_status.return_value = mock_status
        mock_config_class.return_value = mock_config
        
        args = Namespace(config_command="status", config_file=None, format="json")
        
        result = self.command.run(args)
        
        assert isinstance(result, CommandResult)
        assert result.success is True
        assert result.data == mock_status

    def test_run_unknown_command(self):
        """Test running unknown config command."""
        args = Namespace(config_command="unknown")
        result = self.command.run(args)
        
        assert isinstance(result, CommandResult)
        assert result.success is False
        assert "Unknown config command" in result.message

    def test_display_config_table_flat(self):
        """Test displaying flat config as table."""
        config_dict = {"key1": "value1", "key2": "value2"}
        
        with patch('claude_mpm.cli.commands.config.console') as mock_console:
            self.command._display_config_table(config_dict)
            mock_console.print.assert_called()

    def test_display_config_table_nested(self):
        """Test displaying nested config as table."""
        config_dict = {
            "section1": {"key1": "value1", "key2": "value2"},
            "section2": {"nested": {"deep": "value"}}
        }
        
        with patch('claude_mpm.cli.commands.config.console') as mock_console:
            self.command._display_config_table(config_dict)
            mock_console.print.assert_called()

    def test_flatten_config_simple(self):
        """Test flattening simple config."""
        config = {"key": "value"}
        flattened = self.command._flatten_config(config)
        assert flattened == {"key": "value"}

    def test_flatten_config_nested(self):
        """Test flattening nested config."""
        config = {"section": {"key": "value", "nested": {"deep": "data"}}}
        flattened = self.command._flatten_config(config)
        assert flattened["section.key"] == "value"
        assert flattened["section.nested.deep"] == "data"

    def test_flatten_config_with_lists(self):
        """Test flattening config with lists."""
        config = {"items": ["item1", "item2"], "nested": {"list": [1, 2, 3]}}
        flattened = self.command._flatten_config(config)
        assert flattened["items"] == "['item1', 'item2']"
        assert flattened["nested.list"] == "[1, 2, 3]"


class TestManageConfigFunction:
    """Test manage_config backward compatibility function."""

    @patch.object(ConfigCommand, 'execute')
    def test_manage_config_success(self, mock_execute):
        """Test manage_config function with success."""
        mock_result = CommandResult.success_result("Config managed")
        mock_execute.return_value = mock_result
        
        args = Namespace(config_command="view")
        exit_code = manage_config(args)
        
        assert exit_code == 0
        mock_execute.assert_called_once_with(args)

    @patch.object(ConfigCommand, 'execute')
    def test_manage_config_error(self, mock_execute):
        """Test manage_config function with error."""
        mock_result = CommandResult.error_result("Config error", exit_code=2)
        mock_execute.return_value = mock_result
        
        args = Namespace(config_command="validate")
        exit_code = manage_config(args)
        
        assert exit_code == 2
        mock_execute.assert_called_once_with(args)

    @patch.object(ConfigCommand, 'execute')
    @patch.object(ConfigCommand, 'print_result')
    def test_manage_config_structured_output(self, mock_print, mock_execute):
        """Test manage_config with structured output format."""
        mock_result = CommandResult.success_result("Config managed", {"key": "value"})
        mock_execute.return_value = mock_result
        
        args = Namespace(config_command="view", format="json")
        exit_code = manage_config(args)
        
        assert exit_code == 0
        mock_execute.assert_called_once_with(args)
        mock_print.assert_called_once_with(mock_result, args)


class TestConfigCommandIntegration:
    """Integration tests for ConfigCommand."""

    def test_full_execution_flow(self):
        """Test full execution flow with mocked dependencies."""
        command = ConfigCommand()
        
        with patch('claude_mpm.cli.commands.config.Config') as mock_config_class:
            mock_config = Mock()
            mock_config.to_dict.return_value = {"test": "data"}
            mock_config_class.return_value = mock_config
            
            args = Namespace(config_command="view", format="json", config_file=None, output=None)
            
            result = command.execute(args)
            
            assert isinstance(result, CommandResult)
            assert result.success is True
            assert result.data == {"test": "data"}

    def test_error_handling_in_execution(self):
        """Test error handling during execution."""
        command = ConfigCommand()
        
        with patch('claude_mpm.cli.commands.config.Config') as mock_config_class:
            mock_config_class.side_effect = Exception("Config loading failed")
            
            args = Namespace(config_command="view", format="json")
            
            result = command.execute(args)
            
            assert isinstance(result, CommandResult)
            assert result.success is False
            assert "Config loading failed" in result.message
