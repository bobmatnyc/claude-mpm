"""PreToolUse hook: rewrite Bash commands through `ztk run` for token compression.

ztk (https://github.com/codejunkie99/ztk) is a Zig binary that compresses shell
command output before it reaches Claude. Benchmarks show 80-97% token reduction
on common commands (git diff, ls, grep, pytest, etc.) with a 90.6% overall
reduction across a 256-command session.

This hook integrates ztk into claude-mpm's existing hook dispatcher rather than
running `ztk init -g` (which would conflict with our own hook setup).

Behavior:
- If `ztk` is in PATH AND tool is `Bash`: rewrite `command` to `ztk run <original>`
- If `ztk` is NOT in PATH: pass through unchanged (graceful degradation)
- Already-wrapped commands (already starting with `ztk `) are left alone
- Uses permissionDecision "allow" (transparent — users have already granted Bash perms)

Returns hookSpecificOutput with updatedInput to modify the Bash command parameter.
"""

import json
import os
import shutil
import sys


def _log_debug(message: str) -> None:
    """Write a debug line to stderr when CLAUDE_MPM_ZTK_DEBUG=1."""
    if os.environ.get("CLAUDE_MPM_ZTK_DEBUG") == "1":
        print(f"[ztk-hook] {message}", file=sys.stderr, flush=True)


def _passthrough() -> None:
    """Emit a continue response with no input modification."""
    print(json.dumps({"continue": True}))


def main() -> None:
    try:
        event = json.load(sys.stdin)
    except Exception as exc:
        _log_debug(f"failed to parse event JSON: {exc}")
        _passthrough()
        return

    tool_name = event.get("tool_name", "")
    tool_input = event.get("tool_input", {}) or {}

    # Only act on Bash tool calls
    if tool_name != "Bash":
        _passthrough()
        return

    command = tool_input.get("command", "")
    if not isinstance(command, str) or not command.strip():
        _passthrough()
        return

    # Idempotency: skip commands that are already wrapped
    stripped = command.lstrip()
    if stripped.startswith("ztk ") or stripped.startswith("ztk\t"):
        _log_debug("command already wrapped; skipping")
        _passthrough()
        return

    # Exclusions: skip commands that ztk blocks by default
    # Commands with ' -c ' (e.g., python3 -c, bash -c, sh -c, perl -e) are denied by ztk
    if " -c " in command or " -e " in command:
        _log_debug("command contains ' -c ' or ' -e '; ztk blocks these patterns")
        _passthrough()
        return

    # Skip multi-statement compound commands (contain newlines)
    if "\n" in command:
        _log_debug("command contains newlines; skipping multi-statement compound")
        _passthrough()
        return

    # Graceful degradation: ztk must be on PATH
    if shutil.which("ztk") is None:
        _log_debug("ztk not found on PATH; pass-through")
        _passthrough()
        return

    # Rewrite the command
    tool_input["command"] = f"ztk run {command}"
    _log_debug(f"rewrote Bash command: {command[:80]!r} -> ztk run ...")

    result = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "updatedInput": tool_input,
        }
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
