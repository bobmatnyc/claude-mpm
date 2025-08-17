"""
Monitor command parser for claude-mpm CLI.

WHY: This module contains all arguments specific to monitoring server management,
extracted from the monolithic parser.py for better organization.

DESIGN DECISION: Monitor commands handle Socket.IO server management and
have their own subcommand structure.
"""

import argparse

from ...constants import CLICommands, MonitorCommands
from .base_parser import add_common_arguments


def add_monitor_subparser(subparsers) -> argparse.ArgumentParser:
    """
    Add the monitor subparser with all monitoring server commands.

    WHY: Monitor management has multiple subcommands for starting, stopping,
    and managing the Socket.IO monitoring server.

    Args:
        subparsers: The subparsers object from the main parser

    Returns:
        The configured monitor subparser
    """
    # Monitor command with subcommands
    monitor_parser = subparsers.add_parser(
        CLICommands.MONITOR.value, help="Manage Socket.IO monitoring server"
    )
    add_common_arguments(monitor_parser)

    monitor_subparsers = monitor_parser.add_subparsers(
        dest="monitor_command", help="Monitor commands", metavar="SUBCOMMAND"
    )

    # Start monitor
    start_monitor_parser = monitor_subparsers.add_parser(
        MonitorCommands.START.value, help="Start Socket.IO monitoring server"
    )
    start_monitor_parser.add_argument(
        "--port", type=int, default=8765, help="Port to start server on (default: 8765)"
    )
    start_monitor_parser.add_argument(
        "--host", default="localhost", help="Host to bind to (default: localhost)"
    )
    start_monitor_parser.add_argument(
        "--dashboard", action="store_true", help="Enable web dashboard interface"
    )
    start_monitor_parser.add_argument(
        "--dashboard-port",
        type=int,
        default=8766,
        help="Dashboard port (default: 8766)",
    )
    start_monitor_parser.add_argument(
        "--background", action="store_true", help="Run server in background"
    )

    # Stop monitor
    stop_monitor_parser = monitor_subparsers.add_parser(
        MonitorCommands.STOP.value, help="Stop Socket.IO monitoring server"
    )
    stop_monitor_parser.add_argument(
        "--port", type=int, default=8765, help="Port of server to stop (default: 8765)"
    )
    stop_monitor_parser.add_argument(
        "--force", action="store_true", help="Force stop even if clients are connected"
    )

    # Restart monitor
    restart_monitor_parser = monitor_subparsers.add_parser(
        MonitorCommands.RESTART.value, help="Restart Socket.IO monitoring server"
    )
    restart_monitor_parser.add_argument(
        "--port", type=int, help="Port to restart on"
    )
    restart_monitor_parser.add_argument(
        "--host", default="localhost", help="Host to bind to (default: localhost)"
    )

    # Status monitor
    status_monitor_parser = monitor_subparsers.add_parser(
        MonitorCommands.STATUS.value, help="Check monitoring server status"
    )
    status_monitor_parser.add_argument(
        "--verbose", action="store_true", help="Show detailed status information"
    )

    # Port monitor (start/restart on specific port)
    port_monitor_parser = monitor_subparsers.add_parser(
        MonitorCommands.PORT.value, help="Start/restart monitoring server on specific port"
    )
    port_monitor_parser.add_argument(
        "port", type=int, help="Port number to use"
    )
    port_monitor_parser.add_argument(
        "--host", default="localhost", help="Host to bind to (default: localhost)"
    )

    return monitor_parser
