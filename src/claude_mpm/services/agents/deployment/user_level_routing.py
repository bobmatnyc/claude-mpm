"""Project-level deployment guard for USER_LEVEL_AGENTS (CORE agents).

WHAT: Single chokepoint predicate that stops CORE agents (members of
``USER_LEVEL_AGENTS``) from being written into a project's ``.claude/agents/``
directory, and self-heals by pruning any stale project-level duplicate left
over from an earlier routing bug.

WHY: Several deployment code paths write agent files, but historically only the
canonical :meth:`AgentDeploymentService.deploy_agents` applied USER_LEVEL_AGENTS
routing.  The other paths silently re-created project-level copies of CORE
agents, which shadow the shared ``~/.claude/agents/`` copies (project always
wins over user in resolution order) and bloat every session's context with
duplicate definitions that will never be selected.  Centralising the decision
here guarantees every write path behaves identically.

References
----------
SPEC-AGENTS-10~1 : docs/specs/agents.md#SPEC-AGENTS-10~1
"""

from __future__ import annotations

import logging
from pathlib import Path

from claude_mpm.services.agents.deployment_utils import normalize_deployment_filename
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
    """Return True when *agent_name* is a CORE agent that belongs at user level."""
    return normalize_agent_id(agent_name) in _user_level_agents()


def user_level_agents_dir() -> Path:
    """Return the shared user-level agents directory (``~/.claude/agents``)."""
    return Path.home() / ".claude" / "agents"


def is_user_level_agents_dir(target_dir: Path) -> bool:
    """Return True when *target_dir* is the shared ``~/.claude/agents`` directory."""
    try:
        return Path(target_dir).resolve() == user_level_agents_dir().resolve()
    except OSError:
        return False


def skip_project_level_user_agent(
    agent_name: str,
    target_dir: Path,
    logger: logging.Logger | None = None,
) -> bool:
    """Guard a project-level write of a CORE agent and self-heal stale copies.

    WHAT: Returns ``True`` when *agent_name* is a ``USER_LEVEL_AGENTS`` member and
    *target_dir* is a project-level ``.claude/agents/`` directory (i.e. NOT the
    shared ``~/.claude/agents``); in that case any stale project-level file for
    the agent is deleted before returning so callers skip the write.  Returns
    ``False`` for non-CORE agents and for writes targeting the shared user-level
    directory, which are always allowed.

    WHY: CORE agents must live only at ``~/.claude/agents``.  Every deployment
    path calls this before writing so no path can re-introduce a project-level
    duplicate, and existing leftovers are cleaned up automatically on next deploy.
    The shared ``~/.claude/agents`` directory is never modified here.

    :spec: SPEC-AGENTS-10~1
    """
    if not is_user_level_agent(agent_name):
        return False

    target_dir = Path(target_dir)
    if is_user_level_agents_dir(target_dir):
        return False

    log = logger or _logger

    # Self-heal: prune leftover project-level duplicate(s).  Cover the normalized
    # dash-based filename plus the raw stem so historical variants are removed.
    candidates = {
        normalize_deployment_filename(f"{agent_name}.md"),
        f"{normalize_agent_id(agent_name)}.md",
        f"{agent_name}.md",
    }
    for filename in candidates:
        stale = target_dir / filename
        try:
            if stale.is_file():
                stale.unlink()
                log.info(
                    "Removed stale project-level CORE agent %s (belongs at %s)",
                    stale,
                    user_level_agents_dir(),
                )
        except OSError as exc:  # pragma: no cover - defensive
            log.debug("Could not remove stale project agent %s: %s", stale, exc)

    return True
