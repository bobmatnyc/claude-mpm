# Socket.IO Server Reliability Features

This document provides comprehensive documentation for the advanced reliability features implemented in the claude-mpm Socket.IO server, including PID validation, health monitoring, automatic recovery, and enhanced error handling systems.

## Table of Contents

1. [Overview](#overview)
2. [PID File Validation System](#pid-file-validation-system)
3. [Health Monitoring System](#health-monitoring-system)
4. [Automatic Recovery Mechanisms](#automatic-recovery-mechanisms)
5. [Enhanced Error Messaging](#enhanced-error-messaging)
6. [Configuration Guide](#configuration-guide)
7. [API Endpoints](#api-endpoints)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Migration Guide](#migration-guide)

## Overview

The Socket.IO server reliability features provide comprehensive monitoring, validation, and recovery capabilities to ensure robust service operation. These features work together to:

- Prevent daemon conflicts through enhanced process validation
- Monitor system health and detect issues early
- Automatically recover from failures using graduated response strategies
- Provide detailed error messages with actionable resolution steps
- Maintain service availability through circuit breaker patterns

### Key Benefits

- **High Availability**: Automatic recovery minimizes service downtime
- **Early Detection**: Health monitoring catches issues before they become critical
- **Conflict Prevention**: PID validation prevents multiple server instances
- **Actionable Errors**: Enhanced error messages include specific resolution steps
- **Graduated Recovery**: Proportionate response to different failure types

## PID File Validation System

The PID validation system ensures only one Socket.IO server instance runs per port and provides robust process identity checking.

### Features

#### Enhanced Process Identity Checking
- **psutil Integration**: Uses psutil for accurate process information when available
- **Process Validation**: Verifies process name, command line, and start time
- **Cross-Platform Support**: Works on Linux, macOS, and Windows
- **Fallback Mechanisms**: Graceful degradation when psutil is unavailable

#### File Locking Mechanism
- **Atomic Operations**: Uses file locking to prevent race conditions
- **JSON-Enriched Format**: PID files contain additional metadata
- **Lock Validation**: Ensures PID file integrity during read/write operations

#### Stale Process Detection
- **Zombie Detection**: Identifies and handles zombie processes
- **Process Status Validation**: Checks process health and accessibility
- **Automatic Cleanup**: Removes stale PID files automatically

### Implementation

```python
from claude_mpm.services.standalone_socketio_server import StandaloneSocketIOServer
from claude_mpm.services.exceptions import DaemonConflictError, StaleProcessError

# Server automatically handles PID validation
server = StandaloneSocketIOServer(host="localhost", port=8765)

try:
    server.start()
except DaemonConflictError as e:
    print(f"Server conflict: {e.message}")
    # Access structured error information
    print(f"Existing PID: {e.existing_pid}")
    print(f"Resolution steps: {e.context['resolution_steps']}")
except StaleProcessError as e:
    print(f"Stale process detected: {e.message}")
    print(f"Process status: {e.process_status}")
```

### JSON PID File Format

```json
{
    "pid": 12345,
    "server_id": "socketio-server-8765",
    "port": 8765,
    "host": "localhost",
    "start_time": "2025-08-06T14:30:00.000Z",
    "version": "1.2.0",
    "process_info": {
        "name": "python",
        "status": "running",
        "cpu_percent": 2.5,
        "memory_mb": 45.2
    },
    "lock_acquired": true,
    "created_by": "claude-mpm"
}
```

## Health Monitoring System

The health monitoring system provides comprehensive health checking capabilities with configurable thresholds and automated reporting.

### Health Checkers

#### Process Resource Checker
Monitors process-specific metrics:

```python
from claude_mpm.services.health_monitor import ProcessResourceChecker

# Initialize with custom thresholds
checker = ProcessResourceChecker(
    pid=server_pid,
    cpu_threshold=80.0,        # CPU usage percentage
    memory_threshold_mb=500,   # Memory usage in MB
    fd_threshold=1000         # File descriptor count
)

# Metrics collected:
# - CPU usage percentage
# - Memory usage (RSS, VMS)
# - File descriptor count
# - Thread count
# - Process status and start time
```

#### Network Connectivity Checker
Monitors network-specific metrics:

```python
from claude_mpm.services.health_monitor import NetworkConnectivityChecker

checker = NetworkConnectivityChecker(
    host="localhost",
    port=8765,
    timeout=1.0
)

# Metrics collected:
# - Port accessibility
# - Socket creation capability
# - Network interface status
```

#### Service Health Checker
Monitors service-specific metrics:

```python
from claude_mpm.services.health_monitor import ServiceHealthChecker

# Service stats dictionary (updated by server)
service_stats = {
    "clients_connected": 15,
    "events_processed": 1250,
    "errors": 2,
    "last_activity": "2025-08-06T14:35:00.000Z"
}

checker = ServiceHealthChecker(
    service_stats=service_stats,
    max_clients=1000,
    max_error_rate=0.1
)

# Metrics collected:
# - Connected clients count
# - Event processing rate
# - Error rates
# - Time since last activity
```

### Advanced Health Monitor

The `AdvancedHealthMonitor` integrates multiple health checkers:

```python
from claude_mpm.services.health_monitor import AdvancedHealthMonitor

# Initialize monitor
monitor = AdvancedHealthMonitor({
    'check_interval': 30,      # Check every 30 seconds
    'history_size': 100,       # Keep 100 health check results
    'aggregation_window': 300  # 5-minute aggregation window
})

# Add health checkers
monitor.add_checker(ProcessResourceChecker(server_pid))
monitor.add_checker(NetworkConnectivityChecker("localhost", 8765))
monitor.add_checker(ServiceHealthChecker(service_stats))

# Start continuous monitoring
monitor.start_monitoring()

# Get current status
current_status = monitor.get_current_status()
print(f"Overall health: {current_status.overall_status.value}")

# Get aggregated health over time window
aggregated = monitor.get_aggregated_status(window_seconds=600)
print(f"10-minute health summary: {aggregated['overall_status']}")
```

### Health Status Levels

```python
from claude_mpm.services.health_monitor import HealthStatus

# Status hierarchy (from best to worst)
HealthStatus.HEALTHY    # All metrics within normal ranges
HealthStatus.WARNING    # Some metrics elevated but not critical
HealthStatus.CRITICAL   # Critical issues requiring immediate attention
HealthStatus.UNKNOWN    # Unable to determine health status
```

### Health Callbacks

Register callbacks to respond to health changes:

```python
def health_change_handler(result):
    if result.overall_status == HealthStatus.CRITICAL:
        # Trigger recovery or alerting
        recovery_manager.handle_health_result(result)

monitor.add_health_callback(health_change_handler)
```

## Automatic Recovery Mechanisms

The recovery system provides automated failure recovery with circuit breaker protection.

### Recovery Strategies

#### Graded Recovery Strategy
Implements graduated response based on failure severity:

```python
from claude_mpm.services.recovery_manager import GradedRecoveryStrategy

strategy = GradedRecoveryStrategy({
    'warning_threshold': 2,           # Failures before action on warnings
    'critical_threshold': 1,          # Failures before action on critical
    'failure_window_seconds': 300,    # Time window for failure counting
    'min_recovery_interval': 60       # Minimum time between recoveries
})
```

**Recovery Action Escalation:**

1. **Healthy** → No action
2. **Warning** (repeated) → Log warning → Clear connections
3. **Critical** → Clear connections → Restart service → Emergency stop

#### Recovery Actions

```python
from claude_mpm.services.recovery_manager import RecoveryAction

RecoveryAction.NONE             # No action required
RecoveryAction.LOG_WARNING      # Log detailed warning information
RecoveryAction.CLEAR_CONNECTIONS # Disconnect all clients, reset state
RecoveryAction.RESTART_SERVICE  # Graceful service restart
RecoveryAction.EMERGENCY_STOP   # Force immediate shutdown
```

### Circuit Breaker Pattern

Prevents recovery loops and cascading failures:

```python
from claude_mpm.services.recovery_manager import CircuitBreaker

breaker = CircuitBreaker(
    failure_threshold=5,      # Failures before opening circuit
    timeout_seconds=300,      # Time in OPEN state
    success_threshold=3       # Successes needed to close circuit
)

# Circuit states
CircuitState.CLOSED     # Normal operation, recovery allowed
CircuitState.OPEN       # Recovery blocked due to failures
CircuitState.HALF_OPEN  # Testing recovery capability
```

### Recovery Manager

```python
from claude_mpm.services.recovery_manager import RecoveryManager

# Initialize recovery manager
recovery_manager = RecoveryManager({
    'enabled': True,
    'check_interval': 60,
    'max_recovery_attempts': 5,
    'recovery_timeout': 30,
    'circuit_breaker': {
        'failure_threshold': 5,
        'timeout_seconds': 300,
        'success_threshold': 3
    },
    'strategy': {
        'warning_threshold': 2,
        'critical_threshold': 1,
        'failure_window_seconds': 300
    }
}, server_instance=server)

# Handle health results automatically
monitor.add_health_callback(recovery_manager.handle_health_result)

# Get recovery status
status = recovery_manager.get_recovery_status()
print(f"Recovery enabled: {status['enabled']}")
print(f"Circuit breaker state: {status['circuit_breaker']['state']}")
```

### Recovery Event Logging

All recovery actions are logged with detailed information:

```python
# Recovery events include:
{
    "timestamp": 1691325000.123,
    "timestamp_iso": "2025-08-06T14:30:00.123Z",
    "action": "restart_service",
    "trigger": "health_check",
    "health_status": "critical",
    "success": true,
    "duration_ms": 2500.5,
    "error_message": null
}

# Access recovery history
history = recovery_manager.get_recovery_history(limit=10)
for event in history:
    print(f"{event.timestamp_iso}: {event.action} ({'success' if event.success else 'failed'})")
```

## Enhanced Error Messaging

The error handling system provides detailed, actionable error messages with specific resolution steps.

### Error Classes

#### DaemonConflictError
Raised when attempting to start a server while another instance is running:

```python
from claude_mpm.services.exceptions import DaemonConflictError

try:
    server.start()
except DaemonConflictError as e:
    print(e.message)  # Detailed error with process information
    print(f"Existing PID: {e.existing_pid}")
    print(f"Process info: {e.process_info}")
    
    # Get resolution steps
    for i, step in enumerate(e.context['resolution_steps'], 1):
        print(f"{i}. {step}")
```

**Example Error Output:**
```
🚫 Socket.IO server conflict detected on port 8765

CONFLICT DETAILS:
  • Existing PID: 12345
  • Server ID: socketio-server-8765
  • Process Status: running
  • Process Name: python
  • Started: 2025-08-06 14:20:15 (uptime: 900s)
  • Memory Usage: 45.2 MB
  • PID File: /home/user/.claude-mpm/socketio-server.pid

RESOLUTION STEPS:
  1. Check if the existing server is still needed: ps -p 12345
  2. Stop the existing server gracefully: kill -TERM 12345
  3. If graceful shutdown fails: kill -KILL 12345
  4. Remove stale PID file if needed: rm /home/user/.claude-mpm/socketio-server.pid
  5. Wait a few seconds for port cleanup
  6. Try starting the server again on port 8765
  7. Alternative: Use a different port with --port <new_port>
```

#### PortConflictError
Raised when a network port is already in use:

```python
from claude_mpm.services.exceptions import PortConflictError

try:
    server.bind_port()
except PortConflictError as e:
    print(f"Port {e.port} is in use by PID {e.conflicting_process['pid']}")
```

#### StaleProcessError
Raised when dealing with stale processes or PID files:

```python
from claude_mpm.services.exceptions import StaleProcessError

# Automatically handled during server startup
# Provides cleanup guidance for stale processes
```

#### RecoveryFailedError
Raised when automatic recovery mechanisms fail:

```python
from claude_mpm.services.exceptions import RecoveryFailedError

# Contains information about:
# - Failed recovery action
# - Failure reason
# - Attempt count
# - Current health status
# - Manual resolution steps
```

#### HealthCheckError
Raised when health monitoring detects critical issues:

```python
from claude_mpm.services.exceptions import HealthCheckError

# Provides details about:
# - Failed health check
# - Exceeded thresholds
# - Recommended actions
# - System health context
```

### Platform-Specific Commands

Error messages include platform-specific diagnostic commands:

**Linux/macOS:**
```bash
# Check port usage
lsof -i :8765
netstat -tulpn | grep 8765

# Check process
ps -p 12345 -o pid,ppid,cmd
```

**Windows:**
```cmd
# Check port usage
netstat -ano | findstr 8765
tasklist /fi "PID eq 12345"
```

### Troubleshooting Guide Generator

```python
from claude_mpm.services.exceptions import format_troubleshooting_guide

try:
    server.start()
except Exception as e:
    if isinstance(e, SocketIOServerError):
        guide = format_troubleshooting_guide(e)
        print(guide)
        
        # Save to file for reference
        with open('troubleshooting.txt', 'w') as f:
            f.write(guide)
```

## Configuration Guide

### Server Configuration

```python
# Basic configuration
server_config = {
    'host': 'localhost',
    'port': 8765,
    'health_monitoring': {
        'enabled': True,
        'check_interval': 30,
        'thresholds': {
            'cpu_percent': 80.0,
            'memory_mb': 500,
            'file_descriptors': 1000
        }
    },
    'recovery': {
        'enabled': True,
        'strategy': 'graded',
        'circuit_breaker': {
            'failure_threshold': 5,
            'timeout_seconds': 300
        }
    },
    'pid_validation': {
        'enhanced': True,
        'use_psutil': True,
        'lock_timeout': 5.0
    }
}

server = StandaloneSocketIOServer(**server_config)
```

### Environment-Specific Configuration

```python
# Development environment
dev_config = {
    'health_monitoring': {
        'check_interval': 10,  # More frequent checks
        'history_size': 50
    },
    'recovery': {
        'circuit_breaker': {
            'failure_threshold': 3  # Lower threshold for faster feedback
        }
    }
}

# Production environment  
prod_config = {
    'health_monitoring': {
        'check_interval': 60,   # Less frequent checks
        'history_size': 200,    # Longer history
        'aggregation_window': 600
    },
    'recovery': {
        'circuit_breaker': {
            'failure_threshold': 10,  # Higher threshold for stability
            'timeout_seconds': 600    # Longer recovery timeout
        }
    }
}
```

### Configuration Files

Create configuration files for different environments:

**`~/.claude-mpm/socketio-config.json`:**
```json
{
    "server": {
        "host": "localhost",
        "port": 8765,
        "enable_cors": true
    },
    "health_monitoring": {
        "enabled": true,
        "check_interval": 30,
        "thresholds": {
            "cpu_percent": 80.0,
            "memory_mb": 500,
            "file_descriptors": 1000,
            "error_rate": 0.1
        }
    },
    "recovery": {
        "enabled": true,
        "strategy": "graded",
        "min_recovery_interval": 60,
        "circuit_breaker": {
            "failure_threshold": 5,
            "timeout_seconds": 300,
            "success_threshold": 3
        }
    },
    "logging": {
        "level": "INFO",
        "file": "~/.claude-mpm/socketio-server.log",
        "max_size_mb": 50,
        "backup_count": 5
    }
}
```

## API Endpoints

The Socket.IO server provides several HTTP endpoints for health monitoring and diagnostics.

### Health Endpoint

**GET `/health`**

Returns current health status:

```json
{
    "status": "healthy",
    "timestamp": "2025-08-06T14:35:00.000Z",
    "uptime_seconds": 3600,
    "version": "1.2.0",
    "pid": 12345,
    "checks": {
        "process_resources": "healthy",
        "network_connectivity": "healthy",
        "service_health": "healthy"
    },
    "metrics": {
        "cpu_percent": 15.2,
        "memory_mb": 45.8,
        "clients_connected": 3,
        "events_processed": 1250
    }
}
```

### Diagnostics Endpoint

**GET `/diagnostics`**

Returns detailed diagnostic information:

```json
{
    "server_info": {
        "version": "1.2.0",
        "pid": 12345,
        "start_time": "2025-08-06T13:35:00.000Z",
        "uptime_seconds": 3600,
        "host": "localhost",
        "port": 8765
    },
    "health_monitor": {
        "enabled": true,
        "last_check": "2025-08-06T14:34:30.000Z",
        "overall_status": "healthy",
        "checks_performed": 120,
        "checks_failed": 2
    },
    "recovery_manager": {
        "enabled": true,
        "circuit_breaker_state": "closed",
        "total_recoveries": 0,
        "successful_recoveries": 0,
        "failed_recoveries": 0
    },
    "process_info": {
        "cpu_percent": 15.2,
        "memory_mb": 45.8,
        "file_descriptors": 25,
        "thread_count": 8
    }
}
```

### Metrics Endpoint

**GET `/metrics`**

Returns metrics in Prometheus format (optional):

```
# HELP socketio_uptime_seconds Server uptime in seconds
# TYPE socketio_uptime_seconds counter
socketio_uptime_seconds 3600

# HELP socketio_clients_connected Number of connected clients
# TYPE socketio_clients_connected gauge
socketio_clients_connected 3

# HELP socketio_events_processed_total Total number of events processed
# TYPE socketio_events_processed_total counter
socketio_events_processed_total 1250

# HELP socketio_health_status Current health status (0=unknown, 1=healthy, 2=warning, 3=critical)
# TYPE socketio_health_status gauge
socketio_health_status 1
```

### Status Endpoint

**GET `/status`**

Returns brief status information:

```json
{
    "status": "running",
    "version": "1.2.0",
    "uptime": 3600,
    "clients": 3,
    "health": "healthy"
}
```

## Troubleshooting Guide

### Common Issues

#### Server Won't Start

**Symptom:** Server fails to start with daemon conflict error

**Diagnosis:**
```bash
# Check if server is already running
ps aux | grep socketio
lsof -i :8765

# Check PID file
cat ~/.claude-mpm/socketio-server.pid
```

**Solutions:**
1. Stop existing server: `kill -TERM <PID>`
2. Remove stale PID file: `rm ~/.claude-mpm/socketio-server.pid`
3. Use different port: `--port 8766`

#### Health Checks Failing

**Symptom:** Continuous health check warnings or critical status

**Diagnosis:**
```bash
# Check server diagnostics
curl http://localhost:8765/diagnostics

# Check system resources
top -p <SERVER_PID>
df -h
```

**Solutions:**
1. Adjust health check thresholds
2. Increase system resources
3. Review application load patterns
4. Check for memory leaks

#### Recovery Loop

**Symptom:** Server continuously restarting, circuit breaker opens

**Diagnosis:**
```bash
# Check recovery history
curl http://localhost:8765/diagnostics | jq '.recovery_manager'

# Check server logs
tail -f ~/.claude-mpm/socketio-server.log
```

**Solutions:**
1. Identify root cause from logs
2. Adjust recovery thresholds
3. Disable recovery temporarily
4. Fix underlying system issues

#### Port Already in Use

**Symptom:** PortConflictError when starting server

**Diagnosis:**
```bash
# Linux/macOS
lsof -i :8765
netstat -tulpn | grep 8765

# Windows
netstat -ano | findstr 8765
```

**Solutions:**
1. Stop conflicting process
2. Use different port
3. Wait for port cleanup (30-60 seconds)

### Debug Mode

Enable debug mode for detailed logging:

```bash
# Set environment variable
export CLAUDE_MPM_DEBUG=1

# Or in code
import logging
logging.getLogger('claude_mpm').setLevel(logging.DEBUG)
```

### Log Analysis

Common log patterns to look for:

```bash
# Health check failures
grep "Health check failed" ~/.claude-mpm/socketio-server.log

# Recovery events
grep "Recovery action" ~/.claude-mpm/socketio-server.log

# Circuit breaker events
grep "Circuit breaker" ~/.claude-mpm/socketio-server.log

# Process validation issues
grep "PID validation" ~/.claude-mpm/socketio-server.log
```

### Performance Tuning

Optimize for different scenarios:

**High-Traffic Environments:**
```python
config = {
    'health_monitoring': {
        'check_interval': 60,     # Less frequent checks
        'thresholds': {
            'cpu_percent': 90.0,  # Higher CPU threshold
            'memory_mb': 1000     # Higher memory threshold
        }
    },
    'recovery': {
        'circuit_breaker': {
            'failure_threshold': 10  # Higher failure tolerance
        }
    }
}
```

**Development Environments:**
```python
config = {
    'health_monitoring': {
        'check_interval': 10,     # Frequent checks for quick feedback
        'thresholds': {
            'cpu_percent': 50.0,  # Lower thresholds for early detection
            'memory_mb': 200
        }
    },
    'recovery': {
        'circuit_breaker': {
            'failure_threshold': 3   # Quick recovery testing
        }
    }
}
```

## Migration Guide

### Upgrading from Basic Socket.IO Server

If you're upgrading from a basic Socket.IO implementation:

1. **Update Dependencies**
   ```bash
   pip install psutil  # For enhanced process monitoring
   ```

2. **Update Server Initialization**
   ```python
   # Old way
   from claude_mpm.services.socketio_server import SocketIOServer
   server = SocketIOServer()
   
   # New way
   from claude_mpm.services.standalone_socketio_server import StandaloneSocketIOServer
   server = StandaloneSocketIOServer(
       host="localhost",
       port=8765,
       enable_health_monitoring=True,
       enable_recovery=True
   )
   ```

3. **Update Error Handling**
   ```python
   # Add specific error handling
   from claude_mpm.services.exceptions import (
       DaemonConflictError, PortConflictError, 
       StaleProcessError, HealthCheckError
   )
   
   try:
       server.start()
   except DaemonConflictError as e:
       print(f"Server conflict: {e}")
       # Handle conflict resolution
   except PortConflictError as e:
       print(f"Port conflict: {e}")
       # Handle port issues
   ```

4. **Add Health Monitoring**
   ```python
   # Optional: Custom health callbacks
   def health_callback(result):
       if result.overall_status.value == 'critical':
           # Custom alerting logic
           send_alert(f"Server health critical: {result}")
   
   server.health_monitor.add_health_callback(health_callback)
   ```

### Configuration Migration

Convert existing configuration:

```python
# Old configuration
old_config = {
    'host': 'localhost',
    'port': 8765,
    'cors_allowed_origins': ['*']
}

# New configuration with reliability features
new_config = {
    'host': 'localhost',
    'port': 8765,
    'cors_allowed_origins': ['*'],
    'health_monitoring': {
        'enabled': True,
        'check_interval': 30
    },
    'recovery': {
        'enabled': True,
        'strategy': 'graded'
    },
    'pid_validation': {
        'enhanced': True
    }
}
```

### Testing Migration

Verify reliability features are working:

```python
# Test health monitoring
health_status = server.health_monitor.get_current_status()
assert health_status is not None
assert health_status.overall_status in [HealthStatus.HEALTHY, HealthStatus.WARNING]

# Test PID validation
assert server.pid_file.exists()
with open(server.pid_file) as f:
    pid_data = json.load(f)
    assert pid_data['pid'] == os.getpid()

# Test recovery manager
recovery_status = server.recovery_manager.get_recovery_status()
assert recovery_status['enabled'] is True
assert recovery_status['circuit_breaker']['state'] == 'closed'
```

---

This comprehensive documentation provides everything needed to understand, configure, and troubleshoot the Socket.IO server reliability features. The system is designed to provide robust, self-healing service operation with detailed observability and automated recovery capabilities.