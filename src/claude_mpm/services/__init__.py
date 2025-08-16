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
    elif name == "AgentDeploymentService":
        # Try new location first, fall back to old
        try:
            from .agent.deployment import AgentDeploymentService
            return AgentDeploymentService
        except ImportError:
            from .agents.deployment import AgentDeploymentService
            return AgentDeploymentService
    elif name == "AgentMemoryManager":
        from .agents.memory import AgentMemoryManager
        return AgentMemoryManager
    elif name == "get_memory_manager":
        from .agents.memory import get_memory_manager
        return get_memory_manager
    # Add backward compatibility for other agent services
    elif name == "AgentRegistry":
        # Try new location first, fall back to old
        try:
            from .agent.registry import AgentRegistry
            return AgentRegistry
        except ImportError:
            from .agents.registry import AgentRegistry
            return AgentRegistry
    elif name == "AgentLifecycleManager":
        from .agents.deployment import AgentLifecycleManager
        return AgentLifecycleManager
    elif name == "AgentManager":
        from .agents.management import AgentManager
        return AgentManager
    elif name == "AgentCapabilitiesGenerator":
        from .agents.management import AgentCapabilitiesGenerator
        return AgentCapabilitiesGenerator
    elif name == "AgentModificationTracker":
        from .agents.registry import AgentModificationTracker
        return AgentModificationTracker
    elif name == "AgentPersistenceService":
        from .agents.memory import AgentPersistenceService
        return AgentPersistenceService
    elif name == "AgentProfileLoader":
        from .agents.loading import AgentProfileLoader
        return AgentProfileLoader
    elif name == "AgentVersionManager":
        from .agents.deployment import AgentVersionManager
        return AgentVersionManager
    elif name == "BaseAgentManager":
        from .agents.loading import BaseAgentManager
        return BaseAgentManager
    elif name == "DeployedAgentDiscovery":
        from .agents.registry import DeployedAgentDiscovery
        return DeployedAgentDiscovery
    elif name == "FrameworkAgentLoader":
        from .agents.loading import FrameworkAgentLoader
        return FrameworkAgentLoader
    elif name == "HookService":
        from .hook_service import HookService
        return HookService
    elif name == "ProjectAnalyzer":
        # Try new location first, fall back to old
        try:
            from .project.analyzer import ProjectAnalyzer
            return ProjectAnalyzer
        except ImportError:
            from .project_analyzer import ProjectAnalyzer
            return ProjectAnalyzer
    elif name == "AdvancedHealthMonitor" or name == "HealthMonitor":
        try:
            from .infrastructure.monitoring import HealthMonitor
            return HealthMonitor
        except ImportError:
            try:
                from .health_monitor import AdvancedHealthMonitor
                return AdvancedHealthMonitor
            except ImportError:
                raise AttributeError(f"Health monitoring not available: {name}")
    elif name == "RecoveryManager":
        try:
            from .recovery_manager import RecoveryManager
            return RecoveryManager
        except ImportError:
            raise AttributeError(f"Recovery management not available: {name}")
    elif name == "StandaloneSocketIOServer" or name == "SocketIOServer":
        try:
            from .communication.socketio import SocketIOServer
            return SocketIOServer
        except ImportError:
            from .standalone_socketio_server import StandaloneSocketIOServer
            return StandaloneSocketIOServer
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
        from .agent.management import AgentManagementService
        return AgentManagementService
    elif name == "ProjectRegistry":
        from .project.registry import ProjectRegistry
        return ProjectRegistry
    elif name == "LoggingService":
        from .infrastructure.logging import LoggingService
        return LoggingService
    elif name == "SocketIOClientManager":
        from .communication.websocket import SocketIOClientManager
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
    elif name.startswith('I') or name in ['BaseService', 'SyncBaseService', 'SingletonService']:
        from . import core
        return getattr(core, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = [
    "TicketManager",
    "AgentDeploymentService",
    "AgentMemoryManager",
    "get_memory_manager",
    "HookService",
    "ProjectAnalyzer",
    "AdvancedHealthMonitor",
    "HealthMonitor",  # New alias
    "RecoveryManager", 
    "StandaloneSocketIOServer",
    "SocketIOServer",  # New alias
    # Additional agent services for backward compatibility
    "AgentRegistry",
    "AgentLifecycleManager",
    "AgentManager",
    "AgentManagementService",  # New service
    "AgentCapabilitiesGenerator",
    "AgentModificationTracker",
    "AgentPersistenceService",
    "AgentProfileLoader",
    "AgentVersionManager",
    "BaseAgentManager",
    "DeployedAgentDiscovery",
    "FrameworkAgentLoader",
    # Project services
    "ProjectRegistry",  # New service
    # Infrastructure services
    "LoggingService",  # New service
    # Communication services
    "SocketIOClientManager",  # New service
    # Memory services (backward compatibility)
    "MemoryBuilder",
    "MemoryRouter",
    "MemoryOptimizer",
    "SimpleCacheService",
    "SharedPromptCache",
    # MCP Gateway services
    "MCPConfiguration",
    "MCPConfigLoader",
    "MCPServer",
    "MCPToolRegistry",
    "BaseMCPService",
    # Core exports
    "BaseService",
    "SyncBaseService",
    "SingletonService",
]