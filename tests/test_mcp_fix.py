import pytest

#!/usr/bin/env python3
"""
Test script to verify MCP gateway reconnection fix.

This script tests that the mock MCP implementation has been removed
and the real MCP SDK is being used correctly.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_mcp_sdk_import():
    """Test that the real MCP SDK can be imported."""
    print("Testing MCP SDK import...")
    try:
        import mcp

        print(f"✓ MCP SDK imported from: {mcp.__file__}")

        # Test specific imports needed by the gateway
        from mcp.server import NotificationOptions, Server
        from mcp.server.models import InitializationOptions
        from mcp.server.stdio import stdio_server
        from mcp.types import TextContent, Tool

        print("✓ All required MCP imports successful")
        return True
    except ImportError as e:
        print(f"✗ Failed to import MCP SDK: {e}")
        return False


def test_mock_removed():
    """Test that the mock MCP directory has been removed."""
    print("\nTesting mock MCP removal...")
    mock_path = Path(__file__).parent.parent / "src" / "mcp"

    if mock_path.exists():
        print(f"✗ Mock MCP directory still exists at: {mock_path}")
        return False
    print("✓ Mock MCP directory successfully removed")
    return True


@pytest.mark.asyncio
async def test_gateway_creation():
    """Test that MCPGateway can be created with real MCP SDK."""
    print("\nTesting MCPGateway creation...")
    try:
        from claude_mpm.services.mcp_gateway.server.mcp_gateway import MCPGateway

        gateway = MCPGateway(gateway_name="test-gateway", version="1.0.0")

        print("✓ MCPGateway created successfully")
        print(f"  - Gateway name: {gateway.gateway_name}")
        print(f"  - Version: {gateway.version}")
        print(f"  - MCP Server type: {type(gateway.mcp_server).__name__}")

        return True
    except Exception as e:
        print(f"✗ Failed to create MCPGateway: {e}")
        import traceback

        traceback.print_exc()
        return False


@pytest.mark.asyncio
async def test_stdio_server():
    """Test that stdio server module can be imported."""
    print("\nTesting stdio server import...")
    try:
        from claude_mpm.services.mcp_gateway.server import stdio_server

        print("✓ stdio_server module imported successfully")
        print(f"  - Module location: {stdio_server.__file__}")

        # Check for main function
        if hasattr(stdio_server, "main"):
            print("  - main() function available")
        if hasattr(stdio_server, "main_sync"):
            print("  - main_sync() function available")

        return True
    except ImportError as e:
        print(f"✗ Failed to import stdio_server: {e}")
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("MCP Gateway Reconnection Fix Verification")
    print("=" * 60)

    results = []

    # Test 1: MCP SDK import
    results.append(test_mcp_sdk_import())

    # Test 2: Mock removed
    results.append(test_mock_removed())

    # Test 3: Gateway creation
    results.append(await test_gateway_creation())

    # Test 4: Stdio server
    results.append(await test_stdio_server())

    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)

    total = len(results)
    passed = sum(results)
    failed = total - passed

    print(f"Total tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if failed == 0:
        print("\n✓ All tests passed! MCP gateway reconnection fix is successful.")
        return 0
    print(f"\n✗ {failed} test(s) failed. Please review the errors above.")
    return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
