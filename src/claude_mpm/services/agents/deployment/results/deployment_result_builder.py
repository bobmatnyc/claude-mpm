"""Deployment result builder for creating structured deployment results."""

from pathlib import Path
from typing import Any, Dict, Optional

from claude_mpm.core.logger import get_logger

from .deployment_metrics import DeploymentMetrics


class DeploymentResultBuilder:
    """Builder for creating structured deployment results.

    This class provides a clean interface for building deployment
    results with proper structure and metrics collection.
    """

    def __init__(self):
        """Initialize the deployment result builder."""
        self.logger = get_logger(__name__)
        self.metrics = DeploymentMetrics()
        self._results: Dict[str, Any] = {}
        self._initialized = False

    def initialize(
        self,
        target_dir: Optional[Path] = None,
        strategy_name: Optional[str] = None,
        deployment_mode: Optional[str] = None,
    ) -> "DeploymentResultBuilder":
        """Initialize the result builder with basic information.

        Args:
            target_dir: Target directory for deployment
            strategy_name: Name of deployment strategy used
            deployment_mode: Deployment mode used

        Returns:
            Self for method chaining
        """
        self._results = {
            "target_dir": str(target_dir) if target_dir else "",
            "deployed": [],
            "updated": [],
            "migrated": [],
            "skipped": [],
            "errors": [],
            "warnings": [],
            "repaired": [],
            "total": 0,
            "deployment_time": 0.0,
            "strategy_used": strategy_name or "Unknown",
            "deployment_mode": deployment_mode or "update",
        }

        # Update metrics
        self.metrics.strategy_used = strategy_name
        self.metrics.deployment_mode = deployment_mode
        self.metrics.target_directory = str(target_dir) if target_dir else None

        self._initialized = True
        self.logger.debug("Result builder initialized")
        return self

    def set_total_agents(self, total: int) -> "DeploymentResultBuilder":
        """Set the total number of agents being processed.

        Args:
            total: Total number of agents

        Returns:
            Self for method chaining
        """
        self._results["total"] = total
        self.metrics.total_agents = total
        return self

    def add_deployed_agent(
        self, agent_name: str, deployment_time: Optional[float] = None
    ) -> "DeploymentResultBuilder":
        """Add a deployed agent to results.

        Args:
            agent_name: Name of the deployed agent
            deployment_time: Time taken to deploy the agent

        Returns:
            Self for method chaining
        """
        self._results["deployed"].append(agent_name)
        self.metrics.add_deployed_agent(agent_name, deployment_time)
        return self

    def add_updated_agent(
        self, agent_name: str, deployment_time: Optional[float] = None
    ) -> "DeploymentResultBuilder":
        """Add an updated agent to results.

        Args:
            agent_name: Name of the updated agent
            deployment_time: Time taken to update the agent

        Returns:
            Self for method chaining
        """
        self._results["updated"].append(agent_name)
        self.metrics.add_updated_agent(agent_name, deployment_time)
        return self

    def add_migrated_agent(self, agent_name: str) -> "DeploymentResultBuilder":
        """Add a migrated agent to results.

        Args:
            agent_name: Name of the migrated agent

        Returns:
            Self for method chaining
        """
        self._results["migrated"].append(agent_name)
        self.metrics.add_migrated_agent(agent_name)
        return self

    def add_skipped_agent(
        self, agent_name: str, reason: Optional[str] = None
    ) -> "DeploymentResultBuilder":
        """Add a skipped agent to results.

        Args:
            agent_name: Name of the skipped agent
            reason: Optional reason for skipping

        Returns:
            Self for method chaining
        """
        self._results["skipped"].append(agent_name)
        self.metrics.add_skipped_agent(agent_name, reason)
        return self

    def add_repaired_agent(self, agent_name: str) -> "DeploymentResultBuilder":
        """Add a repaired agent to results.

        Args:
            agent_name: Name of the repaired agent

        Returns:
            Self for method chaining
        """
        self._results["repaired"].append(agent_name)
        self.metrics.add_repaired_agent(agent_name)
        return self

    def add_error(self, error: str) -> "DeploymentResultBuilder":
        """Add an error to results.

        Args:
            error: Error message

        Returns:
            Self for method chaining
        """
        self._results["errors"].append(error)
        self.metrics.add_error(error)
        return self

    def add_warning(self, warning: str) -> "DeploymentResultBuilder":
        """Add a warning to results.

        Args:
            warning: Warning message

        Returns:
            Self for method chaining
        """
        self._results["warnings"].append(warning)
        self.metrics.add_warning(warning)
        return self

    def add_step_timing(
        self, step_name: str, duration: float
    ) -> "DeploymentResultBuilder":
        """Add timing information for a step.

        Args:
            step_name: Name of the step
            duration: Duration in seconds

        Returns:
            Self for method chaining
        """
        self.metrics.step_timings[step_name] = duration
        return self

    def add_metadata(self, key: str, value: Any) -> "DeploymentResultBuilder":
        """Add metadata to results.

        Args:
            key: Metadata key
            value: Metadata value

        Returns:
            Self for method chaining
        """
        self.metrics.metadata[key] = value
        return self

    def build(self) -> Dict[str, Any]:
        """Build the final results dictionary.

        Returns:
            Complete deployment results dictionary
        """
        if not self._initialized:
            self.logger.warning("Result builder not initialized, using defaults")
            self.initialize()

        # Finalize metrics
        self.metrics.finalize()

        # Update results with final timing
        self._results["deployment_time"] = self.metrics.total_duration or 0.0

        # Add step timings if available
        if self.metrics.step_timings:
            self._results["step_timings"] = self.metrics.step_timings.copy()

        # Add metrics summary
        self._results["metrics"] = self.metrics.get_summary()

        # Add detailed metrics if requested
        self._results["detailed_metrics"] = {
            "deployed_agents": self.metrics.deployed_agent_names,
            "updated_agents": self.metrics.updated_agent_names,
            "migrated_agents": self.metrics.migrated_agent_names,
            "skipped_agents": self.metrics.skipped_agent_names,
            "repaired_agents": self.metrics.repaired_agent_names,
            "failed_agents": self.metrics.failed_agent_names,
            "success_rate": self.metrics.get_success_rate(),
        }

        self.logger.debug(f"Built deployment results with {len(self._results)} fields")
        return self._results.copy()

    def get_metrics(self) -> DeploymentMetrics:
        """Get the metrics object.

        Returns:
            DeploymentMetrics object
        """
        return self.metrics
