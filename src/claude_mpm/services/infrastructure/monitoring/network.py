"""Network health monitoring service.

Monitors network connectivity, port availability, and socket health.
"""

import socket
from typing import Dict, List, Optional

from .base import BaseMonitoringService, HealthMetric, HealthStatus


class NetworkHealthService(BaseMonitoringService):
    """Service for monitoring network health and connectivity.

    Monitors:
    - Port availability and binding
    - Socket creation capability
    - Network interface status
    - Connection health to specified endpoints
    """

    def __init__(self, default_timeout: float = 1.0):
        """Initialize network health service.

        Args:
            default_timeout: Default connection timeout in seconds
        """
        super().__init__("NetworkHealth")
        self.default_timeout = default_timeout
        self.monitored_endpoints: List[Dict[str, any]] = []

    def add_endpoint(
        self,
        host: str,
        port: int,
        name: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        """Add an endpoint to monitor.

        Args:
            host: Host address to monitor
            port: Port number to monitor
            name: Optional name for the endpoint
            timeout: Optional custom timeout for this endpoint
        """
        endpoint = {
            "host": host,
            "port": port,
            "name": name or f"{host}:{port}",
            "timeout": timeout or self.default_timeout,
        }
        self.monitored_endpoints.append(endpoint)
        self.logger.info(f"Added endpoint for monitoring: {endpoint['name']}")

    async def check_health(self) -> List[HealthMetric]:
        """Check network health for all configured endpoints."""
        metrics = []

        # Check socket creation capability
        metrics.extend(self._check_socket_creation())

        # Check all monitored endpoints
        for endpoint in self.monitored_endpoints:
            metrics.extend(
                self._check_endpoint(
                    endpoint["host"],
                    endpoint["port"],
                    endpoint["name"],
                    endpoint["timeout"],
                )
            )

        # Check localhost connectivity (always check)
        if not any(e["host"] == "localhost" for e in self.monitored_endpoints):
            metrics.extend(
                self._check_endpoint("localhost", 8765, "localhost_default", 0.5)
            )

        return metrics

    def _check_socket_creation(self) -> List[HealthMetric]:
        """Check if we can create sockets (resource availability)."""
        metrics = []
        try:
            test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_sock.close()
            metrics.append(
                HealthMetric(
                    name="socket_creation",
                    value=True,
                    status=HealthStatus.HEALTHY,
                    message="Socket creation successful",
                )
            )
        except Exception as e:
            metrics.append(
                HealthMetric(
                    name="socket_creation",
                    value=False,
                    status=HealthStatus.CRITICAL,
                    message=f"Failed to create socket: {e}",
                )
            )
        return metrics

    def _check_endpoint(
        self,
        host: str,
        port: int,
        name: str,
        timeout: float,
    ) -> List[HealthMetric]:
        """Check connectivity to a specific endpoint.

        Args:
            host: Host to check
            port: Port to check
            name: Endpoint name for metrics
            timeout: Connection timeout

        Returns:
            List of health metrics for the endpoint
        """
        metrics = []
        metric_name = f"port_accessible_{name}"

        try:
            # Try to connect to the port
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()

            if result == 0:
                metrics.append(
                    HealthMetric(
                        name=metric_name,
                        value=True,
                        status=HealthStatus.HEALTHY,
                        message=f"Port {port} is accessible on {host}",
                    )
                )
            else:
                # Determine if this is critical or warning based on endpoint type
                status = (
                    HealthStatus.WARNING
                    if "optional" in name.lower()
                    else HealthStatus.CRITICAL
                )
                metrics.append(
                    HealthMetric(
                        name=metric_name,
                        value=False,
                        status=status,
                        message=f"Port {port} is not accessible on {host} (error: {result})",
                    )
                )
        except socket.timeout:
            metrics.append(
                HealthMetric(
                    name=metric_name,
                    value=False,
                    status=HealthStatus.WARNING,
                    message=f"Connection to {host}:{port} timed out after {timeout}s",
                )
            )
        except Exception as e:
            metrics.append(
                HealthMetric(
                    name=metric_name,
                    value=False,
                    status=HealthStatus.UNKNOWN,
                    message=f"Error checking port accessibility: {e}",
                )
            )

        return metrics

    def check_port_available(self, port: int, host: str = "0.0.0.0") -> bool:
        """Check if a port is available for binding.

        Args:
            port: Port number to check
            host: Host interface to check

        Returns:
            True if port is available for binding
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind((host, port))
                return True
        except OSError:
            return False

    def scan_port_range(
        self,
        start_port: int,
        end_port: int,
        host: str = "0.0.0.0",
    ) -> List[int]:
        """Scan a range of ports to find available ones.

        Args:
            start_port: Starting port number
            end_port: Ending port number (inclusive)
            host: Host interface to check

        Returns:
            List of available port numbers
        """
        available_ports = []
        for port in range(start_port, end_port + 1):
            if self.check_port_available(port, host):
                available_ports.append(port)
        return available_ports
