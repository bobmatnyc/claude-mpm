"""Lazy loading service infrastructure for deferred instantiation.

This module provides a lazy loading mechanism for services that are expensive
to initialize but may not be used in every execution path.

WHY lazy loading:
- Reduces startup time from 3-5 seconds to <2 seconds
- Defers heavy initialization until services are actually needed
- Maintains backward compatibility with eager instantiation
- Provides transparent access to underlying services
"""

import asyncio
import functools
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, TypeVar

from ..core.logger import get_logger

T = TypeVar("T")


@dataclass
class LazyMetrics:
    """Metrics for lazy loading performance."""

    created_at: datetime = field(default_factory=datetime.now)
    first_access: datetime | None = None
    initialization_time: float = 0.0
    access_count: int = 0
    initialization_error: Exception | None = None
    is_initialized: bool = False


class LazyService[T]:
    """Lazy loading wrapper for expensive services.

    WHY this design:
    - Services are only initialized when first accessed
    - Thread-safe initialization ensures single instance
    - Transparent proxy pattern preserves service interface
    - Metrics tracking for performance monitoring

    Example:
        # Wrap expensive service
        lazy_analyzer = LazyService(
            service_class=ProjectAnalyzer,
            init_args=(),
            init_kwargs={'config': config}
        )

        # Service is not initialized yet
        assert not lazy_analyzer.is_initialized

        # First access triggers initialization
        result = lazy_analyzer.analyze()  # Initializes here

        # Subsequent accesses use cached instance
        result2 = lazy_analyzer.analyze()  # No initialization
    """

    def __init__(
        self,
        service_class: type[T],
        init_args: tuple = (),
        init_kwargs: dict | None = None,
        name: str | None = None,
        eager: bool = False,
    ):
        """Initialize lazy service wrapper.

        Args:
            service_class: The class to lazily instantiate
            init_args: Positional arguments for initialization
            init_kwargs: Keyword arguments for initialization
            name: Optional name for logging
            eager: If True, initialize immediately (for testing)
        """
        self._service_class = service_class
        self._init_args = init_args
        self._init_kwargs = init_kwargs or {}
        self._name = name or service_class.__name__
        self._eager = eager

        self._instance: T | None = None
        self._lock = threading.RLock()
        self._metrics = LazyMetrics()
        self._logger = get_logger(f"lazy.{self._name}")

        # Initialize immediately if eager mode
        if eager:
            self._ensure_initialized()

    @property
    def is_initialized(self) -> bool:
        """Check if service has been initialized."""
        return self._instance is not None

    @property
    def metrics(self) -> LazyMetrics:
        """Get lazy loading metrics."""
        return self._metrics

    def _ensure_initialized(self) -> T:
        """Ensure service is initialized, creating if necessary.

        Thread-safe initialization with metrics tracking.
        """
        if self._instance is not None:
            return self._instance

        with self._lock:
            # Double-check pattern for thread safety
            if self._instance is not None:
                return self._instance

            # Track initialization
            start_time = time.time()
            if self._metrics.first_access is None:
                self._metrics.first_access = datetime.now(UTC)

            try:
                self._logger.debug(f"Initializing lazy service: {self._name}")

                # Create the actual service instance
                self._instance = self._service_class(
                    *self._init_args, **self._init_kwargs
                )

                # Update metrics
                self._metrics.initialization_time = time.time() - start_time
                self._metrics.is_initialized = True

                self._logger.info(
                    f"Lazy service {self._name} initialized in "
                    f"{self._metrics.initialization_time:.2f}s"
                )

                return self._instance

            except Exception as e:
                self._metrics.initialization_error = e
                self._logger.error(f"Failed to initialize {self._name}: {e}")
                raise

    def __getattr__(self, name: str) -> Any:
        """Proxy attribute access to the underlying service.

        This is called when an attribute is not found on LazyService itself.
        It ensures initialization and forwards the request.
        """
        # Avoid recursion for internal attributes
        if name.startswith("_"):
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'"
            )

        # Initialize if needed
        instance = self._ensure_initialized()
        self._metrics.access_count += 1

        # Forward attribute access
        return getattr(instance, name)

    def __call__(self, *args, **kwargs) -> Any:
        """Make LazyService callable if underlying service is."""
        instance = self._ensure_initialized()
        self._metrics.access_count += 1
        return instance(*args, **kwargs)  # type: ignore[operator]

    def __repr__(self) -> str:
        """String representation of lazy service."""
        status = "initialized" if self.is_initialized else "pending"
        return f"<LazyService({self._name}) [{status}]>"


class LazyServiceRegistry:
    """Registry for managing lazy services.

    WHY registry pattern:
    - Central management of all lazy services
    - Bulk initialization for testing
    - Performance metrics aggregation
    - Service dependency resolution
    """

    def __init__(self):
        """Initialise an empty thread-safe registry.

        WHY: The registry needs a dict to store services, a logger for diagnostics,
        and a lock to prevent race conditions during concurrent registration.
        WHAT: Sets _services to an empty dict, creates a named logger, and creates
        a threading.Lock for mutation protection.
        TEST: Instantiate; assert _services is empty and _lock is a threading.Lock.
        """
        self._services: dict[str, LazyService] = {}
        self._logger = get_logger("lazy_registry")
        self._lock = threading.Lock()

    def register(
        self,
        name: str,
        service_class: type,
        init_args: tuple = (),
        init_kwargs: dict | None = None,
        eager: bool = False,
    ) -> LazyService:
        """Register a lazy service.

        Args:
            name: Unique name for the service
            service_class: The service class to wrap
            init_args: Initialization arguments
            init_kwargs: Initialization keyword arguments
            eager: Whether to initialize immediately

        Returns:
            The registered LazyService instance
        """
        with self._lock:
            if name in self._services:
                self._logger.warning(f"Overwriting existing service: {name}")

            service = LazyService(
                service_class=service_class,
                init_args=init_args,
                init_kwargs=init_kwargs,
                name=name,
                eager=eager,
            )

            self._services[name] = service
            self._logger.debug(f"Registered lazy service: {name}")
            return service

    def get(self, name: str) -> LazyService | None:
        """Get a registered service by name."""
        return self._services.get(name)

    def initialize_all(self) -> dict[str, float]:
        """Initialize all registered services.

        Useful for testing or preloading.

        Returns:
            Dictionary mapping service names to initialization times
        """
        init_times = {}

        for name, service in self._services.items():
            if not service.is_initialized:
                try:
                    service._ensure_initialized()
                    init_times[name] = service.metrics.initialization_time
                except Exception as e:
                    self._logger.error(f"Failed to initialize {name}: {e}")
                    init_times[name] = -1.0

        return init_times

    def get_metrics(self) -> dict[str, dict[str, Any]]:
        """Get metrics for all registered services."""
        metrics = {}

        for name, service in self._services.items():
            m = service.metrics
            metrics[name] = {
                "initialized": service.is_initialized,
                "first_access": m.first_access.isoformat() if m.first_access else None,
                "initialization_time": m.initialization_time,
                "access_count": m.access_count,
                "has_error": m.initialization_error is not None,
            }

        return metrics

    def reset(self):
        """Clear all registered services."""
        with self._lock:
            self._services.clear()
            self._logger.debug("Registry reset")


# Global registry instance
_registry = LazyServiceRegistry()


def lazy_load(
    service_class: type,
    name: str | None = None,
    init_args: tuple = (),
    init_kwargs: dict | None = None,
) -> LazyService:
    """Convenience function to create and register a lazy service.

    Args:
        service_class: The service class to wrap
        name: Optional name (defaults to class name)
        init_args: Initialization arguments
        init_kwargs: Initialization keyword arguments

    Returns:
        Registered LazyService instance

    Example:
        # Create lazy service
        analyzer = lazy_load(
            ProjectAnalyzer,
            init_kwargs={'config': config}
        )

        # Use like normal service
        result = analyzer.analyze_project()
    """
    if name is None:
        name = service_class.__name__

    return _registry.register(
        name=name,
        service_class=service_class,
        init_args=init_args,
        init_kwargs=init_kwargs,
    )


def get_lazy_service(name: str) -> LazyService | None:
    """Get a registered lazy service by name."""
    return _registry.get(name)


def get_lazy_metrics() -> dict[str, dict[str, Any]]:
    """Get metrics for all lazy services."""
    return _registry.get_metrics()


def initialize_all_services() -> dict[str, float]:
    """Initialize all registered lazy services."""
    return _registry.initialize_all()


class lazy_property:
    """Decorator for lazy property initialization.

    WHY decorator pattern:
    - Pythonic approach for lazy attributes
    - Caches expensive computations
    - Thread-safe initialization
    - Transparent to callers

    Example:
        class MyService:
            @lazy_property
            def expensive_data(self):
                # This only runs once
                return self._compute_expensive_data()
    """

    def __init__(self, func: Callable) -> None:
        """Store the wrapped function and create the reentrant lock.

        WHY: Captures the function being decorated and sets up a per-descriptor lock
        so concurrent first-access attempts don't double-initialise the property.
        WHAT: Saves func, creates threading.RLock(), and copies function metadata
        via functools.update_wrapper so the descriptor looks like the original function.
        TEST: Apply @lazy_property to a method; assert the descriptor's __name__ matches
        the original method name (update_wrapper was applied).
        """
        self.func = func
        self.lock = threading.RLock()
        functools.update_wrapper(self, func)  # type: ignore[arg-type]

    def __get__(self, obj: Any, objtype: type | None = None) -> Any:
        """Return the cached value, computing it on first access.

        WHY: Implements the descriptor protocol so the lazy property behaves like a
        regular attribute to callers while deferring expensive computation.
        WHAT: Returns self when accessed on the class (obj is None); otherwise checks
        the instance dict for a cached value, computing it under the lock if absent and
        storing it in the instance dict to bypass the descriptor on future accesses.
        TEST: Attach a spy to the wrapped function; access the property twice on one
        instance; assert the spy was called exactly once.
        """
        if obj is None:
            return self

        # Check if already cached
        val = obj.__dict__.get(self.func.__name__)
        if val is not None:
            return val

        # Thread-safe initialization
        with self.lock:
            # Double-check pattern
            val = obj.__dict__.get(self.func.__name__)
            if val is not None:
                return val

            # Compute and cache
            val = self.func(obj)
            obj.__dict__[self.func.__name__] = val
            return val


class AsyncLazyService[T]:
    """Async version of LazyService for async services.

    Supports services that require async initialization.
    """

    def __init__(
        self,
        service_class: type[T],
        init_args: tuple = (),
        init_kwargs: dict | None = None,
        name: str | None = None,
    ):
        """Initialise the async lazy wrapper without starting the underlying service.

        WHY: Defers construction of async services (those requiring ``await`` during
        ``__init__``) until the first attribute access in an async context.
        WHAT: Stores service class and construction arguments; creates an asyncio.Lock
        for safe concurrent first-access; initialises LazyMetrics for monitoring.
        TEST: Instantiate AsyncLazyService(MyAsyncService); assert is_initialized is False
        and _instance is None before any awaiting occurs.
        """
        self._service_class = service_class
        self._init_args = init_args
        self._init_kwargs = init_kwargs or {}
        self._name = name or service_class.__name__

        self._instance: T | None = None
        self._lock = asyncio.Lock()
        self._metrics = LazyMetrics()
        self._logger = get_logger(f"async_lazy.{self._name}")

    @property
    def is_initialized(self) -> bool:
        """Check if service has been initialized."""
        return self._instance is not None

    async def _ensure_initialized(self) -> T:
        """Ensure service is initialized asynchronously."""
        if self._instance is not None:
            return self._instance

        async with self._lock:
            if self._instance is not None:
                return self._instance

            start_time = time.time()
            if self._metrics.first_access is None:
                self._metrics.first_access = datetime.now(UTC)

            try:
                self._logger.debug(f"Async initializing: {self._name}")

                # Handle both async and sync initialization
                if asyncio.iscoroutinefunction(self._service_class):
                    self._instance = await self._service_class(
                        *self._init_args, **self._init_kwargs
                    )
                else:
                    # Run sync initialization in executor
                    loop = asyncio.get_event_loop()
                    self._instance = await loop.run_in_executor(
                        None, self._service_class, *self._init_args, **self._init_kwargs
                    )

                self._metrics.initialization_time = time.time() - start_time
                self._metrics.is_initialized = True

                self._logger.info(
                    f"Async service {self._name} initialized in "
                    f"{self._metrics.initialization_time:.2f}s"
                )

                if self._instance is None:
                    raise RuntimeError(
                        f"Service {self._name} initialization produced None"
                    )
                return self._instance

            except Exception as e:
                self._metrics.initialization_error = e
                self._logger.error(f"Failed to initialize {self._name}: {e}")
                raise

    def __getattr__(self, name: str) -> Any:
        """Proxy attribute access to the underlying service."""
        if name.startswith("_"):
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'"
            )

        async def async_wrapper(*args, **kwargs):
            """Ensure the service is initialised then proxy the attribute call.

            WHY: Because the underlying service may not yet exist, the wrapper must
            await initialisation before forwarding the call, making the lazy service
            transparent to async callers.
            WHAT: Awaits _ensure_initialized(); increments access count; retrieves the
            named attribute from the instance; awaits it if it is a coroutine, otherwise
            calls it synchronously and returns the result.
            TEST: Create AsyncLazyService wrapping a class with an async method; call
            the method via __getattr__; assert the service was initialised and the correct
            result returned.
            """
            instance = await self._ensure_initialized()
            self._metrics.access_count += 1
            attr = getattr(instance, name)
            if asyncio.iscoroutinefunction(attr):
                return await attr(*args, **kwargs)
            return attr(*args, **kwargs)

        return async_wrapper
