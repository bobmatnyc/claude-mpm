#!/usr/bin/env python3
"""SessionStart MCP-PID capture handler (issue #927).

WHAT: On every Claude Code SessionStart event, discovers the live stdio-mode MCP
server subprocesses Claude Code spawned for this project (trusty-memory,
trusty-search, trusty-review, and any other stdio server declared in
``.mcp.json``) and records their PIDs to
``<project>/.claude-mpm/mcp-pids-<session_id>.json``.  ``claude-mpm session
pause`` later reads those records to SIGTERM the stale servers cleanly.

WHY: ``session pause`` runs as a standalone CLI invocation with no Claude Code
hooks firing, and Claude Code owns the stdio MCP subprocesses.  Capturing the
PIDs at session start is the only correlation point where the live servers and
this session are both known, so pause can target exactly the right processes.

CONVENTIONS: Mirrors ``stop_handler.py`` — fail-open (never raises to the hook
dispatcher), with an always-on debug log so silent failures leave a paper trail.

SESSION-ID CHOICE: We key the record file on the Claude Code ``session_id`` UUID
from the SessionStart event (the natural per-session identifier available to
hooks).  ``session pause`` has no way to correlate back to that UUID — it is a
separate CLI process — so it globs ALL ``mcp-pids-*.json`` records for the
project.  That is intentional and safe: pausing the project is a natural gate to
reap every stdio MCP server spawned for it, and Claude Code simply respawns any
still-active session's servers (picking up the current binary).
"""

from datetime import UTC, datetime
from pathlib import Path

# Always-on debug log — same pattern as stop_handler._stop_debug so failures in
# this fail-open handler remain visible without setting CLAUDE_MPM_HOOK_DEBUG.
_MCP_DEBUG_LOG: Path = (
    Path.home() / ".claude-mpm" / "logs" / "session-start-mcp-debug.log"
)


def _mcp_debug(message: str) -> None:
    """Append *message* to the session-start MCP debug log, unconditionally."""
    try:
        _MCP_DEBUG_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S")
        with _MCP_DEBUG_LOG.open("a") as fh:
            fh.write(f"[{ts}] {message}\n")
    except Exception:
        pass  # Never raise from a debug helper.


def capture_session_mcp_pids(event: dict) -> None:
    """Capture stdio MCP server PIDs for a SessionStart *event*.

    Fail-open: any error is logged to the debug file and swallowed so it can
    never escape to the hook dispatcher.

    Args:
        event: The SessionStart hook event dict (uses ``session_id`` and
            ``cwd``).
    """
    try:
        session_id = event.get("session_id", "") or "unknown"
        cwd = event.get("cwd", "") or str(Path.cwd())
        project_dir = Path(cwd)

        # Import lazily so the hook path stays cheap and self-contained.
        from claude_mpm.services.cli.mcp_process_tracker import capture_session_pids

        record_path = capture_session_pids(project_dir, session_id)
        if record_path is None:
            _mcp_debug(
                f"capture_session_mcp_pids: no stdio MCP processes recorded "
                f"(session={session_id!r} cwd={cwd!r})"
            )
        else:
            _mcp_debug(
                f"capture_session_mcp_pids: wrote {record_path} "
                f"(session={session_id!r})"
            )
    except Exception as exc:  # nosec B110 - fail-open by design
        _mcp_debug(f"capture_session_mcp_pids FAILED (fail-open): {exc}")
