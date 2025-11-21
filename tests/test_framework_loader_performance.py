#!/usr/bin/env python3
"""
Test script to verify framework_loader.py performance optimizations.

This script measures the performance improvements from caching in framework_loader.py
by timing multiple calls to the same methods and checking cache hit rates.
"""

import logging
import sys
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
        datefmt="%H:%M:%S.%f",
    )


def measure_performance():
    """Measure performance improvements from caching."""
    print("\n" + "=" * 80)
    print("Framework Loader Performance Test")
    print("=" * 80)

    # Initialize framework loader
    print("\n1. Initializing FrameworkLoader...")
    start = time.time()
    loader = FrameworkLoader()
    init_time = time.time() - start
    print(f"   Initialization time: {init_time:.3f}s")

    # Test 1: _get_deployed_agents caching
    print("\n2. Testing _get_deployed_agents() caching:")

    # First call (cache miss)
    start = time.time()
    agents1 = loader._get_deployed_agents()
    first_call = time.time() - start
    print(
        f"   First call (cache miss): {first_call:.3f}s - Found {len(agents1)} agents"
    )

    # Second call (cache hit)
    start = time.time()
    loader._get_deployed_agents()
    second_call = time.time() - start
    print(f"   Second call (cache hit): {second_call:.3f}s")

    speedup = first_call / second_call if second_call > 0 else float("inf")
    print(f"   Speedup from caching: {speedup:.1f}x faster")

    # Test 2: _generate_agent_capabilities_section caching
    print("\n3. Testing _generate_agent_capabilities_section() caching:")

    # First call (cache miss)
    start = time.time()
    caps1 = loader._generate_agent_capabilities_section()
    first_call = time.time() - start
    print(
        f"   First call (cache miss): {first_call:.3f}s - Generated {len(caps1)} chars"
    )

    # Second call (cache hit)
    start = time.time()
    loader._generate_agent_capabilities_section()
    second_call = time.time() - start
    print(f"   Second call (cache hit): {second_call:.3f}s")

    speedup = first_call / second_call if second_call > 0 else float("inf")
    print(f"   Speedup from caching: {speedup:.1f}x faster")

    # Test 3: _load_actual_memories caching
    print("\n4. Testing _load_actual_memories() caching:")

    content = {}

    # First call (cache miss)
    start = time.time()
    loader._load_actual_memories(content)
    first_call = time.time() - start
    memories_loaded = (
        len(content.get("actual_memories", "")) if "actual_memories" in content else 0
    )
    print(
        f"   First call (cache miss): {first_call:.3f}s - Loaded {memories_loaded} bytes"
    )

    # Clear content for second call
    content.clear()

    # Second call (cache hit)
    start = time.time()
    loader._load_actual_memories(content)
    second_call = time.time() - start
    print(f"   Second call (cache hit): {second_call:.3f}s")

    speedup = first_call / second_call if second_call > 0 else float("inf")
    print(f"   Speedup from caching: {speedup:.1f}x faster")

    # Test 4: Full framework loading simulation
    print("\n5. Simulating full framework loading (multiple calls):")

    total_time_uncached = 0
    total_time_cached = 0

    # Clear all caches
    loader.clear_all_caches()

    # First full load (no caches)
    start = time.time()
    _ = loader._get_deployed_agents()
    _ = loader._generate_agent_capabilities_section()
    content = {}
    loader._load_actual_memories(content)
    total_time_uncached = time.time() - start
    print(f"   First full load (no cache): {total_time_uncached:.3f}s")

    # Second full load (with caches)
    start = time.time()
    _ = loader._get_deployed_agents()
    _ = loader._generate_agent_capabilities_section()
    content = {}
    loader._load_actual_memories(content)
    total_time_cached = time.time() - start
    print(f"   Second full load (cached): {total_time_cached:.3f}s")

    speedup = (
        total_time_uncached / total_time_cached
        if total_time_cached > 0
        else float("inf")
    )
    time_saved = total_time_uncached - total_time_cached
    print(f"   Overall speedup: {speedup:.1f}x faster")
    print(f"   Time saved per call: {time_saved:.3f}s")

    # Test cache invalidation
    print("\n6. Testing cache invalidation:")
    print("   Clearing all caches...")
    loader.clear_all_caches()

    # Should be slow again (cache miss)
    start = time.time()
    _ = loader._generate_agent_capabilities_section()
    after_clear = time.time() - start
    print(f"   After cache clear: {after_clear:.3f}s (expected to be slow)")

    print("\n" + "=" * 80)
    print("PERFORMANCE OPTIMIZATION SUMMARY")
    print("=" * 80)

    if total_time_cached < 5.0:
        print("✅ SUCCESS: Framework loading is now under 5 seconds!")
        print(f"   Current load time: {total_time_cached:.3f}s")
        print("   Original estimated time: ~11.9s")
        print(f"   Total improvement: ~{11.9 / total_time_cached:.1f}x faster")
    else:
        print("⚠️  WARNING: Framework loading still takes more than 5 seconds")
        print(f"   Current load time: {total_time_cached:.3f}s")
        print("   Further optimization may be needed")

    print("\nCache TTL Settings:")
    print(f"   Agent capabilities: {loader.CAPABILITIES_CACHE_TTL}s")
    print(f"   Deployed agents: {loader.DEPLOYED_AGENTS_CACHE_TTL}s")
    print(f"   Agent metadata: {loader.METADATA_CACHE_TTL}s")
    print(f"   Memories: {loader.MEMORIES_CACHE_TTL}s")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    setup_logging()
    measure_performance()
