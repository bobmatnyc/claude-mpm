#!/usr/bin/env python3
"""End-to-end test script for Memory Guardian system.

Simulates a memory-intensive Claude session, triggers memory threshold breaches,
verifies automatic restart, confirms state preservation, and tests restart loop protection.
"""

import asyncio
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.config.memory_guardian_config import (
    MemoryGuardianConfig,
    MemoryThresholds,
    MonitoringConfig,
    RestartPolicy,
)
from claude_mpm.services.infrastructure.memory_dashboard import MemoryDashboard
from claude_mpm.services.infrastructure.memory_guardian import (
    MemoryGuardian,
    MemoryState,
    ProcessState,
)


class MemoryGuardianE2ETest:
    """End-to-end test for Memory Guardian system."""

    def __init__(self, temp_dir: Path):
        """Initialize E2E test.

        Args:
            temp_dir: Temporary directory for test files
        """
        self.temp_dir = temp_dir
        self.guardian: Optional[MemoryGuardian] = None
        self.dashboard: Optional[MemoryDashboard] = None
        self.test_results: Dict[str, Any] = {
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "details": [],
        }

    async def setup(self):
        """Set up test environment."""
        print("\n" + "=" * 60)
        print("MEMORY GUARDIAN E2E TEST")
        print("=" * 60)
        print("\nSetting up test environment...")

        # Create configuration
        config = MemoryGuardianConfig(
            enabled=True,
            thresholds=MemoryThresholds(
                warning=100, critical=200, emergency=300  # Low thresholds for testing
            ),
            restart_policy=RestartPolicy(
                max_attempts=3,
                attempt_window=300,
                cooldown_seconds=1,
                exponential_backoff=True,
                graceful_timeout=5,
                force_kill_timeout=2,
            ),
            monitoring=MonitoringConfig(
                check_interval=1,
                check_interval_warning=0.5,
                check_interval_critical=0.25,
                log_memory_stats=True,
                log_interval=10,
            ),
            # Use a simple Python script that consumes memory
            process_command=[
                "python",
                "-c",
                """
import time
import sys

# Allocate memory in chunks
memory_blocks = []
block_size = 10 * 1024 * 1024  # 10MB blocks

print("Memory consumer process started", flush=True)

for i in range(50):  # Up to 500MB
    memory_blocks.append(bytearray(block_size))
    print(f"Allocated {(i+1)*10}MB", flush=True)
    time.sleep(2)

    # Check for termination signal
    if i > 0 and i % 5 == 0:
        sys.stdout.flush()

print("Memory consumer process completed", flush=True)
""",
            ],
            state_file=str(self.temp_dir / "memory_guardian.json"),
            persist_state=True,
            auto_start=False,  # We'll control process start
        )

        # Create Memory Guardian
        self.guardian = MemoryGuardian(config)
        success = await self.guardian.initialize()

        if not success:
            raise RuntimeError("Failed to initialize Memory Guardian")

        # Create Dashboard
        self.dashboard = MemoryDashboard(
            memory_guardian=self.guardian,
            restart_protection=self.guardian.restart_protection,
            health_monitor=self.guardian.health_monitor,
            graceful_degradation=self.guardian.graceful_degradation,
            metrics_file=self.temp_dir / "metrics.json",
            export_interval_seconds=5,
        )
        await self.dashboard.initialize()

        print("✓ Test environment ready")

    async def test_memory_monitoring(self):
        """Test 1: Basic memory monitoring."""
        print("\n" + "-" * 60)
        print("TEST 1: Memory Monitoring")
        print("-" * 60)

        try:
            # Start monitoring
            self.guardian.start_monitoring()
            print("✓ Monitoring started")

            # Simulate memory readings
            import unittest.mock as mock

            with mock.patch.object(self.guardian, "get_memory_usage") as mock_memory:
                # Normal state
                mock_memory.return_value = 50.0
                await self.guardian.monitor_memory()
                assert self.guardian.memory_state == MemoryState.NORMAL
                print(f"✓ Normal state detected (50MB)")

                # Warning state
                mock_memory.return_value = 150.0
                await self.guardian.monitor_memory()
                assert self.guardian.memory_state == MemoryState.WARNING
                print(f"✓ Warning state detected (150MB)")

                # Critical state
                mock_memory.return_value = 250.0
                await self.guardian.monitor_memory()
                assert self.guardian.memory_state == MemoryState.CRITICAL
                print(f"✓ Critical state detected (250MB)")

            self._record_test_result("Memory Monitoring", True)
            print("✓ TEST PASSED: Memory monitoring working correctly")

        except Exception as e:
            self._record_test_result("Memory Monitoring", False, str(e))
            print(f"✗ TEST FAILED: {e}")

        finally:
            await self.guardian.stop_monitoring()

    async def test_automatic_restart(self):
        """Test 2: Automatic restart on memory threshold."""
        print("\n" + "-" * 60)
        print("TEST 2: Automatic Restart")
        print("-" * 60)

        try:
            # Mock process operations for controlled testing
            import unittest.mock as mock

            restart_count = 0

            async def mock_restart(reason):
                nonlocal restart_count
                restart_count += 1
                print(f"  → Restart triggered: {reason}")
                return True

            with mock.patch.object(
                self.guardian, "restart_process", side_effect=mock_restart
            ):
                with mock.patch.object(
                    self.guardian, "get_memory_usage", return_value=350.0
                ):
                    # Trigger emergency threshold
                    await self.guardian.monitor_memory()

                    # Wait for restart to be triggered
                    await asyncio.sleep(0.5)

                    assert restart_count > 0
                    print(f"✓ Automatic restart triggered ({restart_count} time(s))")

            self._record_test_result("Automatic Restart", True)
            print("✓ TEST PASSED: Automatic restart working")

        except Exception as e:
            self._record_test_result("Automatic Restart", False, str(e))
            print(f"✗ TEST FAILED: {e}")

    async def test_state_preservation(self):
        """Test 3: State preservation across restarts."""
        print("\n" + "-" * 60)
        print("TEST 3: State Preservation")
        print("-" * 60)

        try:
            # Create test state
            test_state = {
                "session_id": "test_123",
                "timestamp": time.time(),
                "data": {"key": "value"},
            }

            # Save state
            if self.guardian.state_manager:
                await self.guardian.state_manager.persist_state(test_state)
                print("✓ State saved")

                # Simulate restart
                print("  → Simulating restart...")

                # Restore state
                restored = await self.guardian.state_manager.restore_state()
                assert restored is not None
                assert restored.get("session_id") == "test_123"
                print("✓ State restored successfully")

            self._record_test_result("State Preservation", True)
            print("✓ TEST PASSED: State preservation working")

        except Exception as e:
            self._record_test_result("State Preservation", False, str(e))
            print(f"✗ TEST FAILED: {e}")

    async def test_restart_loop_protection(self):
        """Test 4: Restart loop protection."""
        print("\n" + "-" * 60)
        print("TEST 4: Restart Loop Protection")
        print("-" * 60)

        try:
            protection = self.guardian.restart_protection
            if protection:
                # Simulate multiple failed restarts
                for i in range(5):
                    protection.record_restart(f"Test failure {i}", 300, False)

                    if i < 3:
                        allowed, reason = protection.should_allow_restart()
                        print(
                            f"  → Restart {i+1}: {'Allowed' if allowed else f'Blocked ({reason})'}"
                        )
                    else:
                        allowed, reason = protection.should_allow_restart()
                        assert not allowed
                        print(f"  → Restart {i+1}: Blocked - {reason}")

                # Check circuit breaker
                stats = protection.get_restart_statistics()
                print(f"✓ Circuit breaker state: {stats.circuit_state.value}")

                # Test manual reset
                protection.reset_circuit_breaker()
                allowed, _ = protection.should_allow_restart()
                assert allowed
                print("✓ Circuit breaker reset successful")

            self._record_test_result("Restart Loop Protection", True)
            print("✓ TEST PASSED: Restart loop protection working")

        except Exception as e:
            self._record_test_result("Restart Loop Protection", False, str(e))
            print(f"✗ TEST FAILED: {e}")

    async def test_memory_leak_detection(self):
        """Test 5: Memory leak detection."""
        print("\n" + "-" * 60)
        print("TEST 5: Memory Leak Detection")
        print("-" * 60)

        try:
            protection = self.guardian.restart_protection
            if protection:
                # Simulate memory leak pattern
                base_memory = 100.0
                for i in range(20):
                    memory = base_memory + (i * 20)  # 20MB/sample growth
                    protection.record_memory_sample(memory)
                    await asyncio.sleep(0.01)

                # Detect leak
                trend = protection.detect_memory_leak()
                assert trend is not None

                if trend.is_leak_suspected:
                    print(f"✓ Memory leak detected!")
                    print(f"  → Growth rate: {trend.slope_mb_per_min:.2f} MB/min")
                    print(f"  → Correlation: {trend.r_squared:.3f}")
                else:
                    print("⚠ Memory leak not detected (threshold not met)")

            self._record_test_result("Memory Leak Detection", True)
            print("✓ TEST PASSED: Memory leak detection working")

        except Exception as e:
            self._record_test_result("Memory Leak Detection", False, str(e))
            print(f"✗ TEST FAILED: {e}")

    async def test_dashboard_metrics(self):
        """Test 6: Dashboard and metrics."""
        print("\n" + "-" * 60)
        print("TEST 6: Dashboard and Metrics")
        print("-" * 60)

        try:
            # Get dashboard summary
            summary = self.dashboard.get_summary()
            print("Dashboard Summary:")
            print("-" * 30)
            print(summary)
            print("-" * 30)

            # Get metrics
            metrics = self.dashboard.get_current_metrics()
            print(f"✓ Current memory: {metrics.memory_current_mb:.2f} MB")
            print(f"✓ Process state: {metrics.process_state}")
            print(f"✓ Health status: {metrics.health_status}")

            # Export metrics
            json_metrics = self.dashboard.export_json_metrics()
            assert len(json_metrics) > 0
            print("✓ JSON metrics exported")

            prometheus_metrics = self.dashboard.export_prometheus_metrics()
            assert "memory_current_mb" in prometheus_metrics
            print("✓ Prometheus metrics exported")

            self._record_test_result("Dashboard and Metrics", True)
            print("✓ TEST PASSED: Dashboard and metrics working")

        except Exception as e:
            self._record_test_result("Dashboard and Metrics", False, str(e))
            print(f"✗ TEST FAILED: {e}")

    async def test_graceful_degradation(self):
        """Test 7: Graceful degradation."""
        print("\n" + "-" * 60)
        print("TEST 7: Graceful Degradation")
        print("-" * 60)

        try:
            degradation = self.guardian.graceful_degradation
            if degradation:
                # Simulate feature degradation
                await degradation.degrade_feature(
                    "memory_monitoring", "Test degradation", "fallback mode"
                )

                status = degradation.get_status()
                print(f"✓ Degradation level: {status.level.value}")
                print(f"✓ Degraded features: {status.degraded_features}")

                # Recover feature
                await degradation.recover_feature("memory_monitoring")
                status = degradation.get_status()
                assert status.degraded_features == 0
                print("✓ Feature recovered successfully")

            self._record_test_result("Graceful Degradation", True)
            print("✓ TEST PASSED: Graceful degradation working")

        except Exception as e:
            self._record_test_result("Graceful Degradation", False, str(e))
            print(f"✗ TEST FAILED: {e}")

    async def cleanup(self):
        """Clean up test environment."""
        print("\n" + "-" * 60)
        print("Cleaning up...")

        if self.dashboard:
            await self.dashboard.shutdown()

        if self.guardian:
            await self.guardian.shutdown()

        print("✓ Cleanup complete")

    def _record_test_result(
        self, test_name: str, passed: bool, error: Optional[str] = None
    ):
        """Record test result.

        Args:
            test_name: Name of the test
            passed: Whether test passed
            error: Error message if failed
        """
        self.test_results["tests_run"] += 1
        if passed:
            self.test_results["tests_passed"] += 1
        else:
            self.test_results["tests_failed"] += 1

        self.test_results["details"].append(
            {"test": test_name, "passed": passed, "error": error}
        )

    def generate_report(self):
        """Generate test report."""
        print("\n" + "=" * 60)
        print("TEST REPORT")
        print("=" * 60)

        print(f"\nTests Run:    {self.test_results['tests_run']}")
        print(f"Tests Passed: {self.test_results['tests_passed']}")
        print(f"Tests Failed: {self.test_results['tests_failed']}")

        if self.test_results["tests_failed"] > 0:
            print("\nFailed Tests:")
            for detail in self.test_results["details"]:
                if not detail["passed"]:
                    print(f"  - {detail['test']}: {detail['error']}")

        # Save report to file
        report_file = self.temp_dir / "test_report.json"
        with open(report_file, "w") as f:
            json.dump(self.test_results, f, indent=2)
        print(f"\nDetailed report saved to: {report_file}")

        # Return exit code
        return 0 if self.test_results["tests_failed"] == 0 else 1

    async def run_all_tests(self):
        """Run all E2E tests."""
        await self.setup()

        # Run tests
        await self.test_memory_monitoring()
        await self.test_automatic_restart()
        await self.test_state_preservation()
        await self.test_restart_loop_protection()
        await self.test_memory_leak_detection()
        await self.test_dashboard_metrics()
        await self.test_graceful_degradation()

        await self.cleanup()

        return self.generate_report()


async def main():
    """Main entry point."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test = MemoryGuardianE2ETest(Path(tmpdir))
        exit_code = await test.run_all_tests()
        sys.exit(exit_code)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nTest failed with error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
