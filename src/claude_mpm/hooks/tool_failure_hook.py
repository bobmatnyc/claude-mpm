#!/usr/bin/env python3
"""PostToolUseFailure hook handler.

This module is referenced from ``.claude/settings.json`` for the
``PostToolUseFailure`` event. It is a lightweight, non-blocking logger:
it records each tool failure as a structured JSON line so the failures can
be inspected later for debugging.

The ``PostToolUseFailure`` event cannot block execution, so this handler
always emits ``{"continue": true}`` and never raises — a crash here would
be noise in the Claude Code session for no benefit.
"""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

# Append-only JSONL log of tool failures.
_LOG_PATH = Path.home() / ".claude-mpm" / "logs" / "tool_failures.jsonl"


def _build_entry(event: dict) -> dict:
    """Extract the relevant failure fields from a hook event payload.

    Tolerates missing keys: any field absent from the payload is recorded
    as ``None`` rather than raising.
    """
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "tool_name": event.get("tool_name"),
        "error": event.get("error") or event.get("error_message"),
        "exit_code": event.get("exit_code"),
        "cwd": event.get("cwd") or str(Path.cwd()),
    }


def _append_entry(entry: dict) -> None:
    """Append a single JSON line to the failures log.

    Creates the parent directory and file if they do not exist. Any I/O
    error is swallowed — logging failures must never break the session.
    """
    try:
        _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def main() -> None:
    """Read a failure event from stdin, log it, and emit a continue signal."""
    import select as _select

    # Guard the stdin read with select: json.load blocks until EOF, so a pipe
    # that is never cleanly closed would hang until the Claude Code hook
    # timeout. If no data is ready within the window, continue gracefully.
    if sys.stdin.isatty() or not _select.select([sys.stdin], [], [], 2.0)[0]:
        print(json.dumps({"continue": True}), flush=True)
        sys.exit(0)

    try:
        event = json.load(sys.stdin)
        if not isinstance(event, dict):
            event = {}
    except Exception:
        # Malformed or missing stdin — log nothing, but still continue.
        event = {}

    if event:
        _append_entry(_build_entry(event))

    print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
