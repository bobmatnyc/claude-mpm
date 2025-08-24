"""
Service factory utilities to reduce service creation duplication.
"""

from typing import Any, Dict, Optional, Type, TypeVar

from ...core.config import Config
from ...core.logger import get_logger
from ...core.shared import ConfigLoader, PathResolver, SingletonManager

T = TypeVar("T")


class ServiceFactory:
    """
    Factory for creating services with common patterns.

    Reduces duplication by providing standard service creation patterns:
    - Configuration injection
    - Dependency resolution
    - Singleton management
    - Standard initialization
    """

    def __init__(self):
        """Initialize service factory."""
        self.logger = get_logger("service_factory")
        self._config_loader = ConfigLoader()
        self._path_resolver = PathResolver()
        self._registered_services: Dict[str, Type] = {}

    def register_service(self, service_name: str, service_class: Type[T]) -> None:
        """
        Register a service class.

        Args:
            service_name: Name to register service under
            service_class: Service class to register
        """
        self._registered_services[service_name] = service_class
        self.logger.debug(
            f"Registered service: {service_name} -> {service_class.__name__}"
        )

    def create_service(
        self,
        service_class: Type[T],
        service_name: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        singleton: bool = False,
        **kwargs,
    ) -> T:
        """
        Create a service instance with standard patterns.

        Args:
            service_class: Service class to instantiate
            service_name: Optional service name (defaults to class name)
            config: Optional configuration override
            singleton: Whether to use singleton pattern
            **kwargs: Additional constructor arguments

        Returns:
            Service instance
        """
        if service_name is None:
            service_name = service_class.__name__

        self.logger.debug(f"Creating service: {service_name}")

        # Load configuration if not provided
        if config is None:
            config = self._load_service_config(service_name)

        # Prepare constructor arguments
        constructor_args = {"service_name": service_name, "config": config, **kwargs}

        # Filter arguments based on constructor signature
        filtered_args = self._filter_constructor_args(service_class, constructor_args)

        # Create instance
        if singleton:
            instance = SingletonManager.get_instance(service_class, **filtered_args)
        else:
            instance = service_class(**filtered_args)

        self.logger.info(f"Created service: {service_name} ({service_class.__name__})")
        return instance

    def create_registered_service(
        self,
        service_name: str,
        config: Optional[Dict[str, Any]] = None,
        singleton: bool = False,
        **kwargs,
    ) -> Any:
        """
        Create a service by registered name.

        Args:
            service_name: Name of registered service
            config: Optional configuration override
            singleton: Whether to use singleton pattern
            **kwargs: Additional constructor arguments

        Returns:
            Service instance

        Raises:
            ValueError: If service not registered
        """
        if service_name not in self._registered_services:
            raise ValueError(f"Service not registered: {service_name}")

        service_class = self._registered_services[service_name]
        return self.create_service(
            service_class=service_class,
            service_name=service_name,
            config=config,
            singleton=singleton,
            **kwargs,
        )

    def create_agent_service(
        self,
        service_class: Type[T],
        agent_name: str,
        agent_dir: Optional[str] = None,
        **kwargs,
    ) -> T:
        """
        Create an agent-related service.

        Args:
            service_class: Service class to instantiate
            agent_name: Name of the agent
            agent_dir: Optional agent directory
            **kwargs: Additional constructor arguments

        Returns:
            Service instance
        """
        # Load agent-specific configuration
        config = self._config_loader.load_agent_config(agent_dir)

        # Add agent-specific paths
        if agent_dir:
            agent_path = self._path_resolver.resolve_relative_path(agent_dir)
        else:
            agent_path = self._path_resolver.find_agent_file(agent_name)
            if agent_path:
                agent_path = agent_path.parent

        constructor_args = {
            "agent_name": agent_name,
            "agent_dir": agent_path,
            "config": config,
            **kwargs,
        }

        return self.create_service(
            service_class=service_class,
            service_name=f"agent_{agent_name}",
            config=config,
            **constructor_args,
        )

    def create_memory_service(
        self,
        service_class: Type[T],
        agent_name: Optional[str] = None,
        memory_dir: Optional[str] = None,
        **kwargs,
    ) -> T:
        """
        Create a memory-related service.

        Args:
            service_class: Service class to instantiate
            agent_name: Optional agent name
            memory_dir: Optional memory directory
            **kwargs: Additional constructor arguments

        Returns:
            Service instance
        """
        # Load memory-specific configuration
        config = self._config_loader.load_memory_config(memory_dir)

        # Resolve memory directory
        if memory_dir:
            memory_path = self._path_resolver.resolve_relative_path(memory_dir)
        else:
            memory_path = self._path_resolver.resolve_memories_dir(create=True)

        constructor_args = {"memory_dir": memory_path, "config": config, **kwargs}

        if agent_name:
            constructor_args["agent_name"] = agent_name

        service_name = f"memory_{agent_name}" if agent_name else "memory"

        return self.create_service(
            service_class=service_class,
            service_name=service_name,
            config=config,
            **constructor_args,
        )

    def create_config_service(
        self, service_class: Type[T], config_section: Optional[str] = None, **kwargs
    ) -> T:
        """
        Create a configuration-heavy service.

        Args:
            service_class: Service class to instantiate
            config_section: Configuration section name
            **kwargs: Additional constructor arguments

        Returns:
            Service instance
        """
        # Load service-specific configuration
        service_name = config_section or service_class.__name__.lower()
        config = self._config_loader.load_service_config(service_name)

        constructor_args = {
            "config": config,
            "config_section": config_section,
            **kwargs,
        }

        return self.create_service(
            service_class=service_class,
            service_name=service_name,
            config=config,
            **constructor_args,
        )

    def _load_service_config(self, service_name: str) -> Config:
        """Load configuration for a service."""
        try:
            return self._config_loader.load_service_config(service_name)
        except Exception as e:
            self.logger.warning(f"Failed to load config for {service_name}: {e}")
            # Return default config using ConfigLoader
            return self._config_loader.load_main_config()

    def _filter_constructor_args(
        self, service_class: Type, args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Filter constructor arguments based on class signature."""
        import inspect

        try:
            # Get constructor signature
            sig = inspect.signature(service_class.__init__)
            param_names = set(sig.parameters.keys()) - {"self"}

            # Filter arguments
            filtered = {k: v for k, v in args.items() if k in param_names}

            # Log filtered arguments
            if len(filtered) != len(args):
                filtered_out = set(args.keys()) - set(filtered.keys())
                self.logger.debug(f"Filtered out arguments: {filtered_out}")

            return filtered

        except Exception as e:
            self.logger.warning(f"Failed to filter constructor args: {e}")
            return args

    def get_registered_services(self) -> Dict[str, str]:
        """
        Get list of registered services.

        Returns:
            Dictionary mapping service names to class names
        """
        return {name: cls.__name__ for name, cls in self._registered_services.items()}

    def clear_registrations(self) -> None:
        """Clear all service registrations."""
        self._registered_services.clear()
        self.logger.debug("Cleared all service registrations")


# Global factory instance
_global_factory = ServiceFactory()


def get_service_factory() -> ServiceFactory:
    """Get global service factory instance."""
    return _global_factory


def create_service(service_class: Type[T], **kwargs) -> T:
    """Convenience function to create service using global factory."""
    return _global_factory.create_service(service_class, **kwargs)


def register_service(service_name: str, service_class: Type) -> None:
    """Convenience function to register service with global factory."""
    _global_factory.register_service(service_name, service_class)
