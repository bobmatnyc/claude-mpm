"""
Core Interfaces Package for Claude MPM Framework
===============================================

WHY: This package contains the modular interface definitions that were extracted
from the monolithic interfaces.py file. The interfaces are now organized by
domain for better maintainability and discoverability.

DESIGN DECISION: Interfaces are grouped by domain (infrastructure, agent, service,
communication) rather than alphabetically to create logical cohesion and make
it easier to understand the system architecture.

REFACTORING IMPACT:
- Original interfaces.py: 1,437 lines with 34 classes
- Split into 4 focused modules: ~1,200 lines total
- Improved organization and maintainability
- Preserved all original functionality through re-exports

MODULES:
- infrastructure.py: Core framework services (DI, config, caching, health)
- agent.py: Agent management, deployment, and capabilities
- service.py: Business services (memory, hooks, utilities)
- communication.py: External communication (WebSocket, project analysis, tickets)
"""

# Agent interfaces (agent management and operations)
from .agent import (  # Agent registry; Agent deployment; Agent capabilities; System instructions; Subprocess management; Runner configuration; Agent recommendation; Auto-configuration
    AgentCapabilitiesInterface,
    AgentDeploymentInterface,
    AgentMetadata,
    IAgentRecommender,
    IAgentRegistry,
    IAutoConfigManager,
    RunnerConfigurationInterface,
    SubprocessLauncherInterface,
    SystemInstructionsInterface,
)

# Communication interfaces (external services)
from .communication import (  # WebSocket/SocketIO; Project analysis; Ticket management
    ProjectAnalyzerInterface,
    SocketIOServiceInterface,
    TicketManagerInterface,
)

# Health interfaces (health monitoring)
from .health import (  # Health checks; Health monitoring
    IHealthCheck,
    IHealthCheckManager,
)

# Infrastructure interfaces (core framework services)
from .infrastructure import (  # Type variables; Core dependency injection; Configuration management; Caching; Health monitoring; Template management; Service factory; Logging; Service lifecycle; Error handling; Performance monitoring; Event system
    CacheEntry,
    HealthStatus,
    ICacheService,
    IConfigurationManager,
    IConfigurationService,
    IErrorHandler,
    IEventBus,
    IHealthMonitor,
    IPerformanceMonitor,
    IPromptCache,
    IServiceContainer,
    IServiceFactory,
    IServiceLifecycle,
    IStructuredLogger,
    ITemplateManager,
    ServiceType,
    T,
    TemplateRenderContext,
)

# Model interfaces (content processing and model providers)
from .model import (  # Model providers; Routing
    IModelProvider,
    IModelRouter,
    ModelCapability,
    ModelProvider,
    ModelResponse,
)

# Process interfaces (local process management)
from .process import (  # Process lifecycle; State persistence
    IDeploymentStateManager,
    ILocalProcessManager,
)

# Project interfaces (project analysis and toolchain detection)
from .project import IToolchainAnalyzer  # Toolchain analysis

# Restart interfaces (auto-restart management)
from .restart import (  # Crash detection; Restart policy; Restart orchestration
    ICrashDetector,
    IRestartManager,
    IRestartPolicy,
)

# Service interfaces (business services)
from .service import (  # Version service; Command handling; Memory management; Session management; Utilities; Hook service
    CommandHandlerInterface,
    HookServiceInterface,
    MemoryHookInterface,
    MemoryServiceInterface,
    SessionManagementInterface,
    UtilityServiceInterface,
    VersionServiceInterface,
)

# Stability interfaces (proactive monitoring and crash prevention)
from .stability import (  # Memory leak detection; Log monitoring; Resource monitoring
    ILogMonitor,
    IMemoryLeakDetector,
    IResourceMonitor,
)


# Interface registry for dependency injection discovery
class InterfaceRegistry:
    """Registry of all core interfaces for dependency injection.

    WHY: Provides a centralized registry for interface discovery and
    dependency injection container registration. This enables dynamic
    service discovery and loose coupling between components.
    """

    _interfaces = {
        # Infrastructure interfaces
        "service_container": IServiceContainer,
        "configuration_service": IConfigurationService,
        "configuration_manager": IConfigurationManager,
        "cache_service": ICacheService,
        "prompt_cache": IPromptCache,
        "health_monitor": IHealthMonitor,
        "template_manager": ITemplateManager,
        "service_factory": IServiceFactory,
        "structured_logger": IStructuredLogger,
        "service_lifecycle": IServiceLifecycle,
        "error_handler": IErrorHandler,
        "performance_monitor": IPerformanceMonitor,
        "event_bus": IEventBus,
        # Agent interfaces
        "agent_registry": IAgentRegistry,
        "agent_deployment": AgentDeploymentInterface,
        "agent_capabilities": AgentCapabilitiesInterface,
        "system_instructions": SystemInstructionsInterface,
        "subprocess_launcher": SubprocessLauncherInterface,
        "runner_configuration": RunnerConfigurationInterface,
        # Service interfaces
        "version_service": VersionServiceInterface,
        "command_handler": CommandHandlerInterface,
        "memory_hook": MemoryHookInterface,
        "memory_service": MemoryServiceInterface,
        "session_management": SessionManagementInterface,
        "utility_service": UtilityServiceInterface,
        "hook_service": HookServiceInterface,
        # Communication interfaces
        "socketio_service": SocketIOServiceInterface,
        "project_analyzer": ProjectAnalyzerInterface,
        "ticket_manager": TicketManagerInterface,
        # Project interfaces
        "toolchain_analyzer": IToolchainAnalyzer,
        "agent_recommender": IAgentRecommender,
        "auto_config_manager": IAutoConfigManager,
        # Model interfaces
        "model_provider": IModelProvider,
        "model_router": IModelRouter,
        # Process interfaces
        "deployment_state_manager": IDeploymentStateManager,
        "local_process_manager": ILocalProcessManager,
        # Health interfaces
        "health_check": IHealthCheck,
        "health_check_manager": IHealthCheckManager,
        # Restart interfaces
        "crash_detector": ICrashDetector,
        "restart_policy": IRestartPolicy,
        "restart_manager": IRestartManager,
        # Stability interfaces
        "memory_leak_detector": IMemoryLeakDetector,
        "log_monitor": ILogMonitor,
        "resource_monitor": IResourceMonitor,
    }

    @classmethod
    def get_interface(cls, name: str):
        """Get interface by name."""
        return cls._interfaces.get(name)

    @classmethod
    def get_all_interfaces(cls):
        """Get all registered interfaces."""
        return cls._interfaces.copy()

    @classmethod
    def register_interface(cls, name: str, interface_class):
        """Register a new interface."""
        cls._interfaces[name] = interface_class

    @classmethod
    def list_interface_names(cls):
        """Get list of all interface names."""
        return list(cls._interfaces.keys())


# Re-export everything for backward compatibility
__all__ = [  # noqa: RUF022 - Semantic grouping by domain preferred over alphabetical
    "AgentCapabilitiesInterface",
    "AgentDeploymentInterface",
    "AgentMetadata",
    "CacheEntry",
    "CommandHandlerInterface",
    "HealthStatus",
    "HookServiceInterface",
    # Agent interfaces
    "IAgentRecommender",
    "IAgentRegistry",
    "IAutoConfigManager",
    "ICacheService",
    "IConfigurationManager",
    "IConfigurationService",
    # Process interfaces
    "IDeploymentStateManager",
    "IErrorHandler",
    "IEventBus",
    # Health interfaces
    "IHealthCheck",
    "IHealthCheckManager",
    "IHealthMonitor",
    # Infrastructure interfaces
    "ILocalProcessManager",
    # Restart interfaces
    "ICrashDetector",
    "IRestartManager",
    "IRestartPolicy",
    # Stability interfaces
    "IMemoryLeakDetector",
    "ILogMonitor",
    "IResourceMonitor",
    # Model interfaces
    "IModelProvider",
    "IModelRouter",
    "IPerformanceMonitor",
    "IPromptCache",
    "IServiceContainer",
    "IServiceFactory",
    "IServiceLifecycle",
    "IStructuredLogger",
    "ITemplateManager",
    # Project interfaces
    "IToolchainAnalyzer",
    # Registry
    "InterfaceRegistry",
    "ModelCapability",
    "ModelProvider",
    "ModelResponse",
    "MemoryHookInterface",
    "MemoryServiceInterface",
    "ProjectAnalyzerInterface",
    "RunnerConfigurationInterface",
    "ServiceType",
    "SessionManagementInterface",
    # Communication interfaces
    "SocketIOServiceInterface",
    "SubprocessLauncherInterface",
    "SystemInstructionsInterface",
    # Type variables
    "T",
    "TemplateRenderContext",
    "TicketManagerInterface",
    "UtilityServiceInterface",
    # Service interfaces
    "VersionServiceInterface",
]
