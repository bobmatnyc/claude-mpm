"""
Unit Tests for Resource Monitor
================================

WHY: Provides comprehensive unit testing for ResourceMonitor,
including resource checking, threshold detection, and callback triggers.

COVERAGE:
- Resource usage checking (FD, threads, connections, disk)
- Critical threshold detection (80%)
- Callback triggers
- Platform-specific behavior (Unix/Windows)
- Error handling

TEST STRATEGY:
- Unit tests with mocked psutil
- Test threshold calculations
- Test critical resource detection
- Test callback invocation
- Test error handling for missing processes
"""

from unittest.mock import Mock, patch

import psutil
import pytest

from claude_mpm.services.core.models.process import (DeploymentState,
                                                     ProcessStatus)
from claude_mpm.services.core.models.stability import ResourceUsage
from claude_mpm.services.local_ops import (DeploymentStateManager,
                                           LocalProcessManager)
from claude_mpm.services.local_ops.resource_monitor import ResourceMonitor

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def state_manager(tmp_path):
    """Create a state manager for testing."""
    state_file = tmp_path / "test-resource-state.json"
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
def sample_deployment(state_manager):
    """Create a sample deployment for testing."""
    deployment = DeploymentState(
        deployment_id="test-resource-app",
        process_id=12345,
        command=["python", "app.py"],
        working_directory="/tmp/test-project",
        port=3000,
        status=ProcessStatus.RUNNING,
    )
    state_manager.add_deployment(deployment)
    return deployment


# ============================================================================
# Resource Monitor Tests
# ============================================================================


class TestResourceMonitor:
    """Test suite for ResourceMonitor."""

    def test_initialization(self, process_manager):
        """Test resource monitor initialization."""
        monitor = ResourceMonitor(
            process_manager=process_manager,
            fd_threshold_percent=0.8,
            thread_threshold=1000,
            connection_threshold=500,
            disk_threshold_mb=100.0,
        )

        assert monitor.initialize()
        assert monitor.fd_threshold_percent == 0.8
        assert monitor.thread_threshold == 1000
        assert monitor.connection_threshold == 500
        assert monitor.disk_threshold_mb == 100.0
        assert not monitor._shutdown

        monitor.shutdown()
        assert monitor._shutdown

    @patch("psutil.Process")
    @patch("shutil.disk_usage")
    def test_check_resources_healthy(
        self, mock_disk_usage, mock_process_class, process_manager, sample_deployment
    ):
        """Test checking resources with healthy usage."""
        monitor = ResourceMonitor(
            process_manager=process_manager,
            fd_threshold_percent=0.8,
            thread_threshold=1000,
            connection_threshold=500,
            disk_threshold_mb=100.0,
        )
        monitor.initialize()

        # Mock process with healthy resource usage
        mock_process = Mock()
        mock_process.num_fds.return_value = 50  # Low FD usage
        mock_process.num_threads.return_value = 10  # Low thread count
        mock_process.net_connections.return_value = []  # No connections
        mock_process_class.return_value = mock_process

        # Mock disk usage
        mock_disk_usage.return_value = Mock(free=1024 * 1024 * 1024)  # 1GB free

        # Check resources
        usage = monitor.check_resources(sample_deployment.deployment_id)

        # Should be healthy
        assert not usage.is_critical
        assert usage.threads == 10
        assert usage.connections == 0
        assert usage.disk_free_mb > 100.0

        monitor.shutdown()

    @patch("psutil.Process")
    @patch("shutil.disk_usage")
    @patch("resource.getrlimit")
    def test_check_resources_critical_fd(
        self,
        mock_getrlimit,
        mock_disk_usage,
        mock_process_class,
        process_manager,
        sample_deployment,
    ):
        """Test detecting critical file descriptor usage."""
        monitor = ResourceMonitor(
            process_manager=process_manager,
            fd_threshold_percent=0.8,
            thread_threshold=1000,
            connection_threshold=500,
            disk_threshold_mb=100.0,
        )
        monitor.initialize()

        # Mock high FD usage
        mock_process = Mock()
        mock_process.num_fds.return_value = 900  # 90% of 1000
        mock_process.num_threads.return_value = 10
        mock_process.net_connections.return_value = []
        mock_process_class.return_value = mock_process

        # Mock ulimit
        mock_getrlimit.return_value = (1000, 1000)  # soft, hard limit

        # Mock disk usage
        mock_disk_usage.return_value = Mock(free=1024 * 1024 * 1024)

        # Check resources
        usage = monitor.check_resources(sample_deployment.deployment_id)

        # Should be critical (90% > 80%)
        assert usage.is_critical
        assert usage.file_descriptors == 900
        assert usage.max_file_descriptors == 1000
        assert usage.fd_usage_percent == 90.0
        assert usage.is_fd_critical

        monitor.shutdown()

    @patch("psutil.Process")
    @patch("shutil.disk_usage")
    def test_check_resources_critical_threads(
        self, mock_disk_usage, mock_process_class, process_manager, sample_deployment
    ):
        """Test detecting critical thread usage."""
        monitor = ResourceMonitor(
            process_manager=process_manager,
            fd_threshold_percent=0.8,
            thread_threshold=1000,
            connection_threshold=500,
            disk_threshold_mb=100.0,
        )
        monitor.initialize()

        # Mock high thread usage
        mock_process = Mock()
        mock_process.num_fds.return_value = 50
        mock_process.num_threads.return_value = 900  # 90% of 1000
        mock_process.net_connections.return_value = []
        mock_process_class.return_value = mock_process

        # Mock disk usage
        mock_disk_usage.return_value = Mock(free=1024 * 1024 * 1024)

        # Check resources
        usage = monitor.check_resources(sample_deployment.deployment_id)

        # Should be critical (900 > 800 = 80% of 1000)
        assert usage.is_critical
        assert usage.threads == 900

        monitor.shutdown()

    @patch("psutil.Process")
    @patch("shutil.disk_usage")
    def test_check_resources_critical_connections(
        self, mock_disk_usage, mock_process_class, process_manager, sample_deployment
    ):
        """Test detecting critical connection usage."""
        monitor = ResourceMonitor(
            process_manager=process_manager,
            fd_threshold_percent=0.8,
            thread_threshold=1000,
            connection_threshold=500,
            disk_threshold_mb=100.0,
        )
        monitor.initialize()

        # Mock high connection count
        mock_process = Mock()
        mock_process.num_fds.return_value = 50
        mock_process.num_threads.return_value = 10
        mock_connections = [Mock(status="ESTABLISHED")] * 450  # 90% of 500
        mock_process.net_connections.return_value = mock_connections
        mock_process_class.return_value = mock_process

        # Mock disk usage
        mock_disk_usage.return_value = Mock(free=1024 * 1024 * 1024)

        # Check resources
        usage = monitor.check_resources(sample_deployment.deployment_id)

        # Should be critical (450 > 400 = 80% of 500)
        assert usage.is_critical
        assert usage.connections == 450

        monitor.shutdown()

    @patch("psutil.Process")
    @patch("shutil.disk_usage")
    def test_check_resources_critical_disk(
        self, mock_disk_usage, mock_process_class, process_manager, sample_deployment
    ):
        """Test detecting critical disk space."""
        monitor = ResourceMonitor(
            process_manager=process_manager,
            fd_threshold_percent=0.8,
            thread_threshold=1000,
            connection_threshold=500,
            disk_threshold_mb=100.0,
        )
        monitor.initialize()

        # Mock low disk space
        mock_process = Mock()
        mock_process.num_fds.return_value = 50
        mock_process.num_threads.return_value = 10
        mock_process.net_connections.return_value = []
        mock_process_class.return_value = mock_process

        # Mock disk usage (50MB free < 100MB threshold)
        mock_disk_usage.return_value = Mock(free=50 * 1024 * 1024)

        # Check resources
        usage = monitor.check_resources(sample_deployment.deployment_id)

        # Should be critical
        assert usage.is_critical
        assert usage.disk_free_mb < 100.0

        monitor.shutdown()

    @patch("psutil.Process")
    def test_check_resources_process_not_found(
        self, mock_process_class, process_manager, sample_deployment
    ):
        """Test handling process not found error."""
        monitor = ResourceMonitor(process_manager=process_manager)
        monitor.initialize()

        # Mock process not found
        mock_process_class.side_effect = psutil.NoSuchProcess(12345)

        # Check resources
        usage = monitor.check_resources(sample_deployment.deployment_id)

        # Should return critical status
        assert usage.is_critical
        assert "error" in usage.details

        monitor.shutdown()

    @patch("psutil.Process")
    def test_check_resources_access_denied(
        self, mock_process_class, process_manager, sample_deployment
    ):
        """Test handling access denied error."""
        monitor = ResourceMonitor(process_manager=process_manager)
        monitor.initialize()

        # Mock access denied
        mock_process_class.side_effect = psutil.AccessDenied()

        # Check resources
        usage = monitor.check_resources(sample_deployment.deployment_id)

        # Should not be critical (just can't access)
        assert not usage.is_critical
        assert "error" in usage.details

        monitor.shutdown()

    def test_check_resources_deployment_not_found(self, process_manager):
        """Test checking resources for non-existent deployment."""
        monitor = ResourceMonitor(process_manager=process_manager)
        monitor.initialize()

        # Should raise ValueError
        with pytest.raises(ValueError, match="Deployment not found"):
            monitor.check_resources("nonexistent-app")

        monitor.shutdown()

    @patch("psutil.Process")
    @patch("shutil.disk_usage")
    def test_is_critical(
        self, mock_disk_usage, mock_process_class, process_manager, sample_deployment
    ):
        """Test is_critical() convenience method."""
        monitor = ResourceMonitor(
            process_manager=process_manager,
            thread_threshold=100,
        )
        monitor.initialize()

        # Mock healthy process
        mock_process = Mock()
        mock_process.num_fds.return_value = 10
        mock_process.num_threads.return_value = 10
        mock_process.net_connections.return_value = []
        mock_process_class.return_value = mock_process
        mock_disk_usage.return_value = Mock(free=1024 * 1024 * 1024)

        # Should not be critical
        assert not monitor.is_critical(sample_deployment.deployment_id)

        # Mock critical thread usage
        mock_process.num_threads.return_value = 90  # 90% of 100

        # Should be critical
        assert monitor.is_critical(sample_deployment.deployment_id)

        monitor.shutdown()

    @patch("psutil.Process")
    @patch("shutil.disk_usage")
    def test_critical_callback(
        self, mock_disk_usage, mock_process_class, process_manager, sample_deployment
    ):
        """Test critical resource callback trigger."""
        monitor = ResourceMonitor(
            process_manager=process_manager,
            thread_threshold=100,
        )
        monitor.initialize()

        # Register callback
        callback_called = []

        def critical_callback(dep_id: str, usage: ResourceUsage):
            callback_called.append((dep_id, usage))

        monitor.register_critical_callback(critical_callback)

        # Mock critical thread usage
        mock_process = Mock()
        mock_process.num_fds.return_value = 10
        mock_process.num_threads.return_value = 90  # Critical
        mock_process.net_connections.return_value = []
        mock_process_class.return_value = mock_process
        mock_disk_usage.return_value = Mock(free=1024 * 1024 * 1024)

        # Check resources (should trigger callback)
        usage = monitor.check_resources(sample_deployment.deployment_id)

        # Callback should have been called
        assert len(callback_called) == 1
        assert callback_called[0][0] == sample_deployment.deployment_id
        assert callback_called[0][1].is_critical

        monitor.shutdown()

    @patch("psutil.Process")
    @patch("shutil.disk_usage")
    def test_callback_not_triggered_healthy(
        self, mock_disk_usage, mock_process_class, process_manager, sample_deployment
    ):
        """Test callback NOT triggered when resources healthy."""
        monitor = ResourceMonitor(process_manager=process_manager)
        monitor.initialize()

        # Register callback
        callback_called = []

        def critical_callback(dep_id: str, usage: ResourceUsage):
            callback_called.append((dep_id, usage))

        monitor.register_critical_callback(critical_callback)

        # Mock healthy process
        mock_process = Mock()
        mock_process.num_fds.return_value = 10
        mock_process.num_threads.return_value = 10
        mock_process.net_connections.return_value = []
        mock_process_class.return_value = mock_process
        mock_disk_usage.return_value = Mock(free=1024 * 1024 * 1024)

        # Check resources
        usage = monitor.check_resources(sample_deployment.deployment_id)

        # Callback should NOT have been called
        assert len(callback_called) == 0

        monitor.shutdown()

    @patch("psutil.Process")
    @patch("shutil.disk_usage")
    def test_callback_exception_handling(
        self, mock_disk_usage, mock_process_class, process_manager, sample_deployment
    ):
        """Test callback exception doesn't crash monitor."""
        monitor = ResourceMonitor(
            process_manager=process_manager,
            thread_threshold=10,
        )
        monitor.initialize()

        # Register callback that raises exception
        def bad_callback(dep_id: str, usage: ResourceUsage):
            raise ValueError("Test exception")

        monitor.register_critical_callback(bad_callback)

        # Mock critical usage
        mock_process = Mock()
        mock_process.num_fds.return_value = 10
        mock_process.num_threads.return_value = 100  # Critical
        mock_process.net_connections.return_value = []
        mock_process_class.return_value = mock_process
        mock_disk_usage.return_value = Mock(free=1024 * 1024 * 1024)

        # Check resources - should not crash despite callback exception
        usage = monitor.check_resources(sample_deployment.deployment_id)
        assert usage.is_critical

        monitor.shutdown()

    def test_resource_usage_properties(self):
        """Test ResourceUsage data model properties."""
        usage = ResourceUsage(
            deployment_id="test-app",
            file_descriptors=800,
            max_file_descriptors=1000,
            threads=500,
            connections=250,
            disk_free_mb=50.0,
            is_critical=True,
        )

        assert usage.fd_usage_percent == 80.0
        assert usage.is_fd_critical
        assert usage.deployment_id == "test-app"

    def test_resource_usage_get_critical_resources(self):
        """Test ResourceUsage.get_critical_resources()."""
        usage = ResourceUsage(
            deployment_id="test-app",
            file_descriptors=900,
            max_file_descriptors=1000,
            threads=900,
            connections=450,
            disk_free_mb=50.0,
            is_critical=True,
            details={
                "thread_threshold": 1000,
                "connection_threshold": 500,
                "disk_threshold_mb": 100,
            },
        )

        critical = usage.get_critical_resources()

        # Should include FD, threads, connections, and disk
        assert len(critical) == 4
        assert any("file_descriptors" in c for c in critical)
        assert any("threads" in c for c in critical)
        assert any("connections" in c for c in critical)
        assert any("disk_space" in c for c in critical)

    def test_resource_usage_serialization(self):
        """Test ResourceUsage to_dict/from_dict."""
        original = ResourceUsage(
            deployment_id="test-app",
            file_descriptors=100,
            max_file_descriptors=1000,
            threads=50,
            connections=10,
            disk_free_mb=500.0,
            is_critical=False,
        )

        # Serialize
        data = original.to_dict()

        # Deserialize
        restored = ResourceUsage.from_dict(data)

        assert restored.deployment_id == original.deployment_id
        assert restored.file_descriptors == original.file_descriptors
        assert restored.max_file_descriptors == original.max_file_descriptors
        assert restored.is_critical == original.is_critical


# ============================================================================
# Platform-Specific Tests
# ============================================================================


class TestResourceMonitorPlatform:
    """Test platform-specific behavior."""

    @patch("platform.system")
    @patch("psutil.Process")
    @patch("shutil.disk_usage")
    def test_windows_no_fd_check(
        self,
        mock_disk_usage,
        mock_process_class,
        mock_platform,
        process_manager,
        sample_deployment,
    ):
        """Test Windows platform doesn't check file descriptors."""
        mock_platform.return_value = "Windows"

        monitor = ResourceMonitor(process_manager=process_manager)
        monitor.initialize()

        # Verify platform detection
        assert monitor.is_windows

        # Mock process
        mock_process = Mock()
        # num_fds not available on Windows
        mock_process.num_fds.side_effect = AttributeError()
        mock_process.num_threads.return_value = 10
        mock_process.net_connections.return_value = []
        mock_process_class.return_value = mock_process
        mock_disk_usage.return_value = Mock(free=1024 * 1024 * 1024)

        # Check resources - should not fail on Windows
        usage = monitor.check_resources(sample_deployment.deployment_id)

        # FD fields should be zero/default
        assert usage.file_descriptors == 0
        assert usage.max_file_descriptors == 0

        monitor.shutdown()
