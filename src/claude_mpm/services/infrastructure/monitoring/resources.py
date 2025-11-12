"""Resource monitoring service for system resources (CPU, memory, disk).

Monitors system-wide resource usage including CPU, memory, and disk utilization.
"""

from typing import Dict, List, Optional

from ....core.enums import HealthStatus
from .base import BaseMonitoringService, HealthMetric

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None


class ResourceMonitorService(BaseMonitoringService):
    """Service for monitoring system resource usage.

    Monitors:
    - System CPU usage
    - System memory usage
    - Disk space utilization
    - System load average
    """

    def __init__(
        self,
        cpu_threshold: float = 80.0,
        memory_threshold: float = 85.0,
        disk_threshold: float = 90.0,
    ):
        """Initialize resource monitor service.

        Args:
            cpu_threshold: CPU usage warning threshold (%)
            memory_threshold: Memory usage warning threshold (%)
            disk_threshold: Disk usage warning threshold (%)
        """
        super().__init__("ResourceMonitor")
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.disk_threshold = disk_threshold

    async def check_health(self) -> List[HealthMetric]:
        """Check system resource health."""
        metrics = []

        if not PSUTIL_AVAILABLE:
            metrics.append(
                HealthMetric(
                    name="psutil_availability",
                    value=False,
                    status=HealthStatus.DEGRADED,
                    message="psutil not available for resource monitoring",
                )
            )
            return metrics

        # CPU usage
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_status = self._get_threshold_status(cpu_percent, self.cpu_threshold)

            metrics.append(
                HealthMetric(
                    name="system_cpu_usage",
                    value=round(cpu_percent, 2),
                    status=cpu_status,
                    threshold=self.cpu_threshold,
                    unit="%",
                )
            )

            # CPU count for context
            metrics.append(
                HealthMetric(
                    name="cpu_count",
                    value=psutil.cpu_count(),
                    status=HealthStatus.HEALTHY,
                )
            )
        except Exception as e:
            self.logger.error(f"Failed to get CPU usage: {e}")
            metrics.append(
                HealthMetric(
                    name="system_cpu_usage",
                    value=-1,
                    status=HealthStatus.UNKNOWN,
                    message=str(e),
                )
            )

        # Memory usage
        try:
            memory = psutil.virtual_memory()
            memory_status = self._get_threshold_status(
                memory.percent, self.memory_threshold
            )

            metrics.append(
                HealthMetric(
                    name="system_memory_usage",
                    value=round(memory.percent, 2),
                    status=memory_status,
                    threshold=self.memory_threshold,
                    unit="%",
                )
            )

            # Memory details
            metrics.append(
                HealthMetric(
                    name="memory_available_gb",
                    value=round(memory.available / (1024**3), 2),
                    status=HealthStatus.HEALTHY,
                    unit="GB",
                )
            )

            metrics.append(
                HealthMetric(
                    name="memory_total_gb",
                    value=round(memory.total / (1024**3), 2),
                    status=HealthStatus.HEALTHY,
                    unit="GB",
                )
            )
        except Exception as e:
            self.logger.error(f"Failed to get memory usage: {e}")
            metrics.append(
                HealthMetric(
                    name="system_memory_usage",
                    value=-1,
                    status=HealthStatus.UNKNOWN,
                    message=str(e),
                )
            )

        # Disk usage
        try:
            disk = psutil.disk_usage("/")
            disk_status = self._get_threshold_status(disk.percent, self.disk_threshold)

            metrics.append(
                HealthMetric(
                    name="disk_usage",
                    value=round(disk.percent, 2),
                    status=disk_status,
                    threshold=self.disk_threshold,
                    unit="%",
                )
            )

            metrics.append(
                HealthMetric(
                    name="disk_free_gb",
                    value=round(disk.free / (1024**3), 2),
                    status=HealthStatus.HEALTHY,
                    unit="GB",
                )
            )
        except Exception as e:
            self.logger.error(f"Failed to get disk usage: {e}")
            metrics.append(
                HealthMetric(
                    name="disk_usage",
                    value=-1,
                    status=HealthStatus.UNKNOWN,
                    message=str(e),
                )
            )

        # Load average (Unix only)
        try:
            if hasattr(psutil, "getloadavg"):
                load1, load5, _load15 = psutil.getloadavg()
                cpu_count = psutil.cpu_count()

                # Load is concerning if > cpu_count
                load_status = HealthStatus.HEALTHY
                if load1 > cpu_count:
                    load_status = HealthStatus.DEGRADED
                if load1 > cpu_count * 1.5:
                    load_status = HealthStatus.UNHEALTHY

                metrics.append(
                    HealthMetric(
                        name="load_average_1min",
                        value=round(load1, 2),
                        status=load_status,
                        threshold=cpu_count,
                    )
                )

                metrics.append(
                    HealthMetric(
                        name="load_average_5min",
                        value=round(load5, 2),
                        status=HealthStatus.HEALTHY,
                    )
                )
        except Exception as e:
            self.logger.debug(f"Load average not available: {e}")

        return metrics

    def _get_threshold_status(self, value: float, threshold: float) -> HealthStatus:
        """Determine health status based on threshold.

        Args:
            value: Current value
            threshold: Warning threshold

        Returns:
            Health status based on value vs threshold
        """
        if value < threshold:
            return HealthStatus.HEALTHY
        if value < threshold * 1.1:  # 10% above threshold
            return HealthStatus.DEGRADED
        return HealthStatus.UNHEALTHY

    def get_resource_summary(self) -> Optional[Dict[str, float]]:
        """Get quick resource summary without full health check.

        Returns:
            Dictionary with current resource usage percentages
        """
        if not PSUTIL_AVAILABLE:
            return None

        try:
            return {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage("/").percent,
            }
        except Exception as e:
            self.logger.error(f"Failed to get resource summary: {e}")
            return None
