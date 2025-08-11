#!/usr/bin/env python3
"""Simple performance tests for the QA process."""

import sys
import time
import tempfile
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from claude_mpm.services.async_session_logger import AsyncSessionLogger
from claude_mpm.services.claude_session_logger import ClaudeSessionLogger

def test_async_performance():
    """Test async logger performance."""
    print("Testing AsyncSessionLogger performance...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = AsyncSessionLogger(base_dir=Path(tmpdir))
        
        # Performance test
        start_time = time.perf_counter()
        
        for i in range(100):
            logger.log_response(
                request_summary=f"Test request {i}",
                response_content=f"Test response {i}",
                agent=f"test_agent_{i}"
            )
        
        flush_time = time.perf_counter()
        logger.flush(timeout=10)
        end_time = time.perf_counter()
        
        log_time = flush_time - start_time
        flush_duration = end_time - flush_time
        
        stats = logger.get_stats()
        
        print(f"  Logged 100 entries in {log_time:.3f}s ({log_time*1000/100:.2f}ms per entry)")
        print(f"  Flush took {flush_duration:.3f}s")
        print(f"  Stats: {stats}")
        
        return log_time < 1.0  # Should complete in under 1 second

def test_claude_performance():
    """Test Claude logger performance."""
    print("Testing ClaudeSessionLogger performance...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = ClaudeSessionLogger(base_dir=Path(tmpdir) / "claude")
        
        # Performance test
        start_time = time.perf_counter()
        
        for i in range(100):
            logger.log_response(
                request_summary=f"Test request {i}",
                response_content=f"Test response {i}",
                agent=f"test_agent_{i}"
            )
        
        end_time = time.perf_counter()
        
        log_time = end_time - start_time
        
        print(f"  Logged 100 entries in {log_time:.3f}s ({log_time*1000/100:.2f}ms per entry)")
        
        return log_time < 2.0  # Should complete in under 2 seconds (synchronous)

def main():
    """Run performance tests."""
    print("=== Simple Performance Tests ===")
    
    results = []
    
    try:
        results.append(("AsyncSessionLogger Performance", test_async_performance()))
        results.append(("ClaudeSessionLogger Performance", test_claude_performance()))
    except Exception as e:
        print(f"Performance test error: {e}")
        return False
    
    print("\n=== Performance Test Results ===")
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "PASS" if success else "FAIL"
        print(f"{test_name}: {status}")
        if success:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)