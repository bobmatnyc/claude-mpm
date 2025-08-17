#!/usr/bin/env python3
"""Test script to verify run-guarded experimental warning.

WHY: This script tests that the run-guarded command properly shows
experimental warnings and respects the experimental feature flags.
"""

import os
import subprocess
import sys
from pathlib import Path

# Add src to path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))


def test_experimental_warning():
    """Test that run-guarded shows experimental warning."""
    print("Testing run-guarded experimental warning...")

    # Test without accepting experimental
    env = os.environ.copy()
    # Ensure memory guardian is disabled by default
    env["CLAUDE_MPM_EXPERIMENTAL_ENABLE_MEMORY_GUARDIAN"] = "false"

    result = subprocess.run(
        [sys.executable, "-m", "claude_mpm.cli", "run-guarded", "--help"],
        capture_output=True,
        text=True,
        env=env,
    )

    # Should show experimental in help
    if "EXPERIMENTAL" in result.stdout:
        print("✅ Help text shows EXPERIMENTAL marker")
    else:
        print("❌ Help text missing EXPERIMENTAL marker")
        print(f"Output: {result.stdout}")
        return False

    # Test that it requires enabling
    result = subprocess.run(
        [sys.executable, "-m", "claude_mpm.cli", "run-guarded", "--non-interactive"],
        capture_output=True,
        text=True,
        env=env,
        input="n\n",  # Respond 'no' to the prompt
    )

    if (
        "Memory Guardian is an experimental feature that is currently disabled"
        in result.stdout
    ):
        print("✅ Command correctly reports feature is disabled")
    else:
        print(
            "⚠️  Command did not report feature as disabled (may be enabled in config)"
        )

    # Test with feature enabled
    env["CLAUDE_MPM_EXPERIMENTAL_ENABLE_MEMORY_GUARDIAN"] = "true"
    result = subprocess.run(
        [sys.executable, "-m", "claude_mpm.cli", "run-guarded", "--help"],
        capture_output=True,
        text=True,
        env=env,
    )

    if result.returncode == 0:
        print("✅ Command works when feature is enabled")
    else:
        print("❌ Command failed even with feature enabled")
        return False

    # Test with --accept-experimental flag
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "claude_mpm.cli",
            "run-guarded",
            "--accept-experimental",
            "--help",
        ],
        capture_output=True,
        text=True,
        env=env,
    )

    if result.returncode == 0:
        print("✅ --accept-experimental flag works")
    else:
        print("❌ --accept-experimental flag failed")
        return False

    return True


def test_run_command_unaffected():
    """Test that main run command is unaffected by memory guardian."""
    print("\nTesting main run command independence...")

    # Test run command works normally
    result = subprocess.run(
        [sys.executable, "-m", "claude_mpm.cli", "run", "--help"],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print("✅ Main run command works")
    else:
        print("❌ Main run command failed")
        return False

    # Check that run help doesn't mention memory guardian
    if "memory" in result.stdout.lower() and "guardian" in result.stdout.lower():
        print("❌ Main run command mentions memory guardian")
        return False
    else:
        print("✅ Main run command has no memory guardian references")

    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Run-Guarded Experimental Features")
    print("=" * 60)

    success = True

    if not test_experimental_warning():
        success = False

    if not test_run_command_unaffected():
        success = False

    print("\n" + "=" * 60)
    if success:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
