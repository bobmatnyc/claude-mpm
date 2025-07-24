"""
Enhanced Base Service Implementation for Claude PM Framework v0.8.0
=================================================================

Enhanced base service class implementing IService interface with:
- Dependency injection support
- Enhanced error handling and recovery
- Structured logging with context
- Service discovery and registration
- Circuit breaker patterns for resilience
- Graceful degradation capabilities
- Performance monitoring and metrics
- Health check orchestration

Key Features:
- Interface-based design
- Automatic dependency resolution
- Comprehensive error handling
- Performance optimization
- Service lifecycle management
- Health monitoring integration
"""

import asyncio
import logging
import signal
import sys
import time
import traceback
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Type, Callable
from pathlib import Path
from contextlib import asynccontextmanager
import json

from .interfaces import (
    IServiceLifecycle, IConfigurationService, IHealthMonitor,
    ICacheService, IServiceContainer, IErrorHandler
)
from .base_service import ServiceHealth, ServiceMetrics
from .container import ServiceContainer
from .mixins import LoggerMixin

logger = logging.getLogger(__name__)


@dataclass
class ServiceContext:
    """Service execution context with request tracking."""
    request_id: str
    start_time: float
    service_name: str
    operation: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CircuitBreakerState:
    """Circuit breaker state for service resilience."""
    failure_count: int = 0
    last_failure_time: Optional[float] = None
    state: str = "closed"  # closed, open, half_open
    failure_threshold: int = 5
    timeout_seconds: int = 60
    success_threshold: int = 3  # For half-open state


class EnhancedBaseService(IServiceLifecycle, LoggerMixin, ABC):
    """
    Enhanced base service implementation with dependency injection and resilience patterns.
    
    Provides comprehensive service infrastructure including:
    - Automatic dependency injection
    - Circuit breaker pattern for resilience
    - Structured logging with context
    - Performance monitoring and metrics
    - Health check orchestration
    - Graceful degradation capabilities
    """
    
    def __init__(self, name: str, config: Optional[IConfigurationService] = None,
                 container: Optional[IServiceContainer] = None):
        """
        Initialize the enhanced base service.
        
        Args:
            name: Service name for identification
            config: Configuration service (injected if not provided)
            container: Service container (uses default if not provided)
        """
        self._name = name
        self._container = container or get_default_container()
        self._config = config or self._get_injected_service(IConfigurationService)
        # Set custom logger name based on service name
        self.logger_name = f"{self.__class__.__module__}.{self.__class__.__name__}.{name}"
        
        # Service state
        self._running = False
        self._start_time: Optional[datetime] = None
        self._stop_event = asyncio.Event()
        self._shutdown_timeout = timedelta(seconds=30)
        
        # Health and metrics
        self._health = ServiceHealth(
            status="unknown",
            message="Service not started",
            timestamp=datetime.now().isoformat(),
            metrics={},
            checks={}
        )
        self._metrics = ServiceMetrics()
        self._last_health_check: Optional[float] = None
        
        # Background tasks and monitoring
        self._background_tasks: List[asyncio.Task] = []
        self._health_monitor: Optional[IHealthMonitor] = None
        
        # Error handling and resilience
        self._error_handler: Optional[IErrorHandler] = None
        self._circuit_breaker = CircuitBreakerState()
        self._error_counts: Dict[str, int] = {}
        
        # Performance tracking
        self._request_contexts: Dict[str, ServiceContext] = {}
        self._performance_metrics: Dict[str, List[float]] = {}
        
        # Cache service for performance optimization
        self._cache: Optional[ICacheService] = None
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Service registration
        self._register_service_dependencies()
        
        # Only log if not in quiet mode
        if not self._is_quiet_mode():
            self.logger.info(f"Enhanced service '{self._name}' initialized")
    
    @property
    def name(self) -> str:
        """Service name for identification."""
        return self._name
    
    @property
    def running(self) -> bool:
        """Check if service is currently running."""
        return self._running
    
    @property
    def uptime(self) -> Optional[timedelta]:
        """Get service uptime."""
        if self._start_time and self._running:
            return datetime.now() - self._start_time
        return None
    
    @property
    def health(self) -> ServiceHealth:
        """Get current service health status."""
        return self._health
    
    def get_metrics(self) -> ServiceMetrics:
        """Get current service metrics."""
        with self._lock:
            if self.uptime:
                self._metrics.uptime_seconds = int(self.uptime.total_seconds())
            return self._metrics
    
    async def start(self) -> None:
        """Start the service with enhanced initialization."""
        if self._running:
            self.logger.warning(f"Service {self._name} is already running")
            return
        
        self.logger.info(f"Starting enhanced service {self._name}...")
        
        try:
            async with self._service_operation("start"):
                # Setup signal handlers
                self._setup_signal_handlers()
                
                # Initialize dependencies
                await self._initialize_dependencies()
                
                # Initialize service
                await self._initialize()
                
                # Start background tasks
                await self._start_background_tasks()
                
                # Register with health monitor
                await self._register_with_health_monitor()
                
                # Mark as running
                self._running = True
                self._start_time = datetime.now()
                
                # Update health status
                self._health = ServiceHealth(
                    status="healthy",
                    message="Service started successfully",
                    timestamp=datetime.now().isoformat(),
                    checks={"startup": True},
                    metrics=self._get_health_metrics()
                )
                
                self.logger.info(f"Enhanced service {self._name} started successfully")
        
        except Exception as e:
            self.logger.error(f"Failed to start service {self._name}: {e}")
            self._health = ServiceHealth(
                status="unhealthy",
                message=f"Startup failed: {str(e)}",
                timestamp=datetime.now().isoformat(),
                checks={"startup": False},
                metrics={}
            )
            
            # Handle startup error
            await self._handle_error(e, {"operation": "start", "service": self._name})
            raise
    
    async def stop(self) -> None:
        """Stop the service gracefully with enhanced cleanup."""
        if not self._running:
            self.logger.warning(f"Service {self._name} is not running")
            return
        
        self.logger.info(f"Stopping enhanced service {self._name}...")
        
        try:
            async with asyncio.timeout(self._shutdown_timeout.total_seconds()):
                async with self._service_operation("stop"):
                    # Signal stop to background tasks
                    self._stop_event.set()
                    
                    # Unregister from health monitor
                    await self._unregister_from_health_monitor()
                    
                    # Cancel background tasks
                    await self._stop_background_tasks()
                    
                    # Cleanup service
                    await self._cleanup()
                    
                    # Mark as stopped
                    self._running = False
                    
                    # Update health status
                    self._health = ServiceHealth(
                        status="unknown",
                        message="Service stopped",
                        timestamp=datetime.now().isoformat(),
                        checks={"running": False},
                        metrics={}
                    )
                    
                    self.logger.info(f"Enhanced service {self._name} stopped successfully")
        
        except asyncio.TimeoutError:
            self.logger.error(f"Service {self._name} shutdown timeout exceeded")
            # Force stop background tasks
            for task in self._background_tasks:
                if not task.done():
                    task.cancel()
            raise
        
        except Exception as e:
            self.logger.error(f"Error stopping service {self._name}: {e}")
            await self._handle_error(e, {"operation": "stop", "service": self._name})
            raise
    
    async def restart(self) -> None:
        """Restart the service."""
        self.logger.info(f"Restarting enhanced service {self._name}...")
        await self.stop()
        await self.start()
    
    async def health_check(self) -> ServiceHealth:
        """Perform comprehensive health check with circuit breaker."""
        try:
            async with self._service_operation("health_check"):
                # Check circuit breaker state
                if self._circuit_breaker.state == "open":
                    if self._should_attempt_circuit_recovery():
                        self._circuit_breaker.state = "half_open"
                        self.logger.info(f"Circuit breaker for {self._name} moved to half-open")
                    else:
                        return ServiceHealth(
                            status="degraded",
                            message="Service circuit breaker is open",
                            timestamp=datetime.now().isoformat(),
                            checks={"circuit_breaker": False},
                            metrics=self._get_health_metrics()
                        )
                
                checks = {}
                
                # Basic running check
                checks["running"] = self._running
                
                # Performance checks
                checks["performance"] = self._check_performance_health()
                
                # Resource checks
                checks["resources"] = await self._check_resource_health()
                
                # Custom health checks
                custom_checks = await self._health_check()
                checks.update(custom_checks)
                
                # Determine overall status
                status = self._determine_health_status(checks)
                
                # Update circuit breaker
                if status in ["healthy", "degraded"]:
                    self._record_circuit_success()
                else:
                    self._record_circuit_failure()
                
                # Update health status
                self._health = ServiceHealth(
                    status=status,
                    message=self._get_health_message(status, checks),
                    timestamp=datetime.now().isoformat(),
                    checks=checks,
                    metrics=self._get_health_metrics()
                )
                
                self._last_health_check = time.time()
                return self._health
        
        except Exception as e:
            self.logger.error(f"Health check failed for {self._name}: {e}")
            self._record_circuit_failure()
            
            self._health = ServiceHealth(
                status="unhealthy",
                message=f"Health check error: {str(e)}",
                timestamp=datetime.now().isoformat(),
                checks={"health_check_error": True},
                metrics={}
            )
            
            await self._handle_error(e, {"operation": "health_check", "service": self._name})
            return self._health
    
    # Enhanced service operation context manager
    @asynccontextmanager
    async def _service_operation(self, operation: str):
        """Context manager for tracking service operations."""
        request_id = f"{self._name}_{operation}_{time.time()}"
        context = ServiceContext(
            request_id=request_id,
            start_time=time.time(),
            service_name=self._name,
            operation=operation
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
    
    # Dependency injection helpers
    def _get_injected_service(self, service_type: Type) -> Optional[Any]:
        """Get service from container if available."""
        try:
            if self._container and self._container.has_service(service_type):
                return self._container.get_service(service_type)
        except Exception as e:
            self.logger.warning(f"Failed to inject service {service_type}: {e}")
        return None
    
    def _register_service_dependencies(self) -> None:
        """Register this service's dependencies."""
        try:
            # Get optional dependencies
            self._health_monitor = self._get_injected_service(IHealthMonitor)
            self._error_handler = self._get_injected_service(IErrorHandler)
            self._cache = self._get_injected_service(ICacheService)
            
        except Exception as e:
            self.logger.warning(f"Failed to register dependencies for {self._name}: {e}")
    
    async def _initialize_dependencies(self) -> None:
        """Initialize service dependencies."""
        # This can be overridden by subclasses for specific dependency setup
        pass
    
    # Error handling and resilience
    async def _handle_error(self, error: Exception, context: Dict[str, Any]) -> None:
        """Handle service errors with context."""
        try:
            if self._error_handler:
                await self._error_handler.handle_error(error, context)
            else:
                # Default error handling
                self.logger.error(
                    f"Service error in {self._name}: {error}",
                    extra={
                        "service": self._name,
                        "context": context,
                        "traceback": traceback.format_exc()
                    }
                )
        except Exception as handler_error:
            self.logger.error(f"Error handler failed: {handler_error}")
    
    def _record_circuit_failure(self) -> None:
        """Record circuit breaker failure."""
        self._circuit_breaker.failure_count += 1
        self._circuit_breaker.last_failure_time = time.time()
        
        if self._circuit_breaker.failure_count >= self._circuit_breaker.failure_threshold:
            if self._circuit_breaker.state != "open":
                self._circuit_breaker.state = "open"
                self.logger.warning(f"Circuit breaker opened for service {self._name}")
    
    def _record_circuit_success(self) -> None:
        """Record circuit breaker success."""
        if self._circuit_breaker.state == "half_open":
            self._circuit_breaker.failure_count = max(0, self._circuit_breaker.failure_count - 1)
            if self._circuit_breaker.failure_count == 0:
                self._circuit_breaker.state = "closed"
                self.logger.info(f"Circuit breaker closed for service {self._name}")
        elif self._circuit_breaker.state == "closed":
            self._circuit_breaker.failure_count = max(0, self._circuit_breaker.failure_count - 1)
    
    def _should_attempt_circuit_recovery(self) -> bool:
        """Check if circuit breaker should attempt recovery."""
        if self._circuit_breaker.last_failure_time is None:
            return True
        
        time_since_failure = time.time() - self._circuit_breaker.last_failure_time
        return time_since_failure >= self._circuit_breaker.timeout_seconds
    
    # Performance and metrics
    def _record_operation_metrics(self, operation: str, duration: float, success: bool) -> None:
        """Record operation performance metrics."""
        with self._lock:
            # Update general metrics
            self._metrics.requests_total += 1
            if not success:
                self._metrics.requests_failed += 1
            
            # Update average response time
            if operation not in self._performance_metrics:
                self._performance_metrics[operation] = []
            
            self._performance_metrics[operation].append(duration)
            
            # Keep only recent metrics (last 100 operations)
            if len(self._performance_metrics[operation]) > 100:
                self._performance_metrics[operation] = self._performance_metrics[operation][-100:]
            
            # Calculate average
            operation_times = []
            for times in self._performance_metrics.values():
                operation_times.extend(times)
            
            if operation_times:
                self._metrics.response_time_avg = sum(operation_times) / len(operation_times)
    
    def _check_performance_health(self) -> bool:
        """Check service performance health."""
        try:
            # Check if average response time is reasonable
            if self._metrics.response_time_avg > 10.0:  # 10 seconds threshold
                return False
            
            # Check error rate
            if self._metrics.requests_total > 0:
                error_rate = self._metrics.requests_failed / self._metrics.requests_total
                if error_rate > 0.1:  # 10% error rate threshold
                    return False
            
            return True
        except Exception:
            return False
    
    async def _check_resource_health(self) -> bool:
        """Check resource health (memory, CPU, etc.)."""
        try:
            import psutil
            
            # Check memory usage
            memory_usage = psutil.virtual_memory().percent
            if memory_usage > 90:  # 90% memory usage threshold
                return False
            
            # Check CPU usage
            cpu_usage = psutil.cpu_percent(interval=0.1)
            if cpu_usage > 95:  # 95% CPU usage threshold
                return False
            
            return True
        except ImportError:
            # psutil not available, assume healthy
            return True
        except Exception:
            return False
    
    def _determine_health_status(self, checks: Dict[str, bool]) -> str:
        """Determine overall health status from checks."""
        if not checks.get("running", False):
            return "unhealthy"
        
        failed_checks = [k for k, v in checks.items() if not v]
        
        if not failed_checks:
            return "healthy"
        elif len(failed_checks) <= 2:  # Allow some degradation
            return "degraded"
        else:
            return "unhealthy"
    
    def _get_health_message(self, status: str, checks: Dict[str, bool]) -> str:
        """Get health message based on status and checks."""
        if status == "healthy":
            return "All health checks passed"
        elif status == "degraded":
            failed = [k for k, v in checks.items() if not v]
            return f"Some checks failed: {', '.join(failed)}"
        else:
            failed = [k for k, v in checks.items() if not v]
            return f"Multiple checks failed: {', '.join(failed)}"
    
    def _get_health_metrics(self) -> Dict[str, Any]:
        """Get metrics for health status."""
        return {
            "uptime_seconds": int(self.uptime.total_seconds()) if self.uptime else 0,
            "requests_total": self._metrics.requests_total,
            "requests_failed": self._metrics.requests_failed,
            "response_time_avg": self._metrics.response_time_avg,
            "circuit_breaker_state": self._circuit_breaker.state,
            "error_counts": self._error_counts.copy()
        }
    
    # Logger mixin provides self.logger automatically
    
    def _is_quiet_mode(self) -> bool:
        """Check if service should run in quiet mode."""
        import os
        return os.getenv('CLAUDE_PM_QUIET_MODE', '').lower() == 'true'
    
    # Background task management
    async def _start_background_tasks(self) -> None:
        """Start background tasks with enhanced monitoring."""
        try:
            # Health monitoring task
            if self._config and self._config.get("enable_health_monitoring", True):
                interval = self._config.get("health_check_interval", 30)
                task = asyncio.create_task(self._health_monitor_task(interval))
                self._background_tasks.append(task)
            
            # Metrics collection task
            if self._config and self._config.get("enable_metrics", True):
                interval = self._config.get("metrics_interval", 60)
                task = asyncio.create_task(self._metrics_task(interval))
                self._background_tasks.append(task)
            
            # Custom background tasks
            custom_tasks = await self._start_custom_tasks()
            if custom_tasks:
                self._background_tasks.extend(custom_tasks)
        
        except Exception as e:
            self.logger.error(f"Failed to start background tasks: {e}")
            raise
    
    async def _stop_background_tasks(self) -> None:
        """Stop background tasks gracefully."""
        if not self._background_tasks:
            return
        
        # Cancel all tasks
        for task in self._background_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        try:
            await asyncio.wait_for(
                asyncio.gather(*self._background_tasks, return_exceptions=True),
                timeout=5.0
            )
        except asyncio.TimeoutError:
            self.logger.warning("Background tasks did not complete within timeout")
        
        self._background_tasks.clear()
    
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
        """Collect enhanced service metrics."""
        try:
            # Update uptime
            if self.uptime:
                self._metrics.uptime_seconds = int(self.uptime.total_seconds())
            
            # Memory usage
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
    
    # Health monitor integration
    async def _register_with_health_monitor(self) -> None:
        """Register service with health monitor."""
        if self._health_monitor:
            try:
                await self._health_monitor.register_service(self)
            except Exception as e:
                self.logger.warning(f"Failed to register with health monitor: {e}")
    
    async def _unregister_from_health_monitor(self) -> None:
        """Unregister service from health monitor."""
        if self._health_monitor:
            try:
                await self._health_monitor.unregister_service(self._name)
            except Exception as e:
                self.logger.warning(f"Failed to unregister from health monitor: {e}")
    
    # Signal handling
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.logger.info(f"Service {self._name} received signal {signum}, initiating graceful shutdown...")
            asyncio.create_task(self.stop())
        
        try:
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
        except ValueError:
            # Not running in main thread
            pass
    
    # Abstract methods to be implemented by subclasses
    @abstractmethod
    async def _initialize(self) -> None:
        """Initialize the service. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    async def _cleanup(self) -> None:
        """Cleanup service resources. Must be implemented by subclasses."""
        pass
    
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
        """Collect custom metrics. Override in subclasses."""
        pass
    
    # Utility methods
    async def run_forever(self) -> None:
        """Run the service until stopped."""
        await self.start()
        try:
            while self._running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
        finally:
            await self.stop()
    
    def __repr__(self) -> str:
        """String representation of the service."""
        return f"<{self.__class__.__name__}(name='{self._name}', running={self._running})>"