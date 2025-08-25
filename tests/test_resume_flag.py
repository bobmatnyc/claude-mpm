#!/usr/bin/env python3
"""Test script to debug --resume flag issue."""

import os
import subprocess
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from claude_mpm.cli.commands.run import filter_claude_mpm_args
from claude_mpm.cli.parsers.base_parser import create_parser, preprocess_args


def test_resume_flag_parsing():
    """Test how --resume flag is parsed and filtered."""

    test_cases = [
        # Test case 1: --resume with session ID (Claude native flag)
        (
            ["run", "--", "--resume", "session123"],
            "Claude native --resume with session ID",
        ),
        # Test case 2: --resume without session ID
        (["run", "--", "--resume"], "Claude native --resume without session ID"),
        # Test case 3: --mpm-resume (MPM flag)
        (["run", "--mpm-resume", "session456"], "MPM --mpm-resume with session ID"),
        # Test case 4: Mixed flags
        (
            ["run", "--monitor", "--", "--resume", "abc123", "--model", "opus"],
            "Mixed MPM and Claude flags",
        ),
        # Test case 5: Short form -r
        (["run", "--", "-r", "session789"], "Claude short form -r flag"),
    ]

    print("=" * 60)
    print("Testing --resume flag parsing and filtering")
    print("=" * 60)

    for argv, description in test_cases:
        print(f"\nTest: {description}")
        print(f"Input: {argv}")

        # Step 1: Preprocess arguments
        processed = preprocess_args(argv)
        print(f"After preprocess: {processed}")

        # Step 2: Parse arguments
        parser = create_parser("test")
        try:
            args = parser.parse_args(processed)
            print(f"Parsed args.command: {args.command}")
            print(f"Parsed args.claude_args: {getattr(args, 'claude_args', [])}")
            print(f"Parsed args.mpm_resume: {getattr(args, 'mpm_resume', None)}")

            # Step 3: Filter claude_mpm args
            if hasattr(args, "claude_args"):
                filtered = filter_claude_mpm_args(args.claude_args)
                print(f"After filtering: {filtered}")

        except SystemExit as e:
            print(f"Parser failed with exit code: {e.code}")
        except Exception as e:
            print(f"Parser error: {e}")

    print("\n" + "=" * 60)
    print("Test complete")
    print("=" * 60)


def test_actual_command():
    """Test the actual command execution to see what gets passed."""

    print("\n" + "=" * 60)
    print("Testing actual command execution")
    print("=" * 60)

    # Test command with --resume flag
    cmd = [
        sys.executable,
        "-m",
        "claude_mpm.cli",
        "run",
        "--debug",
        "--",
        "--resume",
        "test123",
        "--dry-run",
    ]

    print(f"\nExecuting: {' '.join(cmd)}")
    print("(Using --dry-run to prevent actual Claude launch)")

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=5, check=False
        )

        print(f"\nReturn code: {result.returncode}")

        if result.stdout:
            print("\nStdout:")
            for line in result.stdout.split("\n")[:20]:  # First 20 lines
                if "claude_args" in line.lower() or "resume" in line.lower():
                    print(f"  > {line}")

        if result.stderr:
            print("\nStderr:")
            for line in result.stderr.split("\n")[:20]:  # First 20 lines
                if "claude_args" in line.lower() or "resume" in line.lower():
                    print(f"  > {line}")

    except subprocess.TimeoutExpired:
        print("Command timed out (expected if Claude is waiting for input)")
    except Exception as e:
        print(f"Error running command: {e}")


if __name__ == "__main__":
    test_resume_flag_parsing()
    test_actual_command()
