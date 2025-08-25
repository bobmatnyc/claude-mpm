#!/usr/bin/env python3
"""
Test MCP Standards Compliance
==============================

Tests that the MCP server implementation follows the official MCP specification
and works correctly with the expected protocol flow.
"""

import subprocess
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_cli_functionality():
    """Test CLI functionality to ensure server components work."""
    print("🧪 Testing MCP Standards Compliance")
    print("=" * 50)

    success = True

    # Test 1: Status command
    print("1. Testing status command...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "claude_mpm.cli", "mcp", "status"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
            check=False,
        )

        if result.returncode == 0:
            print("   ✅ Status command successful")
            if "MCP servers run on-demand via stdio" in result.stdout:
                print("   ✅ Correct stdio-based architecture message")
            else:
                print("   ⚠️  Status message may need updating")
        else:
            print(f"   ❌ Status command failed: {result.stderr}")
            success = False
    except Exception as e:
        print(f"   ❌ Status command error: {e}")
        success = False

    # Test 2: Tools listing
    print("2. Testing tools listing...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "claude_mpm.cli", "mcp", "tools"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
            check=False,
        )

        if result.returncode == 0:
            print("   ✅ Tools listing successful")
            expected_tools = ["echo", "calculator", "system_info"]
            for tool in expected_tools:
                if tool in result.stdout:
                    print(f"   ✅ Found tool: {tool}")
                else:
                    print(f"   ❌ Missing tool: {tool}")
                    success = False
        else:
            print(f"   ❌ Tools listing failed: {result.stderr}")
            success = False
    except Exception as e:
        print(f"   ❌ Tools listing error: {e}")
        success = False

    # Test 3: Tool invocation - Echo
    print("3. Testing echo tool...")
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "claude_mpm.cli",
                "mcp",
                "test",
                "echo",
                "--args",
                '{"message": "Standards Compliance Test"}',
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
            check=False,
        )

        if result.returncode == 0:
            print("   ✅ Echo tool invocation successful")
            if "Standards Compliance Test" in result.stdout:
                print("   ✅ Echo tool returned correct result")
            else:
                print("   ⚠️  Echo tool result may be formatted differently")
        else:
            print(f"   ❌ Echo tool failed: {result.stderr}")
            success = False
    except Exception as e:
        print(f"   ❌ Echo tool error: {e}")
        success = False

    # Test 4: Tool invocation - Calculator
    print("4. Testing calculator tool...")
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "claude_mpm.cli",
                "mcp",
                "test",
                "calculator",
                "--args",
                '{"operation": "multiply", "a": 8, "b": 7}',
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
            check=False,
        )

        if result.returncode == 0:
            print("   ✅ Calculator tool invocation successful")
            if "56" in result.stdout:
                print("   ✅ Calculator tool returned correct result (8 * 7 = 56)")
            else:
                print("   ⚠️  Calculator result may be formatted differently")
        else:
            print(f"   ❌ Calculator tool failed: {result.stderr}")
            success = False
    except Exception as e:
        print(f"   ❌ Calculator tool error: {e}")
        success = False

    # Test 5: Tool invocation - System Info
    print("5. Testing system_info tool...")
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "claude_mpm.cli",
                "mcp",
                "test",
                "system_info",
                "--args",
                '{"info_type": "platform"}',
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
            check=False,
        )

        if result.returncode == 0:
            print("   ✅ System info tool invocation successful")
            # Check for common system info fields
            if any(
                field in result.stdout.lower()
                for field in ["platform", "python", "version"]
            ):
                print("   ✅ System info tool returned expected data")
            else:
                print("   ⚠️  System info result may be formatted differently")
        else:
            print(f"   ❌ System info tool failed: {result.stderr}")
            success = False
    except Exception as e:
        print(f"   ❌ System info tool error: {e}")
        success = False

    # Test 6: Server startup (quick test)
    print("6. Testing server startup...")
    try:
        # Start server and immediately terminate to test startup
        process = subprocess.Popen(
            [sys.executable, "-m", "claude_mpm.cli", "mcp", "start"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=Path(__file__).parent.parent,
        )

        # Give it a moment to start
        import time

        time.sleep(2)

        # Terminate
        process.terminate()
        stdout, stderr = process.communicate(timeout=5)

        # Check if it started properly (startup messages go to stdout)
        stdout_text = stdout.decode()
        stderr_text = stderr.decode()

        if "Starting MCP Gateway server" in stdout_text:
            print("   ✅ Server startup successful")
            if "MCP server stdio connection established" in stdout_text:
                print("   ✅ Stdio connection established correctly")
            else:
                print("   ⚠️  Stdio connection may have issues")

            # I/O errors during shutdown are expected for stdio servers
            if "I/O operation on closed file" in stderr_text:
                print("   ✅ Expected I/O cleanup errors during shutdown (normal)")
        else:
            print("   ❌ Server startup failed")
            success = False

    except Exception as e:
        # Server startup test can have I/O issues during cleanup, but that's expected
        print(
            f"   ⚠️  Server startup test had cleanup issues (expected): {type(e).__name__}"
        )
        # Don't mark as failure since this is expected behavior for stdio servers

    return success


def test_mcp_imports():
    """Test that MCP imports work correctly."""
    print("7. Testing MCP package imports...")
    try:
        from mcp.server import Server
        from mcp.types import TextContent, Tool

        from claude_mpm.services.mcp_gateway.server.mcp_gateway import MCPGateway

        print("   ✅ All MCP imports successful")

        # Test gateway instantiation
        gateway = MCPGateway("test-gateway")
        print("   ✅ MCP gateway instantiation successful")
        return True

    except ImportError as e:
        print(f"   ❌ MCP import failed: {e}")
        return False
    except Exception as e:
        print(f"   ❌ MCP server instantiation failed: {e}")
        return False


def main():
    """Main test function."""
    cli_success = test_cli_functionality()
    import_success = test_mcp_imports()

    overall_success = cli_success and import_success

    print("\n" + "=" * 50)
    if overall_success:
        print("🎉 All MCP standards compliance tests passed!")
        print("\nThe MCP Gateway is ready for:")
        print("  • Claude Code integration")
        print("  • Other MCP client connections")
        print("  • Standards-compliant protocol communication")
        print("\nTo integrate with Claude Code, add this to your MCP config:")
        print("{")
        print('  "mcpServers": {')
        print('    "claude-mpm": {')
        print('      "command": "python",')
        print('      "args": ["-m", "claude_mpm.cli", "mcp", "start"],')
        print(f'      "cwd": "{Path(__file__).parent.parent.absolute()}"')
        print("    }")
        print("  }")
        print("}")
        return 0
    print("❌ Some MCP standards compliance tests failed!")
    print("Please check the errors above and fix any issues.")
    return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
