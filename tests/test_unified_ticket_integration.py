#!/usr/bin/env python3
"""
Integration test for the unified ticket tool.

WHY: This script performs a more thorough integration test of the unified
ticket tool, verifying that the actual invocation handles conditional
parameter validation correctly.
"""

import asyncio
import sys
from pathlib import Path

import pytest

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.claude_mpm.services.mcp_gateway.core.interfaces import MCPToolInvocation
from src.claude_mpm.services.mcp_gateway.tools.unified_ticket_tool import (
    UnifiedTicketTool,
)


@pytest.mark.asyncio
async def test_integration():
    """Test the unified ticket tool with actual invocations."""
    print("Unified Ticket Tool Integration Test")
    print("=" * 50)

    # Create and initialize the tool
    tool = UnifiedTicketTool()
    await tool.initialize()

    # Test 1: Invalid operation should fail
    print("\n1. Testing invalid operation:")
    invocation = MCPToolInvocation(
        tool_name="ticket", parameters={"operation": "invalid"}
    )
    result = await tool.invoke(invocation)
    print(f"   Success: {result.success}")
    print(f"   Error: {result.error}")
    assert not result.success, "Invalid operation should fail"
    assert "Unknown operation" in result.error
    print("   ✅ Correctly rejected invalid operation")

    # Test 2: Missing operation should fail
    print("\n2. Testing missing operation:")
    invocation = MCPToolInvocation(
        tool_name="ticket", parameters={"type": "task", "title": "Test"}
    )
    result = await tool.invoke(invocation)
    print(f"   Success: {result.success}")
    print(f"   Error: {result.error}")
    assert not result.success, "Missing operation should fail"
    assert "Operation parameter is required" in result.error
    print("   ✅ Correctly rejected missing operation")

    # Test 3: Create without required fields should fail at CLI level
    print("\n3. Testing create without title (will fail at CLI):")
    invocation = MCPToolInvocation(
        tool_name="ticket", parameters={"operation": "create", "type": "task"}
    )
    result = await tool.invoke(invocation)
    print(f"   Success: {result.success}")
    if not result.success:
        print(f"   Error: {result.error}")
        print("   ✅ Create without title failed as expected")
    else:
        print("   ⚠️  Create without title unexpectedly succeeded")

    # Test 4: Update without ticket_id should fail
    print("\n4. Testing update without ticket_id:")
    invocation = MCPToolInvocation(
        tool_name="ticket", parameters={"operation": "update", "status": "open"}
    )
    # This should fail at parameter validation or during execution
    try:
        result = await tool.invoke(invocation)
        print(f"   Success: {result.success}")
        if not result.success:
            print(f"   Error: {result.error}")
            print("   ✅ Update without ticket_id failed as expected")
    except KeyError as e:
        print(f"   KeyError: {e}")
        print("   ✅ Update without ticket_id failed with KeyError as expected")

    # Test 5: Test operation routing works
    print("\n5. Testing operation routing:")
    operations_tested = 0
    for op in ["create", "list", "update", "view", "search"]:
        handler_name = f"_handle_{op}"
        if hasattr(tool, handler_name):
            operations_tested += 1
            print(f"   ✅ {op} handler exists")
    assert operations_tested == 5, "All 5 operations should have handlers"

    # Test 6: Check metrics tracking
    print("\n6. Testing metrics tracking:")
    metrics = tool.get_metrics()
    print(f"   Total invocations: {metrics['invocations']}")
    print(f"   Failures tracked: {metrics['failures']}")
    assert metrics["invocations"] > 0, "Should have tracked invocations"
    print("   ✅ Metrics are being tracked")

    await tool.shutdown()

    print("\n" + "=" * 50)
    print("✅ Integration test completed successfully!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(test_integration())
