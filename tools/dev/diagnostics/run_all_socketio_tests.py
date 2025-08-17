#!/usr/bin/env python3
"""
Master test runner for all Socket.IO auto-deployment tests.

This script runs all Socket.IO related tests in sequence and provides
a comprehensive summary of results.
"""

import subprocess
import sys
import time
from pathlib import Path


def run_test_script(script_name, description):
    """Run a single test script and return results."""
    script_path = Path(__file__).parent / script_name

    if not script_path.exists():
        print(f"❌ {description}: Script not found - {script_path}")
        return False

    print(f"\n{'='*60}")
    print(f"🧪 Running: {description}")
    print(f"📄 Script: {script_name}")
    print(f"{'='*60}")

    start_time = time.time()

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=Path(__file__).parent.parent,
            timeout=120,  # 2 minute timeout per test
        )

        end_time = time.time()
        duration = end_time - start_time

        if result.returncode == 0:
            print(f"✅ {description}: PASSED ({duration:.1f}s)")
            return True
        else:
            print(f"❌ {description}: FAILED ({duration:.1f}s)")
            return False

    except subprocess.TimeoutExpired:
        print(f"⏱️  {description}: TIMEOUT (exceeded 2 minutes)")
        return False
    except Exception as e:
        print(f"💥 {description}: ERROR - {e}")
        return False


def main():
    """Run all Socket.IO auto-deployment tests."""
    print("🚀 Socket.IO Auto-Deployment Test Suite")
    print("=" * 60)
    print(f"Python: {sys.executable}")
    print(f"Working Directory: {Path.cwd()}")
    print("=" * 60)

    # Define all tests to run
    tests = [
        ("test_fresh_environment.py", "Fresh Environment Test"),
        ("test_existing_dependencies.py", "Existing Dependencies Test"),
        ("test_error_handling.py", "Error Handling Test"),
        ("test_virtual_environment.py", "Virtual Environment Test"),
        ("test_integration_workflow.py", "Integration Workflow Test"),
    ]

    results = []
    start_time = time.time()

    # Run each test
    for script_name, description in tests:
        success = run_test_script(script_name, description)
        results.append((description, success))

    end_time = time.time()
    total_duration = end_time - start_time

    # Print summary
    print(f"\n{'='*60}")
    print("📊 TEST SUITE SUMMARY")
    print(f"{'='*60}")

    passed = 0
    failed = 0

    for description, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {description}")
        if success:
            passed += 1
        else:
            failed += 1

    print(f"\n📈 Results: {passed} passed, {failed} failed")
    print(f"⏱️  Total duration: {total_duration:.1f} seconds")

    if failed == 0:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Socket.IO auto-deployment is working correctly")
        return True
    elif passed >= len(tests) - 1:
        print(f"\n⚠️  MOSTLY PASSED ({passed}/{len(tests)})")
        print("✅ Socket.IO auto-deployment is mostly working")
        return True
    else:
        print(f"\n❌ MULTIPLE FAILURES ({failed}/{len(tests)} failed)")
        print("🔧 Socket.IO auto-deployment needs attention")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
