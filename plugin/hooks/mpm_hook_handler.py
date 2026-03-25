#!/usr/bin/env python3
"""Thin wrapper that delegates hook events to the installed claude-hook binary.

This script is designed to be FULLY SELF-CONTAINED: it does NOT import anything
from the claude_mpm package.  It may run before ``pip install claude-mpm`` has
happened (install-plugin-first, pip-later flow), so every dependency is from
the Python standard library only.

Architecture:
    Claude Code  -->  this script  -->  claude-hook (installed binary)
                                   -->  OR: python -m claude_mpm.hooks.claude_hooks.hook_handler

Data flow:
    1. Claude Code passes hook event JSON on stdin.
    2. This script reads stdin once and stores it.
    3. It locates the ``claude-hook`` binary (or falls back to ``python -m``).
    4. It invokes the real handler, piping the stored stdin data through.
    5. It relays the handler's stdout back to Claude Code.
    6. On ANY failure it returns ``{"continue": true}`` so Claude Code is never
       blocked.

Environment:
    CLAUDE_HOOK_EVENT  - Hook event type (set by Claude Code or passed as argv[1]).
    CLAUDE_MPM_HOOK_DEBUG - If "true", logs debug info to stderr.

Stdout is RESERVED for the JSON response to Claude Code.  All diagnostic
output goes to stderr.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SAFE_RESPONSE = json.dumps({"continue": True})

DEBUG = os.environ.get("CLAUDE_MPM_HOOK_DEBUG", "").lower() == "true"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _debug(msg: str) -> None:
    """Write a debug message to stderr (never stdout)."""
    if DEBUG:
        print(f"[mpm-plugin-hook] {msg}", file=sys.stderr)


def _find_claude_hook() -> list[str] | None:
    """Locate the claude-hook binary or an equivalent invocation.

    Returns a list of command tokens (suitable for subprocess) or None.

    Search order:
        1. ``claude-hook`` on PATH  (pip / pipx / uv tool install)
        2. ``~/.local/bin/claude-hook``  (pip install --user)
        3. User-site bin directory
        4. ``python3 -m claude_mpm.hooks.claude_hooks.hook_handler``  (module)
    """
    # 1. shutil.which -- covers PATH, venvs, pipx, uv tools
    which_result = shutil.which("claude-hook")
    if which_result:
        _debug(f"Found claude-hook via which: {which_result}")
        return [which_result]

    # 2. Common user-local location
    user_local = Path.home() / ".local" / "bin" / "claude-hook"
    if user_local.is_file() and os.access(str(user_local), os.X_OK):
        _debug(f"Found claude-hook at user-local: {user_local}")
        return [str(user_local)]

    # 3. Python user-site bin (``python3 -m site --user-base`` / bin)
    try:
        import site

        user_base = site.getusersitepackages()
        # user_base is the site-packages dir; go up one level to get the prefix
        user_bin = Path(user_base).parent.parent / "bin" / "claude-hook"
        if user_bin.is_file() and os.access(str(user_bin), os.X_OK):
            _debug(f"Found claude-hook at user-site: {user_bin}")
            return [str(user_bin)]
    except Exception:
        pass

    # 4. Try running as a Python module
    python = shutil.which("python3") or shutil.which("python")
    if python:
        try:
            check = subprocess.run(
                [python, "-c", "import claude_mpm"],
                check=False,
                capture_output=True,
                timeout=5,
            )
            if check.returncode == 0:
                _debug(f"Found claude_mpm module via {python}")
                return [
                    python,
                    "-W",
                    "ignore::RuntimeWarning",
                    "-m",
                    "claude_mpm.hooks.claude_hooks.hook_handler",
                ]
        except Exception:
            pass

    _debug("claude-hook not found anywhere")
    return None


def _run_handler(cmd: list[str], stdin_data: bytes, event_type: str) -> str:
    """Run the real hook handler and return its stdout."""
    env = os.environ.copy()
    env["CLAUDE_HOOK_EVENT"] = event_type

    result = subprocess.run(
        cmd,
        check=False,
        input=stdin_data,
        capture_output=True,
        timeout=55,  # Leave 5s margin below the 60s hook timeout
        env=env,
    )

    stdout = result.stdout.decode("utf-8", errors="replace").strip()
    stderr = result.stderr.decode("utf-8", errors="replace").strip()

    if stderr:
        _debug(f"Handler stderr: {stderr[:500]}")

    if result.returncode != 0:
        _debug(f"Handler exited with code {result.returncode}")
        # If handler produced valid JSON before failing, use it
        if stdout:
            try:
                json.loads(stdout)
                return stdout
            except json.JSONDecodeError:
                pass
        return SAFE_RESPONSE

    return stdout if stdout else SAFE_RESPONSE


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Read hook event from stdin, delegate to claude-hook, relay response."""
    try:
        # Determine event type from argv or environment
        event_type = "Unknown"
        if len(sys.argv) > 1:
            event_type = sys.argv[1]
        elif "CLAUDE_HOOK_EVENT" in os.environ:
            event_type = os.environ["CLAUDE_HOOK_EVENT"]

        _debug(f"Hook event: {event_type}")

        # Read all of stdin (Claude Code sends JSON here)
        stdin_data = sys.stdin.buffer.read()
        _debug(f"Received {len(stdin_data)} bytes on stdin")

        # Find the real handler
        cmd = _find_claude_hook()

        if cmd is None:
            # claude-mpm is not installed -- return a continue response with
            # a gentle nudge to install.
            _debug("claude-mpm not installed, returning continue with message")
            response = {
                "continue": True,
                "message": (
                    "claude-mpm hook handler not found. "
                    "Install with: pip install claude-mpm  "
                    "(or: uv tool install claude-mpm)"
                ),
            }
            print(json.dumps(response))
            return

        # Delegate to the real handler
        _debug(f"Delegating to: {' '.join(cmd)}")
        output = _run_handler(cmd, stdin_data, event_type)

        # Validate JSON before printing
        try:
            json.loads(output)
            print(output)
        except json.JSONDecodeError:
            _debug(f"Handler returned invalid JSON: {output[:200]}")
            print(SAFE_RESPONSE)

    except subprocess.TimeoutExpired:
        _debug("Handler timed out")
        print(SAFE_RESPONSE)
    except Exception as exc:
        _debug(f"Unexpected error: {exc}")
        print(SAFE_RESPONSE)


if __name__ == "__main__":
    main()
