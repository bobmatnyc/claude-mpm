#!/usr/bin/env python3
"""
Performance validation for Socket.IO server enhancements.

This test validates that the new features don't significantly impact performance.
"""

import time
import tempfile
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from claude_mpm.services.standalone_socketio_server import StandaloneSocketIOServer
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False


def time_operation(operation_name, operation_func, iterations=10):
    """Time an operation and return average duration."""
    print(f"Timing {operation_name} ({iterations} iterations)...")
    
    times = []
    for i in range(iterations):
        start_time = time.time()
        operation_func()
        end_time = time.time()
        times.append(end_time - start_time)
    
    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    
    print(f"  Average: {avg_time*1000:.2f}ms")
    print(f"  Range: {min_time*1000:.2f}ms - {max_time*1000:.2f}ms")
    
    return avg_time


def test_server_initialization_performance():
    """Test server initialization performance."""
    temp_dir = Path(tempfile.mkdtemp())
    
    def init_server():
        server = StandaloneSocketIOServer(host="localhost", port=19999)
        server.pidfile_path = temp_dir / "perf_test.pid"
        return server
    
    try:
        avg_time = time_operation("Server Initialization", init_server, iterations=5)
        
        # Server initialization should be fast (under 100ms)
        if avg_time < 0.1:
            print("  ✓ Server initialization performance acceptable")
            return True
        else:
            print("  ⚠ Server initialization slower than expected")
            return False
            
    finally:
        # Clean up
        for file in temp_dir.glob("*.pid"):
            file.unlink()
        temp_dir.rmdir()


def test_pid_file_operations_performance():
    """Test PID file operations performance."""
    temp_dir = Path(tempfile.mkdtemp())
    server = StandaloneSocketIOServer(host="localhost", port=19998)
    server.pidfile_path = temp_dir / "perf_test.pid"
    
    def create_and_remove_pidfile():
        server.create_pidfile()
        server.remove_pidfile()
    
    try:
        avg_time = time_operation("PID File Create/Remove", create_and_remove_pidfile, iterations=20)
        
        # PID file operations should be very fast (under 10ms)
        if avg_time < 0.01:
            print("  ✓ PID file operations performance excellent")
            return True
        elif avg_time < 0.05:
            print("  ✓ PID file operations performance acceptable")
            return True
        else:
            print("  ⚠ PID file operations slower than expected")
            return False
            
    finally:
        # Clean up
        if server.pidfile_path.exists():
            server.pidfile_path.unlink()
        temp_dir.rmdir()


def test_process_validation_performance():
    """Test process validation performance."""
    server = StandaloneSocketIOServer(host="localhost", port=19997)
    
    def validate_current_process():
        return server._validate_process_identity(os.getpid())
    
    avg_time = time_operation("Process Validation", validate_current_process, iterations=10)
    
    # Process validation should be reasonably fast (under 50ms)
    if avg_time < 0.05:
        print("  ✓ Process validation performance excellent")
        return True
    elif avg_time < 0.1:
        print("  ✓ Process validation performance acceptable")
        return True
    else:
        print("  ⚠ Process validation slower than expected")
        return False


def test_is_already_running_performance():
    """Test is_already_running check performance."""
    temp_dir = Path(tempfile.mkdtemp())
    server = StandaloneSocketIOServer(host="localhost", port=19996)
    server.pidfile_path = temp_dir / "perf_test.pid"
    
    def check_already_running():
        return server.is_already_running()
    
    try:
        avg_time = time_operation("is_already_running Check", check_already_running, iterations=15)
        
        # This check should be fast (under 20ms) even with all validation
        if avg_time < 0.02:
            print("  ✓ is_already_running performance excellent")
            return True
        elif avg_time < 0.05:
            print("  ✓ is_already_running performance acceptable")
            return True
        else:
            print("  ⚠ is_already_running slower than expected")
            return False
            
    finally:
        # Clean up
        if server.pidfile_path.exists():
            server.pidfile_path.unlink()
        temp_dir.rmdir()


def run_performance_tests():
    """Run all performance tests."""
    if not IMPORTS_AVAILABLE:
        print("❌ Cannot run performance tests - imports not available")
        return False
    
    print("🚀 Performance Validation for Socket.IO Server Enhancements")
    print("=" * 65)
    
    tests = [
        ("Server Initialization", test_server_initialization_performance),
        ("PID File Operations", test_pid_file_operations_performance),
        ("Process Validation", test_process_validation_performance),
        ("Already Running Check", test_is_already_running_performance)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\\n📊 {test_name}")
        print("-" * 40)
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"  ✗ Test failed: {e}")
            results.append((test_name, False))
    
    print("\\n" + "=" * 65)
    print("PERFORMANCE TEST SUMMARY")
    print("=" * 65)
    
    passed = 0
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name:<30} | {status}")
        if result:
            passed += 1
    
    print("-" * 65)
    print(f"Total: {passed}/{len(results)} performance tests passed")
    
    if passed == len(results):
        print("🎉 All performance tests passed!")
        print("   The enhancements have minimal performance impact.")
        return True
    else:
        print("⚠ Some performance tests failed or showed concerns.")
        print("   Review implementation for optimization opportunities.")
        return False


if __name__ == "__main__":
    success = run_performance_tests()
    exit(0 if success else 1)