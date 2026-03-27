"""
Serve command parser for claude-mpm CLI.

WHY: This module contains all arguments specific to the global session runner
daemon, wiring the existing ui_service FastAPI app as a proper CLI-managed
daemon with start/stop/restart/status lifecycle.

DESIGN DECISION: The serve daemon is global (not CWD-relative), so PID and
log files live in ~/.claude-mpm/ to allow management from any directory.
"""

import argparse


def add_serve_subparser(subparsers) -> argparse.ArgumentParser:
    """Add the serve subparser with all daemon lifecycle commands.

    WHY: The serve command manages the global session-runner daemon that
    exposes the FastAPI ui_service over HTTP/WebSocket.  It mirrors the
    monitor subcommand structure so operators have a consistent mental model.

    Args:
        subparsers: The subparsers object from the main parser

    Returns:
        The configured serve subparser
    """
    serve_parser = subparsers.add_parser(
        "serve",
        help="Manage the global Claude session runner daemon",
    )

    serve_subparsers = serve_parser.add_subparsers(
        dest="serve_command", help="Serve daemon commands", metavar="SUBCOMMAND"
    )

    # ------------------------------------------------------------------
    # start
    # ------------------------------------------------------------------
    start_parser = serve_subparsers.add_parser(
        "start", help="Start the session runner daemon"
    )
    start_parser.add_argument(
        "--port",
        type=int,
        default=7777,
        help="Port to listen on (default: 7777)",
    )
    start_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    # Mutually exclusive foreground / background flags
    mode_group = start_parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--foreground",
        action="store_true",
        help="Run the daemon in the foreground (blocks terminal)",
    )
    mode_group.add_argument(
        "--background",
        action="store_true",
        default=None,
        help="Run the daemon in the background / daemon mode (default behaviour)",
    )
    start_parser.add_argument(
        "--force",
        action="store_true",
        help="Force-kill any existing instance before starting",
    )
    start_parser.add_argument(
        "--channels",
        type=str,
        default=None,
        help=(
            "Comma-separated channel adapters to enable (e.g. telegram,slack,github)"
        ),
    )
    start_parser.add_argument(
        "--project-root",
        dest="project_root",
        type=str,
        default=None,
        help="Default project root directory for new sessions",
    )

    # ------------------------------------------------------------------
    # stop
    # ------------------------------------------------------------------
    stop_parser = serve_subparsers.add_parser(
        "stop", help="Stop the session runner daemon"
    )
    stop_parser.add_argument(
        "--port",
        type=int,
        default=7777,
        help="Port of the daemon to stop (default: 7777)",
    )
    stop_parser.add_argument(
        "--force",
        action="store_true",
        help="Force-stop even if clients are connected",
    )

    # ------------------------------------------------------------------
    # restart
    # ------------------------------------------------------------------
    restart_parser = serve_subparsers.add_parser(
        "restart", help="Restart the session runner daemon"
    )
    restart_parser.add_argument(
        "--port",
        type=int,
        default=7777,
        help="Port for the restarted daemon (default: 7777)",
    )
    restart_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    restart_parser.add_argument(
        "--foreground",
        action="store_true",
        help="Restart in foreground mode",
    )
    restart_parser.add_argument(
        "--channels",
        type=str,
        default=None,
        help="Comma-separated channel adapters to enable",
    )
    restart_parser.add_argument(
        "--project-root",
        dest="project_root",
        type=str,
        default=None,
        help="Default project root directory for new sessions",
    )

    # ------------------------------------------------------------------
    # status
    # ------------------------------------------------------------------
    status_parser = serve_subparsers.add_parser(
        "status", help="Check the session runner daemon status"
    )
    status_parser.add_argument(
        "--port",
        type=int,
        default=7777,
        help="Port to check (default: 7777)",
    )
    status_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed status information",
    )

    return serve_parser
