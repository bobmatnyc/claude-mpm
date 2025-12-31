# Files Tab Empty - Diagnostic Report

## Investigation Summary

I've traced the complete event flow from Claude Code hooks to the dashboard and identified potential issues.

## Event Flow Path

```
Claude Code Tool Use (Read)
    ↓
hook_handler.py (handle_pre_tool_fast/handle_post_tool_fast)
    ↓
event_handlers.py (creates pre_tool_data/post_tool_data)
    ↓
connection_manager.py (emit_event)
    ↓
EventNormalizer (normalize to consistent schema)
    ↓
Socket.IO Connection Pool OR HTTP POST
    ↓
Monitor Server (localhost:8765)
    ↓
Hook Handler (monitor/handlers/hooks.py)
    ↓
Socket.IO Broadcast ("claude_event")
    ↓
Dashboard Frontend (files.svelte.ts)
```

## Event Structure at Each Stage

### 1. Event Handlers Output
```javascript
{
  tool_name: "Read",
  tool_parameters: { file_path: "/absolute/path" },
  correlation_id: "<uuid>",
  session_id: "...",
  timestamp: "...",
  ...
}
```

### 2. Connection Manager Normalization
```javascript
{
  type: "hook",
  subtype: "pre_tool",
  data: {
    tool_name: "Read",
    tool_parameters: { file_path: "/absolute/path" }
  },
  correlation_id: "<uuid>"
}
```

### 3. EventNormalizer Output
```javascript
{
  event: "claude_event",
  source: "hook",
  type: "hook",
  subtype: "pre_tool",
  data: {
    tool_name: "Read",
    tool_parameters: { file_path: "/absolute/path" }
  },
  correlation_id: "<uuid>"
}
```

### 4. Frontend Extraction
```javascript
const eventData = event.data;  // Gets the data object
const filePath = eventData.tool_parameters?.file_path;  // ✅ Should work!
```

## Hypothesis: Events Not Reaching Dashboard

The structure looks correct, which suggests the events might not be reaching the dashboard at all.

### Possible Causes:

1. **Socket.IO Connection Pool Failing**
   - If `get_connection_pool()` returns None or fails
   - Hooks fall back to HTTP POST
   - But HTTP endpoint might not be working

2. **HTTP Fallback Not Reaching Monitor**
   - POST to `localhost:8765/api/events` might fail
   - Monitor server might not be running
   - Or endpoint might not forward to Socket.IO correctly

3. **Socket.IO Not Broadcasting**
   - Hook handler receives events but doesn't broadcast
   - Dashboard clients not connected to Socket.IO
   - Event filtering prevents broadcast

4. **Frontend Not Listening**
   - Events store not properly initialized
   - Socket.IO client not connected
   - Event listener not registered

## Verification Steps Needed

### 1. Check if hooks are firing:
```bash
# Enable debug mode
export CLAUDE_MPM_HOOK_DEBUG=true

# Use a tool and check stderr
claude "read test.txt"
```

### 2. Check monitor server status:
```bash
curl http://localhost:8765/health
```

### 3. Check Socket.IO connection:
```javascript
// In browser console (dashboard)
console.log('Socket connected:', socket.connected);
```

### 4. Check event emission in hooks:
Add logging to `connection_manager.py`:
```python
print(f"✅ Emitted event: {event}", file=sys.stderr)
```

### 5. Check monitor server reception:
Add logging to `handlers/hooks.py`:
```python
print(f"✅ Received claude_event: {data.get('type')}/{data.get('subtype')}", file=sys.stderr)
```

## Next Steps

1. **Verify hook execution** - Check if hooks are even firing when tools are used
2. **Verify event emission** - Check if events are being emitted from hooks
3. **Verify monitor reception** - Check if monitor server receives events
4. **Verify Socket.IO broadcast** - Check if events are broadcast to clients
5. **Verify dashboard reception** - Check if dashboard receives events

## Quick Test

Create a minimal test to verify the entire chain:

```bash
# Terminal 1: Start monitor with debug logging
CLAUDE_MPM_HOOK_DEBUG=true mpm daemon start

# Terminal 2: Open dashboard
open http://localhost:8765

# Terminal 3: Trigger a hook event
claude "read README.md"

# Check:
# - Terminal 1 should show hook events
# - Browser console should show received events
# - Files tab should populate
```

## Expected vs Actual Behavior

**Expected:**
- Hook fires → Event emitted → Monitor receives → Socket.IO broadcasts → Dashboard updates → Files tab shows file

**Actual:**
- Files tab is empty despite tool use events

**Likely Issue:**
Events are not reaching the dashboard (connection issue) rather than a structure mismatch.
