"""
Health Check Manager for Claude MPM Framework
==============================================

WHY: Orchestrates multiple health check types, provides background monitoring,
and maintains historical health data for local deployments.

DESIGN DECISION: Uses background daemon thread for continuous monitoring with
configurable check intervals. Aggregates results from all health check types
using defined priority rules.

ARCHITECTURE:
- Orchestrates HTTP, process, and resource health checks
- Background monitoring thread with configurable interval (default: 30s)
- Thread-safe status tracking with threading.Lock
- Historical health data (last 100 checks per deployment)
- Health status aggregation with priority:
  1. Process UNHEALTHY = Deployment UNHEALTHY (critical)
  2. Any check UNHEALTHY = Deployment DEGRADED (service issues)
  3. All checks HEALTHY = Deployment HEALTHY
  4. Otherwise = UNKNOWN
- Event callbacks for status changes

USAGE:
    health_manager = HealthCheckManager(
        process_manager=process_manager,
        check_interval=30,
    )
    health_manager.start_monitoring()

    # Check health on-demand
    health = health_manager.check_health(deployment_id)

    # Stop monitoring
    health_manager.stop_monitoring()
"""

import threading
from collections import defaultdict
from typing import Callable, Dict, List, Optional

from claude_mpm.core.enums import HealthStatus
from claude_mpm.services.core.base import SyncBaseService
from claude_mpm.services.core.interfaces.health import IHealthCheckManager
from claude_mpm.services.core.interfaces.process import ILocalProcessManager
from claude_mpm.services.core.models.health import DeploymentHealth, HealthCheckResult
from claude_mpm.services.local_ops.health_checks import (
    HttpHealthCheck,
    ProcessHealthCheck,
    ResourceHealthCheck,
)


class HealthCheckManager(SyncBaseService, IHealthCheckManager):
    """
    Health check orchestration and monitoring service.

    WHY: Provides comprehensive health monitoring by coordinating multiple
    check types, maintaining historical data, and enabling background monitoring.

    Thread Safety: All public methods are thread-safe with proper locking.
    """

    def __init__(
        self,
        process_manager: ILocalProcessManager,
        check_interval: int = 30,
        history_limit: int = 100,
    ):
        """
        Initialize health check manager.

        Args:
            process_manager: Process manager for deployment lookup
            check_interval: Background check interval in seconds (default: 30)
            history_limit: Maximum historical entries per deployment (default: 100)
        """
        super().__init__("HealthCheckManager")
        self.process_manager = process_manager
        self.check_interval = check_interval
        self.history_limit = history_limit

        # Initialize health check implementations
        self.http_check = HttpHealthCheck(process_manager)
        self.process_check = ProcessHealthCheck(process_manager)
        self.resource_check = ResourceHealthCheck(process_manager)

        # Background monitoring state
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        # Health history: deployment_id -> List[DeploymentHealth]
        self._health_history: Dict[str, List[DeploymentHealth]] = defaultdict(list)

        # Status change callbacks
        self._status_callbacks: List[Callable] = []

    def initialize(self) -> bool:
        """
        Initialize the health check manager.

        Returns:
            True if initialization successful
        """
        try:
            # Initialize all health check implementations
            if not self.http_check.initialize():
                self.log_error("Failed to initialize HTTP health check")
                return False

            if not self.process_check.initialize():
                self.log_error("Failed to initialize process health check")
                return False

            if not self.resource_check.initialize():
                self.log_error("Failed to initialize resource health check")
                return False

            self._initialized = True
            self.log_info("Health check manager initialized")
            return True

        except Exception as e:
            self.log_error(f"Failed to initialize: {e}")
            return False

    def shutdown(self) -> None:
        """Shutdown health check manager and stop monitoring."""
        if self._monitoring:
            self.stop_monitoring()

        # Shutdown health check implementations
        self.http_check.shutdown()
        self.process_check.shutdown()
        self.resource_check.shutdown()

        self._shutdown = True
        self.log_info("Health check manager shutdown complete")

    def check_health(self, deployment_id: str, **kwargs) -> DeploymentHealth:
        """
        Execute all health checks for a deployment.

        Args:
            deployment_id: Unique deployment identifier
            **kwargs: Optional parameters passed to health checks:
                - endpoint: HTTP endpoint URL
                - timeout: HTTP timeout in seconds
                - cpu_threshold: CPU usage threshold percentage
                - memory_threshold_mb: Memory usage threshold in MB

        Returns:
            DeploymentHealth with aggregated status and check results

        Raises:
            ValueError: If deployment_id not found
        """
        # Validate deployment exists
        deployment = self.process_manager.state_manager.get_deployment(deployment_id)
        if not deployment:
            raise ValueError(f"Deployment not found: {deployment_id}")

        # Execute all health checks
        checks: List[HealthCheckResult] = []

        # 1. Process health check (most critical)
        try:
            process_result = self.process_check.check(deployment_id, **kwargs)
            checks.append(process_result)
        except Exception as e:
            self.log_error(f"Process health check failed: {e}")
            checks.append(
                HealthCheckResult(
                    status=HealthStatus.UNKNOWN,
                    check_type="process",
                    message=f"Check failed: {e}",
                    details={"error": str(e)},
                )
            )

        # 2. Resource health check
        try:
            resource_result = self.resource_check.check(deployment_id, **kwargs)
            checks.append(resource_result)
        except Exception as e:
            self.log_error(f"Resource health check failed: {e}")
            checks.append(
                HealthCheckResult(
                    status=HealthStatus.UNKNOWN,
                    check_type="resource",
                    message=f"Check failed: {e}",
                    details={"error": str(e)},
                )
            )

        # 3. HTTP health check (optional, only if endpoint configured)
        try:
            http_result = self.http_check.check(deployment_id, **kwargs)
            # Only add if check was actually performed (not UNKNOWN due to no endpoint)
            if http_result.status != HealthStatus.UNKNOWN or kwargs.get("endpoint"):
                checks.append(http_result)
        except Exception as e:
            self.log_error(f"HTTP health check failed: {e}")
            checks.append(
                HealthCheckResult(
                    status=HealthStatus.UNKNOWN,
                    check_type="http",
                    message=f"Check failed: {e}",
                    details={"error": str(e)},
                )
            )

        # Aggregate health status
        overall_status = self._aggregate_health_status(checks)

        # Create deployment health
        deployment_health = DeploymentHealth(
            deployment_id=deployment_id,
            overall_status=overall_status,
            checks=checks,
        )

        # Update health history
        with self._lock:
            self._health_history[deployment_id].append(deployment_health)
            # Trim history to limit
            if len(self._health_history[deployment_id]) > self.history_limit:
                self._health_history[deployment_id] = self._health_history[
                    deployment_id
                ][-self.history_limit :]

            # Check for status changes and trigger callbacks
            if len(self._health_history[deployment_id]) >= 2:
                previous_health = self._health_history[deployment_id][-2]
                if previous_health.overall_status != overall_status:
                    self._trigger_status_callbacks(
                        deployment_id, previous_health.overall_status, overall_status
                    )

        return deployment_health

    def start_monitoring(self) -> None:
        """
        Start background health monitoring.

        WHY: Enables continuous health tracking without manual polling.
        Creates a daemon thread that performs periodic checks.
        """
        with self._lock:
            if self._monitoring:
                self.log_warning("Health monitoring already running")
                return

            self._monitoring = True
            self._stop_event.clear()

            # Create and start monitoring thread
            self._monitor_thread = threading.Thread(
                target=self._monitor_loop, daemon=True, name="HealthMonitorThread"
            )
            self._monitor_thread.start()

            self.log_info(
                f"Started health monitoring with {self.check_interval}s interval"
            )

    def stop_monitoring(self) -> None:
        """
        Stop background health monitoring.

        WHY: Gracefully stops the monitoring thread and releases resources.
        """
        with self._lock:
            if not self._monitoring:
                return

            self._monitoring = False
            self._stop_event.set()

        # Wait for monitoring thread to stop
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5.0)

        self.log_info("Stopped health monitoring")

    def is_monitoring(self) -> bool:
        """
        Check if background monitoring is active.

        Returns:
            True if monitoring thread is running
        """
        with self._lock:
            return self._monitoring

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
        with self._lock:
            history = self._health_history.get(deployment_id, [])
            return list(reversed(history[-limit:]))

    def register_status_callback(
        self, callback: Callable[[str, HealthStatus, HealthStatus], None]
    ) -> None:
        """
        Register a callback for health status changes.

        Args:
            callback: Function called with (deployment_id, old_status, new_status)
        """
        with self._lock:
            self._status_callbacks.append(callback)
            self.log_debug(f"Registered status callback: {callback.__name__}")

    def _monitor_loop(self) -> None:
        """
        Background monitoring loop.

        WHY: Runs in a separate thread to perform periodic health checks
        on all active deployments.
        """
        self.log_debug("Health monitoring loop started")

        while not self._stop_event.is_set():
            try:
                # Get all active deployments
                deployments = self.process_manager.state_manager.get_all_deployments()

                for deployment in deployments:
                    if self._stop_event.is_set():
                        break

                    try:
                        # Perform health check
                        self.check_health(deployment.deployment_id)
                    except Exception as e:
                        self.log_error(
                            f"Error checking health for {deployment.deployment_id}: {e}"
                        )

                # Sleep until next check interval
                # Use wait() instead of sleep() for faster shutdown response
                self._stop_event.wait(timeout=self.check_interval)

            except Exception as e:
                self.log_error(f"Error in health monitoring loop: {e}")
                # Don't crash the thread, just continue
                self._stop_event.wait(timeout=1.0)

        self.log_debug("Health monitoring loop stopped")

    def _aggregate_health_status(self, checks: List[HealthCheckResult]) -> HealthStatus:
        """
        Aggregate health status from multiple check results.

        WHY: Combines results from different check types using priority rules
        to determine overall deployment health.

        Priority Rules:
        1. Process UNHEALTHY = Deployment UNHEALTHY (critical)
        2. Any check UNHEALTHY = Deployment DEGRADED (service issues but process alive)
        3. All checks HEALTHY = Deployment HEALTHY
        4. Otherwise = UNKNOWN

        Args:
            checks: List of health check results

        Returns:
            Aggregated HealthStatus
        """
        if not checks:
            return HealthStatus.UNKNOWN

        # Get process check result (most critical)
        process_check = next((c for c in checks if c.check_type == "process"), None)

        # Rule 1: Process UNHEALTHY = Deployment UNHEALTHY
        if process_check and process_check.status == HealthStatus.UNHEALTHY:
            return HealthStatus.UNHEALTHY

        # Rule 2: Any check UNHEALTHY (but process alive) = DEGRADED
        if any(c.status == HealthStatus.UNHEALTHY for c in checks):
            return HealthStatus.DEGRADED

        # Check for degraded status
        if any(c.status == HealthStatus.DEGRADED for c in checks):
            return HealthStatus.DEGRADED

        # Rule 3: All checks HEALTHY = Deployment HEALTHY
        if all(c.status == HealthStatus.HEALTHY for c in checks):
            return HealthStatus.HEALTHY

        # Rule 4: Otherwise = UNKNOWN
        return HealthStatus.UNKNOWN

    def _trigger_status_callbacks(
        self, deployment_id: str, old_status: HealthStatus, new_status: HealthStatus
    ) -> None:
        """
        Trigger registered callbacks for status changes.

        Args:
            deployment_id: Deployment that changed status
            old_status: Previous health status
            new_status: New health status
        """
        for callback in self._status_callbacks:
            try:
                callback(deployment_id, old_status, new_status)
            except Exception as e:
                self.log_error(f"Error in status callback {callback.__name__}: {e}")


__all__ = ["HealthCheckManager"]
