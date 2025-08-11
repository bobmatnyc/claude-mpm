#!/usr/bin/env python3
"""
Performance Testing for Session Logging System

Comprehensive performance tests to measure overhead, throughput,
and scalability of the session logging system.
"""

import os
import sys
import time
import statistics
import threading
import gc
from pathlib import Path
from datetime import datetime
import psutil
import json

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


def clear_session_env_vars():
    """Clear all session-related environment variables."""
    env_vars = ['CLAUDE_SESSION_ID', 'ANTHROPIC_SESSION_ID', 'SESSION_ID']
    for var in env_vars:
        if var in os.environ:
            del os.environ[var]


def reset_logger_singleton():
    """Reset the logger singleton."""
    import claude_mpm.services.claude_session_logger
    claude_mpm.services.claude_session_logger._logger_instance = None


def get_memory_usage():
    """Get current memory usage in MB."""
    process = psutil.Process()
    return process.memory_info().rss / 1024 / 1024


def test_logging_performance():
    """Test basic logging performance."""
    print("Testing Basic Logging Performance")
    print("-" * 50)
    
    clear_session_env_vars()
    test_session_id = f"perf_basic_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.environ['CLAUDE_SESSION_ID'] = test_session_id
    
    reset_logger_singleton()
    
    from claude_mpm.services.claude_session_logger import get_session_logger
    
    logger = get_session_logger()
    
    # Test different response sizes
    test_cases = [
        ("Small", "Short response." * 5),  # ~70 chars
        ("Medium", "Medium length response. " * 20),  # ~520 chars
        ("Large", "Large response content. " * 100),  # ~2400 chars
        ("Very Large", "Very large response content. " * 1000),  # ~26,000 chars
    ]
    
    results = {}
    
    for size_name, response_content in test_cases:
        times = []
        memory_before = get_memory_usage()
        
        # Run multiple iterations
        iterations = 10
        for i in range(iterations):
            start_time = time.time()
            
            response_path = logger.log_response(
                f"Performance test {size_name} - iteration {i+1}",
                response_content,
                {"test": "performance", "size": size_name, "iteration": i+1}
            )
            
            end_time = time.time()
            times.append(end_time - start_time)
            
            if not response_path:
                print(f"  ✗ Failed to log {size_name} response iteration {i+1}")
        
        memory_after = get_memory_usage()
        
        # Calculate statistics
        avg_time = statistics.mean(times)
        min_time = min(times)
        max_time = max(times)
        std_dev = statistics.stdev(times) if len(times) > 1 else 0
        
        results[size_name] = {
            'avg_time': avg_time,
            'min_time': min_time,
            'max_time': max_time,
            'std_dev': std_dev,
            'response_size': len(response_content),
            'memory_delta': memory_after - memory_before
        }
        
        print(f"{size_name} Response ({len(response_content):,} chars):")
        print(f"  Average time: {avg_time*1000:.2f} ms")
        print(f"  Min time: {min_time*1000:.2f} ms")
        print(f"  Max time: {max_time*1000:.2f} ms")
        print(f"  Std deviation: {std_dev*1000:.2f} ms")
        print(f"  Memory delta: {memory_after - memory_before:.2f} MB")
        print(f"  Throughput: {len(response_content)/avg_time/1024:.1f} KB/s")
        print()
    
    clear_session_env_vars()
    return results


def test_concurrent_performance():
    """Test performance under concurrent load."""
    print("Testing Concurrent Performance")
    print("-" * 50)
    
    clear_session_env_vars()
    test_session_id = f"perf_concurrent_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.environ['CLAUDE_SESSION_ID'] = test_session_id
    
    reset_logger_singleton()
    
    from claude_mpm.services.claude_session_logger import get_session_logger
    
    logger = get_session_logger()
    
    thread_counts = [1, 2, 4, 8, 16]
    response_content = "Concurrent performance test response. " * 50  # ~1900 chars
    
    results = {}
    
    for thread_count in thread_counts:
        print(f"Testing with {thread_count} threads...")
        
        times_per_thread = []
        errors_per_thread = []
        memory_before = get_memory_usage()
        
        def worker(thread_id, results_list, errors_list):
            """Worker function for each thread."""
            thread_times = []
            thread_errors = []
            
            iterations_per_thread = 10
            for i in range(iterations_per_thread):
                start_time = time.time()
                
                try:
                    response_path = logger.log_response(
                        f"Concurrent perf test - thread {thread_id}, iteration {i+1}",
                        response_content,
                        {"thread": thread_id, "iteration": i+1, "test": "concurrent_perf"}
                    )
                    
                    end_time = time.time()
                    thread_times.append(end_time - start_time)
                    
                    if not response_path:
                        thread_errors.append(f"Thread {thread_id}, iter {i+1}: Failed to log")
                
                except Exception as e:
                    thread_errors.append(f"Thread {thread_id}, iter {i+1}: {str(e)}")
            
            results_list.append(thread_times)
            errors_list.append(thread_errors)
        
        # Start threads
        threads = []
        start_time = time.time()
        
        for i in range(thread_count):
            thread = threading.Thread(
                target=worker,
                args=(i, times_per_thread, errors_per_thread)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        memory_after = get_memory_usage()
        
        # Analyze results
        all_times = [t for thread_times in times_per_thread for t in thread_times]
        all_errors = [e for thread_errors in errors_per_thread for e in thread_errors]
        
        if all_times:
            avg_time = statistics.mean(all_times)
            total_operations = len(all_times)
            throughput = total_operations / total_time  # ops/second
            
            results[thread_count] = {
                'avg_time': avg_time,
                'total_time': total_time,
                'total_operations': total_operations,
                'throughput': throughput,
                'errors': len(all_errors),
                'memory_delta': memory_after - memory_before
            }
            
            print(f"  Average response time: {avg_time*1000:.2f} ms")
            print(f"  Total time: {total_time:.2f} seconds")
            print(f"  Total operations: {total_operations}")
            print(f"  Throughput: {throughput:.1f} ops/second")
            print(f"  Errors: {len(all_errors)}")
            print(f"  Memory delta: {memory_after - memory_before:.2f} MB")
            
            if all_errors:
                print(f"  Sample errors: {all_errors[:3]}")
        else:
            print(f"  ✗ No successful operations")
        
        print()
    
    clear_session_env_vars()
    return results


def test_memory_usage_scaling():
    """Test memory usage as the number of logged responses increases."""
    print("Testing Memory Usage Scaling")
    print("-" * 50)
    
    clear_session_env_vars()
    test_session_id = f"perf_memory_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.environ['CLAUDE_SESSION_ID'] = test_session_id
    
    reset_logger_singleton()
    
    from claude_mpm.services.claude_session_logger import get_session_logger
    
    logger = get_session_logger()
    
    response_content = "Memory scaling test response. " * 100  # ~3000 chars
    memory_measurements = []
    
    # Test points: 0, 10, 50, 100, 200, 500 responses
    test_points = [0, 10, 50, 100, 200, 500]
    current_count = 0
    
    for target_count in test_points:
        # Log responses up to target count
        while current_count < target_count:
            logger.log_response(
                f"Memory scaling test - response {current_count + 1}",
                response_content,
                {"test": "memory_scaling", "response_number": current_count + 1}
            )
            current_count += 1
        
        # Force garbage collection and measure memory
        gc.collect()
        memory_usage = get_memory_usage()
        memory_measurements.append((target_count, memory_usage))
        
        print(f"Responses logged: {target_count:3d}, Memory usage: {memory_usage:.2f} MB")
    
    # Calculate memory growth rate
    if len(memory_measurements) >= 2:
        first_measurement = memory_measurements[1]  # Skip 0 responses
        last_measurement = memory_measurements[-1]
        
        response_increase = last_measurement[0] - first_measurement[0]
        memory_increase = last_measurement[1] - first_measurement[1]
        
        if response_increase > 0:
            memory_per_response = memory_increase / response_increase
            print(f"\nMemory growth rate: {memory_per_response:.4f} MB per response")
        else:
            print("\nCould not calculate memory growth rate")
    
    print()
    clear_session_env_vars()
    return memory_measurements


def test_hook_performance_overhead():
    """Test performance overhead of the hook system."""
    print("Testing Hook Performance Overhead")
    print("-" * 50)
    
    clear_session_env_vars()
    test_session_id = f"perf_hook_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.environ['CLAUDE_SESSION_ID'] = test_session_id
    
    reset_logger_singleton()
    
    from claude_mpm.hooks.builtin.session_response_logger_hook import SessionResponseLoggerHook
    
    # Test with hook disabled
    config_disabled = {
        'enabled': False,
        'log_all_agents': True,
        'min_response_length': 10
    }
    
    hook_disabled = SessionResponseLoggerHook(config_disabled)
    
    # Test with hook enabled
    config_enabled = {
        'enabled': True,
        'log_all_agents': True,
        'min_response_length': 10
    }
    
    hook_enabled = SessionResponseLoggerHook(config_enabled)
    
    # Create test event
    test_event = {
        'agent_name': 'performance_test_agent',
        'request': 'Performance test request for hook overhead measurement',
        'response': 'This is a performance test response to measure hook processing overhead. ' * 20,
        'model': 'claude-3',
        'tokens': 300,
        'tools_used': ['read', 'write']
    }
    
    iterations = 100
    
    # Test disabled hook performance
    print("Testing disabled hook performance...")
    disabled_times = []
    for i in range(iterations):
        start_time = time.time()
        result = hook_disabled.on_agent_response(test_event.copy())
        end_time = time.time()
        disabled_times.append(end_time - start_time)
    
    # Test enabled hook performance
    print("Testing enabled hook performance...")
    enabled_times = []
    for i in range(iterations):
        start_time = time.time()
        result = hook_enabled.on_agent_response(test_event.copy())
        end_time = time.time()
        enabled_times.append(end_time - start_time)
    
    # Calculate statistics
    disabled_avg = statistics.mean(disabled_times)
    enabled_avg = statistics.mean(enabled_times)
    overhead = enabled_avg - disabled_avg
    overhead_percent = (overhead / disabled_avg * 100) if disabled_avg > 0 else 0
    
    print(f"Disabled hook average: {disabled_avg*1000:.3f} ms")
    print(f"Enabled hook average:  {enabled_avg*1000:.3f} ms")
    print(f"Hook overhead:         {overhead*1000:.3f} ms")
    print(f"Overhead percentage:   {overhead_percent:.1f}%")
    
    # Check how many responses were actually logged
    session_dir = Path.cwd() / "docs" / "responses" / test_session_id
    if session_dir.exists():
        files = list(session_dir.glob("response_*.json"))
        print(f"Responses logged:      {len(files)}")
    else:
        print("No responses logged")
    
    print()
    clear_session_env_vars()
    
    return {
        'disabled_avg': disabled_avg,
        'enabled_avg': enabled_avg,
        'overhead': overhead,
        'overhead_percent': overhead_percent
    }


def test_file_system_performance():
    """Test file system performance characteristics."""
    print("Testing File System Performance")
    print("-" * 50)
    
    clear_session_env_vars()
    test_session_id = f"perf_fs_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.environ['CLAUDE_SESSION_ID'] = test_session_id
    
    reset_logger_singleton()
    
    from claude_mpm.services.claude_session_logger import get_session_logger
    
    logger = get_session_logger()
    
    # Test file sizes
    file_sizes = [
        ("1KB", "X" * 1024),
        ("10KB", "X" * 10240),
        ("100KB", "X" * 102400),
        ("1MB", "X" * 1048576),
    ]
    
    for size_name, content in file_sizes:
        print(f"Testing {size_name} files...")
        
        times = []
        for i in range(5):
            start_time = time.time()
            
            response_path = logger.log_response(
                f"File system performance test {size_name} - {i+1}",
                content,
                {"test": "filesystem", "size": size_name, "iteration": i+1}
            )
            
            end_time = time.time()
            times.append(end_time - start_time)
            
            if not response_path:
                print(f"  ✗ Failed to write {size_name} file")
        
        if times:
            avg_time = statistics.mean(times)
            file_size_bytes = len(content)
            throughput_mbps = (file_size_bytes / (1024 * 1024)) / avg_time
            
            print(f"  Average write time: {avg_time*1000:.2f} ms")
            print(f"  Write throughput: {throughput_mbps:.2f} MB/s")
    
    print()
    clear_session_env_vars()


def generate_performance_report(basic_results, concurrent_results, hook_results):
    """Generate a comprehensive performance report."""
    print("Performance Test Summary")
    print("=" * 70)
    
    print("\n1. Basic Logging Performance:")
    print("-" * 40)
    for size, metrics in basic_results.items():
        print(f"{size:12s}: {metrics['avg_time']*1000:6.2f} ms avg, "
              f"{metrics['response_size']/metrics['avg_time']/1024:6.1f} KB/s")
    
    print("\n2. Concurrent Performance:")
    print("-" * 40)
    for threads, metrics in concurrent_results.items():
        if 'throughput' in metrics:
            print(f"{threads:2d} threads: {metrics['throughput']:6.1f} ops/sec, "
                  f"{metrics['avg_time']*1000:6.2f} ms avg, "
                  f"{metrics['errors']:2d} errors")
    
    print("\n3. Hook System Overhead:")
    print("-" * 40)
    print(f"Processing overhead: {hook_results['overhead']*1000:.3f} ms")
    print(f"Overhead percentage: {hook_results['overhead_percent']:.1f}%")
    
    # Performance recommendations
    print("\n4. Performance Analysis:")
    print("-" * 40)
    
    # Check for any concerning metrics
    concerns = []
    recommendations = []
    
    # Basic logging performance analysis
    large_response_time = basic_results.get('Very Large', {}).get('avg_time', 0)
    if large_response_time > 0.1:  # More than 100ms
        concerns.append(f"Large responses take {large_response_time*1000:.0f}ms to log")
        recommendations.append("Consider async logging for large responses")
    
    # Concurrent performance analysis
    single_thread_throughput = concurrent_results.get(1, {}).get('throughput', 0)
    multi_thread_throughput = concurrent_results.get(16, {}).get('throughput', 0)
    
    if single_thread_throughput > 0 and multi_thread_throughput > 0:
        scaling_factor = multi_thread_throughput / single_thread_throughput
        if scaling_factor < 8:  # Poor scaling with 16 threads
            concerns.append(f"Poor concurrent scaling: {scaling_factor:.1f}x with 16 threads")
            recommendations.append("Check for synchronization bottlenecks")
    
    # Hook overhead analysis
    if hook_results['overhead_percent'] > 50:
        concerns.append(f"High hook overhead: {hook_results['overhead_percent']:.1f}%")
        recommendations.append("Optimize hook processing logic")
    
    if concerns:
        print("⚠️  Performance Concerns:")
        for concern in concerns:
            print(f"   • {concern}")
    else:
        print("✓ No significant performance concerns identified")
    
    if recommendations:
        print("\n💡 Recommendations:")
        for rec in recommendations:
            print(f"   • {rec}")
    
    print()


if __name__ == "__main__":
    print("Session Logging Performance Testing")
    print("=" * 70)
    
    # Run all performance tests
    basic_results = test_logging_performance()
    concurrent_results = test_concurrent_performance()
    memory_measurements = test_memory_usage_scaling()
    hook_results = test_hook_performance_overhead()
    test_file_system_performance()
    
    # Generate comprehensive report
    generate_performance_report(basic_results, concurrent_results, hook_results)
    
    print("Performance testing complete!")
    print("Review the results above for system characteristics and optimization opportunities.")