"""Base classes and data structures for monitoring services.

This module defines the core types and interfaces used across all monitoring services.
"""

import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from ....core.enums import HealthStatus


@dataclass
class HealthMetric:
    """Individual health metric data structure."""

    name: str
    value: Union[int, float, str, bool]
    status: HealthStatus
    threshold: Optional[Union[int, float]] = None
    unit: Optional[str] = None
    timestamp: float = None
    message: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert metric to dictionary format."""
        result = asdict(self)
        result["status"] = self.status.value
        result["timestamp_iso"] = datetime.fromtimestamp(
            self.timestamp, timezone.utc
        ).isoformat()
        return result


@dataclass
class HealthCheckResult:
    """Result of a health check operation."""

    overall_status: HealthStatus
    metrics: List[HealthMetric]
    timestamp: float
    duration_ms: float
    errors: List[str]

    def __post_init__(self):
        if not hasattr(self, "timestamp") or self.timestamp is None:
            self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert health check result to dictionary format."""
        return {
            "overall_status": self.overall_status.value,
            "metrics": [metric.to_dict() for metric in self.metrics],
            "timestamp": self.timestamp,
            "timestamp_iso": datetime.fromtimestamp(
                self.timestamp, timezone.utc
            ).isoformat(),
            "duration_ms": self.duration_ms,
            "errors": self.errors,
            "metric_count": len(self.metrics),
            "healthy_metrics": len(
                [m for m in self.metrics if m.status == HealthStatus.HEALTHY]
            ),
            "degraded_metrics": len(
                [m for m in self.metrics if m.status == HealthStatus.DEGRADED]
            ),
            "unhealthy_metrics": len(
                [m for m in self.metrics if m.status == HealthStatus.UNHEALTHY]
            ),
        }


class HealthChecker(ABC):
    """Abstract base class for health checkers.

    Health checkers implement specific monitoring logic for different aspects
    of the system (process resources, network connectivity, service health, etc.).
    """

    @abstractmethod
    def get_name(self) -> str:
        """Get the name of this health checker."""

    @abstractmethod
    async def check_health(self) -> List[HealthMetric]:
        """Perform health check and return metrics."""


class BaseMonitoringService(ABC):
    """Base class for monitoring services with dependency injection support."""

    def __init__(self, name: str):
        """Initialize base monitoring service.

        Args:
            name: Service name for logging and identification
        """
        self.name = name
        self._logger = None

    @property
    def logger(self):
        """Lazy-load logger to avoid circular imports."""
        if self._logger is None:
            import logging

            self._logger = logging.getLogger(f"claude_mpm.monitoring.{self.name}")
        return self._logger

    @abstractmethod
    async def check_health(self) -> List[HealthMetric]:
        """Perform health check and return metrics."""

    def get_name(self) -> str:
        """Get service name."""
        return self.name
