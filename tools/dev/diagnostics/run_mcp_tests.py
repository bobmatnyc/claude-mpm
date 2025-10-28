#!/usr/bin/env python3
"""
MCP Test Runner
===============

Comprehensive test runner for all MCP functionality.
Runs both unit tests and integration tests.
"""

import subprocess
import sys
import time
from pathlib import Path


def run_command(cmd, description):
    """Run a command and report results."""
    print(f"\n{'='*60}")
    print(f"🧪 {description}")
    print("=" * 60)

    start_time = time.time()
    result = subprocess.run(
        cmd, shell=True, cwd=Path(__file__).parent.parent, check=False
    )
    end_time = time.time()

    duration = end_time - start_time
    if result.returncode == 0:
        print(f"✅ {description} - PASSED ({duration:.2f}s)")
        return True
    print(f"❌ {description} - FAILED ({duration:.2f}s)")
    return False


def main():
    """Run all MCP tests."""
    print("🚀 Running Comprehensive MCP Test Suite")
    print("=" * 60)

    tests = [
        # Unit Tests
        (
            "python -m pytest tests/services/test_mcp_tool_adapters_unit.py -v",
            "Unit Tests: Tool Adapters (Echo, Calculator, System Info)",
        ),
        (
            "python -m pytest tests/services/test_mcp_registry_simple.py -v",
            "Unit Tests: Tool Registry",
        ),
        # Integration Tests
        (
            "python scripts/test_mcp_server.py",
            "Integration Test: MCP Server + Tool Registry",
        ),
        (
            "python scripts/test_mcp_standards_compliance.py",
            "Integration Test: MCP Standards Compliance",
        ),
        # CLI Tests
        ("python -m claude_mpm.cli mcp status", "CLI Test: Status Command"),
        ("python -m claude_mpm.cli mcp tools", "CLI Test: Tools Listing"),
        (
            'python -m claude_mpm.cli mcp test echo --args \'{"message": "Unit Test"}\'',
            "CLI Test: Echo Tool",
        ),
        (
            'python -m claude_mpm.cli mcp test calculator --args \'{"operation": "add", "a": 10, "b": 5}\'',
            "CLI Test: Calculator Tool",
        ),
        (
            'python -m claude_mpm.cli mcp test system_info --args \'{"info_type": "platform"}\'',
            "CLI Test: System Info Tool",
        ),
    ]

    passed = 0
    failed = 0

    for cmd, description in tests:
        if run_command(cmd, description):
            passed += 1
        else:
            failed += 1

    # Summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📈 Total:  {passed + failed}")

    if failed == 0:
        print("\n🎉 ALL MCP TESTS PASSED!")
        print("\nThe MCP Gateway is ready for:")
        print("  • Claude Code integration")
        print("  • Production deployment")
        print("  • Extension with new tools")
        return 0
    print(f"\n💥 {failed} TEST(S) FAILED!")
    print("Please review the failures above and fix any issues.")
    return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
