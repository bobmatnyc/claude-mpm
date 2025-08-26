"""
Test file for enhanced dependency injection container.

This test demonstrates all the new features of the enhanced DIContainer:
- Service registration types (singleton, factory, scoped)
- Automatic constructor injection
- Circular dependency detection
- Service lifecycle management
- Named registrations
- Configuration injection
"""

import threading
from typing import List

import pytest

from claude_mpm.core.container import (
    CircularDependencyError,
    DIContainer,
    ServiceLifetime,
    ServiceNotFoundError,
)


# Test interfaces and implementations
class ILogger:
    """Logger interface."""

    def log(self, message: str) -> None:
        raise NotImplementedError


class IDatabase:
    """Database interface."""

    def connect(self) -> None:
        raise NotImplementedError

    def disconnect(self) -> None:
        raise NotImplementedError


class IRepository:
    """Repository interface."""

    def save(self, data: dict) -> None:
        raise NotImplementedError


class IService:
    """Service interface."""

    def process(self, data: str) -> str:
        raise NotImplementedError


class IScopedService:
    """Scoped service interface."""

    def get_id(self) -> str:
        raise NotImplementedError


class ConsoleLogger(ILogger):
    """Console logger implementation."""

    def __init__(self):
        self.messages: List[str] = []

    def log(self, message: str) -> None:
        self.messages.append(message)


class Database(IDatabase):
    """Database implementation."""

    def __init__(self, logger: ILogger):
        self.logger = logger
        self.connected = False
        self.disposed = False

    def connect(self) -> None:
        self.connected = True
        self.logger.log("Database connected")

    def disconnect(self) -> None:
        self.connected = False
        self.logger.log("Database disconnected")

    def dispose(self) -> None:
        """Called when container is disposed."""
        if self.connected:
            self.disconnect()
        self.disposed = True


class Repository(IRepository):
    """Repository implementation with dependencies."""

    def __init__(self, database: IDatabase, logger: ILogger):
        self.database = database
        self.logger = logger

    def save(self, data: dict) -> None:
        if not self.database.connected:
            self.database.connect()
        self.logger.log(f"Saving data: {data}")


class BusinessService(IService):
    """Business service with repository dependency."""

    def __init__(self, repository: IRepository):
        self.repository = repository

    def process(self, data: str) -> str:
        self.repository.save({"data": data})
        return f"Processed: {data}"


class ScopedService(IScopedService):
    """Service with scoped lifetime."""

    _counter = 0

    def __init__(self):
        ScopedService._counter += 1
        self.id = f"scoped_{ScopedService._counter}"

    def get_id(self) -> str:
        return self.id


# Circular dependency classes for testing
class ServiceA:
    def __init__(self, service_b: "ServiceB"):
        self.service_b = service_b


class ServiceB:
    def __init__(self, service_a: "ServiceA"):
        self.service_a = service_a


class TestDIContainer:
    """Test suite for enhanced DI container."""

    def test_singleton_registration():
        """Test singleton service registration and resolution."""
        container = DIContainer()

        # Register singleton
        container.register_singleton(ILogger, ConsoleLogger)

        # Resolve multiple times
        logger1 = container.get(ILogger)
        logger2 = container.get(ILogger)

        # Should be same instance
        assert logger1 is logger2
        assert isinstance(logger1, ConsoleLogger)

    def test_factory_registration():
        """Test factory function registration."""
        container = DIContainer()

        # Register with factory
        created_count = 0

        def create_logger(c: DIContainer) -> ILogger:
            nonlocal created_count
            created_count += 1
            return ConsoleLogger()

        container.register_factory(
            ILogger, create_logger, lifetime=ServiceLifetime.TRANSIENT
        )

        # Each resolution creates new instance
        logger1 = container.get(ILogger)
        logger2 = container.get(ILogger)

        assert logger1 is not logger2
        assert created_count == 2

    def test_scoped_registration():
        """Test scoped service lifetime."""
        container = DIContainer()

        # Register scoped service
        container.register_scoped(IScopedService, ScopedService)

        # Create first scope
        with container.create_scope():
            service1 = container.get(IScopedService)
            service2 = container.get(IScopedService)

            # Same instance within scope
            assert service1 is service2
            first_id = service1.get_id()

        # Create second scope
        with container.create_scope():
            service3 = container.get(IScopedService)
            service4 = container.get(IScopedService)

            # Same instance within scope
            assert service3 is service4
            # Different instance from first scope
            assert service3.get_id() != first_id

    def test_automatic_constructor_injection():
        """Test automatic dependency resolution in constructors."""
        container = DIContainer()

        # Register dependencies
        container.register_singleton(ILogger, ConsoleLogger)
        container.register_singleton(IDatabase, Database)
        container.register_singleton(IRepository, Repository)
        container.register_singleton(IService, BusinessService)

        # Resolve service with nested dependencies
        service = container.get(IService)

        assert isinstance(service, BusinessService)
        assert isinstance(service.repository, Repository)
        assert isinstance(service.repository.database, Database)
        assert isinstance(service.repository.logger, ConsoleLogger)

        # Test that dependencies are properly injected
        result = service.process("test data")
        assert result == "Processed: test data"

        # Verify logger received messages
        logger = container.get(ILogger)
        assert "Database connected" in logger.messages
        assert "Saving data: {'data': 'test data'}" in logger.messages

    def test_circular_dependency_detection():
        """Test that circular dependencies are detected."""
        container = DIContainer()

        # Register circular dependencies
        container.register_singleton(ServiceA, ServiceA)
        container.register_singleton(ServiceB, ServiceB)

        # Should raise CircularDependencyError
        with pytest.raises(CircularDependencyError) as exc_info:
            container.get(ServiceA)

        assert "Circular dependency detected" in str(exc_info.value)

    def test_service_not_found_with_suggestions():
        """Test service not found error with suggestions."""
        container = DIContainer()

        # Register some services
        container.register_singleton(ILogger, ConsoleLogger)
        container.register_singleton(IDatabase, Database)

        # Try to resolve unregistered service similar to registered ones
        with pytest.raises(ServiceNotFoundError) as exc_info:
            container.get(IRepository)

        error_msg = str(exc_info.value)
        assert "IRepository is not registered" in error_msg

    def test_named_registrations():
        """Test named service registrations."""
        container = DIContainer()

        # Register multiple implementations with names
        primary_logger = ConsoleLogger()
        secondary_logger = ConsoleLogger()

        container.register_singleton(ILogger, instance=primary_logger, name="primary")
        container.register_singleton(
            ILogger, instance=secondary_logger, name="secondary"
        )

        # Resolve by name
        logger1 = container.get(ILogger, name="primary")
        logger2 = container.get(ILogger, name="secondary")

        assert logger1 is primary_logger
        assert logger2 is secondary_logger
        assert logger1 is not logger2

    def test_disposal_lifecycle():
        """Test service disposal lifecycle."""
        container = DIContainer()

        # Register services with disposal needs
        container.register_singleton(ILogger, ConsoleLogger)
        container.register_singleton(IDatabase, Database)

        # Resolve and use services
        database = container.get(IDatabase)
        database.connect()
        assert database.connected

        # Dispose container
        container.dispose()

        # Database should be properly disposed
        assert database.disposed
        assert not database.connected

    def test_disposal_handler():
        """Test custom disposal handlers."""
        container = DIContainer()

        # Track disposal
        disposed_services = []

        def dispose_logger(logger: ILogger):
            disposed_services.append("logger")

        def dispose_database(db: IDatabase):
            disposed_services.append("database")
            db.disconnect()

        # Register with disposal handlers
        container.register_singleton(
            ILogger, ConsoleLogger, dispose_handler=dispose_logger
        )
        container.register_singleton(
            IDatabase, Database, dispose_handler=dispose_database
        )

        # Resolve services
        container.get(ILogger)
        database = container.get(IDatabase)
        database.connect()

        # Dispose container
        container.dispose()

        # Verify disposal handlers were called
        assert "logger" in disposed_services
        assert "database" in disposed_services
        assert not database.connected

    def test_initialization_hooks():
        """Test service initialization hooks."""

        class ServiceWithInit:
            def __init__(self):
                self.initialized = False

            def initialize(self):
                self.initialized = True

        container = DIContainer()
        container.register_singleton(ServiceWithInit, ServiceWithInit)

        # Resolve service
        service = container.get(ServiceWithInit)

        # Should be initialized
        assert service.initialized

    def test_optional_dependencies():
        """Test optional dependency resolution."""
        container = DIContainer()

        # Only register logger, not database
        container.register_singleton(ILogger, ConsoleLogger)

        # Use resolve_optional for optional dependencies
        logger = container.resolve_optional(ILogger)
        database = container.resolve_optional(IDatabase, default=None)

        assert isinstance(logger, ConsoleLogger)
        assert database is None

    def test_thread_safety():
        """Test thread-safe service resolution."""
        container = DIContainer()
        container.register_singleton(ILogger, ConsoleLogger)

        results = []
        errors = []

        def resolve_service():
            try:
                logger = container.get(ILogger)
                results.append(logger)
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=resolve_service)
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Should have no errors
        assert len(errors) == 0
        # All results should be same singleton instance
        assert all(r is results[0] for r in results)

    def test_scoped_disposal():
        """Test that scoped services are disposed properly."""

        class DisposableScoped:
            def __init__(self):
                self.disposed = False

            def dispose(self):
                self.disposed = True

        container = DIContainer()
        container.register_scoped(DisposableScoped, DisposableScoped)

        # Create scope and resolve service
        with container.create_scope():
            service = container.get(DisposableScoped)
            assert not service.disposed

        # After scope exit, service should be disposed
        assert service.disposed

    def test_child_container():
        """Test child container functionality."""
        parent = DIContainer()
        parent.register_singleton(ILogger, ConsoleLogger)

        # Create child container
        child = parent.create_child_container()

        # Child inherits registrations
        assert child.is_registered(ILogger)

        # But has separate singleton instances
        parent_logger = parent.get(ILogger)
        child_logger = child.get(ILogger)

        assert isinstance(parent_logger, ConsoleLogger)
        assert isinstance(child_logger, ConsoleLogger)
        assert parent_logger is not child_logger


if __name__ == "__main__":
    # Run tests manually
    test = TestDIContainer()

    print("Running enhanced DI container tests...")

    try:
        test.test_singleton_registration()
        print("✓ Singleton registration")

        test.test_factory_registration()
        print("✓ Factory registration")

        test.test_scoped_registration()
        print("✓ Scoped registration")

        test.test_automatic_constructor_injection()
        print("✓ Automatic constructor injection")

        test.test_circular_dependency_detection()
        print("✓ Circular dependency detection")

        test.test_service_not_found_with_suggestions()
        print("✓ Service not found with suggestions")

        test.test_named_registrations()
        print("✓ Named registrations")

        test.test_disposal_lifecycle()
        print("✓ Disposal lifecycle")

        test.test_disposal_handler()
        print("✓ Custom disposal handlers")

        test.test_initialization_hooks()
        print("✓ Initialization hooks")

        test.test_optional_dependencies()
        print("✓ Optional dependencies")

        test.test_thread_safety()
        print("✓ Thread safety")

        test.test_scoped_disposal()
        print("✓ Scoped disposal")

        test.test_child_container()
        print("✓ Child container")

        print("\nAll tests passed! ✨")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
