"""Advanced health monitoring system for claude-mpm Socket.IO server.

This module provides comprehensive health checking capabilities including:
- Process resource monitoring (CPU, memory, file descriptors)
- Service-specific health markers
- Configurable thresholds and intervals
- Health status aggregation and history
- Integration with automatic recovery mechanisms

Design Principles:
- Minimal performance impact through efficient polling
- Extensible metric collection system
- Circuit breaker integration for failure detection
- Comprehensive logging for debugging and diagnostics
"""

import asyncio
import logging
import time
import threading
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Union
import json
import socket

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None


class HealthStatus(Enum):
    """Health status levels for monitoring."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthMetric:
    """Individual health metric data structure."""
    name: str
    value: Union[int, float, str, bool]
    status: HealthStatus
    threshold: Optional[Union[int, float]] = None
    unit: Optional[str] = None
    timestamp: float = None
    message: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metric to dictionary format."""
        result = asdict(self)
        result['status'] = self.status.value
        result['timestamp_iso'] = datetime.fromtimestamp(self.timestamp, timezone.utc).isoformat()
        return result


@dataclass
class HealthCheckResult:
    """Result of a health check operation."""
    overall_status: HealthStatus
    metrics: List[HealthMetric]
    timestamp: float
    duration_ms: float
    errors: List[str]
    
    def __post_init__(self):
        if not hasattr(self, 'timestamp') or self.timestamp is None:
            self.timestamp = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert health check result to dictionary format."""
        return {
            'overall_status': self.overall_status.value,
            'metrics': [metric.to_dict() for metric in self.metrics],
            'timestamp': self.timestamp,
            'timestamp_iso': datetime.fromtimestamp(self.timestamp, timezone.utc).isoformat(),
            'duration_ms': self.duration_ms,
            'errors': self.errors,
            'metric_count': len(self.metrics),
            'healthy_metrics': len([m for m in self.metrics if m.status == HealthStatus.HEALTHY]),
            'warning_metrics': len([m for m in self.metrics if m.status == HealthStatus.WARNING]),
            'critical_metrics': len([m for m in self.metrics if m.status == HealthStatus.CRITICAL])
        }


class HealthChecker(ABC):
    """Abstract base class for health checkers.
    
    Health checkers implement specific monitoring logic for different aspects
    of the system (process resources, network connectivity, service health, etc.).
    """
    
    @abstractmethod
    def get_name(self) -> str:
        """Get the name of this health checker."""
        pass
    
    @abstractmethod
    async def check_health(self) -> List[HealthMetric]:
        """Perform health check and return metrics."""
        pass


class ProcessResourceChecker(HealthChecker):
    """Health checker for process resource usage.
    
    Monitors:
    - CPU usage percentage
    - Memory usage (RSS, VMS)
    - File descriptor count
    - Thread count
    - Process status
    """
    
    def __init__(self, pid: int, cpu_threshold: float = 80.0, 
                 memory_threshold_mb: int = 500, fd_threshold: int = 1000):
        """Initialize process resource checker.
        
        Args:
            pid: Process ID to monitor
            cpu_threshold: CPU usage threshold as percentage
            memory_threshold_mb: Memory usage threshold in MB
            fd_threshold: File descriptor count threshold
        """
        self.pid = pid
        self.cpu_threshold = cpu_threshold
        self.memory_threshold_mb = memory_threshold_mb
        self.fd_threshold = fd_threshold
        self.process = None
        self.logger = logging.getLogger(f"{__name__}.ProcessResourceChecker")
        
        if PSUTIL_AVAILABLE:
            try:
                self.process = psutil.Process(pid)
            except psutil.NoSuchProcess:
                self.logger.warning(f"Process {pid} not found for monitoring")
    
    def get_name(self) -> str:
        return f"process_resources_{self.pid}"
    
    async def check_health(self) -> List[HealthMetric]:
        """Check process resource usage."""
        metrics = []
        
        if not PSUTIL_AVAILABLE:
            metrics.append(HealthMetric(
                name="psutil_availability",
                value=False,
                status=HealthStatus.WARNING,
                message="psutil not available for enhanced monitoring"
            ))
            return metrics
        
        if not self.process:
            metrics.append(HealthMetric(
                name="process_exists",
                value=False,
                status=HealthStatus.CRITICAL,
                message=f"Process {self.pid} not found"
            ))
            return metrics
        
        try:
            # Check if process still exists
            if not self.process.is_running():
                metrics.append(HealthMetric(
                    name="process_exists",
                    value=False,
                    status=HealthStatus.CRITICAL,
                    message=f"Process {self.pid} is no longer running"
                ))
                return metrics
            
            # Process status
            status = self.process.status()
            process_healthy = status not in [psutil.STATUS_ZOMBIE, psutil.STATUS_DEAD, psutil.STATUS_STOPPED]
            metrics.append(HealthMetric(
                name="process_status",
                value=status,
                status=HealthStatus.HEALTHY if process_healthy else HealthStatus.CRITICAL,
                message=f"Process status: {status}"
            ))
            
            # CPU usage
            try:
                cpu_percent = self.process.cpu_percent(interval=0.1)
                cpu_status = HealthStatus.HEALTHY
                if cpu_percent > self.cpu_threshold:
                    cpu_status = HealthStatus.WARNING if cpu_percent < self.cpu_threshold * 1.2 else HealthStatus.CRITICAL
                
                metrics.append(HealthMetric(
                    name="cpu_usage_percent",
                    value=round(cpu_percent, 2),
                    status=cpu_status,
                    threshold=self.cpu_threshold,
                    unit="%"
                ))
            except Exception as e:
                metrics.append(HealthMetric(
                    name="cpu_usage_percent",
                    value=-1,
                    status=HealthStatus.UNKNOWN,
                    message=f"Failed to get CPU usage: {e}"
                ))
            
            # Memory usage
            try:
                memory_info = self.process.memory_info()
                memory_mb = memory_info.rss / (1024 * 1024)
                memory_status = HealthStatus.HEALTHY
                if memory_mb > self.memory_threshold_mb:
                    memory_status = HealthStatus.WARNING if memory_mb < self.memory_threshold_mb * 1.2 else HealthStatus.CRITICAL
                
                metrics.append(HealthMetric(
                    name="memory_usage_mb",
                    value=round(memory_mb, 2),
                    status=memory_status,
                    threshold=self.memory_threshold_mb,
                    unit="MB"
                ))
                
                metrics.append(HealthMetric(
                    name="memory_vms_mb",
                    value=round(memory_info.vms / (1024 * 1024), 2),
                    status=HealthStatus.HEALTHY,
                    unit="MB"
                ))
            except Exception as e:
                metrics.append(HealthMetric(
                    name="memory_usage_mb",
                    value=-1,
                    status=HealthStatus.UNKNOWN,
                    message=f"Failed to get memory usage: {e}"
                ))
            
            # File descriptors (Unix only)
            if hasattr(self.process, 'num_fds'):
                try:
                    fd_count = self.process.num_fds()
                    fd_status = HealthStatus.HEALTHY
                    if fd_count > self.fd_threshold:
                        fd_status = HealthStatus.WARNING if fd_count < self.fd_threshold * 1.2 else HealthStatus.CRITICAL
                    
                    metrics.append(HealthMetric(
                        name="file_descriptors",
                        value=fd_count,
                        status=fd_status,
                        threshold=self.fd_threshold
                    ))
                except Exception as e:
                    metrics.append(HealthMetric(
                        name="file_descriptors",
                        value=-1,
                        status=HealthStatus.UNKNOWN,
                        message=f"Failed to get file descriptor count: {e}"
                    ))
            
            # Thread count
            try:
                thread_count = self.process.num_threads()
                metrics.append(HealthMetric(
                    name="thread_count",
                    value=thread_count,
                    status=HealthStatus.HEALTHY,
                ))
            except Exception as e:
                metrics.append(HealthMetric(
                    name="thread_count",
                    value=-1,
                    status=HealthStatus.UNKNOWN,
                    message=f"Failed to get thread count: {e}"
                ))
            
            # Process create time (for validation)
            try:
                create_time = self.process.create_time()
                metrics.append(HealthMetric(
                    name="process_start_time",
                    value=create_time,
                    status=HealthStatus.HEALTHY,
                    unit="timestamp"
                ))
            except Exception as e:
                metrics.append(HealthMetric(
                    name="process_start_time",
                    value=-1,
                    status=HealthStatus.UNKNOWN,
                    message=f"Failed to get process start time: {e}"
                ))
                
        except psutil.NoSuchProcess:
            metrics.append(HealthMetric(
                name="process_exists",
                value=False,
                status=HealthStatus.CRITICAL,
                message=f"Process {self.pid} no longer exists"
            ))
        except Exception as e:
            self.logger.error(f"Error checking process health: {e}")
            metrics.append(HealthMetric(
                name="process_check_error",
                value=str(e),
                status=HealthStatus.UNKNOWN,
                message=f"Unexpected error during process health check: {e}"
            ))
        
        return metrics


class NetworkConnectivityChecker(HealthChecker):
    """Health checker for network connectivity.
    
    Monitors:
    - Port availability and binding status
    - Socket connection health
    - Network interface status
    """
    
    def __init__(self, host: str, port: int, timeout: float = 1.0):
        """Initialize network connectivity checker.
        
        Args:
            host: Host address to check
            port: Port number to check
            timeout: Connection timeout in seconds
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.logger = logging.getLogger(f"{__name__}.NetworkConnectivityChecker")
    
    def get_name(self) -> str:
        return f"network_connectivity_{self.host}_{self.port}"
    
    async def check_health(self) -> List[HealthMetric]:
        """Check network connectivity."""
        metrics = []
        
        # Check port binding
        try:
            # Try to connect to the port
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((self.host, self.port))
            sock.close()
            
            if result == 0:
                metrics.append(HealthMetric(
                    name="port_accessible",
                    value=True,
                    status=HealthStatus.HEALTHY,
                    message=f"Port {self.port} is accessible on {self.host}"
                ))
            else:
                metrics.append(HealthMetric(
                    name="port_accessible",
                    value=False,
                    status=HealthStatus.CRITICAL,
                    message=f"Port {self.port} is not accessible on {self.host}"
                ))
        except Exception as e:
            metrics.append(HealthMetric(
                name="port_accessible",
                value=False,
                status=HealthStatus.UNKNOWN,
                message=f"Error checking port accessibility: {e}"
            ))
        
        # Check if we can create a socket (resource availability)
        try:
            test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_sock.close()
            metrics.append(HealthMetric(
                name="socket_creation",
                value=True,
                status=HealthStatus.HEALTHY,
                message="Socket creation successful"
            ))
        except Exception as e:
            metrics.append(HealthMetric(
                name="socket_creation",
                value=False,
                status=HealthStatus.CRITICAL,
                message=f"Failed to create socket: {e}"
            ))
        
        return metrics


class ServiceHealthChecker(HealthChecker):
    """Health checker for service-specific metrics.
    
    Monitors:
    - Connected clients count
    - Event processing rate
    - Error rates
    - Response times
    """
    
    def __init__(self, service_stats: Dict[str, Any], 
                 max_clients: int = 1000, max_error_rate: float = 0.1):
        """Initialize service health checker.
        
        Args:
            service_stats: Reference to service statistics dictionary
            max_clients: Maximum allowed connected clients
            max_error_rate: Maximum allowed error rate (0.0-1.0)
        """
        self.service_stats = service_stats
        self.max_clients = max_clients
        self.max_error_rate = max_error_rate
        self.last_check_time = time.time()
        self.last_events_processed = 0
        self.logger = logging.getLogger(f"{__name__}.ServiceHealthChecker")
    
    def get_name(self) -> str:
        return "service_health"
    
    async def check_health(self) -> List[HealthMetric]:
        """Check service-specific health metrics."""
        metrics = []
        current_time = time.time()
        
        # Connected clients
        try:
            client_count = self.service_stats.get("clients_connected", 0)
            client_status = HealthStatus.HEALTHY
            if client_count > self.max_clients * 0.8:
                client_status = HealthStatus.WARNING
            if client_count > self.max_clients:
                client_status = HealthStatus.CRITICAL
            
            metrics.append(HealthMetric(
                name="connected_clients",
                value=client_count,
                status=client_status,
                threshold=self.max_clients
            ))
        except Exception as e:
            metrics.append(HealthMetric(
                name="connected_clients",
                value=-1,
                status=HealthStatus.UNKNOWN,
                message=f"Failed to get client count: {e}"
            ))
        
        # Event processing rate
        try:
            events_processed = self.service_stats.get("events_processed", 0)
            time_diff = current_time - self.last_check_time
            
            if time_diff > 0 and self.last_events_processed > 0:
                event_rate = (events_processed - self.last_events_processed) / time_diff
                metrics.append(HealthMetric(
                    name="event_processing_rate",
                    value=round(event_rate, 2),
                    status=HealthStatus.HEALTHY,
                    unit="events/sec"
                ))
            
            self.last_events_processed = events_processed
            
            # Total events processed
            metrics.append(HealthMetric(
                name="total_events_processed",
                value=events_processed,
                status=HealthStatus.HEALTHY
            ))
        except Exception as e:
            metrics.append(HealthMetric(
                name="event_processing_rate",
                value=-1,
                status=HealthStatus.UNKNOWN,
                message=f"Failed to calculate event rate: {e}"
            ))
        
        # Error rate
        try:
            errors = self.service_stats.get("errors", 0)
            total_events = self.service_stats.get("events_processed", 1)  # Avoid division by zero
            error_rate = errors / max(total_events, 1)
            
            error_status = HealthStatus.HEALTHY
            if error_rate > self.max_error_rate * 0.5:
                error_status = HealthStatus.WARNING
            if error_rate > self.max_error_rate:
                error_status = HealthStatus.CRITICAL
            
            metrics.append(HealthMetric(
                name="error_rate",
                value=round(error_rate, 4),
                status=error_status,
                threshold=self.max_error_rate,
                unit="ratio"
            ))
            
            metrics.append(HealthMetric(
                name="total_errors",
                value=errors,
                status=HealthStatus.HEALTHY if errors == 0 else HealthStatus.WARNING
            ))
        except Exception as e:
            metrics.append(HealthMetric(
                name="error_rate",
                value=-1,
                status=HealthStatus.UNKNOWN,
                message=f"Failed to calculate error rate: {e}"
            ))
        
        # Last activity timestamp
        try:
            last_activity = self.service_stats.get("last_activity")
            if last_activity:
                # Parse ISO timestamp or use as-is if numeric
                if isinstance(last_activity, str):
                    try:
                        from dateutil.parser import parse
                        last_activity_dt = parse(last_activity)
                        last_activity_timestamp = last_activity_dt.timestamp()
                    except ImportError:
                        # Fallback: try to parse ISO format manually
                        try:
                            from datetime import datetime
                            clean_timestamp = last_activity.rstrip('Z')
                            last_activity_dt = datetime.fromisoformat(clean_timestamp.replace('T', ' '))
                            last_activity_timestamp = last_activity_dt.timestamp()
                        except Exception:
                            # Final fallback: treat as current time
                            last_activity_timestamp = current_time
                else:
                    last_activity_timestamp = float(last_activity)
                
                time_since_activity = current_time - last_activity_timestamp
                activity_status = HealthStatus.HEALTHY
                if time_since_activity > 300:  # 5 minutes
                    activity_status = HealthStatus.WARNING
                if time_since_activity > 1800:  # 30 minutes
                    activity_status = HealthStatus.CRITICAL
                
                metrics.append(HealthMetric(
                    name="time_since_last_activity",
                    value=round(time_since_activity, 2),
                    status=activity_status,
                    unit="seconds"
                ))
            else:
                metrics.append(HealthMetric(
                    name="time_since_last_activity",
                    value=-1,
                    status=HealthStatus.WARNING,
                    message="No last activity recorded"
                ))
        except Exception as e:
            metrics.append(HealthMetric(
                name="time_since_last_activity",
                value=-1,
                status=HealthStatus.UNKNOWN,
                message=f"Failed to parse last activity: {e}"
            ))
        
        self.last_check_time = current_time
        return metrics


class AdvancedHealthMonitor:
    """Advanced health monitoring system with configurable checks and thresholds.
    
    Provides comprehensive health monitoring including:
    - Multiple health checker integration
    - Configurable check intervals and thresholds
    - Health history tracking
    - Status aggregation and reporting
    - Integration with recovery systems
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize advanced health monitor.
        
        Args:
            config: Configuration dictionary for health monitoring
        """
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.AdvancedHealthMonitor")
        
        # Configuration with defaults
        self.check_interval = self.config.get('check_interval', 30)
        self.history_size = self.config.get('history_size', 100)
        self.aggregation_window = self.config.get('aggregation_window', 300)  # 5 minutes
        
        # Health checkers
        self.checkers: List[HealthChecker] = []
        
        # Health history
        self.health_history: deque = deque(maxlen=self.history_size)
        
        # Monitoring state
        self.monitoring = False
        self.monitor_task: Optional[asyncio.Task] = None
        self.last_check_result: Optional[HealthCheckResult] = None
        
        # Health callbacks for recovery integration
        self.health_callbacks: List[Callable[[HealthCheckResult], None]] = []
        
        # Initialize metrics
        self.monitoring_stats = {
            'checks_performed': 0,
            'checks_failed': 0,
            'average_check_duration_ms': 0,
            'last_check_timestamp': None
        }
        
        self.logger.info("Advanced health monitor initialized")
    
    def add_checker(self, checker: HealthChecker) -> None:
        """Add a health checker to the monitoring system."""
        self.checkers.append(checker)
        self.logger.info(f"Added health checker: {checker.get_name()}")
    
    def add_health_callback(self, callback: Callable[[HealthCheckResult], None]) -> None:
        """Add a callback to be called when health checks complete.
        
        Args:
            callback: Function to call with HealthCheckResult
        """
        self.health_callbacks.append(callback)
        self.logger.debug(f"Added health callback: {callback.__name__}")
    
    async def perform_health_check(self) -> HealthCheckResult:
        """Perform comprehensive health check using all registered checkers."""
        start_time = time.time()
        all_metrics = []
        errors = []
        
        # Run all health checkers
        for checker in self.checkers:
            try:
                checker_start = time.time()
                metrics = await checker.check_health()
                checker_duration = (time.time() - checker_start) * 1000
                
                all_metrics.extend(metrics)
                self.logger.debug(f"Health checker {checker.get_name()} completed in {checker_duration:.2f}ms")
                
            except Exception as e:
                error_msg = f"Health checker {checker.get_name()} failed: {e}"
                errors.append(error_msg)
                self.logger.error(error_msg)
                
                # Add error metric
                all_metrics.append(HealthMetric(
                    name=f"{checker.get_name()}_error",
                    value=str(e),
                    status=HealthStatus.UNKNOWN,
                    message=error_msg
                ))
        
        # Determine overall status
        overall_status = self._determine_overall_status(all_metrics)
        
        # Create result
        duration_ms = (time.time() - start_time) * 1000
        result = HealthCheckResult(
            overall_status=overall_status,
            metrics=all_metrics,
            timestamp=start_time,
            duration_ms=duration_ms,
            errors=errors
        )
        
        # Update statistics
        self.monitoring_stats['checks_performed'] += 1
        if errors:
            self.monitoring_stats['checks_failed'] += 1
        
        # Update average duration
        current_avg = self.monitoring_stats['average_check_duration_ms']
        checks_count = self.monitoring_stats['checks_performed']
        self.monitoring_stats['average_check_duration_ms'] = (
            (current_avg * (checks_count - 1) + duration_ms) / checks_count
        )
        self.monitoring_stats['last_check_timestamp'] = time.time()
        
        # Store in history
        self.health_history.append(result)
        self.last_check_result = result
        
        # Notify callbacks
        for callback in self.health_callbacks:
            try:
                callback(result)
            except Exception as e:
                self.logger.error(f"Health callback {callback.__name__} failed: {e}")
        
        self.logger.debug(f"Health check completed: {overall_status.value} "
                         f"({len(all_metrics)} metrics, {len(errors)} errors, "
                         f"{duration_ms:.2f}ms)")
        
        return result
    
    def _determine_overall_status(self, metrics: List[HealthMetric]) -> HealthStatus:
        """Determine overall health status from individual metrics."""
        if not metrics:
            return HealthStatus.UNKNOWN
        
        # Count metrics by status
        status_counts = {status: 0 for status in HealthStatus}
        for metric in metrics:
            status_counts[metric.status] += 1
        
        # Determine overall status based on counts
        total_metrics = len(metrics)
        
        # If any critical metrics, overall is critical
        if status_counts[HealthStatus.CRITICAL] > 0:
            return HealthStatus.CRITICAL
        
        # If more than 30% warning metrics, overall is warning
        warning_ratio = status_counts[HealthStatus.WARNING] / total_metrics
        if warning_ratio > 0.3:
            return HealthStatus.WARNING
        
        # If any warning metrics but less than 30%, still healthy
        if status_counts[HealthStatus.WARNING] > 0:
            return HealthStatus.HEALTHY
        
        # If any unknown metrics, overall is unknown
        if status_counts[HealthStatus.UNKNOWN] > 0:
            return HealthStatus.UNKNOWN
        
        # All metrics healthy
        return HealthStatus.HEALTHY
    
    def start_monitoring(self) -> None:
        """Start continuous health monitoring."""
        if self.monitoring:
            self.logger.warning("Health monitoring is already running")
            return
        
        self.monitoring = True
        self.monitor_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info(f"Started health monitoring with {self.check_interval}s interval")
    
    async def stop_monitoring(self) -> None:
        """Stop continuous health monitoring."""
        if not self.monitoring:
            return
        
        self.monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
            self.monitor_task = None
        
        self.logger.info("Stopped health monitoring")
    
    async def _monitoring_loop(self) -> None:
        """Continuous health monitoring loop."""
        try:
            while self.monitoring:
                try:
                    await self.perform_health_check()
                except Exception as e:
                    self.logger.error(f"Error during health check: {e}")
                
                # Wait for next check
                await asyncio.sleep(self.check_interval)
        except asyncio.CancelledError:
            self.logger.debug("Health monitoring loop cancelled")
        except Exception as e:
            self.logger.error(f"Health monitoring loop error: {e}")
    
    def get_current_status(self) -> Optional[HealthCheckResult]:
        """Get the most recent health check result."""
        return self.last_check_result
    
    def get_health_history(self, limit: Optional[int] = None) -> List[HealthCheckResult]:
        """Get health check history.
        
        Args:
            limit: Maximum number of results to return
            
        Returns:
            List of health check results, newest first
        """
        history = list(self.health_history)
        history.reverse()  # Newest first
        
        if limit:
            history = history[:limit]
        
        return history
    
    def get_aggregated_status(self, window_seconds: Optional[int] = None) -> Dict[str, Any]:
        """Get aggregated health status over a time window.
        
        Args:
            window_seconds: Time window for aggregation (defaults to configured window)
            
        Returns:
            Dictionary with aggregated health statistics
        """
        window_seconds = window_seconds or self.aggregation_window
        current_time = time.time()
        cutoff_time = current_time - window_seconds
        
        # Filter history to time window
        recent_results = [
            result for result in self.health_history
            if result.timestamp >= cutoff_time
        ]
        
        if not recent_results:
            return {
                'period': 'no_data',
                'window_seconds': window_seconds,
                'checks_count': 0,
                'overall_status': HealthStatus.UNKNOWN.value
            }
        
        # Aggregate statistics
        status_counts = {status: 0 for status in HealthStatus}
        total_metrics = 0
        total_errors = 0
        total_duration_ms = 0
        
        for result in recent_results:
            status_counts[result.overall_status] += 1
            total_metrics += len(result.metrics)
            total_errors += len(result.errors)
            total_duration_ms += result.duration_ms
        
        checks_count = len(recent_results)
        
        # Determine aggregated status
        if status_counts[HealthStatus.CRITICAL] > 0:
            aggregated_status = HealthStatus.CRITICAL
        elif status_counts[HealthStatus.WARNING] > checks_count * 0.3:
            aggregated_status = HealthStatus.WARNING
        elif status_counts[HealthStatus.UNKNOWN] > checks_count * 0.5:
            aggregated_status = HealthStatus.UNKNOWN
        else:
            aggregated_status = HealthStatus.HEALTHY
        
        return {
            'period': f'last_{window_seconds}_seconds',
            'window_seconds': window_seconds,
            'checks_count': checks_count,
            'overall_status': aggregated_status.value,
            'status_distribution': {status.value: count for status, count in status_counts.items()},
            'average_metrics_per_check': round(total_metrics / checks_count, 2) if checks_count > 0 else 0,
            'total_errors': total_errors,
            'average_duration_ms': round(total_duration_ms / checks_count, 2) if checks_count > 0 else 0,
            'monitoring_stats': dict(self.monitoring_stats)
        }
    
    def export_diagnostics(self) -> Dict[str, Any]:
        """Export comprehensive diagnostics information."""
        return {
            'monitor_info': {
                'check_interval': self.check_interval,
                'history_size': self.history_size,
                'aggregation_window': self.aggregation_window,
                'monitoring_active': self.monitoring,
                'checkers_count': len(self.checkers),
                'callbacks_count': len(self.health_callbacks)
            },
            'checkers': [checker.get_name() for checker in self.checkers],
            'current_status': self.last_check_result.to_dict() if self.last_check_result else None,
            'aggregated_status': self.get_aggregated_status(),
            'monitoring_stats': dict(self.monitoring_stats),
            'history_summary': {
                'total_checks': len(self.health_history),
                'oldest_check': self.health_history[0].timestamp if self.health_history else None,
                'newest_check': self.health_history[-1].timestamp if self.health_history else None
            }
        }