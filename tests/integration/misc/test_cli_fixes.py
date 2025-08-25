#!/usr/bin/env python3
"""
Test script to validate CLI execution fixes.

WHY: This script verifies that the critical CLI execution issues have been
properly fixed, including:
1. CLI module execution with python -m claude_mpm.cli
2. Correct memory system imports
3. Proper error tracking and reporting

DESIGN DECISION: We test both the fixes and the verification script logic
to ensure the Docker container will properly detect and report failures.
"""

import shlex
import subprocess
import sys
from pathlib import Path


def run_subcommand(cmd, description):
    """Run a command and return success status and output."""
    print(f"\nTesting: {description}")
    print(f"Command: {cmd}")

    try:
        # Split command string into a list to avoid shell=True
        command_parts = shlex.split(cmd)
        result = subprocess.run(
            command_parts, capture_output=True, text=True, timeout=10, check=False
        )

        success = result.returncode == 0
        if success:
            print("✓ PASSED")
        else:
            print(f"✗ FAILED (exit code: {result.returncode})")
            if result.stderr:
                print(f"  Error: {result.stderr[:200]}")

        return success, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        print("✗ FAILED (timeout)")
        return False, "", "Command timed out"
    except Exception as e:
        print(f"✗ FAILED (exception: {e})")
        return False, "", str(e)


def main():
    """Run all tests and report results."""
    print("=== CLI Execution Fixes Verification ===")

    tests_run = 0
    tests_passed = 0
    failed_tests = []

    # Test 1: Check __main__.py exists
    tests_run += 1
    main_file = Path(__file__).parent.parent / "src/claude_mpm/cli/__main__.py"
    if main_file.exists():
        print(f"\n✓ Test 1: __main__.py file exists at {main_file}")
        tests_passed += 1
    else:
        print(f"\n✗ Test 1: __main__.py file missing at {main_file}")
        failed_tests.append("__main__.py file missing")

    # Test 2: CLI module execution with --version
    tests_run += 1
    success, stdout, stderr = run_subcommand(
        "python -m claude_mpm.cli --version", "CLI module execution with --version"
    )
    if success and "claude-mpm" in stdout.lower():
        tests_passed += 1
    else:
        failed_tests.append("CLI module execution with --version")

    # Test 3: CLI module execution with --help
    tests_run += 1
    success, stdout, stderr = run_subcommand(
        "python -m claude_mpm.cli --help", "CLI module execution with --help"
    )
    if success and "usage:" in stdout.lower():
        tests_passed += 1
    else:
        failed_tests.append("CLI module execution with --help")

    # Test 4: Memory system imports (general)
    tests_run += 1
    success, stdout, stderr = run_subcommand(
        "python -c \"from claude_mpm.services.memory import MemoryBuilder, MemoryRouter, MemoryOptimizer; print('Memory imports OK')\"",
        "General memory system imports",
    )
    if success and "Memory imports OK" in stdout:
        tests_passed += 1
    else:
        failed_tests.append("General memory system imports")

    # Test 5: Agent memory imports
    tests_run += 1
    success, stdout, stderr = run_subcommand(
        "python -c \"from claude_mpm.services.agents.memory import AgentMemoryManager, get_memory_manager; print('Agent memory imports OK')\"",
        "Agent-specific memory imports",
    )
    if success and "Agent memory imports OK" in stdout:
        tests_passed += 1
    else:
        failed_tests.append("Agent-specific memory imports")

    # Test 6: Agent services imports
    tests_run += 1
    success, stdout, stderr = run_subcommand(
        "python -c \"from claude_mpm.services.agents.deployment import AgentDeploymentService; from claude_mpm.services.agents.registry import AgentRegistry; print('Agent services imports OK')\"",
        "Agent services imports",
    )
    if success and "Agent services imports OK" in stdout:
        tests_passed += 1
    else:
        failed_tests.append("Agent services imports")

    # Print results
    print("\n" + "=" * 50)
    print("=== Test Results ===")
    print(f"Tests run: {tests_run}")
    print(f"Tests passed: {tests_passed}")
    print(f"Tests failed: {tests_run - tests_passed}")

    if failed_tests:
        print("\nFailed tests:")
        for test in failed_tests:
            print(f"  - {test}")

    # Exit with appropriate code
    if tests_passed == tests_run:
        print("\n✓ All tests passed successfully!")
        return 0
    print(f"\n✗ {len(failed_tests)} test(s) failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
