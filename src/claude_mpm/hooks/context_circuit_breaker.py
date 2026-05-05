"""PreToolUse circuit-breaker: deny tool calls when context >= CRITICAL threshold.

When the running session's context window is at or above the critical threshold
(>=95%), every additional tool call risks pushing the conversation past the
hard limit and dropping prior context.  This hook returns a ``deny`` decision
so the harness blocks the call and surfaces a wrap-up message to the user.

State source
------------
The cumulative context-usage state is written by
:class:`claude_mpm.services.infrastructure.context_usage_tracker.ContextUsageTracker`
to ``<cwd>/.claude-mpm/state/context-usage.json``.  That same file is read by
:mod:`claude_mpm.hooks.claude_hooks.auto_pause_handler` and is the only
cross-process source of context state available to the hook subprocess (the
SDK-mode ``MonitorAgent`` keeps its tracker in-memory only).

Fail-open policy
----------------
If the state file is missing, unreadable, or malformed -- or if the recorded
``session_id`` doesn't match the current session -- the breaker returns an
empty dict (pass-through).  False denials are far worse than missed denials:
the worst case for fail-open is the existing behavior; the worst case for
fail-closed is bricking the session on a stale state file from a prior run.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# Critical threshold (percentage).  Mirrors
# ``ContextUsageTracker.THRESHOLDS["critical"]`` (0.95 -> 95%).
CRITICAL_THRESHOLD: float = 95.0

_STATE_FILE_RELATIVE = Path(".claude-mpm") / "state" / "context-usage.json"


def _load_state(cwd: str) -> dict[str, Any] | None:
    """Read context-usage state from disk.

    Returns ``None`` when the file is missing, unreadable, or malformed --
    the breaker treats all of those cases as fail-open.
    """
    if not cwd:
        return None
    state_path = Path(cwd) / _STATE_FILE_RELATIVE
    try:
        if not state_path.is_file():
            return None
        with state_path.open(encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def _current_session_id(event: dict[str, Any]) -> str | None:
    """Return the current session ID from the event payload or environment."""
    sid = event.get("session_id")
    if isinstance(sid, str) and sid:
        return sid
    env_sid = os.environ.get("CLAUDE_SESSION_ID")
    if env_sid:
        return env_sid
    return None


def evaluate(event: dict[str, Any]) -> dict[str, Any]:
    """Evaluate the breaker against the current event.

    Returns a ``hookSpecificOutput``-shaped dict when the breaker fires, and
    an empty dict otherwise.  Callers should treat any non-empty result as
    "emit this and stop processing".
    """
    cwd = event.get("cwd", "") or ""
    state = _load_state(cwd)
    if state is None:
        return {}

    # Session-ID guard: only block when the persisted state belongs to the
    # current session.  Stale state from a prior run must not deny live work.
    current_sid = _current_session_id(event)
    state_sid = state.get("session_id")
    if current_sid is not None and state_sid and state_sid != current_sid:
        return {}

    percentage_raw = state.get("percentage_used")
    if percentage_raw is None:
        return {}
    try:
        percentage = float(percentage_raw)
    except (TypeError, ValueError):
        return {}

    if percentage < CRITICAL_THRESHOLD:
        return {}

    pct_display = round(percentage)
    reason = (
        f"Context at {pct_display}% — session paused to prevent data loss. "
        "Use /mpm-resume or start a new session."
    )
    return {
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }


def main() -> None:
    """Entry point when invoked as ``python3 -m claude_mpm.hooks.context_circuit_breaker``.

    Reads a hook event from stdin, evaluates the breaker, and emits either a
    deny decision wrapped in ``hookSpecificOutput`` or a pass-through
    ``{"continue": true}`` payload.  Any failure short-circuits to pass-through
    (fail-open).
    """
    import sys

    try:
        event = json.load(sys.stdin)
        if not isinstance(event, dict):
            event = {}
    except Exception:
        print(json.dumps({"continue": True}))
        return

    decision = evaluate(event)
    if decision.get("permissionDecision") == "deny":
        payload = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": decision.get(
                    "permissionDecisionReason", ""
                ),
            }
        }
        print(json.dumps(payload))
        return

    print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
