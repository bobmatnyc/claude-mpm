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
