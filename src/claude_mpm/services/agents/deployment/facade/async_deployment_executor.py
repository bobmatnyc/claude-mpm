"""Asynchronous deployment executor."""

from pathlib import Path
from typing import Any, Dict, Optional

from claude_mpm.core.config import Config
from claude_mpm.core.logger import get_logger

from .deployment_executor import DeploymentExecutor


class AsyncDeploymentExecutor(DeploymentExecutor):
    """Asynchronous deployment executor.

    This executor uses async operations for improved performance
    when processing multiple agents concurrently.
    """

    def __init__(self):
        """Initialize async deployment executor."""
        self.logger = get_logger(__name__)
        self._async_module = None
        self._is_available = None

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
        """Execute asynchronous deployment.

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
        if not self.is_available():
            raise RuntimeError("Async deployment is not available")

        self.logger.info("Executing asynchronous deployment")

        try:
            # Import async deployment module
            async_module = self._get_async_module()

            # Execute async deployment
            results = async_module.deploy_agents_async_wrapper(
                templates_dir=templates_dir,
                base_agent_path=base_agent_path,
                working_directory=working_directory,
                target_dir=target_dir,
                force_rebuild=force_rebuild,
                config=config,
            )

            # Add executor metadata
            if "metadata" not in results:
                results["metadata"] = {}

            results["metadata"]["executor"] = self.get_executor_name()
            results["metadata"]["execution_mode"] = "asynchronous"

            # Add performance metrics
            if "metrics" not in results:
                results["metrics"] = {}

            results["metrics"]["deployment_method"] = "async"

            return results

        except Exception as e:
            self.logger.error(f"Asynchronous deployment failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "deployed": [],
                "updated": [],
                "migrated": [],
                "skipped": [],
                "errors": [str(e)],
                "metadata": {
                    "executor": self.get_executor_name(),
                    "execution_mode": "asynchronous",
                    "error_type": type(e).__name__,
                },
            }

    def is_available(self) -> bool:
        """Check if async deployment is available.

        Returns:
            True if async deployment module can be imported
        """
        if self._is_available is None:
            try:
                self._get_async_module()
                self._is_available = True
            except ImportError:
                self._is_available = False
                self.logger.debug("Async deployment module not available")
            except Exception as e:
                self._is_available = False
                self.logger.debug(f"Async deployment check failed: {e}")

        return self._is_available

    def _get_async_module(self):
        """Get the async deployment module.

        Returns:
            Async deployment module

        Raises:
            ImportError: If async module cannot be imported
        """
        if self._async_module is None:
            try:
                from claude_mpm.services.agents.deployment import async_agent_deployment

                self._async_module = async_agent_deployment
            except ImportError as e:
                raise ImportError("Async deployment module not available") from e

        return self._async_module

    def get_executor_name(self) -> str:
        """Get executor name.

        Returns:
            Executor name
        """
        return "async"

    def get_performance_characteristics(self) -> Dict[str, Any]:
        """Get performance characteristics.

        Returns:
            Performance characteristics dictionary
        """
        return {
            "name": self.get_executor_name(),
            "available": self.is_available(),
            "estimated_speedup": 1.6,  # 50-70% faster based on existing comments
            "memory_usage": "higher",  # Concurrent operations use more memory
            "reliability": "medium",  # More complex, potential for async issues
            "description": "Concurrent processing for improved performance",
        }
