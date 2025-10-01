"""Core components for Claude MPM.

Lazy imports for all components to avoid loading heavy dependencies
when only importing lightweight utilities (constants, logging_utils, etc).
"""


# Lazy imports via __getattr__ to prevent loading heavy dependencies
# when hooks only need lightweight utilities
def __getattr__(name):
    """Lazy load core components only when accessed using dictionary-based mapping."""
    from importlib import import_module

    # Dictionary mapping: name -> (module_path, attribute_name)
    _LAZY_IMPORTS = {
        # Core components
        "ClaudeRunner": ("claude_mpm.core.claude_runner", "ClaudeRunner"),
        "Config": ("claude_mpm.core.config", "Config"),
        # Dependency injection
        "DIContainer": ("claude_mpm.core.container", "DIContainer"),
        "ServiceLifetime": ("claude_mpm.core.container", "ServiceLifetime"),
        "get_container": ("claude_mpm.core.container", "get_container"),
        # Factories
        "AgentServiceFactory": ("claude_mpm.core.factories", "AgentServiceFactory"),
        "ConfigurationFactory": ("claude_mpm.core.factories", "ConfigurationFactory"),
        "ServiceFactory": ("claude_mpm.core.factories", "ServiceFactory"),
        "SessionManagerFactory": ("claude_mpm.core.factories", "SessionManagerFactory"),
        "get_factory_registry": ("claude_mpm.core.factories", "get_factory_registry"),
        # Services and utilities
        "InjectableService": (
            "claude_mpm.core.injectable_service",
            "InjectableService",
        ),
        "LoggerMixin": ("claude_mpm.core.mixins", "LoggerMixin"),
        # Service registry
        "ServiceRegistry": ("claude_mpm.core.service_registry", "ServiceRegistry"),
        "get_service_registry": (
            "claude_mpm.core.service_registry",
            "get_service_registry",
        ),
        "initialize_services": (
            "claude_mpm.core.service_registry",
            "initialize_services",
        ),
    }

    if name in _LAZY_IMPORTS:
        module_path, attr_name = _LAZY_IMPORTS[name]
        module = import_module(module_path)
        return getattr(module, attr_name)

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    "AgentServiceFactory",
    "ClaudeRunner",
    "Config",
    "ConfigurationFactory",
    "DIContainer",
    "InjectableService",
    "LoggerMixin",
    "ServiceFactory",
    "ServiceLifetime",
    "ServiceRegistry",
    "SessionManagerFactory",
    "get_container",
    "get_factory_registry",
    "get_service_registry",
    "initialize_services",
]
