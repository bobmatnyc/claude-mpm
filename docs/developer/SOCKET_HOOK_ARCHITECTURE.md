# Socket.IO and Hook System Architecture

## Overview

The Claude MPM Socket.IO and Hook system provides real-time event streaming and processing capabilities for the dashboard and external integrations. This document details the architecture, data flow, configuration, and troubleshooting for this critical system.

## System Architecture

### High-Level Components

```
┌─────────────────┐    ┌───────────────────┐    ┌──────────────────┐
│   Claude Code   │    │   Hook Handler    │    │  Socket.IO       │
│     Events      │───→│   (Processor)     │───→│  Server          │
└─────────────────┘    └───────────────────┘    └──────────────────┘
                                │                         │
                                ▼                         ▼
                       ┌─────────────────┐    ┌──────────────────┐
                       │  Event Storage  │    │  Dashboard       │
                       │  & History      │    │  Client          │
                       └─────────────────┘    └──────────────────┘
```

### Core Services

1. **Hook Handler Service** (`hook_handler.py`)
   - Processes Claude Code events via stdin/stdout
   - Validates and enriches event data
   - Manages state and session tracking
   - Handles duplicate event detection

2. **Socket.IO Daemon** (`socketio_daemon.py`)
   - Manages server lifecycle and process control
   - Virtual environment detection and Python path resolution
   - PID tracking and process monitoring
   - Signal handling for graceful shutdown

3. **Socket.IO Client** (`socket-client.js`)
   - Dashboard WebSocket connection management
   - Event processing and display
   - Connection resilience with retry logic
   - Health monitoring and status reporting

4. **Hook Installer** (`installer.py`)
   - Claude Code hook installation and configuration
   - Script deployment and validation
   - Version compatibility checking
   - Automatic hook registration

## Data Flow Architecture

### Event Processing Pipeline

```
1. Claude Code Event Generation
   ├─ Tool execution events (Start/Stop)
   ├─ Subagent lifecycle events
   ├─ File operation events
   └─ Error and status events

2. Hook Handler Processing
   ├─ Event validation and schema checking
   ├─ Duplicate detection and filtering
   ├─ Event enrichment (timestamps, session IDs)
   ├─ State management and persistence
   └─ Error handling and recovery

3. Socket.IO Broadcasting
   ├─ Event serialization and formatting
   ├─ Client connection management
   ├─ Message queuing for disconnected clients
   └─ Health monitoring and diagnostics

4. Dashboard Client Processing
   ├─ Event reception and validation
   ├─ UI state updates and rendering
   ├─ Event history and session tracking
   └─ User interaction handling
```

### Event Types and Flow

#### Tool Events
- **Start Events**: Tool execution begins
- **Stop Events**: Tool execution completes
- **Error Events**: Tool execution failures

#### Subagent Events
- **SubagentStart**: Subagent initialization
- **SubagentStop**: Subagent completion
- **SubagentError**: Subagent failures

#### System Events
- **Connection**: Client connection status
- **Status**: System health and metrics
- **Config**: Configuration changes

### Thread Safety Considerations

#### Hook Handler
- **Single-threaded processing**: Processes events sequentially
- **Signal handlers**: Async-signal-safe operations only
- **State management**: Thread-safe singleton pattern
- **File operations**: Atomic writes with temporary files

#### Socket.IO Server
- **Event loop**: Single-threaded async event processing
- **Connection pool**: Thread-safe client management
- **Message queuing**: Lock-free queue implementation
- **Health monitoring**: Background thread for ping/pong

#### Dashboard Client
- **JavaScript single-threaded**: No concurrency issues
- **Event callbacks**: Queued and executed sequentially
- **Connection state**: Atomic state changes
- **Timer management**: Single event loop coordination

## Configuration

### Environment Variables

```bash
# Debug Mode
CLAUDE_MPM_HOOK_DEBUG=true|false          # Enable/disable hook debug output

# Connection Settings
CLAUDE_MPM_SOCKETIO_PORT=8765              # Default Socket.IO server port
CLAUDE_MPM_SOCKETIO_TIMEOUT=20000          # Connection timeout (ms)
CLAUDE_MPM_PING_INTERVAL=45000             # Ping interval (ms)
CLAUDE_MPM_PING_TIMEOUT=20000              # Ping timeout (ms)

# Performance Settings
CLAUDE_MPM_EVENT_QUEUE_SIZE=100            # Max events in queue
CLAUDE_MPM_RETRY_ATTEMPTS=5                # Max connection retries
CLAUDE_MPM_HEALTH_CHECK_INTERVAL=45000     # Health check frequency (ms)

# Security Settings
CLAUDE_MPM_BIND_HOST=127.0.0.1             # Server bind address (localhost only)
CLAUDE_MPM_MAX_CONNECTIONS=100             # Maximum client connections
```

### Server Configuration

#### Socket.IO Server Settings
```python
# Critical timing settings - must match client
PING_INTERVAL = 45000  # 45 seconds
PING_TIMEOUT = 20000   # 20 seconds

# Connection management
MAX_HTTP_BUFFER_SIZE = 1000000  # 1MB max message size
CORS_ALLOWED_ORIGINS = ["http://localhost:*"]  # Localhost only
ASYNC_MODE = 'eventlet'  # High-performance async mode
```

#### Client Configuration
```javascript
// Must match server ping settings
pingInterval: 45000,    // 45 seconds
pingTimeout: 20000,     // 20 seconds

// Connection resilience
reconnection: true,
reconnectionDelay: 1000,
reconnectionDelayMax: 5000,
reconnectionAttempts: 5,
timeout: 20000
```

### Hook Installation Configuration

```json
{
  "name": "claude-mpm-hooks",
  "version": "1.0.0",
  "matchers": [
    {
      "pattern": ".*",
      "script": "claude-hook-handler.sh"
    }
  ],
  "config": {
    "debug": true,
    "timeout": 30,
    "retry_attempts": 3
  }
}
```

## Performance Considerations

### Optimization Strategies

1. **Event Processing**
   - Lazy validation for non-critical events
   - Batch processing for high-frequency events
   - Schema caching to reduce validation overhead
   - Early filtering to reject invalid events

2. **Connection Management**
   - Connection pooling for multiple clients
   - Keep-alive mechanisms to prevent timeouts
   - Exponential backoff for retry logic
   - Health monitoring to detect issues early

3. **Memory Management**
   - Event queue size limits (100 events max)
   - Automatic cleanup of stale sessions
   - Circular buffer for event history
   - Garbage collection of disconnected clients

4. **Network Optimization**
   - Message compression for large payloads
   - Batching of frequent small messages
   - Binary serialization for performance-critical data
   - Local-only connections to avoid network latency

### Performance Metrics

- **Event Processing Rate**: ~1000 events/second
- **Connection Establishment**: <100ms on localhost
- **Memory Usage**: ~10MB base + 1KB per queued event
- **CPU Usage**: <5% during normal operation
- **Network Bandwidth**: <1MB/hour for typical usage

## Security Architecture

### Security Boundaries

1. **Network Security**
   - Localhost-only binding (127.0.0.1)
   - No external network access allowed
   - Port restrictions to ephemeral range
   - Connection limit enforcement

2. **Process Security**
   - Separate process isolation for daemon
   - PID file protection and ownership validation
   - Signal handling for clean shutdown
   - Resource limits and timeout enforcement

3. **Data Security**
   - Event schema validation prevents injection
   - No persistent storage of sensitive data
   - Memory-only event queues
   - Automatic cleanup of stale data

### Security Gotchas

⚠️ **Critical Security Notes**:

1. **Localhost Only**: Server MUST bind to 127.0.0.1, never 0.0.0.0
2. **No Authentication**: System relies on localhost access control
3. **Process Trust**: Hook handler runs with user privileges
4. **Event Content**: No validation of event payload content
5. **File Operations**: Hook installer modifies Claude Code configuration

## Troubleshooting Guide

### Common Issues

#### Connection Problems

**Symptom**: Dashboard shows "Disconnected" status
```bash
# Check if server is running
ps aux | grep socketio

# Check port availability
netstat -ln | grep :8765

# Test connection manually
curl http://localhost:8765/socket.io/

# Check server logs
tail -f ~/.claude-mpm/logs/socketio.log
```

**Solutions**:
- Restart Socket.IO daemon: `claude-mpm dashboard --restart-socketio`
- Check firewall settings (should allow localhost connections)
- Verify virtual environment has required packages
- Check for port conflicts with other applications

#### Event Processing Issues

**Symptom**: Events not appearing in dashboard
```bash
# Enable debug mode
export CLAUDE_MPM_HOOK_DEBUG=true

# Check hook installation
claude hooks list | grep claude-mpm

# Test hook manually
echo '{"event": "test"}' | python3 hook_handler.py

# Check event validation
grep "validation failed" ~/.claude-mpm/logs/hook.log
```

**Solutions**:
- Reinstall hooks: `claude-mpm hooks install`
- Validate event schema format
- Check Claude Code version compatibility (>=1.0.92)
- Verify hook handler permissions and execution

#### Performance Issues

**Symptom**: High CPU usage or memory consumption
```bash
# Monitor resource usage
top -p $(pgrep -f socketio)

# Check event queue size
curl http://localhost:8765/socket.io/status | jq '.queue_size'

# Monitor connection count
netstat -an | grep :8765 | wc -l
```

**Solutions**:
- Reduce event queue size in configuration
- Implement event filtering for noisy sources
- Check for connection leaks in client code
- Monitor garbage collection and memory usage

### Diagnostic Tools

#### Health Check Endpoints

```bash
# Server status
curl http://localhost:8765/socket.io/status

# Connection information
curl http://localhost:8765/socket.io/connections

# Event statistics
curl http://localhost:8765/socket.io/events/stats

# Health check
curl http://localhost:8765/socket.io/health
```

#### Log Analysis

```bash
# Server logs
tail -f ~/.claude-mpm/logs/socketio-server.log

# Hook handler logs
tail -f ~/.claude-mpm/logs/hook-handler.log

# Client connection logs
tail -f ~/.claude-mpm/logs/socketio-client.log

# Error analysis
grep ERROR ~/.claude-mpm/logs/*.log | tail -20
```

#### Debug Mode Commands

```bash
# Enable full debug output
export CLAUDE_MPM_HOOK_DEBUG=true
export CLAUDE_MPM_SOCKETIO_DEBUG=true

# Test hook processing
echo '{"test": "event"}' | python3 -m claude_mpm.hooks.claude_hooks.hook_handler

# Monitor real-time events
websocat ws://localhost:8765/socket.io/?EIO=4&transport=websocket

# Validate configuration
python3 -c "from claude_mpm.config import get_socketio_config; print(get_socketio_config())"
```

### Recovery Procedures

#### Complete System Reset

```bash
# Stop all processes
pkill -f socketio
pkill -f hook_handler

# Clean state files
rm -f ~/.claude-mpm/socketio-*
rm -f ~/.claude-mpm/hook-*

# Reinstall hooks
claude-mpm hooks uninstall
claude-mpm hooks install

# Restart services
claude-mpm dashboard --start-socketio
```

#### Graceful Recovery

```bash
# Soft restart (preserves connections)
curl -X POST http://localhost:8765/socket.io/reload

# Reconnect clients
curl -X POST http://localhost:8765/socket.io/reconnect-all

# Clear event queues
curl -X POST http://localhost:8765/socket.io/clear-queues
```

## Gotchas and Common Pitfalls

### Development Gotchas

1. **Ping Interval Mismatch**: Client and server ping intervals MUST match exactly
2. **Virtual Environment**: Daemon must use same Python environment as parent
3. **Signal Handling**: Async-signal-safe functions only in signal handlers
4. **Event Queue Overflow**: Queue size limits prevent memory exhaustion
5. **Connection Race Conditions**: Use proper cleanup delays between connections

### Production Considerations

1. **Process Monitoring**: Implement health checks and automatic restart
2. **Log Rotation**: Prevent log files from consuming disk space
3. **Resource Limits**: Set appropriate memory and CPU limits
4. **Error Recovery**: Handle network partitions and process crashes gracefully
5. **Version Compatibility**: Test hook compatibility with Claude Code updates

### Testing Considerations

1. **Mock Environments**: Tests may not have full Socket.IO environment
2. **Timing Dependencies**: Use proper synchronization in async tests
3. **Resource Cleanup**: Always clean up connections and processes in tests
4. **Error Injection**: Test error conditions and recovery scenarios
5. **Performance Testing**: Include load testing for high event volumes

## Future Architecture Improvements

### Planned Enhancements

1. **Event Persistence**: Optional database storage for event history
2. **Authentication**: Token-based authentication for external access
3. **Clustering**: Multi-instance support with load balancing
4. **Monitoring**: Comprehensive metrics and alerting system
5. **Configuration UI**: Web-based configuration management

### Scalability Considerations

1. **Horizontal Scaling**: Multi-process architecture for high load
2. **Event Streaming**: Apache Kafka integration for large-scale deployments
3. **Caching**: Redis integration for distributed caching
4. **Load Balancing**: HAProxy/nginx integration for multiple instances
5. **Monitoring**: Prometheus/Grafana integration for observability