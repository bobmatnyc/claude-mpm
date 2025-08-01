# Socket.IO Implementation Guide

This comprehensive guide covers the Socket.IO implementation in Claude MPM, which provides real-time monitoring, event streaming, and interactive dashboard capabilities.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Namespace Organization](#namespace-organization)
- [Getting Started](#getting-started)
- [Dashboard Usage](#dashboard-usage)
- [Custom Client Integration](#custom-client-integration)
- [API Reference](#api-reference)
- [Configuration](#configuration)
- [Security Considerations](#security-considerations)
- [Troubleshooting](#troubleshooting)

---

## Overview

Claude MPM includes a sophisticated Socket.IO implementation that replaces the previous WebSocket-based system. This provides better reliability, automatic reconnection, and enhanced features for real-time monitoring of Claude MPM sessions.

### Why Socket.IO over Raw WebSockets?

- **Automatic reconnection** with exponential backoff
- **Built-in event system** with acknowledgments
- **Namespace support** for organizing events by category
- **Room-based client grouping** for targeted broadcasting
- **Better error handling** and debugging capabilities
- **Admin UI support** out of the box
- **Fallback mechanisms** for network issues

### Key Features

- **Real-time monitoring** of Claude MPM sessions
- **Multi-namespace architecture** for organized event streams
- **Interactive dashboard** with filtering and search
- **Admin UI integration** for detailed connection management
- **Automatic logging integration** for real-time log streaming
- **Memory system events** for agent memory operations
- **Hook system integration** for extensibility events

---

## Architecture

The Socket.IO implementation follows a clean, namespace-based architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                    Socket.IO Server                         │
│                  (Port 8765 / 3000)                        │
├─────────────────────────────────────────────────────────────┤
│  Namespaces:                                               │
│  • /system    - Server status, connections                 │
│  • /session   - Session lifecycle events                   │
│  • /claude    - Claude process events                      │
│  • /agent     - Agent delegation events                    │
│  • /hook      - Hook execution events                      │
│  • /todo      - Todo list updates                          │
│  • /memory    - Memory system events                       │
│  • /log       - Real-time logging                          │
└─────────────────────────────────────────────────────────────┘
│
├── Dashboard Client (HTML/JS)
├── Admin UI Client
├── Custom Clients
└── Hook Handlers
```

### Components

1. **SocketIOServer** (`src/claude_mpm/services/websocket_server.py`)
   - Main server implementation with namespace handlers
   - Event broadcasting and room management
   - Authentication and security features

2. **SocketIOClientProxy** (`src/claude_mpm/services/websocket_server.py`)
   - Client proxy for exec mode scenarios
   - Connects to existing server instances
   - Provides same interface as server

3. **WebSocketHandler** (`src/claude_mpm/core/websocket_handler.py`)
   - Logging handler for real-time log streaming
   - Integrates with the unified logging system
   - Socket.IO client for reliable log emission

4. **Dashboard** (`scripts/claude_mpm_socketio_dashboard.html`)
   - Interactive web dashboard for monitoring
   - Multi-namespace event filtering
   - Real-time metrics and visualizations

---

## Namespace Organization

The Socket.IO server is organized into logical namespaces, each handling specific types of events:

### `/system` - System Events
- **Purpose**: Server status, connection management, health checks
- **Events**: `status`, `heartbeat`, `server_info`
- **Clients**: Admin tools, monitoring dashboards

### `/session` - Session Lifecycle
- **Purpose**: Track Claude MPM session start/end events
- **Events**: `start`, `end`, `status_changed`
- **Data**: Session ID, start time, working directory, duration

### `/claude` - Claude Process Events
- **Purpose**: Monitor Claude AI process state and output
- **Events**: `status_changed`, `output`, `thinking`
- **Data**: Process ID, status, output streams, thinking indicators

### `/agent` - Agent Operations
- **Purpose**: Track agent delegation and task execution
- **Events**: `task_delegated`, `task_completed`, `agent_switched`
- **Data**: Agent type, task description, execution status

### `/hook` - Hook System Events
- **Purpose**: Monitor hook execution and extensibility events
- **Events**: `user_prompt`, `pre_tool`, `post_tool`, `hook_error`
- **Data**: Hook name, execution context, timing information

### `/todo` - Todo Management
- **Purpose**: Real-time todo list updates and task tracking
- **Events**: `updated`, `task_added`, `task_completed`
- **Data**: Todo items, completion statistics, progress metrics

### `/memory` - Memory System Events
- **Purpose**: Agent memory operations and learning events
- **Events**: `loaded`, `created`, `updated`, `injected`
- **Data**: Agent ID, memory operations, learning content

### `/log` - Real-time Logging
- **Purpose**: Stream log messages in real-time
- **Events**: `message`, `error`, `warning`
- **Data**: Log level, message content, module information

---

## Getting Started

### Prerequisites

- Node.js 14+ (for Socket.IO server)
- Python 3.8+ with `python-socketio` package
- Modern web browser (for dashboard)

### Quick Start

1. **Launch the Socket.IO Dashboard**:
   ```bash
   python scripts/launch_socketio_dashboard.py
   ```

2. **Start Claude MPM with Socket.IO enabled**:
   ```bash
   ./claude-mpm --manager
   ```

3. **Access the Dashboard**:
   - Dashboard: http://localhost:3000/claude_mpm_socketio_dashboard.html
   - Admin UI: http://localhost:3000/admin

### Manual Setup

If you prefer manual setup:

1. **Install Dependencies**:
   ```bash
   cd scripts/
   npm install socket.io @socket.io/admin-ui
   ```

2. **Start Socket.IO Server**:
   ```bash
   node scripts/socketio_server.js
   ```

3. **Connect Claude MPM**:
   ```bash
   ./claude-mpm  # Will auto-detect running Socket.IO server
   ```

---

## Dashboard Usage

The Socket.IO dashboard provides a comprehensive interface for monitoring Claude MPM sessions in real-time.

### Dashboard Features

#### Connection Management
- **Auto-connect**: Dashboard connects automatically on load
- **Reconnection**: Automatic reconnection with status indicators
- **Multiple namespaces**: Subscribe to relevant event streams
- **Connection info**: Display socket ID, connection time, active namespaces

#### Event Filtering and Search
- **Namespace tabs**: Filter events by namespace (`/system`, `/session`, etc.)
- **Event type filter**: Filter by specific event types
- **Search functionality**: Full-text search across event data
- **Real-time filtering**: Instant filtering without losing live updates

#### Visualizations and Metrics
- **Live metrics**: Total events, events per minute, unique event types
- **Error tracking**: Count and highlight error events
- **Event stream**: Real-time scrolling event list
- **Event details**: Click events for detailed JSON view

#### Data Export
- **JSON export**: Export filtered events to JSON file
- **Session data**: Include metadata and filtering context
- **Keyboard shortcuts**: Ctrl/Cmd+E for quick export

### Keyboard Shortcuts

- **Ctrl/Cmd + K**: Focus search input
- **Ctrl/Cmd + E**: Export current events
- **Ctrl/Cmd + R**: Clear event history
- **Escape**: Close modal dialogs

### Dashboard Configuration

The dashboard supports URL parameters for customization:

```
http://localhost:3000/claude_mpm_socketio_dashboard.html?port=3000&autoconnect=true
```

Parameters:
- `port`: Socket.IO server port (default: 3000)
- `autoconnect`: Auto-connect on page load (default: false)

---

## Custom Client Integration

You can create custom clients to integrate with the Claude MPM Socket.IO server.

### Basic Socket.IO Client

```javascript
const io = require('socket.io-client');

// Connect to multiple namespaces
const systemSocket = io('http://localhost:3000/system');
const sessionSocket = io('http://localhost:3000/session');
const logSocket = io('http://localhost:3000/log');

// System events
systemSocket.on('connect', () => {
    console.log('Connected to system namespace');
});

systemSocket.on('status', (data) => {
    console.log('System status:', data);
});

// Session events
sessionSocket.on('start', (data) => {
    console.log('Session started:', data.session_id);
});

sessionSocket.on('end', (data) => {
    console.log('Session ended after', data.duration_seconds, 'seconds');
});

// Real-time logs
logSocket.on('message', (data) => {
    console.log(`[${data.level}] ${data.message}`);
});
```

### Python Client Example

```python
import socketio

# Create Socket.IO client
sio = socketio.Client()

# Connect to server
sio.connect('http://localhost:3000')

# Connect to specific namespaces
system_sio = socketio.Client()
system_sio.connect('http://localhost:3000/system')

@system_sio.event
def status(data):
    print(f"System status: {data}")

@sio.event
def connect():
    print("Connected to Socket.IO server")

@sio.event  
def disconnect():
    print("Disconnected from Socket.IO server")

# Keep client running
sio.wait()
```

### Authentication

For production deployments, enable authentication:

```javascript
const socket = io('http://localhost:3000/system', {
    auth: {
        token: 'your-auth-token'
    }
});
```

Set the authentication token via environment variable:
```bash
export CLAUDE_MPM_SOCKETIO_TOKEN=your-secret-token
```

---

## API Reference

### Server Events (Outbound)

#### System Namespace (`/system`)

**Event: `status`**
```json
{
    "session_id": "20250131_143052",
    "session_start": "2025-01-31T14:30:52.123Z",
    "claude_status": "running",
    "claude_pid": 12345,
    "server_info": {
        "host": "localhost",
        "port": 3000,
        "working_dir": "/path/to/project",
        "timestamp": "2025-01-31T14:35:22.456Z"
    }
}
```

#### Session Namespace (`/session`)

**Event: `start`**
```json
{
    "session_id": "20250131_143052",
    "start_time": "2025-01-31T14:30:52.123Z",
    "launch_method": "interactive",
    "working_directory": "/path/to/project",
    "timestamp": "2025-01-31T14:30:52.123Z"
}
```

**Event: `end`**
```json
{
    "session_id": "20250131_143052",
    "end_time": "2025-01-31T14:45:22.456Z",
    "duration_seconds": 890.333,
    "timestamp": "2025-01-31T14:45:22.456Z"
}
```

#### Claude Namespace (`/claude`)

**Event: `status_changed`**
```json
{
    "status": "running",
    "pid": 12345,
    "message": "Claude process started successfully",
    "timestamp": "2025-01-31T14:30:55.789Z"
}
```

**Event: `output`**
```json
{
    "content": "Processing your request...",
    "stream": "stdout",
    "timestamp": "2025-01-31T14:31:00.123Z"
}
```

#### Agent Namespace (`/agent`)

**Event: `task_delegated`**
```json
{
    "agent": "engineer",
    "task": "Implement user authentication system",
    "status": "started",
    "timestamp": "2025-01-31T14:31:15.456Z"
}
```

#### Hook Namespace (`/hook`)

**Event: `user_prompt`**
```json
{
    "prompt": "Implement user authentication",
    "session_id": "20250131_143052",
    "timestamp": "2025-01-31T14:31:10.789Z"
}
```

**Event: `pre_tool`**
```json
{
    "tool_name": "Edit",
    "session_id": "20250131_143052",
    "timestamp": "2025-01-31T14:31:20.123Z"
}
```

#### Todo Namespace (`/todo`)

**Event: `updated`**
```json
{
    "todos": [
        {
            "id": "1",
            "content": "Implement authentication",
            "status": "in_progress",
            "priority": "high"
        }
    ],
    "stats": {
        "total": 5,
        "completed": 2,
        "in_progress": 1,
        "pending": 2
    },
    "timestamp": "2025-01-31T14:31:25.456Z"
}
```

#### Memory Namespace (`/memory`)

**Event: `loaded`**
```json
{
    "agent_id": "engineer",
    "memory_size": 2048,
    "sections_count": 3,
    "timestamp": "2025-01-31T14:30:58.789Z"
}
```

**Event: `updated`**
```json
{
    "agent_id": "engineer",
    "learning_type": "success_pattern",
    "content": "Successfully implemented authentication using JWT",
    "section": "implementation_patterns",
    "timestamp": "2025-01-31T14:45:10.123Z"
}
```

#### Log Namespace (`/log`)

**Event: `message`**
```json
{
    "timestamp": "2025-01-31T14:31:30.456Z",
    "level": "INFO",
    "logger": "claude_mpm.core.claude_runner",
    "message": "Claude session started successfully",
    "module": "claude_runner",
    "function": "start_session",
    "line": 145,
    "thread": 140234567890,
    "thread_name": "MainThread"
}
```

### Client Events (Inbound)

#### System Namespace (`/system`)

**Event: `get_status`**
Request current system status. Server responds with `status` event.

### HTTP Endpoints

**GET `/health`**
```json
{
    "status": "healthy",
    "server": "claude-mpm-socketio",
    "timestamp": "2025-01-31T14:35:00.123Z",
    "session_id": "20250131_143052",
    "claude_status": "running"
}
```

**GET `/admin`**
Returns HTML page for Socket.IO Admin UI integration.

**POST `/emit`**
Inject events externally:
```json
{
    "namespace": "system",
    "event": "custom_event",
    "data": {
        "message": "Custom event data"
    }
}
```

---

## Configuration

### Environment Variables

- `CLAUDE_MPM_SOCKETIO_TOKEN`: Authentication token for connections
- `CLAUDE_MPM_HOOK_DEBUG`: Enable debug logging for Socket.IO components
- `SOCKETIO_PORT`: Override default Socket.IO server port (default: 3000/8765)

### Server Configuration

The Socket.IO server can be configured via the launcher script:

```bash
python scripts/launch_socketio_dashboard.py --port 3000 --no-browser
```

Options:
- `--port PORT`: Server port (default: 3000)
- `--no-browser`: Don't open browser automatically
- `--admin-only`: Open only admin UI
- `--setup-only`: Setup files without starting server

### Integration Configuration

Configure Socket.IO integration in Claude MPM:

```python
from claude_mpm.services.websocket_server import start_socketio_server

# Start with custom port
server = start_socketio_server()
server.port = 3000
server.start()
```

---

## Security Considerations

### Authentication

- Set `CLAUDE_MPM_SOCKETIO_TOKEN` environment variable
- Clients must provide matching token in auth object
- Default development mode accepts all connections

### CORS Configuration

The server allows CORS from localhost by default. For production:

```javascript
const io = new Server(httpServer, {
    cors: {
        origin: ["https://yourdomain.com"],
        methods: ["GET", "POST"],
        credentials: true
    }
});
```

### Data Privacy

- Log events may contain sensitive information
- Consider log filtering for production deployments
- Memory events may expose agent learning content

### Network Security

- Use HTTPS/WSS in production environments
- Configure proper firewall rules
- Consider VPN access for remote monitoring

---

## Troubleshooting

### Common Issues

#### Connection Failures

**Problem**: Dashboard shows "Connection Failed"
**Solutions**:
1. Verify Socket.IO server is running: `curl http://localhost:3000/health`
2. Check port availability: `netstat -tlnp | grep 3000`
3. Review server logs for errors
4. Try different port: `python scripts/launch_socketio_dashboard.py --port 8765`

#### No Events Appearing

**Problem**: Dashboard connects but shows no events
**Solutions**:
1. Ensure Claude MPM is running with Socket.IO enabled
2. Check namespace connections in browser dev tools
3. Verify event emission in server logs
4. Test with manual event injection: `curl -X POST http://localhost:3000/emit -d '{"namespace":"system","event":"test","data":{}}'`

#### Performance Issues

**Problem**: Dashboard becomes slow with many events
**Solutions**:
1. Use event filtering to reduce noise
2. Clear event history regularly (Ctrl+R)
3. Increase browser memory limits
4. Use virtual scrolling for large event lists

#### Authentication Errors

**Problem**: "Invalid authentication token" errors
**Solutions**:
1. Set correct `CLAUDE_MPM_SOCKETIO_TOKEN` environment variable
2. Restart both server and client after token changes
3. Check token format (no special characters/spaces)
4. Use development mode (no token required) for testing

### Debug Mode

Enable debug mode for detailed troubleshooting:

```bash
export CLAUDE_MPM_HOOK_DEBUG=true
python scripts/launch_socketio_dashboard.py
```

This provides:
- Detailed connection logs
- Event emission tracing
- Error stack traces
- Performance metrics

### Log Analysis

Check Socket.IO server logs:
```bash
# If using launcher script
tail -f ~/.claude-mpm/logs/socketio_server.log

# If running manually
# Check console output of socketio_server.js
```

Check Claude MPM integration logs:
```bash
tail -f ~/.claude-mpm/logs/latest.log | grep -i socketio
```

### Performance Monitoring

Monitor Socket.IO performance:

1. **Admin UI**: Use Socket.IO Admin UI at http://localhost:3000/admin
2. **Browser Tools**: Check WebSocket connections in Network tab
3. **System Resources**: Monitor CPU/memory usage of Node.js process
4. **Event Metrics**: Use dashboard metrics panel for event rates

---

## Advanced Usage

### Custom Event Broadcasting

Emit custom events from Python code:

```python
from claude_mpm.services.websocket_server import get_socketio_server

server = get_socketio_server() 
server.emit_event('/system', 'custom_event', {
    "message": "Custom event data",
    "user_id": "admin",
    "action": "manual_trigger"
})
```

### Hook Integration

Create hooks that emit Socket.IO events:

```python
from claude_mpm.hooks.base_hook import BaseHook
from claude_mpm.services.websocket_server import get_socketio_server

class SocketIOHook(BaseHook):
    def __init__(self):
        self.server = get_socketio_server()
    
    def post_tool_use(self, tool_name: str, result, session_id: str):
        self.server.emit_event('/hook', 'post_tool', {
            "tool_name": tool_name,
            "success": result.success,
            "session_id": session_id
        })
```

### Multi-Server Setup

For distributed deployments:

1. **Redis Adapter**: Use Redis for multi-server Socket.IO
2. **Load Balancing**: Configure sticky sessions
3. **Health Checks**: Implement distributed health monitoring
4. **Event Aggregation**: Centralize event collection

This comprehensive guide covers all aspects of the Socket.IO implementation in Claude MPM. For additional support, refer to the troubleshooting section or check the Socket.IO documentation at https://socket.io/docs/.