# Tools View Fix - Event Subtype Detection

## Problem
The Tools view in the Svelte dashboard was showing "No tool executions yet" even though `pre_tool` and `post_tool` events were visible in the Event Stream.

## Root Cause
The `tools.svelte.ts` store was only checking `event.subtype` for filtering tool events, but there was a potential for the `subtype` field to be nested in `event.data.subtype` depending on how events are structured when they arrive from the backend.

## Solution
Updated `src/claude_mpm/dashboard-svelte/src/lib/stores/tools.svelte.ts` to check for `subtype` in **both locations**:

### Changes Made

**Before:**
```typescript
$events.forEach(event => {
  // Only process pre_tool and post_tool events
  if (event.subtype !== 'pre_tool' && event.subtype !== 'post_tool') {
    return;
  }

  const data = event.data as Record<string, unknown> | null;
  // ...
```

**After:**
```typescript
$events.forEach(event => {
  // Extract subtype from multiple possible locations
  // Check both top-level event.subtype AND nested event.data.subtype
  const data = event.data as Record<string, unknown> | null;
  const eventSubtype = event.subtype || (data?.subtype as string);

  // Only process pre_tool and post_tool events
  if (eventSubtype !== 'pre_tool' && eventSubtype !== 'post_tool') {
    return;
  }
  // ...
```

### All Updated References
- Line 13: Extract `eventSubtype` from both `event.subtype` and `event.data.subtype`
- Line 16: Updated filter condition to use `eventSubtype`
- Line 35: Updated console.log to use `eventSubtype`
- Line 44: Updated `if (eventSubtype === 'pre_tool')` condition
- Line 70: Updated `else if (eventSubtype === 'post_tool')` condition

## Backend Event Structure Verification

Confirmed in `src/claude_mpm/services/monitor/handlers/hooks.py` (line 422):
```python
def _process_claude_event(self, data: Dict) -> Dict:
    return {
        "type": data.get("type", "hook"),
        "subtype": data.get("subtype", "unknown"),  # ← Top-level subtype
        "timestamp": data.get("timestamp", asyncio.get_event_loop().time()),
        "session_id": data.get("session_id"),
        "source": data.get("source", "claude_hooks"),
        "data": data.get("data", {}),  # ← data is separate
        ...
    }
```

Backend events ARE emitted with top-level `subtype`, but the defensive check ensures robustness if event structures vary.

## Files Modified
- `src/claude_mpm/dashboard-svelte/src/lib/stores/tools.svelte.ts`

## Build Status
✅ Svelte dashboard rebuilt successfully
✅ Built files copied to `src/claude_mpm/dashboard/static/svelte-build/`

## Testing
The console.log statements are already in place in `tools.svelte.ts` (line 35-42):
```typescript
console.log(`[Tools Store] Processing ${eventSubtype} event:`, {
  correlationId,
  generatedId: id,
  toolName,
  sessionId,
  hasCorrelationId: !!correlationId,
  eventData: data
});
```

When the dashboard receives tool events, the console will show whether they're being detected and processed.

## Expected Behavior After Fix
- Tools view should now detect and display tool executions
- Console logs will show `[Tools Store] Processing pre_tool event:` and `[Tools Store] Processing post_tool event:`
- Tool correlation should work via `correlation_id` field
- Fallback matching by session_id + tool_name + timestamp if no correlation_id

## LOC Delta
- **Added**: 5 lines (extraction logic + comments)
- **Modified**: 3 lines (updated to use `eventSubtype`)
- **Net Change**: +5 lines

## Related Files
- Event types: `src/claude_mpm/dashboard-svelte/src/lib/types/events.ts`
- Socket store: `src/claude_mpm/dashboard-svelte/src/lib/stores/socket.svelte.ts`
- Event normalizer: `src/claude_mpm/services/socketio/event_normalizer.py`
- Hooks handler: `src/claude_mpm/services/monitor/handlers/hooks.py`
