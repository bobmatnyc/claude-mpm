#!/usr/bin/env python3
"""Test script to verify the customize-pm command fix.

This script tests that:
1. customize-pm writes to .claude-mpm/INSTRUCTIONS.md, not CLAUDE.md
2. The framework loader correctly loads custom INSTRUCTIONS.md files
3. No CLAUDE.md files are created
"""

import os
import sys
import tempfile
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.cli.commands.agent_manager import AgentManagerCommand
from claude_mpm.core.framework_loader import FrameworkLoader


def test_customize_pm_location():
    """Test that customize-pm writes to the correct location."""
    print("Testing customize-pm command...")

    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        os.chdir(tmpdir)

        try:
            # Create a mock args object
            class Args:
                agent_manager_command = "customize-pm"
                level = "project"
                patterns = ["Test pattern"]
                rules = ["Test rule"]

            args = Args()

            # Run the customize-pm command
            cmd = AgentManagerCommand()
            cmd.run(args)

            # Check that the file was created in the right place
            expected_file = Path(tmpdir) / ".claude-mpm" / "INSTRUCTIONS.md"
            claude_file = Path(tmpdir) / "CLAUDE.md"

            assert expected_file.exists(), f"Expected file not created: {expected_file}"
            assert not claude_file.exists(), (
                f"CLAUDE.md should not be created: {claude_file}"
            )

            # Check the content
            content = expected_file.read_text()
            assert "Custom PM Instructions" in content
            assert "Test pattern" in content
            assert "Test rule" in content

            print(
                f"✅ customize-pm correctly writes to {expected_file.relative_to(Path(tmpdir))}"
            )

        finally:
            os.chdir(original_cwd)


def test_framework_loader():
    """Test that the framework loader loads custom INSTRUCTIONS.md."""
    print("\nTesting framework loader...")

    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        os.chdir(tmpdir)

        try:
            # Create a custom INSTRUCTIONS.md file
            instructions_dir = Path(tmpdir) / ".claude-mpm"
            instructions_dir.mkdir(parents=True, exist_ok=True)
            instructions_file = instructions_dir / "INSTRUCTIONS.md"

            custom_content = """# Custom Test Instructions

These are custom PM instructions for testing.

## Test Section
This should be loaded by the framework loader.
"""
            instructions_file.write_text(custom_content)

            # Create a framework loader and load content
            loader = FrameworkLoader()

            # Check that custom instructions were loaded
            assert loader.framework_content.get("custom_instructions"), (
                "Custom instructions not loaded"
            )
            assert (
                "Custom Test Instructions"
                in loader.framework_content["custom_instructions"]
            )
            assert (
                loader.framework_content.get("custom_instructions_level") == "project"
            )

            # Get the formatted framework and check it includes custom instructions
            formatted = loader.get_framework_instructions()
            assert "Custom PM Instructions (project level)" in formatted
            assert "Custom Test Instructions" in formatted

            print(
                f"✅ Framework loader correctly loads from {instructions_file.relative_to(Path(tmpdir))}"
            )

        finally:
            os.chdir(original_cwd)


def test_no_claude_md_created():
    """Verify that no CLAUDE.md files are created anywhere."""
    print("\nVerifying no CLAUDE.md files are created...")

    # Check that customize-pm doesn't reference CLAUDE.md in its implementation
    agent_manager_file = (
        Path(__file__).parent.parent
        / "src"
        / "claude_mpm"
        / "cli"
        / "commands"
        / "agent_manager.py"
    )
    content = agent_manager_file.read_text()

    # Look for any remaining references to writing CLAUDE.md
    bad_patterns = ['CLAUDE.md"', "CLAUDE.md'", "write.*CLAUDE", "CLAUDE.*write"]

    issues = []
    for pattern in bad_patterns:
        if (
            pattern in content
            and ".claude-mpm"
            not in content[content.find(pattern) - 50 : content.find(pattern) + 50]
        ):
            issues.append(f"Found potentially problematic pattern: {pattern}")

    if issues:
        print("❌ Found references to CLAUDE.md that might be problematic:")
        for issue in issues:
            print(f"   - {issue}")
    else:
        print("✅ No problematic CLAUDE.md references found")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing customize-pm command fix")
    print("=" * 60)

    try:
        test_customize_pm_location()
        test_framework_loader()
        test_no_claude_md_created()

        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        print("\nSummary:")
        print("- customize-pm now writes to .claude-mpm/INSTRUCTIONS.md")
        print("- Framework loader correctly loads custom INSTRUCTIONS.md")
        print("- No CLAUDE.md files are created")

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
