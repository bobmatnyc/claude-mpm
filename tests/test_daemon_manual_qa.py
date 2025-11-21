#!/usr/bin/env python3
"""
Manual QA test script that uses process background execution for testing.
"""

import json
import os
import signal
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import contextlib

from claude_mpm.core.unified_paths import get_project_root

DAEMON_SCRIPT = (
    Path(__file__).parent.parent
    / "src"
    / "claude_mpm"
    / "scripts"
    / "socketio_daemon_hardened.py"
)
TEST_RESULTS = []


class DaemonTestManager:
    """Manages daemon testing with proper background process handling."""

    def __init__(self):
        self.deployment_root = get_project_root()
        self.daemon_process = None

    def start_daemon_background(self, timeout=15):
        """Start daemon in background and wait for it to be ready."""
        try:
            # Start daemon in background
            self.daemon_process = subprocess.Popen(
                [sys.executable, str(DAEMON_SCRIPT), "start"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Wait for daemon to be ready
            start_time = time.time()
            while time.time() - start_time < timeout:
                server_pid, supervisor_pid, port = self.get_daemon_info()
                if server_pid > 0 and supervisor_pid > 0 and port > 0:
                    if self.check_port_listening(port, timeout=2):
                        return True
                time.sleep(1)

            return False

        except Exception as e:
            print(f"Error starting daemon: {e}")
            return False

    def stop_daemon(self):
        """Stop the daemon."""
        try:
            result = subprocess.run(
                [sys.executable, str(DAEMON_SCRIPT), "stop"],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            time.sleep(2)
            return result.returncode == 0
        except Exception as e:
            print(f"Error stopping daemon: {e}")
            return False
        finally:
            if self.daemon_process:
                try:
                    self.daemon_process.terminate()
                    self.daemon_process.wait(timeout=5)
                except:
                    with contextlib.suppress(Exception):
                        self.daemon_process.kill()
                self.daemon_process = None

    def get_daemon_info(self):
        """Get daemon process info."""
        server_pid = 0
        supervisor_pid = 0
        port = 0

        # Get server PID
        pid_file = self.deployment_root / ".claude-mpm" / "socketio-server.pid"
        if pid_file.exists():
            try:
                with pid_file.open() as f:
                    server_pid = int(f.read().strip())
            except Exception:
                pass

        # Get supervisor PID
        supervisor_pid_file = (
            self.deployment_root / ".claude-mpm" / "socketio-supervisor.pid"
        )
        if supervisor_pid_file.exists():
            try:
                with supervisor_pid_file.open() as f:
                    supervisor_pid = int(f.read().strip())
            except Exception:
                pass

        # Get port
        port_file = self.deployment_root / ".claude-mpm" / "socketio-port"
        if port_file.exists():
            try:
                with port_file.open() as f:
                    port = int(f.read().strip())
            except Exception:
                pass

        return server_pid, supervisor_pid, port

    def check_port_listening(self, port: int, timeout: float = 5.0) -> bool:
        """Check if a port is listening."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1.0)
                result = sock.connect_ex(("localhost", port))
                sock.close()
                if result == 0:
                    return True
            except Exception:
                pass
            time.sleep(0.2)
        return False

    def cleanup(self):
        """Clean up all daemon processes and files."""
        self.stop_daemon()

        # Clean up files
        cleanup_files = [
            ".claude-mpm/socketio-server.pid",
            ".claude-mpm/socketio-supervisor.pid",
            ".claude-mpm/socketio-server.lock",
            ".claude-mpm/socketio-port",
        ]

        for file_path in cleanup_files:
            with contextlib.suppress(Exception):
                (self.deployment_root / file_path).unlink(missing_ok=True)

        # Kill any remaining processes
        try:
            result = subprocess.run(
                ["pgrep", "-f", "socketio_daemon"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.stdout.strip():
                pids = result.stdout.strip().split("\n")
                for pid in pids:
                    with contextlib.suppress(ValueError, ProcessLookupError):
                        os.kill(int(pid), signal.SIGKILL)
        except Exception:
            pass

    def get_metrics(self) -> dict:
        """Get daemon metrics."""
        metrics_file = (
            self.deployment_root / ".claude-mpm" / ".claude-mpm/socketio-metrics.json"
        )
        if metrics_file.exists():
            try:
                with metrics_file.open() as f:
                    return json.load(f)
            except Exception:
                pass
        return {}


def log_test(name: str, passed: bool, details: str = ""):
    """Log test results."""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {name}")
    if details:
        print(f"  Details: {details}")
    TEST_RESULTS.append({"name": name, "passed": passed, "details": details})


def test_basic_functionality():
    """Test basic daemon functionality."""
    print("\n=== BASIC FUNCTIONALITY TEST ===")

    manager = DaemonTestManager()

    try:
        # Test startup
        print("Starting daemon...")
        if manager.start_daemon_background():
            server_pid, supervisor_pid, port = manager.get_daemon_info()
            log_test(
                "Daemon startup",
                True,
                f"Server PID: {server_pid}, Supervisor: {supervisor_pid}, Port: {port}",
            )

            # Test port accessibility
            if manager.check_port_listening(port):
                log_test(
                    "Port accessibility", True, f"Port {port} accepting connections"
                )
            else:
                log_test("Port accessibility", False, f"Port {port} not responding")

            # Test status command
            result = subprocess.run(
                [sys.executable, str(DAEMON_SCRIPT), "status"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if result.returncode == 0 and "RUNNING" in result.stdout:
                log_test("Status command", True, "Status shows running state")
            else:
                log_test("Status command", False, "Status command failed")

            # Test metrics
            metrics = manager.get_metrics()
            if metrics and metrics.get("status"):
                log_test("Metrics generation", True, f"Status: {metrics.get('status')}")
            else:
                log_test("Metrics generation", False, "No metrics generated")

        else:
            log_test("Daemon startup", False, "Failed to start daemon")

    finally:
        manager.cleanup()


def test_crash_recovery():
    """Test crash recovery functionality."""
    print("\n=== CRASH RECOVERY TEST ===")

    manager = DaemonTestManager()

    try:
        # Start daemon
        if not manager.start_daemon_background():
            log_test("Recovery setup", False, "Could not start daemon")
            return

        initial_server_pid, supervisor_pid, _port = manager.get_daemon_info()
        print(
            f"Initial: Server PID {initial_server_pid}, Supervisor PID {supervisor_pid}"
        )

        # Kill server process
        try:
            os.kill(initial_server_pid, signal.SIGKILL)
            log_test(
                "Crash simulation", True, f"Killed server process {initial_server_pid}"
            )
        except Exception as e:
            log_test("Crash simulation", False, f"Could not kill process: {e}")
            return

        # Wait for recovery
        print("Waiting for automatic recovery...")
        recovery_timeout = 15
        start_time = time.time()

        while time.time() - start_time < recovery_timeout:
            time.sleep(2)
            new_server_pid, _new_supervisor_pid, new_port = manager.get_daemon_info()

            if new_server_pid > 0 and new_server_pid != initial_server_pid:
                log_test(
                    "Automatic recovery", True, f"New server PID: {new_server_pid}"
                )

                if manager.check_port_listening(new_port):
                    log_test(
                        "Service continuity",
                        True,
                        f"Service restored on port {new_port}",
                    )
                else:
                    log_test("Service continuity", False, "Service not restored")

                # Check restart tracking
                metrics = manager.get_metrics()
                if metrics.get("restarts", 0) > 0:
                    log_test(
                        "Restart tracking", True, f"Restarts: {metrics['restarts']}"
                    )
                else:
                    log_test("Restart tracking", False, "Restart not tracked")

                return

        log_test("Automatic recovery", False, "Recovery timed out")

    finally:
        manager.cleanup()


def test_configuration():
    """Test configuration functionality."""
    print("\n=== CONFIGURATION TEST ===")

    manager = DaemonTestManager()

    # Set custom configuration
    os.environ["SOCKETIO_PORT_START"] = "9600"
    os.environ["SOCKETIO_PORT_END"] = "9610"
    os.environ["SOCKETIO_MAX_RETRIES"] = "8"

    try:
        if manager.start_daemon_background():
            _, _, port = manager.get_daemon_info()

            if 9600 <= port <= 9610:
                log_test(
                    "Custom port configuration",
                    True,
                    f"Using port {port} from custom range",
                )
            else:
                log_test(
                    "Custom port configuration",
                    False,
                    f"Port {port} not in custom range",
                )

            # Check status output
            result = subprocess.run(
                [sys.executable, str(DAEMON_SCRIPT), "status"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if "Max Retries: 8" in result.stdout:
                log_test(
                    "Configuration reflection", True, "Custom config shown in status"
                )
            else:
                log_test(
                    "Configuration reflection", False, "Custom config not reflected"
                )
        else:
            log_test(
                "Configuration test setup",
                False,
                "Could not start daemon with custom config",
            )

    finally:
        for key in ["SOCKETIO_PORT_START", "SOCKETIO_PORT_END", "SOCKETIO_MAX_RETRIES"]:
            if key in os.environ:
                del os.environ[key]
        manager.cleanup()


def test_health_monitoring():
    """Test health monitoring functionality."""
    print("\n=== HEALTH MONITORING TEST ===")

    manager = DaemonTestManager()

    # Set faster health checks for testing
    os.environ["SOCKETIO_HEALTH_CHECK_INTERVAL"] = "3"
    os.environ["SOCKETIO_METRICS_ENABLED"] = "true"

    try:
        if manager.start_daemon_background():
            # Wait for health checks to run
            print("Waiting for health checks...")
            time.sleep(8)

            metrics = manager.get_metrics()

            if metrics and metrics.get("health_checks_passed", 0) > 0:
                log_test(
                    "Health checks execution",
                    True,
                    f"Passed: {metrics['health_checks_passed']}",
                )
            else:
                log_test("Health checks execution", False, "No health checks recorded")

            if metrics.get("status") in ["healthy", "running"]:
                log_test("Health status tracking", True, f"Status: {metrics['status']}")
            else:
                log_test(
                    "Health status tracking",
                    False,
                    f"Unexpected status: {metrics.get('status')}",
                )
        else:
            log_test("Health monitoring setup", False, "Could not start daemon")

    finally:
        for key in ["SOCKETIO_HEALTH_CHECK_INTERVAL", "SOCKETIO_METRICS_ENABLED"]:
            if key in os.environ:
                del os.environ[key]
        manager.cleanup()


def main():
    """Run manual QA tests."""
    print("HARDENED SOCKET.IO DAEMON - MANUAL QA TESTS")
    print("=" * 50)
    print(f"Test started: {datetime.now(timezone.utc)}")

    manager = DaemonTestManager()
    manager.cleanup()  # Clean start

    try:
        test_basic_functionality()
        test_crash_recovery()
        test_configuration()
        test_health_monitoring()

    except KeyboardInterrupt:
        print("\nTests interrupted by user")
    except Exception as e:
        print(f"\nTest error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        manager.cleanup()

    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)

    if TEST_RESULTS:
        passed = sum(1 for r in TEST_RESULTS if r["passed"])
        total = len(TEST_RESULTS)

        print(f"Passed: {passed}/{total} ({passed / total * 100:.1f}%)")

        if passed < total:
            print("\nFailed tests:")
            for result in TEST_RESULTS:
                if not result["passed"]:
                    print(f"  ❌ {result['name']}: {result['details']}")

        # Production readiness assessment
        critical_tests = [
            "Daemon startup",
            "Port accessibility",
            "Status command",
            "Automatic recovery",
            "Service continuity",
        ]

        critical_passed = sum(
            1
            for r in TEST_RESULTS
            if r["passed"] and any(ct in r["name"] for ct in critical_tests)
        )
        critical_total = sum(
            1 for r in TEST_RESULTS if any(ct in r["name"] for ct in critical_tests)
        )

        if critical_total > 0:
            critical_percentage = critical_passed / critical_total * 100
            print(
                f"\nCritical Tests: {critical_passed}/{critical_total} ({critical_percentage:.1f}%)"
            )

            if critical_percentage >= 90:
                print("✅ PRODUCTION READY - Critical functionality validated")
            elif critical_percentage >= 75:
                print(
                    "⚠️  PRODUCTION READY WITH MONITORING - Most critical tests passed"
                )
            else:
                print("❌ NOT PRODUCTION READY - Critical issues detected")

        return 0 if passed == total else 1
    print("No tests executed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
