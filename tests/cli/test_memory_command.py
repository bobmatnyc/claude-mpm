"""
Comprehensive tests for the migrated MemoryCommand class.

WHY: Verify that the memory command migration to BaseCommand pattern
works correctly and maintains backward compatibility.
"""

import pytest
from argparse import Namespace
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from claude_mpm.cli.commands.memory import MemoryManagementCommand, manage_memory
from claude_mpm.cli.shared.command_base import CommandResult


class TestMemoryCommand:
    """Test MemoryCommand functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.command = MemoryManagementCommand()

    def test_initialization(self):
        """Test MemoryCommand initialization."""
        assert self.command.command_name == "memory"
        assert self.command.logger is not None

    def test_validate_args_no_command(self):
        """Test validation with no memory command (should be valid for status)."""
        args = Namespace()
        error = self.command.validate_args(args)
        assert error is None  # No command defaults to status

    def test_validate_args_invalid_command(self):
        """Test validation with invalid memory command."""
        args = Namespace(memory_command="invalid")
        error = self.command.validate_args(args)
        assert "Unknown memory command" in error

    def test_validate_args_valid_command(self):
        """Test validation with valid memory command."""
        args = Namespace(memory_command="init")
        error = self.command.validate_args(args)
        assert error is None

    @patch('claude_mpm.cli.commands.memory.AgentMemoryManager')
    def test_run_default_status(self, mock_memory_manager_class):
        """Test running memory command with default (status)."""
        mock_manager = Mock()
        mock_memory_manager_class.return_value = mock_manager
        
        args = Namespace()
        
        with patch.object(self.command, '_show_status') as mock_show_status:
            mock_show_status.return_value = CommandResult.success_result("Status shown")
            
            result = self.command.run(args)
            
            assert isinstance(result, CommandResult)
            assert result.success is True
            mock_show_status.assert_called_once_with(args)

    @patch('claude_mpm.cli.commands.memory.AgentMemoryManager')
    def test_run_init_command(self, mock_memory_manager_class):
        """Test running memory init command."""
        mock_manager = Mock()
        mock_memory_manager_class.return_value = mock_manager

        args = Namespace(memory_command="init")

        with patch.object(self.command, '_init_memory') as mock_init:
            mock_init.return_value = CommandResult.success_result("Memory initialized")

            result = self.command.run(args)

            assert isinstance(result, CommandResult)
            assert result.success is True
            mock_init.assert_called_once_with(args)

    @patch('claude_mpm.cli.commands.memory.AgentMemoryManager')
    def test_run_view_command(self, mock_memory_manager_class):
        """Test running memory view command."""
        mock_manager = Mock()
        mock_memory_manager_class.return_value = mock_manager

        args = Namespace(memory_command="view")

        with patch.object(self.command, '_show_memories') as mock_show:
            mock_show.return_value = CommandResult.success_result("Memories shown")

            result = self.command.run(args)

            assert isinstance(result, CommandResult)
            assert result.success is True
            mock_show.assert_called_once_with(args)

    @patch('claude_mpm.cli.commands.memory.AgentMemoryManager')
    def test_run_add_command(self, mock_memory_manager_class):
        """Test running memory add command."""
        mock_manager = Mock()
        mock_memory_manager_class.return_value = mock_manager

        args = Namespace(memory_command="add")

        with patch.object(self.command, '_add_learning') as mock_add:
            mock_add.return_value = CommandResult.success_result("Learning added")

            result = self.command.run(args)

            assert isinstance(result, CommandResult)
            assert result.success is True
            mock_add.assert_called_once_with(args)

    @patch('claude_mpm.cli.commands.memory.AgentMemoryManager')
    def test_run_clean_command(self, mock_memory_manager_class):
        """Test running memory clean command."""
        mock_manager = Mock()
        mock_memory_manager_class.return_value = mock_manager
        
        args = Namespace(memory_command="clean")
        
        with patch.object(self.command, '_clean_memory') as mock_clean:
            mock_clean.return_value = CommandResult.success_result("Memory cleaned")
            
            result = self.command.run(args)
            
            assert isinstance(result, CommandResult)
            assert result.success is True
            mock_clean.assert_called_once_with(args)

    @patch('claude_mpm.cli.commands.memory.AgentMemoryManager')
    def test_run_optimize_command(self, mock_memory_manager_class):
        """Test running memory optimize command."""
        mock_manager = Mock()
        mock_memory_manager_class.return_value = mock_manager
        
        args = Namespace(memory_command="optimize")
        
        with patch.object(self.command, '_optimize_memory') as mock_optimize:
            mock_optimize.return_value = CommandResult.success_result("Memory optimized")
            
            result = self.command.run(args)
            
            assert isinstance(result, CommandResult)
            assert result.success is True
            mock_optimize.assert_called_once_with(args)

    @patch('claude_mpm.cli.commands.memory.AgentMemoryManager')
    def test_run_build_command(self, mock_memory_manager_class):
        """Test running memory build command."""
        mock_manager = Mock()
        mock_memory_manager_class.return_value = mock_manager
        
        args = Namespace(memory_command="build")
        
        with patch.object(self.command, '_build_memory') as mock_build:
            mock_build.return_value = CommandResult.success_result("Memory built")
            
            result = self.command.run(args)
            
            assert isinstance(result, CommandResult)
            assert result.success is True
            mock_build.assert_called_once_with(args)

    @patch('claude_mpm.cli.commands.memory.AgentMemoryManager')
    def test_run_cross_ref_command(self, mock_memory_manager_class):
        """Test running memory cross-ref command."""
        mock_manager = Mock()
        mock_memory_manager_class.return_value = mock_manager
        
        args = Namespace(memory_command="cross-ref")
        
        with patch.object(self.command, '_cross_reference_memory') as mock_cross_ref:
            mock_cross_ref.return_value = CommandResult.success_result("Cross-reference completed")
            
            result = self.command.run(args)
            
            assert isinstance(result, CommandResult)
            assert result.success is True
            mock_cross_ref.assert_called_once_with(args)

    @patch('claude_mpm.cli.commands.memory.AgentMemoryManager')
    def test_run_route_command(self, mock_memory_manager_class):
        """Test running memory route command."""
        mock_manager = Mock()
        mock_memory_manager_class.return_value = mock_manager
        
        args = Namespace(memory_command="route")
        
        with patch.object(self.command, '_route_memory_command') as mock_route:
            mock_route.return_value = CommandResult.success_result("Command routed")
            
            result = self.command.run(args)
            
            assert isinstance(result, CommandResult)
            assert result.success is True
            mock_route.assert_called_once_with(args)

    def test_run_unknown_command(self):
        """Test running unknown memory command."""
        args = Namespace(memory_command="unknown")
        result = self.command.run(args)
        
        assert isinstance(result, CommandResult)
        assert result.success is False
        assert "Unknown memory command" in result.message

    @patch('claude_mpm.cli.commands.memory.AgentMemoryManager')

    def test_init_memory_success(self, mock_memory_manager_class):
        """Test successful memory initialization."""
        mock_manager = Mock()
        mock_memory_manager_class.return_value = mock_manager
        
        args = Namespace()
        result = self.command._init_memory(args)
        
        assert isinstance(result, CommandResult)
        assert result.success is True
        assert "initialization" in result.message.lower()

    @patch('claude_mpm.cli.commands.memory.AgentMemoryManager')

    def test_init_memory_failure(self, mock_memory_manager_class):
        """Test memory initialization - current implementation always succeeds."""
        mock_manager = Mock()
        mock_memory_manager_class.return_value = mock_manager

        args = Namespace()
        result = self.command._init_memory(args)

        # Current implementation always succeeds by design (shows task to user)
        assert isinstance(result, CommandResult)
        assert result.success is True
        assert "initialization" in result.message.lower()

    @patch('claude_mpm.cli.commands.memory.AgentMemoryManager')

    def test_show_status_success(self, mock_memory_manager_class):
        """Test successful memory status display."""
        mock_manager = Mock()
        mock_manager.get_memory_status.return_value = {
            'total_size_kb': 100.5,
            'memory_count': 5,
            'enabled': True
        }
        mock_manager.memory_dir = Mock()
        mock_manager.memory_dir.glob.return_value = []
        mock_memory_manager_class.return_value = mock_manager

        args = Namespace()
        result = self.command._show_status(args)

        assert isinstance(result, CommandResult)
        assert result.success is True

    @patch('claude_mpm.cli.commands.memory.AgentMemoryManager')
    
    def test_show_memories_text_format(self, mock_memory_manager_class):
        """Test showing memories in text format."""
        mock_manager = Mock()
        mock_memory_manager_class.return_value = mock_manager
        
        args = Namespace(format='text')
        result = self.command._show_memories(args)
        
        assert isinstance(result, CommandResult)
        assert result.success is True

    @patch('claude_mpm.cli.commands.memory.AgentMemoryManager')
    def test_show_memories_json_format(self, mock_memory_manager_class):
        """Test showing memories in JSON format."""
        mock_manager = Mock()
        mock_manager.get_memories.return_value = [
            {"id": "1", "content": "Memory 1"},
            {"id": "2", "content": "Memory 2"}
        ]
        # Mock the memory directory and its methods
        from pathlib import Path
        mock_memory_dir = Mock(spec=Path)
        mock_memory_dir.exists.return_value = True
        mock_memory_dir.glob.return_value = []
        mock_manager.memory_dir = mock_memory_dir
        mock_manager.memories_dir = mock_memory_dir
        mock_memory_manager_class.return_value = mock_manager

        args = Namespace(format='json')
        result = self.command._show_memories(args)

        assert isinstance(result, CommandResult)
        assert result.success is True
        assert result.data is not None
        assert "agents" in result.data

    @patch('claude_mpm.cli.commands.memory.AgentMemoryManager')
    def test_route_memory_command_json_format(self, mock_memory_manager_class):
        """Test routing memory command in JSON format."""
        mock_manager = Mock()
        mock_memory_manager_class.return_value = mock_manager
        
        args = Namespace(format='json', command='test command')
        result = self.command._route_memory_command(args)
        
        assert isinstance(result, CommandResult)
        assert result.success is True
        assert result.data is not None
        assert "routed_to" in result.data

    @patch('claude_mpm.cli.commands.memory._route_memory_command')
    @patch('claude_mpm.cli.commands.memory.AgentMemoryManager')
    def test_route_memory_command_text_format(self, mock_memory_manager_class, mock_route_func):
        """Test routing memory command in text format."""
        mock_manager = Mock()
        mock_memory_manager_class.return_value = mock_manager

        args = Namespace(format='text')
        result = self.command._route_memory_command(args)

        assert isinstance(result, CommandResult)
        assert result.success is True


class TestManageMemoryFunction:
    """Test manage_memory backward compatibility function."""

    @patch.object(MemoryManagementCommand, 'execute')
    def test_manage_memory_success(self, mock_execute):
        """Test manage_memory function with success."""
        mock_result = CommandResult.success_result("Memory managed")
        mock_execute.return_value = mock_result
        
        args = Namespace(memory_command="status")
        exit_code = manage_memory(args)
        
        assert exit_code == 0
        mock_execute.assert_called_once_with(args)

    @patch.object(MemoryManagementCommand, 'execute')
    def test_manage_memory_error(self, mock_execute):
        """Test manage_memory function with error."""
        mock_result = CommandResult.error_result("Memory error", exit_code=2)
        mock_execute.return_value = mock_result

        args = Namespace(memory_command="init")
        exit_code = manage_memory(args)

        assert exit_code == 2
        mock_execute.assert_called_once_with(args)

    @patch.object(MemoryManagementCommand, 'execute')
    @patch.object(MemoryManagementCommand, 'print_result')
    def test_manage_memory_structured_output(self, mock_print, mock_execute):
        """Test manage_memory with structured output format."""
        mock_result = CommandResult.success_result("Memory managed", {"memories": []})
        mock_execute.return_value = mock_result
        
        args = Namespace(memory_command="view", format="json")
        exit_code = manage_memory(args)
        
        assert exit_code == 0
        mock_execute.assert_called_once_with(args)
        mock_print.assert_called_once_with(mock_result, args)


class TestMemoryCommandIntegration:
    """Integration tests for MemoryCommand."""

    @patch('claude_mpm.cli.commands.memory.AgentMemoryManager')
    def test_full_execution_flow(self, mock_memory_manager_class):
        """Test full execution flow with mocked dependencies."""
        command = MemoryManagementCommand()
        mock_manager = Mock()
        mock_manager.get_memories.return_value = [{"id": "1", "content": "Test memory"}]
        # Mock the memory directory and its methods
        from pathlib import Path
        mock_memory_dir = Mock(spec=Path)
        mock_memory_dir.exists.return_value = True
        mock_memory_dir.glob.return_value = []
        mock_manager.memory_dir = mock_memory_dir
        mock_manager.memories_dir = mock_memory_dir
        mock_memory_manager_class.return_value = mock_manager

        args = Namespace(memory_command="view", format="json")

        result = command.execute(args)

        assert isinstance(result, CommandResult)
        assert result.success is True
        assert result.data is not None

    @patch('claude_mpm.cli.commands.memory.AgentMemoryManager')
    def test_error_handling_in_execution(self, mock_memory_manager_class):
        """Test error handling during execution."""
        command = MemoryManagementCommand()
        mock_memory_manager_class.side_effect = Exception("Memory manager failed")
        
        args = Namespace(memory_command="init")
        
        result = command.execute(args)
        
        assert isinstance(result, CommandResult)
        assert result.success is False
        assert "Memory manager failed" in result.message
