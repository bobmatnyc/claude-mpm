"""Core components for Claude MPM."""

from .claude_runner import ClaudeRunner
from .mixins import LoggerMixin

# Import config components if needed
try:
    from .config import Config
    from .config_aliases import ConfigAliases
except ImportError:
    pass

# Import DI components
try:
    from .container import DIContainer, ServiceLifetime, get_container
    from .service_registry import ServiceRegistry, get_service_registry, initialize_services
    from .injectable_service import InjectableService
    from .factories import (
        ServiceFactory, HookManagerFactory, OrchestratorFactoryWrapper,
        AgentServiceFactory, SessionManagerFactory, ConfigurationFactory,
        get_factory_registry
    )
except ImportError:
    pass

__all__ = [
    "ClaudeRunner",
    "LoggerMixin",
    "Config",
    "ConfigAliases",
    "DIContainer",
    "ServiceLifetime",
    "get_container",
    "ServiceRegistry",
    "get_service_registry",
    "initialize_services",
    "InjectableService",
    "ServiceFactory",
    "HookManagerFactory",
    "OrchestratorFactoryWrapper",
    "AgentServiceFactory",
    "SessionManagerFactory",
    "ConfigurationFactory",
    "get_factory_registry",
]