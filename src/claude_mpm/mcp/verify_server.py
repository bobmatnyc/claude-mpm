#!/usr/bin/env python3
"""Verify MCP server can start and respond to basic requests."""

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path


async def verify_server() -> bool:
    """Verify the MCP server starts and responds correctly."""

    # Locate server script relative to this module
    # This file is at src/claude_mpm/mcp/verify_server.py
    # Project root is four levels up
    module_dir = Path(__file__).resolve().parent
    project_root = module_dir.parent.parent.parent.parent
    # Resolve back via pyproject.toml search if needed
    for candidate in [project_root, *project_root.parents]:
        if (candidate / "pyproject.toml").exists():
            project_root = candidate
            break

    server_script = project_root / "src" / "claude_mpm" / "scripts" / "mcp_server.py"
    server_path = str(server_script)

    # Check if script exists and is executable
    if not server_script.exists():
        print(f"✗ Server script not found: {server_path}", file=sys.stderr)
        return False

    if not os.access(server_path, os.X_OK):
        print("⚠ Server script not executable, fixing...", file=sys.stderr)
        os.chmod(server_path, 0o755)  # nosec B103

    # Start the server
    process = None
    try:
        process = await asyncio.create_subprocess_exec(
            "python3",
            server_path,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
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
                "clientInfo": {"name": "claude-desktop", "version": "unknown"},
            },
            "id": 1,
        }

        if process.stdin is not None:
            process.stdin.write((json.dumps(request) + "\n").encode())
            await process.stdin.drain()

        # Read response with timeout
        try:
            if process.stdout is None:
                print("✗ Server stdout not available", file=sys.stderr)
                return False

            response_line = await asyncio.wait_for(
                process.stdout.readline(), timeout=5.0
            )
            response = json.loads(response_line.decode())

            if "result" in response and "serverInfo" in response["result"]:
                server_info = response["result"]["serverInfo"]
                print(
                    f"✓ Server initialized: {server_info['name']} v{server_info['version']}",
                    file=sys.stderr,
                )

                # Check for backward compatibility patch
                if process.stderr is not None:
                    stderr_data = await asyncio.wait_for(
                        process.stderr.read(500), timeout=0.5
                    )
                    if b"Applied MCP Server message handling patch" in stderr_data:
                        print("✓ Backward compatibility patch applied", file=sys.stderr)

                return True
            print("✗ Invalid initialize response", file=sys.stderr)
            return False

        except TimeoutError:
            print("✗ Server did not respond within 5 seconds", file=sys.stderr)

            # Check stderr for errors
            if process.stderr is not None:
                stderr = await process.stderr.read()
                if stderr:
                    print("\nServer errors:", file=sys.stderr)
                    print(stderr.decode()[:500], file=sys.stderr)
            return False

    finally:
        # Clean shutdown
        if process is not None:
            process.terminate()
            await process.wait()


async def main() -> int:
    """Main verification routine."""
    print("MCP Server Verification", file=sys.stderr)
    print("=" * 40, file=sys.stderr)

    success = await verify_server()

    if success:
        print("\n✅ MCP server is ready for use", file=sys.stderr)
        print("\nClaude Code configuration is correct:", file=sys.stderr)
        print("  Command: python3", file=sys.stderr)
        module_dir = Path(__file__).resolve().parent
        project_root = module_dir.parent.parent.parent.parent
        for candidate in [project_root, *project_root.parents]:
            if (candidate / "pyproject.toml").exists():
                project_root = candidate
                break
        print(
            f"  Args: {project_root / 'src' / 'claude_mpm' / 'scripts' / 'mcp_server.py'}",
            file=sys.stderr,
        )
        return 0
    print("\n❌ MCP server verification failed", file=sys.stderr)
    return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
