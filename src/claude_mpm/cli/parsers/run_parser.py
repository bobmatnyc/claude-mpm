"""
Run command parser for claude-mpm CLI.

WHY: This module contains all arguments specific to the run command,
extracted from the monolithic parser.py for better organization.

DESIGN DECISION: Run command arguments are complex enough to warrant
their own module, including hook management, ticket creation, and
interaction modes.
"""

import argparse

from ...constants import CLICommands
from .base_parser import add_common_arguments


def add_run_arguments(parser: argparse.ArgumentParser) -> None:
    """
    Add arguments specific to the run command.

    WHY: The run command has specific arguments for controlling how Claude sessions
    are executed, including hook management, ticket creation, and interaction modes.

    Args:
        parser: The argument parser to add arguments to
    """
    run_group = parser.add_argument_group("run options")

    run_group.add_argument(
        "--no-hooks",
        action="store_true",
        help="Disable hook service (runs without hooks)",
    )
    run_group.add_argument(
        "--no-tickets", action="store_true", help="Disable automatic ticket creation"
    )
    run_group.add_argument(
        "--intercept-commands",
        action="store_true",
        help="Enable command interception in interactive mode (intercepts /mpm: commands)",
    )
    run_group.add_argument(
        "--no-native-agents",
        action="store_true",
        help="Disable deployment of Claude Code native agents",
    )
    run_group.add_argument(
        "--launch-method",
        choices=["exec", "subprocess"],
        default="exec",
        help="Method to launch Claude: exec (replace process) or subprocess (child process)",
    )
    # Monitor options - consolidated monitoring and management interface
    run_group.add_argument(
        "--monitor",
        action="store_true",
        help="Enable monitoring and management interface with WebSocket server and dashboard (default port: 8765)",
    )
    run_group.add_argument(
        "--websocket-port",
        type=int,
        default=8765,
        help="WebSocket server port (default: 8765)",
    )
    run_group.add_argument(
        "--force",
        action="store_true",
        help="Force operations even with warnings (e.g., large .claude.json file)",
    )
    run_group.add_argument(
        "--mpm-resume",
        type=str,
        nargs="?",
        const="last",
        help="Resume an MPM session (last session if no ID specified, or specific session ID)",
    )
    run_group.add_argument(
        "--resume",
        action="store_true",
        help="Pass --resume flag to Claude Code to resume the last conversation",
    )

    # Dependency checking options
    dep_group = parser.add_argument_group("dependency options")
    dep_group.add_argument(
        "--no-check-dependencies",
        action="store_false",
        dest="check_dependencies",
        help="Skip agent dependency checking at startup",
    )
    dep_group.add_argument(
        "--force-check-dependencies",
        action="store_true",
        help="Force dependency checking even if cached results exist",
    )
    dep_group.add_argument(
        "--no-prompt",
        action="store_true",
        help="Never prompt for dependency installation (non-interactive mode)",
    )
    dep_group.add_argument(
        "--force-prompt",
        action="store_true",
        help="Force interactive prompting even in non-TTY environments (use with caution)",
    )

    # Input/output options
    io_group = parser.add_argument_group("input/output options")
    io_group.add_argument(
        "-i",
        "--input",
        type=str,
        help="Input text or file path (for non-interactive mode)",
    )
    io_group.add_argument(
        "--non-interactive",
        action="store_true",
        help="Run in non-interactive mode (read from stdin or --input)",
    )

    # Claude CLI arguments
    parser.add_argument(
        "claude_args",
        nargs=argparse.REMAINDER,
        help="Additional arguments to pass to Claude CLI (use -- before Claude args)",
    )


def add_run_subparser(subparsers) -> argparse.ArgumentParser:
    """
    Add the run subparser to the main parser.

    WHY: This creates the explicit 'run' command subparser with all
    run-specific arguments.

    Args:
        subparsers: The subparsers object from the main parser

    Returns:
        The configured run subparser
    """
    # Run command (explicit)
    run_parser = subparsers.add_parser(
        CLICommands.RUN.value,
        help="Run orchestrated Claude session (default)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_common_arguments(run_parser)
    add_run_arguments(run_parser)

    return run_parser
