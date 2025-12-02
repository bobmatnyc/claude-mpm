"""
Integration tests for Service Container with Framework Loader
=============================================================

WHY: These tests ensure the service container properly integrates with
the framework loader and other core components.
"""

from claude_mpm.core.framework_loader import FrameworkLoader
from claude_mpm.services.core.cache_manager import CacheManager
from claude_mpm.services.core.service_container import (
    ServiceContainer,
    get_global_container,
)
from claude_mpm.services.core.service_interfaces import ICacheManager


class TestServiceContainerIntegration:
    """Test service container integration with framework components."""

    def test_framework_loader_uses_container(self):
        """Test that framework loader properly uses the service container."""
        # Create a custom container
        container = ServiceContainer()

        # Create framework loader with custom container
        loader = FrameworkLoader(service_container=container)

        # Verify cache manager was registered and resolved
        assert container.is_registered(ICacheManager)
        assert loader._cache_manager is not None
        assert isinstance(loader._cache_manager, CacheManager)

    def test_framework_loader_uses_global_container(self):
        """Test that framework loader uses global container when none provided."""
        # Clear global container first
        global_container = get_global_container()
        global_container.clear()

        # Create framework loader without container
        loader = FrameworkLoader()

        # Should use global container
        assert loader.container is global_container
        assert global_container.is_registered(ICacheManager)

    def test_cache_manager_singleton_behavior(self):
        """Test that cache manager behaves as singleton in framework loader."""
        container = ServiceContainer()

        # Create two framework loaders with same container
        loader1 = FrameworkLoader(service_container=container)
        loader2 = FrameworkLoader(service_container=container)

        # Both should have the same cache manager instance
        assert loader1._cache_manager is loader2._cache_manager

    def test_cache_operations_through_container(self):
        """Test cache operations work correctly through DI container."""
        container = ServiceContainer()
        loader = FrameworkLoader(service_container=container)

        # Test setting and getting capabilities
        test_capabilities = "Test Agent Capabilities"
        loader._cache_manager.set_capabilities(test_capabilities)
        retrieved = loader._cache_manager.get_capabilities()

        assert retrieved == test_capabilities

        # Test cache clearing
        loader._cache_manager.clear_all()
        assert loader._cache_manager.get_capabilities() is None

    def test_custom_cache_manager_implementation(self):
        """Test registering a custom cache manager implementation."""

        # Create a mock cache manager
        class MockCacheManager:
            def __init__(self):
                self.capabilities = None
                self.deployed_agents = None
                self.memories = None
                self.capabilities_ttl = 60
                self.deployed_agents_ttl = 30
                self.metadata_ttl = 60
                self.memories_ttl = 60

            def get_capabilities(self):
                return self.capabilities

            def set_capabilities(self, value):
                self.capabilities = value

            def get_deployed_agents(self):
                return self.deployed_agents

            def set_deployed_agents(self, agents):
                self.deployed_agents = agents

            def get_agent_metadata(self, agent_file):
                return None

            def set_agent_metadata(self, agent_file, metadata, mtime):
                pass

            def get_memories(self):
                return self.memories

            def set_memories(self, memories):
                self.memories = memories

            def clear_all(self):
                self.capabilities = None
                self.deployed_agents = None
                self.memories = None

            def clear_agent_caches(self):
                self.capabilities = None
                self.deployed_agents = None

            def clear_memory_caches(self):
                self.memories = None

            def is_cache_valid(self, cache_time, ttl):
                return True

        # Create container and register mock
        container = ServiceContainer()
        mock_cache = MockCacheManager()
        container.register_instance(ICacheManager, mock_cache)

        # Create framework loader with custom container
        loader = FrameworkLoader(service_container=container)

        # Should use our mock cache manager
        assert loader._cache_manager is mock_cache

        # Test that it works
        loader._cache_manager.set_capabilities("Mock capabilities")
        assert loader._cache_manager.get_capabilities() == "Mock capabilities"

    def test_container_registration_info(self):
        """Test getting registration information from container."""
        container = ServiceContainer()
        FrameworkLoader(service_container=container)

        # Get registration info
        info = container.get_registration_info()

        # Should have ICacheManager registered
        assert "ICacheManager" in info
        assert info["ICacheManager"]["lifetime"] == "singleton"
        assert info["ICacheManager"]["implementation"] == "CacheManager"

    def test_multiple_loaders_share_cache_manager(self):
        """Test that multiple framework loaders share the same cache manager."""
        container = ServiceContainer()

        # Create multiple loaders
        loader1 = FrameworkLoader(service_container=container)
        loader2 = FrameworkLoader(service_container=container)
        loader3 = FrameworkLoader(service_container=container)

        # All should share the same cache manager (singleton)
        assert loader1._cache_manager is loader2._cache_manager
        assert loader2._cache_manager is loader3._cache_manager

        # Changes in one should be visible in all
        loader1._cache_manager.set_capabilities("Shared capabilities")
        assert loader2._cache_manager.get_capabilities() == "Shared capabilities"
        assert loader3._cache_manager.get_capabilities() == "Shared capabilities"

    def test_container_clear_behavior(self):
        """Test container clearing and re-registration."""
        container = ServiceContainer()

        # Create loader (registers cache manager)
        loader1 = FrameworkLoader(service_container=container)
        cache1 = loader1._cache_manager

        # Clear container
        container.clear()

        # Cache manager should no longer be registered
        assert not container.is_registered(ICacheManager)

        # Create new loader (should re-register)
        loader2 = FrameworkLoader(service_container=container)
        cache2 = loader2._cache_manager

        # Should be a different instance (container was cleared)
        assert cache1 is not cache2
        assert container.is_registered(ICacheManager)
