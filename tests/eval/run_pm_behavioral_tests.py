#!/usr/bin/env python3
"""
PM Behavioral Compliance Test Runner

Runs comprehensive PM behavioral tests. Integrates with release process
to validate PM instruction changes.

Usage:
    # Run all behavioral tests
    python tests/eval/run_pm_behavioral_tests.py

    # Run specific category
    python tests/eval/run_pm_behavioral_tests.py --category delegation

    # Run critical tests only
    python tests/eval/run_pm_behavioral_tests.py --severity critical

    # Run circuit breaker tests
    python tests/eval/run_pm_behavioral_tests.py --category circuit_breaker

    # Generate compliance report
    python tests/eval/run_pm_behavioral_tests.py --report

    # Release process integration (exit non-zero on failure)
    python tests/eval/run_pm_behavioral_tests.py --release-check
"""

import argparse
import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any


def main():
    parser = argparse.ArgumentParser(
        description="Run PM behavioral compliance tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all behavioral tests
  %(prog)s

  # Run delegation tests only
  %(prog)s --category delegation

  # Run critical severity tests
  %(prog)s --severity critical

  # Run with HTML report
  %(prog)s --report

  # Release check mode (fails on any violation)
  %(prog)s --release-check --severity critical

Categories:
  delegation      - Delegation-first principle behaviors
  tools           - Tool usage behaviors
  circuit_breaker - Circuit breaker compliance
  workflow        - 5-phase workflow sequence
  evidence        - Assertion-evidence requirements
  file_tracking   - Git file tracking protocol
  memory          - Memory management behaviors

Severity Levels:
  critical - Fundamental PM violations (must never occur)
  high     - Important requirements (indicates training issue)
  medium   - Best practice violations (should be corrected)
  low      - Nice-to-have behaviors (informational)
        """
    )

    parser.add_argument(
        "--category",
        choices=["delegation", "tools", "circuit_breaker", "workflow",
                 "evidence", "file_tracking", "memory", "all"],
        default="all",
        help="Test category to run (default: all)"
    )

    parser.add_argument(
        "--severity",
        choices=["critical", "high", "medium", "low", "all"],
        default="all",
        help="Test severity filter (default: all)"
    )

    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate HTML compliance report"
    )

    parser.add_argument(
        "--release-check",
        action="store_true",
        help="Run as part of release process (exit non-zero on any failure)"
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output"
    )

    parser.add_argument(
        "--list-tests",
        action="store_true",
        help="List all available tests and exit"
    )

    args = parser.parse_args()

    # List tests mode
    if args.list_tests:
        list_available_tests()
        return 0

    # Print header
    print("=" * 70)
    print("PM Behavioral Compliance Test Suite")
    print("=" * 70)
    print(f"Category:      {args.category}")
    print(f"Severity:      {args.severity}")
    print(f"Release Check: {args.release_check}")
    print(f"Report:        {args.report}")
    print("=" * 70 + "\n")

    # Build pytest command
    test_file = Path(__file__).parent / "test_cases" / "test_pm_behavioral_compliance.py"

    cmd = [
        "pytest",
        str(test_file),
        "-v" if args.verbose else "-q",
    ]

    # Build marker expression
    markers = ["behavioral"]

    if args.category != "all":
        markers.append(args.category)

    if args.severity != "all":
        markers.append(args.severity)

    if markers:
        cmd.extend(["-m", " and ".join(markers)])

    # Add report generation
    if args.report:
        report_dir = Path(__file__).parent / "reports"
        report_dir.mkdir(exist_ok=True)
        report_file = report_dir / "pm_behavioral_compliance.html"
        cmd.extend(["--html", str(report_file), "--self-contained-html"])

    # Run tests
    print("Running tests...")
    print(f"Command: {' '.join(cmd)}\n")

    result = subprocess.run(cmd, capture_output=True, text=True)

    # Print output
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)

    # Generate summary
    print("\n" + "=" * 70)
    if result.returncode == 0:
        print("✅ ALL TESTS PASSED")
        print("PM behavioral compliance verified")
    else:
        print("❌ TESTS FAILED")
        print("PM behavioral compliance violations detected")

    print("=" * 70)

    # Generate report
    if args.report:
        generate_compliance_report(result.returncode, args)

    # Release check mode: fail on any test failure
    if args.release_check and result.returncode != 0:
        print("\n" + "=" * 70)
        print("❌ RELEASE CHECK FAILED")
        print("PM behavioral compliance tests have failures.")
        print("Fix violations before releasing PM instruction changes.")
        print("=" * 70)
        return 1

    return result.returncode


def list_available_tests():
    """List all available test scenarios."""
    scenarios_file = Path(__file__).parent / "scenarios" / "pm_behavioral_requirements.json"

    with open(scenarios_file) as f:
        data = json.load(f)
        scenarios = data["scenarios"]

    print("Available Test Scenarios")
    print("=" * 70)
    print(f"Total scenarios: {len(scenarios)}\n")

    # Group by category
    by_category = {}
    for scenario in scenarios:
        category = scenario["category"]
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(scenario)

    # Print by category
    for category, tests in sorted(by_category.items()):
        print(f"\n{category.upper()} ({len(tests)} tests)")
        print("-" * 70)

        # Group by severity
        by_severity = {"critical": [], "high": [], "medium": [], "low": []}
        for test in tests:
            by_severity[test["severity"]].append(test)

        for severity in ["critical", "high", "medium", "low"]:
            if by_severity[severity]:
                print(f"  {severity.upper()}: {len(by_severity[severity])} tests")
                for test in by_severity[severity]:
                    print(f"    - {test['scenario_id']}: {test['name']}")


def generate_compliance_report(exit_code: int, args: argparse.Namespace):
    """Generate PM behavioral compliance report."""
    report_dir = Path(__file__).parent / "reports"
    report_dir.mkdir(exist_ok=True)

    # Generate markdown summary
    summary_file = report_dir / "pm_behavioral_summary.md"

    with open(summary_file, "w") as f:
        f.write("# PM Behavioral Compliance Report\n\n")
        f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
        f.write(f"**Category:** {args.category}\n")
        f.write(f"**Severity:** {args.severity}\n")
        f.write(f"**Status:** {'PASSED ✅' if exit_code == 0 else 'FAILED ❌'}\n\n")

        f.write("## Test Configuration\n\n")
        f.write(f"- Category filter: `{args.category}`\n")
        f.write(f"- Severity filter: `{args.severity}`\n")
        f.write(f"- Release check: `{args.release_check}`\n\n")

        f.write("## Results Summary\n\n")
        if exit_code == 0:
            f.write("All PM behavioral compliance tests passed.\n\n")
            f.write("The PM agent correctly:\n")
            f.write("- Delegates work to specialized agents\n")
            f.write("- Uses tools appropriately\n")
            f.write("- Complies with all circuit breakers\n")
            f.write("- Follows 5-phase workflow sequence\n")
            f.write("- Provides evidence for all assertions\n")
            f.write("- Tracks files immediately after creation\n")
            f.write("- Manages memory correctly\n\n")
        else:
            f.write("**WARNING:** PM behavioral compliance violations detected.\n\n")
            f.write("Review the detailed HTML report for specific violations.\n\n")
            f.write("Common violation categories:\n")
            f.write("- **Circuit Breaker Violations:** PM performing work directly instead of delegating\n")
            f.write("- **Evidence Violations:** Making claims without verification evidence\n")
            f.write("- **Tool Misuse:** Using incorrect tools for tasks\n")
            f.write("- **Workflow Violations:** Skipping mandatory phases\n\n")

        f.write("## Next Steps\n\n")
        if exit_code != 0:
            f.write("1. Review HTML report for detailed violation information\n")
            f.write("2. Identify which PM instruction rules were violated\n")
            f.write("3. Update PM instructions or fix implementation\n")
            f.write("4. Re-run tests to verify fixes\n")
            f.write("5. Update this report in release documentation\n")
        else:
            f.write("No action required. PM behavioral compliance verified.\n")

    print(f"\n✅ Compliance report generated: {summary_file}")

    if args.report:
        html_report = report_dir / "pm_behavioral_compliance.html"
        print(f"✅ HTML report generated: {html_report}")


def load_test_stats() -> Dict[str, Any]:
    """Load test statistics from scenarios file."""
    scenarios_file = Path(__file__).parent / "scenarios" / "pm_behavioral_requirements.json"

    with open(scenarios_file) as f:
        data = json.load(f)
        scenarios = data["scenarios"]

    stats = {
        "total": len(scenarios),
        "by_category": {},
        "by_severity": {}
    }

    for scenario in scenarios:
        category = scenario["category"]
        severity = scenario["severity"]

        stats["by_category"][category] = stats["by_category"].get(category, 0) + 1
        stats["by_severity"][severity] = stats["by_severity"].get(severity, 0) + 1

    return stats


if __name__ == "__main__":
    sys.exit(main())
