# WebSocket API

The Claude MPM WebSocket API provides real-time monitoring of Claude sessions, including process status, agent delegations, todo updates, and more.

## Quick Start

1. Enable WebSocket server when running claude-mpm:
   ```bash
   # Default port (8765)
   claude-mpm --websocket --launch-method subprocess
   
   # Custom port
   claude-mpm --websocket --websocket-port 8766 --launch-method subprocess
   ```

2. Connect to the WebSocket server at `ws://localhost:PORT`

3. Open the included HTML monitor:
   ```bash
   open scripts/websocket_monitor.html
   ```

## Command Line Usage

### Enable WebSocket Server

```bash
# With subprocess launcher (recommended for full features)
claude-mpm --websocket --launch-method subprocess

# With custom port
claude-mpm --websocket --websocket-port 8766 --launch-method subprocess

# With exec launcher (limited monitoring)
claude-mpm --websocket
```

### Managing Multiple Instances

```bash
# Find available port
python scripts/find_websocket_port.py

# Check if specific port is available
python scripts/find_websocket_port.py 8766

# Run multiple instances on different ports
claude-mpm --websocket --websocket-port 8765  # Instance 1
claude-mpm --websocket --websocket-port 8766  # Instance 2
claude-mpm --websocket --websocket-port 8767  # Instance 3
```

### Test WebSocket Connection

```bash
# Test default port
python scripts/test_websocket_quick.py

# Test specific port
python scripts/test_websocket_quick.py 8766

# Monitor with full client
python scripts/test_websocket.py
```

## WebSocket Events

### Session Events
- `session.start` - Session begins
- `session.end` - Session ends

### Claude Process Events  
- `claude.status` - Status changes (starting, running, stopped, error)
- `claude.output` - Real-time output from Claude

### Agent Events
- `agent.delegation` - Agent task delegation detected
- `agent.status` - Agent activity status

### Todo Events
- `todo.update` - Todo list changes

### System Events
- `system.status` - System status update
- `system.error` - Error notifications

## Example Clients

### Python Client
```python
import asyncio
import json
import websockets

async def monitor():
    async with websockets.connect("ws://localhost:8765") as ws:
        # Subscribe to all events
        await ws.send(json.dumps({
            "command": "subscribe", 
            "channels": ["*"]
        }))
        
        # Listen for events
        async for message in ws:
            event = json.loads(message)
            print(f"{event['type']}: {event['data']}")

asyncio.run(monitor())
```

### JavaScript Client
```javascript
const ws = new WebSocket('ws://localhost:8765');

ws.onopen = () => {
    ws.send(JSON.stringify({
        command: 'subscribe',
        channels: ['*']
    }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log(data.type, data.data);
};
```

## Integration with claude-mpm-portfolio-manager

The WebSocket API is designed to integrate with the claude-mpm-portfolio-manager dashboard for comprehensive session monitoring and management.

## Instance Identification

Each WebSocket server provides instance information in its events:

```json
{
  "type": "session.start",
  "data": {
    "session_id": "uuid",
    "websocket_port": 8765,
    "instance_info": {
      "port": 8765,
      "host": "localhost",
      "working_dir": "/path/to/project"
    }
  }
}
```

This allows clients to:
- Connect to multiple instances simultaneously
- Display which instance each event comes from
- Route commands to specific instances

## Notes

- WebSocket monitoring is most effective with `--launch-method subprocess`
- In exec mode, monitoring stops when Claude takes over the process
- Default port is 8765, but can be configured with `--websocket-port`
- Each instance must use a unique port