# System Heartbeat Events

## Overview

The MPM Socket.IO server now includes a system heartbeat event that sends status updates every 60 seconds. This provides real-time server health monitoring and session tracking independent of hook events.

## Features

### System Event Channel
- **Event Type**: `system_event` (separate from `claude_event`)
- **Event Name**: `heartbeat`
- **Frequency**: Every 60 seconds (configurable)
- **Purpose**: Verify event flow and monitor server health

### Heartbeat Data Format

```json
{
  "type": "system",
  "event": "heartbeat",
  "timestamp": "2024-01-17T12:00:00Z",
  "data": {
    "uptime_seconds": 3600,
    "connected_clients": 2,
    "total_events": 150,
    "active_sessions": [
      {
        "session_id": "session_123",
        "start_time": "2024-01-17T11:00:00Z",
        "agent": "engineer",
        "status": "active",
        "last_activity": "2024-01-17T12:00:00Z"
      }
    ],
    "server_info": {
      "version": "4.0.2",
      "port": 8765
    }
  }
}
```

## Session Tracking

The heartbeat system tracks active MPM sessions from multiple sources:

### Direct API Calls
- `session_started()` - Creates new session
- `agent_delegated()` - Updates session agent
- `session_ended()` - Removes session

### Hook Events
The system also tracks sessions from hook events:
- `user_prompt` - Creates PM session
- `pre_tool` (Task) - Updates delegation
- `subagent_start` - Tracks agent session
- `subagent_stop` - Marks session complete

## Implementation Details

### Architecture
1. **Core Server** (`core.py`): Contains heartbeat loop
2. **Main Server** (`main.py`): Manages session tracking
3. **Broadcaster** (`broadcaster.py`): Handles event emission
4. **Hook Handler** (`handlers/hook.py`): Processes hook events

### Key Components

#### Heartbeat Loop
- Runs asynchronously in the core server
- Sends heartbeat every 60 seconds
- Includes server stats and active sessions
- Continues even if individual heartbeats fail

#### Session Management
- Sessions tracked in `active_sessions` dictionary
- Automatic cleanup of sessions older than 1 hour
- Session states: `active`, `delegated`, `completed`

## Testing

### Test Scripts

1. **Basic Monitor** (`scripts/test_heartbeat.py`)
   - Connects as client and displays heartbeats
   - Shows session information and server stats

2. **Combined Test** (`scripts/test_heartbeat_combined.py`)
   - Starts server and client together
   - Creates test sessions
   - Verifies heartbeat functionality

3. **Hook Integration** (`scripts/test_heartbeat_hooks.py`)
   - Simulates hook events
   - Verifies session tracking from hooks
   - Tests complete session lifecycle

### Running Tests

```bash
# Monitor heartbeats from running server
python scripts/test_heartbeat.py

# Run combined server/client test
python scripts/test_heartbeat_combined.py

# Test hook event integration
python scripts/test_heartbeat_hooks.py
```

## Configuration

### Heartbeat Interval
Default: 60 seconds

To customize (in code):
```python
server = SocketIOServer()
server.core.heartbeat_interval = 30  # 30 seconds
```

### Debugging
Heartbeat events are logged at INFO level:
```
System heartbeat sent - clients: 2, uptime: 3600s, events: 150, sessions: 3
```

## Dashboard Integration

The dashboard can subscribe to system events:

```javascript
socket.on('system_event', (data) => {
  if (data.type === 'system' && data.event === 'heartbeat') {
    // Update UI with heartbeat data
    updateServerHealth(data.data);
    updateActiveSessions(data.data.active_sessions);
  }
});
```

## Benefits

1. **Health Monitoring**: Regular heartbeats confirm server is responsive
2. **Session Visibility**: Track all active MPM sessions in real-time
3. **Event Flow Verification**: Confirm Socket.IO broadcasting works
4. **Independent Channel**: System events separate from hook events
5. **Debugging Aid**: Heartbeat data helps diagnose issues

## Future Enhancements

Potential improvements for the heartbeat system:

1. **Metrics Collection**: Add CPU, memory, and performance metrics
2. **Alert Thresholds**: Trigger alerts when metrics exceed limits
3. **Historical Data**: Store heartbeat history for analysis
4. **Client Heartbeats**: Two-way heartbeats for connection monitoring
5. **Custom Events**: Allow plugins to add data to heartbeats