"""Services for Claude MPM."""

# Use lazy imports to prevent circular dependency issues
def __getattr__(name):
    """Lazy import to prevent circular dependencies."""
    if name == "TicketManager":
        from .ticket_manager import TicketManager
        return TicketManager
    elif name == "AgentDeploymentService":
        from .agent_deployment import AgentDeploymentService
        return AgentDeploymentService
    elif name == "AgentMemoryManager":
        from .agent_memory_manager import AgentMemoryManager
        return AgentMemoryManager
    elif name == "get_memory_manager":
        from .agent_memory_manager import get_memory_manager
        return get_memory_manager
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
]