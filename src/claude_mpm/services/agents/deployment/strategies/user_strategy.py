"""User-specific agent deployment strategy."""

from pathlib import Path

from .base_strategy import BaseDeploymentStrategy, DeploymentContext


class UserAgentDeploymentStrategy(BaseDeploymentStrategy):
    """Strategy for deploying user-specific agents.

    User agents are custom agents created by the user,
    deployed to user-specific directories.
    """

    def __init__(self):
        super().__init__("User Agent Deployment")

    def can_handle(self, context: DeploymentContext) -> bool:
        """Check if this is a user-specific deployment.

        User deployment when:
        - Templates directory is in ~/.claude-mpm/agents/, OR
        - Target directory is explicitly set to user directory, OR
        - Environment variable CLAUDE_MPM_USER_PWD is set

        Args:
            context: Deployment context

        Returns:
            True if this should handle user agent deployment
        """
        # Check if templates_dir is in user's home directory
        if context.templates_dir:
            user_agents_dir = Path.home() / ".claude-mpm" / "agents"
            try:
                context.templates_dir.resolve().relative_to(user_agents_dir.resolve())
                return True
            except ValueError:
                # templates_dir is not within user agents directory
                pass

        # Check if target_dir is explicitly set to user directory
        if context.target_dir:
            user_claude_dir = Path.home() / ".claude-mpm" / "agents"
            if context.target_dir.resolve() == user_claude_dir.resolve():
                return True

        # Check for user-specific environment variable
        import os

        if "CLAUDE_MPM_USER_PWD" in os.environ:
            return True

        return False

    def determine_target_directory(self, context: DeploymentContext) -> Path:
        """Determine target directory for user agents.

        User agents can be deployed to various user-specific locations.

        Args:
            context: Deployment context

        Returns:
            Path to user agents directory
        """
        if context.target_dir:
            return context.target_dir

        # Check for user-specific environment variable
        import os

        if "CLAUDE_MPM_USER_PWD" in os.environ:
            user_pwd = Path(os.environ["CLAUDE_MPM_USER_PWD"])
            return user_pwd / ".claude" / "agents"

        # Default to user's home directory
        return Path.home() / ".claude-mpm" / "agents"

    def get_templates_directory(self, context: DeploymentContext) -> Path:
        """Get templates directory for user agents.

        Args:
            context: Deployment context

        Returns:
            Path to user templates directory
        """
        if context.templates_dir:
            return context.templates_dir

        # User-specific templates directory
        return Path.home() / ".claude-mpm" / "agents"

    def get_excluded_agents(self, context: DeploymentContext) -> List[str]:
        """Get excluded agents for user deployment.

        User deployment typically has minimal exclusions.

        Args:
            context: Deployment context

        Returns:
            List of excluded agent names (usually empty for user deployment)
        """
        if not context.config:
            return []

        # User deployments might have different exclusion rules
        # or might ignore global exclusions
        return context.config.get("agent_deployment.user_excluded_agents", [])

    def should_deploy_system_instructions(self, context: DeploymentContext) -> bool:
        """User deployment may or may not deploy system instructions.

        Depends on user preferences and configuration.

        Args:
            context: Deployment context

        Returns:
            True if user wants system instructions deployed
        """
        if context.config:
            return context.config.get("agent_deployment.deploy_user_instructions", True)
        return True

    def get_deployment_priority(self) -> int:
        """User deployment has highest priority.

        User-specific deployments should take precedence over
        system and project deployments.

        Returns:
            Priority 10 (highest priority)
        """
        return 10
