#!/usr/bin/env python3
"""
Test framework_loader caching under concurrent access.

This ensures the caching is thread-safe and works correctly when multiple
threads access the framework loader simultaneously.
"""

import concurrent.futures
import sys
import threading
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.framework_loader import FrameworkLoader

# Shared loader instance for concurrency test
shared_loader = None
loader_lock = threading.Lock()


def get_shared_loader():
    """Get or create the shared loader instance (thread-safe)."""
    global shared_loader
    if shared_loader is None:
        with loader_lock:
            if shared_loader is None:
                shared_loader = FrameworkLoader()
    return shared_loader


def concurrent_access_test(thread_id: int) -> dict:
    """Test concurrent access to framework loader."""
    results = {"thread_id": thread_id, "times": {}, "errors": []}

    try:
        loader = get_shared_loader()

        # Test deployed agents
        start = time.time()
        agents = loader._get_deployed_agents()
        results["times"]["deployed_agents"] = time.time() - start
        results["agents_count"] = len(agents)

        # Test capabilities generation
        start = time.time()
        capabilities = loader._generate_agent_capabilities_section()
        results["times"]["capabilities"] = time.time() - start
        results["capabilities_size"] = len(capabilities)

        # Test memory loading
        start = time.time()
        content = {}
        loader._load_actual_memories(content)
        results["times"]["memories"] = time.time() - start
        results["memories_loaded"] = "actual_memories" in content

    except Exception as e:
        results["errors"].append(str(e))

    return results


def test_concurrent_access():
    """Test framework loader under concurrent access."""
    print("\n" + "=" * 80)
    print("CONCURRENT ACCESS TEST")
    print("=" * 80)

    num_threads = 10
    print(f"\nTesting with {num_threads} concurrent threads...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        # Submit all tasks
        futures = [
            executor.submit(concurrent_access_test, i) for i in range(num_threads)
        ]

        # Collect results
        results = []
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)

    # Analyze results
    print("\nResults by thread:")
    total_times = {"deployed_agents": 0, "capabilities": 0, "memories": 0}
    errors = []

    for result in sorted(results, key=lambda x: x["thread_id"]):
        thread_id = result["thread_id"]
        times = result["times"]

        print(f"  Thread {thread_id:2d}: ", end="")
        print(f"agents={times.get('deployed_agents', -1):.3f}s, ", end="")
        print(f"caps={times.get('capabilities', -1):.3f}s, ", end="")
        print(f"mem={times.get('memories', -1):.3f}s")

        if result["errors"]:
            errors.extend(result["errors"])
            print(f"    ERRORS: {result['errors']}")

        for key in total_times:
            if key in times:
                total_times[key] += times[key]

    # Calculate averages
    print("\nAverage times across all threads:")
    for key, total in total_times.items():
        avg = total / num_threads
        print(f"  {key}: {avg:.4f}s")

    # Check consistency
    print("\nConsistency check:")
    agents_counts = [r.get("agents_count", -1) for r in results]
    capabilities_sizes = [r.get("capabilities_size", -1) for r in results]
    memories_loaded = [r.get("memories_loaded", False) for r in results]

    if len(set(agents_counts)) == 1 and agents_counts[0] != -1:
        print(f"  ✅ All threads got same agent count: {agents_counts[0]}")
    else:
        print(f"  ❌ Inconsistent agent counts: {set(agents_counts)}")

    if len(set(capabilities_sizes)) == 1 and capabilities_sizes[0] != -1:
        print(
            f"  ✅ All threads got same capabilities size: {capabilities_sizes[0]} chars"
        )
    else:
        print(f"  ❌ Inconsistent capabilities sizes: {set(capabilities_sizes)}")

    if all(memories_loaded):
        print("  ✅ All threads successfully loaded memories")
    else:
        print("  ❌ Some threads failed to load memories")

    if not errors:
        print("\n✅ No errors during concurrent access")
    else:
        print(f"\n❌ {len(errors)} errors during concurrent access:")
        for error in errors[:5]:  # Show first 5 errors
            print(f"    - {error}")

    print("\n" + "=" * 80)


def test_cache_expiry():
    """Test that caches expire correctly after TTL."""
    print("\n" + "=" * 80)
    print("CACHE EXPIRY TEST")
    print("=" * 80)

    loader = FrameworkLoader()

    # Set very short TTLs for testing
    loader.CAPABILITIES_CACHE_TTL = 0.5  # 500ms
    loader.DEPLOYED_AGENTS_CACHE_TTL = 0.5
    loader.MEMORIES_CACHE_TTL = 0.5

    print("\nTesting cache expiry with 500ms TTL...")

    # First call (cache miss)
    start = time.time()
    loader._generate_agent_capabilities_section()
    time1 = time.time() - start
    print(f"  First call: {time1:.3f}s (cache miss)")

    # Immediate second call (cache hit)
    start = time.time()
    loader._generate_agent_capabilities_section()
    time2 = time.time() - start
    print(f"  Immediate second call: {time2:.3f}s (cache hit)")

    # Wait for cache to expire
    print("  Waiting 600ms for cache to expire...")
    time.sleep(0.6)

    # Third call (cache expired, should be slow again)
    start = time.time()
    loader._generate_agent_capabilities_section()
    time3 = time.time() - start
    print(f"  After expiry: {time3:.3f}s (cache miss)")

    if time2 < time1 and time3 > time2:
        print("\n✅ Cache expiry working correctly")
        print(f"   Cache hit was {time1 / time2:.1f}x faster")
        print("   Cache expired correctly after TTL")
    else:
        print("\n⚠️  Cache expiry may not be working correctly")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    test_concurrent_access()
    test_cache_expiry()
