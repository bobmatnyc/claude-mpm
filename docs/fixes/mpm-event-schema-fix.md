# MPM Hook Event Schema Fix

## Summary

Fixed the MPM hook event schema to use correct field values for event emission.

## Problem

Hook execution events were using incorrect schema values:

```json
{
  "event": "claude_event",      ❌ Wrong event name
  "source": "mpm_hook",
  "type": "hook",                ❌ Generic type instead of actual hook
  "subtype": "execution",
  ...
}
```

## Solution

Updated the schema to use correct values:

```json
{
  "event": "mpm_event",          ✅ Correct event name
  "source": "mpm_hook",
  "type": "UserPromptSubmit",    ✅ Actual hook type
  "subtype": "execution",
  ...
}
```

## Changes Made

### 1. Event Name: "claude_event" → "mpm_event"

**Files Modified:**
- `src/claude_mpm/services/socketio/event_normalizer.py`
  - Updated `NormalizedEvent` dataclass default: `event: str = "mpm_event"`
  - Updated all `NormalizedEvent` instantiations in `normalize()` method
  - Updated fallback error event creation
  - Updated `_validate_normalized()` method
  - Updated module docstring

- `src/claude_mpm/hooks/claude_hooks/services/connection_manager.py`
  - Updated `emit()` call: `self.connection_pool.emit("mpm_event", claude_event_data)`
  - Updated fallback `EventNormalizer` class

**Rationale:** Events from MPM hooks should be identified as "mpm_event" not "claude_event" to distinguish them from Claude Code's internal events.

### 2. Type Field: "hook" → "<hook_name>" for hook_execution events

**Files Modified:**
- `src/claude_mpm/hooks/claude_hooks/services/connection_manager.py`
  - Added logic in `emit_event()` to extract actual hook type from data
  - For `hook_execution` events, uses `data.get("hook_type")` as the type
  - For other events, keeps "hook" as the generic type

**Code Added:**
```python
# For hook_execution events, extract the actual hook type from data
# Otherwise use "hook" as the type
if event == "hook_execution":
    hook_type = data.get("hook_type", "unknown")
    event_type = hook_type
else:
    event_type = "hook"

raw_event = {
    "type": event_type,  # Use actual hook type for hook_execution
    "subtype": event,    # "execution" for hook_execution events
    ...
}
```

**Rationale:** The `type` field should indicate the actual hook that executed (e.g., "UserPromptSubmit", "PreToolUse"), not a generic "hook" value. This makes filtering and routing events much easier.

### 3. Source Field: "claude_hooks" → "mpm_hook"

**Files Modified:**
- `src/claude_mpm/hooks/claude_hooks/services/connection_manager.py`
  - Changed `"source": "claude_hooks"` → `"source": "mpm_hook"`

**Rationale:** Consistent naming with the required schema (was already mostly correct, just standardized).

## Event Examples

### Hook Execution Events

#### UserPromptSubmit
```json
{
  "event": "mpm_event",
  "source": "mpm_hook",
  "type": "UserPromptSubmit",
  "subtype": "execution",
  "timestamp": "2025-12-23T14:33:03.612087+00:00",
  "data": {
    "hook_name": "UserPromptSubmit",
    "hook_type": "UserPromptSubmit",
    "session_id": "abc123",
    "working_directory": "/path/to/project",
    "success": true,
    "duration_ms": 45,
    "result_summary": "Processed user prompt (127 chars)"
  },
  "correlation_id": "corr-456",
  "session_id": "abc123",
  "cwd": "/path/to/project"
}
```

#### PreToolUse
```json
{
  "event": "mpm_event",
  "source": "mpm_hook",
  "type": "PreToolUse",
  "subtype": "execution",
  "timestamp": "2025-12-23T14:33:03.612201+00:00",
  "data": {
    "hook_name": "PreToolUse",
    "hook_type": "PreToolUse",
    "tool_name": "Bash",
    "session_id": "abc123",
    "success": true,
    "duration_ms": 12,
    "result_summary": "Pre-processing tool call: Bash"
  }
}
```

#### PostToolUse
```json
{
  "event": "mpm_event",
  "source": "mpm_hook",
  "type": "PostToolUse",
  "subtype": "execution",
  "data": {
    "hook_name": "PostToolUse",
    "hook_type": "PostToolUse",
    "tool_name": "Bash",
    "exit_code": 0,
    "success": true,
    "duration_ms": 8,
    "result_summary": "Completed tool call: Bash (success)"
  }
}
```

#### SubagentStop
```json
{
  "event": "mpm_event",
  "source": "mpm_hook",
  "type": "SubagentStop",
  "subtype": "execution",
  "data": {
    "hook_name": "SubagentStop",
    "hook_type": "SubagentStop",
    "agent_type": "python_engineer",
    "reason": "completed",
    "success": true,
    "duration_ms": 230,
    "result_summary": "Subagent python_engineer stopped: completed"
  }
}
```

### Regular Hook Events (non-execution)

For events that aren't hook execution metadata, the type remains "hook":

```json
{
  "event": "mpm_event",
  "source": "mpm_hook",
  "type": "hook",
  "subtype": "pre_tool",
  "data": {
    "tool_name": "Read",
    "session_id": "abc123"
  }
}
```

## Impact

### Positive
- ✅ Events now use the correct schema as specified in requirements
- ✅ Dashboard can filter by actual hook type (e.g., show only "PreToolUse" events)
- ✅ Event routing and processing is clearer and more explicit
- ✅ Consistent naming across the codebase

### Breaking Changes
- ⚠️ Frontend/dashboard code expecting "claude_event" will need to listen for "mpm_event"
- ⚠️ Code filtering by `type: "hook"` for execution events will need to filter by actual hook names
- ⚠️ Event handlers expecting generic "hook" type may need updates

### Migration Guide

If your code was listening for the old format:

```javascript
// BEFORE
socket.on("claude_event", (data) => {
  if (data.type === "hook" && data.subtype === "execution") {
    // Handle hook execution
  }
});

// AFTER
socket.on("mpm_event", (data) => {
  if (data.subtype === "execution") {
    // data.type now contains the actual hook name
    console.log(`Hook ${data.type} executed`);
  }
});
```

## Testing

Run the test script to see example output:
```bash
python test_mpm_event_format.py
```

## Files Modified

1. **src/claude_mpm/services/socketio/event_normalizer.py**
   - Updated `NormalizedEvent` dataclass
   - Updated all event creation in `normalize()` method
   - Updated documentation

2. **src/claude_mpm/hooks/claude_hooks/services/connection_manager.py**
   - Updated event type extraction for hook_execution events
   - Changed source field to "mpm_hook"
   - Updated Socket.IO emit call to use "mpm_event"
   - Updated fallback EventNormalizer

## Verification

To verify the changes are working:

1. Start the MPM daemon
2. Run a Claude Code command that triggers hooks
3. Check the dashboard events panel
4. Verify events show:
   - `event: "mpm_event"`
   - `type: "<HookName>"` (e.g., "UserPromptSubmit")
   - `source: "mpm_hook"`

## Next Steps

- Update dashboard/frontend code to listen for "mpm_event" instead of "claude_event"
- Update any event filtering logic to use the new type values
- Consider adding event schema validation to catch future mismatches
