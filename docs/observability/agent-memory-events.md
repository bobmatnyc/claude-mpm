# Agent Memory Event Observability

## Overview

Agent memory loading events are now observable through the claude-mpm EventBus. This allows you to monitor when agents load their accumulated knowledge at runtime.

## Event Type

**Event Name:** `agent.memory.loaded`

**Event Data:**
```python
{
    "agent_id": str,        # Agent identifier (e.g., "engineer", "qa")
    "memory_source": str,   # Source of memory: "runtime"
    "memory_size": int,     # Size of loaded memory in bytes
    "timestamp": str        # ISO 8601 timestamp
}
```

## How to Observe Events

### Method 1: Register an Event Handler

```python
from claude_mpm.services.event_bus.event_bus import EventBus

# Get EventBus instance
bus = EventBus.get_instance()

# Define your handler
def memory_loaded_handler(data):
    agent_id = data["agent_id"]
    size = data["memory_size"]
    print(f"Agent '{agent_id}' loaded {size} bytes of memory")

# Register handler
bus.on("agent.memory.loaded", memory_loaded_handler)
```

### Method 2: Use Wildcard Handlers

```python
# Listen to all agent.* events
def agent_event_handler(event_type, data):
    print(f"Agent Event: {event_type}")
    print(f"Data: {data}")

bus.on("agent.*", agent_event_handler)
```

### Method 3: View EventBus Statistics

```python
# Get statistics
stats = bus.get_stats()
print(f"Events published: {stats['events_published']}")

# Get recent events
recent = bus.get_recent_events(limit=10)
for event in recent:
    print(f"{event['timestamp']}: {event['type']}")
```

## Implementation Details

### When Events Are Emitted

Events are emitted in `MemoryPreDelegationHook.execute()` when:
1. Memory manager is available
2. Agent memory is successfully loaded
3. Memory content is non-empty

### Event Flow

```
Agent Delegation Request
  ↓
MemoryPreDelegationHook.execute()
  ↓
Load agent memory from storage
  ↓
Emit "agent.memory.loaded" event ← Observability point
  ↓
Inject memory into delegation context
  ↓
Continue with delegation
```

## Use Cases

1. **Monitoring**: Track which agents are loading memory and how much
2. **Analytics**: Measure memory usage patterns across agents
3. **Debugging**: Verify memory is being loaded correctly
4. **Metrics**: Build dashboards showing memory loading trends

## Example: Logging Handler

```python
import logging
from claude_mpm.services.event_bus.event_bus import EventBus

logger = logging.getLogger(__name__)

def log_memory_events(data):
    logger.info(
        "Agent memory loaded",
        extra={
            "agent_id": data["agent_id"],
            "memory_source": data["memory_source"],
            "memory_size": data["memory_size"],
            "timestamp": data["timestamp"]
        }
    )

bus = EventBus.get_instance()
bus.on("agent.memory.loaded", log_memory_events)
```

## Event vs SocketIO

The codebase emits both EventBus events and legacy SocketIO events:

- **EventBus** (`agent.memory.loaded`): New, preferred method for in-process observability
- **SocketIO** (`memory_injected`): Legacy method for web UI integration

Both are maintained for backward compatibility.

## Related Files

- **Event Emission**: `/src/claude_mpm/hooks/memory_integration_hook.py` (lines 165-179)
- **EventBus Implementation**: `/src/claude_mpm/services/event_bus/event_bus.py`
- **Memory Manager**: `/src/claude_mpm/services/agents/memory/`

## Migration Notes

This replaces the previous deployment-time memory injection approach where memory was appended to agent markdown files. The new runtime approach:

1. ✅ More flexible - memory loaded fresh for each delegation
2. ✅ Observable - events track when/what is loaded
3. ✅ Cleaner - separates deployment from runtime concerns
4. ✅ Testable - event bus enables easy testing
