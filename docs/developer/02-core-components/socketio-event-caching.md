# Socket.IO Event Caching

## Overview

The Socket.IO server implements an event caching mechanism that stores the last 50-100 events and automatically sends them to new dashboard clients when they connect. This ensures that users see recent activity immediately upon opening the dashboard, providing context for the current session state.

## How It Works

### Event Storage

1. **Event History Buffer**: The server maintains a circular buffer (`deque`) with a maximum size defined by `SystemLimits.MAX_EVENTS_BUFFER` (default: 1000 events)

2. **Automatic Storage**: All events broadcast through the system are automatically added to the event history:
   - Events sent via `SocketIOEventBroadcaster.broadcast_event()`
   - Hook events processed by the `HookEventHandler`
   - System events like heartbeats

3. **Event Structure**: Each cached event follows this structure:
```python
{
    "type": "hook" | "session_started" | "agent_delegated" | ...,
    "timestamp": "2025-01-17T10:30:00.123456",
    "data": {
        # Event-specific data
    }
}
```

### Client Connection Flow

When a new dashboard client connects:

1. **Connection Handler** (`ConnectionEventHandler`) processes the connection
2. **Initial Messages** sent to the client:
   - Status message with server info
   - Welcome message with client ID
3. **Event History** automatically sent (last 50 events by default)
4. **Real-time Streaming** begins for new events

### Implementation Details

#### Server-Side Components

**Main Server** (`SocketIOServer` in `server/main.py`):
- Maintains the `event_history` deque
- Shares reference with broadcaster for event storage

**Event Broadcaster** (`SocketIOEventBroadcaster` in `server/broadcaster.py`):
- Adds all broadcast events to event history
- Ensures consistent event structure

**Connection Handler** (`ConnectionEventHandler` in `handlers/connection.py`):
- Sends cached events on client connection
- Handles history requests with filtering

**Core Server** (`SocketIOServerCore` in `server/core.py`):
- Adds system events (heartbeats) to history

#### Client-Side Handling

Dashboard clients receive history via the `history` event:
```javascript
socket.on('history', (data) => {
    // data.events: Array of historical events
    // data.count: Number of events in this batch
    // data.total_available: Total events available on server
    
    // Process events to update UI
    data.events.forEach(event => {
        processHistoricalEvent(event);
    });
});
```

## Configuration

### Buffer Size

The maximum number of events stored is configured via `SystemLimits.MAX_EVENTS_BUFFER`:
```python
# In core/constants.py
class SystemLimits:
    MAX_EVENTS_BUFFER = 1000  # Maximum events to store
```

### History Send Limit

By default, the last 50 events are sent to new clients. This can be adjusted in the connection handler:
```python
# In handlers/connection.py
await self._send_event_history(sid, limit=50)  # Adjust limit as needed
```

## Testing

Three comprehensive test scripts validate the event caching functionality:

1. **Basic Caching Test** (`scripts/test_event_caching.py`):
   - Tests basic event storage and retrieval
   - Verifies chronological ordering
   - Confirms real-time events continue working

2. **Dashboard Simulation** (`scripts/test_dashboard_event_cache.py`):
   - Simulates 60+ events (exceeds 50 event limit)
   - Verifies last 50 events are sent
   - Tests various event types

3. **Hook Integration** (`scripts/test_hook_event_caching.py`):
   - Tests hook event caching specifically
   - Verifies integration with HookManager
   - Confirms event structure preservation

Run tests with:
```bash
python scripts/test_event_caching.py
python scripts/test_dashboard_event_cache.py
python scripts/test_hook_event_caching.py
```

## Benefits

1. **Immediate Context**: Users see recent activity instantly upon connecting
2. **Session Recovery**: Can understand what happened before joining
3. **Debugging Aid**: Historical events help diagnose issues
4. **User Experience**: No blank dashboard on initial load

## Limitations

1. **Memory Usage**: Large event buffers consume memory
2. **Event Size**: Very large events may impact performance
3. **Persistence**: Events are not persisted across server restarts

## Future Enhancements

Potential improvements for the event caching system:

1. **Persistent Storage**: Save events to disk for recovery after restart
2. **Event Filtering**: Send only relevant events based on client preferences
3. **Compression**: Compress old events to save memory
4. **Time-based Cleanup**: Remove events older than X minutes
5. **Event Prioritization**: Keep important events longer than routine ones