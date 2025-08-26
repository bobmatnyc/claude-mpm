#!/usr/bin/env python3
"""
Test Script for MCP Entry Points
=================================

This script tests that the MCP server entry points defined in pyproject.toml work correctly.

WHY: We need to verify that the installed commands work after moving the MCP server script.
"""

import contextlib
import json
import subprocess
import sys
import time


def test_entry_point(command_name):
    """
    Test a specific entry point command.

    Args:
        command_name: Name of the command to test

    Returns:
        bool: True if test passed
    """
    print(f"\n[TEST] Testing entry point: {command_name}")

    try:
        # Start the process
        proc = subprocess.Popen(
            [command_name],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Give it time to start
        time.sleep(2)

        # Send a test request
        test_request = (
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-01",
                        "capabilities": {},
                        "clientInfo": {"name": "test-client", "version": "1.0.0"},
                    },
                    "id": 1,
                }
            )
            + "\n"
        )

        proc.stdin.write(test_request)
        proc.stdin.flush()

        # Wait briefly for response
        time.sleep(1)

        # Check if process is still running
        if proc.poll() is not None:
            # Process died
            stderr = proc.stderr.read()
            print("  ✗ FAILED - Process died")
            if stderr:
                print(f"  Error output: {stderr[:500]}")
            return False

        # Process is running - terminate and check
        proc.terminate()
        time.sleep(0.5)
        stderr = proc.stderr.read()

        if (
            "Starting MCP Gateway Server" in stderr
            or "Server instance created" in stderr
        ):
            print(f"  ✓ PASSED - Command {command_name} works")
            return True
        print("  ✗ FAILED - Command started but server initialization unclear")
        return False

    except FileNotFoundError:
        print(f"  ✗ FAILED - Command {command_name} not found (not installed?)")
        return False
    except Exception as e:
        print(f"  ✗ FAILED - Exception: {e}")
        return False
    finally:
        with contextlib.suppress(Exception):
            proc.terminate()


def main():
    """Run entry point tests."""
    print("=" * 60)
    print(" MCP Entry Point Tests")
    print("=" * 60)

    print(f"Python: {sys.executable}")
    print(f"Version: {sys.version}")

    # Test the MCP entry points
    commands_to_test = [
        "claude-mpm-mcp",  # Direct MCP server command
        "claude-mpm-mcp-wrapper",  # Wrapper command
    ]

    results = []
    for cmd in commands_to_test:
        results.append(test_entry_point(cmd))

    # Summary
    print("\n" + "=" * 60)
    print(" Test Summary")
    print("=" * 60)

    passed = sum(results)
    total = len(results)

    print(f"Tests passed: {passed}/{total}")

    if passed == total:
        print("\n✅ All entry points work correctly!")
    else:
        print("\n⚠️ Some entry points failed.")
        print("\nTo fix:")
        print("1. Ensure claude-mpm is installed: pip install -e .")
        print("2. Check that the installation completed successfully")
        print("3. Try reinstalling if commands are not found")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
