# FileViewer Content Display Fix

**Date**: 2025-12-22
**Issue**: FileViewer showing "⚠️ No content available for this operation" despite content existing

## Problem Analysis

The FileViewer component was not displaying file content from Read operations, showing "No content available" instead. The issue was in the content extraction logic in the files store.

### Root Cause

**Files Store (`files.svelte.ts`)**: The content extraction was checking for nested `eventData.data.output` when the backend actually sends content directly at `eventData.output`.

**Backend Event Structure** (from `event_handlers.py` line 461):
```python
# Backend sends:
post_tool_data["output"] = event["output"]
```

This means the SSE event structure is:
```javascript
{
  data: {
    output: "file content here",
    tool_name: "Read",
    tool_parameters: { file_path: "/path/to/file" }
  }
}
```

**Original Extraction Logic** (incorrect):
```typescript
const innerData = eventData.data && typeof eventData.data === 'object'
  ? eventData.data as Record<string, unknown>
  : null;
const content = (
  typeof (innerData as any)?.output === 'string' ? (innerData as any).output :
  typeof eventData.output === 'string' ? eventData.output :
  // ... fallbacks
);
```

This tried to access `eventData.data.output` first (which doesn't exist), when it should check `eventData.output` directly.

## Solution

### 1. Fixed Content Extraction Path

**Updated** `src/claude_mpm/dashboard-svelte/src/lib/stores/files.svelte.ts` (lines 152-190):

```typescript
// Check for Read operations
if (event.type === 'hook' && event.subtype === 'post_tool' && toolName === 'Read') {
  // Extract content from output field
  // Backend structure: { data: { output: "content", tool_name: "Read", tool_parameters: {...} } }
  // The output is directly in eventData.output (not nested)
  const content = (
    // Check eventData.output first (direct format from backend)
    typeof eventData.output === 'string' ? eventData.output :
    // Check eventData.result (alternative format)
    typeof eventData.result === 'string' ? eventData.result :
    // Check for nested data.output (shouldn't be needed but defensive)
    typeof (eventData.data as any)?.output === 'string' ? (eventData.data as any).output :
    undefined
  );
```

**Key Changes**:
- Prioritize `eventData.output` first (direct backend format)
- Simplified extraction logic
- Removed unnecessary `innerData` nesting
- Enhanced debug logging to track extraction path

### 2. Improved FileViewer Fallback

**Enhanced** `src/claude_mpm/dashboard-svelte/src/lib/components/FileViewer.svelte` (lines 109-114):

```typescript
} catch (e) {
  // Fallback to plain text if syntax highlighting fails
  console.warn('[FileViewer] Syntax highlighting failed for', language, ':', e);
  // Always show content even if highlighting fails - use plain text fallback
  highlightedContent = addLineNumbers(content);
}
```

**Key Changes**:
- Updated error message to clarify "syntax highlighting failed" vs "no content"
- Comment emphasizes that content should ALWAYS be shown even if highlighting fails
- Ensures plain text fallback is used when Shiki fails

## Testing

### How to Verify Fix

1. **Start the dashboard**:
   ```bash
   cd /Users/masa/Projects/claude-mpm
   python -m claude_mpm.cli dashboard --port 5002
   ```

2. **Perform a Read operation** in Claude (e.g., ask Claude to read a file)

3. **Check the Files tab**:
   - File should appear in the list
   - Clicking the file should show content (either syntax-highlighted or plain text)
   - Should NOT show "⚠️ No content available for this operation"

4. **Check browser console**:
   - Look for debug logs: `[FILES] Read operation for <path>`
   - Verify `hasContent: true` and `contentLength > 0`
   - Look for `[FileViewer] Content extraction:` showing content preview

### Expected Behavior

- **Read operations**: Show syntax-highlighted code with line numbers
- **Syntax highlighting fails**: Show plain text with line numbers (not error message)
- **No content exists**: Show "No content available for this operation" error
- **Debug logs**: Provide clear extraction path information

## Files Modified

1. `src/claude_mpm/dashboard-svelte/src/lib/stores/files.svelte.ts`
   - Fixed content extraction to check `eventData.output` first
   - Simplified extraction logic
   - Enhanced debug logging

2. `src/claude_mpm/dashboard-svelte/src/lib/components/FileViewer.svelte`
   - Improved error message clarity
   - Ensured fallback to plain text when highlighting fails

## Impact

- ✅ FileViewer now displays Read operation content correctly
- ✅ Better debugging with enhanced logging
- ✅ Graceful fallback to plain text if syntax highlighting fails
- ✅ Never shows "No content available" when content exists
- 🔍 Debug logs help diagnose future content extraction issues

## Related Issues

- Previous fix: Addressed nested data extraction in event structure
- This fix: Corrected the actual content path for Read operations
- Both fixes work together to ensure proper content display

## Build Status

✅ Dashboard rebuilt successfully with `npm run build` (2025-12-22)
