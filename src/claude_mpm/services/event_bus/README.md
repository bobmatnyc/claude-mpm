# EventBus Service

A decoupled event handling system for claude-mpm that enables loose coupling between event producers (like hooks) and consumers (like Socket.IO).

## Overview

The EventBus service provides a centralized publish-subscribe system that:
- Decouples event producers from consumers
- Supports both synchronous and asynchronous handlers
- Provides event filtering and routing capabilities
- Isolates failures in individual consumers
- Offers comprehensive monitoring and statistics

## Architecture

```
Hook Handler → EventBus → Multiple Consumers
                         ├── Socket.IO Relay
                         ├── Logging Service
                         ├── Analytics
                         └── Custom Handlers
```

## Key Components

### EventBus (`event_bus.py`)
- Singleton pattern for centralized event coordination
- Thread-safe event publishing from any context
- Support for wildcard subscriptions (`hook.*`)
- Event filtering and routing
- Built-in statistics and history tracking

### SocketIORelay (`relay.py`)
- Consumes events from EventBus
- Relays to Socket.IO clients
- Handles connection failures gracefully
- Single point of Socket.IO management

### Configuration (`config.py`)
- Environment variable support
- Runtime configuration changes
- Easy testing with different settings

## Installation

The EventBus requires `pyee` (Python EventEmitter):

```bash
pip install pyee>=13.0.0
```

## Usage

### Basic Publishing

```python
from claude_mpm.services.event_bus import EventBus

# Get singleton instance
event_bus = EventBus.get_instance()

# Publish an event
event_bus.publish("hook.pre_tool", {
    "tool_name": "Read",
    "file_path": "/example.py",
    "sessionId": "abc-123"
})
```

### Subscribing to Events

```python
# Subscribe to specific event
def handle_pre_tool(data):
    print(f"Tool: {data.get('tool_name')}")

event_bus.on("hook.pre_tool", handle_pre_tool)

# Subscribe to wildcard pattern
def handle_all_hooks(event_type, data):
    print(f"Hook event: {event_type}")

event_bus.on("hook.*", handle_all_hooks)
```

### Async Handlers

```python
async def async_handler(data):
    await process_async(data)

event_bus.on("app.async_event", async_handler)
```

### Event Filtering

```python
# Only allow specific events
event_bus.add_filter("hook.*")
event_bus.add_filter("system.critical.*")

# Events outside filters will be dropped
event_bus.publish("app.user_action", {})  # Filtered out
```

### Socket.IO Integration

```python
from claude_mpm.services.event_bus import SocketIORelay

# Create and start relay
relay = SocketIORelay(port=8765)
relay.start()

# Events published to EventBus will be relayed to Socket.IO
event_bus.publish("hook.subagent_stop", {
    "agent_type": "Engineer",
    "result": "Success"
})
```

## Configuration

Configure via environment variables:

```bash
# EventBus settings
export CLAUDE_MPM_EVENTBUS_ENABLED=true
export CLAUDE_MPM_EVENTBUS_DEBUG=false
export CLAUDE_MPM_EVENTBUS_HISTORY_SIZE=100
export CLAUDE_MPM_EVENTBUS_FILTERS="hook.*,system.critical.*"

# Relay settings
export CLAUDE_MPM_RELAY_ENABLED=true
export CLAUDE_MPM_SOCKETIO_PORT=8765
export CLAUDE_MPM_RELAY_DEBUG=false
export CLAUDE_MPM_RELAY_MAX_RETRIES=3
```

## Migration from Direct Socket.IO

### Before (Direct Socket.IO)
```python
# In hook_handler.py
client = socketio.Client()
client.connect("http://localhost:8765")
client.emit("claude_event", normalized_data)
```

### After (EventBus)
```python
# In hook_handler.py
event_bus = EventBus.get_instance()
event_bus.publish("hook.pre_tool", data)

# Socket.IO handled by relay (separate concern)
```

## Benefits

1. **Decoupling**: Hooks don't need to know about Socket.IO
2. **Testability**: Easy to test without Socket.IO running
3. **Reliability**: Failures in one consumer don't affect others
4. **Flexibility**: Add new consumers without modifying producers
5. **Performance**: Events processed asynchronously
6. **Monitoring**: Built-in statistics and event history

## Testing

Run the test suite:

```bash
# Integration tests
python scripts/test_eventbus_integration.py

# Usage examples
python scripts/eventbus_usage_example.py

# Complete flow test
python scripts/test_eventbus_flow.py
```

## Monitoring

Get EventBus statistics:

```python
stats = event_bus.get_stats()
print(f"Events published: {stats['events_published']}")
print(f"Events filtered: {stats['events_filtered']}")

# Recent event history
recent = event_bus.get_recent_events(10)
for event in recent:
    print(f"{event['type']} at {event['timestamp']}")
```

## Error Handling

Errors in consumers are isolated:

```python
def good_handler(data):
    process(data)  # Always runs

def bad_handler(data):
    raise Exception("Error")  # Doesn't affect good_handler

event_bus.on("app.event", good_handler)
event_bus.on("app.event", bad_handler)
```

## Performance

- Handles 30,000+ events/second
- Minimal memory overhead
- Thread-safe for concurrent publishing
- Efficient wildcard matching

## Troubleshooting

### Events not being received
1. Check if EventBus is enabled: `CLAUDE_MPM_EVENTBUS_ENABLED=true`
2. Verify no filters are blocking: `event_bus.clear_filters()`
3. Check handler registration: `event_bus.on("event_type", handler)`

### Socket.IO relay not working
1. Verify Socket.IO server is running on configured port
2. Check relay is started: `relay.start()`
3. Enable debug logging: `CLAUDE_MPM_RELAY_DEBUG=true`

### High memory usage
1. Reduce history size: `CLAUDE_MPM_EVENTBUS_HISTORY_SIZE=50`
2. Clear history periodically: `event_bus.clear_history()`

## Future Enhancements

- [ ] Persistent event storage
- [ ] Event replay capabilities
- [ ] Advanced routing rules
- [ ] Event prioritization
- [ ] Distributed EventBus (Redis backend)
- [ ] Event schema validation
- [ ] Rate limiting per consumer