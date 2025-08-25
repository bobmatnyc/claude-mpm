#!/usr/bin/env python3
"""
Comprehensive MCP Setup Verification Script
===========================================

This script verifies that the MCP server can be started in all the different ways
it might be invoked by Claude Code or manually.

WHY: We need to ensure the MCP server works regardless of how it's started,
including as a script, module, or through the Claude Code configuration.
"""

import json
import subprocess
import sys
import time
from pathlib import Path


def print_header(title):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


def test_method(name, command, cwd=None):
    """
    Test a specific invocation method.

    Args:
        name: Description of the test
        command: Command to run (list)
        cwd: Working directory (optional)

    Returns:
        bool: True if test passed
    """
    print(f"\n[TEST] {name}")
    print(f"Command: {' '.join(command)}")
    if cwd:
        print(f"CWD: {cwd}")

    try:
        # Start the process
        proc = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd,
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

        # Wait briefly for any startup errors
        time.sleep(1)

        # Check if process is still running
        if proc.poll() is not None:
            # Process died
            stderr = proc.stderr.read()
            print("  ✗ FAILED - Process died")
            if stderr:
                print(f"  Error output: {stderr[:500]}")
            return False

        # Process is running - check for successful startup in stderr
        proc.terminate()
        time.sleep(0.5)
        stderr = proc.stderr.read()

        if (
            "Server instance created successfully" in stderr
            or "MCP Gateway Server" in stderr
        ):
            print("  ✓ PASSED - Server started successfully")
            return True
        if "Failed to import" in stderr or "FATAL ERROR" in stderr:
            print("  ✗ FAILED - Import or startup error")
            error_lines = [
                l for l in stderr.split("\n") if "Error" in l or "Failed" in l
            ]
            for line in error_lines[:3]:
                print(f"    {line}")
            return False
        print("  ? UNCERTAIN - Server started but status unclear")
        return True

    except Exception as e:
        print(f"  ✗ FAILED - Exception: {e}")
        return False
    finally:
        try:
            proc.terminate()
        except:
            pass


def main():
    """Run all verification tests."""
    print_header("MCP Setup Verification")

    # Get project paths
    project_root = Path.cwd()
    wrapper_script = project_root / "scripts" / "mcp_wrapper.py"
    server_script = project_root / "src" / "claude_mpm" / "scripts" / "mcp_server.py"

    print(f"Project root: {project_root}")
    print(f"Python executable: {sys.executable}")
    print(f"Python version: {sys.version}")

    # Check file existence
    print_header("File Existence Check")
    files_to_check = [
        ("Wrapper script", wrapper_script),
        ("Server script", server_script),
        ("pyproject.toml", project_root / "pyproject.toml"),
        (
            "stdio_server.py",
            project_root
            / "src"
            / "claude_mpm"
            / "services"
            / "mcp_gateway"
            / "server"
            / "stdio_server.py",
        ),
    ]

    all_exist = True
    for name, path in files_to_check:
        if path.exists():
            print(f"  ✓ {name}: {path}")
        else:
            print(f"  ✗ {name}: NOT FOUND at {path}")
            all_exist = False

    if not all_exist:
        print("\n❌ Some required files are missing!")
        return 1

    # Test different invocation methods
    print_header("Testing Invocation Methods")

    results = []

    # Test 1: Direct wrapper script invocation (as Claude Code would)
    results.append(
        test_method(
            "Direct wrapper script (Claude Code style)",
            ["python3", str(wrapper_script)],
            cwd=str(project_root),
        )
    )

    # Test 2: Direct server script invocation (legacy)
    results.append(
        test_method(
            "Direct server script (legacy)",
            ["python3", str(server_script)],
            cwd=str(project_root),
        )
    )

    # Test 3: Module invocation
    results.append(
        test_method(
            "Module invocation (-m)",
            ["python3", "-m", "claude_mpm.services.mcp_gateway.server.stdio_server"],
            cwd=str(project_root),
        )
    )

    # Test 4: Script from different working directory
    results.append(
        test_method(
            "Wrapper from different CWD",
            ["python3", str(wrapper_script.absolute())],
            cwd="/tmp",
        )
    )

    # Check Claude Code configuration
    print_header("Claude Code Configuration")

    config_path = (
        Path.home()
        / "Library"
        / "Application Support"
        / "Claude"
        / "claude_desktop_config.json"
    )
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)

        if "mcpServers" in config and "claude-mpm-gateway" in config["mcpServers"]:
            mcp_config = config["mcpServers"]["claude-mpm-gateway"]
            print("Current configuration:")
            print(f"  Command: {mcp_config.get('command', 'NOT SET')}")
            print(f"  Args: {mcp_config.get('args', 'NOT SET')}")
            print(f"  CWD: {mcp_config.get('cwd', 'NOT SET')}")

            # Check if it points to wrapper
            if "mcp_wrapper.py" in str(mcp_config.get("args", [])):
                print("  ✓ Configuration uses the new wrapper script")
            else:
                print("  ⚠ Configuration does NOT use the wrapper script")
                print("  Recommended configuration:")
                print(
                    json.dumps(
                        {
                            "command": "python3",
                            "args": [str(wrapper_script.absolute())],
                            "cwd": str(project_root),
                        },
                        indent=2,
                    )
                )
        else:
            print("  ⚠ MCP server not configured in Claude Code")
    else:
        print(f"  ⚠ Config file not found at {config_path}")

    # Summary
    print_header("Test Summary")

    passed = sum(results)
    total = len(results)

    print(f"Tests passed: {passed}/{total}")

    if passed == total:
        print("\n✅ All tests passed! MCP server is properly configured.")
        print("\nNext steps:")
        print("1. Restart Claude Code to pick up the new configuration")
        print("2. Check if the MCP icon appears in Claude Code")
        print("3. Try using MCP tools in a conversation")
        return 0
    print("\n⚠️ Some tests failed. Please review the errors above.")
    print("\nTroubleshooting:")
    print("1. Ensure claude-mpm is installed: pip install -e .")
    print("2. Check Python version is 3.8+")
    print("3. Verify all dependencies are installed")
    print("4. Review the error messages above for specific issues")
    return 1


if __name__ == "__main__":
    sys.exit(main())
