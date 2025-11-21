"""Pipeline executor for running deployment pipelines."""

import time
from typing import Any, Dict, List

from claude_mpm.core.logger import get_logger

from .pipeline_context import PipelineContext
from .steps.base_step import BaseDeploymentStep


class DeploymentPipelineExecutor:
    """Executor for running deployment pipelines.

    This executor runs a series of deployment steps in order,
    handling errors and collecting results.
    """

    def __init__(self):
        """Initialize the pipeline executor."""
        self.logger = get_logger(__name__)

    def execute(
        self, steps: List[BaseDeploymentStep], context: PipelineContext
    ) -> Dict[str, Any]:
        """Execute a deployment pipeline.

        Args:
            steps: List of deployment steps to execute
            context: Pipeline context containing deployment data

        Returns:
            Dictionary with execution results
        """
        self.logger.info(f"Starting deployment pipeline with {len(steps)} steps")

        # Initialize context
        if context.deployment_start_time is None:
            context.deployment_start_time = time.time()

        context.initialize_results()

        # Execute steps
        executed_steps = []
        failed_steps = []
        skipped_steps = []

        for i, step in enumerate(steps):
            step_start_time = time.time()

            try:
                # Check if step should be executed
                if not step.should_execute(context):
                    self.logger.info(f"Skipping step {i + 1}/{len(steps)}: {step.name}")
                    skipped_steps.append(step.name)
                    continue

                self.logger.info(f"Executing step {i + 1}/{len(steps)}: {step.name}")

                # Execute the step
                result = step.execute(context)

                # Log result
                if result.is_success:
                    self.logger.info(f"Step completed successfully: {step.name}")
                    executed_steps.append(step.name)
                elif result.is_warning:
                    self.logger.warning(
                        f"Step completed with warnings: {step.name} - {result.message}"
                    )
                    executed_steps.append(step.name)
                elif result.is_failure:
                    self.logger.error(f"Step failed: {step.name} - {result.message}")
                    failed_steps.append(step.name)

                    # Check if we can continue
                    if not step.can_continue_on_failure():
                        self.logger.error(
                            f"Critical step failed, stopping pipeline: {step.name}"
                        )
                        break
                elif result.is_skipped:
                    self.logger.info(
                        f"Step was skipped: {step.name} - {result.message}"
                    )
                    skipped_steps.append(step.name)

                # Record timing
                step_execution_time = time.time() - step_start_time
                context.step_timings[step.name] = step_execution_time

            except Exception as e:
                step_execution_time = time.time() - step_start_time
                context.step_timings[step.name] = step_execution_time

                error_msg = f"Unexpected error in step {step.name}: {e!s}"
                self.logger.error(error_msg, exc_info=True)
                context.add_error(error_msg)
                failed_steps.append(step.name)

                # Check if we can continue
                if not step.can_continue_on_failure():
                    self.logger.error(
                        f"Critical step failed with exception, stopping pipeline: {step.name}"
                    )
                    break

        # Finalize results
        end_time = time.time()
        final_results = context.finalize_results(end_time)

        # Add pipeline execution metadata
        final_results.update(
            {
                "pipeline_execution": {
                    "total_steps": len(steps),
                    "executed_steps": executed_steps,
                    "failed_steps": failed_steps,
                    "skipped_steps": skipped_steps,
                    "success": len(failed_steps) == 0,
                    "total_execution_time": end_time - context.deployment_start_time,
                }
            }
        )

        # Log final results
        if len(failed_steps) == 0:
            self.logger.info(
                f"Pipeline completed successfully in {final_results['deployment_time']:.3f}s"
            )
        else:
            self.logger.error(
                f"Pipeline completed with {len(failed_steps)} failed steps"
            )

        return final_results

    def validate_pipeline(self, steps: List[BaseDeploymentStep]) -> List[str]:
        """Validate a pipeline before execution.

        Args:
            steps: List of deployment steps to validate

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        if not steps:
            errors.append("Pipeline cannot be empty")
            return errors

        # Check for duplicate step names
        step_names = [step.name for step in steps]
        duplicates = {name for name in step_names if step_names.count(name) > 1}
        if duplicates:
            errors.append(f"Duplicate step names found: {duplicates}")

        # Validate dependencies (simplified check)
        for step in steps:
            dependencies = step.get_dependencies()
            for dep_class in dependencies:
                # Check if any step in the pipeline is of the required type
                if not any(isinstance(s, dep_class) for s in steps):
                    errors.append(
                        f"Step {step.name} requires {dep_class.__name__} but it's not in the pipeline"
                    )

        return errors
