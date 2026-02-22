"""
Parser for message queue management commands.
"""

from argparse import ArgumentParser
from typing import Any

from .base_parser import add_common_arguments


def add_queue_subparser(subparsers: Any) -> ArgumentParser:
    """
    Add the queue command subparser.

    Args:
        subparsers: The subparsers object from argparse.

    Returns:
        The queue parser object.
    """
    # Queue command with subcommands
    queue_parser = subparsers.add_parser(
        "queue", help="Manage the message queue consumer"
    )
    add_common_arguments(queue_parser)

    queue_subparsers = queue_parser.add_subparsers(
        dest="queue_command", help="Queue commands", metavar="SUBCOMMAND"
    )

    # Start command
    start_parser = queue_subparsers.add_parser(
        "start", help="Start the message queue consumer"
    )
    start_parser.add_argument(
        "--workers",
        "-w",
        type=int,
        default=2,
        help="Number of worker threads (default: 2)",
    )
    start_parser.add_argument(
        "--daemon", "-d", action="store_true", help="Run as daemon in background"
    )

    # Status command
    queue_subparsers.add_parser("status", help="Show message queue status")

    # Cleanup command
    queue_subparsers.add_parser(
        "cleanup", help="Clean up old messages and stale sessions"
    )

    return queue_parser
