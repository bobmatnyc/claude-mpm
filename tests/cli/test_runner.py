#!/usr/bin/env python3
"""
Test runner for CLI command tests.

WHY: Provides a convenient way to run all CLI tests and generate reports
for the comprehensive test suite created for TSK-0142.
"""

import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime


def run_pytest_with_coverage():
    """Run pytest with coverage for CLI tests."""
    cli_test_dir = Path(__file__).parent
    
    # Run pytest with coverage
    cmd = [
        sys.executable, "-m", "pytest",
        str(cli_test_dir),
        "-v",
        "--tb=short",
        "--cov=claude_mpm.cli",
        "--cov-report=term-missing",
        "--cov-report=json:tests/cli/coverage.json",
        "--junit-xml=tests/cli/test-results.xml"
    ]
    
    print("Running CLI tests with coverage...")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    return result.returncode


def run_specific_test_file(test_file):
    """Run a specific test file."""
    cli_test_dir = Path(__file__).parent
    test_path = cli_test_dir / test_file
    
    if not test_path.exists():
        print(f"Test file not found: {test_path}")
        return 1
    
    cmd = [
        sys.executable, "-m", "pytest",
        str(test_path),
        "-v",
        "--tb=short"
    ]
    
    print(f"Running {test_file}...")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)
    
    result = subprocess.run(cmd)
    return result.returncode


def generate_test_report():
    """Generate a comprehensive test report."""
    cli_test_dir = Path(__file__).parent
    coverage_file = cli_test_dir / "coverage.json"
    results_file = cli_test_dir / "test-results.xml"
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "test_suite": "CLI Commands - BaseCommand Pattern",
        "description": "Comprehensive test suite for migrated CLI commands (TSK-0142)",
        "test_files": [
            "test_base_command.py",
            "test_shared_utilities.py", 
            "test_config_command.py",
            "test_memory_command.py",
            "test_aggregate_command.py",
            "test_tickets_command_migration.py",  # Existing
            "test_run_command_migration.py"       # Existing
        ],
        "coverage": None,
        "results": None
    }
    
    # Load coverage data if available
    if coverage_file.exists():
        try:
            with open(coverage_file, 'r') as f:
                coverage_data = json.load(f)
                report["coverage"] = {
                    "total_coverage": coverage_data.get("totals", {}).get("percent_covered", 0),
                    "files_covered": len(coverage_data.get("files", {})),
                    "lines_covered": coverage_data.get("totals", {}).get("covered_lines", 0),
                    "lines_total": coverage_data.get("totals", {}).get("num_statements", 0)
                }
        except Exception as e:
            print(f"Error loading coverage data: {e}")
    
    # Save report
    report_file = cli_test_dir / "test_report.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\nTest report saved to: {report_file}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("CLI TEST SUITE SUMMARY")
    print("=" * 60)
    print(f"Test Suite: {report['test_suite']}")
    print(f"Description: {report['description']}")
    print(f"Test Files: {len(report['test_files'])}")
    
    if report["coverage"]:
        print(f"Coverage: {report['coverage']['total_coverage']:.1f}%")
        print(f"Lines Covered: {report['coverage']['lines_covered']}/{report['coverage']['lines_total']}")
    
    print("=" * 60)


def main():
    """Main test runner function."""
    if len(sys.argv) > 1:
        # Run specific test file
        test_file = sys.argv[1]
        exit_code = run_specific_test_file(test_file)
    else:
        # Run all CLI tests
        exit_code = run_pytest_with_coverage()
        
        # Generate report regardless of test results
        generate_test_report()
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
