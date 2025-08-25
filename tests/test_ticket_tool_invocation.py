import pytest

#!/usr/bin/env python3
"""
Test script to verify ticket tools can be invoked through the MCP server.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from claude_mpm.services.mcp_gateway.core.interfaces import MCPToolInvocation
from claude_mpm.services.mcp_gateway.server.stdio_server import SimpleMCPServer


@pytest.mark.asyncio
async def test_ticket_tool_invocation():
    """Test invoking a ticket tool."""
    print("Testing ticket tool invocation...")

    # Create server instance
    server = SimpleMCPServer(name="test-gateway", version="1.0.0")

    if not hasattr(server, "ticket_tools"):
        print("❌ No ticket tools found")
        return

    # Test ticket_list tool
    print("\n📋 Testing ticket_list tool...")

    tool_name = "ticket_list"
    if tool_name in server.ticket_tools:
        tool_adapter = server.ticket_tools[tool_name]

        # Initialize the tool
        await tool_adapter.initialize()

        # Create invocation
        invocation = MCPToolInvocation(
            tool_name=tool_name,
            parameters={"status": "open", "limit": 5},
            request_id="test_001",
        )

        # Invoke the tool
        print(f"Invoking {tool_name} with parameters: {invocation.parameters}")

        try:
            result = await tool_adapter.invoke(invocation)

            if result.success:
                print("✅ Tool invocation successful!")
                print(f"Execution time: {result.execution_time:.2f}s")
                print(f"Result type: {type(result.data)}")

                # Print first part of result if it's text
                if isinstance(result.data, str):
                    preview = (
                        result.data[:200] + "..."
                        if len(result.data) > 200
                        else result.data
                    )
                    print(f"Result preview: {preview}")
            else:
                print(f"❌ Tool invocation failed: {result.error}")
        except Exception as e:
            print(f"❌ Error invoking tool: {e}")
    else:
        print(f"❌ Tool {tool_name} not found")

    print("\n✅ Ticket tool invocation test complete")


if __name__ == "__main__":
    asyncio.run(test_ticket_tool_invocation())
