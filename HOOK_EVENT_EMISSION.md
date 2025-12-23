# Hook Event Emission System

## Overview

The MPM hooks system now emits structured JSON events for every hook execution, providing visibility into timing, success/failure status, and execution context.

## Architecture

Every hook execution now follows this flow:

```
Hook Triggered → Handler Executes → Timing Captured → Event Emitted
                                   ↓
                    ConnectionManager → EventNormalizer → Socket.IO/HTTP
```

## Event Schema

All hook execution events follow the normalized `claude_event` schema:

```json
{
  "event": "claude_event",
  "source": "mpm_hook",
  "type": "hook",
  "subtype": "execution",
  "timestamp": "2025-12-23T10:30:00.123Z",
  "correlation_id": "<uuid>",
  "data": {
    "hook_name": "<hook_name>",
    "hook_type": "<hook_type>",
    "session_id": "<session_id>",
    "working_directory": "<cwd>",
    "success": true|false,
    "duration_ms": <execution_time>,
    "result_summary": "<human-readable description>",
    // ... hook-specific fields
  }
}
```

## Hook-Specific Fields

### UserPromptSubmit

```json
{
  "hook_name": "UserPromptSubmit",
  "hook_type": "UserPromptSubmit",
  "success": true,
  "duration_ms": 15,
  "result_summary": "Processed user prompt (87 chars)",
  "prompt_preview": "Write a Python function...",
  "prompt_length": 87
}
```

### PreToolUse

```json
{
  "hook_name": "PreToolUse",
  "hook_type": "PreToolUse",
  "success": true,
  "duration_ms": 8,
  "result_summary": "Pre-processing tool call: Bash",
  "tool_name": "Bash"
}
```

### PostToolUse

```json
{
  "hook_name": "PostToolUse",
  "hook_type": "PostToolUse",
  "success": true,
  "duration_ms": 12,
  "result_summary": "Completed tool call: Bash (success)",
  "tool_name": "Bash",
  "exit_code": 0
}
```

### SubagentStop

```json
{
  "hook_name": "SubagentStop",
  "hook_type": "SubagentStop",
  "success": true,
  "duration_ms": 25,
  "result_summary": "Subagent engineer stopped: completed",
  "agent_type": "engineer",
  "reason": "completed"
}
```

### SessionStart

```json
{
  "hook_name": "SessionStart",
  "hook_type": "SessionStart",
  "success": true,
  "duration_ms": 5,
  "result_summary": "New session started"
}
```

### Stop

```json
{
  "hook_name": "Stop",
  "hook_type": "Stop",
  "success": true,
  "duration_ms": 10,
  "result_summary": "Session stopped: completed"
}
```

### Notification

```json
{
  "hook_name": "Notification",
  "hook_type": "Notification",
  "success": true,
  "duration_ms": 3,
  "result_summary": "Notification received: status_update"
}
```

### AssistantResponse

```json
{
  "hook_name": "AssistantResponse",
  "hook_type": "AssistantResponse",
  "success": true,
  "duration_ms": 20,
  "result_summary": "Assistant response generated (1234 chars)"
}
```

## Error Events

When a hook fails during processing, the event includes error information:

```json
{
  "hook_name": "PreToolUse",
  "hook_type": "PreToolUse",
  "success": false,
  "duration_ms": 5,
  "result_summary": "Hook PreToolUse failed during processing",
  "error_message": "Invalid tool parameters: missing required field 'command'"
}
```

## Implementation Details

### Hook Execution Timing

The system captures execution time using Python's `time.time()`:

```python
start_time = time.time()
try:
    result = handler(event)
    success = True
except Exception as e:
    error_message = str(e)
    success = False
finally:
    duration_ms = int((time.time() - start_time) * 1000)
    self._emit_hook_execution_event(...)
```

### Event Emission Path

Hook events follow the single-path emission architecture:

1. **Primary**: Direct Socket.IO connection via `ConnectionManager`
2. **Fallback**: HTTP POST to monitor server at `http://localhost:8765/api/events`

### Event Normalization

The `EventNormalizer` handles `hook_execution` events with this mapping:

```python
EVENT_MAPPINGS = {
    "hook_execution": (EventType.HOOK, "execution"),
    # ... other mappings
}
```

## Usage Examples

### Filtering Hook Events in Dashboard

```typescript
// Filter for hook execution events
const hookEvents = events.filter(e =>
  e.type === 'hook' && e.subtype === 'execution'
);

// Filter by specific hook type
const preToolEvents = hookEvents.filter(e =>
  e.data.hook_type === 'PreToolUse'
);

// Filter by success/failure
const failedHooks = hookEvents.filter(e => !e.data.success);
```

### Analyzing Hook Performance

```typescript
// Calculate average hook execution time
const avgDuration = hookEvents.reduce((sum, e) =>
  sum + e.data.duration_ms, 0
) / hookEvents.length;

// Find slowest hooks
const slowHooks = hookEvents
  .sort((a, b) => b.data.duration_ms - a.data.duration_ms)
  .slice(0, 10);
```

### Correlating Pre/Post Tool Events

```typescript
// Use correlation_id to match PreToolUse with PostToolUse
const preToolEvent = events.find(e =>
  e.type === 'hook' &&
  e.subtype === 'execution' &&
  e.data.hook_type === 'PreToolUse'
);

const postToolEvent = events.find(e =>
  e.type === 'hook' &&
  e.subtype === 'execution' &&
  e.data.hook_type === 'PostToolUse' &&
  e.correlation_id === preToolEvent.correlation_id
);

const totalToolTime = postToolEvent.timestamp - preToolEvent.timestamp;
```

## Benefits

1. **Visibility**: Every hook execution is now visible in the event stream
2. **Performance Monitoring**: Track hook execution times to identify bottlenecks
3. **Error Tracking**: Immediate visibility into hook failures
4. **Debugging**: Correlation IDs link related events (pre/post tool, etc.)
5. **Analytics**: Analyze hook usage patterns and success rates
6. **Consistency**: All events follow the same normalized schema

## Testing

Run the test suite to validate hook event emission:

```bash
python test_hook_events.py
```

Expected output:
- ✅ All hook types emit execution events
- ✅ Events include timing information
- ✅ Events include success/failure status
- ✅ Events include human-readable summaries
- ✅ Hook-specific fields are present
- ✅ Events follow normalized schema

## Debug Mode

Enable debug output to see hook execution events in real-time:

```bash
export CLAUDE_MPM_HOOK_DEBUG=true
```

Debug output includes:
- `📊 Hook execution event: UserPromptSubmit - 15ms - ✅`
- `📊 Hook execution event: PreToolUse - 8ms - ✅`
- `📊 Hook execution event: PostToolUse - 12ms - ❌` (on failure)

## Migration Notes

### Backward Compatibility

This implementation maintains full backward compatibility:
- ✅ Existing hook processing unchanged
- ✅ Existing events still emitted (pre_tool, post_tool, etc.)
- ✅ No breaking changes to event handlers
- ✅ New events are additive only

### Event Duplication

Hook execution events are **separate** from the detailed hook events:
- **Detailed events**: `pre_tool`, `post_tool`, `user_prompt`, etc.
- **Execution events**: `hook_execution` (metadata about the hook run)

Both are emitted to provide different levels of detail:
- Use detailed events for tool parameters, outputs, etc.
- Use execution events for timing, success/failure, performance analysis

## Future Enhancements

Potential improvements for v2:
- Hook execution metrics aggregation (avg duration, success rate)
- Hook performance anomaly detection (unusually slow hooks)
- Hook failure rate alerts
- Hook execution history visualization
- Correlation with system performance metrics
