"""
Resource Monitor for Claude MPM Framework
==========================================

WHY: Monitors multiple resource types (file descriptors, threads, connections,
disk space) to detect resource exhaustion BEFORE it causes crashes or degradation.

DESIGN DECISION: Extends basic resource health checks with higher granularity,
percentage-based thresholds (80% of limits), and preemptive alerting.

ARCHITECTURE:
- File descriptor monitoring (Unix: ulimit -n, Windows: handle count)
- Thread count monitoring
- Network connection monitoring
- Disk space monitoring (working directory)
- 80% threshold for preemptive alerts
- Callback system for critical resource usage
- Thread-safe with proper locking

USAGE:
    monitor = ResourceMonitor(
        process_manager=process_manager,
        fd_threshold_percent=0.8,
        thread_threshold=1000,
        connection_threshold=500,
        disk_threshold_mb=100,
    )
    monitor.initialize()

    # Check resources
    usage = monitor.check_resources(deployment_id)
    if usage.is_critical:
        print(f"Critical resources: {usage.get_critical_resources()}")
"""

import platform
import resource as resource_module
import shutil
import threading
from typing import Callable, Dict, List

import psutil

from claude_mpm.services.core.base import SyncBaseService
from claude_mpm.services.core.interfaces.process import ILocalProcessManager
from claude_mpm.services.core.interfaces.stability import IResourceMonitor
from claude_mpm.services.core.models.stability import ResourceUsage


class ResourceMonitor(SyncBaseService, IResourceMonitor):
    """
    Comprehensive resource usage monitoring service.

    WHY: Provides early warning of resource exhaustion by monitoring multiple
    resource types and detecting when usage approaches limits (80% threshold).

    Thread Safety: All public methods are thread-safe with proper locking.
    """

    def __init__(
        self,
        process_manager: ILocalProcessManager,
        fd_threshold_percent: float = 0.8,
        thread_threshold: int = 1000,
        connection_threshold: int = 500,
        disk_threshold_mb: float = 100.0,
    ):
        """
        Initialize resource monitor.

        Args:
            process_manager: Process manager for deployment lookup
            fd_threshold_percent: File descriptor threshold as percent of ulimit (default: 0.8)
            thread_threshold: Thread count threshold (default: 1000)
            connection_threshold: Connection count threshold (default: 500)
            disk_threshold_mb: Minimum free disk space in MB (default: 100)
        """
        super().__init__("ResourceMonitor")
        self.process_manager = process_manager
        self.fd_threshold_percent = fd_threshold_percent
        self.thread_threshold = thread_threshold
        self.connection_threshold = connection_threshold
        self.disk_threshold_mb = disk_threshold_mb

        # Platform detection
        self.is_windows = platform.system() == "Windows"
        self.is_unix = not self.is_windows

        # Critical resource callbacks
        self._critical_callbacks: List[Callable[[str, ResourceUsage], None]] = []

        # Thread safety
        self._lock = threading.Lock()

    def initialize(self) -> bool:
        """
        Initialize the resource monitor.

        Returns:
            True if initialization successful
        """
        self._initialized = True
        self.log_info(
            f"Resource monitor initialized "
            f"(fd_threshold={self.fd_threshold_percent * 100:.0f}%, "
            f"thread_threshold={self.thread_threshold}, "
            f"connection_threshold={self.connection_threshold}, "
            f"disk_threshold={self.disk_threshold_mb}MB)"
        )
        return True

    def shutdown(self) -> None:
        """Shutdown resource monitor and clear callbacks."""
        with self._lock:
            self._critical_callbacks.clear()

        self._shutdown = True
        self.log_info("Resource monitor shutdown complete")

    def check_resources(self, deployment_id: str) -> ResourceUsage:
        """
        Check resource usage for a deployment.

        WHY: Provides comprehensive snapshot of resource consumption across
        all monitored resource types.

        Args:
            deployment_id: Deployment identifier

        Returns:
            ResourceUsage with current metrics and critical status

        Raises:
            ValueError: If deployment not found
        """
        # Validate deployment exists
        deployment = self.process_manager.state_manager.get_deployment(deployment_id)
        if not deployment:
            raise ValueError(f"Deployment not found: {deployment_id}")

        try:
            process = psutil.Process(deployment.process_id)

            # Initialize usage object
            usage = ResourceUsage(deployment_id=deployment_id)
            details = {}

            # 1. Check file descriptors (Unix only)
            if self.is_unix:
                try:
                    num_fds = process.num_fds()
                    max_fds = self._get_max_fds()

                    usage.file_descriptors = num_fds
                    usage.max_file_descriptors = max_fds
                    details["fd_usage_percent"] = usage.fd_usage_percent
                except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
                    pass

            # 2. Check thread count
            try:
                num_threads = process.num_threads()
                usage.threads = num_threads
                details["thread_threshold"] = self.thread_threshold
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

            # 3. Check connection count
            try:
                connections = process.net_connections()
                usage.connections = len(connections)
                details["connection_threshold"] = self.connection_threshold

                # Add connection breakdown by state
                connection_states: Dict[str, int] = {}
                for conn in connections:
                    state = conn.status
                    connection_states[state] = connection_states.get(state, 0) + 1
                details["connection_states"] = connection_states
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

            # 4. Check disk space
            try:
                working_dir = deployment.working_directory
                disk_usage = shutil.disk_usage(working_dir)
                disk_free_mb = disk_usage.free / (1024 * 1024)
                usage.disk_free_mb = disk_free_mb
                details["disk_threshold_mb"] = self.disk_threshold_mb
            except (OSError, FileNotFoundError):
                pass

            # Store thresholds in details
            details["fd_threshold_percent"] = self.fd_threshold_percent
            details["thread_threshold"] = self.thread_threshold
            details["connection_threshold"] = self.connection_threshold
            details["disk_threshold_mb"] = self.disk_threshold_mb
            usage.details = details

            # 5. Determine if any resource is critical
            is_critical = self._check_critical(usage)
            usage.is_critical = is_critical

            # Trigger callbacks if critical
            if is_critical:
                critical_resources = usage.get_critical_resources()
                self.log_warning(
                    f"Critical resource usage for {deployment_id}: "
                    f"{', '.join(critical_resources)}"
                )
                self._trigger_critical_callbacks(deployment_id, usage)

            return usage

        except psutil.NoSuchProcess:
            # Process does not exist
            return ResourceUsage(
                deployment_id=deployment_id,
                is_critical=True,
                details={"error": "Process no longer exists"},
            )

        except psutil.AccessDenied as e:
            # Cannot access process information
            return ResourceUsage(
                deployment_id=deployment_id,
                is_critical=False,
                details={"error": f"Access denied: {e}"},
            )

        except Exception as e:
            # Unexpected error
            self.log_error(f"Unexpected error checking resources: {e}")
            return ResourceUsage(
                deployment_id=deployment_id,
                is_critical=False,
                details={"error": str(e)},
            )

    def is_critical(self, deployment_id: str) -> bool:
        """
        Check if any resource is at critical threshold (>80%).

        Returns:
            True if any resource exceeds 80% of limit
        """
        try:
            usage = self.check_resources(deployment_id)
            return usage.is_critical
        except ValueError:
            return False

    def register_critical_callback(
        self, callback: Callable[[str, ResourceUsage], None]
    ) -> None:
        """
        Register callback for critical resource usage.

        Args:
            callback: Function called with (deployment_id, usage) when critical
        """
        with self._lock:
            self._critical_callbacks.append(callback)
            self.log_debug(f"Registered critical callback: {callback.__name__}")

    def _check_critical(self, usage: ResourceUsage) -> bool:
        """
        Check if resource usage is at critical levels.

        Args:
            usage: ResourceUsage to check

        Returns:
            True if any resource is critical (>80% threshold)
        """
        # Check file descriptors
        if usage.max_file_descriptors > 0:
            fd_percent = usage.fd_usage_percent / 100.0
            if fd_percent > self.fd_threshold_percent:
                return True

        # Check threads
        if usage.threads > self.thread_threshold * self.fd_threshold_percent:
            return True

        # Check connections
        if usage.connections > self.connection_threshold * self.fd_threshold_percent:
            return True

        # Check disk space
        if usage.disk_free_mb < self.disk_threshold_mb:
            return True

        return False

    def _get_max_fds(self) -> int:
        """
        Get maximum file descriptors allowed (ulimit -n).

        Returns:
            Maximum file descriptors, or 0 if cannot determine
        """
        if not self.is_unix:
            return 0

        try:
            soft_limit, _hard_limit = resource_module.getrlimit(
                resource_module.RLIMIT_NOFILE
            )
            return soft_limit
        except (ValueError, OSError):
            return 0

    def _trigger_critical_callbacks(
        self, deployment_id: str, usage: ResourceUsage
    ) -> None:
        """
        Trigger registered callbacks for critical resource usage.

        Args:
            deployment_id: Deployment with critical usage
            usage: ResourceUsage with critical metrics
        """
        for callback in self._critical_callbacks:
            try:
                callback(deployment_id, usage)
            except Exception as e:
                self.log_error(f"Error in critical callback {callback.__name__}: {e}")


__all__ = ["ResourceMonitor"]
