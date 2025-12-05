#!/usr/bin/env python3
"""
Run PM behavior validation tests and generate report.

This script runs the PM behavior validation test suite created to verify
the ticketing delegation fixes (commit 0872411a).

Usage:
    # Test with compliant responses (should pass)
    python tests/eval/run_pm_validation.py

    # Test with violation responses (should fail, proving detection works)
    python tests/eval/run_pm_validation.py --use-violations

    # Verbose output
    python tests/eval/run_pm_validation.py -v

    # Run specific test
    python tests/eval/run_pm_validation.py --test linear_url_delegation_fix

    # Generate detailed report
    python tests/eval/run_pm_validation.py --report

Examples:
    # Quick validation that PM is compliant
    python tests/eval/run_pm_validation.py

    # Verify detection works correctly
    python tests/eval/run_pm_validation.py --use-violations

    # Full report with all scenarios
    python tests/eval/run_pm_validation.py -v --report
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Run PM behavior validation tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("Usage:")[1] if "Usage:" in __doc__ else "",
    )

    parser.add_argument(
        "--use-violations",
        action="store_true",
        help="Use violation responses to test detection (should fail)",
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    parser.add_argument(
        "--test", type=str, default=None, help="Run specific test by scenario ID"
    )

    parser.add_argument(
        "--report", action="store_true", help="Generate detailed HTML report"
    )

    parser.add_argument(
        "--pytest-args",
        type=str,
        default="",
        help="Additional pytest arguments (quoted string)",
    )

    args = parser.parse_args()

    # Build pytest command
    test_file = "tests/eval/test_cases/test_pm_behavior_validation.py"

    cmd = ["pytest", test_file, "-m", "integration"]

    # Add verbosity
    if args.verbose:
        cmd.append("-vv")
        cmd.append("-s")  # Show print statements
    else:
        cmd.append("-v")

    # Add violation mode if requested
    if args.use_violations:
        cmd.append("--use-violation-responses")

    # Add specific test filter
    if args.test:
        cmd.extend(["-k", args.test])

    # Add report generation
    if args.report:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"tests/eval/reports/pm_validation_{timestamp}.html"
        cmd.extend(["--html", report_file, "--self-contained-html"])

    # Add custom pytest args
    if args.pytest_args:
        cmd.extend(args.pytest_args.split())

    # Print header
    print("=" * 70)
    print("PM Behavior Validation Test Suite")
    print("=" * 70)
    print(
        f"Mode: {'Violation Detection Test' if args.use_violations else 'Compliance Test'}"
    )
    print(f"File: {test_file}")

    if args.test:
        print(f"Filter: {args.test}")

    if args.report:
        print(f"Report: {report_file}")

    print("=" * 70)
    print()

    # Show command being run
    if args.verbose:
        print(f"Running: {' '.join(cmd)}")
        print()

    # Run tests
    result = subprocess.run(cmd, check=False)

    # Print summary
    print()
    print("=" * 70)

    if result.returncode == 0:
        if args.use_violations:
            print("✅ VIOLATION DETECTION WORKING")
            print("All violations were correctly detected by metrics.")
            print()
            print("This confirms that the detection system can catch")
            print("the types of violations that occurred before the fix.")
        else:
            print("✅ ALL VALIDATION TESTS PASSED")
            print("PM behavior is compliant with instructions.")
            print()
            print("Circuit Breaker #6 is properly enforced:")
            print("- PM delegates all ticketing operations")
            print("- PM does NOT use forbidden tools")
            print("- PM reports with agent attribution")
    elif args.use_violations:
        print("❌ VIOLATION DETECTION FAILED")
        print("Some violations were NOT detected by metrics.")
        print()
        print("⚠️  This indicates the metrics need improvement")
        print("   to catch the types of violations being tested.")
    else:
        print("❌ SOME VALIDATION TESTS FAILED")
        print("PM behavior is NOT fully compliant.")
        print()
        print("⚠️  Circuit Breaker #6 violations detected:")
        print("   PM may still be using forbidden tools directly")
        print("   instead of delegating to ticketing agent.")
        print()
        print("Review the test output above for specific failures.")

    print("=" * 70)

    if args.report:
        print()
        print(f"📊 Detailed report: {report_file}")

    print()

    return result.returncode


def print_usage_examples():
    """Print helpful usage examples."""
    print("""
Common Usage Patterns:

1. Quick Validation (default)
   python tests/eval/run_pm_validation.py
   → Tests that PM correctly delegates (should PASS)

2. Test Detection System
   python tests/eval/run_pm_validation.py --use-violations
   → Tests that metrics detect violations (should FAIL, proving detection works)

3. Debug Specific Scenario
   python tests/eval/run_pm_validation.py --test linear_url -v
   → Run only Linear URL test with verbose output

4. Full Analysis
   python tests/eval/run_pm_validation.py -v --report
   → Verbose output + HTML report generation

5. CI/CD Integration
   python tests/eval/run_pm_validation.py --pytest-args "--tb=short"
   → Concise output for automated pipelines
""")


if __name__ == "__main__":
    # Print usage examples if --help-examples
    if len(sys.argv) > 1 and sys.argv[1] == "--help-examples":
        print_usage_examples()
        sys.exit(0)

    sys.exit(main())
