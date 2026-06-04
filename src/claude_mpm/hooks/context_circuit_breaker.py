"""PreToolUse context circuit breaker — warn (not hard-block) when context nears full.

WHAT: Reads cumulative context-usage state from the per-session state file and
emits a *warning* annotation when the session's context exceeds a critical
threshold.  Read-only and recovery tools are always allowed through, so a
session that has hit the threshold can still self-recover via /compact, Read,
Grep, or /mpm-resume.

WHY: Prior to this fix (issue #642) the breaker hard-blocked every tool call
once the token count exceeded 95 % of a *hardcoded* 200 K ceiling.  On models
with 1 M context windows (Opus 4.x, large-context Sonnet 4.5+) this fired
almost immediately and made sessions completely unrecoverable.  The fix:

1. **Dynamic context window** — the ceiling is resolved from the active model id
   (via :mod:`claude_mpm.hooks.model_context_window`) so 1 M-context models are
   never compared against a 200 K budget.
2. **Percentage clamped at 100** — ``percentage_used`` read from the state file
   can exceed 100 when a prior version wrote it with the wrong budget; we cap
   it before evaluation so display values are always sane.
3. **Allow-with-warning instead of hard-block** — the breaker no longer
   returns ``permissionDecision: deny`` for regular tool calls.  It emits
   ``permissionDecision: "allow"`` (the only documented non-blocking value)
   with the warning text in ``permissionDecisionReason``, preserving session
   usability.  "warn" is not a documented PreToolUse value and was removed.
4. **Always allow read-only / recovery tools** — the tools listed in
   ``ALWAYS_ALLOWED_TOOLS`` pass through unconditionally, even if the threshold
   is exceeded and warnings are suppressed for them.
5. **Disable switch** — set the ``CLAUDE_MPM_DISABLE_CONTEXT_BREAKER=1`` env
   var or the ``context_circuit_breaker.disabled`` config key to fully bypass
   this module.  The disable instructions are included in the warning message.

State source
------------
The cumulative context-usage state is written by
:class:`claude_mpm.services.infrastructure.context_usage_tracker.ContextUsageTracker`
to ``<cwd>/.claude-mpm/state/context-usage.json``.

Fail-open policy
----------------
If the state file is missing, unreadable, or malformed the breaker returns an
empty dict (pass-through).  False positives (blocking a session unnecessarily)
are far worse than a missed warning.

Disable switch
--------------
Set ``CLAUDE_MPM_DISABLE_CONTEXT_BREAKER=1`` (or ``true`` / ``yes``) in the
environment **or** add ``"context_circuit_breaker": {"disabled": true}`` to
``.claude/settings.json`` to fully disable this module.

References
----------
SPEC-HOOKS-11~1 : docs/specs/hooks.md#SPEC-HOOKS-11~1
GitHub issue #642
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from claude_mpm.hooks.model_context_window import (
    resolve_context_window,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Threshold (percentage) above which the warning fires.
# Mirrors ``ContextUsageTracker.THRESHOLDS["critical"]`` (0.95 → 95 %).
CRITICAL_THRESHOLD: float = 95.0

# Tools that are always allowed through — even above the critical threshold.
# These are read-only / recovery / navigation tools that a user needs to be
# able to run in order to self-recover from a full context window.
ALWAYS_ALLOWED_TOOLS: frozenset[str] = frozenset(
    {
        # Read-only file tools
        "Read",
        "Glob",
        "Grep",
        "LS",
        "NotebookRead",
        # Web retrieval (needed to fetch docs during recovery)
        "WebSearch",
        "WebFetch",
        # Session management / recovery skills
        "mpm-resume",
        "mpm-session-pause",
        "mpm-compact",
        # Claude Code built-ins
        "TodoRead",
        "TodoWrite",
        "exit_plan_mode",
    }
)

_STATE_FILE_RELATIVE = Path(".claude-mpm") / "state" / "context-usage.json"

# Environment variable name for the disable switch.
_DISABLE_ENV_VAR = "CLAUDE_MPM_DISABLE_CONTEXT_BREAKER"

# Config key path inside .claude/settings.json for the disable switch.
# JSON path: {"context_circuit_breaker": {"disabled": true}}
_CONFIG_KEY = "context_circuit_breaker"
_CONFIG_DISABLED_FIELD = "disabled"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_disabled(cwd: str) -> bool:
    """Return True if the circuit breaker has been explicitly disabled.

    Checks, in order:
    1. ``CLAUDE_MPM_DISABLE_CONTEXT_BREAKER`` env var (any truthy value).
    2. ``context_circuit_breaker.disabled`` in .claude/settings.json.
    3. ``context_circuit_breaker.disabled`` in ~/.claude/settings.json.
    """
    env_val = os.environ.get(_DISABLE_ENV_VAR, "").strip().lower()
    if env_val in ("1", "true", "yes", "on"):
        return True

    # Check project and global settings files.
    settings_candidates: list[Path] = []
    if cwd:
        settings_candidates.extend(
            [
                Path(cwd) / ".claude" / "settings.local.json",
                Path(cwd) / ".claude" / "settings.json",
            ]
        )
    settings_candidates.append(Path.home() / ".claude" / "settings.json")

    for settings_path in settings_candidates:
        try:
            if not settings_path.is_file():
                continue
            with settings_path.open(encoding="utf-8") as fh:
                data = json.load(fh)
            cb_config = data.get(_CONFIG_KEY)
            if isinstance(cb_config, dict):
                disabled_val = cb_config.get(_CONFIG_DISABLED_FIELD, False)
                if disabled_val is True or str(disabled_val).lower() in (
                    "1",
                    "true",
                    "yes",
                    "on",
                ):
                    return True
        except (OSError, json.JSONDecodeError, ValueError):
            continue

    return False


def _load_state(cwd: str) -> dict[str, Any] | None:
    """Read context-usage state from disk.

    Returns ``None`` when the file is missing, unreadable, or malformed —
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


def _compute_percentage(state: dict[str, Any]) -> float | None:
    """Compute context usage percentage from state, clamped to [0, 100].

    The ``percentage_used`` field may have been written by an older version of
    the tracker that used a hardcoded 200 K budget against a 1 M-context model.
    That can produce values well above 100.  We clamp the displayed value and,
    more importantly, recompute from raw token counts when the active model's
    real window is larger than the stored budget.

    Returns ``None`` when the percentage cannot be determined (fail-open).
    """
    # Prefer recomputing from raw tokens if available, using the real window.
    cumulative_input = state.get("cumulative_input_tokens")
    cumulative_output = state.get("cumulative_output_tokens")

    if isinstance(cumulative_input, (int, float)) and isinstance(
        cumulative_output, (int, float)
    ):
        total_tokens = float(cumulative_input) + float(cumulative_output)
        # Resolve context window for the active model.
        context_window = resolve_context_window()
        raw_pct = (total_tokens / context_window) * 100.0
        return min(raw_pct, 100.0)

    # Fall back to the stored percentage_used field.
    percentage_raw = state.get("percentage_used")
    if percentage_raw is None:
        return None
    try:
        percentage = float(percentage_raw)
    except (TypeError, ValueError):
        return None
    # Clamp to [0, 100] regardless of what was stored.
    return min(max(percentage, 0.0), 100.0)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def evaluate(event: dict[str, Any]) -> dict[str, Any]:
    """Evaluate the breaker against the current event.

    Returns a ``hookSpecificOutput``-shaped dict when the breaker fires a
    *warning*, and an empty dict otherwise.  At/above threshold the decision
    is ``permissionDecision: "allow"`` (a documented PreToolUse value) with
    the warning text in ``permissionDecisionReason``.  This is the only
    non-empty decision this function can emit — "deny" and "warn" are never
    returned (the former was the pre-#642 behavior; the latter is not a
    documented Claude Code value and could be treated as an error).

    Read-only and recovery tools (``ALWAYS_ALLOWED_TOOLS``) are never warned
    against and always return an empty dict (unconditional pass-through).

    :spec: SPEC-HOOKS-11~1
    """
    cwd = event.get("cwd", "") or ""

    # Unconditional allow for read-only / recovery tools.
    tool_name = str(event.get("tool_name") or "")
    if tool_name in ALWAYS_ALLOWED_TOOLS:
        return {}

    # Disable switch check.
    if _is_disabled(cwd):
        return {}

    state = _load_state(cwd)
    if state is None:
        return {}

    # Session-ID guard: only warn when the persisted state belongs to the
    # current session.  Stale state from a prior run must not affect live work.
    current_sid = _current_session_id(event)
    state_sid = state.get("session_id")
    if current_sid is not None and state_sid and state_sid != current_sid:
        return {}

    percentage = _compute_percentage(state)
    if percentage is None:
        return {}

    if percentage < CRITICAL_THRESHOLD:
        return {}

    pct_display = round(percentage)
    reason = (
        f"Context at {pct_display}% — approaching session limit. "
        "Consider running /compact or starting a new session via /mpm-resume. "
        f"To disable this warning: set {_DISABLE_ENV_VAR}=1 or add "
        f'"{_CONFIG_KEY}": {{"disabled": true}} to .claude/settings.json.'
    )
    # Return allow-with-warning — "allow" is a documented PreToolUse value;
    # "warn" is NOT documented and risks being treated as deny/error.
    # The warning text is carried in permissionDecisionReason so the harness
    # can surface it while still letting the tool call proceed.
    return {
        "permissionDecision": "allow",
        "permissionDecisionReason": reason,
    }


def main() -> None:
    """Entry point when invoked as ``python3 -m claude_mpm.hooks.context_circuit_breaker``.

    Reads a hook event from stdin, evaluates the breaker, and emits either a
    warning annotation or a pass-through ``{"continue": true}`` payload.
    Any failure short-circuits to pass-through (fail-open).
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
    decision_type = decision.get("permissionDecision")

    # evaluate() only ever returns "allow" (allow-with-warning) or nothing ({}
    # → pass-through).  "deny" and "warn" are never emitted post-#642 fix.
    if decision_type == "allow":
        payload = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
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
