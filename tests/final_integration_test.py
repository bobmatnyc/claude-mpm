#!/usr/bin/env python3
"""Final integration test for memory system fixes."""

import shutil
import sys
import tempfile
import unittest.mock
from pathlib import Path

from claude_mpm.core.config import Config
from claude_mpm.services.agents.memory.agent_memory_manager import AgentMemoryManager


def run_final_integration_test():
    print("=== Final Integration Test ===")

    # Create test environment
    temp_dir = Path(tempfile.mkdtemp(prefix="final_memory_test_"))
    test_user_home = temp_dir / "user_home"
    test_project_dir = temp_dir / "project"
    test_user_home.mkdir(parents=True)
    test_project_dir.mkdir(parents=True)

    try:
        # Mock user home
        with unittest.mock.patch("pathlib.Path.home", return_value=test_user_home):
            config = Config()

            # Test PM memory (should go to user directory)
            memory_manager = AgentMemoryManager(config, test_project_dir)
            memory_manager.load_agent_memory("PM")

            # Verify PM file location
            user_pm_file = (
                test_user_home / ".claude-mpm" / "memories" / "PM_memories.md"
            )
            project_pm_file = (
                test_project_dir / ".claude-mpm" / "memories" / "PM_memories.md"
            )

            assert user_pm_file.exists(), "PM memory should be in user directory"
            assert not project_pm_file.exists(), (
                "PM memory should NOT be in project directory"
            )
            print("✅ PM memory persistence verified")

            # Test other agent (should go to project directory)
            memory_manager.load_agent_memory("engineer")

            # Verify engineer file location
            user_engineer_file = (
                test_user_home / ".claude-mpm" / "memories" / "engineer_memories.md"
            )
            project_engineer_file = (
                test_project_dir / ".claude-mpm" / "memories" / "engineer_memories.md"
            )

            assert project_engineer_file.exists(), (
                "Engineer memory should be in project directory"
            )
            assert not user_engineer_file.exists(), (
                "Engineer memory should NOT be in user directory"
            )
            print("✅ Other agent directory handling verified")

            # Test memory extraction with proper JSON
            json_response = """
Task completed.

```json
{
    "remember": ["Test extraction works correctly", "Memory system is functional"]
}
```
"""

            success = memory_manager.extract_and_update_memory(
                "engineer", json_response
            )
            assert success, "Memory extraction should work"

            # Verify extraction worked
            updated_memory = memory_manager.load_agent_memory("engineer")
            assert "Test extraction works correctly" in updated_memory
            print("✅ Memory extraction verified")

            # Test cross-project PM persistence
            second_project_dir = temp_dir / "project2"
            second_project_dir.mkdir(parents=True)

            memory_manager2 = AgentMemoryManager(config, second_project_dir)

            # Add PM memory in project 1
            memory_manager.add_learning(
                "PM", "guideline", "Cross-project test successful"
            )

            # Check PM memory in project 2
            pm_memory2 = memory_manager2.load_agent_memory("PM")
            assert "Cross-project test successful" in pm_memory2
            print("✅ Cross-project PM memory verified")

            print("\n🎉 ALL INTEGRATION TESTS PASSED!")
            return True

    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

    finally:
        # Cleanup
        shutil.rmtree(temp_dir)
        print("✅ Test cleanup completed")


if __name__ == "__main__":
    success = run_final_integration_test()
    sys.exit(0 if success else 1)
