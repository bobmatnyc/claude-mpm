"""
Unit Tests for Health Check Implementations
============================================

WHY: Provides comprehensive test coverage for HTTP, process, and resource
health checks to ensure reliability and correctness.

COVERAGE:
- HTTP health check: endpoint availability, timeouts, retries, status codes
- Process health check: existence, status, responsiveness
- Resource health check: CPU, memory, file descriptors, threads, connections

TEST STRATEGY:
- Mock external dependencies (psutil, requests)
- Test success and failure scenarios
- Test edge cases and error handling
- Verify health status aggregation logic
"""

import time
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import psutil
import pytest
import requests
from requests.exceptions import ConnectionError, RequestException, Timeout

from claude_mpm.services.core.models.health import HealthStatus
from claude_mpm.services.core.models.process import (DeploymentState,
                                                     ProcessStatus,
                                                     StartConfig)
from claude_mpm.services.local_ops.health_checks import (HttpHealthCheck,
                                                         ProcessHealthCheck,
                                                         ResourceHealthCheck)
from claude_mpm.services.local_ops.state_manager import DeploymentStateManager


# Fixtures
@pytest.fixture
def state_manager(tmp_path):
    """Create a state manager for testing."""
    state_file = tmp_path / "test-state.json"
    # Don't create the file - let DeploymentStateManager create it properly
    manager = DeploymentStateManager(str(state_file))
    manager.initialize()
    return manager


@pytest.fixture
def process_manager_mock(state_manager):
    """Create a mock process manager with state manager."""
    mock = Mock()
    mock.state_manager = state_manager
    return mock


@pytest.fixture
def sample_deployment(state_manager):
    """Create a sample deployment for testing."""
    deployment = DeploymentState(
        deployment_id="test-deployment-123",
        process_id=12345,
        command=["python", "app.py"],
        working_directory="/tmp/test-project",
        port=3000,
        status=ProcessStatus.RUNNING,
    )
    state_manager.add_deployment(deployment)
    return deployment


# ============================================================================
# HTTP Health Check Tests
# ============================================================================


class TestHttpHealthCheck:
    """Test suite for HttpHealthCheck."""

    def test_initialization(self, process_manager_mock):
        """Test health check initialization."""
        http_check = HttpHealthCheck(process_manager_mock)
        assert http_check.initialize()
        assert http_check.is_initialized
        assert http_check.get_check_type() == "http"

    def test_healthy_response(self, process_manager_mock, sample_deployment):
        """Test healthy HTTP response."""
        http_check = HttpHealthCheck(process_manager_mock)
        http_check.initialize()

        # Mock successful HTTP request
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            result = http_check.check(
                sample_deployment.deployment_id,
                endpoint="http://localhost:3000/health",
            )

            assert result.status == HealthStatus.HEALTHY
            assert result.check_type == "http"
            assert "responding normally" in result.message
            assert result.details["status_code"] == 200
            assert "response_time_ms" in result.details

    def test_endpoint_from_deployment_port(
        self, process_manager_mock, sample_deployment
    ):
        """Test endpoint construction from deployment port."""
        http_check = HttpHealthCheck(process_manager_mock)
        http_check.initialize()

        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            # Don't provide endpoint, should use deployment port
            result = http_check.check(sample_deployment.deployment_id)

            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert "localhost:3000" in call_args[0][0]

    def test_no_endpoint_no_port(self, process_manager_mock, state_manager):
        """Test behavior when no endpoint and no port configured."""
        deployment = DeploymentState(
            deployment_id="test-no-port",
            process_id=99999,
            command=["python", "app.py"],
            working_directory="/tmp/test",
            port=None,  # No port
            status=ProcessStatus.RUNNING,
        )
        state_manager.add_deployment(deployment)

        http_check = HttpHealthCheck(process_manager_mock)
        http_check.initialize()

        result = http_check.check(deployment.deployment_id)

        assert result.status == HealthStatus.UNKNOWN
        assert "No HTTP endpoint configured" in result.message

    def test_unexpected_status_code(self, process_manager_mock, sample_deployment):
        """Test HTTP response with unexpected status code."""
        http_check = HttpHealthCheck(process_manager_mock)
        http_check.initialize()

        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_get.return_value = mock_response

            result = http_check.check(
                sample_deployment.deployment_id,
                endpoint="http://localhost:3000/health",
                expected_status=200,
            )

            assert result.status == HealthStatus.DEGRADED
            assert "unexpected status code" in result.message
            assert result.details["status_code"] == 500

    def test_timeout_with_retry(self, process_manager_mock, sample_deployment):
        """Test HTTP timeout with retry logic."""
        http_check = HttpHealthCheck(
            process_manager_mock, default_timeout=1.0, max_retries=2
        )
        http_check.initialize()

        with patch("requests.get") as mock_get:
            mock_get.side_effect = Timeout("Connection timeout")

            result = http_check.check(
                sample_deployment.deployment_id,
                endpoint="http://localhost:3000/health",
            )

            # Should retry 2 times + initial attempt = 3 total
            assert mock_get.call_count == 3
            assert result.status == HealthStatus.DEGRADED
            assert "timeout" in result.message.lower()
            assert result.details["attempts"] == 3

    def test_connection_error_with_retry(self, process_manager_mock, sample_deployment):
        """Test connection error with retry logic."""
        http_check = HttpHealthCheck(process_manager_mock, max_retries=2)
        http_check.initialize()

        with patch("requests.get") as mock_get:
            mock_get.side_effect = ConnectionError("Connection refused")

            result = http_check.check(
                sample_deployment.deployment_id,
                endpoint="http://localhost:3000/health",
            )

            assert mock_get.call_count == 3
            assert result.status == HealthStatus.UNHEALTHY
            assert "Cannot connect" in result.message

    def test_request_exception(self, process_manager_mock, sample_deployment):
        """Test general request exception."""
        http_check = HttpHealthCheck(process_manager_mock)
        http_check.initialize()

        with patch("requests.get") as mock_get:
            mock_get.side_effect = RequestException("SSL error")

            result = http_check.check(
                sample_deployment.deployment_id,
                endpoint="http://localhost:3000/health",
            )

            assert result.status == HealthStatus.UNHEALTHY
            assert "request failed" in result.message.lower()

    def test_deployment_not_found(self, process_manager_mock):
        """Test check with non-existent deployment."""
        http_check = HttpHealthCheck(process_manager_mock)
        http_check.initialize()

        with pytest.raises(ValueError, match="Deployment not found"):
            http_check.check("non-existent-deployment")


# ============================================================================
# Process Health Check Tests
# ============================================================================


class TestProcessHealthCheck:
    """Test suite for ProcessHealthCheck."""

    def test_initialization(self, process_manager_mock):
        """Test health check initialization."""
        process_check = ProcessHealthCheck(process_manager_mock)
        assert process_check.initialize()
        assert process_check.is_initialized
        assert process_check.get_check_type() == "process"

    def test_healthy_process(self, process_manager_mock, sample_deployment):
        """Test health check on healthy running process."""
        process_check = ProcessHealthCheck(process_manager_mock)
        process_check.initialize()

        # Mock psutil.Process
        with patch("psutil.Process") as mock_process_class:
            mock_process = Mock()
            mock_process.is_running.return_value = True
            mock_process.status.return_value = psutil.STATUS_RUNNING
            # cpu_percent(interval=X) is called with argument, so use Mock(return_value=...)
            mock_process.cpu_percent = Mock(return_value=5.0)
            mock_process.name.return_value = "python"
            mock_process.num_threads.return_value = 4
            mock_process_class.return_value = mock_process

            result = process_check.check(sample_deployment.deployment_id)

            assert result.status == HealthStatus.HEALTHY
            assert result.check_type == "process"
            assert "running normally" in result.message
            assert result.details["pid"] == sample_deployment.process_id
            assert result.details["status"] == psutil.STATUS_RUNNING

    def test_zombie_process(self, process_manager_mock, sample_deployment):
        """Test detection of zombie process."""
        process_check = ProcessHealthCheck(process_manager_mock)
        process_check.initialize()

        with patch("psutil.Process") as mock_process_class:
            mock_process = Mock()
            mock_process.is_running.return_value = True
            mock_process.status.return_value = psutil.STATUS_ZOMBIE
            mock_process_class.return_value = mock_process

            result = process_check.check(sample_deployment.deployment_id)

            assert result.status == HealthStatus.UNHEALTHY
            assert "zombie" in result.message.lower()

    def test_stopped_process(self, process_manager_mock, sample_deployment):
        """Test detection of stopped process."""
        process_check = ProcessHealthCheck(process_manager_mock)
        process_check.initialize()

        with patch("psutil.Process") as mock_process_class:
            mock_process = Mock()
            mock_process.is_running.return_value = True
            mock_process.status.return_value = psutil.STATUS_STOPPED
            mock_process_class.return_value = mock_process

            result = process_check.check(sample_deployment.deployment_id)

            assert result.status == HealthStatus.UNHEALTHY
            assert "stopped" in result.message.lower()

    def test_not_running_process(self, process_manager_mock, sample_deployment):
        """Test process that is_running() returns False."""
        process_check = ProcessHealthCheck(process_manager_mock)
        process_check.initialize()

        with patch("psutil.Process") as mock_process_class:
            mock_process = Mock()
            mock_process.is_running.return_value = False
            mock_process_class.return_value = mock_process

            result = process_check.check(sample_deployment.deployment_id)

            assert result.status == HealthStatus.UNHEALTHY
            assert "not running" in result.message

    def test_no_such_process(self, process_manager_mock, sample_deployment):
        """Test process that no longer exists."""
        process_check = ProcessHealthCheck(process_manager_mock)
        process_check.initialize()

        with patch("psutil.Process") as mock_process_class:
            mock_process_class.side_effect = psutil.NoSuchProcess(12345)

            result = process_check.check(sample_deployment.deployment_id)

            assert result.status == HealthStatus.UNHEALTHY
            assert "no longer exists" in result.message

    def test_access_denied(self, process_manager_mock, sample_deployment):
        """Test process with access denied."""
        process_check = ProcessHealthCheck(process_manager_mock)
        process_check.initialize()

        with patch("psutil.Process") as mock_process_class:
            mock_process_class.side_effect = psutil.AccessDenied(12345)

            result = process_check.check(sample_deployment.deployment_id)

            assert result.status == HealthStatus.UNKNOWN
            assert "Cannot access" in result.message

    def test_unresponsive_process(self, process_manager_mock, sample_deployment):
        """Test detection of unresponsive process."""
        process_check = ProcessHealthCheck(process_manager_mock)
        process_check.initialize()

        with patch("psutil.Process") as mock_process_class:
            mock_process = Mock()
            mock_process.is_running.return_value = True
            mock_process.status.return_value = psutil.STATUS_RUNNING
            # cpu_percent(interval=X) is called with argument, so use Mock(return_value=...)
            mock_process.cpu_percent = Mock(return_value=0.0)
            mock_process_class.return_value = mock_process

            result = process_check.check(
                sample_deployment.deployment_id,
                check_responsiveness=True,
            )

            # Process with 0% CPU and RUNNING status might be unresponsive
            assert result.status == HealthStatus.DEGRADED
            assert "unresponsive" in result.message.lower()

    def test_deployment_not_found(self, process_manager_mock):
        """Test check with non-existent deployment."""
        process_check = ProcessHealthCheck(process_manager_mock)
        process_check.initialize()

        with pytest.raises(ValueError, match="Deployment not found"):
            process_check.check("non-existent-deployment")


# ============================================================================
# Resource Health Check Tests
# ============================================================================


class TestResourceHealthCheck:
    """Test suite for ResourceHealthCheck."""

    def test_initialization(self, process_manager_mock):
        """Test health check initialization."""
        resource_check = ResourceHealthCheck(process_manager_mock)
        assert resource_check.initialize()
        assert resource_check.is_initialized
        assert resource_check.get_check_type() == "resource"

    def test_healthy_resources(self, process_manager_mock, sample_deployment):
        """Test healthy resource usage."""
        resource_check = ResourceHealthCheck(process_manager_mock)
        resource_check.initialize()

        with patch("psutil.Process") as mock_process_class:
            mock_process = Mock()
            # cpu_percent(interval=X) is called with argument, so use Mock(return_value=...)
            mock_process.cpu_percent = Mock(return_value=25.0)  # Below threshold
            mock_memory_info = Mock()
            mock_memory_info.rss = 100 * 1024 * 1024  # 100MB
            mock_process.memory_info.return_value = mock_memory_info
            mock_process.num_threads.return_value = 10
            mock_process.num_fds = Mock(return_value=50)  # Unix only - file descriptors
            mock_process.net_connections.return_value = []
            mock_process_class.return_value = mock_process

            result = resource_check.check(sample_deployment.deployment_id)

            assert result.status == HealthStatus.HEALTHY
            assert "within normal limits" in result.message
            assert result.details["cpu_percent"] == 25.0
            assert result.details["memory_mb"] == 100.0

    def test_high_cpu_usage(self, process_manager_mock, sample_deployment):
        """Test detection of high CPU usage."""
        resource_check = ResourceHealthCheck(process_manager_mock)
        resource_check.initialize()

        with patch("psutil.Process") as mock_process_class:
            mock_process = Mock()
            # cpu_percent(interval=X) is called with argument, so use Mock(return_value=...)
            mock_process.cpu_percent = Mock(return_value=95.0)  # Above threshold
            mock_memory_info = Mock()
            mock_memory_info.rss = 100 * 1024 * 1024
            mock_process.memory_info.return_value = mock_memory_info
            mock_process.num_threads.return_value = 10
            mock_process.num_fds = Mock(return_value=50)  # Unix only - file descriptors
            mock_process.net_connections.return_value = []
            mock_process_class.return_value = mock_process

            result = resource_check.check(
                sample_deployment.deployment_id,
                cpu_threshold=80.0,
            )

            assert result.status == HealthStatus.DEGRADED
            assert "High CPU usage" in result.message
            assert result.details["cpu_percent"] == 95.0

    def test_high_memory_usage(self, process_manager_mock, sample_deployment):
        """Test detection of high memory usage."""
        resource_check = ResourceHealthCheck(process_manager_mock)
        resource_check.initialize()

        with patch("psutil.Process") as mock_process_class:
            mock_process = Mock()
            # cpu_percent(interval=X) is called with argument, so use Mock(return_value=...)
            mock_process.cpu_percent = Mock(return_value=25.0)
            mock_memory_info = Mock()
            mock_memory_info.rss = 600 * 1024 * 1024  # 600MB
            mock_process.memory_info.return_value = mock_memory_info
            mock_process.num_threads.return_value = 10
            mock_process.num_fds = Mock(return_value=50)  # Unix only - file descriptors
            mock_process.net_connections.return_value = []
            mock_process_class.return_value = mock_process

            result = resource_check.check(
                sample_deployment.deployment_id,
                memory_threshold_mb=500.0,
            )

            assert result.status == HealthStatus.DEGRADED
            assert "High memory usage" in result.message
            assert result.details["memory_mb"] == 600.0

    def test_high_thread_count(self, process_manager_mock, sample_deployment):
        """Test detection of high thread count."""
        resource_check = ResourceHealthCheck(process_manager_mock)
        resource_check.initialize()

        with patch("psutil.Process") as mock_process_class:
            mock_process = Mock()
            # cpu_percent(interval=X) is called with argument, so use Mock(return_value=...)
            mock_process.cpu_percent = Mock(return_value=25.0)
            mock_memory_info = Mock()
            mock_memory_info.rss = 100 * 1024 * 1024
            mock_process.memory_info.return_value = mock_memory_info
            mock_process.num_threads.return_value = 150  # High thread count
            mock_process.num_fds = Mock(return_value=50)  # Unix only - file descriptors
            mock_process.net_connections.return_value = []
            mock_process_class.return_value = mock_process

            result = resource_check.check(
                sample_deployment.deployment_id,
                thread_threshold=100,
            )

            assert result.status == HealthStatus.DEGRADED
            assert "High thread count" in result.message
            assert result.details["num_threads"] == 150

    def test_connection_tracking(self, process_manager_mock, sample_deployment):
        """Test network connection tracking."""
        resource_check = ResourceHealthCheck(process_manager_mock)
        resource_check.initialize()

        with patch("psutil.Process") as mock_process_class:
            mock_process = Mock()
            # cpu_percent(interval=X) is called with argument, so use Mock(return_value=...)
            mock_process.cpu_percent = Mock(return_value=25.0)
            mock_memory_info = Mock()
            mock_memory_info.rss = 100 * 1024 * 1024
            mock_process.memory_info.return_value = mock_memory_info
            mock_process.num_threads.return_value = 10
            mock_process.num_fds = Mock(return_value=50)  # Unix only - file descriptors

            # Mock connections
            mock_conn1 = Mock()
            mock_conn1.status = "ESTABLISHED"
            mock_conn2 = Mock()
            mock_conn2.status = "ESTABLISHED"
            mock_conn3 = Mock()
            mock_conn3.status = "LISTEN"
            mock_process.net_connections.return_value = [
                mock_conn1,
                mock_conn2,
                mock_conn3,
            ]

            mock_process_class.return_value = mock_process

            result = resource_check.check(sample_deployment.deployment_id)

            assert result.status == HealthStatus.HEALTHY
            assert result.details["num_connections"] == 3
            assert result.details["connection_states"]["ESTABLISHED"] == 2
            assert result.details["connection_states"]["LISTEN"] == 1

    def test_multiple_resource_issues(self, process_manager_mock, sample_deployment):
        """Test detection of multiple resource issues."""
        resource_check = ResourceHealthCheck(process_manager_mock)
        resource_check.initialize()

        with patch("psutil.Process") as mock_process_class:
            mock_process = Mock()
            # cpu_percent(interval=X) is called with argument, so use Mock(return_value=...)
            mock_process.cpu_percent = Mock(return_value=95.0)  # High CPU
            mock_memory_info = Mock()
            mock_memory_info.rss = 600 * 1024 * 1024  # High memory
            mock_process.memory_info.return_value = mock_memory_info
            mock_process.num_threads.return_value = 150  # High threads
            mock_process.num_fds = Mock(return_value=50)  # Unix only - file descriptors
            mock_process.net_connections.return_value = []
            mock_process_class.return_value = mock_process

            result = resource_check.check(sample_deployment.deployment_id)

            assert result.status == HealthStatus.DEGRADED
            assert "High CPU usage" in result.message
            assert "High memory usage" in result.message
            assert "High thread count" in result.message

    def test_no_such_process(self, process_manager_mock, sample_deployment):
        """Test resource check on non-existent process."""
        resource_check = ResourceHealthCheck(process_manager_mock)
        resource_check.initialize()

        with patch("psutil.Process") as mock_process_class:
            mock_process_class.side_effect = psutil.NoSuchProcess(12345)

            result = resource_check.check(sample_deployment.deployment_id)

            assert result.status == HealthStatus.UNHEALTHY
            assert "no longer exists" in result.message

    def test_deployment_not_found(self, process_manager_mock):
        """Test check with non-existent deployment."""
        resource_check = ResourceHealthCheck(process_manager_mock)
        resource_check.initialize()

        with pytest.raises(ValueError, match="Deployment not found"):
            resource_check.check("non-existent-deployment")
