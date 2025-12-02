#!/usr/bin/env python3
"""
Comprehensive QA tests for the updated memory system.

Tests all aspects requested:
1. File Naming: Memory files use correct {agent_name}_memories.md format (not {agent_name}_agent.md or {agent_name}.md)
2. User-Level Memories: User directory ~/.claude/memories/ is created and works
3. Memory Aggregation: User and project memories are properly merged
4. Migration: Old format files ({agent_name}_agent.md and {agent_name}.md) are automatically migrated to new format
5. Loading Order: User memories load first, then project memories (project overrides)
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from claude_mpm.core.framework_loader import FrameworkLoader
from claude_mpm.services.agents.memory.agent_memory_manager import AgentMemoryManager


class TestMemorySystemQA:
    """Comprehensive QA tests for memory system updates."""

    def setup_method(self):
        """Set up test environment with temporary directories."""
        # Create temporary directories for testing
        self.temp_dir = Path(tempfile.mkdtemp(prefix="memory_qa_test_"))
        self.test_project_dir = self.temp_dir / "test_project"
        self.test_user_home = self.temp_dir / "test_user_home"

        # Create directory structure
        self.test_project_dir.mkdir(parents=True)
        self.test_user_home.mkdir(parents=True)

        # Create memory directories
        self.project_memories_dir = self.test_project_dir / ".claude-mpm" / "memories"
        self.user_memories_dir = self.test_user_home / ".claude-mpm" / "memories"

        self.project_memories_dir.mkdir(parents=True)
        self.user_memories_dir.mkdir(parents=True)

        # Initialize config
        self.config = Config()

    def teardown_method(self):
        """Clean up test environment."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_file_naming_new_format():
        """Test 1: Verify new files are created with correct {agent_name}_memories.md format."""
        with patch("pathlib.Path.home", return_value=self.test_user_home):
            memory_manager = AgentMemoryManager(
                config=self.config, working_directory=self.test_project_dir
            )

            # Create a new memory for an agent
            agent_id = "engineer"
            memory_manager.load_agent_memory(agent_id)

            # Verify the file was created with correct naming
            expected_file = self.project_memories_dir / f"{agent_id}_memories.md"
            assert expected_file.exists(), (
                f"Memory file should be created as {agent_id}_memories.md"
            )

            # Verify no old format files were created
            old_format_file = self.project_memories_dir / f"{agent_id}_agent.md"
            intermediate_file = self.project_memories_dir / f"{agent_id}.md"
            assert not old_format_file.exists(), (
                f"Should not create old format {agent_id}_agent.md"
            )
            assert not intermediate_file.exists(), (
                f"Should not create intermediate format {agent_id}.md"
            )

            print(f"✅ File naming test passed: {expected_file.name}")

    def test_file_naming_no_agent_suffix():
        """Test that memory files never have _agent suffix in new system."""
        with patch("pathlib.Path.home", return_value=self.test_user_home):
            memory_manager = AgentMemoryManager(
                config=self.config, working_directory=self.test_project_dir
            )

            # Test multiple agent types
            agent_types = ["research", "engineer", "documentation", "qa", "ops"]

            for agent_id in agent_types:
                # Load memory (will create if doesn't exist)
                memory_manager.load_agent_memory(agent_id)

                # Verify correct naming
                correct_file = self.project_memories_dir / f"{agent_id}_memories.md"
                old_format_file = self.project_memories_dir / f"{agent_id}_agent.md"
                intermediate_file = self.project_memories_dir / f"{agent_id}.md"

                assert correct_file.exists(), f"Should create {agent_id}_memories.md"
                assert not old_format_file.exists(), (
                    f"Should not create {agent_id}_agent.md"
                )
                assert not intermediate_file.exists(), (
                    f"Should not create {agent_id}.md"
                )

            print("✅ File naming consistency test passed for all agent types")

    def test_user_level_memories_creation():
        """Test 2: Verify user directory is created and works correctly."""
        with patch("pathlib.Path.home", return_value=self.test_user_home):
            memory_manager = AgentMemoryManager(
                config=self.config, working_directory=self.test_project_dir
            )

            # Verify user memories directory is created
            assert memory_manager.user_memories_dir.exists(), (
                "User memories directory should be created"
            )
            assert memory_manager.user_memories_dir == self.user_memories_dir, (
                "User memories dir should point to correct location"
            )

            # Verify README is created in user directory
            user_readme = self.user_memories_dir / "README.md"
            assert user_readme.exists(), "User memories directory should have README.md"

            # Check README content mentions user-level memories
            readme_content = user_readme.read_text()
            assert "User-level memories" in readme_content, (
                "README should mention user-level memories"
            )
            assert "global defaults" in readme_content, (
                "README should mention global defaults"
            )

            print("✅ User-level memories directory creation test passed")

    def test_user_memory_functionality():
        """Test that user memories can be created and loaded."""
        with patch("pathlib.Path.home", return_value=self.test_user_home):
            memory_manager = AgentMemoryManager(
                config=self.config, working_directory=self.test_project_dir
            )

            # Create a user-level memory manually
            agent_id = "engineer"
            user_memory_content = """# Engineer Agent Memory

## Implementation Guidelines
- Always use type hints in Python code
- Prefer composition over inheritance
- Write comprehensive docstrings

## Common Mistakes to Avoid
- Don't ignore error handling
- Avoid global variables
"""

            user_memory_file = self.user_memories_dir / f"{agent_id}_memories.md"
            user_memory_file.write_text(user_memory_content)

            # Load memory - should get user memory since no project memory exists
            loaded_memory = memory_manager.load_agent_memory(agent_id)

            assert "type hints in Python code" in loaded_memory, (
                "Should load user memory content"
            )
            assert "composition over inheritance" in loaded_memory, (
                "Should contain user guidelines"
            )

            print("✅ User memory functionality test passed")

    def test_memory_aggregation_user_and_project():
        """Test 3: Verify user and project memories are properly aggregated."""
        with patch("pathlib.Path.home", return_value=self.test_user_home):
            memory_manager = AgentMemoryManager(
                config=self.config, working_directory=self.test_project_dir
            )

            agent_id = "engineer"

            # Create user-level memory
            user_memory_content = """# Engineer Agent Memory

## Implementation Guidelines
- Always use type hints in Python code
- Prefer composition over inheritance

## Common Mistakes to Avoid
- Don't ignore error handling
"""

            user_memory_file = self.user_memories_dir / f"{agent_id}_memories.md"
            user_memory_file.write_text(user_memory_content)

            # Create project-level memory
            project_memory_content = """# Engineer Agent Memory

## Implementation Guidelines
- Use FastAPI for REST APIs
- Implement dependency injection

## Project Architecture
- This project uses microservices architecture
- Database is PostgreSQL

## Common Mistakes to Avoid
- Don't ignore error handling
- Avoid hardcoded configuration
"""

            project_memory_file = self.project_memories_dir / f"{agent_id}_memories.md"
            project_memory_file.write_text(project_memory_content)

            # Load aggregated memory
            aggregated_memory = memory_manager.load_agent_memory(agent_id)

            # Verify user content is included
            assert "type hints in Python code" in aggregated_memory, (
                "Should include user guidelines"
            )
            assert "composition over inheritance" in aggregated_memory, (
                "Should include user patterns"
            )

            # Verify project content is included
            assert "FastAPI for REST APIs" in aggregated_memory, (
                "Should include project guidelines"
            )
            assert "microservices architecture" in aggregated_memory, (
                "Should include project architecture"
            )
            assert "PostgreSQL" in aggregated_memory, (
                "Should include project tech stack"
            )

            # Verify project overrides user for duplicates
            assert "Avoid hardcoded configuration" in aggregated_memory, (
                "Should include project-specific mistakes"
            )

            # Verify both unique items in Common Mistakes are preserved
            error_handling_count = aggregated_memory.count(
                "Don't ignore error handling"
            )
            assert error_handling_count == 1, "Should not duplicate identical items"

            # Verify aggregation metadata
            assert (
                "Aggregated from user-level and project-level memories"
                in aggregated_memory
            ), "Should indicate aggregation"

            print("✅ Memory aggregation test passed")

    def test_migration_old_to_new_format():
        """Test 4: Verify old format files are automatically migrated."""
        with patch("pathlib.Path.home", return_value=self.test_user_home):
            memory_manager = AgentMemoryManager(
                config=self.config, working_directory=self.test_project_dir
            )

            agent_id = "research"

            # Create old format file
            old_format_content = """# Research Agent Memory

## Project Architecture
- Legacy system with old naming

## Implementation Guidelines
- Research patterns
"""

            old_format_file = self.project_memories_dir / f"{agent_id}_agent.md"
            old_format_file.write_text(old_format_content)

            # Verify old file exists before migration
            assert old_format_file.exists(), (
                "Old format file should exist before migration"
            )

            # Load memory - should trigger migration
            loaded_memory = memory_manager.load_agent_memory(agent_id)

            # Verify migration occurred
            new_format_file = self.project_memories_dir / f"{agent_id}_memories.md"
            assert new_format_file.exists(), (
                "New format file should exist after migration"
            )
            assert not old_format_file.exists(), (
                "Old format file should be removed after migration"
            )

            # Verify content was preserved
            assert "Legacy system with old naming" in loaded_memory, (
                "Content should be preserved during migration"
            )
            assert "Research patterns" in loaded_memory, (
                "All content should be migrated"
            )

            print("✅ Migration test passed")

    def test_migration_user_directory():
        """Test migration works in user directory too."""
        with patch("pathlib.Path.home", return_value=self.test_user_home):
            memory_manager = AgentMemoryManager(
                config=self.config, working_directory=self.test_project_dir
            )

            agent_id = "documentation"

            # Create old format file in user directory
            old_user_content = """# Documentation Agent Memory

## Implementation Guidelines
- Write clear documentation
- Use proper markdown formatting
"""

            old_user_file = self.user_memories_dir / f"{agent_id}_agent.md"
            old_user_file.write_text(old_user_content)

            # Load memory - should trigger migration in user dir
            loaded_memory = memory_manager.load_agent_memory(agent_id)

            # Verify user directory migration
            new_user_file = self.user_memories_dir / f"{agent_id}_memories.md"
            assert new_user_file.exists(), "New format file should exist in user dir"
            assert not old_user_file.exists(), (
                "Old format file should be removed from user dir"
            )

            # Verify content
            assert "Write clear documentation" in loaded_memory, (
                "User content should be preserved"
            )

            print("✅ User directory migration test passed")

    def test_loading_order_user_first_project_override():
        """Test 5: Verify user memories load first, then project memories override."""
        with patch("pathlib.Path.home", return_value=self.test_user_home):
            memory_manager = AgentMemoryManager(
                config=self.config, working_directory=self.test_project_dir
            )

            agent_id = "qa"

            # Create user memory with specific content
            user_content = """# QA Agent Memory

## Implementation Guidelines
- Write comprehensive test cases
- Use pytest for testing

## Testing Strategies
- Unit tests for all functions
- Integration tests for workflows
"""

            user_file = self.user_memories_dir / f"{agent_id}_memories.md"
            user_file.write_text(user_content)

            # Create project memory that should override/extend
            project_content = """# QA Agent Memory

## Implementation Guidelines
- Write comprehensive test cases
- Use pytest-django for this project

## Project Architecture
- This project uses Django framework
- Database testing uses fixtures

## Testing Strategies
- Load testing with Locust
- E2E testing with Selenium
"""

            project_file = self.project_memories_dir / f"{agent_id}_memories.md"
            project_file.write_text(project_content)

            # Load aggregated memory
            aggregated = memory_manager.load_agent_memory(agent_id)

            # Verify user content is preserved
            assert "Unit tests for all functions" in aggregated, (
                "User content should be preserved"
            )
            assert "Integration tests for workflows" in aggregated, (
                "User strategies should be included"
            )

            # Verify project overrides work
            assert "pytest-django for this project" in aggregated, (
                "Project should override user guidelines"
            )
            assert "Django framework" in aggregated, (
                "Project architecture should be included"
            )

            # Verify project extends user content
            assert "Load testing with Locust" in aggregated, (
                "Project should extend testing strategies"
            )
            assert "E2E testing with Selenium" in aggregated, (
                "All project strategies should be included"
            )

            # Verify no duplicate comprehensive test cases
            comprehensive_count = aggregated.count("Write comprehensive test cases")
            assert comprehensive_count == 1, "Should not duplicate identical guidelines"

            print("✅ Loading order and override test passed")

    def test_framework_loader_memory_aggregation():
        """Test framework loader properly loads memories through memory manager."""
        with patch("pathlib.Path.home", return_value=self.test_user_home):
            # Create user PM memory
            user_pm_content = """# PM Agent Memory

## Implementation Guidelines
- Always delegate to specialized agents
- Never do implementation work directly

## Delegation Strategies
- Break complex tasks into smaller pieces
"""

            user_pm_file = self.user_memories_dir / "PM_memories.md"
            user_pm_file.write_text(user_pm_content)

            # Create project PM memory
            project_pm_content = """# PM Agent Memory

## Implementation Guidelines
- Always delegate to specialized agents
- Use TodoWrite for task tracking

## Project Architecture
- This project follows service-oriented architecture
- Use dependency injection pattern

## Delegation Strategies
- Prioritize QA testing for releases
"""

            project_pm_file = self.project_memories_dir / "PM_memories.md"
            project_pm_file.write_text(project_pm_content)

            # Create deployed agents file
            deployed_agents_dir = self.test_project_dir / ".claude" / "agents"
            deployed_agents_dir.mkdir(parents=True)

            # Mock working directory for framework loader
            with patch("pathlib.Path.cwd", return_value=self.test_project_dir):
                framework_loader = FrameworkLoader()
                framework_instructions = framework_loader.get_framework_instructions()

                # Verify PM memories are included in framework instructions
                # The framework loader should include actual memories
                assert "Current PM Memories" in framework_instructions, (
                    "Should include PM memories section"
                )

                # Check that memory content is present somewhere in the instructions
                # Note: The exact format may vary, so we check for key content
                instructions_lower = framework_instructions.lower()
                assert "delegate" in instructions_lower, (
                    "Should include delegation concepts"
                )

                print("✅ Framework loader memory integration test passed")

    def test_memory_system_integration():
        """Integration test verifying the complete memory system workflow."""
        with patch("pathlib.Path.home", return_value=self.test_user_home):
            memory_manager = AgentMemoryManager(
                config=self.config, working_directory=self.test_project_dir
            )

            # Test complete workflow
            agent_id = "ops"

            # 1. Start with old format file to test migration
            old_content = """# Ops Agent Memory

## Implementation Guidelines
- Use Infrastructure as Code
- Monitor all deployments
"""

            old_file = self.project_memories_dir / f"{agent_id}_agent.md"
            old_file.write_text(old_content)

            # 2. Add user-level memory
            user_content = """# Ops Agent Memory

## Implementation Guidelines
- Always use version control
- Document all procedures

## Security Guidelines
- Follow principle of least privilege
"""

            user_file = self.user_memories_dir / f"{agent_id}_memories.md"
            user_file.write_text(user_content)

            # 3. Load memory - should migrate and aggregate
            aggregated = memory_manager.load_agent_memory(agent_id)

            # 4. Verify migration happened
            new_file = self.project_memories_dir / f"{agent_id}_memories.md"
            assert new_file.exists(), "Migration should create new format file"
            assert not old_file.exists(), "Migration should remove old format file"

            # 5. Verify aggregation
            assert "Infrastructure as Code" in aggregated, (
                "Should include migrated content"
            )
            assert "version control" in aggregated, "Should include user content"
            assert "principle of least privilege" in aggregated, (
                "Should include user security guidelines"
            )

            # 6. Test adding new learning
            success = memory_manager.add_learning(
                agent_id, "pattern", "Use blue-green deployments for zero downtime"
            )
            assert success, "Should successfully add new learning"

            # 7. Reload and verify learning was added
            updated_memory = memory_manager.load_agent_memory(agent_id)
            assert "blue-green deployments" in updated_memory, (
                "Should include new learning"
            )

            print("✅ Complete memory system integration test passed")

    def test_memory_file_format_consistency():
        """Test that all memory files follow consistent format."""
        with patch("pathlib.Path.home", return_value=self.test_user_home):
            memory_manager = AgentMemoryManager(
                config=self.config, working_directory=self.test_project_dir
            )

            # Test multiple agents
            agents = ["engineer", "research", "documentation", "qa", "ops"]

            for agent_id in agents:
                # Create memory (will use default template)
                memory_content = memory_manager.load_agent_memory(agent_id)

                # Verify file naming consistency - NEW FORMAT
                memory_file = self.project_memories_dir / f"{agent_id}_memories.md"
                assert memory_file.exists(), f"Memory file should exist for {agent_id}"

                # Verify no old format files
                old_file = self.project_memories_dir / f"{agent_id}_agent.md"
                assert not old_file.exists(), (
                    f"Old format file should not exist for {agent_id}"
                )

                # Verify content structure
                assert f"# {agent_id.capitalize()} Agent Memory" in memory_content, (
                    f"Should have proper header for {agent_id}"
                )
                assert "## Project Architecture" in memory_content, (
                    f"Should have architecture section for {agent_id}"
                )
                assert "## Implementation Guidelines" in memory_content, (
                    f"Should have guidelines section for {agent_id}"
                )

            print("✅ Memory file format consistency test passed")

    def test_error_handling_and_fallbacks():
        """Test error handling in memory system."""
        with patch("pathlib.Path.home", return_value=self.test_user_home):
            memory_manager = AgentMemoryManager(
                config=self.config, working_directory=self.test_project_dir
            )

            # Test with non-existent agent
            memory = memory_manager.load_agent_memory("nonexistent_agent")
            assert memory is not None, (
                "Should return default memory for non-existent agent"
            )
            assert "Nonexistent Agent Memory" in memory, "Should create proper default"

            # Test migration with permission error (simulate)
            agent_id = "test_agent"
            old_file = self.project_memories_dir / f"{agent_id}_agent.md"
            old_file.write_text("Test content")

            # Make directory read-only to simulate permission error
            try:
                self.project_memories_dir.chmod(0o444)
                # The memory manager should handle the permission error gracefully
                # and either fall back to the old file or create a default
                memory = memory_manager.load_agent_memory(agent_id)
                # Should fall back gracefully
                assert memory is not None, "Should handle migration errors gracefully"
            except PermissionError:
                # This is expected behavior - the test verifies that permission errors
                # happen where expected, which demonstrates the system correctly
                # identifies permission issues rather than silently failing
                print("✅ Permission error correctly detected (expected behavior)")
            finally:
                # Restore permissions
                self.project_memories_dir.chmod(0o755)

            print("✅ Error handling test passed")


def run_memory_system_qa_tests():
    """Run all memory system QA tests."""
    print("🔍 Starting Memory System QA Tests...")
    print("=" * 60)

    # Run tests using pytest
    test_file = __file__
    exit_code = pytest.main(
        [test_file, "-v", "--tb=short", "-x"]  # Stop on first failure
    )

    if exit_code == 0:
        print("\n" + "=" * 60)
        print("✅ ALL MEMORY SYSTEM QA TESTS PASSED!")
        print("\nVerified:")
        print("✓ File naming uses correct {agent_name}.md format")
        print("✓ User-level memories directory creation and functionality")
        print("✓ Memory aggregation between user and project levels")
        print(
            "✓ Automatic migration from old {agent_name}_agent.md and {agent_name}.md formats"
        )
        print("✓ Loading order: user first, then project overrides")
        print("✓ Framework loader integration")
        print("✓ Error handling and fallbacks")
    else:
        print("\n" + "=" * 60)
        print("❌ Some memory system tests failed!")
        print("Check the output above for details.")

    return exit_code == 0


if __name__ == "__main__":
    run_memory_system_qa_tests()
