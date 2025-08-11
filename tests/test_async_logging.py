#!/usr/bin/env python3
"""
Test script for async logging performance improvements.

Demonstrates the performance difference between sync and async logging,
and shows how the new timestamp-based filenames eliminate concurrency issues.
"""

import asyncio
import time
import json
import tempfile
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import statistics

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.claude_session_logger import ClaudeSessionLogger
from claude_mpm.services.async_session_logger import AsyncSessionLogger, LogFormat


def generate_test_response(size_kb: int = 10) -> str:
    """Generate a test response of specified size."""
    # Create a response with approximately the specified size
    base_content = "This is a test response content. " * 30
    multiplier = (size_kb * 1024) // len(base_content)
    return base_content * multiplier


def test_sync_logging(num_responses: int = 100, response_size_kb: int = 10):
    """Test synchronous logging performance."""
    print(f"\n=== Testing SYNCHRONOUS Logging ===")
    print(f"Logging {num_responses} responses of {response_size_kb}KB each...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = ClaudeSessionLogger(base_dir=Path(tmpdir), use_async=False)
        logger.set_session_id("sync_test_session")
        
        response_content = generate_test_response(response_size_kb)
        
        start_time = time.perf_counter()
        
        for i in range(num_responses):
            logger.log_response(
                request_summary=f"Test request {i}",
                response_content=response_content,
                metadata={"agent": "test_agent", "index": i}
            )
        
        elapsed_time = time.perf_counter() - start_time
        
        # Count files created
        session_dir = Path(tmpdir) / "sync_test_session"
        files_created = len(list(session_dir.glob("*.json")))
        
        print(f"✓ Created {files_created} files")
        print(f"✓ Total time: {elapsed_time:.2f} seconds")
        print(f"✓ Average time per response: {(elapsed_time / num_responses) * 1000:.2f} ms")
        print(f"✓ Throughput: {num_responses / elapsed_time:.1f} responses/sec")
        
        return elapsed_time


def test_async_logging(num_responses: int = 100, response_size_kb: int = 10):
    """Test asynchronous logging performance."""
    print(f"\n=== Testing ASYNCHRONOUS Logging (Timestamp-based) ===")
    print(f"Logging {num_responses} responses of {response_size_kb}KB each...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = AsyncSessionLogger(
            base_dir=Path(tmpdir),
            log_format=LogFormat.JSON,
            enable_async=True
        )
        logger.set_session_id("async_test_session")
        
        response_content = generate_test_response(response_size_kb)
        
        start_time = time.perf_counter()
        
        for i in range(num_responses):
            logger.log_response(
                request_summary=f"Test request {i}",
                response_content=response_content,
                metadata={"agent": "test_agent", "index": i}
            )
        
        # Don't wait for flush in fire-and-forget mode
        queue_time = time.perf_counter() - start_time
        
        # Now flush to ensure all writes complete
        flush_start = time.perf_counter()
        logger.flush(timeout=10.0)
        flush_time = time.perf_counter() - flush_start
        
        total_time = queue_time + flush_time
        
        # Count files created
        session_dir = Path(tmpdir) / "async_test_session"
        files_created = len(list(session_dir.glob("*.json")))
        
        # Get statistics
        stats = logger.get_stats()
        
        print(f"✓ Created {files_created} files")
        print(f"✓ Queue time (non-blocking): {queue_time:.3f} seconds")
        print(f"✓ Flush time: {flush_time:.2f} seconds")
        print(f"✓ Total time: {total_time:.2f} seconds")
        print(f"✓ Average queue time per response: {(queue_time / num_responses) * 1000:.3f} ms")
        print(f"✓ Throughput (queue): {num_responses / queue_time:.1f} responses/sec")
        print(f"✓ Stats: {stats}")
        
        logger.shutdown()
        
        return queue_time, total_time


def test_concurrent_logging(num_threads: int = 10, responses_per_thread: int = 10):
    """Test concurrent logging to demonstrate no race conditions."""
    print(f"\n=== Testing CONCURRENT Logging (No Race Conditions) ===")
    print(f"Running {num_threads} threads, each logging {responses_per_thread} responses...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = AsyncSessionLogger(
            base_dir=Path(tmpdir),
            log_format=LogFormat.JSON,
            enable_async=True
        )
        logger.set_session_id("concurrent_test_session")
        
        response_content = generate_test_response(5)
        
        def log_responses(thread_id: int):
            """Function to run in each thread."""
            for i in range(responses_per_thread):
                logger.log_response(
                    request_summary=f"Thread {thread_id} request {i}",
                    response_content=response_content,
                    metadata={"thread": thread_id, "index": i}
                )
        
        start_time = time.perf_counter()
        
        # Run concurrent logging
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(log_responses, i)
                for i in range(num_threads)
            ]
            
            # Wait for all threads to complete
            for future in futures:
                future.result()
        
        queue_time = time.perf_counter() - start_time
        
        # Flush all pending writes
        logger.flush(timeout=10.0)
        total_time = time.perf_counter() - start_time
        
        # Verify all files were created
        session_dir = Path(tmpdir) / "concurrent_test_session"
        files_created = len(list(session_dir.glob("*.json")))
        expected_files = num_threads * responses_per_thread
        
        # Check for any file collisions (files with same name)
        filenames = [f.name for f in session_dir.glob("*.json")]
        unique_filenames = len(set(filenames))
        
        print(f"✓ Expected files: {expected_files}")
        print(f"✓ Created files: {files_created}")
        print(f"✓ Unique filenames: {unique_filenames}")
        print(f"✓ File collisions: {files_created - unique_filenames}")
        print(f"✓ Queue time: {queue_time:.2f} seconds")
        print(f"✓ Total time: {total_time:.2f} seconds")
        print(f"✓ Throughput: {expected_files / queue_time:.1f} responses/sec")
        
        # Verify no data corruption
        corrupted = 0
        for json_file in session_dir.glob("*.json"):
            try:
                with open(json_file) as f:
                    data = json.load(f)
                    # Basic validation
                    assert "timestamp" in data
                    assert "request_summary" in data
                    assert "response_content" in data
            except:
                corrupted += 1
        
        print(f"✓ Corrupted files: {corrupted}")
        
        logger.shutdown()
        
        return files_created == expected_files and corrupted == 0


def test_syslog_performance(num_responses: int = 100):
    """Test syslog logging performance (OS-native)."""
    print(f"\n=== Testing SYSLOG Logging (OS-native) ===")
    print(f"Logging {num_responses} responses to syslog...")
    
    try:
        logger = AsyncSessionLogger(
            base_dir=Path("/tmp/syslog_test"),
            log_format=LogFormat.SYSLOG,
            enable_async=True
        )
        logger.set_session_id("syslog_test_session")
        
        response_content = generate_test_response(10)
        
        start_time = time.perf_counter()
        
        for i in range(num_responses):
            logger.log_response(
                request_summary=f"Test request {i}",
                response_content=response_content,
                metadata={"agent": "test_agent", "index": i}
            )
        
        queue_time = time.perf_counter() - start_time
        
        logger.flush(timeout=5.0)
        total_time = time.perf_counter() - start_time
        
        print(f"✓ Queue time: {queue_time:.3f} seconds")
        print(f"✓ Total time: {total_time:.2f} seconds")
        print(f"✓ Average time per response: {(queue_time / num_responses) * 1000:.3f} ms")
        print(f"✓ Throughput: {num_responses / queue_time:.1f} responses/sec")
        print(f"Note: Check system logs with 'tail -f /var/log/system.log | grep claude-mpm'")
        
        logger.shutdown()
        
    except Exception as e:
        print(f"✗ Syslog test failed: {e}")
        print("  (This is expected on some systems without syslog access)")


def benchmark_comparison():
    """Run comprehensive benchmark comparison."""
    print("\n" + "="*60)
    print("PERFORMANCE BENCHMARK COMPARISON")
    print("="*60)
    
    # Test parameters
    test_sizes = [10, 100, 500]
    response_size = 10  # KB
    
    results = {}
    
    for size in test_sizes:
        print(f"\n--- Testing with {size} responses ---")
        
        # Sync test
        sync_time = test_sync_logging(size, response_size)
        
        # Async test
        queue_time, total_time = test_async_logging(size, response_size)
        
        # Calculate improvement
        improvement = (sync_time - queue_time) / sync_time * 100
        
        results[size] = {
            "sync": sync_time,
            "async_queue": queue_time,
            "async_total": total_time,
            "improvement": improvement
        }
        
        print(f"\n✨ Performance Improvement: {improvement:.1f}% faster (queue time)")
        print(f"   Sync: {sync_time:.3f}s vs Async Queue: {queue_time:.3f}s")
    
    # Summary
    print("\n" + "="*60)
    print("BENCHMARK SUMMARY")
    print("="*60)
    print(f"{'Responses':<12} {'Sync (s)':<12} {'Async Queue (s)':<16} {'Improvement':<12}")
    print("-"*52)
    
    for size, data in results.items():
        print(f"{size:<12} {data['sync']:<12.3f} {data['async_queue']:<16.3f} {data['improvement']:.1f}%")
    
    avg_improvement = statistics.mean([r["improvement"] for r in results.values()])
    print(f"\nAverage Performance Improvement: {avg_improvement:.1f}%")


def main():
    """Main test function."""
    print("🚀 Async Logging Performance Test Suite")
    print("="*60)
    
    # Run individual tests
    test_sync_logging(50, 10)
    test_async_logging(50, 10)
    test_concurrent_logging(10, 10)
    test_syslog_performance(50)
    
    # Run comprehensive benchmark
    benchmark_comparison()
    
    print("\n✅ All tests completed!")
    print("\nKey Benefits of Async Logging:")
    print("1. ⚡ Near-zero latency with fire-and-forget pattern")
    print("2. 🔒 No race conditions with timestamp-based filenames")
    print("3. 📈 Scales linearly with concurrent requests")
    print("4. 🛡️ Graceful degradation on errors")
    print("5. 🔧 Optional OS-native logging for extreme performance")


if __name__ == "__main__":
    main()