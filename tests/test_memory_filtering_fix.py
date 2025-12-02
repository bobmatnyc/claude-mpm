#!/usr/bin/env python3
"""
Test script to verify the memory file filtering fix works correctly.

This script verifies that:
1. Only *_memories.md files are loaded (not README.md or other docs)
2. PM_memories.md is handled specially
3. Agent memories are only loaded if the agent is deployed
4. Old format files are migrated to new format
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.framework_loader import FrameworkLoader


def test_memory_filtering():
    """Test that memory filtering works correctly."""

    # Create a temporary test directory
    with tmp_path as tmpdir:
        tmpdir = Path(tmpdir)

        # Create test directories
        base_dir = tmpdir / ".claude"
        memories_dir = base_dir / "memories"
        agents_dir = base_dir / "agents"
        memories_dir.mkdir(parents=True)
        agents_dir.mkdir(parents=True)

        # Create test memory files
        test_files = {
            "PM_memories.md": "# PM Memory\nTest PM memory content",
            "Engineer_memories.md": "# Engineer Memory\nTest engineer memory",
            "Research_memories.md": "# Research Memory\nTest research memory",
            "README.md": "# README\nThis should NOT be loaded as memory",
            "NOTES.md": "# Notes\nThis should also NOT be loaded",
            "old_agent.md": "# Old Agent\nOld format - should be migrated to old_memories.md",
            "legacy_agent.md": "# Legacy Agent\nLegacy format - should be migrated",
        }

        for filename, content in test_files.items():
            (memories_dir / filename).write_text(content)

        # Deploy only the Engineer agent
        engineer_dir = agents_dir / "Engineer"
        engineer_dir.mkdir()
        (engineer_dir / "instructions.md").write_text("Engineer instructions")

        # Create a test config with proper framework path
        config = Config()
        config.base_dir = base_dir

        # Initialize framework loader with the actual project path
        project_root = Path(__file__).parent.parent
        loader = FrameworkLoader(config)
        loader.framework_path = project_root

        # Load memories
        memories = loader._load_memories("test", memories_dir, ["Engineer"])

        print("=" * 60)
        print("Memory Loading Test Results")
        print("=" * 60)

        # Check that PM memory was loaded
        pm_loaded = any("PM Memory" in m["content"] for m in memories)
        print(f"✓ PM_memories.md loaded: {pm_loaded}")
        assert pm_loaded, "PM_memories.md should be loaded"

        # Check that Engineer memory was loaded (deployed agent)
        engineer_loaded = any("Engineer Memory" in m["content"] for m in memories)
        print(f"✓ Engineer_memories.md loaded (deployed): {engineer_loaded}")
        assert engineer_loaded, (
            "Engineer_memories.md should be loaded (agent is deployed)"
        )

        # Check that Research memory was NOT loaded (not deployed)
        research_loaded = any("Research Memory" in m["content"] for m in memories)
        print(
            f"✓ Research_memories.md NOT loaded (not deployed): {not research_loaded}"
        )
        assert not research_loaded, (
            "Research_memories.md should NOT be loaded (agent not deployed)"
        )

        # Check that README.md was NOT loaded
        readme_loaded = any("README" in m["content"] for m in memories)
        print(f"✓ README.md NOT loaded: {not readme_loaded}")
        assert not readme_loaded, "README.md should NOT be loaded"

        # Check that NOTES.md was NOT loaded
        notes_loaded = any("Notes" in m["content"] for m in memories)
        print(f"✓ NOTES.md NOT loaded: {not notes_loaded}")
        assert not notes_loaded, "NOTES.md should NOT be loaded"

        # Check that old format files were migrated
        old_migrated = (memories_dir / "old_memories.md").exists()
        print(f"✓ old_agent.md migrated to old_memories.md: {old_migrated}")
        assert old_migrated, "old_agent.md should be migrated to old_memories.md"

        legacy_migrated = (memories_dir / "legacy_memories.md").exists()
        print(f"✓ legacy_agent.md migrated to legacy_memories.md: {legacy_migrated}")
        assert legacy_migrated, (
            "legacy_agent.md should be migrated to legacy_memories.md"
        )

        print("\n" + "=" * 60)
        print(f"Total memories loaded: {len(memories)}")
        print("Memory files loaded:")
        for mem in memories:
            path = Path(mem["path"])
            print(f"  - {path.name}")

        print("\n✅ All tests passed! Memory filtering is working correctly.")
        print("=" * 60)

        return True


if __name__ == "__main__":
    try:
        success = test_memory_filtering()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
