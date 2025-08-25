#!/usr/bin/env python3
"""Test script to verify the cleanup command fix."""

import subprocess
import sys


def test_cleanup_with_echo():
    """Test cleanup command with echo piping input."""
    print("Testing cleanup command with echo input...")

    # Test 'n' response (should cancel) - without dry-run flag to trigger prompt
    print("\n1. Testing 'n' response (should cancel):")
    # Note: We'll use --dry-run after the prompt to avoid actual changes
    # but we need to test the prompt itself
    result = subprocess.run(
        'echo "n" | claude-mpm cleanup-memory',
        shell=True,
        capture_output=True,
        text=True, check=False,
    )

    if "Cleanup cancelled" in result.stdout:
        print("✅ 'n' response works correctly - cleanup cancelled")
    else:
        print("❌ 'n' response may have failed (check if .claude.json exists)")
        print("stdout:", result.stdout[:500])  # Truncate for readability
        print("stderr:", result.stderr[:500] if result.stderr else "No errors")

    # Test with dry-run to check if prompt appears correctly
    print("\n2. Testing with --dry-run (should NOT prompt):")
    result = subprocess.run(
        "claude-mpm cleanup-memory --dry-run",
        shell=True,
        capture_output=True,
        text=True, check=False,
    )

    if "Continue?" not in result.stdout and "DRY RUN MODE" in result.stdout:
        print("✅ --dry-run correctly skips prompt")
    else:
        print("❌ --dry-run behavior incorrect")
        print("stdout:", result.stdout[:500])


def test_cleanup_with_force():
    """Test cleanup command with --force flag (no prompt)."""
    print("\n3. Testing with --force flag (should skip prompt):")

    result = subprocess.run(
        "claude-mpm cleanup-memory --dry-run --force",
        shell=True,
        capture_output=True,
        text=True, check=False,
    )

    if "Continue?" not in result.stdout and "DRY RUN MODE" in result.stdout:
        print("✅ --force flag works correctly - no prompt shown")
    else:
        print("❌ --force flag failed")
        print("stdout:", result.stdout)
        print("stderr:", result.stderr)


def test_cleanup_interactive():
    """Test interactive mode (for manual testing)."""
    print("\n4. Interactive test (manual - requires user input):")
    print("   Run: claude-mpm cleanup-memory --dry-run")
    print("   This should now accept keyboard input properly")


if __name__ == "__main__":
    print("=== Testing Cleanup Command Fix ===\n")

    # Check if claude-mpm is available
    result = subprocess.run(["which", "claude-mpm"], capture_output=True, check=False)
    if result.returncode != 0:
        print("❌ claude-mpm not found in PATH")
        print("   Please ensure claude-mpm is installed and in your PATH")
        sys.exit(1)

    test_cleanup_with_echo()
    test_cleanup_with_force()
    test_cleanup_interactive()

    print("\n=== Test Complete ===")
    print("Note: For full interactive testing, run:")
    print("  claude-mpm cleanup-memory --dry-run")
    print("And verify you can type 'y' or 'n' when prompted")
