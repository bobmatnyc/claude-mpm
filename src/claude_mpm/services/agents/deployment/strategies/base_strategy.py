"""Base deployment strategy interface and context."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from claude_mpm.core.config import Config


@dataclass
class DeploymentContext:
    """Context object containing all deployment parameters."""

    target_dir: Optional[Path] = None
    force_rebuild: bool = False
    deployment_mode: str = "update"
    config: Optional[Config] = None
    use_async: bool = False
    working_directory: Optional[Path] = None
    templates_dir: Optional[Path] = None
    base_agent_path: Optional[Path] = None


class BaseDeploymentStrategy(ABC):
    """Base class for all deployment strategies.

    This abstract base class defines the interface that all deployment
    strategies must implement. Each strategy handles a specific type
    of deployment (system, project, user) with its own logic.
    """

    def __init__(self, name: str):
        """Initialize the deployment strategy.

        Args:
            name: Human-readable name for this strategy
        """
        self.name = name

    @abstractmethod
    def can_handle(self, context: DeploymentContext) -> bool:
        """Check if this strategy can handle the given deployment context.

        Args:
            context: Deployment context with parameters

        Returns:
            True if this strategy should handle the deployment
        """

    @abstractmethod
    def determine_target_directory(self, context: DeploymentContext) -> Path:
        """Determine the target directory for deployment.

        Args:
            context: Deployment context with parameters

        Returns:
            Path where agents should be deployed
        """

    @abstractmethod
    def get_templates_directory(self, context: DeploymentContext) -> Path:
        """Get the templates directory for this deployment type.

        Args:
            context: Deployment context with parameters

        Returns:
            Path to the templates directory
        """

    @abstractmethod
    def get_excluded_agents(self, context: DeploymentContext) -> List[str]:
        """Get list of agents to exclude for this deployment type.

        Args:
            context: Deployment context with parameters

        Returns:
            List of agent names to exclude from deployment
        """

    @abstractmethod
    def should_deploy_system_instructions(self, context: DeploymentContext) -> bool:
        """Check if system instructions should be deployed.

        Args:
            context: Deployment context with parameters

        Returns:
            True if system instructions should be deployed
        """

    @abstractmethod
    def get_deployment_priority(self) -> int:
        """Get the priority of this deployment strategy.

        Lower numbers have higher priority. Used when multiple
        strategies can handle the same context.

        Returns:
            Priority number (lower = higher priority)
        """

    def __str__(self) -> str:
        """String representation of the strategy."""
        return f"{self.__class__.__name__}({self.name})"

    def __repr__(self) -> str:
        """Detailed string representation of the strategy."""
        return f"{self.__class__.__name__}(name='{self.name}', priority={self.get_deployment_priority()})"
