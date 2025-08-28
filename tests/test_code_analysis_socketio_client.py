#!/usr/bin/env python3
"""
Socket.IO Client Test for Code Analysis Dashboard
================================================

WHY: Comprehensive testing of Socket.IO client functionality for code analysis
events. Verifies that the fixed event format (using colons instead of dots/underscores)
works correctly and all expected events are properly emitted and received.

DESIGN DECISIONS:
- Use python-socketio client library to simulate dashboard client
- Monitor ALL code-related events
- Test both requesting and receiving events
- Validate event data structure and content
- Measure performance metrics
- Test error scenarios
"""

import asyncio
import json
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import socketio

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))



class CodeAnalysisSocketIOTest:
    """Test class for Socket.IO client testing of code analysis functionality."""

    def __init__(self, socketio_url="http://localhost:8765"):
        """Initialize the test client.

        Args:
            socketio_url: URL of the Socket.IO server to test against
        """
        self.socketio_url = socketio_url
        self.client = None
        self.connected = False
        self.received_events = []
        self.event_stats = {}
        self.test_results = {}
        self.start_time = None
        self.connection_lock = threading.Lock()

        # Expected event types for colon format validation
        self.expected_events = {
            "code:discover:top_level",
            "code:directory:discovered",
            "code:file:discovered",
            "code:file:analyzed",
            "code:node:found",
            "code:analysis:start",
            "code:analysis:complete",
            "code:analysis:progress",
            "code:analysis:error",
            "code:analysis:queued",
            "code:analysis:accepted",
        }

    async def setup_client(self):
        """Setup Socket.IO client with event handlers."""
        self.client = socketio.AsyncClient(
            reconnection=True,
            reconnection_attempts=3,
            reconnection_delay=1,
            logger=False,
            engineio_logger=False,
        )

        @self.client.event
        async def connect():
            with self.connection_lock:
                self.connected = True
            print(f"✅ Connected to Socket.IO server at {self.socketio_url}")

        @self.client.event
        async def disconnect():
            with self.connection_lock:
                self.connected = False
            print("❌ Disconnected from Socket.IO server")

        @self.client.event
        async def connect_error(data):
            print(f"❌ Connection error: {data}")

        # Register handlers for all expected code events
        for event_type in self.expected_events:
            self.client.on(event_type, self.create_event_handler(event_type))

        # Also listen to the generic event that all events go through
        @self.client.event
        async def claude_event(data):
            await self.handle_claude_event(data)

    def create_event_handler(self, event_type: str):
        """Create a handler for a specific event type."""

        async def handler(data):
            await self.handle_event(event_type, data)

        return handler

    async def handle_event(self, event_type: str, data: Dict[str, Any]):
        """Handle received events and update statistics."""
        timestamp = datetime.now().isoformat()
        event_data = {
            "type": event_type,
            "data": data,
            "timestamp": timestamp,
            "received_at": time.time(),
        }

        self.received_events.append(event_data)

        # Update event statistics
        if event_type not in self.event_stats:
            self.event_stats[event_type] = {
                "count": 0,
                "first_seen": timestamp,
                "last_seen": timestamp,
            }
        self.event_stats[event_type]["count"] += 1
        self.event_stats[event_type]["last_seen"] = timestamp

        print(f"📨 Received {event_type}: {json.dumps(data, indent=2)}")

    async def handle_claude_event(self, data: Dict[str, Any]):
        """Handle the generic claude_event that all events flow through."""
        event_type = data.get("type", "unknown")
        if event_type.startswith("code:"):
            await self.handle_event(f"claude_event:{event_type}", data)

    async def connect_client(self, timeout=10):
        """Connect to the Socket.IO server with timeout."""
        try:
            await asyncio.wait_for(
                self.client.connect(self.socketio_url), timeout=timeout
            )

            # Wait for connection to be established
            max_wait = 5
            waited = 0
            while not self.connected and waited < max_wait:
                await asyncio.sleep(0.1)
                waited += 0.1

            if not self.connected:
                raise TimeoutError("Failed to establish connection")

            return True

        except Exception as e:
            print(f"❌ Failed to connect to {self.socketio_url}: {e}")
            return False

    async def disconnect_client(self):
        """Disconnect from the Socket.IO server."""
        if self.client and self.connected:
            await self.client.disconnect()

    async def test_connection(self) -> Dict[str, Any]:
        """Test basic Socket.IO connection."""
        print("\n🔗 Testing Socket.IO Connection...")

        success = await self.connect_client()

        result = {
            "test_name": "connection_test",
            "success": success,
            "details": {"url": self.socketio_url, "connected": self.connected},
        }

        if success:
            print("✅ Connection test passed")
        else:
            print("❌ Connection test failed")

        return result

    async def test_event_format_validation(self) -> Dict[str, Any]:
        """Test that all events use the correct colon format."""
        print("\n📋 Testing Event Format Validation...")

        format_violations = []
        valid_events = []

        for event in self.received_events:
            event_type = event.get("type", "")

            # Check if it's a code event
            if event_type.startswith("code"):
                # Validate colon format
                if self._validate_colon_format(event_type):
                    valid_events.append(event_type)
                else:
                    format_violations.append(
                        {
                            "event_type": event_type,
                            "violation": "Does not follow colon format",
                            "timestamp": event.get("timestamp"),
                        }
                    )

        result = {
            "test_name": "event_format_validation",
            "success": len(format_violations) == 0,
            "details": {
                "total_code_events": len(
                    [
                        e
                        for e in self.received_events
                        if e.get("type", "").startswith("code")
                    ]
                ),
                "valid_events": len(valid_events),
                "format_violations": format_violations,
                "unique_valid_events": list(set(valid_events)),
            },
        }

        if result["success"]:
            print(
                f"✅ Event format validation passed - {len(valid_events)} valid events"
            )
        else:
            print(
                f"❌ Event format validation failed - {len(format_violations)} violations"
            )
            for violation in format_violations[:5]:  # Show first 5 violations
                print(f"   - {violation['event_type']}: {violation['violation']}")

        return result

    def _validate_colon_format(self, event_type: str) -> bool:
        """Validate that event uses colon format (not dots or underscores)."""
        if not event_type.startswith("code:"):
            return False

        # Should not contain dots or underscores in the main structure
        parts = event_type.split(":")
        if len(parts) < 2:
            return False

        # All parts should be lowercase and contain only letters, numbers, and underscores
        for part in parts:
            if (
                not part.islower()
                or not part.replace("_", "").replace("-", "").isalnum()
            ):
                return False

        return True

    async def test_code_discovery_flow(self) -> Dict[str, Any]:
        """Test the complete code discovery flow."""
        print("\n🔍 Testing Code Discovery Flow...")

        self.start_time = time.time()
        initial_event_count = len(self.received_events)

        # Emit top-level discovery request
        discovery_request = {"path": ".", "depth": "top_level"}

        print(
            f"📤 Emitting code:discover:top_level with data: {json.dumps(discovery_request)}"
        )
        await self.client.emit("code:discover:top_level", discovery_request)

        # Wait for events to come back
        await asyncio.sleep(2)

        new_events = self.received_events[initial_event_count:]
        discovery_events = [
            e for e in new_events if e.get("type", "").startswith("code:")
        ]

        result = {
            "test_name": "code_discovery_flow",
            "success": len(discovery_events) > 0,
            "details": {
                "request_sent": discovery_request,
                "events_received": len(discovery_events),
                "event_types": [e.get("type") for e in discovery_events],
                "time_to_first_event": None,
                "total_time": time.time() - self.start_time,
            },
        }

        # Calculate time to first event
        if discovery_events:
            first_event_time = discovery_events[0].get("received_at", self.start_time)
            result["details"]["time_to_first_event"] = (
                first_event_time - self.start_time
            )

        if result["success"]:
            print(
                f"✅ Code discovery flow passed - received {len(discovery_events)} events"
            )
        else:
            print("❌ Code discovery flow failed - no events received")

        return result

    async def test_file_analysis_request(self) -> Dict[str, Any]:
        """Test file analysis request and response."""
        print("\n📄 Testing File Analysis Request...")

        initial_event_count = len(self.received_events)

        # Find a Python file to analyze (prefer test files for safety)
        test_file = None
        current_dir = Path()
        for py_file in current_dir.glob("**/*.py"):
            if "test" in py_file.name.lower():
                test_file = str(py_file)
                break

        if not test_file:
            # Fallback to any Python file
            for py_file in current_dir.glob("*.py"):
                test_file = str(py_file)
                break

        if not test_file:
            return {
                "test_name": "file_analysis_request",
                "success": False,
                "details": {"error": "No Python file found to test with"},
            }

        # Emit file analysis request
        analysis_request = {"path": test_file}

        print(f"📤 Emitting code:analyze:file for: {test_file}")
        await self.client.emit("code:analyze:file", analysis_request)

        # Wait for analysis results
        await asyncio.sleep(3)

        new_events = self.received_events[initial_event_count:]
        analysis_events = [
            e
            for e in new_events
            if e.get("type", "").startswith("code:")
            and ("analyzed" in e.get("type", "") or "node" in e.get("type", ""))
        ]

        result = {
            "test_name": "file_analysis_request",
            "success": len(analysis_events) > 0,
            "details": {
                "file_analyzed": test_file,
                "analysis_events": len(analysis_events),
                "event_types": [e.get("type") for e in analysis_events],
            },
        }

        if result["success"]:
            print(
                f"✅ File analysis request passed - received {len(analysis_events)} analysis events"
            )
        else:
            print("❌ File analysis request failed - no analysis events received")

        return result

    async def test_event_data_structure(self) -> Dict[str, Any]:
        """Test that event data has the expected structure."""
        print("\n📊 Testing Event Data Structure...")

        structure_issues = []
        valid_events = 0

        required_fields = {"timestamp", "data"}

        for event in self.received_events:
            event_type = event.get("type", "")
            if not event_type.startswith("code:"):
                continue

            # Check required fields
            missing_fields = []
            for field in required_fields:
                if field not in event:
                    missing_fields.append(field)

            if missing_fields:
                structure_issues.append(
                    {
                        "event_type": event_type,
                        "issue": f"Missing fields: {missing_fields}",
                        "timestamp": event.get("timestamp"),
                    }
                )
            else:
                valid_events += 1

            # Validate data field structure
            event_data = event.get("data", {})
            if not isinstance(event_data, dict):
                structure_issues.append(
                    {
                        "event_type": event_type,
                        "issue": f"Data field is not a dictionary: {type(event_data)}",
                        "timestamp": event.get("timestamp"),
                    }
                )

        code_events_count = len(
            [e for e in self.received_events if e.get("type", "").startswith("code:")]
        )

        result = {
            "test_name": "event_data_structure",
            "success": len(structure_issues) == 0,
            "details": {
                "total_code_events": code_events_count,
                "valid_events": valid_events,
                "structure_issues": structure_issues[:10],  # Limit to first 10 issues
            },
        }

        if result["success"]:
            print(f"✅ Event data structure test passed - {valid_events} valid events")
        else:
            print(
                f"❌ Event data structure test failed - {len(structure_issues)} issues found"
            )

        return result

    async def test_performance_metrics(self) -> Dict[str, Any]:
        """Test performance metrics of event processing."""
        print("\n⚡ Testing Performance Metrics...")

        if not self.received_events:
            return {
                "test_name": "performance_metrics",
                "success": False,
                "details": {"error": "No events to measure performance"},
            }

        # Calculate event throughput
        code_events = [
            e for e in self.received_events if e.get("type", "").startswith("code:")
        ]

        if len(code_events) < 2:
            return {
                "test_name": "performance_metrics",
                "success": False,
                "details": {"error": "Not enough events to calculate metrics"},
            }

        first_event_time = code_events[0].get("received_at", 0)
        last_event_time = code_events[-1].get("received_at", 0)
        time_span = last_event_time - first_event_time

        throughput = len(code_events) / time_span if time_span > 0 else 0

        # Calculate average time between events
        time_diffs = []
        for i in range(1, len(code_events)):
            prev_time = code_events[i - 1].get("received_at", 0)
            curr_time = code_events[i].get("received_at", 0)
            if curr_time > prev_time:
                time_diffs.append(curr_time - prev_time)

        avg_time_between_events = sum(time_diffs) / len(time_diffs) if time_diffs else 0

        # Performance thresholds
        throughput_threshold = 10  # events per second
        avg_time_threshold = 0.5  # seconds between events

        result = {
            "test_name": "performance_metrics",
            "success": throughput >= throughput_threshold
            and avg_time_between_events <= avg_time_threshold,
            "details": {
                "total_events": len(code_events),
                "time_span": time_span,
                "throughput_eps": round(throughput, 2),
                "avg_time_between_events": round(avg_time_between_events, 3),
                "thresholds": {
                    "throughput_threshold": throughput_threshold,
                    "avg_time_threshold": avg_time_threshold,
                },
            },
        }

        if result["success"]:
            print(f"✅ Performance metrics passed - {throughput:.2f} events/sec")
        else:
            print(
                f"❌ Performance metrics failed - {throughput:.2f} events/sec (threshold: {throughput_threshold})"
            )

        return result

    async def test_error_scenarios(self) -> Dict[str, Any]:
        """Test error handling scenarios."""
        print("\n🚨 Testing Error Scenarios...")

        error_tests = []

        # Test 1: Invalid path analysis
        print("Testing invalid path analysis...")
        initial_count = len(self.received_events)

        await self.client.emit("code:analyze:file", {"path": "/invalid/path/file.py"})
        await asyncio.sleep(1)

        new_events = self.received_events[initial_count:]
        error_events = [e for e in new_events if "error" in e.get("type", "").lower()]

        error_tests.append(
            {
                "test": "invalid_path",
                "success": len(error_events) > 0,
                "error_events": len(error_events),
            }
        )

        # Test 2: Malformed request
        print("Testing malformed request...")
        initial_count = len(self.received_events)

        await self.client.emit("code:discover:top_level", {"invalid": "data"})
        await asyncio.sleep(1)

        new_events = self.received_events[initial_count:]
        error_events = [e for e in new_events if "error" in e.get("type", "").lower()]

        error_tests.append(
            {
                "test": "malformed_request",
                "success": len(error_events) > 0,
                "error_events": len(error_events),
            }
        )

        successful_tests = sum(1 for test in error_tests if test["success"])

        result = {
            "test_name": "error_scenarios",
            "success": successful_tests == len(error_tests),
            "details": {
                "total_tests": len(error_tests),
                "successful_tests": successful_tests,
                "test_results": error_tests,
            },
        }

        if result["success"]:
            print(
                f"✅ Error scenarios test passed - {successful_tests}/{len(error_tests)} tests passed"
            )
        else:
            print(
                f"❌ Error scenarios test failed - {successful_tests}/{len(error_tests)} tests passed"
            )

        return result

    async def run_full_test_suite(self) -> Dict[str, Any]:
        """Run the complete test suite."""
        print("🚀 Starting Socket.IO Client Test Suite for Code Analysis")
        print("=" * 60)

        suite_start_time = time.time()
        test_results = []

        try:
            # Setup client
            await self.setup_client()

            # Run individual tests
            test_methods = [
                self.test_connection,
                self.test_code_discovery_flow,
                self.test_file_analysis_request,
                self.test_event_format_validation,
                self.test_event_data_structure,
                self.test_performance_metrics,
                self.test_error_scenarios,
            ]

            for test_method in test_methods:
                try:
                    result = await test_method()
                    test_results.append(result)
                except Exception as e:
                    error_result = {
                        "test_name": test_method.__name__,
                        "success": False,
                        "details": {"error": str(e)},
                    }
                    test_results.append(error_result)
                    print(f"❌ Test {test_method.__name__} failed with exception: {e}")

        except Exception as e:
            print(f"💥 Test suite setup failed: {e}")
            return {
                "suite_success": False,
                "total_time": time.time() - suite_start_time,
                "error": str(e),
            }
        finally:
            # Cleanup
            await self.disconnect_client()

        # Calculate summary
        successful_tests = sum(
            1 for result in test_results if result.get("success", False)
        )
        suite_success = successful_tests == len(test_results)

        suite_result = {
            "suite_success": suite_success,
            "total_tests": len(test_results),
            "successful_tests": successful_tests,
            "failed_tests": len(test_results) - successful_tests,
            "total_time": time.time() - suite_start_time,
            "event_statistics": self.event_stats,
            "test_results": test_results,
        }

        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUITE SUMMARY")
        print("=" * 60)
        print(f"Overall Result: {'✅ PASSED' if suite_success else '❌ FAILED'}")
        print(f"Tests Passed: {successful_tests}/{len(test_results)}")
        print(f"Total Events Received: {len(self.received_events)}")
        print(
            f"Code Events Received: {len([e for e in self.received_events if e.get('type', '').startswith('code:')])}"
        )
        print(f"Unique Event Types: {len(self.event_stats)}")
        print(f"Total Time: {suite_result['total_time']:.2f}s")

        # Print event statistics
        if self.event_stats:
            print("\n📈 Event Statistics:")
            for event_type, stats in sorted(self.event_stats.items()):
                print(f"  {event_type}: {stats['count']} events")

        return suite_result


async def main():
    """Main test function."""
    # Check if server port is specified
    import argparse

    parser = argparse.ArgumentParser(
        description="Socket.IO Client Test for Code Analysis"
    )
    parser.add_argument("--port", type=int, default=8765, help="Socket.IO server port")
    parser.add_argument("--url", type=str, help="Full Socket.IO server URL")
    args = parser.parse_args()

    # Determine URL
    if args.url:
        socketio_url = args.url
    else:
        socketio_url = f"http://localhost:{args.port}"

    print(f"Testing Socket.IO server at: {socketio_url}")

    # Run test suite
    tester = CodeAnalysisSocketIOTest(socketio_url)
    results = await tester.run_full_test_suite()

    # Save results to file
    results_file = Path("test_results_socketio.json")
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n📁 Test results saved to: {results_file}")

    # Exit with appropriate code
    exit_code = 0 if results.get("suite_success", False) else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
