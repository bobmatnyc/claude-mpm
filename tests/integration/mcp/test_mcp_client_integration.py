import pytest

#!/usr/bin/env python3
"""
Test MCP Client Integration
===========================

Tests the official MCP server with a simple MCP client to ensure
standards compliance and proper protocol implementation.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class SimpleMCPClient:
    """Simple MCP client for testing the server."""

    def __init__(self, server_process):
        self.server_process = server_process
        self.request_id = 0

    def get_next_id(self) -> int:
        """Get next request ID."""
        self.request_id += 1
        return self.request_id

    async def send_request(
        self, method: str, params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Send a JSON-RPC request to the server."""
        request = {"jsonrpc": "2.0", "id": self.get_next_id(), "method": method}

        if params:
            request["params"] = params

        # Send request
        request_json = json.dumps(request) + "\n"
        self.server_process.stdin.write(request_json.encode())
        await self.server_process.stdin.drain()

        # Read response
        response_line = await self.server_process.stdout.readline()
        if not response_line:
            raise Exception("No response from server")

        try:
            response = json.loads(response_line.decode().strip())
            return response
        except json.JSONDecodeError:
            raise Exception(f"Invalid JSON response: {response_line.decode()}")

    async def initialize(self) -> Dict[str, Any]:
        """Initialize the MCP connection."""
        return await self.send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        )

    async def list_tools(self) -> Dict[str, Any]:
        """List available tools."""
        return await self.send_request("tools/list")

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool."""
        return await self.send_request(
            "tools/call", {"name": name, "arguments": arguments}
        )


@pytest.mark.asyncio
async def test_mcp_integration():
    """Test MCP server integration with a client."""
    print("🧪 Testing MCP Server Integration")
    print("=" * 50)

    # Start the MCP server
    print("1. Starting MCP server...")
    server_cmd = [sys.executable, "-m", "claude_mpm.cli", "mcp", "start"]

    server_process = await asyncio.create_subprocess_exec(
        *server_cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=Path(__file__).parent.parent,
    )

    try:
        # Give server time to start
        await asyncio.sleep(1)

        # Create client
        client = SimpleMCPClient(server_process)

        # Test 1: Initialize connection
        print("2. Testing initialization...")
        try:
            init_response = await client.initialize()
            if "result" in init_response:
                print("   ✅ Initialization successful")
                print(
                    f"   Protocol version: {init_response['result'].get('protocolVersion', 'unknown')}"
                )
                print(
                    f"   Server: {init_response['result'].get('serverInfo', {}).get('name', 'unknown')}"
                )
            else:
                print(f"   ❌ Initialization failed: {init_response}")
                return False
        except Exception as e:
            print(f"   ❌ Initialization error: {e}")
            return False

        # Test 2: List tools
        print("3. Testing tool listing...")
        try:
            tools_response = await client.list_tools()
            if "result" in tools_response and "tools" in tools_response["result"]:
                tools = tools_response["result"]["tools"]
                print(f"   ✅ Found {len(tools)} tools:")
                for tool in tools:
                    print(
                        f"      - {tool['name']}: {tool.get('description', 'No description')}"
                    )
            else:
                print(f"   ❌ Tool listing failed: {tools_response}")
                return False
        except Exception as e:
            print(f"   ❌ Tool listing error: {e}")
            return False

        # Test 3: Call echo tool
        print("4. Testing tool invocation (echo)...")
        try:
            echo_response = await client.call_tool(
                "echo", {"message": "MCP Integration Test"}
            )
            if "result" in echo_response:
                result = echo_response["result"]
                if "content" in result and len(result["content"]) > 0:
                    content = result["content"][0]
                    if content.get("type") == "text":
                        print(f"   ✅ Echo tool response: {content['text']}")
                    else:
                        print(f"   ✅ Echo tool response: {result}")
                else:
                    print(f"   ✅ Echo tool response: {result}")
            else:
                print(f"   ❌ Echo tool failed: {echo_response}")
                return False
        except Exception as e:
            print(f"   ❌ Echo tool error: {e}")
            return False

        # Test 4: Call calculator tool
        print("5. Testing tool invocation (calculator)...")
        try:
            calc_response = await client.call_tool(
                "calculator", {"operation": "multiply", "a": 7, "b": 6}
            )
            if "result" in calc_response:
                result = calc_response["result"]
                print(f"   ✅ Calculator tool response: {result}")
            else:
                print(f"   ❌ Calculator tool failed: {calc_response}")
                return False
        except Exception as e:
            print(f"   ❌ Calculator tool error: {e}")
            return False

        print("\n🎉 All MCP integration tests passed!")
        return True

    finally:
        # Clean up
        print("6. Cleaning up...")
        server_process.terminate()
        try:
            await asyncio.wait_for(server_process.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            server_process.kill()
            await server_process.wait()


async def main():
    """Main test function."""
    success = await test_mcp_integration()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
