"""
Service Container with Dependency Injection
===========================================

WHY: This service container provides comprehensive dependency injection to manage
all services in the Claude MPM framework, enabling loose coupling, better testability,
and simplified service management.

DESIGN DECISIONS:
- Thread-safe implementation for concurrent service resolution
- Support for singleton, transient, and factory patterns
- Automatic dependency resolution based on constructor parameters
- Circular dependency detection and prevention
- Lazy initialization support for expensive services

FEATURES:
- Service registration (interface → implementation mapping)
- Automatic dependency injection based on type hints
- Multiple lifetime management strategies
- Factory pattern support for complex creation logic
- Service resolution with automatic dependency graph traversal
"""

import inspect
import threading
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union

from claude_mpm.core.logger import get_logger

# Type variable for generic service types
T = TypeVar("T")


class ServiceLifetime(Enum):
    """Service lifetime management strategies."""

    SINGLETON = "singleton"  # Single instance for entire application lifetime
    TRANSIENT = "transient"  # New instance for each resolution
    SCOPED = "scoped"  # Single instance per scope (e.g., request)


class ServiceDescriptor:
    """Describes a registered service."""

    def __init__(
        self,
        service_type: Type,
        implementation: Optional[Type] = None,
        instance: Optional[Any] = None,
        factory: Optional[Callable] = None,
        lifetime: ServiceLifetime = ServiceLifetime.SINGLETON,
    ):
        """
        Initialize service descriptor.

        Args:
            service_type: The interface or base type
            implementation: The concrete implementation class
            instance: Pre-created instance (for singleton registration)
            factory: Factory function to create instances
            lifetime: Service lifetime management strategy
        """
        self.service_type = service_type
        self.implementation = implementation
        self.instance = instance
        self.factory = factory
        self.lifetime = lifetime
        self.lock = threading.RLock()  # For thread-safe singleton creation

        # Validate descriptor
        if not any([implementation, instance, factory]):
            raise ValueError(
                "Service descriptor must have either implementation, instance, or factory"
            )


class CircularDependencyError(Exception):
    """Raised when circular dependencies are detected."""

    def __init__(self, resolution_chain: List[Type]):
        self.resolution_chain = resolution_chain
        chain_str = " -> ".join(t.__name__ for t in resolution_chain)
        super().__init__(f"Circular dependency detected: {chain_str}")


class ServiceNotFoundError(Exception):
    """Raised when a required service is not registered."""

    def __init__(self, service_type: Type):
        self.service_type = service_type
        super().__init__(f"Service not registered: {service_type.__name__}")


class ServiceContainer:
    """
    Dependency injection container for service management.

    This container provides:
    - Service registration with lifetime management
    - Automatic dependency resolution
    - Circular dependency detection
    - Thread-safe service creation
    - Factory pattern support
    """

    def __init__(self):
        """Initialize the service container."""
        self.logger = get_logger("service_container")
        self._services: Dict[Type, ServiceDescriptor] = {}
        self._lock = threading.RLock()
        self._resolution_stack: threading.local = threading.local()

        # Register the container itself for self-injection scenarios
        self.register_instance(ServiceContainer, self)

        self.logger.debug("Service container initialized")

    def register(
        self,
        service_type: Type[T],
        implementation: Type[T],
        lifetime: Union[ServiceLifetime, bool] = ServiceLifetime.SINGLETON,
    ) -> None:
        """
        Register a service implementation.

        Args:
            service_type: The interface or base type to register
            implementation: The concrete implementation class
            lifetime: Service lifetime (ServiceLifetime enum or bool for backward compat)
                     If bool: True = SINGLETON, False = TRANSIENT

        Example:
            container.register(ICacheManager, CacheManager, ServiceLifetime.SINGLETON)
            # or for backward compatibility:
            container.register(ICacheManager, CacheManager, singleton=True)
        """
        # Handle backward compatibility for singleton parameter
        if isinstance(lifetime, bool):
            lifetime = (
                ServiceLifetime.SINGLETON if lifetime else ServiceLifetime.TRANSIENT
            )

        with self._lock:
            # Validate implementation
            if not self._is_valid_implementation(service_type, implementation):
                self.logger.warning(
                    f"Implementation {implementation.__name__} may not properly implement "
                    f"{service_type.__name__}"
                )

            descriptor = ServiceDescriptor(
                service_type=service_type,
                implementation=implementation,
                lifetime=lifetime,
            )

            self._services[service_type] = descriptor

            self.logger.debug(
                f"Registered {implementation.__name__} for {service_type.__name__} "
                f"with {lifetime.value} lifetime"
            )

    def register_instance(self, service_type: Type[T], instance: T) -> None:
        """
        Register a pre-created service instance (always singleton).

        Args:
            service_type: The interface or base type to register
            instance: The pre-created instance

        Example:
            cache_manager = CacheManager()
            container.register_instance(ICacheManager, cache_manager)
        """
        with self._lock:
            descriptor = ServiceDescriptor(
                service_type=service_type,
                instance=instance,
                lifetime=ServiceLifetime.SINGLETON,
            )

            self._services[service_type] = descriptor

            self.logger.debug(
                f"Registered instance of {instance.__class__.__name__} "
                f"for {service_type.__name__}"
            )

    def register_factory(
        self,
        service_type: Type[T],
        factory: Callable[[], T],
        lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT,
    ) -> None:
        """
        Register a factory function for service creation.

        Args:
            service_type: The interface or base type to register
            factory: Factory function that creates instances
            lifetime: Service lifetime management strategy

        Example:
            def create_logger():
                return Logger(config=get_config())

            container.register_factory(ILogger, create_logger)
        """
        with self._lock:
            descriptor = ServiceDescriptor(
                service_type=service_type, factory=factory, lifetime=lifetime
            )

            self._services[service_type] = descriptor

            self.logger.debug(
                f"Registered factory for {service_type.__name__} "
                f"with {lifetime.value} lifetime"
            )

    def resolve(self, service_type: Type[T]) -> T:
        """
        Resolve a service by type with automatic dependency injection.

        Args:
            service_type: The interface or type to resolve

        Returns:
            The resolved service instance

        Raises:
            ServiceNotFoundError: If the service is not registered
            CircularDependencyError: If circular dependencies are detected

        Example:
            cache_manager = container.resolve(ICacheManager)
        """
        # Initialize resolution stack for this thread if needed
        if not hasattr(self._resolution_stack, "stack"):
            self._resolution_stack.stack = []

        # Check for circular dependencies
        if service_type in self._resolution_stack.stack:
            raise CircularDependencyError([*self._resolution_stack.stack, service_type])

        try:
            # Add to resolution stack
            self._resolution_stack.stack.append(service_type)

            with self._lock:
                # Check if service is registered
                if service_type not in self._services:
                    raise ServiceNotFoundError(service_type)

                descriptor = self._services[service_type]

                # Handle different lifetime strategies
                if descriptor.lifetime == ServiceLifetime.SINGLETON:
                    return self._resolve_singleton(descriptor)
                if descriptor.lifetime == ServiceLifetime.TRANSIENT:
                    return self._resolve_transient(descriptor)
                if descriptor.lifetime == ServiceLifetime.SCOPED:
                    # TODO: Implement scoped lifetime (requires scope context)
                    return self._resolve_transient(descriptor)
                raise ValueError(f"Unknown lifetime: {descriptor.lifetime}")

        finally:
            # Remove from resolution stack
            self._resolution_stack.stack.pop()

    def resolve_all(self, service_type: Type[T]) -> List[T]:
        """
        Resolve all implementations of a service type.

        Args:
            service_type: The interface or base type to resolve

        Returns:
            List of all registered implementations

        Example:
            handlers = container.resolve_all(IEventHandler)
        """
        results = []

        with self._lock:
            for registered_type, _descriptor in self._services.items():
                # Check if registered type is subclass of requested type
                if self._is_assignable(registered_type, service_type):
                    try:
                        instance = self.resolve(registered_type)
                        results.append(instance)
                    except Exception as e:
                        self.logger.warning(
                            f"Failed to resolve {registered_type.__name__}: {e}"
                        )

        return results

    def is_registered(self, service_type: Type) -> bool:
        """
        Check if a service type is registered.

        Args:
            service_type: The interface or type to check

        Returns:
            True if the service is registered, False otherwise

        Example:
            if container.is_registered(ICacheManager):
                cache = container.resolve(ICacheManager)
        """
        with self._lock:
            return service_type in self._services

    def clear(self) -> None:
        """Clear all registered services except the container itself."""
        with self._lock:
            # Keep reference to self registration
            self_descriptor = self._services.get(ServiceContainer)

            # Clear all services
            self._services.clear()

            # Re-register self if it was registered
            if self_descriptor:
                self._services[ServiceContainer] = self_descriptor

            self.logger.debug("Service container cleared")

    # Private helper methods

    def _resolve_singleton(self, descriptor: ServiceDescriptor) -> Any:
        """Resolve a singleton service."""
        with descriptor.lock:
            # Return existing instance if available
            if descriptor.instance is not None:
                return descriptor.instance

            # Create new instance
            if descriptor.factory:
                instance = descriptor.factory()
            elif descriptor.implementation:
                instance = self._create_instance(descriptor.implementation)
            else:
                raise ValueError("No way to create service instance")

            # Cache the instance
            descriptor.instance = instance

            return instance

    def _resolve_transient(self, descriptor: ServiceDescriptor) -> Any:
        """Resolve a transient service (new instance each time)."""
        if descriptor.instance is not None:
            # Pre-created instances are always returned as-is
            return descriptor.instance

        if descriptor.factory:
            return descriptor.factory()
        if descriptor.implementation:
            return self._create_instance(descriptor.implementation)
        raise ValueError("No way to create service instance")

    def _create_instance(self, implementation: Type) -> Any:
        """
        Create an instance with automatic dependency injection.

        Args:
            implementation: The class to instantiate

        Returns:
            The created instance with injected dependencies
        """
        # Get constructor signature
        try:
            sig = inspect.signature(implementation.__init__)
        except (ValueError, TypeError):
            # Fallback for classes without proper __init__
            return implementation()

        # Resolve constructor dependencies
        kwargs = {}
        for param_name, param in sig.parameters.items():
            # Skip 'self' parameter
            if param_name == "self":
                continue

            # Get type hint for parameter
            param_type = param.annotation

            # Skip if no type hint or if it's not a class
            if param_type == inspect.Parameter.empty:
                # Use default value if available
                if param.default != inspect.Parameter.empty:
                    kwargs[param_name] = param.default
                continue

            # Handle Optional types
            origin = getattr(param_type, "__origin__", None)
            if origin is Union:
                # Get the non-None type from Optional[T]
                args = getattr(param_type, "__args__", ())
                non_none_types = [t for t in args if t != type(None)]
                if non_none_types:
                    param_type = non_none_types[0]
                else:
                    continue

            # Try to resolve the dependency
            if isinstance(param_type, type) and self.is_registered(param_type):
                try:
                    kwargs[param_name] = self.resolve(param_type)
                    self.logger.debug(
                        f"Injected {param_type.__name__} into {implementation.__name__}.{param_name}"
                    )
                except CircularDependencyError:
                    # Re-raise circular dependency errors to trigger proper handling
                    raise
                except Exception as e:
                    self.logger.warning(
                        f"Failed to inject {param_type.__name__} into "
                        f"{implementation.__name__}.{param_name}: {e}"
                    )
                    # Use default value if available, otherwise fail if required
                    if param.default != inspect.Parameter.empty:
                        kwargs[param_name] = param.default
                    else:
                        # Required parameter with no default - can't create instance
                        raise
            elif param.default != inspect.Parameter.empty:
                # Use default value if available
                kwargs[param_name] = param.default

        # Create instance with resolved dependencies
        return implementation(**kwargs)

    def _is_valid_implementation(
        self, service_type: Type, implementation: Type
    ) -> bool:
        """Check if implementation properly implements the service type."""
        # If service_type is ABC, check if implementation has all abstract methods
        if hasattr(service_type, "__abstractmethods__"):
            abstract_methods = getattr(service_type, "__abstractmethods__", set())
            for method in abstract_methods:
                if not hasattr(implementation, method):
                    return False

        # Check if implementation is subclass (for classes)
        try:
            if issubclass(implementation, service_type):
                return True
        except TypeError:
            # Not classes, can't check subclass relationship
            pass

        return True  # Assume valid if we can't determine otherwise

    def _is_assignable(self, from_type: Type, to_type: Type) -> bool:
        """Check if from_type can be assigned to to_type."""
        try:
            return issubclass(from_type, to_type)
        except TypeError:
            return from_type == to_type

    def get_registration_info(self) -> Dict[str, Any]:
        """
        Get information about all registered services.

        Returns:
            Dictionary with registration information
        """
        info = {}

        with self._lock:
            for service_type, descriptor in self._services.items():
                type_name = service_type.__name__

                info[type_name] = {
                    "lifetime": descriptor.lifetime.value,
                    "has_instance": descriptor.instance is not None,
                    "has_factory": descriptor.factory is not None,
                    "implementation": (
                        descriptor.implementation.__name__
                        if descriptor.implementation
                        else None
                    ),
                }

        return info


# Global container instance (optional, for convenience)
_global_container: Optional[ServiceContainer] = None
_global_lock = threading.Lock()


def get_global_container() -> ServiceContainer:
    """
    Get or create the global service container.

    Returns:
        The global service container instance

    Example:
        container = get_global_container()
        container.register(IMyService, MyService)
    """
    global _global_container

    if _global_container is None:
        with _global_lock:
            if _global_container is None:
                _global_container = ServiceContainer()

    return _global_container
