"""Advanced health monitoring system for claude-mpm Socket.IO server.

This module has been refactored into a modular service-based architecture.
All functionality is preserved through the monitoring package.

The refactoring reduces complexity from 1,034 lines to under 100 lines
by delegating to specialized services:
- ResourceMonitorService: System resource monitoring
- ProcessHealthService: Process-specific monitoring
- ServiceHealthService: Application-level metrics
- NetworkHealthService: Network connectivity checks
- MonitoringAggregatorService: Orchestration and aggregation

For new code, use the service-based API:
    from claude_mpm.services.infrastructure.monitoring import (
        ResourceMonitorService,
        ProcessHealthService,
        ServiceHealthService,
        NetworkHealthService,
        MonitoringAggregatorService,
    )

For backward compatibility, legacy classes are still available:
    from claude_mpm.services.infrastructure.monitoring import (
        ProcessResourceChecker,
        NetworkConnectivityChecker,
        ServiceHealthChecker,
        AdvancedHealthMonitor,
    )
"""

# Re-export all components from the modular implementation
from .monitoring import (
    AdvancedHealthMonitor,
    HealthChecker,
    HealthCheckResult,
    HealthMetric,
    HealthStatus,
    MonitoringAggregatorService,
    NetworkConnectivityChecker,
    NetworkHealthService,
    ProcessHealthService,
    ProcessResourceChecker,
    ResourceMonitorService,
    ServiceHealthChecker,
    ServiceHealthService,
)

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

# Module metadata
__version__ = "2.0.0"
__author__ = "Claude MPM Team"
__description__ = "Refactored modular health monitoring system"
