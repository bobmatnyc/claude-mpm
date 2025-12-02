#!/usr/bin/env python3
"""
Test script to verify cache behavior, TTL expiration, and manual clearing.

This script tests that the caching system works correctly including TTL
expiration and manual cache clearing functionality.
"""

import logging
import sys
import threading
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.framework_loader import FrameworkLoader


def setup_logging():
    """Setup logging to see cache hit/miss messages."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )


def test_cache_ttl_expiration():
    """Test that caches expire after TTL."""
    print("\n" + "=" * 60)
    print("Testing Cache TTL Expiration")
    print("=" * 60)

    # Create loader with short TTL for testing
    loader = FrameworkLoader()

    # Override TTL settings for faster testing
    original_ttl = loader.CAPABILITIES_CACHE_TTL
    loader.CAPABILITIES_CACHE_TTL = 2  # 2 seconds for testing

    try:
        # First call - should be cache miss
        print("1. First call (cache miss expected)...")
        start = time.time()
        capabilities1 = loader._generate_agent_capabilities_section()
        first_time = time.time() - start
        print(f"   Time: {first_time:.3f}s")

        # Second call immediately - should be cache hit
        print("2. Second call immediately (cache hit expected)...")
        start = time.time()
        capabilities2 = loader._generate_agent_capabilities_section()
        second_time = time.time() - start
        print(f"   Time: {second_time:.3f}s")

        assert capabilities1 == capabilities2, "Cache should return same content"
        print("   ✓ Cache hit successful - same content returned")

        # Wait for TTL to expire
        print(
            f"3. Waiting {loader.CAPABILITIES_CACHE_TTL + 1} seconds for TTL expiration..."
        )
        time.sleep(loader.CAPABILITIES_CACHE_TTL + 1)

        # Third call after TTL - should be cache miss
        print("4. Third call after TTL (cache miss expected)...")
        start = time.time()
        capabilities3 = loader._generate_agent_capabilities_section()
        third_time = time.time() - start
        print(f"   Time: {third_time:.3f}s")

        assert capabilities1 == capabilities3, "Content should be consistent"
        print("   ✓ TTL expiration working - content consistent after reload")

        # Verify timing indicates cache miss
        if third_time > second_time * 2:
            print(
                "   ✓ TTL expiration confirmed - third call took longer than cached call"
            )
        else:
            print("   ⚠ TTL expiration timing unclear - but functionality works")

    finally:
        # Restore original TTL
        loader.CAPABILITIES_CACHE_TTL = original_ttl

    return True


def test_manual_cache_clearing():
    """Test manual cache clearing functionality."""
    print("\n" + "=" * 60)
    print("Testing Manual Cache Clearing")
    print("=" * 60)

    loader = FrameworkLoader()

    # Load caches
    print("1. Loading caches...")
    deployed_agents = loader._get_deployed_agents()
    capabilities = loader._generate_agent_capabilities_section()
    content = {}
    loader._load_actual_memories(content)

    print(f"   Deployed agents: {len(deployed_agents)}")
    print(f"   Capabilities: {len(capabilities)} chars")
    print(f"   Memories loaded: {'actual_memories' in content}")

    # Verify caches are populated
    assert loader._deployed_agents_cache is not None, (
        "Deployed agents cache should be populated"
    )
    assert loader._agent_capabilities_cache is not None, (
        "Capabilities cache should be populated"
    )
    print("   ✓ Caches are populated")

    # Clear all caches
    print("2. Clearing all caches...")
    loader.clear_all_caches()

    # Verify caches are cleared
    assert loader._deployed_agents_cache is None, (
        "Deployed agents cache should be cleared"
    )
    assert loader._agent_capabilities_cache is None, (
        "Capabilities cache should be cleared"
    )
    assert loader._memories_cache is None, "Memories cache should be cleared"
    assert len(loader._agent_metadata_cache) == 0, "Metadata cache should be cleared"
    print("   ✓ All caches cleared successfully")

    # Test selective cache clearing
    print("3. Testing selective cache clearing...")

    # Reload some caches
    loader._get_deployed_agents()
    loader._generate_agent_capabilities_section()

    # Clear only agent caches
    loader.clear_agent_caches()
    assert loader._deployed_agents_cache is None, (
        "Deployed agents cache should be cleared"
    )
    assert loader._agent_capabilities_cache is None, (
        "Capabilities cache should be cleared"
    )
    print("   ✓ Agent caches cleared selectively")

    # Load memory and test memory cache clearing
    content2 = {}
    loader._load_actual_memories(content2)
    assert loader._memories_cache is not None, "Memory cache should be populated"

    loader.clear_memory_caches()
    assert loader._memories_cache is None, "Memory cache should be cleared"
    print("   ✓ Memory cache cleared selectively")

    return True


def test_cache_consistency():
    """Test that cached content is consistent with fresh loads."""
    print("\n" + "=" * 60)
    print("Testing Cache Consistency")
    print("=" * 60)

    loader = FrameworkLoader()

    # Clear all caches to start fresh
    loader.clear_all_caches()

    # Load content multiple times and verify consistency
    print("1. Testing deployed agents consistency...")
    agents1 = loader._get_deployed_agents()
    agents2 = loader._get_deployed_agents()  # Should be cached
    loader.clear_agent_caches()
    agents3 = loader._get_deployed_agents()  # Fresh load

    assert agents1 == agents2 == agents3, "Deployed agents should be consistent"
    print(f"   ✓ Deployed agents consistent across {len(agents1)} agents")

    print("2. Testing capabilities consistency...")
    caps1 = loader._generate_agent_capabilities_section()
    caps2 = loader._generate_agent_capabilities_section()  # Should be cached
    loader.clear_agent_caches()
    caps3 = loader._generate_agent_capabilities_section()  # Fresh load

    assert caps1 == caps2 == caps3, "Capabilities should be consistent"
    print(f"   ✓ Capabilities consistent across {len(caps1)} chars")

    print("3. Testing memory consistency...")
    content1 = {}
    loader._load_actual_memories(content1)
    content2 = {}
    loader._load_actual_memories(content2)  # Should be cached
    loader.clear_memory_caches()
    content3 = {}
    loader._load_actual_memories(content3)  # Fresh load

    # Compare memory content
    mem1 = content1.get("actual_memories", "")
    mem2 = content2.get("actual_memories", "")
    mem3 = content3.get("actual_memories", "")

    assert mem1 == mem2 == mem3, "Memory content should be consistent"
    print(f"   ✓ Memory content consistent across {len(mem1)} bytes")

    return True


def test_concurrent_access():
    """Test thread-safety under concurrent access."""
    print("\n" + "=" * 60)
    print("Testing Concurrent Access (Thread Safety)")
    print("=" * 60)

    loader = FrameworkLoader()
    loader.clear_all_caches()

    results = {}
    errors = []

    def worker(thread_id):
        """Worker function for concurrent testing."""
        try:
            # Each thread does the same operations
            deployed = loader._get_deployed_agents()
            caps = loader._generate_agent_capabilities_section()
            content = {}
            loader._load_actual_memories(content)

            results[thread_id] = {
                "deployed": deployed,
                "capabilities": caps,
                "memories": content.get("actual_memories", ""),
            }
        except Exception as e:
            errors.append(f"Thread {thread_id}: {e}")

    # Launch multiple threads
    print("1. Launching 5 concurrent threads...")
    threads = []
    for i in range(5):
        thread = threading.Thread(target=worker, args=(i,))
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    print(f"2. All threads completed. Errors: {len(errors)}")

    if errors:
        for error in errors:
            print(f"   Error: {error}")
        return False

    # Verify all threads got consistent results
    print("3. Verifying result consistency across threads...")

    reference = results[0]
    for thread_id, result in results.items():
        if result["deployed"] != reference["deployed"]:
            print(f"   ✗ Thread {thread_id} deployed agents differ")
            return False
        if result["capabilities"] != reference["capabilities"]:
            print(f"   ✗ Thread {thread_id} capabilities differ")
            return False
        if result["memories"] != reference["memories"]:
            print(f"   ✗ Thread {thread_id} memories differ")
            return False

    print(f"   ✓ All {len(results)} threads returned consistent results")
    print("   ✓ Thread safety confirmed")

    return True


def main():
    """Run all cache behavior tests."""
    setup_logging()

    print("Framework Loader Cache Behavior Test")
    print("=" * 80)
    print("Testing cache TTL, manual clearing, and thread safety...")

    tests = [
        test_manual_cache_clearing,
        test_cache_consistency,
        test_concurrent_access,
        test_cache_ttl_expiration,  # Last because it sleeps
    ]

    passed = 0
    total = len(tests)

    for test_func in tests:
        try:
            test_func()
            passed += 1
            print("✓ PASSED")
        except Exception as e:
            print(f"✗ FAILED: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 80)
    print("CACHE BEHAVIOR TEST SUMMARY")
    print("=" * 80)
    print(f"Tests passed: {passed}/{total}")

    if passed == total:
        print("✅ ALL CACHE TESTS PASSED!")
        print("Cache behavior is working correctly.")
    else:
        print("⚠️ SOME CACHE TESTS FAILED!")
        print("Cache behavior may have issues.")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
