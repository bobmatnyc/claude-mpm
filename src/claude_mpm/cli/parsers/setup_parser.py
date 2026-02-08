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
        description="Set up Slack, Google Workspace, or other service integrations.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available services:
  slack                  Set up Slack MPM integration
  google-workspace-mcp   Set up Google Workspace MCP integration
  oauth                  Set up OAuth authentication for a service

Example:
  claude-mpm setup slack
  claude-mpm setup google-workspace-mcp
  claude-mpm setup oauth google-workspace-mcp
        """,
    )

    # Create subparsers for each service
    service_subparsers = setup_parser.add_subparsers(
        dest="service", help="Service to set up"
    )

    # Slack setup
    service_subparsers.add_parser("slack", help="Set up Slack MPM integration")

    # Google Workspace setup
    service_subparsers.add_parser(
        "google-workspace-mcp", help="Set up Google Workspace MCP integration"
    )

    # OAuth setup (requires service name)
    oauth_parser = service_subparsers.add_parser(
        "oauth",
        help="Set up OAuth authentication for a service",
        description="Set up OAuth authentication for a service like google-workspace-mcp.",
    )
    oauth_parser.add_argument(
        "service_name", help="Service name (e.g., google-workspace-mcp)"
    )
    oauth_parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't auto-open browser for authentication",
    )
    oauth_parser.add_argument(
        "--no-launch",
        action="store_true",
        help="Don't auto-launch claude-mpm after setup",
    )
    oauth_parser.add_argument(
        "--force", action="store_true", help="Force credential re-entry"
    )
