"""
Health Check Interfaces for Claude MPM Framework
=================================================

WHY: This module defines interfaces for health monitoring operations,
enabling the local-ops-agent to perform comprehensive health checks on
deployed processes including HTTP endpoints, process status, and resource usage.

DESIGN DECISION: Health check interfaces are separated to enable modular
health monitoring with different check types (HTTP, process, resource).

ARCHITECTURE:
- IHealthCheck: Interface for individual health check implementations
- IHealthCheckManager: Interface for orchestrating multiple health checks
- Health data models defined in models/health.py

USAGE:
    http_check = HttpHealthCheck(endpoint="http://localhost:3000/health")
    process_check = ProcessHealthCheck(process_manager)
    resource_check = ResourceHealthCheck(process_manager)

    health_manager = HealthCheckManager(
        process_manager=process_manager,
        check_interval=30
    )
    health_manager.start_monitoring()
"""

from abc import ABC, abstractmethod
from typing import List

from claude_mpm.services.core.models.health import DeploymentHealth, HealthCheckResult


class IHealthCheck(ABC):
    """
    Interface for individual health check implementations.

    WHY: Abstracts different types of health checks (HTTP, process, resource)
    to enable flexible health monitoring strategies.

    DESIGN DECISION: Each check type implements this interface to provide
    a consistent API for executing checks and interpreting results.

    Thread Safety: Implementations must be thread-safe for concurrent execution.
    """

    @abstractmethod
    def check(self, deployment_id: str, **kwargs) -> HealthCheckResult:
        """
        Execute the health check for a deployment.

        Args:
            deployment_id: Unique deployment identifier
            **kwargs: Check-specific parameters (e.g., endpoint URL, thresholds)

        Returns:
            HealthCheckResult with check status and details

        Raises:
            ValueError: If deployment_id not found
        """

    @abstractmethod
    def get_check_type(self) -> str:
        """
        Get the type identifier for this health check.

        Returns:
            Check type string (e.g., "http", "process", "resource")
        """


class IHealthCheckManager(ABC):
    """
    Interface for coordinating health checks across deployments.

    WHY: Health monitoring requires orchestrating multiple check types,
    aggregating results, and maintaining historical data. This interface
    provides a high-level API for comprehensive health monitoring.

    DESIGN DECISION: Provides both synchronous (check_health) and asynchronous
    (background monitoring) operations to support different use cases.

    Background Monitoring:
    - Runs health checks at regular intervals
    - Maintains historical health data
    - Triggers callbacks on status changes
    - Thread-safe with proper locking
    """

    @abstractmethod
    def check_health(self, deployment_id: str) -> DeploymentHealth:
        """
        Execute all health checks for a deployment.

        WHY: Provides a comprehensive health snapshot by running all
        registered health checks and aggregating results.

        Args:
            deployment_id: Unique deployment identifier

        Returns:
            DeploymentHealth with aggregated status and check results

        Raises:
            ValueError: If deployment_id not found
        """

    @abstractmethod
    def start_monitoring(self) -> None:
        """
        Start background health monitoring.

        WHY: Enables continuous health tracking without manual polling.
        Monitoring runs in a separate daemon thread.

        Thread Safety: Creates a daemon thread that performs periodic checks.
        """

    @abstractmethod
    def stop_monitoring(self) -> None:
        """
        Stop background health monitoring.

        WHY: Gracefully stops the monitoring thread and releases resources.
        """

    @abstractmethod
    def is_monitoring(self) -> bool:
        """
        Check if background monitoring is active.

        Returns:
            True if monitoring thread is running
        """

    @abstractmethod
    def get_health_history(
        self, deployment_id: str, limit: int = 10
    ) -> List[DeploymentHealth]:
        """
        Get historical health check results for a deployment.

        Args:
            deployment_id: Unique deployment identifier
            limit: Maximum number of historical entries to return

        Returns:
            List of DeploymentHealth objects, newest first
        """

    @abstractmethod
    def register_status_callback(self, callback) -> None:
        """
        Register a callback for health status changes.

        WHY: Enables reactive behavior based on health status changes
        (e.g., alerts, auto-recovery, logging).

        Args:
            callback: Function called with (deployment_id, old_status, new_status)
        """


__all__ = [
    "IHealthCheck",
    "IHealthCheckManager",
]
