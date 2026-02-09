"""
Argument parser for claude-mpm tools command.

WHY: Provides consistent CLI interface for service-specific tools.
Supports extensible subparsers for each service.
"""

import argparse


def add_tools_subparser(subparsers: argparse._SubParsersAction) -> None:
    """
    Add tools subparser to the main parser.

    Args:
        subparsers: The subparsers object from argparse
    """
    tools_parser = subparsers.add_parser(
        "tools",
        help="Bulk operations for MCP services",
        description="Execute bulk operations for Google Workspace, Slack, Notion, etc.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available services:
  google    Google Workspace bulk operations (gmail, calendar, drive, docs)
  slack     Slack bulk operations (messages, channels)
  notion    Notion bulk operations (pages, databases) [future]

Examples:
  # Gmail export
  claude-mpm tools google gmail-export --query "from:john@example.com" --max-results 100

  # Calendar bulk create
  claude-mpm tools google calendar-bulk-create --events events.json

  # Slack message export
  claude-mpm tools slack messages-export --channel general --days 30

  # List available actions for a service
  claude-mpm tools google --help

Common options:
  --format json|text    Output format (default: json)
  --output FILE         Write output to file instead of stdout
  --verbose             Show detailed progress
        """,
    )

    # Service name (required)
    tools_parser.add_argument(
        "service",
        nargs="?",
        help="Service name (google, slack, notion)",
    )

    # Action name (required)
    tools_parser.add_argument(
        "action",
        nargs="?",
        help="Action to perform (e.g., gmail-export, calendar-bulk-create)",
    )

    # Common options
    tools_parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)",
    )

    tools_parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Write output to file instead of stdout",
    )

    tools_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed progress",
    )

    # Service-specific arguments will be added dynamically
    # For now, allow arbitrary arguments to pass through
    tools_parser.add_argument(
        "tool_args",
        nargs=argparse.REMAINDER,
        help="Service and action-specific arguments",
    )
