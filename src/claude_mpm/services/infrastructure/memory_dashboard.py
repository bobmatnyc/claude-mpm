from pathlib import Path

"""Memory monitoring dashboard for Memory Guardian system.

Provides real-time memory usage display, restart history, and metrics export.
"""

import asyncio
import json
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from claude_mpm.services.core.base import BaseService
from claude_mpm.services.infrastructure.graceful_degradation import GracefulDegradation
from claude_mpm.services.infrastructure.health_monitor import HealthMonitor
from claude_mpm.services.infrastructure.memory_guardian import (
    MemoryGuardian,
    MemoryState,
)
from claude_mpm.services.infrastructure.restart_protection import RestartProtection


@dataclass
class DashboardMetrics:
    """Dashboard metrics snapshot."""

    timestamp: float
    memory_current_mb: float
    memory_peak_mb: float
    memory_average_mb: float
    memory_state: str
    process_state: str
    process_uptime_hours: float
    total_restarts: int
    recent_restarts: int
    health_status: str
    degradation_level: str
    active_features: int
    degraded_features: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp,
            "timestamp_iso": datetime.fromtimestamp(self.timestamp).isoformat(),
            "memory": {
                "current_mb": round(self.memory_current_mb, 2),
                "peak_mb": round(self.memory_peak_mb, 2),
                "average_mb": round(self.memory_average_mb, 2),
                "state": self.memory_state,
            },
            "process": {
                "state": self.process_state,
                "uptime_hours": round(self.process_uptime_hours, 2),
            },
            "restarts": {"total": self.total_restarts, "recent": self.recent_restarts},
            "health": {
                "status": self.health_status,
                "degradation_level": self.degradation_level,
                "active_features": self.active_features,
                "degraded_features": self.degraded_features,
            },
        }


class MemoryDashboard(BaseService):
    """Dashboard service for memory monitoring visualization and metrics."""

    def __init__(
        self,
        memory_guardian: Optional[MemoryGuardian] = None,
        restart_protection: Optional[RestartProtection] = None,
        health_monitor: Optional[HealthMonitor] = None,
        graceful_degradation: Optional[GracefulDegradation] = None,
        metrics_file: Optional[Path] = None,
        export_interval_seconds: int = 60,
    ):
        """Initialize memory dashboard service.

        Args:
            memory_guardian: MemoryGuardian service instance
            restart_protection: RestartProtection service instance
            health_monitor: HealthMonitor service instance
            graceful_degradation: GracefulDegradation service instance
            metrics_file: Optional file for metrics export
            export_interval_seconds: Interval for metrics export
        """
        super().__init__("MemoryDashboard")

        # Service dependencies
        self.memory_guardian = memory_guardian
        self.restart_protection = restart_protection
        self.health_monitor = health_monitor
        self.graceful_degradation = graceful_degradation

        # Configuration
        self.metrics_file = metrics_file
        self.export_interval = export_interval_seconds

        # Metrics tracking
        self.metrics_history: List[DashboardMetrics] = []
        self.export_task: Optional[asyncio.Task] = None
        self.dashboard_active = False

        self.log_info("Memory dashboard initialized")

    async def initialize(self) -> bool:
        """Initialize the memory dashboard service.

        Returns:
            True if initialization successful
        """
        try:
            self.log_info("Initializing memory dashboard service")

            # Verify service dependencies
            if not self.memory_guardian:
                self.log_warning(
                    "Memory Guardian not available, dashboard running in limited mode"
                )

            # Start metrics export if configured
            if self.metrics_file and self.export_interval > 0:
                self.export_task = asyncio.create_task(self._export_metrics_loop())

            self._initialized = True
            self.log_info("Memory dashboard service initialized successfully")
            return True

        except Exception as e:
            self.log_error(f"Failed to initialize memory dashboard: {e}")
            return False

    async def shutdown(self) -> None:
        """Shutdown the memory dashboard service."""
        try:
            self.log_info("Shutting down memory dashboard service")

            # Stop export task
            if self.export_task:
                self.export_task.cancel()
                try:
                    await self.export_task
                except asyncio.CancelledError:
                    pass

            # Export final metrics
            if self.metrics_file:
                self._export_metrics()

            self._shutdown = True
            self.log_info("Memory dashboard service shutdown complete")

        except Exception as e:
            self.log_error(f"Error during memory dashboard shutdown: {e}")

    def get_current_metrics(self) -> DashboardMetrics:
        """Get current system metrics.

        Returns:
            DashboardMetrics snapshot
        """
        # Get memory metrics
        memory_current = 0.0
        memory_peak = 0.0
        memory_average = 0.0
        memory_state = "unknown"
        process_state = "unknown"
        process_uptime = 0.0
        total_restarts = 0

        if self.memory_guardian:
            status = self.memory_guardian.get_status()
            memory_current = status["memory"]["current_mb"]
            memory_peak = status["memory"]["peak_mb"]
            memory_average = status["memory"]["average_mb"]
            memory_state = status["memory"]["state"]
            process_state = status["process"]["state"]
            process_uptime = status["process"]["uptime_hours"]
            total_restarts = status["restarts"]["total"]

        # Get restart metrics
        recent_restarts = 0
        if self.restart_protection:
            stats = self.restart_protection.get_restart_statistics()
            recent_restarts = len(
                [
                    r
                    for r in self.restart_protection.restart_history
                    if r.timestamp >= time.time() - 3600
                ]
            )

        # Get health metrics
        health_status = "unknown"
        if self.health_monitor:
            health = self.health_monitor.get_health_status()
            if health:
                health_status = health.status.value

        # Get degradation metrics
        degradation_level = "normal"
        active_features = 0
        degraded_features = 0
        if self.graceful_degradation:
            status = self.graceful_degradation.get_status()
            degradation_level = status.level.value
            active_features = status.available_features
            degraded_features = status.degraded_features

        return DashboardMetrics(
            timestamp=time.time(),
            memory_current_mb=memory_current,
            memory_peak_mb=memory_peak,
            memory_average_mb=memory_average,
            memory_state=memory_state,
            process_state=process_state,
            process_uptime_hours=process_uptime,
            total_restarts=total_restarts,
            recent_restarts=recent_restarts,
            health_status=health_status,
            degradation_level=degradation_level,
            active_features=active_features,
            degraded_features=degraded_features,
        )

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data.

        Returns:
            Dictionary with all dashboard information
        """
        current_metrics = self.get_current_metrics()

        # Get restart history
        restart_history = []
        if self.restart_protection:
            stats = self.restart_protection.get_restart_statistics()
            restart_history = [
                r.to_dict() for r in list(self.restart_protection.restart_history)[-10:]
            ]

        # Get health checks
        health_checks = []
        if self.health_monitor:
            health = self.health_monitor.get_health_status()
            if health:
                health_checks = [c.to_dict() for c in health.checks]

        # Get feature status
        features = []
        if self.graceful_degradation:
            status = self.graceful_degradation.get_status()
            features = [f.to_dict() for f in status.features]

        # Get thresholds
        thresholds = {}
        if self.memory_guardian:
            config = self.memory_guardian.config
            thresholds = {
                "warning_mb": config.thresholds.warning,
                "critical_mb": config.thresholds.critical,
                "emergency_mb": config.thresholds.emergency,
            }

        return {
            "current_metrics": current_metrics.to_dict(),
            "thresholds": thresholds,
            "restart_history": restart_history,
            "health_checks": health_checks,
            "features": features,
            "metrics_history": [m.to_dict() for m in self.metrics_history[-50:]],
            "timestamp": time.time(),
        }

    def get_summary(self) -> str:
        """Get a text summary of current status.

        Returns:
            Human-readable status summary
        """
        metrics = self.get_current_metrics()

        lines = [
            "=" * 60,
            "MEMORY GUARDIAN DASHBOARD",
            "=" * 60,
            "",
            "MEMORY STATUS",
            "-" * 30,
            f"Current:  {metrics.memory_current_mb:8.2f} MB",
            f"Peak:     {metrics.memory_peak_mb:8.2f} MB",
            f"Average:  {metrics.memory_average_mb:8.2f} MB",
            f"State:    {metrics.memory_state.upper()}",
            "",
            "PROCESS STATUS",
            "-" * 30,
            f"State:    {metrics.process_state}",
            f"Uptime:   {metrics.process_uptime_hours:.2f} hours",
            "",
            "RESTART STATISTICS",
            "-" * 30,
            f"Total:    {metrics.total_restarts}",
            f"Recent:   {metrics.recent_restarts} (last hour)",
            "",
        ]

        # Add restart protection info
        if self.restart_protection:
            stats = self.restart_protection.get_restart_statistics()
            lines.extend(
                [
                    "RESTART PROTECTION",
                    "-" * 30,
                    f"Circuit:  {stats.circuit_state.value}",
                    f"Failures: {stats.consecutive_failures}",
                    "",
                ]
            )

            # Add memory trend if available
            if stats.memory_trend and stats.memory_trend.is_leak_suspected:
                lines.extend(
                    [
                        "⚠️  MEMORY LEAK SUSPECTED",
                        f"Growth:   {stats.memory_trend.slope_mb_per_min:.2f} MB/min",
                        "",
                    ]
                )

        # Add health status
        lines.extend(
            [
                "SYSTEM HEALTH",
                "-" * 30,
                f"Status:   {metrics.health_status}",
                f"Level:    {metrics.degradation_level}",
                "",
            ]
        )

        # Add feature status if degraded
        if metrics.degraded_features > 0:
            lines.extend(["DEGRADED FEATURES", "-" * 30])

            if self.graceful_degradation:
                status = self.graceful_degradation.get_status()
                for feature in status.features:
                    if feature.state.value != "available":
                        lines.append(f"• {feature.name}: {feature.state.value}")

            lines.append("")

        # Add timestamp
        lines.extend(
            ["-" * 60, f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"]
        )

        return "\n".join(lines)

    def export_prometheus_metrics(self) -> str:
        """Export metrics in Prometheus format.

        Returns:
            Prometheus-formatted metrics string
        """
        metrics = self.get_current_metrics()
        timestamp = int(metrics.timestamp * 1000)

        lines = [
            "# HELP memory_current_mb Current memory usage in megabytes",
            "# TYPE memory_current_mb gauge",
            f"memory_current_mb {metrics.memory_current_mb} {timestamp}",
            "",
            "# HELP memory_peak_mb Peak memory usage in megabytes",
            "# TYPE memory_peak_mb gauge",
            f"memory_peak_mb {metrics.memory_peak_mb} {timestamp}",
            "",
            "# HELP memory_average_mb Average memory usage in megabytes",
            "# TYPE memory_average_mb gauge",
            f"memory_average_mb {metrics.memory_average_mb} {timestamp}",
            "",
            "# HELP process_uptime_hours Process uptime in hours",
            "# TYPE process_uptime_hours counter",
            f"process_uptime_hours {metrics.process_uptime_hours} {timestamp}",
            "",
            "# HELP total_restarts Total number of process restarts",
            "# TYPE total_restarts counter",
            f"total_restarts {metrics.total_restarts} {timestamp}",
            "",
            "# HELP recent_restarts Number of restarts in the last hour",
            "# TYPE recent_restarts gauge",
            f"recent_restarts {metrics.recent_restarts} {timestamp}",
            "",
            "# HELP degraded_features Number of degraded system features",
            "# TYPE degraded_features gauge",
            f"degraded_features {metrics.degraded_features} {timestamp}",
            "",
        ]

        # Add memory state as labeled metric
        memory_state_value = {
            "normal": 0,
            "warning": 1,
            "critical": 2,
            "emergency": 3,
        }.get(metrics.memory_state.lower(), -1)

        lines.extend(
            [
                "# HELP memory_state Current memory state (0=normal, 1=warning, 2=critical, 3=emergency)",
                "# TYPE memory_state gauge",
                f"memory_state {memory_state_value} {timestamp}",
                "",
            ]
        )

        # Add health status as labeled metric
        health_value = {"healthy": 0, "degraded": 1, "unhealthy": 2, "critical": 3}.get(
            metrics.health_status.lower(), -1
        )

        lines.extend(
            [
                "# HELP health_status System health status (0=healthy, 1=degraded, 2=unhealthy, 3=critical)",
                "# TYPE health_status gauge",
                f"health_status {health_value} {timestamp}",
            ]
        )

        return "\n".join(lines)

    def export_json_metrics(self) -> str:
        """Export metrics in JSON format.

        Returns:
            JSON-formatted metrics string
        """
        data = self.get_dashboard_data()
        return json.dumps(data, indent=2)

    async def _export_metrics_loop(self) -> None:
        """Background task to export metrics periodically."""
        while not self._shutdown:
            try:
                # Collect metrics
                metrics = self.get_current_metrics()
                self.metrics_history.append(metrics)

                # Trim history
                if (
                    len(self.metrics_history) > 1440
                ):  # Keep 24 hours at 1-minute intervals
                    self.metrics_history = self.metrics_history[-1440:]

                # Export to file
                if self.metrics_file:
                    self._export_metrics()

                await asyncio.sleep(self.export_interval)

            except Exception as e:
                self.log_error(f"Error in metrics export loop: {e}")
                await asyncio.sleep(self.export_interval)

    def _export_metrics(self) -> None:
        """Export metrics to file."""
        if not self.metrics_file:
            return

        try:
            # Determine format from file extension
            if self.metrics_file.suffix == ".json":
                content = self.export_json_metrics()
            elif self.metrics_file.suffix == ".prom":
                content = self.export_prometheus_metrics()
            else:
                # Default to JSON
                content = self.export_json_metrics()

            # Write to file
            self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
            self.metrics_file.write_text(content)

            self.log_debug(f"Exported metrics to {self.metrics_file}")

        except Exception as e:
            self.log_error(f"Failed to export metrics: {e}")
