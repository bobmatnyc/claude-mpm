#!/usr/bin/env python3
"""
Cache Performance Benchmark
===========================

Comprehensive benchmark for validating cache effectiveness and performance:
- SharedPromptCache hit rates and performance
- File operation caching improvements
- Memory usage optimization
- Cache eviction and TTL behavior

Target: 50% reduction in file operations through caching
"""

import argparse
import asyncio
import json
import logging
import random
import statistics
import string
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Add claude-mpm to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

try:
    from claude_mpm.services.memory.cache.shared_prompt_cache import SharedPromptCache

    CLAUDE_MPM_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import claude-mpm modules: {e}")
    CLAUDE_MPM_AVAILABLE = False


@dataclass
class CacheTestResult:
    """Result of a cache performance test."""

    test_name: str
    operation_count: int
    duration_seconds: float
    hit_rate_percent: float
    miss_rate_percent: float
    operations_per_second: float
    memory_usage_mb: float
    cache_size_entries: int
    success: bool
    error_message: Optional[str] = None
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat() + "Z"


class CacheBenchmark:
    """Comprehensive cache performance benchmark."""

    def __init__(self):
        self.logger = self._setup_logging()
        self.project_root = Path(__file__).parent.parent.parent

        # Test data generation
        self.test_data_sizes = [100, 1000, 10000]  # bytes
        self.test_patterns = ["sequential", "random", "mixed"]

    def _setup_logging(self) -> logging.Logger:
        """Setup logging for cache benchmarks."""
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
        )
        return logging.getLogger("cache_benchmark")

    def generate_test_data(self, size_bytes: int) -> str:
        """Generate test data of specified size."""
        return "".join(
            random.choices(string.ascii_letters + string.digits, k=size_bytes)
        )

    async def test_cache_basic_operations(
        self, cache: SharedPromptCache, operations: int = 1000
    ) -> CacheTestResult:
        """Test basic cache operations (set/get)."""
        self.logger.info(f"🔧 Testing basic cache operations ({operations} ops)...")

        start_time = time.time()
        hits = 0
        misses = 0
        errors = 0

        try:
            # Phase 1: Set operations (populate cache)
            set_count = operations // 2
            for i in range(set_count):
                key = f"test_basic_{i}"
                value = {"id": i, "data": self.generate_test_data(1000)}

                success = cache.set(key, value, ttl=300)
                if not success:
                    errors += 1

            # Phase 2: Get operations (test retrieval)
            get_count = operations - set_count
            for i in range(get_count):
                key = f"test_basic_{i % set_count}"  # Mix hits and misses

                result = cache.get(key)
                if result is not None:
                    hits += 1
                else:
                    misses += 1

            end_time = time.time()
            duration = end_time - start_time

            # Get cache metrics
            metrics = cache.get_metrics()

            return CacheTestResult(
                test_name="Basic Operations",
                operation_count=operations,
                duration_seconds=duration,
                hit_rate_percent=metrics.get("hit_rate", 0.0) * 100,
                miss_rate_percent=metrics.get("miss_rate", 0.0) * 100,
                operations_per_second=operations / duration if duration > 0 else 0,
                memory_usage_mb=metrics.get("size_mb", 0.0),
                cache_size_entries=metrics.get("entry_count", 0),
                success=errors == 0,
            )

        except Exception as e:
            self.logger.error(f"Basic operations test failed: {e}")
            return CacheTestResult(
                test_name="Basic Operations",
                operation_count=operations,
                duration_seconds=time.time() - start_time,
                hit_rate_percent=0.0,
                miss_rate_percent=100.0,
                operations_per_second=0.0,
                memory_usage_mb=0.0,
                cache_size_entries=0,
                success=False,
                error_message=str(e),
            )

    async def test_cache_hit_rate_patterns(
        self, cache: SharedPromptCache, pattern: str = "mixed", operations: int = 1000
    ) -> CacheTestResult:
        """Test cache hit rates with different access patterns."""
        self.logger.info(
            f"📊 Testing cache hit rates with {pattern} pattern ({operations} ops)..."
        )

        start_time = time.time()

        try:
            # Populate cache with initial data
            cache_size = min(operations // 4, 250)  # Quarter of operations or 250 max

            for i in range(cache_size):
                key = f"pattern_{pattern}_{i}"
                value = {
                    "pattern": pattern,
                    "id": i,
                    "data": self.generate_test_data(500),
                }
                cache.set(key, value, ttl=600)

            # Test different access patterns
            if pattern == "sequential":
                # Sequential access - high hit rate expected
                keys = [
                    f"pattern_{pattern}_{i % cache_size}" for i in range(operations)
                ]

            elif pattern == "random":
                # Random access - mixed hit/miss rate
                keys = [
                    f"pattern_{pattern}_{random.randint(0, cache_size * 2)}"
                    for _ in range(operations)
                ]

            elif pattern == "mixed":
                # Mixed pattern - 70% hits, 30% misses
                hit_keys = [
                    f"pattern_{pattern}_{i % cache_size}"
                    for i in range(operations * 7 // 10)
                ]
                miss_keys = [
                    f"pattern_{pattern}_miss_{i}" for i in range(operations * 3 // 10)
                ]
                keys = hit_keys + miss_keys
                random.shuffle(keys)

            else:
                keys = [f"pattern_{pattern}_{i}" for i in range(operations)]

            # Perform access operations
            hits = 0
            misses = 0

            for key in keys:
                result = cache.get(key)
                if result is not None:
                    hits += 1
                else:
                    misses += 1

            end_time = time.time()
            duration = end_time - start_time

            # Calculate metrics
            hit_rate = (hits / operations * 100) if operations > 0 else 0
            miss_rate = (misses / operations * 100) if operations > 0 else 0

            cache_metrics = cache.get_metrics()

            return CacheTestResult(
                test_name=f"Hit Rate Pattern ({pattern})",
                operation_count=operations,
                duration_seconds=duration,
                hit_rate_percent=hit_rate,
                miss_rate_percent=miss_rate,
                operations_per_second=operations / duration if duration > 0 else 0,
                memory_usage_mb=cache_metrics.get("size_mb", 0.0),
                cache_size_entries=cache_metrics.get("entry_count", 0),
                success=True,
            )

        except Exception as e:
            self.logger.error(f"Hit rate pattern test ({pattern}) failed: {e}")
            return CacheTestResult(
                test_name=f"Hit Rate Pattern ({pattern})",
                operation_count=operations,
                duration_seconds=time.time() - start_time,
                hit_rate_percent=0.0,
                miss_rate_percent=100.0,
                operations_per_second=0.0,
                memory_usage_mb=0.0,
                cache_size_entries=0,
                success=False,
                error_message=str(e),
            )

    async def test_cache_concurrency(
        self,
        cache: SharedPromptCache,
        concurrent_workers: int = 10,
        operations_per_worker: int = 100,
    ) -> CacheTestResult:
        """Test cache performance under concurrent load."""
        self.logger.info(
            f"⚡ Testing cache concurrency ({concurrent_workers} workers, {operations_per_worker} ops each)..."
        )

        start_time = time.time()
        total_operations = concurrent_workers * operations_per_worker

        async def worker_task(worker_id: int):
            """Worker task for concurrent operations."""
            worker_hits = 0
            worker_misses = 0

            # Each worker operates on its own key space but with some overlap
            for i in range(operations_per_worker):
                # 50% chance to use shared keys (for cache hits)
                if random.random() < 0.5:
                    key = f"shared_key_{i % 50}"
                else:
                    key = f"worker_{worker_id}_key_{i}"

                # Mix of set and get operations
                if random.random() < 0.3:  # 30% set operations
                    value = {
                        "worker": worker_id,
                        "iteration": i,
                        "data": self.generate_test_data(200),
                    }
                    cache.set(key, value, ttl=300)
                else:  # 70% get operations
                    result = cache.get(key)
                    if result is not None:
                        worker_hits += 1
                    else:
                        worker_misses += 1

            return worker_hits, worker_misses

        try:
            # Run concurrent workers
            tasks = [worker_task(i) for i in range(concurrent_workers)]
            results = await asyncio.gather(*tasks)

            end_time = time.time()
            duration = end_time - start_time

            # Aggregate results
            total_hits = sum(r[0] for r in results)
            total_misses = sum(r[1] for r in results)
            total_gets = total_hits + total_misses

            hit_rate = (total_hits / total_gets * 100) if total_gets > 0 else 0
            miss_rate = (total_misses / total_gets * 100) if total_gets > 0 else 0

            cache_metrics = cache.get_metrics()

            return CacheTestResult(
                test_name="Concurrency Test",
                operation_count=total_operations,
                duration_seconds=duration,
                hit_rate_percent=hit_rate,
                miss_rate_percent=miss_rate,
                operations_per_second=(
                    total_operations / duration if duration > 0 else 0
                ),
                memory_usage_mb=cache_metrics.get("size_mb", 0.0),
                cache_size_entries=cache_metrics.get("entry_count", 0),
                success=True,
            )

        except Exception as e:
            self.logger.error(f"Concurrency test failed: {e}")
            return CacheTestResult(
                test_name="Concurrency Test",
                operation_count=total_operations,
                duration_seconds=time.time() - start_time,
                hit_rate_percent=0.0,
                miss_rate_percent=100.0,
                operations_per_second=0.0,
                memory_usage_mb=0.0,
                cache_size_entries=0,
                success=False,
                error_message=str(e),
            )

    async def test_cache_memory_efficiency(
        self, cache: SharedPromptCache
    ) -> CacheTestResult:
        """Test cache memory usage and efficiency."""
        self.logger.info("💾 Testing cache memory efficiency...")

        start_time = time.time()

        try:
            initial_metrics = cache.get_metrics()
            initial_memory = initial_metrics.get("size_mb", 0.0)

            # Add progressively larger data to test memory management
            data_sizes = [100, 500, 1000, 5000, 10000]  # bytes
            entries_per_size = 50
            total_operations = len(data_sizes) * entries_per_size

            for size in data_sizes:
                for i in range(entries_per_size):
                    key = f"memory_test_{size}_{i}"
                    value = {
                        "size": size,
                        "data": self.generate_test_data(size),
                        "metadata": {"created": time.time()},
                    }
                    cache.set(key, value, ttl=300)

            # Test retrieval to ensure data is accessible
            retrieved_count = 0
            for size in data_sizes:
                for i in range(min(10, entries_per_size)):  # Sample 10 entries per size
                    key = f"memory_test_{size}_{i}"
                    result = cache.get(key)
                    if result is not None:
                        retrieved_count += 1

            end_time = time.time()
            duration = end_time - start_time

            final_metrics = cache.get_metrics()
            final_memory = final_metrics.get("size_mb", 0.0)
            memory_growth = final_memory - initial_memory

            # Calculate efficiency metrics
            expected_size_mb = sum(size * entries_per_size for size in data_sizes) / (
                1024 * 1024
            )
            memory_efficiency = (
                (expected_size_mb / memory_growth * 100) if memory_growth > 0 else 0
            )

            return CacheTestResult(
                test_name="Memory Efficiency",
                operation_count=total_operations,
                duration_seconds=duration,
                hit_rate_percent=(retrieved_count / (len(data_sizes) * 10) * 100),
                miss_rate_percent=100
                - (retrieved_count / (len(data_sizes) * 10) * 100),
                operations_per_second=(
                    total_operations / duration if duration > 0 else 0
                ),
                memory_usage_mb=memory_growth,
                cache_size_entries=final_metrics.get("entry_count", 0),
                success=True,
            )

        except Exception as e:
            self.logger.error(f"Memory efficiency test failed: {e}")
            return CacheTestResult(
                test_name="Memory Efficiency",
                operation_count=0,
                duration_seconds=time.time() - start_time,
                hit_rate_percent=0.0,
                miss_rate_percent=100.0,
                operations_per_second=0.0,
                memory_usage_mb=0.0,
                cache_size_entries=0,
                success=False,
                error_message=str(e),
            )

    async def test_cache_ttl_behavior(
        self, cache: SharedPromptCache
    ) -> CacheTestResult:
        """Test cache TTL (Time To Live) behavior."""
        self.logger.info("⏰ Testing cache TTL behavior...")

        start_time = time.time()

        try:
            # Set entries with different TTL values
            ttl_values = [1, 3, 5]  # seconds
            entries_per_ttl = 20
            total_operations = len(ttl_values) * entries_per_ttl

            # Phase 1: Set entries with TTL
            for ttl in ttl_values:
                for i in range(entries_per_ttl):
                    key = f"ttl_test_{ttl}_{i}"
                    value = {
                        "ttl": ttl,
                        "created": time.time(),
                        "data": self.generate_test_data(100),
                    }
                    cache.set(key, value, ttl=ttl)

            # Phase 2: Test immediate retrieval (should all be hits)
            immediate_hits = 0
            for ttl in ttl_values:
                for i in range(entries_per_ttl):
                    key = f"ttl_test_{ttl}_{i}"
                    result = cache.get(key)
                    if result is not None:
                        immediate_hits += 1

            # Phase 3: Wait for some TTL expiration
            await asyncio.sleep(2)

            # Phase 4: Test after partial expiration
            partial_hits = 0
            for ttl in ttl_values:
                for i in range(entries_per_ttl):
                    key = f"ttl_test_{ttl}_{i}"
                    result = cache.get(key)
                    if result is not None:
                        partial_hits += 1

            # Phase 5: Wait for all TTL expiration
            await asyncio.sleep(4)

            # Phase 6: Test after full expiration
            final_hits = 0
            for ttl in ttl_values:
                for i in range(entries_per_ttl):
                    key = f"ttl_test_{ttl}_{i}"
                    result = cache.get(key)
                    if result is not None:
                        final_hits += 1

            end_time = time.time()
            duration = end_time - start_time

            # Calculate TTL effectiveness
            immediate_rate = (
                (immediate_hits / total_operations * 100) if total_operations > 0 else 0
            )
            partial_rate = (
                (partial_hits / total_operations * 100) if total_operations > 0 else 0
            )
            final_rate = (
                (final_hits / total_operations * 100) if total_operations > 0 else 0
            )

            cache_metrics = cache.get_metrics()

            # TTL is working if we see decreasing hit rates over time
            ttl_working = immediate_rate > partial_rate >= final_rate

            return CacheTestResult(
                test_name="TTL Behavior",
                operation_count=total_operations,
                duration_seconds=duration,
                hit_rate_percent=final_rate,  # Final hit rate after all should expire
                miss_rate_percent=100 - final_rate,
                operations_per_second=(
                    total_operations / duration if duration > 0 else 0
                ),
                memory_usage_mb=cache_metrics.get("size_mb", 0.0),
                cache_size_entries=cache_metrics.get("entry_count", 0),
                success=ttl_working,
            )

        except Exception as e:
            self.logger.error(f"TTL behavior test failed: {e}")
            return CacheTestResult(
                test_name="TTL Behavior",
                operation_count=0,
                duration_seconds=time.time() - start_time,
                hit_rate_percent=0.0,
                miss_rate_percent=100.0,
                operations_per_second=0.0,
                memory_usage_mb=0.0,
                cache_size_entries=0,
                success=False,
                error_message=str(e),
            )

    async def run_comprehensive_cache_benchmark(self) -> Dict[str, Any]:
        """Run comprehensive cache benchmark suite."""
        self.logger.info("🎯 Starting comprehensive cache benchmark...")

        if not CLAUDE_MPM_AVAILABLE:
            raise RuntimeError("Claude MPM modules not available")

        start_time = time.time()

        # Initialize cache
        cache = SharedPromptCache.get_instance(
            {
                "max_size": 1000,
                "max_memory_mb": 100,
                "default_ttl": 300,
                "cleanup_interval": 30,
            }
        )

        await cache.start()

        try:
            results = []

            # Run all test categories
            test_methods = [
                (self.test_cache_basic_operations, {"operations": 1000}),
                (
                    self.test_cache_hit_rate_patterns,
                    {"pattern": "sequential", "operations": 500},
                ),
                (
                    self.test_cache_hit_rate_patterns,
                    {"pattern": "random", "operations": 500},
                ),
                (
                    self.test_cache_hit_rate_patterns,
                    {"pattern": "mixed", "operations": 500},
                ),
                (
                    self.test_cache_concurrency,
                    {"concurrent_workers": 5, "operations_per_worker": 50},
                ),
                (self.test_cache_memory_efficiency, {}),
                (self.test_cache_ttl_behavior, {}),
            ]

            for test_method, kwargs in test_methods:
                try:
                    self.logger.info(f"Running {test_method.__name__}...")
                    result = await test_method(cache, **kwargs)
                    results.append(result)

                    # Clear cache between tests to avoid interference
                    cache.clear()

                except Exception as e:
                    self.logger.error(f"Test {test_method.__name__} failed: {e}")
                    # Add failed result
                    failed_result = CacheTestResult(
                        test_name=test_method.__name__,
                        operation_count=0,
                        duration_seconds=0.0,
                        hit_rate_percent=0.0,
                        miss_rate_percent=100.0,
                        operations_per_second=0.0,
                        memory_usage_mb=0.0,
                        cache_size_entries=0,
                        success=False,
                        error_message=str(e),
                    )
                    results.append(failed_result)

            execution_time = time.time() - start_time

            # Analyze results
            successful_results = [r for r in results if r.success]
            failed_results = [r for r in results if not r.success]

            # Calculate aggregate metrics
            if successful_results:
                avg_hit_rate = statistics.mean(
                    [r.hit_rate_percent for r in successful_results]
                )
                avg_ops_per_sec = statistics.mean(
                    [r.operations_per_second for r in successful_results]
                )
                total_operations = sum([r.operation_count for r in successful_results])
            else:
                avg_hit_rate = 0.0
                avg_ops_per_sec = 0.0
                total_operations = 0

            # Check if performance targets are met
            target_hit_rate = 50.0  # Target 50% improvement in cache effectiveness
            meets_target = avg_hit_rate >= target_hit_rate

            benchmark_results = {
                "benchmark_metadata": {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "execution_time": execution_time,
                    "total_tests": len(results),
                    "successful_tests": len(successful_results),
                    "failed_tests": len(failed_results),
                    "target_hit_rate": target_hit_rate,
                    "meets_target": meets_target,
                },
                "aggregate_metrics": {
                    "average_hit_rate_percent": avg_hit_rate,
                    "average_operations_per_second": avg_ops_per_sec,
                    "total_operations": total_operations,
                    "cache_effectiveness_score": min(
                        100, avg_hit_rate * 2
                    ),  # Score out of 100
                },
                "test_results": [asdict(r) for r in results],
                "failed_tests": [
                    {
                        "test_name": r.test_name,
                        "error": r.error_message,
                        "timestamp": r.timestamp,
                    }
                    for r in failed_results
                ],
            }

            self.logger.info(f"📊 Cache benchmark completed in {execution_time:.2f}s")

            return benchmark_results

        finally:
            await cache.stop()

    def save_results(
        self, results: Dict[str, Any], output_file: Optional[Path] = None
    ) -> Path:
        """Save benchmark results to JSON file."""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = Path(__file__).parent / f"cache_benchmark_{timestamp}.json"

        with open(output_file, "w") as f:
            json.dump(results, f, indent=2, default=str)

        self.logger.info(f"📁 Results saved to: {output_file}")
        return output_file

    def print_summary(self, results: Dict[str, Any]):
        """Print benchmark summary."""
        metadata = results.get("benchmark_metadata", {})
        metrics = results.get("aggregate_metrics", {})

        print(f"\n{'='*60}")
        print("💾 CACHE PERFORMANCE BENCHMARK RESULTS")
        print(f"{'='*60}")
        print(f"Timestamp: {metadata.get('timestamp', 'Unknown')}")
        print(f"Total Tests: {metadata.get('total_tests', 0)}")
        print(f"Successful: {metadata.get('successful_tests', 0)}")
        print(f"Failed: {metadata.get('failed_tests', 0)}")
        print(f"Execution Time: {metadata.get('execution_time', 0):.2f}s")

        print("\n📊 AGGREGATE METRICS:")
        print(f"{'='*60}")
        print(
            f"Average Hit Rate:        {metrics.get('average_hit_rate_percent', 0):.1f}%"
        )
        print(
            f"Average Ops/Sec:         {metrics.get('average_operations_per_second', 0):.0f}"
        )
        print(f"Total Operations:        {metrics.get('total_operations', 0):,}")
        print(
            f"Cache Effectiveness:     {metrics.get('cache_effectiveness_score', 0):.1f}/100"
        )

        target_hit_rate = metadata.get("target_hit_rate", 50.0)
        meets_target = metadata.get("meets_target", False)
        print("\n🎯 TARGET VALIDATION:")
        print(f"{'='*60}")
        print(f"Target Hit Rate:         {target_hit_rate:.1f}%")
        print(
            f"Actual Hit Rate:         {metrics.get('average_hit_rate_percent', 0):.1f}%"
        )
        print(f"Target Met:              {'✅ YES' if meets_target else '❌ NO'}")

        # Individual test results
        print("\n📋 INDIVIDUAL TEST RESULTS:")
        print(f"{'='*60}")
        for result in results.get("test_results", []):
            status = "✅" if result["success"] else "❌"
            hit_rate = result["hit_rate_percent"]
            ops_per_sec = result["operations_per_second"]
            print(
                f"{result['test_name']:25} {status} {hit_rate:6.1f}% hit rate, {ops_per_sec:6.0f} ops/s"
            )


async def main():
    """Main entry point for cache benchmark."""
    parser = argparse.ArgumentParser(
        description="Claude MPM Cache Performance Benchmark"
    )

    parser.add_argument(
        "--output", "-o", type=Path, help="Output file for results (JSON)"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    benchmark = CacheBenchmark()

    # Run comprehensive benchmark
    results = await benchmark.run_comprehensive_cache_benchmark()

    # Save results
    output_file = benchmark.save_results(results, args.output)

    # Print summary
    benchmark.print_summary(results)

    # Return exit code based on target achievement
    meets_target = results.get("benchmark_metadata", {}).get("meets_target", False)
    return 0 if meets_target else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
