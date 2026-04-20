"""
Core Service Interfaces for Claude PM Framework
==============================================

DEPRECATED: This file has been moved to services/core/interfaces.py

This file is maintained for backward compatibility only.
All new code should import from claude_mpm.services.core.interfaces

Part of TSK-0046: Service Layer Architecture Reorganization

Original description:
This module defines the core service interfaces that establish contracts for
dependency injection, service discovery, and framework orchestration.

Phase 1 Refactoring: Interface extraction and dependency injection foundation
- IServiceContainer: Dependency injection container
- IAgentRegistry: Agent discovery and management
- IPromptCache: Performance-critical caching
- IHealthMonitor: Service health monitoring
- IConfigurationManager: Configuration management
- ITemplateManager: Template processing and rendering
- IServiceFactory: Service creation patterns

These interfaces reduce cyclomatic complexity and establish clean separation of concerns.
"""

# Keep original imports to prevent any parsing issues

# Re-export everything from the new location for backward compatibility
from claude_mpm.services.core.interfaces import (  # noqa: F401
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
