# Local Process Management - Developer Guide

Comprehensive developer guide for the Local Process Management system architecture, implementation, and extension points.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Component Descriptions](#component-descriptions)
- [Implementation Phases](#implementation-phases)
- [Service Layer API](#service-layer-api)
- [Extension Points](#extension-points)
- [Testing Strategy](#testing-strategy)
- [Performance Considerations](#performance-considerations)
- [Integration Patterns](#integration-patterns)

## Architecture Overview

The Local Process Management system is built on a five-phase architecture, each building on the previous:

```
┌─────────────────────────────────────────────────────────────────┐
│                    UnifiedLocalOpsManager                        │
│                   (Phase 5: Integration)                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐ │
│  │ LocalProcess     │  │ HealthCheck      │  │ Auto-Restart │ │
│  │ Manager          │  │ Manager          │  │ Manager      │ │
│  │ (Phase 1)        │  │ (Phase 2)        │  │ (Phase 3)    │ │
│  └──────────────────┘  └──────────────────┘  └──────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │         Stability Enhancements (Phase 4)                   │ │
│  ├──────────────┬──────────────┬──────────────────────────────┤ │
│  │ Memory Leak  │ Log Pattern  │ Resource Exhaustion          │ │
│  │ Detector     │ Monitor      │ Monitor                      │ │
│  └──────────────┴──────────────┴──────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    CLI Commands (10 subcommands)                 │
│  start | stop | restart | status | health | list | monitor      │
│  history | enable-auto-restart | disable-auto-restart           │
└─────────────────────────────────────────────────────────────────┘
```

### Design Principles

1. **Layered Architecture**: Each phase builds on previous phases
2. **Service-Oriented**: Components as independent services with interfaces
3. **Single Responsibility**: Each service has one clear purpose
4. **Dependency Injection**: Services composed via constructor injection
5. **Configuration-Driven**: YAML configuration with sensible defaults
6. **Backward Compatible**: No breaking changes to existing APIs

## Component Descriptions

### Phase 1: Core Process Management

**Location**: `src/claude_mpm/services/local_ops/process_manager.py`

**Purpose**: Fundamental process lifecycle management

**Key Components**:

```python
class LocalProcessManager(BaseService):
    """
    Manages local process lifecycle with isolation and monitoring.

    Capabilities:
    - Background process spawning with subprocess.Popen
    - Process group isolation (PGID)
    - Environment variable injection
    - State persistence to disk
    - Port conflict detection
    - Graceful shutdown with SIGTERM/SIGKILL
    """

    def start_process(self, config: StartConfig) -> ProcessInfo:
        """Start a background process with full isolation."""

    def stop_process(self, pid: int, timeout: int = 10, force: bool = False) -> bool:
        """Stop process gracefully or forcefully."""

    def get_process_info(self, pid: int) -> ProcessInfo:
        """Get comprehensive process information."""
```

**Process Isolation**:
- Uses `os.setpgid()` to create new process group
- Separate PGID enables killing entire process tree
- Custom environment with controlled inheritance

**State Management**:
```python
class StateManager:
    """
    Persists deployment state to JSON files.

    State includes:
    - Process configuration (command, env, working_dir)
    - Runtime information (PID, port, start_time)
    - Auto-restart configuration
    - Monitoring settings
    """

    # State stored in: .claude-mpm/local-ops-state/
```

**Port Management**:
```python
def is_port_available(port: int) -> bool:
    """Check if port is available for binding."""

def find_available_port(start_port: int, max_attempts: int = 10) -> Optional[int]:
    """Find next available port starting from start_port."""
```

### Phase 2: Health Monitoring

**Location**: `src/claude_mpm/services/local_ops/health_manager.py`

**Purpose**: Multi-tier health monitoring with background checks

**Architecture**:

```python
# Interface definition
class IHealthCheckManager(ABC):
    @abstractmethod
    def check_health(self, deployment_id: str) -> DeploymentHealth:
        """Run all health checks and aggregate results."""

    @abstractmethod
    def start_monitoring(self) -> None:
        """Start background monitoring thread."""

    @abstractmethod
    def stop_monitoring(self) -> None:
        """Stop background monitoring."""

    @abstractmethod
    def get_health_history(self, deployment_id: str, limit: int = 10) -> List[DeploymentHealth]:
        """Retrieve historical health data."""
```

**Implementation**:

```python
class HealthCheckManager(BaseService, IHealthCheckManager):
    """
    Orchestrates three-tier health checks with background monitoring.

    Components:
    - HTTPHealthCheck: Endpoint availability and response time
    - ProcessHealthCheck: Process existence and responsiveness
    - ResourceHealthCheck: CPU, memory, FDs, threads

    Features:
    - Background daemon thread for continuous monitoring
    - Configurable check interval (default: 30s)
    - Historical data storage (default: last 100 checks)
    - Thread-safe with threading.Lock
    - Status change callbacks
    """

    def __init__(self, check_interval: int = 30):
        self.checks = [
            HTTPHealthCheck(),
            ProcessHealthCheck(),
            ResourceHealthCheck()
        ]
        self._monitoring_thread: Optional[threading.Thread] = None
        self._health_history: Dict[str, deque] = {}
```

**Health Check Implementations**:

1. **HTTP Health Check** (`health_checks/http_check.py`):
   ```python
   class HTTPHealthCheck(IHealthCheck):
       """
       HTTP endpoint health verification.

       Features:
       - Configurable timeout (default: 5s)
       - Retry logic with exponential backoff
       - Response time measurement
       - SSL/TLS support
       - Custom headers support
       """

       def check(self, deployment_id: str, **kwargs) -> HealthCheckResult:
           url = kwargs.get('url') or f"http://localhost:{port}"
           response = requests.get(url, timeout=self.timeout)
           return HealthCheckResult(
               status=HealthStatus.HEALTHY if response.ok else HealthStatus.UNHEALTHY,
               check_type="http",
               message=f"HTTP {response.status_code}",
               details={"response_time_ms": response_time}
           )
   ```

2. **Process Health Check** (`health_checks/process_check.py`):
   ```python
   class ProcessHealthCheck(IHealthCheck):
       """
       Process existence and responsiveness verification.

       Checks:
       - Process exists (psutil.Process)
       - Process status (running/zombie/stopped)
       - CPU activity (responsiveness indicator)
       - Exit code detection
       - Parent-child relationship
       """

       def check(self, deployment_id: str, **kwargs) -> HealthCheckResult:
           pid = kwargs.get('pid')
           process = psutil.Process(pid)

           if process.status() == psutil.STATUS_ZOMBIE:
               return HealthCheckResult(status=HealthStatus.UNHEALTHY, ...)

           if process.cpu_percent(interval=0.1) == 0.0:
               return HealthCheckResult(status=HealthStatus.DEGRADED, ...)
   ```

3. **Resource Health Check** (`health_checks/resource_check.py`):
   ```python
   class ResourceHealthCheck(IHealthCheck):
       """
       Resource consumption monitoring.

       Monitors:
       - CPU usage percentage
       - Memory usage (RSS, VMS)
       - File descriptors (Linux/macOS)
       - Thread count
       - Network connections by state

       Thresholds:
       - CPU: 80% (configurable)
       - Memory: 500MB (configurable)
       - FDs: 1000 (configurable)
       - Threads: 100 (configurable)
       """

       def check(self, deployment_id: str, **kwargs) -> HealthCheckResult:
           pid = kwargs.get('pid')
           process = psutil.Process(pid)

           issues = []
           if process.cpu_percent() > self.cpu_threshold:
               issues.append(f"High CPU: {cpu}%")

           if memory_mb > self.memory_threshold_mb:
               issues.append(f"High memory: {memory_mb}MB")
   ```

**Health Status Aggregation**:

```python
def _aggregate_status(self, checks: List[HealthCheckResult]) -> HealthStatus:
    """
    Aggregate individual check results into overall status.

    Logic:
    1. Process UNHEALTHY → Overall UNHEALTHY (critical)
    2. Any check UNHEALTHY → Overall DEGRADED (service issues)
    3. All checks HEALTHY → Overall HEALTHY
    4. Otherwise → UNKNOWN
    """
    process_check = next((c for c in checks if c.check_type == "process"), None)
    if process_check and process_check.status == HealthStatus.UNHEALTHY:
        return HealthStatus.UNHEALTHY

    if any(c.status == HealthStatus.UNHEALTHY for c in checks):
        return HealthStatus.DEGRADED

    if all(c.status == HealthStatus.HEALTHY for c in checks):
        return HealthStatus.HEALTHY

    return HealthStatus.UNKNOWN
```

### Phase 3: Auto-Restart System

**Location**: `src/claude_mpm/services/local_ops/restart_manager.py`

**Purpose**: Intelligent crash recovery with exponential backoff and circuit breaker

**Components**:

```python
class RestartManager(BaseService):
    """
    Manages automatic restart on process failures.

    Features:
    - Crash detection via health checks
    - Exponential backoff policy
    - Circuit breaker pattern
    - Restart history tracking
    - Configurable retry limits
    """

    def __init__(self, restart_config: RestartConfig):
        self.crash_detector = CrashDetector()
        self.restart_policy = RestartPolicy(restart_config)
        self.restart_history: Dict[str, RestartHistory] = {}
```

**Crash Detection** (`crash_detector.py`):

```python
class CrashDetector:
    """
    Detects process crashes and failures.

    Detection methods:
    1. Process exit (poll() returns non-None)
    2. Health check failures (UNHEALTHY status)
    3. Zombie process state
    4. Unresponsive process (no CPU activity)
    """

    def is_crashed(self, deployment_id: str) -> Tuple[bool, str]:
        """
        Check if deployment has crashed.

        Returns:
            (crashed, reason) tuple
        """
        # Check process still exists
        if not process.is_running():
            return (True, f"Process exited with code {exit_code}")

        # Check health status
        health = health_manager.check_health(deployment_id)
        if health.overall_status == HealthStatus.UNHEALTHY:
            return (True, "Health check failure: process unhealthy")

        return (False, "")
```

**Restart Policy** (`restart_policy.py`):

```python
class RestartPolicy:
    """
    Exponential backoff restart policy with circuit breaker.

    Algorithm:
    1. Calculate backoff: min(initial * (multiplier ** attempts), max_backoff)
    2. Check circuit breaker state
    3. Enforce max attempts limit

    Circuit Breaker States:
    - CLOSED: Normal operation, restarts allowed
    - OPEN: Too many failures, restarts blocked
    - HALF_OPEN: Testing if issue resolved
    """

    def __init__(self, config: RestartConfig):
        self.max_attempts = config.max_attempts
        self.initial_backoff = config.initial_backoff_seconds
        self.max_backoff = config.max_backoff_seconds
        self.backoff_multiplier = config.backoff_multiplier
        self.circuit_breaker = CircuitBreaker(
            threshold=config.circuit_breaker_threshold,
            window_seconds=config.circuit_breaker_window_seconds,
            reset_seconds=config.circuit_breaker_reset_seconds
        )

    def should_restart(self, deployment_id: str, attempt: int) -> Tuple[bool, float]:
        """
        Determine if restart should be attempted.

        Returns:
            (should_restart, backoff_seconds) tuple
        """
        # Check circuit breaker
        if self.circuit_breaker.is_open(deployment_id):
            return (False, 0.0)

        # Check attempt limit
        if attempt >= self.max_attempts:
            return (False, 0.0)

        # Calculate backoff
        backoff = min(
            self.initial_backoff * (self.backoff_multiplier ** attempt),
            self.max_backoff
        )

        return (True, backoff)
```

**Circuit Breaker** (`circuit_breaker.py`):

```python
class CircuitBreaker:
    """
    Circuit breaker pattern for restart attempts.

    Prevents restart loops by opening circuit after
    too many failures within time window.

    States:
    - CLOSED: Normal, restarts allowed
    - OPEN: Circuit tripped, no restarts
    - HALF_OPEN: Testing after timeout
    """

    def __init__(self, threshold: int, window_seconds: int, reset_seconds: int):
        self.threshold = threshold  # e.g., 3 failures
        self.window_seconds = window_seconds  # e.g., 300s (5 min)
        self.reset_seconds = reset_seconds  # e.g., 600s (10 min)
        self.failure_times: Dict[str, deque] = {}
        self.open_time: Dict[str, float] = {}

    def record_failure(self, deployment_id: str) -> None:
        """Record a failure and potentially open circuit."""
        now = time.time()

        # Initialize or get failure history
        if deployment_id not in self.failure_times:
            self.failure_times[deployment_id] = deque()

        failures = self.failure_times[deployment_id]

        # Remove old failures outside window
        while failures and failures[0] < now - self.window_seconds:
            failures.popleft()

        # Add new failure
        failures.append(now)

        # Open circuit if threshold exceeded
        if len(failures) >= self.threshold:
            self.open_time[deployment_id] = now

    def is_open(self, deployment_id: str) -> bool:
        """Check if circuit is open."""
        if deployment_id not in self.open_time:
            return False

        # Check if reset timeout has passed
        if time.time() - self.open_time[deployment_id] > self.reset_seconds:
            del self.open_time[deployment_id]
            return False

        return True
```

### Phase 4: Stability Enhancements

**Location**: `src/claude_mpm/services/local_ops/stability/`

**Purpose**: Preemptive issue detection and prevention

**Components**:

1. **Memory Leak Detector** (`memory_leak_detector.py`):
   ```python
   class MemoryLeakDetector:
       """
       Detect memory leaks via growth rate analysis.

       Algorithm:
       1. Track memory usage over time (sliding window)
       2. Calculate linear regression slope (MB/minute)
       3. Compare to threshold (default: 10 MB/min)
       4. Trigger preemptive restart if exceeded

       Features:
       - Sliding window (default: 10 samples)
       - Linear regression via numpy
       - Configurable threshold
       - False positive reduction (require sustained growth)
       """

       def __init__(self, threshold_mb_per_minute: float = 10.0):
           self.threshold = threshold_mb_per_minute
           self.memory_history: Dict[str, deque] = {}

       def check_memory_leak(self, deployment_id: str, current_memory_mb: float) -> bool:
           """
           Check if deployment has memory leak.

           Returns:
               True if leak detected (sustained growth > threshold)
           """
           history = self.memory_history[deployment_id]
           history.append((time.time(), current_memory_mb))

           if len(history) < 5:  # Need minimum samples
               return False

           # Calculate growth rate via linear regression
           times, memories = zip(*history)
           slope = self._linear_regression_slope(times, memories)

           # Convert to MB/minute
           mb_per_minute = slope * 60

           return mb_per_minute > self.threshold
   ```

2. **Log Pattern Monitor** (`log_monitor.py`):
   ```python
   class LogMonitor:
       """
       Monitor log files for error patterns.

       Features:
       - Tail log file with efficient seek
       - Regex pattern matching
       - Configurable error patterns
       - Rate limiting (avoid restart loops on log spam)
       - Multi-line error detection
       """

       def __init__(self, error_patterns: List[str]):
           self.patterns = [re.compile(p) for p in error_patterns]
           self.last_position: Dict[str, int] = {}

       def check_for_errors(self, log_file: Path) -> List[str]:
           """
           Check log file for new error patterns.

           Returns:
               List of detected error messages
           """
           if not log_file.exists():
               return []

           # Get last read position
           last_pos = self.last_position.get(str(log_file), 0)

           errors = []
           with open(log_file, 'r') as f:
               f.seek(last_pos)
               for line in f:
                   for pattern in self.patterns:
                       if pattern.search(line):
                           errors.append(line.strip())

               self.last_position[str(log_file)] = f.tell()

           return errors
   ```

3. **Resource Exhaustion Monitor** (`resource_monitor.py`):
   ```python
   class ResourceMonitor:
       """
       Monitor resource limits and prevent exhaustion.

       Monitors:
       - File descriptors (% of system limit)
       - Thread count (absolute threshold)
       - Network connections (by state)
       - Disk space (available MB)

       Actions:
       - Preemptive restart before hitting limits
       - Graceful degradation (close idle connections)
       - Alert on threshold breach
       """

       def __init__(self, config: ResourceConfig):
           self.fd_threshold = config.fd_threshold_percent
           self.thread_threshold = config.thread_threshold
           self.connection_threshold = config.connection_threshold
           self.disk_threshold_mb = config.disk_threshold_mb

       def check_resources(self, deployment_id: str, pid: int) -> List[str]:
           """
           Check resource usage against thresholds.

           Returns:
               List of threshold breaches
           """
           process = psutil.Process(pid)
           issues = []

           # File descriptors (Linux/macOS)
           try:
               num_fds = process.num_fds()
               fd_limit = resource.getrlimit(resource.RLIMIT_NOFILE)[0]
               fd_percent = num_fds / fd_limit

               if fd_percent > self.fd_threshold:
                   issues.append(f"File descriptor threshold exceeded: {fd_percent:.1%}")
           except (AttributeError, OSError):
               pass  # Not supported on Windows

           # Thread count
           num_threads = process.num_threads()
           if num_threads > self.thread_threshold:
               issues.append(f"Thread count threshold exceeded: {num_threads}")

           # Network connections
           connections = process.connections()
           if len(connections) > self.connection_threshold:
               issues.append(f"Connection count threshold exceeded: {len(connections)}")

           return issues
   ```

### Phase 5: Unified Integration

**Location**: `src/claude_mpm/services/local_ops/unified_manager.py`

**Purpose**: Single coordinated interface for all process management

**Implementation**:

```python
class UnifiedLocalOpsManager(BaseService):
    """
    Unified manager coordinating all process management components.

    Aggregates:
    - LocalProcessManager (Phase 1)
    - HealthCheckManager (Phase 2)
    - RestartManager (Phase 3)
    - MemoryLeakDetector (Phase 4)
    - LogMonitor (Phase 4)
    - ResourceMonitor (Phase 4)

    Provides:
    - Single API for all operations
    - Configuration-driven initialization
    - Coordinated component lifecycle
    - Comprehensive status aggregation
    """

    def __init__(self, project_root: Path, config: Optional[Dict] = None):
        self.project_root = project_root
        self.config = config or self._load_config()

        # Initialize components
        self.process_manager = LocalProcessManager(project_root)
        self.health_manager = HealthCheckManager(
            check_interval=self.config['defaults']['health_check_interval_seconds']
        )
        self.restart_manager = RestartManager(
            RestartConfig(**self.config['restart_policy'])
        )
        self.memory_detector = MemoryLeakDetector(
            self.config['stability']['memory_leak_threshold_mb_per_minute']
        )
        self.log_monitor = LogMonitor(
            self.config['log_monitoring']['error_patterns']
        )
        self.resource_monitor = ResourceMonitor(
            ResourceConfig(**self.config['stability'])
        )

    def _load_config(self) -> Dict:
        """Load configuration from YAML or use defaults."""
        config_path = self.project_root / '.claude-mpm' / 'local-ops-config.yaml'

        if config_path.exists():
            with open(config_path) as f:
                return yaml.safe_load(f)

        # Return defaults
        return DEFAULT_CONFIG

    def start_deployment(
        self,
        config: StartConfig,
        auto_restart: bool = False
    ) -> DeploymentState:
        """
        Start deployment with full monitoring.

        Workflow:
        1. Start process via ProcessManager
        2. Enable auto-restart if requested
        3. Start health monitoring
        4. Verify initial health
        5. Return deployment state
        """
        # Start process
        process_info = self.process_manager.start_process(config)

        # Enable auto-restart
        if auto_restart:
            self.restart_manager.enable_auto_restart(
                process_info.deployment_id,
                RestartConfig(**self.config['restart_policy'])
            )

        # Start monitoring
        if not self.health_manager.is_monitoring():
            self.health_manager.start_monitoring()

        # Initial health check
        health = self.health_manager.check_health(process_info.deployment_id)

        return DeploymentState(
            deployment_id=process_info.deployment_id,
            process_info=process_info,
            health=health,
            auto_restart_enabled=auto_restart
        )

    def get_full_status(self, deployment_id: str) -> Dict[str, Any]:
        """
        Get comprehensive status across all components.

        Returns:
            {
                'process': ProcessInfo,
                'health': DeploymentHealth,
                'restart_history': RestartHistory,
                'memory_trend': MemoryTrend,
                'resource_status': ResourceStatus,
                'log_errors': List[str]
            }
        """
        process_info = self.process_manager.get_process_info(deployment_id)
        health = self.health_manager.check_health(deployment_id)
        restart_history = self.restart_manager.get_restart_history(deployment_id)

        # Memory leak check
        memory_mb = process_info.memory_mb
        memory_leak = self.memory_detector.check_memory_leak(deployment_id, memory_mb)

        # Resource status
        resource_issues = self.resource_monitor.check_resources(
            deployment_id,
            process_info.pid
        )

        # Log errors (if log file configured)
        log_errors = []
        if process_info.log_file:
            log_errors = self.log_monitor.check_for_errors(process_info.log_file)

        return {
            'process': process_info,
            'health': health,
            'restart_history': restart_history,
            'memory_trend': {
                'current_mb': memory_mb,
                'leak_detected': memory_leak
            },
            'resource_status': {
                'issues': resource_issues,
                'critical': len(resource_issues) > 0
            },
            'log_errors': log_errors
        }
```

## Service Layer API

### Core Data Models

**Location**: `src/claude_mpm/services/core/models/`

```python
# process.py
@dataclass
class ProcessInfo:
    """Process information model."""
    deployment_id: str
    pid: int
    status: ProcessStatus  # RUNNING, STOPPED, CRASHED
    command: str
    port: Optional[int]
    start_time: float
    uptime_seconds: float
    memory_mb: float
    cpu_percent: float
    log_file: Optional[Path]

# health.py
@dataclass
class HealthCheckResult:
    """Individual health check result."""
    status: HealthStatus  # HEALTHY, DEGRADED, UNHEALTHY, UNKNOWN
    check_type: str  # "http", "process", "resource"
    message: str
    details: Dict[str, Any]
    checked_at: float

@dataclass
class DeploymentHealth:
    """Aggregated deployment health."""
    deployment_id: str
    overall_status: HealthStatus
    checks: List[HealthCheckResult]
    last_check: float

# restart.py
@dataclass
class RestartAttempt:
    """Single restart attempt record."""
    attempt_number: int
    timestamp: float
    success: bool
    reason: str
    backoff_seconds: float

@dataclass
class RestartHistory:
    """Complete restart history."""
    deployment_id: str
    total_restarts: int
    successful_restarts: int
    failed_restarts: int
    circuit_breaker_state: str  # "CLOSED", "OPEN", "HALF_OPEN"
    last_restart: Optional[RestartAttempt]
    recent_attempts: List[RestartAttempt]
```

### Interface Contracts

**Location**: `src/claude_mpm/services/core/interfaces/`

```python
# process.py
class IProcessManager(ABC):
    @abstractmethod
    def start_process(self, config: StartConfig) -> ProcessInfo:
        """Start a background process."""

    @abstractmethod
    def stop_process(self, pid: int, timeout: int, force: bool) -> bool:
        """Stop a running process."""

    @abstractmethod
    def get_process_info(self, pid: int) -> ProcessInfo:
        """Get process information."""

# health.py
class IHealthCheckManager(ABC):
    @abstractmethod
    def check_health(self, deployment_id: str) -> DeploymentHealth:
        """Run all health checks."""

    @abstractmethod
    def start_monitoring(self) -> None:
        """Start background monitoring."""

    @abstractmethod
    def stop_monitoring(self) -> None:
        """Stop background monitoring."""

# restart.py
class IRestartManager(ABC):
    @abstractmethod
    def enable_auto_restart(self, deployment_id: str, config: RestartConfig) -> bool:
        """Enable auto-restart for deployment."""

    @abstractmethod
    def disable_auto_restart(self, deployment_id: str) -> bool:
        """Disable auto-restart."""

    @abstractmethod
    def get_restart_history(self, deployment_id: str) -> RestartHistory:
        """Get restart history."""
```

## Extension Points

### Custom Health Checks

To add a new health check type:

```python
from claude_mpm.services.core.interfaces.health import IHealthCheck
from claude_mpm.services.core.models.health import HealthCheckResult, HealthStatus

class DatabaseHealthCheck(IHealthCheck):
    """Custom health check for database connectivity."""

    def check(self, deployment_id: str, **kwargs) -> HealthCheckResult:
        """Check database connection."""
        db_url = kwargs.get('database_url')

        try:
            # Attempt database connection
            connection = psycopg2.connect(db_url, connect_timeout=5)
            connection.close()

            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                check_type="database",
                message="Database connection successful",
                details={"database_url": db_url},
                checked_at=time.time()
            )
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                check_type="database",
                message=f"Database connection failed: {str(e)}",
                details={"error": str(e)},
                checked_at=time.time()
            )

    def get_check_type(self) -> str:
        return "database"

# Register with HealthCheckManager
health_manager.register_check(DatabaseHealthCheck())
```

### Custom Restart Policies

To implement a custom restart policy:

```python
from claude_mpm.services.local_ops.restart_policy import RestartPolicy

class AdaptiveRestartPolicy(RestartPolicy):
    """
    Adaptive restart policy that adjusts based on time of day.

    Example: More aggressive restarts during business hours,
    conservative restarts at night.
    """

    def should_restart(self, deployment_id: str, attempt: int) -> Tuple[bool, float]:
        """Determine if restart should be attempted with adaptive backoff."""

        # Check base policy
        should_restart, base_backoff = super().should_restart(deployment_id, attempt)

        if not should_restart:
            return (False, 0.0)

        # Adjust backoff based on time
        hour = datetime.now().hour

        if 9 <= hour <= 17:  # Business hours
            # More aggressive: reduce backoff
            backoff = base_backoff * 0.5
        else:  # Off hours
            # Conservative: increase backoff
            backoff = base_backoff * 1.5

        return (True, backoff)
```

### Custom Stability Monitors

To add a new stability monitor:

```python
class DiskIOMonitor:
    """
    Monitor disk I/O for excessive write operations.

    Use case: Detect runaway logging or database writes.
    """

    def __init__(self, threshold_mb_per_second: float = 50.0):
        self.threshold = threshold_mb_per_second
        self.io_history: Dict[str, deque] = {}

    def check_disk_io(self, deployment_id: str, pid: int) -> bool:
        """
        Check if disk I/O exceeds threshold.

        Returns:
            True if excessive I/O detected
        """
        process = psutil.Process(pid)
        io_counters = process.io_counters()

        # Calculate write rate
        write_bytes = io_counters.write_bytes
        now = time.time()

        if deployment_id not in self.io_history:
            self.io_history[deployment_id] = deque(maxlen=10)

        history = self.io_history[deployment_id]
        history.append((now, write_bytes))

        if len(history) < 2:
            return False

        # Calculate MB/s
        time_diff = history[-1][0] - history[0][0]
        bytes_diff = history[-1][1] - history[0][1]
        mb_per_second = (bytes_diff / time_diff) / (1024 * 1024)

        return mb_per_second > self.threshold

# Integrate with UnifiedLocalOpsManager
unified_manager.disk_io_monitor = DiskIOMonitor()
```

## Testing Strategy

### Unit Tests

**Location**: `tests/services/local_ops/`

```python
# test_health_checks.py
class TestHTTPHealthCheck:
    """Test HTTP health check implementation."""

    def test_healthy_endpoint(self, mock_server):
        """Test health check against healthy endpoint."""
        check = HTTPHealthCheck()
        result = check.check("test-deployment", url="http://localhost:8000")

        assert result.status == HealthStatus.HEALTHY
        assert result.check_type == "http"
        assert "response_time_ms" in result.details

    def test_unhealthy_endpoint(self):
        """Test health check against non-existent endpoint."""
        check = HTTPHealthCheck()
        result = check.check("test-deployment", url="http://localhost:9999")

        assert result.status == HealthStatus.UNHEALTHY
        assert "Connection refused" in result.message

# test_restart_policy.py
class TestRestartPolicy:
    """Test restart policy logic."""

    def test_exponential_backoff(self):
        """Test exponential backoff calculation."""
        config = RestartConfig(
            max_attempts=5,
            initial_backoff_seconds=2.0,
            backoff_multiplier=2.0,
            max_backoff_seconds=300.0
        )
        policy = RestartPolicy(config)

        # First attempt: 2 seconds
        should_restart, backoff = policy.should_restart("test", 0)
        assert should_restart
        assert backoff == 2.0

        # Second attempt: 4 seconds
        should_restart, backoff = policy.should_restart("test", 1)
        assert should_restart
        assert backoff == 4.0

        # Third attempt: 8 seconds
        should_restart, backoff = policy.should_restart("test", 2)
        assert should_restart
        assert backoff == 8.0

    def test_max_attempts(self):
        """Test max attempts enforcement."""
        config = RestartConfig(max_attempts=3)
        policy = RestartPolicy(config)

        # Attempts 0-2: allowed
        assert policy.should_restart("test", 0)[0]
        assert policy.should_restart("test", 1)[0]
        assert policy.should_restart("test", 2)[0]

        # Attempt 3: blocked
        assert not policy.should_restart("test", 3)[0]
```

### Integration Tests

```python
# test_unified_manager_integration.py
class TestUnifiedManagerIntegration:
    """Integration tests for unified manager."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create UnifiedLocalOpsManager instance."""
        config = {
            'defaults': {
                'health_check_interval_seconds': 1,  # Fast for testing
                'auto_restart_enabled': False
            },
            'restart_policy': {
                'max_attempts': 3,
                'initial_backoff_seconds': 0.5,
                'max_backoff_seconds': 5.0,
                'backoff_multiplier': 2.0,
                'circuit_breaker_threshold': 2,
                'circuit_breaker_window_seconds': 60,
                'circuit_breaker_reset_seconds': 120
            },
            'stability': {
                'memory_leak_threshold_mb_per_minute': 10.0,
                'fd_threshold_percent': 0.8,
                'thread_threshold': 100
            },
            'log_monitoring': {
                'enabled': True,
                'error_patterns': ['ERROR', 'FATAL']
            }
        }

        return UnifiedLocalOpsManager(tmp_path, config)

    def test_full_deployment_lifecycle(self, manager):
        """Test complete deployment lifecycle."""
        # Start deployment
        config = StartConfig(
            command="python -m http.server 8000",
            port=8000,
            working_directory=Path.cwd()
        )

        deployment = manager.start_deployment(config, auto_restart=True)
        assert deployment.process_info.status == ProcessStatus.RUNNING

        # Check status
        status = manager.get_full_status(deployment.deployment_id)
        assert status['process'].pid > 0
        assert status['health'].overall_status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]

        # Stop deployment
        success = manager.stop_deployment(deployment.deployment_id)
        assert success

    def test_auto_restart_on_crash(self, manager):
        """Test auto-restart triggers on crash."""
        # Start deployment that will crash
        config = StartConfig(
            command="python -c 'import sys; sys.exit(1)'",
            port=None,
            working_directory=Path.cwd()
        )

        deployment = manager.start_deployment(config, auto_restart=True)

        # Wait for crash and restart
        time.sleep(3)

        # Check restart history
        history = manager.restart_manager.get_restart_history(deployment.deployment_id)
        assert history.total_restarts > 0
```

### End-to-End Tests

```python
# test_cli_e2e.py
class TestCLIEndToEnd:
    """End-to-end tests via CLI commands."""

    def test_start_stop_workflow(self, cli_runner):
        """Test start and stop via CLI."""
        # Start deployment
        result = cli_runner.invoke([
            'local-deploy', 'start',
            '--command', 'python -m http.server 8000',
            '--port', '8000',
            '--auto-restart'
        ])

        assert result.exit_code == 0
        assert 'deployment-' in result.output

        # Extract deployment ID
        deployment_id = extract_deployment_id(result.output)

        # Check status
        result = cli_runner.invoke(['local-deploy', 'status', deployment_id])
        assert result.exit_code == 0
        assert 'RUNNING' in result.output

        # Stop
        result = cli_runner.invoke(['local-deploy', 'stop', deployment_id])
        assert result.exit_code == 0
        assert 'stopped' in result.output.lower()
```

## Performance Considerations

### Background Monitoring Overhead

**Health Check Thread**:
- Default interval: 30 seconds
- CPU usage: <0.1% average
- Memory: ~2MB per deployment

**Optimization**:
```yaml
defaults:
  health_check_interval_seconds: 60  # Reduce frequency for lower overhead
```

### Memory Usage

**Per Deployment**:
- Process state: ~1KB
- Health history (100 checks): ~50KB
- Restart history: ~10KB
- Total: ~61KB per deployment

**Optimization**:
```python
# Limit history size
health_manager.set_history_limit(50)  # Default: 100
```

### Disk I/O

**State Persistence**:
- Write on state change only
- Typical: 1-2KB per write
- Frequency: Low (only on start/stop/config change)

**Log Monitoring**:
- Only reads new log lines
- Uses file seek for efficiency
- Typical: <100 bytes/second

### CPU Usage

**Process Monitoring** (psutil):
- CPU: <0.05% per process
- Increases with process count

**Resource Checks**:
- CPU, memory, FDs: <0.01% per check
- Network connections: <0.05% per check

## Integration Patterns

### With Local-Ops-Agent

```python
# Agent delegates to CLI commands
class LocalOpsAgent:
    """Agent integration pattern."""

    async def deploy_application(self, framework: str, port: int):
        """Deploy application with appropriate command."""

        # Detect framework and build command
        if framework == "nextjs":
            command = "npm run dev"
        elif framework == "django":
            command = f"python manage.py runserver {port}"
        else:
            command = self._detect_start_command()

        # Start deployment via CLI
        result = await self.run_command([
            'local-deploy', 'start',
            '--command', command,
            '--port', str(port),
            '--auto-restart',
            '--log-file', f'./logs/{framework}.log'
        ])

        deployment_id = self._extract_deployment_id(result.stdout)

        # Verify health
        await self._verify_deployment_health(deployment_id)

        # Monitor for initial stability
        await self._monitor_initial_period(deployment_id, duration=30)

        return deployment_id
```

### With PM2 (Compatibility Layer)

```python
# PM2 compatibility wrapper
class PM2CompatibilityLayer:
    """Wrapper for PM2-compatible API."""

    def __init__(self, unified_manager: UnifiedLocalOpsManager):
        self.manager = unified_manager

    def start(self, config: dict) -> dict:
        """PM2-style start method."""
        start_config = StartConfig(
            command=config['script'],
            port=config.get('port'),
            working_directory=Path(config.get('cwd', '.')),
            env=config.get('env', {})
        )

        deployment = self.manager.start_deployment(
            start_config,
            auto_restart=config.get('autorestart', False)
        )

        # Convert to PM2-style response
        return {
            'pm_id': deployment.deployment_id,
            'name': config.get('name', deployment.deployment_id),
            'pid': deployment.process_info.pid,
            'status': 'online' if deployment.process_info.status == ProcessStatus.RUNNING else 'stopped'
        }
```

## Related Documentation

- **[User Guide](../user/03-features/local-process-management.md)** - End-user documentation
- **[CLI Reference](../reference/LOCAL_OPS_COMMANDS.md)** - Complete CLI command reference
- **[Architecture Overview](ARCHITECTURE.md)** - Overall system architecture
- **[Testing Guide](TESTING.md)** - Testing strategies and patterns
- **[Services Guide](SERVICES.md)** - Service layer development

---

This developer guide provides comprehensive documentation of the Local Process Management system's architecture, implementation details, and extension points for developers working on the Claude MPM codebase.
