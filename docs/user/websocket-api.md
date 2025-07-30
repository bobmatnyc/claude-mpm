# WebSocket API

The Claude MPM WebSocket API provides real-time monitoring of Claude sessions, including process status, agent delegations, todo updates, and more.

## Quick Start

1. Enable WebSocket server when running claude-mpm:
   ```bash
   claude-mpm --websocket --launch-method subprocess
   ```

2. Connect to the WebSocket server at `ws://localhost:8765`

3. Open the included HTML monitor:
   ```bash
   open scripts/websocket_monitor.html
   ```

## Command Line Usage

### Enable WebSocket Server

```bash
# With subprocess launcher (recommended for full features)
claude-mpm --websocket --launch-method subprocess

# With exec launcher (limited monitoring)
claude-mpm --websocket
```

### Test WebSocket Connection

```bash
# Run the test client
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

## Notes

- WebSocket monitoring is most effective with `--launch-method subprocess`
- In exec mode, monitoring stops when Claude takes over the process
- Default port is 8765 (not configurable in current version)