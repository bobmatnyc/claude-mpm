# Tools View Verification Guide

## What Was Fixed

The Tools view in the dashboard was not showing tool executions because the tools store was:
- Only checking `event.correlation_id` at the top level
- Skipping ALL events without correlation_id
- Not checking `data.tool_call_id` or `data.correlation_id`

## Solution

Updated `src/claude_mpm/dashboard-svelte/src/lib/stores/tools.svelte.ts` to:

1. **Check multiple locations** for correlation_id:
   - `event.correlation_id`
   - `event.data.correlation_id`
   - `event.data.tool_call_id`

2. **Generate fallback ID** if no correlation_id:
   - `${sessionId}_${toolName}_${timestamp}`

3. **Smart matching** for pre/post tool events:
   - Primary: exact correlation_id match
   - Fallback: session + tool + 30-second time window

4. **Debug logging** to diagnose issues

## How to Verify

### 1. Start the monitor server
```bash
cd /Users/masa/Projects/claude-mpm
claude-mpm run
```

### 2. Open the dashboard
Open http://localhost:8765 in your browser

### 3. Trigger Claude Code tool usage
Open Claude Code and use some tools:
- Read a file
- Edit a file
- Run a bash command
- Search with Grep/Glob

### 4. Check the dashboard

**Event Stream (Events tab):**
- Should show `pre_tool` and `post_tool` events
- Each event should have tool_name in the Agent column
- Duration badge should appear for post_tool events

**Tools View (Tools tab):**
- **BEFORE FIX**: Empty "No tool executions yet"
- **AFTER FIX**: Shows all tool executions with:
  - Tool Name (Bash, Read, Edit, etc.)
  - Operation (command, file path, etc.)
  - Status (⏳ pending, ✅ success, ❌ error)
  - Duration (calculated from pre/post events)

### 5. Check browser console
Look for debug messages like:
```
[Tools Store] Processing pre_tool event: {
  correlationId: "abc123...",
  generatedId: "abc123...",
  toolName: "Read",
  sessionId: "session-123",
  hasCorrelationId: true,
  eventData: { tool_name: "Read", file_path: "..." }
}
```

## Expected Behavior

### With correlation_id (normal case)
```
Event 1: pre_tool with correlation_id="abc123"
→ Tools view: Shows "Read" as pending (⏳)

Event 2: post_tool with correlation_id="abc123"
→ Tools view: Updates to success (✅) with duration "250ms"
```

### Without correlation_id (fallback case)
```
Event 1: pre_tool without correlation_id
→ Generates fallback ID: "session-123_Read_2025-12-12T14:00:00Z"
→ Tools view: Shows "Read" as pending (⏳)

Event 2: post_tool without correlation_id
→ Matches by: session + tool + time window
→ Tools view: Updates to success (✅) with estimated duration
```

### Multiple concurrent tools
```
Event 1: pre_tool Bash correlation_id="task1"
Event 2: pre_tool Read correlation_id="task2"
Event 3: post_tool Bash correlation_id="task1" (finished first)
Event 4: post_tool Read correlation_id="task2"

→ Tools view shows both correctly matched
```

## Troubleshooting

### Tools still not showing?

1. **Hard refresh browser**: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)
2. **Clear browser cache**: Ensure new build is loaded
3. **Check console for errors**: F12 → Console tab
4. **Verify events are arriving**: Check Events tab first
5. **Check debug logs**: Should see `[Tools Store]` messages

### Tools showing but not correlating?

1. **Check console logs**: See what correlation strategy is used
2. **Verify event structure**: Inspect event in JSON Explorer
3. **Time window too short?**: Increase from 30s if tools take longer
4. **Multiple sessions?**: Filter by session in dropdown

### No debug logs?

Build may not have loaded. Verify:
```bash
cd /Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard-svelte
npm run build
```

Then restart `claude-mpm run`.

## Performance Notes

- **Correlation by ID**: O(1) lookup (instant)
- **Correlation by time**: O(n) search (only when no correlation_id)
- **Time window**: 30 seconds (configurable in code)
- **Memory**: Stores all tools in browser memory (cleared on page refresh)

## Future Improvements

1. **Remove debug logging** once verified stable
2. **Add tool filtering** by name, status, session
3. **Add tool search** for operations
4. **Add tool export** for performance analysis
5. **Add tool statistics** (success rate, avg duration)
6. **Persistent storage** (IndexedDB for tool history)

## Files Modified

- `src/claude_mpm/dashboard-svelte/src/lib/stores/tools.svelte.ts` (~50 lines added)
- `src/claude_mpm/dashboard/static/svelte-build/` (rebuilt output)

## Related Documentation

- `/Users/masa/Projects/claude-mpm/TOOLS_VIEW_FIX.md` - Detailed fix summary
- `/Users/masa/Projects/claude-mpm/docs/implementation/tool-call-correlation-2025-12-12.md` - Implementation notes
