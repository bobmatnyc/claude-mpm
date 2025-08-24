"""
Base class for services with complex lifecycle management.
"""

import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional

from ...core.mixins import LoggerMixin


class ServiceState(Enum):
    """Standard service states."""

    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    INITIALIZED = "initialized"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class LifecycleServiceBase(LoggerMixin, ABC):
    """
    Base class for services with complex lifecycle management.

    Provides common patterns:
    - State machine management
    - Lifecycle hooks
    - Health monitoring
    - Dependency management
    """

    def __init__(self, service_name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize lifecycle service.

        Args:
            service_name: Name of the service
            config: Optional configuration
        """
        self.service_name = service_name
        self._logger_name = f"service.{service_name}"
        self.config = config or {}

        # State management
        self._state = ServiceState.UNINITIALIZED
        self._previous_state = None
        self._state_history: List[tuple] = []

        # Lifecycle tracking
        self._start_time: Optional[float] = None
        self._last_health_check: Optional[float] = None
        self._health_status: Dict[str, Any] = {}

        # Dependencies
        self._dependencies: List[str] = []
        self._dependents: List[str] = []

        # Error tracking
        self._errors: List[Dict[str, Any]] = []
        self._max_errors = 10

    @property
    def state(self) -> ServiceState:
        """Get current service state."""
        return self._state

    @property
    def is_running(self) -> bool:
        """Check if service is running."""
        return self._state == ServiceState.RUNNING

    @property
    def is_healthy(self) -> bool:
        """Check if service is healthy."""
        return (
            self._state == ServiceState.RUNNING
            and len(self._errors) == 0
            and self._health_status.get("healthy", True)
        )

    @property
    def uptime(self) -> Optional[float]:
        """Get service uptime in seconds."""
        if self._start_time and self.is_running:
            return time.time() - self._start_time
        return None

    def add_dependency(self, service_name: str) -> None:
        """Add a service dependency."""
        if service_name not in self._dependencies:
            self._dependencies.append(service_name)
            self.logger.debug(f"Added dependency: {service_name}")

    def add_dependent(self, service_name: str) -> None:
        """Add a dependent service."""
        if service_name not in self._dependents:
            self._dependents.append(service_name)
            self.logger.debug(f"Added dependent: {service_name}")

    def initialize(self) -> bool:
        """
        Initialize the service.

        Returns:
            True if initialization successful
        """
        if self._state != ServiceState.UNINITIALIZED:
            self.logger.warning(f"Service {self.service_name} already initialized")
            return self._state in (ServiceState.INITIALIZED, ServiceState.RUNNING)

        self._transition_state(ServiceState.INITIALIZING)
        self.logger.info(f"Initializing service: {self.service_name}")

        try:
            # Check dependencies
            if not self._check_dependencies():
                self._transition_state(ServiceState.ERROR)
                return False

            # Service-specific initialization
            success = self._do_initialize()

            if success:
                self._transition_state(ServiceState.INITIALIZED)
                self.logger.info(
                    f"Service {self.service_name} initialized successfully"
                )
            else:
                self._transition_state(ServiceState.ERROR)
                self.logger.error(f"Service {self.service_name} initialization failed")

            return success

        except Exception as e:
            self._record_error("initialization", e)
            self._transition_state(ServiceState.ERROR)
            self.logger.error(
                f"Service {self.service_name} initialization error: {e}", exc_info=True
            )
            return False

    def start(self) -> bool:
        """
        Start the service.

        Returns:
            True if start successful
        """
        if self._state == ServiceState.RUNNING:
            self.logger.warning(f"Service {self.service_name} already running")
            return True

        if self._state != ServiceState.INITIALIZED and not self.initialize():
            return False

        self._transition_state(ServiceState.STARTING)
        self.logger.info(f"Starting service: {self.service_name}")

        try:
            success = self._do_start()

            if success:
                self._start_time = time.time()
                self._transition_state(ServiceState.RUNNING)
                self.logger.info(f"Service {self.service_name} started successfully")
            else:
                self._transition_state(ServiceState.ERROR)
                self.logger.error(f"Service {self.service_name} start failed")

            return success

        except Exception as e:
            self._record_error("start", e)
            self._transition_state(ServiceState.ERROR)
            self.logger.error(
                f"Service {self.service_name} start error: {e}", exc_info=True
            )
            return False

    def stop(self) -> bool:
        """
        Stop the service.

        Returns:
            True if stop successful
        """
        if self._state == ServiceState.STOPPED:
            self.logger.warning(f"Service {self.service_name} already stopped")
            return True

        self._transition_state(ServiceState.STOPPING)
        self.logger.info(f"Stopping service: {self.service_name}")

        try:
            success = self._do_stop()

            if success:
                self._start_time = None
                self._transition_state(ServiceState.STOPPED)
                self.logger.info(f"Service {self.service_name} stopped successfully")
            else:
                self._transition_state(ServiceState.ERROR)
                self.logger.error(f"Service {self.service_name} stop failed")

            return success

        except Exception as e:
            self._record_error("stop", e)
            self._transition_state(ServiceState.ERROR)
            self.logger.error(
                f"Service {self.service_name} stop error: {e}", exc_info=True
            )
            return False

    def restart(self) -> bool:
        """Restart the service."""
        self.logger.info(f"Restarting service: {self.service_name}")

        if self.is_running and not self.stop():
            return False

        return self.start()

    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check.

        Returns:
            Health status dictionary
        """
        self._last_health_check = time.time()

        try:
            # Service-specific health check
            service_health = self._do_health_check()

            # Combine with base health info
            health_status = {
                "service": self.service_name,
                "state": self._state.value,
                "healthy": self.is_healthy,
                "uptime": self.uptime,
                "error_count": len(self._errors),
                "dependencies": self._dependencies,
                "dependents": self._dependents,
                "last_check": self._last_health_check,
                **service_health,
            }

            self._health_status = health_status
            return health_status

        except Exception as e:
            self._record_error("health_check", e)
            return {
                "service": self.service_name,
                "state": self._state.value,
                "healthy": False,
                "error": str(e),
            }

    def _transition_state(self, new_state: ServiceState) -> None:
        """Transition to a new state."""
        old_state = self._state
        self._previous_state = old_state
        self._state = new_state

        # Record state transition
        self._state_history.append((time.time(), old_state.value, new_state.value))

        # Keep history bounded
        if len(self._state_history) > 50:
            self._state_history = self._state_history[-50:]

        self.logger.debug(f"State transition: {old_state.value} -> {new_state.value}")

    def _record_error(self, operation: str, error: Exception) -> None:
        """Record an error."""
        error_record = {
            "timestamp": time.time(),
            "operation": operation,
            "error": str(error),
            "type": type(error).__name__,
        }

        self._errors.append(error_record)

        # Keep error list bounded
        if len(self._errors) > self._max_errors:
            self._errors = self._errors[-self._max_errors :]

    def _check_dependencies(self) -> bool:
        """Check if all dependencies are satisfied."""
        # This is a placeholder - in a real implementation,
        # you would check with a service registry
        return True

    @abstractmethod
    def _do_initialize(self) -> bool:
        """Service-specific initialization logic."""

    @abstractmethod
    def _do_start(self) -> bool:
        """Service-specific start logic."""

    @abstractmethod
    def _do_stop(self) -> bool:
        """Service-specific stop logic."""

    def _do_health_check(self) -> Dict[str, Any]:
        """Service-specific health check logic."""
        return {"healthy": True}

    def __repr__(self) -> str:
        """String representation."""
        return f"{self.__class__.__name__}(name={self.service_name}, state={self._state.value})"
