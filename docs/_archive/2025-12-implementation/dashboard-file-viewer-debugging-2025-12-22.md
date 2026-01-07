# Dashboard File Viewer Deep Investigation

**Date**: 2025-12-22
**Status**: Root cause identified - Data structure mismatch
**Severity**: Critical - Complete feature failure

## Problem Statement

The dashboard file viewer is completely broken - no files are showing despite file operations being performed.

## Investigation Results

### Backend Event Flow (WORKING)

#### 1. Hook Event Capture
**File**: `src/claude_mpm/hooks/claude_hooks/event_handlers.py`

When Claude performs a Read operation:

```python
# Line 125-192: handle_pre_tool_fast
pre_tool_data = {
    "tool_name": "Read",
    "operation_type": "read",
    "tool_parameters": {
        "file_path": "/path/to/file.py"  # ← File path is here
    },
    "session_id": "session-123",
    "working_directory": "/Users/masa/Projects/...",
    "correlation_id": "uuid-...",
    # ... other fields
}
```

#### 2. Event Emission
**File**: `src/claude_mpm/hooks/claude_hooks/services/connection_manager.py`

Events are wrapped in a normalized structure:

```python
# Line 122-134
raw_event = {
    "type": "hook",
    "subtype": "pre_tool",  # ← Event subtype
    "timestamp": "2025-12-22T...",
    "data": pre_tool_data,  # ← Contains tool_parameters with file_path
    "source": "claude_hooks",
    "session_id": "session-123",
    "correlation_id": "uuid-..."
}

# Normalized and emitted as "claude_event"
normalized_event = normalizer.normalize(raw_event, source="hook")
emit("claude_event", normalized_event.to_dict())
```

#### 3. Socket.IO Emission
**File**: `src/claude_mpm/services/socketio/dashboard_server.py`

Dashboard server relays events from monitor:

```python
# Line 154-171: Events relayed from monitor to dashboard
relay_events = [
    "pre_tool",  # ← Relayed
    "post_tool", # ← Relayed
    # ... other events
]
```

**Backend event structure emitted to frontend:**

```json
{
  "event": "claude_event",
  "type": "hook",
  "subtype": "pre_tool",
  "timestamp": "2025-12-22T10:30:00Z",
  "data": {
    "tool_name": "Read",
    "tool_parameters": {
      "file_path": "/Users/masa/Projects/claude-mpm/src/file.py"
    },
    "session_id": "abc-123",
    "correlation_id": "uuid-456"
  },
  "correlation_id": "uuid-456"
}
```

### Frontend Event Processing (BROKEN)

#### 1. Socket Event Reception
**File**: `src/claude_mpm/dashboard-svelte/src/lib/stores/socket.svelte.ts`

Frontend listens for events:

```typescript
// Line 163-171: Event type listeners
const eventTypes = ['claude_event', 'hook_event', 'cli_event', ...];

eventTypes.forEach(eventType => {
  newSocket.on(eventType, (data: ClaudeEvent) => {
    handleEvent({ ...data, event: eventType }); // ← Data arrives here
  });
});
```

#### 2. Files Store Processing
**File**: `src/claude_mpm/dashboard-svelte/src/lib/stores/files.svelte.ts`

**THE PROBLEM IS HERE** - Line 96-130:

```typescript
// Line 96-109: Looking for hook_input_data (WRONG!)
const hookInputData = eventData.hook_input_data && // ← DOES NOT EXIST!
                      typeof eventData.hook_input_data === 'object'
  ? eventData.hook_input_data as Record<string, unknown>
  : null;

const hookParams = hookInputData?.params && // ← NULL because hookInputData is null
                   typeof hookInputData.params === 'object'
  ? hookInputData.params as Record<string, unknown>
  : null;

// Line 118-125: File path extraction (FAILS!)
const filePath = (
  hookParams?.file_path ||      // ← NULL (no hookParams)
  hookParams?.path ||
  toolParams?.file_path ||      // ← NULL (no tool_parameters at root)
  toolParams?.path ||
  eventData.file_path ||        // ← NULL (not at root)
  eventData.path
) as string | undefined;

// Result: filePath = undefined → No files displayed!
```

## Root Cause Analysis

### Data Structure Mismatch

**Backend sends:**
```json
{
  "data": {
    "tool_parameters": {
      "file_path": "/path/to/file"
    }
  }
}
```

**Frontend expects:**
```json
{
  "data": {
    "hook_input_data": {
      "params": {
        "file_path": "/path/to/file"
      }
    }
  }
}
```

### Why This Happened

The frontend was written expecting a different event structure (`hook_input_data.params`) but the backend emits events with `tool_parameters` at the top level of `data`.

This is a **legacy compatibility issue** - the frontend code was likely written for an older event format that has since been refactored.

## The Fix

### Option 1: Update Frontend (RECOMMENDED)

Fix the file path extraction in `files.svelte.ts`:

```typescript
// Line 118-125: CORRECT extraction
const filePath = (
  eventData.tool_parameters?.file_path ||  // ← Check data.tool_parameters first
  eventData.tool_parameters?.path ||
  hookParams?.file_path ||                 // Keep legacy support
  hookParams?.path ||
  eventData.file_path ||
  eventData.path
) as string | undefined;
```

### Option 2: Update Backend (NOT RECOMMENDED)

Change event structure to match frontend expectations - this would break other consumers.

## Additional Issues Found

### 1. Tool Name Extraction
**File**: `files.svelte.ts` Line 133

```typescript
const toolName = (hookInputData?.tool_name || eventData.tool_name) as string | undefined;
```

Should be:
```typescript
const toolName = (eventData.tool_name || hookInputData?.tool_name) as string | undefined;
```

Because `tool_name` is at `data.tool_name`, not inside `hook_input_data`.

### 2. Content Extraction for Read Operations
**File**: `files.svelte.ts` Line 148-160

```typescript
// Check for Read operations (use event.subtype, not event.type)
if (event.subtype === 'post_tool' && toolName === 'Read') {
  // Extract content from output field - check multiple possible locations
  const content = (
    typeof eventData.output === 'string'
      ? eventData.output
      : typeof hookInputData?.output === 'string'
        ? (hookInputData.output as string)
        : // ... more fallbacks
  );
}
```

This should work IF `eventData.output` exists. Need to verify backend includes it.

**Backend code** (event_handlers.py Line 460-461):
```python
# Include full output for file operations (Read, Edit, Write)
if tool_name in ("Read", "Edit", "Write", "Grep", "Glob") and "output" in event:
    post_tool_data["output"] = event["output"]
```

✅ Backend does include `output` field in `post_tool_data`.

## Complete Event Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. Claude Code executes Read('/path/to/file.py')                │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. Hook Handler (event_handlers.py)                             │
│    - handle_pre_tool_fast() captures tool call                  │
│    - Extracts: tool_name, tool_parameters, file_path            │
│    - Creates pre_tool_data with tool_parameters.file_path       │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. Connection Manager (connection_manager.py)                   │
│    - Wraps in normalized structure:                             │
│      {                                                           │
│        type: "hook",                                            │
│        subtype: "pre_tool",                                     │
│        data: { tool_parameters: { file_path: "..." } }          │
│      }                                                           │
│    - Emits as "claude_event"                                    │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. Dashboard Server (dashboard_server.py)                       │
│    - Receives from monitor server                               │
│    - Relays "pre_tool" event to dashboard clients               │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. Frontend Socket Store (socket.svelte.ts)                     │
│    - Listens on "claude_event"                                  │
│    - Receives event and adds to events store                    │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 6. Files Store (files.svelte.ts) ❌ BREAKS HERE                 │
│    - Derived store processes events                             │
│    - Looks for: eventData.hook_input_data.params.file_path      │
│    - REALITY:   eventData.tool_parameters.file_path             │
│    - Result: filePath = undefined → No files displayed!         │
└─────────────────────────────────────────────────────────────────┘
```

## Specific Fix Required

**File**: `src/claude_mpm/dashboard-svelte/src/lib/stores/files.svelte.ts`

### Lines to Change

#### Change 1: File Path Extraction (Line 118-125)

**BEFORE:**
```typescript
const filePath = (
  hookParams?.file_path ||      // ← Null because hookParams is null
  hookParams?.path ||
  toolParams?.file_path ||      // ← Null because toolParams looks at wrong location
  toolParams?.path ||
  eventData.file_path ||
  eventData.path
) as string | undefined;
```

**AFTER:**
```typescript
const filePath = (
  eventData.tool_parameters?.file_path ||  // ← PRIORITY 1: Check data.tool_parameters
  eventData.tool_parameters?.path ||
  hookParams?.file_path ||                 // Legacy support
  hookParams?.path ||
  toolParams?.file_path ||
  toolParams?.path ||
  eventData.file_path ||
  eventData.path
) as string | undefined;
```

#### Change 2: Tool Name Extraction (Line 133)

**BEFORE:**
```typescript
const toolName = (hookInputData?.tool_name || eventData.tool_name) as string | undefined;
```

**AFTER:**
```typescript
const toolName = (eventData.tool_name || hookInputData?.tool_name) as string | undefined;
```

#### Change 3: Parameter Extraction for Write/Edit Operations

**Lines 184, 198-199:**

**BEFORE:**
```typescript
// Write operation
const content = (hookParams?.content || toolParams?.content) as string | undefined;

// Edit operation
const oldString = (hookParams?.old_string || toolParams?.old_string) as string | undefined;
const newString = (hookParams?.new_string || toolParams?.new_string) as string | undefined;
```

**AFTER:**
```typescript
// Write operation
const content = (
  eventData.tool_parameters?.content ||
  hookParams?.content ||
  toolParams?.content
) as string | undefined;

// Edit operation
const oldString = (
  eventData.tool_parameters?.old_string ||
  hookParams?.old_string ||
  toolParams?.old_string
) as string | undefined;
const newString = (
  eventData.tool_parameters?.new_string ||
  hookParams?.new_string ||
  toolParams?.new_string
) as string | undefined;
```

#### Change 4: Pattern Extraction for Grep/Glob (Lines 214, 228)

**BEFORE:**
```typescript
// Grep
const pattern = (hookParams?.pattern || toolParams?.pattern) as string | undefined;

// Glob
const pattern = (hookParams?.pattern || toolParams?.pattern) as string | undefined;
```

**AFTER:**
```typescript
// Grep
const pattern = (
  eventData.tool_parameters?.pattern ||
  hookParams?.pattern ||
  toolParams?.pattern
) as string | undefined;

// Glob
const pattern = (
  eventData.tool_parameters?.pattern ||
  hookParams?.pattern ||
  toolParams?.pattern
) as string | undefined;
```

## Expected Outcome After Fix

1. ✅ File paths extracted correctly from `data.tool_parameters.file_path`
2. ✅ Tool names extracted correctly from `data.tool_name`
3. ✅ File operations (Read/Write/Edit/Grep/Glob) captured correctly
4. ✅ Files appear in dashboard file viewer with operation history
5. ✅ File content displayed for Read operations
6. ✅ Edit diffs shown for Edit operations
7. ✅ Search patterns shown for Grep/Glob operations

## Testing Plan

After applying the fix:

1. **Start dashboard**: `mpm dashboard`
2. **Run Claude Code**: Perform file operations (Read, Write, Edit)
3. **Check browser console**: Look for `[FILES]` debug logs
4. **Verify file list**: Files should appear in dashboard
5. **Check file details**: Click file to see operations and content

## Notes

- Backend event structure is correct and consistent
- Frontend was expecting legacy/different event format
- This is purely a frontend data extraction bug
- No backend changes required
- Fix is straightforward - update field access paths
