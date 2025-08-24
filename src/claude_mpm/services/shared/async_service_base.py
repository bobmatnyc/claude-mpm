"""
Base class for asynchronous services to reduce duplication.
"""

import asyncio
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Optional

from ...core.mixins import LoggerMixin


class AsyncServiceState(Enum):
    """Standard states for async services."""

    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class AsyncServiceBase(LoggerMixin, ABC):
    """
    Base class for asynchronous services.

    Provides common patterns:
    - State management
    - Lifecycle methods
    - Error handling
    - Background task management
    """

    def __init__(self, service_name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize async service.

        Args:
            service_name: Name of the service
            config: Optional configuration dictionary
        """
        self.service_name = service_name
        self._logger_name = f"service.{service_name}"
        self.config = config or {}

        # State management
        self._state = AsyncServiceState.UNINITIALIZED
        self._state_lock = asyncio.Lock()

        # Background tasks
        self._background_tasks: set = set()
        self._shutdown_event = asyncio.Event()

        # Error tracking
        self._last_error: Optional[Exception] = None
        self._error_count = 0

    @property
    def state(self) -> AsyncServiceState:
        """Get current service state."""
        return self._state

    @property
    def is_running(self) -> bool:
        """Check if service is running."""
        return self._state == AsyncServiceState.RUNNING

    @property
    def is_healthy(self) -> bool:
        """Check if service is healthy."""
        return self._state == AsyncServiceState.RUNNING and self._last_error is None

    async def initialize(self) -> bool:
        """
        Initialize the service.

        Returns:
            True if initialization successful
        """
        async with self._state_lock:
            if self._state != AsyncServiceState.UNINITIALIZED:
                self.logger.warning(f"Service {self.service_name} already initialized")
                return self._state == AsyncServiceState.RUNNING

            self._state = AsyncServiceState.INITIALIZING
            self.logger.info(f"Initializing service: {self.service_name}")

            try:
                success = await self._do_initialize()
                if success:
                    self._state = AsyncServiceState.RUNNING
                    self.logger.info(
                        f"Service {self.service_name} initialized successfully"
                    )
                else:
                    self._state = AsyncServiceState.ERROR
                    self.logger.error(
                        f"Service {self.service_name} initialization failed"
                    )

                return success

            except Exception as e:
                self._state = AsyncServiceState.ERROR
                self._last_error = e
                self._error_count += 1
                self.logger.error(
                    f"Service {self.service_name} initialization error: {e}",
                    exc_info=True,
                )
                return False

    async def shutdown(self) -> None:
        """Shutdown the service gracefully."""
        async with self._state_lock:
            if self._state in (AsyncServiceState.STOPPED, AsyncServiceState.STOPPING):
                return

            self._state = AsyncServiceState.STOPPING
            self.logger.info(f"Shutting down service: {self.service_name}")

            try:
                # Signal shutdown to background tasks
                self._shutdown_event.set()

                # Cancel background tasks
                await self._cancel_background_tasks()

                # Service-specific shutdown
                await self._do_shutdown()

                self._state = AsyncServiceState.STOPPED
                self.logger.info(f"Service {self.service_name} shut down successfully")

            except Exception as e:
                self._state = AsyncServiceState.ERROR
                self._last_error = e
                self.logger.error(
                    f"Service {self.service_name} shutdown error: {e}", exc_info=True
                )

    async def restart(self) -> bool:
        """Restart the service."""
        self.logger.info(f"Restarting service: {self.service_name}")
        await self.shutdown()

        # Reset state for restart
        self._state = AsyncServiceState.UNINITIALIZED
        self._shutdown_event.clear()
        self._last_error = None

        return await self.initialize()

    def create_background_task(self, coro, name: Optional[str] = None) -> asyncio.Task:
        """
        Create and track a background task.

        Args:
            coro: Coroutine to run
            name: Optional task name

        Returns:
            Created task
        """
        task = asyncio.create_task(coro, name=name)
        self._background_tasks.add(task)

        # Remove task from set when done
        task.add_done_callback(self._background_tasks.discard)

        return task

    async def _cancel_background_tasks(self) -> None:
        """Cancel all background tasks."""
        if not self._background_tasks:
            return

        self.logger.debug(f"Cancelling {len(self._background_tasks)} background tasks")

        # Cancel all tasks
        for task in self._background_tasks:
            if not task.done():
                task.cancel()

        # Wait for cancellation with timeout
        try:
            await asyncio.wait_for(
                asyncio.gather(*self._background_tasks, return_exceptions=True),
                timeout=5.0,
            )
        except asyncio.TimeoutError:
            self.logger.warning("Some background tasks did not cancel within timeout")

        self._background_tasks.clear()

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check.

        Returns:
            Health status dictionary
        """
        return {
            "service": self.service_name,
            "state": self._state.value,
            "healthy": self.is_healthy,
            "error_count": self._error_count,
            "last_error": str(self._last_error) if self._last_error else None,
            "background_tasks": len(self._background_tasks),
        }

    @abstractmethod
    async def _do_initialize(self) -> bool:
        """
        Service-specific initialization logic.

        Returns:
            True if initialization successful
        """

    async def _do_shutdown(self) -> None:
        """Service-specific shutdown logic."""

    def __repr__(self) -> str:
        """String representation."""
        return f"{self.__class__.__name__}(name={self.service_name}, state={self._state.value})"
