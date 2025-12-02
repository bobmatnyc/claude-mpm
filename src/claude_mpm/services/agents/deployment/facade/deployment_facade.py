"""Deployment facade for handling async/sync deployment modes."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from claude_mpm.core.config import Config
from claude_mpm.core.logger import get_logger

from .async_deployment_executor import AsyncDeploymentExecutor
from .deployment_executor import DeploymentExecutor
from .sync_deployment_executor import SyncDeploymentExecutor


class DeploymentFacade:
    """Facade for handling different deployment execution modes.

    This facade provides a clean interface for choosing between
    async and sync deployment execution without cluttering the
    main deployment logic with conditional complexity.
    """

    def __init__(self, pipeline_builder, pipeline_executor):
        """Initialize deployment facade.

        Args:
            pipeline_builder: Pipeline builder for sync deployment
            pipeline_executor: Pipeline executor for sync deployment
        """
        self.logger = get_logger(__name__)

        # Initialize executors
        self.sync_executor = SyncDeploymentExecutor(pipeline_builder, pipeline_executor)
        self.async_executor = AsyncDeploymentExecutor()

        # Executor registry
        self.executors = {
            "sync": self.sync_executor,
            "async": self.async_executor,
        }

    def deploy_agents(
        self,
        templates_dir: Path,
        base_agent_path: Path,
        working_directory: Path,
        target_dir: Optional[Path] = None,
        force_rebuild: bool = False,
        deployment_mode: str = "update",
        config: Optional[Config] = None,
        use_async: bool = False,
        preferred_executor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Deploy agents using the appropriate executor.

        Args:
            templates_dir: Directory containing agent templates
            base_agent_path: Path to base agent configuration
            working_directory: Working directory for deployment
            target_dir: Target directory for deployment
            force_rebuild: Whether to force rebuild
            deployment_mode: Deployment mode (update/project)
            config: Optional configuration
            use_async: Whether to prefer async execution
            preferred_executor: Specific executor to use ('sync' or 'async')

        Returns:
            Deployment results dictionary
        """
        # Select executor
        executor = self._select_executor(use_async, preferred_executor)

        self.logger.info(f"Using {executor.get_executor_name()} deployment executor")

        # Execute deployment
        try:
            results = executor.execute_deployment(
                templates_dir=templates_dir,
                base_agent_path=base_agent_path,
                working_directory=working_directory,
                target_dir=target_dir,
                force_rebuild=force_rebuild,
                deployment_mode=deployment_mode,
                config=config,
            )

            # Add facade metadata
            if "metadata" not in results:
                results["metadata"] = {}

            results["metadata"]["facade_version"] = "1.0.0"
            results["metadata"]["selected_executor"] = executor.get_executor_name()
            results["metadata"]["executor_characteristics"] = (
                executor.get_performance_characteristics()
            )

            return results

        except Exception as e:
            self.logger.error(
                f"Deployment failed with {executor.get_executor_name()} executor: {e}"
            )

            # If async failed and we have a fallback option, try sync
            if (
                executor.get_executor_name() == "async"
                and self.sync_executor.is_available()
            ):
                self.logger.info("Falling back to synchronous deployment")
                return self._fallback_to_sync(
                    templates_dir,
                    base_agent_path,
                    working_directory,
                    target_dir,
                    force_rebuild,
                    deployment_mode,
                    config,
                    e,
                )

            # No fallback available, return error result
            return {
                "success": False,
                "error": str(e),
                "deployed": [],
                "updated": [],
                "migrated": [],
                "skipped": [],
                "errors": [str(e)],
                "metadata": {
                    "facade_version": "1.0.0",
                    "selected_executor": executor.get_executor_name(),
                    "error_type": type(e).__name__,
                    "fallback_attempted": False,
                },
            }

    def _select_executor(
        self, use_async: bool, preferred_executor: Optional[str]
    ) -> DeploymentExecutor:
        """Select the appropriate deployment executor.

        Args:
            use_async: Whether to prefer async execution
            preferred_executor: Specific executor preference

        Returns:
            Selected deployment executor
        """
        # If specific executor is requested, try to use it
        if preferred_executor:
            if preferred_executor in self.executors:
                executor = self.executors[preferred_executor]
                if executor.is_available():
                    return executor
                self.logger.warning(
                    f"Preferred executor '{preferred_executor}' is not available"
                )
            else:
                self.logger.warning(f"Unknown executor '{preferred_executor}'")

        # If async is preferred and available, use it
        if use_async and self.async_executor.is_available():
            return self.async_executor

        # Fall back to sync executor
        if self.sync_executor.is_available():
            return self.sync_executor

        # This should never happen, but just in case
        raise RuntimeError("No deployment executors are available")

    def get_available_executors(self) -> List[Dict[str, Any]]:
        """Get information about available executors.

        Returns:
            List of executor information dictionaries
        """
        return [
            executor.get_performance_characteristics()
            for executor in self.executors.values()
            if executor.is_available()
        ]

    def get_recommended_executor(self, agent_count: int = 1) -> str:
        """Get recommended executor based on deployment characteristics.

        Args:
            agent_count: Number of agents to deploy

        Returns:
            Recommended executor name
        """
        # For small deployments, sync is fine
        if agent_count <= 3:
            return "sync"

        # For larger deployments, prefer async if available
        if self.async_executor.is_available():
            return "async"

        # Fallback to sync
        return "sync"

    def _fallback_to_sync(
        self,
        templates_dir: Path,
        base_agent_path: Path,
        working_directory: Path,
        target_dir: Optional[Path],
        force_rebuild: bool,
        deployment_mode: str,
        config: Optional[Config],
        original_error: Exception,
    ) -> Dict[str, Any]:
        """Fallback to sync deployment when async fails.

        Args:
            templates_dir: Directory containing agent templates
            base_agent_path: Path to base agent configuration
            working_directory: Working directory for deployment
            target_dir: Target directory for deployment
            force_rebuild: Whether to force rebuild
            deployment_mode: Deployment mode
            config: Optional configuration
            original_error: The original error that caused fallback

        Returns:
            Deployment results from sync executor
        """
        try:
            results = self.sync_executor.execute_deployment(
                templates_dir=templates_dir,
                base_agent_path=base_agent_path,
                working_directory=working_directory,
                target_dir=target_dir,
                force_rebuild=force_rebuild,
                deployment_mode=deployment_mode,
                config=config,
            )

            # Add fallback metadata
            if "metadata" not in results:
                results["metadata"] = {}

            results["metadata"]["fallback_from"] = "async"
            results["metadata"]["original_error"] = str(original_error)
            results["metadata"]["fallback_successful"] = results.get("success", False)

            return results

        except Exception as fallback_error:
            self.logger.error(f"Fallback to sync also failed: {fallback_error}")
            return {
                "success": False,
                "error": f"Both async and sync deployment failed. Async: {original_error}, Sync: {fallback_error}",
                "deployed": [],
                "updated": [],
                "migrated": [],
                "skipped": [],
                "errors": [str(original_error), str(fallback_error)],
                "metadata": {
                    "facade_version": "1.0.0",
                    "selected_executor": "async",
                    "fallback_attempted": True,
                    "fallback_successful": False,
                    "original_error": str(original_error),
                    "fallback_error": str(fallback_error),
                },
            }
