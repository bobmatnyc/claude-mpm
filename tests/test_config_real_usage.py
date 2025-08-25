#!/usr/bin/env python3
"""Test configuration loading in real usage scenario."""

import re
import subprocess
import sys
from pathlib import Path


def count_success_messages(output):
    """Count configuration success messages in output."""
    pattern = r"✓ Successfully loaded configuration"
    matches = re.findall(pattern, output)
    return len(matches)


def test_claude_mpm_run():
    """Test the actual claude-mpm run command."""
    print("=" * 70)
    print("Testing 'claude-mpm run' command")
    print("=" * 70)

    # Run claude-mpm with a simple command that exits quickly
    cmd = [sys.executable, "scripts/claude-mpm", "run", "--help"]

    print(f"\nRunning: {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
        check=False,
    )

    # Combine stdout and stderr for analysis
    full_output = result.stdout + result.stderr

    # Count success messages
    success_count = count_success_messages(full_output)

    print(f"\nSuccess messages found: {success_count}")

    # Show relevant lines
    print("\nRelevant output lines:")
    for line in full_output.split("\n"):
        if any(
            keyword in line
            for keyword in [
                "Successfully loaded configuration",
                "Creating new Config singleton",
                "Reusing existing Config singleton",
            ]
        ):
            print(f"  {line}")

    # Determine pass/fail
    if success_count <= 1:
        print(f"\n✓ PASS: {success_count} success message(s) (expected 0 or 1)")
        return True
    print(f"\n✗ FAIL: {success_count} success messages (expected 0 or 1)")
    return False


def test_claude_mpm_agents():
    """Test the agents command."""
    print("\n" + "=" * 70)
    print("Testing 'claude-mpm agents list' command")
    print("=" * 70)

    # Run claude-mpm agents list
    cmd = [sys.executable, "scripts/claude-mpm", "agents", "list"]

    print(f"\nRunning: {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
        check=False,
    )

    # Combine stdout and stderr for analysis
    full_output = result.stdout + result.stderr

    # Count success messages
    success_count = count_success_messages(full_output)

    print(f"\nSuccess messages found: {success_count}")

    # Determine pass/fail
    if success_count <= 1:
        print(f"\n✓ PASS: {success_count} success message(s) (expected 0 or 1)")
        return True
    print(f"\n✗ FAIL: {success_count} success messages (expected 0 or 1)")
    return False


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("Real Usage Configuration Test")
    print("=" * 70)

    tests = [test_claude_mpm_run, test_claude_mpm_agents]

    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"\n✗ Test failed with error: {e}")
            results.append(False)

    print("\n" + "=" * 70)
    print("FINAL RESULTS:")
    print("=" * 70)

    for i, (test, result) in enumerate(zip(tests, results), 1):
        status = "PASS" if result else "FAIL"
        print(f"  Test {i} ({test.__name__}): {status}")

    all_pass = all(results)
    print(f"\nOverall: {'✓ ALL TESTS PASSED' if all_pass else '✗ SOME TESTS FAILED'}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
