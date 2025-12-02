"""
Comprehensive tests for Service Container with Dependency Injection
===================================================================

WHY: These tests ensure the service container properly handles all aspects of
dependency injection including registration, resolution, lifetime management,
circular dependency detection, and thread safety.
"""

import threading
import time
from abc import ABC, abstractmethod
from typing import List, Optional

import pytest

from claude_mpm.services.core.service_container import (
    CircularDependencyError, ServiceContainer, ServiceLifetime,
    ServiceNotFoundError, get_global_container)


# Test interfaces and implementations
class ITestService(ABC):
    """Test service interface."""

    @abstractmethod
    def get_value(self) -> str:
        """Get a test value."""


class TestService(ITestService):
    """Test service implementation."""

    def __init__(self):
        self.created_at = time.time()
        self.id = id(self)

    def get_value(self) -> str:
        return "test_value"


class IDependentService(ABC):
    """Service that depends on ITestService."""

    @abstractmethod
    def process(self) -> str:
        """Process something."""


class DependentService(IDependentService):
    """Implementation with dependency."""

    def __init__(self, test_service: ITestService):
        self.test_service = test_service

    def process(self) -> str:
        return f"processed_{self.test_service.get_value()}"


class OptionalDependencyService:
    """Service with optional dependency."""

    def __init__(self, test_service: Optional[ITestService] = None):
        self.test_service = test_service

    def has_dependency(self) -> bool:
        return self.test_service is not None


class MultiDependencyService:
    """Service with multiple dependencies."""

    def __init__(
        self, test_service: ITestService, dependent_service: IDependentService
    ):
        self.test_service = test_service
        self.dependent_service = dependent_service

    def get_all_values(self) -> List[str]:
        return [self.test_service.get_value(), self.dependent_service.process()]


# Circular dependency test classes
class ICircularA(ABC):
    @abstractmethod
    def get_a(self) -> str:
        pass


class ICircularB(ABC):
    @abstractmethod
    def get_b(self) -> str:
        pass


class CircularA(ICircularA):
    def __init__(self, b_service: ICircularB):
        self.b_service = b_service

    def get_a(self) -> str:
        return "a"


class CircularB(ICircularB):
    def __init__(self, a_service: ICircularA):
        self.a_service = a_service

    def get_b(self) -> str:
        return "b"


class TestServiceContainer:
    """Test suite for ServiceContainer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.container = ServiceContainer()

    def test_register_and_resolve_simple(self):
        """Test basic service registration and resolution."""
        # Register service
        self.container.register(ITestService, TestService)

        # Resolve service
        service = self.container.resolve(ITestService)

        # Verify
        assert isinstance(service, TestService)
        assert service.get_value() == "test_value"

    def test_singleton_lifetime(self):
        """Test singleton lifetime management."""
        # Register as singleton
        self.container.register(ITestService, TestService, ServiceLifetime.SINGLETON)

        # Resolve multiple times
        service1 = self.container.resolve(ITestService)
        service2 = self.container.resolve(ITestService)
        service3 = self.container.resolve(ITestService)

        # All should be the same instance
        assert service1 is service2
        assert service2 is service3
        assert service1.id == service2.id == service3.id

    def test_transient_lifetime(self):
        """Test transient lifetime management."""
        # Register as transient
        self.container.register(ITestService, TestService, ServiceLifetime.TRANSIENT)

        # Resolve multiple times
        service1 = self.container.resolve(ITestService)
        service2 = self.container.resolve(ITestService)
        service3 = self.container.resolve(ITestService)

        # All should be different instances
        assert service1 is not service2
        assert service2 is not service3
        assert service1.id != service2.id != service3.id

    def test_backward_compatibility_singleton_bool(self):
        """Test backward compatibility with boolean singleton parameter."""
        # Register with singleton=True (old style)
        self.container.register(ITestService, TestService, True)

        # Should behave as singleton
        service1 = self.container.resolve(ITestService)
        service2 = self.container.resolve(ITestService)
        assert service1 is service2

    def test_backward_compatibility_transient_bool(self):
        """Test backward compatibility with boolean singleton=False."""
        # Register with singleton=False (old style)
        self.container.register(ITestService, TestService, False)

        # Should behave as transient
        service1 = self.container.resolve(ITestService)
        service2 = self.container.resolve(ITestService)
        assert service1 is not service2

    def test_register_instance(self):
        """Test registering a pre-created instance."""
        # Create instance
        instance = TestService()

        # Register instance
        self.container.register_instance(ITestService, instance)

        # Resolve should return the same instance
        resolved = self.container.resolve(ITestService)
        assert resolved is instance
        assert resolved.id == instance.id

    def test_register_factory(self):
        """Test registering a factory function."""
        # Track factory calls
        call_count = 0

        def create_service():
            nonlocal call_count
            call_count += 1
            return TestService()

        # Register factory as transient
        self.container.register_factory(
            ITestService, create_service, ServiceLifetime.TRANSIENT
        )

        # Each resolution should call factory
        service1 = self.container.resolve(ITestService)
        service2 = self.container.resolve(ITestService)

        assert call_count == 2
        assert service1 is not service2

    def test_factory_singleton(self):
        """Test factory with singleton lifetime."""
        call_count = 0

        def create_service():
            nonlocal call_count
            call_count += 1
            return TestService()

        # Register factory as singleton
        self.container.register_factory(
            ITestService, create_service, ServiceLifetime.SINGLETON
        )

        # Multiple resolutions should only call factory once
        service1 = self.container.resolve(ITestService)
        service2 = self.container.resolve(ITestService)
        service3 = self.container.resolve(ITestService)

        assert call_count == 1
        assert service1 is service2 is service3

    def test_automatic_dependency_injection(self):
        """Test automatic dependency resolution."""
        # Register dependencies
        self.container.register(ITestService, TestService)
        self.container.register(IDependentService, DependentService)

        # Resolve dependent service
        service = self.container.resolve(IDependentService)

        # Verify dependency was injected
        assert isinstance(service, DependentService)
        assert isinstance(service.test_service, TestService)
        assert service.process() == "processed_test_value"

    def test_optional_dependency(self):
        """Test optional dependency handling."""
        # Register service with optional dependency as TRANSIENT (dependency not registered)
        # Must be transient to get new instance when dependency is added
        self.container.register(
            OptionalDependencyService,
            OptionalDependencyService,
            ServiceLifetime.TRANSIENT,
        )

        # Should resolve without the dependency
        service = self.container.resolve(OptionalDependencyService)
        assert not service.has_dependency()

        # Now register the dependency
        self.container.register(ITestService, TestService)

        # New resolution should have the dependency (since it's transient)
        service2 = self.container.resolve(OptionalDependencyService)
        assert service2.has_dependency()

    def test_multiple_dependencies(self):
        """Test resolution with multiple dependencies."""
        # Register all dependencies
        self.container.register(ITestService, TestService)
        self.container.register(IDependentService, DependentService)
        self.container.register(MultiDependencyService, MultiDependencyService)

        # Resolve service with multiple dependencies
        service = self.container.resolve(MultiDependencyService)

        # Verify all dependencies were injected
        assert isinstance(service.test_service, TestService)
        assert isinstance(service.dependent_service, DependentService)
        values = service.get_all_values()
        assert "test_value" in values
        assert "processed_test_value" in values

    def test_circular_dependency_detection(self):
        """Test circular dependency detection."""
        # Register circular dependencies
        self.container.register(ICircularA, CircularA)
        self.container.register(ICircularB, CircularB)

        # Should raise CircularDependencyError
        with pytest.raises(CircularDependencyError) as exc_info:
            self.container.resolve(ICircularA)

        # Check error message contains the cycle
        assert "Circular dependency detected" in str(exc_info.value)

    def test_service_not_found_error(self):
        """Test error when service is not registered."""
        with pytest.raises(ServiceNotFoundError) as exc_info:
            self.container.resolve(ITestService)

        assert "Service not registered" in str(exc_info.value)
        assert "ITestService" in str(exc_info.value)

    def test_is_registered(self):
        """Test checking if service is registered."""
        # Initially not registered
        assert not self.container.is_registered(ITestService)

        # Register service
        self.container.register(ITestService, TestService)

        # Now should be registered
        assert self.container.is_registered(ITestService)

    def test_resolve_all(self):
        """Test resolving all implementations of a type."""

        # Create multiple service interfaces that could match
        class IBaseService(ABC):
            @abstractmethod
            def get_name(self) -> str:
                pass

        class ServiceA(IBaseService):
            def get_name(self) -> str:
                return "A"

        class ServiceB(IBaseService):
            def get_name(self) -> str:
                return "B"

        # Register multiple implementations
        self.container.register(IBaseService, ServiceA, ServiceLifetime.TRANSIENT)
        # Note: resolve_all would need enhancement to handle multiple registrations
        # This is a limitation test

        services = self.container.resolve_all(IBaseService)
        assert len(services) >= 1

    def test_clear_container(self):
        """Test clearing the container."""
        # Register some services
        self.container.register(ITestService, TestService)
        self.container.register(IDependentService, DependentService)

        # Verify they're registered
        assert self.container.is_registered(ITestService)
        assert self.container.is_registered(IDependentService)

        # Clear container
        self.container.clear()

        # Should no longer be registered
        assert not self.container.is_registered(ITestService)
        assert not self.container.is_registered(IDependentService)

        # Container itself should still be registered
        assert self.container.is_registered(ServiceContainer)

    def test_thread_safety_singleton(self):
        """Test thread-safe singleton creation."""
        self.container.register(ITestService, TestService, ServiceLifetime.SINGLETON)

        instances = []
        barrier = threading.Barrier(10)

        def resolve_service():
            barrier.wait()  # Synchronize thread start
            instance = self.container.resolve(ITestService)
            instances.append(instance)

        # Start multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=resolve_service)
            thread.start()
            threads.append(thread)

        # Wait for all threads
        for thread in threads:
            thread.join()

        # All instances should be the same
        first_instance = instances[0]
        for instance in instances:
            assert instance is first_instance

    def test_thread_safety_transient(self):
        """Test thread-safe transient creation."""
        self.container.register(ITestService, TestService, ServiceLifetime.TRANSIENT)

        instances = []
        barrier = threading.Barrier(10)

        def resolve_service():
            barrier.wait()  # Synchronize thread start
            instance = self.container.resolve(ITestService)
            instances.append(instance)

        # Start multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=resolve_service)
            thread.start()
            threads.append(thread)

        # Wait for all threads
        for thread in threads:
            thread.join()

        # All instances should be different
        instance_ids = [inst.id for inst in instances]
        assert len(set(instance_ids)) == 10  # All unique

    def test_get_registration_info(self):
        """Test getting registration information."""
        # Register various services
        self.container.register(ITestService, TestService, ServiceLifetime.SINGLETON)
        self.container.register_instance(
            IDependentService, DependentService(TestService())
        )

        # Get registration info
        info = self.container.get_registration_info()

        # Verify info structure
        assert "ITestService" in info
        assert info["ITestService"]["lifetime"] == "singleton"
        assert info["ITestService"]["implementation"] == "TestService"

        assert "IDependentService" in info
        assert info["IDependentService"]["has_instance"] is True

    def test_container_self_registration(self):
        """Test that container registers itself."""
        # Container should be able to resolve itself
        resolved = self.container.resolve(ServiceContainer)
        assert resolved is self.container

    def test_invalid_descriptor(self):
        """Test that invalid descriptors raise errors."""
        from claude_mpm.services.core.service_container import \
            ServiceDescriptor

        # Should raise ValueError without implementation, instance, or factory
        with pytest.raises(ValueError) as exc_info:
            ServiceDescriptor(service_type=ITestService)

        assert "must have either implementation" in str(exc_info.value)

    def test_complex_dependency_graph(self):
        """Test resolution of complex dependency graph."""

        # Create a more complex dependency structure
        class IServiceA(ABC):
            pass

        class IServiceB(ABC):
            pass

        class IServiceC(ABC):
            pass

        class ServiceA(IServiceA):
            def __init__(self):
                self.name = "A"

        class ServiceB(IServiceB):
            def __init__(self, service_a: IServiceA):
                self.service_a = service_a
                self.name = "B"

        class ServiceC(IServiceC):
            def __init__(self, service_a: IServiceA, service_b: IServiceB):
                self.service_a = service_a
                self.service_b = service_b
                self.name = "C"

        # Register all services
        self.container.register(IServiceA, ServiceA)
        self.container.register(IServiceB, ServiceB)
        self.container.register(IServiceC, ServiceC)

        # Resolve the most dependent service
        service_c = self.container.resolve(IServiceC)

        # Verify the entire graph was resolved
        assert service_c.name == "C"
        assert service_c.service_a.name == "A"
        assert service_c.service_b.name == "B"
        assert service_c.service_b.service_a.name == "A"

        # With singleton lifetime, shared dependencies should be the same instance
        assert service_c.service_a is service_c.service_b.service_a


class TestGlobalContainer:
    """Test global container functionality."""

    def test_get_global_container(self):
        """Test getting the global container."""
        container1 = get_global_container()
        container2 = get_global_container()

        # Should be the same instance
        assert container1 is container2

    def test_global_container_thread_safety(self):
        """Test thread-safe global container creation."""
        containers = []
        barrier = threading.Barrier(10)

        def get_container():
            barrier.wait()
            container = get_global_container()
            containers.append(container)

        # Start multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=get_container)
            thread.start()
            threads.append(thread)

        # Wait for all threads
        for thread in threads:
            thread.join()

        # All should be the same instance
        first_container = containers[0]
        for container in containers:
            assert container is first_container
