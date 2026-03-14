"""
Startup Reconciliation Hook

This module provides a hook for performing agent/skill reconciliation
during application startup, ensuring deployed state matches configuration.

Usage:
    from claude_mpm.services.agents.deployment.startup_reconciliation import (
        perform_startup_reconciliation
    )

    # In your startup code
    perform_startup_reconciliation()
"""

from pathlib import Path
from typing import Optional

from claude_mpm.core.logging_utils import get_logger
from claude_mpm.core.unified_config import UnifiedConfig

from .deployment_reconciler import DeploymentReconciler, DeploymentResult

logger = get_logger(__name__)


def _extract_agent_id_from_frontmatter(content: str) -> Optional[str]:
    """Extract agent_id from YAML frontmatter.

    Args:
        content: Full text content of the agent .md file

    Returns:
        The agent_id value if found, otherwise None.
    """
    if not content.startswith("---"):
        return None
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None
    for line in parts[1].split("\n"):
        line = line.strip()
        if line.startswith("agent_id:"):
            return line[9:].strip().strip("'\"")
    return None


def _detect_and_remove_orphaned_agents(
    project_path: Path,
    config: UnifiedConfig,
    agent_result: DeploymentResult,
) -> list[str]:
    """Detect and remove orphaned MPM agents after reconciliation.

    An orphaned agent is a deployed file in .claude/agents/ that:
    1. Is managed by MPM (has author: claude-mpm in frontmatter)
    2. Is NOT in the expected set of agents (not in cache or config)

    This handles the case where agents are renamed in the source repo:
    the old-named file persists while the new-named file is deployed.

    Args:
        project_path: Project directory
        config: Configuration instance
        agent_result: Result from reconciliation (for context)

    Returns:
        List of removed agent filenames
    """
    from claude_mpm.core.unified_paths import get_path_manager
    from claude_mpm.utils.agent_provenance import is_mpm_managed_agent

    deploy_dir = project_path / ".claude" / "agents"
    if not deploy_dir.exists():
        return []

    path_manager = get_path_manager()
    cache_dir = path_manager.get_cache_dir() / "agents"

    # Build expected agent set
    expected_stems: set[str] = set()

    # Source 1: All agents in the cache (covers remote sources)
    if cache_dir.exists():
        from claude_mpm.services.agents.deployment_utils import (
            normalize_deployment_filename,
        )

        for agent_file in cache_dir.glob("**/*.md"):
            # Add raw cache stem for backward compatibility
            expected_stems.add(agent_file.stem)
            # Add normalized stem (strips -agent suffix, lowercases, etc.)
            normalized_filename = normalize_deployment_filename(agent_file.name)
            expected_stems.add(Path(normalized_filename).stem)
            # Also check frontmatter for agent_id override (e.g. web-ui -> web-ui-engineer)
            try:
                content = agent_file.read_text(encoding="utf-8")
                agent_id = _extract_agent_id_from_frontmatter(content)
                if agent_id:
                    normalized_id_filename = normalize_deployment_filename(
                        f"{agent_id}.md"
                    )
                    expected_stems.add(Path(normalized_id_filename).stem)
            except Exception:
                pass  # Skip unreadable files

    # Source 2: Configured agents (covers explicit configuration)
    if config.agents.enabled:
        expected_stems.update(config.agents.enabled)
    if config.agents.required:
        expected_stems.update(config.agents.required)

    # Source 3: Local templates (project-level)
    local_template_dir = project_path / ".claude-mpm" / "agents"
    if local_template_dir.exists():
        from claude_mpm.services.agents.deployment_utils import (
            normalize_deployment_filename,
        )

        for agent_file in local_template_dir.glob("*.md"):
            expected_stems.add(agent_file.stem)
            normalized_filename = normalize_deployment_filename(agent_file.name)
            expected_stems.add(Path(normalized_filename).stem)
            try:
                content = agent_file.read_text(encoding="utf-8")
                agent_id = _extract_agent_id_from_frontmatter(content)
                if agent_id:
                    normalized_id_filename = normalize_deployment_filename(
                        f"{agent_id}.md"
                    )
                    expected_stems.add(Path(normalized_id_filename).stem)
            except Exception:
                pass

    # Source 4: User-level templates
    user_template_dir = Path.home() / ".claude-mpm" / "agents"
    if user_template_dir.exists():
        from claude_mpm.services.agents.deployment_utils import (
            normalize_deployment_filename,
        )

        for agent_file in user_template_dir.glob("*.md"):
            expected_stems.add(agent_file.stem)
            normalized_filename = normalize_deployment_filename(agent_file.name)
            expected_stems.add(Path(normalized_filename).stem)
            try:
                content = agent_file.read_text(encoding="utf-8")
                agent_id = _extract_agent_id_from_frontmatter(content)
                if agent_id:
                    normalized_id_filename = normalize_deployment_filename(
                        f"{agent_id}.md"
                    )
                    expected_stems.add(Path(normalized_id_filename).stem)
            except Exception:
                pass

    if not expected_stems:
        # No expected agents found — don't remove anything
        # This prevents accidental deletion if cache is empty
        logger.debug("No expected agents found, skipping orphan detection")
        return []

    # Scan deployed directory for orphans
    removed: list[str] = []
    for deployed_file in deploy_dir.glob("*.md"):
        stem = deployed_file.stem

        # Skip if this agent is expected
        if stem in expected_stems:
            continue

        # Only remove MPM-managed agents (protect user agents)
        try:
            content = deployed_file.read_text(encoding="utf-8")
            if not is_mpm_managed_agent(content):
                logger.debug(f"Preserved user agent during orphan scan: {stem}")
                continue
        except Exception as e:
            logger.debug(f"Could not read {deployed_file} for orphan check: {e}")
            continue

        # This is an orphaned MPM agent — remove it
        try:
            deployed_file.unlink()
            removed.append(stem)
            logger.info(f"Removed orphaned agent: {stem}")
        except Exception as e:
            logger.warning(f"Failed to remove orphaned agent {stem}: {e}")

    return removed


def perform_startup_reconciliation(
    project_path: Optional[Path] = None,
    config: Optional[UnifiedConfig] = None,
    silent: bool = False,
) -> tuple[DeploymentResult, DeploymentResult]:
    """
    Perform agent and skill reconciliation during startup.

    This ensures the deployed state (.claude/agents, .claude/skills) matches
    the configuration (agents.enabled, skills.enabled lists).

    Args:
        project_path: Project directory (default: current directory)
        config: Configuration instance (auto-loads if None)
        silent: Suppress info logging (only errors)

    Returns:
        Tuple of (agent_result, skill_result)
    """
    project_path = project_path or Path.cwd()

    # Load config if not provided
    if config is None:
        config = UnifiedConfig()

    # Initialize reconciler
    reconciler = DeploymentReconciler(config)

    if not silent:
        logger.info("Performing startup reconciliation...")

    # Reconcile agents
    agent_result = reconciler.reconcile_agents(project_path)

    # Detect and remove orphaned agents post-reconciliation
    orphans_removed = _detect_and_remove_orphaned_agents(
        project_path, config, agent_result
    )
    if orphans_removed and not silent:
        logger.info(
            f"Removed {len(orphans_removed)} orphaned agent(s): "
            f"{', '.join(orphans_removed)}"
        )
    # Append orphan removals to the result for reporting
    agent_result.removed.extend(orphans_removed)

    if agent_result.deployed and not silent:
        logger.info(f"Deployed agents: {', '.join(agent_result.deployed)}")
    if agent_result.removed and not silent:
        logger.info(f"Removed agents: {', '.join(agent_result.removed)}")
    if agent_result.errors:
        for error in agent_result.errors:
            logger.error(f"Agent reconciliation error: {error}")

    # Reconcile skills
    skill_result = reconciler.reconcile_skills(project_path)

    if skill_result.deployed and not silent:
        logger.info(f"Deployed skills: {', '.join(skill_result.deployed)}")
    if skill_result.removed and not silent:
        logger.info(f"Removed skills: {', '.join(skill_result.removed)}")
    if skill_result.errors:
        for error in skill_result.errors:
            logger.error(f"Skill reconciliation error: {error}")

    if not silent:
        total_errors = len(agent_result.errors) + len(skill_result.errors)
        if total_errors == 0:
            logger.info("Startup reconciliation complete")
        else:
            logger.warning(
                f"Startup reconciliation complete with {total_errors} errors"
            )

    return agent_result, skill_result


def check_reconciliation_needed(
    project_path: Optional[Path] = None, config: Optional[UnifiedConfig] = None
) -> bool:
    """
    Check if reconciliation is needed (without performing it).

    Args:
        project_path: Project directory
        config: Configuration instance

    Returns:
        True if reconciliation would make changes
    """
    project_path = project_path or Path.cwd()

    if config is None:
        config = UnifiedConfig()

    reconciler = DeploymentReconciler(config)
    view = reconciler.get_reconciliation_view(project_path)

    agent_state = view["agents"]
    skill_state = view["skills"]

    # Check if any changes needed
    return (
        len(agent_state.to_deploy) > 0
        or len(agent_state.to_remove) > 0
        or len(skill_state.to_deploy) > 0
        or len(skill_state.to_remove) > 0
    )


# Example integration in startup code:
#
# from claude_mpm.services.agents.deployment.startup_reconciliation import (
#     perform_startup_reconciliation,
#     check_reconciliation_needed
# )
#
# def startup():
#     # Check if reconciliation needed
#     if check_reconciliation_needed():
#         logger.info("Reconciliation needed, performing...")
#         perform_startup_reconciliation()
#     else:
#         logger.debug("No reconciliation needed")
