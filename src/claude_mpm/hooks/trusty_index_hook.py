"""PostToolUse hook: re-index modified files in trusty-search.

Fires after Write/Edit/MultiEdit/NotebookEdit tool calls. Extracts the file
path from the tool input and asynchronously runs ``trusty-search index-file
<path>`` so the local trusty-search daemon picks up the change without
requiring a full reindex.

Design constraints:
- Never blocks Claude Code. The reindex is fire-and-forget via ``Popen``.
- Tolerates missing/empty stdin (e.g. when invoked manually for testing) by
  guarding the read with ``select``.
- Silently no-ops if ``trusty-search`` is not installed.
- Always emits ``{"continue": true}`` — a crash here would be noise.
"""

from __future__ import annotations

import json
import select
import subprocess  # nosec B404
import sys
from pathlib import Path

# Tools that produce file modifications worth re-indexing.
_MODIFYING_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}


def _read_event() -> dict:
    """Read the hook event JSON from stdin, tolerating empty/missing input.

    Returns an empty dict if stdin is a TTY, has no data within 2 seconds,
    or contains malformed JSON. Never raises.
    """
    if sys.stdin.isatty() or not select.select([sys.stdin], [], [], 2.0)[0]:
        return {}
    try:
        data = json.load(sys.stdin)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _extract_file_path(event: dict) -> str | None:
    """Pull the file path out of a PostToolUse event payload.

    Different tools nest the path under different keys; check the common
    ones. Returns None if nothing usable is found.
    """
    tool_input = event.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return None
    for key in ("file_path", "path", "notebook_path"):
        value = tool_input.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _trigger_reindex(file_path: str) -> None:
    """Fire-and-forget ``trusty-search index-file`` for the modified path.

    Suppresses all output so we never pollute Claude's hook channel. Silently
    no-ops if trusty-search is not installed.
    """
    try:
        subprocess.Popen(  # nosec B603 B607
            ["trusty-search", "index-file", file_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
        )
    except (FileNotFoundError, OSError):
        # trusty-search not installed or unable to spawn — silently skip.
        pass


def main() -> None:
    """Entry point. Always exits 0 with a continue signal."""
    event = _read_event()
    tool_name = event.get("tool_name", "")

    if tool_name in _MODIFYING_TOOLS:
        file_path = _extract_file_path(event)
        if file_path:
            # Resolve to absolute path so the daemon doesn't depend on its
            # own cwd matching Claude's.
            try:
                file_path = str(Path(file_path).resolve())
            except (OSError, RuntimeError):
                pass  # Use as-is if resolve fails.
            _trigger_reindex(file_path)

    print(json.dumps({"continue": True}), flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
