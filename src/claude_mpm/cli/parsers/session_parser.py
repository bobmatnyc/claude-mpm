"""
Session parser module for claude-mpm CLI.

WHAT: Provides the ``add_session_subparser`` factory that registers the top-level
``session`` command group with ``pause``, ``resume``, and ``create`` subcommands.

WHY: Exposes ``claude-mpm session pause|resume|create`` as first-class CLI
commands so that skill implementations and shell scripts can use a stable
console-script entry point.  The ``create`` subcommand was added for issue #771
to enable programmatic session creation via the REST/socket daemon API.

References
----------
SPEC-CLI-04~1 : docs/specs/cli.md#SPEC-CLI-04~1
"""

import argparse
from typing import Any


def add_session_subparser(subparsers: Any) -> None:
    """Add the session subparser to the main parser.

    WHAT: Registers the ``session`` top-level command group and its ``pause``
    and ``resume`` subcommands — with all flags and positional arguments —
    onto the provided ``subparsers`` object.

    WHY: The ``session`` command group gives users and skills a clean,
    memorable entry point for pause/resume operations without needing to
    know about the ``mpm-init`` subcommand hierarchy.

    :spec: SPEC-CLI-04~1

    Args:
        subparsers: The subparsers object to add the session command to
    """
    session_parser = subparsers.add_parser(
        "session",
        help="Manage session state (pause / resume / create)",
        description=(
            "Manage Claude MPM session state. Use 'pause' to save current work "
            "context, 'resume' to load a previously saved session, or 'create' to "
            "programmatically create a new session via the REST daemon API."
        ),
        epilog=(
            "Examples:\n"
            "  claude-mpm session pause                       # Pause current session\n"
            "  claude-mpm session pause -m 'End of day'      # Pause with message\n"
            "  claude-mpm session resume                      # Resume most recent session\n"
            "  claude-mpm session resume --select 2           # Resume 2nd most recent\n"
            "  claude-mpm session resume --select 20240101    # Resume by partial ID\n"
            "  claude-mpm session resume <session-id>         # Resume by exact ID\n"
            "  claude-mpm session create                      # Create session via daemon\n"
            "  claude-mpm session create --model opus         # Create with specific model\n"
            "  SESSION_ID=$(claude-mpm session create)        # Capture session id\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    session_parser.set_defaults(command="session")

    # Add subparsers for pause and resume
    session_subparsers = session_parser.add_subparsers(
        dest="session_command",
        title="session subcommands",
        description="Available session management operations",
        metavar="SUBCOMMAND",
    )

    # -------------------------------------------------------------------------
    # pause subcommand
    # -------------------------------------------------------------------------
    pause_parser = session_subparsers.add_parser(
        "pause",
        help="Pause current session and save state",
        description=(
            "Create session pause documents for later resume. Captures git context, "
            "conversation state, todos, and working directory state.\n\n"
            "Creates two file formats:\n"
            "  - JSON: Machine-readable structured data\n"
            "  - Markdown: Full documentation format"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  claude-mpm session pause                          # Basic pause\n"
            "  claude-mpm session pause -m 'End of day'         # With message\n"
            "  claude-mpm session pause --export session.json   # Export copy\n"
        ),
    )
    pause_parser.add_argument(
        "--message",
        "-m",
        type=str,
        default=None,
        help="Optional message describing pause reason or context",
    )
    # --no-commit is kept as a deprecated no-op for back-compat; sessions are
    # written to .claude-mpm/sessions/ which is gitignored and never committed.
    pause_parser.add_argument(
        "--no-commit",
        action="store_true",
        help=argparse.SUPPRESS,  # deprecated no-op — sessions are never committed
    )
    pause_parser.add_argument(
        "--export",
        type=str,
        default=None,
        help="Export session state to custom location",
    )
    pause_parser.add_argument(
        "project_path",
        nargs="?",
        default=".",
        help="Path to project directory (default: current directory)",
    )

    # -------------------------------------------------------------------------
    # resume subcommand
    # -------------------------------------------------------------------------
    resume_parser = session_subparsers.add_parser(
        "resume",
        help="Resume from a previously paused session",
        description=(
            "Load and display context from a paused session. With no arguments, "
            "resumes the most recent session (or lists all sessions when multiple "
            "exist). Use --select to pick a specific session by index or partial ID."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  claude-mpm session resume                                # Resume most recent\n"
            "  claude-mpm session resume --select 2                    # 2nd most recent\n"
            "  claude-mpm session resume --select 20240101             # Partial ID match\n"
            "  claude-mpm session resume <session-id>                  # Exact session ID\n"
            "  claude-mpm session resume --project-path /my/project    # Specify project\n"
        ),
    )
    resume_parser.add_argument(
        "--select",
        type=str,
        default=None,
        metavar="INDEX_OR_ID",
        help=(
            "Select session by 1-based index or partial session ID. "
            "Example: --select 2 (second most recent), --select 20240101 (date prefix)"
        ),
    )
    resume_parser.add_argument(
        "session_id",
        nargs="?",
        default=None,
        help="Exact session ID to resume (backward-compatible positional argument)",
    )
    resume_parser.add_argument(
        "--project-path",
        type=str,
        default=".",
        dest="project_path",
        help="Path to project directory (default: current directory)",
    )

    # -------------------------------------------------------------------------
    # create subcommand (issue #771 — programmatic session creation)
    # -------------------------------------------------------------------------
    create_parser = session_subparsers.add_parser(
        "create",
        help="Create a new session via the serve daemon REST API",
        description=(
            "Create a new Claude session via the running serve daemon and print "
            "the session_id to stdout.  The daemon must be started first with "
            "'claude-mpm serve start'.\n\n"
            "Ideal for shell scripting:\n"
            "  SESSION_ID=$(claude-mpm session create --model opus)\n"
            "  claude-mpm session create --cwd /path/to/project"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  claude-mpm session create                         # Default model\n"
            "  claude-mpm session create --model claude-opus-4-5 # Specific model\n"
            "  claude-mpm session create --cwd /my/project       # Set working dir\n"
            "  claude-mpm session create --url http://localhost:7777  # Explicit URL\n"
            "  SESSION=$(claude-mpm session create) && echo $SESSION\n"
        ),
    )
    create_parser.add_argument(
        "--prompt",
        type=str,
        default=None,
        metavar="TEXT",
        help="Initial prompt to send to the new session (optional).",
    )
    create_parser.add_argument(
        "--model",
        type=str,
        default=None,
        metavar="MODEL",
        help="Claude model identifier (e.g. claude-opus-4-5, sonnet). "
        "Defaults to daemon's configured default.",
    )
    create_parser.add_argument(
        "--cwd",
        type=str,
        default=None,
        metavar="PATH",
        help="Working directory for the new Claude subprocess (default: daemon default)",
    )
    create_parser.add_argument(
        "--permission-mode",
        dest="permission_mode",
        type=str,
        default="default",
        metavar="MODE",
        help="Permission mode for the session (default: 'default')",
    )
    create_parser.add_argument(
        "--url",
        type=str,
        default=None,
        metavar="URL",
        help="Daemon HTTP URL (e.g. http://127.0.0.1:7777). "
        "Overrides auto-detection from socket file.",
    )
    create_parser.add_argument(
        "--socket",
        dest="socket_path",
        type=str,
        default=None,
        metavar="PATH",
        help="Unix socket path of the daemon "
        "(default: ~/.claude-mpm/daemon.sock if it exists).",
    )
