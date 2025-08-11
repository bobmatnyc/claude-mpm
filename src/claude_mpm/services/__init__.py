"""Services for Claude MPM."""

# Use lazy imports to prevent circular dependency issues
def __getattr__(name):
    """Lazy import to prevent circular dependencies."""
    if name == "TicketManager":
        from .ticket_manager import TicketManager
        return TicketManager
    elif name == "AgentDeploymentService":
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
        from .project_analyzer import ProjectAnalyzer
        return ProjectAnalyzer
    elif name == "AdvancedHealthMonitor":
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
    elif name == "StandaloneSocketIOServer":
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
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = [
    "TicketManager",
    "AgentDeploymentService",
    "AgentMemoryManager",
    "get_memory_manager",
    "HookService",
    "ProjectAnalyzer",
    "AdvancedHealthMonitor",
    "RecoveryManager", 
    "StandaloneSocketIOServer",
    # Additional agent services for backward compatibility
    "AgentRegistry",
    "AgentLifecycleManager",
    "AgentManager",
    "AgentCapabilitiesGenerator",
    "AgentModificationTracker",
    "AgentPersistenceService",
    "AgentProfileLoader",
    "AgentVersionManager",
    "BaseAgentManager",
    "DeployedAgentDiscovery",
    "FrameworkAgentLoader",
    # Memory services (backward compatibility)
    "MemoryBuilder",
    "MemoryRouter",
    "MemoryOptimizer",
    "SimpleCacheService",
    "SharedPromptCache",
]