#!/usr/bin/env python3
"""
Simple test to verify the glob pattern change works correctly.
Tests the core memory filtering logic without full framework initialization.
"""

import sys
from pathlib import Path


def test_glob_patterns():
    """Test that different glob patterns filter files correctly."""

    # Create a temporary test directory
    with tmp_path as tmpdir:
        tmpdir = Path(tmpdir)

        # Create test files
        test_files = [
            "PM_memories.md",
            "Engineer_memories.md",
            "Research_memories.md",
            "QA_memories.md",
            "README.md",
            "NOTES.md",
            "old_agent.md",
            "legacy.md",
            "documentation.md",
        ]

        for filename in test_files:
            (tmpdir / filename).write_text(f"Content of {filename}")

        print("=" * 60)
        print("Glob Pattern Test Results")
        print("=" * 60)
        print(f"\nTest directory: {tmpdir}")
        print(f"Total files created: {len(test_files)}\n")

        # Test old pattern (*.md) - would match ALL .md files
        old_pattern_files = list(tmpdir.glob("*.md"))
        old_pattern_names = [f.name for f in old_pattern_files]
        print("Old pattern (*.md) matches:")
        for name in sorted(old_pattern_names):
            print(f"  - {name}")
        print(f"Total: {len(old_pattern_names)} files")

        # Test new pattern (*_memories.md) - should only match memory files
        new_pattern_files = list(tmpdir.glob("*_memories.md"))
        new_pattern_names = [f.name for f in new_pattern_files]
        print("\nNew pattern (*_memories.md) matches:")
        for name in sorted(new_pattern_names):
            print(f"  - {name}")
        print(f"Total: {len(new_pattern_names)} files")

        # Verify the difference
        print("\n" + "=" * 60)
        print("Verification:")
        print("=" * 60)

        # Files that old pattern matches but new pattern doesn't
        excluded_files = set(old_pattern_names) - set(new_pattern_names)
        print("\nFiles excluded by new pattern (correctly filtered out):")
        for name in sorted(excluded_files):
            print(f"  ✓ {name} - NOT loaded as memory")

        # Expected memory files
        expected_memories = [
            "PM_memories.md",
            "Engineer_memories.md",
            "Research_memories.md",
            "QA_memories.md",
        ]

        # Verify all expected memory files are matched
        print("\nExpected memory files:")
        for expected in expected_memories:
            if expected in new_pattern_names:
                print(f"  ✓ {expected} - correctly matched")
            else:
                print(f"  ✗ {expected} - MISSING!")

        # Verify no non-memory files are matched
        print("\nNon-memory files verification:")
        non_memory_files = [
            "README.md",
            "NOTES.md",
            "old_agent.md",
            "legacy.md",
            "documentation.md",
        ]
        all_excluded = True
        for non_memory in non_memory_files:
            if non_memory not in new_pattern_names:
                print(f"  ✓ {non_memory} - correctly excluded")
            else:
                print(f"  ✗ {non_memory} - INCORRECTLY INCLUDED!")
                all_excluded = False

        # Summary
        print("\n" + "=" * 60)
        print("Summary:")
        print("=" * 60)
        print(
            f"✓ Old pattern (*.md) matched: {len(old_pattern_names)} files (TOO MANY)"
        )
        print(
            f"✓ New pattern (*_memories.md) matched: {len(new_pattern_names)} files (CORRECT)"
        )
        print(f"✓ Filtered out {len(excluded_files)} non-memory files")

        # Assert correctness
        assert len(new_pattern_names) == 4, (
            f"Expected 4 memory files, got {len(new_pattern_names)}"
        )
        assert all(name.endswith("_memories.md") for name in new_pattern_names), (
            "All matched files should end with _memories.md"
        )
        assert "README.md" not in new_pattern_names, "README.md should not be matched"
        assert all_excluded, "All non-memory files should be excluded"

        print(
            "\n✅ All tests passed! The new glob pattern correctly filters memory files."
        )
        return True


if __name__ == "__main__":
    try:
        success = test_glob_patterns()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
