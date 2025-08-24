"""Pipeline context for deployment operations."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from claude_mpm.core.config import Config

from ..strategies.base_strategy import BaseDeploymentStrategy


@dataclass
class PipelineContext:
    """Context object that flows through the deployment pipeline.

    This context contains all the data needed for deployment and is
    passed between pipeline steps. Each step can read from and modify
    the context as needed.
    """

    # Input parameters
    target_dir: Optional[Path] = None
    force_rebuild: bool = False
    deployment_mode: str = "update"
    config: Optional[Config] = None
    use_async: bool = False
    working_directory: Optional[Path] = None
    templates_dir: Optional[Path] = None
    base_agent_path: Optional[Path] = None

    # Strategy and execution context
    strategy: Optional[BaseDeploymentStrategy] = None
    actual_target_dir: Optional[Path] = None
    actual_templates_dir: Optional[Path] = None
    actual_base_agent_path: Optional[Path] = None

    # Configuration and exclusions
    excluded_agents: List[str] = field(default_factory=list)
    case_sensitive_exclusion: bool = True

    # Template and agent data
    template_files: List[Path] = field(default_factory=list)
    base_agent_data: Optional[Dict[str, Any]] = None
    base_agent_version: Optional[tuple] = None
    agent_sources: Dict[str, str] = field(
        default_factory=dict
    )  # Maps agent names to sources

    # Deployment results
    results: Dict[str, Any] = field(default_factory=dict)

    # Metrics and timing
    deployment_start_time: Optional[float] = None
    step_timings: Dict[str, float] = field(default_factory=dict)

    # Error handling
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # Step control flags
    should_deploy_system_instructions: bool = True
    should_collect_metrics: bool = True
    should_repair_existing_agents: bool = True

    def add_error(self, error: str) -> None:
        """Add an error to the context.

        Args:
            error: Error message to add
        """
        self.errors.append(error)
        if "errors" not in self.results:
            self.results["errors"] = []
        self.results["errors"].append(error)

    def add_warning(self, warning: str) -> None:
        """Add a warning to the context.

        Args:
            warning: Warning message to add
        """
        self.warnings.append(warning)
        if "warnings" not in self.results:
            self.results["warnings"] = []
        self.results["warnings"].append(warning)

    def has_errors(self) -> bool:
        """Check if there are any errors in the context.

        Returns:
            True if there are errors
        """
        return len(self.errors) > 0

    def get_error_count(self) -> int:
        """Get the number of errors.

        Returns:
            Number of errors
        """
        return len(self.errors)

    def get_warning_count(self) -> int:
        """Get the number of warnings.

        Returns:
            Number of warnings
        """
        return len(self.warnings)

    def initialize_results(self) -> None:
        """Initialize the results dictionary with default structure."""
        if not self.results:
            self.results = {
                "target_dir": (
                    str(self.actual_target_dir) if self.actual_target_dir else ""
                ),
                "deployed": [],
                "updated": [],
                "migrated": [],
                "skipped": [],
                "errors": [],
                "warnings": [],
                "repaired": [],
                "total": 0,
                "deployment_time": 0.0,
                "strategy_used": self.strategy.name if self.strategy else "Unknown",
            }

    def finalize_results(self, end_time: float) -> Dict[str, Any]:
        """Finalize the results dictionary.

        Args:
            end_time: End time of deployment

        Returns:
            Final results dictionary
        """
        if self.deployment_start_time:
            self.results["deployment_time"] = end_time - self.deployment_start_time

        # Add step timings if available
        if self.step_timings:
            self.results["step_timings"] = self.step_timings.copy()

        # Ensure all required fields are present
        for field in [
            "deployed",
            "updated",
            "migrated",
            "skipped",
            "errors",
            "warnings",
            "repaired",
        ]:
            if field not in self.results:
                self.results[field] = []

        if "total" not in self.results:
            self.results["total"] = len(self.template_files)

        return self.results.copy()
