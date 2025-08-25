#!/usr/bin/env python3
"""
Simple test for the unified ticket tool.

WHY: This provides a basic verification that the unified ticket tool
can be imported and initialized without the full MCP Gateway stack.
"""

import asyncio
import sys
from pathlib import Path

# Add the src directory to Python path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from claude_mpm.services.mcp_gateway.tools.unified_ticket_tool import UnifiedTicketTool


async def simple_test():
    """Run a simple test of the unified ticket tool."""
    print("Simple Unified Ticket Tool Test")
    print("=" * 50)

    try:
        # Create the tool
        print("\n1. Creating unified ticket tool...")
        tool = UnifiedTicketTool()
        print("✅ Tool created")

        # Initialize
        print("\n2. Initializing tool...")
        if await tool.initialize():
            print("✅ Tool initialized")
        else:
            print("❌ Failed to initialize")
            return

        # Get definition
        print("\n3. Getting tool definition...")
        definition = tool.get_definition()
        print(f"✅ Tool name: {definition.name}")
        print(f"   Description: {definition.description}")

        # Check schema
        print("\n4. Checking schema...")
        schema = definition.input_schema
        if "properties" in schema and "operation" in schema["properties"]:
            operations = schema["properties"]["operation"].get("enum", [])
            print(f"✅ Operations available: {', '.join(operations)}")
        else:
            print("❌ Schema missing operation parameter")

        # Test parameter validation
        print("\n5. Testing parameter validation...")

        test_params = [
            (
                {"operation": "create", "type": "task", "title": "Test"},
                True,
                "Valid create",
            ),
            ({"operation": "list"}, True, "Valid list"),
            (
                {"operation": "invalid"},
                True,
                "Invalid operation (schema allows, handler rejects)",
            ),
            ({}, False, "Missing operation"),
        ]

        for params, expected, desc in test_params:
            is_valid = tool.validate_parameters(params)
            status = "✅" if is_valid == expected else "❌"
            print(f"   {status} {desc}: {is_valid}")

        # Shutdown
        print("\n6. Shutting down...")
        await tool.shutdown()
        print("✅ Tool shutdown complete")

        print("\n" + "=" * 50)
        print("✅ Simple test completed successfully!")
        print("=" * 50)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(simple_test())
