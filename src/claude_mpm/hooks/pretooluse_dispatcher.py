#!/usr/bin/env python3
"""Consolidated PreToolUse + PermissionRequest hook dispatcher.

This module replaces four separate hook subprocesses that previously fired on
every PreToolUse event:

* ``model_tier_hook``       — injects a model tier into ``Agent`` tool calls.
* ``ztk_hook``              — rewrites ``Bash`` commands through ztk compression.
* ``context_circuit_breaker`` — denies all tool calls when context >= 95%.
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
3. For ``PreToolUse``: run the context circuit breaker FIRST.  If it denies,
   emit the deny response immediately and stop — no point rewriting a call
   that is about to be blocked.
4. Branch on ``tool_name``:
   * ``Agent`` -> model tier injection.
   * ``Bash``  -> ztk rewrite.
   * anything else -> ``{"continue": true}``.

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
    destructive_op_guard,
    model_tier_hook,
    ztk_hook,
)


def _passthrough() -> dict[str, Any]:
    """Return the no-op pass-through response."""
    return {"continue": True}


def _circuit_breaker_deny_response(decision: dict[str, Any]) -> dict[str, Any]:
    """Wrap a circuit-breaker deny decision in the PreToolUse wire format."""
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": decision.get("permissionDecisionReason", ""),
        }
    }


def dispatch(event: dict[str, Any]) -> dict[str, Any]:
    """Evaluate all PreToolUse / PermissionRequest concerns for one event.

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

        # Context circuit breaker runs first: if context is critical, deny the
        # call outright before doing any model/ztk rewriting.
        breaker_decision = context_circuit_breaker.evaluate(event)
        if breaker_decision.get("permissionDecision") == "deny":
            return _circuit_breaker_deny_response(breaker_decision)

        # Branch on the tool being invoked.
        tool_name = event.get("tool_name", "")
        if tool_name == "Agent":
            return model_tier_hook.build_model_tier_response(event)
        if tool_name == "Bash":
            # Destructive-op guard runs before ztk rewriting: deny irreversible
            # git/file operations (issue #420 Phase 1) rather than rewrite them.
            guard_decision = destructive_op_guard.evaluate(event)
            if guard_decision.get("permissionDecision") == "deny":
                return _circuit_breaker_deny_response(guard_decision)
            return ztk_hook.build_ztk_response(event)

        return _passthrough()
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
