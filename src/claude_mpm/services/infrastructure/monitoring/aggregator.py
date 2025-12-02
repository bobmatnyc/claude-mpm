"""Monitoring aggregator service that combines all health checks.

Orchestrates multiple monitoring services and provides unified health status.
"""

import asyncio
import contextlib
import time
from collections import deque
from typing import Any, Callable, Dict, List, Optional

from ....core.enums import HealthStatus
from .base import BaseMonitoringService, HealthChecker, HealthCheckResult, HealthMetric


class MonitoringAggregatorService(BaseMonitoringService):
    """Service that aggregates health checks from multiple monitoring services.

    Provides:
    - Unified health checking across all registered services
    - Health history tracking
    - Status aggregation and reporting
    - Continuous monitoring with configurable intervals
    - Integration with recovery systems via callbacks
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize monitoring aggregator service.

        Args:
            config: Configuration dictionary for monitoring
        """
        super().__init__("MonitoringAggregator")
        self.config = config or {}

        # Configuration with defaults
        self.check_interval = self.config.get("check_interval", 30)
        self.history_size = self.config.get("history_size", 100)
        self.aggregation_window = self.config.get("aggregation_window", 300)

        # Registered monitoring services
        self.services: List[BaseMonitoringService] = []
        self.checkers: List[HealthChecker] = []  # For backward compatibility

        # Health history
        self.health_history: deque = deque(maxlen=self.history_size)

        # Monitoring state
        self.monitoring = False
        self.monitor_task: Optional[asyncio.Task] = None
        self.last_check_result: Optional[HealthCheckResult] = None

        # Health callbacks for recovery integration
        self.health_callbacks: List[Callable[[HealthCheckResult], None]] = []

        # Statistics
        self.monitoring_stats = {
            "checks_performed": 0,
            "checks_failed": 0,
            "average_check_duration_ms": 0,
            "last_check_timestamp": None,
        }

        self.logger.info("Monitoring aggregator initialized")

    def add_service(self, service: BaseMonitoringService) -> None:
        """Add a monitoring service to aggregate.

        Args:
            service: Monitoring service to add
        """
        self.services.append(service)
        self.logger.info(f"Added monitoring service: {service.get_name()}")

    def add_checker(self, checker: HealthChecker) -> None:
        """Add a health checker (backward compatibility).

        Args:
            checker: Health checker to add
        """
        self.checkers.append(checker)
        self.logger.info(f"Added health checker: {checker.get_name()}")

    def add_health_callback(
        self, callback: Callable[[HealthCheckResult], None]
    ) -> None:
        """Add a callback to be called when health checks complete.

        Args:
            callback: Function to call with HealthCheckResult
        """
        self.health_callbacks.append(callback)
        self.logger.debug(f"Added health callback: {callback.__name__}")

    async def check_health(self) -> List[HealthMetric]:
        """Perform health check across all services.

        Returns:
            Combined list of health metrics from all services
        """
        result = await self.perform_health_check()
        return result.metrics

    async def perform_health_check(self) -> HealthCheckResult:
        """Perform comprehensive health check using all registered services."""
        start_time = time.time()
        all_metrics = []
        errors = []

        # Check all monitoring services
        for service in self.services:
            try:
                service_start = time.time()
                metrics = await service.check_health()
                service_duration = (time.time() - service_start) * 1000

                all_metrics.extend(metrics)
                self.logger.debug(
                    f"Service {service.get_name()} completed in {service_duration:.2f}ms"
                )
            except Exception as e:
                error_msg = f"Service {service.get_name()} failed: {e}"
                errors.append(error_msg)
                self.logger.error(error_msg)

                all_metrics.append(
                    HealthMetric(
                        name=f"{service.get_name()}_error",
                        value=str(e),
                        status=HealthStatus.UNKNOWN,
                        message=error_msg,
                    )
                )

        # Check legacy health checkers
        for checker in self.checkers:
            try:
                checker_start = time.time()
                metrics = await checker.check_health()
                checker_duration = (time.time() - checker_start) * 1000

                all_metrics.extend(metrics)
                self.logger.debug(
                    f"Checker {checker.get_name()} completed in {checker_duration:.2f}ms"
                )
            except Exception as e:
                error_msg = f"Checker {checker.get_name()} failed: {e}"
                errors.append(error_msg)
                self.logger.error(error_msg)

                all_metrics.append(
                    HealthMetric(
                        name=f"{checker.get_name()}_error",
                        value=str(e),
                        status=HealthStatus.UNKNOWN,
                        message=error_msg,
                    )
                )

        # Determine overall status
        overall_status = self._determine_overall_status(all_metrics)

        # Create result
        duration_ms = (time.time() - start_time) * 1000
        result = HealthCheckResult(
            overall_status=overall_status,
            metrics=all_metrics,
            timestamp=start_time,
            duration_ms=duration_ms,
            errors=errors,
        )

        # Update statistics
        self._update_statistics(result, duration_ms)

        # Store in history
        self.health_history.append(result)
        self.last_check_result = result

        # Notify callbacks
        await self._notify_callbacks(result)

        self.logger.debug(
            f"Health check completed: {overall_status.value} "
            f"({len(all_metrics)} metrics, {len(errors)} errors, "
            f"{duration_ms:.2f}ms)"
        )

        return result

    def _determine_overall_status(self, metrics: List[HealthMetric]) -> HealthStatus:
        """Determine overall health status from individual metrics.

        Args:
            metrics: List of health metrics

        Returns:
            Overall health status
        """
        if not metrics:
            return HealthStatus.UNKNOWN

        # Count metrics by status
        status_counts = dict.fromkeys(HealthStatus, 0)
        for metric in metrics:
            status_counts[metric.status] += 1

        total_metrics = len(metrics)

        # Unhealthy if any unhealthy metrics
        if status_counts[HealthStatus.UNHEALTHY] > 0:
            return HealthStatus.UNHEALTHY

        # Degraded if >30% degraded metrics
        degraded_ratio = status_counts[HealthStatus.DEGRADED] / total_metrics
        if degraded_ratio > 0.3:
            return HealthStatus.DEGRADED

        # Unknown if >50% unknown metrics
        unknown_ratio = status_counts[HealthStatus.UNKNOWN] / total_metrics
        if unknown_ratio > 0.5:
            return HealthStatus.UNKNOWN

        # Healthy if mostly healthy metrics
        return HealthStatus.HEALTHY

    def _update_statistics(self, result: HealthCheckResult, duration_ms: float) -> None:
        """Update monitoring statistics.

        Args:
            result: Health check result
            duration_ms: Check duration in milliseconds
        """
        self.monitoring_stats["checks_performed"] += 1
        if result.errors:
            self.monitoring_stats["checks_failed"] += 1

        # Update average duration
        current_avg = self.monitoring_stats["average_check_duration_ms"]
        checks_count = self.monitoring_stats["checks_performed"]
        self.monitoring_stats["average_check_duration_ms"] = (
            current_avg * (checks_count - 1) + duration_ms
        ) / checks_count
        self.monitoring_stats["last_check_timestamp"] = time.time()

    async def _notify_callbacks(self, result: HealthCheckResult) -> None:
        """Notify health callbacks asynchronously.

        Args:
            result: Health check result to pass to callbacks
        """
        for callback in self.health_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(result)
                else:
                    callback(result)
            except Exception as e:
                self.logger.error(f"Health callback {callback.__name__} failed: {e}")

    def start_monitoring(self) -> None:
        """Start continuous health monitoring."""
        if self.monitoring:
            self.logger.warning("Health monitoring is already running")
            return

        self.monitoring = True
        self.monitor_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info(
            f"Started health monitoring with {self.check_interval}s interval"
        )

    async def stop_monitoring(self) -> None:
        """Stop continuous health monitoring."""
        if not self.monitoring:
            return

        self.monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.monitor_task
            self.monitor_task = None

        self.logger.info("Stopped health monitoring")

    async def _monitoring_loop(self) -> None:
        """Continuous health monitoring loop."""
        try:
            while self.monitoring:
                try:
                    await self.perform_health_check()
                except Exception as e:
                    self.logger.error(f"Error during health check: {e}")

                # Wait for next check
                await asyncio.sleep(self.check_interval)
        except asyncio.CancelledError:
            self.logger.debug("Health monitoring loop cancelled")
        except Exception as e:
            self.logger.error(f"Health monitoring loop error: {e}")

    def get_current_status(self) -> Optional[HealthCheckResult]:
        """Get the most recent health check result.

        Returns:
            Most recent health check result or None
        """
        return self.last_check_result

    def get_health_history(
        self, limit: Optional[int] = None
    ) -> List[HealthCheckResult]:
        """Get health check history.

        Args:
            limit: Maximum number of results to return

        Returns:
            List of health check results, newest first
        """
        history = list(self.health_history)
        history.reverse()  # Newest first

        if limit:
            history = history[:limit]

        return history

    def get_aggregated_status(
        self, window_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get aggregated health status over a time window.

        Args:
            window_seconds: Time window for aggregation

        Returns:
            Dictionary with aggregated health statistics
        """
        window_seconds = window_seconds or self.aggregation_window
        current_time = time.time()
        cutoff_time = current_time - window_seconds

        # Filter history to time window
        recent_results = [
            result for result in self.health_history if result.timestamp >= cutoff_time
        ]

        if not recent_results:
            return {
                "period": "no_data",
                "window_seconds": window_seconds,
                "checks_count": 0,
                "overall_status": HealthStatus.UNKNOWN.value,
            }

        # Aggregate statistics
        status_counts = dict.fromkeys(HealthStatus, 0)
        total_metrics = 0
        total_errors = 0
        total_duration_ms = 0

        for result in recent_results:
            status_counts[result.overall_status] += 1
            total_metrics += len(result.metrics)
            total_errors += len(result.errors)
            total_duration_ms += result.duration_ms

        checks_count = len(recent_results)

        # Determine aggregated status
        if status_counts[HealthStatus.UNHEALTHY] > 0:
            aggregated_status = HealthStatus.UNHEALTHY
        elif status_counts[HealthStatus.DEGRADED] > checks_count * 0.3:
            aggregated_status = HealthStatus.DEGRADED
        elif status_counts[HealthStatus.UNKNOWN] > checks_count * 0.5:
            aggregated_status = HealthStatus.UNKNOWN
        else:
            aggregated_status = HealthStatus.HEALTHY

        return {
            "period": f"last_{window_seconds}_seconds",
            "window_seconds": window_seconds,
            "checks_count": checks_count,
            "overall_status": aggregated_status.value,
            "status_distribution": {
                status.value: count for status, count in status_counts.items()
            },
            "average_metrics_per_check": (
                round(total_metrics / checks_count, 2) if checks_count > 0 else 0
            ),
            "total_errors": total_errors,
            "average_duration_ms": (
                round(total_duration_ms / checks_count, 2) if checks_count > 0 else 0
            ),
            "monitoring_stats": dict(self.monitoring_stats),
        }

    def export_diagnostics(self) -> Dict[str, Any]:
        """Export comprehensive diagnostics information.

        Returns:
            Dictionary with diagnostic information
        """
        return {
            "monitor_info": {
                "check_interval": self.check_interval,
                "history_size": self.history_size,
                "aggregation_window": self.aggregation_window,
                "monitoring_active": self.monitoring,
                "services_count": len(self.services),
                "checkers_count": len(self.checkers),
                "callbacks_count": len(self.health_callbacks),
            },
            "services": [service.get_name() for service in self.services],
            "checkers": [checker.get_name() for checker in self.checkers],
            "current_status": (
                self.last_check_result.to_dict() if self.last_check_result else None
            ),
            "aggregated_status": self.get_aggregated_status(),
            "monitoring_stats": dict(self.monitoring_stats),
            "history_summary": {
                "total_checks": len(self.health_history),
                "oldest_check": (
                    self.health_history[0].timestamp if self.health_history else None
                ),
                "newest_check": (
                    self.health_history[-1].timestamp if self.health_history else None
                ),
            },
        }
