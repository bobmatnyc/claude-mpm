# Dashboard File Viewer Fix

## Problem
The dashboard's Files tab was not displaying file operations because of a data structure mismatch between frontend expectations and backend event format.

### Root Cause
- **Frontend expected**: `eventData.tool_parameters.file_path`
- **Backend provided**: `eventData.hook_input_data.params.file_path`

The files store was only checking `tool_parameters`, missing the actual event structure sent by the backend hooks system.

## Solution

### File Modified
`/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard-svelte/src/lib/stores/files.svelte.ts`

### Changes Made

#### 1. Hook Event Structure Support (lines 96-133)

**Before:**
```typescript
const toolParams = eventData.tool_parameters as Record<string, unknown> | undefined;
const filePath = (eventData.file_path || toolParams?.file_path) as string | undefined;
const toolName = eventData.tool_name as string | undefined;
```

**After:**
```typescript
// Extract hook_input_data (hook event structure from backend)
const hookInputData = eventData.hook_input_data &&
                      typeof eventData.hook_input_data === 'object' &&
                      !Array.isArray(eventData.hook_input_data)
  ? eventData.hook_input_data as Record<string, unknown>
  : null;

// Extract params from hook_input_data
const hookParams = hookInputData?.params &&
                   typeof hookInputData.params === 'object' &&
                   !Array.isArray(hookInputData.params)
  ? hookInputData.params as Record<string, unknown>
  : null;

// Extract tool_parameters (alternative format)
const toolParams = eventData.tool_parameters &&
                   typeof eventData.tool_parameters === 'object' &&
                   !Array.isArray(eventData.tool_parameters)
  ? eventData.tool_parameters as Record<string, unknown>
  : null;

// Extract file path - prioritize hook event format
const filePath = (
  hookParams?.file_path ||      // Hook event format (PRIORITY 1)
  hookParams?.path ||
  toolParams?.file_path ||      // Alternative format
  toolParams?.path ||
  eventData.file_path ||
  eventData.path
) as string | undefined;

// Get tool name (check both hook_input_data and direct field)
const toolName = (hookInputData?.tool_name || eventData.tool_name) as string | undefined;
```

#### 2. Operation Data Extraction (lines 147-218)

Updated all operation type handlers to check `hookParams` first, then fall back to `toolParams`:

**Write Operations:**
```typescript
const content = (hookParams?.content || toolParams?.content) as string | undefined;
```

**Edit Operations:**
```typescript
const oldString = (hookParams?.old_string || toolParams?.old_string) as string | undefined;
const newString = (hookParams?.new_string || toolParams?.new_string) as string | undefined;
```

**Grep/Glob Operations:**
```typescript
const pattern = (hookParams?.pattern || toolParams?.pattern) as string | undefined;
```

## Backend Event Structure Reference

Based on actual backend code (`tests/test_claude_hook_flow.py`):

```typescript
interface PreToolUseEvent {
  hook_event_name: "PreToolUse";
  hook_input_data: {
    tool_name: string;
    params: {
      file_path?: string;      // For Read/Write/Edit
      path?: string;           // Alternative field name
      content?: string;        // For Write
      old_string?: string;     // For Edit
      new_string?: string;     // For Edit
      pattern?: string;        // For Grep/Glob
    };
    tool_id: string;
  };
  // ... other fields
}
```

## Expected Behavior After Fix

The Files tab should now display:
1. **File list** with operation badges (Read, Write, Edit, Grep, Glob)
2. **Syntax highlighted content** (using Shiki - already installed)
3. **Diff viewing** for edit operations (using diff2html - already installed)

## Testing

Build verification:
```bash
cd src/claude_mpm/dashboard-svelte
npm run build  # ✅ Success
```

## Technical Notes

### Why Two Data Structures?

The code now supports both:
1. **Hook event format** (`hook_input_data.params.*`) - Primary format from backend
2. **Tool parameters format** (`tool_parameters.*`) - Alternative/fallback format

This ensures compatibility across different event sources and maintains backwards compatibility.

### Priority Order

The extraction uses a priority fallback chain:
```
hookParams.file_path
  → hookParams.path
    → toolParams.file_path
      → toolParams.path
        → eventData.file_path
          → eventData.path
```

This ensures maximum compatibility while prioritizing the actual backend format.

## Related Files

- `/src/claude_mpm/dashboard-svelte/src/lib/stores/tools.svelte.ts` - Uses similar extraction pattern
- `/tests/test_claude_hook_flow.py` - Backend event structure reference
- `/tests/test_complete_event_flow.py` - Additional event structure examples

## Migration Notes

This fix aligns the files store with the tools store pattern, which already handled the `hook_input_data` structure correctly. Future stores should follow this same pattern for consistency.
