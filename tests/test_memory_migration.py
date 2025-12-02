#!/usr/bin/env python3

"""
Memory Migration Test
====================

Test memory file migration from old formats to new format.
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


def test_memory_migration():
    """Test migration from old memory file formats."""
    print("Testing memory file migration...")

    # Create temporary project directory
    temp_project_dir = tempfile.mkdtemp(prefix="test_migration_")

    try:
        project_memories_dir = Path(temp_project_dir) / ".claude-mpm" / "memories"
        project_memories_dir.mkdir(parents=True, exist_ok=True)

        print(f"Project directory: {temp_project_dir}")

        # Test 1: Migration from old format (security_agent.md -> security_memories.md)
        print("\n1. Testing migration from old format...")

        old_file = project_memories_dir / "security_agent.md"
        old_content = "# Security Agent Memory\n\n## Security Guidelines\n- Old format security memory\n"
        old_file.write_text(old_content)
        print(f"   Created old format file: {old_file.name}")

        # Create memory manager and load (should trigger migration)
        config = Config()
        manager = AgentMemoryManager(config, Path(temp_project_dir))

        loaded_memory = manager.load_agent_memory("security")
        print(
            f"   Migration triggered successfully: {'Old format security memory' in loaded_memory}"
        )

        # Check new file exists
        new_file = project_memories_dir / "security_memories.md"
        print(f"   New format file created: {new_file.exists()}")

        # Check old file removed
        print(f"   Old format file removed: {not old_file.exists()}")

        # Test 2: Migration from simple format (docs.md -> docs_memories.md)
        print("\n2. Testing migration from simple format...")

        simple_file = project_memories_dir / "docs.md"
        simple_content = "# Docs Agent Memory\n\n## Documentation Standards\n- Simple format docs memory\n"
        simple_file.write_text(simple_content)
        print(f"   Created simple format file: {simple_file.name}")

        loaded_memory = manager.load_agent_memory("docs")
        print(
            f"   Migration triggered successfully: {'Simple format docs memory' in loaded_memory}"
        )

        # Check new file exists
        new_docs_file = project_memories_dir / "docs_memories.md"
        print(f"   New format file created: {new_docs_file.exists()}")

        # Check old file removed
        print(f"   Simple format file removed: {not simple_file.exists()}")

        # Test 3: No migration needed (already in correct format)
        print("\n3. Testing no migration needed...")

        correct_file = project_memories_dir / "research_memories.md"
        correct_content = "# Research Agent Memory\n\n## Research Guidelines\n- Already correct format\n"
        correct_file.write_text(correct_content)
        print(f"   Created correct format file: {correct_file.name}")

        loaded_memory = manager.load_agent_memory("research")
        print(f"   Correct format loaded: {'Already correct format' in loaded_memory}")
        print(f"   File still exists: {correct_file.exists()}")

        # Test 4: PM migration (PM.md -> PM_memories.md)
        print("\n4. Testing PM migration...")

        old_pm_file = project_memories_dir / "PM.md"
        old_pm_content = (
            "# PM Agent Memory\n\n## Project Architecture\n- Old PM format\n"
        )
        old_pm_file.write_text(old_pm_content)
        print(f"   Created old PM format file: {old_pm_file.name}")

        loaded_memory = manager.load_agent_memory("PM")
        print(
            f"   PM migration triggered successfully: {'Old PM format' in loaded_memory}"
        )

        # Check new PM file exists
        new_pm_file = project_memories_dir / "PM_memories.md"
        print(f"   New PM format file created: {new_pm_file.exists()}")

        # Check old PM file removed
        print(f"   Old PM format file removed: {not old_pm_file.exists()}")

        # Summary
        print("\n" + "=" * 50)
        print("MIGRATION TEST RESULTS")
        print("=" * 50)

        # Check all new format files exist
        new_format_files = [
            project_memories_dir / "security_memories.md",
            project_memories_dir / "docs_memories.md",
            project_memories_dir / "research_memories.md",
            project_memories_dir / "PM_memories.md",
        ]

        all_passed = True
        for file_path in new_format_files:
            if file_path.exists():
                print(f"✅ {file_path.name} exists in correct format")
            else:
                print(f"❌ {file_path.name} missing")
                all_passed = False

        # Check old format files removed
        old_format_files = [
            project_memories_dir / "security_agent.md",
            project_memories_dir / "docs.md",
            project_memories_dir / "PM.md",
        ]

        for file_path in old_format_files:
            if not file_path.exists():
                print(f"✅ {file_path.name} correctly removed")
            else:
                print(f"❌ {file_path.name} still exists")
                all_passed = False

        if all_passed:
            print("\n🎉 ALL MIGRATION TESTS PASSED!")
            print("✅ Old format files migrated to new format")
            print("✅ Old files correctly removed")
            print("✅ PM migration works same as other agents")
            print("✅ All migrations happen in project directory")
        else:
            print("\n❌ SOME MIGRATION TESTS FAILED!")

        return all_passed

    finally:
        # Cleanup
        shutil.rmtree(temp_project_dir, ignore_errors=True)


if __name__ == "__main__":
    success = test_memory_migration()
    sys.exit(0 if success else 1)
