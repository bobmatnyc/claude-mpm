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
"""

from __future__ import annotations

import os

__all__ = ["agent_teams_active"]

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_TRUTHY_VALUES: frozenset[str] = frozenset({"1", "true", "yes", "on"})


def _env_truthy(name: str) -> bool:
    """Return True if *name* is set to a truthy value in the environment.

    Recognised truthy strings (case-insensitive): ``1``, ``true``, ``yes``,
    ``on``.  An unset or empty variable returns False.
    """
    raw = os.environ.get(name, "")
    return raw.strip().lower() in _TRUTHY_VALUES


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
