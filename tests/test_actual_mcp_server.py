#!/usr/bin/env python3
"""Test actual MCP server memory usage with proper protocol."""

import asyncio
import sys
from pathlib import Path

import psutil

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def get_memory_usage():
    """Get current process memory usage in MB."""
    process = psutil.Process()
    return process.memory_info().rss / 1024 / 1024


async def simulate_mcp_request():
    """Simulate what happens when Claude Code makes a request."""

    print("Simulating MCP server lifecycle...")
    initial_mem = get_memory_usage()
    print(f"Initial memory: {initial_mem:.2f} MB\n")

    # Import and create server (this happens once per process)
    from claude_mpm.services.mcp_gateway.server.stdio_server import SimpleMCPServer

    server = SimpleMCPServer()
    print(f"After server creation: {get_memory_usage():.2f} MB")

    # Initialize ticket tool (happens once)
    await server._initialize_ticket_tool()
    print(f"After ticket tool init: {get_memory_usage():.2f} MB\n")

    # Simulate multiple ticket list requests
    for i in range(5):
        print(f"--- Request {i + 1}: ticket list ---")
        mem_before = get_memory_usage()

        # This is what happens when Claude invokes the tool
        try:
            from claude_mpm.services.mcp_gateway.core.interfaces import (
                MCPToolInvocation,
            )

            invocation = MCPToolInvocation(
                tool_name="ticket",
                parameters={"operation": "list", "limit": 10},
                request_id=f"req_{i}",
            )

            result = await server.unified_ticket_tool.invoke(invocation)
            print(f"  Result success: {result.success}")
            if result.data and isinstance(result.data, str):
                print(f"  Data length: {len(result.data)} chars")
        except Exception as e:
            print(f"  Error: {e}")

        mem_after = get_memory_usage()
        print(f"  Memory before: {mem_before:.2f} MB")
        print(f"  Memory after: {mem_after:.2f} MB")
        print(f"  Increase: {(mem_after - mem_before):.2f} MB\n")

    final_mem = get_memory_usage()
    print(f"Final memory: {final_mem:.2f} MB")
    print(f"Total increase: {(final_mem - initial_mem):.2f} MB")


if __name__ == "__main__":
    asyncio.run(simulate_mcp_request())
