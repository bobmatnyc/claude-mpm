"""System agent deployment strategy."""

from pathlib import Path
from typing import List

from claude_mpm.core.unified_paths import get_path_manager

from .base_strategy import BaseDeploymentStrategy, DeploymentContext


class SystemAgentDeploymentStrategy(BaseDeploymentStrategy):
    """Strategy for deploying system-wide agents.

    System agents are the default agents provided by claude-mpm,
    deployed to ~/.claude/agents/ for global availability.
    """

    def __init__(self):
        super().__init__("System Agent Deployment")

    def can_handle(self, context: DeploymentContext) -> bool:
        """Check if this is a system agent deployment.

        System deployment is the default when:
        - No specific target directory is provided, OR
        - Templates directory points to system templates, OR
        - Working directory is not set (CLI usage)

        Args:
            context: Deployment context

        Returns:
            True if this should handle system agent deployment
        """
        # If templates_dir points to system templates, this is system deployment
        if context.templates_dir:
            # Check for user system templates directory
            system_templates_dir = (
                get_path_manager().get_user_agents_dir() / "templates"
            )
            if context.templates_dir.resolve() == system_templates_dir.resolve():
                return True

            # Check for framework templates directory (packaged installation)
            framework_templates_dir = (
                get_path_manager().get_agents_dir("framework") / "templates"
            )
            if context.templates_dir.resolve() == framework_templates_dir.resolve():
                return True

        # If no target_dir specified and no working_directory, assume system deployment
        if not context.target_dir and not context.working_directory:
            return True

        # If target_dir points to user's home .claude directory
        if context.target_dir:
            home_claude_dir = Path.home() / ".claude" / "agents"
            if context.target_dir.resolve() == home_claude_dir.resolve():
                return True

        return False

    def determine_target_directory(self, context: DeploymentContext) -> Path:
        """Determine target directory for system agents.

        MODIFIED: System agents are now deployed to project .claude/agents/
        to maintain consistency with the new deployment behavior.
        All agents (system, user, project) deploy to the project level.

        Args:
            context: Deployment context

        Returns:
            Path to <project>/.claude/agents/
        """
        # Always deploy to project directory
        if context.working_directory:
            return context.working_directory / ".claude" / "agents"
        # Fallback to current working directory if not specified
        return Path.cwd() / ".claude" / "agents"

    def get_templates_directory(self, context: DeploymentContext) -> Path:
        """Get templates directory for system agents.

        Args:
            context: Deployment context

        Returns:
            Path to system templates directory
        """
        if context.templates_dir:
            return context.templates_dir
        return get_path_manager().get_user_agents_dir() / "templates"

    def get_excluded_agents(self, context: DeploymentContext) -> List[str]:
        """Get excluded agents for system deployment.

        System deployment respects global exclusion configuration.

        Args:
            context: Deployment context

        Returns:
            List of excluded agent names
        """
        if not context.config:
            return []

        return context.config.get("agent_deployment.excluded_agents", [])

    def should_deploy_system_instructions(self, context: DeploymentContext) -> bool:
        """System deployment should deploy system instructions.

        Args:
            context: Deployment context

        Returns:
            True - system deployment includes instructions
        """
        return True

    def get_deployment_priority(self) -> int:
        """System deployment has lowest priority (highest number).

        This ensures project and user deployments take precedence
        when multiple strategies could handle the same context.

        Returns:
            Priority 100 (lowest priority)
        """
        return 100
