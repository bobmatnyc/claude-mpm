"""Core components for Claude MPM.

Lazy imports for all components to avoid loading heavy dependencies
when only importing lightweight utilities (constants, logging_utils, etc).
"""

# Lazy imports via __getattr__ to prevent loading heavy dependencies
# when hooks only need lightweight utilities
def __getattr__(name):
    """Lazy load core components only when accessed."""
    if name == "ClaudeRunner":
        from .claude_runner import ClaudeRunner
        return ClaudeRunner
    elif name == "Config":
        from .config import Config
        return Config
    elif name == "DIContainer":
        from .container import DIContainer
        return DIContainer
    elif name == "ServiceLifetime":
        from .container import ServiceLifetime
        return ServiceLifetime
    elif name == "get_container":
        from .container import get_container
        return get_container
    elif name == "AgentServiceFactory":
        from .factories import AgentServiceFactory
        return AgentServiceFactory
    elif name == "ConfigurationFactory":
        from .factories import ConfigurationFactory
        return ConfigurationFactory
    elif name == "ServiceFactory":
        from .factories import ServiceFactory
        return ServiceFactory
    elif name == "SessionManagerFactory":
        from .factories import SessionManagerFactory
        return SessionManagerFactory
    elif name == "get_factory_registry":
        from .factories import get_factory_registry
        return get_factory_registry
    elif name == "InjectableService":
        from .injectable_service import InjectableService
        return InjectableService
    elif name == "LoggerMixin":
        from .mixins import LoggerMixin
        return LoggerMixin
    elif name == "ServiceRegistry":
        from .service_registry import ServiceRegistry
        return ServiceRegistry
    elif name == "get_service_registry":
        from .service_registry import get_service_registry
        return get_service_registry
    elif name == "initialize_services":
        from .service_registry import initialize_services
        return initialize_services
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
