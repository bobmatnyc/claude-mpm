"""
Local Operations Service Package
=================================

WHY: Provides process management and health monitoring capabilities for local
development deployments. This package implements the core infrastructure needed
by the local-ops-agent to spawn, track, manage, and monitor background processes.

DESIGN DECISION: Organized as a service package under services/ to integrate
with the existing service architecture and dependency injection system.

ARCHITECTURE:
- StateManager: Persistent deployment state tracking
- ProcessManager: Process lifecycle management with isolation
- HealthCheckManager: Three-tier health monitoring (HTTP, process, resource)
- HealthChecks: HTTP, process, and resource health check implementations
- CrashDetector: Crash detection via health status monitoring
- RestartPolicy: Intelligent restart policies with exponential backoff
- RestartManager: Auto-restart orchestration with circuit breaker
- MemoryLeakDetector: Proactive memory leak detection using trend analysis
- LogMonitor: Real-time log file monitoring for error patterns
- ResourceMonitor: Comprehensive resource exhaustion prevention
- Data Models: Process status, deployment state, health status, restart history,
              stability metrics (memory trends, log matches, resource usage)
- Interfaces: ILocalProcessManager, IDeploymentStateManager, IHealthCheckManager,
             ICrashDetector, IRestartPolicy, IRestartManager, IMemoryLeakDetector,
             ILogMonitor, IResourceMonitor

USAGE:
    from claude_mpm.services.local_ops import (
        LocalProcessManager,
        DeploymentStateManager,
        HealthCheckManager,
        StartConfig,
        HealthStatus,
    )
    from claude_mpm.core.enums import ServiceState

    # Initialize managers
    state_manager = DeploymentStateManager(".claude-mpm/deployment-state.json")
    process_manager = LocalProcessManager(state_manager)
    health_manager = HealthCheckManager(process_manager, check_interval=30)

    # Start a process
    config = StartConfig(
        command=["npm", "run", "dev"],
        working_directory="/path/to/project",
        port=3000
    )
    deployment = process_manager.start(config)

    # Check health
    health = health_manager.check_health(deployment.deployment_id)

    # Start background monitoring
    health_manager.start_monitoring()

Note: ProcessStatus has been consolidated into ServiceState (core.enums) as of Phase 3A Batch 24.
"""

# Re-export data models and interfaces for convenience
from claude_mpm.core.enums import HealthStatus
from claude_mpm.services.core.interfaces.health import IHealthCheck, IHealthCheckManager
from claude_mpm.services.core.interfaces.process import (
    IDeploymentStateManager,
    ILocalProcessManager,
)
from claude_mpm.services.core.interfaces.restart import (
    ICrashDetector,
    IRestartManager,
    IRestartPolicy,
)
from claude_mpm.services.core.interfaces.stability import (
    ILogMonitor,
    IMemoryLeakDetector,
    IResourceMonitor,
)
from claude_mpm.services.core.models.health import DeploymentHealth, HealthCheckResult
from claude_mpm.services.core.models.process import (
    PROTECTED_PORT_RANGES,
    DeploymentState,
    ProcessInfo,
    ProcessStatus,
    StartConfig,
    is_port_protected,
)
from claude_mpm.services.core.models.restart import (
    CircuitBreakerState,
    RestartAttempt,
    RestartConfig,
    RestartHistory,
)
from claude_mpm.services.core.models.stability import (
    LogPatternMatch,
    MemoryTrend,
    ResourceUsage,
)

# Import service implementations
from .health_manager import HealthCheckManager
from .log_monitor import LogMonitor
from .memory_leak_detector import MemoryLeakDetector
from .process_manager import LocalProcessManager, PortConflictError, ProcessSpawnError
from .resource_monitor import ResourceMonitor
from .state_manager import DeploymentStateManager, StateCorruptionError
from .unified_manager import UnifiedLocalOpsManager

__all__ = [
    "PROTECTED_PORT_RANGES",
    # Data models - Restart
    "CircuitBreakerState",
    "CrashDetector",
    "DeploymentHealth",
    "DeploymentState",
    # Service implementations
    "DeploymentStateManager",
    "HealthCheckManager",
    "HealthCheckResult",
    # Data models - Health
    "HealthStatus",
    "ICrashDetector",
    # Interfaces
    "IDeploymentStateManager",
    "IHealthCheck",
    "IHealthCheckManager",
    "ILocalProcessManager",
    "ILogMonitor",
    "IMemoryLeakDetector",
    "IResourceMonitor",
    "IRestartManager",
    "IRestartPolicy",
    "LocalProcessManager",
    "LogMonitor",
    "LogPatternMatch",
    "MemoryLeakDetector",
    # Data models - Stability
    "MemoryTrend",
    "PortConflictError",
    "ProcessInfo",
    "ProcessSpawnError",
    "ProcessStatus",
    # Data models - Process
    "ResourceMonitor",
    "ResourceUsage",
    "RestartAttempt",
    "RestartConfig",
    "RestartHistory",
    "RestartManager",
    "RestartPolicy",
    "StartConfig",
    # Exceptions
    "StateCorruptionError",
    "UnifiedLocalOpsManager",
    "is_port_protected",
]
