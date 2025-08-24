"""Configuration loading step for deployment pipeline."""

import time

from claude_mpm.core.config import Config

from .base_step import BaseDeploymentStep, StepResult, StepStatus


class ConfigurationLoadStep(BaseDeploymentStep):
    """Step to load and process deployment configuration."""

    def __init__(self):
        super().__init__(
            name="Configuration Loading",
            description="Load and process deployment configuration settings",
        )

    def execute(self, context) -> StepResult:
        """Execute configuration loading step.

        Args:
            context: Pipeline context

        Returns:
            Result of configuration loading
        """
        start_time = time.time()

        try:
            # Load configuration if not provided
            if context.config is None:
                self.logger.debug("Loading default configuration")
                context.config = Config()

            # Extract excluded agents
            context.excluded_agents = context.config.get(
                "agent_deployment.excluded_agents", []
            )

            # Extract case sensitivity setting
            context.case_sensitive_exclusion = context.config.get(
                "agent_deployment.case_sensitive_exclusion", True
            )

            # Log configuration details
            self.logger.info(
                f"Loaded configuration with {len(context.excluded_agents)} excluded agents"
            )
            if context.excluded_agents:
                self.logger.debug(f"Excluded agents: {context.excluded_agents}")

            execution_time = time.time() - start_time
            context.step_timings[self.name] = execution_time

            return StepResult(
                status=StepStatus.SUCCESS,
                message=f"Configuration loaded successfully in {execution_time:.3f}s",
                execution_time=execution_time,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            context.step_timings[self.name] = execution_time

            error_msg = f"Failed to load configuration: {e!s}"
            self.logger.error(error_msg)
            context.add_error(error_msg)

            return StepResult(
                status=StepStatus.FAILURE,
                message=error_msg,
                error=e,
                execution_time=execution_time,
            )

    def can_continue_on_failure(self) -> bool:
        """Configuration loading failure should stop the pipeline."""
        return False
