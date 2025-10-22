# Local Process Management

Learn how to deploy, monitor, and manage local development processes with Claude MPM's comprehensive process management system.

## What is Local Process Management?

Local Process Management is a sophisticated system for running and monitoring development servers, build processes, and other localhost deployments with:

- **Automated Health Monitoring**: Three-tier health checks (HTTP, process, resource)
- **Auto-Restart on Crash**: Exponential backoff with circuit breaker protection
- **Memory Leak Detection**: Preemptive restart before out-of-memory crashes
- **Log Error Monitoring**: Pattern-based detection of application errors
- **Resource Exhaustion Prevention**: Track CPU, memory, file descriptors, threads
- **Graceful Shutdown**: Clean process termination with configurable timeouts

### Key Benefits

- **Reliability**: Auto-restart keeps your development servers running through crashes
- **Observability**: Real-time health monitoring and comprehensive status reporting
- **Stability**: Detect and prevent memory leaks and resource exhaustion
- **Convenience**: Single command to start deployments with full monitoring
- **Team Consistency**: YAML configuration for standardized process management

## Getting Started

### Quick Start

Start a development server with monitoring:

```bash
# Start Next.js development server with auto-restart
claude-mpm local-deploy start \
  --command "npm run dev" \
  --port 3000 \
  --auto-restart

# Start Django development server
claude-mpm local-deploy start \
  --command "python manage.py runserver 8000" \
  --port 8000 \
  --auto-restart

# Start with custom log monitoring
claude-mpm local-deploy start \
  --command "npm run dev" \
  --port 3000 \
  --auto-restart \
  --log-file ./logs/dev-server.log
```

### Basic Workflow

1. **Start a deployment**:
   ```bash
   claude-mpm local-deploy start --command "npm run dev" --port 3000 --auto-restart
   # Returns: deployment-12345678
   ```

2. **Check status**:
   ```bash
   claude-mpm local-deploy status deployment-12345678
   ```

3. **Monitor live**:
   ```bash
   claude-mpm local-deploy monitor deployment-12345678
   # Press Ctrl+C to exit monitoring
   ```

4. **Stop when done**:
   ```bash
   claude-mpm local-deploy stop deployment-12345678
   ```

## Core Features

### 1. Process Management

**Background Process Spawning**: Processes run in the background with proper isolation

```bash
# Start process with custom working directory
claude-mpm local-deploy start \
  --command "npm run dev" \
  --working-directory /path/to/project \
  --port 3000

# Start with environment variables
claude-mpm local-deploy start \
  --command "python manage.py runserver" \
  --port 8000 \
  --env NODE_ENV=development \
  --env DEBUG=true
```

**Port Conflict Prevention**: Automatic port finding when requested port is unavailable

```bash
# Auto-find alternative port if 3000 is taken
claude-mpm local-deploy start \
  --command "npm run dev" \
  --port 3000 \
  --auto-find-port

# Disable auto-find (fail if port unavailable)
claude-mpm local-deploy start \
  --command "npm run dev" \
  --port 3000 \
  --no-auto-find-port
```

### 2. Health Monitoring

**Three-Tier Health Checks**:

1. **HTTP Health Check**: Verifies the service responds to HTTP requests
   - Checks endpoint availability
   - Measures response time
   - Validates status codes (2xx/3xx)
   - Supports SSL/TLS

2. **Process Health Check**: Verifies the process is alive and responsive
   - Confirms process existence
   - Checks process status (running vs zombie)
   - Validates CPU activity
   - Detects exit codes

3. **Resource Health Check**: Monitors resource consumption
   - CPU usage (default threshold: 80%)
   - Memory usage (default threshold: 500MB)
   - File descriptors (default threshold: 1000)
   - Thread count (default threshold: 100)
   - Network connections

**Check Health Status**:

```bash
# View health check results
claude-mpm local-deploy health deployment-12345678

# Output shows:
# - Overall health status (HEALTHY/DEGRADED/UNHEALTHY)
# - Individual check results
# - Response times
# - Resource usage metrics
```

**Background Monitoring**: Health checks run automatically in background thread

```yaml
# Default check interval: 30 seconds
# Configurable via .claude-mpm/local-ops-config.yaml
defaults:
  health_check_interval_seconds: 30
```

### 3. Auto-Restart System

**Crash Detection**: Automatically detects when process crashes or exits

**Exponential Backoff**: Prevents restart loops with intelligent backoff

```yaml
# Default restart policy
restart_policy:
  max_attempts: 5                    # Give up after 5 failures
  initial_backoff_seconds: 2.0      # Start with 2s delay
  max_backoff_seconds: 300.0        # Cap at 5 minutes
  backoff_multiplier: 2.0           # Double delay each time
```

**Circuit Breaker Protection**: Stops restart attempts after too many failures

```yaml
restart_policy:
  circuit_breaker_threshold: 3            # Open after 3 failures
  circuit_breaker_window_seconds: 300     # Within 5 minute window
  circuit_breaker_reset_seconds: 600      # Try again after 10 minutes
```

**Enable/Disable Auto-Restart**:

```bash
# Enable for existing deployment
claude-mpm local-deploy enable-auto-restart deployment-12345678

# Disable auto-restart
claude-mpm local-deploy disable-auto-restart deployment-12345678

# Enable at startup
claude-mpm local-deploy start --command "npm run dev" --auto-restart
```

**View Restart History**:

```bash
# See restart attempts and outcomes
claude-mpm local-deploy history deployment-12345678

# Output shows:
# - Total restarts (successful/failed)
# - Circuit breaker state
# - Recent restart attempts with timestamps
# - Failure reasons
```

### 4. Stability Enhancements

**Memory Leak Detection**: Preemptively restart before out-of-memory crashes

```yaml
stability:
  # Restart if memory grows >10MB per minute
  memory_leak_threshold_mb_per_minute: 10.0
```

**Log Pattern Monitoring**: Detect errors in application logs

```yaml
log_monitoring:
  enabled: true
  error_patterns:
    - "OutOfMemoryError"
    - "Segmentation fault"
    - "Exception:"
    - "FATAL"
    - "panic:"
    - "UnhandledPromiseRejectionWarning"
```

**Resource Exhaustion Prevention**: Monitor and prevent resource limits

```yaml
stability:
  fd_threshold_percent: 0.8        # 80% of file descriptor limit
  thread_threshold: 1000           # Maximum thread count
  connection_threshold: 500        # Maximum network connections
  disk_threshold_mb: 100          # Minimum free disk space
```

## CLI Commands

### List All Deployments

```bash
# List all deployments
claude-mpm local-deploy list

# Filter by status
claude-mpm local-deploy list --status running
claude-mpm local-deploy list --status stopped

# Output shows:
# - Deployment ID
# - Command
# - Port
# - Status (running/stopped/crashed)
# - PID
# - Uptime
```

### Comprehensive Status

```bash
# Get full status
claude-mpm local-deploy status deployment-12345678

# JSON output for scripting
claude-mpm local-deploy status deployment-12345678 --json

# Status includes:
# - Process information (PID, status, uptime)
# - Health check results (HTTP, process, resource)
# - Restart history (attempts, circuit breaker state)
# - Memory trend (growth rate, leak detection)
# - Resource usage (CPU, memory, FDs, threads)
```

### Live Monitoring

```bash
# Monitor with default 2-second refresh
claude-mpm local-deploy monitor deployment-12345678

# Custom refresh interval
claude-mpm local-deploy monitor deployment-12345678 --refresh 5

# Dashboard shows:
# - Real-time process metrics
# - Health status (live updates)
# - Resource consumption graphs
# - Recent log entries (if configured)
```

### Restart Deployment

```bash
# Graceful restart
claude-mpm local-deploy restart deployment-12345678

# Custom shutdown timeout
claude-mpm local-deploy restart deployment-12345678 --timeout 30
```

### Stop Deployment

```bash
# Graceful stop (default 10s timeout)
claude-mpm local-deploy stop deployment-12345678

# Custom timeout
claude-mpm local-deploy stop deployment-12345678 --timeout 30

# Force kill immediately
claude-mpm local-deploy stop deployment-12345678 --force
```

## Configuration

### Configuration File

Create `.claude-mpm/local-ops-config.yaml` to customize behavior:

```yaml
version: "1.0"

# Default settings for all deployments
defaults:
  health_check_interval_seconds: 30
  auto_restart_enabled: false

# Restart policy
restart_policy:
  max_attempts: 5
  initial_backoff_seconds: 2.0
  max_backoff_seconds: 300.0
  backoff_multiplier: 2.0
  circuit_breaker_threshold: 3
  circuit_breaker_window_seconds: 300
  circuit_breaker_reset_seconds: 600

# Stability monitoring
stability:
  memory_leak_threshold_mb_per_minute: 10.0
  fd_threshold_percent: 0.8
  thread_threshold: 1000
  connection_threshold: 500
  disk_threshold_mb: 100

# Log monitoring
log_monitoring:
  enabled: true
  error_patterns:
    - "OutOfMemoryError"
    - "Exception:"
    - "FATAL"
    - "panic:"
```

**Example Configuration**: See `.claude-mpm/local-ops-config.yaml.example`

### Configuration Sections

**Defaults**: Global settings for all deployments
- `health_check_interval_seconds`: How often to run health checks
- `auto_restart_enabled`: Default auto-restart setting

**Restart Policy**: Controls auto-restart behavior
- `max_attempts`: Maximum restart attempts before giving up
- Backoff settings: Control delay between restart attempts
- Circuit breaker: Prevent restart loops

**Stability**: Resource monitoring thresholds
- Memory leak detection threshold
- File descriptor, thread, connection limits
- Disk space requirements

**Log Monitoring**: Error pattern detection
- Enable/disable log monitoring
- Custom error patterns to detect

## Common Use Cases

### 1. Next.js Development Server

```bash
# Start with auto-restart and monitoring
claude-mpm local-deploy start \
  --command "npm run dev" \
  --port 3000 \
  --auto-restart \
  --log-file ./logs/nextjs.log

# Monitor for issues
claude-mpm local-deploy monitor <deployment-id>

# Stop when done
claude-mpm local-deploy stop <deployment-id>
```

### 2. Django Development Server

```bash
# Start Django with custom environment
claude-mpm local-deploy start \
  --command "python manage.py runserver 8000" \
  --port 8000 \
  --auto-restart \
  --env DJANGO_DEBUG=True \
  --env DATABASE_URL=postgresql://localhost/dev

# Check health
claude-mpm local-deploy health <deployment-id>
```

### 3. Multiple Microservices

```bash
# Start API server
claude-mpm local-deploy start \
  --command "npm run start:api" \
  --port 8080 \
  --auto-restart

# Start frontend
claude-mpm local-deploy start \
  --command "npm run dev" \
  --port 3000 \
  --auto-restart

# Start background worker
claude-mpm local-deploy start \
  --command "python worker.py" \
  --auto-restart \
  --log-file ./logs/worker.log

# List all deployments
claude-mpm local-deploy list
```

### 4. Long-Running Build Process

```bash
# Start build with monitoring
claude-mpm local-deploy start \
  --command "npm run build:watch" \
  --auto-restart \
  --log-file ./logs/build.log

# Monitor resource usage
claude-mpm local-deploy monitor <deployment-id>

# Check for memory leaks
claude-mpm local-deploy status <deployment-id> | grep -i memory
```

## Troubleshooting

### Deployment Won't Start

**Check port availability**:
```bash
# Try with auto-find-port
claude-mpm local-deploy start \
  --command "npm run dev" \
  --port 3000 \
  --auto-find-port

# Check what's using the port
lsof -i :3000
```

**Check command validity**:
```bash
# Test command manually first
npm run dev

# Ensure full command path if needed
claude-mpm local-deploy start \
  --command "/usr/local/bin/npm run dev" \
  --port 3000
```

### Deployment Keeps Crashing

**Check restart history**:
```bash
# View restart attempts and failures
claude-mpm local-deploy history <deployment-id>

# Common issues shown:
# - Exit code indicates reason
# - Circuit breaker opened (too many failures)
# - Memory leak detected
# - Resource exhaustion
```

**Check health status**:
```bash
# See which health checks are failing
claude-mpm local-deploy health <deployment-id>

# Common issues:
# - HTTP check failing: service not binding to port
# - Process check failing: process crashing immediately
# - Resource check failing: out of memory/file descriptors
```

**Review logs**:
```bash
# If log file specified, check for errors
tail -f ./logs/dev-server.log

# Look for error patterns that trigger restarts
grep -E "Exception|Error|FATAL" ./logs/dev-server.log
```

### High Memory Usage

**Monitor memory trend**:
```bash
# Check memory growth rate
claude-mpm local-deploy status <deployment-id> | grep -i memory

# Watch for memory leak detection
claude-mpm local-deploy monitor <deployment-id>
```

**Adjust threshold if needed**:
```yaml
# .claude-mpm/local-ops-config.yaml
stability:
  memory_leak_threshold_mb_per_minute: 20.0  # Increase if false positives
```

### Circuit Breaker Opened

**Check restart history**:
```bash
claude-mpm local-deploy history <deployment-id>
# Shows: "Circuit breaker OPEN - too many failures"
```

**Options to resolve**:
1. **Fix the underlying issue** causing crashes
2. **Wait for circuit breaker to reset** (default: 10 minutes)
3. **Manually restart** after fixing:
   ```bash
   claude-mpm local-deploy restart <deployment-id>
   ```
4. **Adjust circuit breaker settings**:
   ```yaml
   restart_policy:
     circuit_breaker_threshold: 5      # Allow more failures
     circuit_breaker_window_seconds: 600  # Longer time window
   ```

### Deployment Not Responding

**Check process status**:
```bash
# Verify process is running
claude-mpm local-deploy list

# Check detailed status
claude-mpm local-deploy status <deployment-id>
```

**Check health**:
```bash
# See which checks are failing
claude-mpm local-deploy health <deployment-id>

# Common issues:
# - Process running but HTTP not responding (app issue)
# - Process zombie/hung (needs restart)
# - Resource exhaustion (out of FDs, threads)
```

**Manual intervention**:
```bash
# Try graceful restart
claude-mpm local-deploy restart <deployment-id>

# Force restart if hung
claude-mpm local-deploy stop <deployment-id> --force
claude-mpm local-deploy start --command "..." --port ... --auto-restart
```

## Best Practices

### Development Workflow

1. **Always use auto-restart** for development servers:
   ```bash
   --auto-restart
   ```
   Keeps server running through code errors and crashes.

2. **Specify log files** for better debugging:
   ```bash
   --log-file ./logs/dev-server.log
   ```
   Enables error pattern monitoring and easier troubleshooting.

3. **Monitor on startup** to verify health:
   ```bash
   claude-mpm local-deploy start ... && \
   claude-mpm local-deploy monitor <deployment-id>
   ```

4. **Check status before reporting issues**:
   ```bash
   claude-mpm local-deploy status <deployment-id>
   ```
   Provides comprehensive diagnostic information.

### Configuration Management

1. **Create project-specific config**:
   ```bash
   cp .claude-mpm/local-ops-config.yaml.example \
      .claude-mpm/local-ops-config.yaml
   ```

2. **Customize for your stack**:
   - Adjust memory thresholds for memory-intensive apps
   - Add custom error patterns for your framework
   - Configure circuit breaker for expected failure rates

3. **Version control your config**:
   ```bash
   git add .claude-mpm/local-ops-config.yaml
   ```
   Share configuration with team for consistency.

### Resource Management

1. **Monitor resource usage** for long-running processes:
   ```bash
   claude-mpm local-deploy monitor <deployment-id>
   ```

2. **Set appropriate thresholds** for your application:
   ```yaml
   stability:
     memory_leak_threshold_mb_per_minute: 15.0  # Adjust based on normal growth
   ```

3. **Clean up stopped deployments**:
   ```bash
   # List all deployments
   claude-mpm local-deploy list

   # Stop unused ones
   claude-mpm local-deploy stop <deployment-id>
   ```

### Team Collaboration

1. **Share configuration** in version control
2. **Document custom commands** in project README
3. **Use consistent port ranges** for different services
4. **Create deployment scripts** for complex setups:
   ```bash
   #!/bin/bash
   # start-dev.sh
   claude-mpm local-deploy start \
     --command "npm run dev" \
     --port 3000 \
     --auto-restart \
     --log-file ./logs/nextjs.log
   ```

## Integration with Claude MPM Agents

The local-ops-agent can automatically manage deployments using these commands:

```bash
# Delegate to local-ops-agent
claude-mpm run --agent local-ops "Start Next.js development server on port 3000 with auto-restart"

# Agent will:
# 1. Detect framework (Next.js)
# 2. Find appropriate start command
# 3. Start deployment with monitoring
# 4. Enable auto-restart
# 5. Verify health checks pass
# 6. Report deployment URL and status
```

See [Local Agents Guide](local-agents.md) for more on agent integration.

## Advanced Topics

### Custom Health Checks

Health checks are configurable but not extensible via config file. For custom health checks, see [Developer Guide - Local Process Management](../../developer/LOCAL_PROCESS_MANAGEMENT.md).

### Performance Tuning

**Adjust health check interval** for different use cases:

```yaml
defaults:
  health_check_interval_seconds: 10  # More frequent for critical services
```

**Trade-offs**:
- More frequent: Earlier detection, higher CPU usage
- Less frequent: Lower overhead, slower to detect issues

### Multi-Process Coordination

For complex deployments with dependencies:

```bash
# Start database first
claude-mpm local-deploy start \
  --command "docker-compose up postgres" \
  --auto-restart

# Wait for database to be ready
sleep 5

# Start API server
claude-mpm local-deploy start \
  --command "npm run start:api" \
  --port 8080 \
  --auto-restart \
  --env DATABASE_URL=postgresql://localhost/dev

# Start frontend
claude-mpm local-deploy start \
  --command "npm run dev" \
  --port 3000 \
  --auto-restart
```

## Related Documentation

- **[CLI Commands Reference](../../reference/LOCAL_OPS_COMMANDS.md)** - Complete command reference
- **[Developer Guide](../../developer/LOCAL_PROCESS_MANAGEMENT.md)** - Architecture and extension points
- **[Local Agents](local-agents.md)** - Integration with local-ops-agent
- **[Configuration Reference](../../reference/CONFIGURATION.md)** - Configuration file schema

---

This comprehensive process management system provides professional-grade reliability and observability for your local development workflows, with intelligent auto-restart, health monitoring, and resource management built in.
