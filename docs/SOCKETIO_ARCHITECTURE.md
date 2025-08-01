# Standalone Socket.IO Server Architecture

This document describes the new standalone Socket.IO server architecture with independent versioning and deployment agnostic design.

## Overview

The new architecture provides a robust, scalable Socket.IO server that can run independently of claude-mpm processes while maintaining compatibility and providing intelligent connection management.

## Key Features

### 1. **Single Server Per Machine**
- Only one Socket.IO server instance runs per port
- Automatic detection of existing servers
- PID file management for process tracking
- Graceful handling of port conflicts

### 2. **Persistent Across Sessions**
- Server continues running when claude-mpm sessions end
- Maintains event history and client connections
- Automatic reconnection for clients
- Health monitoring and recovery

### 3. **Independent Versioning**
- Server has its own version schema (v1.0.0)
- Compatibility matrix with claude-mpm versions
- Version discovery endpoint (`/version`)
- Graceful handling of version mismatches

### 4. **Deployment Agnostic**
- Works with local scripts, PyPI installations, Docker containers
- Cross-platform support (Linux, macOS, Windows)
- Automatic environment detection
- Service/daemon installation support

## Architecture Components

### Core Server (`standalone_socketio_server.py`)
```python
from claude_mpm.services.standalone_socketio_server import StandaloneSocketIOServer

# Create and start server
server = StandaloneSocketIOServer(host="localhost", port=8765)
server.start()  # Runs until stopped
```

**Key Features:**
- Independent lifecycle management
- Version compatibility checking
- Health monitoring endpoints
- Process isolation
- Signal handling for graceful shutdown

### Client Manager (`socketio_client_manager.py`)
```python
from claude_mpm.services.socketio_client_manager import get_client_manager

# Auto-discover and connect to servers
client_manager = get_client_manager()
client_manager.start_connection_manager()
```

**Key Features:**
- Automatic server discovery
- Version compatibility verification
- Intelligent server selection
- Automatic reconnection
- Fallback mechanisms

### Intelligent Server Factory (`websocket_server.py`)
```python
from claude_mpm.services.websocket_server import get_socketio_server

# Automatically selects best server mode
server = get_socketio_server()  # Returns client or embedded server
server.start()
```

**Modes:**
- **Auto**: Discovers standalone servers, falls back to embedded
- **Client**: Forces connection to standalone server
- **Embedded**: Forces local server instance

### Configuration Management (`socketio_config.py`)
```python
from claude_mpm.config.socketio_config import get_config

config = get_config()  # Auto-detects environment
# or
config = SocketIOConfig.for_production()
```

**Environments:**
- **Development**: Debug logging, shorter timeouts
- **Production**: Security hardening, file logging
- **Docker**: Container-optimized settings

## Installation and Management

### Server Manager Script
```bash
# Start a server
./scripts/claude-mpm-socketio start

# Check status
./scripts/claude-mpm-socketio status -v

# Stop server
./scripts/claude-mpm-socketio stop

# Health check
./scripts/claude-mpm-socketio health
```

### Installation Script
```bash
# Install for current user
./scripts/install_socketio_server.py --mode user

# Install system-wide with service
./scripts/install_socketio_server.py --mode system --environment production
```

## Version Compatibility

### Current Compatibility Matrix
```python
COMPATIBILITY_MATRIX = {
    "1.0.0": {
        "claude_mpm_versions": [">=0.7.0"],
        "min_python": "3.8",
        "socketio_min": "5.11.0",
        "features": [
            "persistent_server",
            "version_compatibility", 
            "process_isolation",
            "health_monitoring",
            "event_namespacing"
        ]
    }
}
```

### Version Discovery
```bash
curl http://localhost:8765/version
```

```json
{
  "server_version": "1.0.0",
  "server_id": "socketio-abc12345",
  "socketio_version": "5.11.0",
  "compatibility_matrix": {...},
  "supported_client_versions": [">=0.7.0"],
  "features": [...]
}
```

## Deployment Scenarios

### 1. **Local Development**
```bash
# Auto-detection mode (recommended)
python -m claude_mpm.cli.commands.run --monitor  # Starts embedded or connects to standalone

# Explicit standalone server
python -m claude_mpm.services.standalone_socketio_server
```

### 2. **PyPI Installation**
```bash
# Install socket.io dependencies
pip install claude-mpm[monitor]

# Start server
claude-mpm-socketio start

# Use in claude-mpm
claude-mpm run --monitor  # Auto-detects server
```

### 3. **Docker Container**
```dockerfile
FROM python:3.11
RUN pip install claude-mpm[monitor]
EXPOSE 8765
CMD ["python", "-m", "claude_mpm.services.standalone_socketio_server", "--host", "0.0.0.0"]
```

### 4. **System Service**
```bash
# Install as systemd service (Linux)
./scripts/install_socketio_server.py --mode system

# Start service
sudo systemctl start claude-mpm-socketio
```

## API Endpoints

### Health and Status
- `GET /health` - Server health check
- `GET /status` - Alias for health
- `GET /version` - Version and compatibility info
- `GET /stats` - Detailed server statistics

### Compatibility
- `POST /compatibility` - Check client version compatibility
  ```json
  {"client_version": "0.7.0"}
  ```

### Socket.IO Events
- **Client Events**: `claude_event`, `ping`, `get_version`, `get_history`
- **Server Events**: `connection_ack`, `compatibility_warning`, `server_status`, `event_history`

## Benefits

### For Developers
- **Persistent Monitoring**: Dashboard stays connected across sessions
- **Better Debugging**: Continuous event history
- **Easy Setup**: Auto-detection "just works"
- **Flexible Deployment**: Works in any environment

### For Operations
- **Resource Efficiency**: One server handles multiple clients
- **Independent Updates**: Server can be updated without touching claude-mpm
- **Health Monitoring**: Built-in diagnostics and monitoring
- **Service Management**: Standard systemd/launchd integration

### For Users
- **Seamless Experience**: Transparent connection management
- **Reliability**: Automatic reconnection and fallback
- **Performance**: Optimized for different deployment scenarios
- **Compatibility**: Clear version requirements and checking

## Migration Guide

### From Old WebSocket Server
The new architecture maintains full backward compatibility:

```python
# Old code continues to work
from claude_mpm.services.websocket_server import get_websocket_server
server = get_websocket_server()  # Now returns intelligent server
server.start()
```

### New Recommended Usage
```python
# Preferred new approach
from claude_mpm.services.websocket_server import get_socketio_server
server = get_socketio_server()  # Auto-selects best mode
server.start()
```

## Configuration Examples

### Environment Variables
```bash
export CLAUDE_MPM_SOCKETIO_HOST=0.0.0.0
export CLAUDE_MPM_SOCKETIO_PORT=8765
export CLAUDE_MPM_SOCKETIO_MODE=standalone
export CLAUDE_MPM_SOCKETIO_LOG_LEVEL=INFO
```

### Configuration File (`~/.claude-mpm/socketio_config.json`)
```json
{
  "host": "localhost",
  "port": 8765,
  "deployment_mode": "auto",
  "persistent": true,
  "cors_allowed_origins": "*",
  "log_level": "INFO",
  "max_history_size": 10000
}
```

## Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   ./scripts/claude-mpm-socketio start --port 8766
   ```

2. **Dependencies Missing**
   ```bash
   ./scripts/claude-mpm-socketio install-deps
   ```

3. **Version Incompatibility**
   ```bash
   curl http://localhost:8765/compatibility -d '{"client_version": "0.7.0"}'
   ```

4. **Server Not Starting**
   ```bash
   ./scripts/claude-mpm-socketio health
   python -m claude_mpm.services.standalone_socketio_server --help
   ```

### Debug Mode
```bash
export CLAUDE_MPM_SOCKETIO_LOG_LEVEL=DEBUG
python -m claude_mpm.services.standalone_socketio_server
```

## Future Enhancements

- **Load Balancing**: Multiple server instances with load balancing
- **Authentication**: Token-based authentication for production
- **Metrics**: Prometheus/Grafana integration
- **Clustering**: Redis-based clustering for horizontal scaling
- **SSL/TLS**: HTTPS support for production deployments

This architecture provides a solid foundation for scalable, reliable Socket.IO communication in claude-mpm while maintaining simplicity for development and flexibility for various deployment scenarios.