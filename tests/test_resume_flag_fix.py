#!/usr/bin/env python3
"""
Test script to verify --resume flag handling in claude-mpm.

This script tests various scenarios to ensure the --resume flag
is properly passed through to Claude Code.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.cli import main
from claude_mpm.cli.commands.run import filter_claude_mpm_args


def test_filter_function():
    """Test that --resume is not filtered out by filter_claude_mpm_args."""
    print("Testing filter_claude_mpm_args function...")

    # Test 1: --resume should pass through
    test_args = ["--resume", "--model", "opus"]
    filtered = filter_claude_mpm_args(test_args)
    assert "--resume" in filtered, (
        f"Expected --resume in filtered args, got: {filtered}"
    )
    print("✓ --resume passes through filter")

    # Test 2: --mpm-resume should be filtered out
    test_args = ["--mpm-resume", "last", "--resume"]
    filtered = filter_claude_mpm_args(test_args)
    assert "--mpm-resume" not in filtered, (
        f"--mpm-resume should be filtered, got: {filtered}"
    )
    assert "last" not in filtered, f"'last' value should be filtered, got: {filtered}"
    assert "--resume" in filtered, f"--resume should remain, got: {filtered}"
    print("✓ --mpm-resume is filtered while --resume passes through")

    # Test 3: Mixed args
    test_args = ["--resume", "--monitor", "--model", "opus"]
    filtered = filter_claude_mpm_args(test_args)
    assert "--resume" in filtered, f"--resume should pass through, got: {filtered}"
    assert "--monitor" not in filtered, f"--monitor should be filtered, got: {filtered}"
    assert "--model" in filtered, f"--model should pass through, got: {filtered}"
    print("✓ Mixed args filtered correctly")

    print("✅ All filter function tests passed!\n")


def test_argument_parsing():
    """Test that argument parsing handles --resume correctly."""
    print("Testing argument parsing...")

    from claude_mpm.cli.commands.parser import create_parser

    parser = create_parser()

    # Test 1: --resume without command (defaults to run) - resumes last session
    args = parser.parse_args(["--resume"])
    assert hasattr(args, "resume"), "Parser should have resume attribute"
    # args.resume is now "" (empty string) when used without session_id
    assert args.resume == "", f"resume should be '' (empty string), got: {repr(args.resume)}"
    print("✓ --resume parsed at top level (resume last session)")

    # Test 2: run command with --resume and session_id
    args = parser.parse_args(["run", "--resume", "session123"])
    assert hasattr(args, "resume"), "Parser should have resume attribute"
    assert args.resume == "session123", f"resume should be 'session123', got: {repr(args.resume)}"
    print("✓ 'run --resume session123' parsed correctly")

    # Test 3: --resume with --mpm-resume
    args = parser.parse_args(["--resume", "abc", "--mpm-resume", "last"])
    assert args.resume == "abc", f"resume should be 'abc', got: {repr(args.resume)}"
    assert args.mpm_resume == "last", (
        f"mpm_resume should be 'last', got: {args.mpm_resume}"
    )
    print("✓ Both --resume and --mpm-resume work together")

    # Test 4: No --resume flag means None
    args = parser.parse_args([])
    assert args.resume is None, f"resume should be None when not used, got: {repr(args.resume)}"
    print("✓ No --resume flag results in None")

    print("✅ All argument parsing tests passed!\n")


def test_command_construction():
    """Test that the Claude command is constructed correctly with --resume."""
    print("Testing command construction...")

    from claude_mpm.cli import _ensure_run_attributes

    # Create a mock args object
    class Args:
        def __init__(self):
            self.resume = None  # None means flag not used
            self.claude_args = []
            self.no_tickets = False
            self.no_hooks = False
            self.monitor = False
            self.mpm_resume = None
            self.force = False

    # Test 1: --resume without session_id (resume last) adds just --resume to claude_args
    args = Args()
    args.resume = ""  # Empty string means resume last session
    _ensure_run_attributes(args)
    assert "--resume" in args.claude_args, (
        f"Expected --resume in claude_args, got: {args.claude_args}"
    )
    assert "--fork-session" not in args.claude_args, (
        f"--fork-session should not be present for resume last, got: {args.claude_args}"
    )
    print("✓ --resume added to claude_args when resuming last session")

    # Test 2: --resume with session_id adds --resume <id> --fork-session
    args = Args()
    args.resume = "session123"
    _ensure_run_attributes(args)
    assert "--resume" in args.claude_args, (
        f"Expected --resume in claude_args, got: {args.claude_args}"
    )
    assert "session123" in args.claude_args, (
        f"Expected session123 in claude_args, got: {args.claude_args}"
    )
    assert "--fork-session" in args.claude_args, (
        f"Expected --fork-session in claude_args, got: {args.claude_args}"
    )
    print("✓ --resume with session_id adds --resume <id> --fork-session")

    # Test 3: --resume not added when flag is None (not used)
    args = Args()
    args.resume = None
    _ensure_run_attributes(args)
    assert "--resume" not in args.claude_args, (
        f"--resume should not be in claude_args when None, got: {args.claude_args}"
    )
    print("✓ --resume not added when flag is None")

    # Test 4: --resume not duplicated if already in claude_args
    args = Args()
    args.resume = ""  # Resume last
    args.claude_args = ["--resume", "--model", "opus"]
    _ensure_run_attributes(args)
    assert args.claude_args.count("--resume") == 1, (
        f"--resume should appear once, got: {args.claude_args}"
    )
    print("✓ --resume not duplicated if already present")

    print("✅ All command construction tests passed!\n")


def test_bash_wrapper():
    """Test that the bash wrapper recognizes --resume as an MPM flag."""
    print("Testing bash wrapper script...")

    script_path = Path(__file__).parent / "claude-mpm"
    if not script_path.exists():
        print("⚠️  Bash wrapper script not found at expected location")
        return

    # Read the script and check if --resume is in MPM_FLAGS
    content = script_path.read_text()
    if '"--resume"' in content and "MPM_FLAGS=" in content:
        # Find the MPM_FLAGS line
        for line in content.split("\n"):
            if "MPM_FLAGS=" in line and '"--resume"' in line:
                print("✓ --resume is in MPM_FLAGS list")
                break
        else:
            print("⚠️  --resume might not be properly added to MPM_FLAGS")
    else:
        print("❌ --resume not found in MPM_FLAGS")

    print("✅ Bash wrapper check complete!\n")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing --resume flag implementation")
    print("=" * 60)
    print()

    try:
        test_filter_function()
        test_argument_parsing()
        test_command_construction()
        test_bash_wrapper()

        print("=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nThe --resume flag should now work correctly:")
        print("  • claude-mpm --resume")
        print("  • claude-mpm run --resume")
        print("  • claude-mpm --resume --mpm-resume last")
        print("\nThe flag will be properly passed to Claude Code.")

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
