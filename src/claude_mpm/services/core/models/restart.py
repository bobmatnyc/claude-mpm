"""
Restart Management Data Models for Claude MPM Framework
========================================================

WHY: This module defines data structures for auto-restart operations,
including restart attempts, history tracking, and circuit breaker states.

DESIGN DECISION: Uses dataclasses for immutability and type safety. Provides
serialization methods for state persistence across service restarts.

ARCHITECTURE:
- CircuitBreakerState: Enum of circuit breaker states
- RestartAttempt: Single restart attempt record
- RestartHistory: Complete restart history for a deployment
- RestartConfig: Configuration for restart policies
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class CircuitBreakerState(Enum):
    """
    Circuit breaker state for restart management.

    WHY: Circuit breaker prevents infinite restart loops by blocking
    restarts after repeated failures within a time window.

    States:
        CLOSED: Normal operation, restarts allowed
        OPEN: Circuit breaker tripped, restarts blocked
        HALF_OPEN: Testing if service recovered (allows one restart)
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def allows_restart(self) -> bool:
        """Check if state allows restart attempts."""
        return self in (CircuitBreakerState.CLOSED, CircuitBreakerState.HALF_OPEN)


@dataclass
class RestartAttempt:
    """
    Record of a single restart attempt.

    WHY: Tracks detailed information about each restart attempt to enable
    debugging and policy decisions (exponential backoff, circuit breaker).

    Attributes:
        attempt_number: Sequential attempt number (1-based)
        deployment_id: Unique deployment identifier
        started_at: When the restart was initiated
        completed_at: When the restart finished (None if in progress)
        success: Whether the restart succeeded
        failure_reason: Optional reason for failure
        backoff_seconds: Backoff time before this attempt
    """

    attempt_number: int
    deployment_id: str
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    success: bool = False
    failure_reason: Optional[str] = None
    backoff_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation with datetime converted to ISO format
        """
        return {
            "attempt_number": self.attempt_number,
            "deployment_id": self.deployment_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "success": self.success,
            "failure_reason": self.failure_reason,
            "backoff_seconds": self.backoff_seconds,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RestartAttempt":
        """
        Create RestartAttempt from dictionary.

        Args:
            data: Dictionary from JSON deserialization

        Returns:
            RestartAttempt instance
        """
        # Convert ISO strings to datetime
        if isinstance(data.get("started_at"), str):
            data["started_at"] = datetime.fromisoformat(data["started_at"])

        if data.get("completed_at") and isinstance(data["completed_at"], str):
            data["completed_at"] = datetime.fromisoformat(data["completed_at"])

        return cls(**data)


@dataclass
class RestartHistory:
    """
    Complete restart history for a deployment.

    WHY: Maintains restart attempt history, circuit breaker state, and
    failure window tracking to enable intelligent restart policies.

    Attributes:
        deployment_id: Unique deployment identifier
        attempts: List of restart attempts (newest first)
        circuit_breaker_state: Current circuit breaker state
        last_failure_window_start: Start of current failure window
        failure_count_in_window: Number of failures in current window
    """

    deployment_id: str
    attempts: List[RestartAttempt] = field(default_factory=list)
    circuit_breaker_state: CircuitBreakerState = CircuitBreakerState.CLOSED
    last_failure_window_start: Optional[datetime] = None
    failure_count_in_window: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation
        """
        return {
            "deployment_id": self.deployment_id,
            "attempts": [attempt.to_dict() for attempt in self.attempts],
            "circuit_breaker_state": self.circuit_breaker_state.value,
            "last_failure_window_start": (
                self.last_failure_window_start.isoformat()
                if self.last_failure_window_start
                else None
            ),
            "failure_count_in_window": self.failure_count_in_window,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RestartHistory":
        """
        Create RestartHistory from dictionary.

        Args:
            data: Dictionary from JSON deserialization

        Returns:
            RestartHistory instance
        """
        # Convert circuit breaker state string to enum
        if isinstance(data.get("circuit_breaker_state"), str):
            data["circuit_breaker_state"] = CircuitBreakerState(
                data["circuit_breaker_state"]
            )

        # Convert ISO string to datetime
        if data.get("last_failure_window_start") and isinstance(
            data["last_failure_window_start"], str
        ):
            data["last_failure_window_start"] = datetime.fromisoformat(
                data["last_failure_window_start"]
            )

        # Convert attempt dicts to RestartAttempt objects
        if isinstance(data.get("attempts"), list):
            data["attempts"] = [
                (
                    RestartAttempt.from_dict(attempt)
                    if isinstance(attempt, dict)
                    else attempt
                )
                for attempt in data["attempts"]
            ]

        return cls(**data)

    def get_latest_attempt(self) -> Optional[RestartAttempt]:
        """
        Get the most recent restart attempt.

        Returns:
            Latest RestartAttempt if any, None otherwise
        """
        return self.attempts[0] if self.attempts else None

    def get_attempt_count(self) -> int:
        """
        Get total number of restart attempts.

        Returns:
            Number of attempts
        """
        return len(self.attempts)

    def get_consecutive_failures(self) -> int:
        """
        Get number of consecutive failures from the most recent attempt.

        Returns:
            Count of consecutive failures
        """
        count = 0
        for attempt in self.attempts:
            if not attempt.success:
                count += 1
            else:
                break
        return count


@dataclass
class RestartConfig:
    """
    Configuration for restart policies.

    WHY: Encapsulates all restart policy parameters to enable flexible
    configuration and testing.

    Attributes:
        max_attempts: Maximum restart attempts before giving up
        initial_backoff_seconds: Initial backoff time (doubles each attempt)
        max_backoff_seconds: Maximum backoff cap (default: 5 minutes)
        backoff_multiplier: Backoff multiplier for exponential backoff
        circuit_breaker_threshold: Failures to trip circuit breaker
        circuit_breaker_window_seconds: Time window for failure counting
        circuit_breaker_reset_seconds: Cooldown before resetting breaker
        health_check_timeout_seconds: Time to wait for health check after restart
    """

    max_attempts: int = 5
    initial_backoff_seconds: float = 2.0
    max_backoff_seconds: float = 300.0  # 5 minutes
    backoff_multiplier: float = 2.0
    circuit_breaker_threshold: int = 3  # failures to trip breaker
    circuit_breaker_window_seconds: int = 300  # 5 minute window
    circuit_breaker_reset_seconds: int = 600  # 10 minute cooldown
    health_check_timeout_seconds: int = 30  # wait for health check

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")

        if self.initial_backoff_seconds < 0:
            raise ValueError("initial_backoff_seconds must be >= 0")

        if self.max_backoff_seconds < self.initial_backoff_seconds:
            raise ValueError("max_backoff_seconds must be >= initial_backoff_seconds")

        if self.backoff_multiplier < 1.0:
            raise ValueError("backoff_multiplier must be >= 1.0")

        if self.circuit_breaker_threshold < 1:
            raise ValueError("circuit_breaker_threshold must be >= 1")

        if self.circuit_breaker_window_seconds < 1:
            raise ValueError("circuit_breaker_window_seconds must be >= 1")

        if self.circuit_breaker_reset_seconds < 1:
            raise ValueError("circuit_breaker_reset_seconds must be >= 1")

        if self.health_check_timeout_seconds < 1:
            raise ValueError("health_check_timeout_seconds must be >= 1")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RestartConfig":
        """
        Create RestartConfig from dictionary.

        Args:
            data: Dictionary from JSON deserialization

        Returns:
            RestartConfig instance
        """
        return cls(**data)


__all__ = [
    "CircuitBreakerState",
    "RestartAttempt",
    "RestartConfig",
    "RestartHistory",
]
