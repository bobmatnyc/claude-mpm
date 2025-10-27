# Local Ops Agent

Specialized operations agent for local development deployments with comprehensive process management, health monitoring, and multi-language support. Expert in PM2, Docker, port management, and production-ready local deployments. **Enhanced with Next.js PM2 monitoring features (v2.0.0+)**.

## Table of Contents

1. [Overview](#overview)
2. [Next.js PM2 Monitoring Enhancements (v2.0.0+)](#nextjs-pm2-monitoring-enhancements-v200)
3. [Getting Started](#getting-started)
4. [Core Features](#core-features)
5. [Installation and Setup](#installation-and-setup)
6. [Usage Examples](#usage-examples)
7. [Configuration Guide](#configuration-guide)
8. [Multi-Language Support](#multi-language-support)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)
11. [Reference](#reference)

## Overview

The Local Ops Agent is a specialized component of the Claude MPM framework designed to handle all aspects of local development deployments. It provides comprehensive process management, health monitoring, and multi-language support for modern application development.

### Key Capabilities

- **Process Management**: PM2, Docker, and native process management
- **Health Monitoring**: Real-time health checks with auto-restart
- **Port Management**: Consistent port allocation across deployments
- **Multi-Language Support**: 8 languages, 20+ frameworks
- **Auto-Restart**: Exponential backoff with circuit breaker
- **Resource Monitoring**: CPU, memory, and file descriptor tracking
- **Log Monitoring**: Pattern-based error detection
- **Orphan Cleanup**: Safe detection and removal of orphaned processes

### Supported Languages & Frameworks

**JavaScript/Node.js**: Next.js, React, Vue, Angular, Svelte, Nuxt, Gatsby, Express, NestJS, Remix, SvelteKit, Astro

**Python**: Django, Flask, FastAPI, Streamlit, Gradio

**Rust**: Actix-web, Rocket, Axum, Warp

**Go**: Gin, Echo, Fiber, net/http

**Java**: Spring Boot, Tomcat, Jetty

**Ruby**: Rails, Sinatra

**PHP**: Laravel, Symfony

**Dart**: Flutter Web, Shelf

## Next.js PM2 Monitoring Enhancements (v2.0.0+)

The Local Ops Agent has been significantly enhanced with production-ready PM2 monitoring capabilities specifically optimized for Next.js deployments. These enhancements provide automatic memory management, intelligent health checks, and real-time metrics extraction.

### 1. PM2 Memory Restart Configuration

Advanced memory management with automatic restart when memory thresholds are exceeded.

#### Configuration Details

**Memory Limit**: 2G with automatic restart
- Prevents memory leaks from crashing deployments
- Triggers graceful restart before OOM conditions
- Configurable per-deployment basis

**Max Restarts**: 10 with 3s minimum uptime
- Prevents restart loops from bad code
- Requires 3 seconds of stable operation before counting as successful restart
- Circuit breaker trips after threshold is exceeded

**Graceful Shutdown Timeouts**:
- **Kill Timeout**: 5 seconds for SIGTERM handling
- **Listen Timeout**: 8 seconds for new connections
- **Shutdown with Message**: Enabled for clean shutdown signals

#### PM2 Command Pattern

**Production Deployment**:
```bash
pm2 start npm --name 'my-nextjs-app' -- start \
  --max-memory-restart 2G \
  --max-restarts 10 \
  --min-uptime 3000
```

**Development Deployment**:
```bash
pm2 start npm --name 'my-nextjs-app-dev' -- run dev \
  --max-memory-restart 2G \
  --max-restarts 10 \
  --min-uptime 3000 \
  --watch
```

#### Configuration Options

| Option | Value | Purpose |
|--------|-------|---------|
| `max_memory_restart` | 2G | Memory threshold for automatic restart |
| `max_restarts` | 10 | Maximum restart attempts before giving up |
| `min_uptime` | 3000ms | Minimum stable uptime before counting restart as successful |
| `autorestart` | true | Enable automatic restart on crashes |
| `kill_timeout` | 5000ms | Time to wait for SIGTERM before SIGKILL |
| `listen_timeout` | 8000ms | Time to wait for application to start listening |
| `shutdown_with_message` | true | Send shutdown message to application |
| `watch` | true (dev) | Enable file watching for automatic reload in development |

### 2. Next.js-Specific Health Checks

Three-tiered validation process ensuring Next.js applications are fully operational.

#### Health Check Strategy

**Primary Endpoints**:
- **`/api/health`**: Custom health endpoint (if implemented)
- **`/`**: Homepage fallback validation

**Build Artifacts**:
- **`.next/BUILD_ID`**: Verifies build completed successfully
- **`.next/routes-manifest.json`**: Confirms routing is properly configured

**Static Assets**:
- **`/_next/static/chunks`**: Validates static asset generation

#### 3-Step Validation Process

1. **Endpoint Validation**
   - Test primary endpoint (`/api/health` or `/`)
   - Expected status: 200 OK
   - Timeout: 5 seconds
   - Retries: 3 attempts with exponential backoff

2. **Build Artifact Verification**
   - Check `.next/BUILD_ID` exists
   - Verify `.next/routes-manifest.json` is present
   - Validate file integrity

3. **Static Asset Checking**
   - Confirm `/_next/static/chunks` directory exists
   - Validate chunk files are present
   - Check manifest files

#### Health Check Configuration

```yaml
health_check:
  endpoints:
    primary: "http://localhost:{port}/api/health"
    fallback: "http://localhost:{port}/"
  build_artifacts:
    - ".next/BUILD_ID"
    - ".next/routes-manifest.json"
  static_assets:
    - "/_next/static/chunks"
  validation:
    timeout_ms: 5000
    retries: 3
    expected_status: 200
```

#### Implementation Example

```bash
# The agent performs these checks automatically:

# 1. HTTP Health Check
curl -f -m 5 http://localhost:3000/api/health || curl -f -m 5 http://localhost:3000/

# 2. Build Artifact Validation
test -f .next/BUILD_ID && test -f .next/routes-manifest.json

# 3. Static Asset Verification
test -d .next/static/chunks && ls .next/static/chunks/*.js > /dev/null 2>&1
```

### 3. Enhanced PM2 Monitoring

Real-time metrics extraction and intelligent alerting for PM2-managed deployments.

#### Metrics Extraction

**PM2 Commands Integration**:
```bash
# Status overview
pm2 jlist              # JSON list of all processes

# Detailed process info
pm2 describe {app_name}  # Comprehensive process details

# Live metrics
pm2 show {app_name}     # Real-time metrics display
```

**Tracked Metrics**:
- **restart_count**: Number of restarts since deployment
- **uptime**: Process uptime in milliseconds
- **memory_usage**: Current memory usage in MB
- **cpu_percent**: Current CPU utilization percentage
- **status**: Process status (online, stopped, errored, etc.)

#### Metrics Data Structure

```json
{
  "app_name": "my-nextjs-app",
  "metrics": {
    "restart_count": 2,
    "uptime": 3600000,
    "memory_usage": 456.7,
    "cpu_percent": 2.3,
    "status": "online"
  },
  "pm2_env": {
    "pm_uptime": 1729622052000,
    "created_at": 1729618452000,
    "pm_id": 0,
    "unstable_restarts": 0
  }
}
```

#### Smart Alerts

**Restart Alert**:
- **Threshold**: 5 restarts
- **Trigger**: When restart_count exceeds 5 in monitoring period
- **Action**: Investigate logs, check for memory leaks or crashes
- **Message**: "⚠️ High restart count detected: 5+ restarts"

**Memory Alert**:
- **Threshold**: 1.8G (90% of 2G limit)
- **Trigger**: When memory_usage approaches max_memory_restart threshold
- **Action**: Preemptive investigation before automatic restart
- **Message**: "⚠️ Memory usage high: 1.8G/2G (90%)"

**Status Alert**:
- **Threshold**: Status not "online"
- **Trigger**: Process in stopped, errored, or other non-running state
- **Action**: Immediate attention required
- **Message**: "🚨 Process not running: status = {status}"

#### Alert Configuration

```yaml
alerts:
  restart_threshold: 5
  memory_threshold_percent: 90  # 90% of max_memory_restart
  status_check_enabled: true
  notification:
    console: true
    log_file: "./logs/pm2-alerts.log"
```

#### Monitoring Dashboard

The agent provides real-time monitoring output:

```
PM2 Monitoring: my-nextjs-app
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Status:        ✓ online
Uptime:        2h 15m 34s
Restarts:      2
Memory:        456.7 MB / 2048 MB (22%)
CPU:           2.3%

Health Checks:
  ✓ Endpoint: http://localhost:3000/api/health (143ms)
  ✓ Build artifacts: .next/BUILD_ID present
  ✓ Static assets: 47 chunks found

Alerts:        None
Last Check:    2025-10-27 15:30:45
```

### Usage Patterns

#### Deploy Next.js with Enhanced Monitoring

```bash
# Production deployment with full monitoring
claude-mpm local-deploy start \
  --command "npm start" \
  --port 3000 \
  --auto-restart \
  --health-check http://localhost:3000/api/health

# The agent automatically:
# 1. Detects Next.js framework
# 2. Configures PM2 with memory restart (2G)
# 3. Sets up 3-step health validation
# 4. Enables metrics extraction
# 5. Configures smart alerts (5 restart threshold, 1.8G memory threshold)
```

#### Monitor PM2 Deployment

```bash
# Real-time monitoring with PM2 metrics
claude-mpm local-deploy monitor <deployment-id>

# Check PM2 status
claude-mpm local-deploy status <deployment-id>

# View restart history with PM2 data
claude-mpm local-deploy history <deployment-id>
```

#### Health Check Validation

```bash
# Run comprehensive health checks
claude-mpm local-deploy health <deployment-id>

# Output includes:
# - Endpoint validation (primary + fallback)
# - Build artifact verification
# - Static asset checking
# - PM2 metrics (restart count, memory, CPU)
```

### Configuration Examples

#### Custom Memory Threshold

```yaml
# .claude-mpm/local-ops-config.yaml
deployment_strategies:
  production:
    nextjs:
      pm2_options:
        max_memory_restart: "3G"  # Increase to 3G for larger apps
        max_restarts: 15           # Allow more restarts
        min_uptime: 5000           # Require 5s stability
```

#### Custom Health Endpoints

```yaml
health_checks:
  nextjs:
    endpoints:
      primary: "/api/status"      # Custom health endpoint
      fallback: "/api/ping"       # Custom fallback
    timeout_ms: 10000             # Increase timeout to 10s
    retries: 5                    # More retry attempts
```

#### Alert Thresholds

```yaml
pm2_monitoring:
  alerts:
    restart_threshold: 3          # Alert after 3 restarts
    memory_threshold_percent: 85  # Alert at 85% memory
    cpu_threshold_percent: 80     # Alert at 80% CPU
```

### Troubleshooting PM2 Monitoring

#### High Restart Count

**Symptom**: Restart count exceeds threshold (5+)

**Diagnosis**:
```bash
# Check PM2 logs
pm2 logs my-nextjs-app --lines 100

# Check restart reasons
pm2 describe my-nextjs-app | grep "restart\|error"
```

**Solutions**:
- Memory leak: Increase `max_memory_restart` or fix memory leak
- Crash on startup: Check application logs for errors
- Port conflict: Verify port is not in use
- Build issues: Ensure `npm run build` completes successfully

#### Memory Approaching Limit

**Symptom**: Memory usage near 1.8G (90% of 2G threshold)

**Diagnosis**:
```bash
# Monitor memory in real-time
pm2 monit

# Check memory growth rate
claude-mpm local-deploy status <deployment-id> | grep "Memory Trend"
```

**Solutions**:
- Memory leak detected: Restart deployment, investigate code
- Normal growth: Increase `max_memory_restart` to 3G or 4G
- Large dataset: Optimize data loading and caching

#### Health Checks Failing

**Symptom**: Health check validation fails after deployment

**Diagnosis**:
```bash
# Test endpoints manually
curl -v http://localhost:3000/api/health
curl -v http://localhost:3000/

# Check build artifacts
ls -la .next/BUILD_ID .next/routes-manifest.json

# Verify static assets
ls -la .next/static/chunks/
```

**Solutions**:
- Build not completed: Run `npm run build` manually
- Server not started: Check PM2 status with `pm2 status`
- Port mismatch: Verify deployment port matches health check URL
- Custom endpoint: Update health_check configuration to match your endpoint

### Integration with Claude MPM Workflow

The enhanced PM2 monitoring integrates seamlessly with Claude MPM's orchestration:

1. **PM Agent**: Delegates deployment to Local Ops Agent
2. **Local Ops Agent**:
   - Detects Next.js framework
   - Configures PM2 with memory restart
   - Sets up 3-step health validation
   - Enables metrics extraction and alerts
3. **Monitoring**: Real-time dashboard with PM2 metrics
4. **Alerts**: Automatic notification of restart/memory issues
5. **Recovery**: Auto-restart with circuit breaker protection

### Benefits

**Production Readiness**:
- Automatic memory management prevents OOM crashes
- Circuit breaker prevents infinite restart loops
- Graceful shutdown ensures clean process termination

**Developer Experience**:
- Real-time visibility into process health
- Smart alerts for proactive issue detection
- Comprehensive metrics for debugging

**Reliability**:
- 3-step validation ensures deployments are truly healthy
- Auto-restart recovers from transient failures
- Exponential backoff prevents resource exhaustion

## Getting Started

### Prerequisites

- Node.js (for Next.js, React, Express, etc.)
- Python (for Django, Flask, FastAPI)
- Rust (for Actix-web, Rocket, etc.)
- Go (for Gin, Echo, etc.)
- Java (for Spring Boot)
- PM2 (optional, auto-installed)
- Docker (optional)

### Quick Start

```bash
# Deploy a Next.js application
claude-mpm local-deploy start --command "npm run dev" --port 3000 --auto-restart

# Monitor deployment
claude-mpm local-deploy monitor <deployment-id>

# Check health
claude-mpm local-deploy health <deployment-id>

# Stop deployment
claude-mpm local-deploy stop <deployment-id>
```

## Core Features

### 1. Process Management

**PM2 Integration**:
- Production-ready process management
- Cluster mode for scaling
- Memory restart configuration
- Watch mode for development

**Docker Integration**:
- Container-based deployments
- Volume management
- Network configuration
- Multi-container orchestration

**Native Process Management**:
- Direct process spawning
- PID tracking
- Signal handling
- Resource monitoring

### 2. Health Monitoring

**HTTP Health Checks**:
- Endpoint validation
- Response time tracking
- Status code verification
- Custom headers support

**Process Health Checks**:
- PID validation
- Resource usage monitoring
- Crash detection
- Auto-restart configuration

**Build Validation** (Next.js):
- Build artifact verification
- Route manifest checking
- Static asset validation

### 3. Port Management

**Consistent Port Allocation**:
- Project-based port assignment
- Port conflict detection
- Automatic port finding
- Port reservation system

**Default Ports by Language**:
- Node.js/Next.js: 3000
- Python/Django: 8000
- Python/FastAPI: 8000
- Rust: 8080
- Go: 8080
- Java/Spring Boot: 8080
- Ruby/Rails: 3000
- PHP/Laravel: 8000

### 4. Auto-Restart

**Exponential Backoff**:
- Initial delay: 2 seconds
- Multiplier: 2.0
- Max delay: 300 seconds (5 minutes)
- Max attempts: 5

**Circuit Breaker**:
- Threshold: 3 failures in 5 minutes
- Reset timeout: 10 minutes
- Prevents infinite restart loops

**Restart Triggers**:
- Process crashes
- Health check failures
- Memory leaks detected
- Log error patterns matched

### 5. Resource Monitoring

**Tracked Resources**:
- CPU usage (threshold: 80%)
- Memory usage (threshold: 500MB)
- File descriptors (threshold: 80% of ulimit)
- Thread count (threshold: 1000)
- Network connections (threshold: 500)

**Monitoring Actions**:
- Alert on threshold breach
- Trigger preemptive restart
- Log resource trends
- Memory leak detection

### 6. Log Monitoring

**Error Pattern Detection**:
- Python: `ERROR`, `CRITICAL`, `Exception`, `Traceback`
- JavaScript: `Error:`, `UnhandledPromiseRejectionWarning`
- Rust: `ERROR`, `panic:`, `thread .* panicked`
- Go: `ERROR`, `FATAL`, `panic:`, `runtime error`
- Java: `ERROR`, `SEVERE`, `Exception`, `OutOfMemoryError`

**Log Actions**:
- Trigger auto-restart on critical patterns
- Alert on error threshold
- Log pattern statistics

## Installation and Setup

### Install Claude MPM

```bash
# Install Claude MPM
pip install claude-mpm

# Verify installation
claude-mpm --version
```

### Configure Local Ops

```bash
# Create configuration file
cp .claude-mpm/local-ops-config.yaml.example .claude-mpm/local-ops-config.yaml

# Edit configuration
vim .claude-mpm/local-ops-config.yaml
```

### Install Optional Dependencies

```bash
# Install PM2 (for Node.js deployments)
npm install -g pm2

# Install Docker (for containerized deployments)
# Follow Docker installation guide for your OS
```

## Usage Examples

### Example 1: Next.js with PM2 Monitoring

```bash
# Deploy Next.js in production with full PM2 monitoring
claude-mpm local-deploy start \
  --command "npm start" \
  --port 3000 \
  --auto-restart \
  --log-file ./logs/nextjs.log

# Monitor with PM2 metrics
claude-mpm local-deploy monitor <deployment-id>

# Check PM2 status and alerts
claude-mpm local-deploy status <deployment-id>
```

### Example 2: FastAPI with Auto-Restart

```bash
# Deploy FastAPI with uvicorn and auto-restart
claude-mpm local-deploy start \
  --command "uvicorn main:app --host 0.0.0.0 --port 8000" \
  --port 8000 \
  --auto-restart \
  --health-check http://localhost:8000/health
```

### Example 3: Rust Actix-web Development

```bash
# Deploy Rust app with hot reload
claude-mpm local-deploy start \
  --command "cargo watch -x run" \
  --port 8080 \
  --working-directory /path/to/rust/project
```

### Example 4: Go Gin Production

```bash
# Build and deploy Go application
cd /path/to/go/project
go build -o app

claude-mpm local-deploy start \
  --command "./app" \
  --port 8080 \
  --auto-restart \
  --health-check http://localhost:8080/ping
```

### Example 5: Spring Boot with Actuator

```bash
# Deploy Spring Boot with health checks
claude-mpm local-deploy start \
  --command "java -jar target/app.jar" \
  --port 8080 \
  --auto-restart \
  --health-check http://localhost:8080/actuator/health
```

### Example 6: Multi-Service Deployment

```bash
# Deploy API backend
API_ID=$(claude-mpm local-deploy start \
  --command "uvicorn api.main:app --port 8000" \
  --port 8000 \
  --auto-restart)

# Deploy Next.js frontend
WEB_ID=$(claude-mpm local-deploy start \
  --command "npm start" \
  --port 3000 \
  --auto-restart \
  --env API_URL=http://localhost:8000)

# Monitor all deployments
claude-mpm local-deploy list
```

## Configuration Guide

### Configuration File Location

`.claude-mpm/local-ops-config.yaml`

### Complete Configuration Schema

```yaml
version: "1.0"

defaults:
  health_check_interval_seconds: 30
  auto_restart_enabled: false

restart_policy:
  max_attempts: 5
  initial_backoff_seconds: 2.0
  max_backoff_seconds: 300.0
  backoff_multiplier: 2.0
  circuit_breaker_threshold: 3
  circuit_breaker_window_seconds: 300
  circuit_breaker_reset_seconds: 600

stability:
  memory_leak_threshold_mb_per_minute: 10.0
  fd_threshold_percent: 0.8
  thread_threshold: 1000
  connection_threshold: 500
  disk_threshold_mb: 100

log_monitoring:
  enabled: true
  error_patterns:
    - "OutOfMemoryError"
    - "Segmentation fault"
    - "Exception:"
    - "Error:"
    - "FATAL"
    - "CRITICAL"
    - "panic:"
    - "AssertionError"
    - "UnhandledPromiseRejectionWarning"

pm2_monitoring:
  metrics_extraction:
    enabled: true
  alerts:
    restart_threshold: 5
    memory_threshold_percent: 90
    cpu_threshold_percent: 80

health_checks:
  nextjs:
    endpoints:
      primary: "/api/health"
      fallback: "/"
    build_artifacts:
      - ".next/BUILD_ID"
      - ".next/routes-manifest.json"
    static_assets:
      - "/_next/static/chunks"
    timeout_ms: 5000
    retries: 3
```

## Multi-Language Support

### JavaScript/Node.js

**Frameworks**: Next.js, React, Vue, Angular, Svelte, Express, NestJS

**Development**:
```bash
# Next.js
npm run dev

# Express with nodemon
nodemon server.js
```

**Production**:
```bash
# Next.js with PM2
pm2 start npm --name app -- start --max-memory-restart 2G

# Express
node server.js
```

### Python

**Frameworks**: Django, Flask, FastAPI, Streamlit

**Development**:
```bash
# FastAPI with reload
uvicorn main:app --reload --port 8000

# Django
python manage.py runserver 8000
```

**Production**:
```bash
# FastAPI with workers
uvicorn main:app --workers 4 --port 8000

# Django with gunicorn
gunicorn app:app --bind 0.0.0.0:8000
```

### Rust

**Frameworks**: Actix-web, Rocket, Axum, Warp

**Development**:
```bash
# Hot reload with cargo-watch
cargo watch -x run
```

**Production**:
```bash
# Optimized build
cargo build --release
./target/release/app
```

### Go

**Frameworks**: Gin, Echo, Fiber, net/http

**Development**:
```bash
# Hot reload with air
air

# Or direct run
go run .
```

**Production**:
```bash
# Build and run
go build -o app
./app
```

### Java/Spring Boot

**Build Tools**: Maven, Gradle

**Development**:
```bash
# Maven
mvn spring-boot:run

# Gradle
gradle bootRun
```

**Production**:
```bash
# Maven package and run
mvn clean package
java -jar target/app.jar
```

## Best Practices

### Port Selection

- Use consistent ports per project
- Avoid system ports (< 1024)
- Use default ports when possible
- Enable auto-find-port for flexibility

### Health Checks

- Implement `/health` or `/api/health` endpoints
- Return 200 OK for healthy status
- Include dependency checks (database, cache, etc.)
- Keep response time under 1 second

### Auto-Restart Configuration

- Enable for production deployments
- Use exponential backoff to prevent restart loops
- Configure circuit breaker for safety
- Monitor restart history regularly

### Resource Monitoring

- Set appropriate memory limits
- Monitor memory growth trends
- Track CPU usage patterns
- Watch for file descriptor leaks

### Log Monitoring

- Use structured logging
- Include severity levels
- Add context to error messages
- Configure log rotation

### Environment Configuration

**Development**:
```bash
NODE_ENV=development
DEBUG=true
LOG_LEVEL=debug
```

**Production**:
```bash
NODE_ENV=production
DEBUG=false
LOG_LEVEL=info
```

## Troubleshooting

### Port Conflicts

**Symptom**: "Port 3000 already in use"

**Solution**:
```bash
# Find process using port
lsof -i :3000

# Stop conflicting process
claude-mpm local-deploy stop <deployment-id>

# Or use auto-find-port
claude-mpm local-deploy start --command "npm run dev" --port 3000 --auto-find-port
```

### Build Failures

**Symptom**: Deployment fails during build step

**Solution**:
```bash
# Check build logs
npm run build

# Clear cache
rm -rf .next node_modules
npm install
npm run build

# Redeploy
claude-mpm local-deploy start --command "npm start" --port 3000
```

### Health Check Failures

**Symptom**: "Health check failed after 3 retries"

**Solution**:
```bash
# Test endpoint manually
curl http://localhost:3000/api/health

# Check application logs
claude-mpm local-deploy status <deployment-id>

# Verify build artifacts (Next.js)
ls -la .next/BUILD_ID .next/routes-manifest.json

# Increase timeout
# Edit .claude-mpm/local-ops-config.yaml
health_checks:
  timeout_ms: 10000
```

### Memory Leaks

**Symptom**: Memory usage growing continuously

**Solution**:
```bash
# Check memory trend
claude-mpm local-deploy status <deployment-id> | grep "Memory Trend"

# Lower memory restart threshold
# Edit .claude-mpm/local-ops-config.yaml
pm2_monitoring:
  memory_threshold_percent: 80

# Or increase max memory
deployment_strategies:
  production:
    nextjs:
      pm2_options:
        max_memory_restart: "3G"
```

### Circuit Breaker Tripped

**Symptom**: "Auto-restart disabled: circuit breaker open"

**Solution**:
```bash
# Check restart history
claude-mpm local-deploy history <deployment-id>

# Fix underlying issue (check logs)
claude-mpm local-deploy status <deployment-id>

# Wait for circuit breaker reset (10 minutes)
# Or manually restart after fixing
claude-mpm local-deploy restart <deployment-id>
```

## Reference

### CLI Commands

See [LOCAL_OPS_COMMANDS.md](../reference/LOCAL_OPS_COMMANDS.md) for complete CLI reference.

**Common Commands**:
- `start`: Start deployment
- `stop`: Stop deployment
- `restart`: Restart deployment
- `status`: Show detailed status
- `health`: Run health checks
- `monitor`: Live monitoring dashboard
- `list`: List all deployments
- `history`: Show restart history

### Configuration Files

- **`.claude-mpm/local-ops-config.yaml`**: Main configuration
- **`.claude-mpm/local-ops-config.yaml.example`**: Example configuration
- **`.next/BUILD_ID`**: Next.js build identifier
- **`.next/routes-manifest.json`**: Next.js route configuration

### Environment Variables

**Development**:
- `NODE_ENV=development`
- `DEBUG=true`
- `RELOAD=true`
- `LOG_LEVEL=debug`

**Production**:
- `NODE_ENV=production`
- `DEBUG=false`
- `WORKERS=4`
- `LOG_LEVEL=info`

### Default Ports

| Framework | Default Port |
|-----------|--------------|
| Next.js | 3000 |
| React | 3000 |
| Express | 3000 |
| Django | 8000 |
| FastAPI | 8000 |
| Flask | 5000 |
| Rust (Actix) | 8080 |
| Go (Gin) | 8080 |
| Spring Boot | 8080 |
| Rails | 3000 |
| Laravel | 8000 |

### PM2 Commands

```bash
# List processes
pm2 list
pm2 jlist  # JSON format

# Process details
pm2 describe <app_name>
pm2 show <app_name>

# Logs
pm2 logs <app_name>
pm2 logs <app_name> --lines 100

# Monitoring
pm2 monit

# Management
pm2 restart <app_name>
pm2 stop <app_name>
pm2 delete <app_name>
```

### Health Check Endpoints

**Next.js**:
- `/api/health`
- `/`

**FastAPI**:
- `/health`
- `/docs`
- `/openapi.json`

**Spring Boot**:
- `/actuator/health`
- `/actuator/info`

**Express**:
- `/health`
- `/ping`

**Gin (Go)**:
- `/ping`
- `/health`

### Related Documentation

- **[CLI Commands Reference](../reference/LOCAL_OPS_COMMANDS.md)** - Complete CLI documentation
- **[User Guide](../user/03-features/local-process-management.md)** - End-user documentation
- **[Configuration Guide](../reference/CONFIGURATION.md)** - General configuration reference
- **[Agent System](AGENTS.md)** - Agent architecture overview

---

**Version**: 2.0.0
**Last Updated**: 2025-10-27
**Status**: Production Ready

This comprehensive documentation provides complete coverage of the Local Ops Agent's capabilities, with special emphasis on the enhanced Next.js PM2 monitoring features introduced in v2.0.0.
