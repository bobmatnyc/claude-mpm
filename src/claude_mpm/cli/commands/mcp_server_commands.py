"""MCP server command implementations.

This module provides MCP server management commands.
Extracted from mcp.py to reduce complexity and improve maintainability.
"""

import asyncio
import os
import subprocess
import sys
from pathlib import Path


class MCPServerCommands:
    """Handles MCP server commands."""

    def __init__(self, logger):
        """Initialize the MCP server commands handler."""
        self.logger = logger

    async def start_server(self, args):
        """Start MCP server command.

        WHY: This command starts the MCP server using the proper stdio-based
        implementation that Claude Desktop can communicate with.
        NOTE: MCP is for Claude Desktop's Code features.

        DESIGN DECISION: We now use the wrapper script to ensure proper
        environment setup regardless of how the server is invoked.
        """
        self.logger.info("MCP server start command called")

        # Check if we're being called by Claude Code (no special flags)
        show_instructions = getattr(args, "instructions", False)
        test_mode = getattr(args, "test", False)
        daemon_mode = getattr(args, "daemon", False)

        if daemon_mode:
            # Daemon mode - not recommended for MCP
            print("⚠️  MCP servers are designed to be spawned by Claude Code")
            print("   Running as a daemon is not recommended.")
            print("   Note: MCP is ONLY for Claude Code, not Claude Desktop.")
            return 1

        if show_instructions:
            # Show configuration instructions
            print("🚀 MCP Server Setup Instructions for Claude Desktop")
            print("=" * 50)
            print("\nThe MCP server enables Claude Desktop to use tools and integrations.")
            print("\nTo configure the MCP server:")
            print("\n1. Run the configuration script:")
            print("   python scripts/configure_mcp_server.py")
            print("\n2. Or manually configure Claude Desktop:")
            
            # Find project root for paths
            project_root = Path(__file__).parent.parent.parent.parent.parent
            wrapper_path = project_root / "scripts" / "mcp_wrapper.py"
            
            print("\n   Add this to your Claude Desktop configuration:")
            print("   (~/Library/Application Support/Claude/claude_desktop_config.json on macOS)")
            print("\n   {")
            print('     "mcpServers": {')
            print('       "claude-mpm-gateway": {')
            print(f'         "command": "{sys.executable}",')
            print(f'         "args": ["{wrapper_path}"],')
            print(f'         "cwd": "{project_root}"')
            print('       }')
            print('     }')
            print('   }')
            print("\n3. Restart Claude Desktop to load the MCP server")
            print("\nTo test the server directly:")
            print("   python scripts/mcp_wrapper.py")
            print("\nTo check running MCP processes:")
            print("   python scripts/check_mcp_processes.py")
            print("\nFor more information, see:")
            print("   https://github.com/anthropics/mcp")

            return 0

        # Default behavior: Use the wrapper script for proper environment setup
        if test_mode:
            print("🧪 Starting MCP server in test mode...")
            print("   This will run the server with stdio communication.")
            print("   Press Ctrl+C to stop.\n")

        try:
            # Instead of running directly, we should use the wrapper script
            # for consistent environment setup
            import subprocess
            from pathlib import Path
            
            # Find the wrapper script
            project_root = Path(__file__).parent.parent.parent.parent.parent
            wrapper_script = project_root / "scripts" / "mcp_wrapper.py"
            
            if not wrapper_script.exists():
                print(f"❌ Error: Wrapper script not found at {wrapper_script}", file=sys.stderr)
                print("\nPlease ensure the wrapper script is installed.", file=sys.stderr)
                return 1
            
            # Run the wrapper script
            print(f"Starting MCP server via wrapper: {wrapper_script}", file=sys.stderr)
            
            # Use subprocess to run the wrapper
            # This ensures proper environment setup
            result = subprocess.run(
                [sys.executable, str(wrapper_script)],
                cwd=str(project_root),
                env={**os.environ, "MCP_MODE": "test" if test_mode else "production"}
            )
            
            return result.returncode

        except ImportError as e:
            self.logger.error(f"Failed to import MCP server: {e}")
            # Don't print to stdout as it would interfere with JSON-RPC protocol
            # Log to stderr instead
            import sys

            print(
                f"❌ Error: Could not import MCP server components: {e}", file=sys.stderr
            )
            print("\nMake sure the MCP package is installed:", file=sys.stderr)
            print("  pip install mcp", file=sys.stderr)
            return 1
        except KeyboardInterrupt:
            # Graceful shutdown
            self.logger.info("MCP server interrupted")
            return 0
        except Exception as e:
            self.logger.error(f"Server error: {e}")
            import sys

            print(f"❌ Error running server: {e}", file=sys.stderr)
            return 1

    def stop_server(self, args):
        """Stop MCP server command."""
        self.logger.info("MCP server stop command called")
        print("🛑 MCP server stop functionality has been simplified")
        print("   This command is now a placeholder - full implementation needed")
        return 0

    def show_status(self, args):
        """Show MCP server status command."""
        self.logger.info("MCP server status command called")
        print("📊 MCP server status functionality has been simplified")
        print("   This command is now a placeholder - full implementation needed")
        return 0

    def cleanup_locks(self, args):
        """Cleanup MCP server locks command."""
        self.logger.info("MCP server cleanup locks command called")
        print("🧹 MCP server cleanup locks functionality has been simplified")
        print("   This command is now a placeholder - full implementation needed")
        return 0
