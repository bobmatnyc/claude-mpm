#!/usr/bin/env python3
"""Test for duplicate messages during actual startup."""

import subprocess
import sys
import tempfile
from pathlib import Path


def test_actual_startup():
    """Test actual claude-mpm startup."""
    print("=" * 70)
    print("TESTING ACTUAL CLAUDE-MPM STARTUP")
    print("=" * 70)

    # Use the actual claude-mpm script
    claude_mpm_script = Path(__file__).parent / "claude-mpm"

    if not claude_mpm_script.exists():
        print(f"✗ claude-mpm script not found at {claude_mpm_script}")
        return False

    print(f"Using script: {claude_mpm_script}")

    # Create a temporary script that will exit immediately
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("exit\n")
        input_file = f.name

    try:
        # Run claude-mpm with immediate exit
        cmd = [
            str(claude_mpm_script),
            "run",
            "--input",
            input_file,
            "--non-interactive",
        ]

        print(f"\nRunning: {' '.join(cmd)}")

        # Run with timeout
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            env={**subprocess.os.environ, "LOG_LEVEL": "DEBUG"},
            check=False,
        )

        # Check output for duplicate messages
        full_output = result.stdout + result.stderr

        # Count success messages
        success_lines = []
        for i, line in enumerate(full_output.split("\n"), 1):
            if "Successfully loaded configuration" in line:
                success_lines.append((i, line))

        print("\n" + "=" * 70)
        print("RESULTS:")
        print(f"Success messages found: {len(success_lines)}")

        if len(success_lines) > 0:
            print("\nSuccess message occurrences:")
            for line_num, line in success_lines:
                print(f"  Line {line_num}: {line[:120]}")

        # Also check for Config singleton messages
        config_lines = []
        for line in full_output.split("\n"):
            if "Creating new Config singleton" in line:
                config_lines.append(("CREATE", line))
            elif "Reusing existing Config singleton" in line:
                config_lines.append(("REUSE", line))

        if config_lines:
            print("\nConfig singleton activity:")
            for action, line in config_lines[:10]:  # Show first 10
                print(f"  [{action}] {line[:100]}")

        if len(success_lines) == 0:
            print("⚠ No configuration success messages (may be normal)")
            return True
        if len(success_lines) == 1:
            print("✓ SUCCESS: Configuration loaded exactly once!")
            return True
        print(f"✗ FAILURE: Configuration loaded {len(success_lines)} times!")
        return False

    finally:
        Path(input_file).unlink()


def test_with_hooks():
    """Test with hooks enabled."""
    print("\n" + "=" * 70)
    print("TESTING WITH HOOKS ENABLED")
    print("=" * 70)

    # Run a simple command that would trigger hook service
    cmd = [sys.executable, "-m", "claude_mpm.cli", "agents", "list"]

    env = {
        **subprocess.os.environ,
        "PYTHONPATH": str(Path(__file__).parent.parent / "src"),
        "LOG_LEVEL": "DEBUG",
    }

    print(f"Running: {' '.join(cmd)}")

    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=10, env=env, check=False
    )

    full_output = result.stdout + result.stderr

    # Count success messages
    success_count = sum(
        1
        for line in full_output.split("\n")
        if "Successfully loaded configuration" in line
    )

    print(f"\nSuccess messages found: {success_count}")

    if success_count <= 1:
        print("✓ No duplicate messages with hooks")
        return True
    print(f"✗ Found {success_count} duplicate messages")
    # Show them
    for i, line in enumerate(full_output.split("\n"), 1):
        if "Successfully loaded configuration" in line:
            print(f"  Line {i}: {line[:120]}")
    return False


def main():
    """Run all tests."""
    print("=" * 70)
    print("ACTUAL STARTUP DUPLICATE MESSAGE TESTING")
    print("=" * 70)

    all_passed = True

    # Test 1: Actual startup
    try:
        if not test_actual_startup():
            all_passed = False
    except subprocess.TimeoutExpired:
        print("✗ Startup test timed out")
        all_passed = False
    except Exception as e:
        print(f"✗ Startup test failed: {e}")
        all_passed = False

    # Test 2: With hooks
    try:
        if not test_with_hooks():
            all_passed = False
    except Exception as e:
        print(f"✗ Hooks test failed: {e}")
        all_passed = False

    print("\n" + "=" * 70)
    if all_passed:
        print("✓ ALL TESTS PASSED")
    else:
        print("✗ SOME TESTS FAILED")
    print("=" * 70)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
