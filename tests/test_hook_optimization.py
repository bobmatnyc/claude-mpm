#!/usr/bin/env python3
"""

import pytest

# Skip entire module - optimized_hook_service module removed in refactoring
pytestmark = pytest.mark.skip(reason="optimized_hook_service module removed in refactoring")

Test hook system optimization and caching.
Validates hook loading, caching, and performance improvements.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# from claude_mpm.services.optimized_hook_service import HookConfig, OptimizedHookService


# Test content commented due to missing imports
'''
class TestPreHook(PreDelegationHook):
    """Test pre-delegation hook."""

    def __init__(self, delay: float = 0.0):
        super().__init__("test_pre_hook", priority=10)
        self.delay = delay
        self.execution_count = 0

    def validate(self, context: HookContext) -> bool:
        return True

    def execute(self, context: HookContext) -> HookResult:
        self.execution_count += 1
        if self.delay > 0:
            time.sleep(self.delay)

        # Modify context data
        modified_data = context.data.copy()
        modified_data["pre_hook_executed"] = True
        modified_data["pre_hook_execution_count"] = self.execution_count

        return HookResult(success=True, data=modified_data, modified=True)


class TestPostHook(PostDelegationHook):
    """Test post-delegation hook."""

    def __init__(self, delay: float = 0.0):
        super().__init__("test_post_hook", priority=90)
        self.delay = delay
        self.execution_count = 0

    def validate(self, context: HookContext) -> bool:
        return True

    def execute(self, context: HookContext) -> HookResult:
        self.execution_count += 1
        if self.delay > 0:
            time.sleep(self.delay)

        # Modify context data
        modified_data = context.data.copy()
        modified_data["post_hook_executed"] = True
        modified_data["post_hook_execution_count"] = self.execution_count

        return HookResult(success=True, data=modified_data, modified=True)


class ParallelSafeHook(PreDelegationHook):
    """Hook that can be executed in parallel."""

    def __init__(self):
        super().__init__("parallel_safe_hook", priority=20)
        self.parallel_safe = True
        self.execution_count = 0

    def validate(self, context: HookContext) -> bool:
        return True

    def execute(self, context: HookContext) -> HookResult:
        self.execution_count += 1

        # Simulate some work
        time.sleep(0.001)

        modified_data = context.data.copy()
        modified_data["parallel_hook_executed"] = True

        return HookResult(success=True, data=modified_data, modified=True)


def test_hook_service_singleton():
    """Test that hook service uses singleton pattern."""
    print("\n=== Testing Hook Service Singleton ===")

    # Create multiple instances
    service1 = OptimizedHookService()
    service2 = OptimizedHookService()
    service3 = OptimizedHookService()

    # They should all be the same instance
    same_instance = service1 is service2 is service3
    print(f"  ✓ Singleton pattern working: {same_instance}")

    return {"singleton_working": same_instance}


def test_hook_caching():
    """Test hook configuration caching and lazy loading."""
    print("\n=== Testing Hook Caching and Lazy Loading ===")

    # Create a fresh hook service instance
    OptimizedHookService._instance = None  # Reset singleton for testing

    # Create mock config with hooks
    mock_config = MagicMock()
    mock_config.get.side_effect = lambda key, default=None: {
        "hooks.registered": {
            "test_hook_1": {
                "module": "test_module.hooks",
                "class": "TestHook1",
                "priority": 10,
                "enabled": True,
                "type": "pre",
                "params": {"param1": "value1"},
            },
            "test_hook_2": {
                "module": "test_module.hooks",
                "class": "TestHook2",
                "priority": 20,
                "enabled": True,
                "type": "post",
                "params": {"param2": "value2"},
            },
        },
        "hooks.enabled": True,
        "hooks.max_workers": 4,
        "hooks.pre_delegation.enabled": True,
        "hooks.post_delegation.enabled": True,
    }.get(key, default)

    service = OptimizedHookService(mock_config)

    # Check that hooks were cached
    cached_hooks_count = len(service._hook_configs)
    pre_hooks_count = len(service._pre_hooks_cache)
    post_hooks_count = len(service._post_hooks_cache)

    print(f"  ✓ Cached hook configurations: {cached_hooks_count}")
    print(f"  ✓ Pre-hooks cached: {pre_hooks_count}")
    print(f"  ✓ Post-hooks cached: {post_hooks_count}")

    # Check that no instances are loaded yet (lazy loading)
    loaded_instances = sum(
        1
        for config in service._hook_configs.values()
        if config.loaded_instance is not None
    )
    print(f"  ✓ Lazy loading - instances not loaded yet: {loaded_instances == 0}")

    return {
        "cached_configs": cached_hooks_count,
        "pre_hooks_cached": pre_hooks_count,
        "post_hooks_cached": post_hooks_count,
        "lazy_loading_working": loaded_instances == 0,
    }


def test_hook_registration_and_execution():
    """Test hook registration and execution performance."""
    print("\n=== Testing Hook Registration and Execution ===")

    # Reset singleton for testing
    OptimizedHookService._instance = None

    service = OptimizedHookService()

    # Register test hooks
    pre_hook = TestPreHook(delay=0.001)  # Small delay to measure timing
    post_hook = TestPostHook(delay=0.001)
    parallel_hook = ParallelSafeHook()

    registration_start = time.perf_counter()

    service.register_hook(pre_hook)
    service.register_hook(post_hook)
    service.register_hook(parallel_hook)

    registration_time = time.perf_counter() - registration_start

    print(f"  ✓ Registered 3 hooks in {registration_time*1000:.3f} ms")

    # Test pre-delegation hooks execution
    from datetime import datetime

    context = HookContext(
        hook_type=HookType.PRE_DELEGATION,
        data={"initial_data": "test"},
        metadata={"test": True},
        timestamp=datetime.now(),
        session_id="test_session",
        user_id="test_user",
    )

    # Execute multiple times to test caching benefits
    execution_times = []

    for i in range(10):
        start_time = time.perf_counter()

        result = service.execute_pre_delegation_hooks(context)

        execution_time = time.perf_counter() - start_time
        execution_times.append(execution_time)

        # Verify result
        assert result.success, "Hook execution should succeed"
        assert result.modified, "Hooks should modify data"
        assert "pre_hook_executed" in result.data, "Pre-hook should have executed"
        assert (
            "parallel_hook_executed" in result.data
        ), "Parallel hook should have executed"

    avg_execution_time = sum(execution_times) / len(execution_times)
    min_execution_time = min(execution_times)
    max_execution_time = max(execution_times)

    print(f"  ✓ Average execution time: {avg_execution_time*1000:.3f} ms")
    print(f"  ✓ Min execution time: {min_execution_time*1000:.3f} ms")
    print(f"  ✓ Max execution time: {max_execution_time*1000:.3f} ms")
    print(f"  ✓ Pre-hook executed {pre_hook.execution_count} times")
    print(f"  ✓ Parallel hook executed {parallel_hook.execution_count} times")

    # Test post-delegation hooks
    post_context = HookContext(
        hook_type=HookType.POST_DELEGATION,
        data=result.data,
        metadata={"test": True},
        timestamp=datetime.now(),
        session_id="test_session",
        user_id="test_user",
    )

    post_result = service.execute_post_delegation_hooks(post_context)

    assert post_result.success, "Post-hook execution should succeed"
    assert "post_hook_executed" in post_result.data, "Post-hook should have executed"

    print(f"  ✓ Post-hook executed {post_hook.execution_count} times")

    return {
        "registration_time_ms": registration_time * 1000,
        "avg_execution_time_ms": avg_execution_time * 1000,
        "min_execution_time_ms": min_execution_time * 1000,
        "max_execution_time_ms": max_execution_time * 1000,
        "pre_hook_executions": pre_hook.execution_count,
        "post_hook_executions": post_hook.execution_count,
        "parallel_hook_executions": parallel_hook.execution_count,
    }


def test_hook_metrics():
    """Test hook performance metrics collection."""
    print("\n=== Testing Hook Metrics Collection ===")

    # Reset singleton
    OptimizedHookService._instance = None

    service = OptimizedHookService()

    # Register hooks with different performance characteristics
    fast_hook = TestPreHook(delay=0.001)  # 1ms delay
    slow_hook = TestPreHook(delay=0.010)  # 10ms delay
    fast_hook.name = "fast_hook"
    slow_hook.name = "slow_hook"

    service.register_hook(fast_hook)
    service.register_hook(slow_hook)

    # Execute hooks multiple times
    context = HookContext(
        hook_type=HookType.PRE_DELEGATION,
        data={"test": "data"},
        metadata={},
        timestamp=datetime.now(),
        session_id="test_session",
        user_id="test_user",
    )

    for i in range(5):
        service.execute_pre_delegation_hooks(context)

    # Get metrics
    metrics = service.get_metrics()

    print(f"  ✓ Collected metrics for {len(metrics)} hooks")

    for hook_name, hook_metrics in metrics.items():
        print(f"  ✓ {hook_name}:")
        print(f"    - Executions: {hook_metrics['execution_count']}")
        print(f"    - Avg time: {hook_metrics['avg_time_ms']:.3f} ms")
        print(f"    - Max time: {hook_metrics['max_time_ms']:.3f} ms")
        print(f"    - Min time: {hook_metrics['min_time_ms']:.3f} ms")
        print(f"    - Error count: {hook_metrics['error_count']}")
        print(f"    - Error rate: {hook_metrics['error_rate']:.1f}%")

    # Verify metrics make sense
    fast_hook_metrics = metrics.get("fast_hook", {})
    slow_hook_metrics = metrics.get("slow_hook", {})

    fast_avg_time = fast_hook_metrics.get("avg_time_ms", 0)
    slow_avg_time = slow_hook_metrics.get("avg_time_ms", 0)

    performance_difference_detected = slow_avg_time > fast_avg_time
    print(f"  ✓ Performance difference detected: {performance_difference_detected}")

    return {
        "metrics_collected": len(metrics) > 0,
        "fast_hook_avg_ms": fast_avg_time,
        "slow_hook_avg_ms": slow_avg_time,
        "performance_difference": performance_difference_detected,
        "total_hooks_tracked": len(metrics),
    }


def test_hook_listing_and_management():
    """Test hook listing and enable/disable functionality."""
    print("\n=== Testing Hook Management ===")

    # Reset singleton
    OptimizedHookService._instance = None

    service = OptimizedHookService()

    # Register some hooks
    hooks = [TestPreHook(), TestPostHook(), ParallelSafeHook()]

    for hook in hooks:
        service.register_hook(hook)

    # List hooks
    hook_list = service.list_hooks()

    print(f"  ✓ Pre-delegation hooks: {hook_list['pre_delegation']}")
    print(f"  ✓ Post-delegation hooks: {hook_list['post_delegation']}")
    print(f"  ✓ Available hooks: {hook_list['available']}")

    # Test enabling/disabling
    test_hook_name = hooks[0].name

    # Disable hook
    disable_success = service.disable_hook(test_hook_name)
    print(f"  ✓ Disabled hook '{test_hook_name}': {disable_success}")

    # Enable hook
    enable_success = service.enable_hook(test_hook_name)
    print(f"  ✓ Enabled hook '{test_hook_name}': {enable_success}")

    # Try to disable non-existent hook
    nonexistent_disable = service.disable_hook("nonexistent_hook")
    print(f"  ✓ Disable nonexistent hook (should fail): {not nonexistent_disable}")

    return {
        "pre_hooks_listed": len(hook_list["pre_delegation"]),
        "post_hooks_listed": len(hook_list["post_delegation"]),
        "available_hooks_listed": len(hook_list["available"]),
        "disable_success": disable_success,
        "enable_success": enable_success,
        "nonexistent_handling": not nonexistent_disable,
    }


def benchmark_hook_performance():
    """Benchmark hook performance improvements."""
    print("\n=== Hook Performance Benchmark ===")

    # Reset singleton
    OptimizedHookService._instance = None

    service = OptimizedHookService()

    # Register multiple hooks to simulate realistic load
    hooks = []
    for i in range(10):
        hook = TestPreHook(delay=0.0001)  # Very small delay
        hook.name = f"benchmark_hook_{i}"
        hooks.append(hook)
        service.register_hook(hook)

    context = HookContext(
        hook_type=HookType.PRE_DELEGATION,
        data={"benchmark": "test"},
        metadata={},
        timestamp=datetime.now(),
        session_id="benchmark_session",
        user_id="benchmark_user",
    )

    # Benchmark with different numbers of executions
    execution_counts = [10, 100, 1000]
    benchmark_results = {}

    for count in execution_counts:
        print(f"\n--- Benchmarking {count} executions ---")

        start_time = time.perf_counter()

        for i in range(count):
            result = service.execute_pre_delegation_hooks(context)
            assert result.success, f"Execution {i} should succeed"

        total_time = time.perf_counter() - start_time
        avg_time_per_execution = (total_time / count) * 1000  # ms
        throughput = count / total_time

        print(f"  ✓ Total time: {total_time:.3f} seconds")
        print(f"  ✓ Avg time per execution: {avg_time_per_execution:.3f} ms")
        print(f"  ✓ Throughput: {throughput:.1f} executions/sec")

        benchmark_results[count] = {
            "total_time": total_time,
            "avg_time_ms": avg_time_per_execution,
            "throughput": throughput,
        }

    return benchmark_results


def main():
    """Main test function."""
    print("🔧 HOOK SYSTEM OPTIMIZATION TEST SUITE")
    print("=" * 60)

    # Run tests
    singleton_result = test_hook_service_singleton()
    caching_result = test_hook_caching()
    execution_result = test_hook_registration_and_execution()
    metrics_result = test_hook_metrics()
    management_result = test_hook_listing_and_management()
    benchmark_results = benchmark_hook_performance()

    # Summary
    print("\n" + "=" * 60)
    print("HOOK SYSTEM OPTIMIZATION SUMMARY")
    print("=" * 60)

    print(f"🏗️ Singleton Pattern:")
    print(
        f"  ✓ Working correctly: {'✅' if singleton_result['singleton_working'] else '❌'}"
    )

    print(f"\n🗃️ Caching & Lazy Loading:")
    print(f"  ✓ Configurations cached: {caching_result['cached_configs']}")
    print(f"  ✓ Pre-hooks cached: {caching_result['pre_hooks_cached']}")
    print(f"  ✓ Post-hooks cached: {caching_result['post_hooks_cached']}")
    print(f"  ✓ Lazy loading: {'✅' if caching_result['lazy_loading_working'] else '❌'}")

    print(f"\n⚡ Execution Performance:")
    print(f"  ✓ Registration time: {execution_result['registration_time_ms']:.3f} ms")
    print(f"  ✓ Avg execution time: {execution_result['avg_execution_time_ms']:.3f} ms")
    print(f"  ✓ Min execution time: {execution_result['min_execution_time_ms']:.3f} ms")
    print(f"  ✓ Max execution time: {execution_result['max_execution_time_ms']:.3f} ms")

    print(f"\n📊 Metrics Collection:")
    print(
        f"  ✓ Metrics collected: {'✅' if metrics_result['metrics_collected'] else '❌'}"
    )
    print(
        f"  ✓ Performance tracking: {'✅' if metrics_result['performance_difference'] else '❌'}"
    )
    print(f"  ✓ Hooks tracked: {metrics_result['total_hooks_tracked']}")

    print(f"\n🎛️ Hook Management:")
    print(f"  ✓ Hooks listed: {management_result['available_hooks_listed']}")
    print(f"  ✓ Enable/disable: {'✅' if management_result['enable_success'] else '❌'}")
    print(
        f"  ✓ Error handling: {'✅' if management_result['nonexistent_handling'] else '❌'}"
    )

    print(f"\n🏃 Performance Benchmark:")
    for count, results in benchmark_results.items():
        print(
            f"  ✓ {count} executions: {results['throughput']:.1f} exec/sec, {results['avg_time_ms']:.3f}ms avg"
        )

    # Overall assessment
    core_tests_passed = all(
        [
            singleton_result["singleton_working"],
            caching_result["lazy_loading_working"],
            execution_result["avg_execution_time_ms"] < 50,  # Should be fast
            metrics_result["metrics_collected"],
            management_result["enable_success"],
        ]
    )

    if core_tests_passed:
        print("\n🎉 HOOK OPTIMIZATION TESTS PASSED!")
        print("✅ Singleton pattern implemented correctly")
        print("✅ Hook caching and lazy loading working")
        print("✅ Performance metrics collection active")
        print("✅ Hook management functionality operational")
        print("✅ Execution performance within expected ranges")
    else:
        print("\n⚠️ SOME HOOK OPTIMIZATION TESTS FAILED")
        print("❌ Review failed tests above for issues")

    return {
        "singleton": singleton_result,
        "caching": caching_result,
        "execution": execution_result,
        "metrics": metrics_result,
        "management": management_result,
        "benchmark": benchmark_results,
        "overall_success": core_tests_passed,
    }
'''

if __name__ == "__main__":
    main()
