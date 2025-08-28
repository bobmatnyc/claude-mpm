"""
Dashboard command parser for claude-mpm CLI.

WHY: This module contains all arguments specific to dashboard management,
providing a clean interface for starting, stopping, and managing the web dashboard.

DESIGN DECISION: Dashboard commands handle web interface management and
have their own subcommand structure similar to monitor commands.
"""

import argparse

from ...constants import CLICommands, DashboardCommands
from .base_parser import add_common_arguments


def add_dashboard_subparser(subparsers) -> argparse.ArgumentParser:
    """
    Add the dashboard subparser with all dashboard management commands.

    WHY: Dashboard management has multiple subcommands for starting, stopping,
    checking status, and opening the web interface in a browser.

    Args:
        subparsers: The subparsers object from the main parser

    Returns:
        The configured dashboard subparser
    """
    # Dashboard command with subcommands
    dashboard_parser = subparsers.add_parser(
        CLICommands.DASHBOARD.value,
        help="Manage the web dashboard interface for monitoring and analysis",
    )
    add_common_arguments(dashboard_parser)

    dashboard_subparsers = dashboard_parser.add_subparsers(
        dest="dashboard_command", help="Dashboard commands", metavar="SUBCOMMAND"
    )

    # Start dashboard
    start_dashboard_parser = dashboard_subparsers.add_parser(
        DashboardCommands.START.value,
        help="Start the web dashboard server",
    )
    start_dashboard_parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port to start dashboard on (default: 8765)",
    )
    start_dashboard_parser.add_argument(
        "--host",
        default="localhost",
        help="Host to bind to (default: localhost)",
    )
    start_dashboard_parser.add_argument(
        "--background",
        action="store_true",
        help="Run dashboard server in background",
    )
    start_dashboard_parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't open browser automatically",
    )

    # Stop dashboard
    stop_dashboard_parser = dashboard_subparsers.add_parser(
        DashboardCommands.STOP.value,
        help="Stop the web dashboard server",
    )
    stop_dashboard_parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port of dashboard to stop (default: 8765)",
    )
    stop_dashboard_parser.add_argument(
        "--all",
        action="store_true",
        help="Stop all running dashboard instances",
    )

    # Status dashboard
    status_dashboard_parser = dashboard_subparsers.add_parser(
        DashboardCommands.STATUS.value,
        help="Check dashboard server status",
    )
    status_dashboard_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed status information",
    )
    status_dashboard_parser.add_argument(
        "--show-ports",
        action="store_true",
        help="Show status of all ports in the range (8765-8785)",
    )

    # Open dashboard
    open_dashboard_parser = dashboard_subparsers.add_parser(
        DashboardCommands.OPEN.value,
        help="Open the dashboard in a web browser (starts if not running)",
    )
    open_dashboard_parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port of dashboard to open (default: 8765)",
    )

    return dashboard_parser
