#!/usr/bin/env python3
"""
Test script to verify that only the unified ticket tool is registered.

This script tests the MCP gateway to ensure we have only one ticket tool
with an operation parameter, not 5 separate ticket tools.
"""

import asyncio
import sys
from pathlib import Path

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.claude_mpm.services.mcp_gateway.registry.tool_registry import ToolRegistry
from src.claude_mpm.services.mcp_gateway.server.mcp_gateway import MCPGateway
from src.claude_mpm.services.mcp_gateway.tools.unified_ticket_tool import (
    UnifiedTicketTool,
)


@pytest.mark.asyncio
async def test_unified_tool():
    """Test that only the unified ticket tool is registered."""
    print("Testing Unified Ticket Tool Registration")
    print("=" * 50)

    # Create tool registry
    registry = ToolRegistry()
    await registry.initialize()

    # Register only the unified ticket tool
    unified_tool = UnifiedTicketTool()
    await unified_tool.initialize()

    if registry.register_tool(unified_tool, category="builtin"):
        print("✓ Successfully registered unified ticket tool")
    else:
        print("✗ Failed to register unified ticket tool")
        return False

    # List all registered tools
    tools = registry.list_tools()
    print(f"\nTotal tools registered: {len(tools)}")

    # Check for ticket-related tools
    ticket_tools = [t for t in tools if "ticket" in t.name.lower()]
    print(f"Ticket-related tools: {len(ticket_tools)}")

    for tool in ticket_tools:
        print(f"\nTool: {tool.name}")
        print(f"Description: {tool.description}")

        # Check the schema for operation parameter
        if "properties" in tool.input_schema:
            properties = tool.input_schema["properties"]
            if "operation" in properties:
                operations = properties["operation"].get("enum", [])
                print(f"✓ Has operation parameter with options: {operations}")
            else:
                print("✗ Missing operation parameter - this is a separate tool!")

    # Verify we have exactly one ticket tool
    if len(ticket_tools) == 1:
        print("\n✓ SUCCESS: Only one unified ticket tool found!")
        return True
    print(f"\n✗ FAILURE: Found {len(ticket_tools)} ticket tools, expected 1")
    return False


@pytest.mark.asyncio
async def test_mcp_gateway():
    """Test the MCP Gateway with unified ticket tool."""
    print("\n" + "=" * 50)
    print("Testing MCP Gateway Integration")
    print("=" * 50)

    # Create gateway and registry
    gateway = MCPGateway(gateway_name="test-gateway", version="1.0.0")
    registry = ToolRegistry()
    await registry.initialize()

    # Register unified ticket tool
    unified_tool = UnifiedTicketTool()
    await unified_tool.initialize()
    registry.register_tool(unified_tool, category="builtin")

    # Set registry on gateway
    gateway.set_tool_registry(registry)
    await gateway.initialize()

    # Check capabilities
    capabilities = gateway.get_capabilities()
    print(f"Gateway capabilities: {capabilities}")

    # Get metrics to verify setup
    metrics = gateway.get_metrics()
    print(f"Gateway metrics: {metrics}")

    print("\n✓ MCP Gateway successfully configured with unified ticket tool")
    return True


async def main():
    """Run all tests."""
    success = True

    # Test unified tool registration
    if not await test_unified_tool():
        success = False

    # Test MCP gateway integration
    if not await test_mcp_gateway():
        success = False

    if success:
        print("\n" + "=" * 50)
        print("✓ ALL TESTS PASSED")
        print("The unified ticket tool is properly configured!")
        print("=" * 50)
        return 0
    print("\n" + "=" * 50)
    print("✗ TESTS FAILED")
    print("Please check the configuration")
    print("=" * 50)
    return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
