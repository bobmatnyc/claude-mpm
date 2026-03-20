#!/usr/bin/env python3
"""Test script to verify MCP wrapper functionality."""

import json
import subprocess
import sys
import time


def test_wrapper():
    """Test the MCP wrapper script."""
    print("Testing MCP wrapper script...")

    # Start the wrapper process
    proc = subprocess.Popen(
        [sys.executable, "scripts/mcp_wrapper.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Give it time to start
    time.sleep(2)

    # Send a simple JSON-RPC request to test if it's responding
    test_request = (
        json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-01",
                    "capabilities": {},
                    "clientInfo": {"name": "test-client", "version": "1.0.0"},
                },
                "id": 1,
            }
        )
        + "\n"
    )

    try:
        # Send the request
        proc.stdin.write(test_request)
        proc.stdin.flush()

        # Wait for response with timeout
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        # This is expected - server runs indefinitely
        print("✓ Server is running (as expected)")
    except Exception as e:
        print(f"✗ Error: {e}")
    finally:
        # Terminate the process
        proc.terminate()
        time.sleep(0.5)

        # Get any stderr output
        stderr = proc.stderr.read()
        if stderr:
            print("\nServer stderr output:")
            print("-" * 40)
            for line in stderr.split("\n")[:30]:  # First 30 lines
                if line.strip():
                    print(line)
            print("-" * 40)

        # Check if process started successfully
        if "MCP Server Wrapper Starting" in stderr:
            print("\n✓ Wrapper script started successfully")
        else:
            print("\n✗ Wrapper script may have issues")

        if "SimpleMCPServer class imported successfully" in stderr:
            print("✓ All imports successful")
        elif "Failed to import" in stderr:
            print("✗ Import errors detected")

        return 0 if "Server instance created successfully" in stderr else 1


if __name__ == "__main__":
    sys.exit(test_wrapper())
