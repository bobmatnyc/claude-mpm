"""
Lightweight Dependency Injection Container for Claude MPM.

This module provides a simple yet powerful dependency injection container
that supports:
- Service registration with interfaces
- Constructor injection
- Singleton and transient lifetimes
- Factory functions
- Lazy initialization
- Circular dependency detection
"""

import inspect
import threading
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Type, TypeVar, Union

from claude_mpm.services.core.interfaces import IServiceContainer

from .logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class ServiceLifetime(Enum):
    """Service lifetime options."""

    SINGLETON = "singleton"  # One instance per container
    TRANSIENT = "transient"  # New instance per request
    SCOPED = "scoped"  # One instance per scope


class ServiceRegistration:
    """Represents a service registration in the container."""

    def __init__(
        self,
        service_type: Type,
        implementation: Optional[Union[Type, Callable]] = None,
        factory: Optional[Callable] = None,
        instance: Optional[Any] = None,
        lifetime: ServiceLifetime = ServiceLifetime.SINGLETON,
        dependencies: Optional[Dict[str, Type]] = None,
    ):
        """
        Initialize service registration.

        Args:
            service_type: The interface/base type being registered
            implementation: The concrete implementation class
            factory: Factory function to create instances
            instance: Pre-created instance (for singleton registration)
            lifetime: Service lifetime management
            dependencies: Explicit dependency mapping
        """
        self.service_type = service_type
        self.implementation = implementation or service_type
        self.factory = factory
        self.instance = instance
        self.lifetime = lifetime
        self.dependencies = dependencies or {}
        self._lock = threading.Lock()

    def create_instance(self, container: "DIContainer") -> Any:
        """Create an instance of the service."""
        if self.instance is not None:
            return self.instance

        if self.factory:
            return self.factory(container)

        # Get constructor parameters
        if inspect.isclass(self.implementation):
            return container.create_instance(self.implementation, self.dependencies)
        # It's already an instance or callable
        return self.implementation


class CircularDependencyError(Exception):
    """Raised when circular dependencies are detected."""


class ServiceNotFoundError(Exception):
    """Raised when a requested service is not registered."""


class ServiceScope:
    """
    Represents a service scope for scoped lifetime services.

    Scoped services live for the duration of the scope and are shared
    within that scope.
    """

    def __init__(self, container: "DIContainer"):
        """Initialize service scope."""
        self._container = container
        self._scoped_instances: Dict[Type, Any] = {}
        self._disposed = False
        self._lock = threading.Lock()

    def get_scoped_instance(self, service_type: Type) -> Optional[Any]:
        """Get scoped instance if exists."""
        with self._lock:
            return self._scoped_instances.get(service_type)

    def set_scoped_instance(self, service_type: Type, instance: Any) -> None:
        """Store scoped instance."""
        with self._lock:
            if not self._disposed:
                self._scoped_instances[service_type] = instance

    def dispose(self) -> None:
        """
        Dispose of the scope and all scoped instances.

        Calls dispose() on instances that implement IDisposable.
        """
        with self._lock:
            if self._disposed:
                return

            for service_type, instance in self._scoped_instances.items():
                # Call dispose if available
                if hasattr(instance, "dispose"):
                    try:
                        instance.dispose()
                    except Exception as e:
                        logger.error(
                            f"Error disposing scoped service {service_type}: {e}"
                        )

            self._scoped_instances.clear()
            self._disposed = True

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - dispose scope."""
        self.dispose()


class DIContainer(IServiceContainer):
    """
    Enhanced Dependency Injection Container.

    Implements IServiceContainer interface to provide a complete
    dependency injection solution.

    Provides:
    - Service registration with multiple lifetime options
    - Automatic constructor injection
    - Interface to implementation mapping
    - Circular dependency detection
    - Lazy loading support
    - Scoped service support
    - Service disposal lifecycle
    - Named registrations
    - Configuration injection
    """

    def __init__(self):
        """Initialize the DI container."""
        self._registrations: Dict[Type, ServiceRegistration] = {}
        self._named_registrations: Dict[str, ServiceRegistration] = {}
        self._factories: Dict[Type, Callable] = {}
        self._singletons: Dict[Type, Any] = {}
        self._scopes: List[ServiceScope] = []
        self._initialization_order: List[Type] = []
        self._disposal_handlers: Dict[Type, Callable] = {}
        self._lock = threading.RLock()
        self._resolving: Set[Type] = set()
        self._current_scope: Optional[ServiceScope] = None

    def register(
        self, service_type: type, implementation: type, singleton: bool = True
    ) -> None:
        """
        Register a service implementation (IServiceContainer interface method).

        Args:
            service_type: The interface/base type to register
            implementation: The concrete implementation class
            singleton: Whether to use singleton lifetime (default True)

        Examples:
            # Register interface with implementation
            container.register(ILogger, ConsoleLogger)

            # Register as transient (new instance each time)
            container.register(IService, ServiceImpl, singleton=False)
        """
        lifetime = ServiceLifetime.SINGLETON if singleton else ServiceLifetime.TRANSIENT
        self._register_internal(
            service_type=service_type, implementation=implementation, lifetime=lifetime
        )

    def _register_internal(
        self,
        service_type: Type[T],
        implementation: Optional[Union[Type[T], Callable[..., T]]] = None,
        lifetime: ServiceLifetime = ServiceLifetime.SINGLETON,
        factory: Optional[Callable[["DIContainer"], T]] = None,
        instance: Optional[T] = None,
        dependencies: Optional[Dict[str, Type]] = None,
    ) -> None:
        """
        Internal registration method with full flexibility.

        Args:
            service_type: The interface/base type to register
            implementation: The concrete implementation (class or factory)
            lifetime: Service lifetime (singleton/transient)
            factory: Optional factory function
            instance: Pre-created instance (for singleton)
            dependencies: Explicit dependency mapping for constructor params
        """
        with self._lock:
            registration = ServiceRegistration(
                service_type=service_type,
                implementation=implementation,
                factory=factory,
                instance=instance,
                lifetime=lifetime,
                dependencies=dependencies,
            )
            self._registrations[service_type] = registration

            # If instance provided, store as singleton
            if instance is not None:
                self._singletons[service_type] = instance

    def register_instance(self, service_type: type, instance: Any) -> None:
        """
        Register a service instance (IServiceContainer interface method).

        Args:
            service_type: The interface/base type to register
            instance: Pre-created instance to register as singleton

        Examples:
            # Register a pre-created instance using ConfigLoader
            config_loader = ConfigLoader()
            config = config_loader.load_main_config()
            container.register_instance(IConfig, config)
        """
        self._register_internal(
            service_type=service_type,
            instance=instance,
            lifetime=ServiceLifetime.SINGLETON,
        )

    def resolve_all(self, service_type: type) -> List[Any]:
        """
        Resolve all implementations of a service type (IServiceContainer interface method).

        Args:
            service_type: The type to resolve

        Returns:
            List of all registered implementations for the service type

        Examples:
            # Register multiple implementations
            container.register(IPlugin, PluginA)
            container.register(IPlugin, PluginB)

            # Get all implementations
            plugins = container.resolve_all(IPlugin)
        """
        with self._lock:
            # For now, return a list with the single registered implementation
            # In the future, we could support multiple registrations for the same type
            if service_type in self._registrations:
                return [self._resolve_internal(service_type)]
            return []

    def register_singleton(
        self,
        interface: Type[T],
        implementation: Optional[Union[Type[T], T]] = None,
        instance: Optional[T] = None,
        name: Optional[str] = None,
        dispose_handler: Optional[Callable[[T], None]] = None,
    ) -> None:
        """
        Register a singleton service.

        Args:
            interface: The interface/base type to register
            implementation: The concrete implementation class
            instance: Pre-created instance (alternative to implementation)
            name: Optional name for named registration
            dispose_handler: Optional handler called when disposing service

        Examples:
            # Register with implementation class
            container.register_singleton(ILogger, ConsoleLogger)

            # Register with instance using ConfigLoader
            config_loader = ConfigLoader()
            container.register_singleton(IConfig, instance=config_loader.load_main_config())

            # Register with disposal handler
            container.register_singleton(
                IDatabase,
                DatabaseConnection,
                dispose_handler=lambda db: db.close()
            )
        """
        # For named registrations, create a unique registration
        if name:
            # Create named registration directly
            registration = ServiceRegistration(
                service_type=interface,
                implementation=implementation,
                instance=instance,
                lifetime=ServiceLifetime.SINGLETON,
            )
            self._named_registrations[name] = registration

            # Also store the instance if provided
            if instance is not None:
                # Store with a composite key for retrieval
                named_key = (interface, name)
                if not hasattr(self, "_named_singletons"):
                    self._named_singletons = {}
                self._named_singletons[named_key] = instance
        # Normal registration without name
        elif instance is not None:
            self._register_internal(interface, instance=instance)
        elif implementation is not None and not inspect.isclass(implementation):
            # It's an instance passed as implementation (backward compatibility)
            self._register_internal(interface, instance=implementation)
        else:
            self._register_internal(
                interface, implementation, lifetime=ServiceLifetime.SINGLETON
            )

        # Handle disposal handler
        if dispose_handler:
            if name:
                # Store with composite key for named services
                if not hasattr(self, "_named_disposal_handlers"):
                    self._named_disposal_handlers = {}
                self._named_disposal_handlers[(interface, name)] = dispose_handler
            else:
                self._disposal_handlers[interface] = dispose_handler

        # Track initialization order for proper disposal
        key = (interface, name) if name else interface
        if key not in self._initialization_order:
            self._initialization_order.append(key)

    def register_scoped(
        self,
        interface: Type[T],
        implementation: Optional[Type[T]] = None,
        name: Optional[str] = None,
    ) -> None:
        """
        Register a scoped service.

        Scoped services are created once per scope and shared within that scope.

        Args:
            interface: The interface/base type to register
            implementation: The concrete implementation
            name: Optional name for named registration

        Examples:
            # Register scoped service
            container.register_scoped(IRequestContext, RequestContext)

            # Use in scope
            with container.create_scope() as scope:
                context = container.get(IRequestContext)  # Created
                context2 = container.get(IRequestContext)  # Same instance
        """
        self._register_internal(
            interface, implementation, lifetime=ServiceLifetime.SCOPED
        )
        if name:
            self._named_registrations[name] = self._registrations[interface]

    def register_transient(
        self, service_type: Type[T], implementation: Optional[Type[T]] = None
    ) -> None:
        """
        Register a transient service.

        Convenience method for registering transient services.
        """
        self._register_internal(
            service_type, implementation, lifetime=ServiceLifetime.TRANSIENT
        )

    def register_factory(
        self,
        interface: Type[T],
        factory: Callable[["DIContainer"], T],
        lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT,
        name: Optional[str] = None,
    ) -> None:
        """
        Register a service with a factory function.

        The factory receives the container as parameter for resolving dependencies.

        Args:
            interface: The interface/base type to register
            factory: Factory function that creates instances
            lifetime: Service lifetime (default: TRANSIENT for factories)
            name: Optional name for named registration

        Examples:
            # Register with factory
            container.register_factory(
                IService,
                lambda c: Service(c.get(ILogger), c.get(IConfig)),
                lifetime=ServiceLifetime.SINGLETON
            )
        """
        self._register_internal(interface, factory=factory, lifetime=lifetime)
        self._factories[interface] = factory
        if name:
            self._named_registrations[name] = self._registrations[interface]

    def get(self, interface: Type[T], name: Optional[str] = None) -> T:
        """
        Get service instance with dependency resolution.

        This is the primary method for retrieving services from the container.
        It handles all lifetime management and dependency resolution.

        Args:
            interface: The type to resolve
            name: Optional name for named registration lookup

        Returns:
            Instance of the requested service

        Raises:
            ServiceNotFoundError: If service is not registered
            CircularDependencyError: If circular dependencies detected

        Examples:
            # Get by interface
            logger = container.get(ILogger)

            # Get named service
            primary_db = container.get(IDatabase, name="primary")
        """
        if name:
            if name not in self._named_registrations:
                suggestions = self._get_similar_names(name)
                raise ServiceNotFoundError(
                    f"Named service '{name}' is not registered. "
                    f"Did you mean: {', '.join(suggestions)}?"
                    if suggestions
                    else ""
                )

            # Check if we have a pre-stored instance for this named service
            named_key = (interface, name)
            if (
                hasattr(self, "_named_singletons")
                and named_key in self._named_singletons
            ):
                return self._named_singletons[named_key]

            # Otherwise resolve from named registration
            registration = self._named_registrations[name]
            if registration.instance is not None:
                return registration.instance
            if registration.factory:
                return registration.factory(self)
            return self.create_instance(
                registration.implementation, registration.dependencies
            )

        return self._resolve_internal(interface)

    def resolve(self, service_type: Type[T]) -> T:
        """
        Resolve a service from the container (legacy method).

        This method is maintained for backward compatibility.
        New code should use get() instead.

        Args:
            service_type: The type to resolve

        Returns:
            Instance of the requested service

        Raises:
            ServiceNotFoundError: If service is not registered
            CircularDependencyError: If circular dependencies detected
        """
        return self.get(service_type)

    def _resolve_internal(self, service_type: Type[T]) -> T:
        """
        Internal method to resolve a service.

        Handles the actual resolution logic with proper locking and lifecycle management.
        """
        with self._lock:
            # Check for circular dependencies
            if service_type in self._resolving:
                cycle = (
                    " -> ".join(str(t.__name__) for t in self._resolving)
                    + f" -> {service_type.__name__}"
                )
                raise CircularDependencyError(f"Circular dependency detected: {cycle}")

            # Check if registered
            if service_type not in self._registrations:
                suggestions = self._get_similar_types(service_type)
                error_msg = f"Service {service_type.__name__} is not registered."
                if suggestions:
                    error_msg += f" Did you mean: {', '.join(suggestions)}?"
                raise ServiceNotFoundError(error_msg)

            registration = self._registrations[service_type]

            # Handle different lifetimes
            if registration.lifetime == ServiceLifetime.SINGLETON:
                # Return existing singleton if available
                if service_type in self._singletons:
                    return self._singletons[service_type]

            elif registration.lifetime == ServiceLifetime.SCOPED:
                # Check current scope
                if (
                    self._current_scope
                    and (
                        instance := self._current_scope.get_scoped_instance(
                            service_type
                        )
                    )
                    is not None
                ):
                    return instance

            # Mark as resolving
            self._resolving.add(service_type)

            try:
                # Create instance
                instance = registration.create_instance(self)

                # Store based on lifetime
                if registration.lifetime == ServiceLifetime.SINGLETON:
                    self._singletons[service_type] = instance
                    if service_type not in self._initialization_order:
                        self._initialization_order.append(service_type)

                elif registration.lifetime == ServiceLifetime.SCOPED:
                    if self._current_scope:
                        self._current_scope.set_scoped_instance(service_type, instance)

                # Call initialization hook if available
                if hasattr(instance, "initialize"):
                    try:
                        instance.initialize()
                    except Exception as e:
                        logger.error(
                            f"Failed to initialize service {service_type.__name__}: {e}"
                        )
                        raise

                return instance

            finally:
                self._resolving.remove(service_type)

    def resolve_optional(
        self, service_type: Type[T], default: Optional[T] = None
    ) -> Optional[T]:
        """
        Resolve a service if registered, otherwise return default.

        Useful for optional dependencies.
        """
        try:
            return self.resolve(service_type)
        except ServiceNotFoundError:
            return default

    def create_instance(
        self, cls: Type[T], explicit_deps: Optional[Dict[str, Type]] = None
    ) -> T:
        """
        Create an instance of a class, resolving constructor dependencies.

        Args:
            cls: The class to instantiate
            explicit_deps: Explicit dependency mapping for constructor params

        Returns:
            New instance with resolved dependencies
        """
        # Get constructor signature
        sig = inspect.signature(cls.__init__)
        kwargs = {}

        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue

            # Check explicit dependencies first
            if explicit_deps and param_name in explicit_deps:
                dep_type = explicit_deps[param_name]
                kwargs[param_name] = self.resolve(dep_type)
                continue

            # Try to resolve by type annotation
            if param.annotation != param.empty:
                param_type = param.annotation

                # Handle string annotations (forward references)
                if isinstance(param_type, str):
                    # Try to resolve forward reference
                    try:
                        # Get the module where the class is defined
                        import sys

                        frame = sys._getframe(1)
                        module = frame.f_globals
                        if param_type in module:
                            param_type = module[param_type]
                        else:
                            # Try looking in registrations by name
                            for reg_type in self._registrations:
                                if reg_type.__name__ == param_type:
                                    param_type = reg_type
                                    break
                    except Exception:
                        # If we can't resolve, skip this parameter
                        if param.default != param.empty:
                            kwargs[param_name] = param.default
                        continue

                # Handle Optional types
                if hasattr(param_type, "__origin__") and param_type.__origin__ is Union:
                    # Get the non-None type from Optional
                    args = param_type.__args__
                    param_type = next(
                        (arg for arg in args if arg is not type(None)), None
                    )

                if param_type and param_type in self._registrations:
                    # Check for circular dependency
                    if param_type in self._resolving:
                        # Circular dependency detected
                        cycle = (
                            " -> ".join(str(t.__name__) for t in self._resolving)
                            + f" -> {param_type.__name__}"
                        )
                        raise CircularDependencyError(
                            f"Circular dependency detected: {cycle}"
                        )
                    kwargs[param_name] = self.resolve(param_type)
                elif param.default != param.empty:
                    # Use default value
                    kwargs[param_name] = param.default

        return cls(**kwargs)

    def is_registered(self, service_type: Type) -> bool:
        """Check if a service type is registered."""
        return service_type in self._registrations

    def get_all_registrations(self) -> Dict[Type, ServiceRegistration]:
        """Get all service registrations."""
        with self._lock:
            return self._registrations.copy()

    def create_scope(self) -> ServiceScope:
        """
        Create a new service scope.

        Scoped services will be created once per scope and shared within that scope.

        Returns:
            New ServiceScope instance

        Examples:
            # Use scope with context manager
            with container.create_scope() as scope:
                # Services with SCOPED lifetime are shared within this scope
                service1 = container.get(IScopedService)
                service2 = container.get(IScopedService)
                assert service1 is service2  # Same instance

            # Scope is disposed, scoped instances are cleaned up
        """
        scope = ServiceScope(self)
        with self._lock:
            self._scopes.append(scope)
            # Set as current scope for resolution
            old_scope = self._current_scope
            self._current_scope = scope

        # Return a context manager that restores old scope
        class ScopeContext:
            def __init__(self, container, new_scope, old_scope):
                self.container = container
                self.new_scope = new_scope
                self.old_scope = old_scope

            def __enter__(self):
                return self.new_scope

            def __exit__(self, exc_type, exc_val, exc_tb):
                with self.container._lock:
                    self.container._current_scope = self.old_scope
                    if self.new_scope in self.container._scopes:
                        self.container._scopes.remove(self.new_scope)
                self.new_scope.dispose()

        return ScopeContext(self, scope, old_scope)

    def create_child_container(self) -> "DIContainer":
        """
        Create a child container that inherits registrations.

        Useful for isolated scenarios where you want separate singleton instances.
        """
        child = DIContainer()
        with self._lock:
            # Copy registrations but not singleton instances
            for service_type, registration in self._registrations.items():
                child._registrations[service_type] = registration
            # Copy named registrations
            child._named_registrations = self._named_registrations.copy()
            # Copy factories
            child._factories = self._factories.copy()
            # Copy disposal handlers
            child._disposal_handlers = self._disposal_handlers.copy()
        return child

    def dispose(self) -> None:
        """
        Dispose of the container and all managed services.

        Calls disposal handlers for singleton services in reverse initialization order.
        Also disposes any active scopes.
        """
        with self._lock:
            # Dispose scopes first
            for scope in reversed(self._scopes):
                scope.dispose()
            self._scopes.clear()

            # Dispose singletons in reverse initialization order
            for service_type in reversed(self._initialization_order):
                if service_type in self._singletons:
                    instance = self._singletons[service_type]

                    # Call disposal handler if registered
                    if service_type in self._disposal_handlers:
                        try:
                            self._disposal_handlers[service_type](instance)
                        except Exception as e:
                            logger.error(
                                f"Error in disposal handler for {service_type.__name__}: {e}"
                            )

                    # Call dispose method if available
                    elif hasattr(instance, "dispose"):
                        try:
                            instance.dispose()
                        except Exception as e:
                            logger.error(
                                f"Error disposing service {service_type.__name__}: {e}"
                            )

            # Clear everything
            self._singletons.clear()
            self._initialization_order.clear()
            self._current_scope = None

    def clear(self) -> None:
        """Clear all registrations and instances."""
        self.dispose()
        with self._lock:
            self._registrations.clear()
            self._named_registrations.clear()
            self._factories.clear()
            self._disposal_handlers.clear()
            self._resolving.clear()

    def _get_similar_types(self, service_type: Type) -> List[str]:
        """
        Get similar registered type names for better error messages.

        Uses simple string similarity to suggest possible alternatives.
        """
        if not self._registrations:
            return []

        type_name = service_type.__name__.lower()
        similar = []

        for registered_type in self._registrations:
            registered_name = registered_type.__name__
            registered_lower = registered_name.lower()

            # Check for substring match
            if type_name in registered_lower or registered_lower in type_name:
                similar.append(registered_name)
                continue

            # Check for common prefix
            common_prefix_len = 0
            for i, (a, b) in enumerate(zip(type_name, registered_lower)):
                if a == b:
                    common_prefix_len = i + 1
                else:
                    break

            if common_prefix_len >= min(3, len(type_name) // 2):
                similar.append(registered_name)

        return similar[:3]  # Return top 3 suggestions

    def _get_similar_names(self, name: str) -> List[str]:
        """
        Get similar registered names for better error messages.
        """
        if not self._named_registrations:
            return []

        name_lower = name.lower()
        similar = []

        for registered_name in self._named_registrations:
            registered_lower = registered_name.lower()

            # Check for substring match
            if name_lower in registered_lower or registered_lower in name_lower:
                similar.append(registered_name)
                continue

            # Check for common prefix
            common_prefix_len = 0
            for i, (a, b) in enumerate(zip(name_lower, registered_lower)):
                if a == b:
                    common_prefix_len = i + 1
                else:
                    break

            if common_prefix_len >= min(3, len(name_lower) // 2):
                similar.append(registered_name)

        return similar[:3]  # Return top 3 suggestions


# Global container instance (optional, for convenience)
_global_container: Optional[DIContainer] = None
_global_lock = threading.Lock()


def get_container() -> DIContainer:
    """
    Get the global DI container instance.

    Creates one if it doesn't exist.
    """
    global _global_container
    with _global_lock:
        if _global_container is None:
            _global_container = DIContainer()
        return _global_container


def set_container(container: DIContainer) -> None:
    """Set the global DI container instance."""
    global _global_container
    with _global_lock:
        _global_container = container
