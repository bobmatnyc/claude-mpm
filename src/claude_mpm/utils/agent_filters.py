"""
Agent filtering utilities for claude-mpm.

WHY: This module provides centralized filtering logic to remove non-deployable
agents (BASE_AGENT and BASE-* composition templates) and already-deployed agents
from user-facing displays.  It also exposes the ``local_only`` allow-list
helpers used to protect project-managed agents from MPM sync/cleanup.

ARCHITECTURE:
- SOURCE: ~/.claude-mpm/cache/agents/ (git repository cache)
- DEPLOYMENT: .claude/agents/ (project-level deployment location)

DESIGN DECISIONS:
- BASE_AGENT / BASE-* files are composition templates, not deployable agents
- ``is_base_template`` is the SINGLE predicate for all BASE-file guards
- ``is_base_agent`` is preserved for backward compatibility (delegates to
  ``is_base_template`` for the single-agent case)
- Deployed agent detection checks .claude/agents/ for all deployed agents
- Supports both virtual (.mpm_deployment_state) and physical (.md files) detection
- Case-insensitive BASE-* detection for robustness
- Pure functions for easy testing and reuse

TERMINOLOGY:
- ``local_only`` agents are committed to the project git repo; "local_only"
  means MPM-unmanaged, not git-ignored. These agents live in
  ``.claude/agents/`` and should be tracked in git, but MPM sync/cleanup
  must never delete or overwrite them.

IMPLEMENTATION NOTES:
- Related to ticket 1M-502 Phase 1: UX improvements for agent filtering
- Addresses user confusion from seeing BASE_AGENT and deployed agents in lists
- BASE-* template exclusion: fixes parse errors for BASE-ENGINEER, BASE-QA, etc.
"""

from pathlib import Path


def is_base_template(filename: str) -> bool:
    """Return True when *filename* is a BASE composition template.

    BASE templates (``BASE-*.md`` and ``BASE_*.md``) are composition
    ingredients composed INTO agents by the assembly pipeline.  They are
    NOT stand-alone agents and must never be deployed to ``~/.claude/agents/``
    or ``.claude/agents/``, nor parsed by the agent discovery/loading code.

    The check is case-insensitive on the ``BASE`` prefix so that both
    ``BASE-AGENT.md`` and ``base-engineer.md`` are caught uniformly.

    WHY: Centralises the exclusion predicate in one place so every
    deployment / discovery callsite imports the same guard rather than
    duplicating ad-hoc string checks.

    WHAT: Strips any leading path components, then tests whether the
    bare filename starts with ``base-`` or ``base_`` (case-insensitive).
    The file extension is irrelevant — the guard fires on ``.md``,
    ``.yaml``, or no extension alike.

    TEST: Assert ``is_base_template("BASE-AGENT.md")`` is True,
    ``is_base_template("BASE_ENGINEER.md")`` is True,
    ``is_base_template("base-research.md")`` is True,
    ``is_base_template("engineer.md")`` is False,
    ``is_base_template("code-critic.md")`` is False.

    Args:
        filename: Bare filename *or* full path string.  Only the last
            path component is tested.

    Returns:
        ``True`` if the file is a BASE composition template; ``False``
        otherwise.

    Examples:
        >>> is_base_template("BASE-AGENT.md")
        True
        >>> is_base_template("BASE_ENGINEER.md")
        True
        >>> is_base_template("base-qa.md")
        True
        >>> is_base_template("/some/path/BASE-OPS.md")
        True
        >>> is_base_template("engineer.md")
        False
        >>> is_base_template("code-critic.md")
        False
    """
    if not filename:
        return False
    # Use only the bare filename so callers can pass full paths too.
    basename = Path(filename).name
    lower = basename.lower()
    return lower.startswith("base-") or lower.startswith("base_")


def is_base_agent(agent_id: str) -> bool:
    """Check if agent is a BASE composition template (build tool, not deployable).

    Preserved for backward compatibility.  New call sites should prefer
    :func:`is_base_template` which covers all ``BASE-*`` / ``BASE_*`` files,
    not only the exact ``BASE_AGENT`` / ``BASE-AGENT`` variant.

    This implementation now delegates to ``is_base_template`` so it catches
    ``BASE-ENGINEER``, ``BASE-QA``, ``BASE-OPS``, ``BASE-RESEARCH``, etc. in
    addition to the original ``BASE_AGENT`` / ``BASE-AGENT`` forms.

    Args:
        agent_id: Agent identifier to check (may include path like "qa/BASE-AGENT")

    Returns:
        True if agent is a BASE template (case-insensitive), False otherwise

    Examples:
        >>> is_base_agent("BASE_AGENT")
        True
        >>> is_base_agent("base-agent")
        True
        >>> is_base_agent("qa/BASE-AGENT")
        True
        >>> is_base_agent("BASE-ENGINEER")
        True
        >>> is_base_agent("ENGINEER")
        False
    """
    if not agent_id:
        return False

    # Extract filename from path (handle cases like "qa/BASE-AGENT")
    # 1M-502: Remote agents may have path prefixes like "qa/", "pm/", etc.
    agent_name = agent_id.rsplit("/", maxsplit=1)[-1]

    # Delegate to the canonical predicate — treat any BASE-* / BASE_* as a template.
    return is_base_template(agent_name)


def filter_base_agents(agents: list[dict]) -> list[dict]:
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


def normalize_agent_id(agent_id: str) -> str:
    """Canonical agent ID normalizer for memory lookups and comparisons.

    Produces a stable, lowercase, kebab-case identifier with no -agent suffix.
    This is the SINGLE SOURCE OF TRUTH for agent ID normalization.
    All other normalizers should delegate to this function.

    Algorithm:
    1. Guard against empty/whitespace input
    2. Extract leaf name (last component after /)
    3. Strip common file extensions (.md, .yaml, .yml, .json)
    4. Lowercase
    5. Replace underscores and spaces with dashes
    6. Collapse multiple dashes
    7. Strip leading/trailing dashes
    8. Strip -agent suffix
    9. Guard against empty result

    Args:
        agent_id: Raw agent ID in any format

    Returns:
        Normalized lowercase kebab-case agent ID, or "" for invalid input

    Examples:
        >>> normalize_agent_id("python_engineer")
        'python-engineer'
        >>> normalize_agent_id("research-agent")
        'research'
        >>> normalize_agent_id("PM")
        'pm'
        >>> normalize_agent_id("")
        ''
        >>> normalize_agent_id("-agent")
        'agent'
        >>> normalize_agent_id("python-engineer.md")
        'python-engineer'
    """
    if not agent_id or not agent_id.strip():
        return ""

    # Extract leaf name (handle path-style agent IDs)
    leaf = agent_id.rsplit("/", maxsplit=1)[-1]

    # Strip common file extensions
    for ext in (".md", ".yaml", ".yml", ".json"):
        if leaf.lower().endswith(ext):
            leaf = leaf[: -len(ext)]
            break

    # Lowercase, replace underscores and spaces with dashes
    normalized = leaf.lower().replace("_", "-").replace(" ", "-")

    # Collapse multiple dashes
    while "--" in normalized:
        normalized = normalized.replace("--", "-")

    # Strip leading/trailing dashes
    normalized = normalized.strip("-")

    # Strip -agent suffix
    if normalized.endswith("-agent"):
        normalized = normalized[:-6]

    return normalized


def normalize_agent_id_for_comparison(agent_id: str) -> str:
    """Normalize an agent_id to match deployed filename stems.

    Delegates to normalize_agent_id() -- the canonical normalizer.
    Kept for backward compatibility with existing callers.

    Args:
        agent_id: Raw agent ID from frontmatter

    Returns:
        Normalized stem matching deployed filename

    Examples:
        >>> normalize_agent_id_for_comparison("research-agent")
        'research'
        >>> normalize_agent_id_for_comparison("dart_engineer")
        'dart-engineer'
        >>> normalize_agent_id_for_comparison("PM")
        'pm'
    """
    return normalize_agent_id(agent_id)


def get_deployed_agent_ids(project_dir: Path | None = None) -> set[str]:
    """Get set of currently deployed agent IDs.

    Checks virtual deployment state (.mpm_deployment_state) first, then falls back
    to physical .md files for backward compatibility. This ensures agents are detected
    whether deployed virtually or as physical files.

    Args:
        project_dir: Project directory to check, defaults to current working directory

    Returns:
        Set of normalized deployed agent IDs (lowercase, hyphenated, no -agent suffix).
        All IDs are passed through normalize_agent_id_for_comparison() so callers
        can compare directly without additional normalization.

    Examples:
        >>> deployed = get_deployed_agent_ids()
        >>> "python-engineer" in deployed  # If agent exists in deployment state
        True
        >>> "engineer" in deployed  # If ENGINEER.md exists (normalized to lowercase)
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

                # Extract agent IDs from deployment state and normalize
                # Agent IDs are leaf names (e.g., "python-engineer", "qa")
                agents = state.get("last_check_results", {}).get("agents", {})
                deployed.update(normalize_agent_id_for_comparison(k) for k in agents)

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
            # Exclude BASE composition templates (BASE-*.md / BASE_*.md) and
            # macOS metadata files.  Use the canonical predicate so that
            # BASE-ENGINEER, BASE-QA, BASE-OPS, etc. are all excluded here.
            if not is_base_template(file.name) and file.stem != ".DS_Store":
                deployed.add(normalize_agent_id_for_comparison(file.stem))

    # NOTE: .claude/templates/ contains PM instruction templates, NOT deployed agents
    # It should NOT be checked here. Agents are deployed to:
    # - .mpm_deployment_state (virtual deployment)
    # - .claude/agents/*.md (project deployment)

    return deployed


def filter_deployed_agents(
    agents: list[dict], project_dir: Path | None = None
) -> list[dict]:
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
    return [
        a
        for a in agents
        if normalize_agent_id_for_comparison(a.get("agent_id", "")) not in deployed_ids
    ]


def load_local_only_agents(project_dir: Path | None = None) -> list[str]:
    """Load the ``agents.local_only`` list from ``.claude-mpm/configuration.yaml``.

    ``local_only`` agents are committed to the project git repo; "local_only"
    means MPM-unmanaged, not git-ignored. They are hand-crafted by the
    project owner, live in ``.claude/agents/``, and must NEVER be deleted or
    overwritten by MPM sync/cleanup (Issue #560).

    This loader reads the project configuration file directly (without going
    through ``UnifiedConfig``) so it can be called cheaply from filesystem
    code paths that do not already hold a config instance.

    Args:
        project_dir: Project directory to check. Defaults to ``Path.cwd()``.

    Returns:
        List of agent IDs marked as ``local_only`` in the project config,
        or ``[]`` if the config is missing, malformed, or has no list.

    Failure Modes:
        - Missing file: returns ``[]``
        - Malformed YAML: returns ``[]`` (logs debug message)
        - Missing ``agents`` or ``agents.local_only`` key: returns ``[]``
        - Non-list ``local_only`` value: returns ``[]`` (logs warning)
    """
    if project_dir is None:
        project_dir = Path.cwd()

    candidate_paths = [
        project_dir / ".claude-mpm" / "configuration.yaml",
        project_dir / ".claude-mpm" / "configuration.yml",
    ]

    for config_path in candidate_paths:
        if not config_path.exists():
            continue

        try:
            import yaml

            with config_path.open(encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception as e:
            import logging

            logging.getLogger(__name__).debug(
                "Failed to read local_only from %s: %s", config_path, e
            )
            return []

        if not isinstance(data, dict):
            return []

        agents_section = data.get("agents", {})
        if not isinstance(agents_section, dict):
            return []

        local_only = agents_section.get("local_only", [])
        if not isinstance(local_only, list):
            import logging

            logging.getLogger(__name__).warning(
                "agents.local_only in %s is not a list (got %s); ignoring",
                config_path,
                type(local_only).__name__,
            )
            return []

        return [str(a) for a in local_only]

    return []


def is_local_only(agent_id: str, local_only_list: list[str]) -> bool:
    """Check if ``agent_id`` is in the project-local-only allow list.

    ``local_only`` agents are committed to the project git repo; "local_only"
    means MPM-unmanaged, not git-ignored. Membership in this list signals
    that MPM sync/cleanup must skip the agent.

    Comparison is performed against normalized IDs (see
    :func:`normalize_agent_id`) so callers do not need to worry about
    case, separators, or ``-agent`` suffixes.

    Args:
        agent_id: Raw agent ID (filename stem, frontmatter id, etc.).
        local_only_list: List of agent IDs from ``agents.local_only``.

    Returns:
        ``True`` if ``agent_id`` matches any entry in ``local_only_list``
        under normalized comparison; ``False`` otherwise (including empty
        inputs).

    Examples:
        >>> is_local_only("writer", ["writer", "fact-checker"])
        True
        >>> is_local_only("WRITER", ["writer"])
        True
        >>> is_local_only("writer.md", ["writer"])
        True
        >>> is_local_only("writer-agent", ["writer"])
        True
        >>> is_local_only("engineer", ["writer", "fact-checker"])
        False
        >>> is_local_only("anything", [])
        False
    """
    if not agent_id or not local_only_list:
        return False

    normalized_id = normalize_agent_id(agent_id)
    if not normalized_id:
        return False

    normalized_allow = {normalize_agent_id(name) for name in local_only_list}
    return normalized_id in normalized_allow


def warn_missing_local_only_agents(
    local_only_list: list[str], project_dir: Path | None = None
) -> list[str]:
    """Warn when ``local_only`` agents are configured but not present on disk.

    ``local_only`` agents are committed to the project git repo; "local_only"
    means MPM-unmanaged, not git-ignored. They are expected to exist as
    ``.md`` files in ``.claude/agents/`` and to be tracked in source control.

    Issue #560 requires a warning (not an error) when a configured
    ``local_only`` agent has no corresponding ``.md`` file in
    ``.claude/agents/``. This helps surface drift between the config and the
    actual project state without breaking deployment.

    Args:
        local_only_list: List of agent IDs from ``agents.local_only``.
        project_dir: Project directory to check. Defaults to ``Path.cwd()``.

    Returns:
        List of normalized agent IDs that are configured but missing from
        ``.claude/agents/``. Empty list when all agents are present or the
        input list is empty.
    """
    if not local_only_list:
        return []

    if project_dir is None:
        project_dir = Path.cwd()

    deployed = get_deployed_agent_ids(project_dir)
    missing: list[str] = []

    for agent_id in local_only_list:
        normalized = normalize_agent_id(agent_id)
        if not normalized:
            continue
        if normalized not in deployed:
            missing.append(normalized)

    if missing:
        import logging

        logging.getLogger(__name__).warning(
            "Configured local_only agents not found in %s: %s. "
            "These agents are MPM-unmanaged (skipped by MPM sync/cleanup) "
            "but should be committed to the project repo as .md files in "
            ".claude/agents/. 'local_only' means MPM-unmanaged, not "
            "git-ignored.",
            project_dir / ".claude" / "agents",
            ", ".join(sorted(missing)),
        )

    return missing


def apply_all_filters(
    agents: list[dict],
    project_dir: Path | None = None,
    filter_base: bool = True,
    filter_deployed: bool = False,
) -> list[dict]:
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
