#!/usr/bin/env python3
"""
Test script for the hardened Socket.IO daemon.

WHY: Verify that all hardening features work correctly including retry logic,
health monitoring, automatic recovery, and graceful degradation.
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

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.unified_paths import get_project_root

# Test configuration
TEST_RESULTS = []
DAEMON_SCRIPT = (
    Path(__file__).parent.parent
    / "src"
    / "claude_mpm"
    / "scripts"
    / "socketio_daemon_hardened.py"
)


def log_test(name: str, passed: bool, details: str = ""):
    """Log test results."""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {name}")
    if details:
        print(f"  Details: {details}")
    TEST_RESULTS.append({"name": name, "passed": passed, "details": details})


def check_port_listening(port: int, timeout: float = 5.0) -> bool:
    """Check if a port is listening."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(("localhost", port))
            sock.close()
            if result == 0:
                return True
        except:
            pass
        time.sleep(0.5)
    return False


def get_daemon_pid() -> int:
    """Get the daemon PID if running."""
    deployment_root = get_project_root()
    pid_file = deployment_root / ".claude-mpm" / "socketio-server.pid"

    if pid_file.exists():
        try:
            with pid_file.open() as f:
                return int(f.read().strip())
        except:
            pass
    return 0


def get_supervisor_pid() -> int:
    """Get the supervisor PID if running."""
    deployment_root = get_project_root()
    pid_file = deployment_root / ".claude-mpm" / "socketio-supervisor.pid"

    if pid_file.exists():
        try:
            with pid_file.open() as f:
                return int(f.read().strip())
        except:
            pass
    return 0


def get_daemon_port() -> int:
    """Get the daemon port if running."""
    deployment_root = get_project_root()
    port_file = deployment_root / ".claude-mpm" / "socketio-port"

    if port_file.exists():
        try:
            with port_file.open() as f:
                return int(f.read().strip())
        except:
            pass
    return 0


def get_metrics() -> dict:
    """Get daemon metrics."""
    deployment_root = get_project_root()
    metrics_file = deployment_root / ".claude-mpm" / ".claude-mpm/socketio-metrics.json"

    if metrics_file.exists():
        try:
            with metrics_file.open() as f:
                return json.load(f)
        except:
            pass
    return {}


def cleanup_daemon():
    """Ensure daemon is stopped and cleaned up."""
    print("Cleaning up any existing daemon...")
    subprocess.run(
        [sys.executable, str(DAEMON_SCRIPT), "stop"], capture_output=True, check=False
    )
    time.sleep(2)


def test_basic_startup():
    """Test 1: Basic daemon startup and shutdown."""
    print("\n" + "=" * 60)
    print("TEST 1: Basic Startup and Shutdown")
    print("=" * 60)

    # Start daemon
    result = subprocess.run(
        [sys.executable, str(DAEMON_SCRIPT), "start"],
        capture_output=True,
        text=True,
        check=False,
    )

    # Wait for startup
    time.sleep(3)

    # Check if running
    pid = get_daemon_pid()
    supervisor_pid = get_supervisor_pid()
    port = get_daemon_port()

    if pid > 0 and supervisor_pid > 0:
        log_test(
            "Daemon startup",
            True,
            f"Server PID: {pid}, Supervisor PID: {supervisor_pid}, Port: {port}",
        )

        # Check if port is listening
        if check_port_listening(port):
            log_test("Port listening", True, f"Port {port} is accepting connections")
        else:
            log_test(
                "Port listening", False, f"Port {port} is not accepting connections"
            )
    else:
        log_test("Daemon startup", False, f"Failed to start daemon: {result.stderr}")
        return

    # Check metrics
    metrics = get_metrics()
    if metrics and metrics.get("status") == "running":
        log_test("Metrics initialized", True, f"Status: {metrics.get('status')}")
    else:
        log_test("Metrics initialized", False, "Metrics not properly initialized")

    # Stop daemon
    result = subprocess.run(
        [sys.executable, str(DAEMON_SCRIPT), "stop"],
        capture_output=True,
        text=True,
        check=False,
    )

    time.sleep(2)

    # Verify stopped
    if get_daemon_pid() == 0 and get_supervisor_pid() == 0:
        log_test("Daemon shutdown", True, "Daemon stopped cleanly")
    else:
        log_test("Daemon shutdown", False, "Daemon did not stop properly")


def test_crash_recovery():
    """Test 2: Automatic recovery after crash."""
    print("\n" + "=" * 60)
    print("TEST 2: Crash Recovery")
    print("=" * 60)

    # Start daemon
    subprocess.run(
        [sys.executable, str(DAEMON_SCRIPT), "start"], capture_output=True, check=False
    )
    time.sleep(3)

    initial_pid = get_daemon_pid()
    supervisor_pid = get_supervisor_pid()
    port = get_daemon_port()

    if initial_pid == 0:
        log_test("Crash recovery setup", False, "Could not start daemon for test")
        return

    print(f"Initial server PID: {initial_pid}, Supervisor PID: {supervisor_pid}")

    # Kill the server process (not supervisor)
    try:
        os.kill(initial_pid, signal.SIGKILL)
        print(f"Killed server process {initial_pid}")
    except:
        log_test("Crash simulation", False, "Could not kill server process")
        return

    # Wait for supervisor to detect and restart
    print("Waiting for automatic recovery...")
    time.sleep(10)

    # Check if restarted with new PID
    new_pid = get_daemon_pid()
    new_supervisor_pid = get_supervisor_pid()

    if new_pid > 0 and new_pid != initial_pid and new_supervisor_pid == supervisor_pid:
        log_test(
            "Automatic recovery", True, f"Server restarted with new PID: {new_pid}"
        )

        # Check if port is still listening
        if check_port_listening(port):
            log_test(
                "Service continuity", True, f"Service recovered on same port {port}"
            )
        else:
            log_test(
                "Service continuity", False, "Service not listening after recovery"
            )

        # Check metrics for restart count
        metrics = get_metrics()
        if metrics.get("restarts", 0) > 0:
            log_test(
                "Restart tracking", True, f"Restarts tracked: {metrics['restarts']}"
            )
        else:
            log_test("Restart tracking", False, "Restart not tracked in metrics")
    else:
        log_test("Automatic recovery", False, f"Server not recovered. PID: {new_pid}")

    # Cleanup
    subprocess.run(
        [sys.executable, str(DAEMON_SCRIPT), "stop"], capture_output=True, check=False
    )
    time.sleep(2)


def test_health_monitoring():
    """Test 3: Health monitoring and metrics."""
    print("\n" + "=" * 60)
    print("TEST 3: Health Monitoring")
    print("=" * 60)

    # Set environment for faster health checks
    os.environ["SOCKETIO_HEALTH_CHECK_INTERVAL"] = "5"

    # Start daemon
    subprocess.run(
        [sys.executable, str(DAEMON_SCRIPT), "start"], capture_output=True, check=False
    )
    time.sleep(3)

    if get_daemon_pid() == 0:
        log_test("Health monitoring setup", False, "Could not start daemon")
        return

    # Wait for health checks
    print("Waiting for health checks to run...")
    time.sleep(10)

    # Check metrics
    metrics = get_metrics()

    if metrics:
        health_passed = metrics.get("health_checks_passed", 0)
        if health_passed > 0:
            log_test(
                "Health checks running", True, f"Health checks passed: {health_passed}"
            )
        else:
            log_test("Health checks running", False, "No health checks recorded")

        if metrics.get("status") == "healthy" or metrics.get("status") == "running":
            log_test("Health status", True, f"Status: {metrics['status']}")
        else:
            log_test(
                "Health status", False, f"Unexpected status: {metrics.get('status')}"
            )

        if metrics.get("last_health_check"):
            log_test(
                "Health check timestamp",
                True,
                f"Last check: {metrics['last_health_check']}",
            )
        else:
            log_test("Health check timestamp", False, "No health check timestamp")
    else:
        log_test("Health monitoring", False, "No metrics available")

    # Cleanup
    subprocess.run(
        [sys.executable, str(DAEMON_SCRIPT), "stop"], capture_output=True, check=False
    )
    time.sleep(2)


def test_configuration():
    """Test 4: Configuration through environment variables."""
    print("\n" + "=" * 60)
    print("TEST 4: Configuration")
    print("=" * 60)

    # Set custom configuration
    os.environ["SOCKETIO_MAX_RETRIES"] = "5"
    os.environ["SOCKETIO_PORT_START"] = "9000"
    os.environ["SOCKETIO_PORT_END"] = "9010"
    os.environ["SOCKETIO_LOG_LEVEL"] = "DEBUG"

    # Start daemon
    result = subprocess.run(
        [sys.executable, str(DAEMON_SCRIPT), "start"],
        capture_output=True,
        text=True,
        check=False,
    )

    time.sleep(3)

    port = get_daemon_port()

    # Check if using custom port range
    if 9000 <= port <= 9010:
        log_test("Custom port range", True, f"Using port {port} from custom range")
    else:
        log_test(
            "Custom port range", False, f"Port {port} not in custom range 9000-9010"
        )

    # Check status output for configuration
    result = subprocess.run(
        [sys.executable, str(DAEMON_SCRIPT), "status"],
        capture_output=True,
        text=True,
        check=False,
    )

    if "Max Retries: 5" in result.stdout:
        log_test("Custom max retries", True, "Configuration applied")
    else:
        log_test("Custom max retries", False, "Configuration not reflected in status")

    # Cleanup
    subprocess.run(
        [sys.executable, str(DAEMON_SCRIPT), "stop"], capture_output=True, check=False
    )
    time.sleep(2)

    # Reset environment
    for key in [
        "SOCKETIO_MAX_RETRIES",
        "SOCKETIO_PORT_START",
        "SOCKETIO_PORT_END",
        "SOCKETIO_LOG_LEVEL",
    ]:
        if key in os.environ:
            del os.environ[key]


def test_concurrent_protection():
    """Test 5: Protection against concurrent instances."""
    print("\n" + "=" * 60)
    print("TEST 5: Concurrent Instance Protection")
    print("=" * 60)

    # Start first instance
    subprocess.run(
        [sys.executable, str(DAEMON_SCRIPT), "start"], capture_output=True, check=False
    )
    time.sleep(3)

    first_pid = get_daemon_pid()
    if first_pid == 0:
        log_test("First instance", False, "Could not start first instance")
        return

    # Try to start second instance
    subprocess.run(
        [sys.executable, str(DAEMON_SCRIPT), "start"],
        capture_output=True,
        text=True,
        check=False,
    )

    # Check that second instance was prevented
    second_pid = get_daemon_pid()

    if second_pid == first_pid:
        log_test(
            "Concurrent protection",
            True,
            "Second instance prevented, same PID maintained",
        )
    else:
        log_test(
            "Concurrent protection",
            False,
            f"Second instance started with PID {second_pid}",
        )

    # Cleanup
    subprocess.run(
        [sys.executable, str(DAEMON_SCRIPT), "stop"], capture_output=True, check=False
    )
    time.sleep(2)


def main():
    """Run all tests."""
    print("=" * 70)
    print("HARDENED SOCKET.IO DAEMON TEST SUITE")
    print("=" * 70)
    print(f"Testing daemon script: {DAEMON_SCRIPT}")
    print(f"Test started: {datetime.now(timezone.utc)}")

    # Ensure clean state
    cleanup_daemon()

    # Run tests
    tests = [
        test_basic_startup,
        test_crash_recovery,
        test_health_monitoring,
        test_configuration,
        test_concurrent_protection,
    ]

    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"\n❌ Test {test.__name__} failed with exception: {e}")
            import traceback

            traceback.print_exc()
        finally:
            # Ensure cleanup between tests
            cleanup_daemon()

    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for r in TEST_RESULTS if r["passed"])
    failed = sum(1 for r in TEST_RESULTS if not r["passed"])

    print(f"Total Tests: {len(TEST_RESULTS)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if failed > 0:
        print("\nFailed Tests:")
        for result in TEST_RESULTS:
            if not result["passed"]:
                print(f"  - {result['name']}: {result['details']}")

    # Final cleanup
    cleanup_daemon()

    # Exit code based on results
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
