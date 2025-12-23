"""
Agent filtering utilities for claude-mpm.

WHY: This module provides centralized filtering logic to remove non-deployable
agents (BASE_AGENT) and already-deployed agents from user-facing displays.

ARCHITECTURE:
- SOURCE: ~/.claude-mpm/cache/agents/ (git repository cache)
- DEPLOYMENT: .claude/agents/ (project-level deployment location)

DESIGN DECISIONS:
- BASE_AGENT is a build tool, not a deployable agent - filter everywhere
- Deployed agent detection checks .claude/agents/ for all deployed agents
- Supports both virtual (.mpm_deployment_state) and physical (.md files) detection
- Case-insensitive BASE_AGENT detection for robustness
- Pure functions for easy testing and reuse

IMPLEMENTATION NOTES:
- Related to ticket 1M-502 Phase 1: UX improvements for agent filtering
- Addresses user confusion from seeing BASE_AGENT and deployed agents in lists
"""

from pathlib import Path
from typing import Dict, List, Optional, Set


def is_base_agent(agent_id: str) -> bool:
    """Check if agent is BASE_AGENT (build tool, not deployable).

    BASE_AGENT is an internal build tool used to construct other agents.
    It should never appear in user-facing agent lists or deployment menus.

    Args:
        agent_id: Agent identifier to check (may include path like "qa/BASE-AGENT")

    Returns:
        True if agent is BASE_AGENT (case-insensitive), False otherwise

    Examples:
        >>> is_base_agent("BASE_AGENT")
        True
        >>> is_base_agent("base-agent")
        True
        >>> is_base_agent("qa/BASE-AGENT")
        True
        >>> is_base_agent("ENGINEER")
        False
    """
    if not agent_id:
        return False

    # Extract filename from path (handle cases like "qa/BASE-AGENT")
    # 1M-502: Remote agents may have path prefixes like "qa/", "pm/", etc.
    agent_name = agent_id.split("/")[-1]

    normalized_id = agent_name.lower().replace("-", "").replace("_", "")
    return normalized_id == "baseagent"


def filter_base_agents(agents: List[Dict]) -> List[Dict]:
    """Remove BASE_AGENT from agent list.

    Filters out any agent with agent_id matching BASE_AGENT (case-insensitive).
    This prevents users from seeing or selecting the internal build tool.

    Args:
        agents: List of agent dictionaries, each containing at least 'agent_id' key

    Returns:
        Filtered list with BASE_AGENT removed

    Examples:
        >>> agents = [
        ...     {"agent_id": "ENGINEER", "name": "Engineer"},
        ...     {"agent_id": "BASE_AGENT", "name": "Base Agent"},
        ...     {"agent_id": "PM", "name": "PM"}
        ... ]
        >>> filtered = filter_base_agents(agents)
        >>> len(filtered)
        2
        >>> "BASE_AGENT" in [a["agent_id"] for a in filtered]
        False
    """
    return [a for a in agents if not is_base_agent(a.get("agent_id", ""))]


def get_deployed_agent_ids(project_dir: Optional[Path] = None) -> Set[str]:
    """Get set of currently deployed agent IDs.

    Checks virtual deployment state (.mpm_deployment_state) first, then falls back
    to physical .md files for backward compatibility. This ensures agents are detected
    whether deployed virtually or as physical files.

    Args:
        project_dir: Project directory to check, defaults to current working directory

    Returns:
        Set of deployed agent IDs (leaf names like "python-engineer", "qa")

    Examples:
        >>> deployed = get_deployed_agent_ids()
        >>> "python-engineer" in deployed  # If agent exists in deployment state
        True
        >>> "ENGINEER" in deployed  # If ENGINEER.md exists
        True

    Design Rationale:
        - Primary detection: Virtual deployment state (.mpm_deployment_state)
        - Fallback detection: Physical .md files in .claude/agents/
        - Returns leaf names for consistent comparison with agent_id formats
        - Combines both detection methods for complete coverage
        - Graceful error handling for malformed or missing state files
        - Only checks project-level deployment (simplified architecture)

    Related:
        - Fixes checkbox interface showing all agents as "○ [Available]" instead of "● [Installed]"
        - Matches detection logic from _is_agent_deployed() in agent_state_manager.py
        - Related to ticket 1M-502: Virtual deployment state detection
    """
    deployed = set()

    # Track if project_dir was explicitly provided

    if project_dir is None:
        project_dir = Path.cwd()

    # NEW: Check virtual deployment state (primary method)
    # This is the current deployment model used by Claude Code
    # Only checking project-level deployment in simplified architecture
    deployment_state_paths = [
        project_dir / ".claude" / "agents" / ".mpm_deployment_state",
    ]

    for state_path in deployment_state_paths:
        if state_path.exists():
            try:
                import json

                with state_path.open() as f:
                    state = json.load(f)

                # Extract agent IDs from deployment state
                # Agent IDs are leaf names (e.g., "python-engineer", "qa")
                agents = state.get("last_check_results", {}).get("agents", {})
                deployed.update(agents.keys())

            except (json.JSONDecodeError, KeyError) as e:
                # Log error but continue - don't break if state file is malformed
                import logging

                logger = logging.getLogger(__name__)
                logger.debug(f"Failed to read deployment state from {state_path}: {e}")
                continue
            except Exception as e:
                # Catch unexpected errors - fail gracefully
                import logging

                logger = logging.getLogger(__name__)
                logger.debug(f"Unexpected error reading deployment state: {e}")
                continue

    # EXISTING: Check physical .md files (fallback for backward compatibility)
    # Check project deployment location (.claude/agents/)
    agents_dir = project_dir / ".claude" / "agents"
    if agents_dir.exists():
        for file in agents_dir.glob("*.md"):
            if file.stem not in {"BASE-AGENT", ".DS_Store"}:
                deployed.add(file.stem)

    # NOTE: .claude/templates/ contains PM instruction templates, NOT deployed agents
    # It should NOT be checked here. Agents are deployed to:
    # - .mpm_deployment_state (virtual deployment)
    # - .claude/agents/*.md (project deployment)

    return deployed


def filter_deployed_agents(
    agents: List[Dict], project_dir: Optional[Path] = None
) -> List[Dict]:
    """Remove already-deployed agents from list.

    Filters agent list to show only agents that are not currently deployed.
    This prevents users from attempting to re-deploy existing agents and
    reduces confusion in deployment menus.

    Args:
        agents: List of agent dictionaries, each containing at least 'agent_id' key
        project_dir: Project directory to check, defaults to current working directory

    Returns:
        Filtered list containing only non-deployed agents

    Examples:
        >>> agents = [
        ...     {"agent_id": "ENGINEER", "name": "Engineer"},
        ...     {"agent_id": "PM", "name": "PM"},
        ...     {"agent_id": "QA", "name": "QA"}
        ... ]
        >>> # Assuming ENGINEER is deployed
        >>> filtered = filter_deployed_agents(agents)
        >>> "ENGINEER" not in [a["agent_id"] for a in filtered]
        True

    Design Rationale:
        - Checks filesystem for actual deployed files (source of truth)
        - Supports both new and legacy agent directory structures
        - Preserves agent order for consistent UX
    """
    deployed_ids = get_deployed_agent_ids(project_dir)
    return [a for a in agents if a.get("agent_id") not in deployed_ids]


def apply_all_filters(
    agents: List[Dict],
    project_dir: Optional[Path] = None,
    filter_base: bool = True,
    filter_deployed: bool = False,
) -> List[Dict]:
    """Apply multiple filters to agent list in correct order.

    Convenience function to apply common filtering combinations. Filters are
    applied in this order:
    1. BASE_AGENT filtering (if enabled)
    2. Deployed agent filtering (if enabled)

    Args:
        agents: List of agent dictionaries to filter
        project_dir: Project directory for deployment checks
        filter_base: Remove BASE_AGENT from list (default: True)
        filter_deployed: Remove deployed agents from list (default: False)

    Returns:
        Filtered agent list

    Examples:
        >>> agents = get_all_agents()
        >>> # For display/info purposes - remove only BASE_AGENT
        >>> filtered = apply_all_filters(
        ...     agents, filter_base=True, filter_deployed=False
        ... )
        >>> # For deployment menus - remove BASE_AGENT and deployed agents
        >>> deployable = apply_all_filters(
        ...     agents, filter_base=True, filter_deployed=True
        ... )

    Usage Guidelines:
        - Use filter_base=True (default) for all user-facing displays
        - Use filter_deployed=True when showing deployment options
        - Use filter_deployed=False when showing all available agents
          (info/list commands)
    """
    result = agents

    if filter_base:
        result = filter_base_agents(result)

    if filter_deployed:
        result = filter_deployed_agents(result, project_dir)

    return result
