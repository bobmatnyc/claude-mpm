# Pre_tool and Post_tool Event Correlation Research

**Date**: 2025-12-12
**Researcher**: Claude Code (Research Agent)
**Project**: Claude MPM - Dashboard Event Correlation
**Status**: ✅ Complete

---

## Executive Summary

This research investigates how to correlate `pre_tool` and `post_tool` events in the Claude MPM dashboard to link them together as pairs representing a single tool execution.

**Key Findings:**
1. ✅ **Correlation ID exists but is unused**: The Event dataclass has a `correlation_id` field that is currently not being set
2. ✅ **Session ID provides partial correlation**: Both pre_tool and post_tool events include `session_id` which helps group events within a session
3. ✅ **Tool name correlation**: Both events include `tool_name` field with the same value
4. ✅ **Timestamp-based matching**: Events occur in sequence with pre_tool followed immediately by post_tool
5. ⚠️ **No unique tool call ID**: Currently there's no unique identifier per tool invocation

---

## Current Event Structure

### Event Core Definition
**Location**: `src/claude_mpm/services/events/core.py`

```python
@dataclass
class Event:
    """Standard event format for the event bus."""

    id: str                          # Unique event ID (UUID)
    topic: str                       # Event topic (e.g., "hook.response")
    type: str                        # Event type (e.g., "AssistantResponse")
    timestamp: datetime              # When event was created
    source: str                      # Who created the event
    data: Dict[str, Any]             # Event payload
    metadata: Optional[EventMetadata] = None
    correlation_id: Optional[str] = None  # ⚠️ EXISTS BUT UNUSED
    priority: EventPriority = EventPriority.NORMAL
```

**Key Finding**: The `correlation_id` field exists in the Event dataclass but is **never set** in the current implementation.

### Pre_tool Event Data Structure

**Source**: `src/claude_mpm/hooks/claude_hooks/event_handlers.py:117-167`

```python
pre_tool_data = {
    "tool_name": tool_name,                    # ✅ Key correlation field
    "operation_type": operation_type,
    "tool_parameters": tool_params,
    "session_id": event.get("session_id", ""),  # ✅ Session correlation
    "working_directory": working_dir,
    "git_branch": git_branch,
    "timestamp": datetime.now(timezone.utc).isoformat(),  # ✅ Temporal ordering
    "parameter_count": len(tool_input),
    "is_file_operation": tool_name in ["Write", "Edit", ...],
    "is_execution": tool_name in ["Bash", "NotebookEdit"],
    "is_delegation": tool_name == "Task",
    "security_risk": assess_security_risk(tool_name, tool_input),
}
```

**Correlation Fields Available:**
- ✅ `tool_name` - exact match with post_tool
- ✅ `session_id` - groups events within a session
- ✅ `timestamp` - temporal ordering
- ⚠️ No unique tool call ID

### Post_tool Event Data Structure

**Source**: `src/claude_mpm/hooks/claude_hooks/event_handlers.py:368-430`

```python
post_tool_data = {
    "tool_name": tool_name,                     # ✅ Matches pre_tool
    "exit_code": exit_code,
    "success": exit_code == 0,
    "status": ("success" if exit_code == 0 else "error"),
    "duration_ms": duration,
    "result_summary": result_data,
    "session_id": event.get("session_id", ""),   # ✅ Same session as pre_tool
    "working_directory": working_dir,
    "git_branch": git_branch,
    "timestamp": datetime.now(timezone.utc).isoformat(),  # ✅ Later than pre_tool
    "has_output": bool(result_data.get("output")),
    "has_error": bool(result_data.get("error")),
    "output_size": len(str(result_data.get("output", ""))),
}
```

**Correlation Fields Available:**
- ✅ `tool_name` - exact match with pre_tool
- ✅ `session_id` - same as pre_tool
- ✅ `timestamp` - occurs after pre_tool
- ⚠️ No unique tool call ID

---

## Socket.IO Event Format

**Source**: `src/claude_mpm/services/events/consumers/socketio.py:298-331`

Events are converted to Socket.IO format with these fields:

```python
{
    "event": socketio_event,  # e.g., "hook_event"
    "data": {
        "id": event.id,                    # ✅ Unique per event (but different for pre/post)
        "type": event.type,                # "hook"
        "topic": event.topic,              # e.g., "hook.pre_tool"
        "timestamp": event.timestamp,
        "source": event.source,            # "claude_hooks"
        "data": event.data,                # Contains tool_name, session_id, etc.
        "correlation_id": event.correlation_id,  # ⚠️ Currently None/undefined
    },
    "namespace": "/",
}
```

**Key Finding**: The `correlation_id` field is passed through to Socket.IO but is currently `None` or undefined.

---

## Frontend Event Type Definition

**Source**: `src/claude_mpm/dashboard-svelte/src/lib/types/events.ts`

```typescript
export interface ClaudeEvent {
    id: string;
    event?: string;         // Socket event name (claude_event, hook_event, etc.)
    type: string;           // "hook", "session.ended", etc.
    timestamp: string | number;
    data: unknown;
    agent?: string;
    sessionId?: string;     // TypeScript format (camelCase)
    session_id?: string;    // Python format (snake_case)
    subtype?: string;       // "pre_tool", "post_tool", etc.
    source?: string;
    metadata?: unknown;
    cwd?: string;
}
```

**Missing**: No `correlation_id` field in TypeScript definition

---

## Correlation Approaches

### Option 1: Use `correlation_id` Field (Recommended)

**Implementation**:
1. Add `correlation_id` field to TypeScript `ClaudeEvent` interface
2. Generate a unique tool call ID when creating pre_tool event
3. Pass the same correlation_id to post_tool event
4. Use correlation_id to link events in dashboard UI

**Advantages**:
- ✅ Designed for this exact purpose
- ✅ Clean, explicit correlation
- ✅ Works across different sessions
- ✅ Future-proof for other event pairs

**Changes Required**:

**Backend** (`src/claude_mpm/hooks/claude_hooks/event_handlers.py`):
```python
import uuid

# In handle_pre_tool_fast():
tool_call_id = str(uuid.uuid4())  # Generate unique ID
pre_tool_data["tool_call_id"] = tool_call_id
# Store in handler for later retrieval
self.hook_handler.active_tool_calls[session_id] = {
    "tool_call_id": tool_call_id,
    "tool_name": tool_name,
    "timestamp": timestamp,
}

# In handle_post_tool_fast():
# Retrieve the tool_call_id from active calls
call_info = self.hook_handler.active_tool_calls.pop(session_id, {})
tool_call_id = call_info.get("tool_call_id")
if tool_call_id:
    post_tool_data["tool_call_id"] = tool_call_id
```

**Event Creation** (`src/claude_mpm/services/events/core.py` or connection manager):
```python
# When creating Event objects from hook data
event = Event(
    id=str(uuid.uuid4()),
    topic=f"hook.{event_type}",
    type="hook",
    timestamp=datetime.now(timezone.utc),
    source="claude_hooks",
    data=event_data,
    correlation_id=event_data.get("tool_call_id"),  # Set from tool_call_id
)
```

**Frontend** (`src/claude_mpm/dashboard-svelte/src/lib/types/events.ts`):
```typescript
export interface ClaudeEvent {
    // ... existing fields
    correlation_id?: string;  // Add correlation ID field
}
```

### Option 2: Session + Tool Name + Timestamp Matching (Fallback)

**Implementation**:
Match events where:
- `session_id` is the same
- `tool_name` is the same
- `post_tool.timestamp > pre_tool.timestamp`
- No other pre_tool exists between them

**Advantages**:
- ✅ Works with current data structure
- ✅ No backend changes required

**Disadvantages**:
- ⚠️ Fragile with parallel tool calls
- ⚠️ Breaks if events arrive out of order
- ⚠️ Complex matching logic in frontend

**Frontend Logic**:
```typescript
// Group events by session_id and tool_name
const eventPairs = new Map<string, { pre?: ClaudeEvent, post?: ClaudeEvent }>();

events.forEach(event => {
    if (event.subtype === 'pre_tool') {
        const key = `${event.session_id}:${event.data.tool_name}:${event.timestamp}`;
        eventPairs.set(key, { pre: event, post: eventPairs.get(key)?.post });
    } else if (event.subtype === 'post_tool') {
        // Find matching pre_tool (most recent with same session/tool)
        const matchingPre = findMostRecentPreTool(event);
        if (matchingPre) {
            const key = `${matchingPre.session_id}:${matchingPre.data.tool_name}:${matchingPre.timestamp}`;
            eventPairs.set(key, { pre: matchingPre, post: event });
        }
    }
});
```

### Option 3: Hybrid Approach

Use `correlation_id` when available, fall back to session/tool/timestamp matching:

```typescript
function linkEventPairs(events: ClaudeEvent[]): EventPair[] {
    const pairs: EventPair[] = [];

    // First pass: match by correlation_id
    const byCorrelationId = new Map<string, { pre?: ClaudeEvent, post?: ClaudeEvent }>();
    events.forEach(event => {
        if (event.correlation_id) {
            const existing = byCorrelationId.get(event.correlation_id) || {};
            if (event.subtype === 'pre_tool') existing.pre = event;
            if (event.subtype === 'post_tool') existing.post = event;
            byCorrelationId.set(event.correlation_id, existing);
        }
    });

    // Second pass: fallback to heuristic matching for events without correlation_id
    // ... (session/tool/timestamp logic)

    return pairs;
}
```

---

## Other Event Pairs to Consider

The same correlation approach can be applied to:

### Subagent Start/Stop
- `subagent_start` (emitted in `handle_pre_tool_fast` when `tool_name == "Task"`)
- `subagent_stop` (emitted in `handle_subagent_stop_fast`)

**Current Correlation**:
- ✅ Both include `session_id`
- ✅ Both include `agent_type`
- ⚠️ No unique delegation ID

**Recommendation**: Add `delegation_id` field similar to `tool_call_id`

### User Prompt/Assistant Response
- `user_prompt` (in `handle_user_prompt_fast`)
- `assistant_response` (in `handle_assistant_response`)

**Current Correlation**:
- ✅ Uses `pending_prompts` dict keyed by `session_id`
- ✅ Tracked in response_tracking_manager

**Recommendation**: Already tracked via session, correlation_id would provide additional robustness

---

## Recommended Implementation Plan

### Phase 1: Add Correlation ID Support (Backend)

**File**: `src/claude_mpm/hooks/claude_hooks/event_handlers.py`

1. Add `active_tool_calls` dict to `ClaudeHookHandler.__init__`:
   ```python
   self.active_tool_calls = {}  # session_id -> {tool_call_id, tool_name, timestamp}
   ```

2. Modify `handle_pre_tool_fast`:
   ```python
   tool_call_id = str(uuid.uuid4())
   pre_tool_data["tool_call_id"] = tool_call_id
   self.hook_handler.active_tool_calls[session_id] = {
       "tool_call_id": tool_call_id,
       "tool_name": tool_name,
       "timestamp": pre_tool_data["timestamp"],
   }
   ```

3. Modify `handle_post_tool_fast`:
   ```python
   call_info = self.hook_handler.active_tool_calls.pop(session_id, {})
   tool_call_id = call_info.get("tool_call_id")
   if tool_call_id:
       post_tool_data["tool_call_id"] = tool_call_id
   ```

**File**: `src/claude_mpm/hooks/claude_hooks/services/connection_manager.py`

4. Modify `emit_event` to set correlation_id from tool_call_id:
   ```python
   # Extract tool_call_id if present
   tool_call_id = data.get("tool_call_id")

   raw_event = {
       "type": "hook",
       "subtype": event,
       "timestamp": datetime.now(timezone.utc).isoformat(),
       "data": data,
       "source": "claude_hooks",
       "session_id": data.get("sessionId"),
       "correlation_id": tool_call_id,  # Set from tool_call_id
   }
   ```

**Note**: If using the Event Bus, set correlation_id when creating Event objects:
```python
event = Event(
    correlation_id=event_data.get("tool_call_id"),
    # ... other fields
)
```

### Phase 2: Update Frontend Types

**File**: `src/claude_mpm/dashboard-svelte/src/lib/types/events.ts`

```typescript
export interface ClaudeEvent {
    id: string;
    event?: string;
    type: string;
    timestamp: string | number;
    data: unknown;
    agent?: string;
    sessionId?: string;
    session_id?: string;
    subtype?: string;
    source?: string;
    metadata?: unknown;
    cwd?: string;
    correlation_id?: string;  // ✅ Add this field
}
```

### Phase 3: Implement UI Linking

**File**: `src/claude_mpm/dashboard-svelte/src/lib/components/EventStream.svelte`

Add event pairing logic:

```typescript
// Create a derived store for event pairs
let eventPairs = $derived.by(() => {
    const pairs = new Map<string, {
        pre?: ClaudeEvent,
        post?: ClaudeEvent,
        correlation_id: string
    }>();

    events.forEach(event => {
        // Use correlation_id if available
        if (event.correlation_id) {
            const existing = pairs.get(event.correlation_id) || {
                correlation_id: event.correlation_id
            };

            if (event.subtype === 'pre_tool') {
                existing.pre = event;
            } else if (event.subtype === 'post_tool') {
                existing.post = event;
            }

            pairs.set(event.correlation_id, existing);
        }
    });

    return Array.from(pairs.values());
});

// Render paired events with visual linking
{#each eventPairs as pair}
    <div class="event-pair">
        {#if pair.pre}
            <div class="pre-tool" class:linked={pair.post}>
                <!-- pre_tool event display -->
            </div>
        {/if}
        {#if pair.post}
            <div class="post-tool" class:linked={pair.pre}>
                <!-- post_tool event display -->
                {#if pair.pre}
                    <span class="duration">
                        {calculateDuration(pair.pre.timestamp, pair.post.timestamp)}ms
                    </span>
                {/if}
            </div>
        {/if}
    </div>
{/each}
```

### Phase 4: Visual Design

**UI Enhancements**:
1. **Indentation**: Indent post_tool events slightly to show hierarchy
2. **Connecting Lines**: Draw visual lines connecting pre/post pairs
3. **Grouping**: Highlight or collapse paired events
4. **Duration Display**: Show execution time between pre and post
5. **Status Indicator**: Show success/failure status on the pair

**Example CSS**:
```css
.event-pair {
    position: relative;
    margin: 8px 0;
}

.pre-tool.linked {
    border-left: 3px solid #3b82f6;
}

.post-tool.linked {
    margin-left: 16px;
    border-left: 3px solid #3b82f6;
}

.post-tool .duration {
    background: #1e293b;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 0.75rem;
    color: #94a3b8;
}
```

---

## Testing Strategy

### Test Case 1: Single Tool Execution
1. Execute a single Bash command
2. Verify pre_tool and post_tool events have same `correlation_id`
3. Verify events are visually linked in dashboard

### Test Case 2: Multiple Sequential Tools
1. Execute 3 different tools in sequence
2. Verify each pair has unique `correlation_id`
3. Verify no cross-linking between different tool calls

### Test Case 3: Parallel Tool Execution (Edge Case)
1. Trigger parallel tool execution (if possible)
2. Verify each tool has unique `correlation_id`
3. Verify events don't get mixed up

### Test Case 4: Subagent Delegation
1. Delegate to a subagent (Task tool)
2. Verify pre_tool/post_tool correlation for Task
3. Verify subagent_start/subagent_stop correlation

---

## Performance Considerations

### Memory Usage
- `active_tool_calls` dict grows with concurrent tool calls
- **Mitigation**: Cleanup completed calls in `handle_post_tool_fast`
- **Cleanup strategy**: Remove entries older than 5 minutes

### Event Processing Overhead
- Adding `correlation_id` is lightweight (UUID generation ~1μs)
- Storing in dict is O(1) operation
- **Impact**: Negligible (<0.1% overhead)

### Frontend Rendering
- Pairing logic runs on every event update
- **Mitigation**: Use memoization/derived stores
- **Complexity**: O(n) where n = number of events

---

## Future Enhancements

### 1. Correlation ID for All Event Pairs
Extend correlation_id to:
- Subagent start/stop (`delegation_id`)
- User prompt/assistant response (`interaction_id`)
- Build events (`build_id`)

### 2. Event Timeline View
Use correlation_id to create timeline visualization:
```
[pre_tool: Read file.py] ──────┐
                               │ 45ms
[post_tool: Read file.py] ─────┘
```

### 3. Performance Analytics
Group by correlation_id to analyze:
- Tool execution times
- Success/failure rates per tool
- Tool usage patterns

### 4. Event Replay/Debugging
Use correlation_id to:
- Filter events by specific tool execution
- Replay specific tool calls
- Debug failed operations

---

## Code Locations Reference

### Backend Files
- Event core definition: `src/claude_mpm/services/events/core.py`
- Event handlers: `src/claude_mpm/hooks/claude_hooks/event_handlers.py`
- Connection manager: `src/claude_mpm/hooks/claude_hooks/services/connection_manager.py`
- Socket.IO consumer: `src/claude_mpm/services/events/consumers/socketio.py`

### Frontend Files
- Event types: `src/claude_mpm/dashboard-svelte/src/lib/types/events.ts`
- Event stream UI: `src/claude_mpm/dashboard-svelte/src/lib/components/EventStream.svelte`
- Socket store: `src/claude_mpm/dashboard-svelte/src/lib/stores/socket.svelte.ts`

### Hook Manager
- Hook manager: `src/claude_mpm/core/hook_manager.py` (for PM-triggered events)

---

## Conclusion

**Recommended Approach**: **Option 1 - Use `correlation_id` Field**

This approach provides:
- ✅ Clean, explicit correlation between event pairs
- ✅ Future-proof design for other event types
- ✅ Minimal performance overhead
- ✅ Simple frontend implementation
- ✅ Better debugging and analytics capabilities

**Implementation Effort**: ~4-6 hours
- Backend changes: 2-3 hours
- Frontend changes: 1-2 hours
- Testing: 1 hour

**Alternative**: If immediate implementation isn't feasible, use **Option 2** (session/tool/timestamp matching) as a temporary solution, then migrate to correlation_id when possible.

---

## Related Issues/Tickets

- Dashboard event correlation (this research)
- Subagent delegation tracking
- Performance analytics
- Event replay functionality

---

**Research Status**: ✅ Complete
**Next Steps**:
1. Review findings with team
2. Prioritize implementation
3. Create implementation tickets
4. Begin Phase 1 (backend correlation_id support)
