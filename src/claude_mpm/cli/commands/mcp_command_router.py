"""MCP command router for CLI commands.

This module routes MCP commands to their appropriate handlers.
Extracted from mcp.py to reduce complexity and improve maintainability.
"""

import asyncio
import os
import sys
from typing import Any

from ...constants import MCPCommands


class MCPCommandRouter:
    """Routes MCP commands to appropriate handlers."""

    def __init__(self, logger):
        """Initialize the command router."""
        self.logger = logger

    def route_command(self, args) -> int:
        """Route command to appropriate handler."""
        if args.mcp_command == MCPCommands.START.value:
            return asyncio.run(self._start_server(args))

        elif args.mcp_command == MCPCommands.STOP.value:
            return self._stop_server(args)

        elif args.mcp_command == MCPCommands.STATUS.value:
            return self._show_status(args)

        elif args.mcp_command == MCPCommands.TOOLS.value:
            return self._manage_tools(args)

        elif args.mcp_command == MCPCommands.REGISTER.value:
            return self._register_tool(args)

        elif args.mcp_command == MCPCommands.TEST.value:
            return self._test_tool(args)

        elif args.mcp_command == MCPCommands.INSTALL.value:
            return self._install_gateway(args)

        elif args.mcp_command == MCPCommands.CONFIG.value:
            return self._manage_config(args)

        elif args.mcp_command == MCPCommands.SERVER.value:
            return self._run_server(args)

        elif args.mcp_command == "cleanup":
            return self._cleanup_locks(args)

        else:
            self.logger.error(f"Unknown MCP command: {args.mcp_command}")
            print(f"Unknown MCP command: {args.mcp_command}")
            self._show_help()
            return 1

    async def _start_server(self, args) -> int:
        """Start server command handler."""
        from .mcp_server_commands import MCPServerCommands

        handler = MCPServerCommands(self.logger)
        return await handler.start_server(args)

    def _stop_server(self, args) -> int:
        """Stop server command handler."""
        from .mcp_server_commands import MCPServerCommands

        handler = MCPServerCommands(self.logger)
        return handler.stop_server(args)

    def _show_status(self, args) -> int:
        """Show status command handler."""
        from .mcp_server_commands import MCPServerCommands

        handler = MCPServerCommands(self.logger)
        return handler.show_status(args)

    def _manage_tools(self, args) -> int:
        """Manage tools command handler."""
        from .mcp_tool_commands import MCPToolCommands

        handler = MCPToolCommands(self.logger)
        return handler.manage_tools(args)

    def _register_tool(self, args) -> int:
        """Register tool command handler."""
        from .mcp_tool_commands import MCPToolCommands

        handler = MCPToolCommands(self.logger)
        return handler.register_tool(args)

    def _test_tool(self, args) -> int:
        """Test tool command handler."""
        from .mcp_tool_commands import MCPToolCommands

        handler = MCPToolCommands(self.logger)
        return handler.test_tool(args)

    def _install_gateway(self, args) -> int:
        """Install gateway command handler."""
        from .mcp_install_commands import MCPInstallCommands

        handler = MCPInstallCommands(self.logger)
        return handler.install_gateway(args)

    def _manage_config(self, args) -> int:
        """Manage config command handler."""
        from .mcp_config_commands import MCPConfigCommands

        handler = MCPConfigCommands(self.logger)
        return handler.manage_config(args)

    def _cleanup_locks(self, args) -> int:
        """Cleanup locks command handler."""
        from .mcp_server_commands import MCPServerCommands

        handler = MCPServerCommands(self.logger)
        return handler.cleanup_locks(args)

    def _run_server(self, args) -> int:
        """Run server command handler - direct server execution."""
        try:
            self.logger.info("Starting MCP server directly via CLI command")

            # Import the server components
            from claude_mpm.services.mcp_gateway.server.stdio_server import SimpleMCPServer

            # Create server instance
            server = SimpleMCPServer(name="claude-mpm-gateway", version="1.0.0")

            if args.test:
                self.logger.info("Running in test mode")
                print("🧪 Starting MCP server in test mode...", file=sys.stderr)
                print("   This will run the server with stdio communication.", file=sys.stderr)
                print("   Press Ctrl+C to stop.\n", file=sys.stderr)

            # Run the server, handling event loop properly
            try:
                # Check if there's already an event loop running
                loop = asyncio.get_running_loop()
                # If we get here, there's already a loop running
                # We need to run in a subprocess to avoid conflicts
                import subprocess
                import json

                # Create a simple script to run the server
                script_content = f'''
import asyncio
import sys
import os
sys.path.insert(0, "{os.path.join(os.path.dirname(__file__), '..', '..', '..')}")

async def main():
    from claude_mpm.services.mcp_gateway.server.stdio_server import SimpleMCPServer
    server = SimpleMCPServer(name="claude-mpm-gateway", version="1.0.0")
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())
'''

                # Write the script to a temporary file
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                    f.write(script_content)
                    temp_script = f.name

                try:
                    # Run the server in a subprocess
                    result = subprocess.run([sys.executable, temp_script])
                    return result.returncode
                finally:
                    # Clean up the temporary file
                    os.unlink(temp_script)

            except RuntimeError:
                # No event loop running, we can use asyncio.run
                async def run_async():
                    await server.run()

                asyncio.run(run_async())
            return 0

        except ImportError as e:
            self.logger.error(f"Failed to import MCP server: {e}")
            print(f"❌ Error: Could not import MCP server components: {e}", file=sys.stderr)
            print("\nMake sure the MCP package is installed:", file=sys.stderr)
            print("  pip install mcp", file=sys.stderr)
            return 1
        except KeyboardInterrupt:
            self.logger.info("MCP server interrupted")
            print("\n🛑 MCP server stopped", file=sys.stderr)
            return 0
        except Exception as e:
            self.logger.error(f"Server error: {e}")
            print(f"❌ Error running server: {e}", file=sys.stderr)
            return 1

    def _show_help(self):
        """Show available MCP commands."""
        print("\nAvailable MCP commands:")
        print("  install  - Install and configure MCP Gateway")
        print("  start    - Start the MCP Gateway server (stdio mode)")
        print("  server   - Run the MCP Gateway server directly")
        print("  stop     - Stop the MCP Gateway server")
        print("  status   - Show server and tool status")
        print("  tools    - List and manage registered tools")
        print("  register - Register a new tool")
        print("  test     - Test tool invocation")
        print("  config   - View and manage configuration")
        print("  cleanup  - Clean up legacy files")
        print("\nFor help with a specific command:")
        print("  claude-mpm mcp <command> --help")
        print("\nExamples:")
        print("  claude-mpm mcp install")
        print("  claude-mpm mcp start                  # Run server (for Claude Code)")
        print("  claude-mpm mcp server                 # Run server directly")
        print("  claude-mpm mcp server --test          # Test mode with debug output")
        print("  claude-mpm mcp start --instructions    # Show setup instructions")
        print("  claude-mpm mcp tools")
        print("  claude-mpm mcp register my-tool")
        print("  claude-mpm mcp test my-tool")
