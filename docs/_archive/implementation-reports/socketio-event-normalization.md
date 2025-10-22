# Socket.IO Event Normalization Implementation

## Overview

This document describes the Socket.IO event model consistency fixes implemented to ensure all events follow a normalized schema throughout the claude-mpm system.

## Normalized Event Schema

All events are now normalized to the following consistent schema before being emitted:

```json
{
  "event": "claude_event",
  "type": "hook|system|file|etc",  
  "subtype": "specific_event",
  "timestamp": "ISO format",
  "data": { ... }
}
```

## Key Components Modified

### 1. EventNormalizer (`src/claude_mpm/services/socketio/event_normalizer.py`)

- Central class for normalizing all events to consistent schema
- Handles various input formats (legacy, string, dictionary)
- Maps event names to type/subtype categorization
- Provides backward compatibility for legacy event formats

### 2. Hook Handler (`src/claude_mpm/hooks/claude_hooks/hook_handler.py`)

- Added EventNormalizer instance to the handler
- Modified `_emit_socketio_event` to normalize all events before emission
- All events now go through normalization pipeline
- Maintains backward compatibility with fallback normalizer

### 3. Event Handlers (`src/claude_mpm/hooks/claude_hooks/event_handlers.py`)

- Removed namespace concatenation (was "/hook", now "")
- Events are emitted without namespace as they're normalized
- Cleaner event emission without hardcoded namespaces

### 4. Socket.IO Broadcaster (`src/claude_mpm/services/socketio/server/broadcaster.py`)

- Already uses EventNormalizer for all broadcast events
- Ensures consistent schema for all server-side emissions
- Handles retry logic with normalized events

### 5. Dashboard Client (`src/claude_mpm/dashboard/static/js/socket-client.js`)

- Added schema validation for incoming events
- `validateEventSchema` method ensures all required fields
- Provides defaults for missing fields
- Maintains backward compatibility with transformation

### 6. Event Viewer (`src/claude_mpm/dashboard/static/js/components/event-viewer.js`)

- Already handles type/subtype filtering correctly
- `formatEventType` combines type and subtype for display
- Filtering works with normalized event structure

## Event Categories

The system now uses these main event categories:

- **HOOK**: Claude Code hook events
- **SYSTEM**: System health and status events  
- **SESSION**: Session lifecycle events
- **FILE**: File system events
- **CONNECTION**: Client connection events
- **MEMORY**: Memory system events
- **GIT**: Git operation events
- **TODO**: Todo list updates
- **TICKET**: Ticket system events
- **AGENT**: Agent delegation events
- **ERROR**: Error events
- **PERFORMANCE**: Performance metrics
- **CLAUDE**: Claude process events
- **TEST**: Test events
- **TOOL**: Tool events
- **SUBAGENT**: Subagent events

## Testing

Two comprehensive test scripts verify the implementation:

1. **`scripts/test_normalized_event_flow.py`**
   - Tests EventNormalizer directly
   - Verifies hook handler integration
   - Tests Socket.IO connection and event reception

2. **`scripts/test_hook_event_normalization.py`**
   - Simulates actual Claude Code hook events
   - Verifies end-to-end normalization
   - Tests various event types

## Benefits

1. **Consistency**: All events follow the same schema
2. **Reliability**: Schema validation catches malformed events
3. **Backward Compatibility**: Legacy events are transformed
4. **Maintainability**: Single normalization point
5. **Debugging**: Easier to trace and filter events
6. **Extensibility**: Easy to add new event types

## Migration Notes

- Existing code using legacy event formats will continue to work
- The EventNormalizer handles transformation automatically
- Dashboard filters work with both old and new formats
- No breaking changes for existing integrations

## Future Improvements

1. Add event type discovery endpoint
2. Implement event schema documentation generator
3. Add metrics for normalization performance
4. Consider event compression for high-volume scenarios
5. Add event replay functionality for debugging