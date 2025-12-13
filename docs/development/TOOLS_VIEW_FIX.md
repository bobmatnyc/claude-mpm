# Tools View Fix - Summary

## Problem
The Tools view in the Claude MPM Svelte dashboard was not showing tool executions even though `pre_tool` and `post_tool` events were visible in the Event Stream.

## Root Cause
The tools store (`src/claude_mpm/dashboard-svelte/src/lib/stores/tools.svelte.ts`) was:

1. **Only looking for `correlation_id` at the top level** of events
2. **Skipping all events without `correlation_id`** (lines 17-20)
3. **Not handling events with `tool_call_id` in data**

While the backend correctly sets `correlation_id` from `data.tool_call_id`, events without this field were being completely ignored.

## Solution Implemented

### 1. Multi-location correlation_id extraction
```typescript
const correlationId =
    event.correlation_id ||
    (data?.correlation_id as string) ||
    (data?.tool_call_id as string);
```

### 2. Fallback ID generation
If no correlation_id is found, generate a unique ID using:
```typescript
const id = correlationId || `${sessionId}_${toolName}_${timestamp}`;
```

This ensures **ALL pre_tool events are shown**, even without correlation_id.

### 3. Smart pre/post matching
When matching `post_tool` to `pre_tool`:

- **Primary**: Use `correlation_id` if available (exact match)
- **Fallback**: Match by `session_id + tool_name + time window` (30 seconds)

This handles cases where:
- Events arrive out of order
- `correlation_id` is missing but events are related
- Multiple tools run concurrently

### 4. Debug logging
Added comprehensive console logging:
```typescript
console.log(`[Tools Store] Processing ${event.subtype} event:`, {
    correlationId,
    generatedId: id,
    toolName,
    sessionId,
    hasCorrelationId: !!correlationId,
    eventData: data
});
```

This helps diagnose future issues with tool correlation.

## Files Changed

### Modified
- `src/claude_mpm/dashboard-svelte/src/lib/stores/tools.svelte.ts`
  - Enhanced correlation_id extraction (lines 15-20)
  - Added fallback ID generation (lines 22-28)
  - Added debug logging (lines 30-38)
  - Improved post_tool matching with time-based fallback (lines 66-91)

### Built
- `src/claude_mpm/dashboard/static/svelte-build/` (rebuilt with npm run build)

## Testing Recommendations

1. **Clear Browser Cache**: Ensure new build is loaded
2. **Check Console**: Look for `[Tools Store]` debug messages
3. **Test Scenarios**:
   - Tools with `correlation_id` (should work as before)
   - Tools without `correlation_id` (should now appear)
   - Multiple concurrent tools (should match correctly)
   - Tools with `tool_call_id` in data (should extract and use)

## Expected Behavior

**Before Fix:**
- Tools view shows "No tool executions yet"
- Event stream shows pre_tool and post_tool events
- Tools without correlation_id are completely hidden

**After Fix:**
- ALL tool executions appear in Tools view
- Tools are correlated using correlation_id when available
- Fallback matching by session + tool + time when needed
- Debug logs show what correlation strategy is used

## Performance Impact
- **Minimal**: Only processes pre_tool/post_tool events (same as before)
- **Time-based matching**: O(n) search in worst case (no correlation_id), but limited by 30-second window
- **Typical case**: O(1) lookup using correlation_id

## Future Improvements
1. **Remove debug logging** once verified stable (lines 30-38)
2. **Add tool count badge** to Tools tab showing pending/running tools
3. **Add filtering** by tool name, status, session
4. **Add search** for tool operations
5. **Export tool history** for performance analysis

## Related Backend Code
- `src/claude_mpm/hooks/claude_hooks/services/connection_manager.py` (lines 118-130)
  - Sets `correlation_id` from `tool_call_id`
- `src/claude_mpm/services/socketio/event_normalizer.py` (lines 81-98)
  - Includes `correlation_id` in normalized events only if present

## Verification Steps

1. Start Claude MPM monitor server:
   ```bash
   claude-mpm run
   ```

2. Open dashboard at http://localhost:8765

3. Trigger some Claude Code tool usage (Read, Edit, Bash, etc.)

4. Switch to Tools view - should now show all tool executions

5. Check browser console for debug logs showing correlation strategy

## LOC Delta
- Added: ~50 lines (correlation logic, fallback matching, debug logging)
- Removed: 0 lines
- Net Change: +50 lines
- Phase: Enhancement (fixing missing functionality)

## Deployment
Files already built and copied to:
```
src/claude_mpm/dashboard/static/svelte-build/
```

No additional deployment steps needed. Restart `claude-mpm run` to serve updated files.
