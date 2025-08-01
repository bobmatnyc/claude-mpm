# WebSocket Hooks Architecture

This document details the WebSocket architecture used for real-time event broadcasting in Claude MPM.

## Overview

The WebSocket system enables real-time communication between Claude Code hooks and the monitoring dashboard. It uses a persistent server architecture with client proxies to ensure minimal latency and maximum reliability.

## Architecture Components

### 1. WebSocket Server (`WebSocketServer`)

The main server that handles client connections and event broadcasting.

**Location**: `src/claude_mpm/services/websocket_server.py`

**Key Features**:
- Runs on port 8765 by default
- Handles multiple client connections
- Maintains event history (last 1000 events)
- Thread-safe broadcasting
- Automatic client cleanup

**Implementation**:
```python
class WebSocketServer:
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.clients: Set = set()
        self.event_history: deque = deque(maxlen=1000)
        
    async def broadcast(self, message: str):
        # Broadcasts to all connected clients
        websockets.broadcast(self.clients, message)
```

### 2. WebSocket Client Proxy (`WebSocketClientProxy`)

A proxy that connects to the persistent server from hook handlers.

**Key Features**:
- Automatically detects if server is running
- Non-blocking event sending
- Automatic reconnection
- Compatible with WebSocketServer interface

**Optimizations**:
```python
def broadcast_event(self, event_type: str, data: Dict[str, Any]):
    # Send asynchronously without blocking
    asyncio.run_coroutine_threadsafe(
        self._send_message(message), 
        self._client_loop
    )
    # Don't wait for result - let it send in background
```

### 3. Production WebSocket Server

Enhanced server with session management and health monitoring.

**Location**: `scripts/websocket_server_production.py`

**Features**:
- Session-based event filtering
- Health checks every 30 seconds
- Graceful error handling
- Connection monitoring with ping/pong
- Automatic client cleanup

**Session Management**:
```python
# Clients register with session ID
{
    "type": "register",
    "session_id": "your-session-id"
}

# Events are filtered by session
self.clients = {
    "session-1": {websocket1, websocket2},
    "session-2": {websocket3},
    "global": {websocket4}
}
```

## Event Flow

### 1. Hook Triggered
```
Claude Code → Hook Handler → WebSocketClientProxy
```

### 2. Event Broadcasting
```
WebSocketClientProxy → WebSocket Server → All Dashboard Clients
```

### 3. Event Structure
```json
{
    "type": "hook.user_prompt",
    "timestamp": "2025-07-31T12:00:00.000Z",
    "data": {
        "prompt": "User's prompt text",
        "session_id": "abc123",
        "cwd": "/path/to/project"
    }
}
```

## Connection Management

### Server Detection

The system automatically detects if a server is running:

```python
def get_websocket_server() -> WebSocketServer:
    # Check if server is running on port 8765
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        result = s.connect_ex(('127.0.0.1', 8765))
        if result == 0:
            # Server running - create proxy
            return WebSocketClientProxy(port=8765)
        else:
            # No server - create real server
            return WebSocketServer()
```

### IPv4/IPv6 Handling

To avoid connection issues, the system uses IPv4 explicitly:
- Server binds to `127.0.0.1` (not `localhost`)
- Clients connect to `ws://127.0.0.1:8765`

## Performance Considerations

### Non-blocking Operations

All WebSocket operations are non-blocking:
- Events sent asynchronously
- No waiting for send confirmation
- Fire-and-forget pattern for minimal latency

### Connection Pooling

The WebSocketClientProxy maintains a persistent connection:
- Connection established once
- Reused for all events
- Automatic reconnection on failure

### Message Batching

While not currently implemented, the architecture supports:
- Event batching for high-frequency events
- Compression for large payloads
- Priority queuing for critical events

## Security Considerations

### Local-only Binding

The server only binds to localhost:
- Not accessible from network
- No authentication required
- Suitable for local development

### Future Enhancements

For production use, consider:
- TLS/SSL for encrypted connections
- Authentication tokens
- Rate limiting
- Access control lists

## Debugging

### Enable Debug Logging

```python
import logging
logging.getLogger('websocket_server').setLevel(logging.DEBUG)
```

### Monitor Connections

```python
# In production server
logger.info(f"Total clients: {self._total_clients()}")
logger.info(f"Sessions: {list(self.clients.keys())}")
```

### Test Connection

```bash
# Verify server is accessible
python scripts/verify_websocket_connection.py

# Monitor events in real-time
python scripts/monitor_websocket_events.py
```

## Common Issues

### Port Already in Use

```bash
# Kill processes on port 8765
lsof -ti :8765 | xargs kill -9
```

### Connection Refused

- Ensure server is running
- Check firewall settings
- Verify correct port number

### Events Not Appearing

- Check session ID matching
- Verify hook handler has WebSocket access
- Ensure server is receiving events

## Best Practices

1. **Always use 127.0.0.1** instead of localhost
2. **Keep messages small** - truncate large payloads
3. **Handle disconnections gracefully** - auto-reconnect
4. **Use session filtering** to avoid cross-instance pollution
5. **Monitor server health** with periodic checks