"""
MCP Gateway command implementation for claude-mpm.

WHY: This module provides CLI commands for managing the MCP (Model Context Protocol) Gateway,
allowing users to start, stop, configure, and test MCP server functionality.

DESIGN DECISION: We follow the existing CLI pattern using a main function
that dispatches to specific subcommand handlers, maintaining consistency
with other command modules like agents.py and memory.py.
"""

import json
import sys
from pathlib import Path

from ...constants import MCPCommands
from ...core.logger import get_logger


def manage_mcp(args):
    """
    Manage MCP Gateway server and tools.

    WHY: The MCP Gateway provides Model Context Protocol integration for Claude MPM,
    enabling tool invocation and external service integration. This command provides
    a unified interface for all MCP-related operations.

    DESIGN DECISION: When no subcommand is provided, we show the server status
    as the default action, giving users a quick overview of the MCP system state.

    Args:
        args: Parsed command line arguments with mcp_command attribute
    """
    logger = get_logger("cli.mcp")

    # First check if MCP package is installed for any command
    try:
        import mcp
    except ImportError:
        if args.mcp_command != MCPCommands.INSTALL.value:
            print("\nMCP package is not installed.", file=sys.stderr)
            print("Please install it first:", file=sys.stderr)
            print("  claude-mpm mcp install", file=sys.stderr)
            print("\nOr manually:", file=sys.stderr)
            print("  pip install mcp", file=sys.stderr)
            return 1

    try:
        # Import MCP Gateway services with error handling
        try:
            from ...services.mcp_gateway import (
                MCPConfiguration,
                MCPServiceRegistry,
                ToolRegistry,
            )
            from ...services.mcp_gateway.server.mcp_gateway import MCPGateway
        except ImportError as e:
            # Provide minimal fallbacks for basic commands
            logger.warning(f"Some MCP Gateway services not available: {e}")

            # Allow install command to proceed
            if args.mcp_command == MCPCommands.INSTALL.value:
                MCPConfiguration = None
                MCPServiceRegistry = None
                ToolRegistry = None
                MCPGateway = None
            else:
                print(
                    "\nError: MCP Gateway services not fully available",
                    file=sys.stderr,
                )
                print(f"Details: {e}", file=sys.stderr)
                print("\nTry running:", file=sys.stderr)
                print("  claude-mpm mcp install", file=sys.stderr)
                return 1

        if not args.mcp_command:
            # No subcommand - show status by default
            return _show_status(
                args,
                logger,
                MCPConfiguration,
                MCPServiceRegistry,
                ToolRegistry,
                MCPGateway,
            )

        # Route to specific command handlers
        from .mcp_command_router import MCPCommandRouter

        router = MCPCommandRouter(logger)
        return router.route_command(args)

    except ImportError as e:
        logger.error(f"MCP Gateway services not available: {e}")
        print("Error: MCP Gateway services not available")
        print("This may indicate a missing dependency. Try running:")
        print("  pip install mcp")
        return 1
    except Exception as e:
        logger.error(f"Error managing MCP Gateway: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


# Command handlers moved to separate modules


# All command handler functions moved to separate modules
# - MCPServerCommands: start, stop, status, cleanup
# - MCPToolCommands: tools, register, test
# - MCPInstallCommands: install
# - MCPConfigCommands: config


def _show_status(
    args, logger, MCPConfiguration, MCPServiceRegistry, ToolRegistry, MCPGateway
):
    """
    Show MCP Gateway status when no subcommand is provided.

    WHY: Users often want a quick overview of the MCP system state.
    This provides server status, registered tools, and configuration info.

    DESIGN DECISION: We show a comprehensive status including server state,
    tool count, and configuration path to give users a complete picture.
    """
    print("📊 MCP Gateway Status")
    print("=" * 50)

    # Check if MCP package is installed
    try:
        import mcp

        print("✅ MCP package installed")
    except ImportError:
        print("❌ MCP package not installed")
        print("   Run: claude-mpm mcp install")
        return 1

    # Show configuration status
    print("\n📁 Configuration:")
    config_path = Path.home() / ".claude" / "mcp_config.json"
    if config_path.exists():
        print(f"   Config file: {config_path}")
        try:
            with open(config_path) as f:
                config = json.load(f)
                if "servers" in config:
                    print(f"   Configured servers: {len(config.get('servers', {}))}")
        except Exception as e:
            print(f"   ⚠️  Error reading config: {e}")
    else:
        print(f"   No config file at {config_path}")

    # Show Claude Code configuration
    claude_config = (
        Path.home()
        / "Library"
        / "Application Support"
        / "Claude"
        / "claude_desktop_config.json"
    )
    if claude_config.exists():
        print(f"\n🖥️  Claude Code Config: {claude_config}")
        try:
            with open(claude_config) as f:
                config = json.load(f)
                mcp_servers = config.get("mcpServers", {})
                if "claude-mpm" in mcp_servers:
                    print("   ✅ claude-mpm server configured")
                else:
                    print("   ⚠️  claude-mpm server not configured")
                    print("   Run: claude-mpm mcp start (for instructions)")
        except Exception as e:
            print(f"   ⚠️  Error reading config: {e}")
    else:
        print("\n🖥️  Claude Code not configured for MCP")
        print("   Run: claude-mpm mcp start (for instructions)")

    # Show available tools count
    if ToolRegistry:
        try:
            ToolRegistry()
            # Don't initialize fully, just check
            print("\n🔧 Tools: Check with 'claude-mpm mcp tools'")
        except:
            print("\n🔧 Tools: Registry not available")

    print("\n💡 Available Commands:")
    print("   claude-mpm mcp install    - Install MCP dependencies")
    print("   claude-mpm mcp start      - Start MCP server (stdio mode)")
    print("   claude-mpm mcp start --instructions - Show setup instructions")
    print("   claude-mpm mcp tools      - List available tools")
    print("   claude-mpm mcp test       - Test tool invocation")
    print("   claude-mpm mcp config     - Manage configuration")

    return 0
