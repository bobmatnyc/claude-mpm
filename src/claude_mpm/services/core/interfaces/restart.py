"""
Restart Management Interfaces for Claude MPM Framework
========================================================

WHY: This module defines interfaces for auto-restart functionality with crash
detection, intelligent restart policies, and circuit breaker patterns.

DESIGN DECISION: Restart interfaces are separated to enable modular restart
management with different crash detection strategies and restart policies.

ARCHITECTURE:
- ICrashDetector: Interface for detecting process crashes and failures
- IRestartPolicy: Interface for restart decision logic with backoff
- IRestartManager: Interface for orchestrating the full restart workflow

USAGE:
    crash_detector = CrashDetector(health_manager)
    restart_policy = RestartPolicy(config)
    restart_manager = RestartManager(
        process_manager=process_manager,
        health_manager=health_manager,
        config=config
    )
    restart_manager.enable_auto_restart(deployment_id)
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    from claude_mpm.services.core.models.restart import RestartHistory


class ICrashDetector(ABC):
    """
    Interface for detecting process crashes and failures.

    WHY: Crash detection requires monitoring health status changes, process
    exits, and zombie states. This interface abstracts different detection
    strategies to enable flexible crash monitoring.

    DESIGN DECISION: Integrates with IHealthCheckManager via callbacks to
    receive real-time status updates. Tracks crash history per deployment
    to enable pattern detection.

    Thread Safety: Implementations must be thread-safe for concurrent monitoring.
    """

    @abstractmethod
    def register_crash_callback(self, callback: Callable[[str, str], None]) -> None:
        """
        Register a callback to be invoked when a crash is detected.

        Args:
            callback: Function called with (deployment_id, reason)
        """

    @abstractmethod
    def start_monitoring(self, deployment_id: str) -> None:
        """
        Start monitoring a deployment for crashes.

        WHY: Enables targeted monitoring for specific deployments.

        Args:
            deployment_id: Unique deployment identifier

        Raises:
            ValueError: If deployment_id not found
        """

    @abstractmethod
    def stop_monitoring(self, deployment_id: str) -> None:
        """
        Stop monitoring a deployment.

        Args:
            deployment_id: Unique deployment identifier
        """

    @abstractmethod
    def is_monitoring(self, deployment_id: str) -> bool:
        """
        Check if a deployment is being monitored.

        Args:
            deployment_id: Unique deployment identifier

        Returns:
            True if deployment is being monitored
        """

    @abstractmethod
    def get_crash_count(self, deployment_id: str) -> int:
        """
        Get the number of crashes detected for a deployment.

        Args:
            deployment_id: Unique deployment identifier

        Returns:
            Number of crashes detected
        """


class IRestartPolicy(ABC):
    """
    Interface for restart decision logic with exponential backoff.

    WHY: Restart policies prevent restart loops through exponential backoff,
    max attempts, and circuit breaker patterns. This interface abstracts
    the decision-making logic to enable different strategies.

    DESIGN DECISION: Implements exponential backoff with configurable
    parameters and circuit breaker state transitions (CLOSED → OPEN → HALF_OPEN).

    Circuit Breaker States:
    - CLOSED: Normal operation, restarts allowed
    - OPEN: Circuit breaker tripped, restarts blocked
    - HALF_OPEN: Testing if service recovered
    """

    @abstractmethod
    def should_restart(self, deployment_id: str) -> bool:
        """
        Determine if a deployment should be restarted.

        WHY: Central decision point that considers attempt count, circuit
        breaker state, and backoff timing.

        Args:
            deployment_id: Unique deployment identifier

        Returns:
            True if restart should proceed
        """

    @abstractmethod
    def calculate_backoff(self, deployment_id: str) -> float:
        """
        Calculate backoff time in seconds for next restart.

        WHY: Implements exponential backoff to prevent restart storms.
        Formula: min(initial * (multiplier ** (attempt - 1)), max_backoff)

        Args:
            deployment_id: Unique deployment identifier

        Returns:
            Backoff time in seconds (0 if first attempt)
        """

    @abstractmethod
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

    @abstractmethod
    def reset_restart_history(self, deployment_id: str) -> None:
        """
        Reset restart history for a deployment.

        WHY: Clears restart attempts after successful recovery or manual
        intervention.

        Args:
            deployment_id: Unique deployment identifier
        """

    @abstractmethod
    def get_circuit_breaker_state(self, deployment_id: str) -> str:
        """
        Get current circuit breaker state.

        Args:
            deployment_id: Unique deployment identifier

        Returns:
            Circuit breaker state (CLOSED, OPEN, HALF_OPEN)
        """

    @abstractmethod
    def get_restart_attempt_count(self, deployment_id: str) -> int:
        """
        Get number of restart attempts for a deployment.

        Args:
            deployment_id: Unique deployment identifier

        Returns:
            Number of restart attempts
        """


class IRestartManager(ABC):
    """
    Interface for orchestrating the complete restart workflow.

    WHY: Restart management requires coordinating crash detection, policy
    evaluation, process restart, and health verification. This interface
    provides a high-level API for automatic and manual restarts.

    DESIGN DECISION: Provides both automatic (background) and manual
    (on-demand) restart operations. Integrates with all components:
    CrashDetector, RestartPolicy, ProcessManager, and HealthCheckManager.

    Restart Workflow:
    1. Detect crash (via CrashDetector callback)
    2. Check restart policy (max attempts, circuit breaker)
    3. Wait for backoff period
    4. Execute restart (preserve original StartConfig)
    5. Verify health after restart
    6. Record attempt and update circuit breaker
    """

    @abstractmethod
    def enable_auto_restart(self, deployment_id: str) -> None:
        """
        Enable automatic restarts for a deployment.

        WHY: Enables hands-free recovery from crashes. Starts monitoring
        via CrashDetector and registers restart callbacks.

        Args:
            deployment_id: Unique deployment identifier

        Raises:
            ValueError: If deployment_id not found
        """

    @abstractmethod
    def disable_auto_restart(self, deployment_id: str) -> None:
        """
        Disable automatic restarts for a deployment.

        Args:
            deployment_id: Unique deployment identifier
        """

    @abstractmethod
    def is_auto_restart_enabled(self, deployment_id: str) -> bool:
        """
        Check if auto-restart is enabled for a deployment.

        Args:
            deployment_id: Unique deployment identifier

        Returns:
            True if auto-restart is enabled
        """

    @abstractmethod
    def restart_deployment(self, deployment_id: str, manual: bool = False) -> bool:
        """
        Restart a deployment (manual or automatic trigger).

        WHY: Provides unified restart operation that respects policy
        constraints and performs health verification.

        Args:
            deployment_id: Unique deployment identifier
            manual: If True, bypass some policy checks (e.g., circuit breaker)

        Returns:
            True if restart succeeded

        Raises:
            ValueError: If deployment_id not found
        """

    @abstractmethod
    def get_restart_history(self, deployment_id: str) -> Optional["RestartHistory"]:
        """
        Get restart history for a deployment.

        Args:
            deployment_id: Unique deployment identifier

        Returns:
            RestartHistory if found, None otherwise
        """

    @abstractmethod
    def clear_restart_history(self, deployment_id: str) -> None:
        """
        Clear restart history and reset circuit breaker.

        WHY: Allows manual intervention to clear failed restart state.

        Args:
            deployment_id: Unique deployment identifier
        """


__all__ = [
    "ICrashDetector",
    "IRestartManager",
    "IRestartPolicy",
]
