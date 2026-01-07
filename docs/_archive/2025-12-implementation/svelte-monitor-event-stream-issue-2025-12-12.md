# Svelte Monitor Dashboard - Event Stream Not Showing Events

**Research Date:** 2025-12-12
**Status:** Root Cause Identified
**Severity:** High - Core functionality broken

## Executive Summary

The Svelte monitor dashboard is not displaying events because of a **critical event name mismatch** between the backend Socket.IO consumer and the frontend event listener.

**Root Cause:** The frontend only listens for `claude_event`, but the backend emits multiple event types: `hook_event`, `cli_event`, `system_event`, `agent_event`, `build_event`, and `claude_event`.

## Technical Analysis

### Backend Event Emission (SocketIOConsumer)

**Location:** `src/claude_mpm/services/events/consumers/socketio.py`

The backend maps event topics to different Socket.IO event names:

```python
def _convert_to_socketio(self, event: Event) -> Dict[str, Any]:
    """Convert an Event to Socket.IO format."""
    # Determine Socket.IO event name based on topic
    if event.topic.startswith("hook."):
        socketio_event = "hook_event"
    elif event.topic.startswith("cli."):
        socketio_event = "cli_event"
    elif event.topic.startswith("system."):
        socketio_event = "system_event"
    elif event.topic.startswith("agent."):
        socketio_event = "agent_event"
    elif event.topic.startswith("build."):
        socketio_event = "build_event"
    else:
        socketio_event = "claude_event"  # Default fallback
```

**Emitted Events:**
- `hook_event` - For hook.* topics (e.g., Claude Code hooks)
- `cli_event` - For cli.* topics
- `system_event` - For system.* topics
- `agent_event` - For agent.* topics
- `build_event` - For build.* topics
- `claude_event` - Default fallback for other events

### Frontend Event Listening (Socket Store)

**Location:** `src/claude_mpm/dashboard-svelte/src/lib/stores/socket.svelte.ts`

The frontend only subscribes to ONE event type:

```typescript
// Listen for claude events
newSocket.on('claude_event', (data: ClaudeEvent) => {
    console.log('Received claude_event:', data);
    handleEvent(data);
});
```

**Problem:** If the backend emits events as `hook_event`, `agent_event`, etc., the frontend will never receive them because it only listens for `claude_event`.

## Event Flow Analysis

### Expected Flow (Working)

```
Backend Event → topic = "other"
    ↓
SocketIOConsumer._convert_to_socketio()
    ↓
socketio_event = "claude_event"
    ↓
socketio.emit("claude_event", data)
    ↓
Frontend: newSocket.on('claude_event', callback)
    ↓
✅ Event displayed in EventStream
```

### Actual Flow (Broken for most events)

```
Backend Event → topic = "hook.tool_call"
    ↓
SocketIOConsumer._convert_to_socketio()
    ↓
socketio_event = "hook_event"
    ↓
socketio.emit("hook_event", data)
    ↓
Frontend: NO LISTENER for 'hook_event'
    ↓
❌ Event silently dropped
```

## Evidence from Code

### Frontend Socket Store Listeners

**Lines 52-60 in socket.svelte.ts:**

```typescript
// Listen for claude events
newSocket.on('claude_event', (data: ClaudeEvent) => {
    console.log('Received claude_event:', data);
    handleEvent(data);
});

// Listen for heartbeat events (server sends these periodically)
newSocket.on('heartbeat', (data: unknown) => {
    // Heartbeats confirm connection is alive - don't log to reduce noise
});
```

**Missing Listeners:**
- `hook_event` ❌
- `cli_event` ❌
- `system_event` ❌
- `agent_event` ❌
- `build_event` ❌

### Backend Event Emission

**Lines 304-316 in socketio.py:**

```python
# Determine Socket.IO event name based on topic
if event.topic.startswith("hook."):
    socketio_event = "hook_event"
elif event.topic.startswith("cli."):
    socketio_event = "cli_event"
elif event.topic.startswith("system."):
    socketio_event = "system_event"
elif event.topic.startswith("agent."):
    socketio_event = "agent_event"
elif event.topic.startswith("build."):
    socketio_event = "build_event"
else:
    socketio_event = "claude_event"
```

## Impact Assessment

### User Experience
- **Critical:** Dashboard shows "No events yet" indefinitely
- **Affected Events:** All hook.*, cli.*, system.*, agent.*, build.* events (likely 95%+ of events)
- **Working Events:** Only events with topics NOT matching the patterns above

### Detection Difficulty
- Socket.IO connection succeeds (shows as connected)
- No JavaScript errors in console
- Events are being emitted by backend (can be verified in server logs)
- Events are silently dropped on client side

## Recommended Solutions

### Solution 1: Unified Event Name (Recommended)

**Simplify backend to emit all events as `claude_event`:**

Change `_convert_to_socketio()` to always use the same event name:

```python
def _convert_to_socketio(self, event: Event) -> Dict[str, Any]:
    """Convert an Event to Socket.IO format."""
    return {
        "event": "claude_event",  # Always use unified event name
        "data": {
            "id": event.id,
            "type": event.type,
            "topic": event.topic,  # Topic preserved in data
            "timestamp": event.timestamp.isoformat(),
            "source": event.source,
            "data": event.data,
            "correlation_id": event.correlation_id,
        },
        "namespace": "/",
    }
```

**Pros:**
- Minimal code change (backend only)
- Frontend already configured correctly
- Topic information preserved in event data for filtering
- Simpler architecture

**Cons:**
- Loses Socket.IO-level event categorization
- Cannot use Socket.IO namespaces/rooms for filtering

### Solution 2: Add All Event Listeners (Alternative)

**Add listeners for all event types in frontend:**

```typescript
const eventTypes = ['claude_event', 'hook_event', 'cli_event', 'system_event', 'agent_event', 'build_event'];

eventTypes.forEach(eventType => {
    newSocket.on(eventType, (data: ClaudeEvent) => {
        console.log(`Received ${eventType}:`, data);
        handleEvent(data);
    });
});
```

**Pros:**
- Preserves Socket.IO event categorization
- Could enable event-type-specific filtering in future
- More extensible for future event types

**Cons:**
- Requires frontend code change
- More complex listener management
- Need to maintain event type list in sync with backend

### Solution 3: Catch-All Listener with onAny (Alternative)

**Use Socket.IO's `onAny` to capture all events:**

```typescript
// Catch all events dynamically
newSocket.onAny((eventName, data) => {
    if (eventName.endsWith('_event')) {
        console.log(`Received ${eventName}:`, data);
        handleEvent(data);
    }
});
```

**Pros:**
- Most flexible - automatically handles new event types
- Single listener for all events
- No need to maintain event type list

**Cons:**
- Less explicit than named listeners
- Harder to debug (catch-all pattern)
- May catch unintended events

## Implementation Priority

**RECOMMENDED: Solution 1 (Unified Event Name)**

**Rationale:**
1. **Principle of Least Change:** Frontend is already correct for a unified event model
2. **Simplicity:** Single event name reduces complexity
3. **Topic Preservation:** All categorization info preserved in `event.data.topic`
4. **Performance:** No impact on event throughput
5. **Backwards Compatibility:** Existing `claude_event` listeners continue working

## Testing Strategy

### Verification Steps

1. **Before Fix:**
   - Start monitor: `mpm-monitor --port 8765`
   - Trigger Claude Code hooks (use any tool)
   - Observe: Dashboard shows "No events yet"
   - Check browser console: No `claude_event` logs
   - Check server logs: Events being emitted as `hook_event`, etc.

2. **After Fix:**
   - Apply recommended solution
   - Restart monitor server
   - Trigger Claude Code hooks
   - Observe: Events appear in dashboard
   - Check browser console: `Received claude_event:` logs appear
   - Verify event data contains correct `topic` field

### Test Cases

**Test Case 1: Hook Events**
- Trigger: Execute tool in Claude Code
- Expected topic: `hook.tool_call`
- Before fix: Not displayed ❌
- After fix: Displayed with topic="hook.tool_call" ✅

**Test Case 2: CLI Events**
- Trigger: Run `mpm-agents-list`
- Expected topic: `cli.agents.list`
- Before fix: Not displayed ❌
- After fix: Displayed with topic="cli.agents.list" ✅

**Test Case 3: System Events**
- Trigger: System startup
- Expected topic: `system.startup`
- Before fix: Not displayed ❌
- After fix: Displayed with topic="system.startup" ✅

## Code Locations

### Files to Modify (Solution 1)

**Backend (Required):**
- `src/claude_mpm/services/events/consumers/socketio.py`
  - Method: `_convert_to_socketio()` (lines 298-331)
  - Change: Remove topic-based event name mapping
  - Return `"claude_event"` for all events

**Frontend (No changes required):**
- `src/claude_mpm/dashboard-svelte/src/lib/stores/socket.svelte.ts`
  - Already listening for `claude_event` ✅

### Files to Modify (Solution 2)

**Frontend (Required):**
- `src/claude_mpm/dashboard-svelte/src/lib/stores/socket.svelte.ts`
  - Add listeners for: `hook_event`, `cli_event`, `system_event`, `agent_event`, `build_event`

**Backend (No changes required):**
- `src/claude_mpm/services/events/consumers/socketio.py`
  - Already emitting categorized events ✅

## Related Components

### Event Flow Chain

1. **Event Source:** Claude Code hooks, CLI commands, system events
2. **Event Bus:** `src/claude_mpm/services/events/core.py`
3. **Consumer:** `src/claude_mpm/services/events/consumers/socketio.py` ⚠️ **Issue Here**
4. **Socket.IO Server:** `src/claude_mpm/services/socketio/server.py`
5. **Frontend Store:** `src/claude_mpm/dashboard-svelte/src/lib/stores/socket.svelte.ts` ⚠️ **Issue Here**
6. **UI Component:** `src/claude_mpm/dashboard-svelte/src/lib/components/EventStream.svelte`

### Debug Points

**Backend Verification:**
```bash
# Check if events are being emitted
tail -f ~/.claude-mpm/cache/logs/monitor-*.log | grep "Emitted.*events"
```

**Frontend Verification:**
```javascript
// In browser console
window.socketStore = socketStore;  // Add this to socket.svelte.ts for debugging
```

## Architectural Notes

### Design Intent Analysis

The backend's event categorization suggests an **intent for topic-based routing**, but the frontend implementation suggests a **unified event stream approach**.

**Possible Original Design:**
- Backend: Route different event types to different Socket.IO rooms/namespaces
- Frontend: Subscribe to specific event categories
- Reality: Implementation mismatch

**Current State:**
- Backend: Emits categorized events
- Frontend: Only listens for unified event stream
- Result: Most events dropped

### Future Considerations

If event categorization is needed in the future:
1. Use `event.data.topic` field for filtering (already available)
2. Add frontend filters based on topic patterns
3. No need for Socket.IO-level categorization unless using namespaces/rooms

## Conclusion

**Root Cause:** Event name mismatch between backend emission and frontend subscription

**Fix Complexity:** Low (single function change)

**Testing Required:** Moderate (verify all event types display correctly)

**Recommended Approach:** Solution 1 (Unified Event Name)

**Next Steps:**
1. Apply Solution 1 to backend socketio.py
2. Rebuild and restart monitor server
3. Test with hook.*, cli.*, system.*, agent.*, build.* events
4. Verify event stream displays all events
5. Commit fix with test evidence

---

**Research conducted by:** Claude Code Research Agent
**Framework:** Claude MPM v5.3.1
**Investigation method:** Static code analysis + event flow tracing
