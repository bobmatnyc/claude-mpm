"""
Restart Manager for Claude MPM Framework
=========================================

WHY: Orchestrates the complete restart workflow including crash detection,
policy evaluation, process restart, and health verification.

DESIGN DECISION: Integrates all restart components (CrashDetector,
RestartPolicy, ProcessManager, HealthCheckManager) to provide automatic
and manual restart operations with proper verification.

ARCHITECTURE:
- Auto-restart workflow:
  1. CrashDetector detects crash → triggers callback
  2. RestartManager checks policy (max attempts, circuit breaker)
  3. Calculate and wait for backoff period
  4. Execute restart via ProcessManager
  5. Wait for health check verification
  6. Record attempt and update circuit breaker
- Manual restart: bypasses some policy checks
- Thread-safe operations with proper locking
- State persistence for restart history

USAGE:
    config = RestartConfig(max_attempts=5, circuit_breaker_threshold=3)
    restart_manager = RestartManager(
        process_manager=process_manager,
        health_manager=health_manager,
        crash_detector=crash_detector,
        restart_policy=restart_policy
    )

    # Enable auto-restart
    restart_manager.enable_auto_restart(deployment_id)

    # Manual restart
    success = restart_manager.restart_deployment(deployment_id, manual=True)
"""

import json
import threading
import time
from pathlib import Path
from typing import Optional, Set

from claude_mpm.core.enums import HealthStatus
from claude_mpm.services.core.base import SyncBaseService
from claude_mpm.services.core.interfaces.health import IHealthCheckManager
from claude_mpm.services.core.interfaces.process import ILocalProcessManager
from claude_mpm.services.core.interfaces.restart import (
    ICrashDetector,
    IRestartManager,
    IRestartPolicy,
)
from claude_mpm.services.core.models.restart import RestartHistory


class RestartManager(SyncBaseService, IRestartManager):
    """
    Orchestrates automatic and manual restart operations.

    WHY: Provides complete restart workflow by coordinating crash detection,
    policy evaluation, process restart, and health verification.

    Thread Safety: All public methods are thread-safe with proper locking.
    """

    def __init__(
        self,
        process_manager: ILocalProcessManager,
        health_manager: IHealthCheckManager,
        crash_detector: ICrashDetector,
        restart_policy: IRestartPolicy,
        state_dir: Optional[Path] = None,
    ):
        """
        Initialize restart manager.

        Args:
            process_manager: Process manager for restart operations
            health_manager: Health check manager for verification
            crash_detector: Crash detector for automatic restarts
            restart_policy: Restart policy for decision making
            state_dir: Directory for restart history persistence
        """
        super().__init__("RestartManager")
        self.process_manager = process_manager
        self.health_manager = health_manager
        self.crash_detector = crash_detector
        self.restart_policy = restart_policy

        # State persistence
        if state_dir is None:
            state_dir = Path.home() / ".claude-mpm"
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.state_dir / "restart-history.json"

        # Auto-restart tracking
        self._lock = threading.Lock()
        self._auto_restart_enabled: Set[str] = set()

        # In-progress restart tracking (prevent concurrent restarts)
        self._restart_in_progress: Set[str] = set()

    def initialize(self) -> bool:
        """
        Initialize the restart manager.

        Returns:
            True if initialization successful
        """
        self.logger.info("Initializing RestartManager")

        # Register crash callback
        self.crash_detector.register_crash_callback(self._on_crash_detected)

        # Load restart history from disk
        self._load_restart_history()

        self.logger.info("RestartManager initialized successfully")
        return True

    def enable_auto_restart(self, deployment_id: str) -> None:
        """
        Enable automatic restarts for a deployment.

        Args:
            deployment_id: Unique deployment identifier

        Raises:
            ValueError: If deployment_id not found
        """
        # Verify deployment exists
        deployment = self.process_manager.get_status(deployment_id)
        if deployment is None:
            raise ValueError(f"Deployment not found: {deployment_id}")

        with self._lock:
            if deployment_id in self._auto_restart_enabled:
                self.logger.debug(f"Auto-restart already enabled for {deployment_id}")
                return

            # Enable auto-restart
            self._auto_restart_enabled.add(deployment_id)

            # Start crash monitoring
            self.crash_detector.start_monitoring(deployment_id)

            self.logger.info(f"Enabled auto-restart for deployment: {deployment_id}")

    def disable_auto_restart(self, deployment_id: str) -> None:
        """
        Disable automatic restarts for a deployment.

        Args:
            deployment_id: Unique deployment identifier
        """
        with self._lock:
            self._auto_restart_enabled.discard(deployment_id)

            # Stop crash monitoring
            self.crash_detector.stop_monitoring(deployment_id)

            self.logger.info(f"Disabled auto-restart for deployment: {deployment_id}")

    def is_auto_restart_enabled(self, deployment_id: str) -> bool:
        """
        Check if auto-restart is enabled for a deployment.

        Args:
            deployment_id: Unique deployment identifier

        Returns:
            True if auto-restart is enabled
        """
        with self._lock:
            return deployment_id in self._auto_restart_enabled

    def restart_deployment(self, deployment_id: str, manual: bool = False) -> bool:
        """
        Restart a deployment (manual or automatic trigger).

        Args:
            deployment_id: Unique deployment identifier
            manual: If True, bypass circuit breaker check

        Returns:
            True if restart succeeded

        Raises:
            ValueError: If deployment_id not found
        """
        with self._lock:
            # Check if restart already in progress
            if deployment_id in self._restart_in_progress:
                self.logger.warning(
                    f"Restart already in progress for {deployment_id}, skipping"
                )
                return False

            # Mark restart in progress
            self._restart_in_progress.add(deployment_id)

        try:
            # Check restart policy (unless manual override)
            if not manual:
                if not self.restart_policy.should_restart(deployment_id):
                    self.logger.warning(
                        f"Restart policy blocked restart for {deployment_id}"
                    )
                    return False

            # Calculate and wait for backoff
            backoff = self.restart_policy.calculate_backoff(deployment_id)
            if backoff > 0:
                self.logger.info(
                    f"Waiting {backoff:.1f}s backoff before restarting {deployment_id}"
                )
                time.sleep(backoff)

            # Execute restart
            self.logger.info(f"Restarting deployment: {deployment_id}")
            try:
                new_deployment = self.process_manager.restart(deployment_id)

                # Wait for initial health check
                self.logger.debug(
                    f"Waiting for health check verification for {deployment_id}"
                )
                time.sleep(5)  # Brief wait for process to initialize

                # Verify health status
                health = self.health_manager.check_health(new_deployment.deployment_id)
                success = health.overall_status != HealthStatus.UNHEALTHY

                if success:
                    self.logger.info(
                        f"Restart succeeded for {deployment_id}, "
                        f"health status: {health.overall_status.value}"
                    )
                else:
                    self.logger.warning(
                        f"Restart completed but deployment unhealthy: {deployment_id}"
                    )

                # Record attempt
                failure_reason = (
                    None
                    if success
                    else f"Health check failed: {health.overall_status.value}"
                )
                self.restart_policy.record_restart_attempt(
                    deployment_id, success, failure_reason
                )

                # Persist restart history
                self._save_restart_history()

                return success

            except Exception as e:
                self.logger.error(
                    f"Restart failed for {deployment_id}: {e}", exc_info=True
                )

                # Record failed attempt
                self.restart_policy.record_restart_attempt(
                    deployment_id, success=False, failure_reason=str(e)
                )

                # Persist restart history
                self._save_restart_history()

                return False

        finally:
            # Clear in-progress flag
            with self._lock:
                self._restart_in_progress.discard(deployment_id)

    def get_restart_history(self, deployment_id: str) -> Optional[RestartHistory]:
        """
        Get restart history for a deployment.

        Args:
            deployment_id: Unique deployment identifier

        Returns:
            RestartHistory if found, None otherwise
        """
        return self.restart_policy.get_history(deployment_id)

    def clear_restart_history(self, deployment_id: str) -> None:
        """
        Clear restart history and reset circuit breaker.

        Args:
            deployment_id: Unique deployment identifier
        """
        self.restart_policy.reset_restart_history(deployment_id)
        self._save_restart_history()
        self.logger.info(f"Cleared restart history for deployment: {deployment_id}")

    def _on_crash_detected(self, deployment_id: str, reason: str) -> None:
        """
        Handle crash detection callback.

        WHY: Invoked by CrashDetector when a crash is detected.
        Triggers automatic restart if enabled.

        Args:
            deployment_id: Unique deployment identifier
            reason: Reason for crash detection
        """
        self.logger.warning(f"Crash detected for {deployment_id}: {reason}")

        # Check if auto-restart is enabled
        with self._lock:
            if deployment_id not in self._auto_restart_enabled:
                self.logger.debug(
                    f"Auto-restart not enabled for {deployment_id}, ignoring crash"
                )
                return

        # Trigger automatic restart
        self.logger.info(f"Triggering automatic restart for {deployment_id}")
        self.restart_deployment(deployment_id, manual=False)

    def _load_restart_history(self) -> None:
        """
        Load restart history from disk.

        WHY: Persists restart state across service restarts to maintain
        circuit breaker state and attempt counts.
        """
        if not self.history_file.exists():
            self.logger.debug("No restart history file found, starting fresh")
            return

        try:
            with self.history_file.open() as f:
                data = json.load(f)

            # Load history into restart policy
            for deployment_id, history_data in data.items():
                history = RestartHistory.from_dict(history_data)
                # Inject into restart policy's internal state
                if hasattr(self.restart_policy, "_history"):
                    self.restart_policy._history[deployment_id] = history

            self.logger.info(f"Loaded restart history for {len(data)} deployments")

        except Exception as e:
            self.logger.error(f"Failed to load restart history: {e}", exc_info=True)

    def _save_restart_history(self) -> None:
        """
        Save restart history to disk.

        WHY: Persists restart state to maintain circuit breaker and
        attempt counts across service restarts.
        """
        try:
            # Collect all restart histories from restart policy
            data = {}
            if hasattr(self.restart_policy, "_history"):
                for deployment_id, history in self.restart_policy._history.items():
                    data[deployment_id] = history.to_dict()

            # Write to disk
            with self.history_file.open("w") as f:
                json.dump(data, f, indent=2)

            self.logger.debug(f"Saved restart history for {len(data)} deployments")

        except Exception as e:
            self.logger.error(f"Failed to save restart history: {e}", exc_info=True)

    def shutdown(self) -> bool:
        """
        Shutdown the restart manager.

        Returns:
            True if shutdown successful
        """
        # Save restart history before shutdown
        self._save_restart_history()

        with self._lock:
            # Disable all auto-restarts
            for deployment_id in list(self._auto_restart_enabled):
                self.crash_detector.stop_monitoring(deployment_id)
            self._auto_restart_enabled.clear()
            self._restart_in_progress.clear()

        self.logger.info("RestartManager shutdown successfully")
        return True


__all__ = ["RestartManager"]
