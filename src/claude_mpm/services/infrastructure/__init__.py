"""
Infrastructure Services Module
=============================

This module contains infrastructure-related services including
logging, monitoring, and system health management.

Part of TSK-0046: Service Layer Architecture Reorganization

Services:
- LoggingService: Centralized logging with structured output
- HealthMonitor: System health monitoring and alerting
- MemoryGuardian: Memory monitoring and process restart management
- ContextUsageTracker: Token usage tracking across hook invocations
"""

from .context_usage_tracker import ContextUsageState, ContextUsageTracker
from .logging import LoggingService
from .monitoring import (
    AdvancedHealthMonitor,
    MonitoringAggregatorService,
    NetworkHealthService,
    ProcessHealthService,
    ResourceMonitorService,
    ServiceHealthService,
)

# Check if optional modules exist
try:
    from .health_monitor import HealthMonitor
except ImportError:
    HealthMonitor = None

try:
    from .memory_guardian import MemoryGuardian
except ImportError:
    MemoryGuardian = None

__all__ = [
    "AdvancedHealthMonitor",  # For SocketIO server monitoring
    "ContextUsageState",
    "ContextUsageTracker",
    "LoggingService",
    # New service-based monitoring API
    "MonitoringAggregatorService",
    "NetworkHealthService",
    "ProcessHealthService",
    "ResourceMonitorService",
    "ServiceHealthService",
]

# Add optional modules if they exist
if HealthMonitor is not None:
    __all__.append("HealthMonitor")
if MemoryGuardian is not None:
    __all__.append("MemoryGuardian")
