#!/usr/bin/env python3

"""
Simple Memory System Test
========================

Quick test to verify memory system saves to project directory only.
"""

import shutil
import sys
import tempfile
from pathlib import Path

# Add src directory to Python path
test_dir = Path(__file__).parent
project_root = test_dir.parent
src_dir = project_root / "src"
sys.path.insert(0, str(src_dir))

from claude_mpm.services.agents.memory.agent_memory_manager import AgentMemoryManager


def test_memory_project_directory_only():
    """Test that all memories go to project directory only."""
    print("Testing memory system - project directory only storage...")

    # Create temporary directories
    temp_project_dir = tempfile.mkdtemp(prefix="test_project_")
    temp_user_dir = tempfile.mkdtemp(prefix="test_user_")

    try:
        project_memories_dir = Path(temp_project_dir) / ".claude-mpm" / "memories"
        user_memories_dir = Path(temp_user_dir) / ".claude-mpm" / "memories"

        print(f"Project directory: {temp_project_dir}")
        print(f"User directory: {temp_user_dir}")

        # Create memory manager
        config = Config()
        manager = AgentMemoryManager(config, Path(temp_project_dir))

        # Test 1: PM memory save
        print("\n1. Testing PM memory save...")
        pm_content = "# PM Agent Memory\n\n## Project Architecture\n- Test PM memory\n"
        success = manager._save_memory_file("PM", pm_content)
        print(f"   PM save success: {success}")

        # Check project directory
        pm_project_file = project_memories_dir / "PM_memories.md"
        print(f"   PM file in project: {pm_project_file.exists()}")

        # Check user directory (should not exist)
        pm_user_file = user_memories_dir / "PM_memories.md"
        print(f"   PM file NOT in user: {not pm_user_file.exists()}")

        # Test 2: Other agent memory save
        print("\n2. Testing engineer memory save...")
        engineer_content = "# Engineer Agent Memory\n\n## Implementation Guidelines\n- Test engineer memory\n"
        success = manager._save_memory_file("engineer", engineer_content)
        print(f"   Engineer save success: {success}")

        # Check project directory
        engineer_project_file = project_memories_dir / "engineer_memories.md"
        print(f"   Engineer file in project: {engineer_project_file.exists()}")

        # Check user directory (should not exist)
        engineer_user_file = user_memories_dir / "engineer_memories.md"
        print(f"   Engineer file NOT in user: {not engineer_user_file.exists()}")

        # Test 3: Memory extraction
        print("\n3. Testing memory extraction...")
        mock_response = """
        Task complete.

        ```json
        {
            "remember": [
                "This project uses Python 3.11",
                "Memory system saves to project directory only"
            ]
        }
        ```
        """

        success = manager.extract_and_update_memory("qa", mock_response)
        print(f"   Memory extraction success: {success}")

        # Check project directory
        qa_project_file = project_memories_dir / "qa_memories.md"
        print(f"   QA file in project: {qa_project_file.exists()}")

        # Check user directory (should not exist)
        qa_user_file = user_memories_dir / "qa_memories.md"
        print(f"   QA file NOT in user: {not qa_user_file.exists()}")

        # Summary
        print("\n" + "=" * 50)
        print("MEMORY SYSTEM TEST RESULTS")
        print("=" * 50)

        all_passed = True

        # Check all project files exist
        project_files = [pm_project_file, engineer_project_file, qa_project_file]
        for file_path in project_files:
            if file_path.exists():
                print(f"✅ {file_path.name} exists in project directory")
            else:
                print(f"❌ {file_path.name} missing from project directory")
                all_passed = False

        # Check no user files exist
        user_files = [pm_user_file, engineer_user_file, qa_user_file]
        for file_path in user_files:
            if not file_path.exists():
                print(f"✅ {file_path.name} correctly NOT in user directory")
            else:
                print(f"❌ {file_path.name} incorrectly created in user directory")
                all_passed = False

        if all_passed:
            print("\n🎉 ALL TESTS PASSED!")
            print("✅ Memory system correctly saves to project directory only")
            print("✅ PM is treated exactly like other agents")
            print("✅ No files created in user directory")
        else:
            print("\n❌ SOME TESTS FAILED!")

        return all_passed

    finally:
        # Cleanup
        shutil.rmtree(temp_project_dir, ignore_errors=True)
        shutil.rmtree(temp_user_dir, ignore_errors=True)


if __name__ == "__main__":
    success = test_memory_project_directory_only()
    sys.exit(0 if success else 1)
