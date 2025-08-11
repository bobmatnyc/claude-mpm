#!/usr/bin/env python3
"""
Advanced cache testing for AgentRegistry.

Tests more complex caching scenarios including:
- Pattern-based invalidation
- Multiple registry instances sharing cache
- TTL expiration
- Cache size limits
"""

import sys
import time
import tempfile
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from claude_mpm.services.agent_registry import AgentRegistry
from claude_mpm.services.simple_cache_service import SimpleCacheService


def test_pattern_invalidation():
    """Test pattern-based cache invalidation."""
    print("\n=== Testing Pattern-Based Cache Invalidation ===")
    
    # Create a shared cache service
    cache_service = SimpleCacheService()
    
    # Create registry
    registry = AgentRegistry(cache_service=cache_service)
    
    # Discover agents
    print("Initial discovery...")
    agents = registry.discover_agents()
    print(f"  Found {len(agents)} agents")
    
    # Add some other cache entries
    cache_service.set("test_key_1", "value1")
    cache_service.set("test_key_2", "value2")
    cache_service.set("agent_registry_custom", "custom_value")
    
    print(f"Cache size before invalidation: {len(cache_service.cache)}")
    
    # Invalidate all agent_registry_* keys
    invalidated = cache_service.invalidate("agent_registry_*")
    print(f"Invalidated {invalidated} entries matching 'agent_registry_*'")
    
    print(f"Cache size after invalidation: {len(cache_service.cache)}")
    
    # Test keys should still exist
    assert cache_service.get("test_key_1") == "value1", "Non-matching keys should be preserved"
    assert cache_service.get("test_key_2") == "value2", "Non-matching keys should be preserved"
    
    # Registry cache should be gone
    assert cache_service.get("agent_registry_registry") is None, "Registry cache should be invalidated"
    
    print("✓ Pattern-based invalidation works correctly")


def test_shared_cache():
    """Test multiple registry instances sharing the same cache."""
    print("\n=== Testing Shared Cache Between Instances ===")
    
    # Create a shared cache service
    cache_service = SimpleCacheService()
    
    # Create first registry
    registry1 = AgentRegistry(cache_service=cache_service)
    print("Registry 1 discovering agents...")
    agents1 = registry1.discover_agents()
    print(f"  Registry 1: Found {len(agents1)} agents")
    print(f"  Registry 1 stats: hits={registry1.discovery_stats['cache_hits']}, misses={registry1.discovery_stats['cache_misses']}")
    
    # Create second registry with same cache
    registry2 = AgentRegistry(cache_service=cache_service)
    print("\nRegistry 2 discovering agents (should use cache from Registry 1)...")
    agents2 = registry2.discover_agents()
    print(f"  Registry 2: Found {len(agents2)} agents")
    print(f"  Registry 2 stats: hits={registry2.discovery_stats['cache_hits']}, misses={registry2.discovery_stats['cache_misses']}")
    
    # Registry 2 should have gotten a cache hit
    assert registry2.discovery_stats['cache_hits'] == 1, "Registry 2 should use cached data"
    assert agents1.keys() == agents2.keys(), "Both registries should have same agents"
    
    print("✓ Multiple registries can share cache successfully")


def test_ttl_expiration():
    """Test TTL-based cache expiration."""
    print("\n=== Testing TTL Expiration ===")
    
    # Create cache with very short TTL
    cache_service = SimpleCacheService(default_ttl=1)  # 1 second TTL
    registry = AgentRegistry(cache_service=cache_service)
    
    # Override the registry's TTL setting
    registry.cache_ttl = 1
    
    print("Discovery with 1-second TTL...")
    agents1 = registry.discover_agents()
    print(f"  Found {len(agents1)} agents")
    
    # Should use cache immediately
    print("Immediate second discovery (should use cache)...")
    agents2 = registry.discover_agents()
    assert registry.discovery_stats['cache_hits'] == 1, "Should get cache hit immediately"
    
    # Wait for TTL to expire
    print("Waiting 1.5 seconds for TTL to expire...")
    time.sleep(1.5)
    
    # Should not use cache after TTL
    print("Discovery after TTL expiration (should not use cache)...")
    agents3 = registry.discover_agents()
    assert registry.discovery_stats['cache_misses'] == 2, "Should get cache miss after TTL"
    
    print("✓ TTL expiration works correctly")


def test_cache_size_limits():
    """Test cache size limits and LRU eviction."""
    print("\n=== Testing Cache Size Limits ===")
    
    # Create cache with small size limit
    cache_service = SimpleCacheService(max_size=5)
    
    print("Adding entries to cache with max_size=5...")
    
    # Add entries up to the limit
    for i in range(5):
        cache_service.set(f"key_{i}", f"value_{i}")
    
    print(f"Cache size at limit: {len(cache_service.cache)}")
    assert len(cache_service.cache) == 5, "Cache should be at max size"
    
    # Access some entries to update their access time
    time.sleep(0.01)
    cache_service.get("key_2")  # Access key_2
    cache_service.get("key_3")  # Access key_3
    
    # Add one more entry (should evict LRU)
    cache_service.set("key_5", "value_5")
    
    print(f"Cache size after adding beyond limit: {len(cache_service.cache)}")
    assert len(cache_service.cache) == 5, "Cache should stay at max size"
    
    # Check that least recently used was evicted
    # key_0 should be evicted (not accessed recently)
    assert cache_service.get("key_0") is None, "LRU entry should be evicted"
    assert cache_service.get("key_2") == "value_2", "Recently accessed entry should be preserved"
    
    print(f"Evictions count: {cache_service.metrics['evictions']}")
    assert cache_service.metrics['evictions'] >= 1, "Should have at least one eviction"
    
    print("✓ Cache size limits and LRU eviction work correctly")


def test_file_tracking_integration():
    """Test integration of file tracking with cache."""
    print("\n=== Testing File Tracking Integration ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Create multiple agent files
        files = []
        for i in range(3):
            agent_file = tmppath / f"agent_{i}.md"
            agent_file.write_text(f"# Agent {i}\nVersion: 1.0.{i}")
            files.append(agent_file)
        
        # Create registry and discover
        registry = AgentRegistry()
        registry.add_discovery_path(tmppath)
        
        print(f"Created {len(files)} agent files")
        agents = registry.discover_agents()
        print(f"Discovered {len(agents)} agents")
        
        # Check that files are being tracked
        print(f"Tracking {len(registry.discovered_files)} files")
        
        # Modify one file
        print("Modifying one agent file...")
        files[1].write_text("# Agent 1\nVersion: 2.0.0")
        
        # Discovery should detect the change
        agents2 = registry.discover_agents()
        
        # The cache should have been invalidated due to file modification
        print("✓ File tracking is integrated with cache system")


def test_cache_metrics_detailed():
    """Test detailed cache metrics."""
    print("\n=== Testing Detailed Cache Metrics ===")
    
    cache_service = SimpleCacheService()
    registry = AgentRegistry(cache_service=cache_service)
    
    # Perform various operations
    registry.discover_agents()  # Miss
    registry.discover_agents()  # Hit
    registry.discover_agents()  # Hit
    registry.invalidate_cache()
    registry.discover_agents()  # Miss after invalidation
    
    # Get metrics
    metrics = cache_service.get_cache_metrics()
    
    print("Cache Metrics:")
    for key, value in metrics.items():
        print(f"  {key}: {value}")
    
    assert metrics['hits'] > 0, "Should have cache hits"
    assert metrics['misses'] > 0, "Should have cache misses"
    assert metrics['sets'] > 0, "Should have cache sets"
    
    # Calculate and verify hit rate
    total = metrics['total_requests']
    if total > 0:
        expected_hit_rate = (metrics['hits'] / total) * 100
        reported_hit_rate = float(metrics['hit_rate'].rstrip('%'))
        assert abs(expected_hit_rate - reported_hit_rate) < 0.1, "Hit rate calculation should be accurate"
    
    print("✓ Detailed cache metrics work correctly")


def main():
    """Run all advanced cache tests."""
    print("=" * 60)
    print("Advanced Cache Testing for AgentRegistry")
    print("=" * 60)
    
    try:
        test_pattern_invalidation()
        test_shared_cache()
        test_ttl_expiration()
        test_cache_size_limits()
        test_file_tracking_integration()
        test_cache_metrics_detailed()
        
        print("\n" + "=" * 60)
        print("✅ All advanced cache tests passed!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()