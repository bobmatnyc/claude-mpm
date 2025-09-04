"""
Health Monitoring for Unified Monitor
=====================================

WHY: This module provides health monitoring for the unified monitor daemon.
It tracks system resources and service health to ensure stability.

DESIGN DECISIONS:
- Simple health monitoring without external dependencies
- Basic resource tracking and service health checks
- Configurable thresholds for alerts
"""

import threading
import time
from typing import Dict

from ....core.logging_config import get_logger


class HealthMonitor:
    """Health monitoring system for the unified monitor daemon."""

    def __init__(self, port: int = 8765):
        """Initialize health monitor.

        Args:
            port: Port to monitor for service health
        """
        self.port = port
        self.logger = get_logger(__name__)

        # Monitoring state
        self.running = False
        self.monitor_thread = None

        # Health metrics
        self.metrics = {
            "service_responsive": True,
            "last_check": time.time(),
            "uptime": 0.0,
            "error_count": 0,
        }

    def start(self):
        """Start health monitoring."""
        try:
            if self.running:
                self.logger.warning("Health monitor already running")
                return

            self.running = True
            self.monitor_thread = threading.Thread(
                target=self._monitor_loop, daemon=True
            )
            self.monitor_thread.start()

            self.logger.info("Health monitor started")

        except Exception as e:
            self.logger.error(f"Error starting health monitor: {e}")
            self.running = False

    def stop(self):
        """Stop health monitoring."""
        try:
            self.running = False

            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=5)

            self.logger.info("Health monitor stopped")

        except Exception as e:
            self.logger.error(f"Error stopping health monitor: {e}")

    def _monitor_loop(self):
        """Main monitoring loop."""
        start_time = time.time()

        while self.running:
            try:
                # Update metrics
                self.metrics["uptime"] = time.time() - start_time
                self.metrics["last_check"] = time.time()
                self.metrics["service_responsive"] = self._check_service_health()

                # Sleep before next check
                time.sleep(30)  # Check every 30 seconds

            except Exception as e:
                self.logger.error(f"Error in health monitoring loop: {e}")
                self.metrics["error_count"] += 1
                time.sleep(10)  # Shorter sleep on error

    def _check_service_health(self) -> bool:
        """Check if the service is responsive."""
        try:
            import socket

            # Try to connect to the service port
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)  # 5 second timeout
            result = sock.connect_ex(("localhost", self.port))
            sock.close()

            return result == 0

        except Exception as e:
            self.logger.debug(f"Service health check failed: {e}")
            return False

    def get_status(self) -> Dict:
        """Get current health status."""
        try:
            return {
                "monitoring": self.running,
                "healthy": self.metrics["service_responsive"],
                "metrics": self.metrics.copy(),
            }

        except Exception as e:
            self.logger.error(f"Error getting health status: {e}")
            return {"monitoring": False, "healthy": False, "error": str(e)}
