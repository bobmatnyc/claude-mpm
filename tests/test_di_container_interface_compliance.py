"""
Test file for DIContainer interface compliance.

This test verifies that DIContainer properly implements the IServiceContainer interface
as required by TSK-0063.
"""

import sys
from typing import Any, List

from claude_mpm.core.container import DIContainer
from claude_mpm.services.core.interfaces import IServiceContainer


# Test classes for registration
class ITestService:
    """Test service interface."""

    def get_value(self) -> str:
        raise NotImplementedError


class TestServiceImpl(ITestService):
    """Test service implementation."""

    def __init__(self):
        self.value = "test_value"

    def get_value(self) -> str:
        return self.value


class TestServiceImpl2(ITestService):
    """Another test service implementation."""

    def __init__(self):
        self.value = "test_value_2"

    def get_value(self) -> str:
        return self.value


class TestDIContainerInterfaceCompliance:
    """Test suite for DIContainer interface compliance."""

    def test_di_container_implements_interface():
        """Test that DIContainer explicitly implements IServiceContainer."""
        container = DIContainer()
        assert isinstance(container, IServiceContainer), (
            "DIContainer must inherit from IServiceContainer"
        )

    def test_register_method_exists():
        """Test that register method exists with correct signature."""
        container = DIContainer()

        # Method should exist
        assert hasattr(container, "register"), "DIContainer must have register method"

        # Test basic registration
        container.register(ITestService, TestServiceImpl)
        assert container.is_registered(ITestService)

        # Test with singleton parameter
        container.register(ITestService, TestServiceImpl2, singleton=False)

    def test_register_instance_method_exists():
        """Test that register_instance method exists with correct signature."""
        container = DIContainer()

        # Method should exist
        assert hasattr(container, "register_instance"), (
            "DIContainer must have register_instance method"
        )

        # Test instance registration
        instance = TestServiceImpl()
        container.register_instance(ITestService, instance)

        # Verify the same instance is returned
        resolved = container.resolve(ITestService)
        assert resolved is instance, "Should return the same instance"

    def test_resolve_method_exists():
        """Test that resolve method exists with correct signature."""
        container = DIContainer()

        # Method should exist
        assert hasattr(container, "resolve"), "DIContainer must have resolve method"

        # Register and resolve
        container.register(ITestService, TestServiceImpl)
        resolved = container.resolve(ITestService)
        assert isinstance(resolved, TestServiceImpl)
        assert resolved.get_value() == "test_value"

    def test_resolve_all_method_exists():
        """Test that resolve_all method exists with correct signature."""
        container = DIContainer()

        # Method should exist
        assert hasattr(container, "resolve_all"), (
            "DIContainer must have resolve_all method"
        )

        # Test with no registrations
        results = container.resolve_all(ITestService)
        assert isinstance(results, list), "resolve_all must return a list"
        assert len(results) == 0, "Should return empty list when no registrations"

        # Test with registration
        container.register(ITestService, TestServiceImpl)
        results = container.resolve_all(ITestService)
        assert isinstance(results, list), "resolve_all must return a list"
        assert len(results) == 1, "Should return list with one item"
        assert isinstance(results[0], TestServiceImpl)

    def test_is_registered_method_exists():
        """Test that is_registered method exists with correct signature."""
        container = DIContainer()

        # Method should exist
        assert hasattr(container, "is_registered"), (
            "DIContainer must have is_registered method"
        )

        # Test before registration
        assert not container.is_registered(ITestService)

        # Test after registration
        container.register(ITestService, TestServiceImpl)
        assert container.is_registered(ITestService)

    def test_interface_method_signatures_match():
        """Test that all interface methods have matching signatures."""
        container = DIContainer()

        # Get the interface methods
        interface_methods = [
            "register",
            "register_instance",
            "resolve",
            "resolve_all",
            "is_registered",
        ]

        for method_name in interface_methods:
            assert hasattr(container, method_name), (
                f"DIContainer must have {method_name} method"
            )
            method = getattr(container, method_name)
            assert callable(method), f"{method_name} must be callable"

    def test_singleton_behavior():
        """Test that singleton registration works correctly."""
        container = DIContainer()

        # Register as singleton (default)
        container.register(ITestService, TestServiceImpl)

        # Should get the same instance
        instance1 = container.resolve(ITestService)
        instance2 = container.resolve(ITestService)
        assert instance1 is instance2, "Singleton should return same instance"

    def test_transient_behavior():
        """Test that transient registration works correctly."""
        container = DIContainer()

        # Register as transient
        container.register(ITestService, TestServiceImpl, singleton=False)

        # Should get different instances
        instance1 = container.resolve(ITestService)
        instance2 = container.resolve(ITestService)
        assert instance1 is not instance2, "Transient should return different instances"

    def test_backwards_compatibility():
        """Test that existing functionality still works after interface implementation."""
        container = DIContainer()

        # Test the enhanced methods still work
        container.register_singleton(ITestService, TestServiceImpl)
        assert container.is_registered(ITestService)

        container.register_transient(ITestService, TestServiceImpl2)
        instance = container.resolve(ITestService)
        assert isinstance(instance, TestServiceImpl2)

        # Test get method (alias for resolve)
        instance = container.get(ITestService)
        assert isinstance(instance, TestServiceImpl2)

    def test_type_annotations():
        """Test that type annotations are properly defined."""
        import inspect

        # Check register method signature
        sig = inspect.signature(DIContainer.register)
        params = sig.parameters

        assert "service_type" in params
        assert params["service_type"].annotation == type

        assert "implementation" in params
        assert params["implementation"].annotation == type

        assert "singleton" in params
        assert params["singleton"].annotation == bool
        assert params["singleton"].default is True

        # Check register_instance method signature
        sig = inspect.signature(DIContainer.register_instance)
        params = sig.parameters

        assert "service_type" in params
        assert params["service_type"].annotation == type

        assert "instance" in params
        assert params["instance"].annotation == Any

        # Check resolve_all return type
        sig = inspect.signature(DIContainer.resolve_all)
        assert sig.return_annotation == List[Any]


if __name__ == "__main__":
    # Run the tests
    test_instance = TestDIContainerInterfaceCompliance()

    print("Running DIContainer interface compliance tests...")

    test_methods = [
        method for method in dir(test_instance) if method.startswith("test_")
    ]

    passed = 0
    failed = 0

    for method_name in test_methods:
        try:
            method = getattr(test_instance, method_name)
            method()
            print(f"✓ {method_name}")
            passed += 1
        except AssertionError as e:
            print(f"✗ {method_name}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {method_name}: Unexpected error: {e}")
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")

    if failed == 0:
        print("All interface compliance tests passed!")
    else:
        sys.exit(1)
