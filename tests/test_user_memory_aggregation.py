#!/usr/bin/env python3
"""Tests for user-level memory support and aggregation."""

import unittest
from pathlib import Path
from unittest.mock import patch

from claude_mpm.core.framework_loader import FrameworkLoader
from claude_mpm.services.agents.memory.agent_memory_manager import AgentMemoryManager


class TestUserMemoryAggregation(unittest.TestCase):
    """Test user-level memory support and aggregation functionality."""

    def setUp(self):
        """Set up test environment."""
        self.test_user_dir = Path(tmp_path) / ".claude-mpm" / "memories"
        self.test_project_dir = Path(tmp_path) / ".claude-mpm" / "memories"
        self.test_user_dir.mkdir(parents=True, exist_ok=True)
        self.test_project_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        """Clean up test environment."""
        import shutil

        if self.test_user_dir.parent.parent.exists():
            shutil.rmtree(self.test_user_dir.parent.parent)
        if self.test_project_dir.parent.parent.exists():
            shutil.rmtree(self.test_project_dir.parent.parent)

    def test_memory_directory_creation():
        """Test that both user and project memory directories are created."""
        with patch.object(Path, "home", return_value=self.test_user_dir.parent.parent):
            with patch(
                "os.getcwd", return_value=str(self.test_project_dir.parent.parent)
            ):
                manager = AgentMemoryManager()

                # Check both directories exist
                self.assertTrue(manager.user_memories_dir.exists())
                self.assertTrue(manager.project_memories_dir.exists())

                # Check README files
                user_readme = manager.user_memories_dir / "README.md"
                project_readme = manager.project_memories_dir / "README.md"
                self.assertTrue(user_readme.exists())
                self.assertTrue(project_readme.exists())

    def test_memory_aggregation_both_exist():
        """Test memory aggregation when both user and project memories exist."""
        user_memory = """# Engineer Memory (User)

## Implementation Guidelines
- Always use type hints
- Follow SOLID principles

## Common Mistakes to Avoid
- Avoid premature optimization
"""

        project_memory = """# Engineer Memory (Project)

## Implementation Guidelines
- Use async/await for I/O operations
- Follow FastAPI conventions

## Project Architecture
- Microservices architecture
- REST API design
"""

        with patch.object(Path, "home", return_value=self.test_user_dir.parent.parent):
            with patch(
                "os.getcwd", return_value=str(self.test_project_dir.parent.parent)
            ):
                manager = AgentMemoryManager()

                # Write test memories
                (manager.user_memories_dir / "engineer_memories.md").write_text(
                    user_memory
                )
                (manager.project_memories_dir / "engineer_memories.md").write_text(
                    project_memory
                )

                # Load aggregated memory
                result = manager.load_agent_memory("engineer")

                # Check aggregation
                self.assertIn("type hints", result)  # From user
                self.assertIn("async/await", result)  # From project
                self.assertIn(
                    "Microservices architecture", result
                )  # Project-only section
                self.assertIn("Aggregated from user-level and project-level", result)

    def test_memory_aggregation_only_user():
        """Test memory loading when only user memory exists."""
        user_memory = """# Engineer Memory (User)

## Implementation Guidelines
- Always use type hints
- Follow SOLID principles
"""

        with patch.object(Path, "home", return_value=self.test_user_dir.parent.parent):
            with patch(
                "os.getcwd", return_value=str(self.test_project_dir.parent.parent)
            ):
                manager = AgentMemoryManager()

                # Write only user memory
                (manager.user_memories_dir / "engineer_memories.md").write_text(
                    user_memory
                )

                # Load memory
                result = manager.load_agent_memory("engineer")

                # Should return user memory as-is
                self.assertIn("type hints", result)
                self.assertIn("SOLID principles", result)

    def test_memory_aggregation_only_project():
        """Test memory loading when only project memory exists."""
        project_memory = """# Engineer Memory (Project)

## Project Architecture
- Microservices architecture
- REST API design
"""

        with patch.object(Path, "home", return_value=self.test_user_dir.parent.parent):
            with patch(
                "os.getcwd", return_value=str(self.test_project_dir.parent.parent)
            ):
                manager = AgentMemoryManager()

                # Write only project memory
                (manager.project_memories_dir / "engineer_memories.md").write_text(
                    project_memory
                )

                # Load memory
                result = manager.load_agent_memory("engineer")

                # Should return project memory as-is
                self.assertIn("Microservices architecture", result)
                self.assertIn("REST API design", result)

    def test_memory_section_merging():
        """Test that duplicate sections are properly merged."""
        user_memory = """# Engineer Memory (User)

## Implementation Guidelines
- Item A
- Item B

## Common Section
- User item 1
- User item 2
"""

        project_memory = """# Engineer Memory (Project)

## Implementation Guidelines
- Item C
- Item D

## Common Section
- Project item 1
- User item 2
"""

        with patch.object(Path, "home", return_value=self.test_user_dir.parent.parent):
            with patch(
                "os.getcwd", return_value=str(self.test_project_dir.parent.parent)
            ):
                manager = AgentMemoryManager()

                # Write test memories
                (manager.user_memories_dir / "engineer_memories.md").write_text(
                    user_memory
                )
                (manager.project_memories_dir / "engineer_memories.md").write_text(
                    project_memory
                )

                # Load aggregated memory
                result = manager.load_agent_memory("engineer")

                # Check all items are present
                self.assertIn("Item A", result)
                self.assertIn("Item B", result)
                self.assertIn("Item C", result)
                self.assertIn("Item D", result)
                self.assertIn("User item 1", result)
                self.assertIn("Project item 1", result)

                # Check no duplicates (User item 2 should appear only once)
                self.assertEqual(result.count("User item 2"), 1)

    def test_framework_loader_memory_loading():
        """Test that FrameworkLoader properly loads memories from both directories."""
        with patch.object(Path, "home", return_value=self.test_user_dir.parent.parent):
            with patch.object(
                Path, "cwd", return_value=self.test_project_dir.parent.parent
            ):
                # Create test PM memories
                user_pm = self.test_user_dir / "PM_memories.md"
                user_pm.parent.mkdir(parents=True, exist_ok=True)
                user_pm.write_text("## User Section\n- User content")

                project_pm = self.test_project_dir / "PM_memories.md"
                project_pm.parent.mkdir(parents=True, exist_ok=True)
                project_pm.write_text("## Project Section\n- Project content")

                # Create loader and load content
                loader = FrameworkLoader()

                # Mock the _get_deployed_agents to return empty set
                with patch.object(loader, "_get_deployed_agents", return_value=set()):
                    content = {}
                    loader._load_actual_memories(content)

                    # Check that memories were aggregated
                    self.assertIn("actual_memories", content)
                    self.assertIn("Aggregated Memory", content["actual_memories"])
                    self.assertIn("User content", content["actual_memories"])
                    self.assertIn("Project content", content["actual_memories"])

    def test_save_memory_to_user_directory():
        """Test saving memory to user directory explicitly."""
        with patch.object(Path, "home", return_value=self.test_user_dir.parent.parent):
            with patch(
                "os.getcwd", return_value=str(self.test_project_dir.parent.parent)
            ):
                manager = AgentMemoryManager()

                test_content = "# Test Memory\n## Section\n- Item"

                # Save to user directory
                success = manager._save_memory_file(
                    "test_agent", test_content, save_to_user=True
                )
                self.assertTrue(success)

                # Check file exists in user directory with new naming convention
                user_file = manager.user_memories_dir / "test_agent_memories.md"
                self.assertTrue(user_file.exists())
                self.assertEqual(user_file.read_text(), test_content)

                # Check file doesn't exist in project directory
                project_file = manager.project_memories_dir / "test_agent_memories.md"
                self.assertFalse(project_file.exists())

    def test_save_memory_to_project_directory():
        """Test saving memory to project directory (default)."""
        with patch.object(Path, "home", return_value=self.test_user_dir.parent.parent):
            with patch(
                "os.getcwd", return_value=str(self.test_project_dir.parent.parent)
            ):
                manager = AgentMemoryManager()

                test_content = "# Test Memory\n## Section\n- Item"

                # Save to project directory (default)
                success = manager._save_memory_file("test_agent", test_content)
                self.assertTrue(success)

                # Check file exists in project directory with new naming convention
                project_file = manager.project_memories_dir / "test_agent_memories.md"
                self.assertTrue(project_file.exists())
                self.assertEqual(project_file.read_text(), test_content)

                # Check file doesn't exist in user directory
                user_file = manager.user_memories_dir / "test_agent_memories.md"
                self.assertFalse(user_file.exists())


if __name__ == "__main__":
    unittest.main()
