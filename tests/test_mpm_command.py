#!/usr/bin/env python3
"""Test script to verify /mpm:test command functionality."""

import sys
import subprocess
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_oneshot_mode():
    """Test /mpm:test in oneshot mode."""
    print("Testing /mpm:test in oneshot mode...")
    
    cmd = ["./claude-mpm", "run", "-i", "/mpm:test", "--non-interactive"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if "Hello World" in result.stdout:
        print("✓ Oneshot mode: PASSED")
        return True
    else:
        print("✗ Oneshot mode: FAILED")
        print(f"  Output: {result.stdout}")
        print(f"  Error: {result.stderr}")
        return False


def test_interactive_wrapper():
    """Test /mpm:test with interactive wrapper."""
    print("\nTesting /mpm:test with interactive wrapper...")
    
    # Test the wrapper directly
    wrapper_path = Path(__file__).parent / "interactive_wrapper.py"
    cmd = [sys.executable, str(wrapper_path)]
    
    # Send /mpm:test command
    result = subprocess.run(
        cmd,
        input="/mpm:test\nexit\n",
        capture_output=True,
        text=True
    )
    
    if "Hello World" in result.stdout:
        print("✓ Interactive wrapper: PASSED")
        return True
    else:
        print("✗ Interactive wrapper: FAILED")
        print(f"  Output: {result.stdout}")
        print(f"  Error: {result.stderr}")
        return False


def test_cli_with_intercept():
    """Test /mpm:test through CLI with --intercept-commands."""
    print("\nTesting /mpm:test through CLI with --intercept-commands...")
    
    cmd = ["./claude-mpm", "run", "--intercept-commands"]
    
    # Send /mpm:test command
    result = subprocess.run(
        cmd,
        input="/mpm:test\nexit\n",
        capture_output=True,
        text=True
    )
    
    if "Hello World" in result.stdout:
        print("✓ CLI with --intercept-commands: PASSED")
        return True
    else:
        print("✗ CLI with --intercept-commands: FAILED")
        print(f"  Output: {result.stdout}")
        print(f"  Error: {result.stderr}")
        return False


def main():
    """Run all tests."""
    print("=== Testing /mpm:test Command ===\n")
    
    tests = [
        test_oneshot_mode,
        test_interactive_wrapper,
        test_cli_with_intercept
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"✗ {test.__name__}: EXCEPTION - {e}")
            results.append(False)
    
    print("\n=== Summary ===")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())