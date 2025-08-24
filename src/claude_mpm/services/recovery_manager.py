"""Automatic recovery manager for claude-mpm Socket.IO server.

This module provides comprehensive recovery mechanisms including:
- Circuit breaker pattern to prevent restart loops
- Configurable recovery strategies
- Graceful restart and recovery procedures
- Recovery event logging and notifications
- Integration with health monitoring system

Design Principles:
- Prevention of restart loops through circuit breaker
- Graduated recovery responses based on failure severity
- Comprehensive logging for recovery events
- Configurable recovery policies and thresholds
- Integration with existing service lifecycle
"""

import asyncio
import logging
import os
import signal
import time
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from claude_mpm.core.constants import PerformanceConfig, RetryConfig

from .infrastructure.monitoring import HealthCheckResult, HealthStatus


class RecoveryAction(Enum):
    """Types of recovery actions that can be performed."""

    NONE = "none"
    LOG_WARNING = "log_warning"
    CLEAR_CONNECTIONS = "clear_connections"
    RESTART_SERVICE = "restart_service"
    EMERGENCY_STOP = "emergency_stop"


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Recovery blocked due to failures
    HALF_OPEN = "half_open"  # Testing if recovery is working


@dataclass
class RecoveryEvent:
    """Recovery event record."""

    timestamp: float
    action: RecoveryAction
    trigger: str
    health_status: HealthStatus
    success: bool
    duration_ms: float
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert recovery event to dictionary."""
        return {
            "timestamp": self.timestamp,
            "timestamp_iso": datetime.fromtimestamp(
                self.timestamp, timezone.utc
            ).isoformat(),
            "action": self.action.value,
            "trigger": self.trigger,
            "health_status": self.health_status.value,
            "success": self.success,
            "duration_ms": self.duration_ms,
            "error_message": self.error_message,
        }


class RecoveryStrategy(ABC):
    """Abstract base class for recovery strategies."""

    @abstractmethod
    def should_recover(self, health_result: HealthCheckResult) -> bool:
        """Determine if recovery should be triggered based on health result."""

    @abstractmethod
    def get_recovery_action(self, health_result: HealthCheckResult) -> RecoveryAction:
        """Determine the appropriate recovery action."""

    @abstractmethod
    def get_name(self) -> str:
        """Get the name of this recovery strategy."""


class GradedRecoveryStrategy(RecoveryStrategy):
    """Recovery strategy with graduated response based on health status and history.

    Recovery actions are escalated based on:
    - Current health status severity
    - Number of recent failures
    - Time since last recovery attempt
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize graded recovery strategy.

        Args:
            config: Configuration dictionary for recovery thresholds
        """
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.GradedRecoveryStrategy")

        # Configuration with defaults
        self.warning_threshold = self.config.get("warning_threshold", 2)
        self.critical_threshold = self.config.get(
            "critical_threshold", RetryConfig.CRITICAL_THRESHOLD
        )
        self.failure_window_seconds = self.config.get(
            "failure_window_seconds", RetryConfig.FAILURE_WINDOW
        )
        self.min_recovery_interval = self.config.get(
            "min_recovery_interval", RetryConfig.MIN_RECOVERY_INTERVAL
        )

        # Track recent failures
        self.recent_failures: deque = deque(maxlen=10)
        self.last_recovery_time = 0

    def get_name(self) -> str:
        return "graded_recovery"

    def should_recover(self, health_result: HealthCheckResult) -> bool:
        """Determine if recovery should be triggered."""
        current_time = time.time()

        # Don't trigger recovery too frequently
        if current_time - self.last_recovery_time < self.min_recovery_interval:
            self.logger.debug("Recovery suppressed due to min interval")
            return False

        # Check current health status
        if health_result.overall_status in [HealthStatus.CRITICAL]:
            return True

        if health_result.overall_status == HealthStatus.WARNING:
            # Count recent warnings in time window
            cutoff_time = current_time - self.failure_window_seconds
            recent_warnings = [
                event for event in self.recent_failures if event >= cutoff_time
            ]

            if len(recent_warnings) >= self.warning_threshold:
                return True

        return False

    def get_recovery_action(self, health_result: HealthCheckResult) -> RecoveryAction:
        """Determine the appropriate recovery action based on health status."""
        current_time = time.time()

        # Count recent failures
        cutoff_time = current_time - self.failure_window_seconds
        recent_failures = [
            event for event in self.recent_failures if event >= cutoff_time
        ]

        failure_count = len(recent_failures)

        # Record this failure
        if health_result.overall_status in [
            HealthStatus.WARNING,
            HealthStatus.CRITICAL,
        ]:
            self.recent_failures.append(current_time)

        # Determine action based on status and failure history
        if health_result.overall_status == HealthStatus.CRITICAL:
            if failure_count >= 3:
                return RecoveryAction.EMERGENCY_STOP
            if failure_count >= 2:
                return RecoveryAction.RESTART_SERVICE
            return RecoveryAction.CLEAR_CONNECTIONS

        if health_result.overall_status == HealthStatus.WARNING:
            if failure_count >= self.warning_threshold:
                return RecoveryAction.CLEAR_CONNECTIONS
            return RecoveryAction.LOG_WARNING

        return RecoveryAction.NONE


class CircuitBreaker:
    """Circuit breaker to prevent recovery loops and cascading failures.

    Implements the circuit breaker pattern to:
    - Prevent excessive recovery attempts
    - Allow time for systems to stabilize
    - Gradually re-enable recovery after failures
    """

    def __init__(
        self,
        failure_threshold: int = RetryConfig.FAILURE_THRESHOLD,
        timeout_seconds: int = RetryConfig.CIRCUIT_TIMEOUT,
        success_threshold: int = RetryConfig.SUCCESS_THRESHOLD,
    ):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout_seconds: Time to wait in OPEN state before trying HALF_OPEN
            success_threshold: Number of successes needed in HALF_OPEN to close circuit
        """
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.success_threshold = success_threshold

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
        self.state_change_time = time.time()

        self.logger = logging.getLogger(f"{__name__}.CircuitBreaker")
        self.logger.info(
            f"Circuit breaker initialized: failure_threshold={failure_threshold}, "
            f"timeout={timeout_seconds}s, success_threshold={success_threshold}"
        )

    def can_proceed(self) -> bool:
        """Check if recovery operations can proceed."""
        current_time = time.time()

        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if timeout has elapsed
            if current_time - self.last_failure_time >= self.timeout_seconds:
                self._transition_to_half_open()
                return True
            return False

        return self.state == CircuitState.HALF_OPEN

    def record_success(self) -> None:
        """Record a successful recovery operation."""
        if self.state == CircuitState.CLOSED:
            # Reset failure count on success in normal state
            self.failure_count = 0

        elif self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            self.logger.debug(
                f"Circuit breaker success count: {self.success_count}/{self.success_threshold}"
            )

            if self.success_count >= self.success_threshold:
                self._transition_to_closed()

    def record_failure(self) -> None:
        """Record a failed recovery operation."""
        current_time = time.time()
        self.last_failure_time = current_time

        if self.state == CircuitState.CLOSED:
            self.failure_count += 1
            self.logger.warning(
                f"Circuit breaker failure count: {self.failure_count}/{self.failure_threshold}"
            )

            if self.failure_count >= self.failure_threshold:
                self._transition_to_open()

        elif self.state == CircuitState.HALF_OPEN:
            # Failure in half-open state goes back to open
            self._transition_to_open()

    def _transition_to_open(self) -> None:
        """Transition circuit to OPEN state."""
        self.state = CircuitState.OPEN
        self.state_change_time = time.time()
        self.success_count = 0
        self.logger.warning(
            f"Circuit breaker OPENED due to {self.failure_count} failures. "
            f"Recovery blocked for {self.timeout_seconds} seconds."
        )

    def _transition_to_half_open(self) -> None:
        """Transition circuit to HALF_OPEN state."""
        self.state = CircuitState.HALF_OPEN
        self.state_change_time = time.time()
        self.success_count = 0
        self.logger.info(
            "Circuit breaker transitioned to HALF_OPEN. Testing recovery..."
        )

    def _transition_to_closed(self) -> None:
        """Transition circuit to CLOSED state."""
        self.state = CircuitState.CLOSED
        self.state_change_time = time.time()
        self.failure_count = 0
        self.success_count = 0
        self.logger.info("Circuit breaker CLOSED. Normal recovery operations resumed.")

    def get_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status."""
        current_time = time.time()
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
            "state_change_time": self.state_change_time,
            "time_in_current_state": current_time - self.state_change_time,
            "can_proceed": self.can_proceed(),
            "config": {
                "failure_threshold": self.failure_threshold,
                "timeout_seconds": self.timeout_seconds,
                "success_threshold": self.success_threshold,
            },
        }


class RecoveryManager:
    """Advanced recovery manager with circuit breaker and configurable strategies.

    Provides comprehensive recovery capabilities including:
    - Health-based recovery triggering
    - Circuit breaker protection
    - Multiple recovery strategies
    - Recovery event logging and history
    - Integration with service lifecycle
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, server_instance=None):
        """Initialize recovery manager.

        Args:
            config: Configuration dictionary for recovery settings
            server_instance: Reference to the Socket.IO server instance
        """
        self.config = config or {}
        self.server_instance = server_instance
        self.logger = logging.getLogger(f"{__name__}.RecoveryManager")

        # Configuration with defaults
        self.enabled = self.config.get("enabled", True)
        self.check_interval = self.config.get("check_interval", 60)
        self.max_recovery_attempts = self.config.get("max_recovery_attempts", 5)
        self.recovery_timeout = self.config.get("recovery_timeout", 30)

        # Initialize circuit breaker
        circuit_config = self.config.get("circuit_breaker", {})
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=circuit_config.get(
                "failure_threshold", RetryConfig.FAILURE_THRESHOLD
            ),
            timeout_seconds=circuit_config.get(
                "timeout_seconds", RetryConfig.CIRCUIT_TIMEOUT
            ),
            success_threshold=circuit_config.get(
                "success_threshold", RetryConfig.SUCCESS_THRESHOLD
            ),
        )

        # Initialize recovery strategy
        strategy_config = self.config.get("strategy", {})
        self.recovery_strategy = GradedRecoveryStrategy(strategy_config)

        # Recovery event history
        self.recovery_history: deque = deque(maxlen=100)

        # Recovery state
        self.recovery_in_progress = False
        self.last_recovery_time = 0
        self.recovery_count = 0

        # Recovery callbacks
        self.recovery_callbacks: List[Callable[[RecoveryEvent], None]] = []

        # Statistics
        self.recovery_stats = {
            "total_recoveries": 0,
            "successful_recoveries": 0,
            "failed_recoveries": 0,
            "actions_performed": {action.value: 0 for action in RecoveryAction},
            "average_recovery_duration_ms": 0,
        }

        self.logger.info(
            f"Recovery manager initialized with strategy: {self.recovery_strategy.get_name()}"
        )

    def add_recovery_callback(self, callback: Callable[[RecoveryEvent], None]) -> None:
        """Add a callback to be notified of recovery events."""
        self.recovery_callbacks.append(callback)
        self.logger.debug(f"Added recovery callback: {callback.__name__}")

    def handle_health_result(
        self, health_result: HealthCheckResult
    ) -> Optional[RecoveryEvent]:
        """Handle health check result and trigger recovery if needed.

        Args:
            health_result: Health check result to evaluate

        Returns:
            RecoveryEvent if recovery was triggered, None otherwise
        """
        if not self.enabled:
            return None

        if self.recovery_in_progress:
            self.logger.debug("Recovery already in progress, skipping")
            return None

        # Check if recovery should be triggered
        if not self.recovery_strategy.should_recover(health_result):
            return None

        # Check circuit breaker
        if not self.circuit_breaker.can_proceed():
            self.logger.warning("Recovery suppressed by circuit breaker")
            return None

        # Determine recovery action
        action = self.recovery_strategy.get_recovery_action(health_result)

        if action == RecoveryAction.NONE:
            return None

        # Trigger recovery
        return asyncio.create_task(
            self._perform_recovery(action, health_result, "health_check")
        )

    async def _perform_recovery(
        self, action: RecoveryAction, health_result: HealthCheckResult, trigger: str
    ) -> RecoveryEvent:
        """Perform recovery action and record the event.

        Args:
            action: Recovery action to perform
            health_result: Health result that triggered recovery
            trigger: Description of what triggered the recovery

        Returns:
            RecoveryEvent record of the recovery attempt
        """
        if self.recovery_in_progress:
            raise RuntimeError("Recovery already in progress")

        self.recovery_in_progress = True
        start_time = time.time()
        success = False
        error_message = None

        try:
            self.logger.info(
                f"Starting recovery action: {action.value} (trigger: {trigger})"
            )

            if action == RecoveryAction.LOG_WARNING:
                success = await self._log_warning(health_result)
            elif action == RecoveryAction.CLEAR_CONNECTIONS:
                success = await self._clear_connections()
            elif action == RecoveryAction.RESTART_SERVICE:
                success = await self._restart_service()
            elif action == RecoveryAction.EMERGENCY_STOP:
                success = await self._emergency_stop()
            else:
                error_message = f"Unknown recovery action: {action}"
                self.logger.error(error_message)

        except Exception as e:
            error_message = f"Recovery action failed: {e}"
            self.logger.error(error_message)
            success = False

        finally:
            self.recovery_in_progress = False
            duration_ms = (time.time() - start_time) * PerformanceConfig.SECONDS_TO_MS

            # Create recovery event
            event = RecoveryEvent(
                timestamp=start_time,
                action=action,
                trigger=trigger,
                health_status=health_result.overall_status,
                success=success,
                duration_ms=duration_ms,
                error_message=error_message,
            )

            # Update statistics
            self._update_recovery_stats(event)

            # Record in circuit breaker
            if success:
                self.circuit_breaker.record_success()
            else:
                self.circuit_breaker.record_failure()

            # Store event
            self.recovery_history.append(event)
            self.last_recovery_time = start_time
            self.recovery_count += 1

            # Notify callbacks
            for callback in self.recovery_callbacks:
                try:
                    callback(event)
                except Exception as e:
                    self.logger.error(
                        f"Recovery callback {callback.__name__} failed: {e}"
                    )

            result_msg = "succeeded" if success else "failed"
            self.logger.info(
                f"Recovery action {action.value} {result_msg} in {duration_ms:.2f}ms"
            )

            return event

    async def _log_warning(self, health_result: HealthCheckResult) -> bool:
        """Log a warning about health issues."""
        try:
            warning_metrics = [
                m for m in health_result.metrics if m.status == HealthStatus.WARNING
            ]
            critical_metrics = [
                m for m in health_result.metrics if m.status == HealthStatus.CRITICAL
            ]

            self.logger.warning(
                f"Health warning detected: {len(warning_metrics)} warning metrics, "
                f"{len(critical_metrics)} critical metrics"
            )

            for metric in warning_metrics + critical_metrics:
                self.logger.warning(
                    f"  {metric.name}: {metric.value} ({metric.status.value}) - {metric.message}"
                )

            return True
        except Exception as e:
            self.logger.error(f"Failed to log warning: {e}")
            return False

    async def _clear_connections(self) -> bool:
        """Clear all client connections to reset connection state."""
        try:
            if not self.server_instance or not hasattr(self.server_instance, "sio"):
                self.logger.warning(
                    "No server instance available for connection clearing"
                )
                return False

            sio = self.server_instance.sio
            if not sio:
                self.logger.warning("Socket.IO instance not available")
                return False

            # Get current clients
            clients = (
                list(self.server_instance.clients)
                if hasattr(self.server_instance, "clients")
                else []
            )

            self.logger.info(f"Clearing {len(clients)} client connections")

            # Disconnect all clients
            for client_id in clients:
                try:
                    await sio.disconnect(client_id)
                except Exception as e:
                    self.logger.warning(f"Failed to disconnect client {client_id}: {e}")

            # Clear client tracking
            if hasattr(self.server_instance, "clients"):
                self.server_instance.clients.clear()
            if hasattr(self.server_instance, "client_versions"):
                self.server_instance.client_versions.clear()

            self.logger.info("Client connections cleared successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to clear connections: {e}")
            return False

    async def _restart_service(self) -> bool:
        """Restart the Socket.IO service."""
        try:
            if not self.server_instance:
                self.logger.error("No server instance available for restart")
                return False

            self.logger.info("Attempting graceful service restart")

            # Save current configuration
            getattr(self.server_instance, "host", "localhost")
            getattr(self.server_instance, "port", 8765)

            # Stop current server
            try:
                await self.server_instance._shutdown_async()
                self.logger.info("Server shutdown completed")
            except Exception as e:
                self.logger.warning(f"Error during shutdown: {e}")

            # Wait a moment for cleanup
            await asyncio.sleep(1)

            # Restart server
            await self.server_instance.start_async()
            self.logger.info("Server restart completed successfully")

            return True

        except Exception as e:
            self.logger.error(f"Failed to restart service: {e}")
            return False

    async def _emergency_stop(self) -> bool:
        """Perform emergency stop of the service."""
        try:
            self.logger.critical(
                "Performing emergency stop due to critical health issues"
            )

            if self.server_instance:
                try:
                    # Force immediate shutdown
                    await self.server_instance._shutdown_async()
                except Exception as e:
                    self.logger.error(f"Error during emergency shutdown: {e}")

            # Send termination signal to process
            try:
                os.kill(os.getpid(), signal.SIGTERM)
            except Exception as e:
                self.logger.error(f"Failed to send termination signal: {e}")
                return False

            return True

        except Exception as e:
            self.logger.error(f"Emergency stop failed: {e}")
            return False

    def _update_recovery_stats(self, event: RecoveryEvent) -> None:
        """Update recovery statistics with new event."""
        self.recovery_stats["total_recoveries"] += 1

        if event.success:
            self.recovery_stats["successful_recoveries"] += 1
        else:
            self.recovery_stats["failed_recoveries"] += 1

        self.recovery_stats["actions_performed"][event.action.value] += 1

        # Update average duration
        total_recoveries = self.recovery_stats["total_recoveries"]
        current_avg = self.recovery_stats["average_recovery_duration_ms"]
        self.recovery_stats["average_recovery_duration_ms"] = (
            current_avg * (total_recoveries - 1) + event.duration_ms
        ) / total_recoveries

    def get_recovery_status(self) -> Dict[str, Any]:
        """Get comprehensive recovery manager status."""
        return {
            "enabled": self.enabled,
            "recovery_in_progress": self.recovery_in_progress,
            "last_recovery_time": self.last_recovery_time,
            "recovery_count": self.recovery_count,
            "strategy": self.recovery_strategy.get_name(),
            "circuit_breaker": self.circuit_breaker.get_status(),
            "recovery_stats": dict(self.recovery_stats),
            "recent_recoveries": [
                event.to_dict() for event in list(self.recovery_history)[-10:]
            ],
            "config": {
                "check_interval": self.check_interval,
                "max_recovery_attempts": self.max_recovery_attempts,
                "recovery_timeout": self.recovery_timeout,
            },
        }

    def get_recovery_history(self, limit: Optional[int] = None) -> List[RecoveryEvent]:
        """Get recovery event history.

        Args:
            limit: Maximum number of events to return

        Returns:
            List of recovery events, newest first
        """
        history = list(self.recovery_history)
        history.reverse()  # Newest first

        if limit:
            history = history[:limit]

        return history

    def is_enabled(self) -> bool:
        """Check if recovery manager is enabled."""
        return self.enabled

    def enable(self) -> None:
        """Enable recovery manager."""
        self.enabled = True
        self.logger.info("Recovery manager enabled")

    def disable(self) -> None:
        """Disable recovery manager."""
        self.enabled = False
        self.logger.info("Recovery manager disabled")
