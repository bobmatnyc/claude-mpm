#!/usr/bin/env python3
"""
Test script to verify the MCP server is working properly.

This script tests the MCP server by sending proper JSON-RPC requests
and verifying responses.
"""

import json
import subprocess
import sys
from pathlib import Path


def test_mcp_server():
    """Test the MCP server with proper JSON-RPC communication."""

    print("Testing MCP server...")

    # Find the Python executable
    venv_python = Path(__file__).parent.parent / "venv" / "bin" / "python"
    if not venv_python.exists():
        venv_python = sys.executable

    # Start the MCP server process
    cmd = [str(venv_python), "-m", "claude_mpm.cli", "mcp", "start"]
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        # Send initialize request
        initialize_request = {
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
        proc.stdin.write(json.dumps(initialize_request) + "\n")
        proc.stdin.flush()

        # Read response (with timeout)
        import time

        # Wait for response
        time.sleep(1)

        # Check if there's output
        response_line = proc.stdout.readline()
        if response_line:
            try:
                response = json.loads(response_line)
                print(f"✅ Server responded: {json.dumps(response, indent=2)}")

                # Check if it's a valid JSON-RPC response
                if "jsonrpc" in response and response["jsonrpc"] == "2.0":
                    print("✅ Valid JSON-RPC response received")

                    # Send a list tools request
                    list_tools_request = {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/list",
                        "params": {},
                    }

                    proc.stdin.write(json.dumps(list_tools_request) + "\n")
                    proc.stdin.flush()

                    time.sleep(1)
                    response_line = proc.stdout.readline()
                    if response_line:
                        response = json.loads(response_line)
                        print(
                            f"✅ Tools list response: {json.dumps(response, indent=2)}"
                        )

                    return True
                print("❌ Invalid JSON-RPC response format")
                return False

            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse response: {e}")
                print(f"   Raw response: {response_line}")
                return False
        else:
            print("❌ No response from server")
            stderr = proc.stderr.read()
            if stderr:
                print(f"   Server errors: {stderr}")
            return False

    finally:
        # Clean up
        proc.terminate()
        try:
            proc.wait(timeout=2)
            print("\n✅ Server terminated cleanly")
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            print("\n✅ Server terminated (forced)")


if __name__ == "__main__":
    success = test_mcp_server()
    sys.exit(0 if success else 1)
