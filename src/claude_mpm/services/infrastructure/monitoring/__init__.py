"""Refactored monitoring services package.

Exports main monitoring components for backward compatibility.
"""

from .aggregator import MonitoringAggregatorService
from .base import (
    HealthChecker,
    HealthCheckResult,
    HealthMetric,
    HealthStatus,
)

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
    # New service-based API
    "ResourceMonitorService",
    "ProcessHealthService",
    "ServiceHealthService",
    "NetworkHealthService",
    "MonitoringAggregatorService",
    # Base components
    "HealthStatus",
    "HealthMetric",
    "HealthCheckResult",
    "HealthChecker",
    # Legacy compatibility
    "ProcessResourceChecker",
    "NetworkConnectivityChecker",
    "ServiceHealthChecker",
    "AdvancedHealthMonitor",
]
