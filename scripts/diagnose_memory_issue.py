#!/usr/bin/env python3
"""
Diagnose memory accumulation issue in MCP server.

This script traces what happens when the ticket tool is invoked
to identify where memory accumulation occurs.
"""

import asyncio
import gc
import json
import psutil
import sys
import time
import tracemalloc
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.mcp_gateway.server.stdio_server import SimpleMCPServer
from claude_mpm.services.mcp_gateway.core.interfaces import MCPToolInvocation


def get_memory_usage():
    """Get current process memory usage in MB."""
    process = psutil.Process()
    return process.memory_info().rss / 1024 / 1024


async def test_ticket_tool():
    """Test the ticket tool invocation and track memory."""
    print("Starting memory diagnosis...")
    print(f"Initial memory: {get_memory_usage():.2f} MB\n")
    
    # Start memory tracing
    tracemalloc.start()
    
    # Create server instance
    server = SimpleMCPServer()
    print(f"After server creation: {get_memory_usage():.2f} MB")
    
    # Initialize ticket tool
    await server._initialize_ticket_tool()
    print(f"After ticket tool init: {get_memory_usage():.2f} MB\n")
    
    # Track memory for multiple invocations
    for i in range(3):
        print(f"\n--- Invocation {i+1} ---")
        
        # Force garbage collection before measurement
        gc.collect()
        mem_before = get_memory_usage()
        
        # Create invocation
        invocation = MCPToolInvocation(
            tool_name="ticket",
            parameters={
                "operation": "list",
                "limit": 5
            },
            request_id=f"test_req_{i}"
        )
        
        # Invoke the tool
        try:
            result = await server.unified_ticket_tool.invoke(invocation)
            print(f"Tool result success: {result.success}")
        except Exception as e:
            print(f"Tool invocation error: {e}")
        
        # Force garbage collection after invocation
        gc.collect()
        mem_after = get_memory_usage()
        
        print(f"Memory before: {mem_before:.2f} MB")
        print(f"Memory after: {mem_after:.2f} MB")
        print(f"Memory increase: {(mem_after - mem_before):.2f} MB")
        
        # Get top memory allocations
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')[:5]
        
        print("\nTop 5 memory allocations:")
        for stat in top_stats:
            print(f"  {stat}: {stat.size / 1024:.2f} KB")
    
    # Final memory check
    gc.collect()
    final_memory = get_memory_usage()
    print(f"\n--- Final Report ---")
    print(f"Final memory: {final_memory:.2f} MB")
    
    # Stop memory tracing
    tracemalloc.stop()


async def test_framework_loader():
    """Test if FrameworkLoader is causing memory accumulation."""
    print("\n=== Testing FrameworkLoader ===")
    
    from claude_mpm.core.framework_loader import FrameworkLoader
    
    tracemalloc.start()
    initial_mem = get_memory_usage()
    print(f"Initial memory: {initial_mem:.2f} MB")
    
    loaders = []
    for i in range(3):
        print(f"\n--- Creating FrameworkLoader {i+1} ---")
        gc.collect()
        mem_before = get_memory_usage()
        
        loader = FrameworkLoader()
        instructions = loader.get_framework_instructions()
        loaders.append(loader)  # Keep reference to prevent GC
        
        gc.collect()
        mem_after = get_memory_usage()
        
        print(f"Memory increase: {(mem_after - mem_before):.2f} MB")
        print(f"Instructions length: {len(instructions)} chars")
    
    # Check if clearing references helps
    print("\n--- Clearing loader references ---")
    gc.collect()
    mem_before_clear = get_memory_usage()
    
    loaders.clear()
    gc.collect()
    mem_after_clear = get_memory_usage()
    
    print(f"Memory before clear: {mem_before_clear:.2f} MB")
    print(f"Memory after clear: {mem_after_clear:.2f} MB")
    print(f"Memory released: {(mem_before_clear - mem_after_clear):.2f} MB")
    
    tracemalloc.stop()


async def test_system_instructions_service():
    """Test if SystemInstructionsService accumulates memory."""
    print("\n=== Testing SystemInstructionsService ===")
    
    from claude_mpm.services.system_instructions_service import SystemInstructionsService
    
    tracemalloc.start()
    initial_mem = get_memory_usage()
    print(f"Initial memory: {initial_mem:.2f} MB")
    
    services = []
    for i in range(3):
        print(f"\n--- Creating SystemInstructionsService {i+1} ---")
        gc.collect()
        mem_before = get_memory_usage()
        
        service = SystemInstructionsService()
        instructions = service.load_system_instructions()
        services.append(service)  # Keep reference to prevent GC
        
        gc.collect()
        mem_after = get_memory_usage()
        
        print(f"Memory increase: {(mem_after - mem_before):.2f} MB")
        print(f"Instructions length: {len(instructions)} chars")
        print(f"Service has cached loader: {service._framework_loader is not None}")
        print(f"Service has cached instructions: {service._loaded_instructions is not None}")
    
    # Check if services share the same loader
    if len(services) > 1:
        print(f"\nLoaders are same object: {services[0]._framework_loader is services[1]._framework_loader}")
    
    # Clear references
    print("\n--- Clearing service references ---")
    gc.collect()
    mem_before_clear = get_memory_usage()
    
    services.clear()
    gc.collect()
    mem_after_clear = get_memory_usage()
    
    print(f"Memory before clear: {mem_before_clear:.2f} MB")
    print(f"Memory after clear: {mem_after_clear:.2f} MB")
    print(f"Memory released: {(mem_before_clear - mem_after_clear):.2f} MB")
    
    tracemalloc.stop()


async def main():
    """Run all diagnostic tests."""
    print("MCP Memory Accumulation Diagnostic\n")
    print("=" * 50)
    
    # Test ticket tool invocations
    await test_ticket_tool()
    
    # Test FrameworkLoader directly
    await test_framework_loader()
    
    # Test SystemInstructionsService
    await test_system_instructions_service()


if __name__ == "__main__":
    asyncio.run(main())
