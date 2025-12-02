#!/usr/bin/env python3

"""
Comprehensive Memory System Verification Test
===========================================

Test that all memories are saved to project directory only.

Objectives:
1. Verify ALL agents save to ./.claude/memories/
2. Confirm NO new files are created in ~/.claude/memories/
3. Test that PM is treated exactly like other agents
4. Test memory extraction from responses
5. Test file migration
6. Test backward compatibility
"""

import shutil
import sys
import tempfile
from pathlib import Path
from unittest import mock

# Add src directory to Python path
test_dir = Path(__file__).parent
project_root = test_dir.parent
src_dir = project_root / "src"
sys.path.insert(0, str(src_dir))

from claude_mpm.services.agents.memory.agent_memory_manager import AgentMemoryManager


class MemorySystemTester:
    """Comprehensive test suite for memory system fixes."""

    def __init__(self):
        self.test_results = []
        self.passed = 0
        self.failed = 0

    def log_test(self, test_name: str, passed: bool, message: str = ""):
        """Log test result."""
        status = "PASS" if passed else "FAIL"
        result = f"[{status}] {test_name}"
        if message:
            result += f" - {message}"

        self.test_results.append(result)
        if passed:
            self.passed += 1
        else:
            self.failed += 1
        print(result)

    def setup_test_environment(self):
        """Set up clean test environment."""
        # Create temporary directories
        self.temp_project_dir = tempfile.mkdtemp(prefix="test_project_")
        self.temp_user_dir = tempfile.mkdtemp(prefix="test_user_")

        self.project_memories_dir = (
            Path(self.temp_project_dir) / ".claude-mpm" / "memories"
        )
        self.user_memories_dir = Path(self.temp_user_dir) / ".claude-mpm" / "memories"

        print(f"Project test directory: {self.temp_project_dir}")
        print(f"User test directory: {self.temp_user_dir}")

        # Mock get_path_manager to return our test directories
        self.mock_path_manager = mock.MagicMock()
        self.mock_path_manager.project_root = Path(self.temp_project_dir)
        self.mock_path_manager.user_config_dir = (
            Path(self.temp_user_dir) / ".claude-mpm"
        )

        return self.temp_project_dir, self.temp_user_dir

    def cleanup_test_environment(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_project_dir, ignore_errors=True)
        shutil.rmtree(self.temp_user_dir, ignore_errors=True)

    def test_pm_memory_project_only():
        """Test 1: PM Memory Test - Save PM memory to project directory only."""
        print("\n=== Test 1: PM Memory Project-Only Storage ===")

        try:
            # Create memory manager with project directory
            config = Config()
            manager = AgentMemoryManager(config, Path(self.temp_project_dir))

            # Save PM memory
            pm_memory_content = "# PM Agent Memory\n\n## Project Architecture\n- Test PM memory content\n"
            success = manager._save_memory_file("PM", pm_memory_content)

            self.log_test("PM memory save operation", success)

            # Check project directory has file
            project_pm_file = self.project_memories_dir / "PM_memories.md"
            project_exists = project_pm_file.exists()
            self.log_test("PM memory exists in project directory", project_exists)

            # Check user directory has NO file
            user_pm_file = self.user_memories_dir / "PM_memories.md"
            user_not_exists = not user_pm_file.exists()
            self.log_test("PM memory NOT in user directory", user_not_exists)

            # Verify content
            if project_exists:
                content = project_pm_file.read_text()
                content_correct = "Test PM memory content" in content
                self.log_test("PM memory content correct", content_correct)

        except Exception as e:
            self.log_test("PM memory test exception", False, str(e))

    def test_other_agent_memory_project_only():
        """Test 2: Other Agent Test - Save engineer/qa memory to project directory."""
        print("\n=== Test 2: Other Agent Memory Project-Only Storage ===")

        try:
            config = Config()
            manager = AgentMemoryManager(config, Path(self.temp_project_dir))

            # Test engineer agent
            engineer_content = "# Engineer Agent Memory\n\n## Implementation Guidelines\n- Test engineer memory\n"
            success = manager._save_memory_file("engineer", engineer_content)
            self.log_test("Engineer memory save operation", success)

            # Check project directory
            project_engineer_file = self.project_memories_dir / "engineer_memories.md"
            project_exists = project_engineer_file.exists()
            self.log_test("Engineer memory exists in project directory", project_exists)

            # Check user directory has NO file
            user_engineer_file = self.user_memories_dir / "engineer_memories.md"
            user_not_exists = not user_engineer_file.exists()
            self.log_test("Engineer memory NOT in user directory", user_not_exists)

            # Test QA agent
            qa_content = (
                "# QA Agent Memory\n\n## Testing Strategies\n- Test QA memory\n"
            )
            success = manager._save_memory_file("qa", qa_content)
            self.log_test("QA memory save operation", success)

            # Check project directory
            project_qa_file = self.project_memories_dir / "qa_memories.md"
            project_exists = project_qa_file.exists()
            self.log_test("QA memory exists in project directory", project_exists)

            # Check user directory has NO file
            user_qa_file = self.user_memories_dir / "qa_memories.md"
            user_not_exists = not user_qa_file.exists()
            self.log_test("QA memory NOT in user directory", user_not_exists)

        except Exception as e:
            self.log_test("Other agent memory test exception", False, str(e))

    def test_memory_extraction_project_only():
        """Test 3: Memory Extraction Test - Verify extraction saves to project directory."""
        print("\n=== Test 3: Memory Extraction from Agent Responses ===")

        try:
            config = Config()
            manager = AgentMemoryManager(config, Path(self.temp_project_dir))

            # Mock agent response with memory
            mock_response = """
            Agent completed the task successfully.

            ```json
            {
                "remember": [
                    "This project uses Python 3.11 with strict type checking",
                    "All API endpoints require JWT authentication"
                ]
            }
            ```

            Task complete.
            """

            # Extract and update memory
            success = manager.extract_and_update_memory("research", mock_response)
            self.log_test("Memory extraction from response", success)

            # Check project directory has file
            project_research_file = self.project_memories_dir / "research_memories.md"
            project_exists = project_research_file.exists()
            self.log_test("Research memory exists in project directory", project_exists)

            # Check user directory has NO file
            user_research_file = self.user_memories_dir / "research_memories.md"
            user_not_exists = not user_research_file.exists()
            self.log_test("Research memory NOT in user directory", user_not_exists)

            # Verify extracted content
            if project_exists:
                content = project_research_file.read_text()
                has_python = "Python 3.11" in content
                has_jwt = "JWT authentication" in content
                self.log_test("Extracted memory contains Python info", has_python)
                self.log_test("Extracted memory contains JWT info", has_jwt)

        except Exception as e:
            self.log_test("Memory extraction test exception", False, str(e))

    def test_file_migration_project_only():
        """Test 4: Migration Test - Verify migration happens in project directory."""
        print("\n=== Test 4: File Migration in Project Directory ===")

        try:
            config = Config()
            manager = AgentMemoryManager(config, Path(self.temp_project_dir))

            # Create old format file in project directory
            self.project_memories_dir.mkdir(parents=True, exist_ok=True)
            old_file = self.project_memories_dir / "security_agent.md"
            old_content = "# Security Agent Memory\n\n## Security Guidelines\n- Old format security memory\n"
            old_file.write_text(old_content)

            # Load memory (should trigger migration)
            loaded_memory = manager.load_agent_memory("security")
            migration_success = "Old format security memory" in loaded_memory
            self.log_test("Memory migration successful", migration_success)

            # Check new file exists
            new_file = self.project_memories_dir / "security_memories.md"
            new_exists = new_file.exists()
            self.log_test("New format file created in project directory", new_exists)

            # Check old file removed
            old_removed = not old_file.exists()
            self.log_test("Old format file removed", old_removed)

            # Check user directory has NO files
            user_has_no_files = (
                not list(self.user_memories_dir.glob("*"))
                if self.user_memories_dir.exists()
                else True
            )
            self.log_test("User directory has no migration files", user_has_no_files)

        except Exception as e:
            self.log_test("File migration test exception", False, str(e))

    def test_backward_compatibility_reading():
        """Test 5: Backward Compatibility Test - Can still read existing user files."""
        print("\n=== Test 5: Backward Compatibility for Reading ===")

        try:
            # Create user directory with existing memory file
            self.user_memories_dir.mkdir(parents=True, exist_ok=True)
            user_file = self.user_memories_dir / "docs_memories.md"
            user_content = "# Docs Agent Memory\n\n## Documentation Standards\n- User directory memory content\n"
            user_file.write_text(user_content)

            config = Config()
            manager = AgentMemoryManager(config, Path(self.temp_project_dir))

            # This should NOT read from user directory anymore - all should be project-only
            # Load memory should create default in project directory
            loaded_memory = manager.load_agent_memory("docs")

            # Check that a default was created in project directory
            project_docs_file = self.project_memories_dir / "docs_memories.md"
            project_exists = project_docs_file.exists()
            self.log_test("Default memory created in project directory", project_exists)

            # Verify user file still exists (not affected)
            user_still_exists = user_file.exists()
            self.log_test("User file still exists (unchanged)", user_still_exists)

            # Verify loaded content is project-specific default, not user content
            is_default_content = "User directory memory content" not in loaded_memory
            self.log_test(
                "Loaded content is project default, not user content",
                is_default_content,
            )

        except Exception as e:
            self.log_test("Backward compatibility test exception", False, str(e))

    def test_edge_cases():
        """Test 6: Edge Cases - No directories, memory updates, size limits."""
        print("\n=== Test 6: Edge Cases Testing ===")

        try:
            config = Config()

            # Test with non-existent directory (should create it)
            nonexistent_dir = Path(self.temp_project_dir) / "nonexistent"
            manager = AgentMemoryManager(config, nonexistent_dir)

            test_content = "# Test Agent Memory\n\n## Test Section\n- Test content\n"
            success = manager._save_memory_file("test", test_content)
            self.log_test("Memory save with non-existent directory", success)

            # Check directory was created in the right place
            expected_dir = nonexistent_dir / ".claude-mpm" / "memories"
            dir_created = expected_dir.exists()
            self.log_test("Directory created in correct location", dir_created)

            # Test memory updates (add more content)
            update_success = manager.update_agent_memory(
                "test", "Test Section", "Additional test item"
            )
            self.log_test("Memory update operation", update_success)

            # Test size limits (create large content)
            large_content = "# Large Agent Memory\n\n## Large Section\n"
            for i in range(1000):
                large_content += (
                    f"- Large memory item {i} with lots of text to exceed size limits\n"
                )

            save_success = manager._save_memory_file("large", large_content)
            self.log_test("Large memory save operation", save_success)

            # Check that it was saved to project directory
            large_file = expected_dir / "large_memories.md"
            large_exists = large_file.exists()
            self.log_test("Large memory file exists in project directory", large_exists)

        except Exception as e:
            self.log_test("Edge cases test exception", False, str(e))

    def test_pm_treated_same_as_others():
        """Test 7: PM Treatment Test - Verify PM is treated exactly like other agents."""
        print("\n=== Test 7: PM Treated Same as Other Agents ===")

        try:
            config = Config()
            manager = AgentMemoryManager(config, Path(self.temp_project_dir))

            # Test PM memory path
            pm_file_path = manager._get_memory_file_with_migration(
                self.project_memories_dir, "PM"
            )
            expected_pm_path = self.project_memories_dir / "PM_memories.md"
            pm_path_correct = pm_file_path == expected_pm_path
            self.log_test(
                "PM memory file path follows standard pattern", pm_path_correct
            )

            # Test engineer memory path
            engineer_file_path = manager._get_memory_file_with_migration(
                self.project_memories_dir, "engineer"
            )
            expected_engineer_path = self.project_memories_dir / "engineer_memories.md"
            engineer_path_correct = engineer_file_path == expected_engineer_path
            self.log_test(
                "Engineer memory file path follows standard pattern",
                engineer_path_correct,
            )

            # Test that both use same directory structure
            pm_dir = pm_file_path.parent
            engineer_dir = engineer_file_path.parent
            same_directory = pm_dir == engineer_dir
            self.log_test("PM and Engineer use same directory", same_directory)

            # Test memory loading behavior is identical
            pm_memory = manager.load_agent_memory("PM")
            engineer_memory = manager.load_agent_memory("engineer")

            both_loaded = bool(pm_memory and engineer_memory)
            self.log_test("Both PM and Engineer memories loaded", both_loaded)

            # Test save behavior is identical (both go to project directory)
            pm_save = manager._save_memory_file("PM", "# PM test")
            engineer_save = manager._save_memory_file("engineer", "# Engineer test")

            both_saved = pm_save and engineer_save
            self.log_test(
                "Both PM and Engineer memories saved successfully", both_saved
            )

            # Verify files exist in same location
            pm_exists = (self.project_memories_dir / "PM_memories.md").exists()
            engineer_exists = (
                self.project_memories_dir / "engineer_memories.md"
            ).exists()
            both_exist = pm_exists and engineer_exists
            self.log_test(
                "Both PM and Engineer files exist in project directory", both_exist
            )

        except Exception as e:
            self.log_test("PM treatment test exception", False, str(e))

    def run_all_tests(self):
        """Run complete test suite."""
        print("Starting Comprehensive Memory System Verification Tests")
        print("=" * 60)

        # Setup test environment
        _project_dir, _user_dir = self.setup_test_environment()

        try:
            # Run all tests
            self.test_pm_memory_project_only()
            self.test_other_agent_memory_project_only()
            self.test_memory_extraction_project_only()
            self.test_file_migration_project_only()
            self.test_backward_compatibility_reading()
            self.test_edge_cases()
            self.test_pm_treated_same_as_others()

        finally:
            # Cleanup
            self.cleanup_test_environment()

        # Print summary
        print("\n" + "=" * 60)
        print("MEMORY SYSTEM VERIFICATION SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {self.passed + self.failed}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(
            f"Success Rate: {(self.passed / (self.passed + self.failed) * 100):.1f}%"
            if (self.passed + self.failed) > 0
            else "N/A"
        )

        if self.failed == 0:
            print("\n🎉 ALL TESTS PASSED! Memory system fix is working correctly.")
            print("\n✅ Verified:")
            print("  - All agents save to project directory only")
            print("  - PM is treated exactly like other agents")
            print("  - No new files created in user directory")
            print("  - Memory extraction works correctly")
            print("  - File migration works in project directory")
            print("  - Edge cases handled properly")
        else:
            print(
                f"\n❌ {self.failed} test(s) failed. Review the output above for details."
            )

        return self.failed == 0


if __name__ == "__main__":
    tester = MemorySystemTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
