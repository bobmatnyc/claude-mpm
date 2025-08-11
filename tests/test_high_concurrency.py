#!/usr/bin/env python3
"""
High concurrency test for async logging system.
Tests with 100+ concurrent threads to verify collision prevention.
"""

import asyncio
import time
import json
import tempfile
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics
import threading

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.async_session_logger import AsyncSessionLogger, LogFormat


def test_extreme_concurrency(num_threads: int = 100, responses_per_thread: int = 50):
    """Test extreme concurrency to demonstrate no race conditions."""
    print(f"\n=== EXTREME CONCURRENCY TEST ===")
    print(f"Running {num_threads} threads, each logging {responses_per_thread} responses...")
    print(f"Total expected responses: {num_threads * responses_per_thread}")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = AsyncSessionLogger(
            base_dir=Path(tmpdir),
            log_format=LogFormat.JSON,
            enable_async=True,
            max_queue_size=50000  # Increase queue size for high load
        )
        logger.set_session_id("extreme_concurrency_test")
        
        # Test response content
        response_content = "Test response content " * 100  # ~2KB per response
        
        # Shared counters for verification
        thread_results = {}
        thread_lock = threading.Lock()
        
        def log_responses(thread_id: int):
            """Function to run in each thread."""
            success_count = 0
            start_time = time.perf_counter()
            
            for i in range(responses_per_thread):
                success = logger.log_response(
                    request_summary=f"Thread {thread_id} request {i}",
                    response_content=response_content,
                    metadata={
                        "thread": thread_id,
                        "index": i,
                        "timestamp": time.time()
                    }
                )
                if success:
                    success_count += 1
            
            thread_time = time.perf_counter() - start_time
            
            with thread_lock:
                thread_results[thread_id] = {
                    "success_count": success_count,
                    "thread_time": thread_time
                }
            
            return thread_id, success_count, thread_time
        
        # Start timing
        start_time = time.perf_counter()
        
        # Run all threads concurrently
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            # Submit all tasks
            futures = [
                executor.submit(log_responses, i)
                for i in range(num_threads)
            ]
            
            # Collect results as they complete
            completed = 0
            for future in as_completed(futures):
                try:
                    thread_id, success_count, thread_time = future.result()
                    completed += 1
                    if completed % 10 == 0:
                        print(f"  ✓ Completed {completed}/{num_threads} threads")
                except Exception as e:
                    print(f"  ✗ Thread failed: {e}")
        
        queue_time = time.perf_counter() - start_time
        
        # Wait for all async writes to complete
        print("  ⏳ Flushing pending writes...")
        flush_start = time.perf_counter()
        logger.flush(timeout=30.0)
        flush_time = time.perf_counter() - flush_start
        
        total_time = time.perf_counter() - start_time
        
        # Analyze results
        session_dir = Path(tmpdir) / "extreme_concurrency_test"
        files_created = len(list(session_dir.glob("*.json")))
        expected_files = num_threads * responses_per_thread
        
        # Check for filename collisions
        filenames = [f.name for f in session_dir.glob("*.json")]
        unique_filenames = len(set(filenames))
        collisions = files_created - unique_filenames
        
        # Verify no data corruption
        corrupted = 0
        total_size = 0
        for json_file in session_dir.glob("*.json"):
            try:
                with open(json_file) as f:
                    data = json.load(f)
                    # Basic validation
                    assert "timestamp" in data
                    assert "request_summary" in data
                    assert "response_content" in data
                    assert "metadata" in data
                    total_size += json_file.stat().st_size
            except Exception as e:
                corrupted += 1
                print(f"  ✗ Corrupted file {json_file}: {e}")
        
        # Get logger statistics
        stats = logger.get_stats()
        
        # Calculate thread performance statistics
        thread_times = [r["thread_time"] for r in thread_results.values()]
        success_counts = [r["success_count"] for r in thread_results.values()]
        
        print(f"\n📊 RESULTS:")
        print(f"  ✓ Expected files: {expected_files}")
        print(f"  ✓ Created files: {files_created}")
        print(f"  ✓ Success rate: {files_created/expected_files*100:.1f}%")
        print(f"  ✓ Unique filenames: {unique_filenames}")
        print(f"  ✓ File collisions: {collisions}")
        print(f"  ✓ Corrupted files: {corrupted}")
        print(f"  ✓ Total data size: {total_size/1024/1024:.2f} MB")
        
        print(f"\n⏱️ TIMING:")
        print(f"  ✓ Queue time: {queue_time:.3f} seconds")
        print(f"  ✓ Flush time: {flush_time:.3f} seconds")
        print(f"  ✓ Total time: {total_time:.3f} seconds")
        print(f"  ✓ Queue throughput: {expected_files/queue_time:.1f} responses/sec")
        print(f"  ✓ Overall throughput: {expected_files/total_time:.1f} responses/sec")
        
        print(f"\n📈 THREAD STATISTICS:")
        print(f"  ✓ Avg thread time: {statistics.mean(thread_times):.3f} seconds")
        print(f"  ✓ Min thread time: {min(thread_times):.3f} seconds")
        print(f"  ✓ Max thread time: {max(thread_times):.3f} seconds")
        print(f"  ✓ Thread time stddev: {statistics.stdev(thread_times):.3f} seconds")
        
        print(f"\n🔧 LOGGER STATISTICS:")
        print(f"  ✓ Logged: {stats['logged']}")
        print(f"  ✓ Queued: {stats['queued']}")
        print(f"  ✓ Dropped: {stats['dropped']}")
        print(f"  ✓ Errors: {stats['errors']}")
        print(f"  ✓ Avg write time: {stats['avg_write_time_ms']:.3f} ms")
        
        logger.shutdown()
        
        # Return test results
        return {
            "success": collisions == 0 and corrupted == 0 and files_created == expected_files,
            "files_created": files_created,
            "expected_files": expected_files,
            "collisions": collisions,
            "corrupted": corrupted,
            "queue_time": queue_time,
            "total_time": total_time,
            "throughput": expected_files / queue_time,
            "stats": stats
        }


def test_stress_with_different_loads():
    """Test with different thread/load combinations."""
    print("\n" + "="*60)
    print("STRESS TESTING WITH DIFFERENT LOADS")
    print("="*60)
    
    test_cases = [
        (50, 20),   # 50 threads, 20 responses each = 1,000 total
        (100, 50),  # 100 threads, 50 responses each = 5,000 total
        (200, 25),  # 200 threads, 25 responses each = 5,000 total
        (500, 10),  # 500 threads, 10 responses each = 5,000 total
    ]
    
    results = []
    
    for threads, responses in test_cases:
        print(f"\n--- Testing: {threads} threads × {responses} responses = {threads * responses} total ---")
        
        try:
            result = test_extreme_concurrency(threads, responses)
            results.append({
                "threads": threads,
                "responses": responses,
                "total": threads * responses,
                "result": result
            })
            
            if result["success"]:
                print(f"✅ PASS - No collisions, no corruption")
            else:
                print(f"❌ FAIL - {result['collisions']} collisions, {result['corrupted']} corrupted")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            results.append({
                "threads": threads,
                "responses": responses,
                "total": threads * responses,
                "result": {"error": str(e)}
            })
    
    # Summary table
    print("\n" + "="*80)
    print("STRESS TEST SUMMARY")
    print("="*80)
    print(f"{'Threads':<8} {'Responses':<10} {'Total':<8} {'Status':<8} {'Throughput':<12} {'Collisions':<10}")
    print("-"*70)
    
    for test in results:
        if "error" not in test["result"]:
            r = test["result"]
            status = "✅ PASS" if r["success"] else "❌ FAIL"
            throughput = f"{r['throughput']:.0f}/s"
            collisions = r["collisions"]
        else:
            status = "❌ ERROR"
            throughput = "N/A"
            collisions = "N/A"
            
        print(f"{test['threads']:<8} {test['responses']:<10} {test['total']:<8} {status:<8} {throughput:<12} {collisions:<10}")
    
    return results


if __name__ == "__main__":
    print("🚀 HIGH CONCURRENCY ASYNC LOGGING TEST")
    print("="*60)
    
    # Run stress tests with different loads
    results = test_stress_with_different_loads()
    
    # Analyze overall results
    successful_tests = sum(1 for r in results if r["result"].get("success", False))
    total_tests = len(results)
    
    print(f"\n🎯 OVERALL RESULTS:")
    print(f"  ✓ Successful tests: {successful_tests}/{total_tests}")
    print(f"  ✓ Success rate: {successful_tests/total_tests*100:.1f}%")
    
    if successful_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ File collision prevention is working correctly")
        print("✅ Data integrity maintained under high concurrency")
        print("✅ System scales well with concurrent loads")
    else:
        print("\n⚠️ SOME TESTS FAILED")
        print("❌ Review failed tests above for issues")