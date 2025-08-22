#!/usr/bin/env python3
"""
Basic test for audit_documentation.py script

This is a simple test to verify the audit script runs without errors
and produces expected output format.
"""

import json
import subprocess
import sys
from pathlib import Path


def test_audit_script():
    """Test basic functionality of audit_documentation.py"""
    project_root = Path(__file__).parent.parent
    audit_script = project_root / "scripts" / "audit_documentation.py"

    if not audit_script.exists():
        print("❌ ERROR: audit_documentation.py script not found")
        return False

    print("Testing audit_documentation.py...")

    try:
        # Test 1: Basic run (should not crash)
        print("Test 1: Basic execution...")
        result = subprocess.run(
            [sys.executable, str(audit_script), "--project-root", str(project_root)],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode not in [0, 1]:  # 0 = success, 1 = issues found
            print(f"❌ FAIL: Unexpected return code {result.returncode}")
            print(f"STDERR: {result.stderr}")
            return False

        if "DOCUMENTATION AUDIT REPORT" not in result.stdout:
            print("❌ FAIL: Expected report header not found")
            print(f"STDOUT: {result.stdout}")
            return False

        print("✅ PASS: Basic execution works")

        # Test 2: JSON output
        print("Test 2: JSON output...")
        result = subprocess.run(
            [
                sys.executable,
                str(audit_script),
                "--project-root",
                str(project_root),
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode not in [0, 1]:
            print(f"❌ FAIL: JSON mode unexpected return code {result.returncode}")
            return False

        try:
            output_data = json.loads(result.stdout)
            required_keys = ["summary", "issues", "fixed_count"]
            if not all(key in output_data for key in required_keys):
                print(f"❌ FAIL: JSON output missing required keys")
                print(f"Got keys: {list(output_data.keys())}")
                return False
        except json.JSONDecodeError as e:
            print(f"❌ FAIL: Invalid JSON output: {e}")
            print(f"Output: {result.stdout[:200]}...")
            return False

        print("✅ PASS: JSON output format correct")

        # Test 3: Help message
        print("Test 3: Help message...")
        result = subprocess.run(
            [sys.executable, str(audit_script), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            print(f"❌ FAIL: Help command failed")
            return False

        if "usage:" not in result.stdout.lower():
            print("❌ FAIL: Help message format incorrect")
            return False

        print("✅ PASS: Help message works")

        print("\n🎉 All basic tests passed!")
        print("The audit_documentation.py script is ready for use.")
        return True

    except subprocess.TimeoutExpired:
        print("❌ FAIL: Script execution timed out")
        return False
    except Exception as e:
        print(f"❌ FAIL: Unexpected error: {e}")
        return False


def show_sample_usage():
    """Show sample usage examples"""
    print("\n" + "=" * 60)
    print("SAMPLE USAGE EXAMPLES")
    print("=" * 60)

    examples = [
        ("Basic audit", "python scripts/audit_documentation.py"),
        ("Verbose mode", "python scripts/audit_documentation.py --verbose"),
        ("Auto-fix issues", "python scripts/audit_documentation.py --fix"),
        ("JSON output", "python scripts/audit_documentation.py --json"),
        ("CI/CD mode", "python scripts/audit_documentation.py --json --strict"),
    ]

    for description, command in examples:
        print(f"\n{description}:")
        print(f"  {command}")


if __name__ == "__main__":
    success = test_audit_script()
    if success:
        show_sample_usage()
        sys.exit(0)
    else:
        print("\n❌ Tests failed. Please check the audit script.")
        sys.exit(1)