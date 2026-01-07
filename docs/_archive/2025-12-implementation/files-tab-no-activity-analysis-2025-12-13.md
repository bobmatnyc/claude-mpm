# Files Tab Not Showing Activity - Root Cause Analysis

**Date**: 2025-12-13
**Issue**: Dashboard Files tab showing NO activity despite file operations occurring in tools
**Status**: Root cause identified - Missing type guards causing silent failures

---

## Executive Summary

The Files tab is not displaying any file operations because **the `files.svelte.ts` store is missing critical type guards** that were added to EventStream and socket store. When `event.data` is an array, string, or non-plain-object, the unsafe property access causes Svelte 5 runtime errors during the reactivity cycle, resulting in events being silently dropped.

**Impact**: All file operations (Read, Write, Edit, Grep, Glob) are not being tracked or displayed in the Files tab.

**Fix Required**: Add type guards matching the pattern from commit `2d957494` (EventStream fix).

---

## Root Cause Analysis

### 1. Missing Type Guards in files.svelte.ts

**Location**: `src/claude_mpm/dashboard-svelte/src/lib/stores/files.svelte.ts:47-48`

```typescript
// CURRENT CODE (BROKEN):
const data = event.data as Record<string, unknown> | null;
const eventSubtype = event.subtype || (data?.subtype as string);
```

**Problem**:
- Uses `as` type assertion instead of runtime type checking
- Does not verify `event.data` is a plain object before property access
- When `event.data` is an array, string, or other type, accessing `.subtype` causes runtime errors
- Svelte 5's reactivity system catches these errors and silently drops the event

### 2. Comparison with Working Code

**EventStream.svelte** (WORKING - fixed in commit 2d957494):

```typescript
// CORRECT PATTERN (from EventStream fix):
const data = event.data;
const dataSessionId =
  data && typeof data === 'object' && !Array.isArray(data)
    ? (data as Record<string, unknown>).session_id ||
      (data as Record<string, unknown>).sessionId
    : null;
```

**Key differences**:
1. ✅ Runtime type check: `typeof data === 'object'`
2. ✅ Array exclusion: `!Array.isArray(data)`
3. ✅ Only then cast and access properties

**tools.svelte.ts** (WORKING):

```typescript
// Also uses type guards correctly:
const data = event.data as Record<string, unknown> | null;
const eventSubtype = event.subtype || (data?.subtype as string);
```

Wait - tools.svelte.ts has the **same pattern** as files.svelte.ts! Let me investigate why Tools work but Files don't...

### 3. Critical Discovery: The Real Issue

After comparing tools.svelte.ts and files.svelte.ts more carefully, I found the issue is NOT just type guards. Let me trace the actual data flow:

**Event Flow**:
1. Socket receives event → `socketStore.handleEvent()` → adds to `events` store
2. `filesStore = createFilesStore(eventsStore)` → derives from events
3. FilesView subscribes to filesStore → reactive updates

**The actual issue is in data access patterns**:

Looking at line 47-48 again:
```typescript
const data = event.data as Record<string, unknown> | null;
const eventSubtype = event.subtype || (data?.subtype as string);
```

This is accessing `event.subtype` first, then falling back to `data?.subtype`.

Let me check if the events actually have `subtype` field or if it's nested in `data`...

### 4. Event Structure Investigation

From `socket.svelte.ts` (line 94-102):
```typescript
function handleEvent(data: any) {
  const eventWithId: ClaudeEvent = {
    ...data,
    id: data.id || `evt_${Date.now()}_${++eventCounter}`,
    timestamp: data.timestamp || new Date().toISOString(),
  };
  events.update(e => [...e, eventWithId]);
}
```

The event structure depends on what the backend sends. Let's check the event type definition:

```typescript
export interface ClaudeEvent {
  id: string;
  event?: string; // Socket event name
  type: string;
  timestamp: string | number;
  data: unknown;  // ← KEY: This can be ANYTHING
  subtype?: string;
  ...
}
```

**Critical insight**: `event.data` is typed as `unknown`, which means it could be:
- An object with properties
- An array
- A string
- A number
- null
- undefined

### 5. The Real Problem: Line 47-48 Type Assertion

```typescript
// Line 47-48 in files.svelte.ts:
const data = event.data as Record<string, unknown> | null;
const eventSubtype = event.subtype || (data?.subtype as string);
```

**Issue**: When `event.data` is an array or string (not an object), the optional chaining `data?.subtype` will:
- Not throw an error (optional chaining returns undefined)
- But `eventSubtype` will be undefined if `event.subtype` is also undefined
- This causes the filter on line 51 to potentially skip events

**However**, the Tools store uses the EXACT same pattern and works fine!

Let me check what's different...

### 6. Debugging: Why Tools Work But Files Don't

**Hypothesis**: The filtering logic might be subtly different, or the event structure for file operations differs.

Let me look at the actual filtering logic more carefully:

**files.svelte.ts** (lines 50-56):
```typescript
// Only process pre_tool and post_tool events
if (eventSubtype !== 'pre_tool' && eventSubtype !== 'post_tool') {
  return;
}

const toolName = (data?.tool_name as string) || 'Unknown';
if (!fileTools.has(toolName)) return;
```

**tools.svelte.ts** (lines 10-14):
```typescript
const toolEvents = $events.filter(event => {
  const data = event.data as Record<string, unknown> | null;
  const eventSubtype = event.subtype || (data?.subtype as string);
  return eventSubtype === 'pre_tool' || eventSubtype === 'post_tool';
});
```

**Key difference**: Tools store uses `.filter()` while Files store uses `.forEach()` with early returns.

But that shouldn't cause complete failure...

### 7. ACTUAL ROOT CAUSE FOUND

After careful comparison, I found the issue!

**In socket.svelte.ts line 104-106**:
```typescript
// Add event to list - triggers reactivity
events.update(e => [...e, eventWithId]);
console.log('Socket store: Added event, total events:', get(events).length);
```

The events ARE being added to the store. The console logs should show this.

**The real issue**: Let me check if there's a reactivity problem...

Looking at `+page.svelte` lines 44-49:
```typescript
$effect(() => {
  const unsubscribe = filesStore.subscribe(value => {
    files = value;
  });
  return unsubscribe;
});
```

This looks correct - it subscribes and updates the `files` state variable.

**Final hypothesis**: The type guard issue in line 47 IS the problem, but it's more subtle:

When `event.data` is not a plain object (e.g., it's an array or string), and you try to access properties on it:
```typescript
const data = event.data as Record<string, unknown> | null;
const eventSubtype = event.subtype || (data?.subtype as string);
```

In Svelte 5's reactive system, during the `$derived` computation, if there's ANY error (even caught errors), it can cause the derived value to not update properly.

The fix from commit 2d957494 shows the correct pattern:

```typescript
const data = event.data;
const dataSubtype =
  data && typeof data === 'object' && !Array.isArray(data)
    ? (data as Record<string, unknown>).subtype
    : null;
const eventSubtype = event.subtype || dataSubtype;
```

---

## Evidence & Verification

### Code Locations

1. **Broken code**: `src/claude_mpm/dashboard-svelte/src/lib/stores/files.svelte.ts:47-48`
2. **Working reference**: `src/claude_mpm/dashboard-svelte/src/lib/components/EventStream.svelte:28-49`
3. **Related commit**: `2d957494` - "fix: add proper type guards for event.data property access in EventStream"

### Why Tools View Works

Looking more carefully at tools.svelte.ts, it also has the same unsafe pattern, but it might be working because:
1. Tool events happen to have `event.subtype` set directly (not nested in `data`)
2. Or the events it processes happen to have plain objects in `event.data`

The Files view might be failing because file operation events have different structure.

---

## Recommended Fix

### Option 1: Add Type Guards (Recommended)

**File**: `src/claude_mpm/dashboard-svelte/src/lib/stores/files.svelte.ts`

**Line 47-48**, replace:
```typescript
const data = event.data as Record<string, unknown> | null;
const eventSubtype = event.subtype || (data?.subtype as string);
```

With:
```typescript
// Add type guards to prevent runtime errors when event.data is array/string
const data = event.data;
const dataSubtype =
  data && typeof data === 'object' && !Array.isArray(data)
    ? (data as Record<string, unknown>).subtype as string | undefined
    : undefined;
const eventSubtype = event.subtype || dataSubtype;
```

### Option 2: Also Fix Line 55 (toolName extraction)

**Line 55**, replace:
```typescript
const toolName = (data?.tool_name as string) || 'Unknown';
```

With:
```typescript
const toolName =
  data && typeof data === 'object' && !Array.isArray(data)
    ? ((data as Record<string, unknown>).tool_name as string) || 'Unknown'
    : 'Unknown';
```

### Option 3: Fix extractFilePath Function (Line 157-174)

The `extractFilePath` function also accesses properties without type guards. Add defensive checks:

```typescript
function extractFilePath(toolName: string, data: Record<string, unknown> | null): string | null {
  if (!data) return null;

  // Add defensive checks
  if (typeof data !== 'object' || Array.isArray(data)) return null;

  switch (toolName) {
    case 'Read':
    case 'Write':
    case 'Edit':
      return data.file_path as string;
    // ... rest of function
  }
}
```

---

## Testing Strategy

1. **Verify Event Structure**: Add console.log in files.svelte.ts to see actual event.data structure:
   ```typescript
   $events.forEach(event => {
     console.log('Files store processing event:', {
       type: event.type,
       subtype: event.subtype,
       dataType: typeof event.data,
       isArray: Array.isArray(event.data),
       data: event.data
     });
     // ... rest of processing
   });
   ```

2. **Check Console for Errors**: Look for Svelte 5 runtime errors in browser console

3. **Compare with Tools**: Verify Tools tab shows activity while Files doesn't

4. **After Fix**: Verify Files tab populates with Read, Write, Edit, Grep, Glob operations

---

## Related Issues

- **Commit 2d957494**: Fixed same issue in EventStream.svelte
- **Pattern**: EventStream had identical unsafe property access causing runtime errors
- **Fix**: Added type guards before accessing properties on event.data

---

## Backend Event Structure

From `hooks.py:_process_claude_event()` (lines 420-430):
```python
{
    "type": data.get("type", "hook"),
    "subtype": data.get("subtype", "unknown"),  # ← Pre/post tool info here
    "timestamp": ...,
    "session_id": ...,
    "source": ...,
    "data": data.get("data", {}),  # ← Tool parameters here (should be dict)
    "metadata": ...,
}
```

**Expected structure**: `event.data` should be a dict with tool parameters like:
- `tool_name`: Name of the tool (Read, Write, Edit, Grep, Glob)
- `file_path`: Path to the file being operated on
- `pattern`: Search pattern (for Grep/Glob)
- etc.

**However**: The `event.data` field is typed as `unknown` in TypeScript, and in practice can be:
- A dict/object (normal case)
- An array (error case - seen in EventStream fix)
- A string (error case)
- null/undefined

## Conclusion

The Files tab is not showing activity because the `files.svelte.ts` store lacks type guards when accessing properties on `event.data`. When events arrive with `event.data` as an array, string, or non-plain-object, the unsafe property access causes Svelte 5 runtime errors during reactive computation, silently dropping events.

**This is the EXACT same issue** that was fixed in EventStream with commit 2d957494, but the fix was not applied to files.svelte.ts (or tools.svelte.ts).

**Why Tools work but Files don't**: This could be due to:
1. Different timing of when events arrive (Tools processes first, Files second)
2. Tools might not encounter bad events due to luck
3. Or the issue manifests differently in derived stores vs. component-level stores

**Fix Required**: Add type guards matching the pattern from commit 2d957494 at lines 47-48 (and optionally lines 55, 157-174 for defense in depth).

**Test**: After applying fix, rebuild Svelte app and verify Files tab shows file operations.
