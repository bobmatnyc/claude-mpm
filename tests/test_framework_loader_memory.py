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
            print(f"Agent memories loaded: {list(agent_memories.keys())}")

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

            # Check that deployed agent memories were loaded
            engineer_loaded = "Engineer" in agent_memories
            print(f"✓ Engineer_memories.md loaded (deployed): {engineer_loaded}")
            assert engineer_loaded, (
                "Engineer_memories.md should be loaded (agent is deployed)"
            )
            if engineer_loaded:
                assert "Test engineer memory" in agent_memories["Engineer"], (
                    "Engineer memory content not found"
                )

            qa_loaded = "QA" in agent_memories
            print(f"✓ QA_memories.md loaded (deployed): {qa_loaded}")
            assert qa_loaded, "QA_memories.md should be loaded (agent is deployed)"
            if qa_loaded:
                assert "Test QA memory" in agent_memories["QA"], (
                    "QA memory content not found"
                )

            # Check that non-deployed agent memory was NOT loaded
            research_loaded = "Research" in agent_memories
            print(
                f"✓ Research_memories.md NOT loaded (not deployed): {not research_loaded}"
            )
            assert not research_loaded, (
                "Research_memories.md should NOT be loaded (agent not deployed)"
            )

            # Check that README and NOTES were not loaded as memories
            all_memory_content = content.get("actual_memories", "") + str(
                agent_memories
            )
            assert "README" not in all_memory_content, "README.md should NOT be loaded"
            assert "Notes" not in all_memory_content, "NOTES.md should NOT be loaded"
            print("✓ README.md and NOTES.md NOT loaded")

            # Verify count (PM + 2 deployed agents)
            total_loaded = (1 if has_pm else 0) + len(agent_memories)
            expected_count = 3
            print(
                f"\n✓ Expected {expected_count} memory sources, loaded {total_loaded}"
            )
            assert total_loaded == expected_count, (
                f"Expected {expected_count} memory sources, got {total_loaded}"
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
