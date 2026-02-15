"""
OAuth command parser for claude-mpm CLI.

WHY: This module provides the oauth command with subcommands for
managing OAuth authentication for MCP services that require OAuth2 flows.

DESIGN DECISION: 'oauth' provides comprehensive OAuth management including
listing OAuth-capable services, setup, status, token revocation, and refresh.
"""

import argparse

from .base_parser import add_common_arguments


def add_oauth_subparser(subparsers) -> argparse.ArgumentParser:
    """
    Add the oauth subparser with all OAuth management subcommands.

    WHY: 'oauth' provides comprehensive OAuth management for MCP services
    that require OAuth2 authentication flows.

    Args:
        subparsers: The subparsers object from the main parser

    Returns:
        The configured oauth subparser
    """
    # OAuth command with subcommands
    oauth_parser = subparsers.add_parser(
        "oauth",
        help="Manage OAuth authentication for MCP services",
        description="""
Manage OAuth authentication for MCP services.

Available commands:
  list              List OAuth-capable MCP services
  setup <service>   Set up OAuth authentication for a service
  status <service>  Show OAuth token status for a service
  revoke <service>  Revoke OAuth tokens for a service
  refresh <service> Refresh OAuth tokens for a service

Examples:
  claude-mpm oauth list
  claude-mpm oauth setup gworkspace-mcp
  claude-mpm oauth status gworkspace-mcp
  claude-mpm oauth revoke gworkspace-mcp
  claude-mpm oauth refresh gworkspace-mcp
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_common_arguments(oauth_parser)

    # Add subcommands
    oauth_subparsers = oauth_parser.add_subparsers(
        dest="oauth_command", help="OAuth commands", metavar="SUBCOMMAND"
    )

    # List subcommand
    list_parser = oauth_subparsers.add_parser(
        "list",
        help="List OAuth-capable MCP services",
        description="List all MCP services that support OAuth authentication.",
    )
    add_common_arguments(list_parser)
    list_parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="Output format (default: table)",
    )

    # Setup subcommand
    setup_parser = oauth_subparsers.add_parser(
        "setup",
        help="Set up OAuth authentication for a service",
        description="""
Set up OAuth authentication for an MCP service.

This command initiates the OAuth2 flow by:
1. Looking for credentials in .env.local, .env, or environment variables
2. Prompting for credentials if not found
3. Opening a browser for user authentication
4. Starting a local callback server to receive the OAuth redirect
5. Storing the tokens securely for future use

Required environment variables (checked in order):
  1. .env.local file (highest priority)
  2. .env file
  3. Environment variables

For Google OAuth services:
  GOOGLE_OAUTH_CLIENT_ID     - Your OAuth client ID
  GOOGLE_OAUTH_CLIENT_SECRET - Your OAuth client secret

Get credentials from: https://console.cloud.google.com/apis/credentials
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_common_arguments(setup_parser)
    setup_parser.add_argument(
        "service_name",
        help="Name of the MCP service to authenticate (e.g., gworkspace-mcp)",
    )
    setup_parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force credential prompt even if found in environment or .env files",
    )
    setup_parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't open browser automatically, just print the URL",
    )
    setup_parser.add_argument(
        "--port",
        type=int,
        default=8789,
        help="Port for the OAuth callback server (default: 8789). This must match the redirect URI configured in your OAuth provider (e.g., http://127.0.0.1:8789/callback for Google Cloud Console).",
    )
    setup_parser.add_argument(
        "--no-launch",
        action="store_true",
        help="Don't launch claude-mpm after successful OAuth setup",
    )

    # Status subcommand
    status_parser = oauth_subparsers.add_parser(
        "status",
        help="Show OAuth token status for a service",
        description="Display the current OAuth token status including validity and expiration.",
    )
    add_common_arguments(status_parser)
    status_parser.add_argument(
        "service_name",
        help="Name of the MCP service to check",
    )
    status_parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="Output format (default: table)",
    )

    # Revoke subcommand
    revoke_parser = oauth_subparsers.add_parser(
        "revoke",
        help="Revoke OAuth tokens for a service",
        description="Revoke and delete stored OAuth tokens for a service.",
    )
    add_common_arguments(revoke_parser)
    revoke_parser.add_argument(
        "service_name",
        help="Name of the MCP service to revoke tokens for",
    )
    revoke_parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Skip confirmation prompt",
    )

    # Refresh subcommand
    refresh_parser = oauth_subparsers.add_parser(
        "refresh",
        help="Refresh OAuth tokens for a service",
        description="Refresh the OAuth tokens using the stored refresh token.",
    )
    add_common_arguments(refresh_parser)
    refresh_parser.add_argument(
        "service_name",
        help="Name of the MCP service to refresh tokens for",
    )

    return oauth_parser
