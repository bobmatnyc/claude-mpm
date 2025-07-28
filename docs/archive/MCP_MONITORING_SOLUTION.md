# MCP Monitoring Solution Documentation

## Overview

The MCP (Model Context Protocol) Monitoring Solution provides a robust, production-ready system for managing and monitoring MCP services, addressing common instability issues such as service crashes, port conflicts, and unhealthy service states. This solution ensures high availability and automatic recovery for eva-memory, cloud bridge, and desktop gateway services.

## Problem Statement

MCP services often suffer from:
- **Service Crashes**: Services unexpectedly terminate due to errors or resource constraints
- **Port Conflicts**: Services fail to start when ports are already in use
- **Health Degradation**: Services become unresponsive while still technically running
- **Manual Recovery**: Requiring human intervention to restart failed services
- **Lack of Visibility**: No centralized monitoring or logging

## Solution Architecture

The monitoring solution consists of three main components:

1. **Monitor Script** (`scripts/monitor_mcp_services.py`): Core monitoring daemon with health checks and auto-restart capabilities
2. **Setup Script** (`scripts/setup_local_mcp.sh`): Easy-to-use management interface for setup and control
3. **Configuration** (`config/mcp_services.yaml`): Centralized service configuration

### How It Solves Instability Problems

1. **Automatic Recovery**: Services are automatically restarted when they crash or become unhealthy
2. **Port Management**: Automatically detects and resolves port conflicts before starting services
3. **Health Monitoring**: Regular health checks ensure services are not just running but actually functional
4. **Process Management**: Proper signal handling and graceful shutdowns prevent zombie processes
5. **Comprehensive Logging**: All events are logged for troubleshooting and analysis

## Quick Start Guide

### Prerequisites

- Python 3.7+
- Node.js and npm
- Basic command-line tools (lsof, kill)

### Installation

1. Clone the repository and navigate to the project directory
2. Ensure the monitoring scripts are executable:
   ```bash
   chmod +x scripts/setup_local_mcp.sh
   chmod +x scripts/monitor_mcp_services.py
   ```

### Basic Usage

#### Interactive Mode
```bash
./scripts/setup_local_mcp.sh
```

This launches an interactive menu with options to:
- Setup environment
- Start/stop monitoring
- View service status
- Access logs
- Clean up resources

#### Command-Line Mode
```bash
# Initial setup
./scripts/setup_local_mcp.sh setup

# Start monitoring
./scripts/setup_local_mcp.sh start

# Check status
./scripts/setup_local_mcp.sh status

# View logs
./scripts/setup_local_mcp.sh logs

# Stop everything
./scripts/setup_local_mcp.sh stop
```

### Direct Monitor Usage
```bash
# Start monitoring with custom config
python scripts/monitor_mcp_services.py --config config/mcp_services.yaml

# Check status only
python scripts/monitor_mcp_services.py --status
```

## Features

### 1. Automatic Service Recovery

The monitor continuously checks service health and automatically restarts failed services:

- **Process Monitoring**: Detects when a service process terminates
- **Health Checks**: HTTP-based health endpoint monitoring
- **Smart Restart**: Configurable restart delays and retry limits
- **Failure Tracking**: Prevents restart loops with consecutive failure tracking

### 2. Port Conflict Resolution

Before starting any service, the monitor:

- Checks if the configured port is available
- Identifies processes using the port
- Attempts graceful termination of conflicting processes
- Falls back to force-kill if necessary
- Waits for port release before starting the service

### 3. Health Monitoring

Each service is monitored via HTTP health endpoints:

```yaml
health_endpoint: "http://localhost:3001/health"
health_timeout: 5  # seconds
```

Features:
- Configurable health check intervals
- Retry logic with exponential backoff
- Timeout handling for unresponsive services
- Support for custom health endpoints

### 4. Process Management

Robust process lifecycle management:

- **Graceful Startup**: Waits for services to become healthy before marking as started
- **Signal Handling**: Proper handling of SIGTERM and SIGINT for clean shutdowns
- **Process Tracking**: PID-based tracking with automatic cleanup
- **Resource Limits**: Prevents runaway processes (configurable)

### 5. Comprehensive Logging

Multi-level logging system:

- **Monitor Logs**: Overall system events and status changes
- **Service Logs**: Individual log files for each service
- **Structured Format**: Timestamp, level, and context for each log entry
- **Log Rotation**: Automatic cleanup of old logs (7-day retention)

## Configuration Options

### Service Configuration

Each service in `config/mcp_services.yaml` supports:

```yaml
service-name:
  command: ["executable", "arg1", "arg2"]  # Command to start service
  port: 3001                                # Port number
  health_endpoint: "http://..."             # Health check URL
  health_timeout: 5                         # Health check timeout (seconds)
  startup_timeout: 30                       # Time to wait for healthy startup
  restart_delay: 5                          # Delay between restart attempts
  max_retries: 3                           # Maximum consecutive failures
  log_file: "service.log"                  # Service-specific log file
  env_vars:                                # Environment variables
    KEY: "value"
  working_dir: "/path/to/dir"              # Working directory (optional)
```

### Global Configuration

```yaml
global:
  health_check_interval: 10    # Seconds between health checks
  max_memory_mb: 512          # Memory limit per service
  max_cpu_percent: 80         # CPU usage limit
  bind_host: "0.0.0.0"        # Network binding
  shutdown_timeout: 30        # Graceful shutdown timeout
  metrics_enabled: true       # Enable metrics collection
  metrics_port: 9090         # Metrics endpoint port
```

### Environment Variables

The setup script creates `~/.mcp/.env` with:

```bash
MCP_HOME="/Users/username/.mcp"
MCP_LOGS="/Users/username/.mcp/logs"
NODE_ENV="development"
EVA_MEMORY_PORT="3001"
CLOUD_BRIDGE_PORT="3002"
DESKTOP_GATEWAY_PORT="3003"
AWS_REGION="us-east-1"
AWS_PROFILE="default"
```

## Troubleshooting

### Common Issues

#### 1. Port Already in Use
**Symptom**: Service fails to start with "Address already in use" error

**Solution**: The monitor automatically handles this, but you can manually check:
```bash
# Find process using port
lsof -i :3001

# Kill process
kill -9 <PID>
```

#### 2. Service Won't Stay Running
**Symptom**: Service repeatedly crashes after restart

**Solution**: Check service logs for the root cause:
```bash
# View specific service log
./scripts/setup_local_mcp.sh logs eva-memory

# Check monitor log
tail -f ~/.mcp/logs/monitor.out
```

#### 3. Health Checks Failing
**Symptom**: Service running but marked as unhealthy

**Solution**: 
- Verify the health endpoint is correct in configuration
- Check if service needs more startup time
- Ensure service implements health endpoint correctly

#### 4. Permission Errors
**Symptom**: Cannot kill processes or bind to ports

**Solution**:
- Run with appropriate permissions (avoid sudo if possible)
- Check file permissions in MCP directories
- Ensure user has access to configured ports (>1024)

### Debug Mode

Enable verbose logging by modifying the monitor script:
```python
logging.basicConfig(level=logging.DEBUG)
```

### Manual Service Control

If automatic management fails:

```bash
# Stop all MCP processes
pkill -f "mcp-server"
pkill -f "modelcontextprotocol"

# Clear port
lsof -ti :3001 | xargs kill -9

# Start service manually
npx -y @modelcontextprotocol/server-memory
```

## Example Usage Scenarios

### Scenario 1: Development Environment Setup

```bash
# One-time setup
./scripts/setup_local_mcp.sh setup

# Start services for development
./scripts/setup_local_mcp.sh start

# Monitor logs during development
./scripts/setup_local_mcp.sh logs

# Stop at end of day
./scripts/setup_local_mcp.sh stop
```

### Scenario 2: Production Deployment

```bash
# Start monitor as daemon
nohup python scripts/monitor_mcp_services.py \
  --config /etc/mcp/services.yaml \
  --log-dir /var/log/mcp &

# Add to systemd for automatic startup
sudo systemctl enable mcp-monitor
sudo systemctl start mcp-monitor
```

### Scenario 3: Debugging Service Issues

```bash
# Check current status
./scripts/setup_local_mcp.sh status

# Tail specific service log
tail -f ~/.mcp/logs/eva-memory.log

# Monitor health checks
watch -n 5 'curl -s http://localhost:3001/health'

# Force restart a service
pkill -f eva-memory  # Monitor will auto-restart
```

### Scenario 4: Custom Service Configuration

1. Edit `config/mcp_services.yaml`:
```yaml
custom-service:
  command: ["node", "/path/to/service.js"]
  port: 3004
  health_endpoint: "http://localhost:3004/status"
  startup_timeout: 60  # Longer startup for complex service
  env_vars:
    CUSTOM_CONFIG: "/etc/custom/config.json"
    LOG_LEVEL: "debug"
```

2. Restart monitoring:
```bash
./scripts/setup_local_mcp.sh stop
./scripts/setup_local_mcp.sh start
```

## Advanced Topics

### Integration with CI/CD

```yaml
# GitHub Actions example
- name: Start MCP Services
  run: |
    ./scripts/setup_local_mcp.sh setup
    ./scripts/setup_local_mcp.sh start
    
- name: Run Tests
  run: pytest tests/

- name: Stop Services
  if: always()
  run: ./scripts/setup_local_mcp.sh stop
```

### Monitoring Metrics

When metrics are enabled, access at `http://localhost:9090/metrics`:

- Service uptime
- Restart counts
- Health check latencies
- Resource usage

### Custom Health Checks

Implement custom health logic:

```python
# In your service
@app.route('/health')
def health_check():
    # Check dependencies
    if not database_connected():
        return {'status': 'unhealthy'}, 503
    
    # Check performance
    if response_time > 1000:
        return {'status': 'degraded'}, 503
        
    return {'status': 'healthy'}, 200
```

## Best Practices

1. **Configuration Management**
   - Keep service configurations in version control
   - Use environment-specific config files
   - Document all custom settings

2. **Resource Allocation**
   - Set appropriate memory and CPU limits
   - Monitor resource usage trends
   - Scale horizontally when needed

3. **Logging Strategy**
   - Use structured logging in services
   - Implement log rotation
   - Centralize logs for analysis

4. **Health Check Design**
   - Keep health checks lightweight
   - Check critical dependencies only
   - Implement graduated health states

5. **Deployment Practices**
   - Test configuration changes in staging
   - Use gradual rollouts
   - Maintain rollback procedures

## Conclusion

The MCP Monitoring Solution provides a comprehensive answer to service instability issues through automatic recovery, intelligent port management, and continuous health monitoring. By following this documentation, you can ensure your MCP services remain stable and available, allowing you to focus on development rather than operations.

For additional support or feature requests, please refer to the project's issue tracker or documentation repository.