"""MCP command router for CLI commands.

This module routes MCP commands to their appropriate handlers.
Extracted from mcp.py to reduce complexity and improve maintainability.
"""

import asyncio

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

        if args.mcp_command == MCPCommands.STOP.value:
            return self._stop_server(args)

        if args.mcp_command == MCPCommands.STATUS.value:
            return self._show_status(args)

        if args.mcp_command == MCPCommands.TOOLS.value:
            return self._manage_tools(args)

        if args.mcp_command == MCPCommands.REGISTER.value:
            return self._register_tool(args)

        if args.mcp_command == MCPCommands.TEST.value:
            return self._test_tool(args)

        if args.mcp_command == MCPCommands.INSTALL.value:
            return self._install_gateway(args)

        if args.mcp_command == MCPCommands.CONFIG.value:
            return self._manage_config(args)

        if args.mcp_command == MCPCommands.SERVER.value:
            return self._run_server(args)

        if args.mcp_command == "cleanup":
            return self._cleanup_locks(args)

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
        # Simply delegate to the async start_server method using asyncio.run
        from .mcp_server_commands import MCPServerCommands

        handler = MCPServerCommands(self.logger)
        return asyncio.run(handler.start_server(args))

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
