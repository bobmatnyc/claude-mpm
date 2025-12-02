#!/usr/bin/env python3
"""
Test script to verify MCP server tool registration.

This script simulates what happens when the MCP server starts up,
showing which tools get registered.
"""

import asyncio
import sys
from pathlib import Path

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.claude_mpm.services.mcp_gateway.registry.tool_registry import ToolRegistry

# Import the same components as the MCP server scripts
from src.claude_mpm.services.mcp_gateway.tools.base_adapter import (
    CalculatorToolAdapter,
    EchoToolAdapter,
    SystemInfoToolAdapter,
)
from src.claude_mpm.services.mcp_gateway.tools.document_summarizer import (
    DocumentSummarizerTool,
)
from src.claude_mpm.services.mcp_gateway.tools.unified_ticket_tool import (
    UnifiedTicketTool,
)


@pytest.mark.asyncio
async def test_bin_claude_mpm_mcp():
    """Test what bin/claude-mpm-mcp registers."""
    print("Testing bin/claude-mpm-mcp tool registration")
    print("=" * 50)

    # Create the tool registry
    registry = ToolRegistry()
    await registry.initialize()

    # Register all available tools (matching bin/claude-mpm-mcp)
    tools = [
        # Basic tools
        EchoToolAdapter(),
        CalculatorToolAdapter(),
        SystemInfoToolAdapter(),
        # Document summarizer
        DocumentSummarizerTool(),
        # Unified ticket management tool
        UnifiedTicketTool(),
    ]

    # Initialize and register each tool
    for tool in tools:
        try:
            if await tool.initialize():
                if registry.register_tool(tool, category="builtin"):
                    print(f"✓ Registered tool: {tool.get_definition().name}")
                else:
                    print(f"✗ Failed to register tool: {tool.get_definition().name}")
            else:
                print(f"✗ Failed to initialize tool: {tool.get_definition().name}")
        except Exception as e:
            print(f"✗ Error with tool {type(tool).__name__}: {e}")

    # List all registered tools
    registered_tools = registry.list_tools()
    print(f"\nTotal tools registered: {len(registered_tools)}")

    # Check for ticket tools
    ticket_tools = [t for t in registered_tools if "ticket" in t.name.lower()]
    print(f"Ticket tools found: {len(ticket_tools)}")

    if len(ticket_tools) == 1 and ticket_tools[0].name == "ticket":
        print("✓ Only unified ticket tool registered (correct!)")
        return True
    print("✗ Wrong ticket tool configuration!")
    for t in ticket_tools:
        print(f"  - {t.name}: {t.description}")
    return False


@pytest.mark.asyncio
async def test_main_py():
    """Test what main.py registers."""
    print("\n" + "=" * 50)
    print("Testing main.py tool registration")
    print("=" * 50)

    # Import and use the orchestrator from main.py
    from src.claude_mpm.services.mcp_gateway.main import MCPGatewayOrchestrator

    orchestrator = MCPGatewayOrchestrator()

    # Initialize (this will register tools)
    if await orchestrator.initialize():
        print("✓ Orchestrator initialized successfully")

        # Check what tools were registered
        if orchestrator.registry:
            tools = orchestrator.registry.list_tools()
            print(f"Total tools registered: {len(tools)}")

            # List all tools
            for tool in tools:
                print(f"  - {tool.name}: {tool.description[:50]}...")

            # Check ticket tools
            ticket_tools = [t for t in tools if "ticket" in t.name.lower()]
            print(f"\nTicket tools found: {len(ticket_tools)}")

            if len(ticket_tools) == 1 and ticket_tools[0].name == "ticket":
                print("✓ Only unified ticket tool registered (correct!)")
                return True
            print("✗ Wrong ticket tool configuration!")
            return False
        print("✗ No registry available")
        return False
    print("✗ Failed to initialize orchestrator")
    return False


async def main():
    """Run all registration tests."""
    print("MCP Server Tool Registration Test")
    print("=" * 50)

    success = True

    # Test bin/claude-mpm-mcp
    if not await test_bin_claude_mpm_mcp():
        success = False

    # Test main.py
    if not await test_main_py():
        success = False

    if success:
        print("\n" + "=" * 50)
        print("✓ SUCCESS: All MCP servers use unified ticket tool")
        print("No more 5 separate ticket tools!")
        print("=" * 50)
        return 0
    print("\n" + "=" * 50)
    print("✗ FAILURE: Some servers still have wrong configuration")
    print("=" * 50)
    return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
