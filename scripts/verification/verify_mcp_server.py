#!/usr/bin/env python3
"""Verify MCP server can start and respond to basic requests."""

import json
import subprocess
import sys
import asyncio
import os

async def verify_server():
    """Verify the MCP server starts and responds correctly."""
    
    # MCP server script is now in src/claude_mpm/scripts/
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    server_path = os.path.join(project_root, 'src', 'claude_mpm', 'scripts', 'mcp_server.py')
    
    # Check if script exists and is executable
    if not os.path.exists(server_path):
        print(f"✗ Server script not found: {server_path}", file=sys.stderr)
        return False
    
    if not os.access(server_path, os.X_OK):
        print(f"⚠ Server script not executable, fixing...", file=sys.stderr)
        os.chmod(server_path, 0o755)
    
    # Start the server
    try:
        process = await asyncio.create_subprocess_exec(
            'python3', server_path,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
    except Exception as e:
        print(f"✗ Failed to start server: {e}", file=sys.stderr)
        return False
    
    print("✓ Server process started", file=sys.stderr)
    
    try:
        # Send initialize request
        request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "claude-desktop",
                    "version": "unknown"
                }
            },
            "id": 1
        }
        
        process.stdin.write((json.dumps(request) + '\n').encode())
        await process.stdin.drain()
        
        # Read response with timeout
        try:
            response_line = await asyncio.wait_for(
                process.stdout.readline(), 
                timeout=5.0
            )
            response = json.loads(response_line.decode())
            
            if 'result' in response and 'serverInfo' in response['result']:
                server_info = response['result']['serverInfo']
                print(f"✓ Server initialized: {server_info['name']} v{server_info['version']}", file=sys.stderr)
                
                # Check for backward compatibility patch
                stderr_data = await asyncio.wait_for(
                    process.stderr.read(500),
                    timeout=0.5
                )
                if b'Applied MCP Server message handling patch' in stderr_data:
                    print("✓ Backward compatibility patch applied", file=sys.stderr)
                
                return True
            else:
                print("✗ Invalid initialize response", file=sys.stderr)
                return False
                
        except asyncio.TimeoutError:
            print("✗ Server did not respond within 5 seconds", file=sys.stderr)
            
            # Check stderr for errors
            stderr = await process.stderr.read()
            if stderr:
                print("\nServer errors:", file=sys.stderr)
                print(stderr.decode()[:500], file=sys.stderr)
            return False
            
    finally:
        # Clean shutdown
        process.terminate()
        await process.wait()

async def main():
    """Main verification routine."""
    print("MCP Server Verification", file=sys.stderr)
    print("=" * 40, file=sys.stderr)
    
    success = await verify_server()
    
    if success:
        print("\n✅ MCP server is ready for use", file=sys.stderr)
        print("\nClaude Code configuration is correct:", file=sys.stderr)
        print("  Command: python3", file=sys.stderr)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        print(f"  Args: {os.path.join(project_root, 'src', 'claude_mpm', 'scripts', 'mcp_server.py')}", file=sys.stderr)
        return 0
    else:
        print("\n❌ MCP server verification failed", file=sys.stderr)
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)