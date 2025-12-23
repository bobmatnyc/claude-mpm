# FileViewer Implementation Summary

## Problem
The FileViewer component was trying to extract file content from hook events, which is inefficient and incomplete. File events only tell us WHICH files were accessed, not their full content.

## Solution
Implemented a proper **server-client architecture** where:

1. **Hook events track file access** (which files were Read/Written/Edited)
2. **Server API serves file content** when the user selects a file
3. **FileViewer fetches on-demand** via the `/api/file` endpoint

## Changes Made

### 1. Backend API (Already Existed)
- `/api/file` endpoint in `server.py` (lines 515-589)
- Accepts POST with `{ path: "/absolute/path" }`
- Returns `{ success: true, content: "file contents", ... }`
- Includes security checks (absolute paths, size limits, text files only)

### 2. Frontend FileViewer Component
**File:** `src/claude_mpm/dashboard-svelte/src/lib/components/FileViewer.svelte`

**Before:**
- Tried to extract content from `currentOperation.content`, `currentOperation.written_content`, `post_event.data.output`, etc.
- Complex nested data extraction logic
- Content might not be available in hook events

**After:**
- Simple `fetchFileContent(filePath)` function that calls `/api/file`
- Fetches current file state from disk when user selects a file
- Cleaner, more reliable architecture

**Key changes:**
```typescript
// Added server API call
async function fetchFileContent(filePath: string): Promise<string> {
  const response = await fetch('/api/file', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path: filePath })
  });

  const data = await response.json();
  return data.content;
}

// Updated effect to fetch from server
$effect(() => {
  if (showContent) {
    const content = await fetchFileContent(file.file_path);
    // ... syntax highlight and display
  }
});
```

### 3. Files Store Cleanup
**File:** `src/claude_mpm/dashboard-svelte/src/lib/stores/files.svelte.ts`

**Changes:**
- Removed content extraction from Read operations
- Removed content extraction from Write operations
- Simplified FileOperation interface
- Added comment: "File content for Read/Write is fetched from server API"

**Before:**
```typescript
// Complex content extraction from events
const content = (
  actualEventData.output ||
  eventData.output ||
  eventData.result ||
  // ... 10 more fallbacks
);
```

**After:**
```typescript
// Simple operation tracking - no content extraction
operation = {
  type: 'Read',
  timestamp,
  correlation_id: event.correlation_id,
  pre_event: event,
  post_event: event
  // Content will be fetched from server when user selects the file
};
```

### 4. Removed Debug Logging
- Removed excessive console.log statements
- Removed visible debug output in UI
- Kept minimal logging for troubleshooting

## Architecture Benefits

### Before (Event-based content extraction)
- ❌ Complex nested data extraction
- ❌ Content might not be in events
- ❌ Large event payloads sent over WebSocket
- ❌ Stale content (snapshot at time of event)

### After (Server API content fetching)
- ✅ Simple, clean API call
- ✅ Always gets current file state from disk
- ✅ Smaller event payloads (just metadata)
- ✅ Fresh content when user views file
- ✅ Security checks (file size, path validation)
- ✅ Clear separation of concerns

## Data Flow

```
1. Claude reads/writes file → Hook emits event
2. Event contains: file_path, tool_name, timestamp
3. Frontend receives event → Updates file list
4. User clicks file → FileViewer fetches content from server
5. Server reads file from disk → Returns content
6. FileViewer renders with syntax highlighting
```

## File Operations

| Operation | Event Data | Content Source |
|-----------|-----------|----------------|
| **Read** | File path, timestamp | Server API (current file) |
| **Write** | File path, timestamp | Server API (current file) |
| **Edit** | old_string, new_string | From event data (for diff) |
| **Grep** | Pattern, matches | Event metadata only |
| **Glob** | Pattern | Event metadata only |

## Testing

1. Start monitor: `mpm monitor`
2. Access files in Claude conversation
3. Check dashboard Files tab
4. Click on a file → Content should load from server
5. Verify syntax highlighting works
6. Check browser console for any errors

## Future Enhancements

### Git History API (Optional)
Add `/api/files/history?path=/path/to/file` to show:
- Git log for the file
- Git diff between versions
- Blame information

Implementation:
```python
async def api_file_history_handler(request):
    path = request.query.get('path')
    result = subprocess.run(
        ['git', 'log', '--oneline', '-10', path],
        capture_output=True,
        text=True
    )
    # Return formatted git history
```

### File Versioning (Optional)
Track file state at each operation timestamp:
- Store snapshots of file content when events occur
- Allow viewing "file as it was when Claude read it"
- Useful for debugging race conditions

## LOC Delta

**Deleted:** ~150 lines
- Removed complex content extraction logic
- Removed debug logging
- Removed unused fields

**Added:** ~20 lines
- `fetchFileContent()` function
- Server API call logic

**Net:** -130 lines ✅

## Related Files

- `src/claude_mpm/services/monitor/server.py` - Backend API (already existed)
- `src/claude_mpm/dashboard-svelte/src/lib/components/FileViewer.svelte` - Updated
- `src/claude_mpm/dashboard-svelte/src/lib/stores/files.svelte.ts` - Simplified

## Build Commands

```bash
# Build Svelte dashboard
cd /Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard-svelte
npm run build

# Copy to static directory
rm -rf ../dashboard/static/svelte-build
cp -R .svelte-kit/output/client ../dashboard/static/svelte-build
```

## Verification

✅ Build successful
✅ No TypeScript errors
✅ Server API endpoint exists
✅ FileViewer fetches from server
✅ Debug logging removed
✅ Clean architecture

---

**Date:** 2025-12-22
**Status:** ✅ Complete and deployed
