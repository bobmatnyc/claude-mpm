"""
Setup command parser for claude-mpm CLI.

WHY: Unified setup command needs argument parsing for multiple services.

DESIGN DECISIONS:
- Support subcommands for different services (slack, google-workspace-mcp, oauth)
- Follow BaseCommand pattern for consistency
- Keep simple - service name as positional argument
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
        description="Set up Slack, Google Workspace, or other service integrations. Multiple services can be set up in sequence.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available services:
  slack                  Set up Slack MPM integration
  google-workspace-mcp   Set up Google Workspace MCP integration
  oauth                  Set up OAuth authentication for a service

Examples:
  claude-mpm setup slack
  claude-mpm setup google-workspace-mcp
  claude-mpm setup slack google-workspace-mcp  # Multiple services
  claude-mpm setup oauth google-workspace-mcp
        """,
    )

    # Accept multiple services as positional arguments
    setup_parser.add_argument(
        "services",
        nargs="+",
        choices=["slack", "google-workspace-mcp", "oauth"],
        help="One or more services to set up",
        metavar="SERVICE",
    )

    # OAuth-specific options
    setup_parser.add_argument(
        "--oauth-service",
        help="Service name for OAuth setup (e.g., google-workspace-mcp)",
        metavar="NAME",
    )
    setup_parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't auto-open browser for OAuth authentication",
    )
    setup_parser.add_argument(
        "--no-launch",
        action="store_true",
        help="Don't auto-launch claude-mpm after OAuth setup",
    )
    setup_parser.add_argument(
        "--force", action="store_true", help="Force OAuth credential re-entry"
    )
