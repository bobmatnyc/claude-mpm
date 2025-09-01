#!/usr/bin/env python3
"""
Complete Event Flow Test for Code Analysis
==========================================

WHY: Integration test that validates the complete event flow from user interaction
to backend processing to frontend updates. Tests the entire pipeline to ensure
the fix for event naming (dots/underscores to colon format) works end-to-end.

DESIGN DECISIONS:
- Start dashboard server in subprocess
- Use both Socket.IO client and browser automation
- Monitor events at every stage of the pipeline
- Validate event format consistency
- Test lazy loading and user interactions
- Measure performance throughout the flow
"""

import asyncio
import contextlib
import json
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict

from test_code_analysis_browser import CodeAnalysisBrowserTest

# Import our test modules
from test_code_analysis_socketio_client import CodeAnalysisSocketIOTest


class CompleteEventFlowTest:
    """Integration test for complete code analysis event flow."""

    def __init__(self, base_port=8765, dashboard_timeout=30):
        """Initialize the complete event flow test.

        Args:
            base_port: Base port for dashboard server
            dashboard_timeout: Timeout for dashboard startup
        """
        self.base_port = base_port
        self.dashboard_url = f"http://localhost:{base_port}"
        self.dashboard_timeout = dashboard_timeout

        self.dashboard_process = None
        self.socketio_tester = None
        self.browser_tester = None

        self.test_results = {}
        self.event_flow_log = []
        self.performance_metrics = {}

    def start_dashboard_server(self) -> bool:
        """Start the dashboard server in a subprocess."""
        print(f"\n🚀 Starting dashboard server on port {self.base_port}...")

        try:
            # Build command to start dashboard
            python_exe = sys.executable
            cmd = [
                python_exe,
                "-m",
                "claude_mpm",
                "dashboard",
                "--port",
                str(self.base_port),
                "--host",
                "localhost",
            ]

            print(f"Command: {' '.join(cmd)}")

            # Start subprocess
            self.dashboard_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )

            # Wait for server to start
            start_time = time.time()
            server_ready = False

            while time.time() - start_time < self.dashboard_timeout:
                if self.dashboard_process.poll() is not None:
                    # Process terminated
                    stdout, stderr = self.dashboard_process.communicate()
                    print("❌ Dashboard process terminated early")
                    print(f"STDOUT: {stdout}")
                    print(f"STDERR: {stderr}")
                    return False

                # Check if server is responding
                try:
                    import requests

                    response = requests.get(self.dashboard_url, timeout=2)
                    if response.status_code == 200:
                        server_ready = True
                        break
                except:
                    pass

                time.sleep(1)
                print(f"  Waiting for server... ({int(time.time() - start_time)}s)")

            if server_ready:
                print(
                    f"✅ Dashboard server started successfully in {time.time() - start_time:.1f}s"
                )
                return True
            print(
                f"❌ Dashboard server failed to start within {self.dashboard_timeout}s"
            )
            return False

        except Exception as e:
            print(f"❌ Failed to start dashboard server: {e}")
            return False

    def stop_dashboard_server(self):
        """Stop the dashboard server subprocess."""
        if self.dashboard_process:
            print("\n🛑 Stopping dashboard server...")

            try:
                # Try graceful termination
                self.dashboard_process.terminate()
                try:
                    self.dashboard_process.wait(timeout=5)
                    print("✅ Dashboard server stopped gracefully")
                except subprocess.TimeoutExpired:
                    # Force kill if needed
                    self.dashboard_process.kill()
                    self.dashboard_process.wait()
                    print("⚠️ Dashboard server force killed")

            except Exception as e:
                print(f"❌ Error stopping dashboard server: {e}")
            finally:
                self.dashboard_process = None

    async def test_event_format_consistency(self) -> Dict[str, Any]:
        """Test that events use consistent colon format throughout the flow."""
        print("\n📋 Testing Event Format Consistency...")

        # Start monitoring with Socket.IO client
        self.socketio_tester = CodeAnalysisSocketIOTest(self.dashboard_url)
        await self.socketio_tester.setup_client()

        socketio_connected = await self.socketio_tester.connect_client()
        if not socketio_connected:
            return {
                "test_name": "event_format_consistency",
                "success": False,
                "details": {"error": "Failed to connect Socket.IO client"},
            }

        # Trigger analysis via Socket.IO
        discovery_request = {"path": ".", "depth": "top_level"}
        await self.socketio_tester.client.emit(
            "code:discover:top_level", discovery_request
        )

        # Wait for events to flow
        await asyncio.sleep(3)

        # Check event format consistency
        format_result = await self.socketio_tester.test_event_format_validation()

        await self.socketio_tester.disconnect_client()

        return format_result

    async def test_browser_to_backend_flow(self) -> Dict[str, Any]:
        """Test the complete flow from browser click to backend processing."""
        print("\n🔄 Testing Browser to Backend Flow...")

        # Setup browser tester
        self.browser_tester = CodeAnalysisBrowserTest(self.dashboard_url)
        browser_result = await self.browser_tester.run_browser_test_suite(
            "chrome", headless=True
        )

        # Focus on the analyze button and tree visualization tests
        analyze_test = None
        tree_test = None

        for test in browser_result.get("test_results", []):
            if test.get("test_name") == "analyze_button_click":
                analyze_test = test
            elif test.get("test_name") == "tree_visualization":
                tree_test = test

        success = (
            analyze_test
            and analyze_test.get("success", False)
            and tree_test
            and tree_test.get("success", False)
        )

        return {
            "test_name": "browser_to_backend_flow",
            "success": success,
            "details": {
                "analyze_button_test": analyze_test,
                "tree_visualization_test": tree_test,
                "browser_suite_success": browser_result.get("suite_success", False),
            },
        }

    async def test_lazy_loading_interaction(self) -> Dict[str, Any]:
        """Test lazy loading and user interaction flow."""
        print("\n🔄 Testing Lazy Loading Interaction...")

        # Setup Socket.IO monitoring
        self.socketio_tester = CodeAnalysisSocketIOTest(self.dashboard_url)
        await self.socketio_tester.setup_client()

        socketio_connected = await self.socketio_tester.connect_client()
        if not socketio_connected:
            return {
                "test_name": "lazy_loading_interaction",
                "success": False,
                "details": {"error": "Failed to connect Socket.IO client"},
            }

        # Test lazy loading flow
        lazy_start_time = time.time()

        # Step 1: Request top-level discovery
        await self.socketio_tester.client.emit(
            "code:discover:top_level", {"path": ".", "depth": "top_level"}
        )
        await asyncio.sleep(2)

        # Step 2: Request directory expansion
        await self.socketio_tester.client.emit(
            "code:discover:directory", {"path": "src", "depth": 1}
        )
        await asyncio.sleep(2)

        # Step 3: Request file analysis
        test_file = "src/claude_mpm/__init__.py"
        if Path(test_file).exists():
            await self.socketio_tester.client.emit(
                "code:analyze:file", {"path": test_file}
            )
            await asyncio.sleep(2)

        lazy_total_time = time.time() - lazy_start_time

        # Analyze received events
        code_events = [
            e
            for e in self.socketio_tester.received_events
            if e.get("type", "").startswith("code:")
        ]

        # Check for expected event types
        expected_lazy_events = {
            "code:directory:discovered",
            "code:file:discovered",
            "code:file:analyzed",
        }

        received_event_types = {e.get("type", "") for e in code_events}
        lazy_events_found = expected_lazy_events.intersection(received_event_types)

        await self.socketio_tester.disconnect_client()

        success = len(lazy_events_found) >= 2  # At least 2 of the expected events

        return {
            "test_name": "lazy_loading_interaction",
            "success": success,
            "details": {
                "total_code_events": len(code_events),
                "expected_events": list(expected_lazy_events),
                "received_event_types": list(received_event_types),
                "lazy_events_found": list(lazy_events_found),
                "total_time": lazy_total_time,
            },
        }

    async def test_performance_throughout_flow(self) -> Dict[str, Any]:
        """Test performance metrics throughout the complete flow."""
        print("\n⚡ Testing Performance Throughout Flow...")

        performance_start = time.time()

        # Setup Socket.IO monitoring with performance tracking
        self.socketio_tester = CodeAnalysisSocketIOTest(self.dashboard_url)
        await self.socketio_tester.setup_client()

        socketio_connected = await self.socketio_tester.connect_client()
        if not socketio_connected:
            return {
                "test_name": "performance_throughout_flow",
                "success": False,
                "details": {"error": "Failed to connect Socket.IO client"},
            }

        # Track timing for different phases
        phases = {}

        # Phase 1: Connection and initial request
        phase1_start = time.time()
        await self.socketio_tester.client.emit(
            "code:discover:top_level", {"path": ".", "depth": "top_level"}
        )
        await asyncio.sleep(1)
        phases["connection_and_request"] = time.time() - phase1_start

        # Phase 2: Wait for initial events
        phase2_start = time.time()
        await asyncio.sleep(3)
        phases["initial_event_processing"] = time.time() - phase2_start

        # Phase 3: File analysis request
        phase3_start = time.time()
        test_files = ["src/claude_mpm/__init__.py", "setup.py", "README.md"]
        for test_file in test_files:
            if Path(test_file).exists():
                await self.socketio_tester.client.emit(
                    "code:analyze:file", {"path": test_file}
                )
                await asyncio.sleep(0.5)
                break
        phases["file_analysis_request"] = time.time() - phase3_start

        # Phase 4: Wait for analysis results
        phase4_start = time.time()
        await asyncio.sleep(2)
        phases["analysis_processing"] = time.time() - phase4_start

        total_performance_time = time.time() - performance_start

        # Analyze event timing
        code_events = [
            e
            for e in self.socketio_tester.received_events
            if e.get("type", "").startswith("code:")
        ]

        # Calculate event throughput
        if len(code_events) >= 2:
            first_event_time = code_events[0].get("received_at", performance_start)
            last_event_time = code_events[-1].get("received_at", time.time())
            event_timespan = last_event_time - first_event_time
            throughput = len(code_events) / event_timespan if event_timespan > 0 else 0
        else:
            throughput = 0

        await self.socketio_tester.disconnect_client()

        # Performance thresholds
        max_total_time = 10  # seconds
        min_throughput = 1  # events per second

        success = (
            total_performance_time <= max_total_time and throughput >= min_throughput
        )

        return {
            "test_name": "performance_throughout_flow",
            "success": success,
            "details": {
                "total_time": total_performance_time,
                "phase_timings": phases,
                "event_count": len(code_events),
                "throughput_eps": round(throughput, 2),
                "thresholds": {
                    "max_total_time": max_total_time,
                    "min_throughput": min_throughput,
                },
            },
        }

    async def test_error_recovery_flow(self) -> Dict[str, Any]:
        """Test error handling and recovery in the complete flow."""
        print("\n🚨 Testing Error Recovery Flow...")

        # Setup Socket.IO monitoring
        self.socketio_tester = CodeAnalysisSocketIOTest(self.dashboard_url)
        await self.socketio_tester.setup_client()

        socketio_connected = await self.socketio_tester.connect_client()
        if not socketio_connected:
            return {
                "test_name": "error_recovery_flow",
                "success": False,
                "details": {"error": "Failed to connect Socket.IO client"},
            }

        error_tests = []

        # Test 1: Invalid directory discovery
        initial_count = len(self.socketio_tester.received_events)
        await self.socketio_tester.client.emit(
            "code:discover:directory", {"path": "/nonexistent/path"}
        )
        await asyncio.sleep(1)

        new_events = self.socketio_tester.received_events[initial_count:]
        error_events = [e for e in new_events if "error" in e.get("type", "").lower()]

        error_tests.append(
            {
                "test": "invalid_directory_discovery",
                "success": len(error_events) > 0
                or len(new_events) == 0,  # Error event OR no response
                "error_events": len(error_events),
                "total_events": len(new_events),
            }
        )

        # Test 2: Malformed file analysis request
        initial_count = len(self.socketio_tester.received_events)
        await self.socketio_tester.client.emit(
            "code:analyze:file", {"invalid_field": "invalid_value"}
        )
        await asyncio.sleep(1)

        new_events = self.socketio_tester.received_events[initial_count:]
        error_events = [e for e in new_events if "error" in e.get("type", "").lower()]

        error_tests.append(
            {
                "test": "malformed_analysis_request",
                "success": len(error_events) > 0 or len(new_events) == 0,
                "error_events": len(error_events),
                "total_events": len(new_events),
            }
        )

        # Test 3: Recovery with valid request
        initial_count = len(self.socketio_tester.received_events)
        await self.socketio_tester.client.emit("code:discover:top_level", {"path": "."})
        await asyncio.sleep(2)

        new_events = self.socketio_tester.received_events[initial_count:]
        success_events = [
            e
            for e in new_events
            if e.get("type", "").startswith("code:")
            and "error" not in e.get("type", "")
        ]

        error_tests.append(
            {
                "test": "recovery_with_valid_request",
                "success": len(success_events) > 0,
                "success_events": len(success_events),
                "total_events": len(new_events),
            }
        )

        await self.socketio_tester.disconnect_client()

        # Success if error handling works and recovery is possible
        successful_error_tests = sum(1 for test in error_tests if test["success"])
        success = successful_error_tests >= 2  # At least 2 out of 3 tests should pass

        return {
            "test_name": "error_recovery_flow",
            "success": success,
            "details": {
                "total_error_tests": len(error_tests),
                "successful_tests": successful_error_tests,
                "test_results": error_tests,
            },
        }

    async def run_complete_event_flow_test(self) -> Dict[str, Any]:
        """Run the complete event flow test suite."""
        print("🌐 Starting Complete Event Flow Test Suite")
        print("=" * 70)

        suite_start_time = time.time()

        # Start dashboard server
        server_started = self.start_dashboard_server()
        if not server_started:
            return {
                "suite_success": False,
                "error": "Failed to start dashboard server",
                "total_time": time.time() - suite_start_time,
            }

        try:
            # Run individual test phases
            test_methods = [
                self.test_event_format_consistency,
                self.test_browser_to_backend_flow,
                self.test_lazy_loading_interaction,
                self.test_performance_throughout_flow,
                self.test_error_recovery_flow,
            ]

            test_results = []
            for test_method in test_methods:
                try:
                    print(f"\n{'='*50}")
                    result = await test_method()
                    test_results.append(result)

                    if result.get("success", False):
                        print(f"✅ {result.get('test_name', 'Unknown test')} PASSED")
                    else:
                        print(f"❌ {result.get('test_name', 'Unknown test')} FAILED")

                except Exception as e:
                    error_result = {
                        "test_name": test_method.__name__,
                        "success": False,
                        "details": {"error": str(e)},
                    }
                    test_results.append(error_result)
                    print(f"💥 Test {test_method.__name__} failed with exception: {e}")

            # Calculate overall results
            successful_tests = sum(
                1 for result in test_results if result.get("success", False)
            )
            suite_success = successful_tests == len(test_results)

            complete_result = {
                "suite_success": suite_success,
                "total_tests": len(test_results),
                "successful_tests": successful_tests,
                "failed_tests": len(test_results) - successful_tests,
                "total_time": time.time() - suite_start_time,
                "dashboard_url": self.dashboard_url,
                "test_results": test_results,
            }

            # Print final summary
            print("\n" + "=" * 70)
            print("🏆 COMPLETE EVENT FLOW TEST SUMMARY")
            print("=" * 70)
            print(f"Overall Result: {'✅ PASSED' if suite_success else '❌ FAILED'}")
            print(f"Tests Passed: {successful_tests}/{len(test_results)}")
            print(f"Total Time: {complete_result['total_time']:.2f}s")
            print(f"Dashboard URL: {self.dashboard_url}")

            # Print individual test results
            print("\n📊 Individual Test Results:")
            for result in test_results:
                status = "✅ PASS" if result.get("success", False) else "❌ FAIL"
                print(f"  {status} - {result.get('test_name', 'Unknown')}")

            return complete_result

        except Exception as e:
            return {
                "suite_success": False,
                "error": str(e),
                "total_time": time.time() - suite_start_time,
            }
        finally:
            # Always cleanup
            self.stop_dashboard_server()

    def cleanup(self):
        """Cleanup resources."""
        self.stop_dashboard_server()

        # Cleanup testers
        if self.socketio_tester:
            with contextlib.suppress(Exception):
                asyncio.create_task(self.socketio_tester.disconnect_client())

        if self.browser_tester and self.browser_tester.driver:
            with contextlib.suppress(Exception):
                self.browser_tester.driver.quit()


async def main():
    """Main test function."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Complete Event Flow Test for Code Analysis"
    )
    parser.add_argument("--port", type=int, default=8765, help="Dashboard server port")
    parser.add_argument(
        "--timeout", type=int, default=30, help="Dashboard startup timeout"
    )
    args = parser.parse_args()

    print(f"Starting complete event flow test on port {args.port}")
    print(f"Dashboard startup timeout: {args.timeout}s")

    # Setup signal handler for cleanup
    tester = CompleteEventFlowTest(args.port, args.timeout)

    def signal_handler(sig, frame):
        print("\n🛑 Received interrupt signal, cleaning up...")
        tester.cleanup()
        sys.exit(1)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Run complete test suite
        results = await tester.run_complete_event_flow_test()

        # Save results to file
        results_file = Path("test_results_complete_flow.json")
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n📁 Test results saved to: {results_file}")

        # Exit with appropriate code
        exit_code = 0 if results.get("suite_success", False) else 1
        return exit_code

    except Exception as e:
        print(f"💥 Complete event flow test failed: {e}")
        return 1
    finally:
        tester.cleanup()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
