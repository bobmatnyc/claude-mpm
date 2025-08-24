from pathlib import Path

"""
MCP command parser for claude-mpm CLI.

WHY: This module contains all arguments specific to MCP Gateway management,
extracted from the monolithic parser.py for better organization.

DESIGN DECISION: MCP commands handle Model Context Protocol Gateway server
and tool management with complex subcommand structures.
"""

import argparse

from ...constants import CLICommands, MCPCommands
from .base_parser import add_common_arguments


def add_mcp_subparser(subparsers) -> argparse.ArgumentParser:
    """
    Add the MCP subparser with all MCP Gateway management commands.

    WHY: MCP management has multiple complex subcommands for server management,
    tool registration, and configuration that need their own structures.

    Args:
        subparsers: The subparsers object from the main parser

    Returns:
        The configured MCP subparser
    """
    # MCP command with subcommands
    mcp_parser = subparsers.add_parser(
        CLICommands.MCP.value, help="Manage MCP Gateway server and tools"
    )
    add_common_arguments(mcp_parser)

    mcp_subparsers = mcp_parser.add_subparsers(
        dest="mcp_command", help="MCP commands", metavar="SUBCOMMAND"
    )

    # Install MCP Gateway
    install_mcp_parser = mcp_subparsers.add_parser(
        MCPCommands.INSTALL.value, help="Install and configure MCP Gateway"
    )
    install_mcp_parser.add_argument(
        "--force", action="store_true", help="Force overwrite existing configuration"
    )

    # Start MCP server
    start_mcp_parser = mcp_subparsers.add_parser(
        MCPCommands.START.value, help="Start the MCP Gateway server"
    )
    start_mcp_parser.add_argument(
        "--mode",
        choices=["stdio", "standalone"],
        default="stdio",
        help="Server mode: stdio for Claude integration, standalone for testing (default: stdio)",
    )
    start_mcp_parser.add_argument(
        "--port",
        type=int,
        default=8766,
        help="Port for standalone mode (default: 8766)",
    )
    start_mcp_parser.add_argument(
        "--config-file", type=Path, help="Path to MCP configuration file"
    )
    start_mcp_parser.add_argument(
        "--test", action="store_true", help="Run in test mode with debug output"
    )
    start_mcp_parser.add_argument(
        "--instructions",
        action="store_true",
        help="Show setup instructions instead of running server",
    )
    start_mcp_parser.add_argument(
        "--daemon", action="store_true", help="Run as daemon (not recommended for MCP)"
    )

    # Stop MCP server
    mcp_subparsers.add_parser(
        MCPCommands.STOP.value, help="Stop the MCP Gateway server"
    )

    # MCP status
    status_mcp_parser = mcp_subparsers.add_parser(
        MCPCommands.STATUS.value, help="Check server and tool status"
    )
    status_mcp_parser.add_argument(
        "--verbose", action="store_true", help="Show detailed status information"
    )

    # List/manage tools
    tools_mcp_parser = mcp_subparsers.add_parser(
        MCPCommands.TOOLS.value, help="List and manage registered tools"
    )
    tools_mcp_parser.add_argument(
        "tool_action",
        nargs="?",
        choices=["list", "enable", "disable"],
        default="list",
        help="Tool action (default: list)",
    )
    tools_mcp_parser.add_argument(
        "tool_name", nargs="?", help="Tool name for enable/disable actions"
    )
    tools_mcp_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed tool information including schemas",
    )

    # Register new tool
    register_mcp_parser = mcp_subparsers.add_parser(
        MCPCommands.REGISTER.value, help="Register a new MCP tool"
    )
    register_mcp_parser.add_argument("name", help="Tool name")
    register_mcp_parser.add_argument("description", help="Tool description")
    register_mcp_parser.add_argument(
        "--schema-file", type=Path, help="Path to JSON schema file for tool input"
    )
    register_mcp_parser.add_argument(
        "--adapter", help="Path to custom tool adapter module"
    )
    register_mcp_parser.add_argument(
        "--save", action="store_true", help="Save tool to configuration"
    )

    # Test tool invocation
    test_mcp_parser = mcp_subparsers.add_parser(
        MCPCommands.TEST.value, help="Test MCP tool invocation"
    )
    test_mcp_parser.add_argument("tool_name", help="Name of tool to test")
    test_mcp_parser.add_argument("--args", help="Tool arguments as JSON string")
    test_mcp_parser.add_argument(
        "--args-file", type=Path, help="Path to JSON file containing tool arguments"
    )

    # Manage configuration
    config_mcp_parser = mcp_subparsers.add_parser(
        MCPCommands.CONFIG.value, help="View and manage MCP configuration"
    )
    config_mcp_parser.add_argument(
        "config_action",
        nargs="?",
        choices=["view", "edit", "reset"],
        default="view",
        help="Configuration action (default: view)",
    )

    # MCP Server command (direct server execution)
    server_mcp_parser = mcp_subparsers.add_parser(
        MCPCommands.SERVER.value, help="Run the MCP Gateway server directly"
    )
    server_mcp_parser.add_argument(
        "--mode",
        choices=["stdio", "standalone"],
        default="stdio",
        help="Server mode: stdio for Claude integration, standalone for testing (default: stdio)",
    )
    server_mcp_parser.add_argument(
        "--port",
        type=int,
        default=8766,
        help="Port for standalone mode (default: 8766)",
    )
    server_mcp_parser.add_argument(
        "--config-file", type=Path, help="Path to MCP configuration file"
    )
    server_mcp_parser.add_argument(
        "--test", action="store_true", help="Run in test mode with debug output"
    )
    server_mcp_parser.add_argument(
        "--instructions",
        action="store_true",
        help="Show setup instructions for Claude Code",
    )

    return mcp_parser
