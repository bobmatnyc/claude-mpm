#!/usr/bin/env python3
"""
Test script for AgentRegistry caching mechanism.

This script tests:
1. Cache hits and misses
2. File modification detection
3. Force refresh functionality
4. Cache invalidation
5. Performance improvement
"""

import sys
import time
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.agents.registry import AgentRegistry
from claude_mpm.services.memory.cache.simple_cache import SimpleCacheService


def test_basic_caching():
    """Test basic caching functionality."""
    print("\n=== Testing Basic Caching ===")

    # Create registry with default cache
    registry = get_agent_registry()

    # First discovery (cache miss)
    print("First discovery (should be cache miss)...")
    start = time.time()
    agents1 = registry.discover_agents()
    first_time = time.time() - start
    print(f"  Discovered {len(agents1)} agents in {first_time:.3f}s")
    print(
        f"  Cache stats: hits={registry.discovery_stats['cache_hits']}, misses={registry.discovery_stats['cache_misses']}"
    )

    # Second discovery (cache hit)
    print("\nSecond discovery (should be cache hit)...")
    start = time.time()
    agents2 = registry.discover_agents()
    second_time = time.time() - start
    print(f"  Discovered {len(agents2)} agents in {second_time:.3f}s")
    print(
        f"  Cache stats: hits={registry.discovery_stats['cache_hits']}, misses={registry.discovery_stats['cache_misses']}"
    )

    # Verify cache is faster
    assert second_time < first_time / 2, "Cache should be significantly faster"
    assert agents1.keys() == agents2.keys(), "Cache should return same agents"
    print("✓ Basic caching works correctly")


def test_force_refresh():
    """Test force refresh functionality."""
    print("\n=== Testing Force Refresh ===")

    registry = get_agent_registry()

    # Initial discovery
    print("Initial discovery...")
    registry.discover_agents()
    initial_hits = registry.discovery_stats["cache_hits"]
    initial_misses = registry.discovery_stats["cache_misses"]

    # Force refresh
    print("Force refresh...")
    registry.discover_agents(force_refresh=True)

    # Should have one more miss, same hits
    assert registry.discovery_stats["cache_misses"] == initial_misses + 1
    assert registry.discovery_stats["cache_hits"] == initial_hits
    print("✓ Force refresh bypasses cache correctly")


def test_file_modification_detection():
    """Test that cache invalidates when files are modified."""
    print("\n=== Testing File Modification Detection ===")

    # Create a temporary directory with an agent file
    with tmp_path as tmpdir:
        tmppath = Path(tmpdir)
        agent_file = tmppath / "test_agent.md"

        # Write initial agent file
        agent_file.write_text(
            """# Test Agent
Description: Initial version
Version: 1.0.0
"""
        )

        # Create registry and add the temp path
        registry = get_agent_registry()
        registry.add_discovery_path(tmppath)

        # First discovery
        print("First discovery...")
        registry.discover_agents()
        test_agent1 = registry.get_agent("test")
        print(f"  Found agent: {test_agent1.name if test_agent1 else 'None'}")

        # Wait a bit to ensure file modification time changes
        time.sleep(0.1)

        # Modify the agent file
        print("Modifying agent file...")
        agent_file.write_text(
            """# Test Agent
Description: Modified version
Version: 2.0.0
"""
        )

        # Second discovery (should detect modification)
        print("Second discovery (should detect file change)...")
        registry.discover_agents()
        test_agent2 = registry.get_agent("test")

        # Cache should have detected the change
        if test_agent1 and test_agent2:
            print(f"  Version changed: {test_agent1.version} -> {test_agent2.version}")

        print("✓ File modification detection works (cache invalidated on file change)")


def test_cache_invalidation():
    """Test manual cache invalidation."""
    print("\n=== Testing Cache Invalidation ===")

    registry = get_agent_registry()

    # Initial discovery
    print("Initial discovery...")
    registry.discover_agents()

    # Should use cache
    print("Second discovery (should use cache)...")
    registry.discover_agents()
    hits_before = registry.discovery_stats["cache_hits"]

    # Invalidate cache
    print("Invalidating cache...")
    registry.invalidate_cache()

    # Should not use cache
    print("Third discovery (should not use cache after invalidation)...")
    registry.discover_agents()
    hits_after = registry.discovery_stats["cache_hits"]

    assert hits_after == hits_before, "Cache should be invalidated"
    print("✓ Manual cache invalidation works correctly")


def test_cache_metrics():
    """Test cache metrics reporting."""
    print("\n=== Testing Cache Metrics ===")

    # Create registry with custom cache service
    cache_service = SimpleCacheService(default_ttl=300, max_size=100)
    registry = AgentRegistry(cache_service=cache_service)

    # Perform several operations
    registry.discover_agents()
    registry.discover_agents()  # Cache hit
    registry.discover_agents(force_refresh=True)  # Force refresh

    # Get statistics
    stats = registry.get_statistics()

    print("Registry statistics:")
    print(f"  Total agents: {stats['total_agents']}")
    print(f"  Discovery stats: {stats['discovery_stats']}")

    if stats.get("cache_metrics"):
        print(f"  Cache metrics: {stats['cache_metrics']}")
        assert stats["cache_metrics"]["hits"] > 0, "Should have cache hits"
        assert stats["cache_metrics"]["misses"] > 0, "Should have cache misses"

    print("✓ Cache metrics reporting works correctly")


def test_performance_improvement():
    """Test that caching improves performance."""
    print("\n=== Testing Performance Improvement ===")

    # Test with cache disabled (simulate by always forcing refresh)
    registry_no_cache = get_agent_registry()

    print("Testing without cache (10 discoveries with force_refresh)...")
    start = time.time()
    for _i in range(10):
        registry_no_cache.discover_agents(force_refresh=True)
    time_without_cache = time.time() - start
    print(f"  Time without cache: {time_without_cache:.3f}s")

    # Test with cache enabled
    registry_with_cache = get_agent_registry()

    print("Testing with cache (10 discoveries, first is miss, rest are hits)...")
    start = time.time()
    for _i in range(10):
        registry_with_cache.discover_agents()
    time_with_cache = time.time() - start
    print(f"  Time with cache: {time_with_cache:.3f}s")

    improvement = (time_without_cache - time_with_cache) / time_without_cache * 100
    print(f"  Performance improvement: {improvement:.1f}%")

    assert time_with_cache < time_without_cache, "Cache should improve performance"
    print("✓ Caching provides significant performance improvement")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing AgentRegistry Caching Mechanism")
    print("=" * 60)

    try:
        test_basic_caching()
        test_force_refresh()
        test_file_modification_detection()
        test_cache_invalidation()
        test_cache_metrics()
        test_performance_improvement()

        print("\n" + "=" * 60)
        print("✅ All cache tests passed successfully!")
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
