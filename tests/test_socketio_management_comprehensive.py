#!/usr/bin/env python3
"""
Comprehensive QA test for Socket.IO management script fixes.

Tests:
1. Stop command fix for daemon-managed servers
2. Script coordination between daemon and manager
3. Error handling and messaging improvements
4. Status and diagnostics features
5. Backward compatibility
"""

import io
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
from contextlib import redirect_stdout
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import from scripts directory
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))
from socketio_server_manager import ServerManager


class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []

    def add_test(self, name, passed, details=""):
        self.tests.append({"name": name, "passed": passed, "details": details})
        if passed:
            self.passed += 1
        else:
            self.failed += 1

    def print_summary(self):
        print(f"\n📊 Test Summary:")
        print(f"   Passed: {self.passed}")
        print(f"   Failed: {self.failed}")
        print(f"   Total: {self.passed + self.failed}")

        if self.failed > 0:
            print(f"\n❌ Failed tests:")
            for test in self.tests:
                if not test["passed"]:
                    print(f"   • {test['name']}: {test['details']}")


def test_stop_command_fix(results):
    """Test 1: Stop command fix for daemon-managed servers."""
    print("\n🧪 Test 1: Stop Command Fix")
    print("=" * 50)

    manager = ServerManager()

    # Test 1.1: Stop non-existent server
    print("1.1 Testing stop on non-existent server...")
    success = manager.stop_server(port=8765)
    if not success:
        results.add_test("Stop non-existent server", True, "Correctly returned False")
        print("   ✅ Correctly failed to stop non-existent server")
    else:
        results.add_test(
            "Stop non-existent server", False, "Should have returned False"
        )
        print("   ❌ Should have returned False")

    # Test 1.2: Create mock daemon PID file and test daemon stop
    print("1.2 Testing daemon-style stop...")
    daemon_pidfile = Path.home() / ".claude-mpm" / "socketio-server.pid"
    daemon_pidfile.parent.mkdir(exist_ok=True)

    # Create a test subprocess to simulate daemon
    test_proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])

    try:
        with open(daemon_pidfile, "w") as f:
            f.write(str(test_proc.pid))

        print(f"   Created mock daemon PID: {test_proc.pid}")

        # Test daemon detection
        detected_pid = manager._get_daemon_pid()
        if detected_pid == test_proc.pid:
            results.add_test("Daemon PID detection", True)
            print("   ✅ Daemon PID detection works")
        else:
            results.add_test(
                "Daemon PID detection",
                False,
                f"Expected {test_proc.pid}, got {detected_pid}",
            )
            print(f"   ❌ Expected {test_proc.pid}, got {detected_pid}")

        # Test daemon stop
        print("   Testing _try_daemon_stop method...")
        daemon_stop_success = manager._try_daemon_stop(8765)

        time.sleep(1)  # Give process time to stop

        if daemon_stop_success and test_proc.poll() is not None:
            results.add_test("Daemon stop method", True)
            print("   ✅ Daemon stop method works")
        else:
            results.add_test(
                "Daemon stop method", False, "Process should have been stopped"
            )
            print("   ❌ Process should have been stopped")

    finally:
        # Clean up
        try:
            test_proc.kill()
            test_proc.wait(timeout=5)
        except:
            pass
        daemon_pidfile.unlink(missing_ok=True)


def test_script_coordination(results):
    """Test 2: Script coordination between daemon and manager."""
    print("\n🧪 Test 2: Script Coordination")
    print("=" * 50)

    manager = ServerManager()

    # Test 2.1: Status shows management style
    print("2.1 Testing status shows management style...")
    f = io.StringIO()
    with redirect_stdout(f):
        manager.status(verbose=True)

    output = f.getvalue()
    if "Management options" in output or "management" in output.lower():
        results.add_test("Status shows management info", True)
        print("   ✅ Status includes management information")
    else:
        results.add_test(
            "Status shows management info", False, "Missing management info"
        )
        print("   ❌ Status missing management information")

    # Test 2.2: Daemon server info integration
    print("2.2 Testing daemon server info...")
    daemon_pidfile = Path.home() / ".claude-mpm" / "socketio-server.pid"
    daemon_pidfile.parent.mkdir(exist_ok=True)

    test_pid = os.getpid()  # Use our own PID as it's guaranteed to exist

    try:
        with open(daemon_pidfile, "w") as f:
            f.write(str(test_pid))

        daemon_info = manager._get_daemon_server_info()
        if daemon_info and daemon_info.get("management_style") == "daemon":
            results.add_test("Daemon server info", True)
            print("   ✅ Daemon server info correctly identifies management style")
        else:
            results.add_test(
                "Daemon server info", False, "Missing or incorrect daemon info"
            )
            print("   ❌ Daemon server info incorrect")

        # Test server listing includes daemon
        servers = manager.list_running_servers()
        daemon_servers = [s for s in servers if s.get("management_style") == "daemon"]

        if len(daemon_servers) > 0:
            results.add_test("Daemon in server list", True)
            print("   ✅ Daemon server included in server listing")
        else:
            results.add_test(
                "Daemon in server list", False, "Daemon not found in listing"
            )
            print("   ❌ Daemon server not found in listing")

    finally:
        daemon_pidfile.unlink(missing_ok=True)


def test_error_handling(results):
    """Test 3: Error handling and messaging improvements."""
    print("\n🧪 Test 3: Error Handling & Messaging")
    print("=" * 50)

    manager = ServerManager()

    # Test 3.1: Stop with invalid PID handling
    print("3.1 Testing invalid PID handling...")

    # Test PID validation
    invalid_pid = 999999
    valid_pid = os.getpid()

    if not manager._validate_pid(invalid_pid) and manager._validate_pid(valid_pid):
        results.add_test("PID validation", True)
        print("   ✅ PID validation works correctly")
    else:
        results.add_test("PID validation", False, "PID validation incorrect")
        print("   ❌ PID validation incorrect")

    # Test 3.2: Error messages in stop command
    print("3.2 Testing error messages...")
    f = io.StringIO()
    with redirect_stdout(f):
        manager.stop_server(port=8999)  # Non-existent port

    output = f.getvalue()
    if "daemon-style stop" in output or "daemon" in output:
        results.add_test("Stop error messages", True)
        print("   ✅ Stop command provides helpful error messages")
    else:
        results.add_test("Stop error messages", False, "Missing helpful error messages")
        print("   ❌ Stop command missing helpful error messages")


def test_diagnostics(results):
    """Test 4: Status and diagnostics features."""
    print("\n🧪 Test 4: Status & Diagnostics")
    print("=" * 50)

    manager = ServerManager()

    # Test 4.1: Diagnose command
    print("4.1 Testing diagnose command...")
    f = io.StringIO()
    with redirect_stdout(f):
        manager.diagnose_conflicts(port=8765)

    output = f.getvalue()
    required_sections = [
        "Server Analysis",
        "Port Status",
        "Management Style Comparison",
    ]

    all_present = all(section in output for section in required_sections)
    if all_present:
        results.add_test("Diagnose command", True)
        print("   ✅ Diagnose command includes all required sections")
    else:
        missing = [s for s in required_sections if s not in output]
        results.add_test("Diagnose command", False, f"Missing: {missing}")
        print(f"   ❌ Diagnose command missing: {missing}")

    # Test 4.2: Status verbose output
    print("4.2 Testing verbose status output...")
    f = io.StringIO()
    with redirect_stdout(f):
        manager.status(verbose=True)

    output = f.getvalue()
    if "Management" in output and ("PID" in output or "No Socket.IO servers" in output):
        results.add_test("Verbose status", True)
        print("   ✅ Verbose status includes management and PID info")
    else:
        results.add_test("Verbose status", False, "Missing verbose information")
        print("   ❌ Verbose status missing information")


def test_backward_compatibility(results):
    """Test 5: Backward compatibility."""
    print("\n🧪 Test 5: Backward Compatibility")
    print("=" * 50)

    manager = ServerManager()

    # Test 5.1: Manager methods still work
    print("5.1 Testing manager methods...")
    try:
        # These should not raise exceptions
        servers = manager.list_running_servers()
        manager.find_available_port()

        results.add_test("Manager methods compatibility", True)
        print("   ✅ Manager methods work without errors")
    except Exception as e:
        results.add_test("Manager methods compatibility", False, str(e))
        print(f"   ❌ Manager methods error: {e}")

    # Test 5.2: CLI interface backwards compatibility
    print("5.2 Testing CLI backwards compatibility...")

    # Test that help still works
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "claude_mpm.scripts.socketio_server_manager",
                "--help",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if (
            result.returncode == 0
            and "start" in result.stdout
            and "stop" in result.stdout
        ):
            results.add_test("CLI help backwards compatibility", True)
            print("   ✅ CLI help works and includes expected commands")
        else:
            results.add_test(
                "CLI help backwards compatibility", False, "Help output incorrect"
            )
            print("   ❌ CLI help output incorrect")

    except Exception as e:
        results.add_test("CLI help backwards compatibility", False, str(e))
        print(f"   ❌ CLI help error: {e}")


def run_manual_verification():
    """Provide manual verification steps."""
    print("\n📋 Manual Verification Steps:")
    print("=" * 50)

    base_cmd = f"{sys.executable} -m claude_mpm.scripts.socketio_server_manager"
    daemon_cmd = f"{sys.executable} src/claude_mpm/scripts/socketio_daemon.py"

    print("1. Test daemon start/stop coordination:")
    print(f"   a) Start daemon: {daemon_cmd} start")
    print(f"   b) Check with manager: {base_cmd} status")
    print(f"   c) Stop with manager: {base_cmd} stop --port 8765")
    print(f"   d) Verify stopped: {daemon_cmd} status")
    print()

    print("2. Test manager start/stop:")
    print(f"   a) Start with manager: {base_cmd} start")
    print(f"   b) Check status: {base_cmd} status -v")
    print(f"   c) Stop: {base_cmd} stop --port 8765")
    print()

    print("3. Test conflict detection:")
    print(f"   a) Start daemon: {daemon_cmd} start")
    print(f"   b) Try start manager: {base_cmd} start --port 8765")
    print(f"   c) Should show conflict warning")
    print()

    print("4. Test diagnose command:")
    print(f"   a) With no servers: {base_cmd} diagnose")
    print(f"   b) With daemon running: {base_cmd} diagnose")
    print(f"   c) Should show appropriate analysis")


def main():
    """Run comprehensive QA tests."""
    print("🔬 Socket.IO Management Fix - Comprehensive QA Testing")
    print("=" * 60)

    results = TestResults()

    try:
        test_stop_command_fix(results)
        test_script_coordination(results)
        test_error_handling(results)
        test_diagnostics(results)
        test_backward_compatibility(results)

        results.print_summary()

        if results.failed == 0:
            print("\n🎉 All automated tests PASSED!")
            print("✅ QA Approval: Socket.IO management fixes are working correctly")
        else:
            print(f"\n⚠️ {results.failed} test(s) failed - needs attention")
            print("❌ QA Status: CONDITIONAL PASS - see failed tests above")

        run_manual_verification()

        return 0 if results.failed == 0 else 1

    except Exception as e:
        print(f"\n💥 Test suite failed with error: {e}")
        import traceback

        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
