# Debug Event Logging - File Content Extraction

## Problem
The Files Store shows "NO CONTENT" for Read operations even though content exists in events.

## Solution Applied
Added comprehensive raw event logging to `files.svelte.ts` to diagnose the exact event structure.

## What to Look For in Browser Console

When you run the dashboard and see file Read operations, look for these console logs:

### 1. Raw Event Structure
```
🔴 RAW EVENT: { ... full JSON ... }
🔴 EVENT KEYS: ["type", "subtype", "data", "timestamp", ...]
🔴 EVENT.DATA: { ... }
🔴 EVENT.DATA KEYS: ["output", "tool_name", "tool_parameters", ...]
🔴 EVENT.TYPE: "hook"
🔴 EVENT.SUBTYPE: "post_tool"
```

### 2. Nested Data Check (for Read operations)
```
🔴 CHECKING NESTED DATA:
🔴 eventData.data exists? true/false
🔴 eventData.data type: object/undefined
🔴 eventData.data keys: [...]
🔴 eventData.data.output? <content or undefined>
🔴 actualEventData === eventData? true/false
🔴 actualEventData.output type: string/undefined
```

### 3. Content Extraction Result
```
[FILES] Read operation for /path/to/file:
  hasContent: true/false
  contentLength: 1234
  contentPreview: "first 100 chars..."
  eventDataKeys: [...]
  eventDataOutput: { exists, type, isString, lengthIfString }
  allPossibleContentFields: { ... }
```

## Expected Event Structure

Based on backend code, we expect:
```json
{
  "type": "hook",
  "subtype": "post_tool",
  "data": {
    "output": "FILE CONTENT HERE",
    "tool_name": "Read",
    "tool_parameters": {
      "file_path": "/absolute/path"
    }
  }
}
```

## Possible Issues to Check

1. **Nested Wrapping**: Is content at `event.data.data.output` instead of `event.data.output`?
2. **Field Name**: Is content in a different field like `result`, `return_value`, `hook_output_data`?
3. **SSE Wrapping**: Does the SSE transport add an extra layer of wrapping?
4. **Type Mismatch**: Is `output` an object instead of a string?

## Next Steps

1. **Start dashboard**: `mpm serve --port 8001`
2. **Open browser console** (F12 or Cmd+Opt+I)
3. **Trigger a Read operation** (navigate to Files tab, file should be read)
4. **Search console** for `🔴 RAW EVENT` to find the exact structure
5. **Copy the raw event JSON** and share it for analysis

## Files Modified
- `src/claude_mpm/dashboard-svelte/src/lib/stores/files.svelte.ts`
  - Added raw event logging at event processing start
  - Added nested data structure checks for Read operations
  - Enhanced content extraction debugging

## Rebuild Command
```bash
cd src/claude_mpm/dashboard-svelte && npm run build
```

## Testing
After rebuilding, the dashboard will emit detailed console logs for every event processed by the Files Store.
