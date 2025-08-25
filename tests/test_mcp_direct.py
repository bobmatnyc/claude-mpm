#!/usr/bin/env python3
"""
Direct test of MCP server communication.
"""

import json
import subprocess
import sys
import threading
import time


def read_stderr(proc):
    """Read and print stderr in a separate thread."""
    for line in proc.stderr:
        print(f"[STDERR] {line.strip()}", file=sys.stderr)


def test_mcp_direct():
    """Test MCP server directly."""
    cmd = ["/Users/masa/Library/Python/3.11/bin/claude-mpm-mcp"]

    print(f"Starting MCP server: {' '.join(cmd)}")
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,  # Line buffered
    )

    # Start stderr reader thread
    stderr_thread = threading.Thread(target=read_stderr, args=(proc,))
    stderr_thread.daemon = True
    stderr_thread.start()

    try:
        # Give server a moment to start
        time.sleep(0.5)

        # Send initialize request
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

        request_str = json.dumps(init_request)
        print(f"\nSending: {request_str}")
        proc.stdin.write(request_str + "\n")
        proc.stdin.flush()

        # Read response with timeout
        print("\nWaiting for response...")
        response = proc.stdout.readline()

        if response:
            print(f"\nReceived: {response}")
            try:
                result = json.loads(response)
                server_info = result.get("result", {}).get("serverInfo", {})
                print(
                    f"\n✓ Server initialized: {server_info.get('name')} v{server_info.get('version')}"
                )

                # Now request tool list
                list_request = {
                    "jsonrpc": "2.0",
                    "method": "tools/list",
                    "params": {},
                    "id": 2,
                }

                print("\nSending tools/list request...")
                proc.stdin.write(json.dumps(list_request) + "\n")
                proc.stdin.flush()

                response = proc.stdout.readline()
                if response:
                    result = json.loads(response)
                    tools = result.get("result", {}).get("tools", [])
                    print(f"\n✓ Found {len(tools)} tools:")
                    for tool in tools:
                        print(f"  - {tool['name']}: {tool['description'][:60]}...")

            except json.JSONDecodeError as e:
                print(f"✗ Failed to parse JSON response: {e}")
                print(f"  Raw response: {response}")
        else:
            print("✗ No response received from server")

    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"✗ Error: {e}")
    finally:
        print("\nTerminating server...")
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        print("Server terminated")


if __name__ == "__main__":
    test_mcp_direct()
