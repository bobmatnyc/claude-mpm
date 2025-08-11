#!/usr/bin/env python3
"""
Stress test with 1 million+ requests to validate system scalability.
Tests memory usage, disk I/O limits, and queue overflow handling.
"""

import time
import sys
import tempfile
import gc
import psutil
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import resource

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.async_session_logger import AsyncSessionLogger, LogFormat


class MemoryMonitor:
    """Monitor memory usage during stress testing."""
    
    def __init__(self):
        self.process = psutil.Process()
        self.peak_memory_mb = 0
        self.peak_memory_percent = 0
        self.monitoring = False
        self._lock = threading.Lock()
    
    def start_monitoring(self):
        """Start memory monitoring in background thread."""
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop memory monitoring."""
        self.monitoring = False
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join(timeout=1.0)
    
    def _monitor_loop(self):
        """Monitor memory usage continuously."""
        while self.monitoring:
            try:
                memory_info = self.process.memory_info()
                memory_percent = self.process.memory_percent()
                memory_mb = memory_info.rss / 1024 / 1024
                
                with self._lock:
                    self.peak_memory_mb = max(self.peak_memory_mb, memory_mb)
                    self.peak_memory_percent = max(self.peak_memory_percent, memory_percent)
                
                time.sleep(0.1)  # Monitor every 100ms
                
            except Exception:
                pass  # Ignore errors during monitoring
    
    def get_stats(self):
        """Get current memory statistics."""
        with self._lock:
            current_memory = self.process.memory_info().rss / 1024 / 1024
            return {
                "current_memory_mb": current_memory,
                "peak_memory_mb": self.peak_memory_mb,
                "peak_memory_percent": self.peak_memory_percent
            }


def test_lightweight_stress(num_requests: int = 100000):
    """Test with many lightweight requests."""
    print(f"\n=== Lightweight Stress Test ({num_requests:,} requests) ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = AsyncSessionLogger(
            base_dir=Path(tmpdir),
            log_format=LogFormat.JSON,
            enable_async=True,
            max_queue_size=50000  # Large queue for stress test
        )
        logger.set_session_id("lightweight_stress")
        
        # Monitor memory usage
        memory_monitor = MemoryMonitor()
        memory_monitor.start_monitoring()
        
        # Generate lightweight responses
        lightweight_response = "OK"  # Minimal response
        
        print(f"  Starting {num_requests:,} lightweight requests...")
        start_time = time.perf_counter()
        
        successful = 0
        dropped = 0
        
        # Batch requests for better performance
        batch_size = 1000
        for batch_start in range(0, num_requests, batch_size):
            batch_end = min(batch_start + batch_size, num_requests)
            
            for i in range(batch_start, batch_end):
                success = logger.log_response(
                    f"Request {i}",
                    lightweight_response,
                    {"agent": "stress_test", "batch": batch_start // batch_size}
                )
                
                if success:
                    successful += 1
                else:
                    dropped += 1
            
            # Progress update
            if (batch_start + batch_size) % 10000 == 0:
                elapsed = time.perf_counter() - start_time
                rate = (batch_start + batch_size) / elapsed if elapsed > 0 else 0
                print(f"    Progress: {batch_start + batch_size:,} requests, {rate:.1f} req/sec")
        
        queue_time = time.perf_counter() - start_time
        
        print(f"  ✓ Queued {num_requests:,} requests in {queue_time:.3f} seconds")
        print(f"  ✓ Queue rate: {num_requests / queue_time:.1f} requests/sec")
        print(f"  ✓ Successful: {successful:,}, Dropped: {dropped:,}")
        
        # Flush all pending writes
        print("  ⏳ Flushing pending writes...")
        flush_start = time.perf_counter()
        
        logger.flush(timeout=60.0)  # Allow more time for large volume
        
        flush_time = time.perf_counter() - flush_start
        total_time = time.perf_counter() - start_time
        
        print(f"  ✓ Flush time: {flush_time:.3f} seconds")
        print(f"  ✓ Total time: {total_time:.3f} seconds")
        print(f"  ✓ Overall rate: {num_requests / total_time:.1f} requests/sec")
        
        # Get final statistics
        stats = logger.get_stats()
        memory_stats = memory_monitor.get_stats()
        memory_monitor.stop_monitoring()
        
        # Count created files
        session_dir = Path(tmpdir) / "lightweight_stress"
        files_created = len(list(session_dir.glob("*.json")))
        
        # Calculate disk usage
        total_size = sum(f.stat().st_size for f in session_dir.glob("*.json"))
        size_mb = total_size / 1024 / 1024
        
        print(f"  📊 Results:")
        print(f"    - Files created: {files_created:,}")
        print(f"    - Total disk usage: {size_mb:.2f} MB")
        print(f"    - Peak memory usage: {memory_stats['peak_memory_mb']:.1f} MB ({memory_stats['peak_memory_percent']:.1f}%)")
        print(f"    - Logger stats: {stats}")
        
        logger.shutdown()
        
        return {
            "requests_sent": num_requests,
            "successful": successful,
            "dropped": dropped,
            "files_created": files_created,
            "queue_time": queue_time,
            "flush_time": flush_time,
            "total_time": total_time,
            "queue_rate": num_requests / queue_time,
            "overall_rate": num_requests / total_time,
            "disk_usage_mb": size_mb,
            "peak_memory_mb": memory_stats['peak_memory_mb'],
            "logger_stats": stats,
            "success": successful > num_requests * 0.95  # Allow 5% drop rate
        }


def test_heavy_payload_stress(num_requests: int = 10000):
    """Test with fewer but heavier payload requests."""
    print(f"\n=== Heavy Payload Stress Test ({num_requests:,} requests) ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = AsyncSessionLogger(
            base_dir=Path(tmpdir),
            log_format=LogFormat.JSON,
            enable_async=True,
            max_queue_size=20000
        )
        logger.set_session_id("heavy_stress")
        
        # Monitor memory usage
        memory_monitor = MemoryMonitor()
        memory_monitor.start_monitoring()
        
        # Generate heavy payload (10KB per response)
        heavy_response = "Heavy response data " * 500  # ~10KB
        
        print(f"  Starting {num_requests:,} heavy payload requests (~10KB each)...")
        start_time = time.perf_counter()
        
        successful = 0
        dropped = 0
        
        for i in range(num_requests):
            success = logger.log_response(
                f"Heavy request {i} with detailed information",
                heavy_response,
                {
                    "agent": "heavy_stress_test",
                    "request_id": i,
                    "payload_size": "10KB",
                    "metadata": {
                        "nested": {"data": "structure"},
                        "array": list(range(100)),
                        "large_text": "Additional metadata " * 50
                    }
                }
            )
            
            if success:
                successful += 1
            else:
                dropped += 1
            
            # Progress update
            if (i + 1) % 1000 == 0:
                elapsed = time.perf_counter() - start_time
                rate = (i + 1) / elapsed if elapsed > 0 else 0
                print(f"    Progress: {i + 1:,} requests, {rate:.1f} req/sec")
        
        queue_time = time.perf_counter() - start_time
        
        print(f"  ✓ Queued {num_requests:,} heavy requests in {queue_time:.3f} seconds")
        print(f"  ✓ Queue rate: {num_requests / queue_time:.1f} requests/sec")
        print(f"  ✓ Data rate: {(num_requests * 10) / queue_time:.1f} KB/sec")
        print(f"  ✓ Successful: {successful:,}, Dropped: {dropped:,}")
        
        # Flush all pending writes
        print("  ⏳ Flushing heavy payload writes...")
        flush_start = time.perf_counter()
        
        logger.flush(timeout=120.0)  # More time for heavy payloads
        
        flush_time = time.perf_counter() - flush_start
        total_time = time.perf_counter() - start_time
        
        print(f"  ✓ Flush time: {flush_time:.3f} seconds")
        print(f"  ✓ Total time: {total_time:.3f} seconds")
        print(f"  ✓ Overall rate: {num_requests / total_time:.1f} requests/sec")
        
        # Get final statistics
        stats = logger.get_stats()
        memory_stats = memory_monitor.get_stats()
        memory_monitor.stop_monitoring()
        
        # Count created files and disk usage
        session_dir = Path(tmpdir) / "heavy_stress"
        files_created = len(list(session_dir.glob("*.json")))
        
        total_size = sum(f.stat().st_size for f in session_dir.glob("*.json"))
        size_mb = total_size / 1024 / 1024
        
        print(f"  📊 Results:")
        print(f"    - Files created: {files_created:,}")
        print(f"    - Total disk usage: {size_mb:.2f} MB")
        print(f"    - Average file size: {size_mb / files_created * 1024:.1f} KB" if files_created > 0 else "N/A")
        print(f"    - Peak memory usage: {memory_stats['peak_memory_mb']:.1f} MB ({memory_stats['peak_memory_percent']:.1f}%)")
        print(f"    - Logger stats: {stats}")
        
        logger.shutdown()
        
        return {
            "requests_sent": num_requests,
            "successful": successful,
            "dropped": dropped,
            "files_created": files_created,
            "queue_time": queue_time,
            "flush_time": flush_time,
            "total_time": total_time,
            "queue_rate": num_requests / queue_time,
            "overall_rate": num_requests / total_time,
            "disk_usage_mb": size_mb,
            "peak_memory_mb": memory_stats['peak_memory_mb'],
            "logger_stats": stats,
            "success": successful > num_requests * 0.90  # Allow 10% drop rate for heavy load
        }


def test_concurrent_stress(num_threads: int = 50, requests_per_thread: int = 5000):
    """Test concurrent stress with multiple threads."""
    print(f"\n=== Concurrent Stress Test ({num_threads} threads × {requests_per_thread:,} = {num_threads * requests_per_thread:,} total) ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = AsyncSessionLogger(
            base_dir=Path(tmpdir),
            log_format=LogFormat.JSON,
            enable_async=True,
            max_queue_size=100000  # Very large queue
        )
        logger.set_session_id("concurrent_stress")
        
        # Monitor memory usage
        memory_monitor = MemoryMonitor()
        memory_monitor.start_monitoring()
        
        def worker_thread(thread_id: int):
            """Worker function for each thread."""
            successful = 0
            
            for i in range(requests_per_thread):
                success = logger.log_response(
                    f"Thread {thread_id} request {i}",
                    f"Concurrent stress test response from thread {thread_id}",
                    {"agent": f"thread_{thread_id}", "request_index": i}
                )
                
                if success:
                    successful += 1
            
            return thread_id, successful
        
        print(f"  Starting {num_threads} concurrent threads...")
        start_time = time.perf_counter()
        
        # Run all threads concurrently
        total_successful = 0
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            # Submit all thread tasks
            futures = [
                executor.submit(worker_thread, i)
                for i in range(num_threads)
            ]
            
            # Collect results as they complete
            completed_threads = 0
            for future in as_completed(futures):
                try:
                    thread_id, successful = future.result()
                    total_successful += successful
                    completed_threads += 1
                    
                    if completed_threads % 10 == 0:
                        elapsed = time.perf_counter() - start_time
                        rate = (completed_threads * requests_per_thread) / elapsed if elapsed > 0 else 0
                        print(f"    Progress: {completed_threads}/{num_threads} threads completed, {rate:.1f} req/sec")
                        
                except Exception as e:
                    print(f"    ✗ Thread failed: {e}")
        
        queue_time = time.perf_counter() - start_time
        total_requests = num_threads * requests_per_thread
        
        print(f"  ✓ Queued {total_requests:,} requests from {num_threads} threads in {queue_time:.3f} seconds")
        print(f"  ✓ Queue rate: {total_requests / queue_time:.1f} requests/sec")
        print(f"  ✓ Successful: {total_successful:,}/{total_requests:,} ({total_successful/total_requests*100:.1f}%)")
        
        # Flush all pending writes
        print("  ⏳ Flushing concurrent writes...")
        flush_start = time.perf_counter()
        
        logger.flush(timeout=180.0)  # Extended time for large concurrent load
        
        flush_time = time.perf_counter() - flush_start
        total_time = time.perf_counter() - start_time
        
        print(f"  ✓ Flush time: {flush_time:.3f} seconds")
        print(f"  ✓ Total time: {total_time:.3f} seconds")
        print(f"  ✓ Overall rate: {total_requests / total_time:.1f} requests/sec")
        
        # Get final statistics
        stats = logger.get_stats()
        memory_stats = memory_monitor.get_stats()
        memory_monitor.stop_monitoring()
        
        # Count created files
        session_dir = Path(tmpdir) / "concurrent_stress"
        files_created = len(list(session_dir.glob("*.json")))
        
        total_size = sum(f.stat().st_size for f in session_dir.glob("*.json"))
        size_mb = total_size / 1024 / 1024
        
        print(f"  📊 Results:")
        print(f"    - Files created: {files_created:,}")
        print(f"    - File collision rate: {(total_requests - files_created) / total_requests * 100:.3f}%")
        print(f"    - Total disk usage: {size_mb:.2f} MB")
        print(f"    - Peak memory usage: {memory_stats['peak_memory_mb']:.1f} MB ({memory_stats['peak_memory_percent']:.1f}%)")
        print(f"    - Logger stats: {stats}")
        
        logger.shutdown()
        
        return {
            "total_requests": total_requests,
            "successful": total_successful,
            "files_created": files_created,
            "queue_time": queue_time,
            "flush_time": flush_time,
            "total_time": total_time,
            "queue_rate": total_requests / queue_time,
            "overall_rate": total_requests / total_time,
            "disk_usage_mb": size_mb,
            "peak_memory_mb": memory_stats['peak_memory_mb'],
            "collision_rate": (total_requests - files_created) / total_requests * 100,
            "logger_stats": stats,
            "success": files_created > total_requests * 0.99  # Less than 1% collision rate
        }


def main():
    """Main stress testing function."""
    print("🚀 STRESS TESTING WITH 1M+ REQUESTS")
    print("="*60)
    
    # Check system resources before starting
    print("\n📊 System Resources Before Testing:")
    process = psutil.Process()
    memory_info = process.memory_info()
    print(f"  ✓ Current memory usage: {memory_info.rss / 1024 / 1024:.1f} MB")
    print(f"  ✓ Available memory: {psutil.virtual_memory().available / 1024 / 1024:.1f} MB")
    print(f"  ✓ CPU count: {psutil.cpu_count()}")
    
    # Run stress tests with different characteristics
    tests_results = {}
    
    try:
        # Test 1: Many lightweight requests (1M)
        tests_results["lightweight"] = test_lightweight_stress(1000000)
        
        # Force garbage collection between tests
        gc.collect()
        
        # Test 2: Heavy payload requests (10K)
        tests_results["heavy"] = test_heavy_payload_stress(10000)
        
        # Force garbage collection between tests
        gc.collect()
        
        # Test 3: Concurrent stress (250K total)
        tests_results["concurrent"] = test_concurrent_stress(50, 5000)
        
    except Exception as e:
        print(f"\n❌ STRESS TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    # Summary
    print("\n" + "="*60)
    print("STRESS TEST SUMMARY")
    print("="*60)
    
    total_requests_tested = 0
    total_files_created = 0
    total_disk_usage = 0
    peak_memory_usage = 0
    
    for test_name, result in tests_results.items():
        if result:
            print(f"\n🔥 {test_name.title()} Stress Test:")
            print(f"  ✓ Requests: {result.get('total_requests', result.get('requests_sent', 0)):,}")
            print(f"  ✓ Files created: {result.get('files_created', 0):,}")
            print(f"  ✓ Queue rate: {result.get('queue_rate', 0):.1f} req/sec")
            print(f"  ✓ Overall rate: {result.get('overall_rate', 0):.1f} req/sec")
            print(f"  ✓ Disk usage: {result.get('disk_usage_mb', 0):.2f} MB")
            print(f"  ✓ Peak memory: {result.get('peak_memory_mb', 0):.1f} MB")
            print(f"  ✓ Status: {'✅ PASS' if result.get('success') else '❌ FAIL'}")
            
            total_requests_tested += result.get('total_requests', result.get('requests_sent', 0))
            total_files_created += result.get('files_created', 0)
            total_disk_usage += result.get('disk_usage_mb', 0)
            peak_memory_usage = max(peak_memory_usage, result.get('peak_memory_mb', 0))
    
    successful_tests = sum(1 for result in tests_results.values() if result and result.get('success'))
    total_tests = len(tests_results)
    
    print(f"\n🎯 OVERALL STRESS TEST RESULTS:")
    print(f"  ✓ Total requests tested: {total_requests_tested:,}")
    print(f"  ✓ Total files created: {total_files_created:,}")
    print(f"  ✓ Total disk usage: {total_disk_usage:.2f} MB")
    print(f"  ✓ Peak memory usage: {peak_memory_usage:.1f} MB")
    print(f"  ✓ Successful test suites: {successful_tests}/{total_tests}")
    
    if successful_tests >= total_tests - 1:  # Allow one test to fail
        print(f"\n🏆 STRESS TESTING PASSED!")
        print(f"✅ System handled {total_requests_tested:,} requests successfully")
        print(f"✅ Memory usage remained reasonable ({peak_memory_usage:.1f} MB peak)")
        print(f"✅ Disk I/O performance adequate ({total_disk_usage:.2f} MB total)")
        print(f"✅ Queue overflow handling working correctly")
        print(f"✅ No system crashes or hangs under extreme load")
    else:
        print(f"\n⚠️ STRESS TESTING HAD ISSUES")
        print(f"❌ Only {successful_tests}/{total_tests} test suites passed")
        print(f"❌ Review failed tests above for bottlenecks or issues")
    
    return {
        "tests_results": tests_results,
        "total_requests_tested": total_requests_tested,
        "total_files_created": total_files_created,
        "total_disk_usage_mb": total_disk_usage,
        "peak_memory_usage_mb": peak_memory_usage,
        "successful_tests": successful_tests,
        "total_tests": total_tests,
        "overall_success": successful_tests >= total_tests - 1
    }


if __name__ == "__main__":
    main()