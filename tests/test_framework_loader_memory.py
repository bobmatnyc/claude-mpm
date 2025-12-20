#!/usr/bin/env python3
"""
Test the FrameworkLoader memory loading functionality after the glob pattern fix.
"""

import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.framework_loader import FrameworkLoader


def test_memory_loading():
    """Test that memory loading works correctly with the new glob pattern."""

    print("=" * 60)
    print("Testing FrameworkLoader Memory Loading")
    print("=" * 60)

    # Create a temporary test directory
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create test directories as .claude-mpm/memories under project root
        memories_dir = tmpdir / ".claude-mpm" / "memories"
        memories_dir.mkdir(parents=True)

        # Create .claude/agents directory for deployed agents
        agents_dir = tmpdir / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        # Create test memory files
        test_files = {
            "PM_memories.md": "# PM Memory\n- Test PM memory content",
            "Engineer_memories.md": "# Engineer Memory\n- Test engineer memory",
            "Research_memories.md": "# Research Memory\n- Test research memory",
            "QA_memories.md": "# QA Memory\n- Test QA memory",
            "README.md": "# README\nThis should NOT be loaded as memory",
            "NOTES.md": "# Notes\nThis should also NOT be loaded",
        }

        for filename, content in test_files.items():
            (memories_dir / filename).write_text(content)

        # Create deployed agent files
        (agents_dir / "Engineer.md").write_text("# Engineer Agent")
        (agents_dir / "QA.md").write_text("# QA Agent")

        # Create a FrameworkLoader with the temp directory as cwd
        import os

        old_cwd = os.getcwd()
        os.chdir(tmpdir)

        try:
            loader = FrameworkLoader()

            print(f"\nTest directory: {memories_dir}")
            print("Deployed agents: Engineer, QA")
            print()

            # Load framework content which will trigger memory loading
            content = loader._load_framework_content()
            loader._load_actual_memories(content)

            # Get the loaded memories
            has_pm = bool(content.get("actual_memories"))
            agent_memories = content.get("agent_memories", {})

            print(f"PM memory loaded: {has_pm}")
            print(f"Agent memories in framework content: {list(agent_memories.keys())}")

            # Verify results
            print("\n" + "=" * 60)
            print("Verification:")
            print("=" * 60)

            # Check that PM memory was loaded
            print(f"✓ PM_memories.md loaded: {has_pm}")
            assert has_pm, "PM_memories.md should always be loaded"
            assert "Test PM memory" in content["actual_memories"], (
                "PM memory content not found"
            )

            # NEW ARCHITECTURE: Agent memories are NOT loaded at framework time
            # They are loaded at agent deployment time and appended to each agent file
            print("\n✓ Agent memories NOT in framework content (expected behavior)")
            print("  Agent memories are now loaded at deployment time")
            assert len(agent_memories) == 0, (
                "Agent memories should NOT be loaded at framework time anymore. "
                "They are now appended to agent files at deployment time."
            )

            # Check that README and NOTES were not loaded as memories
            all_memory_content = content.get("actual_memories", "")
            assert "README" not in all_memory_content, "README.md should NOT be loaded"
            assert "Notes" not in all_memory_content, "NOTES.md should NOT be loaded"
            print("✓ README.md and NOTES.md NOT loaded")

            # Verify count (PM only)
            total_loaded = 1 if has_pm else 0
            expected_count = 1
            print(
                f"\n✓ Expected {expected_count} memory source (PM only), loaded {total_loaded}"
            )
            assert total_loaded == expected_count, (
                f"Expected {expected_count} memory sources (PM only), got {total_loaded}"
            )

            print("\n✅ All tests passed! Memory filtering is working correctly.")
            print("=" * 60)
        finally:
            os.chdir(old_cwd)


if __name__ == "__main__":
    try:
        success = test_memory_loading()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
