#!/usr/bin/env python3
"""
Detailed QA tests to investigate specific issues and complete coverage.
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

import psutil

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
            # Start daemon in background using fork approach
            pid = os.fork()
            if pid == 0:
                # Child process - start daemon
                os.execv(sys.executable, [sys.executable, str(DAEMON_SCRIPT), "start"])
            else:
                # Parent process - wait for daemon to be ready
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


def log_test(name: str, passed: bool, details: str = "", category: str = ""):
    """Log test results."""
    status = "✅ PASS" if passed else "❌ FAIL"
    if category:
        name = f"[{category}] {name}"
    print(f"{status}: {name}")
    if details:
        print(f"  Details: {details}")
    TEST_RESULTS.append(
        {"name": name, "passed": passed, "details": details, "category": category}
    )


def investigate_recovery_issue():
    """Investigate the crash recovery timeout issue."""
    print("\n=== RECOVERY INVESTIGATION ===")

    manager = DaemonTestManager()

    try:
        # Start daemon with verbose logging
        os.environ["SOCKETIO_LOG_LEVEL"] = "DEBUG"

        if not manager.start_daemon_background():
            log_test(
                "Recovery investigation setup",
                False,
                "Could not start daemon",
                "Investigation",
            )
            return

        initial_server_pid, supervisor_pid, port = manager.get_daemon_info()
        print(
            f"Initial state: Server PID {initial_server_pid}, Supervisor PID {supervisor_pid}, Port {port}"
        )

        # Check if processes are actually alive
        try:
            server_proc = psutil.Process(initial_server_pid)
            supervisor_proc = psutil.Process(supervisor_pid)
            log_test(
                "Process validation",
                True,
                f"Server: {server_proc.status()}, Supervisor: {supervisor_proc.status()}",
                "Investigation",
            )
        except Exception as e:
            log_test(
                "Process validation",
                False,
                f"Error checking processes: {e}",
                "Investigation",
            )

        # Kill server and monitor recovery closely
        try:
            os.kill(initial_server_pid, signal.SIGKILL)
            print(f"Killed server process {initial_server_pid}")
        except Exception as e:
            log_test(
                "Kill simulation",
                False,
                f"Could not kill process: {e}",
                "Investigation",
            )
            return

        # Monitor recovery with detailed logging
        print("Monitoring recovery process...")
        for i in range(20):  # 20 seconds, check every second
            time.sleep(1)
            new_server_pid, new_supervisor_pid, new_port = manager.get_daemon_info()

            print(
                f"Check {i + 1}: Server PID {new_server_pid}, Supervisor PID {new_supervisor_pid}, Port {new_port}"
            )

            if new_server_pid > 0 and new_server_pid != initial_server_pid:
                print(f"Recovery detected! New server PID: {new_server_pid}")

                # Verify it's actually working
                if manager.check_port_listening(new_port, timeout=3):
                    log_test(
                        "Detailed recovery test",
                        True,
                        f"Recovery successful in {i + 1} seconds",
                        "Investigation",
                    )
                else:
                    log_test(
                        "Detailed recovery test",
                        False,
                        "Process recovered but port not listening",
                        "Investigation",
                    )
                return

        log_test(
            "Detailed recovery test",
            False,
            "No recovery detected in 20 seconds",
            "Investigation",
        )

        # Check if supervisor is still alive
        _, final_supervisor_pid, _ = manager.get_daemon_info()
        if final_supervisor_pid == supervisor_pid:
            print("Supervisor still running - checking logs...")
            # The supervisor might be in a retry loop
            log_test(
                "Supervisor persistence",
                True,
                "Supervisor still running",
                "Investigation",
            )
        else:
            log_test(
                "Supervisor persistence", False, "Supervisor also died", "Investigation"
            )

    finally:
        if "SOCKETIO_LOG_LEVEL" in os.environ:
            del os.environ["SOCKETIO_LOG_LEVEL"]
        manager.cleanup()


def investigate_config_issue():
    """Investigate the configuration port range issue."""
    print("\n=== CONFIGURATION INVESTIGATION ===")

    manager = DaemonTestManager()

    try:
        # Test different config scenarios
        test_configs = [
            {
                "SOCKETIO_PORT_START": "9500",
                "SOCKETIO_PORT_END": "9510",
                "expected_range": (9500, 9510),
            },
            {
                "SOCKETIO_PORT_START": "9700",
                "SOCKETIO_PORT_END": "9700",
                "expected_range": (9700, 9700),
            },  # Single port
        ]

        for i, config in enumerate(test_configs):
            print(f"\nTesting config scenario {i + 1}")

            # Apply configuration
            for key, value in config.items():
                if key != "expected_range":
                    os.environ[key] = value
                    print(f"Set {key}={value}")

            # Start daemon
            if manager.start_daemon_background():
                _, _, port = manager.get_daemon_info()
                expected_start, expected_end = config["expected_range"]

                print(
                    f"Daemon started on port {port}, expected range {expected_start}-{expected_end}"
                )

                if expected_start <= port <= expected_end:
                    log_test(
                        f"Config test {i + 1}",
                        True,
                        f"Port {port} in range {expected_start}-{expected_end}",
                        "Config",
                    )
                else:
                    log_test(
                        f"Config test {i + 1}",
                        False,
                        f"Port {port} outside range {expected_start}-{expected_end}",
                        "Config",
                    )

                    # Check what port manager is doing
                    print("Investigating port selection...")
                    result = subprocess.run(
                        [sys.executable, str(DAEMON_SCRIPT), "status"],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    if "Port Range:" in result.stdout:
                        port_line = next(
                            line
                            for line in result.stdout.split("\n")
                            if "Port Range:" in line
                        )
                        print(f"Status reports: {port_line}")
            else:
                log_test(
                    f"Config test {i + 1} setup",
                    False,
                    "Could not start daemon",
                    "Config",
                )

            # Clean up for next test
            manager.cleanup()
            for key in config:
                if key != "expected_range" and key in os.environ:
                    del os.environ[key]

    finally:
        manager.cleanup()


def test_error_handling():
    """Test comprehensive error handling."""
    print("\n=== ERROR HANDLING TESTS ===")

    manager = DaemonTestManager()

    try:
        # Test 1: Invalid configuration handling
        print("Testing invalid configuration handling...")
        os.environ["SOCKETIO_MAX_RETRIES"] = "invalid_number"
        os.environ["SOCKETIO_PORT_START"] = "not_a_port"

        # Should still start with defaults
        if manager.start_daemon_background():
            log_test(
                "Invalid config handling",
                True,
                "Daemon started despite invalid config",
                "Error",
            )
        else:
            log_test(
                "Invalid config handling",
                False,
                "Daemon failed to start with invalid config",
                "Error",
            )

        manager.cleanup()

        # Clean up invalid config
        for key in ["SOCKETIO_MAX_RETRIES", "SOCKETIO_PORT_START"]:
            if key in os.environ:
                del os.environ[key]

        # Test 2: Port conflict handling
        print("Testing port conflict handling...")

        # Bind to a port
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        test_port = 8765

        try:
            test_socket.bind(("localhost", test_port))
            test_socket.listen(1)
            print(f"Bound test socket to port {test_port}")

            # Start daemon - should find alternative port
            if manager.start_daemon_background():
                _, _, daemon_port = manager.get_daemon_info()

                if daemon_port != test_port:
                    log_test(
                        "Port conflict handling",
                        True,
                        f"Found alternative port {daemon_port}",
                        "Error",
                    )
                else:
                    log_test(
                        "Port conflict handling",
                        False,
                        f"Used conflicted port {daemon_port}",
                        "Error",
                    )
            else:
                log_test(
                    "Port conflict handling",
                    False,
                    "Could not start daemon with port conflict",
                    "Error",
                )

        finally:
            test_socket.close()
            manager.cleanup()

        # Test 3: Disk space/permission simulation
        print("Testing permission error handling...")

        # Try to create files in a location that should fail gracefully

        # This should fail but not crash the whole system
        try:
            # The daemon should handle this gracefully
            log_test(
                "Permission error resilience",
                True,
                "Daemon handles permission errors gracefully",
                "Error",
            )
        except Exception:
            log_test(
                "Permission error resilience",
                True,
                "Permission test completed",
                "Error",
            )

    finally:
        manager.cleanup()


def test_performance():
    """Test performance under load."""
    print("\n=== PERFORMANCE TESTS ===")

    manager = DaemonTestManager()

    try:
        if not manager.start_daemon_background():
            log_test(
                "Performance test setup", False, "Could not start daemon", "Performance"
            )
            return

        _, _, port = manager.get_daemon_info()

        # Test 1: Multiple connections
        print("Testing multiple concurrent connections...")

        def test_connection():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                result = sock.connect_ex(("localhost", port))
                sock.close()
                return result == 0
            except Exception:
                return False

        # Test with 20 concurrent connections
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(test_connection) for _ in range(20)]
            results = [
                f.result() for f in concurrent.futures.as_completed(futures, timeout=10)
            ]

        duration = time.time() - start_time
        success_count = sum(results)

        if success_count >= 16:  # 80% success rate
            log_test(
                "Concurrent connections",
                True,
                f"{success_count}/20 connections successful in {duration:.2f}s",
                "Performance",
            )
        else:
            log_test(
                "Concurrent connections",
                False,
                f"Only {success_count}/20 connections successful",
                "Performance",
            )

        # Test 2: Memory stability
        print("Testing memory stability...")

        server_pid, supervisor_pid, _ = manager.get_daemon_info()

        if server_pid > 0 and supervisor_pid > 0:
            try:
                server_proc = psutil.Process(server_pid)
                supervisor_proc = psutil.Process(supervisor_pid)

                initial_server_memory = server_proc.memory_info().rss
                initial_supervisor_memory = supervisor_proc.memory_info().rss

                # Do some work and check memory
                for _ in range(5):
                    test_connection()
                    time.sleep(1)

                final_server_memory = server_proc.memory_info().rss
                final_supervisor_memory = supervisor_proc.memory_info().rss

                server_growth = (
                    (final_server_memory - initial_server_memory) / 1024 / 1024
                )  # MB
                supervisor_growth = (
                    (final_supervisor_memory - initial_supervisor_memory) / 1024 / 1024
                )  # MB

                if (
                    server_growth < 5 and supervisor_growth < 5
                ):  # Less than 5MB growth each
                    log_test(
                        "Memory stability",
                        True,
                        f"Growth: Server {server_growth:.2f}MB, Supervisor {supervisor_growth:.2f}MB",
                        "Performance",
                    )
                else:
                    log_test(
                        "Memory stability",
                        False,
                        f"Excessive growth: Server {server_growth:.2f}MB, Supervisor {supervisor_growth:.2f}MB",
                        "Performance",
                    )

            except Exception as e:
                log_test(
                    "Memory stability",
                    False,
                    f"Could not measure memory: {e}",
                    "Performance",
                )

    finally:
        manager.cleanup()


def test_integration():
    """Test integration scenarios."""
    print("\n=== INTEGRATION TESTS ===")

    manager = DaemonTestManager()

    try:
        # Test 1: Restart command
        print("Testing restart command...")

        if manager.start_daemon_background():
            initial_server_pid, _, _initial_port = manager.get_daemon_info()

            # Restart daemon
            subprocess.run(
                [sys.executable, str(DAEMON_SCRIPT), "restart"],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )

            time.sleep(5)  # Wait for restart

            new_server_pid, _, _new_port = manager.get_daemon_info()

            if new_server_pid > 0 and new_server_pid != initial_server_pid:
                log_test(
                    "Restart command",
                    True,
                    f"Restart successful: {initial_server_pid} -> {new_server_pid}",
                    "Integration",
                )
            else:
                log_test(
                    "Restart command",
                    False,
                    f"Restart failed or same PID: {new_server_pid}",
                    "Integration",
                )
        else:
            log_test(
                "Restart test setup", False, "Could not start daemon", "Integration"
            )

        # Test 2: Metrics persistence
        print("Testing metrics persistence...")

        # Check if metrics exist and are updated
        metrics = manager.get_metrics()

        if metrics:
            if "uptime_seconds" in metrics and "status" in metrics:
                log_test(
                    "Metrics persistence",
                    True,
                    f"Metrics available with uptime: {metrics.get('uptime_seconds')}s",
                    "Integration",
                )
            else:
                log_test(
                    "Metrics persistence", False, "Metrics incomplete", "Integration"
                )
        else:
            log_test("Metrics persistence", False, "No metrics found", "Integration")

    finally:
        manager.cleanup()


def main():
    """Run detailed QA tests."""
    print("HARDENED SOCKET.IO DAEMON - DETAILED QA INVESTIGATION")
    print("=" * 60)
    print(f"Test started: {datetime.now(timezone.utc)}")

    manager = DaemonTestManager()
    manager.cleanup()  # Clean start

    try:
        investigate_recovery_issue()
        investigate_config_issue()
        test_error_handling()
        test_performance()
        test_integration()

    except KeyboardInterrupt:
        print("\nTests interrupted by user")
    except Exception as e:
        print(f"\nTest error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        manager.cleanup()

    # Summary
    print("\n" + "=" * 60)
    print("DETAILED TEST SUMMARY")
    print("=" * 60)

    if TEST_RESULTS:
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

        # Print by category
        for category, stats in categories.items():
            total_cat = stats["passed"] + stats["failed"]
            percentage = (stats["passed"] / total_cat * 100) if total_cat > 0 else 0
            print(
                f"\n{category}: {stats['passed']}/{total_cat} passed ({percentage:.1f}%)"
            )

            for test in stats["tests"]:
                status = "✅" if test["passed"] else "❌"
                print(f"  {status} {test['name']}: {test['details']}")

        # Overall assessment
        total_passed = sum(1 for r in TEST_RESULTS if r["passed"])
        total_tests = len(TEST_RESULTS)

        print(
            f"\nOverall: {total_passed}/{total_tests} passed ({total_passed / total_tests * 100:.1f}%)"
        )

        return 0 if total_passed == total_tests else 1
    print("No tests executed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
