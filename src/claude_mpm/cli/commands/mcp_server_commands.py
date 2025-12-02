"""MCP server command implementations.

This module provides MCP server management commands.
Extracted from mcp.py to reduce complexity and improve maintainability.
"""

import os
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
        implementation that Claude Code can communicate with.
        NOTE: MCP is specifically for Claude Code features.

        DESIGN DECISION: Run the server directly in the same process to ensure
        Claude Code sees the correct command path, not a wrapper script.
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
            print("   Note: MCP is specifically for Claude Code.")
            return 1

        if show_instructions:
            # Show configuration instructions
            print("🚀 MCP Server Setup Instructions for Claude Code")
            print("=" * 50)
            print("\nThe MCP server enables Claude Code to use tools and integrations.")
            print("\nTo configure the MCP server:")
            print("\n1. Run the configuration script:")
            print("   python scripts/configure_mcp_server.py")
            print("\n2. Or manually configure Claude Code:")

            # Find project root for paths
            project_root = Path(__file__).parent.parent.parent.parent.parent

            # Use the direct command, not the wrapper
            import shutil

            claude_mpm_path = shutil.which("claude-mpm")
            if not claude_mpm_path:
                # Fallback to current executable
                claude_mpm_path = sys.executable.replace("python", "claude-mpm")

            print("\n   Add this to your Claude Code configuration:")
            print(
                "   (~/Library/Application Support/Claude/claude_desktop_config.json on macOS)"
            )
            print("\n   {")
            print('     "mcpServers": {')
            print('       "claude-mpm-gateway": {')
            print(f'         "command": "{claude_mpm_path}",')
            print('         "args": ["mcp", "server"],')
            print(f'         "cwd": "{project_root}"')
            print("       }")
            print("     }")
            print("   }")
            print("\n3. Restart Claude Code to load the MCP server")
            print("\nTo test the server directly:")
            print("   claude-mpm mcp server")
            print("\nTo check running MCP processes:")
            print("   python scripts/check_mcp_processes.py")
            print("\nFor more information, see:")
            print("   https://github.com/anthropics/mcp")

            return 0

        # Default behavior: Run the server directly in this process
        if test_mode:
            print("🧪 Starting MCP server in test mode...", file=sys.stderr)
            print(
                "   This will run the server with stdio communication.", file=sys.stderr
            )
            print("   Press Ctrl+C to stop.\n", file=sys.stderr)

        try:
            # Import and run the server directly
            from claude_mpm.services.mcp_gateway.server.stdio_server import (
                SimpleMCPServer,
            )

            # Set environment variable if in test mode
            if test_mode:
                os.environ["MCP_MODE"] = "test"
            else:
                os.environ["MCP_MODE"] = "production"

            # Create and run the server
            self.logger.info("Starting MCP Gateway Server directly...")
            server = SimpleMCPServer(name="claude-mpm-gateway", version="1.0.0")

            # Run the server asynchronously
            await server.run()

            return 0

        except ImportError as e:
            self.logger.error(f"Failed to import MCP server: {e}")
            # Don't print to stdout as it would interfere with JSON-RPC protocol
            # Log to stderr instead
            print(
                f"❌ Error: Could not import MCP server components: {e}",
                file=sys.stderr,
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
