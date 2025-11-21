#!/usr/bin/env python3
"""
Test the actual subagent load time with the optimized framework_loader.

This simulates what happens when Claude MPM loads a subagent with the new caching.
"""

import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_subagent_load():
    """Test the actual subagent loading process."""
    print("\n" + "=" * 80)
    print("SUBAGENT LOADING PERFORMANCE TEST")
    print("=" * 80)

    # Simulate multiple subagent loads
    print("\nSimulating 5 consecutive subagent loads...")

    load_times = []

    for i in range(5):
        print(f"\n--- Load #{i + 1} ---")

        # Import fresh each time to simulate new subagent
        if "claude_mpm.core.framework_loader" in sys.modules:
            del sys.modules["claude_mpm.core.framework_loader"]

        start_total = time.time()

        # Import and initialize (this is what happens for each subagent)
        from claude_mpm.core.framework_loader import FrameworkLoader

        loader = FrameworkLoader()

        # Simulate what happens during instruction preparation
        start_ops = time.time()

        # These are the expensive operations that happen during subagent load
        deployed = loader._get_deployed_agents()
        capabilities = loader._generate_agent_capabilities_section()

        content = {}
        loader._load_actual_memories(content)

        ops_time = time.time() - start_ops
        total_time = time.time() - start_total

        load_times.append(total_time)

        print(f"  Framework init + operations: {total_time:.3f}s")
        print(f"  Just operations: {ops_time:.3f}s")
        print(f"  Deployed agents: {len(deployed)}")
        print(f"  Capabilities size: {len(capabilities)} chars")
        print(f"  Memories loaded: {'actual_memories' in content}")

    # Calculate statistics
    avg_time = sum(load_times) / len(load_times)
    first_load = load_times[0]
    subsequent_avg = (
        sum(load_times[1:]) / len(load_times[1:]) if len(load_times) > 1 else 0
    )

    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)
    print(f"First load time: {first_load:.3f}s")
    print(f"Average subsequent loads: {subsequent_avg:.3f}s")
    print(f"Overall average: {avg_time:.3f}s")

    if avg_time < 5.0:
        print(
            f"\n✅ SUCCESS: Average subagent load time is {avg_time:.3f}s (target: <5s)"
        )
        improvement = 11.9 / avg_time
        print(
            f"   Estimated improvement: {improvement:.1f}x faster than original 11.9s"
        )
    else:
        print(f"\n⚠️  WARNING: Average load time {avg_time:.3f}s exceeds 5s target")

    # Test with pre-warmed cache
    print("\n" + "=" * 80)
    print("PRE-WARMED CACHE TEST")
    print("=" * 80)

    # Keep the same loader instance (simulating cached framework)
    print("\nUsing same loader instance (simulating framework cache)...")

    for i in range(3):
        start = time.time()

        # Just the operations that would happen with cached framework
        deployed = loader._get_deployed_agents()
        capabilities = loader._generate_agent_capabilities_section()
        content = {}
        loader._load_actual_memories(content)

        elapsed = time.time() - start
        print(f"  Load #{i + 1} with warm cache: {elapsed:.3f}s")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    test_subagent_load()
