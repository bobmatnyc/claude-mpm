"""Health monitoring service for Memory Guardian system.

Provides comprehensive health checks including system resources, process health,
and integration with existing monitoring infrastructure.
"""

import asyncio
import os
import platform
import psutil
import shutil
import socket
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable

from claude_mpm.services.core.base import BaseService


class HealthStatus(Enum):
    """Health check status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


class CheckType(Enum):
    """Types of health checks."""
    SYSTEM_RESOURCES = "system_resources"
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    DISK_SPACE = "disk_space"
    NETWORK = "network"
    PROCESS = "process"
    DEPENDENCIES = "dependencies"
    CUSTOM = "custom"


@dataclass
class HealthCheck:
    """Individual health check result."""
    name: str
    check_type: CheckType
    status: HealthStatus
    message: str
    details: Dict[str, Any]
    timestamp: float
    duration_ms: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'type': self.check_type.value,
            'status': self.status.value,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp,
            'timestamp_iso': datetime.fromtimestamp(self.timestamp).isoformat(),
            'duration_ms': round(self.duration_ms, 2)
        }


@dataclass
class SystemHealth:
    """Overall system health status."""
    status: HealthStatus
    checks: List[HealthCheck]
    timestamp: float
    
    @property
    def healthy_checks(self) -> int:
        """Count of healthy checks."""
        return sum(1 for c in self.checks if c.status == HealthStatus.HEALTHY)
    
    @property
    def total_checks(self) -> int:
        """Total number of checks."""
        return len(self.checks)
    
    @property
    def health_percentage(self) -> float:
        """Health percentage (0-100)."""
        if self.total_checks == 0:
            return 0.0
        return (self.healthy_checks / self.total_checks) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'status': self.status.value,
            'health_percentage': round(self.health_percentage, 1),
            'healthy_checks': self.healthy_checks,
            'total_checks': self.total_checks,
            'checks': [c.to_dict() for c in self.checks],
            'timestamp': self.timestamp,
            'timestamp_iso': datetime.fromtimestamp(self.timestamp).isoformat()
        }


class HealthMonitor(BaseService):
    """Service for monitoring system and application health."""
    
    def __init__(
        self,
        cpu_threshold_percent: float = 80.0,
        memory_threshold_percent: float = 90.0,
        disk_threshold_percent: float = 90.0,
        min_disk_space_gb: float = 1.0,
        check_interval_seconds: int = 30,
        state_dir: Optional[Path] = None
    ):
        """Initialize health monitor service.
        
        Args:
            cpu_threshold_percent: CPU usage threshold for degradation
            memory_threshold_percent: Memory usage threshold for degradation
            disk_threshold_percent: Disk usage threshold for degradation
            min_disk_space_gb: Minimum required disk space in GB
            check_interval_seconds: Interval between health checks
            state_dir: Directory for state files
        """
        super().__init__("HealthMonitor")
        
        # Configuration
        self.cpu_threshold = cpu_threshold_percent
        self.memory_threshold = memory_threshold_percent
        self.disk_threshold = disk_threshold_percent
        self.min_disk_space_gb = min_disk_space_gb
        self.check_interval = check_interval_seconds
        self.state_dir = state_dir or Path.home() / ".claude-mpm" / "health"
        
        # Health check registry
        self.health_checks: Dict[str, Callable] = {}
        self.custom_checks: List[Callable] = []
        
        # State tracking
        self.last_check: Optional[SystemHealth] = None
        self.check_history: List[SystemHealth] = []
        self.monitoring_task: Optional[asyncio.Task] = None
        self.monitoring_active = False
        
        # Process monitoring
        self.monitored_pid: Optional[int] = None
        self.monitored_process: Optional[psutil.Process] = None
        
        # Register default health checks
        self._register_default_checks()
        
        self.log_info(
            f"Health monitor initialized: "
            f"CPU={cpu_threshold_percent}%, "
            f"Memory={memory_threshold_percent}%, "
            f"Disk={disk_threshold_percent}%"
        )
    
    async def initialize(self) -> bool:
        """Initialize the health monitor service.
        
        Returns:
            True if initialization successful
        """
        try:
            self.log_info("Initializing health monitor service")
            
            # Create state directory
            self.state_dir.mkdir(parents=True, exist_ok=True)
            
            # Verify system capabilities
            if not self._verify_system_capabilities():
                self.log_warning("Some system capabilities unavailable, running in degraded mode")
            
            # Start monitoring if configured
            if self.check_interval > 0:
                self.start_monitoring()
            
            self._initialized = True
            self.log_info("Health monitor service initialized successfully")
            return True
            
        except Exception as e:
            self.log_error(f"Failed to initialize health monitor: {e}")
            return False
    
    async def shutdown(self) -> None:
        """Shutdown the health monitor service."""
        try:
            self.log_info("Shutting down health monitor service")
            
            # Stop monitoring
            await self.stop_monitoring()
            
            self._shutdown = True
            self.log_info("Health monitor service shutdown complete")
            
        except Exception as e:
            self.log_error(f"Error during health monitor shutdown: {e}")
    
    def set_monitored_process(self, pid: int) -> bool:
        """Set the process to monitor.
        
        Args:
            pid: Process ID to monitor
            
        Returns:
            True if process found and set
        """
        try:
            self.monitored_process = psutil.Process(pid)
            self.monitored_pid = pid
            self.log_info(f"Monitoring process {pid}")
            return True
        except psutil.NoSuchProcess:
            self.log_error(f"Process {pid} not found")
            return False
        except Exception as e:
            self.log_error(f"Error setting monitored process: {e}")
            return False
    
    async def check_health(self) -> SystemHealth:
        """Perform all health checks.
        
        Returns:
            SystemHealth object with results
        """
        checks = []
        start_time = time.time()
        
        # Run system resource checks
        checks.append(await self._check_cpu_usage())
        checks.append(await self._check_memory_usage())
        checks.append(await self._check_disk_space())
        
        # Run network check
        checks.append(await self._check_network())
        
        # Run process check if configured
        if self.monitored_process:
            checks.append(await self._check_process_health())
        
        # Run dependency checks
        checks.append(await self._check_dependencies())
        
        # Run custom checks
        for check_func in self.custom_checks:
            try:
                result = await check_func()
                if isinstance(result, HealthCheck):
                    checks.append(result)
            except Exception as e:
                self.log_error(f"Custom health check failed: {e}")
        
        # Determine overall status
        status = self._determine_overall_status(checks)
        
        # Create health report
        health = SystemHealth(
            status=status,
            checks=checks,
            timestamp=start_time
        )
        
        # Update state
        self.last_check = health
        self.check_history.append(health)
        
        # Trim history
        if len(self.check_history) > 100:
            self.check_history = self.check_history[-100:]
        
        return health
    
    async def validate_before_start(self) -> tuple[bool, str]:
        """Validate system resources before starting monitoring.
        
        Returns:
            Tuple of (valid, message)
        """
        # Check available memory
        mem = psutil.virtual_memory()
        if mem.available < 500 * 1024 * 1024:  # Less than 500MB
            return False, f"Insufficient memory: {mem.available / (1024*1024):.0f}MB available"
        
        # Check disk space
        disk = shutil.disk_usage(self.state_dir)
        if disk.free < self.min_disk_space_gb * 1024 * 1024 * 1024:
            return False, f"Insufficient disk space: {disk.free / (1024*1024*1024):.1f}GB available"
        
        # Check CPU load
        cpu_percent = psutil.cpu_percent(interval=0.1)
        if cpu_percent > 95:
            return False, f"CPU overloaded: {cpu_percent:.0f}% usage"
        
        return True, "System resources adequate"
    
    def start_monitoring(self) -> None:
        """Start continuous health monitoring."""
        if self.monitoring_active:
            self.log_warning("Health monitoring already active")
            return
        
        self.monitoring_active = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        self.log_info("Started health monitoring")
    
    async def stop_monitoring(self) -> None:
        """Stop continuous health monitoring."""
        if not self.monitoring_active:
            return
        
        self.monitoring_active = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            self.monitoring_task = None
        
        self.log_info("Stopped health monitoring")
    
    def register_health_check(self, name: str, check_func: Callable) -> None:
        """Register a custom health check.
        
        Args:
            name: Name of the health check
            check_func: Async function that returns HealthCheck
        """
        self.custom_checks.append(check_func)
        self.log_info(f"Registered custom health check: {name}")
    
    def get_health_status(self) -> Optional[SystemHealth]:
        """Get the last health check result.
        
        Returns:
            Last SystemHealth or None
        """
        return self.last_check
    
    def get_health_history(self, limit: int = 10) -> List[SystemHealth]:
        """Get health check history.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of SystemHealth objects
        """
        return self.check_history[-limit:]
    
    async def _check_cpu_usage(self) -> HealthCheck:
        """Check CPU usage."""
        start = time.time()
        
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_count = psutil.cpu_count()
            
            if cpu_percent >= 95:
                status = HealthStatus.CRITICAL
                message = f"CPU critically high: {cpu_percent:.1f}%"
            elif cpu_percent >= self.cpu_threshold:
                status = HealthStatus.DEGRADED
                message = f"CPU usage high: {cpu_percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"CPU usage normal: {cpu_percent:.1f}%"
            
            return HealthCheck(
                name="CPU Usage",
                check_type=CheckType.CPU_USAGE,
                status=status,
                message=message,
                details={
                    'cpu_percent': cpu_percent,
                    'cpu_count': cpu_count,
                    'threshold': self.cpu_threshold
                },
                timestamp=start,
                duration_ms=(time.time() - start) * 1000
            )
            
        except Exception as e:
            return HealthCheck(
                name="CPU Usage",
                check_type=CheckType.CPU_USAGE,
                status=HealthStatus.UNHEALTHY,
                message=f"Failed to check CPU: {e}",
                details={'error': str(e)},
                timestamp=start,
                duration_ms=(time.time() - start) * 1000
            )
    
    async def _check_memory_usage(self) -> HealthCheck:
        """Check memory usage."""
        start = time.time()
        
        try:
            mem = psutil.virtual_memory()
            
            if mem.percent >= 95:
                status = HealthStatus.CRITICAL
                message = f"Memory critically high: {mem.percent:.1f}%"
            elif mem.percent >= self.memory_threshold:
                status = HealthStatus.DEGRADED
                message = f"Memory usage high: {mem.percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Memory usage normal: {mem.percent:.1f}%"
            
            return HealthCheck(
                name="Memory Usage",
                check_type=CheckType.MEMORY_USAGE,
                status=status,
                message=message,
                details={
                    'memory_percent': mem.percent,
                    'available_mb': mem.available / (1024 * 1024),
                    'total_mb': mem.total / (1024 * 1024),
                    'threshold': self.memory_threshold
                },
                timestamp=start,
                duration_ms=(time.time() - start) * 1000
            )
            
        except Exception as e:
            return HealthCheck(
                name="Memory Usage",
                check_type=CheckType.MEMORY_USAGE,
                status=HealthStatus.UNHEALTHY,
                message=f"Failed to check memory: {e}",
                details={'error': str(e)},
                timestamp=start,
                duration_ms=(time.time() - start) * 1000
            )
    
    async def _check_disk_space(self) -> HealthCheck:
        """Check disk space."""
        start = time.time()
        
        try:
            # Check disk where state directory is located
            disk = shutil.disk_usage(self.state_dir)
            disk_percent = (disk.used / disk.total) * 100
            free_gb = disk.free / (1024 * 1024 * 1024)
            
            if free_gb < self.min_disk_space_gb:
                status = HealthStatus.CRITICAL
                message = f"Disk space critical: {free_gb:.1f}GB free"
            elif disk_percent >= self.disk_threshold:
                status = HealthStatus.DEGRADED
                message = f"Disk usage high: {disk_percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Disk space adequate: {free_gb:.1f}GB free"
            
            return HealthCheck(
                name="Disk Space",
                check_type=CheckType.DISK_SPACE,
                status=status,
                message=message,
                details={
                    'disk_percent': disk_percent,
                    'free_gb': free_gb,
                    'total_gb': disk.total / (1024 * 1024 * 1024),
                    'threshold': self.disk_threshold,
                    'min_space_gb': self.min_disk_space_gb,
                    'path': str(self.state_dir)
                },
                timestamp=start,
                duration_ms=(time.time() - start) * 1000
            )
            
        except Exception as e:
            return HealthCheck(
                name="Disk Space",
                check_type=CheckType.DISK_SPACE,
                status=HealthStatus.UNHEALTHY,
                message=f"Failed to check disk: {e}",
                details={'error': str(e)},
                timestamp=start,
                duration_ms=(time.time() - start) * 1000
            )
    
    async def _check_network(self) -> HealthCheck:
        """Check network connectivity."""
        start = time.time()
        
        try:
            # Try to connect to common DNS servers
            test_hosts = [
                ('8.8.8.8', 53),  # Google DNS
                ('1.1.1.1', 53),  # Cloudflare DNS
            ]
            
            connected = False
            for host, port in test_hosts:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)
                    result = sock.connect_ex((host, port))
                    sock.close()
                    if result == 0:
                        connected = True
                        break
                except:
                    continue
            
            if connected:
                status = HealthStatus.HEALTHY
                message = "Network connectivity OK"
            else:
                status = HealthStatus.DEGRADED
                message = "Network connectivity limited"
            
            return HealthCheck(
                name="Network",
                check_type=CheckType.NETWORK,
                status=status,
                message=message,
                details={'connected': connected},
                timestamp=start,
                duration_ms=(time.time() - start) * 1000
            )
            
        except Exception as e:
            return HealthCheck(
                name="Network",
                check_type=CheckType.NETWORK,
                status=HealthStatus.UNHEALTHY,
                message=f"Failed to check network: {e}",
                details={'error': str(e)},
                timestamp=start,
                duration_ms=(time.time() - start) * 1000
            )
    
    async def _check_process_health(self) -> HealthCheck:
        """Check monitored process health."""
        start = time.time()
        
        try:
            if not self.monitored_process:
                return HealthCheck(
                    name="Process Health",
                    check_type=CheckType.PROCESS,
                    status=HealthStatus.HEALTHY,
                    message="No process monitored",
                    details={},
                    timestamp=start,
                    duration_ms=(time.time() - start) * 1000
                )
            
            # Check if process is running
            if not self.monitored_process.is_running():
                return HealthCheck(
                    name="Process Health",
                    check_type=CheckType.PROCESS,
                    status=HealthStatus.CRITICAL,
                    message=f"Process {self.monitored_pid} not running",
                    details={'pid': self.monitored_pid},
                    timestamp=start,
                    duration_ms=(time.time() - start) * 1000
                )
            
            # Get process info
            with self.monitored_process.oneshot():
                cpu_percent = self.monitored_process.cpu_percent()
                mem_info = self.monitored_process.memory_info()
                mem_mb = mem_info.rss / (1024 * 1024)
                status_str = self.monitored_process.status()
            
            # Determine health based on process status
            if status_str in ['zombie', 'dead']:
                status = HealthStatus.CRITICAL
                message = f"Process in {status_str} state"
            elif cpu_percent > 90:
                status = HealthStatus.DEGRADED
                message = f"Process CPU high: {cpu_percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Process healthy (PID: {self.monitored_pid})"
            
            return HealthCheck(
                name="Process Health",
                check_type=CheckType.PROCESS,
                status=status,
                message=message,
                details={
                    'pid': self.monitored_pid,
                    'cpu_percent': cpu_percent,
                    'memory_mb': mem_mb,
                    'status': status_str
                },
                timestamp=start,
                duration_ms=(time.time() - start) * 1000
            )
            
        except psutil.NoSuchProcess:
            return HealthCheck(
                name="Process Health",
                check_type=CheckType.PROCESS,
                status=HealthStatus.CRITICAL,
                message=f"Process {self.monitored_pid} not found",
                details={'pid': self.monitored_pid},
                timestamp=start,
                duration_ms=(time.time() - start) * 1000
            )
        except Exception as e:
            return HealthCheck(
                name="Process Health",
                check_type=CheckType.PROCESS,
                status=HealthStatus.UNHEALTHY,
                message=f"Failed to check process: {e}",
                details={'error': str(e)},
                timestamp=start,
                duration_ms=(time.time() - start) * 1000
            )
    
    async def _check_dependencies(self) -> HealthCheck:
        """Check critical dependencies."""
        start = time.time()
        
        try:
            missing = []
            
            # Check for psutil (critical dependency)
            try:
                import psutil
            except ImportError:
                missing.append('psutil')
            
            if missing:
                status = HealthStatus.DEGRADED
                message = f"Missing dependencies: {', '.join(missing)}"
            else:
                status = HealthStatus.HEALTHY
                message = "All dependencies available"
            
            return HealthCheck(
                name="Dependencies",
                check_type=CheckType.DEPENDENCIES,
                status=status,
                message=message,
                details={'missing': missing},
                timestamp=start,
                duration_ms=(time.time() - start) * 1000
            )
            
        except Exception as e:
            return HealthCheck(
                name="Dependencies",
                check_type=CheckType.DEPENDENCIES,
                status=HealthStatus.UNHEALTHY,
                message=f"Failed to check dependencies: {e}",
                details={'error': str(e)},
                timestamp=start,
                duration_ms=(time.time() - start) * 1000
            )
    
    def _register_default_checks(self) -> None:
        """Register default health checks."""
        # Default checks are implemented as methods
        pass
    
    def _verify_system_capabilities(self) -> bool:
        """Verify system monitoring capabilities.
        
        Returns:
            True if all capabilities available
        """
        capabilities = {
            'psutil': False,
            'cpu': False,
            'memory': False,
            'disk': False,
            'network': False
        }
        
        try:
            import psutil
            capabilities['psutil'] = True
            
            # Test CPU monitoring
            try:
                psutil.cpu_percent(interval=0.1)
                capabilities['cpu'] = True
            except:
                pass
            
            # Test memory monitoring
            try:
                psutil.virtual_memory()
                capabilities['memory'] = True
            except:
                pass
            
            # Test disk monitoring
            try:
                shutil.disk_usage('/')
                capabilities['disk'] = True
            except:
                pass
            
            # Test network monitoring
            try:
                socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                capabilities['network'] = True
            except:
                pass
            
        except ImportError:
            self.log_warning("psutil not available, running in degraded mode")
        
        # Log capabilities
        for cap, available in capabilities.items():
            if not available:
                self.log_warning(f"System capability unavailable: {cap}")
        
        return all(capabilities.values())
    
    def _determine_overall_status(self, checks: List[HealthCheck]) -> HealthStatus:
        """Determine overall health status from individual checks.
        
        Args:
            checks: List of health check results
            
        Returns:
            Overall HealthStatus
        """
        if not checks:
            return HealthStatus.HEALTHY
        
        # Count status types
        critical_count = sum(1 for c in checks if c.status == HealthStatus.CRITICAL)
        unhealthy_count = sum(1 for c in checks if c.status == HealthStatus.UNHEALTHY)
        degraded_count = sum(1 for c in checks if c.status == HealthStatus.DEGRADED)
        
        # Determine overall status
        if critical_count > 0:
            return HealthStatus.CRITICAL
        elif unhealthy_count > 0:
            return HealthStatus.UNHEALTHY
        elif degraded_count > 0:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY
    
    async def _monitoring_loop(self) -> None:
        """Continuous health monitoring loop."""
        try:
            while self.monitoring_active:
                try:
                    # Perform health checks
                    health = await self.check_health()
                    
                    # Log if status changed
                    if self.check_history and len(self.check_history) > 1:
                        prev_status = self.check_history[-2].status
                        if health.status != prev_status:
                            self.log_info(f"Health status changed: {prev_status.value} -> {health.status.value}")
                    
                    # Wait for next check
                    await asyncio.sleep(self.check_interval)
                    
                except Exception as e:
                    self.log_error(f"Error in health monitoring loop: {e}")
                    await asyncio.sleep(self.check_interval)
                    
        except asyncio.CancelledError:
            self.log_debug("Health monitoring loop cancelled")