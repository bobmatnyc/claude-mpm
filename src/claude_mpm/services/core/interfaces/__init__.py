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
from .agent import (  # Agent registry; Agent deployment; Agent capabilities; System instructions; Subprocess management; Runner configuration
    AgentCapabilitiesInterface,
    AgentDeploymentInterface,
    AgentMetadata,
    IAgentRegistry,
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
__all__ = [
    "AgentCapabilitiesInterface",
    "AgentDeploymentInterface",
    "AgentMetadata",
    "CacheEntry",
    "CommandHandlerInterface",
    "HealthStatus",
    "HookServiceInterface",
    # Agent interfaces
    "IAgentRegistry",
    "ICacheService",
    "IConfigurationManager",
    "IConfigurationService",
    "IErrorHandler",
    "IEventBus",
    "IHealthMonitor",
    "IPerformanceMonitor",
    "IPromptCache",
    # Infrastructure interfaces
    "IServiceContainer",
    "IServiceFactory",
    "IServiceLifecycle",
    "IStructuredLogger",
    "ITemplateManager",
    # Registry
    "InterfaceRegistry",
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
