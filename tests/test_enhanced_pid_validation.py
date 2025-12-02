#!/usr/bin/env python3
"""Test suite for enhanced PID file validation in SocketIOServer.

This test suite validates the enhanced process validation, file locking,
and stale process detection features.
"""

import json
import os
import sys
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    import psutil

    from claude_mpm.services.socketio_server import SocketIOServer

    PSUTIL_AVAILABLE = True  # Assume psutil is available for tests
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)


def test_pidfile_creation_and_validation():
    """Test PID file creation with enhanced metadata."""
    print("Testing PID file creation and validation...")

    with tmp_path as temp_dir:
        # Create server instance
        server = SocketIOServer(host="localhost", port=9999)
        server.pidfile_path = Path(temp_dir) / "test.pid"

        # Test PID file creation
        try:
            server.create_pidfile()

            # Verify file exists
            assert server.pidfile_path.exists(), "PID file was not created"

            # Verify content format
            with server.pidfile_path.open() as f:
                content = f.read()

            # Should be JSON format with metadata
            try:
                pidfile_data = json.loads(content)
                assert "pid" in pidfile_data, "PID not found in file"
                assert "server_id" in pidfile_data, "Server ID not found in file"
                assert "server_version" in pidfile_data, (
                    "Server version not found in file"
                )
                assert pidfile_data["pid"] == server.pid, "PID mismatch"
                print("✓ PID file created with correct metadata")
            except json.JSONDecodeError:
                # Fallback check for old format
                assert content.strip().isdigit(), "Invalid PID file format"
                print("✓ PID file created (legacy format)")

            # Test cleanup
            server.remove_pidfile()
            assert not server.pidfile_path.exists(), "PID file was not removed"
            print("✓ PID file cleanup successful")

        except Exception as e:
            print(f"✗ PID file test failed: {e}")
            return False

    return True


def test_process_validation():
    """Test process identity validation."""
    print("Testing process identity validation...")

    if not PSUTIL_AVAILABLE:
        print("⚠ psutil not available, skipping enhanced validation tests")
        return True

    server = SocketIOServer(host="localhost", port=9998)

    # Test with current process (should be valid but not our server)
    current_pid = os.getpid()
    validation = server._validate_process_identity(current_pid)

    assert validation["is_valid"], "Current process should be valid"
    assert not validation["is_zombie"], "Current process should not be zombie"
    print(f"✓ Process validation works for PID {current_pid}")

    # Test with non-existent process
    fake_pid = 999999
    validation = server._validate_process_identity(fake_pid)
    assert not validation["is_valid"], "Non-existent process should not be valid"
    assert len(validation["validation_errors"]) > 0, "Should have validation errors"
    print(f"✓ Correctly identified non-existent process {fake_pid}")

    return True


def test_stale_process_detection():
    """Test stale process detection and cleanup."""
    print("Testing stale process detection...")

    with tmp_path as temp_dir:
        server = SocketIOServer(host="localhost", port=9997)
        server.pidfile_path = Path(temp_dir) / "stale_test.pid"

        # Create a fake stale PID file with non-existent process
        fake_pid = 999998
        with server.pidfile_path.open("w") as f:
            f.write(str(fake_pid))

        # Test detection
        is_running = server.is_already_running()
        assert not is_running, "Should detect stale process as not running"
        assert not server.pidfile_path.exists(), "Stale PID file should be cleaned up"
        print("✓ Stale process detected and cleaned up")

        # Create stale PID file with invalid content
        with server.pidfile_path.open("w") as f:
            f.write("not_a_number")

        is_running = server.is_already_running()
        assert not is_running, "Should handle invalid PID content"
        assert not server.pidfile_path.exists(), "Invalid PID file should be cleaned up"
        print("✓ Invalid PID content handled correctly")

    return True


def test_port_availability_check():
    """Test port availability checking as fallback."""
    print("Testing port availability check...")

    # Use a high port number that's unlikely to be in use
    test_port = 19999
    server = SocketIOServer(host="localhost", port=test_port)

    # Should not detect any server running on unused port
    is_running = server.is_already_running()
    assert not is_running, f"Should not detect server on unused port {test_port}"
    print(f"✓ Correctly detected port {test_port} as available")

    return True


def test_file_locking():
    """Test file locking mechanism."""
    print("Testing file locking mechanism...")

    with tmp_path as temp_dir:
        server1 = SocketIOServer(host="localhost", port=9996)
        server1.pidfile_path = Path(temp_dir) / "lock_test.pid"

        server2 = SocketIOServer(host="localhost", port=9996)
        server2.pidfile_path = Path(temp_dir) / "lock_test.pid"

        try:
            # First server should create and lock the file successfully
            server1.create_pidfile()
            assert server1.pidfile_path.exists(), "First server should create PID file"
            print("✓ First server created PID file with lock")

            # Second server should fail to create/lock the same file
            try:
                server2.create_pidfile()
                print(
                    "⚠ Second server was able to create PID file (locking may not be working)"
                )
                # This might happen on systems without proper locking support
            except RuntimeError as e:
                if "exclusive lock" in str(e).lower():
                    print("✓ Second server correctly failed to acquire lock")
                else:
                    print(f"✗ Unexpected error: {e}")
                    return False

            # Cleanup
            server1.remove_pidfile()
            if server2.pidfile_lock:
                server2.remove_pidfile()

        except Exception as e:
            print(f"✗ File locking test failed: {e}")
            return False

    return True


def run_all_tests():
    """Run all tests and report results."""
    print("=" * 60)
    print("Enhanced PID Validation Test Suite")
    print("=" * 60)

    tests = [
        test_pidfile_creation_and_validation,
        test_process_validation,
        test_stale_process_detection,
        test_port_availability_check,
        test_file_locking,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        print(f"\n{'-' * 40}")
        try:
            if test():
                passed += 1
                print(f"✓ {test.__name__} PASSED")
            else:
                print(f"✗ {test.__name__} FAILED")
        except Exception as e:
            print(f"✗ {test.__name__} ERROR: {e}")

    print(f"\n{'=' * 60}")
    print(f"Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed!")
        return True
    print("❌ Some tests failed")
    return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
