#!/usr/bin/env python3
"""Test script to measure hook performance improvements.

This script tests the performance of the new asynchronous hook system
compared to the old synchronous implementation.
"""

import os
import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.hook_manager import get_hook_manager
from claude_mpm.core.hook_performance_config import (
    get_hook_performance_config,
    set_performance_mode,
    ENVIRONMENT_VARIABLES
)


def test_hook_performance():
    """Test hook performance with different configurations."""
    print("🚀 Testing Hook Performance Improvements")
    print("=" * 50)
    
    # Test configurations
    test_configs = [
        ("Normal Mode", False),
        ("Performance Mode", True),
    ]
    
    for config_name, perf_mode in test_configs:
        print(f"\n📊 Testing {config_name}")
        print("-" * 30)
        
        # Set performance mode
        set_performance_mode(perf_mode)
        
        # Get fresh hook manager instance
        hook_manager = get_hook_manager()
        
        # Test multiple hook triggers
        num_hooks = 100
        start_time = time.time()
        
        for i in range(num_hooks):
            # Trigger different types of hooks
            hook_manager.trigger_pre_tool_hook("TestTool", {"test": f"data_{i}"})
            hook_manager.trigger_post_tool_hook("TestTool", 0, f"result_{i}")
            hook_manager.trigger_user_prompt_hook(f"test prompt {i}")
        
        end_time = time.time()
        total_time = end_time - start_time
        hooks_per_second = (num_hooks * 3) / total_time  # 3 hooks per iteration
        
        print(f"  Triggered {num_hooks * 3} hooks in {total_time:.4f} seconds")
        print(f"  Performance: {hooks_per_second:.2f} hooks/second")
        print(f"  Average time per hook: {(total_time / (num_hooks * 3)) * 1000:.2f} ms")
        
        # Show configuration
        config = get_hook_performance_config()
        print(f"  Performance Mode: {config.performance_mode}")
        print(f"  Queue Size: {config.queue_size}")
        
        # Cleanup
        hook_manager.shutdown()


def show_configuration_options():
    """Show available configuration options."""
    print("\n⚙️  Hook Performance Configuration Options")
    print("=" * 50)
    
    config = get_hook_performance_config()
    print(config.print_config())
    
    print("\n📝 Environment Variables:")
    for var, description in ENVIRONMENT_VARIABLES.items():
        current_value = os.getenv(var, "not set")
        print(f"  {var}={current_value}")
        print(f"    {description}")
        print()


def benchmark_old_vs_new():
    """Benchmark to show improvement over old synchronous approach."""
    print("\n⏱️  Performance Comparison")
    print("=" * 50)
    
    # Simulate old synchronous approach timing
    print("Old Synchronous Approach (simulated):")
    print("  - Each hook blocks for ~5 seconds (timeout)")
    print("  - 3 hooks per tool operation = 15 seconds blocking time")
    print("  - 100 tool operations = 1500 seconds = 25 minutes")
    
    print("\nNew Asynchronous Approach:")
    start_time = time.time()
    
    hook_manager = get_hook_manager()
    for i in range(100):
        hook_manager.trigger_pre_tool_hook("BenchmarkTool", {"iteration": i})
        hook_manager.trigger_post_tool_hook("BenchmarkTool", 0, f"result_{i}")
    
    end_time = time.time()
    async_time = end_time - start_time
    
    print(f"  - 200 hooks processed in {async_time:.4f} seconds")
    print(f"  - Improvement: {1500 / async_time:.0f}x faster")
    print(f"  - Overhead per hook: {(async_time / 200) * 1000:.2f} ms")
    
    hook_manager.shutdown()


def main():
    """Main test function."""
    print("🔧 Claude MPM Hook Performance Test")
    print("This script tests the new asynchronous hook processing system.")
    print()
    
    try:
        # Show current configuration
        show_configuration_options()
        
        # Run performance tests
        test_hook_performance()
        
        # Show benchmark comparison
        benchmark_old_vs_new()
        
        print("\n✅ Hook performance testing completed!")
        print("\nTo optimize performance further:")
        print("  - Set CLAUDE_MPM_PERFORMANCE_MODE=true to disable all hooks")
        print("  - Set specific hook types to false to disable selectively")
        print("  - Adjust CLAUDE_MPM_HOOK_QUEUE_SIZE for memory vs performance tradeoff")
        
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()