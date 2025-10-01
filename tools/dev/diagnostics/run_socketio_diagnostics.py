#!/usr/bin/env python3
"""Socket.IO Diagnostic Test Runner.

This script orchestrates all Socket.IO diagnostic tests to identify where
the event flow is breaking down. It provides a comprehensive analysis of:

1. Server-side event monitoring
2. Hook handler event sending
3. Dashboard namespace listening
4. End-to-end event flow
5. Connection and authentication issues

WHY this orchestrated approach:
- Runs diagnostics in the correct order
- Provides unified reporting
- Identifies the specific point of failure
- Gives actionable recommendations
"""

import subprocess
import sys
import threading
import time
import webbrowser
from datetime import datetime
from pathlib import Path

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

try:
    import socketio

    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False


class SocketIODiagnosticRunner:
    """Orchestrates all Socket.IO diagnostic tests."""

    def __init__(self):
        self.script_dir = Path(__file__).parent
        self.start_time = datetime.now()
        self.test_results = {}
        self.server_process = None
        self.dashboard_url = None

        print("🔍 SOCKET.IO COMPREHENSIVE DIAGNOSTIC SUITE")
        print("=" * 80)
        print(f"📅 Started: {self.start_time.isoformat()}")
        print(f"📁 Script directory: {self.script_dir}")
        print(f"🐍 Python: {sys.executable}")
        print(f"📦 Socket.IO available: {SOCKETIO_AVAILABLE}")
        print("=" * 80)

    def check_prerequisites(self) -> bool:
        """Check if all prerequisites are met."""
        print("🔧 Checking prerequisites...")

        if not SOCKETIO_AVAILABLE:
            print("❌ python-socketio package not installed")
            print("   Run: pip install python-socketio[asyncio_client] aiohttp")
            return False

        # Check if diagnostic scripts exist
        required_scripts = [
            "diagnostic_socketio_server_monitor.py",
            "diagnostic_hook_handler_test.py",
            "diagnostic_dashboard_namespace_test.html",
            "diagnostic_end_to_end_test.py",
            "diagnostic_connection_auth_test.py",
        ]

        missing_scripts = []
        for script in required_scripts:
            script_path = self.script_dir / script
            if not script_path.exists():
                missing_scripts.append(script)

        if missing_scripts:
            print(f"❌ Missing diagnostic scripts: {missing_scripts}")
            return False

        print("✅ Prerequisites check passed")
        return True

    def start_diagnostic_server(self) -> bool:
        """Start the diagnostic Socket.IO server."""
        print("\n🚀 Starting diagnostic Socket.IO server...")

        server_script = self.script_dir / "diagnostic_socketio_server_monitor.py"

        try:
            self.server_process = subprocess.Popen(
                [sys.executable, str(server_script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
            )

            # Give server time to start and capture initial output
            time.sleep(2)

            # Check if server is still running
            if self.server_process.poll() is None:
                print("✅ Diagnostic server started successfully")

                # Start thread to monitor server output
                self.server_output_thread = threading.Thread(
                    target=self._monitor_server_output, daemon=True
                )
                self.server_output_thread.start()

                return True
            # Server exited immediately
            output = (
                self.server_process.stdout.read()
                if self.server_process.stdout
                else "No output"
            )
            print(f"❌ Diagnostic server failed to start: {output}")
            return False

        except Exception as e:
            print(f"❌ Failed to start diagnostic server: {e}")
            return False

    def _monitor_server_output(self):
        """Monitor server output in background."""
        if not self.server_process:
            return

        try:
            for line in iter(self.server_process.stdout.readline, ""):
                if line.strip():
                    print(f"[SERVER] {line.strip()}")
        except Exception:
            pass

    def stop_diagnostic_server(self):
        """Stop the diagnostic server."""
        if self.server_process:
            print("\n🛑 Stopping diagnostic server...")
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
                print("✅ Diagnostic server stopped")
            except subprocess.TimeoutExpired:
                print("⚠️  Server didn't stop gracefully, killing...")
                self.server_process.kill()
            except Exception as e:
                print(f"❌ Error stopping server: {e}")

    def run_connection_auth_test(self) -> bool:
        """Run connection and authentication diagnostic."""
        print("\n🔐 Running connection & authentication diagnostic...")

        script_path = self.script_dir / "diagnostic_connection_auth_test.py"

        try:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                timeout=60, check=False,
            )

            print("📋 Connection & Auth Test Output:")
            print("-" * 50)
            print(result.stdout)
            if result.stderr:
                print("STDERR:")
                print(result.stderr)
            print("-" * 50)

            success = result.returncode == 0
            self.test_results["connection_auth"] = {
                "success": success,
                "output": result.stdout,
                "errors": result.stderr,
            }

            if success:
                print("✅ Connection & authentication test PASSED")
            else:
                print("❌ Connection & authentication test FAILED")

            return success

        except subprocess.TimeoutExpired:
            print("❌ Connection & authentication test TIMED OUT")
            self.test_results["connection_auth"] = {
                "success": False,
                "output": "",
                "errors": "Test timed out",
            }
            return False
        except Exception as e:
            print(f"❌ Connection & authentication test ERROR: {e}")
            self.test_results["connection_auth"] = {
                "success": False,
                "output": "",
                "errors": str(e),
            }
            return False

    def run_hook_handler_test(self) -> bool:
        """Run hook handler event sending diagnostic."""
        print("\n🎣 Running hook handler diagnostic...")

        script_path = self.script_dir / "diagnostic_hook_handler_test.py"

        try:
            result = subprocess.run(
                [sys.executable, str(script_path), "--continuous", "10"],
                capture_output=True,
                text=True,
                timeout=30, check=False,
            )

            print("📋 Hook Handler Test Output:")
            print("-" * 50)
            print(result.stdout)
            if result.stderr:
                print("STDERR:")
                print(result.stderr)
            print("-" * 50)

            success = result.returncode == 0
            self.test_results["hook_handler"] = {
                "success": success,
                "output": result.stdout,
                "errors": result.stderr,
            }

            if success:
                print("✅ Hook handler test PASSED")
            else:
                print("❌ Hook handler test FAILED")

            return success

        except subprocess.TimeoutExpired:
            print("❌ Hook handler test TIMED OUT")
            self.test_results["hook_handler"] = {
                "success": False,
                "output": "",
                "errors": "Test timed out",
            }
            return False
        except Exception as e:
            print(f"❌ Hook handler test ERROR: {e}")
            self.test_results["hook_handler"] = {
                "success": False,
                "output": "",
                "errors": str(e),
            }
            return False

    def run_end_to_end_test(self) -> bool:
        """Run end-to-end event flow diagnostic."""
        print("\n🔄 Running end-to-end diagnostic...")

        script_path = self.script_dir / "diagnostic_end_to_end_test.py"

        try:
            # Use different port for end-to-end test to avoid conflicts
            result = subprocess.run(
                [sys.executable, str(script_path), "--port", "8766", "--events", "5"],
                capture_output=True,
                text=True,
                timeout=120, check=False,
            )

            print("📋 End-to-End Test Output:")
            print("-" * 50)
            print(result.stdout)
            if result.stderr:
                print("STDERR:")
                print(result.stderr)
            print("-" * 50)

            success = result.returncode == 0
            self.test_results["end_to_end"] = {
                "success": success,
                "output": result.stdout,
                "errors": result.stderr,
            }

            if success:
                print("✅ End-to-end test PASSED")
            else:
                print("❌ End-to-end test FAILED")

            return success

        except subprocess.TimeoutExpired:
            print("❌ End-to-end test TIMED OUT")
            self.test_results["end_to_end"] = {
                "success": False,
                "output": "",
                "errors": "Test timed out",
            }
            return False
        except Exception as e:
            print(f"❌ End-to-end test ERROR: {e}")
            self.test_results["end_to_end"] = {
                "success": False,
                "output": "",
                "errors": str(e),
            }
            return False

    def open_dashboard_diagnostic(self):
        """Open the dashboard diagnostic in a web browser."""
        print("\n📊 Opening dashboard diagnostic...")

        dashboard_path = self.script_dir / "diagnostic_dashboard_namespace_test.html"
        self.dashboard_url = f"file://{dashboard_path.absolute()}"

        try:
            webbrowser.open(self.dashboard_url)
            print(f"✅ Dashboard opened: {self.dashboard_url}")
            print("🔧 Instructions:")
            print("   1. The dashboard should automatically connect to all namespaces")
            print("   2. Look for connection status indicators")
            print("   3. Watch the event log for incoming events")
            print("   4. Try the 'Send Test Events' button")
            print("   5. Check which namespaces are receiving events")
            print("\n⏳ Please test the dashboard and press Enter when done...")
            input()
            return True
        except Exception as e:
            print(f"❌ Failed to open dashboard: {e}")
            print(f"📍 Manually open: {self.dashboard_url}")
            return False

    def analyze_results(self):
        """Analyze all test results and provide recommendations."""
        print("\n" + "=" * 80)
        print("📊 COMPREHENSIVE DIAGNOSTIC ANALYSIS")
        print("=" * 80)

        # Overall summary
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results.values() if r["success"])

        print("📈 OVERALL RESULTS:")
        print(f"   Tests run: {total_tests}")
        print(f"   Passed: {passed_tests}")
        print(f"   Failed: {total_tests - passed_tests}")

        # Individual test results
        print("\n📋 INDIVIDUAL TEST RESULTS:")
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            print(f"   {test_name}: {status}")

        # Specific diagnostics and recommendations
        print("\n🔍 DIAGNOSTIC CONCLUSIONS:")

        # Connection issues
        conn_auth = self.test_results.get("connection_auth", {})
        if not conn_auth.get("success"):
            print("   🚨 CONNECTION ISSUES DETECTED:")
            print("      - Check if Socket.IO server is running on port 8765")
            print("      - Verify authentication token configuration")
            print("      - Check firewall/network settings")

        # Hook handler issues
        hook_handler = self.test_results.get("hook_handler", {})
        if not hook_handler.get("success"):
            print("   🚨 HOOK HANDLER ISSUES DETECTED:")
            print("      - Hook handler cannot connect to server")
            print("      - Check namespace routing (/hook, /system)")
            print("      - Verify event emission logic")

        # End-to-end issues
        e2e = self.test_results.get("end_to_end", {})
        if not e2e.get("success"):
            print("   🚨 END-TO-END FLOW ISSUES DETECTED:")
            print("      - Event flow from hook -> server -> dashboard broken")
            print("      - Check event routing and namespace configuration")
            print("      - Verify client-side event listeners")

        # Success case
        if passed_tests == total_tests:
            print("   ✅ ALL TESTS PASSED:")
            print("      - Socket.IO server is working correctly")
            print("      - Hook handler can connect and send events")
            print("      - Event flow is functioning end-to-end")
            print("      - Issue may be in the actual claude-mpm integration")

        # Next steps
        print("\n🎯 RECOMMENDED NEXT STEPS:")

        if not conn_auth.get("success"):
            print("   1. Fix basic connectivity issues first")
            print("      - Start the Socket.IO server manually")
            print(
                "      - Test with 'python scripts/diagnostic_connection_auth_test.py'"
            )

        elif not hook_handler.get("success"):
            print("   1. Debug hook handler integration")
            print("      - Check claude-mpm hook configuration")
            print("      - Verify hook handler script path")
            print("      - Test with CLAUDE_MPM_HOOK_DEBUG=true")

        elif not e2e.get("success"):
            print("   1. Debug event routing")
            print("      - Check namespace configuration")
            print("      - Verify room-based broadcasting")
            print("      - Test dashboard event listeners")

        else:
            print("   1. Check actual claude-mpm session integration")
            print("      - Run claude-mpm with Socket.IO server running")
            print("      - Check if hooks are being triggered")
            print("      - Verify dashboard connection during real session")

        print(f"\n⏰ Diagnostic completed: {datetime.now().isoformat()}")
        total_time = (datetime.now() - self.start_time).total_seconds()
        print(f"🕒 Total time: {total_time:.2f} seconds")

    def run_full_diagnostic(self):
        """Run the complete diagnostic suite."""
        try:
            # Step 1: Check prerequisites
            if not self.check_prerequisites():
                return False

            # Step 2: Start diagnostic server
            if not self.start_diagnostic_server():
                return False

            time.sleep(1)  # Let server stabilize

            # Step 3: Run connection & authentication test
            self.run_connection_auth_test()
            time.sleep(1)

            # Step 4: Run hook handler test
            self.run_hook_handler_test()
            time.sleep(1)

            # Step 5: Open dashboard diagnostic
            self.open_dashboard_diagnostic()

            # Step 6: Run end-to-end test (uses separate server)
            self.run_end_to_end_test()

            # Step 7: Analyze results
            self.analyze_results()

            return True

        except KeyboardInterrupt:
            print("\n🛑 Diagnostic suite interrupted by user")
            return False
        except Exception as e:
            print(f"❌ Diagnostic suite error: {e}")
            import traceback

            traceback.print_exc()
            return False
        finally:
            self.stop_diagnostic_server()


def main():
    """Main diagnostic runner."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Socket.IO Comprehensive Diagnostic Suite"
    )
    parser.add_argument(
        "--no-browser", action="store_true", help="Skip opening dashboard in browser"
    )
    args = parser.parse_args()

    runner = SocketIODiagnosticRunner()

    if args.no_browser:
        runner.open_dashboard_diagnostic = lambda: True  # Skip browser opening

    success = runner.run_full_diagnostic()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
