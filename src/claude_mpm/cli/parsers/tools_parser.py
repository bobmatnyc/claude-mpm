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

    # Gmail-specific arguments
    tools_parser.add_argument(
        "--query",
        type=str,
        help="Gmail search query (for gmail-export)",
    )

    tools_parser.add_argument(
        "--max-results",
        "--max_results",
        type=int,
        dest="max_results",
        help="Maximum number of results (for gmail-export)",
    )

    tools_parser.add_argument(
        "--file",
        type=str,
        help="Input/output file path (for gmail-import)",
    )

    tools_parser.add_argument(
        "--label",
        type=str,
        help="Gmail label to apply (for gmail-import)",
    )

    # Calendar-specific arguments
    tools_parser.add_argument(
        "--calendar-id",
        "--calendar_id",
        type=str,
        dest="calendar_id",
        help="Calendar ID (default: primary)",
    )

    tools_parser.add_argument(
        "--time-min",
        "--time_min",
        type=str,
        dest="time_min",
        help="Minimum time for events (ISO 8601 format, for calendar-export)",
    )

    tools_parser.add_argument(
        "--time-max",
        "--time_max",
        type=str,
        dest="time_max",
        help="Maximum time for events (ISO 8601 format, for calendar-export)",
    )
