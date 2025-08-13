# Socket.IO Dashboard Architecture

This document provides comprehensive technical documentation for the Claude MPM Socket.IO-based real-time dashboard system. This is the **LIVE, production Socket.IO dashboard**, not an experimental or prototype implementation.

## Architecture Overview

The Socket.IO dashboard provides real-time monitoring of Claude Code sessions through a WebSocket-based event streaming system. The architecture follows a client-server model with event-driven communication.

### System Components

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Claude Code   │───▶│   Hook Handler   │───▶│  Socket.IO      │
│    Session      │    │  (Optimized)     │    │   Server        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
                                                         ▼
                                                ┌─────────────────┐
                                                │   Dashboard     │
                                                │   (Browser)     │
                                                └─────────────────┘
```

### Key Principles

1. **Zero-Latency**: Hook handling adds <1ms to Claude Code operations
2. **Real-Time Events**: Live streaming of tool usage, file operations, and agent activities
3. **Persistent Connections**: Automatic reconnection handling for reliable monitoring
4. **Event Isolation**: Session-based filtering prevents cross-session interference
5. **Static Architecture**: Dashboard runs as static files, no web server required

## Event Flow Architecture

### 1. Event Sources

Events originate from Claude Code hooks during normal operation:

- **Tool Events**: Pre/post tool usage (Read, Write, Edit, Grep, etc.)
- **Agent Events**: Subagent delegations and completions
- **Session Events**: Session start/stop and status changes
- **Memory Events**: Learning updates and context injections

### 2. Hook Handler Processing

The hook handler (`/src/claude_mpm/hooks/claude_hooks/hook_handler.py`) captures events and forwards them to the Socket.IO server:

```python
# Event processing flow
1. Claude Code executes tool → Hook triggers
2. Hook handler processes event → Normalizes data
3. Event sent to Socket.IO server → Real-time broadcast
4. Dashboard receives event → UI updates
```

### 3. Socket.IO Server

The server (`/src/claude_mpm/services/socketio_server.py`) manages:

- **Connection Pool**: Multiple dashboard clients can connect simultaneously
- **Event Broadcasting**: Real-time event distribution to all connected clients
- **Session Management**: Event filtering by session ID
- **Persistence**: Optional event history storage

### 4. Dashboard Client

The browser-based dashboard (`/src/claude_mpm/dashboard/templates/index.html`) provides:

- **Live Event Display**: Real-time event visualization across 4 tabs
- **Interactive Filtering**: Search, filter, and analyze events
- **File Operation Tracking**: Detailed file operation history
- **Agent Activity Monitoring**: Subagent delegation and task tracking

## Key Implementation Files

### Core Architecture Files

- **Socket.IO Server**: `/src/claude_mpm/services/socketio_server.py`
  - Main server implementation with connection management
  - Event broadcasting and session handling
  - SocketIOClientProxy for exec mode integration

- **Hook Handler**: `/src/claude_mpm/hooks/claude_hooks/hook_handler.py`
  - Event capture from Claude Code hooks
  - Event normalization and forwarding to Socket.IO

- **Dashboard HTML**: `/src/claude_mpm/dashboard/templates/index.html`
  - Static dashboard interface
  - Socket.IO client connection management
  - Tab-based event visualization

### JavaScript Components

- **File Tool Tracker**: `/src/claude_mpm/dashboard/static/js/components/file-tool-tracker.js`
  - **Purpose**: Tracks file operations and tool calls
  - **Key Feature**: Case-insensitive tool name handling
  - **Supported Tools**: Read, Write, Edit, MultiEdit, Grep, Glob, LS, NotebookEdit, Bash

- **Event Processor**: `/src/claude_mpm/dashboard/static/js/components/event-processor.js`
  - Event correlation and pairing logic
  - Real-time event stream processing

- **Agent Inference**: `/src/claude_mpm/dashboard/static/js/components/agent-inference.js`
  - Agent type detection from events
  - Confidence scoring for agent identification

### Configuration Files

- **Dashboard Config**: Port 8765 (default)
- **Hook Configuration**: Automatically managed when using `--monitor` flag
- **Connection Settings**: `localhost` only for security

## Distinguishing Features vs Other Implementations

This is the **primary Socket.IO dashboard implementation** with these distinguishing characteristics:

### What Makes This the "Live" Dashboard

1. **Production Ready**: Used in actual Claude Code monitoring
2. **Socket.IO Based**: Uses Socket.IO protocol, not raw WebSockets
3. **Real Event Integration**: Connected to actual Claude Code hook system
4. **File Operation Tracking**: Advanced file-tool-tracker.js implementation
5. **Multi-Client Support**: Multiple dashboard instances can connect

### Not a Prototype

- **Full Feature Set**: Complete event processing and visualization
- **Error Handling**: Robust connection management and recovery
- **Performance Optimized**: Micro-batching and circuit breaker patterns
- **Browser Compatibility**: Works across all modern browsers

## Connection Management

### Server Modes

The Socket.IO server operates in two modes:

#### 1. Direct Mode
- Server runs in the same process as Claude MPM
- Used with `./claude-mpm --monitor`
- Immediate startup and shutdown

#### 2. Exec Mode (Proxy)
- Persistent server runs in separate process
- Claude processes connect via SocketIOClientProxy
- Better performance for multiple concurrent sessions

### Connection Flow

```
1. Dashboard Request (Browser)
   ↓
2. Socket.IO Connection (WebSocket upgrade)
   ↓
3. Event Stream Subscription
   ↓
4. Real-time Event Reception
   ↓
5. UI Updates (Live)
```

### Automatic Reconnection

The dashboard implements automatic reconnection:

```javascript
// Connection management
socket.on('disconnect', () => {
    console.log('Disconnected from server, attempting reconnection...');
    // Socket.IO automatically attempts reconnection
});

socket.on('connect', () => {
    console.log('Connected to Socket.IO server');
    // Request event history if needed
});
```

## Port Configuration

- **Default Port**: 8765
- **Protocol**: HTTP/Socket.IO (WebSocket upgrade)
- **Host**: localhost only (security restriction)
- **Access URL**: http://localhost:8765

### Port Configuration Options

```bash
# Environment variable
export SOCKETIO_PORT=8765

# Command line
./claude-mpm --monitor --port 8765

# Configuration file
socketio:
  port: 8765
  host: localhost
```

## Security Architecture

### Local-Only Access

- **Bind Address**: 127.0.0.1 (localhost)
- **No External Access**: Dashboard not accessible from network
- **No Authentication**: Not needed due to local-only access
- **Data Privacy**: All events stay on local machine

### Event Data Security

- **No Sensitive Data Storage**: Events processed in memory
- **Session Isolation**: Events filtered by session ID
- **No Persistence**: Events cleared on restart (optional)

## Performance Characteristics

### Latency Metrics

- **Hook Processing**: <1ms additional latency per event
- **Event Transmission**: <5ms from hook to dashboard
- **UI Updates**: <10ms from event receipt to display
- **Memory Usage**: ~10MB for dashboard server

### Optimization Features

- **Connection Pooling**: Reuses Socket.IO connections
- **Micro-batching**: Groups high-frequency events
- **Circuit Breaker**: Graceful degradation during outages
- **Async Processing**: Non-blocking event handling

### Scalability Limits

- **Concurrent Dashboards**: 10-20 simultaneous connections
- **Event Rate**: 1000+ events/second sustained
- **Memory**: Events cleared periodically to prevent growth
- **CPU Impact**: <1% additional CPU usage

## Next Steps

For detailed implementation guidance, see:

- **[File Viewer Implementation](./FILE_VIEWER_IMPLEMENTATION.md)** - File operation tracking details
- **[Common Issues & Solutions](./TROUBLESHOOTING.md)** - Debugging and problem resolution
- **[Testing & Debugging](./TESTING_DEBUGGING.md)** - Verification procedures
- **[Important Notes](./IMPORTANT_NOTES.md)** - Critical implementation details

## Support and Debugging

### Debug Mode

```bash
# Enable detailed logging
export CLAUDE_MPM_HOOK_DEBUG=true
./claude-mpm --monitor
```

### Health Checks

```bash
# Check server status
curl http://localhost:8765/health

# Monitor connections
netstat -an | grep 8765
```

### Log Locations

- **Server Logs**: stdout/stderr from claude-mpm process
- **Browser Logs**: Browser developer console
- **Hook Logs**: Claude Code hook execution logs