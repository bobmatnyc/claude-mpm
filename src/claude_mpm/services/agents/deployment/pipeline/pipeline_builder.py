"""Pipeline builder for creating deployment pipelines."""

from typing import Dict, List, Type

from claude_mpm.core.logger import get_logger

from .steps.base_step import BaseDeploymentStep
from .steps.configuration_step import ConfigurationLoadStep
from .steps.target_directory_step import TargetDirectorySetupStep


class DeploymentPipelineBuilder:
    """Builder for creating deployment pipelines.

    This builder allows for flexible construction of deployment pipelines
    with different steps based on deployment requirements.
    """

    def __init__(self):
        """Initialize the pipeline builder."""
        self.logger = get_logger(__name__)
        self._steps: List[BaseDeploymentStep] = []
        self._step_registry: Dict[str, Type[BaseDeploymentStep]] = {}

        # Register default steps
        self._register_default_steps()

    def _register_default_steps(self) -> None:
        """Register default deployment steps."""
        self._step_registry.update(
            {
                "configuration": ConfigurationLoadStep,
                "target_directory": TargetDirectorySetupStep,
                # Additional steps will be registered as they're created
            }
        )

    def add_step(self, step: BaseDeploymentStep) -> "DeploymentPipelineBuilder":
        """Add a step to the pipeline.

        Args:
            step: The deployment step to add

        Returns:
            Self for method chaining
        """
        self._steps.append(step)
        self.logger.debug(f"Added step: {step.name}")
        return self

    def add_step_by_name(self, step_name: str, **kwargs) -> "DeploymentPipelineBuilder":
        """Add a step by its registered name.

        Args:
            step_name: Name of the registered step
            **kwargs: Arguments to pass to the step constructor

        Returns:
            Self for method chaining

        Raises:
            ValueError: If step name is not registered
        """
        if step_name not in self._step_registry:
            raise ValueError(f"Unknown step name: {step_name}")

        step_class = self._step_registry[step_name]
        step = step_class(**kwargs)
        return self.add_step(step)

    def create_standard_pipeline(self) -> List[BaseDeploymentStep]:
        """Create a standard deployment pipeline with all common steps.

        Returns:
            List of deployment steps in execution order
        """
        return [
            ConfigurationLoadStep(),
            TargetDirectorySetupStep(),
            # Additional steps will be added as they're implemented
        ]

    def create_minimal_pipeline(self) -> List[BaseDeploymentStep]:
        """Create a minimal deployment pipeline with only essential steps.

        Returns:
            List of essential deployment steps
        """
        return [
            ConfigurationLoadStep(),
            TargetDirectorySetupStep(),
        ]

    def create_custom_pipeline(self, step_names: List[str]) -> List[BaseDeploymentStep]:
        """Create a custom pipeline from step names.

        Args:
            step_names: List of step names to include in the pipeline

        Returns:
            List of deployment steps

        Raises:
            ValueError: If any step name is not registered
        """
        steps = []
        for step_name in step_names:
            if step_name not in self._step_registry:
                raise ValueError(f"Unknown step name: {step_name}")

            step_class = self._step_registry[step_name]
            steps.append(step_class())

        return steps

    def build(self) -> List[BaseDeploymentStep]:
        """Build the pipeline from added steps.

        Returns:
            List of deployment steps in the order they were added
        """
        if not self._steps:
            self.logger.warning(
                "No steps added to pipeline, creating standard pipeline"
            )
            return self.create_standard_pipeline()

        # Sort steps based on dependencies (simplified for now)
        # In a full implementation, this would do topological sorting
        return self._steps.copy()

    def register_step(self, name: str, step_class: Type[BaseDeploymentStep]) -> None:
        """Register a new step type.

        Args:
            name: Name to register the step under
            step_class: The step class to register
        """
        self._step_registry[name] = step_class
        self.logger.debug(f"Registered step: {name} -> {step_class.__name__}")

    def get_registered_steps(self) -> Dict[str, Type[BaseDeploymentStep]]:
        """Get all registered step types.

        Returns:
            Dictionary of step names to step classes
        """
        return self._step_registry.copy()

    def clear(self) -> "DeploymentPipelineBuilder":
        """Clear all added steps.

        Returns:
            Self for method chaining
        """
        self._steps.clear()
        self.logger.debug("Cleared all steps from pipeline builder")
        return self
