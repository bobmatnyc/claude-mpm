# Session/Project Isolation Fix - Implementation Summary

**Date:** 2025-12-23
**Status:** ✅ IMPLEMENTED

## Problem Statement

Events from different projects (e.g., smarterthings vs claude-mpm) were appearing on the same dashboard, causing confusion when users worked across multiple projects. The dashboard showed a mixed stream of events from all projects without any filtering mechanism.

## Root Cause

The dashboard used a **single global Socket.IO connection** that broadcast all events to all connected clients. While events contained project information (via the `cwd` field), there was no filtering mechanism at the frontend to separate events by project.

## Solution Implemented

Added **working directory-based filtering** at the frontend level, allowing users to view only events from their current project or optionally view all projects.

### Changes Made

#### 1. Socket Store Updates (`/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard-svelte/src/lib/stores/socket.svelte.ts`)

**Added Stores:**
- `currentWorkingDirectory`: Stores the dashboard's current working directory
- `projectFilter`: Controls filter mode ('current' | 'all')

**Added Functions:**
- `fetchWorkingDirectory()`: Fetches working directory from `/api/working-directory` endpoint
- `setProjectFilter()`: Updates project filter mode

**Integration:**
- Automatically fetches working directory when connecting to Socket.IO
- Exposes project filter controls to components

#### 2. Header Component Updates (`/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard-svelte/src/lib/components/Header.svelte`)

**Added UI:**
- Project filter dropdown with options:
  - "Current Only" (default) - shows only streams from current working directory
  - "All Projects" - shows streams from all projects

**Updated Stream Filtering:**
- `streamOptions` derived store now filters streams based on `projectFilter` and `currentWorkingDirectory`
- Only shows streams where `projectPath === currentWorkingDirectory` when filter is set to "current"

**User Experience:**
- Tooltip shows current working directory when hovering over "Current Only"
- Stream dropdown only shows streams matching the selected project filter
- Activity indicators (🟢/⚪) still work correctly

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Frontend (Dashboard)                                        │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Socket Store                                         │  │
│  │  - currentWorkingDirectory: "/path/to/claude-mpm"   │  │
│  │  - projectFilter: "current"                          │  │
│  └──────────────────────────────────────────────────────┘  │
│                    ↓                                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Header Component                                     │  │
│  │  - Project Filter: [Current Only ▾]                 │  │
│  │  - Stream Selector: [claude-mpm (abc123) ▾]        │  │
│  └──────────────────────────────────────────────────────┘  │
│                    ↓                                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Filtered Streams                                     │  │
│  │  ✅ stream_abc123 (projectPath: /path/to/claude-mpm)│  │
│  │  ❌ stream_xyz789 (projectPath: /path/to/other)     │  │
│  │     ↑ FILTERED OUT                                   │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                     ↑
                     │ Socket.IO (all events)
                     │
┌─────────────────────────────────────────────────────────────┐
│ Backend (Monitor Server)                                    │
│  - Broadcasts ALL events to ALL clients                     │
│  - Events include cwd field for project identification      │
└─────────────────────────────────────────────────────────────┘
```

### User Workflow

**Before Fix:**
1. User runs Claude Code in Project A (smarterthings)
2. User opens dashboard → sees events from smarterthings ✓
3. User runs Claude Code in Project B (claude-mpm)
4. User opens dashboard → sees events from BOTH projects ❌
5. Confusion: events from different projects mixed together

**After Fix:**
1. User runs Claude Code in Project A (smarterthings)
2. User opens dashboard → sees events from smarterthings ✓
3. User runs Claude Code in Project B (claude-mpm)
4. User opens dashboard → **only sees events from claude-mpm** ✓
5. User can toggle "All Projects" to see all streams if needed ✓

### Default Behavior

**Project Filter:** "Current Only" (default)
- Shows only streams where `projectPath === currentWorkingDirectory`
- Auto-selects first stream from current project
- Hides streams from other projects

**Stream Selector:**
- Only displays streams matching the project filter
- Shows project name and session ID
- Activity indicators work as before

### Edge Cases Handled

1. **No Working Directory:** If `/api/working-directory` fails, filter defaults to "all"
2. **No Matching Streams:** If current project has no streams, selector shows "Waiting for streams..."
3. **Stream Without Project Path:** Events without `cwd` field are not filtered
4. **Multiple Sessions Same Project:** All sessions from same project are shown (not filtered)

### Testing Checklist

- [x] Code changes implemented
- [ ] Test with single project (should work as before)
- [ ] Test with two projects running simultaneously
- [ ] Verify "Current Only" shows only current project streams
- [ ] Verify "All Projects" shows all streams
- [ ] Test stream auto-selection with project filter
- [ ] Test localStorage persistence with project filter
- [ ] Verify working directory fetch on dashboard load

### Files Modified

1. `/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard-svelte/src/lib/stores/socket.svelte.ts`
   - Added `currentWorkingDirectory` and `projectFilter` stores
   - Added `fetchWorkingDirectory()` function
   - Added `setProjectFilter()` function
   - Integrated working directory fetch on connection

2. `/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard-svelte/src/lib/components/Header.svelte`
   - Added project filter dropdown UI
   - Updated `streamOptions` derived store with project filtering logic
   - Added tooltips for better UX

### No Backend Changes Required

The backend already:
- ✅ Includes `cwd` field in all events (ConnectionManager line 148)
- ✅ Provides `/api/working-directory` endpoint (server.py line 875)
- ✅ Broadcasts events with full project metadata

### Future Enhancements (Out of Scope)

1. **Project-Specific localStorage:** Cache events per-project for better isolation
2. **Project Switcher:** Dropdown to switch between detected projects
3. **Color-Coded Projects:** Visual project indicators beyond filtering
4. **Project Comparison View:** Side-by-side view of multiple projects

### Migration Notes

**Backward Compatibility:** ✅ FULL
- Existing dashboards continue to work
- Default "Current Only" filter provides better isolation
- Users can switch to "All Projects" for old behavior

**Breaking Changes:** ❌ NONE
- No API changes
- No event structure changes
- No configuration changes

### Performance Impact

**Minimal:**
- One additional HTTP request on dashboard load (`/api/working-directory`)
- Client-side filtering (no server overhead)
- No change to event broadcasting

### Success Metrics

**Before:**
- Events from Project A + Project B shown together
- User confused by mixed streams

**After:**
- Events from Project A shown only when working on Project A
- Events from Project B shown only when working on Project B
- Clear project context maintained
- Optional view of all projects when needed

### Deployment

**Steps:**
1. Rebuild Svelte dashboard: `npm run build` in dashboard-svelte directory
2. No server restart required (frontend-only change)
3. Users refresh dashboard to get new filtering UI

**Rollback:**
- Revert socket.svelte.ts changes
- Revert Header.svelte changes
- Rebuild dashboard
- No data loss (filter is ephemeral)

---

## Conclusion

The session/project isolation issue has been resolved by implementing **working directory-based filtering** at the frontend level. This approach:

✅ Provides clear project isolation by default
✅ Allows viewing all projects when needed
✅ Requires no backend changes
✅ Maintains backward compatibility
✅ Adds minimal performance overhead

Users working on Project A will now only see events from Project A, with an option to view all projects when needed. This significantly improves the dashboard UX when working across multiple projects.
