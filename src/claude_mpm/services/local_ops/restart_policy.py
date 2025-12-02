"""
Restart Policy for Claude MPM Framework
========================================

WHY: Implements intelligent restart policies with exponential backoff,
max attempts, and circuit breaker patterns to prevent restart loops.

DESIGN DECISION: Uses exponential backoff with configurable parameters
and circuit breaker state transitions (CLOSED → OPEN → HALF_OPEN).
Tracks restart history per deployment for policy decisions.

ARCHITECTURE:
- Exponential backoff: initial * (multiplier ** (attempt - 1))
- Circuit breaker states: CLOSED, OPEN, HALF_OPEN
- Failure window tracking for circuit breaker trip detection
- Thread-safe restart history management

USAGE:
    config = RestartConfig(
        max_attempts=5,
        initial_backoff_seconds=2.0,
        circuit_breaker_threshold=3
    )
    policy = RestartPolicy(config)

    if policy.should_restart(deployment_id):
        backoff = policy.calculate_backoff(deployment_id)
        time.sleep(backoff)
        # Perform restart
        policy.record_restart_attempt(deployment_id, success=True)
"""

import threading
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from claude_mpm.services.core.base import SyncBaseService
from claude_mpm.services.core.interfaces.restart import IRestartPolicy
from claude_mpm.services.core.models.restart import (
    CircuitBreakerState,
    RestartAttempt,
    RestartConfig,
    RestartHistory,
)


class RestartPolicy(SyncBaseService, IRestartPolicy):
    """
    Restart policy with exponential backoff and circuit breaker.

    WHY: Prevents restart loops through intelligent policy decisions.
    Implements exponential backoff to give services time to recover
    and circuit breaker to block restarts after repeated failures.

    Thread Safety: All public methods are thread-safe with proper locking.
    """

    def __init__(self, config: RestartConfig):
        """
        Initialize restart policy.

        Args:
            config: Restart configuration
        """
        super().__init__("RestartPolicy")
        self.config = config
        self._lock = threading.Lock()

        # Restart history per deployment
        self._history: Dict[str, RestartHistory] = {}

    def initialize(self) -> bool:
        """
        Initialize the restart policy.

        Returns:
            True if initialization successful
        """
        self.logger.info(
            f"Initializing RestartPolicy with config: "
            f"max_attempts={self.config.max_attempts}, "
            f"backoff={self.config.initial_backoff_seconds}s-{self.config.max_backoff_seconds}s, "
            f"circuit_breaker={self.config.circuit_breaker_threshold} failures"
        )
        return True

    def should_restart(self, deployment_id: str) -> bool:
        """
        Determine if a deployment should be restarted.

        Args:
            deployment_id: Unique deployment identifier

        Returns:
            True if restart should proceed
        """
        with self._lock:
            history = self._get_or_create_history(deployment_id)

            # Check circuit breaker state
            if history.circuit_breaker_state == CircuitBreakerState.OPEN:
                self.logger.warning(
                    f"Restart blocked for {deployment_id}: circuit breaker OPEN"
                )
                return False

            # Check max attempts
            attempt_count = history.get_attempt_count()
            if attempt_count >= self.config.max_attempts:
                self.logger.warning(
                    f"Restart blocked for {deployment_id}: "
                    f"max attempts reached ({attempt_count}/{self.config.max_attempts})"
                )
                return False

            # Allow restart
            self.logger.debug(
                f"Restart allowed for {deployment_id}: "
                f"attempt {attempt_count + 1}/{self.config.max_attempts}, "
                f"circuit breaker {history.circuit_breaker_state.value}"
            )
            return True

    def calculate_backoff(self, deployment_id: str) -> float:
        """
        Calculate backoff time in seconds for next restart.

        WHY: Implements exponential backoff. For attempt N, backoff = initial * (multiplier ^ (N-2)).
        Attempt 1 has no backoff (0), attempt 2 gets initial backoff, etc.

        Args:
            deployment_id: Unique deployment identifier

        Returns:
            Backoff time in seconds (0 if first attempt)
        """
        with self._lock:
            history = self._get_or_create_history(deployment_id)
            attempt_number = history.get_attempt_count() + 1

            # First attempt has no backoff
            if attempt_number == 1:
                return 0.0

            # Calculate exponential backoff: initial * (multiplier ^ (attempt - 2))
            # This gives: attempt 2 = initial, attempt 3 = initial*multiplier, etc.
            backoff = self.config.initial_backoff_seconds * (
                self.config.backoff_multiplier ** (attempt_number - 2)
            )

            # Cap at max backoff
            backoff = min(backoff, self.config.max_backoff_seconds)

            self.logger.debug(
                f"Calculated backoff for {deployment_id} "
                f"(attempt {attempt_number}): {backoff:.1f}s"
            )
            return backoff

    def record_restart_attempt(
        self, deployment_id: str, success: bool, failure_reason: Optional[str] = None
    ) -> None:
        """
        Record a restart attempt and update circuit breaker state.

        Args:
            deployment_id: Unique deployment identifier
            success: Whether restart succeeded
            failure_reason: Optional reason for failure
        """
        with self._lock:
            history = self._get_or_create_history(deployment_id)
            now = datetime.now(timezone.utc)

            # Calculate backoff for this attempt (already holding lock)
            attempt_number = history.get_attempt_count() + 1
            if attempt_number == 1:
                backoff = 0.0
            else:
                backoff = self.config.initial_backoff_seconds * (
                    self.config.backoff_multiplier ** (attempt_number - 2)
                )
                backoff = min(backoff, self.config.max_backoff_seconds)

            # Create restart attempt record
            attempt = RestartAttempt(
                attempt_number=history.get_attempt_count() + 1,
                deployment_id=deployment_id,
                started_at=now,
                completed_at=now,
                success=success,
                failure_reason=failure_reason,
                backoff_seconds=backoff,
            )

            # Add to history (prepend for newest-first ordering)
            history.attempts.insert(0, attempt)

            # Update circuit breaker based on result
            if success:
                self._handle_successful_restart(history)
            else:
                self._handle_failed_restart(history, now)

            self.logger.info(
                f"Recorded restart attempt for {deployment_id}: "
                f"attempt {attempt.attempt_number}, success={success}, "
                f"circuit breaker={history.circuit_breaker_state.value}"
            )

    def reset_restart_history(self, deployment_id: str) -> None:
        """
        Reset restart history for a deployment.

        Args:
            deployment_id: Unique deployment identifier
        """
        with self._lock:
            if deployment_id in self._history:
                del self._history[deployment_id]
                self.logger.info(
                    f"Reset restart history for deployment: {deployment_id}"
                )

    def get_circuit_breaker_state(self, deployment_id: str) -> str:
        """
        Get current circuit breaker state.

        Args:
            deployment_id: Unique deployment identifier

        Returns:
            Circuit breaker state (CLOSED, OPEN, HALF_OPEN)
        """
        with self._lock:
            history = self._get_or_create_history(deployment_id)
            return history.circuit_breaker_state.value

    def get_restart_attempt_count(self, deployment_id: str) -> int:
        """
        Get number of restart attempts for a deployment.

        Args:
            deployment_id: Unique deployment identifier

        Returns:
            Number of restart attempts
        """
        with self._lock:
            history = self._get_or_create_history(deployment_id)
            return history.get_attempt_count()

    def get_history(self, deployment_id: str) -> Optional[RestartHistory]:
        """
        Get restart history for a deployment.

        Args:
            deployment_id: Unique deployment identifier

        Returns:
            RestartHistory if exists, None otherwise
        """
        with self._lock:
            return self._history.get(deployment_id)

    def shutdown(self) -> bool:
        """
        Shutdown the restart policy.

        Returns:
            True if shutdown successful
        """
        with self._lock:
            self._history.clear()
        self.logger.info("RestartPolicy shutdown successfully")
        return True

    def _get_or_create_history(self, deployment_id: str) -> RestartHistory:
        """
        Get or create restart history for a deployment.

        Args:
            deployment_id: Unique deployment identifier

        Returns:
            RestartHistory instance
        """
        if deployment_id not in self._history:
            self._history[deployment_id] = RestartHistory(deployment_id=deployment_id)
        return self._history[deployment_id]

    def _handle_successful_restart(self, history: RestartHistory) -> None:
        """
        Handle successful restart attempt.

        WHY: Success transitions circuit breaker from HALF_OPEN → CLOSED
        and resets failure window tracking.

        Args:
            history: Restart history to update
        """
        # Reset circuit breaker on success
        if history.circuit_breaker_state == CircuitBreakerState.HALF_OPEN:
            history.circuit_breaker_state = CircuitBreakerState.CLOSED
            self.logger.info(
                f"Circuit breaker CLOSED for {history.deployment_id} after successful restart"
            )

        # Reset failure window
        history.failure_count_in_window = 0
        history.last_failure_window_start = None

    def _handle_failed_restart(self, history: RestartHistory, now: datetime) -> None:
        """
        Handle failed restart attempt.

        WHY: Tracks failures in time window and trips circuit breaker
        if threshold exceeded.

        Args:
            history: Restart history to update
            now: Current timestamp
        """
        # Initialize failure window if needed
        if history.last_failure_window_start is None:
            history.last_failure_window_start = now
            history.failure_count_in_window = 1
        else:
            # Check if we're still in the same window
            window_start = history.last_failure_window_start
            window_end = window_start + timedelta(
                seconds=self.config.circuit_breaker_window_seconds
            )

            if now <= window_end:
                # Still in window, increment count
                history.failure_count_in_window += 1
            else:
                # Window expired, start new window
                history.last_failure_window_start = now
                history.failure_count_in_window = 1

        # Check if we should trip the circuit breaker
        if history.failure_count_in_window >= self.config.circuit_breaker_threshold:
            if history.circuit_breaker_state != CircuitBreakerState.OPEN:
                history.circuit_breaker_state = CircuitBreakerState.OPEN
                self.logger.warning(
                    f"Circuit breaker OPEN for {history.deployment_id}: "
                    f"{history.failure_count_in_window} failures in "
                    f"{self.config.circuit_breaker_window_seconds}s window"
                )

        # Check if we should transition to HALF_OPEN
        elif history.circuit_breaker_state == CircuitBreakerState.OPEN:
            self._check_circuit_breaker_reset(history, now)

    def _check_circuit_breaker_reset(
        self, history: RestartHistory, now: datetime
    ) -> None:
        """
        Check if circuit breaker should reset to HALF_OPEN.

        WHY: After cooldown period, allow one restart attempt to test
        if service has recovered.

        Args:
            history: Restart history to check
            now: Current timestamp
        """
        if history.last_failure_window_start is None:
            return

        # Calculate reset time
        reset_time = history.last_failure_window_start + timedelta(
            seconds=self.config.circuit_breaker_reset_seconds
        )

        # Check if cooldown period has elapsed
        if now >= reset_time:
            history.circuit_breaker_state = CircuitBreakerState.HALF_OPEN
            self.logger.info(
                f"Circuit breaker HALF_OPEN for {history.deployment_id} "
                f"after {self.config.circuit_breaker_reset_seconds}s cooldown"
            )


__all__ = ["RestartPolicy"]
