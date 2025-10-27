"""Process health monitoring service.

Monitors individual process health including CPU, memory, file descriptors, and threads.
"""

from typing import List

from claude_mpm.core.constants import ResourceLimits, TimeoutConfig
from claude_mpm.core.enums import HealthStatus

from .base import BaseMonitoringService, HealthMetric

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None


class ProcessHealthService(BaseMonitoringService):
    """Service for monitoring individual process health.

    Monitors:
    - Process existence and status
    - Process CPU usage
    - Process memory usage (RSS, VMS)
    - File descriptor count (Unix)
    - Thread count
    """

    def __init__(
        self,
        pid: int,
        cpu_threshold: float = 80.0,
        memory_threshold_mb: int = 500,
        fd_threshold: int = 1000,
    ):
        """Initialize process health service.

        Args:
            pid: Process ID to monitor
            cpu_threshold: CPU usage threshold as percentage
            memory_threshold_mb: Memory usage threshold in MB
            fd_threshold: File descriptor count threshold
        """
        super().__init__(f"ProcessHealth_{pid}")
        self.pid = pid
        self.cpu_threshold = cpu_threshold
        self.memory_threshold_mb = memory_threshold_mb
        self.fd_threshold = fd_threshold
        self.process = None

        if PSUTIL_AVAILABLE:
            try:
                self.process = psutil.Process(pid)
            except psutil.NoSuchProcess:
                self.logger.warning(f"Process {pid} not found for monitoring")

    async def check_health(self) -> List[HealthMetric]:
        """Check process health metrics."""
        metrics = []

        if not PSUTIL_AVAILABLE:
            metrics.append(
                HealthMetric(
                    name="psutil_availability",
                    value=False,
                    status=HealthStatus.DEGRADED,
                    message="psutil not available for process monitoring",
                )
            )
            return metrics

        if not self.process:
            metrics.append(
                HealthMetric(
                    name="process_exists",
                    value=False,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Process {self.pid} not found",
                )
            )
            return metrics

        try:
            # Check if process still exists
            if not self.process.is_running():
                metrics.append(
                    HealthMetric(
                        name="process_exists",
                        value=False,
                        status=HealthStatus.UNHEALTHY,
                        message=f"Process {self.pid} is no longer running",
                    )
                )
                return metrics

            # Process status
            metrics.extend(self._check_process_status())

            # CPU usage
            metrics.extend(self._check_cpu_usage())

            # Memory usage
            metrics.extend(self._check_memory_usage())

            # File descriptors
            metrics.extend(self._check_file_descriptors())

            # Thread count
            metrics.extend(self._check_thread_count())

            # Process metadata
            metrics.extend(self._check_process_metadata())

        except psutil.NoSuchProcess:
            metrics.append(
                HealthMetric(
                    name="process_exists",
                    value=False,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Process {self.pid} no longer exists",
                )
            )
        except Exception as e:
            self.logger.error(f"Error checking process health: {e}")
            metrics.append(
                HealthMetric(
                    name="process_check_error",
                    value=str(e),
                    status=HealthStatus.UNKNOWN,
                    message=f"Unexpected error during process health check: {e}",
                )
            )

        return metrics

    def _check_process_status(self) -> List[HealthMetric]:
        """Check process status."""
        metrics = []
        try:
            status = self.process.status()
            process_healthy = status not in [
                psutil.STATUS_ZOMBIE,
                psutil.STATUS_DEAD,
                psutil.STATUS_STOPPED,
            ]
            metrics.append(
                HealthMetric(
                    name="process_status",
                    value=status,
                    status=(
                        HealthStatus.HEALTHY
                        if process_healthy
                        else HealthStatus.UNHEALTHY
                    ),
                    message=f"Process status: {status}",
                )
            )
        except Exception as e:
            metrics.append(
                HealthMetric(
                    name="process_status",
                    value="unknown",
                    status=HealthStatus.UNKNOWN,
                    message=f"Failed to get process status: {e}",
                )
            )
        return metrics

    def _check_cpu_usage(self) -> List[HealthMetric]:
        """Check CPU usage."""
        metrics = []
        try:
            cpu_percent = self.process.cpu_percent(
                interval=TimeoutConfig.CPU_SAMPLE_INTERVAL
            )
            cpu_status = HealthStatus.HEALTHY
            if cpu_percent > self.cpu_threshold:
                cpu_status = (
                    HealthStatus.DEGRADED
                    if cpu_percent < self.cpu_threshold * 1.2
                    else HealthStatus.UNHEALTHY
                )

            metrics.append(
                HealthMetric(
                    name="cpu_usage_percent",
                    value=round(cpu_percent, 2),
                    status=cpu_status,
                    threshold=self.cpu_threshold,
                    unit="%",
                )
            )
        except Exception as e:
            metrics.append(
                HealthMetric(
                    name="cpu_usage_percent",
                    value=-1,
                    status=HealthStatus.UNKNOWN,
                    message=f"Failed to get CPU usage: {e}",
                )
            )
        return metrics

    def _check_memory_usage(self) -> List[HealthMetric]:
        """Check memory usage."""
        metrics = []
        try:
            memory_info = self.process.memory_info()
            memory_mb = memory_info.rss / ResourceLimits.BYTES_TO_MB
            memory_status = HealthStatus.HEALTHY
            if memory_mb > self.memory_threshold_mb:
                memory_status = (
                    HealthStatus.DEGRADED
                    if memory_mb < self.memory_threshold_mb * 1.2
                    else HealthStatus.UNHEALTHY
                )

            metrics.append(
                HealthMetric(
                    name="memory_usage_mb",
                    value=round(memory_mb, 2),
                    status=memory_status,
                    threshold=self.memory_threshold_mb,
                    unit="MB",
                )
            )

            metrics.append(
                HealthMetric(
                    name="memory_vms_mb",
                    value=round(memory_info.vms / ResourceLimits.BYTES_TO_MB, 2),
                    status=HealthStatus.HEALTHY,
                    unit="MB",
                )
            )
        except Exception as e:
            metrics.append(
                HealthMetric(
                    name="memory_usage_mb",
                    value=-1,
                    status=HealthStatus.UNKNOWN,
                    message=f"Failed to get memory usage: {e}",
                )
            )
        return metrics

    def _check_file_descriptors(self) -> List[HealthMetric]:
        """Check file descriptor count (Unix only)."""
        metrics = []
        if hasattr(self.process, "num_fds"):
            try:
                fd_count = self.process.num_fds()
                fd_status = HealthStatus.HEALTHY
                if fd_count > self.fd_threshold:
                    fd_status = (
                        HealthStatus.DEGRADED
                        if fd_count < self.fd_threshold * 1.2
                        else HealthStatus.UNHEALTHY
                    )

                metrics.append(
                    HealthMetric(
                        name="file_descriptors",
                        value=fd_count,
                        status=fd_status,
                        threshold=self.fd_threshold,
                    )
                )
            except Exception as e:
                metrics.append(
                    HealthMetric(
                        name="file_descriptors",
                        value=-1,
                        status=HealthStatus.UNKNOWN,
                        message=f"Failed to get file descriptor count: {e}",
                    )
                )
        return metrics

    def _check_thread_count(self) -> List[HealthMetric]:
        """Check thread count."""
        metrics = []
        try:
            thread_count = self.process.num_threads()
            metrics.append(
                HealthMetric(
                    name="thread_count",
                    value=thread_count,
                    status=HealthStatus.HEALTHY,
                )
            )
        except Exception as e:
            metrics.append(
                HealthMetric(
                    name="thread_count",
                    value=-1,
                    status=HealthStatus.UNKNOWN,
                    message=f"Failed to get thread count: {e}",
                )
            )
        return metrics

    def _check_process_metadata(self) -> List[HealthMetric]:
        """Check process metadata."""
        metrics = []
        try:
            create_time = self.process.create_time()
            metrics.append(
                HealthMetric(
                    name="process_start_time",
                    value=create_time,
                    status=HealthStatus.HEALTHY,
                    unit="timestamp",
                )
            )
        except Exception as e:
            metrics.append(
                HealthMetric(
                    name="process_start_time",
                    value=-1,
                    status=HealthStatus.UNKNOWN,
                    message=f"Failed to get process start time: {e}",
                )
            )
        return metrics

    def is_process_alive(self) -> bool:
        """Quick check if process is still alive.

        Returns:
            True if process exists and is running
        """
        if not PSUTIL_AVAILABLE or not self.process:
            return False

        try:
            return self.process.is_running()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
