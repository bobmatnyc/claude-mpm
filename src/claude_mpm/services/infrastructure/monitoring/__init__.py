"""Refactored monitoring services package.

Exports main monitoring components for backward compatibility.
"""

from ....core.enums import HealthStatus
from .aggregator import MonitoringAggregatorService
from .base import HealthChecker, HealthCheckResult, HealthMetric

# Legacy exports for backward compatibility
from .legacy import (
    AdvancedHealthMonitor,
    NetworkConnectivityChecker,
    ProcessResourceChecker,
    ServiceHealthChecker,
)
from .network import NetworkHealthService
from .process import ProcessHealthService
from .resources import ResourceMonitorService
from .service import ServiceHealthService

__all__ = [
    "AdvancedHealthMonitor",
    "HealthCheckResult",
    "HealthChecker",
    "HealthMetric",
    # Base components
    "HealthStatus",
    "MonitoringAggregatorService",
    "NetworkConnectivityChecker",
    "NetworkHealthService",
    "ProcessHealthService",
    # Legacy compatibility
    "ProcessResourceChecker",
    # New service-based API
    "ResourceMonitorService",
    "ServiceHealthChecker",
    "ServiceHealthService",
]
