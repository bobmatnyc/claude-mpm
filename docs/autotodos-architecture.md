# AutoTodos Event-Driven Architecture

## Overview

The autotodos system converts hook errors into actionable todos for the PM using an event-driven architecture. This document explains the design, data flow, and usage.

## Architecture

```
Hook Error Detected
    ↓
[HookManager] Detects error via error_memory
    ↓
Publish Event: "autotodo.error"
    ├─→ [EventLog] Persistent storage (.claude-mpm/event_log.json)
    └─→ [EventBus] Real-time listeners (Socket.IO, dashboard)
    ↓
[Autotodos CLI] Reads from EventLog
    ↓
Formats as todos for PM
```

## Components

### 1. EventLog Service (`src/claude_mpm/services/event_log.py`)

Simple JSON-based persistent event storage.

**Features:**
- Stores events with timestamp, type, payload, status
- Supports filtering by event type and status
- Message truncation (max 2000 chars) to prevent file bloat
- Mark events as resolved
- Clear resolved events

**Storage Location:** `.claude-mpm/event_log.json`

**Event Structure:**
```json
{
  "id": "2026-01-08T03:45:24.330830+00:00",
  "timestamp": "2026-01-08T03:45:24.330830+00:00",
  "event_type": "autotodo.error",
  "status": "pending",
  "payload": {
    "error_type": "command_not_found",
    "hook_type": "PreToolUse",
    "details": "missing-command",
    "full_message": "Error: command not found: missing-command",
    "suggested_fix": "Install the missing command",
    "source": "hook_manager"
  }
}
```

### 2. HookManager Integration (`src/claude_mpm/core/hook_manager.py`)

**Changes:**
- Added `_publish_error_event()` method
- Publishes to EventLog when error detected
- Also publishes to EventBus for real-time notifications

**When Events Are Published:**
- After error detection in `_execute_hook_sync()`
- After error memory records the error
- Before logging the error suggestion

### 3. Autotodos CLI (`src/claude_mpm/cli/commands/autotodos.py`)

**Refactored from hook_errors.json to event_log:**
- Reads pending events from EventLog
- Formats events as PM-compatible todos
- Marks events as resolved when cleared

**Commands:**

```bash
# Show status
claude-mpm autotodos status

# List pending todos
claude-mpm autotodos list
claude-mpm autotodos list --format json

# Inject into PM session
claude-mpm autotodos inject
claude-mpm autotodos inject --output todos.json

# Clear after resolution
claude-mpm autotodos clear
claude-mpm autotodos clear --event-id ID
claude-mpm autotodos clear -y  # Skip confirmation
```

## Data Flow

### Error Detection → Event Publishing

1. **Hook executes** via HookManager background processor
2. **Error detected** by HookErrorMemory pattern matching
3. **Error recorded** in memory (for skip logic)
4. **Event published** to EventLog (persistent) and EventBus (real-time)
5. **Error logged** with suggestion

### Event Consumption → Todo Generation

1. **CLI invoked** (`claude-mpm autotodos list`)
2. **Events retrieved** from EventLog (status=pending)
3. **Events formatted** as PM-compatible todos
4. **Todos displayed** or injected into PM session

### Resolution Flow

1. **PM delegates** error to appropriate agent
2. **Agent fixes** the error
3. **PM or user runs** `claude-mpm autotodos clear`
4. **Events marked resolved** in EventLog
5. **Events removed** from autotodos list

## Benefits

### Over Previous hook_errors.json Approach

1. **Clean Separation:** Event producers don't know about consumers
2. **Multiple Consumers:** EventLog + EventBus support CLI, dashboard, notifications
3. **Status Tracking:** Pending/resolved/archived states
4. **Audit Trail:** Full history of all errors with timestamps
5. **Extensibility:** Easy to add new event types and consumers

### Design Decisions

**Why EventLog over Database?**
- Simple, human-readable JSON
- No additional dependencies
- Fast for small event volumes
- Easy to inspect and clear manually
- Follows existing patterns (hook_error_memory)

**Why Keep HookErrorMemory?**
- Different purpose: skip logic for repeated failures
- Fast in-memory checks (no I/O)
- Complements EventLog (detection vs. tracking)

**Why Publish to Both EventLog and EventBus?**
- EventLog: Persistent storage for CLI consumption
- EventBus: Real-time notifications for dashboard
- Decoupled: Each consumer gets what it needs

## Migration from hook_errors.json

**Before:**
```python
# autotodos.py
from claude_mpm.core.hook_error_memory import get_hook_error_memory

error_memory = get_hook_error_memory()
for error_key, error_data in error_memory.errors.items():
    if error_data["count"] >= 2:
        todo = format_error_as_todo(error_key, error_data)
```

**After:**
```python
# autotodos.py
from claude_mpm.services.event_log import get_event_log

event_log = get_event_log()
pending_events = event_log.list_events(event_type="autotodo.error", status="pending")
for event in pending_events:
    todo = format_error_event_as_todo(event)
```

## Testing

Run the autotodos tests:

```bash
# Test CLI commands
python -m claude_mpm.cli autotodos status
python -m claude_mpm.cli autotodos list
python -m claude_mpm.cli autotodos inject

# Verify event log
cat .claude-mpm/event_log.json
```

## Future Enhancements

1. **Event Types:** Add more event types (success, warning, info)
2. **Real-Time Dashboard:** Subscribe to EventBus for live updates
3. **Event Retention:** Auto-archive old events
4. **Event Analytics:** Track error trends over time
5. **Event Export:** Export events to external systems

## Related Files

- `src/claude_mpm/services/event_log.py` - EventLog service
- `src/claude_mpm/core/hook_manager.py` - Event publishing
- `src/claude_mpm/cli/commands/autotodos.py` - Event consumption
- `src/claude_mpm/services/event_bus/event_bus.py` - Real-time EventBus
- `.claude-mpm/event_log.json` - Event storage
