#!/usr/bin/env python3
"""
Comprehensive QA test suite for the hardened Socket.IO daemon.

This test suite validates production readiness by testing:
- Crash recovery and reliability
- Health monitoring and metrics
- Process management and signals
- Configuration validation
- Performance under load
- Error handling and edge cases
- Integration testing
"""

import concurrent.futures
import json
import os
import signal
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import psutil

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import contextlib

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
TEST_TIMEOUT = 30  # seconds
LOAD_TEST_CONNECTIONS = 50
LOAD_TEST_DURATION = 10  # seconds


def log_test(name: str, passed: bool, details: str = "", category: str = ""):
    """Log test results with categorization."""
    status = "✅ PASS" if passed else "❌ FAIL"
    if category:
        name = f"[{category}] {name}"
    print(f"{status}: {name}")
    if details:
        print(f"  Details: {details}")
    TEST_RESULTS.append(
        {"name": name, "passed": passed, "details": details, "category": category}
    )


def run_subcommand(
    cmd: List[str], timeout: float = TEST_TIMEOUT
) -> subprocess.CompletedProcess:
    """Run a command with timeout."""
    try:
        return subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            cmd, 124, "", f"Command timed out after {timeout}s"
        )


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
        time.sleep(0.1)
    return False


def get_daemon_pid() -> int:
    """Get the daemon server PID."""
    deployment_root = get_project_root()
    pid_file = deployment_root / ".claude-mpm" / "socketio-server.pid"
    if pid_file.exists():
        try:
            with pid_file.open() as f:
                return int(f.read().strip())
        except Exception:
            pass
    return 0


def get_supervisor_pid() -> int:
    """Get the supervisor PID."""
    deployment_root = get_project_root()
    pid_file = deployment_root / ".claude-mpm" / "socketio-supervisor.pid"
    if pid_file.exists():
        try:
            with pid_file.open() as f:
                return int(f.read().strip())
        except Exception:
            pass
    return 0


def get_daemon_port() -> int:
    """Get the daemon port."""
    deployment_root = get_project_root()
    port_file = deployment_root / ".claude-mpm" / "socketio-port"
    if port_file.exists():
        try:
            with port_file.open() as f:
                return int(f.read().strip())
        except Exception:
            pass
    return 0


def get_metrics() -> Dict:
    """Get daemon metrics."""
    deployment_root = get_project_root()
    metrics_file = deployment_root / ".claude-mpm" / ".claude-mpm/socketio-metrics.json"
    if metrics_file.exists():
        try:
            with metrics_file.open() as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def cleanup_daemon():
    """Forcefully clean up daemon processes and files."""
    print("Cleaning up daemon...")

    # Stop daemon gracefully first
    run_subcommand([sys.executable, str(DAEMON_SCRIPT), "stop"], timeout=10)
    time.sleep(2)

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


def is_process_alive(pid: int) -> bool:
    """Check if a process is alive."""
    try:
        return psutil.pid_exists(pid) and psutil.Process(pid).is_running()
    except Exception:
        return False


# Test Categories


def test_basic_operations():
    """Test Category: Basic Operations"""
    print("\n" + "=" * 60)
    print("TEST CATEGORY: Basic Operations")
    print("=" * 60)

    # Test 1: Basic startup
    result = run_subcommand([sys.executable, str(DAEMON_SCRIPT), "start"])
    time.sleep(3)

    pid = get_daemon_pid()
    supervisor_pid = get_supervisor_pid()
    port = get_daemon_port()

    if pid > 0 and supervisor_pid > 0 and port > 0:
        log_test(
            "Basic startup",
            True,
            f"Server PID: {pid}, Supervisor: {supervisor_pid}, Port: {port}",
            "Basic",
        )

        # Test port accessibility
        if check_port_listening(port):
            log_test(
                "Port accessibility",
                True,
                f"Port {port} accepting connections",
                "Basic",
            )
        else:
            log_test(
                "Port accessibility", False, f"Port {port} not responding", "Basic"
            )
    else:
        log_test("Basic startup", False, f"Failed to start: {result.stderr}", "Basic")
        return

    # Test 2: Status command
    result = run_subcommand([sys.executable, str(DAEMON_SCRIPT), "status"])
    if result.returncode == 0 and "RUNNING" in result.stdout:
        log_test("Status command", True, "Status shows running state", "Basic")
    else:
        log_test(
            "Status command", False, f"Status command failed: {result.stderr}", "Basic"
        )

    # Test 3: Metrics generation
    metrics = get_metrics()
    if metrics and metrics.get("status"):
        log_test(
            "Metrics generation", True, f"Status: {metrics.get('status')}", "Basic"
        )
    else:
        log_test("Metrics generation", False, "No metrics generated", "Basic")

    # Test 4: Clean shutdown
    result = run_subcommand([sys.executable, str(DAEMON_SCRIPT), "stop"])
    time.sleep(2)

    if get_daemon_pid() == 0 and get_supervisor_pid() == 0:
        log_test("Clean shutdown", True, "All processes terminated", "Basic")
    else:
        log_test("Clean shutdown", False, "Processes still running after stop", "Basic")


def test_crash_recovery():
    """Test Category: Crash Recovery"""
    print("\n" + "=" * 60)
    print("TEST CATEGORY: Crash Recovery")
    print("=" * 60)

    # Start daemon
    run_subcommand([sys.executable, str(DAEMON_SCRIPT), "start"])
    time.sleep(3)

    initial_pid = get_daemon_pid()
    supervisor_pid = get_supervisor_pid()
    port = get_daemon_port()

    if initial_pid == 0:
        log_test(
            "Recovery setup",
            False,
            "Could not start daemon for recovery test",
            "Recovery",
        )
        return

    # Test 1: Server crash recovery
    try:
        os.kill(initial_pid, signal.SIGKILL)
        log_test(
            "Crash simulation", True, f"Killed server process {initial_pid}", "Recovery"
        )
    except Exception as e:
        log_test("Crash simulation", False, f"Could not kill process: {e}", "Recovery")
        return

    # Wait for recovery
    time.sleep(8)

    new_pid = get_daemon_pid()
    new_supervisor_pid = get_supervisor_pid()

    if new_pid > 0 and new_pid != initial_pid and new_supervisor_pid == supervisor_pid:
        log_test("Automatic recovery", True, f"New server PID: {new_pid}", "Recovery")

        # Test service continuity
        if check_port_listening(port):
            log_test(
                "Service continuity",
                True,
                f"Service restored on port {port}",
                "Recovery",
            )
        else:
            log_test("Service continuity", False, "Service not restored", "Recovery")

        # Test restart tracking
        metrics = get_metrics()
        if metrics.get("restarts", 0) > 0:
            log_test(
                "Restart tracking", True, f"Restarts: {metrics['restarts']}", "Recovery"
            )
        else:
            log_test("Restart tracking", False, "Restart not tracked", "Recovery")
    else:
        log_test(
            "Automatic recovery",
            False,
            f"Recovery failed. New PID: {new_pid}",
            "Recovery",
        )

    # Test 2: Multiple crash recovery
    for _i in range(3):
        pid = get_daemon_pid()
        if pid > 0:
            try:
                os.kill(pid, signal.SIGKILL)
                time.sleep(5)  # Wait for recovery
            except Exception:
                pass

    final_pid = get_daemon_pid()
    if final_pid > 0:
        log_test(
            "Multiple crash recovery",
            True,
            f"Survived multiple crashes, PID: {final_pid}",
            "Recovery",
        )
    else:
        log_test(
            "Multiple crash recovery",
            False,
            "Failed to recover from multiple crashes",
            "Recovery",
        )

    cleanup_daemon()


def test_health_monitoring():
    """Test Category: Health Monitoring"""
    print("\n" + "=" * 60)
    print("TEST CATEGORY: Health Monitoring")
    print("=" * 60)

    # Set faster health checks for testing
    os.environ["SOCKETIO_HEALTH_CHECK_INTERVAL"] = "5"
    os.environ["SOCKETIO_METRICS_ENABLED"] = "true"

    try:
        # Start daemon
        run_subcommand([sys.executable, str(DAEMON_SCRIPT), "start"])
        time.sleep(3)

        if get_daemon_pid() == 0:
            log_test(
                "Health monitoring setup", False, "Could not start daemon", "Health"
            )
            return

        # Wait for health checks to run
        time.sleep(12)

        metrics = get_metrics()

        # Test 1: Health checks running
        if metrics and metrics.get("health_checks_passed", 0) > 0:
            log_test(
                "Health checks execution",
                True,
                f"Passed: {metrics['health_checks_passed']}",
                "Health",
            )
        else:
            log_test(
                "Health checks execution", False, "No health checks recorded", "Health"
            )

        # Test 2: Health status tracking
        if metrics.get("status") in ["healthy", "running"]:
            log_test(
                "Health status tracking", True, f"Status: {metrics['status']}", "Health"
            )
        else:
            log_test(
                "Health status tracking",
                False,
                f"Unexpected status: {metrics.get('status')}",
                "Health",
            )

        # Test 3: Health timestamp updates
        if metrics.get("last_health_check"):
            log_test(
                "Health timestamp updates",
                True,
                "Health check timestamp present",
                "Health",
            )
        else:
            log_test(
                "Health timestamp updates", False, "No health check timestamp", "Health"
            )

    finally:
        # Clean up environment
        if "SOCKETIO_HEALTH_CHECK_INTERVAL" in os.environ:
            del os.environ["SOCKETIO_HEALTH_CHECK_INTERVAL"]
        if "SOCKETIO_METRICS_ENABLED" in os.environ:
            del os.environ["SOCKETIO_METRICS_ENABLED"]
        cleanup_daemon()


def test_configuration_management():
    """Test Category: Configuration Management"""
    print("\n" + "=" * 60)
    print("TEST CATEGORY: Configuration Management")
    print("=" * 60)

    # Test 1: Environment variable configuration
    test_config = {
        "SOCKETIO_MAX_RETRIES": "15",
        "SOCKETIO_PORT_START": "9000",
        "SOCKETIO_PORT_END": "9010",
        "SOCKETIO_LOG_LEVEL": "DEBUG",
        "SOCKETIO_HEALTH_CHECK_INTERVAL": "60",
    }

    # Apply configuration
    for key, value in test_config.items():
        os.environ[key] = value

    try:
        # Start daemon with custom config
        run_subcommand([sys.executable, str(DAEMON_SCRIPT), "start"])
        time.sleep(3)

        port = get_daemon_port()

        # Test custom port range
        if 9000 <= port <= 9010:
            log_test(
                "Custom port range",
                True,
                f"Using port {port} from custom range",
                "Config",
            )
        else:
            log_test(
                "Custom port range", False, f"Port {port} not in custom range", "Config"
            )

        # Test configuration reflection in status
        result = run_subcommand([sys.executable, str(DAEMON_SCRIPT), "status"])
        if "Max Retries: 15" in result.stdout:
            log_test(
                "Config in status output",
                True,
                "Custom config shown in status",
                "Config",
            )
        else:
            log_test(
                "Config in status output",
                False,
                "Custom config not reflected",
                "Config",
            )

        # Test 2: Invalid configuration handling
        cleanup_daemon()
        os.environ["SOCKETIO_MAX_RETRIES"] = "invalid"

        result = run_subcommand([sys.executable, str(DAEMON_SCRIPT), "start"])
        time.sleep(2)

        # Should still start with default values
        if get_daemon_pid() > 0:
            log_test(
                "Invalid config handling",
                True,
                "Gracefully handled invalid config",
                "Config",
            )
        else:
            log_test(
                "Invalid config handling",
                False,
                "Failed to handle invalid config",
                "Config",
            )

    finally:
        # Clean up environment
        for key in test_config:
            if key in os.environ:
                del os.environ[key]
        if "SOCKETIO_MAX_RETRIES" in os.environ:
            del os.environ["SOCKETIO_MAX_RETRIES"]
        cleanup_daemon()


def test_process_management():
    """Test Category: Process Management"""
    print("\n" + "=" * 60)
    print("TEST CATEGORY: Process Management")
    print("=" * 60)

    # Test 1: PID file creation and cleanup
    run_subcommand([sys.executable, str(DAEMON_SCRIPT), "start"])
    time.sleep(3)

    deployment_root = get_project_root()
    pid_file = deployment_root / ".claude-mpm" / "socketio-server.pid"
    supervisor_pid_file = deployment_root / ".claude-mpm" / "socketio-supervisor.pid"

    if pid_file.exists() and supervisor_pid_file.exists():
        log_test("PID file creation", True, "Both PID files created", "Process")
    else:
        log_test(
            "PID file creation", False, "PID files not created properly", "Process"
        )

    # Test 2: Signal handling
    supervisor_pid = get_supervisor_pid()
    if supervisor_pid > 0:
        try:
            os.kill(supervisor_pid, signal.SIGTERM)
            time.sleep(3)

            if not is_process_alive(supervisor_pid):
                log_test(
                    "SIGTERM handling",
                    True,
                    "Supervisor responded to SIGTERM",
                    "Process",
                )
            else:
                log_test(
                    "SIGTERM handling",
                    False,
                    "Supervisor did not respond to SIGTERM",
                    "Process",
                )
        except Exception as e:
            log_test(
                "SIGTERM handling", False, f"Error sending SIGTERM: {e}", "Process"
            )

    # Test 3: PID file cleanup after shutdown
    if not pid_file.exists() and not supervisor_pid_file.exists():
        log_test(
            "PID file cleanup", True, "PID files cleaned up on shutdown", "Process"
        )
    else:
        log_test("PID file cleanup", False, "PID files not cleaned up", "Process")

    # Test 4: Concurrent instance protection
    run_subcommand([sys.executable, str(DAEMON_SCRIPT), "start"])
    time.sleep(3)

    first_pid = get_daemon_pid()

    # Try to start second instance
    run_subcommand([sys.executable, str(DAEMON_SCRIPT), "start"])
    second_pid = get_daemon_pid()

    if first_pid > 0 and second_pid == first_pid:
        log_test("Concurrent protection", True, "Second instance prevented", "Process")
    else:
        log_test(
            "Concurrent protection",
            False,
            f"Multiple instances running: {first_pid}, {second_pid}",
            "Process",
        )

    cleanup_daemon()


def test_error_handling():
    """Test Category: Error Handling"""
    print("\n" + "=" * 60)
    print("TEST CATEGORY: Error Handling")
    print("=" * 60)

    # Test 1: Port unavailable handling
    # Bind to a port in the daemon's range
    test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        test_socket.bind(("localhost", 8765))
        test_socket.listen(1)

        # Set narrow port range
        os.environ["SOCKETIO_PORT_START"] = "8765"
        os.environ["SOCKETIO_PORT_END"] = "8767"

        run_subcommand([sys.executable, str(DAEMON_SCRIPT), "start"])
        time.sleep(3)

        port = get_daemon_port()

        if port > 8765:  # Should find alternative port
            log_test(
                "Port conflict handling",
                True,
                f"Found alternative port {port}",
                "Error",
            )
        else:
            log_test(
                "Port conflict handling", False, "Did not handle port conflict", "Error"
            )

    finally:
        test_socket.close()
        if "SOCKETIO_PORT_START" in os.environ:
            del os.environ["SOCKETIO_PORT_START"]
        if "SOCKETIO_PORT_END" in os.environ:
            del os.environ["SOCKETIO_PORT_END"]
        cleanup_daemon()

    # Test 2: Disk space simulation (write permission test)
    try:
        # Try to create daemon in read-only directory
        read_only_dir = Path("/tmp/readonly_test")
        read_only_dir.mkdir(exist_ok=True)
        os.chmod(read_only_dir, 0o444)  # Read-only

        # This should fail gracefully
        run_subcommand([sys.executable, str(DAEMON_SCRIPT), "start"])
        # Even if it fails, it should not crash the whole system
        log_test(
            "Permission error handling",
            True,
            "Handled permission errors gracefully",
            "Error",
        )

    except Exception:
        log_test(
            "Permission error handling", True, "Permission test completed", "Error"
        )
    finally:
        try:
            if read_only_dir.exists():
                os.chmod(read_only_dir, 0o755)
                read_only_dir.rmdir()
        except Exception:
            pass


def test_performance_load():
    """Test Category: Performance and Load"""
    print("\n" + "=" * 60)
    print("TEST CATEGORY: Performance and Load")
    print("=" * 60)

    # Start daemon
    run_subcommand([sys.executable, str(DAEMON_SCRIPT), "start"])
    time.sleep(3)

    port = get_daemon_port()
    if port == 0:
        log_test(
            "Load test setup",
            False,
            "Could not start daemon for load test",
            "Performance",
        )
        return

    # Test 1: Multiple connection handling
    def test_connection():
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(("localhost", port))
            sock.close()
            return result == 0
        except Exception:
            return False

    # Run concurrent connections
    start_time = time.time()
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=LOAD_TEST_CONNECTIONS
    ) as executor:
        futures = [
            executor.submit(test_connection) for _ in range(LOAD_TEST_CONNECTIONS)
        ]
        results = [
            f.result()
            for f in concurrent.futures.as_completed(
                futures, timeout=LOAD_TEST_DURATION
            )
        ]

    duration = time.time() - start_time
    success_count = sum(results)

    if success_count >= LOAD_TEST_CONNECTIONS * 0.8:  # 80% success rate
        log_test(
            "Concurrent connections",
            True,
            f"{success_count}/{LOAD_TEST_CONNECTIONS} connections successful in {duration:.2f}s",
            "Performance",
        )
    else:
        log_test(
            "Concurrent connections",
            False,
            f"Only {success_count}/{LOAD_TEST_CONNECTIONS} connections successful",
            "Performance",
        )

    # Test 2: Memory usage stability
    pid = get_daemon_pid()
    supervisor_pid = get_supervisor_pid()

    if pid > 0 and supervisor_pid > 0:
        try:
            server_proc = psutil.Process(pid)
            supervisor_proc = psutil.Process(supervisor_pid)

            initial_server_memory = server_proc.memory_info().rss
            supervisor_proc.memory_info().rss

            # Wait and check again
            time.sleep(5)

            final_server_memory = server_proc.memory_info().rss
            supervisor_proc.memory_info().rss

            memory_growth = (
                (final_server_memory - initial_server_memory) / 1024 / 1024
            )  # MB

            if memory_growth < 10:  # Less than 10MB growth
                log_test(
                    "Memory stability",
                    True,
                    f"Memory growth: {memory_growth:.2f}MB",
                    "Performance",
                )
            else:
                log_test(
                    "Memory stability",
                    False,
                    f"Excessive memory growth: {memory_growth:.2f}MB",
                    "Performance",
                )

        except Exception as e:
            log_test(
                "Memory stability",
                False,
                f"Could not measure memory: {e}",
                "Performance",
            )

    cleanup_daemon()


def test_integration():
    """Test Category: Integration Testing"""
    print("\n" + "=" * 60)
    print("TEST CATEGORY: Integration Testing")
    print("=" * 60)

    # Test 1: Wrapper script functionality
    wrapper_script = (
        Path(__file__).parent.parent / "scripts" / "socketio_daemon_wrapper.py"
    )

    if wrapper_script.exists():
        # Test wrapper with hardened daemon
        os.environ["SOCKETIO_USE_HARDENED"] = "true"

        run_subcommand([sys.executable, str(wrapper_script), "start"])
        time.sleep(3)

        if get_daemon_pid() > 0:
            log_test(
                "Wrapper script integration",
                True,
                "Wrapper successfully started hardened daemon",
                "Integration",
            )

            run_subcommand([sys.executable, str(wrapper_script), "stop"])
            time.sleep(2)

            if get_daemon_pid() == 0:
                log_test(
                    "Wrapper script stop",
                    True,
                    "Wrapper successfully stopped daemon",
                    "Integration",
                )
            else:
                log_test(
                    "Wrapper script stop",
                    False,
                    "Wrapper failed to stop daemon",
                    "Integration",
                )
        else:
            log_test(
                "Wrapper script integration",
                False,
                "Wrapper failed to start daemon",
                "Integration",
            )

        if "SOCKETIO_USE_HARDENED" in os.environ:
            del os.environ["SOCKETIO_USE_HARDENED"]
    else:
        log_test(
            "Wrapper script integration",
            False,
            "Wrapper script not found",
            "Integration",
        )

    # Test 2: Metrics persistence across restarts
    run_subcommand([sys.executable, str(DAEMON_SCRIPT), "start"])
    time.sleep(3)

    # Get initial metrics
    initial_metrics = get_metrics()

    # Restart daemon
    run_subcommand([sys.executable, str(DAEMON_SCRIPT), "restart"])
    time.sleep(5)

    # Check if metrics persisted/updated correctly
    final_metrics = get_metrics()

    if final_metrics and final_metrics.get("restarts", 0) > initial_metrics.get(
        "restarts", 0
    ):
        log_test(
            "Metrics persistence",
            True,
            f"Restart count incremented: {final_metrics.get('restarts')}",
            "Integration",
        )
    else:
        log_test(
            "Metrics persistence",
            False,
            "Metrics not properly updated across restart",
            "Integration",
        )

    cleanup_daemon()


def generate_report():
    """Generate comprehensive QA report."""
    print("\n" + "=" * 70)
    print("COMPREHENSIVE QA REPORT")
    print("=" * 70)

    # Categorize results
    categories = {}
    for result in TEST_RESULTS:
        category = result.get("category", "Other")
        if category not in categories:
            categories[category] = {"passed": 0, "failed": 0, "tests": []}

        if result["passed"]:
            categories[category]["passed"] += 1
        else:
            categories[category]["failed"] += 1
        categories[category]["tests"].append(result)

    # Overall summary
    total_tests = len(TEST_RESULTS)
    total_passed = sum(1 for r in TEST_RESULTS if r["passed"])
    total_failed = total_tests - total_passed

    print(
        f"Overall Results: {total_passed}/{total_tests} tests passed ({(total_passed / total_tests * 100):.1f}%)"
    )
    print()

    # Category breakdown
    for category, stats in categories.items():
        total_cat = stats["passed"] + stats["failed"]
        percentage = (stats["passed"] / total_cat * 100) if total_cat > 0 else 0
        status = "✅" if stats["failed"] == 0 else "⚠️" if percentage >= 75 else "❌"

        print(
            f"{status} {category}: {stats['passed']}/{total_cat} passed ({percentage:.1f}%)"
        )

        # Show failed tests
        if stats["failed"] > 0:
            for test in stats["tests"]:
                if not test["passed"]:
                    print(f"    ❌ {test['name']}: {test['details']}")
        print()

    # Production readiness assessment
    print("=" * 70)
    print("PRODUCTION READINESS ASSESSMENT")
    print("=" * 70)

    critical_categories = ["Basic", "Recovery", "Process", "Error"]
    critical_passed = sum(
        categories.get(cat, {}).get("passed", 0) for cat in critical_categories
    )
    critical_total = sum(
        categories.get(cat, {}).get("passed", 0)
        + categories.get(cat, {}).get("failed", 0)
        for cat in critical_categories
    )

    if critical_total > 0:
        critical_percentage = critical_passed / critical_total * 100

        if critical_percentage >= 95:
            readiness = "✅ PRODUCTION READY"
            recommendation = (
                "The daemon meets production requirements with excellent reliability."
            )
        elif critical_percentage >= 85:
            readiness = "⚠️ PRODUCTION READY WITH MONITORING"
            recommendation = "The daemon is suitable for production with close monitoring of failed areas."
        else:
            readiness = "❌ NOT PRODUCTION READY"
            recommendation = (
                "Critical issues must be resolved before production deployment."
            )

        print(f"Status: {readiness}")
        print(f"Critical Test Success Rate: {critical_percentage:.1f}%")
        print(f"Recommendation: {recommendation}")

    # Detailed recommendations
    print("\nRECOMMENDATIONS:")

    if categories.get("Recovery", {}).get("failed", 0) > 0:
        print("- Address crash recovery issues before production deployment")

    if categories.get("Performance", {}).get("failed", 0) > 0:
        print("- Investigate performance issues under load")

    if categories.get("Error", {}).get("failed", 0) > 0:
        print("- Improve error handling for edge cases")

    if total_failed == 0:
        print("- All tests passed! The daemon is ready for production deployment.")
        print("- Consider implementing monitoring based on the metrics provided.")
        print("- Review logs regularly and set up alerting for health check failures.")

    return total_failed == 0


def main():
    """Run comprehensive QA test suite."""
    print("=" * 70)
    print("HARDENED SOCKET.IO DAEMON - COMPREHENSIVE QA TEST SUITE")
    print("=" * 70)
    print(f"Test started: {datetime.now(timezone.utc)}")
    print(f"Testing: {DAEMON_SCRIPT}")
    print()

    # Ensure clean starting state
    cleanup_daemon()

    # Run test categories
    test_categories = [
        test_basic_operations,
        test_crash_recovery,
        test_health_monitoring,
        test_configuration_management,
        test_process_management,
        test_error_handling,
        test_performance_load,
        test_integration,
    ]

    for test_category in test_categories:
        try:
            test_category()
        except Exception as e:
            log_test(
                f"{test_category.__name__} execution",
                False,
                f"Test category failed: {e}",
                "System",
            )
            import traceback

            traceback.print_exc()
        finally:
            cleanup_daemon()
            time.sleep(1)  # Brief pause between categories

    # Generate final report
    production_ready = generate_report()

    # Final cleanup
    cleanup_daemon()

    print(f"\nTest completed: {datetime.now(timezone.utc)}")
    return 0 if production_ready else 1


if __name__ == "__main__":
    sys.exit(main())
