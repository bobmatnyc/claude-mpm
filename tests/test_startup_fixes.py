#!/usr/bin/env python3
"""
Test script to verify the three startup fixes:
1. --resume flag is properly passed through
2. No duplicate initialization messages
3. Local development paths are used instead of pipx paths

Run this from the claude-mpm development directory.
"""

import os
import subprocess
import sys
from pathlib import Path

# Set development mode to ensure we use local paths
os.environ["CLAUDE_MPM_DEV_MODE"] = "1"


def test_resume_flag():
    """Test that --resume flag is properly passed through."""
    print("\n=== Testing --resume flag ===")

    # Test with --resume flag (should work without error)
    cmd = [sys.executable, "-m", "claude_mpm.cli", "--resume", "last", "--dry-run"]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=5, check=False
        )

        # Check if mpm_resume is being accessed (no AttributeError)
        if "AttributeError" in result.stderr and "mpm_resume" in result.stderr:
            print("❌ FAILED: --resume flag not properly passed through")
            print(f"   Error: {result.stderr}")
            return False
        print("✅ PASSED: --resume flag is properly handled")
        return True

    except subprocess.TimeoutExpired:
        print("⚠️  Command timed out (might be waiting for input)")
        return False
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_duplicate_messages():
    """Test that initialization messages aren't duplicated."""
    print("\n=== Testing for duplicate initialization messages ===")

    # Run with debug logging to see initialization messages
    cmd = [sys.executable, "-m", "claude_mpm.cli", "--logging", "DEBUG", "--help"]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=5, check=False
        )

        # Count occurrences of the initialization message
        init_message = "Working directory for deployment:"
        count = result.stderr.count(init_message) + result.stdout.count(init_message)

        if count > 1:
            print(f"❌ FAILED: Initialization message appears {count} times")
            print("   This indicates services are being initialized multiple times")
            return False
        if count == 1:
            print(
                "⚠️  WARNING: Initialization message appears once (expected 0 for --help)"
            )
            return True
        print("✅ PASSED: No duplicate initialization messages")
        return True

    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_development_paths():
    """Test that local development paths are used instead of pipx paths."""
    print("\n=== Testing development path detection ===")

    # Create a small Python script to check the paths
    test_script = """
import sys
sys.path.insert(0, "src")
from claude_mpm.core.unified_paths import UnifiedPathManager
pm = UnifiedPathManager()
print(f"Deployment context: {pm._deployment_context}")
print(f"Framework root: {pm.framework_root}")
print(f"Package root: {pm.package_root}")
print(f"Scripts dir: {pm.get_scripts_dir()}")
"""

    try:
        result = subprocess.run(
            [sys.executable, "-c", test_script],
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
            check=False,  # Run from current directory
        )

        output = result.stdout + result.stderr

        # Check if we're using development paths
        if "DeploymentContext.DEVELOPMENT" in output:
            print("✅ PASSED: Using development deployment context")
        else:
            print("❌ FAILED: Not using development deployment context")
            print(f"   Output: {output}")
            return False

        # Check that paths don't contain "pipx"
        if "pipx" in output.lower():
            print("❌ FAILED: Paths still contain 'pipx'")
            print(f"   Output: {output}")
            return False
        print("✅ PASSED: Paths don't contain 'pipx'")

        # Check that paths point to the current project
        cwd = str(Path.cwd())
        if cwd in output:
            print(f"✅ PASSED: Paths point to current project ({cwd})")
            return True
        print("⚠️  WARNING: Paths might not point to current project")
        print(f"   Output: {output}")
        return True

    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def main():
    """Run all tests and report results."""
    print("Testing claude-mpm startup fixes")
    print("=" * 50)

    # Check we're in a development directory
    if not (Path.cwd() / "src" / "claude_mpm").exists():
        print(
            "ERROR: This script must be run from the claude-mpm development directory"
        )
        print(f"Current directory: {Path.cwd()}")
        sys.exit(1)

    results = []

    # Run tests
    results.append(("--resume flag", test_resume_flag()))
    results.append(("Duplicate messages", test_duplicate_messages()))
    results.append(("Development paths", test_development_paths()))

    # Report summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)

    passed = 0
    failed = 0

    for test_name, result in results:
        if result:
            print(f"✅ {test_name}: PASSED")
            passed += 1
        else:
            print(f"❌ {test_name}: FAILED")
            failed += 1

    print(f"\nTotal: {passed} passed, {failed} failed")

    if failed == 0:
        print("\n🎉 All tests passed! The fixes are working correctly.")
        sys.exit(0)
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please review the output above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
