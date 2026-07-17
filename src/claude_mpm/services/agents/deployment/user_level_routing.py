"""Deprecated user-level agent routing helpers (legacy).

.. deprecated::
    Fix A for issue #924 removed user-level agent routing.  All agents now
    deploy to project-local ``.claude/agents/``.  This module is retained only
    because migration and cleanup code still imports the predicate helpers
    below; :func:`skip_project_level_user_agent` is now a no-op that always
    returns ``False``.

Historically this module was the single chokepoint that stopped CORE agents
(members of ``USER_LEVEL_AGENTS``) from being written into a project's
``.claude/agents/`` directory and pruned stale project-level duplicates so the
shared ``~/.claude/agents/`` copies would win resolution.  That behaviour is
gone; agents are project-local everywhere now.

References
----------
SPEC-AGENTS-10~1 : docs/specs/agents.md#SPEC-AGENTS-10~1
"""

from __future__ import annotations

import logging
from pathlib import Path

from claude_mpm.utils.agent_filters import normalize_agent_id

_logger = logging.getLogger(__name__)


def _user_level_agents() -> frozenset[str]:
    """Return USER_LEVEL_AGENTS, imported lazily to avoid a circular import.

    WHAT: Fetches the canonical CORE-agent name set from ``agent_deployment``.
    WHY: ``agent_deployment`` imports many deployment sub-modules at load time,
    so importing it at module scope here would create an import cycle.
    """
    from claude_mpm.services.agents.deployment.agent_deployment import (
        USER_LEVEL_AGENTS,
    )

    return USER_LEVEL_AGENTS


def is_user_level_agent(agent_name: str) -> bool:
    """Return True when *agent_name* is a CORE agent that belongs at user level.

    .. deprecated::
        User-level agent routing was removed by Fix A for #924; this helper is
        retained only because migration/cleanup code still imports it.
    """
    return normalize_agent_id(agent_name) in _user_level_agents()


def user_level_agents_dir() -> Path:
    """Return the shared user-level agents directory (``~/.claude/agents``).

    .. deprecated::
        Legacy helper retained for migration/cleanup code; agents no longer
        deploy here (Fix A for #924).
    """
    return Path.home() / ".claude" / "agents"


def is_user_level_agents_dir(target_dir: Path) -> bool:
    """Return True when *target_dir* is the shared ``~/.claude/agents`` directory.

    .. deprecated::
        Legacy helper retained for migration/cleanup code (Fix A for #924).
    """
    try:
        return Path(target_dir).resolve() == user_level_agents_dir().resolve()
    except OSError:
        return False


def skip_project_level_user_agent(
    agent_name: str,
    target_dir: Path,
    logger: logging.Logger | None = None,
) -> bool:
    """Deprecated no-op guard; always returns ``False``.

    .. deprecated::
        User-level agent routing was removed by Fix A for #924.  This guard
        previously blocked CORE agents (``USER_LEVEL_AGENTS`` members) from being
        written into a project's ``.claude/agents/`` directory and pruned stale
        project-level duplicates.  All agents now deploy to project-local scope,
        so the guard never skips anything and always returns ``False``.

        The signature is preserved so existing call sites continue to work.
    """
    return False
