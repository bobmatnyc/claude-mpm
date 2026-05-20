#!/usr/bin/env python3
"""Consolidated PostToolUse hook dispatcher.

Mirrors ``pretooluse_dispatcher`` for the PostToolUse event. Currently the
only concern wired in here is the experimental LLMLingua-2 output
compression hook (``llmlingua_hook``); future PostToolUse-time logic should
be added here rather than spawning new hook subprocesses per tool call.

The dispatcher is **additive**: when no opt-in PostToolUse concerns apply,
it returns the no-op ``{"continue": true}`` and Claude Code's main
``claude-hook`` handler (registered separately in settings.json) continues
to run as before. In particular, this dispatcher does NOT touch ZTK — ZTK
operates on the PreToolUse side and is unaffected.

Fail-open policy
----------------
Any unexpected error results in a ``{"continue": true}`` pass-through. A
hook crash must never corrupt a tool response.
"""

from __future__ import annotations

import json
import sys
from typing import Any

from claude_mpm.hooks import llmlingua_hook


def _passthrough() -> dict[str, Any]:
    """Return the no-op pass-through response."""
    return {"continue": True}


def dispatch(event: dict[str, Any]) -> dict[str, Any]:
    """Evaluate all PostToolUse concerns for one event.

    Returns a single wire-format response dict ready to be JSON-serialized.
    Never raises: any failure falls back to pass-through.
    """
    try:
        # LLMLingua-2 output compression (opt-in via CLAUDE_MPM_USE_LLMLINGUA=1).
        # The hook itself short-circuits to pass-through when the env var is
        # unset, so calling it unconditionally is safe and keeps the wiring
        # symmetric with how ZTK is wired into the PreToolUse dispatcher.
        response = llmlingua_hook.build_llmlingua_response(event)
        if response.get("hookSpecificOutput"):
            return response

        return _passthrough()
    except Exception:
        # Fail-open: a hook crash must never corrupt the tool response.
        return _passthrough()


def main() -> None:
    """Entry point for ``python3 -m claude_mpm.hooks.posttooluse_dispatcher``.

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
