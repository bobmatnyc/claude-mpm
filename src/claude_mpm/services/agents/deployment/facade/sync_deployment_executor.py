"""Synchronous deployment executor."""

from pathlib import Path
from typing import Any, Dict, Optional

from claude_mpm.core.config import Config
from claude_mpm.core.logger import get_logger

from .deployment_executor import DeploymentExecutor


class SyncDeploymentExecutor(DeploymentExecutor):
    """Synchronous deployment executor.

    This executor uses the standard synchronous deployment pipeline
    for reliable, sequential processing of agents.
    """

    def __init__(self, pipeline_builder, pipeline_executor):
        """Initialize sync deployment executor.

        Args:
            pipeline_builder: Pipeline builder for creating deployment pipelines
            pipeline_executor: Pipeline executor for running pipelines
        """
        self.pipeline_builder = pipeline_builder
        self.pipeline_executor = pipeline_executor
        self.logger = get_logger(__name__)

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
        """Execute synchronous deployment.

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
        self.logger.info("Executing synchronous deployment")

        try:
            # Build deployment pipeline
            pipeline = self.pipeline_builder.create_standard_pipeline()

            # Create pipeline context
            from claude_mpm.services.agents.deployment.pipeline import PipelineContext

            context = PipelineContext(
                templates_dir=templates_dir,
                base_agent_path=base_agent_path,
                working_directory=working_directory,
                target_dir=target_dir,
                force_rebuild=force_rebuild,
                deployment_mode=deployment_mode,
                config=config,
            )

            # Execute pipeline
            pipeline_result = self.pipeline_executor.execute(pipeline, context)

            # Convert pipeline result to deployment result format
            deployment_result = self._convert_pipeline_result(pipeline_result, context)

            # Add executor metadata
            deployment_result["metadata"]["executor"] = self.get_executor_name()
            deployment_result["metadata"]["execution_mode"] = "synchronous"

            return deployment_result

        except Exception as e:
            self.logger.error(f"Synchronous deployment failed: {e}", exc_info=True)
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
                    "execution_mode": "synchronous",
                    "error_type": type(e).__name__,
                },
            }

    def _convert_pipeline_result(self, pipeline_result, context) -> Dict[str, Any]:
        """Convert pipeline result to deployment result format.

        Args:
            pipeline_result: Result from pipeline execution (dict)
            context: Pipeline context with results

        Returns:
            Deployment result dictionary
        """
        # Extract pipeline execution info
        pipeline_exec = pipeline_result.get("pipeline_execution", {})

        # Extract results from pipeline result
        deployed = pipeline_result.get("deployed", [])
        updated = pipeline_result.get("updated", [])
        migrated = pipeline_result.get("migrated", [])
        skipped = pipeline_result.get("skipped", [])
        errors = pipeline_result.get("errors", [])

        return {
            "success": pipeline_exec.get("success", False),
            "target_dir": (
                str(context.actual_target_dir)
                if hasattr(context, "actual_target_dir")
                else None
            ),
            "deployed": deployed,
            "updated": updated,
            "migrated": migrated,
            "skipped": skipped,
            "errors": errors,
            "warnings": getattr(context, "warnings", []),
            "metrics": {
                "total_steps": pipeline_exec.get("total_steps", 0),
                "executed_steps": pipeline_exec.get("executed_steps", []),
                "failed_steps": pipeline_exec.get("failed_steps", []),
                "total_execution_time": pipeline_exec.get("total_execution_time", 0),
                "step_timings": getattr(context, "step_timings", {}),
                "deployment_time": pipeline_result.get("deployment_time", 0),
            },
            "metadata": {
                "pipeline_execution": pipeline_exec,
                "step_timings": getattr(context, "step_timings", {}),
            },
        }

    def is_available(self) -> bool:
        """Sync executor is always available.

        Returns:
            True - sync execution is always available
        """
        return True

    def get_executor_name(self) -> str:
        """Get executor name.

        Returns:
            Executor name
        """
        return "sync"

    def get_performance_characteristics(self) -> Dict[str, Any]:
        """Get performance characteristics.

        Returns:
            Performance characteristics dictionary
        """
        return {
            "name": self.get_executor_name(),
            "available": self.is_available(),
            "estimated_speedup": 1.0,  # Baseline
            "memory_usage": "normal",
            "reliability": "high",
            "description": "Sequential processing with high reliability",
        }
