"""Base deployment step interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from claude_mpm.core.enums import OperationResult
from claude_mpm.core.logger import get_logger


@dataclass
class StepResult:
    """Result of executing a pipeline step."""

    status: OperationResult
    message: Optional[str] = None
    error: Optional[Exception] = None
    execution_time: Optional[float] = None

    @property
    def is_success(self) -> bool:
        """Check if the step was successful."""
        return self.status == OperationResult.SUCCESS

    @property
    def is_failure(self) -> bool:
        """Check if the step failed."""
        return self.status == OperationResult.FAILED

    @property
    def is_skipped(self) -> bool:
        """Check if the step was skipped."""
        return self.status == OperationResult.SKIPPED

    @property
    def is_warning(self) -> bool:
        """Check if the step completed with warnings."""
        return self.status == OperationResult.WARNING


class BaseDeploymentStep(ABC):
    """Base class for all deployment pipeline steps.

    Each step in the deployment pipeline should inherit from this class
    and implement the execute method. Steps can read from and modify
    the pipeline context as needed.
    """

    def __init__(self, name: str, description: str = ""):
        """Initialize the deployment step.

        Args:
            name: Human-readable name for this step
            description: Optional description of what this step does
        """
        self.name = name
        self.description = description
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    def execute(self, context) -> "StepResult":
        """Execute this deployment step.

        Args:
            context: Pipeline context containing deployment data

        Returns:
            Result of executing this step
        """

    def should_execute(self, context) -> bool:
        """Check if this step should be executed.

        Override this method to add conditional execution logic.

        Args:
            context: Pipeline context

        Returns:
            True if this step should be executed
        """
        return True

    def can_continue_on_failure(self) -> bool:
        """Check if pipeline can continue if this step fails.

        Override this method for steps that are not critical.

        Returns:
            True if pipeline can continue after this step fails
        """
        return False

    def get_dependencies(self) -> list:
        """Get list of step classes this step depends on.

        Override this method to specify dependencies.

        Returns:
            List of step classes that must execute before this step
        """
        return []

    def __str__(self) -> str:
        """String representation of the step."""
        return f"{self.name}"

    def __repr__(self) -> str:
        """Detailed string representation of the step."""
        return f"{self.__class__.__name__}(name='{self.name}', description='{self.description}')"
