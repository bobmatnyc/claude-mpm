"""
HTTP Health Check for Claude MPM Framework
===========================================

WHY: Provides HTTP endpoint health monitoring with response time measurement,
status code validation, and timeout handling.

DESIGN DECISION: Uses requests library with configurable timeout and retry logic.
Supports custom headers and SSL/TLS validation.

ARCHITECTURE:
- Synchronous HTTP GET requests
- Response time measurement with time.perf_counter()
- Status code validation (2xx/3xx = healthy)
- Timeout and connection error handling
- Retry logic with exponential backoff

USAGE:
    http_check = HttpHealthCheck(process_manager)
    result = http_check.check(
        deployment_id="my-app",
        endpoint="http://localhost:3000/health",
        timeout=5.0
    )
"""

import time

import requests
from requests.exceptions import ConnectionError, RequestException, Timeout

from claude_mpm.core.enums import HealthStatus
from claude_mpm.services.core.base import SyncBaseService
from claude_mpm.services.core.interfaces.health import IHealthCheck
from claude_mpm.services.core.interfaces.process import ILocalProcessManager
from claude_mpm.services.core.models.health import HealthCheckResult


class HttpHealthCheck(SyncBaseService, IHealthCheck):
    """
    HTTP endpoint health check implementation.

    WHY: Validates that deployed services are accessible via HTTP and
    responding within acceptable timeframes.

    Thread Safety: Stateless, safe for concurrent execution.
    """

    def __init__(
        self,
        process_manager: ILocalProcessManager,
        default_timeout: float = 5.0,
        max_retries: int = 2,
    ):
        """
        Initialize HTTP health check.

        Args:
            process_manager: Process manager for deployment lookup
            default_timeout: Default timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        super().__init__("HttpHealthCheck")
        self.process_manager = process_manager
        self.default_timeout = default_timeout
        self.max_retries = max_retries

    def initialize(self) -> bool:
        """
        Initialize the health check.

        Returns:
            True if initialization successful
        """
        self._initialized = True
        self.log_info("HTTP health check initialized")
        return True

    def shutdown(self) -> None:
        """Shutdown health check (no resources to clean up)."""
        self._shutdown = True

    def get_check_type(self) -> str:
        """Get the check type identifier."""
        return "http"

    def check(self, deployment_id: str, **kwargs) -> HealthCheckResult:
        """
        Execute HTTP health check for a deployment.

        Args:
            deployment_id: Unique deployment identifier
            **kwargs: Optional parameters:
                - endpoint: HTTP endpoint URL (required)
                - timeout: Request timeout in seconds (default: 5.0)
                - headers: Custom HTTP headers
                - verify_ssl: Verify SSL certificates (default: True)
                - expected_status: Expected status code (default: 200)

        Returns:
            HealthCheckResult with check status and details

        Raises:
            ValueError: If deployment_id not found or endpoint not provided
        """
        # Validate deployment exists
        deployment = self.process_manager.state_manager.get_deployment(deployment_id)
        if not deployment:
            raise ValueError(f"Deployment not found: {deployment_id}")

        # Get endpoint from kwargs
        endpoint = kwargs.get("endpoint")
        if not endpoint:
            # Try to construct from deployment port
            if deployment.port:
                endpoint = f"http://localhost:{deployment.port}/health"
            else:
                return HealthCheckResult(
                    status=HealthStatus.UNKNOWN,
                    check_type=self.get_check_type(),
                    message="No HTTP endpoint configured for deployment",
                    details={"deployment_id": deployment_id},
                )

        # Get optional parameters
        timeout = kwargs.get("timeout", self.default_timeout)
        headers = kwargs.get("headers", {})
        verify_ssl = kwargs.get("verify_ssl", True)
        expected_status = kwargs.get("expected_status", 200)

        # Perform HTTP check with retries
        for attempt in range(self.max_retries + 1):
            try:
                start_time = time.perf_counter()
                response = requests.get(
                    endpoint, timeout=timeout, headers=headers, verify=verify_ssl
                )
                response_time = time.perf_counter() - start_time

                # Check status code
                if response.status_code == expected_status or (
                    200 <= response.status_code < 400
                ):
                    return HealthCheckResult(
                        status=HealthStatus.HEALTHY,
                        check_type=self.get_check_type(),
                        message="HTTP endpoint responding normally",
                        details={
                            "endpoint": endpoint,
                            "status_code": response.status_code,
                            "response_time_ms": round(response_time * 1000, 2),
                            "attempt": attempt + 1,
                        },
                    )
                return HealthCheckResult(
                    status=HealthStatus.DEGRADED,
                    check_type=self.get_check_type(),
                    message="HTTP endpoint returned unexpected status code",
                    details={
                        "endpoint": endpoint,
                        "status_code": response.status_code,
                        "expected_status": expected_status,
                        "response_time_ms": round(response_time * 1000, 2),
                    },
                )

            except Timeout:
                if attempt < self.max_retries:
                    self.log_debug(
                        f"HTTP check timeout for {deployment_id}, "
                        f"retrying (attempt {attempt + 1}/{self.max_retries})"
                    )
                    time.sleep(0.5 * (2**attempt))  # Exponential backoff
                    continue

                return HealthCheckResult(
                    status=HealthStatus.DEGRADED,
                    check_type=self.get_check_type(),
                    message=f"HTTP endpoint timeout after {self.max_retries + 1} attempts",
                    details={
                        "endpoint": endpoint,
                        "timeout_seconds": timeout,
                        "attempts": self.max_retries + 1,
                    },
                )

            except ConnectionError as e:
                if attempt < self.max_retries:
                    self.log_debug(
                        f"HTTP connection error for {deployment_id}, "
                        f"retrying (attempt {attempt + 1}/{self.max_retries})"
                    )
                    time.sleep(0.5 * (2**attempt))  # Exponential backoff
                    continue

                return HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    check_type=self.get_check_type(),
                    message="Cannot connect to HTTP endpoint",
                    details={
                        "endpoint": endpoint,
                        "error": str(e),
                        "attempts": self.max_retries + 1,
                    },
                )

            except RequestException as e:
                return HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    check_type=self.get_check_type(),
                    message="HTTP request failed",
                    details={"endpoint": endpoint, "error": str(e)},
                )

        # Should not reach here, but return unknown as fallback
        return HealthCheckResult(
            status=HealthStatus.UNKNOWN,
            check_type=self.get_check_type(),
            message="HTTP check completed with unknown result",
            details={"endpoint": endpoint},
        )


__all__ = ["HttpHealthCheck"]
