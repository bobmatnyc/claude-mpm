"""Validation step for deployment pipeline."""

import time

from claude_mpm.services.agents.deployment.validation import DeploymentValidator

from .base_step import BaseDeploymentStep, StepResult, StepStatus


class ValidationStep(BaseDeploymentStep):
    """Step to validate deployment context and templates."""

    def __init__(self):
        super().__init__(
            name="Validation",
            description="Validate deployment environment, templates, and configuration",
        )
        self.validator = DeploymentValidator()

    def execute(self, context) -> StepResult:
        """Execute validation step.

        Args:
            context: Pipeline context

        Returns:
            Result of validation
        """
        start_time = time.time()

        try:
            # Validate deployment context
            validation_result = self.validator.validate_deployment_context(context)

            # Update context with validation results
            if not validation_result.is_valid:
                for error in validation_result.errors:
                    context.add_error(str(error))

            for warning in validation_result.warnings:
                context.add_warning(str(warning))

            # Store validation metadata
            context.results["validation"] = validation_result.to_dict()

            # Calculate execution time
            execution_time = time.time() - start_time
            context.step_timings[self.name] = execution_time

            # Determine step status
            if not validation_result.is_valid:
                status = StepStatus.FAILURE
                message = f"Validation failed with {validation_result.error_count} errors in {execution_time:.3f}s"
            elif validation_result.has_warnings:
                status = StepStatus.WARNING
                message = f"Validation completed with {validation_result.warning_count} warnings in {execution_time:.3f}s"
            else:
                status = StepStatus.SUCCESS
                message = f"Validation passed successfully in {execution_time:.3f}s"

            self.logger.info(message)

            return StepResult(
                status=status, message=message, execution_time=execution_time
            )

        except Exception as e:
            execution_time = time.time() - start_time
            context.step_timings[self.name] = execution_time

            error_msg = f"Validation step failed: {e!s}"
            self.logger.error(error_msg, exc_info=True)
            context.add_error(error_msg)

            return StepResult(
                status=StepStatus.FAILURE,
                message=error_msg,
                error=e,
                execution_time=execution_time,
            )

    def can_continue_on_failure(self) -> bool:
        """Validation failures should stop the pipeline.

        If validation fails, it's not safe to continue with deployment.

        Returns:
            False - stop pipeline on validation failure
        """
        return False

    def get_dependencies(self) -> list:
        """This step depends on target directory setup.

        Returns:
            List of required step classes
        """
        from .target_directory_step import TargetDirectorySetupStep

        return [TargetDirectorySetupStep]
