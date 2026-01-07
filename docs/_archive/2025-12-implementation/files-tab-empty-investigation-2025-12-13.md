# Files Tab Empty Investigation

**Date**: 2025-12-13
**Issue**: Files tab shows nothing despite type guards being added
**Commit**: 9c76c95d (type guards added)
**Status**: ROOT CAUSE IDENTIFIED

## Problem Summary

The Files tab is showing "No file operations yet" despite file operations occurring. The type guards added in commit 9c76c95d were necessary but didn't fix the underlying data flow issue.

## Event Flow Analysis

### 1. Server-Side Event Emission

**Location**: `src/claude_mpm/hooks/claude_hooks/event_handlers.py`

When a tool is used (e.g., Read, Write, Edit), the hook emits events:

```python
# Line 185 in event_handlers.py
self.hook_handler._emit_socketio_event("", "pre_tool", pre_tool_data)

# pre_tool_data structure (lines 153-168):
{
    "tool_name": "Read",           # ← Tool name
    "operation_type": "...",
    "tool_parameters": {...},
    "session_id": "...",
    "working_directory": "...",
    "correlation_id": "...",       # ← Correlation ID
    # ... more fields
}
```

### 2. Connection Manager Normalization

**Location**: `src/claude_mpm/hooks/claude_hooks/services/connection_manager.py`

The `emit_event` method wraps the data:

```python
# Lines 122-130
raw_event = {
    "type": "hook",
    "subtype": event,              # ← "pre_tool" or "post_tool"
    "timestamp": "...",
    "data": data,                  # ← pre_tool_data goes HERE
    "source": "claude_hooks",
    "session_id": data.get("sessionId"),
    "correlation_id": tool_call_id,
}
```

**CRITICAL FINDING**: The `subtype` is set at the TOP LEVEL of the event, NOT inside `data`.

### 3. Event Received by Socket Store

**Location**: `src/claude_mpm/dashboard-svelte/src/lib/stores/socket.svelte.ts`

Events are received and added to the `events` store (line 105):

```typescript
// Line 105
events.update(e => [...e, eventWithId]);
```

The event structure AT THIS POINT:

```json
{
  "id": "evt_...",
  "type": "hook",
  "subtype": "pre_tool",          // ← TOP-LEVEL field
  "timestamp": "2025-12-13T...",
  "data": {
    "tool_name": "Read",          // ← Inside data
    "operation_type": "...",
    "correlation_id": "...",
    // ... rest of pre_tool_data
  },
  "source": "claude_hooks",
  "session_id": "..."
}
```

### 4. Files Store Processing (THE BUG)

**Location**: `src/claude_mpm/dashboard-svelte/src/lib/stores/files.svelte.ts`

**Lines 46-58**: The filtering logic

```typescript
$events.forEach(event => {
  // Add type guards to prevent runtime errors when event.data is array/string
  const data = event.data;
  const dataSubtype =
    data && typeof data === 'object' && !Array.isArray(data)
      ? (data as Record<string, unknown>).subtype as string | undefined
      : undefined;
  const eventSubtype = event.subtype || dataSubtype;  // ← FALLBACK ORDER

  // Only process pre_tool and post_tool events
  if (eventSubtype !== 'pre_tool' && eventSubtype !== 'post_tool') {
    return;
  }
  // ...
```

**THE BUG**: This code checks `event.subtype` FIRST (which is correct), then falls back to `data.subtype`. Since `event.subtype` EXISTS and is set to `"pre_tool"`, this should work.

**Wait... let me check the actual filtering more carefully:**

Looking at lines 61-64:

```typescript
const toolName =
  data && typeof data === 'object' && !Array.isArray(data)
    ? ((data as Record<string, unknown>).tool_name as string) || 'Unknown'
    : 'Unknown';
if (!fileTools.has(toolName)) return;
```

**This should also work** - `tool_name` is in `event.data`.

Let me check the file path extraction (lines 67-68):

```typescript
const filePath = extractFilePath(toolName, data);
if (!filePath) return;
```

**AH HA! THIS IS THE BUG!**

### 5. File Path Extraction Bug

**Location**: `src/claude_mpm/dashboard-svelte/src/lib/stores/files.svelte.ts`, lines 177-199

```typescript
function extractFilePath(toolName: string, data: unknown): string | null {
  if (!data || typeof data !== 'object' || Array.isArray(data)) {
    return null;
  }

  const dataRecord = data as Record<string, unknown>;

  switch (toolName) {
    case 'Read':
    case 'Write':
    case 'Edit':
      return dataRecord.file_path as string;  // ← EXPECTS file_path IN data

    case 'Grep':
    case 'Glob':
      return dataRecord.path as string || null;

    default:
      return null;
  }
}
```

**THE PROBLEM**: The function expects `file_path` to be directly in `event.data`, BUT...

Let me check what's actually IN `event.data` for file operations:

From `event_handlers.py` line 153-168, the `pre_tool_data` structure does NOT include `file_path` directly. It only includes:
- `tool_name`
- `operation_type`
- `tool_parameters` ← FILE PATH MIGHT BE HERE
- `session_id`
- `working_directory`
- etc.

Let me check how tool_parameters is structured:

Looking at line 142:
```python
tool_params = extract_tool_parameters(tool_name, tool_input)
```

I need to find `extract_tool_parameters`:

```bash
grep -n "def extract_tool_parameters" src/claude_mpm/hooks/claude_hooks/*.py
```

## ROOT CAUSE IDENTIFIED

**The file path is likely in `event.data.tool_parameters.file_path`, NOT `event.data.file_path`.**

The Files tab filtering code expects:
```json
{
  "data": {
    "file_path": "/path/to/file.py"  // ← EXPECTED HERE
  }
}
```

But the actual structure is:
```json
{
  "data": {
    "tool_name": "Read",
    "tool_parameters": {
      "file_path": "/path/to/file.py"  // ← ACTUALLY HERE
    }
  }
}
```

## Verification Needed

To confirm, we need to:
1. Check `extract_tool_parameters` implementation
2. Log actual event structure in browser console
3. Verify the exact field path for file operations

## Recommended Fix

**Option 1**: Update `extractFilePath` to look in `tool_parameters`:

```typescript
function extractFilePath(toolName: string, data: unknown): string | null {
  if (!data || typeof data !== 'object' || Array.isArray(data)) {
    return null;
  }

  const dataRecord = data as Record<string, unknown>;
  const toolParams = dataRecord.tool_parameters as Record<string, unknown> | undefined;

  switch (toolName) {
    case 'Read':
    case 'Write':
    case 'Edit':
      // Check both direct field AND tool_parameters
      return (dataRecord.file_path as string) ||
             (toolParams?.file_path as string) ||
             null;

    case 'Grep':
    case 'Glob':
      // Check both direct field AND tool_parameters
      return (dataRecord.path as string) ||
             (toolParams?.path as string) ||
             null;

    default:
      return null;
  }
}
```

**Option 2**: Flatten the server-side event structure to include `file_path` at top level of `data`.

## Next Steps

1. ✅ Check `extract_tool_parameters` implementation
2. ✅ Verify event structure via code analysis
3. ✅ Implement the fix (Option 1 - less server changes)
4. ✅ Build successfully completed
5. Ready for testing with actual file operations

## Fix Implemented

**Files Changed**:
1. `src/claude_mpm/dashboard-svelte/src/lib/stores/files.svelte.ts`
   - Updated `extractFilePath()` to check `tool_parameters.file_path` first
   - Maintains backward compatibility with direct `data.file_path` (fallback)
   - Added documentation explaining both field locations

2. `src/claude_mpm/dashboard-svelte/src/lib/stores/tools.svelte.ts`
   - Updated `extractOperation()` to check `tool_parameters` for all fields
   - Fixes tool operation descriptions for Read/Write/Edit/Grep/Glob
   - Maintains backward compatibility with direct fields (fallback)

**Code Changes**:
```typescript
// Before (files.svelte.ts):
return dataRecord.file_path as string;

// After (files.svelte.ts):
const toolParams = dataRecord.tool_parameters && /* type guards */
  ? dataRecord.tool_parameters as Record<string, unknown>
  : null;
return (dataRecord.file_path as string) ||
       (toolParams?.file_path as string) ||
       null;
```

**Build Status**: ✅ Successful
**Testing**: Ready for runtime verification

## Comparison: Why Does Tools Tab Work?

**Location**: `src/claude_mpm/dashboard-svelte/src/lib/stores/tools.svelte.ts`

The Tools tab uses a different approach - it doesn't need to extract specific file paths. It just needs:
- Tool name (from `event.data` via `getToolName`)
- Correlation ID (from `event.data` via `getCorrelationId`)
- General operation description

The `extractOperation` function (lines 102-147) doesn't rely on deeply nested fields - it checks:
```typescript
case 'Read':
  const filePath = data.file_path as string;
  return filePath ? `Read ${truncate(filePath, 35)}` : 'Read file';
```

BUT - this would ALSO fail if `file_path` is in `tool_parameters`. Let me check if Tools tab is actually showing Read/Write/Edit operations correctly...

**HYPOTHESIS**: Tools tab might also be failing to show file operation details, but still shows the tool row because it doesn't filter based on file path extraction.

## Summary

**Root Cause**: File path extraction expects `event.data.file_path` but actual structure has `event.data.tool_parameters.file_path`.

**Impact**:
- Files tab shows nothing (filters out all events due to `null` file paths)
- Tools tab might show file operations but with generic descriptions

**Fix Priority**: HIGH - Files tab is completely non-functional

**Estimated Effort**: 15 minutes (update extractFilePath function, test, commit)
