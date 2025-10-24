#!/usr/bin/env python3
"""
Unit tests for Memory File Operations.

Tests memory file operations and validation functionality.
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

    def test_memory_size_validation_within_limits(self):
        """Test memory size validation for content within limits."""
        # Create content under 80KB limit
        test_content = "# Test Memory\n" + "x" * 1000  # ~1KB

        is_valid, error_msg = self.validate_memory_size(test_content)

        assert is_valid is True
        assert error_msg is None

    def test_memory_size_validation_exceeds_limits(self):
        """Test memory size validation for content exceeding limits."""
        # Create content over 80KB limit
        test_content = "# Test Memory\n" + "x" * (85 * 1024)  # ~85KB

        is_valid, error_msg = self.validate_memory_size(test_content)

        assert is_valid is False
        assert error_msg is not None
        assert "exceeds" in error_msg.lower()

    def test_memory_directory_initialization(self, temp_dir):
        """Test memory directory is created with proper structure."""
        # Trigger directory creation by saving a memory
        self._save_memory_file("test", "# Test")

        memory_dir = temp_dir / ".claude-mpm" / "memories"
        assert memory_dir.exists()
        assert memory_dir.is_dir()

    def test_memory_file_naming_convention(self, temp_dir):
        """Test memory files follow correct naming convention."""
        test_agents = ["engineer", "qa", "research", "PM"]

        for agent in test_agents:
            self._save_memory_file(agent, f"# {agent} Memory")

            expected_file = (
                temp_dir / ".claude-mpm" / "memories" / f"{agent}_memories.md"
            )
            assert expected_file.exists()

    def test_memory_content_encoding(self, temp_dir):
        """Test memory files are saved with proper UTF-8 encoding."""
        # Test with unicode content
        unicode_content = "# Memory with Unicode\n- 测试 content\n- émoji: 🧠"

        success = self._save_memory_file("test", unicode_content)
        assert success is True

        # Read back and verify encoding
        memory_file = temp_dir / ".claude-mpm" / "memories" / "test_memories.md"
        read_content = memory_file.read_text(encoding="utf-8")
        assert read_content == unicode_content

    def test_memory_file_permissions(self, temp_dir):
        """Test memory files are created with appropriate permissions."""
        self._save_memory_file("test", "# Test")

        memory_file = temp_dir / ".claude-mpm" / "memories" / "test_memories.md"
        assert memory_file.exists()

        # File should be readable and writable by owner
        stat = memory_file.stat()
        assert stat.st_mode & 0o600  # Owner read/write permissions

    def test_concurrent_memory_access(self):
        """Test memory manager handles concurrent access gracefully."""
        import threading

        results = []
        errors = []

        def update_memory(agent_id, item_num):
            try:
                success = self.update_agent_memory(
                    agent_id, "Test Section", f"Test item {item_num}"
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

    def test_memory_backup_and_recovery(self, temp_dir):
        """Test memory content can be backed up and recovered."""
        # Create initial memory
        original_content = "# Original Memory\n- Important data"
        self._save_memory_file("engineer", original_content)

        # Simulate backup
        memory_file = temp_dir / ".claude-mpm" / "memories" / "engineer_memories.md"
        backup_content = memory_file.read_text()

        # Modify memory
        self._save_memory_file("engineer", "# Modified Memory")

        # Restore from backup
        self._save_memory_file("engineer", backup_content)

        # Verify restoration
        restored_content = self.load_agent_memory("engineer")
        assert restored_content == original_content

    def test_memory_file_corruption_handling(self, temp_dir):
        """Test handling of corrupted memory files."""
        # Create memory directory
        memory_dir = temp_dir / ".claude-mpm" / "memories"
        memory_dir.mkdir(parents=True)

        # Create corrupted file (binary data)
        corrupted_file = memory_dir / "engineer_memories.md"
        corrupted_file.write_bytes(b"\x00\x01\x02\x03\x04")

        # Loading should handle corruption gracefully
        result = self.load_agent_memory("engineer")

        # Should return default memory instead of crashing
        assert result is not None
        assert "# Engineer Agent Memory" in result


