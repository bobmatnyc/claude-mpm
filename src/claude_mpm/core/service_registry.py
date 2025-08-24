"""
Service Registry for Claude MPM.

Provides centralized service registration and discovery, working with
the DI container to manage application services.
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, Union

from .base_service import BaseService
from .config import Config
from .container import DIContainer, ServiceLifetime, get_container
from .logger import get_logger
from .shared.config_loader import ConfigLoader

if TYPE_CHECKING:
    from claude_mpm.services.agents.deployment import AgentDeploymentService

logger = get_logger(__name__)


class ServiceRegistry:
    """
    Central registry for all application services.

    Manages service registration, configuration, and lifecycle.
    """

    def __init__(self, container: Optional[DIContainer] = None):
        """
        Initialize service registry.

        Args:
            container: DI container to use (uses global if not provided)
        """
        self.container = container or get_container()
        self._services: Dict[str, Type[BaseService]] = {}
        self._initialized = False

    def register_core_services(self) -> None:
        """Register all core framework services."""
        from claude_mpm.services.memory.cache.shared_prompt_cache import (
            SharedPromptCache,
        )

        from ..services import AgentDeploymentService
        from .agent_session_manager import AgentSessionManager
        from .session_manager import SessionManager

        # Register configuration as singleton with name using ConfigLoader
        config_loader = ConfigLoader()
        config = config_loader.load_main_config()
        self.container.register_singleton(Config, instance=config, name="main_config")

        # Register core services with proper lifetime management
        self.register_service(
            "session_manager", SessionManager, lifetime=ServiceLifetime.SINGLETON
        )

        self.register_service(
            "agent_session_manager",
            AgentSessionManager,
            lifetime=ServiceLifetime.SINGLETON,
            dependencies={"session_dir": lambda c: c.get(Config).get("session_dir")},
        )

        # Register shared cache as singleton with factory
        self.container.register_factory(
            SharedPromptCache,
            lambda c: SharedPromptCache.get_instance(),
            lifetime=ServiceLifetime.SINGLETON,
            name="prompt_cache",
        )

        # Ticket manager removed - use claude-mpm tickets CLI commands instead

        # Register agent deployment service with factory for better initialization
        self.container.register_factory(
            AgentDeploymentService,
            lambda c: self._create_agent_deployment_service(c),
            lifetime=ServiceLifetime.TRANSIENT,
            name="agent_deployment",
        )

        logger.info("Core services registered with enhanced DI container")

    def _create_agent_deployment_service(
        self, container: DIContainer
    ) -> "AgentDeploymentService":
        """Factory method for creating agent deployment service."""
        import os
        from pathlib import Path

        config = container.get(Config)

        # Get working directory from environment or config
        if "CLAUDE_MPM_USER_PWD" in os.environ:
            working_dir = Path(os.environ["CLAUDE_MPM_USER_PWD"])
        else:
            working_dir = Path(config.get("project.dir", "."))

        # Lazy import to avoid circular dependencies
        from claude_mpm.services.agents.deployment import AgentDeploymentService

        return AgentDeploymentService(working_directory=working_dir)

    def register_service(
        self,
        name: str,
        service_class: Type[BaseService],
        lifetime: ServiceLifetime = ServiceLifetime.SINGLETON,
        factory: Optional[Any] = None,
        dependencies: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Register a service with the registry.

        Args:
            name: Service name for lookup
            service_class: Service class (must inherit from BaseService)
            lifetime: Service lifetime management
            factory: Optional factory function
            dependencies: Optional dependency mapping
            config: Optional service-specific configuration
        """
        # Store service metadata
        self._services[name] = service_class

        # Create factory wrapper if config provided
        if config and not factory:

            def factory(c):
                return service_class(name=name, config=config, container=c)

        elif not factory:
            # Default factory with container injection
            def factory(c):
                return service_class(name=name, container=c)

        # Register with DI container
        self.container.register(
            service_class, factory=factory, lifetime=lifetime, dependencies=dependencies
        )

        logger.debug(f"Registered service: {name} ({service_class.__name__})")

    def get_service(self, service_type: Union[str, Type[BaseService]]) -> BaseService:
        """
        Get a service instance.

        Args:
            service_type: Service name or class

        Returns:
            Service instance
        """
        if isinstance(service_type, str):
            # First try to get by name from container
            try:
                # Use the enhanced container's named resolution
                return self.container.get(BaseService, name=service_type)
            except:
                # Fall back to looking up class and resolving
                if service_type not in self._services:
                    raise KeyError(f"Service '{service_type}' not registered")
                service_class = self._services[service_type]
                return self.container.get(service_class)
        else:
            # Direct class resolution
            return self.container.get(service_type)

    def get_service_optional(
        self,
        service_type: Union[str, Type[BaseService]],
        default: Optional[BaseService] = None,
    ) -> Optional[BaseService]:
        """Get a service if available, otherwise return default."""
        try:
            return self.get_service(service_type)
        except (KeyError, Exception):
            return default

    def start_all_services(self) -> None:
        """Start all registered singleton services."""
        import asyncio

        async def _start_all():
            for name, service_class in self._services.items():
                try:
                    # Only start singleton services
                    registration = self.container.get_all_registrations().get(
                        service_class
                    )
                    if (
                        registration
                        and registration.lifetime == ServiceLifetime.SINGLETON
                    ):
                        service = self.get_service(service_class)
                        if hasattr(service, "start"):
                            await service.start()
                            logger.info(f"Started service: {name}")
                except Exception as e:
                    logger.error(f"Failed to start service {name}: {e}")

        asyncio.run(_start_all())
        self._initialized = True

    def stop_all_services(self) -> None:
        """Stop all running singleton services."""
        import asyncio

        async def _stop_all():
            for name, service_class in reversed(list(self._services.items())):
                try:
                    # Only stop singleton services
                    registration = self.container.get_all_registrations().get(
                        service_class
                    )
                    if (
                        registration
                        and registration.lifetime == ServiceLifetime.SINGLETON
                    ) and service_class in self.container._singletons:
                        service = self.container._singletons[service_class]
                        if hasattr(service, "stop") and service.running:
                            await service.stop()
                            logger.info(f"Stopped service: {name}")
                except Exception as e:
                    logger.error(f"Failed to stop service {name}: {e}")

        asyncio.run(_stop_all())

    def get_service_health(self) -> Dict[str, Dict[str, Any]]:
        """Get health status of all services."""
        import asyncio

        async def _get_health():
            health_status = {}

            for name, service_class in self._services.items():
                try:
                    if service_class in self.container._singletons:
                        service = self.container._singletons[service_class]
                        if hasattr(service, "health_check"):
                            health = await service.health_check()
                            health_status[name] = {
                                "status": health.status,
                                "message": health.message,
                                "metrics": health.metrics,
                            }
                except Exception as e:
                    health_status[name] = {"status": "error", "message": str(e)}

            return health_status

        return asyncio.run(_get_health())

    def list_services(self) -> List[Dict[str, Any]]:
        """List all registered services with their metadata."""
        services = []

        for name, service_class in self._services.items():
            registration = self.container.get_all_registrations().get(service_class)

            service_info = {
                "name": name,
                "class": service_class.__name__,
                "module": service_class.__module__,
                "lifetime": registration.lifetime.value if registration else "unknown",
                "is_singleton": (
                    registration.lifetime == ServiceLifetime.SINGLETON
                    if registration
                    else False
                ),
                "is_running": False,
            }

            # Check if singleton is running
            if service_class in self.container._singletons:
                service = self.container._singletons[service_class]
                if hasattr(service, "running"):
                    service_info["is_running"] = service.running

            services.append(service_info)

        return services


# Global registry instance
_global_registry: Optional[ServiceRegistry] = None


def get_service_registry() -> ServiceRegistry:
    """Get the global service registry instance."""
    global _global_registry
    if _global_registry is None:
        _global_registry = ServiceRegistry()
        _global_registry.register_core_services()
    return _global_registry


def initialize_services(config: Optional[Dict[str, Any]] = None) -> ServiceRegistry:
    """
    Initialize all application services.

    Args:
        config: Optional configuration overrides

    Returns:
        Initialized service registry
    """
    registry = get_service_registry()

    if config:
        # Apply configuration overrides
        config_service = registry.container.resolve(Config)
        for key, value in config.items():
            config_service.set(key, value)

    # Start all services
    if not registry._initialized:
        registry.start_all_services()

    return registry
