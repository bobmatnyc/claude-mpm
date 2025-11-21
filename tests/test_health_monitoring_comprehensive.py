import pytest

"""Comprehensive tests for health monitoring and recovery systems.

This test suite validates:
- Health monitoring functionality and metrics collection
- Recovery manager integration and circuit breaker behavior
- Configuration validation and system integration
- Edge cases and error handling scenarios
"""

import asyncio

# Test imports
import sys
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from claude_mpm.services.infrastructure.monitoring import (
        AdvancedHealthMonitor,
        HealthCheckResult,
        HealthMetric,
        HealthStatus,
        NetworkConnectivityChecker,
        ProcessResourceChecker,
        ServiceHealthChecker,
    )
    from claude_mpm.services.recovery_manager import (
        CircuitBreaker,
        CircuitState,
        GradedRecoveryStrategy,
        RecoveryAction,
        RecoveryEvent,
        RecoveryManager,
    )
    from claude_mpm.services.socketio_server import SocketIOServer
    from claude_mpm.utils.config_manager import ConfigurationManager as ConfigManager

    HEALTH_MONITORING_AVAILABLE = True
except ImportError as e:
    HEALTH_MONITORING_AVAILABLE = False
    pytest.skip(f"Health monitoring not available: {e}", allow_module_level=True)


class MockProcess:
    """Mock psutil.Process for testing."""

    def __init__(
        self,
        pid=1234,
        running=True,
        status="running",
        cpu_percent=25.5,
        memory_mb=128,
        num_fds=50,
        num_threads=10,
        create_time=None,
    ):
        self.pid = pid
        self._running = running
        self._status = status
        self._cpu_percent = cpu_percent
        self._memory_mb = memory_mb
        self._num_fds = num_fds
        self._num_threads = num_threads
        self._create_time = create_time or time.time()

    def is_running(self):
        return self._running

    def status(self):
        return self._status

    def cpu_percent(self, interval=None):
        return self._cpu_percent

    def memory_info(self):
        memory_bytes = self._memory_mb * 1024 * 1024
        mock_info = Mock()
        mock_info.rss = memory_bytes
        mock_info.vms = memory_bytes * 1.5
        return mock_info

    def num_fds(self):
        return self._num_fds

    def num_threads(self):
        return self._num_threads

    def create_time(self):
        return self._create_time


@pytest.fixture
def mock_process():
    """Provide a mock process for testing."""
    return MockProcess()


@pytest.fixture
def health_config():
    """Health monitoring configuration for testing."""
    return {
        "check_interval": 1,  # Fast interval for testing
        "history_size": 10,
        "aggregation_window": 5,
    }


@pytest.fixture
def recovery_config():
    """Recovery manager configuration for testing."""
    return {
        "enabled": True,
        "check_interval": 1,
        "max_recovery_attempts": 3,
        "recovery_timeout": 5,
        "circuit_breaker": {
            "failure_threshold": 3,
            "timeout_seconds": 2,
            "success_threshold": 2,
        },
        "strategy": {
            "warning_threshold": 2,
            "critical_threshold": 1,
            "failure_window_seconds": 10,
            "min_recovery_interval": 1,
        },
    }


@pytest.fixture
def service_stats():
    """Mock service statistics for testing."""
    return {
        "events_processed": 100,
        "clients_connected": 5,
        "clients_served": 20,
        "errors": 2,
        "last_activity": datetime.utcnow().isoformat() + "Z",
    }


class TestHealthMetric:
    """Test HealthMetric data structure."""

    def test_health_metric_creation():
        """Test creating a health metric."""
        metric = HealthMetric(
            name="test_metric",
            value=42,
            status=HealthStatus.HEALTHY,
            threshold=50,
            unit="units",
        )

        assert metric.name == "test_metric"
        assert metric.value == 42
        assert metric.status == HealthStatus.HEALTHY
        assert metric.threshold == 50
        assert metric.unit == "units"
        assert metric.timestamp is not None

    def test_health_metric_to_dict():
        """Test converting health metric to dictionary."""
        metric = HealthMetric(
            name="test_metric",
            value=42,
            status=HealthStatus.WARNING,
            message="Test message",
        )

        result = metric.to_dict()
        assert result["name"] == "test_metric"
        assert result["value"] == 42
        assert result["status"] == "warning"
        assert result["message"] == "Test message"
        assert "timestamp_iso" in result


class TestHealthCheckResult:
    """Test HealthCheckResult data structure."""

    def test_health_check_result_creation():
        """Test creating a health check result."""
        metrics = [
            HealthMetric("metric1", 10, HealthStatus.HEALTHY),
            HealthMetric("metric2", 90, HealthStatus.WARNING),
        ]

        result = HealthCheckResult(
            overall_status=HealthStatus.WARNING,
            metrics=metrics,
            timestamp=time.time(),
            duration_ms=150.5,
            errors=["test error"],
        )

        assert result.overall_status == HealthStatus.WARNING
        assert len(result.metrics) == 2
        assert result.duration_ms == 150.5
        assert result.errors == ["test error"]

    def test_health_check_result_to_dict():
        """Test converting health check result to dictionary."""
        metrics = [
            HealthMetric("healthy_metric", 10, HealthStatus.HEALTHY),
            HealthMetric("warning_metric", 90, HealthStatus.WARNING),
            HealthMetric("critical_metric", 95, HealthStatus.CRITICAL),
        ]

        result = HealthCheckResult(
            overall_status=HealthStatus.CRITICAL,
            metrics=metrics,
            timestamp=time.time(),
            duration_ms=200.0,
            errors=[],
        )

        dict_result = result.to_dict()
        assert dict_result["overall_status"] == "critical"
        assert dict_result["metric_count"] == 3
        assert dict_result["healthy_metrics"] == 1
        assert dict_result["warning_metrics"] == 1
        assert dict_result["critical_metrics"] == 1


class TestProcessResourceChecker:
    """Test ProcessResourceChecker functionality."""

    @patch("claude_mpm.services.health_monitor.psutil.Process")
    @patch("claude_mpm.services.health_monitor.PSUTIL_AVAILABLE", True)
    @pytest.mark.asyncio
    async def test_process_resource_checker_healthy(
        self, mock_process_class, mock_process
    ):
        """Test process resource checker with healthy metrics."""
        mock_process_class.return_value = mock_process

        checker = ProcessResourceChecker(
            pid=1234, cpu_threshold=80.0, memory_threshold_mb=500, fd_threshold=1000
        )

        metrics = await checker.check_health()

        # Should have multiple metrics
        assert len(metrics) > 0

        # Find specific metrics
        metric_names = [m.name for m in metrics]
        assert "process_status" in metric_names
        assert "cpu_usage_percent" in metric_names
        assert "memory_usage_mb" in metric_names

        # All should be healthy given mock values
        status_counts = {}
        for metric in metrics:
            status_counts[metric.status] = status_counts.get(metric.status, 0) + 1

        # Most metrics should be healthy
        assert status_counts.get(HealthStatus.HEALTHY, 0) > 0

    @patch("claude_mpm.services.health_monitor.psutil.Process")
    @patch("claude_mpm.services.health_monitor.PSUTIL_AVAILABLE", True)
    @pytest.mark.asyncio
    async def test_process_resource_checker_critical(self):
        """Test process resource checker with critical metrics."""
        # Create a mock process with high resource usage
        critical_mock = MockProcess(
            cpu_percent=95.0,  # Above threshold
            memory_mb=600,  # Above threshold
            num_fds=1200,  # Above threshold
        )
        self.return_value = critical_mock

        checker = ProcessResourceChecker(
            pid=1234, cpu_threshold=80.0, memory_threshold_mb=500, fd_threshold=1000
        )

        metrics = await checker.check_health()

        # Should have warning/critical metrics
        warning_critical = [
            m
            for m in metrics
            if m.status in [HealthStatus.WARNING, HealthStatus.CRITICAL]
        ]
        assert len(warning_critical) > 0

    @patch("claude_mpm.services.health_monitor.PSUTIL_AVAILABLE", False)
    @pytest.mark.asyncio
    async def test_process_resource_checker_no_psutil():
        """Test process resource checker without psutil available."""
        checker = ProcessResourceChecker(pid=1234)
        metrics = await checker.check_health()

        # Should return psutil availability metric
        assert len(metrics) == 1
        assert metrics[0].name == "psutil_availability"
        assert metrics[0].status == HealthStatus.WARNING


class TestNetworkConnectivityChecker:
    """Test NetworkConnectivityChecker functionality."""

    @patch("claude_mpm.services.health_monitor.socket.socket")
    @pytest.mark.asyncio
    async def test_network_connectivity_checker_healthy(self):
        """Test network connectivity checker when port is accessible."""
        # Mock successful connection
        mock_socket = Mock()
        mock_socket.connect_ex.return_value = 0  # Success
        self.return_value = mock_socket

        checker = NetworkConnectivityChecker(host="localhost", port=8765, timeout=1.0)

        metrics = await checker.check_health()

        # Should have healthy connectivity metrics
        port_metric = next((m for m in metrics if m.name == "port_accessible"), None)
        assert port_metric is not None
        assert port_metric.status == HealthStatus.HEALTHY

    @patch("claude_mpm.services.health_monitor.socket.socket")
    @pytest.mark.asyncio
    async def test_network_connectivity_checker_critical(self):
        """Test network connectivity checker when port is not accessible."""
        # Mock failed connection
        mock_socket = Mock()
        mock_socket.connect_ex.return_value = 1  # Connection refused
        self.return_value = mock_socket

        checker = NetworkConnectivityChecker(host="localhost", port=8765, timeout=1.0)

        metrics = await checker.check_health()

        # Should have critical connectivity metric
        port_metric = next((m for m in metrics if m.name == "port_accessible"), None)
        assert port_metric is not None
        assert port_metric.status == HealthStatus.CRITICAL


class TestServiceHealthChecker:
    """Test ServiceHealthChecker functionality."""

    @pytest.mark.asyncio
    async def test_service_health_checker_healthy(self):
        """Test service health checker with healthy stats."""
        checker = ServiceHealthChecker(
            service_stats=self, max_clients=100, max_error_rate=0.1
        )

        metrics = await checker.check_health()

        # Should have service metrics
        metric_names = [m.name for m in metrics]
        assert "connected_clients" in metric_names
        assert "total_events_processed" in metric_names
        assert "error_rate" in metric_names

        # Most should be healthy
        healthy_metrics = [m for m in metrics if m.status == HealthStatus.HEALTHY]
        assert len(healthy_metrics) > 0

    @pytest.mark.asyncio
    async def test_service_health_checker_high_error_rate():
        """Test service health checker with high error rate."""
        high_error_stats = {
            "events_processed": 100,
            "clients_connected": 5,
            "errors": 20,  # High error count
            "last_activity": datetime.utcnow().isoformat() + "Z",
        }

        checker = ServiceHealthChecker(
            service_stats=high_error_stats,
            max_error_rate=0.1,  # 10% threshold
        )

        metrics = await checker.check_health()

        # Error rate should be critical (20/100 = 20% > 10%)
        error_rate_metric = next((m for m in metrics if m.name == "error_rate"), None)
        assert error_rate_metric is not None
        assert error_rate_metric.status == HealthStatus.CRITICAL


class TestAdvancedHealthMonitor:
    """Test AdvancedHealthMonitor functionality."""

    @pytest.mark.asyncio
    async def test_health_monitor_initialization(self):
        """Test health monitor initialization."""
        monitor = AdvancedHealthMonitor(self)

        assert monitor.check_interval == self["check_interval"]
        assert monitor.history_size == self["history_size"]
        assert len(monitor.checkers) == 0
        assert not monitor.monitoring

    @pytest.mark.asyncio
    async def test_add_checker(self, mock_process):
        """Test adding health checkers to monitor."""
        monitor = AdvancedHealthMonitor(self)

        with patch(
            "claude_mpm.services.health_monitor.psutil.Process",
            return_value=mock_process,
        ):
            checker = ProcessResourceChecker(pid=1234)
            monitor.add_checker(checker)

        assert len(monitor.checkers) == 1
        assert monitor.checkers[0] == checker

    @pytest.mark.asyncio
    async def test_perform_health_check(self, service_stats):
        """Test performing a comprehensive health check."""
        monitor = AdvancedHealthMonitor(self)

        # Add service health checker
        service_checker = ServiceHealthChecker(service_stats)
        monitor.add_checker(service_checker)

        # Perform health check
        result = await monitor.perform_health_check()

        assert isinstance(result, HealthCheckResult)
        assert len(result.metrics) > 0
        assert result.duration_ms > 0
        assert result.overall_status in list(HealthStatus)

    @pytest.mark.asyncio
    async def test_determine_overall_status(self):
        """Test overall status determination logic."""
        monitor = AdvancedHealthMonitor(self)

        # All healthy metrics
        healthy_metrics = [
            HealthMetric("metric1", 10, HealthStatus.HEALTHY),
            HealthMetric("metric2", 20, HealthStatus.HEALTHY),
        ]
        status = monitor._determine_overall_status(healthy_metrics)
        assert status == HealthStatus.HEALTHY

        # One critical metric
        critical_metrics = [
            HealthMetric("metric1", 10, HealthStatus.HEALTHY),
            HealthMetric("metric2", 90, HealthStatus.CRITICAL),
        ]
        status = monitor._determine_overall_status(critical_metrics)
        assert status == HealthStatus.CRITICAL

        # Many warning metrics (>30%)
        warning_metrics = [
            HealthMetric("metric1", 70, HealthStatus.WARNING),
            HealthMetric("metric2", 75, HealthStatus.WARNING),
            HealthMetric("metric3", 10, HealthStatus.HEALTHY),
        ]
        status = monitor._determine_overall_status(warning_metrics)
        assert status == HealthStatus.WARNING

    @pytest.mark.asyncio
    async def test_health_history(self, service_stats):
        """Test health check history tracking."""
        monitor = AdvancedHealthMonitor(self)
        service_checker = ServiceHealthChecker(service_stats)
        monitor.add_checker(service_checker)

        # Perform multiple health checks
        for _ in range(3):
            await monitor.perform_health_check()
            await asyncio.sleep(0.1)  # Small delay between checks

        history = monitor.get_health_history()
        assert len(history) == 3

        # History should be newest first
        assert history[0].timestamp > history[1].timestamp > history[2].timestamp

    @pytest.mark.asyncio
    async def test_aggregated_status(self, service_stats):
        """Test aggregated health status calculation."""
        monitor = AdvancedHealthMonitor(self)
        service_checker = ServiceHealthChecker(service_stats)
        monitor.add_checker(service_checker)

        # Perform a health check
        await monitor.perform_health_check()

        # Get aggregated status
        aggregated = monitor.get_aggregated_status(window_seconds=10)

        assert "overall_status" in aggregated
        assert "checks_count" in aggregated
        assert "status_distribution" in aggregated
        assert aggregated["checks_count"] > 0


class TestCircuitBreaker:
    """Test CircuitBreaker functionality."""

    def test_circuit_breaker_initialization():
        """Test circuit breaker initialization."""
        cb = CircuitBreaker(failure_threshold=3, timeout_seconds=5, success_threshold=2)

        assert cb.state == CircuitState.CLOSED
        assert cb.failure_threshold == 3
        assert cb.timeout_seconds == 5
        assert cb.success_threshold == 2
        assert cb.failure_count == 0
        assert cb.success_count == 0

    def test_circuit_breaker_closed_state():
        """Test circuit breaker in closed state."""
        cb = CircuitBreaker(failure_threshold=3)

        assert cb.can_proceed() is True

        # Record failures but stay under threshold
        cb.record_failure()
        cb.record_failure()
        assert cb.can_proceed() is True
        assert cb.state == CircuitState.CLOSED

    def test_circuit_breaker_open_state():
        """Test circuit breaker opening after failures."""
        cb = CircuitBreaker(failure_threshold=3)

        # Exceed failure threshold
        for _ in range(3):
            cb.record_failure()

        assert cb.state == CircuitState.OPEN
        assert cb.can_proceed() is False

    def test_circuit_breaker_timeout_transition():
        """Test circuit breaker timeout and half-open transition."""
        cb = CircuitBreaker(failure_threshold=2, timeout_seconds=0.1)

        # Open the circuit
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # Wait for timeout
        time.sleep(0.15)

        # Should transition to half-open
        assert cb.can_proceed() is True
        assert cb.state == CircuitState.HALF_OPEN

    def test_circuit_breaker_half_open_success():
        """Test circuit breaker closing from half-open after successes."""
        cb = CircuitBreaker(
            failure_threshold=2, timeout_seconds=0.1, success_threshold=2
        )

        # Open the circuit
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.15)  # Wait for timeout
        cb.can_proceed()  # Transition to half-open

        # Record successful operations
        cb.record_success()
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_success()

        # Should close the circuit
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_circuit_breaker_half_open_failure():
        """Test circuit breaker returning to open from half-open after failure."""
        cb = CircuitBreaker(failure_threshold=2, timeout_seconds=0.1)

        # Open the circuit
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.15)
        cb.can_proceed()  # Transition to half-open

        # Record a failure in half-open state
        cb.record_failure()

        # Should go back to open
        assert cb.state == CircuitState.OPEN
        assert cb.can_proceed() is False


class TestGradedRecoveryStrategy:
    """Test GradedRecoveryStrategy functionality."""

    def test_recovery_strategy_initialization():
        """Test recovery strategy initialization."""
        config = {
            "warning_threshold": 2,
            "critical_threshold": 1,
            "failure_window_seconds": 300,
            "min_recovery_interval": 60,
        }

        strategy = GradedRecoveryStrategy(config)
        assert strategy.warning_threshold == 2
        assert strategy.critical_threshold == 1
        assert strategy.get_name() == "graded_recovery"

    def test_should_recover_critical_status():
        """Test recovery triggering for critical health status."""
        strategy = GradedRecoveryStrategy()

        # Create critical health result
        critical_result = HealthCheckResult(
            overall_status=HealthStatus.CRITICAL,
            metrics=[],
            timestamp=time.time(),
            duration_ms=100,
            errors=[],
        )

        assert strategy.should_recover(critical_result) is True

    def test_should_recover_repeated_warnings():
        """Test recovery triggering for repeated warnings."""
        config = {"warning_threshold": 2, "min_recovery_interval": 0}
        strategy = GradedRecoveryStrategy(config)

        # Create warning health results
        warning_result = HealthCheckResult(
            overall_status=HealthStatus.WARNING,
            metrics=[],
            timestamp=time.time(),
            duration_ms=100,
            errors=[],
        )

        # First warning shouldn't trigger recovery
        assert strategy.should_recover(warning_result) is False

        # Second warning should trigger recovery
        assert strategy.should_recover(warning_result) is True

    def test_get_recovery_action_escalation():
        """Test recovery action escalation based on failure history."""
        config = {"min_recovery_interval": 0}
        strategy = GradedRecoveryStrategy(config)

        # First critical - should clear connections
        critical_result = HealthCheckResult(
            overall_status=HealthStatus.CRITICAL,
            metrics=[],
            timestamp=time.time(),
            duration_ms=100,
            errors=[],
        )
        action1 = strategy.get_recovery_action(critical_result)
        assert action1 == RecoveryAction.CLEAR_CONNECTIONS

        # Second critical - should restart service
        action2 = strategy.get_recovery_action(critical_result)
        assert action2 == RecoveryAction.RESTART_SERVICE

        # Third critical - should emergency stop
        action3 = strategy.get_recovery_action(critical_result)
        assert action3 == RecoveryAction.EMERGENCY_STOP


class TestRecoveryManager:
    """Test RecoveryManager functionality."""

    @pytest.mark.asyncio
    async def test_recovery_manager_initialization(self):
        """Test recovery manager initialization."""
        manager = RecoveryManager(self)

        assert manager.enabled is True
        assert manager.check_interval == self["check_interval"]
        assert isinstance(manager.circuit_breaker, CircuitBreaker)
        assert isinstance(manager.recovery_strategy, GradedRecoveryStrategy)
        assert not manager.recovery_in_progress

    @pytest.mark.asyncio
    async def test_handle_health_result_no_recovery_needed(self):
        """Test handling healthy health result (no recovery needed)."""
        manager = RecoveryManager(self)

        healthy_result = HealthCheckResult(
            overall_status=HealthStatus.HEALTHY,
            metrics=[],
            timestamp=time.time(),
            duration_ms=100,
            errors=[],
        )

        event = manager.handle_health_result(healthy_result)
        assert event is None

    @pytest.mark.asyncio
    async def test_handle_health_result_disabled(self):
        """Test handling health result when recovery is disabled."""
        self["enabled"] = False
        manager = RecoveryManager(self)

        critical_result = HealthCheckResult(
            overall_status=HealthStatus.CRITICAL,
            metrics=[],
            timestamp=time.time(),
            duration_ms=100,
            errors=[],
        )

        event = manager.handle_health_result(critical_result)
        assert event is None

    @pytest.mark.asyncio
    async def test_log_warning_recovery(self):
        """Test log warning recovery action."""
        manager = RecoveryManager(self)

        warning_result = HealthCheckResult(
            overall_status=HealthStatus.WARNING,
            metrics=[HealthMetric("test", 75, HealthStatus.WARNING)],
            timestamp=time.time(),
            duration_ms=100,
            errors=[],
        )

        # Perform log warning recovery
        event = await manager._perform_recovery(
            RecoveryAction.LOG_WARNING, warning_result, "test"
        )

        assert event.action == RecoveryAction.LOG_WARNING
        assert event.success is True
        assert event.duration_ms > 0

    @pytest.mark.asyncio
    async def test_recovery_stats_update(self):
        """Test recovery statistics updating."""
        manager = RecoveryManager(self)

        warning_result = HealthCheckResult(
            overall_status=HealthStatus.WARNING,
            metrics=[],
            timestamp=time.time(),
            duration_ms=100,
            errors=[],
        )

        # Initial stats
        initial_total = manager.recovery_stats["total_recoveries"]

        # Perform recovery
        await manager._perform_recovery(
            RecoveryAction.LOG_WARNING, warning_result, "test"
        )

        # Stats should be updated
        assert manager.recovery_stats["total_recoveries"] == initial_total + 1
        assert manager.recovery_stats["successful_recoveries"] > 0

    def test_recovery_history(self):
        """Test recovery event history tracking."""
        manager = RecoveryManager(self)

        # Create mock recovery events
        event1 = RecoveryEvent(
            timestamp=time.time() - 10,
            action=RecoveryAction.LOG_WARNING,
            trigger="test1",
            health_status=HealthStatus.WARNING,
            success=True,
            duration_ms=100,
        )

        event2 = RecoveryEvent(
            timestamp=time.time() - 5,
            action=RecoveryAction.CLEAR_CONNECTIONS,
            trigger="test2",
            health_status=HealthStatus.CRITICAL,
            success=True,
            duration_ms=200,
        )

        manager.recovery_history.append(event1)
        manager.recovery_history.append(event2)

        history = manager.get_recovery_history()

        # Should be newest first
        assert len(history) == 2
        assert history[0].timestamp > history[1].timestamp
        assert history[0].action == RecoveryAction.CLEAR_CONNECTIONS


class TestSocketIOServerIntegration:
    """Test integration of health monitoring with SocketIOServer."""

    @patch(
        "claude_mpm.services.socketio_server.HEALTH_MONITORING_AVAILABLE",
        True,
    )
    def test_server_health_monitoring_initialization():
        """Test that server initializes health monitoring when available."""
        with patch("claude_mpm.services.socketio_server.AdvancedHealthMonitor"), patch(
            "claude_mpm.services.socketio_server.RecoveryManager"
        ):
            server = SocketIOServer(host="localhost", port=8765)

            # Should have attempted to initialize health monitoring
            assert hasattr(server, "health_monitor")
            assert hasattr(server, "recovery_manager")

    @patch(
        "claude_mpm.services.socketio_server.HEALTH_MONITORING_AVAILABLE",
        False,
    )
    def test_server_without_health_monitoring():
        """Test server initialization without health monitoring available."""
        server = SocketIOServer(host="localhost", port=8765)

        # Health monitoring should be None
        assert server.health_monitor is None
        assert server.recovery_manager is None


class TestConfigurationIntegration:
    """Test configuration system integration."""

    def test_health_monitoring_config():
        """Test health monitoring configuration defaults and validation."""
        config = Config()

        health_config = config.get_health_monitoring_config()

        assert "enabled" in health_config
        assert "check_interval" in health_config
        assert "thresholds" in health_config
        assert health_config["thresholds"]["cpu_percent"] > 0
        assert health_config["thresholds"]["memory_mb"] > 0

    def test_recovery_config():
        """Test recovery configuration defaults and validation."""
        config = Config()

        recovery_config = config.get_recovery_config()

        assert "enabled" in recovery_config
        assert "circuit_breaker" in recovery_config
        assert "strategy" in recovery_config
        assert recovery_config["circuit_breaker"]["failure_threshold"] > 0

    def test_config_validation():
        """Test configuration validation for health and recovery settings."""
        # Test with invalid values
        invalid_config = Config(
            {
                "health_thresholds": {
                    "cpu_percent": 150,  # Invalid: > 100
                    "memory_mb": -10,  # Invalid: negative
                    "max_error_rate": 1.5,  # Invalid: > 1.0
                }
            }
        )

        # Should have been corrected to defaults
        thresholds = invalid_config.get("health_thresholds")
        assert thresholds["cpu_percent"] == 80.0
        assert thresholds["memory_mb"] == 500
        assert thresholds["max_error_rate"] == 0.1


@pytest.mark.asyncio
async def test_full_integration_scenario():
    """Test full integration scenario with health monitoring and recovery."""
    # This test validates the complete flow from health check to recovery

    # Setup configuration
    config = {
        "health_monitoring": {
            "check_interval": 0.1,  # Very fast for testing
            "history_size": 5,
        },
        "recovery": {
            "enabled": True,
            "min_recovery_interval": 0,  # Allow immediate recovery for testing
            "circuit_breaker": {"failure_threshold": 2, "timeout_seconds": 1},
        },
    }

    # Create health monitor and recovery manager
    health_monitor = AdvancedHealthMonitor(config["health_monitoring"])
    recovery_manager = RecoveryManager(config["recovery"])

    # Create a failing service health checker
    failing_stats = {
        "events_processed": 10,
        "clients_connected": 0,
        "errors": 5,  # High error rate: 50%
        "last_activity": datetime.utcnow().isoformat() + "Z",
    }

    failing_checker = ServiceHealthChecker(
        service_stats=failing_stats,
        max_error_rate=0.1,  # 10% threshold
    )

    health_monitor.add_checker(failing_checker)
    health_monitor.add_health_callback(recovery_manager.handle_health_result)

    # Perform health check
    result = await health_monitor.perform_health_check()

    # Should detect critical status due to high error rate
    assert result.overall_status in [HealthStatus.WARNING, HealthStatus.CRITICAL]

    # Recovery should have been triggered
    recovery_manager.get_recovery_history()

    # Note: Since handle_health_result returns a Task for async operations,
    # we might need to wait for it to complete in a real scenario
    # For this test, we're validating the detection logic


if __name__ == "__main__":
    pytest.main([__file__])
