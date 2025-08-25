import pytest

#!/usr/bin/env python3
"""
Test MCP Stdio Server
=====================

A simple test script to verify the MCP stdio server works correctly.
This simulates how Claude Code would communicate with the server.

WHY: We need to test that our stdio-based MCP server correctly handles
JSON-RPC messages over stdin/stdout.
"""

import asyncio
import json
import subprocess
import sys


@pytest.mark.asyncio
async def test_mcp_server():
    """Test the MCP stdio server with sample requests."""

    print("Testing MCP Stdio Server")
    print("=" * 50)

    # Start the MCP server as a subprocess
    cmd = [sys.executable, "-m", "claude_mpm.cli", "mcp", "start"]

    print(f"Starting server with command: {' '.join(cmd)}")
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    try:
        # Test 1: Initialize request
        print("\n1. Sending initialize request...")
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "0.1.0",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        }

        # Send request
        request_str = json.dumps(init_request) + "\n"
        proc.stdin.write(request_str.encode())
        await proc.stdin.drain()

        # Read response
        response_line = await asyncio.wait_for(proc.stdout.readline(), timeout=5.0)
        response = json.loads(response_line.decode())
        print(f"Response: {json.dumps(response, indent=2)}")

        # Test 2: List tools
        print("\n2. Sending tools/list request...")
        list_request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}

        request_str = json.dumps(list_request) + "\n"
        proc.stdin.write(request_str.encode())
        await proc.stdin.drain()

        response_line = await asyncio.wait_for(proc.stdout.readline(), timeout=5.0)
        response = json.loads(response_line.decode())
        print(f"Response: {json.dumps(response, indent=2)}")

        # Test 3: Call a tool
        print("\n3. Sending tools/call request (echo)...")
        call_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "echo",
                "arguments": {"message": "Hello from test client!"},
            },
        }

        request_str = json.dumps(call_request) + "\n"
        proc.stdin.write(request_str.encode())
        await proc.stdin.drain()

        response_line = await asyncio.wait_for(proc.stdout.readline(), timeout=5.0)
        response = json.loads(response_line.decode())
        print(f"Response: {json.dumps(response, indent=2)}")

        # Test 4: Calculator tool
        print("\n4. Sending tools/call request (calculator)...")
        calc_request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "calculator", "arguments": {"expression": "2 + 2 * 3"}},
        }

        request_str = json.dumps(calc_request) + "\n"
        proc.stdin.write(request_str.encode())
        await proc.stdin.drain()

        response_line = await asyncio.wait_for(proc.stdout.readline(), timeout=5.0)
        response = json.loads(response_line.decode())
        print(f"Response: {json.dumps(response, indent=2)}")

        print("\n" + "=" * 50)
        print("All tests completed successfully!")

    except asyncio.TimeoutError:
        print("ERROR: Timeout waiting for server response")
        # Read any stderr output
        stderr_output = await proc.stderr.read()
        if stderr_output:
            print("Server stderr output:")
            print(stderr_output.decode())
        return 1
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON response: {e}")
        return 1
    except Exception as e:
        print(f"ERROR: {e}")
        return 1
    finally:
        # Terminate the server
        print("\nStopping server...")
        proc.terminate()
        await proc.wait()

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(test_mcp_server())
    sys.exit(exit_code)
