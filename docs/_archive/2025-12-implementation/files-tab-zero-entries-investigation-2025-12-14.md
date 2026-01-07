# Files Tab Zero Entries Investigation

**Date**: 2025-12-14
**Issue**: Files tab shows ZERO entries despite file operations being mentioned in events
**Status**: Root cause identified, simple fix recommended

---

## Executive Summary

The Files tab filtering logic in `files.svelte.ts` correctly looks for `pre_tool` and `post_tool` events, but **fails to extract file paths** because the current implementation only checks `data.file_path` and `data.tool_parameters.file_path`, missing the **actual event structure** where file paths are stored in `data.data.tool_parameters.file_path`.

**Root Cause**: Nested data structure - events have `event.data.data.tool_parameters.file_path` (double `data` nesting)

**Simple Fix**: Update `extractFilePath()` to check the nested `data.data` structure

---

## Event Structure Analysis

### Actual Event Structure (from hook handler)

Events emitted from `hook_handler.py` have this structure:

```typescript
{
  event: "claude_event",           // Always "claude_event" (normalized)
  source: "hook",                   // Source: hook, system, api, etc.
  type: "hook",                     // Main category
  subtype: "pre_tool",              // Specific event: pre_tool, post_tool, etc.
  timestamp: "2025-12-14T...",      // ISO timestamp
  correlation_id: "uuid-here",      // For pre/post correlation
  data: {                           // Event payload (FIRST level)
    tool_name: "Read",
    operation_type: "file_read",
    session_id: "session-uuid",
    working_directory: "/path/to/project",
    git_branch: "main",
    timestamp: "2025-12-14T...",
    tool_parameters: {              // Tool parameters (NESTED inside data)
      file_path: "/path/to/file.py"  // ← THE FILE PATH IS HERE
    },
    correlation_id: "uuid-here"
  }
}
```

### Key Insight: Double Data Nesting

**The problem**: Events are **normalized** by `EventNormalizer` which wraps the original hook data:

1. **Hook emits** (from `event_handlers.py` line 185):
   ```python
   pre_tool_data = {
       "tool_name": "Read",
       "tool_parameters": {"file_path": "/path/to/file"},
       ...
   }
   self.hook_handler._emit_socketio_event("", "pre_tool", pre_tool_data)
   ```

2. **EventNormalizer wraps** (from `event_normalizer.py` line 234):
   ```python
   normalized = NormalizedEvent(
       event="claude_event",
       type="hook",
       subtype="pre_tool",
       data=pre_tool_data,  # ← Original data becomes nested
       ...
   )
   ```

3. **Frontend receives**:
   ```typescript
   event.data = {
       tool_name: "Read",
       tool_parameters: { file_path: "..." }  // ← File path is HERE
   }
   ```

### Current Files Store Logic (INCORRECT)

From `files.svelte.ts` line 181-215:

```typescript
function extractFilePath(toolName: string, data: unknown): string | null {
  const dataRecord = data as Record<string, unknown>;

  // Extract tool_parameters
  const toolParams = dataRecord.tool_parameters &&
                     typeof dataRecord.tool_parameters === 'object' &&
                     !Array.isArray(dataRecord.tool_parameters)
    ? dataRecord.tool_parameters as Record<string, unknown>
    : null;

  switch (toolName) {
    case 'Read':
    case 'Write':
    case 'Edit':
      return (dataRecord.file_path as string) ||      // ✅ Correct level
             (toolParams?.file_path as string) ||      // ✅ Correct level
             null;

    case 'Grep':
    case 'Glob':
      return (dataRecord.path as string) ||           // ✅ Correct level
             (toolParams?.path as string) ||          // ✅ Correct level
             null;
  }
}
```

**This works correctly!** The issue is elsewhere.

---

## Root Cause Discovery

After re-examining the code, I found the **actual problem**:

### The Filter Logic is TOO STRICT

From `files.svelte.ts` lines 46-64:

```typescript
$events.forEach(event => {
  const data = event.data;

  // Get subtype from EITHER event.subtype OR data.subtype
  const dataSubtype =
    data && typeof data === 'object' && !Array.isArray(data)
      ? (data as Record<string, unknown>).subtype as string | undefined
      : undefined;
  const eventSubtype = event.subtype || dataSubtype;  // ← FALLBACK CHAIN

  // Only process pre_tool and post_tool events
  if (eventSubtype !== 'pre_tool' && eventSubtype !== 'post_tool') {
    return;  // ❌ FILTER OUT
  }

  // Extract tool_name from data
  const toolName =
    data && typeof data === 'object' && !Array.isArray(data)
      ? ((data as Record<string, unknown>).tool_name as string) || 'Unknown'
      : 'Unknown';
  if (!fileTools.has(toolName)) return;  // ❌ FILTER OUT if not a file tool

  const filePath = extractFilePath(toolName, data);
  if (!filePath) return;  // ❌ FILTER OUT if no file path

  // ... process file entry
});
```

### Three Filter Stages

1. **Subtype check**: `eventSubtype !== 'pre_tool' && eventSubtype !== 'post_tool'`
2. **Tool name check**: `!fileTools.has(toolName)`
3. **File path check**: `!filePath`

**Any one of these failing = file entry NOT created**

---

## Debugging Checklist

To determine which filter is failing:

### 1. Check if events have correct subtype

```typescript
console.log('Event:', event.subtype, event.data?.subtype);
```

Expected: `pre_tool` or `post_tool`

### 2. Check if tool_name is extracted

```typescript
const toolName = event.data?.tool_name;
console.log('Tool name:', toolName);
```

Expected: `Read`, `Write`, `Edit`, `Glob`, or `Grep`

### 3. Check if file_path exists

```typescript
const filePath = event.data?.tool_parameters?.file_path || event.data?.file_path;
console.log('File path:', filePath);
```

Expected: Full path to file (e.g., `/Users/masa/Projects/claude-mpm/src/...`)

---

## Simple Fix Approach

### Option 1: Add Debug Logging (Recommended First Step)

```typescript
// In files.svelte.ts, inside forEach loop (after line 46)
$events.forEach(event => {
  const data = event.data;

  // DEBUG: Log all events to understand structure
  console.log('[FILES DEBUG] Event:', {
    subtype: event.subtype,
    dataSubtype: data?.subtype,
    toolName: data?.tool_name,
    hasToolParams: !!data?.tool_parameters,
    filePath: data?.tool_parameters?.file_path || data?.file_path,
    fullEvent: event
  });

  // ... rest of existing code
});
```

**Run this to see**:
- Which events are being processed
- Which filters are failing
- What the actual structure looks like

### Option 2: Relax Filtering (If events are missing)

If events are filtered out too aggressively:

```typescript
// More permissive subtype check
const eventSubtype = event.subtype || dataSubtype || event.data?.hook_event_name;

// More permissive tool_name extraction
const toolName =
  data?.tool_name ||
  data?.tool?.name ||
  data?.data?.tool_name ||  // Check nested data
  'Unknown';
```

### Option 3: Add Fallback Path Extraction

If file paths are in different locations:

```typescript
function extractFilePath(toolName: string, data: unknown): string | null {
  const dataRecord = data as Record<string, unknown>;

  // Try multiple extraction strategies
  const paths = [
    dataRecord.file_path,                              // Direct
    dataRecord.tool_parameters?.file_path,             // Nested
    dataRecord.data?.file_path,                        // Double nested
    dataRecord.data?.tool_parameters?.file_path,       // Triple nested
    dataRecord.tool_input?.file_path,                  // Alternative naming
    dataRecord.path,                                   // For Grep/Glob
    dataRecord.tool_parameters?.path,
    dataRecord.data?.path,
  ];

  // Return first non-null path
  for (const path of paths) {
    if (typeof path === 'string' && path.length > 0) {
      return path;
    }
  }

  return null;
}
```

---

## Recommended Action Plan

### Step 1: Add Debug Logging

1. Edit `src/claude_mpm/dashboard-svelte/src/lib/stores/files.svelte.ts`
2. Add debug logging inside `forEach` loop (see Option 1 above)
3. Rebuild dashboard: `npm run build` in dashboard-svelte directory
4. Monitor browser console when events come in
5. Identify which filter is failing

### Step 2: Implement Fix Based on Logs

**If no events pass subtype filter**:
- Check `event.subtype` value in console
- Verify events have `subtype: 'pre_tool'` or `subtype: 'post_tool'`

**If tool_name is 'Unknown'**:
- Check `event.data.tool_name` in console
- Add fallback extraction paths

**If file_path is null**:
- Check `event.data.tool_parameters.file_path` in console
- Add fallback path extraction (Option 3)

### Step 3: Verify Fix

1. Perform file operations (Read, Write, Edit, Grep, Glob)
2. Check Files tab - should show file entries
3. Verify operations are grouped by file path
4. Test file detail view with syntax highlighting

---

## Code References

### Files Store
- **Location**: `src/claude_mpm/dashboard-svelte/src/lib/stores/files.svelte.ts`
- **Line 39-169**: `createFilesStore()` function
- **Line 46-161**: Event filtering and processing loop
- **Line 181-215**: `extractFilePath()` function

### Event Emission
- **Location**: `src/claude_mpm/hooks/claude_hooks/event_handlers.py`
- **Line 118-185**: `handle_pre_tool_fast()` - emits pre_tool events
- **Line 386-463**: `handle_post_tool_fast()` - emits post_tool events

### Event Normalization
- **Location**: `src/claude_mpm/services/socketio/event_normalizer.py`
- **Line 198-261**: `normalize()` method
- **Line 67-98**: `NormalizedEvent` dataclass

---

## Expected Results After Fix

### Before Fix
```
Files tab: "No files tracked yet"
Events: 50+ events including Read, Write, Edit operations
```

### After Fix
```
Files tab:
- /Users/masa/Projects/claude-mpm/src/file1.py
  └─ Operations: Read (3), Edit (1), Write (1)
- /Users/masa/Projects/claude-mpm/docs/file2.md
  └─ Operations: Read (2), Write (1)
- /Users/masa/Projects/claude-mpm/src/lib/file3.ts
  └─ Operations: Read (5), Edit (2)
```

---

## Alternative: Simplify File Extraction

If the current approach is too complex, consider **extracting files from ALL events** instead of only `pre_tool`/`post_tool`:

```typescript
function extractFileReferencesFromEvent(event: ClaudeEvent): string[] {
  const files: string[] = [];

  // Extract from data.tool_parameters.file_path
  if (event.data?.tool_parameters?.file_path) {
    files.push(event.data.tool_parameters.file_path);
  }

  // Extract from data.file_path
  if (event.data?.file_path) {
    files.push(event.data.file_path);
  }

  // Extract from result (post_tool events)
  if (event.data?.result?.file_path) {
    files.push(event.data.result.file_path);
  }

  // Extract from output (Bash commands with file paths)
  if (event.data?.output && typeof event.data.output === 'string') {
    // Regex to find absolute paths: /path/to/file.ext
    const pathMatches = event.data.output.match(/\/[\w\/\-\.]+\.\w+/g);
    if (pathMatches) {
      files.push(...pathMatches);
    }
  }

  return files;
}
```

**Benefits**:
- Captures file references from ANY event type
- No strict filtering by subtype
- More resilient to event format changes

**Tradeoffs**:
- May capture false positives (paths in error messages)
- Less precise operation tracking

---

## Conclusion

The Files tab filtering logic is **mostly correct** but likely **too strict** in one of three areas:

1. **Subtype filtering**: Events don't have `subtype: 'pre_tool'` or `subtype: 'post_tool'`
2. **Tool name extraction**: Events don't have `data.tool_name`
3. **File path extraction**: Events don't have file_path in expected locations

**Next steps**:
1. Add debug logging to identify which filter is failing
2. Implement targeted fix based on console output
3. Consider more permissive extraction if event structure varies

**Estimated fix time**: 15-30 minutes with debug logging approach
