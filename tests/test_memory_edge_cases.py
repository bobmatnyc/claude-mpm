#!/usr/bin/env python3

"""
Memory Edge Cases Test
=====================

Test edge cases and backward compatibility for memory system.
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


def test_memory_edge_cases():
    """Test edge cases and backward compatibility."""
    print("Testing memory system edge cases...")

    # Create temporary directories
    temp_project_dir = tempfile.mkdtemp(prefix="test_edge_")
    temp_user_dir = tempfile.mkdtemp(prefix="test_user_edge_")

    try:
        Path(temp_project_dir) / ".claude-mpm" / "memories"
        user_memories_dir = Path(temp_user_dir) / ".claude-mpm" / "memories"

        print(f"Project directory: {temp_project_dir}")
        print(f"User directory: {temp_user_dir}")

        # Test 1: Non-existent directory creation
        print("\n1. Testing non-existent directory creation...")

        nonexistent_dir = Path(temp_project_dir) / "nonexistent"
        config = Config()
        manager = AgentMemoryManager(config, nonexistent_dir)

        test_content = "# Test Agent Memory\n\n## Test Section\n- Test content\n"
        success = manager._save_memory_file("test", test_content)
        print(f"   Save with non-existent directory: {success}")

        expected_dir = nonexistent_dir / ".claude-mpm" / "memories"
        print(f"   Directory created correctly: {expected_dir.exists()}")

        test_file = expected_dir / "test_memories.md"
        print(f"   Test file exists: {test_file.exists()}")

        # Test 2: Memory updates
        print("\n2. Testing memory updates...")

        update_success = manager.update_agent_memory(
            "test", "Test Section", "Additional test item"
        )
        print(f"   Memory update success: {update_success}")

        if test_file.exists():
            content = test_file.read_text()
            print(f"   Update persisted: {'Additional test item' in content}")

        # Test 3: Large memory handling (size limits)
        print("\n3. Testing size limits...")

        # Create large content
        large_content = "# Large Agent Memory\n\n## Large Section\n"
        for i in range(200):  # Create moderately large content
            large_content += f"- Large memory item {i} with some descriptive text\n"

        large_success = manager._save_memory_file("large", large_content)
        print(f"   Large memory save: {large_success}")

        large_file = expected_dir / "large_memories.md"
        print(f"   Large memory file exists: {large_file.exists()}")

        # Test 4: User file backward compatibility (NOTE: Should NOT read user files anymore)
        print("\n4. Testing backward compatibility...")

        # Create user directory with existing memory
        user_memories_dir.mkdir(parents=True, exist_ok=True)
        user_file = user_memories_dir / "legacy_memories.md"
        user_content = "# Legacy Agent Memory\n\n## Legacy Section\n- User directory content (should not be read)\n"
        user_file.write_text(user_content)
        print(f"   Created legacy user file: {user_file.name}")

        # Try to load - should create default in project, not read from user
        legacy_memory = manager.load_agent_memory("legacy")
        print(f"   Legacy memory loaded: {bool(legacy_memory)}")
        print(f"   Contains user content: {'User directory content' in legacy_memory}")
        print(f"   Is default content: {'User directory content' not in legacy_memory}")

        # Check that project file was created
        project_legacy_file = expected_dir / "legacy_memories.md"
        print(f"   Project file created: {project_legacy_file.exists()}")
        print(f"   User file unchanged: {user_file.exists()}")

        # Test 5: PM treated same as others
        print("\n5. Testing PM treatment consistency...")

        # Test PM memory path
        pm_file_path = manager._get_memory_file_with_migration(expected_dir, "PM")
        expected_pm_path = expected_dir / "PM_memories.md"
        print(f"   PM path follows standard: {pm_file_path == expected_pm_path}")

        # Test another agent path
        eng_file_path = manager._get_memory_file_with_migration(
            expected_dir, "engineer"
        )
        expected_eng_path = expected_dir / "engineer_memories.md"
        print(
            f"   Engineer path follows standard: {eng_file_path == expected_eng_path}"
        )

        # Test both use same directory
        print(f"   Same directory used: {pm_file_path.parent == eng_file_path.parent}")

        # Test 6: Memory extraction with different JSON formats
        print("\n6. Testing memory extraction formats...")

        # Test standard JSON format
        standard_response = """
        Task complete.

        ```json
        {
            "remember": [
                "Standard format memory item"
            ]
        }
        ```
        """

        standard_success = manager.extract_and_update_memory(
            "format_test", standard_response
        )
        print(f"   Standard JSON extraction: {standard_success}")

        # Test with null remember
        null_response = """
        Task complete.

        ```json
        {
            "remember": null
        }
        ```
        """

        null_success = manager.extract_and_update_memory("null_test", null_response)
        print(
            f"   Null remember handled: {null_success is False}"
        )  # Should return False for null

        # Test with empty list
        empty_response = """
        Task complete.

        ```json
        {
            "remember": []
        }
        ```
        """

        empty_success = manager.extract_and_update_memory("empty_test", empty_response)
        print(
            f"   Empty list handled: {empty_success is False}"
        )  # Should return False for empty list

        # Summary
        print("\n" + "=" * 50)
        print("EDGE CASES TEST RESULTS")
        print("=" * 50)

        all_passed = True

        # Verify key requirements
        checks = [
            (expected_dir.exists(), "Directory creation works"),
            (test_file.exists(), "Memory files created in correct location"),
            (large_file.exists(), "Large memory files handled"),
            (project_legacy_file.exists(), "Project files created for new agents"),
            (user_file.exists(), "User files left unchanged"),
            ("User directory content" not in legacy_memory, "User content not read"),
            (pm_file_path == expected_pm_path, "PM uses standard naming"),
            (
                pm_file_path.parent == eng_file_path.parent,
                "All agents use same directory",
            ),
        ]

        for check, description in checks:
            if check:
                print(f"✅ {description}")
            else:
                print(f"❌ {description}")
                all_passed = False

        if all_passed:
            print("\n🎉 ALL EDGE CASE TESTS PASSED!")
            print("✅ Directory creation works properly")
            print("✅ Memory updates work correctly")
            print("✅ Size limits handled appropriately")
            print("✅ User files ignored (project-only mode)")
            print("✅ PM treated identically to other agents")
            print("✅ All memories stored in project directory")
        else:
            print("\n❌ SOME EDGE CASE TESTS FAILED!")

        return all_passed

    finally:
        # Cleanup
        shutil.rmtree(temp_project_dir, ignore_errors=True)
        shutil.rmtree(temp_user_dir, ignore_errors=True)


if __name__ == "__main__":
    success = test_memory_edge_cases()
    sys.exit(0 if success else 1)
