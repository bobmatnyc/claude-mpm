#!/usr/bin/env python3
"""Test script to verify HTML metadata comments are stripped from PM instructions."""

import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import re

from claude_mpm.core.claude_runner import ClaudeRunner


def test_metadata_stripping():
    """Test that metadata comments are properly stripped from instructions."""
    print("Testing metadata comment stripping...")
    print("-" * 60)

    # Initialize ClaudeRunner
    runner = ClaudeRunner()

    # Get the system instructions
    instructions = runner._load_system_instructions()

    if not instructions:
        print("❌ No instructions loaded")
        return False

    print(f"✅ Instructions loaded ({len(instructions)} characters)")

    # Check for metadata comments
    metadata_patterns = [
        r"<!--\s*FRAMEWORK_VERSION[^>]*-->",
        r"<!--\s*LAST_MODIFIED[^>]*-->",
        r"<!--\s*WORKFLOW_VERSION[^>]*-->",
        r"<!--\s*PROJECT_WORKFLOW_VERSION[^>]*-->",
        r"<!--\s*CUSTOM_PROJECT_WORKFLOW[^>]*-->",
        r"<!--\s*AGENT_VERSION[^>]*-->",
        r"<!--\s*METADATA_VERSION[^>]*-->",
    ]

    found_comments = []
    for pattern in metadata_patterns:
        matches = re.findall(pattern, instructions)
        if matches:
            found_comments.extend(matches)

    if found_comments:
        print(
            f"\n❌ Found {len(found_comments)} metadata comments that should have been stripped:"
        )
        for comment in found_comments[:5]:  # Show first 5
            print(f"  - {comment}")
        if len(found_comments) > 5:
            print(f"  ... and {len(found_comments) - 5} more")
        return False
    else:
        print("✅ No metadata comments found - all properly stripped!")

    # Also check the first few lines to ensure clean output
    print("\n📄 First 5 lines of processed instructions:")
    print("-" * 40)
    lines = instructions.split("\n")[:5]
    for i, line in enumerate(lines, 1):
        print(f"{i:2}: {line[:80]}{'...' if len(line) > 80 else ''}")

    # Check that actual content is present
    if "Claude Multi-Agent Project Manager" in instructions:
        print("\n✅ Core PM instructions content present")
    else:
        print("\n⚠️  Warning: Core PM instructions may be missing")

    return True


if __name__ == "__main__":
    success = test_metadata_stripping()
    print("\n" + "=" * 60)
    if success:
        print("✅ TEST PASSED: Metadata comments are properly stripped")
        sys.exit(0)
    else:
        print("❌ TEST FAILED: Metadata comments still present")
        sys.exit(1)