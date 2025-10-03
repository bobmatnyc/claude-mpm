"""Deployment type detection for agent deployment service.

This module provides utilities to detect the type of agent deployment
(system, project-specific, or user custom) based on template directory paths.
Extracted from AgentDeploymentService to reduce complexity.
"""

from pathlib import Path
from typing import Optional

from claude_mpm.config.paths import paths


class DeploymentTypeDetector:
    """Detects the type of agent deployment based on template directory."""

    @staticmethod
    def is_system_agent_deployment(templates_dir: Optional[Path]) -> bool:
        """
        Check if this is a deployment of system agents.

        System agents are those provided by the claude-mpm package itself,
        located in the package's agents/templates directory.

        Args:
            templates_dir: Directory containing agent templates

        Returns:
            True if deploying system agents, False otherwise
        """
        # Check if templates_dir points to the system templates
        if templates_dir and templates_dir.exists():
            # System agents are in the package's agents/templates directory
            try:
                # Check if templates_dir is within the claude_mpm package structure
                templates_str = str(templates_dir.resolve())
                return (
                    "site-packages/claude_mpm" in templates_str
                    or "src/claude_mpm/agents/templates" in templates_str
                    or (paths.agents_dir / "templates").resolve()
                    == templates_dir.resolve()
                )
            except Exception:
                pass
        return False

    @staticmethod
    def is_project_specific_deployment(
        templates_dir: Optional[Path], working_directory: Path
    ) -> bool:
        """
        Check if deploying project-specific agents.

        Project-specific agents are those found in the project's
        .claude-mpm/agents/ directory.

        Args:
            templates_dir: Directory containing agent templates
            working_directory: Current working directory

        Returns:
            True if deploying project-specific agents, False otherwise
        """
        # Check if we're in a project directory with .claude-mpm/agents
        project_agents_dir = working_directory / ".claude-mpm" / "agents"
        if project_agents_dir.exists() and templates_dir and templates_dir.exists():
            try:
                return project_agents_dir.resolve() == templates_dir.resolve()
            except Exception:
                pass
        return False

    @staticmethod
    def is_user_custom_deployment(templates_dir: Optional[Path]) -> bool:
        """
        Check if deploying user custom agents.

        User custom agents are those in ~/.claude-mpm/agents/

        Args:
            templates_dir: Directory containing agent templates

        Returns:
            True if deploying user custom agents, False otherwise
        """
        user_agents_dir = Path.home() / ".claude-mpm" / "agents"
        if user_agents_dir.exists() and templates_dir and templates_dir.exists():
            try:
                return user_agents_dir.resolve() == templates_dir.resolve()
            except Exception:
                pass
        return False

    @staticmethod
    def determine_source_tier(templates_dir: Optional[Path]) -> str:
        """
        Determine the source tier for logging.

        Understanding which tier (SYSTEM/USER/PROJECT) agents
        are being deployed from helps with debugging and auditing.

        Args:
            templates_dir: Directory containing agent templates

        Returns:
            Source tier string: "SYSTEM", "USER", or "PROJECT"
        """
        if templates_dir:
            templates_str = str(templates_dir)
            if (
                ".claude-mpm/agents" in templates_str
                and "/templates" not in templates_str
            ):
                return "PROJECT"
            if (
                "/.claude-mpm/agents" in templates_str
                and "/templates" not in templates_str
            ):
                return "USER"
        return "SYSTEM"
