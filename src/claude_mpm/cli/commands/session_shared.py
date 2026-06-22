"""
Shared session pause/resume logic for CLI commands.

WHAT: Provides ``handle_pause`` and ``handle_resume`` functions that both the
``mpm-init`` and ``session`` command handlers delegate to, ensuring identical
behaviour from either entry point.

WHY: Without a shared module, each command handler would need to duplicate the
pause/resume dispatch code. Extracting to a shared module guarantees that
``claude-mpm session pause|resume`` and ``claude-mpm mpm-init pause|context``
produce exactly the same output and side-effects.

References
----------
SPEC-CLI-04~1 : docs/specs/cli.md#SPEC-CLI-04~1
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console

if TYPE_CHECKING:
    from claude_mpm.services.cli.session_pause_manager import SessionPauseManager

console = Console()
logger = logging.getLogger(__name__)


def handle_pause(args) -> int:
    """Execute the session pause workflow.

    WHAT: Creates a session pause document capturing git context, todos, and
    working-directory state, then prints a structured success summary.

    WHY: Shared so that both ``claude-mpm mpm-init pause`` and
    ``claude-mpm session pause`` produce identical output and invoke the same
    ``SessionPauseManager`` code path.

    Args:
        args: Parsed argparse Namespace with optional attributes:
              ``project_path`` (str|Path), ``message`` (str|None),
              ``export`` (str|None).

    Returns:
        0 on success, 1 on error.
    """
    try:
        from claude_mpm.services.cli.session_pause_manager import SessionPauseManager

        # Resolve project path — parser always sets the default "." so getattr
        # covers both the CLI path and any direct Namespace construction in tests.
        project_path = Path(getattr(args, "project_path", "."))

        console.print("\n[cyan]Creating session pause...[/cyan]")

        # ``--no-prune-worktrees`` flag disables pruning (default: prune enabled).
        prune_worktrees = not getattr(args, "no_prune_worktrees", False)

        # Create pause session
        pause_manager = SessionPauseManager(project_path)
        session_id = pause_manager.create_pause_session(
            message=getattr(args, "message", None),
            skip_commit=getattr(args, "no_commit", False),
            export_path=getattr(args, "export", None),
            prune_worktrees=prune_worktrees,
        )

        # Display success message
        console.print()
        console.print("[green]Session Paused Successfully[/green]", style="bold")
        console.print()
        console.print(f"[cyan]Session ID:[/cyan] {session_id}")
        console.print(
            f"[cyan]Paused At:[/cyan] {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S %Z')}"
        )
        console.print(f"[cyan]Location:[/cyan] .claude-mpm/sessions/{session_id}.*")

        # Show what was captured
        console.print()
        console.print("[blue]Files Created:[/blue]")
        console.print(f"  - [dim]{session_id}.json[/dim] - Machine-readable data")
        console.print(f"  - [dim]{session_id}.md[/dim] - Human-readable documentation")
        console.print("  - [dim]LATEST-SESSION.txt[/dim] - Quick reference pointer")

        # Export info
        if getattr(args, "export", None):
            console.print()
            console.print(f"[green]Exported to:[/green] {args.export}")

        # Show message if provided
        if getattr(args, "message", None):
            console.print()
            console.print(f"[yellow]Context:[/yellow] {args.message}")

        # Worktree prune summary
        if prune_worktrees:
            _print_prune_summary(pause_manager)

        # Resume instructions
        console.print()
        console.print("[yellow]Resume with:[/yellow] claude-mpm session resume")
        console.print(
            "[yellow]Quick view:[/yellow] cat .claude-mpm/sessions/LATEST-SESSION.txt"
        )
        console.print()

        return 0

    except ImportError as e:
        console.print(f"[red]Error: Required module not available: {e}[/red]")
        console.print("[yellow]Ensure claude-mpm is properly installed[/yellow]")
        return 1
    except KeyboardInterrupt:
        console.print("\n[yellow]Session pause cancelled by user[/yellow]")
        return 130
    except Exception as e:
        console.print(f"[red]Error pausing session: {e}[/red]")
        if getattr(args, "verbose", False):
            import traceback

            traceback.print_exc()
        return 1


def _print_prune_summary(pause_manager: SessionPauseManager) -> None:
    """Print a concise worktree prune summary to the console.

    WHAT: Reads the prune summary from the most-recently-written session and
    displays a compact one-liner plus detail for preserved worktrees and swept
    orphaned directories.

    WHY: Users need to know which worktrees were cleaned and which were kept
    (and why) so they can take action on preserved ones if needed.  Orphan
    sweep results are reported separately so users can distinguish between
    registered-worktree pruning and leftover-directory cleanup.

    Args:
        pause_manager: The SessionPauseManager instance used for the pause;
            its ``prune_stale_worktrees`` result is embedded in the last
            session JSON.  We call it here only for display purposes —
            the actual pruning already happened inside ``create_pause_session``.
    """
    # The prune summary was computed and stored in the last session JSON by
    # create_pause_session.  Re-read it from the attribute set on the manager
    # (we piggy-back on the cached result rather than re-running git).
    # Fall back to a fresh call only when no cached summary is available
    # (e.g. callers that bypass create_pause_session).
    try:
        summary = getattr(pause_manager, "_last_prune_summary", None)
        if summary is None:
            return  # Nothing to show

        pruned = summary.get("pruned_count", 0)
        preserved = summary.get("preserved_count", 0)
        worktrees = summary.get("worktrees", [])
        orphans_swept = summary.get("orphans_swept", 0)
        orphans_preserved = summary.get("orphans_preserved", 0)
        orphans = summary.get("orphans", [])

        total_activity = pruned + preserved + orphans_swept + orphans_preserved
        if total_activity == 0:
            return  # No managed worktrees or orphans found — silent

        console.print()
        console.print("[blue]Worktree Cleanup:[/blue]")

        # Registered-worktree section
        if pruned > 0:
            console.print(f"  [green]Pruned {pruned} stale worktree(s)[/green]")
        if preserved > 0:
            console.print(
                f"  [yellow]Preserved {preserved} worktree(s) with unsaved work[/yellow]"
            )
            for wt in worktrees:
                if wt.get("action") == "preserve":
                    path = wt.get("path", "?")
                    reason = wt.get("reason", "unknown reason")
                    console.print(f"    [dim]{path}[/dim]: {reason}")

        # Orphan sweep section
        if orphans_swept > 0:
            console.print(
                f"  [green]Swept {orphans_swept} orphaned director(ies)[/green]"
            )
        if orphans_preserved > 0:
            console.print(
                f"  [yellow]Preserved {orphans_preserved} orphaned director(ies) with unsaved work[/yellow]"
            )
            for orph in orphans:
                if orph.get("action") == "preserved":
                    path = orph.get("path", "?")
                    reason = orph.get("reason", "unknown reason")
                    console.print(f"    [dim]{path}[/dim]: {reason}")
    except Exception as exc:  # nosec B110
        logger.debug("_print_prune_summary display error (non-fatal): %s", exc)


def handle_resume(args) -> int:
    """Execute the session resume workflow.

    WHAT: Loads a paused session from the project-local session store and
    displays a formatted resume prompt. Supports three selection modes:
    ``--select INDEX_OR_ID``, exact positional ``session_id``, and the
    default (most-recent, or list when multiple exist).

    WHY: Shared so that both ``claude-mpm mpm-init context`` and
    ``claude-mpm session resume`` invoke identical ``SessionResumeHelper``
    code paths and produce the same output.

    Args:
        args: Parsed argparse Namespace with optional attributes:
              ``project_path`` (str|Path), ``select`` (str|None),
              ``session_id`` (str|None).

    Returns:
        0 on success, 1 on error.
    """
    try:
        from claude_mpm.services.cli.session_resume_helper import SessionResumeHelper

        # Resolve project path — parser always sets the default "." so getattr
        # covers both the CLI path and any direct Namespace construction in tests.
        project_path = Path(getattr(args, "project_path", "."))

        helper = SessionResumeHelper(project_path=project_path)

        select_value: str | None = getattr(args, "select", None)
        exact_session_id: str | None = getattr(args, "session_id", None)

        if select_value is not None:
            # --select <index-or-partial-id>
            session_data, error_msg = helper.resolve_session_by_selection(select_value)
            if session_data is None:
                console.print(error_msg)
                return 1
            prompt_text = helper.format_resume_prompt(session_data)
            console.print(prompt_text)
            sid = session_data.get("session_id", "unknown")
            file_path = session_data.get("file_path")
            console.print(f"Loaded session: {sid}")
            if file_path:
                console.print(f"Source: {file_path}")

        elif exact_session_id is not None:
            # Exact session ID supplied (backward-compatible positional form)
            all_sessions = helper.list_all_sessions()
            matched = [
                s for s in all_sessions if s.get("session_id") == exact_session_id
            ]
            if not matched:
                console.print(f"No session found with ID: {exact_session_id}")
                console.print("")
                console.print(helper.format_session_list())
                return 1
            session_data = matched[0]
            prompt_text = helper.format_resume_prompt(session_data)
            console.print(prompt_text)
            file_path = session_data.get("file_path")
            console.print(f"Loaded session: {exact_session_id}")
            if file_path:
                console.print(f"Source: {file_path}")

        else:
            # No arguments — list when multiple sessions exist, else resume most recent
            session_count = helper.get_session_count()
            if session_count == 0:
                console.print(
                    "No paused sessions found for this project in .claude-mpm/sessions/"
                )
                console.print("")
                console.print(
                    "To create a paused session, use: claude-mpm session pause"
                )
                return 0
            if session_count > 1:
                # Show numbered list so the user can pick
                console.print(helper.format_session_list())
                console.print("")
                console.print("Resuming the most recent session automatically...")
                session_data = helper.check_and_display_resume_prompt()
                if session_data:
                    sid = session_data.get("session_id", "unknown")
                    file_path = session_data.get("file_path")
                    console.print(f"Loaded session: {sid}")
                    if file_path:
                        console.print(f"Source: {file_path}")
            else:
                # Only one session — resume it directly
                session_data = helper.check_and_display_resume_prompt()
                if session_data is None:
                    console.print(
                        "No paused sessions found for this project in "
                        ".claude-mpm/sessions/"
                    )
                    console.print("")
                    console.print(
                        "To create a paused session, use: claude-mpm session pause"
                    )
                    return 0
                sid = session_data.get("session_id", "unknown")
                file_path = session_data.get("file_path")
                console.print("")
                console.print(f"Loaded session: {sid}")
                if file_path:
                    console.print(f"Source: {file_path}")

        return 0

    except ImportError as e:
        console.print(f"[red]Error: Required module not available: {e}[/red]")
        console.print("[yellow]Ensure claude-mpm is properly installed[/yellow]")
        return 1
    except KeyboardInterrupt:
        console.print("\n[yellow]Session resume cancelled by user[/yellow]")
        return 130
    except Exception as e:
        console.print(f"[red]Error resuming session: {e}[/red]")
        if getattr(args, "verbose", False):
            import traceback

            traceback.print_exc()
        return 1
