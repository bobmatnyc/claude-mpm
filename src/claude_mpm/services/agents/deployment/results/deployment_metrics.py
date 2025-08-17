"""Deployment metrics data class."""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DeploymentMetrics:
    """Metrics collected during agent deployment.

    This class encapsulates all metrics and timing information
    collected during the deployment process.
    """

    # Timing metrics
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    total_duration: Optional[float] = None

    # Step timing metrics
    step_timings: Dict[str, float] = field(default_factory=dict)

    # Agent metrics
    total_agents: int = 0
    deployed_agents: int = 0
    updated_agents: int = 0
    migrated_agents: int = 0
    skipped_agents: int = 0
    repaired_agents: int = 0
    failed_agents: int = 0

    # Agent lists for detailed tracking
    deployed_agent_names: List[str] = field(default_factory=list)
    updated_agent_names: List[str] = field(default_factory=list)
    migrated_agent_names: List[str] = field(default_factory=list)
    skipped_agent_names: List[str] = field(default_factory=list)
    repaired_agent_names: List[str] = field(default_factory=list)
    failed_agent_names: List[str] = field(default_factory=list)

    # Error and warning tracking
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # Performance metrics
    average_agent_deployment_time: Optional[float] = None
    fastest_agent_deployment: Optional[float] = None
    slowest_agent_deployment: Optional[float] = None

    # Strategy and configuration info
    strategy_used: Optional[str] = None
    deployment_mode: Optional[str] = None
    target_directory: Optional[str] = None

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def finalize(self, end_time: Optional[float] = None) -> None:
        """Finalize metrics calculation.

        Args:
            end_time: Optional end time, defaults to current time
        """
        if end_time is None:
            end_time = time.time()

        self.end_time = end_time
        self.total_duration = end_time - self.start_time

        # Calculate performance metrics
        if self.step_timings:
            agent_times = [
                t for name, t in self.step_timings.items() if "agent" in name.lower()
            ]
            if agent_times:
                self.average_agent_deployment_time = sum(agent_times) / len(agent_times)
                self.fastest_agent_deployment = min(agent_times)
                self.slowest_agent_deployment = max(agent_times)

    def add_deployed_agent(
        self, agent_name: str, deployment_time: Optional[float] = None
    ) -> None:
        """Add a deployed agent to metrics.

        Args:
            agent_name: Name of the deployed agent
            deployment_time: Time taken to deploy the agent
        """
        self.deployed_agents += 1
        self.deployed_agent_names.append(agent_name)

        if deployment_time is not None:
            self.step_timings[f"agent_{agent_name}"] = deployment_time

    def add_updated_agent(
        self, agent_name: str, deployment_time: Optional[float] = None
    ) -> None:
        """Add an updated agent to metrics.

        Args:
            agent_name: Name of the updated agent
            deployment_time: Time taken to update the agent
        """
        self.updated_agents += 1
        self.updated_agent_names.append(agent_name)

        if deployment_time is not None:
            self.step_timings[f"agent_{agent_name}"] = deployment_time

    def add_migrated_agent(self, agent_name: str) -> None:
        """Add a migrated agent to metrics.

        Args:
            agent_name: Name of the migrated agent
        """
        self.migrated_agents += 1
        self.migrated_agent_names.append(agent_name)

    def add_skipped_agent(self, agent_name: str, reason: Optional[str] = None) -> None:
        """Add a skipped agent to metrics.

        Args:
            agent_name: Name of the skipped agent
            reason: Optional reason for skipping
        """
        self.skipped_agents += 1
        self.skipped_agent_names.append(agent_name)

        if reason:
            self.metadata[f"skip_reason_{agent_name}"] = reason

    def add_repaired_agent(self, agent_name: str) -> None:
        """Add a repaired agent to metrics.

        Args:
            agent_name: Name of the repaired agent
        """
        self.repaired_agents += 1
        self.repaired_agent_names.append(agent_name)

    def add_failed_agent(self, agent_name: str, error: str) -> None:
        """Add a failed agent to metrics.

        Args:
            agent_name: Name of the failed agent
            error: Error message
        """
        self.failed_agents += 1
        self.failed_agent_names.append(agent_name)
        self.errors.append(f"Agent {agent_name}: {error}")

    def add_error(self, error: str) -> None:
        """Add a general error to metrics.

        Args:
            error: Error message
        """
        self.errors.append(error)

    def add_warning(self, warning: str) -> None:
        """Add a warning to metrics.

        Args:
            warning: Warning message
        """
        self.warnings.append(warning)

    def get_success_rate(self) -> float:
        """Calculate deployment success rate.

        Returns:
            Success rate as a percentage (0-100)
        """
        if self.total_agents == 0:
            return 100.0

        successful = self.deployed_agents + self.updated_agents + self.skipped_agents
        return (successful / self.total_agents) * 100.0

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of deployment metrics.

        Returns:
            Dictionary with metric summary
        """
        return {
            "total_duration": self.total_duration,
            "total_agents": self.total_agents,
            "deployed": self.deployed_agents,
            "updated": self.updated_agents,
            "migrated": self.migrated_agents,
            "skipped": self.skipped_agents,
            "repaired": self.repaired_agents,
            "failed": self.failed_agents,
            "success_rate": self.get_success_rate(),
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "strategy_used": self.strategy_used,
            "deployment_mode": self.deployment_mode,
        }
