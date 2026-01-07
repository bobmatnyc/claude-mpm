# Session/Project Isolation Issue Analysis

**Date:** 2025-12-23
**Author:** Research Agent
**Status:** Issue Identified + Solution Proposed

## Executive Summary

**Problem:** Events from different projects (e.g., smarterthings vs claude-mpm) appear on the same dashboard, causing confusion and data mixing across unrelated work sessions.

**Root Cause:** The dashboard uses a **single global Socket.IO connection** that broadcasts all events to all connected clients, regardless of which project they originated from. There is no filtering mechanism based on working directory or project path.

**Impact:**
- Users working on Project A see events from Project B
- Event history gets polluted with unrelated project data
- Stream selector shows streams from multiple projects mixed together
- Confusing user experience when switching between projects

**Solution:** Implement **working directory-based filtering** at the frontend level, allowing users to view only events from their current project.

---

## Technical Analysis

### 1. Event Flow Architecture

```
Claude Code (Project A: smarterthings)
  ↓ Hook Event (cwd: /path/to/smarterthings)
  ↓
Hook Handler → ConnectionManager
  ↓ session_id: "abc123"
  ↓ cwd: "/path/to/smarterthings"
  ↓
Socket.IO Server (port 8765)
  ↓ Broadcast to ALL clients
  ↓
Dashboard Client (any project)
  ✓ Receives event with cwd: "/path/to/smarterthings"
```

```
Claude Code (Project B: claude-mpm)
  ↓ Hook Event (cwd: /path/to/claude-mpm)
  ↓
Hook Handler → ConnectionManager
  ↓ session_id: "xyz789"
  ↓ cwd: "/path/to/claude-mpm"
  ↓
Socket.IO Server (port 8765)
  ↓ Broadcast to ALL clients (SAME SERVER!)
  ↓
Dashboard Client (any project)
  ✓ Receives event with cwd: "/path/to/claude-mpm"
```

**Key Finding:** Both projects send events to the **same Socket.IO server instance** (localhost:8765), which broadcasts to **all connected dashboard clients**.

### 2. Current Event Structure

Events **DO include project information** (from `/Users/masa/Projects/claude-mpm/src/claude_mpm/hooks/claude_hooks/services/connection_manager.py` lines 127-148):

```python
# Extract working directory for project identification
# Try multiple field names for maximum compatibility
cwd = (
    data.get("cwd")
    or data.get("working_directory")
    or data.get("workingDirectory")
)

raw_event = {
    "type": event_type,
    "subtype": event,
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "data": data,
    "source": "mpm_hook",
    "session_id": session_id,
    "cwd": cwd,  # ✅ Working directory IS included
    "correlation_id": tool_call_id,
}
```

**Finding:** The `cwd` field **is already being sent** in every event, containing the full project path.

### 3. Frontend Stream Management

From `/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard-svelte/src/lib/stores/socket.svelte.ts`:

**Stream ID Extraction (lines 58-67):**
```typescript
function getStreamId(event: ClaudeEvent): string | null {
    return (
        event.session_id ||
        event.sessionId ||
        (event.data as any)?.session_id ||
        (event.data as any)?.sessionId ||
        event.source ||
        null
    );
}
```

**Problem:** Stream ID is based on `session_id`, which is **session-specific**, not **project-specific**. Each Claude Code session gets a unique session_id, so:
- Session A in Project smarterthings → stream_id: "abc123"
- Session B in Project claude-mpm → stream_id: "xyz789"

Both appear as separate streams in the same dashboard because there's **no filtering by project**.

**Project Metadata Extraction (lines 289-306):**
```typescript
const projectPath =
    data.cwd ||                            // ✅ Direct cwd field
    data.working_directory ||
    data.data?.working_directory ||
    data.data?.cwd ||
    data.metadata?.working_directory ||
    data.metadata?.cwd;

if (projectPath) {
    const projectName = projectPath.split('/').filter(Boolean).pop() || projectPath;

    streamMetadata.update(m => {
        const newMap = new Map(m);
        newMap.set(streamId, { projectPath, projectName });
        return newMap;
    });
}
```

**Finding:** The frontend **already extracts and stores** `projectPath` and `projectName` in `streamMetadata`, but this metadata is **not used for filtering** events or streams.

### 4. Dashboard Server Broadcast Logic

From `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/monitor/server.py` (lines 503-505):

```python
# Emit to Socket.IO clients via the appropriate event
if self.sio:
    await self.sio.emit(event, event_data)  # ❌ Broadcasts to ALL clients
```

**Problem:** The server uses `sio.emit()` which broadcasts to **all connected clients** without any filtering or room-based isolation.

---

## Solution Options

### Option 1: Project-Based Isolation (HIGH COMPLEXITY)
Each project starts its own monitor server on a different port.

**Pros:**
- Complete isolation between projects
- No mixing of events

**Cons:**
- Complex port management (need port allocation strategy)
- Multiple server processes consume more resources
- Dashboard URL changes per project (http://localhost:PORT)
- Configuration complexity (which port for which project?)

**Verdict:** ❌ Too complex for the benefit

### Option 2: Working Directory Filtering (RECOMMENDED ✅)
Filter events at the frontend based on current working directory.

**Pros:**
- Simple to implement (frontend-only change)
- Single monitor server keeps architecture simple
- User can optionally view all projects or filter to current
- Already have `cwd` in events and `streamMetadata`

**Cons:**
- Events from all projects still arrive at frontend (bandwidth)
- Need to determine "current project" for filtering

**Implementation:**
1. Add `/api/working-directory` endpoint to get server's current working directory
2. Frontend fetches current working directory on mount
3. Add project filter UI to stream selector
4. Filter streams to only show those matching current working directory
5. Add "Show All Projects" toggle for advanced users

**Verdict:** ✅ Best balance of simplicity and functionality

### Option 3: Session-Based Grouping (CURRENT STATE)
Keep all events but improve UI grouping by project.

**Pros:**
- No architectural changes needed
- Already have project metadata

**Cons:**
- Still shows all projects mixed together
- Confusing UX when multiple projects active

**Verdict:** ⚠️ Insufficient - doesn't solve the core problem

---

## Recommended Implementation

### Phase 1: Add Working Directory Filtering

**Backend Changes:**
Already done! The `/api/working-directory` endpoint exists (server.py lines 875-879):

```python
async def working_directory_handler(request):
    """Return the current working directory."""
    return web.json_response(
        {"working_directory": str(Path.cwd()), "success": True}
    )
```

**Frontend Changes:**

1. **Fetch Current Working Directory** (in `socket.svelte.ts`):
```typescript
// Add to createSocketStore()
const currentWorkingDirectory = writable<string>('');

async function fetchWorkingDirectory() {
    try {
        const response = await fetch('http://localhost:8765/api/working-directory');
        const data = await response.json();
        if (data.success) {
            currentWorkingDirectory.set(data.working_directory);
        }
    } catch (err) {
        console.warn('Failed to fetch working directory:', err);
    }
}

// Call on mount (in component using socket store)
```

2. **Add Project Filter Store**:
```typescript
const projectFilter = writable<'current' | 'all'>('current');
```

3. **Add Filtered Streams Derived Store**:
```typescript
const filteredStreams = derived(
    [streams, streamMetadata, currentWorkingDirectory, projectFilter],
    ([$streams, $streamMetadata, $currentWd, $filter]) => {
        if ($filter === 'all') {
            return $streams;
        }

        // Filter to only streams matching current working directory
        return new Set(
            Array.from($streams).filter(streamId => {
                const metadata = $streamMetadata.get(streamId);
                return metadata?.projectPath === $currentWd;
            })
        );
    }
);
```

4. **Update Stream Selector UI**:
```svelte
<select bind:value={$projectFilter}>
    <option value="current">Current Project Only</option>
    <option value="all">All Projects</option>
</select>

{#each Array.from($filteredStreams) as streamId}
    <option value={streamId}>
        {$streamMetadata.get(streamId)?.projectName || streamId}
        {#if $streamMetadata.get(streamId)?.projectPath !== $currentWorkingDirectory}
            (external)
        {/if}
    </option>
{/each}
```

5. **Filter Events Display**:
```typescript
const filteredEvents = derived(
    [events, selectedStream, projectFilter, currentWorkingDirectory, streamMetadata],
    ([$events, $selectedStream, $filter, $currentWd, $metadata]) => {
        if ($filter === 'all') {
            return $events.filter(e => getStreamId(e) === $selectedStream);
        }

        // Only show events from current project
        return $events.filter(e => {
            const streamId = getStreamId(e);
            const metadata = $metadata.get(streamId || '');
            const matchesProject = metadata?.projectPath === $currentWd;
            const matchesStream = !$selectedStream || streamId === $selectedStream;
            return matchesProject && matchesStream;
        });
    }
);
```

### Phase 2: Enhanced UX Improvements

1. **Visual Project Indicators**:
   - Badge showing current project name
   - Color-code streams by project
   - Highlight current project streams

2. **Auto-Selection Logic**:
   - On mount, auto-select first stream from current project
   - Ignore streams from other projects during auto-selection

3. **Project Switcher**:
   - Dropdown to switch between detected projects
   - Updates working directory filter accordingly

4. **Cached Events Filtering**:
   - When loading cached events, filter by project
   - Separate localStorage keys per project for better isolation

---

## Migration Path

### Phase 1: Minimal Change (This PR)
1. Add working directory filter to frontend
2. Default to "current project only" mode
3. Provide "all projects" toggle for advanced users

### Phase 2: Enhanced Isolation (Future)
1. Add project-specific localStorage caching
2. Add project switcher UI
3. Persist project filter preference

### Phase 3: Advanced Features (Optional)
1. Per-project color themes
2. Project comparison view (side-by-side)
3. Project-specific event retention policies

---

## Implementation Checklist

### Backend (Minimal Changes)
- [x] `/api/working-directory` endpoint exists
- [x] `cwd` field included in all events
- [ ] Add project name to `/api/config` response

### Frontend (Primary Changes)
- [ ] Add `currentWorkingDirectory` store
- [ ] Add `projectFilter` store ('current' | 'all')
- [ ] Add `filteredStreams` derived store
- [ ] Add `filteredEvents` derived store
- [ ] Update stream selector UI with filter toggle
- [ ] Fetch working directory on dashboard mount
- [ ] Update auto-selection to prefer current project
- [ ] Add visual indicators for current vs. external projects

### Testing
- [ ] Test with two projects running simultaneously
- [ ] Verify events filtered correctly
- [ ] Verify stream selector shows correct projects
- [ ] Test "all projects" mode
- [ ] Test localStorage persistence across sessions

---

## Potential Gotchas

1. **Working Directory Mismatch:**
   - Hook handler runs in project A's directory
   - Dashboard might be served from project B's directory
   - **Solution:** Use event's `cwd` field, not dashboard server's `cwd`

2. **Symlinks and Path Resolution:**
   - `/path/to/project` vs `/real/path/to/project`
   - **Solution:** Normalize paths before comparison (resolve symlinks)

3. **Multiple Sessions in Same Project:**
   - User opens multiple Claude Code windows in same project
   - All should appear in same filtered view
   - **Solution:** Filter by `projectPath` not `session_id`

4. **No Working Directory in Event:**
   - Some events might not have `cwd` field
   - **Solution:** Fallback to "all projects" mode for events without `cwd`

---

## Conclusion

**Root Cause:** Dashboard uses global Socket.IO broadcast without project-based filtering.

**Solution:** Implement working directory filtering at the frontend level using the already-available `cwd` field in events.

**Next Steps:**
1. Implement frontend filtering logic (socket.svelte.ts)
2. Add filter UI to stream selector component
3. Test with multiple projects
4. Document project isolation feature

**Impact:** Users working on Project A will only see events from Project A by default, with option to view all projects if needed.
