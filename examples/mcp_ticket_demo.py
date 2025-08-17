#!/usr/bin/env python3
"""
MCP Ticket Tools Demo
=====================

Demonstrates how to use the MCP ticket tools through Claude Desktop.

This script shows how the ticket tools can be registered and used
via the MCP gateway for seamless aitrackdown integration.

Usage:
    python examples/mcp_ticket_demo.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.mcp_gateway.core.interfaces import MCPToolInvocation
from claude_mpm.services.mcp_gateway.registry.tool_registry import ToolRegistry
from claude_mpm.services.mcp_gateway.tools.ticket_tools import (
    TicketCreateTool,
    TicketListTool,
    TicketSearchTool,
    TicketUpdateTool,
    TicketViewTool,
)


async def demo_ticket_tools():
    """
    Demonstrate the ticket tools in action.

    WHY: This shows how Claude Desktop can interact with aitrackdown
    through the MCP gateway, enabling seamless ticket management.
    """
    print("MCP Ticket Tools Demo")
    print("=" * 60)
    print("\nThis demo shows how Claude Desktop can manage tickets")
    print("through the MCP gateway using aitrackdown.\n")

    # Create a tool registry
    registry = ToolRegistry()
    await registry.initialize()

    # Register ticket tools
    tools = [
        TicketCreateTool(),
        TicketListTool(),
        TicketUpdateTool(),
        TicketViewTool(),
        TicketSearchTool(),
    ]

    print("Registering ticket tools...")
    for tool in tools:
        await tool.initialize()
        if registry.register_tool(tool, category="user"):
            print(f"  ✅ Registered: {tool.get_definition().name}")
        else:
            print(f"  ❌ Failed to register: {tool.get_definition().name}")

    # Show available tools
    tool_list = registry.list_tools()
    print(f"\nTotal tools registered: {len(tool_list)}")
    print("\nAvailable ticket management tools:")
    for tool_def in tool_list:
        print(f"  - {tool_def.name}: {tool_def.description}")

    # Example: Create a ticket
    print("\n" + "=" * 60)
    print("Example: Creating a new task")
    print("-" * 60)

    invocation = MCPToolInvocation(
        tool_name="ticket_create",
        parameters={
            "type": "task",
            "title": "Implement user authentication",
            "description": "Add JWT-based authentication to the API endpoints",
            "priority": "high",
            "tags": ["backend", "security", "api"],
        },
    )

    print("Request:")
    print(f"  Type: {invocation.parameters['type']}")
    print(f"  Title: {invocation.parameters['title']}")
    print(f"  Priority: {invocation.parameters['priority']}")
    print(f"  Tags: {invocation.parameters['tags']}")

    result = await registry.invoke_tool(invocation)

    print("\nResponse:")
    if result.success:
        print(f"  ✅ Success! Created ticket: {result.data.get('ticket_id', 'Unknown')}")
        print(f"  Execution time: {result.execution_time:.2f}s")
    else:
        print(f"  ❌ Failed: {result.error}")

    # Example: List recent tickets
    print("\n" + "=" * 60)
    print("Example: Listing recent tasks")
    print("-" * 60)

    list_invocation = MCPToolInvocation(
        tool_name="ticket_list", parameters={"limit": 3, "status": "open"}
    )

    print("Request:")
    print(f"  Limit: {list_invocation.parameters['limit']}")
    print(f"  Status filter: {list_invocation.parameters['status']}")

    result = await registry.invoke_tool(list_invocation)

    print("\nResponse:")
    if result.success:
        print(f"  ✅ Success! Retrieved ticket list")
        print(f"  Execution time: {result.execution_time:.2f}s")
        # The actual format depends on aitrackdown's output
        if "raw_output" in result.data:
            print("\n  Output preview:")
            lines = result.data["raw_output"].split("\n")[:5]
            for line in lines:
                print(f"    {line}")
    else:
        print(f"  ❌ Failed: {result.error}")

    # Example: Search for tickets
    print("\n" + "=" * 60)
    print("Example: Searching for tickets")
    print("-" * 60)

    search_invocation = MCPToolInvocation(
        tool_name="ticket_search", parameters={"query": "authentication", "limit": 5}
    )

    print("Request:")
    print(f"  Query: '{search_invocation.parameters['query']}'")
    print(f"  Limit: {search_invocation.parameters['limit']}")

    result = await registry.invoke_tool(search_invocation)

    print("\nResponse:")
    if result.success:
        print(f"  ✅ Success! Search completed")
        print(f"  Execution time: {result.execution_time:.2f}s")
        if "raw_output" in result.data:
            print(f"  Found results for query: '{result.data.get('query', '')}'")
    else:
        print(f"  ❌ Failed: {result.error}")

    # Show tool metrics
    print("\n" + "=" * 60)
    print("Tool Usage Metrics")
    print("-" * 60)

    for tool_name in ["ticket_create", "ticket_list", "ticket_search"]:
        tool_adapter = registry.get_tool(tool_name)
        if tool_adapter:
            metrics = tool_adapter.get_metrics()
            print(f"\n{tool_name}:")
            print(f"  Invocations: {metrics['invocations']}")
            print(f"  Successes: {metrics['successes']}")
            print(f"  Failures: {metrics['failures']}")
            if metrics["invocations"] > 0:
                print(f"  Avg execution time: {metrics['average_execution_time']:.3f}s")

    # Cleanup
    await registry.shutdown()

    print("\n" + "=" * 60)
    print("Demo completed!")
    print("\nThese ticket tools are now available through the MCP gateway")
    print("and can be used by Claude Desktop for ticket management.")


if __name__ == "__main__":
    # Run the demo
    asyncio.run(demo_ticket_tools())
