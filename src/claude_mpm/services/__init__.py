"""Services for Claude MPM.

This module provides backward compatibility for the reorganized service layer.
Part of TSK-0046: Service Layer Architecture Reorganization

New structure:
- core/: Core interfaces and base classes
- agent/: Agent-related services
- communication/: SocketIO and WebSocket services
- project/: Project management services
- infrastructure/: Logging and monitoring services
"""


# Use lazy imports to prevent circular dependency issues
def __getattr__(name):
    """Lazy import to prevent circular dependencies."""
    if name == "TicketManager":
        from .ticket_manager import TicketManager

        return TicketManager
    if name == "AgentDeploymentService":
        # Use correct path
        from .agents.deployment import AgentDeploymentService

        return AgentDeploymentService
    if name == "AgentMemoryManager":
        from .agents.memory import AgentMemoryManager

        return AgentMemoryManager
    if name == "get_memory_manager":
        from .agents.memory import get_memory_manager

        return get_memory_manager
    # Add backward compatibility for other agent services
    if name == "AgentRegistry":
        # Use correct path
        from .agents.registry import AgentRegistry

        return AgentRegistry
    if name == "AgentLifecycleManager":
        from .agents.deployment import AgentLifecycleManager

        return AgentLifecycleManager
    if name == "AgentManager":
        from .agents.management import AgentManager

        return AgentManager
    if name == "AgentCapabilitiesGenerator":
        from .agents.management import AgentCapabilitiesGenerator

        return AgentCapabilitiesGenerator
    if name == "AgentModificationTracker":
        from .agents.registry import AgentModificationTracker

        return AgentModificationTracker
    if name == "AgentPersistenceService":
        from .agents.memory import AgentPersistenceService

        return AgentPersistenceService
    if name == "AgentProfileLoader":
        from .agents.loading import AgentProfileLoader

        return AgentProfileLoader
    if name == "AgentVersionManager":
        from .agents.deployment import AgentVersionManager

        return AgentVersionManager
    if name == "BaseAgentManager":
        from .agents.loading import BaseAgentManager

        return BaseAgentManager
    if name == "DeployedAgentDiscovery":
        from .agents.registry import DeployedAgentDiscovery

        return DeployedAgentDiscovery
    if name == "FrameworkAgentLoader":
        from .agents.loading import FrameworkAgentLoader

        return FrameworkAgentLoader
    if name == "HookService":
        from .hook_service import HookService

        return HookService
    if name == "ProjectAnalyzer":
        from .project.analyzer import ProjectAnalyzer

        return ProjectAnalyzer
    if name == "AdvancedHealthMonitor":
        from .infrastructure.monitoring import AdvancedHealthMonitor

        return AdvancedHealthMonitor
    if name == "HealthMonitor":
        # For backward compatibility, return AdvancedHealthMonitor
        # Note: There's also a different HealthMonitor in infrastructure.health_monitor
        from .infrastructure.monitoring import AdvancedHealthMonitor

        return AdvancedHealthMonitor
    if name == "RecoveryManager":
        try:
            from .recovery_manager import RecoveryManager

            return RecoveryManager
        except ImportError:
            raise AttributeError(f"Recovery management not available: {name}")
    elif name in {"StandaloneSocketIOServer", "SocketIOServer"}:
        from .socketio_server import SocketIOServer

        return SocketIOServer
    # Backward compatibility for memory services
    elif name == "MemoryBuilder":
        from .memory.builder import MemoryBuilder

        return MemoryBuilder
    elif name == "MemoryRouter":
        from .memory.router import MemoryRouter

        return MemoryRouter
    elif name == "MemoryOptimizer":
        from .memory.optimizer import MemoryOptimizer

        return MemoryOptimizer
    elif name == "SimpleCacheService":
        from .memory.cache.simple_cache import SimpleCacheService

        return SimpleCacheService
    elif name == "SharedPromptCache":
        from .memory.cache.shared_prompt_cache import SharedPromptCache

        return SharedPromptCache
    # New service organization imports
    elif name == "AgentManagementService":
        from .agents.management import AgentManager

        return AgentManager
    elif name == "ProjectRegistry":
        from .project.registry import ProjectRegistry

        return ProjectRegistry
    elif name == "LoggingService":
        from .infrastructure.logging import LoggingService

        return LoggingService
    elif name == "SocketIOClientManager":
        from .socketio_client_manager import SocketIOClientManager

        return SocketIOClientManager
    # MCP Gateway services
    elif name == "MCPConfiguration":
        from .mcp_gateway.config.configuration import MCPConfiguration

        return MCPConfiguration
    elif name == "MCPConfigLoader":
        from .mcp_gateway.config.config_loader import MCPConfigLoader

        return MCPConfigLoader
    elif name == "MCPServer":
        from .mcp_gateway.server.mcp_server import MCPServer

        return MCPServer
    elif name == "MCPToolRegistry":
        from .mcp_gateway.tools.tool_registry import MCPToolRegistry

        return MCPToolRegistry
    elif name == "BaseMCPService":
        from .mcp_gateway.core.base import BaseMCPService

        return BaseMCPService
    elif name.startswith("IMCP"):
        from .mcp_gateway.core import interfaces

        return getattr(interfaces, name)
    elif name.startswith("MCP") and "Error" in name:
        from .mcp_gateway.core import exceptions

        return getattr(exceptions, name)
    # Core interfaces and base classes
    elif name.startswith("I") or name in [
        "BaseService",
        "SyncBaseService",
        "SingletonService",
    ]:
        from . import core

        return getattr(core, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    "AdvancedHealthMonitor",
    "AgentCapabilitiesGenerator",
    "AgentDeploymentService",
    "AgentLifecycleManager",
    "AgentManagementService",  # New service
    "AgentManager",
    "AgentMemoryManager",
    "AgentModificationTracker",
    "AgentPersistenceService",
    "AgentProfileLoader",
    # Additional agent services for backward compatibility
    "AgentRegistry",
    "AgentVersionManager",
    "BaseAgentManager",
    "BaseMCPService",
    # Core exports
    "BaseService",
    "DeployedAgentDiscovery",
    "FrameworkAgentLoader",
    "HealthMonitor",  # New alias
    "HookService",
    # Infrastructure services
    "LoggingService",  # New service
    "MCPConfigLoader",
    # MCP Gateway services
    "MCPConfiguration",
    "MCPServer",
    "MCPToolRegistry",
    # Memory services (backward compatibility)
    "MemoryBuilder",
    "MemoryOptimizer",
    "MemoryRouter",
    "ProjectAnalyzer",
    # Project services
    "ProjectRegistry",  # New service
    "RecoveryManager",
    "SharedPromptCache",
    "SimpleCacheService",
    "SingletonService",
    # Communication services
    "SocketIOClientManager",  # New service
    "SocketIOServer",  # New alias
    "StandaloneSocketIOServer",
    "SyncBaseService",
    "TicketManager",
    "get_memory_manager",
]
