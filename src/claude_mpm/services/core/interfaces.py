"""
Core Service Interfaces for Claude MPM Framework
===============================================

WHY: This module provides backward compatibility for the modular interface
structure. The original 1,437-line monolithic file has been split into
focused modules in the interfaces/ package.

DESIGN DECISION: We maintain this file for backward compatibility while the actual
interface definitions have been moved to interfaces/ modules for better organization.

REFACTORING NOTE: The original interfaces.py file has been split into:
- interfaces/infrastructure.py: Core framework services (DI, config, caching, health)
- interfaces/agent.py: Agent management, deployment, and capabilities
- interfaces/service.py: Business services (memory, hooks, utilities)
- interfaces/communication.py: External communication (WebSocket, project analysis, tickets)

IMPACT: Reduced from 1,437 lines to ~50 lines, with functionality split across
focused modules for better maintainability and testing.
"""

# Re-export everything from the new modular structure for backward compatibility
from .interfaces import (  # noqa: F401
    AgentCapabilitiesInterface,
    AgentDeploymentInterface,
    AgentMetadata,
    CacheEntry,
    CommandHandlerInterface,
    HealthStatus,
    HookServiceInterface,
    IAgentRecommender,
    IAgentRegistry,
    IAutoConfigManager,
    ICacheService,
    IConfigurationManager,
    IConfigurationService,
    ICrashDetector,
    IDeploymentStateManager,
    IErrorHandler,
    IEventBus,
    IHealthCheck,
    IHealthCheckManager,
    IHealthMonitor,
    ILocalProcessManager,
    ILogMonitor,
    IMemoryLeakDetector,
    IModelProvider,
    IModelRouter,
    InterfaceRegistry,
    IPerformanceMonitor,
    IPromptCache,
    IResourceMonitor,
    IRestartManager,
    IRestartPolicy,
    IServiceContainer,
    IServiceFactory,
    IServiceLifecycle,
    IStructuredLogger,
    ITemplateManager,
    IToolchainAnalyzer,
    MemoryHookInterface,
    MemoryServiceInterface,
    ModelCapability,
    ModelProvider,
    ModelResponse,
    ProjectAnalyzerInterface,
    RunnerConfigurationInterface,
    ServiceType,
    SessionManagementInterface,
    SocketIOServiceInterface,
    SubprocessLauncherInterface,
    SystemInstructionsInterface,
    T,
    TemplateRenderContext,
    TicketManagerInterface,
    UtilityServiceInterface,
    VersionServiceInterface,
)

# All interface definitions have been moved to the interfaces/ package
# This file now serves as a compatibility layer that delegates to the modular structure
