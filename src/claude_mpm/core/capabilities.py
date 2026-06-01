"""Shared capability-detection helpers for Claude MPM.

This module provides a single, cheap, side-effect-free surface for querying
runtime capabilities that affect MPM behaviour.  All checks are environment-
variable reads so they are suitable for use in hooks, startup code, and hot
paths without adding latency.

Design constraints
------------------
* **No heavy imports** — importing this module must not pull in the full MPM
  stack.  Pure stdlib only.
* **No side effects** — every function is a pure read; no caching state, no
  network calls, no file I/O.
* **Feature-neutral** — callers should adapt gracefully to the detected value
  rather than hard-coding Agent-Teams-only instructions.

PreToolUse input modification
-----------------------------
``supports_pretool_modify()`` checks whether the running Claude Code version
supports the ``updatedInput`` field in ``hookSpecificOutput`` for PreToolUse
hooks.  This feature was added in Claude Code v2.0.30.

The check delegates to ``HookInstaller.supports_pretool_modify()`` when that
class is importable (full install) and falls back to a lightweight
``claude --version`` subprocess for minimal or hook-only environments.  In
both cases the result is **not cached here** — callers that need caching
should cache it themselves or rely on ``HookInstaller``'s own instance cache.
"""

from __future__ import annotations

import os

__all__ = ["agent_teams_active", "supports_pretool_modify"]

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_TRUTHY_VALUES: frozenset[str] = frozenset({"1", "true", "yes", "on"})

# Minimum Claude Code version required for PreToolUse input modification.
# Kept in sync with HookInstaller.MIN_PRETOOL_MODIFY_VERSION.
_MIN_PRETOOL_MODIFY_VERSION = "2.0.30"


def _env_truthy(name: str) -> bool:
    """Return True if *name* is set to a truthy value in the environment.

    Recognised truthy strings (case-insensitive): ``1``, ``true``, ``yes``,
    ``on``.  An unset or empty variable returns False.
    """
    raw = os.environ.get(name, "")
    return raw.strip().lower() in _TRUTHY_VALUES


def _version_meets_minimum(version: str, min_version: str) -> bool:
    """Return True iff *version* >= *min_version* (both dotted-decimal strings)."""

    def parse(v: str) -> list[int]:
        try:
            return [int(x) for x in v.split(".")]
        except (ValueError, AttributeError):
            return [0]

    curr = parse(version)
    req = parse(min_version)
    for i in range(max(len(curr), len(req))):
        c = curr[i] if i < len(curr) else 0
        r = req[i] if i < len(req) else 0
        if c < r:
            return False
        if c > r:
            return True
    return True


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def agent_teams_active() -> bool:
    """Return True iff Claude Code Agent Teams mode is currently active.

    The primary signal is the environment variable
    ``CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS``.  Recognised truthy values:
    ``1``, ``true``, ``yes``, ``on`` (case-insensitive).

    When the variable is unset or empty this function returns ``False``,
    preserving the default (non-Teams) experience.

    This function is intentionally cheap — it performs only an environment
    lookup and a string comparison.  It is safe to call in hot paths such as
    hook handlers.

    Examples
    --------
    >>> import os
    >>> os.environ.pop("CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS", None)
    >>> from claude_mpm.core.capabilities import agent_teams_active
    >>> agent_teams_active()
    False
    >>> os.environ["CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"] = "1"
    >>> agent_teams_active()
    True
    """
    return _env_truthy("CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS")


def supports_pretool_modify() -> bool:
    """Return True iff the running Claude Code supports PreToolUse input modification.

    PreToolUse input modification (``updatedInput`` inside
    ``hookSpecificOutput``) was added in Claude Code **v2.0.30**.  Hooks that
    inject data via this mechanism must skip injection on older versions to
    avoid silent failures or "Invalid key" warnings.

    Detection order
    ---------------
    1. Try ``HookInstaller.supports_pretool_modify()`` — uses the installer's
       own cached ``claude --version`` result (preferred, no extra subprocess).
    2. Fall back to a direct ``claude --version`` subprocess when the full
       installer cannot be imported (minimal / hook-only environments).
    3. Return ``False`` conservatively when the version cannot be determined.

    This function is safe to call in hook hot-paths; the installer caches the
    version after the first subprocess call so subsequent calls are cheap.

    Returns
    -------
    bool
        ``True`` if injection is supported, ``False`` otherwise.
    """
    # Fast path: try the installer which already caches the version.
    try:
        from claude_mpm.hooks.claude_hooks.installer import (
            HookInstaller,
        )

        installer = HookInstaller()
        return installer.supports_pretool_modify()
    except Exception:
        pass

    # Fallback: run claude --version directly.
    import re
    import subprocess

    try:
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        output = (result.stdout or result.stderr).strip()
        match = re.search(r"([\d]+\.[\d]+\.[\d]+)", output)
        if not match:
            return False
        return _version_meets_minimum(match.group(1), _MIN_PRETOOL_MODIFY_VERSION)
    except Exception:
        return False
