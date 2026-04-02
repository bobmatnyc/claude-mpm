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
    """Lazy import to prevent circular dependencies using dictionary-based mapping."""
    from importlib import import_module

    # Dictionary mapping: name -> (module_path, attribute_name)
    # For agent services, we import from the __init__.py modules to respect their import structure
    _LAZY_IMPORTS = {
        # Agent services - use __init__.py modules (not direct file paths) to respect import structure
        "AgentDeploymentService": (
            "claude_mpm.services.agents.deployment",
            "AgentDeploymentService",
        ),
        "AgentMemoryManager": (
            "claude_mpm.services.agents.memory",
            "AgentMemoryManager",
        ),
        "get_memory_manager": (
            "claude_mpm.services.agents.memory",
            "get_memory_manager",
        ),
        "AgentRegistry": ("claude_mpm.services.agents.registry", "AgentRegistry"),
        "AgentLifecycleManager": (
            "claude_mpm.services.agents.deployment",
            "AgentLifecycleManager",
        ),
        "AgentManager": ("claude_mpm.services.agents.management", "AgentManager"),
        "AgentCapabilitiesGenerator": (
            "claude_mpm.services.agents.management",
            "AgentCapabilitiesGenerator",
        ),
        "AgentModificationTracker": (
            "claude_mpm.services.agents.registry",
            "AgentModificationTracker",
        ),
        "AgentPersistenceService": (
            "claude_mpm.services.agents.memory",
            "AgentPersistenceService",
        ),
        "AgentProfileLoader": (
            "claude_mpm.services.agents.loading",
            "AgentProfileLoader",
        ),
        "AgentVersionManager": (
            "claude_mpm.services.agents.deployment",
            "AgentVersionManager",
        ),
        "BaseAgentManager": ("claude_mpm.services.agents.loading", "BaseAgentManager"),
        "DeployedAgentDiscovery": (
            "claude_mpm.services.agents.registry",
            "DeployedAgentDiscovery",
        ),
        "FrameworkAgentLoader": (
            "claude_mpm.services.agents.loading",
            "FrameworkAgentLoader",
        ),
        "AgentManagementService": (
            "claude_mpm.services.agents.management",
            "AgentManager",
        ),
        # Infrastructure services
        "HookService": ("claude_mpm.services.hook_service", "HookService"),
        "ProjectAnalyzer": ("claude_mpm.services.project.analyzer", "ProjectAnalyzer"),
        "AdvancedHealthMonitor": (
            "claude_mpm.services.infrastructure.monitoring",
            "AdvancedHealthMonitor",
        ),
        "HealthMonitor": (
            "claude_mpm.services.infrastructure.monitoring",
            "AdvancedHealthMonitor",
        ),
        "LoggingService": (
            "claude_mpm.services.infrastructure.logging",
            "LoggingService",
        ),
        # Communication services
        "StandaloneSocketIOServer": (
            "claude_mpm.services.socketio_server",
            "SocketIOServer",
        ),
        "SocketIOServer": ("claude_mpm.services.socketio_server", "SocketIOServer"),
        "SocketIOClientManager": (
            "claude_mpm.services.socketio_client_manager",
            "SocketIOClientManager",
        ),
        # Memory services
        "MemoryBuilder": ("claude_mpm.services.memory.builder", "MemoryBuilder"),
        "MemoryRouter": ("claude_mpm.services.memory.router", "MemoryRouter"),
        "MemoryOptimizer": ("claude_mpm.services.memory.optimizer", "MemoryOptimizer"),
        "SimpleCacheService": (
            "claude_mpm.services.memory.cache.simple_cache",
            "SimpleCacheService",
        ),
        "SharedPromptCache": (
            "claude_mpm.services.memory.cache.shared_prompt_cache",
            "SharedPromptCache",
        ),
        # Project services
        "ProjectRegistry": ("claude_mpm.services.project.registry", "ProjectRegistry"),
        # MCP Gateway services (removed in v6.x — kept as stubs for backward compat)
        # The mcp_gateway sub-package was deprecated and removed.
        # These entries are intentionally absent so __getattr__ falls through
        # to the AttributeError at the bottom of this function.
        # Other services
        "TicketManager": ("claude_mpm.services.ticket_manager", "TicketManager"),
    }

    # Handle direct mappings
    if name in _LAZY_IMPORTS:
        module_path, attr_name = _LAZY_IMPORTS[name]
        module = import_module(module_path)
        return getattr(module, attr_name)

    # Handle RecoveryManager with special error handling
    if name == "RecoveryManager":
        try:
            module = import_module("claude_mpm.services.recovery_manager")
            return module.RecoveryManager
        except ImportError as e:
            raise AttributeError(f"Recovery management not available: {name}") from e

    # MCP Gateway interfaces/exceptions were removed in v6.x.
    # Raise clear error for any remaining references.
    if name.startswith("IMCP") or (name.startswith("MCP") and "Error" in name):
        raise AttributeError(
            f"'{name}' is no longer available. "
            "The MCP gateway sub-package was removed in v6.x."
        )

    # Handle core interfaces and base classes
    if name.startswith("I") or name in [
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
    # Core exports
    "BaseService",
    "DeployedAgentDiscovery",
    "FrameworkAgentLoader",
    "HealthMonitor",  # New alias
    "HookService",
    # Infrastructure services
    "LoggingService",  # New service
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
