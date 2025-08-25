"""Legacy compatibility wrappers for monitoring classes.

Provides backward compatibility for existing code using the old monitoring API.
"""

from typing import Any, Dict, List, Optional

from .aggregator import MonitoringAggregatorService
from .base import HealthChecker, HealthMetric
from .network import NetworkHealthService
from .process import ProcessHealthService
from .service import ServiceHealthService


class ProcessResourceChecker(HealthChecker):
    """Legacy wrapper for ProcessHealthService.

    Maintains backward compatibility with existing code.
    """

    def __init__(
        self,
        pid: int,
        cpu_threshold: float = 80.0,
        memory_threshold_mb: int = 500,
        fd_threshold: int = 1000,
    ):
        """Initialize legacy process resource checker."""
        self.service = ProcessHealthService(
            pid=pid,
            cpu_threshold=cpu_threshold,
            memory_threshold_mb=memory_threshold_mb,
            fd_threshold=fd_threshold,
        )
        self.pid = pid

    def get_name(self) -> str:
        """Get checker name."""
        return f"process_resources_{self.pid}"

    async def check_health(self) -> List[HealthMetric]:
        """Perform health check."""
        return await self.service.check_health()


class NetworkConnectivityChecker(HealthChecker):
    """Legacy wrapper for NetworkHealthService.

    Maintains backward compatibility with existing code.
    """

    def __init__(self, host: str, port: int, timeout: float = 1.0):
        """Initialize legacy network connectivity checker."""
        self.service = NetworkHealthService(default_timeout=timeout)
        self.service.add_endpoint(host, port, f"{host}_{port}", timeout)
        self.host = host
        self.port = port
        self.timeout = timeout

    def get_name(self) -> str:
        """Get checker name."""
        return f"network_connectivity_{self.host}_{self.port}"

    async def check_health(self) -> List[HealthMetric]:
        """Perform health check."""
        # Filter to only return metrics for the configured endpoint
        all_metrics = await self.service.check_health()
        relevant_metrics = []

        for metric in all_metrics:
            # Include socket creation and metrics for our endpoint
            if (
                metric.name == "socket_creation"
                or f"{self.host}_{self.port}" in metric.name
                or "localhost_default" not in metric.name
            ):
                # Rename metrics to match legacy format
                if f"port_accessible_{self.host}_{self.port}" in metric.name:
                    metric.name = "port_accessible"
                relevant_metrics.append(metric)

        return relevant_metrics


class ServiceHealthChecker(HealthChecker):
    """Legacy wrapper for ServiceHealthService.

    Maintains backward compatibility with existing code.
    """

    def __init__(
        self,
        service_stats: Dict[str, Any],
        max_clients: int = 1000,
        max_error_rate: float = 0.1,
    ):
        """Initialize legacy service health checker."""
        self.service = ServiceHealthService(
            service_stats=service_stats,
            max_clients=max_clients,
            max_error_rate=max_error_rate,
        )
        self.service_stats = service_stats
        self.max_clients = max_clients
        self.max_error_rate = max_error_rate
        self.last_check_time = self.service.last_check_time
        self.last_events_processed = self.service.last_events_processed

    def get_name(self) -> str:
        """Get checker name."""
        return "service_health"

    async def check_health(self) -> List[HealthMetric]:
        """Perform health check."""
        metrics = await self.service.check_health()
        # Update exposed state for compatibility
        self.last_check_time = self.service.last_check_time
        self.last_events_processed = self.service.last_events_processed
        return metrics


class AdvancedHealthMonitor:
    """Legacy wrapper for MonitoringAggregatorService.

    Maintains backward compatibility with existing code.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize legacy advanced health monitor."""
        self.service = MonitoringAggregatorService(config)

        # Expose service properties for compatibility
        self.config = self.service.config
        self.check_interval = self.service.check_interval
        self.history_size = self.service.history_size
        self.aggregation_window = self.service.aggregation_window
        self.checkers = self.service.checkers
        self.health_history = self.service.health_history
        self.monitoring = self.service.monitoring
        self.monitor_task = self.service.monitor_task
        self.last_check_result = self.service.last_check_result
        self.health_callbacks = self.service.health_callbacks
        self.monitoring_stats = self.service.monitoring_stats

        # Legacy logger
        import logging

        self.logger = logging.getLogger(f"{__name__}.AdvancedHealthMonitor")

    def add_checker(self, checker: HealthChecker) -> None:
        """Add a health checker."""
        self.service.add_checker(checker)
        self.checkers = self.service.checkers

    def add_health_callback(self, callback) -> None:
        """Add health callback."""
        self.service.add_health_callback(callback)
        self.health_callbacks = self.service.health_callbacks

    async def perform_health_check(self):
        """Perform health check."""
        result = await self.service.perform_health_check()
        # Update exposed state
        self.health_history = self.service.health_history
        self.last_check_result = self.service.last_check_result
        self.monitoring_stats = self.service.monitoring_stats
        return result

    def _determine_overall_status(self, metrics):
        """Determine overall status."""
        return self.service._determine_overall_status(metrics)

    def start_monitoring(self) -> None:
        """Start monitoring."""
        self.service.start_monitoring()
        self.monitoring = self.service.monitoring
        self.monitor_task = self.service.monitor_task

    async def stop_monitoring(self) -> None:
        """Stop monitoring."""
        await self.service.stop_monitoring()
        self.monitoring = self.service.monitoring
        self.monitor_task = self.service.monitor_task

    async def _monitoring_loop(self) -> None:
        """Monitoring loop (should not be called directly)."""
        await self.service._monitoring_loop()

    def get_current_status(self):
        """Get current status."""
        return self.service.get_current_status()

    def get_health_history(self, limit=None):
        """Get health history."""
        return self.service.get_health_history(limit)

    def get_aggregated_status(self, window_seconds=None):
        """Get aggregated status."""
        return self.service.get_aggregated_status(window_seconds)

    def export_diagnostics(self):
        """Export diagnostics."""
        return self.service.export_diagnostics()
