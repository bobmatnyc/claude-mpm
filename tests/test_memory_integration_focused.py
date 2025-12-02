#!/usr/bin/env python3
"""
Focused integration test for memory extraction system verification.
Tests the actual functioning of memory extraction from agent responses.
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from claude_mpm.services.agents.memory.agent_memory_manager import AgentMemoryManager


class TestMemoryIntegrationFocused(unittest.TestCase):
    """Focused integration tests for memory system verification."""

    def setUp(self):
        """Set up test environment with temporary directory."""
        self.temp_dir = tmp_path
        self.working_dir = Path(self.temp_dir)

        # Mock configuration
        config_data = {
            "memory": {
                "enabled": True,
                "auto_learning": True,
                "limits": {
                    "default_size_kb": 50,
                    "max_sections": 10,
                    "max_items_per_section": 20,
                },
            }
        }

        # Create mock config instance
        mock_config = MagicMock()
        mock_config.config_data = config_data
        mock_config.get.side_effect = lambda key, default=None: self._get_nested_config(
            config_data, key, default
        )

        # Create memory manager with config and working directory
        self.memory_manager = AgentMemoryManager(
            config=mock_config, working_directory=self.working_dir
        )

    def _get_nested_config(self, config_data, key, default=None):
        """Helper to get nested config values like memory.enabled."""
        keys = key.split(".")
        current = config_data
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        return current

    def tearDown(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_simple_remember_field_extraction():
        """Test extraction from simple remember field in JSON response."""
        response = """
        Task completed successfully.

        ```json
        {
          "remember": ["This project uses Python 3.11", "Database is PostgreSQL"]
        }
        ```
        """

        result = self.memory_manager.extract_and_update_memory("test_agent", response)

        # Should return True indicating successful extraction
        self.assertTrue(result, "Simple remember field extraction should succeed")

        # Check memory file was created
        memory_file = self.working_dir / ".claude-mpm" / "memories" / "test_agent.md"
        self.assertTrue(memory_file.exists(), "Memory file should be created")

        # Check content was extracted
        content = memory_file.read_text()
        self.assertIn("Python 3.11", content)
        self.assertIn("PostgreSQL", content)

    def test_capital_remember_field_extraction():
        """Test extraction from Remember field (capital R) in JSON response."""
        response = """
        Analysis complete.

        ```json
        {
          "Remember": ["API uses JWT authentication", "Rate limit is 1000 requests/hour"]
        }
        ```
        """

        result = self.memory_manager.extract_and_update_memory("test_agent2", response)

        # Should return True indicating successful extraction
        self.assertTrue(result, "Capital Remember field extraction should succeed")

        # Check memory file was created
        memory_file = self.working_dir / ".claude-mpm" / "memories" / "test_agent2.md"
        self.assertTrue(memory_file.exists(), "Memory file should be created")

        # Check content was extracted
        content = memory_file.read_text()
        self.assertIn("JWT authentication", content)
        self.assertIn("Rate limit", content)

    def test_null_remember_field_handling():
        """Test handling of null remember field."""
        response = """
        Task completed.

        ```json
        {
          "remember": null
        }
        ```
        """

        result = self.memory_manager.extract_and_update_memory("test_agent3", response)

        # Should return False for null remember field
        self.assertFalse(result, "Null remember field should return False")

        # Memory file should not be created
        memory_file = self.working_dir / ".claude-mpm" / "memories" / "test_agent3.md"
        self.assertFalse(
            memory_file.exists(), "Memory file should not be created for null remember"
        )

    def test_empty_list_remember_field_handling():
        """Test handling of empty list remember field."""
        response = """
        Task completed.

        ```json
        {
          "remember": []
        }
        ```
        """

        result = self.memory_manager.extract_and_update_memory("test_agent4", response)

        # Should return False for empty list
        self.assertFalse(result, "Empty remember list should return False")

    def test_memory_update_structured_format_NOT_IMPLEMENTED():
        """Test extraction from memory-update structured format - EXPECTED TO FAIL."""
        response = """
        Task completed.

        ```json
        {
          "memory-update": {
            "Project Architecture": ["Uses service-oriented design", "Five specialized domains"],
            "Implementation Guidelines": ["Always use type hints", "Follow SOLID principles"]
          }
        }
        ```
        """

        result = self.memory_manager.extract_and_update_memory("engineer", response)

        # This should fail since memory-update format is not implemented
        self.assertFalse(result, "memory-update format should fail (not implemented)")

        # Memory file should not be created
        memory_file = self.working_dir / ".claude-mpm" / "memories" / "engineer.md"
        self.assertFalse(
            memory_file.exists(),
            "Memory file should not be created for unimplemented format",
        )

    def test_no_json_response_handling():
        """Test handling of response with no JSON."""
        response = """
        Task completed successfully.
        Everything looks good to go.
        No memory updates needed.
        """

        result = self.memory_manager.extract_and_update_memory("test_agent5", response)

        # Should return False for no JSON
        self.assertFalse(result, "Response with no JSON should return False")

    def test_invalid_json_handling():
        """Test handling of invalid JSON in response."""
        response = """
        Task completed.

        ```json
        {
          "remember": ["Valid entry"
          // Missing closing bracket
        ```
        """

        result = self.memory_manager.extract_and_update_memory("test_agent6", response)

        # Should return False for invalid JSON
        self.assertFalse(result, "Response with invalid JSON should return False")

    def test_multiple_json_blocks_processing():
        """Test processing multiple JSON blocks in one response."""
        response = """
        First task completed.

        ```json
        {
          "remember": ["First learning"]
        }
        ```

        Second task completed.

        ```json
        {
          "remember": ["Second learning"]
        }
        ```
        """

        result = self.memory_manager.extract_and_update_memory("test_agent7", response)

        # Should return True if any valid memory found
        self.assertTrue(result, "Multiple JSON blocks should be processed")

        # Check both learnings were captured
        memory_file = self.working_dir / ".claude-mpm" / "memories" / "test_agent7.md"
        self.assertTrue(memory_file.exists(), "Memory file should be created")

        content = memory_file.read_text()
        self.assertIn("First learning", content)
        self.assertIn("Second learning", content)

    def test_memory_file_format_consistency():
        """Test that memory files are created with consistent format."""
        response = """
        ```json
        {
          "remember": ["Test learning for format check"]
        }
        ```
        """

        result = self.memory_manager.extract_and_update_memory("format_test", response)
        self.assertTrue(result)

        memory_file = self.working_dir / ".claude-mpm" / "memories" / "format_test.md"
        content = memory_file.read_text()

        # Basic format checks
        self.assertIn("# format_test Agent Memory", content)
        self.assertIn("Test learning for format check", content)


if __name__ == "__main__":
    unittest.main()
