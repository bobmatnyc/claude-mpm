# Hook Server Documentation

This document details the WebSocket server implementation that receives and broadcasts hook events.

## Overview

The hook server is a persistent WebSocket server that:
- Receives events from Claude Code hook handlers
- Broadcasts events to connected dashboard clients
- Manages client sessions and connections
- Provides health monitoring and auto-recovery

## Server Architecture

### Core Components

1. **WebSocketServer** - Basic server implementation
2. **WebSocketClientProxy** - Client for connecting to persistent server
3. **Production Server** - Enhanced server with session management
4. **Server Manager** - Process management and auto-restart

### Server Lifecycle

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Manager   │────▶│    Server    │────▶│   Clients   │
│  (Monitor)  │     │  (Port 8765) │     │ (Dashboard) │
└─────────────┘     └──────────────┘     └─────────────┘
```

## Implementation Details

### Basic WebSocket Server

**Location**: `src/claude_mpm/services/websocket_server.py`

```python
class WebSocketServer:
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.clients: Set = set()
        self.event_history: deque = deque(maxlen=1000)
        
    async def handle_client(self, websocket, path):
        self.clients.add(websocket)
        try:
            await websocket.send(json.dumps({
                "type": "welcome",
                "message": "Connected to WebSocket server"
            }))
            
            async for message in websocket:
                # Broadcast to all clients
                websockets.broadcast(self.clients, message)
        finally:
            self.clients.remove(websocket)
```

### Production WebSocket Server

**Location**: `scripts/websocket_server_production.py`

Enhanced features:

```python
class WebSocketServer:
    def __init__(self):
        # Session-based client management
        self.clients: Dict[str, Set[websockets.WebSocketServerProtocol]] = {}
        
    async def register_client(self, websocket, session_id: Optional[str] = None):
        if session_id is None:
            session_id = "global"
            
        if session_id not in self.clients:
            self.clients[session_id] = set()
            
        self.clients[session_id].add(websocket)
        
    async def broadcast(self, message: dict, session_id: Optional[str] = None):
        if session_id and session_id in self.clients:
            # Send to specific session
            await self._broadcast_to_clients(self.clients[session_id], message)
        else:
            # Send to all clients
            all_clients = set()
            for clients in self.clients.values():
                all_clients.update(clients)
            await self._broadcast_to_clients(all_clients, message)
```

### Server Manager

**Location**: `scripts/websocket_server_manager.py`

Auto-restart and monitoring:

```python
def monitor_server(process):
    restart_count = 0
    max_restarts = 5
    
    while restart_count < max_restarts:
        if process.poll() is None:
            # Server running - check health
            pass
        else:
            # Server stopped - restart
            restart_count += 1
            process = start_server()
```

## Starting the Server

### Manual Start

```bash
# Basic server
python scripts/websocket_server_production.py

# With manager (auto-restart)
python scripts/websocket_server_manager.py
```

### Automatic Start

The server starts automatically when:
1. Running `claude-mpm run --manager`
2. First WebSocket client connects

### Process Management

```bash
# Check if server is running
ps aux | grep websocket.*8765

# Stop server
lsof -ti :8765 | xargs kill -9

# View server logs
tail -f /tmp/websocket_manager.log
```

## Client Connection

### Registration Protocol

Clients should register with a session ID:

```javascript
ws.onopen = () => {
    ws.send(JSON.stringify({
        type: 'register',
        session_id: 'your-session-id'
    }));
};
```

### Message Format

All messages follow this structure:

```json
{
    "type": "event.type",
    "timestamp": "2025-07-31T12:00:00.000Z",
    "data": {
        // Event-specific data
    }
}
```

## Health Monitoring

### Automatic Health Checks

The production server performs health checks every 30 seconds:

```python
async def health_check(self):
    while self.running:
        await asyncio.sleep(30)
        
        # Log server status
        logger.info(f"Server health: {self._total_clients()} clients")
        
        # Send heartbeat
        await self.broadcast({
            "type": "system.heartbeat",
            "data": {"clients": self._total_clients()}
        })
```

### Connection Monitoring

WebSocket ping/pong for connection health:

```python
async with websockets.serve(
    self.handle_client,
    self.host,
    self.port,
    ping_interval=20,  # Send ping every 20 seconds
    ping_timeout=10    # Timeout after 10 seconds
)
```

## Error Handling

### Graceful Degradation

1. **Connection Errors**: Auto-reconnect with backoff
2. **Send Errors**: Silently drop failed messages
3. **Client Errors**: Remove from broadcast list
4. **Server Errors**: Manager restarts server

### Error Recovery

```python
try:
    await websocket.send(message)
except websockets.exceptions.ConnectionClosed:
    # Remove dead client
    clients.remove(websocket)
except Exception as e:
    logger.error(f"Send error: {e}")
    # Continue with other clients
```

## Performance Optimization

### Async Operations

All I/O operations are asynchronous:

```python
# Broadcast to multiple clients concurrently
tasks = [client.send(message) for client in clients]
await asyncio.gather(*tasks, return_exceptions=True)
```

### Message Batching

While not implemented, the architecture supports:

```python
# Future enhancement
message_queue = asyncio.Queue()
batch = []

while True:
    message = await message_queue.get()
    batch.append(message)
    
    if len(batch) >= 10 or time_elapsed > 100ms:
        await broadcast_batch(batch)
        batch.clear()
```

## Security Considerations

### Current Security

- Local-only binding (127.0.0.1)
- No external network access
- No authentication (local trust)

### Production Recommendations

For production deployment:

1. **TLS/SSL**: Use `wss://` instead of `ws://`
2. **Authentication**: Add token-based auth
3. **Rate Limiting**: Prevent DoS attacks
4. **Access Control**: IP whitelisting

## Troubleshooting

### Server Won't Start

```bash
# Check if port is in use
lsof -i :8765

# Kill existing processes
lsof -ti :8765 | xargs kill -9

# Check for errors
python scripts/websocket_server_production.py
```

### Clients Can't Connect

1. **Check server is running**: `ps aux | grep websocket`
2. **Verify port**: Default is 8765
3. **Use 127.0.0.1**: Not localhost (IPv6 issues)
4. **Check firewall**: Ensure port is open

### Events Not Broadcasting

1. **Check session IDs**: Must match between sender and receiver
2. **Verify connection**: Client must be registered
3. **Check message format**: Must be valid JSON

## Monitoring

### Server Metrics

```python
# Total connected clients
total_clients = sum(len(clients) for clients in self.clients.values())

# Active sessions
active_sessions = list(self.clients.keys())

# Events per second
events_per_second = event_count / time_elapsed
```

### Debug Logging

```python
# Enable debug logging
import logging
logging.getLogger('websocket_server').setLevel(logging.DEBUG)

# Log all events
logger.debug(f"Received: {message}")
logger.debug(f"Broadcasting to {len(clients)} clients")
```

## Best Practices

1. **Use persistent server**: Don't create new servers per session
2. **Handle disconnections**: Clients should auto-reconnect
3. **Limit message size**: Truncate large payloads
4. **Use session filtering**: Prevent cross-contamination
5. **Monitor health**: Check server status periodically
6. **Graceful shutdown**: Handle SIGTERM properly