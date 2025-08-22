"""
Comprehensive tests for BaseCommand pattern and shared CLI utilities.

WHY: Verify that the BaseCommand pattern works correctly and provides
consistent behavior across all migrated CLI commands.
"""

import pytest
import tempfile
from argparse import Namespace
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from claude_mpm.cli.shared.base_command import BaseCommand, CommandResult, ServiceCommand, AgentCommand, MemoryCommand
from claude_mpm.utils.config_manager import ConfigurationManager as ConfigManager


class TestCommandResult:
    """Test CommandResult data structure."""

    def test_success_result_creation():
        """Test creating success results."""
        result = CommandResult.success_result("Test success")
        assert result.success is True
        assert result.exit_code == 0
        assert result.message == "Test success"
        assert result.data is None

    def test_success_result_with_data():
        """Test creating success results with data."""
        data = {"key": "value"}
        result = CommandResult.success_result("Test success", data)
        assert result.success is True
        assert result.exit_code == 0
        assert result.message == "Test success"
        assert result.data == data

    def test_error_result_creation():
        """Test creating error results."""
        result = CommandResult.error_result("Test error")
        assert result.success is False
        assert result.exit_code == 1
        assert result.message == "Test error"
        assert result.data is None

    def test_error_result_with_custom_exit_code():
        """Test creating error results with custom exit code."""
        result = CommandResult.error_result("Test error", exit_code=2)
        assert result.success is False
        assert result.exit_code == 2
        assert result.message == "Test error"

    def test_error_result_with_data():
        """Test creating error results with data."""
        data = {"error_type": "validation"}
        result = CommandResult.error_result("Test error", data=data)
        assert result.success is False
        assert result.exit_code == 1
        assert result.message == "Test error"
        assert result.data == data


class ConcreteCommand(BaseCommand):
    """Concrete implementation of BaseCommand for testing."""

    def __init__(self, command_name: str = "test"):
        super().__init__(command_name)
        self.run_called = False
        self.run_args = None

    def run(self, args) -> CommandResult:
        """Test implementation of run method."""
        self.run_called = True
        self.run_args = args
        return CommandResult.success_result("Test command executed")

    def validate_args(self, args) -> str:
        """Test implementation of validate_args."""
        if hasattr(args, 'invalid') and args.invalid:
            return "Invalid argument provided"
        return None


class TestBaseCommand:
    """Test BaseCommand functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.command = ConcreteCommand()

    def test_initialization():
        """Test BaseCommand initialization."""
        assert self.command.command_name == "test"
        assert self.command.logger is not None
        assert self.command._config is None
        assert self.command._working_dir is None

    def test_config_lazy_loading():
        """Test configuration lazy loading."""
        # Config should be None initially
        assert self.command._config is None
        
        # Accessing config should create instance
        config = self.command.config
        assert config is not None
        assert isinstance(config, Config)
        assert self.command._config is config
        
        # Second access should return same instance
        config2 = self.command.config
        assert config2 is config

    def test_working_dir_default():
        """Test working directory default behavior."""
        with patch('os.getcwd', return_value='/test/dir'):
            working_dir = self.command.working_dir
            assert working_dir == Path('/test/dir')

    def test_working_dir_from_env():
        """Test working directory from environment variable."""
        with patch.dict('os.environ', {'CLAUDE_MPM_USER_PWD': '/env/dir'}):
            # Reset cached working dir
            self.command._working_dir = None
            working_dir = self.command.working_dir
            assert working_dir == Path('/env/dir')

    def test_setup_logging_debug():
        """Test logging setup with debug flag."""
        args = Namespace(debug=True)
        
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            self.command.setup_logging(args)
            mock_logger.setLevel.assert_called_once()

    def test_setup_logging_verbose():
        """Test logging setup with verbose flag."""
        args = Namespace(verbose=True, debug=False)
        
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            self.command.setup_logging(args)
            mock_logger.setLevel.assert_called_once()

    def test_setup_logging_quiet():
        """Test logging setup with quiet flag."""
        args = Namespace(quiet=True, debug=False, verbose=False)
        
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            self.command.setup_logging(args)
            mock_logger.setLevel.assert_called_once()

    def test_load_config_default():
        """Test configuration loading with default behavior."""
        args = Namespace()

        # Mock the Config class instead of the property
        with patch('claude_mpm.cli.shared.command_base.Config') as mock_config_class:
            mock_config = Mock()
            mock_config_class.return_value = mock_config

            self.command.load_config(args)
            # Should create config instance
            assert self.command._config is mock_config

    def test_load_config_with_file():
        """Test configuration loading with specific file."""
        with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as tmp:
            tmp.write(b'test_key: test_value\n')
            tmp.flush()
            
            args = Namespace(config=Path(tmp.name))
            
            # Mock Config to avoid actual file loading complexity
            with patch('claude_mpm.cli.shared.command_base.Config') as mock_config_class:
                mock_config = Mock()
                mock_config_class.return_value = mock_config
                
                self.command.load_config(args)
                mock_config_class.assert_called_once_with(config_file=Path(tmp.name))
                assert self.command._config is mock_config

    def test_execute_success():
        """Test successful command execution."""
        args = Namespace()
        
        result = self.command.execute(args)
        
        assert isinstance(result, CommandResult)
        assert result.success is True
        assert result.exit_code == 0
        assert result.message == "Test command executed"
        assert self.command.run_called is True
        assert self.command.run_args is args

    def test_execute_validation_error():
        """Test command execution with validation error."""
        args = Namespace(invalid=True)
        
        result = self.command.execute(args)
        
        assert isinstance(result, CommandResult)
        assert result.success is False
        assert result.exit_code == 1
        assert result.message == "Invalid argument provided"
        assert self.command.run_called is False

    def test_execute_keyboard_interrupt():
        """Test command execution with keyboard interrupt."""
        args = Namespace()
        
        # Mock run method to raise KeyboardInterrupt
        with patch.object(self.command, 'run', side_effect=KeyboardInterrupt()):
            result = self.command.execute(args)
            
            assert isinstance(result, CommandResult)
            assert result.success is False
            assert result.exit_code == 130
            assert "cancelled by user" in result.message

    def test_execute_exception():
        """Test command execution with general exception."""
        args = Namespace()
        
        # Mock run method to raise exception
        with patch.object(self.command, 'run', side_effect=Exception("Test error")):
            result = self.command.execute(args)
            
            assert isinstance(result, CommandResult)
            assert result.success is False
            assert result.exit_code == 1
            assert "Test error" in result.message

    def test_print_result_text_format():
        """Test printing result in text format."""
        result = CommandResult.success_result("Test success")
        args = Namespace(format='text')
        
        with patch('claude_mpm.cli.shared.output_formatters.format_output') as mock_format:
            mock_format.return_value = "Formatted output"
            
            with patch('builtins.print') as mock_print:
                self.command.print_result(result, args)
                
                mock_format.assert_called_once_with(result, 'text')
                mock_print.assert_called_once_with("Formatted output")

    def test_print_result_to_file():
        """Test printing result to file."""
        result = CommandResult.success_result("Test success")
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
            args = Namespace(format='json', output=tmp.name)
            
            with patch('claude_mpm.cli.shared.output_formatters.format_output') as mock_format:
                mock_format.return_value = '{"success": true}'
                
                self.command.print_result(result, args)
                
                # Verify file was written
                with open(tmp.name, 'r') as f:
                    content = f.read()
                    assert content == '{"success": true}'


class ConcreteServiceCommand(ServiceCommand):
    """Concrete implementation of ServiceCommand for testing."""

    def run(self, args) -> CommandResult:
        """Test implementation of run method."""
        return CommandResult.success_result("Service command executed")


class ConcreteAgentCommand(AgentCommand):
    """Concrete implementation of AgentCommand for testing."""

    def run(self, args) -> CommandResult:
        """Test implementation of run method."""
        return CommandResult.success_result("Agent command executed")


class ConcreteMemoryCommand(MemoryCommand):
    """Concrete implementation of MemoryCommand for testing."""

    def run(self, args) -> CommandResult:
        """Test implementation of run method."""
        return CommandResult.success_result("Memory command executed")


class TestServiceCommand:
    """Test ServiceCommand functionality."""

    def test_initialization():
        """Test ServiceCommand initialization."""
        mock_service_class = Mock()
        command = ConcreteServiceCommand("test-service", mock_service_class)

        assert command.command_name == "test-service"
        assert command.service_class is mock_service_class
        assert command._service is None

    def test_service_lazy_loading():
        """Test service lazy loading."""
        mock_service_class = Mock()
        mock_service_instance = Mock()
        mock_service_class.return_value = mock_service_instance

        command = ConcreteServiceCommand("test-service", mock_service_class)

        # Service should be None initially
        assert command._service is None

        # Accessing service should create instance
        service = command.service
        assert service is mock_service_instance
        assert command._service is mock_service_instance
        mock_service_class.assert_called_once()

        # Second access should return same instance
        service2 = command.service
        assert service2 is mock_service_instance
        # Should not call service_class again
        assert mock_service_class.call_count == 1


class TestAgentCommand:
    """Test AgentCommand functionality."""

    def test_initialization():
        """Test AgentCommand initialization."""
        command = ConcreteAgentCommand("test-agent")
        assert command.command_name == "test-agent"

    def test_get_agent_dir_from_args():
        """Test getting agent directory from arguments."""
        command = ConcreteAgentCommand("test-agent")
        agent_dir = Path("/test/agents")
        args = Namespace(agent_dir=agent_dir)

        result = command.get_agent_dir(args)
        assert result == agent_dir

    def test_get_agent_dir_default():
        """Test getting agent directory default."""
        command = ConcreteAgentCommand("test-agent")
        args = Namespace()

        # Mock the underlying _working_dir attribute
        command._working_dir = Path("/test/working")
        result = command.get_agent_dir(args)
        assert result == Path("/test/working")

    def test_get_agent_pattern():
        """Test getting agent pattern from arguments."""
        command = ConcreteAgentCommand("test-agent")
        args = Namespace(agent="test-pattern")

        result = command.get_agent_pattern(args)
        assert result == "test-pattern"

    def test_get_agent_pattern_none():
        """Test getting agent pattern when not provided."""
        command = ConcreteAgentCommand("test-agent")
        args = Namespace()

        result = command.get_agent_pattern(args)
        assert result is None


class TestMemoryCommand:
    """Test MemoryCommand functionality."""

    def test_initialization():
        """Test MemoryCommand initialization."""
        command = ConcreteMemoryCommand("test-memory")
        assert command.command_name == "test-memory"

    def test_get_memory_dir_from_args():
        """Test getting memory directory from arguments."""
        command = ConcreteMemoryCommand("test-memory")
        memory_dir = Path("/test/memories")
        args = Namespace(memory_dir=memory_dir)

        result = command.get_memory_dir(args)
        assert result == memory_dir

    def test_get_memory_dir_default():
        """Test getting memory directory default."""
        command = ConcreteMemoryCommand("test-memory")
        args = Namespace()

        # Mock the underlying _working_dir attribute
        command._working_dir = Path("/test/working")
        result = command.get_memory_dir(args)
        assert result == Path("/test/working") / ".claude-mpm" / "memories"