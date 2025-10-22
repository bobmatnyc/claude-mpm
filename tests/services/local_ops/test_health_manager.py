"""
Integration Tests for Health Check Manager
===========================================

WHY: Provides comprehensive integration testing for HealthCheckManager,
including background monitoring, health aggregation, and callback triggers.

COVERAGE:
- Health check orchestration
- Background monitoring thread lifecycle
- Health history tracking
- Status change callbacks
- Health status aggregation logic

TEST STRATEGY:
- Integration tests with real components where possible
- Mock only external dependencies (psutil, requests)
- Test thread safety and concurrency
- Test background monitoring behavior
"""

import time
from unittest.mock import Mock, patch

import psutil
import pytest

from claude_mpm.services.core.models.health import HealthStatus
from claude_mpm.services.core.models.process import (
    DeploymentState,
    ProcessStatus,
)
from claude_mpm.services.core.models.stability import ResourceUsage
from claude_mpm.services.local_ops import (
    DeploymentStateManager,
    LocalProcessManager,
)
from claude_mpm.services.local_ops.health_manager import HealthCheckManager


# Fixtures
@pytest.fixture
def state_manager(tmp_path):
    """Create a state manager for testing."""
    state_file = tmp_path / "test-health-state.json"
    # Don't create the file - let DeploymentStateManager create it properly
    manager = DeploymentStateManager(str(state_file))
    manager.initialize()
    return manager


@pytest.fixture
def process_manager(state_manager):
    """Create a process manager for testing."""
    manager = LocalProcessManager(state_manager)
    manager.initialize()
    return manager


@pytest.fixture
def health_manager(process_manager):
    """Create a health check manager for testing."""
    manager = HealthCheckManager(
        process_manager=process_manager,
        check_interval=1,  # Fast interval for testing
        history_limit=10,
    )
    manager.initialize()
    yield manager
    # Cleanup
    if manager.is_monitoring():
        manager.stop_monitoring()
    manager.shutdown()


@pytest.fixture
def sample_deployment(state_manager):
    """Create a sample deployment for testing."""
    deployment = DeploymentState(
        deployment_id="test-health-deployment",
        process_id=12345,
        command=["python", "app.py"],
        working_directory="/tmp/test-project",
        port=3000,
        status=ProcessStatus.RUNNING,
    )
    state_manager.add_deployment(deployment)
    return deployment


@pytest.fixture
def healthy_resource_usage():
    """Create a healthy ResourceUsage object for testing."""
    return ResourceUsage(
        deployment_id="test-health-deployment",
        file_descriptors=50,
        max_file_descriptors=1024,
        threads=10,
        connections=5,
        disk_free_mb=1000.0,
        is_critical=False,
    )


@pytest.fixture
def degraded_resource_usage():
    """Create a degraded ResourceUsage object for testing."""
    return ResourceUsage(
        deployment_id="test-health-deployment",
        file_descriptors=850,  # 83% usage - critical
        max_file_descriptors=1024,
        threads=10,
        connections=5,
        disk_free_mb=1000.0,
        is_critical=True,
    )


# ============================================================================
# Health Check Manager Tests
# ============================================================================


class TestHealthCheckManager:
    """Test suite for HealthCheckManager."""

    def test_initialization(self, process_manager):
        """Test health check manager initialization."""
        manager = HealthCheckManager(process_manager, check_interval=30)
        assert manager.initialize()
        assert manager.is_initialized
        assert not manager.is_monitoring()

    def test_check_health_all_healthy(self, health_manager, sample_deployment):
        """Test health check with all checks healthy."""
        # Mock all health checks to return HEALTHY
        with patch("psutil.Process") as mock_process_class:
            mock_process = Mock()
            mock_process.is_running.return_value = True
            mock_process.status.return_value = psutil.STATUS_RUNNING
            # cpu_percent(interval=X) is called with argument, so use side_effect
            mock_process.cpu_percent = Mock(return_value=25.0)
            mock_process.name.return_value = "python"
            mock_process.num_threads.return_value = 4
            mock_process.num_fds = Mock(return_value=50)  # Unix only - file descriptors
            mock_memory_info = Mock()
            mock_memory_info.rss = 100 * 1024 * 1024  # 100MB
            mock_process.memory_info.return_value = mock_memory_info
            mock_process.net_connections.return_value = []
            mock_process_class.return_value = mock_process

            health = health_manager.check_health(sample_deployment.deployment_id)

            assert health.deployment_id == sample_deployment.deployment_id
            assert health.overall_status == HealthStatus.HEALTHY
            assert len(health.checks) >= 2  # At least process and resource
            assert health.last_check is not None

    def test_check_health_process_unhealthy(self, health_manager, sample_deployment):
        """Test health aggregation when process is unhealthy."""
        # Mock process as dead
        with patch("psutil.Process") as mock_process_class:
            mock_process_class.side_effect = psutil.NoSuchProcess(12345)

            health = health_manager.check_health(sample_deployment.deployment_id)

            assert health.overall_status == HealthStatus.UNHEALTHY
            process_check = health.get_check_by_type("process")
            assert process_check is not None
            assert process_check.status == HealthStatus.UNHEALTHY

    def test_check_health_degraded_resources(self, health_manager, sample_deployment):
        """Test health aggregation with degraded resources."""
        # Mock process healthy but resources degraded
        with patch("psutil.Process") as mock_process_class:
            mock_process = Mock()
            mock_process.is_running.return_value = True
            mock_process.status.return_value = psutil.STATUS_RUNNING
            # cpu_percent(interval=X) is called with argument, so use Mock(return_value=...)
            mock_process.cpu_percent = Mock(return_value=95.0)  # High CPU
            mock_process.name.return_value = "python"
            mock_process.num_threads.return_value = 4
            mock_process.num_fds = Mock(return_value=50)  # Unix only - file descriptors
            mock_memory_info = Mock()
            mock_memory_info.rss = 100 * 1024 * 1024
            mock_process.memory_info.return_value = mock_memory_info
            mock_process.net_connections.return_value = []
            mock_process_class.return_value = mock_process

            health = health_manager.check_health(
                sample_deployment.deployment_id,
                cpu_threshold=80.0,
            )

            assert health.overall_status == HealthStatus.DEGRADED
            resource_check = health.get_check_by_type("resource")
            assert resource_check is not None
            assert resource_check.status == HealthStatus.DEGRADED

    def test_check_health_with_http_endpoint(self, health_manager, sample_deployment):
        """Test health check with HTTP endpoint."""
        with patch("psutil.Process") as mock_process_class, patch(
            "requests.get"
        ) as mock_get:
            # Mock process healthy
            mock_process = Mock()
            mock_process.is_running.return_value = True
            mock_process.status.return_value = psutil.STATUS_RUNNING
            # cpu_percent(interval=X) is called with argument, so use Mock(return_value=...)
            mock_process.cpu_percent = Mock(return_value=25.0)
            mock_process.name.return_value = "python"
            mock_process.num_threads.return_value = 4
            mock_memory_info = Mock()
            mock_memory_info.rss = 100 * 1024 * 1024
            mock_process.memory_info.return_value = mock_memory_info
            mock_process.net_connections.return_value = []
            mock_process_class.return_value = mock_process

            # Mock HTTP healthy
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            health = health_manager.check_health(
                sample_deployment.deployment_id,
                endpoint="http://localhost:3000/health",
            )

            assert len(health.checks) == 3  # HTTP, process, resource
            http_check = health.get_check_by_type("http")
            assert http_check is not None
            assert http_check.status == HealthStatus.HEALTHY

    def test_health_history(self, health_manager, sample_deployment):
        """Test health history tracking."""
        with patch("psutil.Process") as mock_process_class:
            mock_process = Mock()
            mock_process.is_running.return_value = True
            mock_process.status.return_value = psutil.STATUS_RUNNING
            # cpu_percent(interval=X) is called with argument, so use Mock(return_value=...)
            mock_process.cpu_percent = Mock(return_value=25.0)
            mock_process.name.return_value = "python"
            mock_process.num_threads.return_value = 4
            mock_memory_info = Mock()
            mock_memory_info.rss = 100 * 1024 * 1024
            mock_process.memory_info.return_value = mock_memory_info
            mock_process.net_connections.return_value = []
            mock_process_class.return_value = mock_process

            # Perform multiple health checks
            for _ in range(5):
                health_manager.check_health(sample_deployment.deployment_id)
                time.sleep(0.1)

            # Get history
            history = health_manager.get_health_history(
                sample_deployment.deployment_id, limit=5
            )

            assert len(history) == 5
            # History should be newest first
            for i in range(len(history) - 1):
                assert history[i].last_check >= history[i + 1].last_check

    def test_health_history_limit(self, health_manager, sample_deployment):
        """Test health history limit enforcement."""
        with patch("psutil.Process") as mock_process_class:
            mock_process = Mock()
            mock_process.is_running.return_value = True
            mock_process.status.return_value = psutil.STATUS_RUNNING
            # cpu_percent(interval=X) is called with argument, so use Mock(return_value=...)
            mock_process.cpu_percent = Mock(return_value=25.0)
            mock_process.name.return_value = "python"
            mock_process.num_threads.return_value = 4
            mock_memory_info = Mock()
            mock_memory_info.rss = 100 * 1024 * 1024
            mock_process.memory_info.return_value = mock_memory_info
            mock_process.net_connections.return_value = []
            mock_process_class.return_value = mock_process

            # Perform more checks than history limit
            for _ in range(15):
                health_manager.check_health(sample_deployment.deployment_id)

            # Should only keep last 10 (history_limit)
            history = health_manager.get_health_history(
                sample_deployment.deployment_id, limit=100
            )

            assert len(history) == 10

    def test_status_change_callback(self, health_manager, sample_deployment):
        """Test status change callback triggering."""
        callback_called = []

        def status_callback(deployment_id, old_status, new_status):
            callback_called.append((deployment_id, old_status, new_status))

        health_manager.register_status_callback(status_callback)

        with patch("psutil.Process") as mock_process_class:
            # First check: healthy
            mock_process = Mock()
            mock_process.is_running.return_value = True
            mock_process.status.return_value = psutil.STATUS_RUNNING
            # cpu_percent(interval=X) is called with argument, so use Mock(return_value=...)
            mock_process.cpu_percent = Mock(return_value=25.0)
            mock_process.name.return_value = "python"
            mock_process.num_threads.return_value = 4
            mock_process.num_fds = Mock(return_value=50)  # Unix only - file descriptors
            mock_memory_info = Mock()
            mock_memory_info.rss = 100 * 1024 * 1024
            mock_process.memory_info.return_value = mock_memory_info
            mock_process.net_connections.return_value = []
            mock_process_class.return_value = mock_process

            health1 = health_manager.check_health(sample_deployment.deployment_id)
            assert health1.overall_status == HealthStatus.HEALTHY

            # Second check: unhealthy
            mock_process_class.side_effect = psutil.NoSuchProcess(12345)

            health2 = health_manager.check_health(sample_deployment.deployment_id)
            assert health2.overall_status == HealthStatus.UNHEALTHY

            # Callback should have been called
            assert len(callback_called) == 1
            assert callback_called[0][0] == sample_deployment.deployment_id
            assert callback_called[0][1] == HealthStatus.HEALTHY
            assert callback_called[0][2] == HealthStatus.UNHEALTHY

    def test_start_stop_monitoring(self, health_manager):
        """Test background monitoring lifecycle."""
        assert not health_manager.is_monitoring()

        health_manager.start_monitoring()
        assert health_manager.is_monitoring()

        # Give thread time to start
        time.sleep(0.1)

        health_manager.stop_monitoring()
        assert not health_manager.is_monitoring()

    def test_monitoring_performs_checks(self, health_manager, sample_deployment):
        """Test that background monitoring performs health checks."""
        with patch("psutil.Process") as mock_process_class:
            mock_process = Mock()
            mock_process.is_running.return_value = True
            mock_process.status.return_value = psutil.STATUS_RUNNING
            # cpu_percent(interval=X) is called with argument, so use Mock(return_value=...)
            mock_process.cpu_percent = Mock(return_value=25.0)
            mock_process.name.return_value = "python"
            mock_process.num_threads.return_value = 4
            mock_memory_info = Mock()
            mock_memory_info.rss = 100 * 1024 * 1024
            mock_process.memory_info.return_value = mock_memory_info
            mock_process.net_connections.return_value = []
            mock_process_class.return_value = mock_process

            # Start monitoring
            health_manager.start_monitoring()

            # Wait for a few check intervals
            time.sleep(2.5)  # Should perform at least 2 checks

            # Stop monitoring
            health_manager.stop_monitoring()

            # Check that history was populated
            history = health_manager.get_health_history(sample_deployment.deployment_id)
            assert len(history) >= 2

    def test_monitoring_handles_exceptions(self, health_manager, sample_deployment):
        """Test that monitoring thread handles exceptions gracefully."""
        with patch("psutil.Process") as mock_process_class:
            # Make process check raise exception
            mock_process_class.side_effect = Exception("Unexpected error")

            # Start monitoring (should not crash)
            health_manager.start_monitoring()
            time.sleep(1.5)
            health_manager.stop_monitoring()

            # Manager should still be operational
            assert not health_manager.is_monitoring()

    def test_deployment_not_found(self, health_manager):
        """Test check with non-existent deployment."""
        with pytest.raises(ValueError, match="Deployment not found"):
            health_manager.check_health("non-existent-deployment")

    def test_shutdown_stops_monitoring(self, process_manager):
        """Test that shutdown stops monitoring."""
        manager = HealthCheckManager(process_manager, check_interval=1)
        manager.initialize()

        manager.start_monitoring()
        assert manager.is_monitoring()

        manager.shutdown()
        assert not manager.is_monitoring()


# ============================================================================
# Health Aggregation Logic Tests
# ============================================================================


class TestHealthAggregation:
    """Test suite for health status aggregation logic."""

    def test_all_healthy(self, health_manager, sample_deployment):
        """Test aggregation when all checks are healthy."""
        with patch("psutil.Process") as mock_process_class:
            mock_process = Mock()
            mock_process.is_running.return_value = True
            mock_process.status.return_value = psutil.STATUS_RUNNING
            # cpu_percent(interval=X) is called with argument, so use Mock(return_value=...)
            mock_process.cpu_percent = Mock(return_value=25.0)
            mock_process.name.return_value = "python"
            mock_process.num_threads.return_value = 4
            mock_process.num_fds = Mock(return_value=50)  # Unix only - file descriptors
            mock_memory_info = Mock()
            mock_memory_info.rss = 100 * 1024 * 1024
            mock_process.memory_info.return_value = mock_memory_info
            mock_process.net_connections.return_value = []
            mock_process_class.return_value = mock_process

            health = health_manager.check_health(sample_deployment.deployment_id)

            assert health.overall_status == HealthStatus.HEALTHY
            assert all(c.status == HealthStatus.HEALTHY for c in health.checks)

    def test_process_unhealthy_overrides_all(self, health_manager, sample_deployment):
        """Test that process UNHEALTHY results in overall UNHEALTHY."""
        # Even if resources are healthy, dead process = unhealthy
        with patch("psutil.Process") as mock_process_class:
            mock_process_class.side_effect = psutil.NoSuchProcess(12345)

            health = health_manager.check_health(sample_deployment.deployment_id)

            assert health.overall_status == HealthStatus.UNHEALTHY

    def test_resource_degraded_with_healthy_process(
        self, health_manager, sample_deployment
    ):
        """Test that resource issues cause DEGRADED when process is healthy."""
        with patch("psutil.Process") as mock_process_class:
            mock_process = Mock()
            mock_process.is_running.return_value = True
            mock_process.status.return_value = psutil.STATUS_RUNNING
            # cpu_percent(interval=X) is called with argument, so use Mock(return_value=...)
            mock_process.cpu_percent = Mock(return_value=95.0)  # High CPU
            mock_process.name.return_value = "python"
            mock_process.num_threads.return_value = 4
            mock_process.num_fds = Mock(return_value=50)  # Unix only - file descriptors
            mock_memory_info = Mock()
            mock_memory_info.rss = 100 * 1024 * 1024
            mock_process.memory_info.return_value = mock_memory_info
            mock_process.net_connections.return_value = []
            mock_process_class.return_value = mock_process

            health = health_manager.check_health(sample_deployment.deployment_id)

            assert health.overall_status == HealthStatus.DEGRADED

    def test_http_unhealthy_with_healthy_process(
        self, health_manager, sample_deployment
    ):
        """Test HTTP issues cause DEGRADED when process is healthy."""
        with patch("psutil.Process") as mock_process_class, patch(
            "requests.get"
        ) as mock_get:
            # Process healthy
            mock_process = Mock()
            mock_process.is_running.return_value = True
            mock_process.status.return_value = psutil.STATUS_RUNNING
            # cpu_percent(interval=X) is called with argument, so use Mock(return_value=...)
            mock_process.cpu_percent = Mock(return_value=25.0)
            mock_process.name.return_value = "python"
            mock_process.num_threads.return_value = 4
            mock_process.num_fds = Mock(return_value=50)  # Unix only - file descriptors
            mock_memory_info = Mock()
            mock_memory_info.rss = 100 * 1024 * 1024
            mock_process.memory_info.return_value = mock_memory_info
            mock_process.net_connections.return_value = []
            mock_process_class.return_value = mock_process

            # HTTP unhealthy
            mock_response = Mock()
            mock_response.status_code = 500
            mock_get.return_value = mock_response

            health = health_manager.check_health(
                sample_deployment.deployment_id,
                endpoint="http://localhost:3000/health",
            )

            assert health.overall_status == HealthStatus.DEGRADED
