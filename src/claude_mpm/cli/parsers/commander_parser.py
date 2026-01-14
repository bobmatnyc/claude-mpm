"""Commander daemon command parser."""

from argparse import _SubParsersAction
from pathlib import Path


def add_commander_subparser(subparsers: _SubParsersAction) -> None:
    """Add commander subcommands to argument parser.

    Args:
        subparsers: Subparser action from ArgumentParser
    """
    # Commander parent command
    commander_parser = subparsers.add_parser(
        "commander",
        help="Manage Commander daemon for multi-project orchestration",
    )

    commander_subparsers = commander_parser.add_subparsers(
        dest="commander_action",
        help="Commander action",
    )

    # commander start
    start_parser = commander_subparsers.add_parser(
        "start",
        help="Start Commander daemon",
    )
    start_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="API server bind address (default: 127.0.0.1)",
    )
    start_parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="API server port (default: 8765)",
    )
    start_parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)",
    )
    start_parser.add_argument(
        "--state-dir",
        type=Path,
        help="State persistence directory (default: ~/.claude-mpm/commander)",
    )

    # commander stop
    commander_subparsers.add_parser(
        "stop",
        help="Stop Commander daemon",
    )

    # commander status
    status_parser = commander_subparsers.add_parser(
        "status",
        help="Check Commander daemon status",
    )
    status_parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="API server port (default: 8765)",
    )
