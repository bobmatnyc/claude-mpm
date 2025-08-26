"""
Unit Tests for CacheManager Service
====================================

Tests the cache management service that was extracted from FrameworkLoader.
Verifies thread safety, TTL behavior, and cache invalidation logic.
"""

import threading
import time
import unittest
from unittest.mock import MagicMock, patch

from claude_mpm.services.core.cache_manager import CacheManager, ICacheManager


class TestCacheManager(unittest.TestCase):
    """Test suite for CacheManager service."""

    def setUp(self):
        """Set up test fixtures."""
        # Create cache manager with short TTLs for testing
        self.cache_manager = CacheManager(
            capabilities_ttl=2,  # 2 seconds for testing
            deployed_agents_ttl=1,  # 1 second for testing
            metadata_ttl=2,
            memories_ttl=2,
        )

    def test_interface_compliance(self):
        """Test that CacheManager implements ICacheManager interface."""
        self.assertIsInstance(self.cache_manager, ICacheManager)

        # Verify all interface methods are implemented
        interface_methods = [
            "get_capabilities",
            "set_capabilities",
            "get_deployed_agents",
            "set_deployed_agents",
            "get_agent_metadata",
            "set_agent_metadata",
            "get_memories",
            "set_memories",
            "clear_all",
            "clear_agent_caches",
            "clear_memory_caches",
            "is_cache_valid",
        ]

        for method_name in interface_methods:
            self.assertTrue(
                hasattr(self.cache_manager, method_name),
                f"Method {method_name} not implemented",
            )

    def test_capabilities_cache(self):
        """Test agent capabilities caching."""
        # Initially empty
        self.assertIsNone(self.cache_manager.get_capabilities())

        # Set and retrieve
        test_capabilities = "Agent1: capability1\nAgent2: capability2"
        self.cache_manager.set_capabilities(test_capabilities)

        cached = self.cache_manager.get_capabilities()
        self.assertEqual(cached, test_capabilities)

        # Test TTL expiration
        time.sleep(2.5)  # Wait for TTL to expire
        self.assertIsNone(self.cache_manager.get_capabilities())

    def test_deployed_agents_cache(self):
        """Test deployed agents caching."""
        # Initially empty
        self.assertIsNone(self.cache_manager.get_deployed_agents())

        # Set and retrieve
        test_agents = {"agent1", "agent2", "agent3"}
        self.cache_manager.set_deployed_agents(test_agents)

        cached = self.cache_manager.get_deployed_agents()
        self.assertEqual(cached, test_agents)

        # Verify we get a copy, not the original
        cached.add("agent4")
        self.assertNotEqual(self.cache_manager.get_deployed_agents(), cached)

        # Test TTL expiration (shorter TTL)
        time.sleep(1.5)  # Wait for TTL to expire
        self.assertIsNone(self.cache_manager.get_deployed_agents())

    def test_agent_metadata_cache(self):
        """Test agent metadata caching."""
        # Initially empty
        self.assertIsNone(self.cache_manager.get_agent_metadata("test_agent.py"))

        # Set and retrieve
        test_metadata = {"name": "TestAgent", "version": "1.0.0"}
        test_mtime = time.time()
        self.cache_manager.set_agent_metadata(
            "test_agent.py", test_metadata, test_mtime
        )

        cached = self.cache_manager.get_agent_metadata("test_agent.py")
        self.assertIsNotNone(cached)
        cached_data, cached_mtime = cached
        self.assertEqual(cached_data, test_metadata)
        self.assertEqual(cached_mtime, test_mtime)

        # Test TTL expiration
        time.sleep(2.5)  # Wait for TTL to expire
        self.assertIsNone(self.cache_manager.get_agent_metadata("test_agent.py"))

    def test_memories_cache(self):
        """Test memories caching."""
        # Initially empty
        self.assertIsNone(self.cache_manager.get_memories())

        # Set and retrieve
        test_memories = {
            "actual_memories": "Memory content 1",
            "agent_memories": "Memory content 2",
        }
        self.cache_manager.set_memories(test_memories)

        cached = self.cache_manager.get_memories()
        self.assertEqual(cached, test_memories)

        # Verify we get a copy
        cached["new_key"] = "new_value"
        self.assertNotEqual(self.cache_manager.get_memories(), cached)

        # Test TTL expiration
        time.sleep(2.5)  # Wait for TTL to expire
        self.assertIsNone(self.cache_manager.get_memories())

    def test_clear_all_caches(self):
        """Test clearing all caches."""
        # Populate all caches
        self.cache_manager.set_capabilities("test capabilities")
        self.cache_manager.set_deployed_agents({"agent1", "agent2"})
        self.cache_manager.set_agent_metadata("test.py", {"test": "data"}, time.time())
        self.cache_manager.set_memories({"memories": "test"})

        # Verify all are populated
        self.assertIsNotNone(self.cache_manager.get_capabilities())
        self.assertIsNotNone(self.cache_manager.get_deployed_agents())
        self.assertIsNotNone(self.cache_manager.get_agent_metadata("test.py"))
        self.assertIsNotNone(self.cache_manager.get_memories())

        # Clear all
        self.cache_manager.clear_all()

        # Verify all are cleared
        self.assertIsNone(self.cache_manager.get_capabilities())
        self.assertIsNone(self.cache_manager.get_deployed_agents())
        self.assertIsNone(self.cache_manager.get_agent_metadata("test.py"))
        self.assertIsNone(self.cache_manager.get_memories())

    def test_clear_agent_caches(self):
        """Test clearing agent-related caches only."""
        # Populate all caches
        self.cache_manager.set_capabilities("test capabilities")
        self.cache_manager.set_deployed_agents({"agent1", "agent2"})
        self.cache_manager.set_agent_metadata("test.py", {"test": "data"}, time.time())
        self.cache_manager.set_memories({"memories": "test"})

        # Clear agent caches only
        self.cache_manager.clear_agent_caches()

        # Verify agent caches are cleared
        self.assertIsNone(self.cache_manager.get_capabilities())
        self.assertIsNone(self.cache_manager.get_deployed_agents())
        self.assertIsNone(self.cache_manager.get_agent_metadata("test.py"))

        # Verify memory cache is NOT cleared
        self.assertIsNotNone(self.cache_manager.get_memories())

    def test_clear_memory_caches(self):
        """Test clearing memory caches only."""
        # Populate all caches
        self.cache_manager.set_capabilities("test capabilities")
        self.cache_manager.set_deployed_agents({"agent1", "agent2"})
        self.cache_manager.set_memories({"memories": "test"})

        # Clear memory caches only
        self.cache_manager.clear_memory_caches()

        # Verify memory cache is cleared
        self.assertIsNone(self.cache_manager.get_memories())

        # Verify agent caches are NOT cleared
        self.assertIsNotNone(self.cache_manager.get_capabilities())
        self.assertIsNotNone(self.cache_manager.get_deployed_agents())

    def test_is_cache_valid(self):
        """Test cache validity checking."""
        current_time = time.time()

        # Valid cache (within TTL)
        self.assertTrue(self.cache_manager.is_cache_valid(current_time - 1, 5))

        # Expired cache (past TTL)
        self.assertFalse(self.cache_manager.is_cache_valid(current_time - 10, 5))

        # Edge case: exactly at TTL
        self.assertFalse(self.cache_manager.is_cache_valid(current_time - 5, 5))

    def test_thread_safety(self):
        """Test thread-safe operations."""
        results = []
        errors = []

        def writer_thread():
            """Thread that writes to cache."""
            try:
                for i in range(50):
                    self.cache_manager.set_capabilities(f"capabilities_{i}")
                    self.cache_manager.set_deployed_agents({f"agent_{i}"})
                    time.sleep(0.001)  # Small delay to increase contention
            except Exception as e:
                errors.append(e)

        def reader_thread():
            """Thread that reads from cache."""
            try:
                for _i in range(50):
                    cap = self.cache_manager.get_capabilities()
                    agents = self.cache_manager.get_deployed_agents()
                    if cap:
                        results.append(cap)
                    if agents:
                        results.append(len(agents))
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        def clearer_thread():
            """Thread that clears caches."""
            try:
                for i in range(10):
                    time.sleep(0.005)
                    if i % 2 == 0:
                        self.cache_manager.clear_agent_caches()
                    else:
                        self.cache_manager.clear_all()
            except Exception as e:
                errors.append(e)

        # Create and start threads
        threads = []
        for _ in range(2):
            threads.append(threading.Thread(target=writer_thread))
            threads.append(threading.Thread(target=reader_thread))
        threads.append(threading.Thread(target=clearer_thread))

        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=5)

        # Verify no errors occurred
        self.assertEqual(len(errors), 0, f"Thread safety errors: {errors}")

        # Verify some operations succeeded
        self.assertGreater(len(results), 0, "No successful operations")

    def test_get_stats(self):
        """Test cache statistics retrieval."""
        # Get initial stats (empty)
        stats = self.cache_manager.get_stats()

        self.assertIn("capabilities", stats)
        self.assertIn("deployed_agents", stats)
        self.assertIn("metadata", stats)
        self.assertIn("memories", stats)

        # Populate some caches
        self.cache_manager.set_capabilities("test")
        self.cache_manager.set_deployed_agents({"a1", "a2", "a3"})

        # Get updated stats
        stats = self.cache_manager.get_stats()

        self.assertTrue(stats["capabilities"]["cached"])
        self.assertTrue(stats["capabilities"]["valid"])
        self.assertIsNotNone(stats["capabilities"]["age"])

        self.assertTrue(stats["deployed_agents"]["cached"])
        self.assertEqual(stats["deployed_agents"]["count"], 3)
        self.assertTrue(stats["deployed_agents"]["valid"])

        self.assertEqual(stats["metadata"]["entries"], 0)
        self.assertFalse(stats["memories"]["cached"])

    def test_default_ttl_values(self):
        """Test default TTL values are properly set."""
        default_manager = CacheManager()

        self.assertEqual(default_manager.capabilities_ttl, 60)
        self.assertEqual(default_manager.deployed_agents_ttl, 30)
        self.assertEqual(default_manager.metadata_ttl, 60)
        self.assertEqual(default_manager.memories_ttl, 60)

    def test_multiple_metadata_entries(self):
        """Test handling multiple metadata entries."""
        # Add multiple metadata entries
        for i in range(5):
            self.cache_manager.set_agent_metadata(
                f"agent_{i}.py", {"name": f"Agent{i}", "id": i}, time.time()
            )

        # Verify all are cached
        for i in range(5):
            cached = self.cache_manager.get_agent_metadata(f"agent_{i}.py")
            self.assertIsNotNone(cached)
            data, _ = cached
            self.assertEqual(data["id"], i)

        # Clear agent caches
        self.cache_manager.clear_agent_caches()

        # Verify all metadata is cleared
        for i in range(5):
            self.assertIsNone(self.cache_manager.get_agent_metadata(f"agent_{i}.py"))


class TestCacheManagerIntegration(unittest.TestCase):
    """Integration tests with underlying FileSystemCache."""

    @patch("claude_mpm.services.core.cache_manager.FileSystemCache")
    def test_fs_cache_initialization(self, mock_fs_cache_class):
        """Test that FileSystemCache is properly initialized."""
        mock_fs_cache = MagicMock()
        mock_fs_cache_class.return_value = mock_fs_cache

        # Create cache manager
        CacheManager(
            capabilities_ttl=100,
            deployed_agents_ttl=50,
            metadata_ttl=75,
            memories_ttl=80,
        )

        # Verify FileSystemCache was created with correct parameters
        mock_fs_cache_class.assert_called_once_with(
            max_size_mb=50, default_ttl=100  # Should use max of all TTLs
        )

    @patch("claude_mpm.services.core.cache_manager.FileSystemCache")
    def test_clear_all_clears_fs_cache(self, mock_fs_cache_class):
        """Test that clear_all also clears the underlying FileSystemCache."""
        mock_fs_cache = MagicMock()
        mock_fs_cache_class.return_value = mock_fs_cache

        manager = CacheManager()
        manager.clear_all()

        # Verify FileSystemCache.clear() was called
        mock_fs_cache.clear.assert_called_once()

    @patch("claude_mpm.services.core.cache_manager.FileSystemCache")
    def test_stats_includes_fs_cache_stats(self, mock_fs_cache_class):
        """Test that stats include FileSystemCache statistics."""
        mock_fs_cache = MagicMock()
        mock_fs_cache.get_stats.return_value = {
            "hits": 100,
            "misses": 20,
            "hit_rate": 0.833,
        }
        mock_fs_cache_class.return_value = mock_fs_cache

        manager = CacheManager()
        stats = manager.get_stats()

        # Verify fs_cache stats are included
        self.assertIn("fs_cache", stats)
        self.assertEqual(stats["fs_cache"]["hits"], 100)
        self.assertEqual(stats["fs_cache"]["misses"], 20)


if __name__ == "__main__":
    unittest.main()
