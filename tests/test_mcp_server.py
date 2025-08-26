#!/usr/bin/env python3
"""
Test script to verify MCP server functionality.

This script tests the MCP server's ability to handle JSON-RPC requests.
"""

import json
import subprocess
import sys
import time


def test_mcp_server():
    """Test the MCP server with basic requests."""
    print("Testing MCP Server...")

    # Start the MCP server
    cmd = [sys.executable, "-m", "claude_mpm.cli", "mcp", "start"]
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        # Wait for server to start and skip initial output
        time.sleep(2)

        # Read and skip any initial server output
        while True:
            line = proc.stdout.readline()
            if not line or line.strip().startswith("{"):
                # We found JSON or no more lines
                if line and line.strip().startswith("{"):
                    # Put it back if it's JSON
                    proc.stdout = [line, *proc.stdout.readlines()]
                break
            print(f"  Server: {line.strip()}")

        # Send initialization request
        init_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
            "id": 1,
        }

        print(f"Sending: {json.dumps(init_request)[:100]}...")
        proc.stdin.write(json.dumps(init_request) + "\n")
        proc.stdin.flush()

        # Read response - skip non-JSON lines
        response = None
        for _ in range(10):  # Try reading up to 10 lines
            line = proc.stdout.readline()
            if line and line.strip().startswith("{"):
                response = line
                break
            if line:
                print(f"  Server output: {line.strip()}")

        if response:
            result = json.loads(response)
            print(
                f"✓ Server responded to initialize: {result.get('result', {}).get('serverInfo', {}).get('name')}"
            )

        # Send tools/list request
        list_request = {"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": 2}

        proc.stdin.write(json.dumps(list_request) + "\n")
        proc.stdin.flush()

        # Read response
        response = proc.stdout.readline()
        if response:
            result = json.loads(response)
            tools = result.get("result", {}).get("tools", [])
            print(f"✓ Server has {len(tools)} tools available")
            for tool in tools:
                print(f"  - {tool['name']}: {tool['description'][:60]}...")

        print("\n✓ MCP Server is working correctly!")

    except Exception as e:
        print(f"✗ Error testing MCP server: {e}")
        return 1

    finally:
        # Clean up
        proc.terminate()
        proc.wait(timeout=5)

    return 0


if __name__ == "__main__":
    sys.exit(test_mcp_server())
