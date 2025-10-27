"""
Crash Detector for Claude MPM Framework
========================================

WHY: Detects process crashes and failures by monitoring health status changes,
process exits, and zombie states. Integrates with HealthCheckManager to receive
real-time status updates.

DESIGN DECISION: Uses callback-based architecture to receive health status
changes from HealthCheckManager. Tracks crash history per deployment to
enable pattern detection and intelligent restart policies.

ARCHITECTURE:
- Subscribes to HealthCheckManager status change callbacks
- Detects crashes when status transitions to UNHEALTHY
- Tracks crash count per deployment
- Invokes registered crash callbacks when crash detected

USAGE:
    crash_detector = CrashDetector(health_manager)
    crash_detector.register_crash_callback(handle_crash)
    crash_detector.start_monitoring(deployment_id)
"""

import threading
from collections import defaultdict
from typing import Callable, Dict, List, Set

from claude_mpm.core.enums import HealthStatus
from claude_mpm.services.core.base import SyncBaseService
from claude_mpm.services.core.interfaces.health import IHealthCheckManager
from claude_mpm.services.core.interfaces.restart import ICrashDetector


class CrashDetector(SyncBaseService, ICrashDetector):
    """
    Detects process crashes via health status monitoring.

    WHY: Provides automated crash detection by monitoring health status
    changes. Enables reactive restart policies based on crash events.

    Thread Safety: All public methods are thread-safe with proper locking.
    """

    def __init__(self, health_manager: IHealthCheckManager):
        """
        Initialize crash detector.

        Args:
            health_manager: Health check manager for status monitoring
        """
        super().__init__("CrashDetector")
        self.health_manager = health_manager
        self._lock = threading.Lock()

        # Deployments being monitored
        self._monitored_deployments: Set[str] = set()

        # Last known health status per deployment
        self._last_health_status: Dict[str, HealthStatus] = {}

        # Crash count per deployment
        self._crash_count: Dict[str, int] = defaultdict(int)

        # Crash callbacks: List of functions called with (deployment_id, reason)
        self._crash_callbacks: List[Callable[[str, str], None]] = []

    def initialize(self) -> bool:
        """
        Initialize the crash detector.

        Returns:
            True if initialization successful
        """
        self.logger.info("Initializing CrashDetector")

        # Register with health manager to receive status change callbacks
        self.health_manager.register_status_callback(self._on_health_status_change)

        self.logger.info("CrashDetector initialized successfully")
        return True

    def register_crash_callback(self, callback: Callable[[str, str], None]) -> None:
        """
        Register a callback to be invoked when a crash is detected.

        Args:
            callback: Function called with (deployment_id, reason)
        """
        with self._lock:
            self._crash_callbacks.append(callback)
            callback_name = getattr(callback, "__name__", repr(callback))
            self.logger.debug(f"Registered crash callback: {callback_name}")

    def start_monitoring(self, deployment_id: str) -> None:
        """
        Start monitoring a deployment for crashes.

        Args:
            deployment_id: Unique deployment identifier

        Raises:
            ValueError: If deployment_id not found
        """
        with self._lock:
            self._monitored_deployments.add(deployment_id)
            self.logger.info(
                f"Started crash monitoring for deployment: {deployment_id}"
            )

            # Get initial health status
            try:
                health = self.health_manager.check_health(deployment_id)
                self._last_health_status[deployment_id] = health.overall_status
                self.logger.debug(
                    f"Initial health status for {deployment_id}: {health.overall_status.value}"
                )
            except Exception as e:
                self.logger.warning(
                    f"Failed to get initial health status for {deployment_id}: {e}"
                )
                self._last_health_status[deployment_id] = HealthStatus.UNKNOWN

    def stop_monitoring(self, deployment_id: str) -> None:
        """
        Stop monitoring a deployment.

        Args:
            deployment_id: Unique deployment identifier
        """
        with self._lock:
            self._monitored_deployments.discard(deployment_id)
            self._last_health_status.pop(deployment_id, None)
            self.logger.info(
                f"Stopped crash monitoring for deployment: {deployment_id}"
            )

    def is_monitoring(self, deployment_id: str) -> bool:
        """
        Check if a deployment is being monitored.

        Args:
            deployment_id: Unique deployment identifier

        Returns:
            True if deployment is being monitored
        """
        with self._lock:
            return deployment_id in self._monitored_deployments

    def get_crash_count(self, deployment_id: str) -> int:
        """
        Get the number of crashes detected for a deployment.

        Args:
            deployment_id: Unique deployment identifier

        Returns:
            Number of crashes detected
        """
        with self._lock:
            return self._crash_count.get(deployment_id, 0)

    def reset_crash_count(self, deployment_id: str) -> None:
        """
        Reset crash count for a deployment.

        WHY: Allows manual intervention to clear crash history.

        Args:
            deployment_id: Unique deployment identifier
        """
        with self._lock:
            self._crash_count[deployment_id] = 0
            self.logger.debug(f"Reset crash count for deployment: {deployment_id}")

    def shutdown(self) -> bool:
        """
        Shutdown the crash detector.

        Returns:
            True if shutdown successful
        """
        with self._lock:
            self._monitored_deployments.clear()
            self._last_health_status.clear()
            self._crash_count.clear()
            self._crash_callbacks.clear()
        self.logger.info("CrashDetector shutdown successfully")
        return True

    def _on_health_status_change(
        self, deployment_id: str, old_status: HealthStatus, new_status: HealthStatus
    ) -> None:
        """
        Handle health status changes from HealthCheckManager.

        WHY: Callback invoked by HealthCheckManager when status changes.
        Detects crashes when status transitions to UNHEALTHY.

        Args:
            deployment_id: Unique deployment identifier
            old_status: Previous health status
            new_status: New health status
        """
        with self._lock:
            # Only process if we're monitoring this deployment
            if deployment_id not in self._monitored_deployments:
                return

            # Update last known status
            self._last_health_status[deployment_id] = new_status

            # Detect crash: transition from operational to UNHEALTHY
            if old_status.is_operational() and new_status.is_critical():
                self._handle_crash(
                    deployment_id, "Health status transitioned to UNHEALTHY"
                )

            # Also detect: transition from UNKNOWN to UNHEALTHY (process died)
            elif (
                old_status == HealthStatus.UNKNOWN
                and new_status == HealthStatus.UNHEALTHY
            ):
                self._handle_crash(deployment_id, "Process became unhealthy")

    def _handle_crash(self, deployment_id: str, reason: str) -> None:
        """
        Handle detected crash.

        WHY: Increments crash count and invokes all registered callbacks.

        Args:
            deployment_id: Unique deployment identifier
            reason: Reason for crash detection
        """
        # Increment crash count
        self._crash_count[deployment_id] += 1
        crash_count = self._crash_count[deployment_id]

        self.logger.warning(
            f"Crash detected for deployment {deployment_id} "
            f"(count: {crash_count}): {reason}"
        )

        # Invoke all crash callbacks
        for callback in self._crash_callbacks:
            try:
                callback(deployment_id, reason)
            except Exception as e:
                self.logger.error(
                    f"Error invoking crash callback {callback.__name__}: {e}",
                    exc_info=True,
                )


__all__ = ["CrashDetector"]
