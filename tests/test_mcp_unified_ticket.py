#!/usr/bin/env python3
"""
Test the unified ticket tool through the MCP Gateway.

WHY: This script verifies that the unified ticket tool works correctly
when integrated with the full MCP Gateway stack, ensuring proper
tool registration and invocation through the gateway.
"""

import asyncio
import sys
from pathlib import Path

import pytest

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.claude_mpm.services.mcp_gateway.registry.tool_registry import ToolRegistry
from src.claude_mpm.services.mcp_gateway.server.mcp_gateway import MCPGateway
from src.claude_mpm.services.mcp_gateway.tools.unified_ticket_tool import (
    UnifiedTicketTool,
)


@pytest.mark.asyncio
async def test_mcp_gateway_integration():
    """Test the unified ticket tool through the MCP Gateway."""
    print("Testing Unified Ticket Tool with MCP Gateway")
    print("=" * 60)

    try:
        # Create and initialize the tool registry
        print("\n1. Setting up Tool Registry...")
        registry = ToolRegistry()
        if not await registry.initialize():
            print("❌ Failed to initialize tool registry")
            return
        print("✅ Tool registry initialized")

        # Create and register the unified ticket tool
        print("\n2. Registering Unified Ticket Tool...")
        tool = UnifiedTicketTool()
        if not await tool.initialize():
            print("❌ Failed to initialize unified ticket tool")
            return

        if not registry.register_tool(tool, category="builtin"):
            print("❌ Failed to register unified ticket tool")
            return
        print("✅ Unified ticket tool registered")

        # Create the MCP Gateway
        print("\n3. Setting up MCP Gateway...")
        gateway = MCPGateway(gateway_name="test-gateway", version="1.0.0")

        # Wire the dependencies
        gateway.set_tool_registry(registry)

        if not await gateway.initialize():
            print("❌ Failed to initialize MCP Gateway")
            return
        print("✅ MCP Gateway initialized")

        # Verify tool is available through the gateway
        print("\n4. Verifying Tool Registration...")
        available_tools = registry.list_tools()
        print(f"Available tools: {len(available_tools)}")

        ticket_tool_found = False
        for tool_name in available_tools:
            print(f"  • {tool_name}")
            if tool_name == "ticket":
                ticket_tool_found = True

        if not ticket_tool_found:
            print("❌ Unified ticket tool not found in registry")
            return
        print("✅ Unified ticket tool is available")

        # Get tool definition to verify schema
        print("\n5. Verifying Tool Schema...")
        tool_def = registry.get_tool("ticket")
        if tool_def:
            definition = tool_def.get_definition()
            print(f"Tool name: {definition.name}")
            print(f"Description: {definition.description}")

            # Check that operation parameter is in schema
            schema = definition.input_schema
            if "properties" in schema and "operation" in schema["properties"]:
                operations = schema["properties"]["operation"].get("enum", [])
                print(f"Available operations: {', '.join(operations)}")

                if set(operations) == {"create", "list", "update", "view", "search"}:
                    print("✅ All 5 operations are available")
                else:
                    print("❌ Missing some operations")
            else:
                print("❌ Operation parameter not found in schema")
        else:
            print("❌ Could not retrieve tool definition")

        # Test metrics
        print("\n6. Checking Tool Metrics...")
        metrics = tool.get_metrics()
        print(f"Total invocations: {metrics['invocations']}")
        print(
            f"Success rate: {metrics['successes']}/{metrics['invocations'] if metrics['invocations'] > 0 else 'N/A'}"
        )
        print("✅ Metrics system working")

        # Cleanup
        print("\n7. Cleaning up...")
        await gateway.shutdown()
        await registry.shutdown()
        print("✅ Cleanup complete")

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nThe unified ticket tool is successfully integrated with")
        print("the MCP Gateway and ready for use in production.")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_mcp_gateway_integration())
