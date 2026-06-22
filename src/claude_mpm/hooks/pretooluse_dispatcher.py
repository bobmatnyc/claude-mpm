#!/usr/bin/env python3
"""Consolidated PreToolUse + PermissionRequest hook dispatcher.

This module replaces four separate hook subprocesses that previously fired on
every PreToolUse event:

* ``model_tier_hook``       — injects a model tier into ``Agent`` tool calls.
* ``ztk_hook``              — rewrites ``Bash`` commands through ztk compression.
* ``context_circuit_breaker`` — warns (not hard-blocks) when context >= 95%;
  read-only/recovery tools are always allowed through (issue #642).
* ``claude-hook``           — the full handler (dashboard, memory, auto-pause).

Spawning four Python interpreters per tool call adds significant latency.  This
dispatcher reads the hook event from stdin once, then calls the importable
functions exposed by the original modules directly — no extra subprocesses.

(The ``claude-hook`` full handler still runs as its own settings.json entry; it
is independent of this dispatcher.)

Processing order
----------------
1. Parse the event from stdin.  On any failure, emit pass-through (fail-open).
2. Route ``PermissionRequest`` events to the permission policy engine.
3. For ``PreToolUse``: run the context circuit breaker.  It now emits
   ``permissionDecision: "allow"`` with a warning reason (not a hard block).
   A non-blocking allow-with-warning must NOT interrupt the dispatch pipeline —
   model-tier injection / ztk rewriting must still run.  Only an actual
   ``permissionDecision: "deny"`` short-circuits immediately.
4. Branch on ``tool_name``:
   * ``Agent`` -> model tier injection (warning attached if present).
   * ``Bash``  -> ztk rewrite (warning attached if present).
   * anything else -> pass-through (with allow+reason if breaker fired).

Fail-open policy
----------------
Any unexpected error results in a ``{"continue": true}`` pass-through.  A hook
crash must never block legitimate tool calls.
"""

from __future__ import annotations

import json
import sys
from typing import Any

from claude_mpm.hooks import (
    context_circuit_breaker,
    gh_footer_hook,
    model_tier_hook,
    ztk_hook,
)


def _passthrough() -> dict[str, Any]:
    """Return the no-op pass-through response."""
    return {"continue": True}


def _circuit_breaker_deny_response(decision: dict[str, Any]) -> dict[str, Any]:
    """Wrap a circuit-breaker *deny* decision in the PreToolUse wire format.

    Only called when ``permissionDecision`` is ``"deny"``.  Allow-with-warning
    decisions (``"allow"``) do NOT short-circuit; they continue through the
    dispatch pipeline so model-tier injection / ztk rewriting still runs.
    """
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": decision.get("permissionDecisionReason", ""),
        }
    }


def _merge_warning_into_response(
    response: dict[str, Any], warning_reason: str
) -> dict[str, Any]:
    """Attach a circuit-breaker warning reason to an existing hook response.

    The warning is carried in ``permissionDecisionReason`` inside
    ``hookSpecificOutput``.  If the response already has a
    ``hookSpecificOutput`` dict we inject there; otherwise we build a minimal
    allow-with-reason envelope so the harness can surface the message.
    """
    if not warning_reason:
        return response

    hso = response.get("hookSpecificOutput")
    if isinstance(hso, dict):
        # Existing hookSpecificOutput: inject reason if not already set.
        if not hso.get("permissionDecisionReason"):
            hso["permissionDecisionReason"] = warning_reason
        # Ensure the decision is at least allow if none is set.
        if not hso.get("permissionDecision"):
            hso["permissionDecision"] = "allow"
        return response

    # No hookSpecificOutput yet: build a minimal allow-with-reason wrapper,
    # preserving any top-level keys the caller already set (e.g. "continue").
    merged = dict(response)
    merged["hookSpecificOutput"] = {
        "hookEventName": "PreToolUse",
        "permissionDecision": "allow",
        "permissionDecisionReason": warning_reason,
    }
    return merged


def dispatch(event: dict[str, Any]) -> dict[str, Any]:
    """Evaluate all PreToolUse / PermissionRequest concerns for one event.

    WHAT: Reads a single hook event and routes it through the full
          PreToolUse concern stack in order — PermissionRequest routing,
          context circuit breaker, model-tier injection (Agent), gh-footer
          normalisation + ztk rewrite (Bash), and MCP GitHub body
          normalisation — then returns exactly one wire-format response
          dict ready for JSON serialisation.
    WHY:  Consolidating four previously separate Python subprocess hooks
          into one importable function eliminates the subprocess-spawn
          latency that accumulated on every tool call.  The strict
          processing order (circuit-breaker first, gh_footer before ztk,
          fail-open on any exception) is the invariant that makes this
          dispatcher safe to use across all tool types.

    Returns a single wire-format response dict ready to be JSON-serialized.
    Never raises: any failure falls back to pass-through.
    """
    try:
        # Route PermissionRequest events to the permission policy engine.
        hook_event = (
            event.get("hook_event_name")
            or event.get("event")
            or event.get("hook_event_type")
            or ""
        )
        if hook_event == "PermissionRequest":
            return model_tier_hook.build_permission_request_response(event)

        # Context circuit breaker runs first.  It emits either:
        #   - "deny" → hard block (short-circuit immediately).
        #   - "allow" + reason → allow-with-warning (do NOT short-circuit;
        #     model-tier injection / ztk rewriting must still run so Agent
        #     calls at high context still get tier routing).
        #   - {} → no-op pass-through.
        breaker_decision = context_circuit_breaker.evaluate(event)
        decision_type = breaker_decision.get("permissionDecision")
        warning_reason: str = ""
        if decision_type == "deny":
            # Hard block — only legacy path; breaker post-#642 never denies.
            return _circuit_breaker_deny_response(breaker_decision)
        if decision_type == "allow":
            # Allow-with-warning: stash the reason, continue the pipeline.
            warning_reason = breaker_decision.get("permissionDecisionReason", "")

        # Branch on the tool being invoked.
        tool_name = event.get("tool_name", "")
        if tool_name == "Agent":
            response = model_tier_hook.build_model_tier_response(event)
            return _merge_warning_into_response(response, warning_reason)
        if tool_name == "Bash":
            # gh_footer_hook runs first so the footer is fixed before ztk
            # wraps the command.  If ztk does not fire (absent binary or
            # compound command), the footer-fixed response is returned directly.
            _footer_rewrite: dict | None = None
            _footer_resp = gh_footer_hook.build_gh_footer_response(event)
            if _footer_resp.get("hookSpecificOutput"):
                _updated = _footer_resp["hookSpecificOutput"].get("updatedInput")
                if isinstance(_updated, dict):
                    event["tool_input"] = _updated  # let ztk see the fixed cmd
                    _footer_rewrite = _footer_resp
            response = ztk_hook.build_ztk_response(event)
            if response.get("hookSpecificOutput"):
                return _merge_warning_into_response(response, warning_reason)
            if _footer_rewrite is not None:
                return _merge_warning_into_response(_footer_rewrite, warning_reason)
            return _merge_warning_into_response(_passthrough(), warning_reason)
        if tool_name.startswith("mcp__github__"):
            # MCP GitHub body normalisation (create_pull_request, create_issue…).
            _mcp_resp = gh_footer_hook.build_gh_footer_response(event)
            if _mcp_resp.get("hookSpecificOutput"):
                return _merge_warning_into_response(_mcp_resp, warning_reason)

        base = _passthrough()
        return _merge_warning_into_response(base, warning_reason)
    except Exception:
        # Fail-open: a hook crash must never block a tool call.
        return _passthrough()


def main() -> None:
    """Entry point for ``python3 -m claude_mpm.hooks.pretooluse_dispatcher``.

    Reads a hook event from stdin, dispatches it, and prints the response.
    """
    try:
        event = json.load(sys.stdin)
        if not isinstance(event, dict):
            event = {}
    except Exception:
        print(json.dumps(_passthrough()))
        return

    print(json.dumps(dispatch(event)))


if __name__ == "__main__":
    main()
