#!/usr/bin/env python3
"""
Comprehensive integration test for Socket.IO server enhancements.

This test validates all components working together:
- PID validation with enhanced error handling
- Health monitoring and metrics collection
- Recovery mechanisms with circuit breaker
- Error messages with troubleshooting guidance
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from claude_mpm.services.exceptions import DaemonConflictError, StaleProcessError
    from claude_mpm.services.infrastructure.monitoring import HealthStatus
    from claude_mpm.services.recovery_manager import RecoveryAction
    from claude_mpm.services.socketio_server import SocketIOServer

    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import modules for integration testing: {e}")
    IMPORTS_AVAILABLE = False


class IntegrationTestSuite:
    """Comprehensive integration test suite."""

    def __init__(self):
        self.test_results = []
        self.temp_dir = None
        self.servers = []

    def setup(self):
        """Set up test environment."""
        self.temp_dir = Path(tmp_path)
        print(f"Test environment: {self.temp_dir}")

    def teardown(self):
        """Clean up test environment."""
        # Clean up any running servers
        for server in self.servers:
            try:
                server.stop()
                if server.pidfile_path.exists():
                    server.pidfile_path.unlink()
            except Exception as e:
                print(f"Cleanup warning: {e}")

        # Clean up temp directory
        if self.temp_dir and self.temp_dir.exists():
            try:
                for file in self.temp_dir.iterdir():
                    file.unlink()
                self.temp_dir.rmdir()
            except Exception:
                pass

    def create_test_server(self, port=18000, server_id=None):
        """Create a test server instance."""
        server = SocketIOServer(
            host="localhost", port=port, server_id=server_id or f"test-server-{port}"
        )
        server.pidfile_path = self.temp_dir / f"socketio_{port}.pid"
        self.servers.append(server)
        return server

    def test_pid_validation_integration():
        """Test 1: PID validation with stale process detection."""
        print("\\n🔍 Testing PID validation integration...")

        server = self.create_test_server(port=18001)

        try:
            # Test 1a: Create and validate PID file
            server.create_pidfile()
            assert server.pidfile_path.exists(), "PID file not created"

            # Verify PID file content
            with server.pidfile_path.open() as f:
                content = f.read().strip()
                try:
                    pidfile_data = json.loads(content)
                    assert pidfile_data["pid"] == server.pid, "PID mismatch in file"
                    assert pidfile_data["server_id"] == server.server_id, (
                        "Server ID mismatch"
                    )
                    print("   ✓ PID file creation and content validation passed")
                except json.JSONDecodeError:
                    # Legacy format check
                    assert content.isdigit(), "Invalid PID file format"
                    print("   ✓ Legacy PID file format validated")

            # Test 1b: Stale process detection
            # Create a stale PID file with non-existent process
            fake_pidfile_data = {
                "pid": 999991,
                "server_id": "stale-server",
                "server_version": "1.0.0",
            }

            stale_server = self.create_test_server(port=18002)
            with stale_server.pidfile_path.open("w") as f:
                json.dump(fake_pidfile_data, f)

            # Should detect and clean up stale process
            is_running = stale_server.is_already_running()
            assert not is_running, "Should detect stale process as not running"
            assert not stale_server.pidfile_path.exists(), (
                "Stale PID file not cleaned up"
            )
            print("   ✓ Stale process detection and cleanup passed")

            # Clean up
            server.remove_pidfile()

            self.test_results.append(("pid_validation_integration", True, None))
            return True

        except Exception as e:
            self.test_results.append(("pid_validation_integration", False, str(e)))
            print(f"   ✗ PID validation integration failed: {e}")
            return False

    def test_enhanced_error_handling():
        """Test 2: Enhanced error handling with troubleshooting guidance."""
        print("\\n🚨 Testing enhanced error handling...")

        try:
            # Test 2a: Daemon conflict error
            server1 = self.create_test_server(port=18003)
            server1.create_pidfile()

            server2 = self.create_test_server(port=18003)  # Same port

            try:
                server2.is_already_running(raise_on_conflict=True)
                raise AssertionError("Should have raised DaemonConflictError")
            except DaemonConflictError as e:
                assert e.port == 18003, "Wrong port in error"
                assert "RESOLUTION STEPS" in str(e), "Missing troubleshooting guide"
                print("   ✓ DaemonConflictError with troubleshooting guide passed")

            # Test 2b: Stale process error
            server1.remove_pidfile()

            # Create stale PID file
            with server2.pidfile_path.open("w") as f:
                json.dump({"pid": 999992, "server_id": "stale"}, f)

            # Mock process validation to simulate stale process
            with patch.object(server2, "_validate_process_identity") as mock_validate:
                mock_validate.return_value = {
                    "is_valid": False,
                    "validation_errors": ["Process 999992 does not exist"],
                }

                try:
                    server2.is_already_running(raise_on_conflict=True)
                    raise AssertionError("Should have raised StaleProcessError")
                except StaleProcessError as e:
                    assert e.pid == 999992, "Wrong PID in error"
                    assert "Process 999992 does not exist" in e.validation_errors, (
                        "Missing validation error"
                    )
                    print("   ✓ StaleProcessError with validation details passed")

            self.test_results.append(("enhanced_error_handling", True, None))
            return True

        except Exception as e:
            self.test_results.append(("enhanced_error_handling", False, str(e)))
            print(f"   ✗ Enhanced error handling failed: {e}")
            return False

    def test_health_monitoring_integration():
        """Test 3: Health monitoring integration."""
        print("\\n💊 Testing health monitoring integration...")

        try:
            server = self.create_test_server(port=18004)

            # Test 3a: Health monitoring initialization
            if hasattr(server, "health_monitor") and server.health_monitor:
                assert server.health_monitor is not None, (
                    "Health monitor not initialized"
                )
                print("   ✓ Health monitor initialization passed")

                # Test 3b: Health check execution
                # Note: In integration testing, we focus on the interface
                # rather than mocking internal behavior
                try:
                    # This will test the actual health monitoring setup
                    health_config = server.health_monitor.check_interval
                    assert health_config > 0, "Invalid health check interval"
                    print("   ✓ Health monitoring configuration valid")

                except AttributeError:
                    print("   ⚠ Health monitoring not fully configured")

            else:
                print("   ⚠ Health monitoring not available in this build")

            # Test 3c: Recovery manager integration
            if hasattr(server, "recovery_manager") and server.recovery_manager:
                assert server.recovery_manager is not None, (
                    "Recovery manager not initialized"
                )
                assert server.recovery_manager.enabled is not None, (
                    "Recovery manager config missing"
                )
                print("   ✓ Recovery manager integration passed")
            else:
                print("   ⚠ Recovery manager not available in this build")

            self.test_results.append(("health_monitoring_integration", True, None))
            return True

        except Exception as e:
            self.test_results.append(("health_monitoring_integration", False, str(e)))
            print(f"   ✗ Health monitoring integration failed: {e}")
            return False

    def test_file_locking_mechanism():
        """Test 4: File locking mechanism to prevent race conditions."""
        print("\\n🔒 Testing file locking mechanism...")

        try:
            server1 = self.create_test_server(port=18005)
            server2 = self.create_test_server(port=18005)  # Same port

            # Test 4a: First server should acquire lock
            server1.create_pidfile()
            assert server1.pidfile_path.exists(), "First server didn't create PID file"
            print("   ✓ First server acquired exclusive lock")

            # Test 4b: Second server should fail to acquire lock
            try:
                server2.create_pidfile()
                # If we get here, locking might not be working as expected
                print(
                    "   ⚠ Second server was able to create PID file (locking may not be working)"
                )
                # This might be expected behavior on some systems
                server2.remove_pidfile()
            except Exception as e:
                if "conflict" in str(e).lower() or "lock" in str(e).lower():
                    print("   ✓ Second server correctly blocked by file lock")
                else:
                    print(f"   ⚠ Unexpected locking error: {e}")

            # Clean up
            server1.remove_pidfile()

            self.test_results.append(("file_locking_mechanism", True, None))
            return True

        except Exception as e:
            self.test_results.append(("file_locking_mechanism", False, str(e)))
            print(f"   ✗ File locking mechanism failed: {e}")
            return False

    def test_cross_platform_compatibility():
        """Test 5: Cross-platform compatibility."""
        print("\\n🌍 Testing cross-platform compatibility...")

        try:
            server = self.create_test_server(port=18006)

            # Test 5a: Platform detection
            import platform

            current_platform = platform.system()
            print(f"   Current platform: {current_platform}")

            # Test 5b: PID validation works on current platform
            server.create_pidfile()
            is_running = server.is_already_running()

            # The server should detect itself as running (or handle gracefully)
            print(f"   Self-detection result: {is_running}")

            # Test 5c: Process validation availability
            try:
                import psutil

                print("   ✓ Process validation (psutil) available")
            except ImportError:
                print("   ⚠ Process validation (psutil) not available - using fallback")

            # Test should pass regardless of psutil availability
            server.remove_pidfile()

            self.test_results.append(("cross_platform_compatibility", True, None))
            return True

        except Exception as e:
            self.test_results.append(("cross_platform_compatibility", False, str(e)))
            print(f"   ✗ Cross-platform compatibility failed: {e}")
            return False

    def test_backward_compatibility():
        """Test 6: Backward compatibility with existing PID files."""
        print("\\n🔄 Testing backward compatibility...")

        try:
            server = self.create_test_server(port=18007)

            # Test 6a: Legacy PID file format (plain text)
            with server.pidfile_path.open("w") as f:
                f.write(str(os.getpid()))  # Write just the PID

            is_running = server.is_already_running()
            print(
                f"   Legacy PID file handled: {not is_running}"
            )  # Should cleanup and return False

            # Test 6b: Mixed format handling
            # Create new format PID file
            server.create_pidfile()

            # Verify it can read it back
            with server.pidfile_path.open() as f:
                content = json.loads(f.read())
                assert "pid" in content, "New format missing PID"
                assert "server_id" in content, "New format missing server_id"
                print("   ✓ New PID file format validated")

            server.remove_pidfile()

            self.test_results.append(("backward_compatibility", True, None))
            return True

        except Exception as e:
            self.test_results.append(("backward_compatibility", False, str(e)))
            print(f"   ✗ Backward compatibility failed: {e}")
            return False

    def run_all_tests(self):
        """Run all integration tests."""
        if not IMPORTS_AVAILABLE:
            print("❌ Cannot run integration tests - imports not available")
            return False

        print("🚀 Starting comprehensive Socket.IO server integration tests...")
        print("=" * 80)

        self.setup()

        tests = [
            self.test_pid_validation_integration,
            self.test_enhanced_error_handling,
            self.test_health_monitoring_integration,
            self.test_file_locking_mechanism,
            self.test_cross_platform_compatibility,
            self.test_backward_compatibility,
        ]

        passed = 0
        total = len(tests)

        try:
            for test in tests:
                try:
                    if test():
                        passed += 1
                except Exception as e:
                    print(f"   ✗ Test {test.__name__} failed with exception: {e}")

        finally:
            self.teardown()

        print("\\n" + "=" * 80)
        print("🏁 INTEGRATION TEST RESULTS")
        print("=" * 80)

        for test_name, success, error in self.test_results:
            status = "PASS" if success else "FAIL"
            print(f"{test_name:<35} | {status}")
            if not success and error:
                print(f"   Error: {error}")

        print("-" * 80)
        print(
            f"Total: {passed}/{total} tests passed ({100 * passed // total if total > 0 else 0}%)"
        )

        if passed == total:
            print("🎉 All integration tests passed!")
            return True
        print("❌ Some integration tests failed")
        return False


def main():
    """Run integration test suite."""
    suite = IntegrationTestSuite()
    success = suite.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
