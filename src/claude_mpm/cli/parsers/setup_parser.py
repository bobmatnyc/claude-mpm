"""
Setup command parser for claude-mpm CLI.

WHY: Unified setup command needs argument parsing for multiple services with service-specific options.

DESIGN DECISIONS:
- Services as positional arguments (slack, gworkspace-mcp, oauth)
- Flags after a service name apply to that service
- Follows Unix convention: "command arg1 --flag1 arg2 --flag2"
"""

import argparse


def add_setup_subparser(subparsers: argparse._SubParsersAction) -> None:
    """
    Add setup subparser to the main parser.

    Args:
        subparsers: The subparsers object from argparse
    """
    setup_parser = subparsers.add_parser(
        "setup",
        help="Set up various services and integrations",
        description="Set up one or more services. Flags after a service name apply to that service.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available services:
  slack                  Set up Slack MPM integration
  gworkspace-mcp         Set up Google Workspace MCP (automatically sets up OAuth)
  oauth                  Set up OAuth authentication (requires --oauth-service)
  kuzu-memory            Set up kuzu-memory integration
  mcp-vector-search      Set up mcp-vector-search semantic code search
  mcp-skillset           Set up mcp-skillset RAG-powered skills (USER-LEVEL, not project-specific)

Service options:
  --oauth-service NAME   Service name for OAuth setup (required for oauth)
  --no-browser           Don't auto-open browser for authentication (oauth only)
  --no-launch            Don't auto-launch claude-mpm after setup (all services)
  --force                Force credential re-entry (oauth only) or reinstall (mcp-vector-search, mcp-skillset)

Examples:
  # Single service
  claude-mpm setup slack

  # Slack without auto-launch
  claude-mpm setup slack --no-launch

  # Multiple services
  claude-mpm setup slack gworkspace-mcp

  # Service with options (flags after service apply to it)
  claude-mpm setup oauth --oauth-service gworkspace-mcp --no-browser

  # Multiple services with mixed options
  claude-mpm setup slack oauth --oauth-service gworkspace-mcp --no-launch

  # Set up mcp-vector-search
  claude-mpm setup mcp-vector-search

  # Force reinstall mcp-vector-search
  claude-mpm setup mcp-vector-search --force

  # Set up mcp-skillset (user-level, available across all projects)
  claude-mpm setup mcp-skillset

  # Force reinstall mcp-skillset
  claude-mpm setup mcp-skillset --force

Note: Flags are associated with the service that precedes them.
      mcp-skillset is installed at user-level (Claude Desktop config) and available to all projects.
        """,
    )

    # Global flags that can appear anywhere in the command
    setup_parser.add_argument(
        "--no-launch",
        action="store_true",
        default=False,
        help="Don't auto-launch claude-mpm after setup",
    )
    setup_parser.add_argument(
        "--no-browser",
        action="store_true",
        default=False,
        help="Don't auto-open browser for authentication",
    )
    setup_parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Force reinstall or credential re-entry",
    )
    setup_parser.add_argument(
        "--oauth-service",
        type=str,
        help="Service name for OAuth setup",
    )

    # Services as positional remainder arguments
    # We'll parse this manually to associate flags with services
    setup_parser.add_argument(
        "service_args",
        nargs="*",
        help="Services and their options (e.g., slack oauth --oauth-service gworkspace-mcp)",
    )
