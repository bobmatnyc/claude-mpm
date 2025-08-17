#!/usr/bin/env python3
"""
Integration test for MCP ticket tools with aitrackdown.

WHY: This script verifies that the MCP ticket tools correctly integrate
with the actual aitrackdown CLI tool.

Usage:
    python tests/integration/test_mcp_ticket_integration.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from claude_mpm.services.mcp_gateway.tools.ticket_tools import (
    TicketCreateTool,
    TicketListTool,
    TicketViewTool,
    TicketSearchTool,
    TicketUpdateTool
)
from claude_mpm.services.mcp_gateway.core.interfaces import MCPToolInvocation


async def test_ticket_workflow():
    """Test a complete ticket workflow."""
    print("Testing MCP Ticket Tools Integration with aitrackdown")
    print("=" * 60)
    
    # 1. Create a test ticket
    print("\n1. Creating a test ticket...")
    create_tool = TicketCreateTool()
    create_invocation = MCPToolInvocation(
        tool_name="ticket_create",
        parameters={
            "type": "task",
            "title": "Test MCP integration",
            "description": "Testing the MCP tool wrappers for aitrackdown",
            "priority": "medium",
            "tags": ["test", "mcp", "integration"]
        }
    )
    
    try:
        result = await create_tool.invoke(create_invocation)
        if result.success:
            ticket_id = result.data.get("ticket_id", "Unknown")
            print(f"✅ Created ticket: {ticket_id}")
            print(f"   Message: {result.data.get('message', '')}")
        else:
            print(f"❌ Failed to create ticket: {result.error}")
            return
    except Exception as e:
        print(f"❌ Error creating ticket: {e}")
        return
    
    # 2. List recent tickets
    print("\n2. Listing recent tickets...")
    list_tool = TicketListTool()
    list_invocation = MCPToolInvocation(
        tool_name="ticket_list",
        parameters={
            "limit": 5,
            "type": "task"
        }
    )
    
    try:
        result = await list_tool.invoke(list_invocation)
        if result.success:
            print(f"✅ Found tickets:")
            if isinstance(result.data, list):
                for ticket in result.data[:5]:
                    print(f"   - {ticket.get('id', 'Unknown')}: {ticket.get('title', 'Unknown')}")
            else:
                print(f"   Raw output: {result.data}")
        else:
            print(f"❌ Failed to list tickets: {result.error}")
    except Exception as e:
        print(f"❌ Error listing tickets: {e}")
    
    # 3. View the created ticket (if we have an ID)
    if ticket_id and ticket_id != "Unknown":
        print(f"\n3. Viewing ticket {ticket_id}...")
        view_tool = TicketViewTool()
        view_invocation = MCPToolInvocation(
            tool_name="ticket_view",
            parameters={
                "ticket_id": ticket_id,
                "format": "json"
            }
        )
        
        try:
            result = await view_tool.invoke(view_invocation)
            if result.success:
                print(f"✅ Ticket details:")
                if isinstance(result.data, dict):
                    print(f"   Title: {result.data.get('title', 'Unknown')}")
                    print(f"   Status: {result.data.get('status', 'Unknown')}")
                    print(f"   Priority: {result.data.get('priority', 'Unknown')}")
                else:
                    print(f"   {result.data}")
            else:
                print(f"❌ Failed to view ticket: {result.error}")
        except Exception as e:
            print(f"❌ Error viewing ticket: {e}")
        
        # 4. Update the ticket status
        print(f"\n4. Updating ticket {ticket_id} status...")
        update_tool = TicketUpdateTool()
        update_invocation = MCPToolInvocation(
            tool_name="ticket_update",
            parameters={
                "ticket_id": ticket_id,
                "status": "in-progress",
                "comment": "Started working on MCP integration"
            }
        )
        
        try:
            result = await update_tool.invoke(update_invocation)
            if result.success:
                print(f"✅ Updated ticket status")
                print(f"   {result.data.get('message', 'Status updated')}")
            else:
                print(f"❌ Failed to update ticket: {result.error}")
        except Exception as e:
            print(f"❌ Error updating ticket: {e}")
    
    # 5. Search for tickets
    print("\n5. Searching for MCP-related tickets...")
    search_tool = TicketSearchTool()
    search_invocation = MCPToolInvocation(
        tool_name="ticket_search",
        parameters={
            "query": "MCP",
            "limit": 5
        }
    )
    
    try:
        result = await search_tool.invoke(search_invocation)
        if result.success:
            print(f"✅ Search results:")
            if isinstance(result.data, list):
                for ticket in result.data[:5]:
                    print(f"   - {ticket.get('id', 'Unknown')}: {ticket.get('title', 'Unknown')}")
            else:
                print(f"   {result.data}")
        else:
            print(f"❌ Failed to search tickets: {result.error}")
    except Exception as e:
        print(f"❌ Error searching tickets: {e}")
    
    print("\n" + "=" * 60)
    print("Integration test completed!")


if __name__ == "__main__":
    # Run the async test
    asyncio.run(test_ticket_workflow())