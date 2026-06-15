"""
Session command handler for claude-mpm CLI.

WHAT: Dispatches ``claude-mpm session pause``, ``claude-mpm session resume``,
and ``claude-mpm session create`` to the appropriate implementation.

WHY: Provides a thin router that keeps the handler trivially small and ensures
both the ``session`` and ``mpm-init`` routes call the same underlying code.
The ``create`` subcommand was added for issue #771 to enable programmatic
session creation via the REST/socket daemon API.
"""

from rich.console import Console

from .session_cmd import handle_session_create
from .session_shared import handle_pause, handle_resume

console = Console()


def manage_session(args) -> int:
    """Handle the session command group dispatch.

    Args:
        args: Parsed argparse Namespace. ``args.session_command`` selects
              the subcommand (``"pause"``, ``"resume"``, or ``"create"``).

    Returns:
        Exit code (0 on success, non-zero on error).
    """
    session_command = getattr(args, "session_command", None)

    if session_command == "pause":
        return handle_pause(args)

    if session_command == "resume":
        return handle_resume(args)

    if session_command == "create":
        return handle_session_create(args)

    # No subcommand specified — show help
    console.print("\n[yellow]Usage:[/yellow] claude-mpm session <subcommand>\n")
    console.print("Subcommands:")
    console.print("  pause   Pause current session and save state")
    console.print("  resume  Resume from a previously paused session")
    console.print("  create  Create a new session via the serve daemon REST API")
    console.print(
        "\nRun [dim]claude-mpm session --help[/dim] for full usage information.\n"
    )
    return 1
