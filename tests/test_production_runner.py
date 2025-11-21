#!/usr/bin/env python3
"""
Test script for production benchmark runner.

This script validates the end-to-end flow:
1. Create task file
2. Invoke agent
3. Extract solution
4. Execute solution
5. Evaluate dimensions
6. Generate results

Usage:
    ./test_production_runner.py [--test-id <id>] [--verbose]
"""

import json
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from production_benchmark_runner import ProductionBenchmarkRunner


def print_separator(char="=", length=70):
    """Print a separator line."""
    print(char * length)


def test_single_python_test(test_id: Optional[str] = None, verbose: bool = False):
    """
    Test a single Python test end-to-end.

    Args:
        test_id: Specific test ID to run (e.g., 'python_easy_01')
        verbose: Print detailed output including solution code
    """
    # Setup
    base_path = Path(__file__).parent.parent
    runner = ProductionBenchmarkRunner(base_path, mock_mode=False)

    print_separator()
    print("PRODUCTION BENCHMARK RUNNER - TEST SCRIPT")
    print_separator()
    print()

    # Load Python tests
    try:
        suite = runner.load_agent_tests("python")
    except Exception as e:
        print(f"Error loading test suite: {e}")
        return False

    # Select test
    if test_id:
        test = next((t for t in suite["tests"] if t["id"] == test_id), None)
        if not test:
            print(f"Test ID '{test_id}' not found in Python test suite.")
            print(f"Available test IDs: {[t['id'] for t in suite['tests']]}")
            return False
    else:
        # Get first easy test by default
        test = next(
            (t for t in suite["tests"] if t["difficulty"] == "easy"), suite["tests"][0]
        )

    print(f"Test Selected: {test['name']} ({test['id']})")
    print(f"Difficulty: {test['difficulty']}")
    print(f"Category: {test['category']}")
    print(f"Description: {test['description'][:100]}...")
    print()
    print_separator("-")
    print()

    # Run test
    print("Running production execution...")
    print("(This will invoke the Python Engineer agent via claude-mpm CLI)")
    print()

    try:
        result = runner.run_single_test("python_engineer", test)
    except Exception as e:
        print(f"FATAL ERROR during test execution: {e}")
        import traceback

        traceback.print_exc()
        return False

    # Display result
    print()
    print_separator()
    print("TEST RESULT")
    print_separator()

    # Status indicator
    status_icon = "✓ PASS" if result["passed"] else "✗ FAIL"
    print(f"\nStatus: {status_icon}")
    print(f"Test ID: {result['test_id']}")
    print(f"Test Name: {result['test_name']}")
    print(f"Weighted Score: {result['weighted_score']:.2f}/10.0")
    print(f"Agent Execution Time: {result['execution_time']:.2f}s")

    # Dimension scores
    print("\nDimension Scores:")
    print_separator("-", 50)
    for dim, score in result["dimensions"].items():
        weight = runner.DIMENSION_WEIGHTS[dim]
        weighted_contribution = score * weight
        print(
            f"  {dim:20s}: {score:4.1f}/10.0 (weight: {weight:.0%}, contribution: {weighted_contribution:.2f})"
        )

    # Error handling
    if "error" in result:
        print(f"\n ERROR: {result['error']}")
        print("\nThis test did not complete successfully.")
        return False

    # Test execution details
    if "execution_details" in result and result["execution_details"].get(
        "test_results"
    ):
        test_results = result["execution_details"]["test_results"]
        passed_tests = sum(1 for r in test_results if r["passed"])
        total_tests = len(test_results)

        print(f"\nTest Cases: {passed_tests}/{total_tests} passed")

        if verbose or not result["passed"]:
            print_separator("-", 50)
            for i, tr in enumerate(test_results, 1):
                status = "✓" if tr["passed"] else "✗"
                print(f"  [{status}] Test {i}:")
                print(f"      Input: {tr['input']}")
                print(f"      Expected: {tr['expected']}")
                print(f"      Actual: {tr.get('actual', 'N/A')}")
                if tr.get("error"):
                    print(f"      Error: {tr['error']}")

    # Solution code
    if verbose and "solution" in result:
        print("\nSolution Code:")
        print_separator("-", 50)
        print(result["solution"])
        if len(result.get("solution", "")) >= 500:
            print("\n... (truncated at 500 chars)")

    print()
    print_separator()
    print()

    # Summary
    if result["passed"]:
        print(f"SUCCESS: Test completed with score {result['weighted_score']:.2f}/10.0")
        return True
    print(f"FAILURE: Test failed with score {result['weighted_score']:.2f}/10.0")
    return False


def test_multiple_tests(count: int = 3):
    """
    Test multiple Python tests to validate consistency.

    Args:
        count: Number of tests to run
    """
    base_path = Path(__file__).parent.parent
    runner = ProductionBenchmarkRunner(base_path, mock_mode=False)

    print_separator()
    print(f"RUNNING {count} TESTS FOR VALIDATION")
    print_separator()
    print()

    # Load Python tests
    suite = runner.load_agent_tests("python")

    # Select diverse tests (easy, medium, hard)
    tests_by_difficulty = {
        "easy": [t for t in suite["tests"] if t["difficulty"] == "easy"],
        "medium": [t for t in suite["tests"] if t["difficulty"] == "medium"],
        "hard": [t for t in suite["tests"] if t["difficulty"] == "hard"],
    }

    selected_tests = []
    for difficulty in ["easy", "medium", "hard"]:
        if tests_by_difficulty[difficulty]:
            selected_tests.append(tests_by_difficulty[difficulty][0])
            if len(selected_tests) >= count:
                break

    results = []
    for i, test in enumerate(selected_tests[:count], 1):
        print(f"\n[{i}/{count}] Testing: {test['name']} ({test['difficulty']})")
        print_separator("-")

        try:
            result = runner.run_single_test("python_engineer", test)
            results.append(result)

            status = "✓ PASS" if result["passed"] else "✗ FAIL"
            print(f"  Result: {status} - Score: {result['weighted_score']:.2f}/10.0")

        except Exception as e:
            print(f"  Error: {e}")
            results.append(None)

    # Summary
    print()
    print_separator()
    print("SUMMARY")
    print_separator()

    valid_results = [r for r in results if r is not None]
    passed = sum(1 for r in valid_results if r["passed"])

    print(f"\nTests Run: {len(valid_results)}/{count}")
    print(f"Tests Passed: {passed}/{len(valid_results)}")
    print(f"Pass Rate: {passed / len(valid_results) * 100:.1f}%")

    if valid_results:
        avg_score = sum(r["weighted_score"] for r in valid_results) / len(valid_results)
        print(f"Average Score: {avg_score:.2f}/10.0")

    print()

    return passed == len(valid_results)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test production benchmark runner")
    parser.add_argument(
        "--test-id", help="Specific test ID to run (e.g., python_easy_01)"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed output including solution code",
    )
    parser.add_argument(
        "--multiple",
        type=int,
        metavar="COUNT",
        help="Run multiple tests for validation (specify count)",
    )

    args = parser.parse_args()

    try:
        if args.multiple:
            success = test_multiple_tests(args.multiple)
        else:
            success = test_single_python_test(
                test_id=args.test_id, verbose=args.verbose
            )

        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
        sys.exit(130)
    except Exception as e:
        print(f"\n\nFATAL ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
