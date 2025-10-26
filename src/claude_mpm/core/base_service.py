"""
Consolidated Base Service for Claude PM Framework.

Combines functionality from:
- base_service.py (basic service infrastructure)
- enhanced_base_service.py (advanced features)

Provides:
- Lifecycle management (start, stop, health checks)
- Configuration management
- Logging with optional structured context
- Metrics collection and performance monitoring
- Error handling with optional circuit breaker
- Optional dependency injection support
- Service discovery and registration
- Background task management
"""

import asyncio
import logging
import os
import signal
import threading
import time
import traceback
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import Config
from .enums import HealthStatus
from .mixins import LoggerMixin


@dataclass
class ServiceHealth:
    """Service health status information."""

    status: HealthStatus  # Type-safe health status using enum
    message: str
    timestamp: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    checks: Dict[str, bool] = field(default_factory=dict)


@dataclass
class ServiceMetrics:
    """Service metrics collection."""

    requests_total: int = 0
    requests_failed: int = 0
    response_time_avg: float = 0.0
    uptime_seconds: int = 0
    memory_usage_mb: float = 0.0
    custom_metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ServiceContext:
    """Service execution context with request tracking (enhanced feature)."""

    request_id: str
    start_time: float
    service_name: str
    operation: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CircuitBreakerState:
    """Circuit breaker state for service resilience (enhanced feature)."""

    failure_count: int = 0
    last_failure_time: Optional[float] = None
    state: str = "closed"  # closed, open, half_open
    failure_threshold: int = 5
    timeout_seconds: int = 60
    success_threshold: int = 3  # For half-open state


class BaseService(LoggerMixin, ABC):
    """
    Base class for all Claude PM services with optional enhanced features.

    Basic features (always enabled):
    - Lifecycle management
    - Configuration
    - Logging
    - Metrics
    - Health checks
    - Background tasks

    Enhanced features (optional):
    - Dependency injection
    - Circuit breaker pattern
    - Request tracking
    - Performance monitoring
    - Structured logging context
    """

    def __init__(
        self,
        name: str,
        config: Optional[Dict[str, Any]] = None,
        config_path: Optional[Path] = None,
        enable_enhanced_features: bool = False,
        container: Optional[Any] = None,
    ):
        """
        Initialize the base service.

        Args:
            name: Service name for identification
            config: Optional configuration dictionary
            config_path: Optional path to configuration file
            enable_enhanced_features: Enable circuit breaker, request tracking, etc.
            container: Optional service container for dependency injection
        """
        self.name = name
        # Use singleton Config instance to prevent duplicate configuration loading
        # Only pass config_path if it's different from what might already be loaded
        if config_path:
            self.config = Config(config or {}, config_path)
        else:
            # Use existing singleton instance without forcing reload
            self.config = Config(config or {})
        self._enable_enhanced = enable_enhanced_features
        self._container = container

        # Set custom logger name based on service name
        self._logger_name = (
            f"{self.__class__.__module__}.{self.__class__.__name__}.{name}"
        )

        # Service state
        self._running = False
        self._start_time: Optional[datetime] = None
        self._stop_event = asyncio.Event()
        self._shutdown_timeout = timedelta(seconds=30)

        # Health and metrics
        self._health = ServiceHealth(
            status=HealthStatus.UNKNOWN,
            message="Service not started",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._metrics = ServiceMetrics()
        self._last_health_check: Optional[float] = None

        # Background tasks
        self._background_tasks: List[asyncio.Task] = []

        # Enhanced features (only initialized if enabled)
        if self._enable_enhanced:
            self._init_enhanced_features()

        # Check for quiet mode
        if os.getenv("CLAUDE_PM_QUIET_MODE") == "true":
            self.logger.setLevel(logging.WARNING)

        # Only log if not in quiet mode
        if os.environ.get("CLAUDE_PM_QUIET_MODE", "").lower() != "true":
            self.logger.debug(f"Initialized {self.name} service")

    def _init_enhanced_features(self):
        """Initialize enhanced features when enabled."""
        # Circuit breaker for resilience
        self._circuit_breaker = CircuitBreakerState()

        # Error tracking
        self._error_counts: Dict[str, int] = {}

        # Request tracking
        self._request_contexts: Dict[str, ServiceContext] = {}

        # Performance metrics
        self._performance_metrics: Dict[str, List[float]] = {}

        # Thread safety
        self._lock = threading.RLock()

        # Optional service dependencies
        self._health_monitor: Optional[Any] = None
        self._error_handler: Optional[Any] = None
        self._cache: Optional[Any] = None

        # Register dependencies if container provided
        if self._container:
            self._register_service_dependencies()

    @property
    def running(self) -> bool:
        """Check if service is currently running."""
        return self._running

    @property
    def uptime(self) -> Optional[float]:
        """Get service uptime in seconds."""
        if self._start_time and self._running:
            return (datetime.now(timezone.utc) - self._start_time).total_seconds()
        return None

    @property
    def health(self) -> ServiceHealth:
        """Get current service health status."""
        return self._health

    @property
    def metrics(self) -> ServiceMetrics:
        """Get current service metrics."""
        if self.uptime:
            self._metrics.uptime_seconds = int(self.uptime)
        return self._metrics

    async def start(self) -> None:
        """Start the service."""
        if self._running:
            self.logger.warning(f"Service {self.name} is already running")
            return

        self.logger.info(f"Starting {self.name} service...")

        try:
            # Use context manager if enhanced features enabled
            if self._enable_enhanced:
                async with self._service_operation("start"):
                    await self._start_internal()
            else:
                await self._start_internal()

            self.logger.info(f"Service {self.name} started successfully")

        except Exception as e:
            self.logger.error(f"Failed to start service {self.name}: {e}")
            self._health = ServiceHealth(
                status=HealthStatus.UNHEALTHY,
                message=f"Startup failed: {e!s}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                checks={"startup": False},
            )

            if self._enable_enhanced and hasattr(self, "_handle_error"):
                await self._handle_error(
                    e, {"operation": "start", "service": self.name}
                )
            raise

    async def _start_internal(self):
        """Internal start logic."""
        # Setup signal handlers
        self._setup_signal_handlers()

        # Initialize dependencies if enhanced
        if self._enable_enhanced and hasattr(self, "_initialize_dependencies"):
            await self._initialize_dependencies()

        # Initialize service
        await self._initialize()

        # Start background tasks
        await self._start_background_tasks()

        # Register with health monitor if available
        if self._enable_enhanced and hasattr(self, "_register_with_health_monitor"):
            await self._register_with_health_monitor()

        # Mark as running
        self._running = True
        self._start_time = datetime.now(timezone.utc)

        # Update health status
        self._health = ServiceHealth(
            status=HealthStatus.HEALTHY,
            message="Service started successfully",
            timestamp=datetime.now(timezone.utc).isoformat(),
            checks={"startup": True},
            metrics=self._get_health_metrics() if self._enable_enhanced else {},
        )

    async def stop(self) -> None:
        """Stop the service gracefully."""
        if not self._running:
            self.logger.warning(f"Service {self.name} is not running")
            return

        self.logger.info(f"Stopping {self.name} service...")

        try:
            # Apply timeout if enhanced features enabled
            if self._enable_enhanced:
                async with asyncio.timeout(self._shutdown_timeout.total_seconds()):
                    await self._stop_internal()
            else:
                await self._stop_internal()

            self.logger.info(f"Service {self.name} stopped successfully")

        except asyncio.TimeoutError:
            self.logger.error(f"Service {self.name} shutdown timeout exceeded")
            # Force stop background tasks
            for task in self._background_tasks:
                if not task.done():
                    task.cancel()
            raise
        except Exception as e:
            self.logger.error(f"Error stopping service {self.name}: {e}")
            if self._enable_enhanced and hasattr(self, "_handle_error"):
                await self._handle_error(e, {"operation": "stop", "service": self.name})
            raise

    async def _stop_internal(self):
        """Internal stop logic."""
        # Signal stop to background tasks
        self._stop_event.set()

        # Unregister from health monitor if available
        if self._enable_enhanced and hasattr(self, "_unregister_from_health_monitor"):
            await self._unregister_from_health_monitor()

        # Cancel background tasks
        for task in self._background_tasks:
            if not task.done():
                task.cancel()

        # Wait for tasks to complete
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)

        # Cleanup service
        await self._cleanup()

        # Mark as stopped
        self._running = False

        # Update health status
        self._health = ServiceHealth(
            status=HealthStatus.UNKNOWN,
            message="Service stopped",
            timestamp=datetime.now(timezone.utc).isoformat(),
            checks={"running": False},
        )

    async def restart(self) -> None:
        """Restart the service."""
        self.logger.info(f"Restarting {self.name} service...")
        await self.stop()
        await self.start()

    async def health_check(self) -> ServiceHealth:
        """
        Perform comprehensive health check.

        Returns:
            ServiceHealth object with current status
        """
        try:
            # Use enhanced health check if enabled
            if self._enable_enhanced and hasattr(self, "_enhanced_health_check"):
                return await self._enhanced_health_check()

            # Basic health check
            checks = {}

            # Basic running check
            checks["running"] = self._running

            # Custom health checks
            custom_checks = await self._health_check()
            checks.update(custom_checks)

            # Determine overall status
            if not checks["running"]:
                status = HealthStatus.UNHEALTHY
                message = "Service is not running"
            elif all(checks.values()):
                status = HealthStatus.HEALTHY
                message = "All health checks passed"
            elif any(checks.values()):
                status = HealthStatus.DEGRADED
                message = "Some health checks failed"
            else:
                status = HealthStatus.UNHEALTHY
                message = "Multiple health checks failed"

            # Update health status
            self._health = ServiceHealth(
                status=status,
                message=message,
                timestamp=datetime.now(timezone.utc).isoformat(),
                checks=checks,
                metrics={
                    "uptime": self.uptime,
                    "requests_total": self._metrics.requests_total,
                    "requests_failed": self._metrics.requests_failed,
                },
            )

            return self._health

        except Exception as e:
            self.logger.error(f"Health check failed for {self.name}: {e}")
            self._health = ServiceHealth(
                status=HealthStatus.UNHEALTHY,
                message=f"Health check error: {e!s}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                checks={"health_check_error": True},
            )
            return self._health

    def update_metrics(self, **kwargs) -> None:
        """Update service metrics."""
        for key, value in kwargs.items():
            if hasattr(self._metrics, key):
                setattr(self._metrics, key, value)
            else:
                self._metrics.custom_metrics[key] = value

    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config.get(key, default)

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""

        def signal_handler(signum, frame):
            self.logger.info(
                f"Received signal {signum}, initiating graceful shutdown..."
            )
            # Get the event loop and create a tracked shutdown task
            try:
                loop = asyncio.get_event_loop()
                task = loop.create_task(self.stop())
                # Store reference to prevent GC during shutdown
                if not hasattr(self, "_shutdown_task"):
                    self._shutdown_task = task
            except RuntimeError:
                # No event loop, call stop synchronously
                self.logger.warning("No event loop available for graceful shutdown")

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def _start_background_tasks(self) -> None:
        """Start background tasks."""
        # Health check task
        if self.get_config("enable_health_monitoring", True):
            interval = self.get_config("health_check_interval", 30)
            task = asyncio.create_task(self._health_monitor_task(interval))
            self._background_tasks.append(task)

        # Metrics collection task
        if self.get_config("enable_metrics", True):
            interval = self.get_config("metrics_interval", 60)
            task = asyncio.create_task(self._metrics_task(interval))
            self._background_tasks.append(task)

        # Custom background tasks
        custom_tasks = await self._start_custom_tasks()
        if custom_tasks:
            self._background_tasks.extend(custom_tasks)

    async def _health_monitor_task(self, interval: int) -> None:
        """Background task for periodic health monitoring."""
        while not self._stop_event.is_set():
            try:
                await self.health_check()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Health monitor task error: {e}")
                await asyncio.sleep(interval)

    async def _metrics_task(self, interval: int) -> None:
        """Background task for metrics collection."""
        while not self._stop_event.is_set():
            try:
                await self._collect_metrics()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Metrics task error: {e}")
                await asyncio.sleep(interval)

    async def _collect_metrics(self) -> None:
        """Collect service metrics."""
        try:
            # Update uptime
            if self.uptime:
                self._metrics.uptime_seconds = int(self.uptime)

            # Memory usage (basic implementation)
            try:
                import psutil

                process = psutil.Process()
                self._metrics.memory_usage_mb = process.memory_info().rss / 1024 / 1024
            except ImportError:
                pass

            # Custom metrics collection
            await self._collect_custom_metrics()

        except Exception as e:
            self.logger.warning(f"Failed to collect metrics: {e}")

    # Enhanced features (conditionally included)

    @asynccontextmanager
    async def _service_operation(self, operation: str):
        """Context manager for tracking service operations (enhanced feature)."""
        if not self._enable_enhanced:
            yield
            return

        request_id = f"{self.name}_{operation}_{time.time()}"
        context = ServiceContext(
            request_id=request_id,
            start_time=time.time(),
            service_name=self.name,
            operation=operation,
        )

        self._request_contexts[request_id] = context

        try:
            yield context

            # Record success metrics
            duration = time.time() - context.start_time
            self._record_operation_metrics(operation, duration, success=True)

        except Exception as e:
            # Record failure metrics
            duration = time.time() - context.start_time
            self._record_operation_metrics(operation, duration, success=False)

            # Update error counts
            error_type = type(e).__name__
            self._error_counts[error_type] = self._error_counts.get(error_type, 0) + 1

            raise

        finally:
            # Cleanup context
            self._request_contexts.pop(request_id, None)

    def _record_operation_metrics(
        self, operation: str, duration: float, success: bool
    ) -> None:
        """Record operation performance metrics (enhanced feature)."""
        if not self._enable_enhanced:
            return

        with self._lock:
            # Update general metrics
            self._metrics.requests_total += 1
            if not success:
                self._metrics.requests_failed += 1

            # Update performance tracking
            if operation not in self._performance_metrics:
                self._performance_metrics[operation] = []

            self._performance_metrics[operation].append(duration)

            # Keep only recent metrics (last 100 operations)
            if len(self._performance_metrics[operation]) > 100:
                self._performance_metrics[operation] = self._performance_metrics[
                    operation
                ][-100:]

            # Calculate average
            all_times = []
            for times in self._performance_metrics.values():
                all_times.extend(times)

            if all_times:
                self._metrics.response_time_avg = sum(all_times) / len(all_times)

    async def _enhanced_health_check(self) -> ServiceHealth:
        """Enhanced health check with circuit breaker (enhanced feature)."""
        async with self._service_operation("health_check"):
            # Check circuit breaker state
            if self._circuit_breaker.state == "open":
                if self._should_attempt_circuit_recovery():
                    self._circuit_breaker.state = "half_open"
                    self.logger.info(
                        f"Circuit breaker for {self.name} moved to half-open"
                    )
                else:
                    return ServiceHealth(
                        status=HealthStatus.DEGRADED,
                        message="Service circuit breaker is open",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        checks={"circuit_breaker": False},
                        metrics=self._get_health_metrics(),
                    )

            # Perform standard health check
            health = await self.health_check()

            # Update circuit breaker
            if health.status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED):
                self._record_circuit_success()
            else:
                self._record_circuit_failure()

            return health

    def _should_attempt_circuit_recovery(self) -> bool:
        """Check if circuit breaker should attempt recovery."""
        if not self._enable_enhanced or self._circuit_breaker.last_failure_time is None:
            return True

        time_since_failure = time.time() - self._circuit_breaker.last_failure_time
        return time_since_failure >= self._circuit_breaker.timeout_seconds

    def _record_circuit_failure(self) -> None:
        """Record circuit breaker failure."""
        if not self._enable_enhanced:
            return

        self._circuit_breaker.failure_count += 1
        self._circuit_breaker.last_failure_time = time.time()

        if (
            self._circuit_breaker.failure_count
            >= self._circuit_breaker.failure_threshold
        ) and self._circuit_breaker.state != "open":
            self._circuit_breaker.state = "open"
            self.logger.warning(f"Circuit breaker opened for service {self.name}")

    def _record_circuit_success(self) -> None:
        """Record circuit breaker success."""
        if not self._enable_enhanced:
            return

        if self._circuit_breaker.state == "half_open":
            self._circuit_breaker.failure_count = max(
                0, self._circuit_breaker.failure_count - 1
            )
            if self._circuit_breaker.failure_count == 0:
                self._circuit_breaker.state = "closed"
                self.logger.info(f"Circuit breaker closed for service {self.name}")
        elif self._circuit_breaker.state == "closed":
            self._circuit_breaker.failure_count = max(
                0, self._circuit_breaker.failure_count - 1
            )

    def _get_health_metrics(self) -> Dict[str, Any]:
        """Get metrics for health status."""
        base_metrics = {
            "uptime_seconds": int(self.uptime) if self.uptime else 0,
            "requests_total": self._metrics.requests_total,
            "requests_failed": self._metrics.requests_failed,
            "response_time_avg": self._metrics.response_time_avg,
        }

        if self._enable_enhanced:
            base_metrics.update(
                {
                    "circuit_breaker_state": self._circuit_breaker.state,
                    "error_counts": self._error_counts.copy(),
                }
            )

        return base_metrics

    async def _handle_error(self, error: Exception, context: Dict[str, Any]) -> None:
        """Handle service errors with context (enhanced feature)."""
        if not self._enable_enhanced:
            return

        try:
            if hasattr(self, "_error_handler") and self._error_handler:
                await self._error_handler.handle_error(error, context)
            else:
                # Default error handling
                self.logger.error(
                    f"Service error in {self.name}: {error}",
                    extra={
                        "service": self.name,
                        "context": context,
                        "traceback": traceback.format_exc(),
                    },
                )
        except Exception as handler_error:
            self.logger.error(f"Error handler failed: {handler_error}")

    def _register_service_dependencies(self) -> None:
        """Register service dependencies (enhanced feature)."""
        if not self._container:
            return

        try:
            # Get optional dependencies from container
            # This is a simplified version - real implementation would use interfaces
            if hasattr(self._container, "get_service"):
                self._health_monitor = self._container.get_service(
                    "IHealthMonitor", None
                )
                self._error_handler = self._container.get_service("IErrorHandler", None)
                self._cache = self._container.get_service("ICacheService", None)
        except Exception as e:
            self.logger.warning(f"Failed to register dependencies for {self.name}: {e}")

    async def _initialize_dependencies(self) -> None:
        """Initialize service dependencies (enhanced feature)."""
        # Override in subclasses for specific dependency setup

    async def _register_with_health_monitor(self) -> None:
        """Register service with health monitor (enhanced feature)."""
        if self._enable_enhanced and self._health_monitor:
            try:
                await self._health_monitor.register_service(self)
            except Exception as e:
                self.logger.warning(f"Failed to register with health monitor: {e}")

    async def _unregister_from_health_monitor(self) -> None:
        """Unregister service from health monitor (enhanced feature)."""
        if self._enable_enhanced and self._health_monitor:
            try:
                await self._health_monitor.unregister_service(self.name)
            except Exception as e:
                self.logger.warning(f"Failed to unregister from health monitor: {e}")

    # Abstract methods to be implemented by subclasses

    @abstractmethod
    async def _initialize(self) -> None:
        """Initialize the service. Must be implemented by subclasses."""

    @abstractmethod
    async def _cleanup(self) -> None:
        """Cleanup service resources. Must be implemented by subclasses."""

    async def _health_check(self) -> Dict[str, bool]:
        """
        Perform custom health checks. Override in subclasses.

        Returns:
            Dictionary of check name -> success boolean
        """
        return {}

    async def _start_custom_tasks(self) -> Optional[List[asyncio.Task]]:
        """
        Start custom background tasks. Override in subclasses.

        Returns:
            List of asyncio tasks or None
        """
        return None

    async def _collect_custom_metrics(self) -> None:
        """Collect custom metrics. Override in subclasses.

        METRICS COLLECTION PATTERN:
        This method is called periodically by the metrics task to collect
        service-specific metrics. Subclasses should override this to:

        1. COLLECT OPERATIONAL METRICS:
           - Request rates and latencies
           - Queue depths and processing times
           - Error rates by type
           - Resource utilization

        2. COLLECT BUSINESS METRICS:
           - Agent usage patterns
           - Model selection distribution
           - Task complexity trends
           - Cost tracking metrics

        3. COLLECT PERFORMANCE METRICS:
           - Cache hit rates
           - Database query times
           - API call latencies
           - Memory usage patterns

        EXAMPLE IMPLEMENTATION:
        ```python
        async def _collect_custom_metrics(self) -> None:
            # Collect agent-specific metrics
            if hasattr(self, 'agent_loader'):
                loader_metrics = self.agent_loader.get_metrics()
                self.update_metrics(
                    cache_hit_rate=loader_metrics['cache_hit_rate_percent'],
                    top_agents=loader_metrics['top_agents_by_usage']
                )

            # Collect deployment metrics
            if hasattr(self, 'deployment_service'):
                deploy_metrics = self.deployment_service.get_deployment_metrics()
                self.update_metrics(
                    deployment_success_rate=deploy_metrics['success_rate_percent'],
                    avg_deployment_time=deploy_metrics['average_deployment_time_ms']
                )

            # Collect resource metrics
            import psutil
            process = psutil.Process()
            self.update_metrics(
                cpu_percent=process.cpu_percent(),
                memory_mb=process.memory_info().rss / 1024 / 1024,
                open_files=len(process.open_files()),
                thread_count=process.num_threads()
            )
        ```

        BEST PRACTICES:
        - Keep collection fast (< 100ms)
        - Handle errors gracefully
        - Use sampling for expensive operations
        - Store aggregated data, not raw events
        - Consider metric cardinality
        """

    # Utility methods

    async def run_forever(self) -> None:
        """Run the service until stopped."""
        await self.start()
        try:
            # Wait for stop signal
            while self._running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
        finally:
            await self.stop()

    def __repr__(self) -> str:
        """String representation of the service."""
        enhanced_str = " (enhanced)" if self._enable_enhanced else ""
        return f"<{self.__class__.__name__}(name='{self.name}', running={self._running}{enhanced_str})>"


# For backwards compatibility, create an alias
EnhancedBaseService = BaseService
