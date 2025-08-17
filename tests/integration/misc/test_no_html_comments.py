#!/usr/bin/env python3
"""Comprehensive test to ensure no HTML comments appear in final PM instructions."""

import os
import re
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_claude_runner_instructions():
    """Test ClaudeRunner's instruction generation."""
    from claude_mpm.core.claude_runner import ClaudeRunner

    print("Testing ClaudeRunner instruction generation...")
    runner = ClaudeRunner()

    # Get the system prompt that would be passed to Claude
    system_prompt = runner._create_system_prompt()

    if not system_prompt:
        print("❌ No system prompt generated")
        return False, None

    print(f"✅ System prompt generated ({len(system_prompt)} characters)")
    return True, system_prompt


def test_framework_loader_instructions():
    """Test FrameworkLoader's instruction generation."""
    from claude_mpm.core.framework_loader import FrameworkLoader

    print("\nTesting FrameworkLoader instruction generation...")
    loader = FrameworkLoader()

    # Get framework instructions
    instructions = loader.get_framework_instructions()

    if not instructions:
        print("❌ No framework instructions generated")
        return False, None

    print(f"✅ Framework instructions generated ({len(instructions)} characters)")
    return True, instructions


def check_for_html_comments(content: str, source: str) -> bool:
    """Check content for any HTML comments."""
    # Find all HTML comments
    html_comments = re.findall(r"<!--[^>]*-->", content)

    if html_comments:
        print(f"\n❌ Found {len(html_comments)} HTML comments in {source}:")
        for i, comment in enumerate(html_comments[:10], 1):  # Show first 10
            # Truncate long comments
            display = comment if len(comment) <= 80 else comment[:77] + "..."
            print(f"  {i:2}. {display}")
        if len(html_comments) > 10:
            print(f"  ... and {len(html_comments) - 10} more")
        return False
    else:
        print(f"✅ No HTML comments found in {source}")
        return True


def main():
    """Run all tests."""
    print("=" * 70)
    print("COMPREHENSIVE HTML COMMENT TEST")
    print("=" * 70)

    all_passed = True

    # Test ClaudeRunner
    success, content = test_claude_runner_instructions()
    if success and content:
        passed = check_for_html_comments(content, "ClaudeRunner system prompt")
        all_passed = all_passed and passed

        # Show sample of output
        print("\n📄 First 3 lines of ClaudeRunner output:")
        lines = content.split("\n")[:3]
        for line in lines:
            print(f"  {line[:80]}{'...' if len(line) > 80 else ''}")
    else:
        all_passed = False

    # Test FrameworkLoader
    success, content = test_framework_loader_instructions()
    if success and content:
        passed = check_for_html_comments(content, "FrameworkLoader instructions")
        all_passed = all_passed and passed

        # Show sample of output
        print("\n📄 First 3 lines of FrameworkLoader output:")
        lines = content.split("\n")[:3]
        for line in lines:
            print(f"  {line[:80]}{'...' if len(line) > 80 else ''}")
    else:
        all_passed = False

    # Final result
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ ALL TESTS PASSED: No HTML comments in PM instructions")
        return 0
    else:
        print("❌ TESTS FAILED: HTML comments still present in instructions")
        return 1


if __name__ == "__main__":
    sys.exit(main())
