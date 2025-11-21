#!/usr/bin/env python3
"""
Focused QA tests for hardened Socket.IO daemon - Basic functionality only.
"""

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


def log_test(name: str, passed: bool, details: str = ""):
    """Log test results."""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {name}")
    if details:
        print(f"  Details: {details}")
    TEST_RESULTS.append({"name": name, "passed": passed, "details": details})


def cleanup_daemon():
    """Clean up daemon processes and files."""
    subprocess.run(
        [sys.executable, str(DAEMON_SCRIPT), "stop"], capture_output=True, check=False
    )
    time.sleep(2)

    # Clean up files
    deployment_root = get_project_root()
    cleanup_files = [
        ".claude-mpm/socketio-server.pid",
        ".claude-mpm/socketio-supervisor.pid",
        ".claude-mpm/socketio-server.lock",
        ".claude-mpm/socketio-port",
    ]

    for file_path in cleanup_files:
        with contextlib.suppress(Exception):
            (deployment_root / file_path).unlink(missing_ok=True)


def get_daemon_info():
    """Get daemon process info."""
    deployment_root = get_project_root()

    server_pid = 0
    supervisor_pid = 0
    port = 0

    # Get server PID
    pid_file = deployment_root / ".claude-mpm" / "socketio-server.pid"
    if pid_file.exists():
        try:
            with pid_file.open() as f:
                server_pid = int(f.read().strip())
        except Exception:
            pass

    # Get supervisor PID
    supervisor_pid_file = deployment_root / ".claude-mpm" / "socketio-supervisor.pid"
    if supervisor_pid_file.exists():
        try:
            with supervisor_pid_file.open() as f:
                supervisor_pid = int(f.read().strip())
        except Exception:
            pass

    # Get port
    port_file = deployment_root / ".claude-mpm" / "socketio-port"
    if port_file.exists():
        try:
            with port_file.open() as f:
                port = int(f.read().strip())
        except Exception:
            pass

    return server_pid, supervisor_pid, port


def check_port_listening(port: int, timeout: float = 5.0) -> bool:
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


def test_basic_startup_shutdown():
    """Test basic daemon startup and shutdown."""
    print("\n=== BASIC STARTUP/SHUTDOWN TEST ===")

    # Test startup
    print("Starting daemon...")
    result = subprocess.run(
        [sys.executable, str(DAEMON_SCRIPT), "start"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    time.sleep(5)  # Wait for startup

    server_pid, supervisor_pid, port = get_daemon_info()

    if server_pid > 0 and supervisor_pid > 0 and port > 0:
        log_test(
            "Daemon startup",
            True,
            f"Server PID: {server_pid}, Supervisor: {supervisor_pid}, Port: {port}",
        )

        # Test port listening
        if check_port_listening(port):
            log_test("Port accessibility", True, f"Port {port} accepting connections")
        else:
            log_test("Port accessibility", False, f"Port {port} not responding")

        # Test status command
        result = subprocess.run(
            [sys.executable, str(DAEMON_SCRIPT), "status"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        if result.returncode == 0 and "RUNNING" in result.stdout:
            log_test("Status command", True, "Status shows running state")
        else:
            log_test("Status command", False, "Status command failed")

        # Test shutdown
        print("Stopping daemon...")
        result = subprocess.run(
            [sys.executable, str(DAEMON_SCRIPT), "stop"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        time.sleep(3)

        server_pid_after, supervisor_pid_after, _ = get_daemon_info()

        if server_pid_after == 0 and supervisor_pid_after == 0:
            log_test("Clean shutdown", True, "All processes terminated")
        else:
            log_test(
                "Clean shutdown",
                False,
                f"Processes still running: server={server_pid_after}, supervisor={supervisor_pid_after}",
            )

    else:
        log_test("Daemon startup", False, f"Failed to start: {result.stderr}")


def test_crash_recovery():
    """Test basic crash recovery."""
    print("\n=== CRASH RECOVERY TEST ===")

    # Start daemon
    subprocess.run(
        [sys.executable, str(DAEMON_SCRIPT), "start"], capture_output=True, check=False
    )
    time.sleep(5)

    initial_server_pid, supervisor_pid, _port = get_daemon_info()

    if initial_server_pid == 0:
        log_test("Recovery test setup", False, "Could not start daemon")
        return

    print(f"Initial server PID: {initial_server_pid}, supervisor: {supervisor_pid}")

    # Kill server process
    try:
        os.kill(initial_server_pid, signal.SIGKILL)
        log_test(
            "Crash simulation", True, f"Killed server process {initial_server_pid}"
        )
    except Exception as e:
        log_test("Crash simulation", False, f"Could not kill process: {e}")
        cleanup_daemon()
        return

    # Wait for recovery
    print("Waiting for recovery...")
    time.sleep(10)

    new_server_pid, _new_supervisor_pid, new_port = get_daemon_info()

    if new_server_pid > 0 and new_server_pid != initial_server_pid:
        log_test("Automatic recovery", True, f"New server PID: {new_server_pid}")

        if check_port_listening(new_port):
            log_test("Service continuity", True, f"Service restored on port {new_port}")
        else:
            log_test("Service continuity", False, "Service not restored")
    else:
        log_test(
            "Automatic recovery", False, f"Recovery failed. New PID: {new_server_pid}"
        )

    cleanup_daemon()


def test_configuration():
    """Test configuration management."""
    print("\n=== CONFIGURATION TEST ===")

    # Set custom configuration
    os.environ["SOCKETIO_PORT_START"] = "9500"
    os.environ["SOCKETIO_PORT_END"] = "9510"
    os.environ["SOCKETIO_MAX_RETRIES"] = "7"

    try:
        subprocess.run(
            [sys.executable, str(DAEMON_SCRIPT), "start"],
            capture_output=True,
            check=False,
        )
        time.sleep(5)

        _, _, port = get_daemon_info()

        if 9500 <= port <= 9510:
            log_test(
                "Custom port configuration",
                True,
                f"Using port {port} from custom range",
            )
        else:
            log_test(
                "Custom port configuration", False, f"Port {port} not in custom range"
            )

        # Check status output
        result = subprocess.run(
            [sys.executable, str(DAEMON_SCRIPT), "status"],
            capture_output=True,
            text=True,
            check=False,
        )
        if "Max Retries: 7" in result.stdout:
            log_test("Configuration reflection", True, "Custom config shown in status")
        else:
            log_test("Configuration reflection", False, "Custom config not reflected")

    finally:
        for key in ["SOCKETIO_PORT_START", "SOCKETIO_PORT_END", "SOCKETIO_MAX_RETRIES"]:
            if key in os.environ:
                del os.environ[key]
        cleanup_daemon()


def test_concurrent_protection():
    """Test protection against concurrent instances."""
    print("\n=== CONCURRENT PROTECTION TEST ===")

    # Start first instance
    subprocess.run(
        [sys.executable, str(DAEMON_SCRIPT), "start"], capture_output=True, check=False
    )
    time.sleep(5)

    first_server_pid, _, _ = get_daemon_info()

    if first_server_pid == 0:
        log_test("First instance start", False, "Could not start first instance")
        return

    # Try to start second instance
    subprocess.run(
        [sys.executable, str(DAEMON_SCRIPT), "start"],
        capture_output=True,
        text=True,
        check=False,
    )

    second_server_pid, _, _ = get_daemon_info()

    if second_server_pid == first_server_pid:
        log_test("Concurrent protection", True, "Second instance prevented")
    else:
        log_test(
            "Concurrent protection",
            False,
            f"Multiple instances: {first_server_pid}, {second_server_pid}",
        )

    cleanup_daemon()


def main():
    """Run focused QA tests."""
    print("HARDENED SOCKET.IO DAEMON - FOCUSED QA TESTS")
    print("=" * 50)
    print(f"Test started: {datetime.now(timezone.utc)}")

    cleanup_daemon()

    try:
        test_basic_startup_shutdown()
        test_crash_recovery()
        test_configuration()
        test_concurrent_protection()
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
    except Exception as e:
        print(f"\nTest error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        cleanup_daemon()

    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)

    passed = sum(1 for r in TEST_RESULTS if r["passed"])
    total = len(TEST_RESULTS)

    print(f"Passed: {passed}/{total} ({passed / total * 100:.1f}%)")

    if passed < total:
        print("\nFailed tests:")
        for result in TEST_RESULTS:
            if not result["passed"]:
                print(f"  ❌ {result['name']}: {result['details']}")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
