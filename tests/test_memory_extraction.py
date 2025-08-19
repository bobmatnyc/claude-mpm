#!/usr/bin/env python3
"""Test memory extraction from agent responses."""

import json
import tempfile
from pathlib import Path

import pytest

from claude_mpm.services.agents.memory.agent_memory_manager import AgentMemoryManager


class TestMemoryExtraction:
    """Test memory extraction and update functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.working_dir = Path(self.temp_dir)
        self.memory_manager = AgentMemoryManager(working_directory=self.working_dir)

    def test_extract_memory_from_json_block(self):
        """Test extracting memory from JSON block in response."""
        response = '''
        I've analyzed the codebase and found some important patterns.
        
        ```json
        {
          "task_completed": true,
          "remember": ["This project uses service-oriented architecture", "Memory files are in .claude-mpm/memories/"]
        }
        ```
        '''
        
        result = self.memory_manager.extract_and_update_memory("test_agent", response)
        assert result is True
        
        # Check memory was saved
        memory_file = self.working_dir / ".claude-mpm" / "memories" / "test_agent_memories.md"
        assert memory_file.exists()
        content = memory_file.read_text()
        assert "This project uses service-oriented architecture" in content
        assert "Memory files are in .claude-mpm/memories/" in content

    def test_extract_memory_update_dict_format_not_supported(self):
        """Test that old memory-update dict format is no longer supported."""
        response = '''
        Task completed successfully.
        
        ```json
        {
          "memory-update": {
            "Project Architecture": ["Uses 5 service domains", "Interface-based contracts"],
            "Implementation Guidelines": ["Always use type hints", "Follow SOLID principles"]
          }
        }
        ```
        '''
        
        result = self.memory_manager.extract_and_update_memory("engineer", response)
        # The old memory-update format should return False (not supported)
        assert result is False

    def test_extract_memory_capital_remember(self):
        """Test extracting Remember field (capital R)."""
        response = '''
        Analysis complete.
        
        ```json
        {
          "Remember": ["PyPI package name is claude-mpm", "Version tracked in VERSION file"]
        }
        ```
        '''
        
        result = self.memory_manager.extract_and_update_memory("ops", response)
        assert result is True
        
        memory_file = self.working_dir / ".claude-mpm" / "memories" / "ops_memories.md"
        assert memory_file.exists()
        content = memory_file.read_text()
        assert "PyPI package name is claude-mpm" in content

    def test_no_memory_update_returns_false(self):
        """Test that response without memory updates returns False."""
        response = '''
        Task completed.
        
        ```json
        {
          "task_completed": true,
          "results": "Fixed the bug"
        }
        ```
        '''
        
        result = self.memory_manager.extract_and_update_memory("qa", response)
        assert result is False

    def test_null_remember_field_returns_false(self):
        """Test that null remember field returns False."""
        response = '''
        Task done.
        
        ```json
        {
          "task_completed": true,
          "remember": null
        }
        ```
        '''
        
        result = self.memory_manager.extract_and_update_memory("qa", response)
        assert result is False

    def test_empty_remember_list_returns_false(self):
        """Test that empty remember list returns False."""
        response = '''
        Complete.
        
        ```json
        {
          "remember": []
        }
        ```
        '''
        
        result = self.memory_manager.extract_and_update_memory("research", response)
        assert result is False

    def test_replace_existing_memory(self):
        """Test that new memory updates add to existing memory (not replace entirely)."""
        # First update
        response1 = '''
        ```json
        {
          "remember": ["Old learning 1", "Old learning 2"]
        }
        ```
        '''
        self.memory_manager.extract_and_update_memory("test", response1)
        
        # Second update should add to existing (not replace)
        response2 = '''
        ```json
        {
          "remember": ["New architecture insight", "New context info"]
        }
        ```
        '''
        result = self.memory_manager.extract_and_update_memory("test", response2)
        assert result is True
        
        memory_file = self.working_dir / ".claude-mpm" / "memories" / "test_memories.md"
        content = memory_file.read_text()
        
        # New content should be present
        assert "New architecture insight" in content
        assert "New context info" in content
        
        # Old content should still be there (memory adds, doesn't replace)
        assert "Old learning 1" in content
        assert "Old learning 2" in content

    def test_memory_with_bullet_points(self):
        """Test that bullet points are handled correctly."""
        response = '''
        ```json
        {
          "remember": [
            "Use async/await for all I/O operations",
            "Follow PEP 8 conventions"
          ]
        }
        ```
        '''
        
        result = self.memory_manager.extract_and_update_memory("engineer", response)
        assert result is True
        
        memory_file = self.working_dir / ".claude-mpm" / "memories" / "engineer_memories.md"
        content = memory_file.read_text()
        
        # Memory manager automatically adds bullet points
        assert "- Use async/await for all I/O operations" in content
        assert "- Follow PEP 8 conventions" in content

    def test_invalid_json_ignored(self):
        """Test that invalid JSON is ignored."""
        response = '''
        ```json
        {
          "remember": ["Valid item"
          // Missing closing bracket
        ```
        '''
        
        result = self.memory_manager.extract_and_update_memory("test", response)
        assert result is False

    def test_multiple_json_blocks(self):
        """Test extracting from multiple JSON blocks (uses first valid one)."""
        response = '''
        First block:
        ```json
        {
          "task_completed": true
        }
        ```
        
        Second block with memory:
        ```json
        {
          "remember": ["Important learning from second block"]
        }
        ```
        '''
        
        result = self.memory_manager.extract_and_update_memory("test", response)
        assert result is True
        
        memory_file = self.working_dir / ".claude-mpm" / "memories" / "test_memories.md"
        content = memory_file.read_text()
        assert "Important learning from second block" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])