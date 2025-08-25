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
from .monitoring import (  # noqa: F401
    # New service-based API
    MonitoringAggregatorService,
    NetworkHealthService,
    ProcessHealthService,
    ResourceMonitorService,
    ServiceHealthService,
    # Base components
    HealthChecker,
    HealthCheckResult,
    HealthMetric,
    HealthStatus,
    # Legacy compatibility
    AdvancedHealthMonitor,
    NetworkConnectivityChecker,
    ProcessResourceChecker,
    ServiceHealthChecker,
)

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

# Module metadata
__version__ = "2.0.0"
__author__ = "Claude MPM Team"
__description__ = "Refactored modular health monitoring system"