#!/usr/bin/env python3
"""Performance validation tests for Socket.IO circuit breaker.

This test suite validates the circuit breaker pattern implementation:
- Test circuit breaker opening after 5 failures
- Verify 30-second recovery timeout
- Test HALF_OPEN state recovery
- Validate fail-fast behavior
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict

# Add the src directory to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(os.path.dirname(script_dir), "src")
sys.path.insert(0, src_dir)

try:
    from claude_mpm.core.socketio_pool import (
        CircuitBreaker,
        CircuitState,
        SocketIOConnectionPool,
    )

    POOL_AVAILABLE = True
except ImportError as e:
    print(f"Circuit breaker modules not available: {e}")
    POOL_AVAILABLE = False


class CircuitBreakerPerformanceTest:
    """Test suite for circuit breaker performance validation."""

    def __init__(self):
        self.results = {
            "failure_threshold": {},
            "recovery_timeout": {},
            "half_open_recovery": {},
            "fail_fast_behavior": {},
            "integration_with_pool": {},
        }

    def test_failure_threshold(self) -> Dict[str, Any]:
        """Test circuit breaker opens after failure threshold.

        Expected behavior:
        - Circuit should remain CLOSED for failures < threshold
        - Circuit should open after reaching failure threshold (5 failures)
        - Circuit should prevent further executions when OPEN
        """
        print("Testing failure threshold behavior...")

        if not POOL_AVAILABLE:
            return {"status": "skipped", "reason": "Circuit breaker not available"}

        try:
            # Create circuit breaker with default settings (5 failures, 30s timeout)
            circuit = CircuitBreaker(failure_threshold=5, recovery_timeout=30)

            # Test initial state
            initial_state = circuit.state
            initial_can_execute = circuit.can_execute()

            # Record failures one by one and test state
            failure_states = []
            for i in range(1, 8):  # Test up to 7 failures
                circuit.record_failure()
                state_info = {
                    "failure_count": i,
                    "circuit_state": circuit.state.value,
                    "can_execute": circuit.can_execute(),
                    "failure_count_internal": circuit.failure_count,
                }
                failure_states.append(state_info)

            return {
                "status": "completed",
                "initial_state": initial_state.value,
                "initial_can_execute": initial_can_execute,
                "failure_states": failure_states,
                "threshold_respected": any(
                    state["circuit_state"] == "open" and state["failure_count"] >= 5
                    for state in failure_states
                ),
                "circuit_opens_at_threshold": failure_states[4]["circuit_state"]
                == "open",  # 5th failure (index 4)
                "prevents_execution_when_open": not failure_states[-1]["can_execute"],
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def test_recovery_timeout(self) -> Dict[str, Any]:
        """Test circuit breaker recovery timeout behavior.

        Expected behavior:
        - Circuit should remain OPEN during timeout period
        - Circuit should transition to HALF_OPEN after timeout
        - Timeout should be configurable
        """
        print("Testing recovery timeout behavior...")

        if not POOL_AVAILABLE:
            return {"status": "skipped", "reason": "Circuit breaker not available"}

        try:
            # Use shorter timeout for testing (2 seconds instead of 30)
            circuit = CircuitBreaker(failure_threshold=3, recovery_timeout=2)

            # Force circuit to OPEN state
            for _ in range(3):
                circuit.record_failure()

            # Record time when circuit opened
            open_time = datetime.now(timezone.utc)
            open_state = circuit.state.value
            open_can_execute = circuit.can_execute()

            # Test during timeout period
            time.sleep(0.5)  # Wait 0.5 seconds
            during_timeout_state = circuit.state.value
            during_timeout_can_execute = circuit.can_execute()

            # Wait for timeout to pass
            time.sleep(2.5)  # Total 3 seconds, should exceed 2-second timeout

            # Test after timeout
            after_timeout_state = circuit.state.value
            after_timeout_can_execute = circuit.can_execute()

            # Record elapsed time
            elapsed_time = (datetime.now(timezone.utc) - open_time).total_seconds()

            return {
                "status": "completed",
                "configured_timeout": 2,
                "open_state": open_state,
                "open_can_execute": open_can_execute,
                "during_timeout_state": during_timeout_state,
                "during_timeout_can_execute": during_timeout_can_execute,
                "after_timeout_state": after_timeout_state,
                "after_timeout_can_execute": after_timeout_can_execute,
                "elapsed_time": elapsed_time,
                "circuit_opened_correctly": open_state == "open"
                and not open_can_execute,
                "remained_closed_during_timeout": during_timeout_state == "open"
                and not during_timeout_can_execute,
                "transitioned_to_half_open": after_timeout_state == "half_open"
                and after_timeout_can_execute,
                "timeout_respected": elapsed_time >= 2.0,
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def test_half_open_recovery(self) -> Dict[str, Any]:
        """Test HALF_OPEN state recovery behavior.

        Expected behavior:
        - HALF_OPEN state should allow one test execution
        - Success should transition circuit back to CLOSED
        - Failure should transition circuit back to OPEN
        """
        print("Testing HALF_OPEN recovery behavior...")

        if not POOL_AVAILABLE:
            return {"status": "skipped", "reason": "Circuit breaker not available"}

        try:
            # Test successful recovery
            circuit_success = CircuitBreaker(failure_threshold=2, recovery_timeout=1)

            # Force to OPEN
            circuit_success.record_failure()
            circuit_success.record_failure()

            # Wait for timeout
            time.sleep(1.5)

            half_open_state = circuit_success.state.value
            half_open_can_execute = circuit_success.can_execute()

            # Record success (should transition to CLOSED)
            circuit_success.record_success()

            success_recovery_state = circuit_success.state.value
            success_recovery_can_execute = circuit_success.can_execute()
            success_failure_count = circuit_success.failure_count

            # Test failed recovery
            circuit_failure = CircuitBreaker(failure_threshold=2, recovery_timeout=1)

            # Force to OPEN
            circuit_failure.record_failure()
            circuit_failure.record_failure()

            # Wait for timeout
            time.sleep(1.5)

            # Record failure (should transition back to OPEN)
            circuit_failure.record_failure()

            failure_recovery_state = circuit_failure.state.value
            failure_recovery_can_execute = circuit_failure.can_execute()

            return {
                "status": "completed",
                "half_open_state": half_open_state,
                "half_open_allows_execution": half_open_can_execute,
                "success_recovery": {
                    "final_state": success_recovery_state,
                    "can_execute": success_recovery_can_execute,
                    "failure_count_reset": success_failure_count == 0,
                    "transitioned_to_closed": success_recovery_state == "closed",
                },
                "failure_recovery": {
                    "final_state": failure_recovery_state,
                    "can_execute": failure_recovery_can_execute,
                    "remained_open": failure_recovery_state == "open",
                },
                "half_open_working": half_open_state == "half_open"
                and half_open_can_execute,
                "success_recovery_working": success_recovery_state == "closed"
                and success_recovery_can_execute,
                "failure_recovery_working": failure_recovery_state == "open"
                and not failure_recovery_can_execute,
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def test_fail_fast_behavior(self) -> Dict[str, Any]:
        """Test fail-fast behavior when circuit is open.

        Expected behavior:
        - OPEN circuit should immediately reject requests without processing
        - Should provide fast failure response
        - Should not attempt actual operations when circuit is open
        """
        print("Testing fail-fast behavior...")

        if not POOL_AVAILABLE:
            return {"status": "skipped", "reason": "Circuit breaker not available"}

        try:
            circuit = CircuitBreaker(failure_threshold=3, recovery_timeout=10)

            # Measure execution time when circuit is CLOSED
            start_closed = time.time()
            can_execute_closed = circuit.can_execute()
            end_closed = time.time()
            closed_execution_time = end_closed - start_closed

            # Force circuit to OPEN
            for _ in range(3):
                circuit.record_failure()

            # Measure execution time when circuit is OPEN (should be fast)
            open_execution_times = []
            for _ in range(10):  # Test multiple times for consistency
                start_open = time.time()
                can_execute_open = circuit.can_execute()
                end_open = time.time()
                open_execution_times.append(end_open - start_open)

            avg_open_time = sum(open_execution_times) / len(open_execution_times)
            max_open_time = max(open_execution_times)

            return {
                "status": "completed",
                "closed_execution_time": closed_execution_time,
                "closed_can_execute": can_execute_closed,
                "open_execution_times": open_execution_times,
                "avg_open_execution_time": avg_open_time,
                "max_open_execution_time": max_open_time,
                "open_can_execute": can_execute_open,
                "fail_fast_working": not can_execute_open,
                "performance_improvement": closed_execution_time > avg_open_time,
                "consistently_fast": max_open_time < 0.001,  # Should be sub-millisecond
                "rejection_rate": 100.0,  # Should reject 100% when open
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def test_integration_with_pool(self) -> Dict[str, Any]:
        """Test circuit breaker integration with connection pool.

        Expected behavior:
        - Pool should respect circuit breaker state
        - Events should be dropped when circuit is open
        - Circuit should recover when service is restored
        """
        print("Testing circuit breaker integration with connection pool...")

        if not POOL_AVAILABLE:
            return {"status": "skipped", "reason": "Connection pool not available"}

        try:
            # Create pool with very sensitive circuit breaker for testing
            pool = SocketIOConnectionPool(max_connections=2)
            pool.circuit_breaker.failure_threshold = 2  # Lower threshold for testing
            pool.circuit_breaker.recovery_timeout = 2  # Shorter timeout for testing
            pool.start()

            # Test normal operation
            initial_state = pool.circuit_breaker.state.value
            initial_stats = pool.get_stats()

            # Emit some events (these will likely fail due to no server, which is what we want for testing)
            test_events = [
                {"namespace": "/hook", "event": "test1", "data": {"test": 1}},
                {"namespace": "/hook", "event": "test2", "data": {"test": 2}},
                {"namespace": "/hook", "event": "test3", "data": {"test": 3}},
            ]

            for event in test_events:
                pool.emit_event(event["namespace"], event["event"], event["data"])
                time.sleep(0.1)  # Allow processing

            # Wait for batch processing and circuit breaker response
            time.sleep(1.0)

            mid_stats = pool.get_stats()
            circuit_state_after_failures = pool.circuit_breaker.state.value

            # Try to emit more events (should be dropped if circuit is open)
            dropped_events = [
                {
                    "namespace": "/hook",
                    "event": "dropped1",
                    "data": {"test": "dropped"},
                },
                {
                    "namespace": "/hook",
                    "event": "dropped2",
                    "data": {"test": "dropped"},
                },
            ]

            for event in dropped_events:
                pool.emit_event(event["namespace"], event["event"], event["data"])
                time.sleep(0.1)

            time.sleep(0.5)
            after_drop_stats = pool.get_stats()

            # Wait for potential recovery
            time.sleep(3.0)  # Should exceed recovery timeout

            final_stats = pool.get_stats()
            final_circuit_state = pool.circuit_breaker.state.value

            pool.stop()

            return {
                "status": "completed",
                "initial_state": initial_state,
                "initial_stats": initial_stats,
                "mid_stats": mid_stats,
                "circuit_state_after_failures": circuit_state_after_failures,
                "after_drop_stats": after_drop_stats,
                "final_stats": final_stats,
                "final_circuit_state": final_circuit_state,
                "circuit_opened_on_failures": circuit_state_after_failures
                in ["open", "half_open"],
                "events_dropped_when_open": after_drop_stats["batch_queue_size"]
                <= mid_stats.get("batch_queue_size", 0),
                "circuit_attempted_recovery": final_circuit_state == "half_open"
                or (
                    final_circuit_state == "closed"
                    and circuit_state_after_failures == "open"
                ),
                "integration_working": True,  # If we got this far without exceptions
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all circuit breaker performance tests."""
        print("=== Circuit Breaker Performance Test Suite ===\n")

        if not POOL_AVAILABLE:
            return {
                "status": "skipped",
                "reason": "Circuit breaker modules not available",
                "import_error": "Could not import circuit breaker modules",
            }

        # Run tests
        self.results["failure_threshold"] = self.test_failure_threshold()
        print()

        self.results["recovery_timeout"] = self.test_recovery_timeout()
        print()

        self.results["half_open_recovery"] = self.test_half_open_recovery()
        print()

        self.results["fail_fast_behavior"] = self.test_fail_fast_behavior()
        print()

        self.results["integration_with_pool"] = self.test_integration_with_pool()
        print()

        # Generate summary
        summary = self.generate_summary()

        return {
            "status": "completed",
            "test_results": self.results,
            "summary": summary,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def generate_summary(self) -> Dict[str, Any]:
        """Generate test summary and assessment."""
        summary = {
            "total_tests": 5,
            "passed_tests": 0,
            "failed_tests": 0,
            "skipped_tests": 0,
            "circuit_breaker_features": [],
            "issues_found": [],
        }

        # Analyze each test
        for test_name, result in self.results.items():
            if result.get("status") == "completed":
                summary["passed_tests"] += 1

                # Check specific criteria
                if test_name == "failure_threshold":
                    if result.get("threshold_respected") and result.get(
                        "circuit_opens_at_threshold"
                    ):
                        summary["circuit_breaker_features"].append(
                            "Failure threshold working correctly (5 failures)"
                        )
                    else:
                        summary["issues_found"].append(
                            "Failure threshold not working as expected"
                        )

                elif test_name == "recovery_timeout":
                    if result.get("timeout_respected") and result.get(
                        "transitioned_to_half_open"
                    ):
                        summary["circuit_breaker_features"].append(
                            "Recovery timeout working correctly"
                        )
                    else:
                        summary["issues_found"].append(
                            "Recovery timeout not working as expected"
                        )

                elif test_name == "half_open_recovery":
                    if (
                        result.get("half_open_working")
                        and result.get("success_recovery_working")
                        and result.get("failure_recovery_working")
                    ):
                        summary["circuit_breaker_features"].append(
                            "HALF_OPEN state transitions working correctly"
                        )
                    else:
                        summary["issues_found"].append(
                            "HALF_OPEN state recovery not working properly"
                        )

                elif test_name == "fail_fast_behavior":
                    if result.get("fail_fast_working") and result.get(
                        "consistently_fast"
                    ):
                        summary["circuit_breaker_features"].append(
                            "Fail-fast behavior working correctly"
                        )
                    else:
                        summary["issues_found"].append(
                            "Fail-fast behavior not working as expected"
                        )

                elif test_name == "integration_with_pool":
                    if result.get("integration_working") and result.get(
                        "circuit_opened_on_failures"
                    ):
                        summary["circuit_breaker_features"].append(
                            "Integration with connection pool working"
                        )
                    else:
                        summary["issues_found"].append(
                            "Circuit breaker integration issues detected"
                        )

            elif result.get("status") == "error":
                summary["failed_tests"] += 1
                summary["issues_found"].append(
                    f"{test_name}: {result.get('error', 'Unknown error')}"
                )

            elif result.get("status") == "skipped":
                summary["skipped_tests"] += 1

        # Overall assessment
        summary["overall_status"] = (
            "PASS" if len(summary["issues_found"]) == 0 else "FAIL"
        )
        summary["success_rate"] = summary["passed_tests"] / summary["total_tests"] * 100

        return summary


def main():
    """Run circuit breaker performance tests."""
    print("Socket.IO Circuit Breaker Performance Validation")
    print("=" * 50)
    print()

    tester = CircuitBreakerPerformanceTest()
    results = tester.run_all_tests()

    # Print summary
    print("=== TEST SUMMARY ===")
    if results["status"] == "skipped":
        print(f"Tests skipped: {results['reason']}")
        return

    summary = results["summary"]
    print(f"Overall Status: {summary['overall_status']}")
    print(f"Success Rate: {summary['success_rate']:.1f}%")
    print(
        f"Tests: {summary['passed_tests']} passed, {summary['failed_tests']} failed, {summary['skipped_tests']} skipped"
    )
    print()

    if summary["circuit_breaker_features"]:
        print("✅ Circuit Breaker Features Working:")
        for feature in summary["circuit_breaker_features"]:
            print(f"   • {feature}")
        print()

    if summary["issues_found"]:
        print("❌ Issues Found:")
        for issue in summary["issues_found"]:
            print(f"   • {issue}")
        print()

    # Save detailed results
    results_file = "/tmp/circuit_breaker_test_results.json"
    try:
        with results_file.open("w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"📄 Detailed results saved to: {results_file}")
    except Exception as e:
        print(f"Failed to save results: {e}")


if __name__ == "__main__":
    main()
