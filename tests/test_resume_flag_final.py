#!/usr/bin/env python3
"""
Comprehensive test script to verify --resume flag functionality.

WHY: This test ensures that the --resume flag works correctly through all layers
of the claude-mpm system, from the bash wrapper to the final Claude CLI call.

DESIGN DECISION: We test multiple scenarios to ensure the fix is robust and
handles various edge cases.
"""

import sys
from pathlib import Path

# Add src to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from claude_mpm.cli.commands.parsers import create_parser
from claude_mpm.cli.commands.run import filter_claude_mpm_args


def test_bash_wrapper_recognition():
    """Test that bash wrapper recognizes --resume as an MPM flag."""
    script_path = project_root / "scripts" / "claude-mpm"

    # Read the script
    with script_path.open() as f:
        content = f.read()

    # Check if --resume is in MPM_FLAGS
    if '"--resume"' in content and "MPM_FLAGS=(" in content:
        # Extract the MPM_FLAGS line
        for line in content.split("\n"):
            if "MPM_FLAGS=(" in line and '"--resume"' in line:
                print("✅ Bash wrapper includes --resume in MPM_FLAGS")
                return True

    print("❌ Bash wrapper does NOT include --resume in MPM_FLAGS")
    return False


def test_parser_configuration():
    """Test that the argument parser correctly handles --resume."""
    parser = create_parser()

    # Test 1: Top-level --resume
    try:
        args = parser.parse_args(["--resume"])
        if hasattr(args, "resume") and args.resume:
            print("✅ Parser correctly handles top-level --resume")
        else:
            print("❌ Parser doesn't set resume flag for top-level --resume")
            return False
    except SystemExit:
        print("❌ Parser fails to parse top-level --resume")
        return False

    # Test 2: Run subcommand with --resume
    try:
        args = parser.parse_args(["run", "--resume"])
        if hasattr(args, "resume") and args.resume:
            print("✅ Parser correctly handles 'run --resume'")
        else:
            print("❌ Parser doesn't set resume flag for 'run --resume'")
            return False
    except SystemExit:
        print("❌ Parser fails to parse 'run --resume'")
        return False

    return True


def test_filter_function():
    """Test that filter_claude_mpm_args doesn't filter out --resume."""
    # Test that --resume passes through
    test_args = ["--resume", "--model", "opus"]
    filtered = filter_claude_mpm_args(test_args)

    if "--resume" in filtered:
        print("✅ Filter function preserves --resume flag")
    else:
        print("❌ Filter function incorrectly removes --resume flag")
        return False

    # Test that MPM-specific flags are filtered
    test_args = ["--resume", "--monitor", "--websocket-port", "8765", "--model", "opus"]
    filtered = filter_claude_mpm_args(test_args)

    if (
        "--resume" in filtered
        and "--monitor" not in filtered
        and "--websocket-port" not in filtered
    ):
        print(
            "✅ Filter function correctly filters MPM flags while preserving --resume"
        )
    else:
        print("❌ Filter function has incorrect filtering behavior")
        return False

    return True


def test_ensure_run_attributes():
    """Test that _ensure_run_attributes adds --resume to claude_args."""
    from claude_mpm.cli import _ensure_run_attributes

    # Create a mock args object
    class Args:
        def __init__(self):
            self.resume = True
            self.claude_args = []
            self.no_tickets = False
            self.no_hooks = False

    args = Args()
    _ensure_run_attributes(args)

    if "--resume" in args.claude_args:
        print("✅ _ensure_run_attributes adds --resume to claude_args")
    else:
        print("❌ _ensure_run_attributes doesn't add --resume to claude_args")
        return False

    # Test that it doesn't duplicate
    args = Args()
    args.claude_args = ["--resume"]
    _ensure_run_attributes(args)

    if args.claude_args.count("--resume") == 1:
        print("✅ _ensure_run_attributes doesn't duplicate --resume")
    else:
        print("❌ _ensure_run_attributes duplicates --resume")
        return False

    return True


def test_end_to_end_command_building():
    """Test that the complete command includes --resume when specified."""
    parser = create_parser()

    # Parse arguments with --resume
    args = parser.parse_args(["--resume", "--", "--model", "opus"])

    # Simulate what happens in run_session
    from claude_mpm.cli import _ensure_run_attributes

    _ensure_run_attributes(args)

    raw_claude_args = getattr(args, "claude_args", [])

    # Add --resume if flag is set (from run.py logic)
    resume_flag_present = getattr(args, "resume", False)
    if resume_flag_present and "--resume" not in raw_claude_args:
        raw_claude_args = ["--resume", *raw_claude_args]

    # Filter MPM-specific args
    filtered_args = filter_claude_mpm_args(raw_claude_args)

    if "--resume" in filtered_args:
        print("✅ End-to-end: --resume flag makes it to final command")
        print(f"   Final claude_args: {filtered_args}")
    else:
        print("❌ End-to-end: --resume flag lost in processing")
        print(f"   Final claude_args: {filtered_args}")
        return False

    return True


def main():
    """Run all tests and report results."""
    print("=" * 60)
    print("Testing --resume Flag Implementation")
    print("=" * 60)
    print()

    all_passed = True

    # Test 1: Bash wrapper
    print("Test 1: Bash Wrapper Recognition")
    print("-" * 40)
    if not test_bash_wrapper_recognition():
        all_passed = False
    print()

    # Test 2: Parser configuration
    print("Test 2: Argument Parser Configuration")
    print("-" * 40)
    if not test_parser_configuration():
        all_passed = False
    print()

    # Test 3: Filter function
    print("Test 3: Filter Function Behavior")
    print("-" * 40)
    if not test_filter_function():
        all_passed = False
    print()

    # Test 4: Ensure run attributes
    print("Test 4: Ensure Run Attributes")
    print("-" * 40)
    if not test_ensure_run_attributes():
        all_passed = False
    print()

    # Test 5: End-to-end
    print("Test 5: End-to-End Command Building")
    print("-" * 40)
    if not test_end_to_end_command_building():
        all_passed = False
    print()

    # Summary
    print("=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED - --resume flag is working correctly!")
    else:
        print("❌ SOME TESTS FAILED - --resume flag has issues")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
