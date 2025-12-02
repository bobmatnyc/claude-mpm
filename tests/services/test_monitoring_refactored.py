"""Comprehensive unit tests for monitoring module refactoring.

Tests all major functionality including:
- ProcessResourceChecker
- NetworkConnectivityChecker
- ServiceHealthChecker
- AdvancedHealthMonitor
- Health metric calculations
- Status aggregation
- Error handling
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from claude_mpm.services.infrastructure.monitoring import (
    AdvancedHealthMonitor, HealthChecker, HealthCheckResult, HealthMetric,
    HealthStatus, NetworkConnectivityChecker, ProcessResourceChecker,
    ServiceHealthChecker)


class TestHealthMetric:
    """Test HealthMetric data structure."""

    def test_health_metric_creation(self):
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

    def test_health_metric_to_dict(self):
        """Test converting metric to dictionary."""
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

    def test_health_check_result_creation(self):
        """Test creating a health check result."""
        metrics = [
            HealthMetric("metric1", 10, HealthStatus.HEALTHY),
            HealthMetric("metric2", 20, HealthStatus.WARNING),
        ]

        result = HealthCheckResult(
            overall_status=HealthStatus.WARNING,
            metrics=metrics,
            timestamp=time.time(),
            duration_ms=5.5,
            errors=["error1"],
        )

        assert result.overall_status == HealthStatus.WARNING
        assert len(result.metrics) == 2
        assert result.duration_ms == 5.5
        assert result.errors == ["error1"]

    def test_health_check_result_to_dict(self):
        """Test converting result to dictionary."""
        metrics = [
            HealthMetric("metric1", 10, HealthStatus.HEALTHY),
            HealthMetric("metric2", 20, HealthStatus.WARNING),
            HealthMetric("metric3", 30, HealthStatus.CRITICAL),
        ]

        result = HealthCheckResult(
            overall_status=HealthStatus.CRITICAL,
            metrics=metrics,
            timestamp=time.time(),
            duration_ms=10.0,
            errors=[],
        )

        data = result.to_dict()

        assert data["overall_status"] == "critical"
        assert data["metric_count"] == 3
        assert data["healthy_metrics"] == 1
        assert data["warning_metrics"] == 1
        assert data["critical_metrics"] == 1
        assert data["duration_ms"] == 10.0


class TestProcessResourceChecker:
    """Test ProcessResourceChecker health monitoring."""

    @patch(
        "claude_mpm.services.infrastructure.monitoring.process.PSUTIL_AVAILABLE", False
    )
    async def test_no_psutil_available(self):
        """Test behavior when psutil is not available."""
        checker = ProcessResourceChecker(pid=12345)
        metrics = await checker.check_health()

        assert len(metrics) == 1
        assert metrics[0].name == "psutil_availability"
        assert metrics[0].value is False
        assert metrics[0].status == HealthStatus.WARNING

    @patch(
        "claude_mpm.services.infrastructure.monitoring.process.PSUTIL_AVAILABLE", True
    )
    @patch("claude_mpm.services.infrastructure.monitoring.process.psutil")
    async def test_process_not_found(self, mock_psutil):
        """Test when process doesn't exist."""
        mock_psutil.NoSuchProcess = Exception
        mock_psutil.Process.side_effect = mock_psutil.NoSuchProcess()

        checker = ProcessResourceChecker(pid=12345)
        metrics = await checker.check_health()

        assert len(metrics) == 1
        assert metrics[0].name == "process_exists"
        assert metrics[0].value is False
        assert metrics[0].status == HealthStatus.CRITICAL

    @patch("claude_mpm.services.infrastructure.monitoring.PSUTIL_AVAILABLE", True)
    @patch("claude_mpm.services.infrastructure.monitoring.psutil")
    async def test_healthy_process_metrics(self, mock_psutil):
        """Test healthy process resource metrics."""
        # Setup mock process
        mock_process = MagicMock()
        mock_process.is_running.return_value = True
        mock_process.status.return_value = "running"
        mock_process.cpu_percent.return_value = 25.5
        mock_process.memory_info.return_value = MagicMock(
            rss=100 * 1024 * 1024,  # 100 MB
            vms=200 * 1024 * 1024,  # 200 MB
        )
        mock_process.num_fds.return_value = 50
        mock_process.num_threads.return_value = 10
        mock_process.create_time.return_value = time.time() - 3600

        mock_psutil.Process.return_value = mock_process
        mock_psutil.STATUS_ZOMBIE = "zombie"
        mock_psutil.STATUS_DEAD = "dead"
        mock_psutil.STATUS_STOPPED = "stopped"

        checker = ProcessResourceChecker(
            pid=12345,
            cpu_threshold=80.0,
            memory_threshold_mb=500,
            fd_threshold=1000,
        )

        metrics = await checker.check_health()

        # Verify metrics
        metric_dict = {m.name: m for m in metrics}

        assert metric_dict["process_status"].value == "running"
        assert metric_dict["process_status"].status == HealthStatus.HEALTHY

        assert metric_dict["cpu_usage_percent"].value == 25.5
        assert metric_dict["cpu_usage_percent"].status == HealthStatus.HEALTHY

        assert metric_dict["memory_usage_mb"].value == 100.0
        assert metric_dict["memory_usage_mb"].status == HealthStatus.HEALTHY

        assert metric_dict["file_descriptors"].value == 50
        assert metric_dict["file_descriptors"].status == HealthStatus.HEALTHY

    @patch("claude_mpm.services.infrastructure.monitoring.PSUTIL_AVAILABLE", True)
    @patch("claude_mpm.services.infrastructure.monitoring.psutil")
    async def test_warning_thresholds(self, mock_psutil):
        """Test warning status when thresholds exceeded."""
        mock_process = MagicMock()
        mock_process.is_running.return_value = True
        mock_process.status.return_value = "running"
        mock_process.cpu_percent.return_value = 85.0  # Above 80% threshold
        mock_process.memory_info.return_value = MagicMock(
            rss=550 * 1024 * 1024,  # 550 MB, above 500 MB threshold
            vms=600 * 1024 * 1024,
        )

        mock_psutil.Process.return_value = mock_process
        mock_psutil.STATUS_ZOMBIE = "zombie"
        mock_psutil.STATUS_DEAD = "dead"
        mock_psutil.STATUS_STOPPED = "stopped"

        checker = ProcessResourceChecker(
            pid=12345,
            cpu_threshold=80.0,
            memory_threshold_mb=500,
        )

        metrics = await checker.check_health()
        metric_dict = {m.name: m for m in metrics}

        assert metric_dict["cpu_usage_percent"].status == HealthStatus.WARNING
        assert metric_dict["memory_usage_mb"].status == HealthStatus.WARNING

    @patch("claude_mpm.services.infrastructure.monitoring.PSUTIL_AVAILABLE", True)
    @patch("claude_mpm.services.infrastructure.monitoring.psutil")
    async def test_critical_thresholds(self, mock_psutil):
        """Test critical status when thresholds greatly exceeded."""
        mock_process = MagicMock()
        mock_process.is_running.return_value = True
        mock_process.status.return_value = "running"
        mock_process.cpu_percent.return_value = 100.0  # > 80% * 1.2
        mock_process.memory_info.return_value = MagicMock(
            rss=650 * 1024 * 1024,  # 650 MB, > 500 * 1.2
            vms=700 * 1024 * 1024,
        )

        mock_psutil.Process.return_value = mock_process
        mock_psutil.STATUS_ZOMBIE = "zombie"
        mock_psutil.STATUS_DEAD = "dead"
        mock_psutil.STATUS_STOPPED = "stopped"

        checker = ProcessResourceChecker(
            pid=12345,
            cpu_threshold=80.0,
            memory_threshold_mb=500,
        )

        metrics = await checker.check_health()
        metric_dict = {m.name: m for m in metrics}

        assert metric_dict["cpu_usage_percent"].status == HealthStatus.CRITICAL
        assert metric_dict["memory_usage_mb"].status == HealthStatus.CRITICAL


class TestNetworkConnectivityChecker:
    """Test NetworkConnectivityChecker health monitoring."""

    async def test_port_accessible(self):
        """Test when port is accessible."""
        with patch("socket.socket") as mock_socket_class:
            mock_socket = MagicMock()
            mock_socket.connect_ex.return_value = 0  # Success
            mock_socket_class.return_value = mock_socket

            checker = NetworkConnectivityChecker("localhost", 8080)
            metrics = await checker.check_health()

            metric_dict = {m.name: m for m in metrics}

            assert metric_dict["port_accessible"].value is True
            assert metric_dict["port_accessible"].status == HealthStatus.HEALTHY
            assert metric_dict["socket_creation"].value is True
            assert metric_dict["socket_creation"].status == HealthStatus.HEALTHY

    async def test_port_not_accessible(self):
        """Test when port is not accessible."""
        with patch("socket.socket") as mock_socket_class:
            mock_socket = MagicMock()
            mock_socket.connect_ex.return_value = 1  # Connection refused
            mock_socket_class.return_value = mock_socket

            checker = NetworkConnectivityChecker("localhost", 8080)
            metrics = await checker.check_health()

            metric_dict = {m.name: m for m in metrics}

            assert metric_dict["port_accessible"].value is False
            assert metric_dict["port_accessible"].status == HealthStatus.CRITICAL

    async def test_socket_creation_failure(self):
        """Test when socket creation fails."""
        with patch("socket.socket") as mock_socket_class:
            # First call succeeds for port check
            mock_socket1 = MagicMock()
            mock_socket1.connect_ex.return_value = 0

            # Second call fails for socket creation test
            mock_socket_class.side_effect = [
                mock_socket1,
                OSError("No file descriptors"),
            ]

            checker = NetworkConnectivityChecker("localhost", 8080)
            metrics = await checker.check_health()

            metric_dict = {m.name: m for m in metrics}

            assert metric_dict["socket_creation"].value is False
            assert metric_dict["socket_creation"].status == HealthStatus.CRITICAL


class TestServiceHealthChecker:
    """Test ServiceHealthChecker health monitoring."""

    async def test_healthy_service_metrics(self):
        """Test healthy service metrics."""
        service_stats = {
            "clients_connected": 10,
            "events_processed": 1000,
            "errors": 5,
            "last_activity": time.time() - 30,  # 30 seconds ago
        }

        checker = ServiceHealthChecker(
            service_stats=service_stats,
            max_clients=100,
            max_error_rate=0.1,
        )

        # Set initial state for rate calculation
        checker.service.last_check_time = time.time() - 10
        checker.service.last_events_processed = 900

        metrics = await checker.check_health()
        metric_dict = {m.name: m for m in metrics}

        assert metric_dict["connected_clients"].value == 10
        assert metric_dict["connected_clients"].status == HealthStatus.HEALTHY

        assert metric_dict["total_events_processed"].value == 1000
        if "event_processing_rate" in metric_dict:
            assert metric_dict["event_processing_rate"].value == pytest.approx(
                10.0, rel=0.5
            )  # ~10 events/sec

        assert metric_dict["error_rate"].value == 0.005  # 5/1000
        assert metric_dict["error_rate"].status == HealthStatus.HEALTHY

    async def test_warning_client_count(self):
        """Test warning status for high client count."""
        service_stats = {
            "clients_connected": 85,  # > 80% of 100
            "events_processed": 1000,
            "errors": 0,
        }

        checker = ServiceHealthChecker(
            service_stats=service_stats,
            max_clients=100,
        )

        metrics = await checker.check_health()
        metric_dict = {m.name: m for m in metrics}

        assert metric_dict["connected_clients"].status == HealthStatus.WARNING

    async def test_critical_client_count(self):
        """Test critical status for exceeded client count."""
        service_stats = {
            "clients_connected": 105,  # > 100 max
            "events_processed": 1000,
            "errors": 0,
        }

        checker = ServiceHealthChecker(
            service_stats=service_stats,
            max_clients=100,
        )

        metrics = await checker.check_health()
        metric_dict = {m.name: m for m in metrics}

        assert metric_dict["connected_clients"].status == HealthStatus.CRITICAL

    async def test_error_rate_thresholds(self):
        """Test error rate threshold detection."""
        # High error rate
        service_stats = {
            "clients_connected": 10,
            "events_processed": 1000,
            "errors": 150,  # 15% error rate
        }

        checker = ServiceHealthChecker(
            service_stats=service_stats,
            max_error_rate=0.1,  # 10% threshold
        )

        metrics = await checker.check_health()
        metric_dict = {m.name: m for m in metrics}

        assert metric_dict["error_rate"].value == 0.15
        assert metric_dict["error_rate"].status == HealthStatus.CRITICAL

    async def test_activity_staleness(self):
        """Test detection of stale activity."""
        service_stats = {
            "clients_connected": 10,
            "events_processed": 1000,
            "errors": 0,
            "last_activity": time.time() - 400,  # > 5 minutes ago
        }

        checker = ServiceHealthChecker(service_stats=service_stats)
        metrics = await checker.check_health()
        metric_dict = {m.name: m for m in metrics}

        assert metric_dict["time_since_last_activity"].status == HealthStatus.WARNING


class TestAdvancedHealthMonitor:
    """Test AdvancedHealthMonitor orchestration."""

    def test_initialization(self):
        """Test monitor initialization."""
        config = {
            "check_interval": 60,
            "history_size": 50,
            "aggregation_window": 600,
        }

        monitor = AdvancedHealthMonitor(config)

        assert monitor.check_interval == 60
        assert monitor.history_size == 50
        assert monitor.aggregation_window == 600
        assert len(monitor.checkers) == 0
        assert not monitor.monitoring

    def test_add_checker(self):
        """Test adding health checkers."""
        monitor = AdvancedHealthMonitor()

        checker1 = Mock(spec=HealthChecker)
        checker1.get_name.return_value = "checker1"

        checker2 = Mock(spec=HealthChecker)
        checker2.get_name.return_value = "checker2"

        monitor.add_checker(checker1)
        monitor.add_checker(checker2)

        assert len(monitor.checkers) == 2
        assert monitor.checkers[0] == checker1
        assert monitor.checkers[1] == checker2

    async def test_perform_health_check(self):
        """Test performing comprehensive health check."""
        monitor = AdvancedHealthMonitor()

        # Create mock checkers
        checker1 = AsyncMock(spec=HealthChecker)
        checker1.get_name.return_value = "checker1"
        checker1.check_health.return_value = [
            HealthMetric("metric1", 10, HealthStatus.HEALTHY),
            HealthMetric("metric2", 20, HealthStatus.WARNING),
        ]

        checker2 = AsyncMock(spec=HealthChecker)
        checker2.get_name.return_value = "checker2"
        checker2.check_health.return_value = [
            HealthMetric("metric3", 30, HealthStatus.CRITICAL),
        ]

        monitor.add_checker(checker1)
        monitor.add_checker(checker2)

        result = await monitor.perform_health_check()

        assert result.overall_status == HealthStatus.CRITICAL  # Due to critical metric
        assert len(result.metrics) == 3
        assert len(result.errors) == 0
        assert monitor.monitoring_stats["checks_performed"] == 1

    async def test_health_check_with_errors(self):
        """Test health check with checker failures."""
        monitor = AdvancedHealthMonitor()

        # Checker that raises exception
        checker = AsyncMock(spec=HealthChecker)
        checker.get_name.return_value = "failing_checker"
        checker.check_health.side_effect = Exception("Checker failed")

        monitor.add_checker(checker)

        result = await monitor.perform_health_check()

        assert len(result.errors) == 1
        assert "failing_checker failed" in result.errors[0]
        assert monitor.monitoring_stats["checks_failed"] == 1

    def test_determine_overall_status(self):
        """Test overall status determination logic."""
        monitor = AdvancedHealthMonitor()

        # All healthy
        metrics = [
            HealthMetric("m1", 1, HealthStatus.HEALTHY),
            HealthMetric("m2", 2, HealthStatus.HEALTHY),
        ]
        assert monitor._determine_overall_status(metrics) == HealthStatus.HEALTHY

        # One critical -> overall critical
        metrics.append(HealthMetric("m3", 3, HealthStatus.CRITICAL))
        assert monitor._determine_overall_status(metrics) == HealthStatus.CRITICAL

        # Many warnings -> overall warning
        metrics = [HealthMetric(f"m{i}", i, HealthStatus.WARNING) for i in range(4)]
        metrics.append(HealthMetric("m5", 5, HealthStatus.HEALTHY))
        assert monitor._determine_overall_status(metrics) == HealthStatus.WARNING

    async def test_monitoring_loop(self):
        """Test continuous monitoring loop."""
        monitor = AdvancedHealthMonitor({"check_interval": 0.1})

        # Mock checker
        checker = AsyncMock(spec=HealthChecker)
        checker.get_name.return_value = "test_checker"
        checker.check_health.return_value = [
            HealthMetric("metric1", 10, HealthStatus.HEALTHY),
        ]

        monitor.add_checker(checker)

        # Start monitoring
        monitor.start_monitoring()
        assert monitor.monitoring

        # Let it run for a bit
        await asyncio.sleep(0.25)

        # Stop monitoring
        await monitor.stop_monitoring()
        assert not monitor.monitoring

        # Verify checks were performed
        assert monitor.monitoring_stats["checks_performed"] >= 2

    def test_health_callbacks(self):
        """Test health check callbacks."""
        monitor = AdvancedHealthMonitor()

        callback_results = []

        def callback(result: HealthCheckResult):
            callback_results.append(result)

        monitor.add_health_callback(callback)

        # Perform check (sync test with async method)
        asyncio.run(monitor.perform_health_check())

        assert len(callback_results) == 1
        assert isinstance(callback_results[0], HealthCheckResult)

    def test_get_aggregated_status(self):
        """Test aggregated status calculation."""
        monitor = AdvancedHealthMonitor({"aggregation_window": 300})

        # Add mock history
        current_time = time.time()

        # Add healthy result
        monitor.health_history.append(
            HealthCheckResult(
                overall_status=HealthStatus.HEALTHY,
                metrics=[],
                timestamp=current_time - 100,
                duration_ms=10,
                errors=[],
            )
        )

        # Add warning result
        monitor.health_history.append(
            HealthCheckResult(
                overall_status=HealthStatus.WARNING,
                metrics=[],
                timestamp=current_time - 50,
                duration_ms=15,
                errors=["test error"],
            )
        )

        aggregated = monitor.get_aggregated_status()

        assert aggregated["checks_count"] == 2
        assert aggregated["overall_status"] == "healthy"
        assert aggregated["total_errors"] == 1
        assert aggregated["average_duration_ms"] == 12.5

    def test_export_diagnostics(self):
        """Test diagnostic information export."""
        monitor = AdvancedHealthMonitor()

        # Add a checker
        checker = Mock(spec=HealthChecker)
        checker.get_name.return_value = "test_checker"
        monitor.add_checker(checker)

        # Set some state
        monitor.monitoring_stats["checks_performed"] = 10

        diagnostics = monitor.export_diagnostics()

        assert diagnostics["monitor_info"]["checkers_count"] == 1
        assert diagnostics["checkers"] == ["test_checker"]
        assert diagnostics["monitoring_stats"]["checks_performed"] == 10
        assert "aggregated_status" in diagnostics
        assert "history_summary" in diagnostics


class TestIntegration:
    """Integration tests for the monitoring system."""

    async def test_full_monitoring_cycle(self):
        """Test complete monitoring cycle with multiple checkers."""
        # Setup monitor
        monitor = AdvancedHealthMonitor(
            {
                "check_interval": 30,
                "history_size": 10,
            }
        )

        # Add process checker
        with patch(
            "claude_mpm.services.infrastructure.monitoring.process.PSUTIL_AVAILABLE",
            True,
        ), patch(
            "claude_mpm.services.infrastructure.monitoring.process.psutil"
        ) as mock_psutil:
            mock_process = MagicMock()
            mock_process.is_running.return_value = True
            mock_process.status.return_value = "running"
            mock_process.cpu_percent.return_value = 25.0
            mock_process.memory_info.return_value = MagicMock(
                rss=100 * 1024 * 1024,
                vms=200 * 1024 * 1024,
            )
            mock_psutil.Process.return_value = mock_process
            mock_psutil.STATUS_ZOMBIE = "zombie"
            mock_psutil.STATUS_DEAD = "dead"
            mock_psutil.STATUS_STOPPED = "stopped"

            process_checker = ProcessResourceChecker(12345)
            monitor.add_checker(process_checker)

        # Add network checker
        with patch("socket.socket") as mock_socket_class:
            mock_socket = MagicMock()
            mock_socket.connect_ex.return_value = 0
            mock_socket_class.return_value = mock_socket

            network_checker = NetworkConnectivityChecker("localhost", 8080)
            monitor.add_checker(network_checker)

        # Add service checker
        service_stats = {
            "clients_connected": 50,
            "events_processed": 5000,
            "errors": 10,
            "last_activity": time.time() - 60,
        }
        service_checker = ServiceHealthChecker(service_stats)
        monitor.add_checker(service_checker)

        # Perform health check
        result = await monitor.perform_health_check()

        # Verify results
        assert result.overall_status in [HealthStatus.HEALTHY, HealthStatus.WARNING]
        assert len(result.metrics) > 5  # Multiple metrics from all checkers
        assert result.duration_ms > 0

        # Check history
        history = monitor.get_health_history()
        assert len(history) == 1

        # Check aggregated status
        aggregated = monitor.get_aggregated_status()
        assert aggregated["checks_count"] == 1

        # Export diagnostics
        diagnostics = monitor.export_diagnostics()
        assert len(diagnostics["checkers"]) == 3
