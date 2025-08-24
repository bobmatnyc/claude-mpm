"""Base deployment executor interface."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional

from claude_mpm.core.config import Config


class DeploymentExecutor(ABC):
    """Abstract base class for deployment executors.

    This interface defines the contract for different deployment
    execution strategies (async vs sync).
    """

    @abstractmethod
    def execute_deployment(
        self,
        templates_dir: Path,
        base_agent_path: Path,
        working_directory: Path,
        target_dir: Optional[Path] = None,
        force_rebuild: bool = False,
        deployment_mode: str = "update",
        config: Optional[Config] = None,
    ) -> Dict[str, Any]:
        """Execute deployment with the specific strategy.

        Args:
            templates_dir: Directory containing agent templates
            base_agent_path: Path to base agent configuration
            working_directory: Working directory for deployment
            target_dir: Target directory for deployment
            force_rebuild: Whether to force rebuild
            deployment_mode: Deployment mode (update/project)
            config: Optional configuration

        Returns:
            Deployment results dictionary
        """

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this executor is available.

        Returns:
            True if executor can be used
        """

    @abstractmethod
    def get_executor_name(self) -> str:
        """Get the name of this executor.

        Returns:
            Executor name for logging/metrics
        """

    def get_performance_characteristics(self) -> Dict[str, Any]:
        """Get performance characteristics of this executor.

        Returns:
            Dictionary with performance info
        """
        return {
            "name": self.get_executor_name(),
            "available": self.is_available(),
            "estimated_speedup": 1.0,  # Override in subclasses
            "memory_usage": "normal",  # Override in subclasses
        }
