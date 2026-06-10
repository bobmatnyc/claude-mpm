"""session-report command: generate a canonical Markdown session report.

WHY: Claude Code records full JSONL transcripts of every session. This command
reads those transcripts — without any LLM calls — and produces a structured
Markdown document capturing the full timeline, all subagent delegations, skill
and MCP calls, per-call token counts, and a total estimated cost at public
rack rates. Intended for debugging and teaching effective agentic coding.

DESIGN DECISIONS:
- Default output path: docs/reporting/session-tracker/{session_id}.md so all
  session reports live in a predictable, version-controlled location.
- --session defaults to the most-recent session for the project directory so
  the common case (just ran a session, want to inspect it) needs no arguments.
- Writing to stdout (--output -) allows piping into other tools.
- All computation is deterministic and offline; no network calls.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import argparse

_DEFAULT_OUTPUT_DIR = Path("docs/reporting/session-tracker")


def run_session_report(args: argparse.Namespace) -> int:
    """Execute the session-report command.

    WHAT: Locates the session transcript, parses it into a SessionReport, and
          renders it to Markdown — writing to a file or stdout.
    WHY:  Thin CLI shim that delegates all logic to the session_analysis
          services so the business logic stays independently testable.
    """
    from ...services.session_analysis.markdown_writer import (
        render_markdown,
        write_report,
    )
    from ...services.session_analysis.transcript_parser import (
        find_most_recent_session,
        locate_transcript,
        parse_session,
    )

    # -- Resolve project path -------------------------------------------------
    project_path_str: str = getattr(args, "project", None) or str(Path.cwd())
    project_path = Path(project_path_str).resolve()
    cwd = str(project_path)

    # -- Resolve session id ---------------------------------------------------
    session_id: str | None = getattr(args, "session", None)
    if not session_id:
        session_id = find_most_recent_session(cwd)
        if not session_id:
            print(
                f"No session transcripts found for project: {cwd}",
                file=sys.stderr,
            )
            return 1

    # -- Verify transcript exists ---------------------------------------------
    transcript_path = locate_transcript(session_id, cwd)
    if not transcript_path.exists():
        print(
            f"Transcript not found: {transcript_path}",
            file=sys.stderr,
        )
        return 1

    # -- Parse ----------------------------------------------------------------
    try:
        report = parse_session(session_id, cwd)
    except Exception as exc:
        print(f"Failed to parse session transcript: {exc}", file=sys.stderr)
        return 1

    # -- Render ---------------------------------------------------------------
    output_arg: str | None = getattr(args, "output", None)

    if output_arg in (None, ""):
        # Default: write to docs/reporting/session-tracker/{session_id}.md
        output_path = _DEFAULT_OUTPUT_DIR / f"{session_id}.md"
        try:
            write_report(report, output_path)
        except OSError as exc:
            print(f"Failed to write report: {exc}", file=sys.stderr)
            return 1
        print(f"Session report written: {output_path}")

    elif output_arg == "-":
        # Stdout
        sys.stdout.write(render_markdown(report))

    else:
        # Explicit file path
        out_path = Path(output_arg)
        try:
            write_report(report, out_path)
        except OSError as exc:
            print(f"Failed to write report: {exc}", file=sys.stderr)
            return 1
        print(f"Session report written: {out_path}")

    return 0


def add_session_report_parser(subparsers: argparse.ArgumentParser) -> None:
    """Register the session-report subcommand."""
    parser = subparsers.add_parser(
        "session-report",
        help="Generate a Markdown session report from a Claude Code transcript",
        description=(
            "Reads Claude Code's own JSONL session transcript and emits a\n"
            "canonical Markdown session report with a full timeline, subagent\n"
            "delegations, skill/MCP calls, token counts, and estimated cost.\n\n"
            "No LLM inference — fully deterministic and offline.\n\n"
            "Output defaults to docs/reporting/session-tracker/{session_id}.md.\n"
            "Use --output - to print to stdout."
        ),
    )
    parser.add_argument(
        "--session",
        "-s",
        metavar="SESSION_ID",
        default=None,
        help=(
            "Session UUID to report on "
            "(default: most recent session for the project directory)"
        ),
    )
    parser.add_argument(
        "--project",
        "-p",
        metavar="PATH",
        default=None,
        help="Project directory path (default: current working directory)",
    )
    parser.add_argument(
        "--output",
        "-o",
        metavar="FILE",
        default=None,
        help=(
            "Output file path.  "
            "Use '-' for stdout.  "
            "Default: docs/reporting/session-tracker/{session_id}.md"
        ),
    )
    parser.set_defaults(command="session-report")
