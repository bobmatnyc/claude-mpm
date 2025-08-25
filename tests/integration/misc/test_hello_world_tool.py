import pytest

#!/usr/bin/env python3
"""
Integration Test Script for Hello World MCP Tool
=================================================

Tests the Hello World tool integration with the MCP Gateway.
Demonstrates tool registration, discovery, and invocation.

Part of ISS-0036: Hello World Tool - Testing and Validation Tool

Usage:
    python scripts/test_hello_world_tool.py [--verbose]
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.mcp_gateway.core.interfaces import MCPToolInvocation
from claude_mpm.services.mcp_gateway.registry.tool_registry import ToolRegistry
from claude_mpm.services.mcp_gateway.tools.hello_world import HelloWorldTool


@pytest.mark.asyncio
async def test_hello_world_tool(verbose: bool = False):
    """
    Test the Hello World tool with the MCP Gateway.

    Args:
        verbose: Enable verbose output
    """
    print("=" * 60)
    print("Hello World Tool Integration Test")
    print("=" * 60)

    # Create tool registry
    print("\n1. Creating tool registry...")
    registry = ToolRegistry()
    await registry.initialize()
    print("   ✓ Registry initialized")

    # Create Hello World tool
    print("\n2. Creating Hello World tool...")
    hello_tool = HelloWorldTool()
    await hello_tool.initialize()
    print(f"   ✓ Hello World Tool v{hello_tool.version} initialized")

    # Register the tool
    print("\n3. Registering tool with registry...")
    success = registry.register_tool(hello_tool)
    if success:
        print("   ✓ Tool registered successfully")
    else:
        print("   ✗ Failed to register tool")
        return False

    # Discover the tool
    print("\n4. Testing tool discovery...")
    tools = registry.list_tools()
    hello_found = any(t.name == "hello_world" for t in tools)
    if hello_found:
        print(f"   ✓ Tool found in registry ({len(tools)} total tools)")
    else:
        print("   ✗ Tool not found in registry")
        return False

    # Get tool by name
    retrieved_tool = registry.get_tool("hello_world")
    if retrieved_tool:
        print("   ✓ Tool retrieved by name")
    else:
        print("   ✗ Failed to retrieve tool by name")
        return False

    # Test various greeting modes
    print("\n5. Testing greeting modes...")
    test_cases = [
        {"name": "Simple Greeting", "params": {"mode": "simple"}},
        {
            "name": "Personalized Greeting",
            "params": {"mode": "personalized", "name": "MCP Tester"},
        },
        {"name": "Time-based Greeting", "params": {"mode": "time_based"}},
        {
            "name": "Multi-language (Spanish)",
            "params": {
                "mode": "multi_language",
                "language": "spanish",
                "name": "Usuario",
            },
        },
        {
            "name": "Multi-language (Japanese)",
            "params": {"mode": "multi_language", "language": "japanese"},
        },
        {"name": "System Info Greeting", "params": {"mode": "system_info"}},
        {
            "name": "Async Test (200ms)",
            "params": {"mode": "async_test", "delay_ms": 200},
        },
        {"name": "Uppercase Simple", "params": {"mode": "simple", "uppercase": True}},
        {"name": "Repeated Greeting", "params": {"mode": "simple", "repeat": 3}},
        {
            "name": "Full Metadata",
            "params": {
                "mode": "personalized",
                "name": "Developer",
                "include_metadata": True,
            },
        },
    ]

    successful_tests = 0
    failed_tests = 0

    for test_case in test_cases:
        print(f"\n   Testing: {test_case['name']}")

        # Create invocation through registry
        invocation = MCPToolInvocation(
            tool_name="hello_world", parameters=test_case["params"]
        )

        try:
            # Invoke through registry
            result = await registry.invoke_tool(invocation)

            if result.success:
                successful_tests += 1
                if verbose:
                    print(
                        f"      Parameters: {json.dumps(test_case['params'], indent=8)}"
                    )
                    print(
                        f"      Response: {json.dumps(result.data, indent=8, ensure_ascii=False)}"
                    )
                    print(f"      Execution time: {result.execution_time:.3f}s")
                else:
                    greeting = result.data.get("greeting", "N/A")
                    # Truncate long greetings for display
                    if len(greeting) > 50:
                        greeting = greeting[:47] + "..."
                    print(f"      ✓ Success: {greeting}")
            else:
                failed_tests += 1
                print(f"      ✗ Failed: {result.error}")

        except Exception as e:
            failed_tests += 1
            print(f"      ✗ Exception: {e!s}")

    # Test error handling
    print("\n6. Testing error handling...")
    error_cases = [
        {"name": "Missing required parameter", "params": {}},
        {"name": "Invalid mode", "params": {"mode": "invalid_mode"}},
        {"name": "Personalized without name", "params": {"mode": "personalized"}},
        {
            "name": "Invalid language",
            "params": {"mode": "multi_language", "language": "klingon"},
        },
        {"name": "Invalid repeat value", "params": {"mode": "simple", "repeat": 100}},
        {
            "name": "Simulated validation error",
            "params": {"mode": "error_test", "error_type": "validation"},
        },
        {
            "name": "Simulated runtime error",
            "params": {"mode": "error_test", "error_type": "runtime"},
        },
    ]

    error_handled = 0

    for error_case in error_cases:
        print(f"\n   Testing: {error_case['name']}")

        invocation = MCPToolInvocation(
            tool_name="hello_world", parameters=error_case["params"]
        )

        try:
            result = await registry.invoke_tool(invocation)

            if not result.success:
                error_handled += 1
                if verbose:
                    print(f"      ✓ Error handled correctly: {result.error}")
                else:
                    print("      ✓ Error handled correctly")
            else:
                print("      ✗ Expected error but got success")

        except Exception as e:
            error_handled += 1
            if verbose:
                print(f"      ✓ Exception handled: {e!s}")
            else:
                print("      ✓ Exception handled")

    # Get analytics
    print("\n7. Tool Analytics...")
    analytics = hello_tool.get_analytics()
    print(f"   Total greetings: {analytics['total_greetings']}")
    print(f"   Average execution time: {analytics['average_execution_time']:.3f}s")
    if analytics["modes_used"]:
        print("   Modes used:")
        for mode, count in analytics["modes_used"].items():
            print(f"      - {mode}: {count}")

    # Get registry metrics
    print("\n8. Registry Metrics...")
    metrics = registry.get_metrics()
    print(f"   Total tools: {metrics['total_tools']}")
    if "hello_world" in metrics.get("invocations", {}):
        print(f"   Hello World invocations: {metrics['invocations']['hello_world']}")

    # Cleanup
    print("\n9. Cleanup...")
    registry.unregister_tool("hello_world")
    print("   ✓ Tool unregistered")

    await hello_tool.shutdown()
    print("   ✓ Tool shutdown")

    await registry.shutdown()
    print("   ✓ Registry shutdown")

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(
        f"Greeting modes tested: {successful_tests}/{successful_tests + failed_tests}"
    )
    print(f"Error cases handled: {error_handled}/{len(error_cases)}")

    total_success = successful_tests + error_handled
    total_tests = successful_tests + failed_tests + len(error_cases)
    success_rate = (total_success / total_tests) * 100 if total_tests > 0 else 0

    print(f"Overall success rate: {success_rate:.1f}%")

    if success_rate >= 95:
        print("\n✅ Hello World Tool validation PASSED!")
        print("The MCP Gateway is working correctly.")
        return True
    print("\n❌ Hello World Tool validation FAILED")
    print("Please check the errors above.")
    return False


async def benchmark_hello_world_tool():
    """
    Benchmark the Hello World tool performance.
    """
    print("\n" + "=" * 60)
    print("Hello World Tool Performance Benchmark")
    print("=" * 60)

    # Initialize components
    registry = ToolRegistry()
    await registry.initialize()

    hello_tool = HelloWorldTool()
    await hello_tool.initialize()
    registry.register_tool(hello_tool)

    # Benchmark different modes
    modes_to_benchmark = [
        ("simple", {"mode": "simple"}),
        ("personalized", {"mode": "personalized", "name": "Benchmark"}),
        ("multi_language", {"mode": "multi_language", "language": "japanese"}),
        ("async_100ms", {"mode": "async_test", "delay_ms": 100}),
    ]

    print("\nRunning benchmarks (100 iterations each)...")

    for mode_name, params in modes_to_benchmark:
        print(f"\n{mode_name}:")

        times = []
        for _ in range(100):
            invocation = MCPToolInvocation(tool_name="hello_world", parameters=params)

            start = datetime.now()
            result = await registry.invoke_tool(invocation)
            duration = (datetime.now() - start).total_seconds()

            if result.success:
                times.append(duration)

        if times:
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)

            print(f"   Average: {avg_time*1000:.2f}ms")
            print(f"   Min: {min_time*1000:.2f}ms")
            print(f"   Max: {max_time*1000:.2f}ms")

    # Cleanup
    registry.unregister_tool("hello_world")
    await hello_tool.shutdown()
    await registry.shutdown()

    print("\n✅ Benchmark completed")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test Hello World MCP Tool integration"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )
    parser.add_argument(
        "--benchmark", "-b", action="store_true", help="Run performance benchmark"
    )

    args = parser.parse_args()

    # Run tests
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        if args.benchmark:
            loop.run_until_complete(benchmark_hello_world_tool())
        else:
            success = loop.run_until_complete(test_hello_world_tool(args.verbose))
            sys.exit(0 if success else 1)
    finally:
        loop.close()


if __name__ == "__main__":
    main()
