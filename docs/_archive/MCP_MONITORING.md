# MCP Services Monitoring and Stabilization

This document describes the comprehensive monitoring solution for MCP services (eva-memory, cloud bridge, and desktop gateway).

## Overview

The MCP monitoring solution provides:
- Automatic health checking of all services
- Automatic restart on failure
- Port conflict prevention
- Comprehensive logging
- Resource management
- Graceful shutdown handling

## Components

### 1. Monitor Script (`scripts/monitor_mcp_services.py`)

The main monitoring daemon that:
- Monitors service health via HTTP endpoints
- Automatically restarts failed services
- Prevents port conflicts by killing conflicting processes
- Logs all events with timestamps
- Handles graceful shutdown

### 2. Setup Script (`scripts/setup_local_mcp.sh`)

Interactive setup script that:
- Checks and installs dependencies
- Sets up directory structure
- Manages service lifecycle
- Provides status monitoring
- Handles cleanup tasks

### 3. Configuration File (`config/mcp_services.yaml`)

Service definitions including:
- Start commands
- Port assignments
- Health check endpoints
- Timeout configurations
- Environment variables

## Quick Start

### 1. Initial Setup

```bash
# Run the setup script
./scripts/setup_local_mcp.sh setup

# Or use interactive mode
./scripts/setup_local_mcp.sh
```

### 2. Start Monitoring

```bash
# Start the monitor and all services
./scripts/setup_local_mcp.sh start

# Or use the Python script directly
python scripts/monitor_mcp_services.py
```

### 3. Check Status

```bash
# Show service status
./scripts/setup_local_mcp.sh status

# Or use the monitor script
python scripts/monitor_mcp_services.py --status
```

### 4. View Logs

```bash
# View monitor logs
./scripts/setup_local_mcp.sh logs

# View specific service logs
./scripts/setup_local_mcp.sh logs eva-memory
```

## Configuration

### Service Configuration

Edit `config/mcp_services.yaml` to customize service settings:

```yaml
services:
  eva-memory:
    command: ["npx", "-y", "@modelcontextprotocol/server-memory"]
    port: 3001
    health_endpoint: "http://localhost:3001/health"
    startup_timeout: 30
    restart_delay: 5
    max_retries: 3
```

### Environment Variables

The setup script creates `~/.mcp/.env` with default settings:

```bash
export EVA_MEMORY_PORT="3001"
export CLOUD_BRIDGE_PORT="3002"
export DESKTOP_GATEWAY_PORT="3003"
export AWS_REGION="us-east-1"
```

## Features

### Automatic Recovery

- Services are monitored every 10 seconds
- Failed services are automatically restarted
- Maximum retry limit prevents infinite restart loops
- Exponential backoff for persistent failures

### Port Conflict Resolution

- Automatically detects port conflicts
- Kills conflicting processes before starting services
- Ensures clean service startup

### Comprehensive Logging

- All events logged with timestamps
- Separate log files for each service
- Monitor log for system-wide events
- Automatic log rotation (keeps 7 days)

### Resource Management

- Configurable memory and CPU limits
- Graceful shutdown on system signals
- Process cleanup on exit

## Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # The monitor will automatically handle this, but you can manually check:
   lsof -i :3001
   ```

2. **Service Won't Start**
   - Check logs: `tail -f ~/.mcp/logs/SERVICE_NAME.log`
   - Verify dependencies are installed
   - Check configuration file syntax

3. **Monitor Crashes**
   - Check monitor log: `tail -f ~/.mcp/logs/monitor.out`
   - Verify Python dependencies: `pip install psutil pyyaml requests`

### Manual Service Management

```bash
# Stop all services
./scripts/setup_local_mcp.sh stop

# Clean up resources
./scripts/setup_local_mcp.sh cleanup

# Kill specific port
lsof -ti:3001 | xargs kill -9
```

## Testing

Test the monitoring system:

```bash
# Run the test script to simulate service failures
python scripts/test_mcp_monitor.py

# In another terminal, start the monitor
python scripts/monitor_mcp_services.py
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   MCP Monitor Process                     │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │   Monitor   │  │   Monitor   │  │   Monitor   │     │
│  │   Thread    │  │   Thread    │  │   Thread    │     │
│  │(eva-memory) │  │(cloud-bridge)│ │(desktop-gw) │     │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘     │
│         │                 │                 │            │
│  ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐     │
│  │   Service   │  │   Service   │  │   Service   │     │
│  │   Process   │  │   Process   │  │   Process   │     │
│  │  Port 3001  │  │  Port 3002  │  │  Port 3003  │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────┘
```

## Best Practices

1. **Always use the setup script** for initial configuration
2. **Monitor logs regularly** for early issue detection
3. **Configure appropriate timeouts** based on service characteristics
4. **Set resource limits** to prevent resource exhaustion
5. **Use health endpoints** for accurate service status

## Integration with Claude MPM

The monitoring solution integrates seamlessly with Claude MPM:

1. Services are available on standard ports
2. Health checks ensure services are ready before use
3. Automatic recovery minimizes disruptions
4. Logs are centralized for easy debugging

## Future Enhancements

- Prometheus metrics export
- Web dashboard for monitoring
- Alert notifications (email/Slack)
- Docker container support
- Kubernetes deployment manifests