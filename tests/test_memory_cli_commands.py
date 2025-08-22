#!/usr/bin/env python3
"""
Comprehensive unit tests for Memory CLI commands.

This test suite provides complete coverage for the memory CLI functionality
including:
- MemoryManagementCommand class methods
- AgentMemoryManager core functionality
- Memory file operations and validation
- Memory status and display functions
- Command routing and utilities
- Error handling and edge cases
"""

import json
import os
import sys
import tempfile
from argparse import Namespace
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, mock_open

import pytest

# Import the classes and functions we're testing
from claude_mpm.cli.commands.memory import (
    MemoryManagementCommand,
    _add_learning,
    _build_memory,
    _clean_memory,
    _cross_reference_memory,
    _init_memory,
    _optimize_memory,
    _output_all_memories_raw,
    _output_single_agent_raw,
    _parse_memory_content,
    _route_memory_command,
    _show_memories,
    _show_status,
    _view_memory,
    manage_memory,
)
from claude_mpm.utils.config_manager import ConfigurationManager as ConfigManager
from claude_mpm.services.agents.memory import AgentMemoryManager
from claude_mpm.cli.shared.base_command import CommandResult


class TestMemoryManagementCommand:
    """Test MemoryManagementCommand class methods."""

    @pytest.fixture
    def mock_memory_manager(self):
        """Create a mock AgentMemoryManager."""
        manager = Mock(spec=AgentMemoryManager)
        manager.memories_dir = Path("/test/memories")
        manager.project_memories_dir = Path("/test/.claude/memories")
        manager.load_agent_memory.return_value = (
            "# Test Memory\n## Patterns\n- Test pattern"
        )
        manager.get_memory_status.return_value = {
            "success": True,
            "system_enabled": True,
            "auto_learning": True,
            "memory_directory": "/test/.claude/memories",
            "system_health": "healthy",
            "total_agents": 3,
            "total_size_kb": 150,
            "agents": {
                "engineer": {
                    "size_kb": 50,
                    "size_limit_kb": 80,
                    "size_utilization": 62.5,
                    "sections": 3,
                    "items": 10,
                    "last_modified": "2025-01-01T12:00:00Z",
                    "auto_learning": True
                }
            }
        }
        manager.update_agent_memory.return_value = True
        manager.add_learning.return_value = True
        return manager

    @pytest.fixture
    def mock_config(self):
        """Create a mock Config."""
        config = Mock(spec=Config)
        return config

    @pytest.fixture
    def memory_subcommand(self, mock_memory_manager):
        """Create MemoryManagementCommand instance with mocked dependencies."""
        with patch('claude_mpm.cli.commands.memory.ConfigLoader') as mock_loader, \
             patch('claude_mpm.cli.commands.memory.AgentMemoryManager') as mock_manager_class:

            mock_loader.return_value.load_main_config.return_value = Mock()
            mock_manager_class.return_value = mock_memory_manager

            command = MemoryManagementCommand()
            return command

    def test_run_no_subcommand_shows_status(memory_command):
        """Test that run() with no subcommand shows status."""
        args = Namespace(memory_command=None)

        result = memory_command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is True
        assert "status" in result.message.lower()

    def test_run_status_command(memory_command):
        """Test run() with status command."""
        args = Namespace(memory_command="status", format="text")

        result = memory_command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is True
        assert "status" in result.message.lower()

    def test_run_init_command(memory_command):
        """Test run() with init command."""
        args = Namespace(memory_command="init", format="text")

        result = memory_command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is True
        assert "initialization" in result.message.lower()

    def test_run_show_memories_command(memory_command):
        """Test run() with show/view command."""
        args = Namespace(memory_command="show", format="text", agent=None)

        with patch('claude_mpm.cli.commands.memory._show_memories') as mock_show:
            result = memory_command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is True
        mock_show.assert_called_once()

    def test_run_add_learning_command(memory_command):
        """Test run() with add command."""
        args = Namespace(
            memory_command="add",
            format="text",
            agent="engineer",
            learning_type="pattern",
            content="Use dependency injection"
        )

        with patch('claude_mpm.cli.commands.memory._add_learning') as mock_add:
            result = memory_command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is True
        mock_add.assert_called_once()

    def test_run_unknown_command_returns_error(memory_command):
        """Test run() with unknown command returns error."""
        args = Namespace(memory_command="unknown_command")

        result = memory_command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is False
        assert "unknown" in result.message.lower() or "error" in result.message.lower()

    def test_get_status_data_no_memory_dir(memory_command, mock_memory_manager):
        """Test _get_status_data when memory directory doesn't exist."""
        mock_memory_manager.memories_dir = Path("/nonexistent")

        status_data = memory_command._get_status_data()

        assert status_data["exists"] is False
        assert status_data["agents"] == []
        assert status_data["total_size_kb"] == 0
        assert status_data["total_files"] == 0

    def test_get_status_data_with_memory_files(memory_command, mock_memory_manager):
        """Test _get_status_data with existing memory files."""
        # Mock memory directory with files
        mock_dir = Mock()
        mock_dir.exists.return_value = True

        # Mock memory files
        mock_file1 = Mock()
        mock_file1.is_file.return_value = True
        mock_file1.stem = "engineer_memories"
        mock_file1.name = "engineer_memories.md"
        mock_file1.stat.return_value.st_size = 1024  # 1KB

        mock_file2 = Mock()
        mock_file2.is_file.return_value = True
        mock_file2.stem = "qa_memories"
        mock_file2.name = "qa_memories.md"
        mock_file2.stat.return_value.st_size = 2048  # 2KB

        mock_dir.glob.return_value = [mock_file1, mock_file2]
        mock_memory_manager.memories_dir = mock_dir

        status_data = memory_command._get_status_data()

        assert status_data["exists"] is True
        assert len(status_data["agents"]) == 2
        assert status_data["total_size_kb"] == 3.0  # 3KB total
        assert status_data["total_files"] == 2


class TestAgentMemoryManager:
    """Test AgentMemoryManager core functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        with tmp_path as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def mock_config(self):
        """Create mock config."""
        config = Mock(spec=Config)
        config.memory_enabled = True
        config.auto_learning = True
        return config

    @pytest.fixture
    def memory_manager(self, temp_dir, mock_config):
        """Create AgentMemoryManager instance."""
        return AgentMemoryManager(mock_config, temp_dir)

    def test_load_agent_memory_creates_default_when_missing(memory_manager):
        """Test load_agent_memory creates default memory when file doesn't exist."""
        result = memory_manager.load_agent_memory("engineer")

        assert result is not None
        assert "# Engineer Agent Memory" in result
        assert "## Coding Patterns Learned" in result
        assert "## Implementation Guidelines" in result

    def test_load_agent_memory_returns_existing_content(memory_manager, temp_dir):
        """Test load_agent_memory returns existing file content."""
        # Create memory directory and file
        memory_dir = temp_dir / ".claude-mpm" / "memories"
        memory_dir.mkdir(parents=True)

        test_content = "# Test Memory\n## Test Section\n- Test item"
        memory_file = memory_dir / "engineer_memories.md"
        memory_file.write_text(test_content)

        result = memory_manager.load_agent_memory("engineer")

        assert result == test_content

    def test_update_agent_memory_adds_new_item(memory_manager):
        """Test update_agent_memory adds new learning item."""
        success = memory_manager.update_agent_memory(
            "engineer",
            "Coding Patterns Learned",
            "Use dependency injection pattern"
        )

        assert success is True

        # Verify the item was added
        memory_content = memory_manager.load_agent_memory("engineer")
        assert "Use dependency injection pattern" in memory_content

    def test_add_learning_with_pattern_type(memory_manager):
        """Test add_learning with pattern learning type."""
        success = memory_manager.add_learning(
            "engineer",
            "pattern",
            "Always validate input parameters"
        )

        assert success is True

        # Verify it was added to correct section
        memory_content = memory_manager.load_agent_memory("engineer")
        assert "Always validate input parameters" in memory_content
        assert "## Coding Patterns Learned" in memory_content

    def test_add_learning_with_architecture_type(memory_manager):
        """Test add_learning with architecture learning type."""
        success = memory_manager.add_learning(
            "engineer",
            "architecture",
            "System uses microservices pattern"
        )

        assert success is True

        memory_content = memory_manager.load_agent_memory("engineer")
        assert "System uses microservices pattern" in memory_content
        assert "## Project Architecture" in memory_content

    def test_save_memory_file_creates_directory(memory_manager, temp_dir):
        """Test _save_memory_file creates directory if it doesn't exist."""
        test_content = "# Test Memory Content"

        success = memory_manager._save_memory_file("test_agent", test_content)

        assert success is True

        # Verify directory was created
        memory_dir = temp_dir / ".claude-mpm" / "memories"
        assert memory_dir.exists()

        # Verify file was created
        memory_file = memory_dir / "test_agent_memories.md"
        assert memory_file.exists()
        assert memory_file.read_text() == test_content

    def test_save_memory_file_handles_errors(memory_manager):
        """Test _save_memory_file handles write errors gracefully."""
        # Mock Path.write_text to raise an exception
        with patch.object(Path, 'write_text', side_effect=PermissionError("Access denied")):
            success = memory_manager._save_memory_file("test_agent", "content")

            assert success is False

    def test_get_memory_status_returns_comprehensive_data(memory_manager, temp_dir):
        """Test get_memory_status returns comprehensive status information."""
        # Create some test memory files
        memory_dir = temp_dir / ".claude-mpm" / "memories"
        memory_dir.mkdir(parents=True)

        (memory_dir / "engineer_memories.md").write_text("# Engineer Memory\n" + "x" * 1000)
        (memory_dir / "qa_memories.md").write_text("# QA Memory\n" + "y" * 500)

        status = memory_manager.get_memory_status()

        assert status["system_enabled"] is True
        assert status["auto_learning"] is True
        assert "memory_directory" in status
        assert status["total_agents"] >= 0
        assert status["total_size_kb"] >= 0
        assert "system_health" in status

    def test_memory_file_migration_from_old_format(memory_manager, temp_dir):
        """Test migration from old memory file formats."""
        # Create memory directory
        memory_dir = temp_dir / ".claude-mpm" / "memories"
        memory_dir.mkdir(parents=True)

        # Create old format file
        old_content = "# Old Format Memory\n- Old learning item"
        old_file = memory_dir / "engineer_agent.md"
        old_file.write_text(old_content)

        # Load memory should trigger migration
        result = memory_manager.load_agent_memory("engineer")

        # Verify new format file exists
        new_file = memory_dir / "engineer_memories.md"
        assert new_file.exists()

        # Verify old file is removed
        assert not old_file.exists()

        # Verify content was migrated
        assert old_content in result


class TestMemoryFileOperations:
    """Test memory file operations and validation."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        with tmp_path as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def mock_config(self):
        """Create mock config."""
        config = Mock(spec=Config)
        config.memory_enabled = True
        config.auto_learning = True
        return config

    @pytest.fixture
    def memory_manager(self, temp_dir, mock_config):
        """Create AgentMemoryManager instance."""
        return AgentMemoryManager(mock_config, temp_dir)

    def test_memory_size_validation_within_limits(memory_manager):
        """Test memory size validation for content within limits."""
        # Create content under 80KB limit
        test_content = "# Test Memory\n" + "x" * 1000  # ~1KB

        is_valid, error_msg = memory_manager.validate_memory_size(test_content)

        assert is_valid is True
        assert error_msg is None

    def test_memory_size_validation_exceeds_limits(memory_manager):
        """Test memory size validation for content exceeding limits."""
        # Create content over 80KB limit
        test_content = "# Test Memory\n" + "x" * (85 * 1024)  # ~85KB

        is_valid, error_msg = memory_manager.validate_memory_size(test_content)

        assert is_valid is False
        assert error_msg is not None
        assert "exceeds" in error_msg.lower()

    def test_memory_directory_initialization(memory_manager, temp_dir):
        """Test memory directory is created with proper structure."""
        # Trigger directory creation by saving a memory
        memory_manager._save_memory_file("test", "# Test")

        memory_dir = temp_dir / ".claude-mpm" / "memories"
        assert memory_dir.exists()
        assert memory_dir.is_dir()

    def test_memory_file_naming_convention(memory_manager, temp_dir):
        """Test memory files follow correct naming convention."""
        test_agents = ["engineer", "qa", "research", "PM"]

        for agent in test_agents:
            memory_manager._save_memory_file(agent, f"# {agent} Memory")

            expected_file = temp_dir / ".claude-mpm" / "memories" / f"{agent}_memories.md"
            assert expected_file.exists()

    def test_memory_content_encoding(memory_manager, temp_dir):
        """Test memory files are saved with proper UTF-8 encoding."""
        # Test with unicode content
        unicode_content = "# Memory with Unicode\n- 测试 content\n- émoji: 🧠"

        success = memory_manager._save_memory_file("test", unicode_content)
        assert success is True

        # Read back and verify encoding
        memory_file = temp_dir / ".claude-mpm" / "memories" / "test_memories.md"
        read_content = memory_file.read_text(encoding="utf-8")
        assert read_content == unicode_content

    def test_memory_file_permissions(memory_manager, temp_dir):
        """Test memory files are created with appropriate permissions."""
        memory_manager._save_memory_file("test", "# Test")

        memory_file = temp_dir / ".claude-mpm" / "memories" / "test_memories.md"
        assert memory_file.exists()

        # File should be readable and writable by owner
        stat = memory_file.stat()
        assert stat.st_mode & 0o600  # Owner read/write permissions

    def test_concurrent_memory_access(memory_manager):
        """Test memory manager handles concurrent access gracefully."""
        import threading
        import time

        results = []
        errors = []

        def update_memory(agent_id, item_num):
            try:
                success = memory_manager.update_agent_memory(
                    agent_id,
                    "Test Section",
                    f"Test item {item_num}"
                )
                results.append(success)
            except Exception as e:
                errors.append(e)

        # Create multiple threads updating memory
        threads = []
        for i in range(5):
            thread = threading.Thread(target=update_memory, args=("engineer", i))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify no errors occurred
        assert len(errors) == 0
        assert len(results) == 5
        assert all(results)  # All updates should succeed

    def test_memory_backup_and_recovery(memory_manager, temp_dir):
        """Test memory content can be backed up and recovered."""
        # Create initial memory
        original_content = "# Original Memory\n- Important data"
        memory_manager._save_memory_file("engineer", original_content)

        # Simulate backup
        memory_file = temp_dir / ".claude-mpm" / "memories" / "engineer_memories.md"
        backup_content = memory_file.read_text()

        # Modify memory
        memory_manager._save_memory_file("engineer", "# Modified Memory")

        # Restore from backup
        memory_manager._save_memory_file("engineer", backup_content)

        # Verify restoration
        restored_content = memory_manager.load_agent_memory("engineer")
        assert restored_content == original_content

    def test_memory_file_corruption_handling(memory_manager, temp_dir):
        """Test handling of corrupted memory files."""
        # Create memory directory
        memory_dir = temp_dir / ".claude-mpm" / "memories"
        memory_dir.mkdir(parents=True)

        # Create corrupted file (binary data)
        corrupted_file = memory_dir / "engineer_memories.md"
        corrupted_file.write_bytes(b'\x00\x01\x02\x03\x04')

        # Loading should handle corruption gracefully
        result = memory_manager.load_agent_memory("engineer")

        # Should return default memory instead of crashing
        assert result is not None
        assert "# Engineer Agent Memory" in result


class TestMemoryStatusAndDisplay:
    """Test memory status and display functions."""

    @pytest.fixture
    def mock_memory_manager(self):
        """Create mock memory manager with comprehensive status."""
        manager = Mock(spec=AgentMemoryManager)
        manager.memories_dir = Path("/test/.claude/memories")
        manager.get_memory_status.return_value = {
            "success": True,
            "system_enabled": True,
            "auto_learning": True,
            "memory_directory": "/test/.claude/memories",
            "system_health": "healthy",
            "total_agents": 2,
            "total_size_kb": 100,
            "agents": {
                "engineer": {
                    "size_kb": 60,
                    "size_limit_kb": 80,
                    "size_utilization": 75,
                    "sections": 4,
                    "items": 15,
                    "last_modified": "2025-01-01T12:00:00Z",
                    "auto_learning": True
                },
                "qa": {
                    "size_kb": 40,
                    "size_limit_kb": 80,
                    "size_utilization": 50,
                    "sections": 3,
                    "items": 10,
                    "last_modified": "2025-01-01T11:00:00Z",
                    "auto_learning": True
                }
            }
        }
        return manager

    def test_show_status_displays_system_health(mock_memory_manager):
        """Test _show_status displays system health information."""
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            _show_status(mock_memory_manager)

        output = mock_stdout.getvalue()
        assert "Memory System Health" in output
        assert "healthy" in output
        assert "System Enabled: Yes" in output
        assert "Auto Learning: Yes" in output

    def test_show_status_displays_agent_information(mock_memory_manager):
        """Test _show_status displays individual agent information."""
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            _show_status(mock_memory_manager)

        output = mock_stdout.getvalue()
        assert "engineer" in output
        assert "qa" in output
        assert "75%" in output  # engineer utilization
        assert "50%" in output  # qa utilization
        assert "15 items" in output  # engineer items
        assert "10 items" in output  # qa items

    def test_show_status_handles_no_memory_directory():
        """Test _show_status handles missing memory directory."""
        manager = Mock(spec=AgentMemoryManager)
        manager.get_memory_status.return_value = {
            "success": True,
            "system_health": "no_memory_dir",
            "memory_directory": "/nonexistent",
            "system_enabled": True,
            "auto_learning": True,
            "total_agents": 0,
            "agents": {}
        }

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            _show_status(manager)

        output = mock_stdout.getvalue()
        assert "no_memory_dir" in output or "No memory" in output

    def test_show_basic_status_fallback():
        """Test _show_basic_status fallback functionality."""
        from claude_mpm.cli.commands.memory import _show_basic_status

        manager = Mock(spec=AgentMemoryManager)
        manager.memories_dir = Path("/test/memories")
        manager.memories_dir.exists.return_value = False

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            _show_basic_status(manager)

        output = mock_stdout.getvalue()
        assert "Basic Status" in output
        assert "not found" in output

    def test_show_memories_all_agents(mock_memory_manager):
        """Test _show_memories displays all agent memories."""
        mock_memory_manager.load_agent_memory.side_effect = lambda agent: f"# {agent} Memory\n- Test content"

        args = Namespace(agent=None, format="summary", raw=False)

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            _show_memories(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        assert "Agent Memories Display" in output

    def test_show_memories_single_agent(mock_memory_manager):
        """Test _show_memories displays single agent memory."""
        mock_memory_manager.load_agent_memory.return_value = "# Engineer Memory\n## Patterns\n- Test pattern"

        args = Namespace(agent="engineer", format="detailed", raw=False)

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            _show_memories(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        assert "Agent Memories Display" in output

    def test_show_memories_raw_output(mock_memory_manager):
        """Test _show_memories with raw JSON output."""
        mock_memory_manager.load_agent_memory.return_value = "# Test Memory"

        args = Namespace(agent="engineer", format="summary", raw=True)

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            _show_memories(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        # Should output JSON format
        try:
            json.loads(output)
            json_valid = True
        except:
            json_valid = False
        assert json_valid

    def test_parse_memory_content_extracts_sections():
        """Test _parse_memory_content extracts memory sections correctly."""
        memory_content = """# Agent Memory

## Coding Patterns Learned
- Use dependency injection
- Follow SOLID principles

## Implementation Guidelines
- Write unit tests first
- Use meaningful variable names

## Common Mistakes to Avoid
- Don't ignore error handling
"""

        sections = _parse_memory_content(memory_content)

        assert "Coding Patterns Learned" in sections
        assert "Implementation Guidelines" in sections
        assert "Common Mistakes to Avoid" in sections

        assert len(sections["Coding Patterns Learned"]) == 2
        assert len(sections["Implementation Guidelines"]) == 2
        assert len(sections["Common Mistakes to Avoid"]) == 1

        assert "Use dependency injection" in sections["Coding Patterns Learned"]
        assert "Write unit tests first" in sections["Implementation Guidelines"]

    def test_parse_memory_content_handles_empty_sections():
        """Test _parse_memory_content handles empty sections."""
        memory_content = """# Agent Memory

## Empty Section

## Section With Content
- Some content
"""

        sections = _parse_memory_content(memory_content)

        assert "Empty Section" in sections
        assert "Section With Content" in sections
        assert len(sections["Empty Section"]) == 0
        assert len(sections["Section With Content"]) == 1


class TestMemoryUtilitiesAndRouting:
    """Test memory command utilities and routing functions."""

    @pytest.fixture
    def mock_memory_manager(self):
        """Create mock memory manager."""
        manager = Mock(spec=AgentMemoryManager)
        manager.add_learning.return_value = True
        manager.update_agent_memory.return_value = True
        return manager

    def test_add_learning_with_valid_parameters(mock_memory_manager):
        """Test _add_learning with valid parameters."""
        args = Namespace(
            agent="engineer",
            learning_type="pattern",
            content="Use factory pattern for object creation"
        )

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            _add_learning(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        assert "Added learning" in output or "Learning added" in output
        mock_memory_manager.add_learning.assert_called_once_with(
            "engineer", "pattern", "Use factory pattern for object creation"
        )

    def test_add_learning_handles_failure(mock_memory_manager):
        """Test _add_learning handles failure gracefully."""
        mock_memory_manager.add_learning.return_value = False

        args = Namespace(
            agent="engineer",
            learning_type="pattern",
            content="Test content"
        )

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            _add_learning(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        assert "Failed" in output or "Error" in output

    def test_init_memory_displays_instructions(mock_memory_manager):
        """Test _init_memory displays initialization instructions."""
        args = Namespace()

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            _init_memory(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        assert "Memory Initialization Task" in output
        assert "claude-mpm memory add" in output
        assert "Example commands" in output

    def test_clean_memory_shows_cleanup_info(mock_memory_manager):
        """Test _clean_memory shows cleanup information."""
        mock_memory_manager.memories_dir = Path("/test/memories")
        mock_memory_manager.memories_dir.exists.return_value = True

        args = Namespace()

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            _clean_memory(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        assert "Memory cleanup" in output

    def test_clean_memory_handles_no_directory(mock_memory_manager):
        """Test _clean_memory handles missing memory directory."""
        mock_memory_manager.memories_dir = Path("/nonexistent")
        mock_memory_manager.memories_dir.exists.return_value = False

        args = Namespace()

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            _clean_memory(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        assert "No memory directory" in output or "nothing to clean" in output

    def test_build_memory_displays_build_info(mock_memory_manager):
        """Test _build_memory displays build information."""
        args = Namespace()

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            _build_memory(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        assert "Memory building" in output or "Build memory" in output

    def test_optimize_memory_displays_optimization_info(mock_memory_manager):
        """Test _optimize_memory displays optimization information."""
        args = Namespace(agent=None)

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            _optimize_memory(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        assert "Memory optimization" in output or "Optimize memory" in output

    def test_route_memory_command_displays_routing_info(mock_memory_manager):
        """Test _route_memory_command displays routing information."""
        args = Namespace(command="test command")

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            _route_memory_subcommand(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        assert "Memory command routing" in output or "Route command" in output

    def test_cross_reference_memory_displays_cross_ref_info(mock_memory_manager):
        """Test _cross_reference_memory displays cross-reference information."""
        args = Namespace()

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            _cross_reference_memory(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        assert "Cross-reference" in output or "Memory cross" in output

    def test_manage_memory_function_calls_command():
        """Test manage_memory function calls MemoryManagementCommand."""
        args = Namespace(memory_command="status", format="text")

        with patch('claude_mpm.cli.commands.memory.MemoryManagementCommand') as mock_command_class:
            mock_command = Mock()
            mock_result = Mock()
            mock_result.exit_code = 0
            mock_command.execute.return_value = mock_result
            mock_command_class.return_value = mock_command

            exit_code = manage_memory(args)

            assert exit_code == 0
            mock_command.execute.assert_called_once_with(args)

    def test_manage_memory_backward_compatibility():
        """Test manage_memory maintains backward compatibility."""
        args = Namespace(memory_command="status", format="text")

        with patch('claude_mpm.cli.commands.memory.MemoryManagementCommand') as mock_command_class:
            mock_command = Mock()
            mock_result = Mock()
            mock_result.exit_code = 0
            mock_command.execute.return_value = mock_result
            mock_command_class.return_value = mock_command

            exit_code = manage_memory(args)

            # Should return exit code
            assert exit_code == 0
            mock_command.execute.assert_called_once_with(args)

    def test_output_single_agent_raw_json_format(mock_memory_manager):
        """Test _output_single_agent_raw outputs valid JSON."""
        mock_memory_manager.load_agent_memory.return_value = "# Test Memory\n- Test item"

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            _output_single_agent_raw("engineer", mock_memory_manager)

        output = mock_stdout.getvalue()

        # Should be valid JSON
        try:
            data = json.loads(output)
            assert "agent_id" in data
            assert "memory_content" in data
            assert data["agent_id"] == "engineer"
        except json.JSONDecodeError:
            pytest.fail("Output is not valid JSON")

    def test_output_all_memories_raw_json_format(mock_memory_manager):
        """Test _output_all_memories_raw outputs valid JSON."""
        mock_memory_manager.memories_dir = Path("/test/memories")
        mock_memory_manager.memories_dir.exists.return_value = True

        # Mock glob to return test files
        mock_file1 = Mock()
        mock_file1.is_file.return_value = True
        mock_file1.stem = "engineer_memories"

        mock_file2 = Mock()
        mock_file2.is_file.return_value = True
        mock_file2.stem = "qa_memories"

        mock_memory_manager.memories_dir.glob.return_value = [mock_file1, mock_file2]
        mock_memory_manager.load_agent_memory.side_effect = lambda agent: f"# {agent} Memory"

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            _output_all_memories_raw(mock_memory_manager)

        output = mock_stdout.getvalue()

        # Should be valid JSON
        try:
            data = json.loads(output)
            assert "agents" in data
            assert "timestamp" in data
            assert isinstance(data["agents"], dict)
        except json.JSONDecodeError:
            pytest.fail("Output is not valid JSON")

    @patch("claude_mpm.cli.commands.memory.AgentMemoryManager")
    @patch("claude_mpm.cli.commands.memory.Config")
    def test_execute_memory_command_status(mock_config_class, mock_manager_class):
        """Test executing memory status command."""
        # Setup mocks
        mock_config = Mock()
        mock_config_class.return_value = mock_config

        mock_manager = Mock()
        mock_manager.get_memory_status.return_value = {
            "total_agents": 2,
            "total_memories": 3,
            "memory_size_kb": 100,
        }
        mock_manager_class.return_value = mock_manager

        args = Namespace(memory_command="status")

        # Capture output
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = execute_memory_subcommand(args)

        # Verify
        assert result is None  # Success returns None
        output = mock_stdout.getvalue()
        assert "Memory Status" in output
        assert "2 agents" in output
        assert "3 memories" in output

    @patch("claude_mpm.cli.commands.memory.AgentMemoryManager")
    @patch("claude_mpm.cli.commands.memory.Config")
    def test_execute_memory_command_no_subcommand(
        self, mock_config_class, mock_manager_class
    ):
        """Test executing memory command without subcommand shows status."""
        # Setup mocks
        mock_config = Mock()
        mock_config_class.return_value = mock_config

        mock_manager = Mock()
        mock_manager.get_memory_status.return_value = {
            "total_agents": 1,
            "total_memories": 1,
            "memory_size_kb": 50,
        }
        mock_manager_class.return_value = mock_manager

        args = Namespace(memory_command=None)

        # Capture output
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = execute_memory_subcommand(args)

        # Verify
        assert result is None
        output = mock_stdout.getvalue()
        assert "Memory Status" in output

    @patch("claude_mpm.cli.commands.memory.AgentMemoryManager")
    @patch("claude_mpm.cli.commands.memory.Config")
    def test_execute_memory_command_unknown(
        self, mock_config_class, mock_manager_class
    ):
        """Test executing unknown memory command."""
        # Setup mocks
        mock_config = Mock()
        mock_config_class.return_value = mock_config

        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager

        args = Namespace(memory_command="unknown_command")

        # Capture output
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = execute_memory_subcommand(args)

        # Verify
        assert result == 1  # Error return code
        output = mock_stdout.getvalue()
        assert "Unknown memory command" in output
        assert "unknown_command" in output


class TestMemoryStatusCommand:
    """Test memory status command functionality."""

    def test_show_status_with_data(mock_memory_manager):
        """Test showing status with memory data."""
        mock_memory_manager.get_memory_status.return_value = {
            "total_agents": 5,
            "total_memories": 8,
            "memory_size_kb": 250,
            "agents_with_memory": ["engineer", "qa", "research"],
            "largest_memory_agent": "engineer",
            "largest_memory_size_kb": 100,
        }

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _show_status(mock_memory_manager)

        output = mock_stdout.getvalue()
        assert "Memory Status" in output
        assert "5 agents" in output
        assert "8 memories" in output
        assert "250 KB" in output
        assert "engineer" in output

    def test_show_status_no_data(mock_memory_manager):
        """Test showing status with no memory data."""
        mock_memory_manager.get_memory_status.return_value = {
            "total_agents": 0,
            "total_memories": 0,
            "memory_size_kb": 0,
        }

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _show_status(mock_memory_manager)

        output = mock_stdout.getvalue()
        assert "Memory Status" in output
        assert "0 agents" in output
        assert "0 memories" in output

    def test_show_status_error_handling(mock_memory_manager):
        """Test status command error handling."""
        mock_memory_manager.get_memory_status.side_effect = Exception("Status error")

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _show_status(mock_memory_manager)

        output = mock_stdout.getvalue()
        assert "Error" in output or "status error" in output.lower()


class TestMemoryViewCommand:
    """Test memory view command functionality."""

    def test_view_memory_success(mock_memory_manager):
        """Test viewing memory content successfully."""
        mock_memory_manager.load_agent_memory.return_value = (
            "# Engineer Memory\n## Patterns\n- Use dependency injection"
        )

        args = Namespace(agent_id="engineer")

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _view_memory(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        assert "Memory for agent: engineer" in output
        assert "Use dependency injection" in output

    def test_view_memory_not_found(mock_memory_manager):
        """Test viewing memory when agent has no memory."""
        mock_memory_manager.load_agent_memory.return_value = None

        args = Namespace(agent_id="nonexistent")

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _view_memory(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        assert "No memory found for agent: nonexistent" in output

    def test_view_memory_file_not_found(mock_memory_manager):
        """Test viewing memory when file doesn't exist."""
        mock_memory_manager.load_agent_memory.side_effect = FileNotFoundError(
            "File not found"
        )

        args = Namespace(agent_id="missing")

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _view_memory(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        assert "No memory file found for agent: missing" in output

    def test_view_memory_error_handling(mock_memory_manager):
        """Test view memory error handling."""
        mock_memory_manager.load_agent_memory.side_effect = Exception("Read error")

        args = Namespace(agent_id="error_agent")

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _view_memory(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        assert "Error viewing memory" in output


class TestMemoryAddCommand:
    """Test memory add command functionality."""

    def test_add_learning_success(mock_memory_manager):
        """Test adding learning successfully."""
        mock_memory_manager.add_learning.return_value = True

        args = Namespace(
            agent_id="engineer",
            learning_type="pattern",
            content="Use factory pattern for object creation",
        )

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _add_learning(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        assert "Learning added successfully" in output

        # Verify the method was called with correct arguments
        mock_memory_manager.add_learning.assert_called_once_with(
            "engineer", "pattern", "Use factory pattern for object creation"
        )

    def test_add_learning_failure(mock_memory_manager):
        """Test adding learning when it fails."""
        mock_memory_manager.add_learning.return_value = False

        args = Namespace(
            agent_id="engineer", learning_type="pattern", content="Test pattern"
        )

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _add_learning(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        assert "Failed to add learning" in output

    def test_add_learning_error_handling(mock_memory_manager):
        """Test add learning error handling."""
        mock_memory_manager.add_learning.side_effect = Exception("Add error")

        args = Namespace(
            agent_id="engineer", learning_type="pattern", content="Test pattern"
        )

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _add_learning(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        assert "Error adding learning" in output


class TestMemoryCleanCommand:
    """Test memory clean command functionality."""

    def test_clean_memory_with_files(mock_memory_manager):
        """Test cleaning memory when files exist."""
        # Mock memory directory with files
        mock_memory_manager.memories_dir = Path("/test/memories")

        with patch("pathlib.Path.exists", return_value=True), patch(
            "pathlib.Path.glob",
            return_value=[
                Path("/test/memories/engineer_agent.md"),
                Path("/test/memories/qa_agent.md"),
            ],
        ), patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            args = Namespace()
            _clean_memory(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        assert "Memory cleanup" in output
        assert "2 memory files found" in output

    def test_clean_memory_no_directory(mock_memory_manager):
        """Test cleaning memory when directory doesn't exist."""
        mock_memory_manager.memories_dir = Path("/test/nonexistent")

        with patch("pathlib.Path.exists", return_value=False), patch(
            "sys.stdout", new_callable=StringIO
        ) as mock_stdout:
            args = Namespace()
            _clean_memory(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        assert "No memory directory found" in output

    def test_clean_memory_no_files(mock_memory_manager):
        """Test cleaning memory when no files exist."""
        mock_memory_manager.memories_dir = Path("/test/memories")

        with patch("pathlib.Path.exists", return_value=True), patch(
            "pathlib.Path.glob", return_value=[]
        ), patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            args = Namespace()
            _clean_memory(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        assert "No memory files found" in output


class TestMemoryBuildCommand:
    """Test memory build command functionality."""

    def test_build_memory_success(mock_memory_manager):
        """Test building memory from documentation successfully."""
        mock_memory_manager.build_memories_from_docs.return_value = {
            "success": True,
            "agents_updated": ["engineer", "qa"],
            "patterns_extracted": 15,
            "total_learnings": 25,
        }

        args = Namespace(force_rebuild=False)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _build_memory(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        assert "Memory Building from Documentation" in output
        assert "2 agents updated" in output
        assert "15 patterns extracted" in output
        assert "25 total learnings" in output

    def test_build_memory_with_force_rebuild(mock_memory_manager):
        """Test building memory with force rebuild flag."""
        mock_memory_manager.build_memories_from_docs.return_value = {
            "success": True,
            "agents_updated": ["engineer"],
            "patterns_extracted": 5,
            "total_learnings": 10,
        }

        args = Namespace(force_rebuild=True)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _build_memory(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        assert "Memory Building from Documentation" in output

        # Verify force_rebuild was passed
        mock_memory_manager.build_memories_from_docs.assert_called_once_with(True)

    def test_build_memory_failure(mock_memory_manager):
        """Test building memory when it fails."""
        mock_memory_manager.build_memories_from_docs.return_value = {
            "success": False,
            "error": "No documentation found",
        }

        args = Namespace(force_rebuild=False)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _build_memory(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        assert "Failed to build memories" in output
        assert "No documentation found" in output

    def test_build_memory_error_handling(mock_memory_manager):
        """Test build memory error handling."""
        mock_memory_manager.build_memories_from_docs.side_effect = Exception(
            "Build error"
        )

        args = Namespace(force_rebuild=False)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _build_memory(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        assert "Error building memories" in output


class TestMemoryShowCommand:
    """Test memory show command functionality."""

    def test_show_memories_single_agent(mock_memory_manager):
        """Test showing memories for a single agent."""
        mock_memory_manager.load_agent_memory.return_value = """# Engineer Memory
## Patterns
- Use dependency injection
- Follow SOLID principles
## Context
- Project uses microservices
## Recent Learnings
- New testing framework adopted"""

        args = Namespace(agent_id="engineer", format="detailed", raw=False)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _show_memories(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        assert "Agent: engineer" in output
        assert "Patterns" in output
        assert "dependency injection" in output

    def test_show_memories_all_agents_summary(mock_memory_manager):
        """Test showing memories for all agents in summary format."""
        mock_memory_manager.memories_dir = Path("/test/memories")

        with patch("pathlib.Path.exists", return_value=True), patch(
            "pathlib.Path.glob",
            return_value=[
                Path("/test/memories/engineer_agent.md"),
                Path("/test/memories/qa_agent.md"),
            ],
        ), patch.object(
            mock_memory_manager,
            "load_agent_memory",
            side_effect=[
                "# Engineer\n## Patterns\n- Pattern 1\n- Pattern 2",
                "# QA\n## Context\n- Context 1",
            ],
        ), patch(
            "sys.stdout", new_callable=StringIO
        ) as mock_stdout:
            args = Namespace(agent_id=None, format="summary", raw=False)
            _show_memories(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        assert "Found memories for 2 agents" in output
        assert "engineer" in output
        assert "qa" in output

    def test_show_memories_raw_output_single(mock_memory_manager):
        """Test showing single agent memory in raw JSON format."""
        mock_memory_manager.get_agent_memory_raw.return_value = {
            "agent_id": "engineer",
            "sections": {
                "patterns": ["Pattern 1", "Pattern 2"],
                "context": ["Context 1"],
            },
            "metadata": {"last_updated": "2024-01-01T00:00:00Z", "total_items": 3},
        }

        args = Namespace(agent_id="engineer", raw=True)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _show_memories(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        data = json.loads(output)
        assert data["agent_id"] == "engineer"
        assert "patterns" in data["sections"]
        assert len(data["sections"]["patterns"]) == 2

    def test_show_memories_raw_output_all(mock_memory_manager):
        """Test showing all agent memories in raw JSON format."""
        mock_memory_manager.get_all_memories_raw.return_value = {
            "agents": {
                "engineer": {
                    "sections": {"patterns": ["Pattern 1"]},
                    "metadata": {"total_items": 1},
                },
                "qa": {
                    "sections": {"context": ["Context 1"]},
                    "metadata": {"total_items": 1},
                },
            },
            "summary": {"total_agents": 2, "total_items": 2},
        }

        args = Namespace(agent_id=None, raw=True)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _show_memories(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        data = json.loads(output)
        assert "agents" in data
        assert "engineer" in data["agents"]
        assert "qa" in data["agents"]
        assert data["summary"]["total_agents"] == 2

    def test_show_memories_error_handling_raw(mock_memory_manager):
        """Test show memories error handling in raw mode."""
        mock_memory_manager.get_agent_memory_raw.side_effect = Exception("Raw error")

        args = Namespace(agent_id="engineer", raw=True)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _show_memories(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        data = json.loads(output)
        assert data["success"] is False
        assert "Raw error" in data["error"]


class TestMemoryRouteCommand:
    """Test memory route command functionality."""

    def test_route_memory_command_success(mock_memory_manager):
        """Test routing memory command successfully."""
        mock_memory_manager.route_memory_command.return_value = {
            "success": True,
            "target_agent": "engineer",
            "section": "patterns",
            "confidence": 0.85,
            "reasoning": "Content mentions design patterns and code structure",
        }

        args = Namespace(content="Use factory pattern for object creation")

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _route_memory_subcommand(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        assert "Memory Command Routing Test" in output
        assert "Target Agent: engineer" in output
        assert "Section: patterns" in output
        assert "Confidence: 0.85" in output
        assert "design patterns" in output

    def test_route_memory_command_no_content(mock_memory_manager):
        """Test routing memory command without content."""
        args = Namespace(content=None)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _route_memory_subcommand(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        assert "No content provided for routing analysis" in output
        assert "Usage: memory route --content" in output

    def test_route_memory_command_failure(mock_memory_manager):
        """Test routing memory command when routing fails."""
        mock_memory_manager.route_memory_command.return_value = {
            "success": False,
            "error": "Unable to determine target agent",
        }

        args = Namespace(content="Ambiguous content")

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _route_memory_subcommand(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        assert "Routing failed" in output
        assert "Unable to determine target agent" in output

    def test_route_memory_command_error_handling(mock_memory_manager):
        """Test route memory command error handling."""
        mock_memory_manager.route_memory_command.side_effect = Exception("Route error")

        args = Namespace(content="Test content")

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _route_memory_subcommand(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        assert "Error routing memory command" in output


class TestMemoryUtilityFunctions:
    """Test utility functions used by memory commands."""

    def test_parse_memory_content():
        """Test parsing memory content into sections."""
        content = """# Agent Memory
## Patterns
- Pattern 1
- Pattern 2

## Context
- Context item 1
- Context item 2

## Recent Learnings
- Learning 1"""

        sections = _parse_memory_content(content)

        assert "Patterns" in sections
        assert "Context" in sections
        assert "Recent Learnings" in sections
        assert len(sections["Patterns"]) == 2
        assert len(sections["Context"]) == 2
        assert len(sections["Recent Learnings"]) == 1
        assert "Pattern 1" in sections["Patterns"]

    def test_parse_memory_content_empty():
        """Test parsing empty memory content."""
        content = ""
        sections = _parse_memory_content(content)
        assert sections == {}

    def test_parse_memory_content_no_sections():
        """Test parsing memory content without sections."""
        content = "Just some text without sections"
        sections = _parse_memory_content(content)
        assert sections == {}