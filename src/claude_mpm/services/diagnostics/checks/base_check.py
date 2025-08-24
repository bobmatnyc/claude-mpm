"""
Base interface for diagnostic checks.

WHY: Define a consistent interface for all diagnostic checks to ensure
they can be easily added, tested, and executed by the diagnostic runner.
"""

from abc import ABC, abstractmethod

from ..models import DiagnosticResult


class BaseDiagnosticCheck(ABC):
    """Base class for all diagnostic checks.

    WHY: Ensures all checks follow the same pattern and can be
    executed uniformly by the diagnostic runner.
    """

    def __init__(self, verbose: bool = False):
        """Initialize the check.

        Args:
            verbose: Whether to include detailed information in results
        """
        self.verbose = verbose

    @property
    @abstractmethod
    def name(self) -> str:
        """Get the name of this check."""

    @property
    @abstractmethod
    def category(self) -> str:
        """Get the category this check belongs to."""

    @property
    def description(self) -> str:
        """Get a description of what this check does."""
        return f"Checking {self.category.lower()} health"

    @abstractmethod
    def run(self) -> DiagnosticResult:
        """Run the diagnostic check.

        Returns:
            DiagnosticResult with the check results
        """

    def should_run(self) -> bool:
        """Determine if this check should run.

        WHY: Some checks may not be applicable in certain environments
        or configurations. This allows checks to opt out gracefully.

        Returns:
            True if the check should run, False to skip
        """
        return True
