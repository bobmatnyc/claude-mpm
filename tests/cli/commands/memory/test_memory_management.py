#!/usr/bin/env python3
"""
Unit tests for Memory Management Command.

Tests the main MemoryManagementCommand class and AgentMemoryManager functionality.
"""

import json
from argparse import Namespace
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from claude_mpm.cli.commands.memory import (
    MemoryManagementCommand,
    _build_memory,
    _cross_reference_memory,
    manage_memory,
)
from claude_mpm.cli.shared.base_command import CommandResult
from claude_mpm.services.agents.memory import AgentMemoryManager
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
                    "auto_learning": True,
                }
            },
        }
        manager.update_agent_memory.return_value = True
        manager.add_learning.return_value = True
        return manager

    @pytest.fixture
    def mock_config(self):
        """Create a mock Config."""
        return Mock(spec=Config)

    @pytest.fixture
    def memory_subcommand(self, mock_memory_manager):
        """Create MemoryManagementCommand instance with mocked dependencies."""
        with patch("claude_mpm.cli.commands.memory.ConfigLoader") as mock_loader, patch(
            "claude_mpm.cli.commands.memory.AgentMemoryManager"
        ) as mock_manager_class:

            mock_loader.return_value.load_main_config.return_value = Mock()
            mock_manager_class.return_value = mock_memory_manager

            return MemoryManagementCommand()

    def test_run_no_subcommand_shows_status(self):
        """Test that run() with no subcommand shows status."""
        args = Namespace(memory_command=None)

        result = self.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is True
        assert "status" in result.message.lower()

    def test_run_status_command(self):
        """Test run() with status command."""
        args = Namespace(memory_command="status", format="text")

        result = self.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is True
        assert "status" in result.message.lower()

    def test_run_init_command(self):
        """Test run() with init command."""
        args = Namespace(memory_command="init", format="text")

        result = self.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is True
        assert "initialization" in result.message.lower()

    def test_run_show_memories_command(self):
        """Test run() with show/view command."""
        args = Namespace(memory_command="show", format="text", agent=None)

        with patch("claude_mpm.cli.commands.memory._show_memories") as mock_show:
            result = self.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is True
        mock_show.assert_called_once()

    def test_run_add_learning_command(self):
        """Test run() with add command."""
        args = Namespace(
            memory_command="add",
            format="text",
            agent="engineer",
            learning_type="pattern",
            content="Use dependency injection",
        )

        with patch("claude_mpm.cli.commands.memory._add_learning") as mock_add:
            result = self.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is True
        mock_add.assert_called_once()

    def test_run_unknown_command_returns_error(self):
        """Test run() with unknown command returns error."""
        args = Namespace(memory_command="unknown_command")

        result = self.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is False
        assert "unknown" in result.message.lower() or "error" in result.message.lower()

    def test_get_status_data_no_memory_dir(self, mock_memory_manager):
        """Test _get_status_data when memory directory doesn't exist."""
        mock_memory_manager.memories_dir = Path("/nonexistent")

        status_data = self._get_status_data()

        assert status_data["exists"] is False
        assert status_data["agents"] == []
        assert status_data["total_size_kb"] == 0
        assert status_data["total_files"] == 0

    def test_get_status_data_with_memory_files(self, mock_memory_manager):
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

        status_data = self._get_status_data()

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

    def test_load_agent_memory_creates_default_when_missing(self):
        """Test load_agent_memory creates default memory when file doesn't exist."""
        result = self.load_agent_memory("engineer")

        assert result is not None
        assert "# Engineer Agent Memory" in result
        assert "## Coding Patterns Learned" in result
        assert "## Implementation Guidelines" in result

    def test_load_agent_memory_returns_existing_content(self, temp_dir):
        """Test load_agent_memory returns existing file content."""
        # Create memory directory and file
        memory_dir = temp_dir / ".claude-mpm" / "memories"
        memory_dir.mkdir(parents=True)

        test_content = "# Test Memory\n## Test Section\n- Test item"
        memory_file = memory_dir / "engineer_memories.md"
        memory_file.write_text(test_content)

        result = self.load_agent_memory("engineer")

        assert result == test_content

    def test_update_agent_memory_adds_new_item(self):
        """Test update_agent_memory adds new learning item."""
        success = self.update_agent_memory(
            "engineer", "Coding Patterns Learned", "Use dependency injection pattern"
        )

        assert success is True

        # Verify the item was added
        memory_content = self.load_agent_memory("engineer")
        assert "Use dependency injection pattern" in memory_content

    def test_add_learning_with_pattern_type(self):
        """Test add_learning with pattern learning type."""
        success = self.add_learning(
            "engineer", "pattern", "Always validate input parameters"
        )

        assert success is True

        # Verify it was added to correct section
        memory_content = self.load_agent_memory("engineer")
        assert "Always validate input parameters" in memory_content
        assert "## Coding Patterns Learned" in memory_content

    def test_add_learning_with_architecture_type(self):
        """Test add_learning with architecture learning type."""
        success = self.add_learning(
            "engineer", "architecture", "System uses microservices pattern"
        )

        assert success is True

        memory_content = self.load_agent_memory("engineer")
        assert "System uses microservices pattern" in memory_content
        assert "## Project Architecture" in memory_content

    def test_save_memory_file_creates_directory(self, temp_dir):
        """Test _save_memory_file creates directory if it doesn't exist."""
        test_content = "# Test Memory Content"

        success = self._save_memory_file("test_agent", test_content)

        assert success is True

        # Verify directory was created
        memory_dir = temp_dir / ".claude-mpm" / "memories"
        assert memory_dir.exists()

        # Verify file was created
        memory_file = memory_dir / "test_agent_memories.md"
        assert memory_file.exists()
        assert memory_file.read_text() == test_content

    def test_save_memory_file_handles_errors(self):
        """Test _save_memory_file handles write errors gracefully."""
        # Mock Path.write_text to raise an exception
        with patch.object(
            Path, "write_text", side_effect=PermissionError("Access denied")
        ):
            success = self._save_memory_file("test_agent", "content")

            assert success is False

    def test_get_memory_status_returns_comprehensive_data(self, temp_dir):
        """Test get_memory_status returns comprehensive status information."""
        # Create some test memory files
        memory_dir = temp_dir / ".claude-mpm" / "memories"
        memory_dir.mkdir(parents=True)

        (memory_dir / "engineer_memories.md").write_text(
            "# Engineer Memory\n" + "x" * 1000
        )
        (memory_dir / "qa_memories.md").write_text("# QA Memory\n" + "y" * 500)

        status = self.get_memory_status()

        assert status["system_enabled"] is True
        assert status["auto_learning"] is True
        assert "memory_directory" in status
        assert status["total_agents"] >= 0
        assert status["total_size_kb"] >= 0
        assert "system_health" in status

    def test_memory_file_migration_from_old_format(self, temp_dir):
        """Test migration from old memory file formats."""
        # Create memory directory
        memory_dir = temp_dir / ".claude-mpm" / "memories"
        memory_dir.mkdir(parents=True)

        # Create old format file
        old_content = "# Old Format Memory\n- Old learning item"
        old_file = memory_dir / "engineer_agent.md"
        old_file.write_text(old_content)

        # Load memory should trigger migration
        result = self.load_agent_memory("engineer")

        # Verify new format file exists
        new_file = memory_dir / "engineer_memories.md"
        assert new_file.exists()

        # Verify old file is removed
        assert not old_file.exists()

        # Verify content was migrated
        assert old_content in result


