"""Project-specific agent deployment strategy."""

from pathlib import Path
from typing import List

from .base_strategy import BaseDeploymentStrategy, DeploymentContext


class ProjectAgentDeploymentStrategy(BaseDeploymentStrategy):
    """Strategy for deploying project-specific agents.

    Project agents are deployed to the project's .claude/agents/
    directory and are specific to that project.
    """

    def __init__(self):
        super().__init__("Project Agent Deployment")

    def can_handle(self, context: DeploymentContext) -> bool:
        """Check if this is a project-specific deployment.

        Project deployment when:
        - Working directory is set AND
        - Target directory is within the working directory, OR
        - Templates directory is within working directory's .claude-mpm/agents/

        Args:
            context: Deployment context

        Returns:
            True if this should handle project agent deployment
        """
        if not context.working_directory:
            return False

        # Check if target_dir is within working directory
        if context.target_dir:
            try:
                # Check if target is within working directory
                context.target_dir.resolve().relative_to(
                    context.working_directory.resolve()
                )
                return True
            except ValueError:
                # target_dir is not within working_directory
                pass

        # Check if templates_dir suggests project deployment
        if context.templates_dir:
            project_agents_dir = context.working_directory / ".claude-mpm" / "agents"
            try:
                context.templates_dir.resolve().relative_to(
                    project_agents_dir.resolve()
                )
                return True
            except ValueError:
                # templates_dir is not within project agents directory
                pass

        # Check if deployment_mode is "project" - this should be sufficient
        return context.deployment_mode == "project"

    def determine_target_directory(self, context: DeploymentContext) -> Path:
        """Determine target directory for project agents.

        Project agents are deployed to {working_directory}/.claude/agents/

        Args:
            context: Deployment context

        Returns:
            Path to project's .claude/agents/ directory
        """
        if context.target_dir:
            return context.target_dir

        if context.working_directory:
            return context.working_directory / ".claude" / "agents"

        # Fallback to current directory
        return Path.cwd() / ".claude" / "agents"

    def get_templates_directory(self, context: DeploymentContext) -> Path:
        """Get templates directory for project agents.

        Args:
            context: Deployment context

        Returns:
            Path to project templates directory or system fallback
        """
        if context.templates_dir:
            return context.templates_dir

        if context.working_directory:
            # Try project-specific agents directory first
            project_agents_dir = context.working_directory / ".claude-mpm" / "agents"
            if project_agents_dir.exists():
                return project_agents_dir

        # Fallback to system templates
        from claude_mpm.core.unified_paths import get_path_manager

        return get_path_manager().get_user_agents_dir() / "templates"

    def get_excluded_agents(self, context: DeploymentContext) -> List[str]:
        """Get excluded agents for project deployment.

        Project deployment may have project-specific exclusions.

        Args:
            context: Deployment context

        Returns:
            List of excluded agent names
        """
        if not context.config:
            return []

        # Project deployments might have different exclusion rules
        excluded = context.config.get("agent_deployment.excluded_agents", [])

        # In project mode, we might want to include all agents by default
        if context.deployment_mode == "project":
            return []

        return excluded

    def should_deploy_system_instructions(self, context: DeploymentContext) -> bool:
        """Project deployment should deploy system instructions.

        Args:
            context: Deployment context

        Returns:
            True - project deployment includes instructions
        """
        return True

    def get_deployment_priority(self) -> int:
        """Project deployment has medium priority.

        Higher priority than system, lower than user.

        Returns:
            Priority 50 (medium priority)
        """
        return 50
