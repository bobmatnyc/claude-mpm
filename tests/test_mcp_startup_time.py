#!/usr/bin/env python3
"""
Test script to measure MCP startup time improvements.

WHY: This script verifies that the MCP service optimizations have reduced
the agent startup delay from 11.9 seconds to under 1 second.

USAGE:
    python scripts/test_mcp_startup_time.py
"""

import asyncio
import subprocess
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from claude_mpm.services.mcp_gateway.core.process_pool import (
    get_process_pool,
    pre_warm_mcp_servers,
)


def measure_cold_start():
    """Measure cold start time (without pre-warming)."""
    print("\n🧊 Testing COLD START (no pre-warming)...")

    # Clean up any existing processes first
    subprocess.run(
        [sys.executable, "scripts/cleanup_mcp_processes.py"],
        capture_output=True,
        cwd=project_root,
        check=False,
    )

    start_time = time.time()

    # Simulate agent invocation that triggers MCP
    cmd = [sys.executable, "-m", "claude_mpm", "run", "engineer", "--help"]
    subprocess.run(cmd, capture_output=True, text=True, cwd=project_root, check=False)

    cold_start_time = time.time() - start_time

    print(f"  Cold start time: {cold_start_time:.2f} seconds")

    return cold_start_time


def measure_warm_start():
    """Measure warm start time (with pre-warming)."""
    print("\n🔥 Testing WARM START (with pre-warming)...")

    # Clean up any existing processes first
    subprocess.run(
        [sys.executable, "scripts/cleanup_mcp_processes.py"],
        capture_output=True,
        cwd=project_root,
        check=False,
    )

    # Pre-warm MCP services
    print("  Pre-warming MCP services...")
    pre_warm_start = time.time()

    async def pre_warm():
        await pre_warm_mcp_servers()

    asyncio.run(pre_warm())
    pre_warm_time = time.time() - pre_warm_start
    print(f"  Pre-warming completed in {pre_warm_time:.2f} seconds")

    # Now measure agent startup
    start_time = time.time()

    # Simulate agent invocation
    cmd = [sys.executable, "-m", "claude_mpm", "run", "engineer", "--help"]
    subprocess.run(cmd, capture_output=True, text=True, cwd=project_root, check=False)

    warm_start_time = time.time() - start_time

    print(f"  Warm start time: {warm_start_time:.2f} seconds")

    return warm_start_time, pre_warm_time


def measure_process_pool_efficiency():
    """Measure process pool efficiency."""
    print("\n♻️  Testing PROCESS POOL efficiency...")

    pool = get_process_pool()

    # Simulate multiple agent invocations
    times = []
    for i in range(3):
        print(f"  Invocation {i + 1}/3...")
        start_time = time.time()

        # Simulate agent invocation
        cmd = [sys.executable, "-m", "claude_mpm", "run", "engineer", "--help"]
        subprocess.run(
            cmd, capture_output=True, text=True, cwd=project_root, check=False
        )

        invocation_time = time.time() - start_time
        times.append(invocation_time)
        print(f"    Time: {invocation_time:.2f} seconds")

    avg_time = sum(times) / len(times)
    print(f"  Average time: {avg_time:.2f} seconds")

    # Get pool status
    status = pool.get_pool_status()
    print("\n  Process pool status:")
    print(f"    Active processes: {status['active_processes']}")
    print(f"    Pre-warmed: {status['pre_warmed']}")

    return avg_time


def check_memory_usage():
    """Check current memory usage of MCP processes."""
    print("\n💾 Checking memory usage...")

    result = subprocess.run(["ps", "aux"], capture_output=True, text=True, check=True)

    total_memory = 0
    mcp_count = 0

    for line in result.stdout.splitlines():
        if (
            any(keyword in line.lower() for keyword in ["mcp", "vector_search"])
            and "grep" not in line
        ):
            parts = line.split(None, 10)
            if len(parts) >= 6:
                try:
                    rss = int(parts[5])  # RSS in KB
                    rss_mb = rss / 1024
                    total_memory += rss_mb
                    mcp_count += 1
                except:
                    pass

    print(f"  MCP processes: {mcp_count}")
    print(f"  Total memory: {total_memory:.1f} MB")

    return mcp_count, total_memory


def main():
    """Main test function."""
    print("=" * 60)
    print("🚀 MCP Startup Time Performance Test")
    print("=" * 60)

    print("\nTarget: Reduce agent startup from 11.9s to <1s")
    print("Strategy: Process pooling, pre-warming, and singleton management")

    # Check initial state
    initial_processes, initial_memory = check_memory_usage()

    # Test cold start
    cold_time = measure_cold_start()

    # Test warm start
    warm_time, pre_warm_duration = measure_warm_start()

    # Test process pool efficiency
    avg_time = measure_process_pool_efficiency()

    # Check final state
    final_processes, final_memory = check_memory_usage()

    # Results summary
    print("\n" + "=" * 60)
    print("📊 PERFORMANCE RESULTS")
    print("=" * 60)

    print(f"\n🧊 Cold Start: {cold_time:.2f}s")
    print(f"🔥 Warm Start: {warm_time:.2f}s (after {pre_warm_duration:.2f}s pre-warm)")
    print(f"♻️  Pooled Average: {avg_time:.2f}s")

    print("\n💾 Memory Usage:")
    print(f"  Initial: {initial_processes} processes, {initial_memory:.1f} MB")
    print(f"  Final: {final_processes} processes, {final_memory:.1f} MB")

    # Calculate improvements
    original_time = 11.9  # Original startup time
    improvement_cold = ((original_time - cold_time) / original_time) * 100
    improvement_warm = ((original_time - warm_time) / original_time) * 100
    improvement_pooled = ((original_time - avg_time) / original_time) * 100

    print("\n📈 Improvements vs Original (11.9s):")
    print(f"  Cold Start: {improvement_cold:.1f}% faster")
    print(f"  Warm Start: {improvement_warm:.1f}% faster")
    print(f"  Pooled: {improvement_pooled:.1f}% faster")

    # Success criteria
    print("\n" + "=" * 60)
    if warm_time < 1.0 and avg_time < 1.0:
        print("✅ SUCCESS: Agent startup reduced to <1 second!")
    elif warm_time < 2.0 and avg_time < 2.0:
        print("⚠️  PARTIAL SUCCESS: Significant improvement but not yet <1s")
    else:
        print("❌ NEEDS MORE WORK: Startup time still above target")

    print("=" * 60)

    return 0 if warm_time < 1.0 else 1


if __name__ == "__main__":
    sys.exit(main())
