"""
Unit tests for CrashDetector
=============================

Tests crash detection via health status monitoring, callback invocation,
and crash history tracking.
"""

from unittest.mock import MagicMock, Mock

import pytest

from claude_mpm.services.core.models.health import (
    DeploymentHealth,
    HealthCheckResult,
    HealthStatus,
)
from claude_mpm.services.local_ops.crash_detector import CrashDetector


class TestCrashDetector:
    """Test suite for CrashDetector."""

    @pytest.fixture
    def mock_health_manager(self):
        """Create mock health check manager."""
        mock = MagicMock()
        mock.check_health.return_value = DeploymentHealth(
            deployment_id="test-deployment",
            overall_status=HealthStatus.HEALTHY,
            checks=[],
        )
        return mock

    @pytest.fixture
    def crash_detector(self, mock_health_manager):
        """Create CrashDetector instance."""
        detector = CrashDetector(health_manager=mock_health_manager)
        detector.initialize()
        return detector

    def test_initialization(self, crash_detector, mock_health_manager):
        """Test crash detector initializes correctly."""
        assert crash_detector.health_manager == mock_health_manager
        # Verify callback was registered with health manager
        mock_health_manager.register_status_callback.assert_called_once()

    def test_register_crash_callback(self, crash_detector):
        """Test registering crash callbacks."""
        callback = Mock()
        crash_detector.register_crash_callback(callback)

        # Verify callback is stored
        assert callback in crash_detector._crash_callbacks

    def test_start_monitoring(self, crash_detector, mock_health_manager):
        """Test starting crash monitoring for a deployment."""
        deployment_id = "test-deployment"

        # Start monitoring
        crash_detector.start_monitoring(deployment_id)

        # Verify monitoring started
        assert crash_detector.is_monitoring(deployment_id)
        assert deployment_id in crash_detector._monitored_deployments

        # Verify initial health check was performed
        mock_health_manager.check_health.assert_called_with(deployment_id)

    def test_stop_monitoring(self, crash_detector):
        """Test stopping crash monitoring."""
        deployment_id = "test-deployment"

        # Start then stop monitoring
        crash_detector.start_monitoring(deployment_id)
        assert crash_detector.is_monitoring(deployment_id)

        crash_detector.stop_monitoring(deployment_id)
        assert not crash_detector.is_monitoring(deployment_id)
        assert deployment_id not in crash_detector._monitored_deployments

    def test_is_monitoring(self, crash_detector):
        """Test checking if deployment is being monitored."""
        deployment_id = "test-deployment"

        # Initially not monitoring
        assert not crash_detector.is_monitoring(deployment_id)

        # Start monitoring
        crash_detector.start_monitoring(deployment_id)
        assert crash_detector.is_monitoring(deployment_id)

    def test_get_crash_count(self, crash_detector):
        """Test getting crash count for a deployment."""
        deployment_id = "test-deployment"

        # Initially zero crashes
        assert crash_detector.get_crash_count(deployment_id) == 0

        # Increment crash count
        crash_detector._crash_count[deployment_id] = 3
        assert crash_detector.get_crash_count(deployment_id) == 3

    def test_reset_crash_count(self, crash_detector):
        """Test resetting crash count."""
        deployment_id = "test-deployment"

        # Set crash count
        crash_detector._crash_count[deployment_id] = 5
        assert crash_detector.get_crash_count(deployment_id) == 5

        # Reset
        crash_detector.reset_crash_count(deployment_id)
        assert crash_detector.get_crash_count(deployment_id) == 0

    def test_detect_crash_healthy_to_unhealthy(self, crash_detector):
        """Test crash detection when status transitions from HEALTHY to UNHEALTHY."""
        deployment_id = "test-deployment"
        callback = Mock()

        # Setup
        crash_detector.register_crash_callback(callback)
        crash_detector.start_monitoring(deployment_id)

        # Simulate health status change: HEALTHY → UNHEALTHY
        crash_detector._on_health_status_change(
            deployment_id, HealthStatus.HEALTHY, HealthStatus.UNHEALTHY
        )

        # Verify crash was detected
        assert crash_detector.get_crash_count(deployment_id) == 1

        # Verify callback was invoked
        callback.assert_called_once()
        args = callback.call_args[0]
        assert args[0] == deployment_id
        assert "UNHEALTHY" in args[1]

    def test_detect_crash_degraded_to_unhealthy(self, crash_detector):
        """Test crash detection when status transitions from DEGRADED to UNHEALTHY."""
        deployment_id = "test-deployment"
        callback = Mock()

        # Setup
        crash_detector.register_crash_callback(callback)
        crash_detector.start_monitoring(deployment_id)

        # Simulate health status change: DEGRADED → UNHEALTHY
        crash_detector._on_health_status_change(
            deployment_id, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY
        )

        # Verify crash was detected
        assert crash_detector.get_crash_count(deployment_id) == 1
        callback.assert_called_once()

    def test_no_crash_on_degraded(self, crash_detector):
        """Test that DEGRADED status does not trigger crash detection."""
        deployment_id = "test-deployment"
        callback = Mock()

        # Setup
        crash_detector.register_crash_callback(callback)
        crash_detector.start_monitoring(deployment_id)

        # Simulate health status change: HEALTHY → DEGRADED
        crash_detector._on_health_status_change(
            deployment_id, HealthStatus.HEALTHY, HealthStatus.DEGRADED
        )

        # Verify no crash was detected
        assert crash_detector.get_crash_count(deployment_id) == 0
        callback.assert_not_called()

    def test_multiple_crashes(self, crash_detector):
        """Test detecting multiple crashes."""
        deployment_id = "test-deployment"
        callback = Mock()

        # Setup
        crash_detector.register_crash_callback(callback)
        crash_detector.start_monitoring(deployment_id)

        # Simulate multiple crashes
        for i in range(3):
            crash_detector._on_health_status_change(
                deployment_id, HealthStatus.HEALTHY, HealthStatus.UNHEALTHY
            )

        # Verify crash count
        assert crash_detector.get_crash_count(deployment_id) == 3

        # Verify callback was invoked 3 times
        assert callback.call_count == 3

    def test_unmonitored_deployment_ignored(self, crash_detector):
        """Test that unmonitored deployments are ignored."""
        deployment_id = "unmonitored-deployment"
        callback = Mock()

        # Register callback but don't start monitoring
        crash_detector.register_crash_callback(callback)

        # Simulate health status change
        crash_detector._on_health_status_change(
            deployment_id, HealthStatus.HEALTHY, HealthStatus.UNHEALTHY
        )

        # Verify no crash was detected
        assert crash_detector.get_crash_count(deployment_id) == 0
        callback.assert_not_called()

    def test_multiple_callbacks(self, crash_detector):
        """Test multiple crash callbacks are invoked."""
        deployment_id = "test-deployment"
        callback1 = Mock()
        callback2 = Mock()

        # Register multiple callbacks
        crash_detector.register_crash_callback(callback1)
        crash_detector.register_crash_callback(callback2)
        crash_detector.start_monitoring(deployment_id)

        # Trigger crash
        crash_detector._on_health_status_change(
            deployment_id, HealthStatus.HEALTHY, HealthStatus.UNHEALTHY
        )

        # Verify both callbacks were invoked
        callback1.assert_called_once()
        callback2.assert_called_once()

    def test_callback_exception_handled(self, crash_detector):
        """Test that callback exceptions don't crash the detector."""
        deployment_id = "test-deployment"

        # Create callback that raises exception
        def bad_callback(dep_id, reason):
            raise RuntimeError("Callback error")

        crash_detector.register_crash_callback(bad_callback)
        crash_detector.start_monitoring(deployment_id)

        # Trigger crash (should not raise exception)
        crash_detector._on_health_status_change(
            deployment_id, HealthStatus.HEALTHY, HealthStatus.UNHEALTHY
        )

        # Verify crash was still detected
        assert crash_detector.get_crash_count(deployment_id) == 1

    def test_unknown_to_unhealthy_detected(self, crash_detector):
        """Test crash detection when status transitions from UNKNOWN to UNHEALTHY."""
        deployment_id = "test-deployment"
        callback = Mock()

        # Setup
        crash_detector.register_crash_callback(callback)
        crash_detector.start_monitoring(deployment_id)

        # Simulate health status change: UNKNOWN → UNHEALTHY
        crash_detector._on_health_status_change(
            deployment_id, HealthStatus.UNKNOWN, HealthStatus.UNHEALTHY
        )

        # Verify crash was detected
        assert crash_detector.get_crash_count(deployment_id) == 1
        callback.assert_called_once()

    def test_thread_safety(self, crash_detector):
        """Test that crash detector operations are thread-safe."""
        import threading

        deployment_id = "test-deployment"
        callback = Mock()

        crash_detector.register_crash_callback(callback)
        crash_detector.start_monitoring(deployment_id)

        # Simulate concurrent crash detection from multiple threads
        def trigger_crash():
            crash_detector._on_health_status_change(
                deployment_id, HealthStatus.HEALTHY, HealthStatus.UNHEALTHY
            )

        threads = [threading.Thread(target=trigger_crash) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Verify all crashes were counted
        assert crash_detector.get_crash_count(deployment_id) == 10
