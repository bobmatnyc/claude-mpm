#!/usr/bin/env python3
"""Comprehensive test of the enhanced PID validation features."""

import json
import os
import sys
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    import psutil

    from claude_mpm.services.socketio_server import SocketIOServer
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)


def test_comprehensive_validation_scenarios():
    """Test various PID validation scenarios comprehensively."""
    print("Testing comprehensive validation scenarios...")

    results = []

    # Scenario 1: Valid process but not our server
    print("\\n1. Testing valid process that's not our server...")
    with tmp_path as temp_dir:
        server = SocketIOServer(host="localhost", port=19001)
        server.pidfile_path = Path(temp_dir) / "test1.pid"

        # Create PID file with current process
        current_pid = os.getpid()
        pidfile_data = {
            "pid": current_pid,
            "server_id": "test-server",
            "server_version": "1.0.0",
            "port": 19001,
        }

        with server.pidfile_path.open("w") as f:
            json.dump(pidfile_data, f)

        # Test validation
        is_running = server.is_already_running()
        results.append(
            ("valid_non_server_process", not is_running)
        )  # Should return False after port check
        print(
            f"   Result: {'PASS' if not is_running else 'FAIL'} - correctly identified non-server process"
        )

    # Scenario 2: Stale PID file with dead process
    print("\\n2. Testing stale PID file with dead process...")
    with tmp_path as temp_dir:
        server = SocketIOServer(host="localhost", port=19002)
        server.pidfile_path = Path(temp_dir) / "test2.pid"

        # Create PID file with non-existent process
        fake_pid = 999999
        with server.pidfile_path.open("w") as f:
            json.dump({"pid": fake_pid, "server_id": "dead-server"}, f)

        is_running = server.is_already_running()
        pidfile_exists = server.pidfile_path.exists()

        results.append(("stale_pidfile_cleanup", not is_running and not pidfile_exists))
        print(
            f"   Result: {'PASS' if not is_running and not pidfile_exists else 'FAIL'} - stale PID file cleaned up"
        )

    # Scenario 3: Corrupted PID file
    print("\\n3. Testing corrupted PID file...")
    with tmp_path as temp_dir:
        server = SocketIOServer(host="localhost", port=19003)
        server.pidfile_path = Path(temp_dir) / "test3.pid"

        # Create corrupted PID file
        with server.pidfile_path.open("w") as f:
            f.write("corrupted{invalid:json")

        is_running = server.is_already_running()
        pidfile_exists = server.pidfile_path.exists()

        results.append(("corrupted_pidfile", not is_running and not pidfile_exists))
        print(
            f"   Result: {'PASS' if not is_running and not pidfile_exists else 'FAIL'} - corrupted PID file handled"
        )

    # Scenario 4: Empty PID file
    print("\\n4. Testing empty PID file...")
    with tmp_path as temp_dir:
        server = SocketIOServer(host="localhost", port=19004)
        server.pidfile_path = Path(temp_dir) / "test4.pid"

        # Create empty PID file
        server.pidfile_path.touch()

        is_running = server.is_already_running()
        pidfile_exists = server.pidfile_path.exists()

        results.append(("empty_pidfile", not is_running and not pidfile_exists))
        print(
            f"   Result: {'PASS' if not is_running and not pidfile_exists else 'FAIL'} - empty PID file handled"
        )

    # Scenario 5: Process validation edge cases
    print("\\n5. Testing process validation edge cases...")
    server = SocketIOServer(host="localhost", port=19005)

    # Test with PID 1 (init process - should exist but not be our server)
    validation = server._validate_process_identity(1)
    init_test_pass = validation["is_valid"] and not validation["is_our_server"]
    results.append(("init_process_validation", init_test_pass))
    print(f"   Init process test: {'PASS' if init_test_pass else 'FAIL'}")

    # Test with current process (should exist but not be our server)
    validation = server._validate_process_identity(os.getpid())
    current_test_pass = validation["is_valid"] and not validation["is_our_server"]
    results.append(("current_process_validation", current_test_pass))
    print(f"   Current process test: {'PASS' if current_test_pass else 'FAIL'}")

    return results


def test_file_locking_scenarios():
    """Test various file locking scenarios."""
    print("\\nTesting file locking scenarios...")

    results = []

    # Test concurrent access prevention
    with tmp_path as temp_dir:
        server1 = SocketIOServer(host="localhost", port=19010)
        server2 = SocketIOServer(host="localhost", port=19010)

        pidfile_path = Path(temp_dir) / "concurrent_test.pid"
        server1.pidfile_path = pidfile_path
        server2.pidfile_path = pidfile_path

        # First server should succeed
        try:
            server1.create_pidfile()
            first_success = pidfile_path.exists() and server1.pidfile_lock is not None
            results.append(("first_server_lock", first_success))
            print(f"   First server lock: {'PASS' if first_success else 'FAIL'}")

            # Second server should fail
            try:
                server2.create_pidfile()
                second_failed = False  # Should not reach here
            except RuntimeError as e:
                second_failed = "exclusive lock" in str(e).lower()

            results.append(("second_server_blocked", second_failed))
            print(f"   Second server blocked: {'PASS' if second_failed else 'FAIL'}")

            # Cleanup
            server1.remove_pidfile()

        except Exception as e:
            print(f"   File locking test error: {e}")
            results.append(("file_locking_error", False))

    return results


def run_comprehensive_tests():
    """Run all comprehensive tests."""
    print("=" * 70)
    print("Comprehensive Enhanced PID Validation Test Suite")
    print("=" * 70)

    all_results = []

    # Run validation scenario tests
    validation_results = test_comprehensive_validation_scenarios()
    all_results.extend(validation_results)

    # Run file locking tests
    locking_results = test_file_locking_scenarios()
    all_results.extend(locking_results)

    # Summary
    print("\\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in all_results if result)
    total = len(all_results)

    for test_name, result in all_results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name:<30} | {status}")

    print("-" * 70)
    print(
        f"Total: {passed}/{total} tests passed ({100 * passed // total if total > 0 else 0}%)"
    )

    if passed == total:
        print("🎉 All comprehensive tests passed!")
        return True
    print("❌ Some comprehensive tests failed")
    return False


if __name__ == "__main__":
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)
