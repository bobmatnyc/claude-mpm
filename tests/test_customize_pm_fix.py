#!/usr/bin/env python3
"""Test script to verify the customize-pm command fix.

This script tests that:
1. customize-pm writes to .claude-mpm/INSTRUCTIONS.md, not CLAUDE.md
2. The framework loader correctly loads custom INSTRUCTIONS.md files
3. No CLAUDE.md files are created
"""

import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.cli.commands.agent_manager import AgentManagerCommand
from claude_mpm.core.framework_loader import FrameworkLoader


def test_customize_pm_location(tmp_path, monkeypatch):
    """Test that customize-pm writes to the correct location."""
    # Change to temp directory (monkeypatch restores CWD after the test)
    monkeypatch.chdir(tmp_path)

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
    expected_file = tmp_path / ".claude-mpm" / "INSTRUCTIONS.md"
    claude_file = tmp_path / "CLAUDE.md"

    assert expected_file.exists(), f"Expected file not created: {expected_file}"
    assert not claude_file.exists(), f"CLAUDE.md should not be created: {claude_file}"

    # Check the content
    content = expected_file.read_text()
    assert "Custom PM Instructions" in content
    assert "Test pattern" in content
    assert "Test rule" in content


def test_framework_loader(tmp_path, monkeypatch):
    """Test that the framework loader loads custom INSTRUCTIONS.md."""
    # Change to temp directory (monkeypatch restores CWD after the test)
    monkeypatch.chdir(tmp_path)

    # Create a custom INSTRUCTIONS.md file
    instructions_dir = tmp_path / ".claude-mpm"
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
    assert "Custom Test Instructions" in loader.framework_content["custom_instructions"]
    assert loader.framework_content.get("custom_instructions_level") == "project"

    # Get the formatted framework and check it includes custom instructions
    formatted = loader.get_framework_instructions()
    assert "Custom PM Instructions (project level)" in formatted
    assert "Custom Test Instructions" in formatted


def test_no_claude_md_created():
    """Verify that no CLAUDE.md files are created anywhere."""
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

    assert not issues, (
        "Found references to CLAUDE.md that might be problematic:\n"
        + "\n".join(f"  - {i}" for i in issues)
    )


def main():
    """Run all tests (legacy standalone entry point)."""
    import os
    import tempfile

    print("=" * 60)
    print("Testing customize-pm command fix")
    print("=" * 60)

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            os.chdir(tmpdir)

            class _FakeMonkeypatch:
                def chdir(self, path):
                    pass  # already chdir'd above

            fake_mp = _FakeMonkeypatch()
            fake_tmp = Path(tmpdir)

            try:
                test_customize_pm_location(fake_tmp, fake_mp)
                test_framework_loader(fake_tmp, fake_mp)
                test_no_claude_md_created()
            finally:
                os.chdir(original_cwd)

        print("\n" + "=" * 60)
        print("All tests passed!")
        print("=" * 60)
        print("\nSummary:")
        print("- customize-pm now writes to .claude-mpm/INSTRUCTIONS.md")
        print("- Framework loader correctly loads custom INSTRUCTIONS.md")
        print("- No CLAUDE.md files are created")

    except AssertionError as e:
        print(f"\nTest failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
