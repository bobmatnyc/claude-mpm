"""PreToolUse hook: rewrite Bash commands through `ztk run` for token compression.

ztk (https://github.com/codejunkie99/ztk, forked at https://github.com/bobmatnyc/ztk)
is a Zig binary that compresses shell command output before it reaches Claude.
Benchmarks show 80-97% token reduction on common commands (git diff, ls, grep,
pytest, etc.) with a 90.6% overall reduction across a 256-command session.

This hook integrates ztk into claude-mpm's existing hook dispatcher rather than
running `ztk init -g` (which would conflict with our own hook setup).

Behavior:
- Resolve ztk via `_resolve_ztk()`: prefers system PATH, falls back to bundled
  binary shipped in the wheel under `claude_mpm/bin/ztk`.
- If ztk is found AND tool is `Bash`: rewrite `command` to `<ztk> run <original>`
- If ztk is NOT found: pass through unchanged (graceful degradation)
- Already-wrapped commands are left alone (idempotency)
- Uses permissionDecision "allow" (transparent — users have already granted Bash perms)

Returns hookSpecificOutput with updatedInput to modify the Bash command parameter.
"""

import json
import os
import shutil
import stat
import sys
from datetime import UTC, datetime
from importlib import resources
from pathlib import Path

# ---------------------------------------------------------------------------
# Disable flag
# ---------------------------------------------------------------------------
# Set CLAUDE_MPM_DISABLE_ZTK=1 (or "true" / "yes") in the environment to skip
# ztk wrapping for the current session.  The hook is ON by default.
#
# Config-file disable (hooks.ztk.enabled: false in configuration.yaml) is
# intentionally NOT supported here: loading PyYAML in a subprocess hook that
# runs on every Bash call would add >10 ms of startup latency per invocation.
# Use the environment variable for persistent disabling (e.g. via shell profile
# or .env file).
_DISABLE_ENV_VAR = "CLAUDE_MPM_DISABLE_ZTK"
_MPM_LOG_DIR = Path.home() / ".claude-mpm"
_MPM_ZTK_LOG = _MPM_LOG_DIR / "ztk-savings.log"


def _log_debug(message: str) -> None:
    """Write a debug line to stderr when CLAUDE_MPM_ZTK_DEBUG=1."""
    if os.environ.get("CLAUDE_MPM_ZTK_DEBUG") == "1":
        print(f"[ztk-hook] {message}", file=sys.stderr, flush=True)


def _passthrough() -> None:
    """Emit a continue response with no input modification."""
    print(json.dumps({"continue": True}))


def _log_intercepted(command: str) -> None:
    """Append a rewritten-command entry to ~/.claude-mpm/ztk-savings.log.

    Format: ISO-timestamp | full command (truncated to 200 chars)

    WHY: ztk's native log (~/.local/share/ztk/savings.log) records only the
    base command name (e.g. "git"), not the full invocation. The MPM log
    captures the full command string so `claude-mpm ztk-stats` can show
    which exact invocations were compressed.
    Savings bytes/pct come from ztk's own log; this file is for audit/debug.
    """
    try:
        _MPM_LOG_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        # Truncate long commands so the log stays readable
        cmd_repr = command[:200].replace("\n", " ")
        line = f"{ts} | {cmd_repr}\n"
        with _MPM_ZTK_LOG.open("a") as fh:
            fh.write(line)
    except OSError as exc:
        _log_debug(f"failed to write MPM savings log: {exc}")


def _resolve_ztk() -> str | None:
    """Resolve the ztk executable path.

    Resolution order:
    1. System PATH (`shutil.which("ztk")`) — user's install takes precedence
    2. Bundled binary at `claude_mpm/bin/ztk` (chmod +x if needed)

    Returns absolute path string, or None if neither is available.
    """
    # 1. System install
    system_ztk = shutil.which("ztk")
    if system_ztk:
        _log_debug(f"using system ztk: {system_ztk}")
        return system_ztk

    # 2. Bundled binary via importlib.resources
    try:
        bundled = resources.files("claude_mpm").joinpath("bin", "ztk")
        # `files()` returns a Traversable; for filesystem-based packages this is
        # a concrete path. Coerce via str() and confirm existence.
        bundled_path = Path(str(bundled))
        if bundled_path.is_file():
            # Ensure executable bit is set (wheels can lose it)
            mode = bundled_path.stat().st_mode
            if not mode & stat.S_IXUSR:
                try:
                    bundled_path.chmod(
                        mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
                    )
                    _log_debug(f"chmod +x applied to {bundled_path}")
                except OSError as exc:
                    _log_debug(f"failed to chmod bundled ztk: {exc}")
                    return None
            _log_debug(f"using bundled ztk: {bundled_path}")
            return str(bundled_path)
    except (ModuleNotFoundError, FileNotFoundError, AttributeError) as exc:
        _log_debug(f"bundled ztk not available: {exc}")

    return None


def main() -> None:
    # Environment-variable disable: fast, session-level override.
    if os.environ.get(_DISABLE_ENV_VAR, "").lower() in ("1", "true", "yes"):
        _log_debug(f"{_DISABLE_ENV_VAR} is set; ztk disabled")
        _passthrough()
        return

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

    # Graceful degradation: ztk must be resolvable
    ztk_path = _resolve_ztk()
    if ztk_path is None:
        _log_debug("ztk not found (system or bundled); pass-through")
        _passthrough()
        return

    # Rewrite the command using the resolved ztk path
    tool_input["command"] = f"{ztk_path} run {command}"
    _log_debug(f"rewrote Bash command: {command[:80]!r} -> {ztk_path} run ...")
    _log_intercepted(command)

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
