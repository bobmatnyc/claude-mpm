"""Target directory setup step for deployment pipeline."""

import time
from pathlib import Path

from .base_step import BaseDeploymentStep, StepResult, StepStatus


class TargetDirectorySetupStep(BaseDeploymentStep):
    """Step to determine and setup the target directory for deployment."""

    def __init__(self):
        super().__init__(
            name="Target Directory Setup",
            description="Determine and create the target directory for agent deployment",
        )

    def execute(self, context) -> StepResult:
        """Execute target directory setup step.

        Args:
            context: Pipeline context

        Returns:
            Result of target directory setup
        """
        start_time = time.time()

        try:
            # Use strategy to determine target directory
            if context.strategy:
                context.actual_target_dir = context.strategy.determine_target_directory(
                    context  # Pass the context which has the DeploymentContext interface
                )
            # Fallback logic if no strategy is set
            elif context.target_dir:
                context.actual_target_dir = context.target_dir
            else:
                # MODIFIED: Default to project .claude/agents directory
                # All agents now deploy to the project level
                context.actual_target_dir = Path.cwd() / ".claude" / "agents"

            # Create target directory if it doesn't exist
            context.actual_target_dir.mkdir(parents=True, exist_ok=True)

            # Verify directory is writable
            test_file = context.actual_target_dir / ".write_test"
            try:
                test_file.write_text("test")
                test_file.unlink()
            except Exception:
                raise PermissionError(
                    f"Target directory is not writable: {context.actual_target_dir}"
                )

            self.logger.info(f"Target directory set up: {context.actual_target_dir}")

            execution_time = time.time() - start_time
            context.step_timings[self.name] = execution_time

            return StepResult(
                status=StepStatus.SUCCESS,
                message=f"Target directory set up at {context.actual_target_dir} in {execution_time:.3f}s",
                execution_time=execution_time,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            context.step_timings[self.name] = execution_time

            error_msg = f"Failed to set up target directory: {e!s}"
            self.logger.error(error_msg)
            context.add_error(error_msg)

            return StepResult(
                status=StepStatus.FAILURE,
                message=error_msg,
                error=e,
                execution_time=execution_time,
            )

    def can_continue_on_failure(self) -> bool:
        """Target directory setup failure should stop the pipeline."""
        return False

    def get_dependencies(self) -> list:
        """This step depends on configuration loading."""
        from .configuration_step import ConfigurationLoadStep

        return [ConfigurationLoadStep]
