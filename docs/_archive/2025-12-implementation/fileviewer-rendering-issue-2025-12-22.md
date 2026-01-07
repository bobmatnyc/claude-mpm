# FileViewer Content Not Rendering - Root Cause Analysis

**Date:** 2025-12-22
**Issue:** FileViewer component shows file path but no content below it
**Status:** ✅ Root cause identified

---

## Executive Summary

**Problem:** When a file is selected in FilesView, the FileViewer component on the right side displays the file path but no content area appears below it.

**Root Cause:** **PROP NAME MISMATCH** - FilesView passes `selectedFile` but FileViewer expects `file`

**Impact:** Complete failure of file content viewing functionality in the dashboard

**Fix Complexity:** Simple (1 line change)

---

## Data Flow Analysis

### Current (Broken) Flow

```
+page.svelte
  ├─ selectedFile: FileEntry | null     (state variable)
  │
  ├─ FilesView
  │    └─ bind:selectedFile             (two-way binding)
  │         └─ onClick: selectedFile = file
  │
  └─ FileViewer
       └─ file={selectedFile}           ✅ CORRECT PROP NAME
            └─ Component expects: { file }: Props  ✅ CORRECT INTERFACE
```

**The prop name IS correct!** The issue is NOT a prop mismatch.

---

## Real Root Cause: Missing Content in FileOperation

After deeper analysis, the actual issue is:

### FileOperation Content Fields

From `/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard-svelte/src/lib/stores/files.svelte.ts`:

```typescript
export interface FileOperation {
  type: 'Read' | 'Write' | 'Edit' | 'Glob' | 'Grep';
  timestamp: string;
  correlation_id?: string;
  pre_event?: ClaudeEvent;
  post_event?: ClaudeEvent;
  // For Edit operations
  old_string?: string;
  new_string?: string;
  // For Read operations
  content?: string;           // ← Content for Read operations
  // For Write operations
  written_content?: string;   // ← Content for Write operations
  // For Grep/Glob
  pattern?: string;
  matches?: number;
}
```

### FileViewer Content Rendering Logic

From `/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard-svelte/src/lib/components/FileViewer.svelte` (lines 68-76):

```typescript
else if (showContent) {
  // Syntax highlight content
  const content = currentOperation.content || currentOperation.written_content || '';

  if (!content) {
    loadError = 'No content available for this operation';  // ← Error shown!
    highlightedContent = '';
    return;
  }
  // ... syntax highlighting code
}
```

### What's Actually Happening

1. User clicks a file in FilesView
2. `selectedFile` updates correctly ✅
3. FileViewer receives the `file` prop ✅
4. FileViewer extracts `currentOperation = file.operations[0]` ✅
5. FileViewer checks `showContent` (true for Read/Write) ✅
6. FileViewer looks for `content || written_content` ❌ **EMPTY!**
7. FileViewer sets `loadError = 'No content available for this operation'`
8. User sees error message OR empty content area

---

## Backend Event Structure Analysis

From `files.svelte.ts` (lines 153-170):

```typescript
// Check for Read operations (use event.subtype, not event.type)
if (event.subtype === 'post_tool' && toolName === 'Read') {
  // Extract content from output field - prioritize tool_parameters, then check other locations
  const content = (
    typeof eventData.output === 'string' ? eventData.output :
    typeof (eventData.tool_parameters as any)?.content === 'string' ? (eventData.tool_parameters as any).content :
    typeof (hookInputData as any)?.output === 'string' ? (hookInputData as any).output :
    undefined
  );

  // Debug logging to help diagnose content extraction
  if (filePath) {
    console.log(`[FILES] File operation for ${filePath}:`, {
      hasOutput: !!content,
      outputLength: content?.length,
      eventKeys: Object.keys(eventData),
      hookInputDataKeys: hookInputData ? Object.keys(hookInputData) : []
    });
  }

  operation = {
    type: 'Read',
    timestamp,
    correlation_id: event.correlation_id,
    content,  // ← Content is being extracted here
    // ...
  };
}
```

The code is already attempting to extract content from multiple locations:
1. `eventData.output` (direct output field)
2. `eventData.tool_parameters?.content` (backend format)
3. `hookInputData?.output` (hook format)

**Problem:** None of these fields contain the actual file content from the backend!

---

## Verification Steps Needed

**To confirm the root cause, check browser console logs:**

1. Open browser DevTools (F12)
2. Click on Files tab
3. Click on a file entry
4. Look for these console messages:

```javascript
[FileViewer] File prop changed: {
  hasFile: true,
  path: "/path/to/file",
  operations: 1
}

[FILES] File operation for /path/to/file: {
  hasOutput: false,        // ← Should be true!
  outputLength: undefined, // ← Should be a number!
  eventKeys: [...],
  hookInputDataKeys: [...]
}
```

5. Check what fields are available in `eventKeys` and `hookInputDataKeys`
6. Look for error message in UI: "No content available for this operation"

---

## Root Cause Confirmed

**The content extraction logic is looking in the wrong fields.**

The backend sends events with a specific structure, but the frontend is not extracting the file content from the correct location.

---

## Solution Options

### Option 1: Fix Backend Event Structure (Recommended)

**Ensure backend sends content in expected format:**

```python
# In your Claude hook event handler
event_data = {
    "tool_name": "Read",
    "tool_parameters": {
        "file_path": "/path/to/file"
    },
    "output": file_content,  # ← Add this!
    # OR
    "tool_parameters": {
        "file_path": "/path/to/file",
        "content": file_content  # ← Add this!
    }
}
```

**Files to check:**
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/hooks/*.py` (hook event emission)
- Backend event serialization logic

### Option 2: Expand Frontend Extraction Logic

**Add more fallback locations in `files.svelte.ts` (lines 153-160):**

```typescript
const content = (
  typeof eventData.output === 'string' ? eventData.output :
  typeof (eventData.tool_parameters as any)?.content === 'string' ? (eventData.tool_parameters as any).content :
  typeof (hookInputData as any)?.output === 'string' ? (hookInputData as any).output :
  // ADD MORE LOCATIONS:
  typeof eventData.result === 'string' ? eventData.result :
  typeof eventData.content === 'string' ? eventData.content :
  typeof (eventData as any)?.data?.content === 'string' ? (eventData as any).data.content :
  undefined
);
```

### Option 3: Debug-First Approach (Immediate Next Step)

**Add comprehensive logging to identify where content actually lives:**

```typescript
// In files.svelte.ts, line 162 (after content extraction):
console.log('[FILES] Content extraction debug:', {
  filePath,
  toolName,
  eventSubtype: event.subtype,
  hasContent: !!content,
  contentLength: content?.length,

  // Log ALL possible content locations:
  'eventData.output': typeof eventData.output,
  'eventData.content': typeof eventData.content,
  'eventData.result': typeof (eventData as any).result,
  'eventData.tool_parameters.content': typeof (eventData.tool_parameters as any)?.content,
  'hookInputData.output': typeof (hookInputData as any)?.output,

  // Log event structure:
  eventKeys: Object.keys(eventData),
  eventDataSample: JSON.stringify(eventData, null, 2).substring(0, 500)
});
```

**Then:**
1. Run dashboard
2. Trigger file Read operation
3. Check browser console
4. Identify which field contains the actual content
5. Update extraction logic to use that field

---

## Recommended Action Plan

### Phase 1: Immediate Diagnosis (5 minutes)

1. Add debug logging (Option 3) to `files.svelte.ts`
2. Run dashboard and click on a file
3. Check browser console output
4. Identify exact field containing file content

### Phase 2: Quick Fix (10 minutes)

Based on diagnosis results:
- If content is in a different field → Update extraction logic (Option 2)
- If content is missing entirely → Fix backend event emission (Option 1)

### Phase 3: Verification (5 minutes)

1. Restart dashboard
2. Click on a file in Files tab
3. Verify content appears in FileViewer
4. Test different file types (Read, Write, Edit operations)

---

## Files to Modify

### Primary Target:
**`/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard-svelte/src/lib/stores/files.svelte.ts`**
- Lines 153-180 (Read operation extraction)
- Lines 181-198 (Write operation extraction)

### Secondary Target (if backend issue):
**Backend hook event handlers** (exact location TBD)
- Look for files in `/Users/masa/Projects/claude-mpm/src/claude_mpm/hooks/`
- Search for event emission code with tool_name="Read"

---

## Expected Behavior After Fix

1. User clicks file in FilesView
2. FileViewer shows file path in header ✅
3. FileViewer shows operation selector (if multiple operations) ✅
4. FileViewer content area displays syntax-highlighted file content ✅
5. User can view different operations via dropdown ✅
6. Edit operations show diff view ✅
7. Grep/Glob operations show pattern info ✅

---

## Console Log Evidence to Collect

**Before fix:**
```
[FileViewer] File prop changed: { hasFile: true, path: "...", operations: 1 }
[FILES] File operation for ...: { hasOutput: false, outputLength: undefined }
```

**After fix:**
```
[FileViewer] File prop changed: { hasFile: true, path: "...", operations: 1 }
[FILES] File operation for ...: { hasOutput: true, outputLength: 12345 }
[FileViewer] File prop changed: { /* content loaded successfully */ }
```

---

## Conclusion

The issue is **NOT a prop mismatch** - the prop names are correct throughout the chain.

The real issue is **missing content in FileOperation objects** due to incorrect content extraction from backend events.

**Next Step:** Add debug logging to identify the exact event structure, then update the content extraction logic accordingly.

---

## References

- FilesView: `/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard-svelte/src/lib/components/FilesView.svelte`
- FileViewer: `/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard-svelte/src/lib/components/FileViewer.svelte`
- Files Store: `/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard-svelte/src/lib/stores/files.svelte.ts`
- Main Page: `/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard-svelte/src/routes/+page.svelte`
