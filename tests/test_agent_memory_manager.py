#!/usr/bin/env python3
"""
Tests for AgentMemoryManager service.

Tests memory file operations, size limits, and learning capture.
"""

import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.services.agents.memory.agent_memory_manager import AgentMemoryManager


class TestAgentMemoryManager:
    """Test suite for AgentMemoryManager."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary project directory."""
        temp_dir = tmp_path
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def memory_manager(self, temp_project_dir):
        """Create a memory manager with mocked project root."""
        with patch("claude_mpm.utils.paths.get_path_manager") as mock_path_manager:
            # Setup the mock path manager
            mock_pm = MagicMock()
            mock_pm.get_project_root.return_value = temp_project_dir
            mock_path_manager.return_value = mock_pm

            # Create a config object with default memory settings
            config = MagicMock()
            config.get.return_value = {"memory": {"enabled": True, "max_size": 1000000}}
            return AgentMemoryManager(config)

    def test_initialization_creates_directory_structure(
        self, memory_manager, temp_project_dir
    ):
        """Test that initialization creates the required directory structure."""
        memories_dir = temp_project_dir / ".claude" / "memories"
        assert memories_dir.exists()
        assert memories_dir.is_dir()

        readme_file = memories_dir / "README.md"
        assert readme_file.exists()
        assert "Agent Memory System" in readme_file.read_text()

    def test_load_agent_memory_creates_default(self):
        """Test that loading non-existent memory creates default."""
        memory = self.load_agent_memory("test_agent")

        assert "Test Agent Memory" in memory
        assert "Project Architecture" in memory
        assert "Implementation Guidelines" in memory
        assert "Common Mistakes to Avoid" in memory
        assert "Current Technical Context" in memory

    def test_add_learning_to_existing_section(self):
        """Test adding learning to an existing section."""
        # Create initial memory
        self.load_agent_memory("engineer")

        # Add a pattern learning
        success = self.add_learning(
            "engineer", "pattern", "Use Factory pattern for object creation"
        )
        assert success

        # Verify it was added
        memory = self.load_agent_memory("engineer")
        assert "Factory pattern" in memory

    def test_add_learning_respects_item_limits(self):
        """Test that section item limits are enforced."""
        # First, load to see how many default items exist
        initial_memory = self.load_agent_memory("qa")

        # Count existing items in Common Mistakes section
        lines = initial_memory.split("\n")
        existing_count = 0
        in_mistakes_section = False
        for line in lines:
            if line.startswith("## Common Mistakes to Avoid"):
                in_mistakes_section = True
            elif line.startswith("## ") and in_mistakes_section:
                break
            elif in_mistakes_section and line.strip().startswith("- "):
                existing_count += 1

        # Add items to reach the limit
        items_to_add = 15 - existing_count
        for i in range(items_to_add):
            self.add_learning("qa", "mistake", f"Mistake number {i}")

        # Add one more - should remove the oldest
        self.add_learning("qa", "mistake", "New mistake that should replace oldest")

        # Verify total count is still 15
        memory = self.load_agent_memory("qa")
        lines = memory.split("\n")
        item_count = 0
        in_mistakes_section = False
        for line in lines:
            if line.startswith("## Common Mistakes to Avoid"):
                in_mistakes_section = True
            elif line.startswith("## ") and in_mistakes_section:
                break
            elif in_mistakes_section and line.strip().startswith("- "):
                item_count += 1

        assert item_count == 15, f"Expected 15 items, got {item_count}"
        assert "New mistake" in memory  # New one added

    def test_line_length_truncation(self):
        """Test that long lines are truncated."""
        long_content = "A" * 150  # Exceeds 120 char limit

        self.add_learning("research", "pattern", long_content)

        memory = self.load_agent_memory("research")
        # Should be truncated to 117 chars + "..."
        assert "AAA..." in memory
        assert (
            len(
                next(
                    line
                    for line in memory.split("\n")
                    if line.strip().startswith("- A")
                )
            )
            <= 122
        )  # "- " prefix

    def test_update_timestamp(self):
        """Test that timestamps are updated on changes."""
        # Create initial memory
        self.load_agent_memory("security")

        # Add a learning
        self.add_learning("security", "guideline", "Always validate input")

        # Check timestamp was updated
        updated_memory = self.load_agent_memory("security")
        assert "<!-- Last Updated:" in updated_memory
        assert "Auto-updated by: system -->" in updated_memory

    def test_validate_and_repair_missing_sections(self):
        """Test that missing required sections are added during validation."""
        # Create a memory file with missing sections
        memory_file = self.memories_dir / "broken_agent.md"
        memory_file.write_text(
            """# Broken Agent Memory

## Some Random Section
- Item 1

## Recent Learnings
- Learning 1
"""
        )

        # Load should repair it
        memory = self.load_agent_memory("broken")

        # Check all required sections exist
        for section in self.REQUIRED_SECTIONS:
            assert f"## {section}" in memory

    def test_size_limit_enforcement(self):
        """Test that file size limits are enforced."""
        # Add many items to approach size limit
        for i in range(100):
            self.add_learning("data", "pattern", f"Pattern {i}: " + "X" * 80)

        # File should still exist and be under limit
        memory_file = self.memories_dir / "data_agent.md"
        assert memory_file.exists()

        file_size_kb = len(memory_file.read_bytes()) / 1024
        assert file_size_kb <= self.memory_limits["max_file_size_kb"]

    def test_error_handling_continues_operation(self):
        """Test that errors don't break the memory system."""
        # Mock a write error
        with patch.object(Path, "write_text", side_effect=OSError("Disk full")):
            # Should return False but not raise
            success = self.add_learning("ops", "mistake", "Some mistake")
            assert not success

        # Should still be able to read
        memory = self.load_agent_memory("ops")
        assert "Ops Agent Memory" in memory

    def test_learning_type_mapping(self):
        """Test that learning types map to correct sections."""
        mappings = [
            ("pattern", "Coding Patterns Learned"),
            ("architecture", "Project Architecture"),
            ("guideline", "Implementation Guidelines"),
            ("mistake", "Common Mistakes to Avoid"),
            ("strategy", "Effective Strategies"),
            ("integration", "Integration Points"),
            ("performance", "Performance Considerations"),
            ("domain", "Domain-Specific Knowledge"),
            ("context", "Current Technical Context"),
            ("unknown", "Recent Learnings"),  # Default
        ]

        for learning_type, expected_section in mappings:
            self.add_learning("test", learning_type, f"Test {learning_type} content")

        memory = self.load_agent_memory("test")

        # Verify each learning went to correct section
        lines = memory.split("\n")
        for learning_type, expected_section in mappings:
            # Find section
            section_idx = None
            for i, line in enumerate(lines):
                if line.startswith(f"## {expected_section}"):
                    section_idx = i
                    break

            assert section_idx is not None, f"Section {expected_section} not found"

            # Check content exists after section
            found = False
            for i in range(section_idx + 1, len(lines)):
                if lines[i].startswith("## "):
                    break
                if f"Test {learning_type} content" in lines[i]:
                    found = True
                    break

            assert found, f"Content for {learning_type} not found in {expected_section}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
