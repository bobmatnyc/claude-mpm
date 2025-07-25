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
from abc import ABC
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Type, TypeVar, Union

from .logger import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


class ServiceLifetime(Enum):
    """Service lifetime options."""
    SINGLETON = "singleton"  # One instance per container
    TRANSIENT = "transient"  # New instance per request
    SCOPED = "scoped"       # One instance per scope (future enhancement)


class ServiceRegistration:
    """Represents a service registration in the container."""
    
    def __init__(
        self,
        service_type: Type,
        implementation: Optional[Union[Type, Callable]] = None,
        factory: Optional[Callable] = None,
        instance: Optional[Any] = None,
        lifetime: ServiceLifetime = ServiceLifetime.SINGLETON,
        dependencies: Optional[Dict[str, Type]] = None
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
        
    def create_instance(self, container: 'DIContainer') -> Any:
        """Create an instance of the service."""
        if self.instance is not None:
            return self.instance
            
        if self.factory:
            return self.factory(container)
            
        # Get constructor parameters
        if inspect.isclass(self.implementation):
            return container.create_instance(self.implementation, self.dependencies)
        else:
            # It's already an instance or callable
            return self.implementation


class CircularDependencyError(Exception):
    """Raised when circular dependencies are detected."""
    pass


class ServiceNotFoundError(Exception):
    """Raised when a requested service is not registered."""
    pass


class DIContainer:
    """
    Lightweight Dependency Injection Container.
    
    Provides service registration, resolution, and lifecycle management.
    """
    
    def __init__(self):
        """Initialize the DI container."""
        self._registrations: Dict[Type, ServiceRegistration] = {}
        self._singletons: Dict[Type, Any] = {}
        self._lock = threading.RLock()
        self._resolving: Set[Type] = set()
        
    def register(
        self,
        service_type: Type[T],
        implementation: Optional[Union[Type[T], Callable[..., T]]] = None,
        lifetime: ServiceLifetime = ServiceLifetime.SINGLETON,
        factory: Optional[Callable[['DIContainer'], T]] = None,
        instance: Optional[T] = None,
        dependencies: Optional[Dict[str, Type]] = None
    ) -> None:
        """
        Register a service in the container.
        
        Args:
            service_type: The interface/base type to register
            implementation: The concrete implementation (class or factory)
            lifetime: Service lifetime (singleton/transient)
            factory: Optional factory function
            instance: Pre-created instance (for singleton)
            dependencies: Explicit dependency mapping for constructor params
            
        Examples:
            # Register interface with implementation
            container.register(ILogger, ConsoleLogger)
            
            # Register with factory
            container.register(IDatabase, factory=lambda c: Database(c.resolve(IConfig)))
            
            # Register singleton instance
            container.register(IConfig, instance=Config())
            
            # Register with explicit dependencies
            container.register(IService, ServiceImpl, dependencies={'logger': ILogger})
        """
        with self._lock:
            registration = ServiceRegistration(
                service_type=service_type,
                implementation=implementation,
                factory=factory,
                instance=instance,
                lifetime=lifetime,
                dependencies=dependencies
            )
            self._registrations[service_type] = registration
            
            # If instance provided, store as singleton
            if instance is not None:
                self._singletons[service_type] = instance
                
    def register_singleton(
        self,
        service_type: Type[T],
        implementation: Optional[Union[Type[T], T]] = None
    ) -> None:
        """
        Register a singleton service.
        
        Convenience method for registering singletons.
        """
        if implementation is not None and not inspect.isclass(implementation):
            # It's an instance
            self.register(service_type, instance=implementation)
        else:
            self.register(service_type, implementation, lifetime=ServiceLifetime.SINGLETON)
            
    def register_transient(
        self,
        service_type: Type[T],
        implementation: Optional[Type[T]] = None
    ) -> None:
        """
        Register a transient service.
        
        Convenience method for registering transient services.
        """
        self.register(service_type, implementation, lifetime=ServiceLifetime.TRANSIENT)
        
    def register_factory(
        self,
        service_type: Type[T],
        factory: Callable[['DIContainer'], T],
        lifetime: ServiceLifetime = ServiceLifetime.SINGLETON
    ) -> None:
        """
        Register a service with a factory function.
        
        The factory receives the container as parameter for resolving dependencies.
        """
        self.register(service_type, factory=factory, lifetime=lifetime)
        
    def resolve(self, service_type: Type[T]) -> T:
        """
        Resolve a service from the container.
        
        Args:
            service_type: The type to resolve
            
        Returns:
            Instance of the requested service
            
        Raises:
            ServiceNotFoundError: If service is not registered
            CircularDependencyError: If circular dependencies detected
        """
        with self._lock:
            # Check for circular dependencies
            if service_type in self._resolving:
                cycle = " -> ".join(str(t) for t in self._resolving) + f" -> {service_type}"
                raise CircularDependencyError(f"Circular dependency detected: {cycle}")
                
            # Check if registered
            if service_type not in self._registrations:
                raise ServiceNotFoundError(f"Service {service_type} is not registered")
                
            registration = self._registrations[service_type]
            
            # Return existing singleton if available
            if registration.lifetime == ServiceLifetime.SINGLETON:
                if service_type in self._singletons:
                    return self._singletons[service_type]
                    
            # Mark as resolving
            self._resolving.add(service_type)
            
            try:
                # Create instance
                instance = registration.create_instance(self)
                
                # Store singleton
                if registration.lifetime == ServiceLifetime.SINGLETON:
                    self._singletons[service_type] = instance
                    
                return instance
                
            finally:
                self._resolving.remove(service_type)
                
    def resolve_optional(self, service_type: Type[T], default: Optional[T] = None) -> Optional[T]:
        """
        Resolve a service if registered, otherwise return default.
        
        Useful for optional dependencies.
        """
        try:
            return self.resolve(service_type)
        except ServiceNotFoundError:
            return default
            
    def create_instance(self, cls: Type[T], explicit_deps: Optional[Dict[str, Type]] = None) -> T:
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
            if param_name == 'self':
                continue
                
            # Check explicit dependencies first
            if explicit_deps and param_name in explicit_deps:
                dep_type = explicit_deps[param_name]
                kwargs[param_name] = self.resolve(dep_type)
                continue
                
            # Try to resolve by type annotation
            if param.annotation != param.empty:
                param_type = param.annotation
                
                # Handle Optional types
                if hasattr(param_type, '__origin__') and param_type.__origin__ is Union:
                    # Get the non-None type from Optional
                    args = param_type.__args__
                    param_type = next((arg for arg in args if arg is not type(None)), None)
                    
                if param_type and param_type in self._registrations:
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
            
    def create_child_container(self) -> 'DIContainer':
        """
        Create a child container that inherits registrations.
        
        Useful for scoped scenarios.
        """
        child = DIContainer()
        with self._lock:
            # Copy registrations but not singleton instances
            for service_type, registration in self._registrations.items():
                child._registrations[service_type] = registration
        return child
        
    def clear(self) -> None:
        """Clear all registrations and instances."""
        with self._lock:
            self._registrations.clear()
            self._singletons.clear()
            self._resolving.clear()


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