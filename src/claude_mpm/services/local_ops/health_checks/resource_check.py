"""
Resource Health Check for Claude MPM Framework
===============================================

WHY: Provides resource usage monitoring including CPU, memory, file descriptors,
threads, and network connections to detect resource exhaustion issues.

DESIGN DECISION: Uses psutil for cross-platform resource monitoring with
configurable thresholds for different resource types.

ARCHITECTURE:
- CPU usage monitoring (threshold: 80%)
- Memory usage monitoring (threshold: 500MB)
- File descriptor count (threshold: 1000, Unix only)
- Thread count monitoring
- Network connection count (open sockets)

USAGE:
    resource_check = ResourceHealthCheck(process_manager)
    result = resource_check.check(
        deployment_id="my-app",
        cpu_threshold=80.0,
        memory_threshold_mb=500.0
    )
"""

import platform

import psutil

from claude_mpm.core.enums import HealthStatus
from claude_mpm.services.core.base import SyncBaseService
from claude_mpm.services.core.interfaces.health import IHealthCheck
from claude_mpm.services.core.interfaces.process import ILocalProcessManager
from claude_mpm.services.core.models.health import HealthCheckResult


class ResourceHealthCheck(SyncBaseService, IHealthCheck):
    """
    Resource usage health check implementation.

    WHY: Monitors resource consumption to detect issues before they
    cause service degradation or failures.

    Thread Safety: Stateless, safe for concurrent execution.
    """

    # Default thresholds
    DEFAULT_CPU_THRESHOLD = 80.0  # Percentage
    DEFAULT_MEMORY_THRESHOLD_MB = 500.0  # Megabytes
    DEFAULT_FD_THRESHOLD = 1000  # File descriptors (Unix only)
    DEFAULT_THREAD_THRESHOLD = 100  # Threads

    def __init__(self, process_manager: ILocalProcessManager):
        """
        Initialize resource health check.

        Args:
            process_manager: Process manager for deployment lookup
        """
        super().__init__("ResourceHealthCheck")
        self.process_manager = process_manager
        self.is_windows = platform.system() == "Windows"

    def initialize(self) -> bool:
        """
        Initialize the health check.

        Returns:
            True if initialization successful
        """
        self._initialized = True
        self.log_info("Resource health check initialized")
        return True

    def shutdown(self) -> None:
        """Shutdown health check (no resources to clean up)."""
        self._shutdown = True

    def get_check_type(self) -> str:
        """Get the check type identifier."""
        return "resource"

    def check(self, deployment_id: str, **kwargs) -> HealthCheckResult:
        """
        Execute resource health check for a deployment.

        Args:
            deployment_id: Unique deployment identifier
            **kwargs: Optional parameters:
                - cpu_threshold: CPU usage threshold percentage (default: 80.0)
                - memory_threshold_mb: Memory usage threshold in MB (default: 500.0)
                - fd_threshold: File descriptor threshold (default: 1000, Unix only)
                - thread_threshold: Thread count threshold (default: 100)

        Returns:
            HealthCheckResult with check status and details

        Raises:
            ValueError: If deployment_id not found
        """
        # Validate deployment exists
        deployment = self.process_manager.state_manager.get_deployment(deployment_id)
        if not deployment:
            raise ValueError(f"Deployment not found: {deployment_id}")

        # Get thresholds from kwargs
        cpu_threshold = kwargs.get("cpu_threshold", self.DEFAULT_CPU_THRESHOLD)
        memory_threshold_mb = kwargs.get(
            "memory_threshold_mb", self.DEFAULT_MEMORY_THRESHOLD_MB
        )
        fd_threshold = kwargs.get("fd_threshold", self.DEFAULT_FD_THRESHOLD)
        thread_threshold = kwargs.get("thread_threshold", self.DEFAULT_THREAD_THRESHOLD)

        try:
            process = psutil.Process(deployment.process_id)

            # Collect resource metrics
            details = {
                "pid": deployment.process_id,
                "deployment_id": deployment_id,
            }

            issues = []

            # Check CPU usage
            try:
                cpu_percent = process.cpu_percent(interval=0.1)
                details["cpu_percent"] = round(cpu_percent, 2)
                details["cpu_threshold"] = cpu_threshold

                if cpu_percent > cpu_threshold:
                    issues.append(
                        f"High CPU usage: {cpu_percent:.1f}% (threshold: {cpu_threshold}%)"
                    )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

            # Check memory usage
            try:
                memory_info = process.memory_info()
                memory_mb = memory_info.rss / (1024 * 1024)
                details["memory_mb"] = round(memory_mb, 2)
                details["memory_threshold_mb"] = memory_threshold_mb

                if memory_mb > memory_threshold_mb:
                    issues.append(
                        f"High memory usage: {memory_mb:.1f}MB (threshold: {memory_threshold_mb}MB)"
                    )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

            # Check file descriptors (Unix only)
            if not self.is_windows:
                try:
                    num_fds = process.num_fds()
                    details["num_fds"] = num_fds
                    details["fd_threshold"] = fd_threshold

                    if num_fds > fd_threshold:
                        issues.append(
                            f"High file descriptor count: {num_fds} (threshold: {fd_threshold})"
                        )
                except (
                    psutil.NoSuchProcess,
                    psutil.AccessDenied,
                    AttributeError,
                ):
                    # num_fds() not available on all platforms
                    pass

            # Check thread count
            try:
                num_threads = process.num_threads()
                details["num_threads"] = num_threads
                details["thread_threshold"] = thread_threshold

                if num_threads > thread_threshold:
                    issues.append(
                        f"High thread count: {num_threads} (threshold: {thread_threshold})"
                    )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

            # Check connection count
            try:
                connections = process.net_connections()
                num_connections = len(connections)
                details["num_connections"] = num_connections

                # Add connection breakdown by state
                connection_states = {}
                for conn in connections:
                    state = conn.status
                    connection_states[state] = connection_states.get(state, 0) + 1
                details["connection_states"] = connection_states
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

            # Determine health status based on issues
            if issues:
                return HealthCheckResult(
                    status=HealthStatus.DEGRADED,
                    check_type=self.get_check_type(),
                    message=f"Resource usage issues detected: {'; '.join(issues)}",
                    details=details,
                )
            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                check_type=self.get_check_type(),
                message="Resource usage within normal limits",
                details=details,
            )

        except psutil.NoSuchProcess:
            # Process does not exist
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                check_type=self.get_check_type(),
                message="Process no longer exists",
                details={
                    "pid": deployment.process_id,
                    "deployment_id": deployment_id,
                },
            )

        except psutil.AccessDenied as e:
            # Cannot access process information
            return HealthCheckResult(
                status=HealthStatus.UNKNOWN,
                check_type=self.get_check_type(),
                message="Cannot access process resource information",
                details={
                    "pid": deployment.process_id,
                    "deployment_id": deployment_id,
                    "error": str(e),
                },
            )

        except Exception as e:
            # Unexpected error
            self.log_error(f"Unexpected error in resource health check: {e}")
            return HealthCheckResult(
                status=HealthStatus.UNKNOWN,
                check_type=self.get_check_type(),
                message="Health check failed with error",
                details={
                    "pid": deployment.process_id,
                    "deployment_id": deployment_id,
                    "error": str(e),
                },
            )


__all__ = ["ResourceHealthCheck"]
