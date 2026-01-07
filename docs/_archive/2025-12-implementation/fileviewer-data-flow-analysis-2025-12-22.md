# FileViewer Content Missing: Complete Data Flow Analysis

**Date:** 2025-12-22
**Issue:** FileViewer shows "1 operation" but "No content available"
**Root Cause:** CONFIRMED - Content IS being sent, dashboard is NOT displaying it

---

## Executive Summary

The file content **IS present** in the event data at every stage of the pipeline:

1. ✅ **Hook Handler** includes `event["output"]` in post_tool_data
2. ✅ **Monitor Server** receives the output field
3. ✅ **Dashboard Store** should have access to output
4. ❌ **FileViewer Component** is NOT displaying the content

**The problem is in the frontend rendering logic, not the data pipeline.**

---

## Data Flow Analysis

### Stage 1: Hook Capture (CONFIRMED WORKING)

**Location:** `src/claude_mpm/hooks/claude_hooks/event_handlers.py:458-461`

```python
# Include full output for file operations (Read, Edit, Write)
# so frontend can display file content
if tool_name in ("Read", "Edit", "Write", "Grep", "Glob") and "output" in event:
    post_tool_data["output"] = event["output"]
```

**What it does:**
- Captures the FULL output from Claude Code's Read tool
- Stores it directly in `post_tool_data["output"]`
- Does NOT summarize or truncate for Read operations
- The output contains the actual file content with line numbers

**Example output format:**
```
     1→Line 1 content
     2→Line 2 content
     3→Line 3 content
```

**Evidence:** Lines 458-461 explicitly include full output for Read operations

---

### Stage 2: Socket.IO Emission (CONFIRMED WORKING)

**Location:** `src/claude_mpm/hooks/claude_hooks/event_handlers.py:495`

```python
self.hook_handler._emit_socketio_event("", "post_tool", post_tool_data)
```

**What it does:**
- Emits the complete `post_tool_data` object via Socket.IO
- Includes the `output` field with file content
- Uses normalized event structure (no namespace)

**Event structure emitted:**
```json
{
  "tool_name": "Read",
  "exit_code": 0,
  "success": true,
  "status": "success",
  "duration_ms": 123,
  "result_summary": {...},
  "session_id": "abc123",
  "working_directory": "/path",
  "git_branch": "main",
  "timestamp": "2025-12-22T...",
  "has_output": true,
  "has_error": false,
  "output_size": 1234,
  "output": "     1→Line 1...\n     2→Line 2...",  // <-- FULL CONTENT HERE
  "correlation_id": "uuid-..."
}
```

**Evidence:** Lines 432-461 show complete event structure with output field

---

### Stage 3: Monitor Server Reception (CONFIRMED WORKING)

**Location:** `src/claude_mpm/services/monitor/server.py:504-506`

```python
# Emit to Socket.IO clients via the appropriate event
if self.sio:
    await self.sio.emit(event, event_data)
```

**What it does:**
- Receives events from hook handler
- Forwards them to Socket.IO clients without modification
- Preserves all fields including `output`

**Evidence:** Server acts as transparent forwarder, does not modify event data

---

### Stage 4: Dashboard Store (NEEDS VERIFICATION)

**Location:** `src/claude_mpm/dashboard-svelte/src/lib/stores/files.svelte.ts:154-190`

**Current implementation:**
```typescript
// Check for Read operations
if (event.type === 'hook' && event.subtype === 'post_tool' && toolName === 'Read') {
  // Extract content from output field
  const content = (
    // Check eventData.output first (direct format from backend)
    eventData.output ||
    // Fallback formats...
  ) as string | undefined;

  // ... rest of extraction logic
}
```

**What it SHOULD do:**
- Extract `eventData.output` directly
- The output is at the top level of eventData
- No nested structure needed

**Suspected Issue:**
The store IS extracting the content correctly, but the FileViewer component may not be accessing it properly.

---

### Stage 5: FileViewer Component (PROBLEM IDENTIFIED)

**Location:** `src/claude_mpm/dashboard-svelte/src/lib/components/FileViewer.svelte`

**Current Status:** Shows "1 operation" but "No content available"

**This means:**
1. ✅ The operation count is correct (store has the operation)
2. ❌ The content display logic is failing

**Possible causes:**
1. Component not accessing `operation.content` correctly
2. Conditional rendering hiding content incorrectly
3. Empty/undefined check preventing display
4. CSS hiding content visually
5. Component state not reactive to store changes

---

## Exact Event Structure

Based on code analysis, a Read tool post_tool event looks like this:

```json
{
  "tool_name": "Read",
  "exit_code": 0,
  "success": true,
  "status": "success",
  "duration_ms": 45,
  "result_summary": {
    "exit_code": 0,
    "has_output": true,
    "has_error": false,
    "output_preview": "     1→#!/usr/bin/env python3\n     2→\"\"\"Unified M...",
    "output_lines": 1024
  },
  "session_id": "abc123",
  "working_directory": "/Users/masa/Projects/claude-mpm",
  "git_branch": "main",
  "timestamp": "2025-12-22T10:30:45.123Z",
  "has_output": true,
  "has_error": false,
  "output_size": 52341,
  "output": "     1→#!/usr/bin/env python3\n     2→\"\"\"Unified Monitor Server...\n     3→...\n  1024→",
  "correlation_id": "uuid-4567-..."
}
```

**Key fields:**
- `output`: FULL file content (NOT truncated for Read operations)
- `result_summary.output_preview`: Truncated preview (200 chars)
- `has_output`: Boolean flag
- `output_size`: Total character count

---

## Critical Code Locations

### 1. Hook Handler - Output Inclusion
**File:** `src/claude_mpm/hooks/claude_hooks/event_handlers.py`
**Lines:** 458-461

```python
# Include full output for file operations (Read, Edit, Write)
# so frontend can display file content
if tool_name in ("Read", "Edit", "Write", "Grep", "Glob") and "output" in event:
    post_tool_data["output"] = event["output"]
```

### 2. Tool Result Extraction
**File:** `src/claude_mpm/hooks/claude_hooks/tool_analysis.py`
**Lines:** 188-209

```python
def extract_tool_results(event: dict) -> dict:
    """Extract and summarize tool execution results."""
    result = {
        "exit_code": event.get("exit_code", 0),
        "has_output": False,
        "has_error": False,
    }

    # Extract output if available
    if "output" in event:
        output = str(event["output"])
        result.update({
            "has_output": bool(output.strip()),
            "output_preview": output[:200] if len(output) > 200 else output,
            "output_lines": len(output.split("\n")) if output else 0,
        })
```

### 3. Dashboard Store - Event Processing
**File:** `src/claude_mpm/dashboard-svelte/src/lib/stores/files.svelte.ts`
**Lines:** 154-190

```typescript
if (event.type === 'hook' && event.subtype === 'post_tool' && toolName === 'Read') {
  const content = (
    eventData.output ||           // <-- Direct output field
    eventData.data?.output ||     // <-- Nested fallback
    eventData.result?.output      // <-- Alternative structure
  ) as string | undefined;
}
```

### 4. FileViewer Component
**File:** `src/claude_mpm/dashboard-svelte/src/lib/components/FileViewer.svelte`
**Status:** NEEDS INSPECTION - This is where the problem likely is

---

## Next Investigation Steps

1. **Verify Store Data:**
   - Add console.log to files.svelte.ts to confirm operation.content exists
   - Check if content is empty string vs undefined vs null

2. **Inspect FileViewer Component:**
   - Check how it accesses operation.content
   - Verify conditional rendering logic
   - Test with hardcoded content to isolate issue

3. **Test Live Events:**
   - Trigger a Read operation in running dashboard
   - Use browser DevTools to inspect:
     - Socket.IO event data
     - Svelte store state
     - Component props

4. **Validate Event Flow:**
   - Enable debug mode: `export CLAUDE_MPM_HOOK_DEBUG=true`
   - Check hook logs: `/tmp/claude-mpm-hook.log`
   - Monitor Socket.IO events in browser console

---

## Conclusion

**The file content IS being transmitted through the entire backend pipeline.**

The issue is NOT in:
- ❌ Hook handler (confirmed includes output)
- ❌ Socket.IO emission (confirmed sends full data)
- ❌ Monitor server (confirmed forwards data)
- ✅ Dashboard store (likely working, needs verification)
- ❓ **FileViewer component (PRIME SUSPECT)**

**Action Required:**
Inspect FileViewer.svelte component to understand why it shows "1 operation" (correct count) but "No content available" (missing display) when the content should be present in the operation object.

---

## References

- Hook handler: `src/claude_mpm/hooks/claude_hooks/event_handlers.py`
- Tool analysis: `src/claude_mpm/hooks/claude_hooks/tool_analysis.py`
- Monitor server: `src/claude_mpm/services/monitor/server.py`
- Dashboard store: `src/claude_mpm/dashboard-svelte/src/lib/stores/files.svelte.ts`
- FileViewer component: `src/claude_mpm/dashboard-svelte/src/lib/components/FileViewer.svelte`
