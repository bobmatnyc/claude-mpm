# Network Port Configuration

## Overview

Claude MPM now uses centralized port configuration with different default ports for each service. This improves clarity and reduces port conflicts when running multiple services simultaneously.

## Default Ports

| Service | Default Port | Environment Variable | Purpose |
|---------|--------------|---------------------|---------|
| Monitor | 8765 | `CLAUDE_MPM_MONITOR_PORT` | Health monitoring and event aggregation |
| Commander | 8766 | `CLAUDE_MPM_COMMANDER_PORT` | Multi-project orchestration API |
| Dashboard | 8767 | `CLAUDE_MPM_DASHBOARD_PORT` | Web dashboard UI |
| SocketIO | 8768 | `CLAUDE_MPM_SOCKETIO_PORT` | Real-time event streaming |

**Port Range**: 8765-8785 (21 ports available for dynamic allocation)

## Configuration Priority

Configuration is resolved in this order (highest to lowest priority):

1. **CLI Arguments**: `--port` flag
2. **Environment Variables**: `CLAUDE_MPM_*_PORT`
3. **configuration.yaml**: Network section
4. **Default Values**: From `NetworkPorts` class

## Configuration File

Add network configuration to `.claude-mpm/configuration.yaml`:

```yaml
network:
  # Optional: Override default host (default: 127.0.0.1)
  host: "127.0.0.1"

  # Optional: Override service ports
  monitor_port: 8765
  commander_port: 8766
  dashboard_port: 8767
  socketio_port: 8768
```

## Environment Variables

Override ports via environment variables:

```bash
# Set monitor port
export CLAUDE_MPM_MONITOR_PORT=9000

# Set commander port
export CLAUDE_MPM_COMMANDER_PORT=9001

# Set dashboard port
export CLAUDE_MPM_DASHBOARD_PORT=9002

# Set socketio port
export CLAUDE_MPM_SOCKETIO_PORT=9003

# Set default host (affects all services)
export CLAUDE_MPM_DEFAULT_HOST="0.0.0.0"
```

## CLI Usage

Override ports with CLI flags:

```bash
# Monitor with custom port
claude-mpm monitor start --port 9000

# Commander with custom port
claude-mpm commander --port 9001

# Dashboard with custom port
claude-mpm dashboard --port 9002
```

## Python API

Use the centralized `NetworkPorts` class:

```python
from claude_mpm.core.network_config import NetworkPorts

# Get default ports
monitor_port = NetworkPorts.MONITOR_DEFAULT  # 8765
commander_port = NetworkPorts.COMMANDER_DEFAULT  # 8766
dashboard_port = NetworkPorts.DASHBOARD_DEFAULT  # 8767
socketio_port = NetworkPorts.SOCKETIO_DEFAULT  # 8768

# Get port from environment with fallback to default
monitor_port = NetworkPorts.get_monitor_port()
commander_port = NetworkPorts.get_commander_port()
dashboard_port = NetworkPorts.get_dashboard_port()
socketio_port = NetworkPorts.get_socketio_port()

# Get default host
host = NetworkPorts.get_default_host()  # "127.0.0.1"

# Check if port is in valid range
is_valid = NetworkPorts.is_port_in_range(8770)  # True
```

## Backward Compatibility

Existing configurations continue to work:

- Old hardcoded port defaults (8765) updated to service-specific defaults
- Legacy environment variables supported with deprecation warnings
- CLI flags take precedence as before
- Existing `configuration.yaml` files work without changes

## Migration Guide

### Before (Hardcoded Defaults)

```python
# Old approach - hardcoded in multiple files
port = 8765  # Which service is this for?
```

### After (Centralized Configuration)

```python
# New approach - clear service-specific defaults
from claude_mpm.core.network_config import NetworkPorts

monitor_port = NetworkPorts.MONITOR_DEFAULT  # 8765
commander_port = NetworkPorts.COMMANDER_DEFAULT  # 8766
dashboard_port = NetworkPorts.DASHBOARD_DEFAULT  # 8767
socketio_port = NetworkPorts.SOCKETIO_DEFAULT  # 8768
```

## Implementation Details

### Single Source of Truth

`src/claude_mpm/core/network_config.py` contains the canonical port definitions:

```python
class NetworkPorts:
    MONITOR_DEFAULT = 8765
    COMMANDER_DEFAULT = 8766
    DASHBOARD_DEFAULT = 8767
    SOCKETIO_DEFAULT = 8768
    PORT_RANGE_START = 8765
    PORT_RANGE_END = 8785
```

### Updated Files

The following files were updated to use `NetworkPorts`:

- `src/claude_mpm/core/network_config.py` (new)
- `src/claude_mpm/core/constants.py` (updated defaults)
- `src/claude_mpm/core/config.py` (updated defaults)
- `src/claude_mpm/core/config_constants.py` (added port methods)
- `src/claude_mpm/commander/config.py` (updated default port)
- `src/claude_mpm/cli/parsers/commander_parser.py` (updated help text)
- `src/claude_mpm/cli/commands/commander.py` (updated default port)
- `src/claude_mpm/core/socketio_pool.py` (import NetworkPorts)

## Troubleshooting

### Port Conflicts

If you encounter port conflicts:

1. Check which port is in use: `lsof -i :<port>`
2. Override with environment variable: `export CLAUDE_MPM_<SERVICE>_PORT=<new_port>`
3. Or use CLI flag: `--port <new_port>`

### Service Not Starting

1. Verify port is not in use
2. Check port is within valid range (8765-8785 by default)
3. Ensure firewall allows the port
4. Check logs for detailed error messages

### Multiple Services

To run all services simultaneously:

```bash
# Terminal 1 - Monitor (default 8765)
claude-mpm monitor start

# Terminal 2 - Commander (default 8766)
claude-mpm commander --daemon-only

# Terminal 3 - Dashboard (default 8767)
claude-mpm dashboard

# Services use different ports, no conflicts
```

## Future Enhancements

Planned improvements:

- [ ] Auto-detect port conflicts and suggest alternatives
- [ ] Service discovery protocol for dynamic port allocation
- [ ] Health check endpoints on all services
- [ ] Port range configuration per deployment environment
