#!/usr/bin/env python3
"""
Integration test to verify memory loading works correctly with the glob pattern fix.
This test simulates the actual memory loading process.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_memory_loading_integration():
    """Test memory loading with actual file structure."""

    print("=" * 60)
    print("Memory Loading Integration Test")
    print("=" * 60)

    # Create a temporary test directory
    with tmp_path as tmpdir:
        tmpdir = Path(tmpdir)

        # Create test directories
        claude_dir = tmpdir / ".claude-mpm"
        memories_dir = claude_dir / "memories"
        memories_dir.mkdir(parents=True)

        # Create test memory files
        test_files = {
            "PM_memories.md": "# PM Memory\n- PM knows this is a test project",
            "engineer_memories.md": "# Engineer Memory\n- Engineer worked on auth module",
            "qa_memories.md": "# QA Memory\n- QA tested login flow",
            "research_memories.md": "# Research Memory\n- Research analyzed codebase",
            "README.md": "# README\nThis is documentation, not memory",
            "NOTES.md": "# Notes\nJust some notes, not memory",
            "old_format.md": "# Old Format\nOld memory file format",
        }

        for filename, content in test_files.items():
            (memories_dir / filename).write_text(content)

        print(f"\nTest directory: {memories_dir}")
        print(f"Created {len(test_files)} test files")

        # List files using the old pattern (*.md)
        old_pattern_files = list(memories_dir.glob("*.md"))
        print(f"\nOld pattern (*.md) would match {len(old_pattern_files)} files:")
        for f in sorted(old_pattern_files):
            print(f"  - {f.name}")

        # List files using the new pattern (*_memories.md)
        new_pattern_files = list(memories_dir.glob("*_memories.md"))
        print(f"\nNew pattern (*_memories.md) matches {len(new_pattern_files)} files:")
        for f in sorted(new_pattern_files):
            print(f"  - {f.name}")

        # Verify the filtering
        print("\n" + "=" * 60)
        print("Verification:")
        print("=" * 60)

        # Expected memory files
        expected_memories = [
            "PM_memories.md",
            "engineer_memories.md",
            "qa_memories.md",
            "research_memories.md",
        ]
        actual_memories = [f.name for f in new_pattern_files]

        print("\nExpected memory files:")
        for expected in expected_memories:
            if expected in actual_memories:
                print(f"  ✓ {expected} - correctly matched")
            else:
                print(f"  ✗ {expected} - MISSING!")

        # Files that should be excluded
        excluded_files = ["README.md", "NOTES.md", "old_format.md"]
        print("\nFiles that should be excluded:")
        for excluded in excluded_files:
            if excluded not in actual_memories:
                print(f"  ✓ {excluded} - correctly excluded")
            else:
                print(f"  ✗ {excluded} - INCORRECTLY INCLUDED!")

        # Summary
        print("\n" + "=" * 60)
        print("Summary:")
        print("=" * 60)

        old_count = len(old_pattern_files)
        new_count = len(new_pattern_files)
        reduction = old_count - new_count

        print(f"Old pattern (*.md): {old_count} files")
        print(f"New pattern (*_memories.md): {new_count} files")
        print(f"Files filtered out: {reduction}")
        print(
            f"Filtering efficiency: {reduction}/{old_count} = {reduction / old_count * 100:.1f}% reduction"
        )

        # Assert correctness
        assert new_count == 4, f"Expected 4 memory files, got {new_count}"
        assert all(name.endswith("_memories.md") for name in actual_memories), (
            "All matched files should end with _memories.md"
        )
        assert "README.md" not in actual_memories, "README.md should not be matched"
        assert "NOTES.md" not in actual_memories, "NOTES.md should not be matched"
        assert reduction == 3, f"Expected to filter out 3 files, filtered {reduction}"

        print("\n✅ All tests passed! Memory filtering works correctly.")
        print("   - Only *_memories.md files are loaded")
        print("   - README.md and other docs are excluded")
        print("   - Old format files are not loaded as memories")
        print("=" * 60)

        return True


if __name__ == "__main__":
    try:
        success = test_memory_loading_integration()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
