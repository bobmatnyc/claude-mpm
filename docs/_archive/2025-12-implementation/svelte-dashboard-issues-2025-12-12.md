# Claude MPM Svelte Dashboard Issues Research

**Date**: 2025-12-12
**Working Directory**: /Users/masa/Projects/claude-mpm
**Research Focus**: Event buffer on load and JSONExplorer data inspector

## Issue 1: Event Buffer on Connection

### Current State
**YES** - The backend HAS event buffering capability that IS being sent when clients connect.

### Implementation Details

**Event Buffer Location**:
- `src/claude_mpm/services/socketio/handlers/connection.py` (lines 344-346)
- Buffer is stored in `self.event_history` (deque with max size from SystemLimits.MAX_EVENTS_BUFFER)

**Connection Flow**:
1. Client connects → `connect` event handler triggered (line 274)
2. Server sends `status` event (line 325)
3. Server sends `welcome` event (line 326-342)
4. **Server automatically sends last 50 events** (line 345):
   ```python
   # Automatically send the last 50 events to new clients
   await self._send_event_history(sid, limit=50)
   ```

**Event History Mechanism** (`_send_event_history` method, lines 585-644):
- Gets most recent events from `self.event_history` deque
- Reverses them to chronological order (oldest first)
- Sends as 'history' event to client with structure:
  ```python
  {
    "events": [...],
    "count": len(history),
    "total_available": len(self.event_history)
  }
  ```

### Verification
- Buffer exists: ✅ (`event_history` deque, line 87 in main.py)
- Sent on connect: ✅ (line 345 in connection.py)
- Event name: `history` (not `dashboard:welcome`)
- Default limit: 50 events

### PROBLEM IDENTIFIED ❌

**Root Cause**: Frontend socket store does NOT listen for `history` event

**File**: `src/claude_mpm/dashboard-svelte/src/lib/stores/socket.svelte.ts`
- Lines 53-60: Only listens for specific event types:
  - `claude_event`, `hook_event`, `cli_event`, `system_event`, `agent_event`, `build_event`
- **Missing**: No listener for `history` event sent by backend on connection
- Backend sends `history` event (connection.py line 620)
- Frontend never receives it because no handler is registered

---

## Issue 2: JSONExplorer Data Inspector Not Working

### Current Implementation Analysis

**Component Structure**:
```
+page.svelte (line 53)
  └─ <JSONExplorer event={selectedEvent} />
       ↓
  JSONExplorer.svelte (line 4)
    └─ Receives: event prop
```

**Data Flow**:
1. `EventStream.svelte` line 91: `selectEvent(event)` sets `selectedEvent = event`
2. `+page.svelte` line 8: `let selectedEvent = $state<ClaudeEvent | null>(null);`
3. `+page.svelte` line 53: Passes `event={selectedEvent}` to JSONExplorer
4. `JSONExplorer.svelte` line 4: Receives as `let { event }: { event: ClaudeEvent | null } = $props();`

### THE PROBLEM IDENTIFIED

**Issue**: Missing `$bindable()` directive in JSONExplorer

**Root Cause**:
- `EventStream.svelte` line 6: Uses `selectedEvent = $bindable(null)`
- `+page.svelte` line 68: Uses `bind:selectedEvent` (two-way binding)
- `JSONExplorer.svelte` line 4: Uses regular `$props()` (one-way binding)

**What's Happening**:
1. EventStream changes `selectedEvent` via `bind:` directive
2. Parent (+page.svelte) receives the update
3. Parent passes updated value to JSONExplorer
4. JSONExplorer receives the prop BUT the reactivity chain works

**Wait - Let me re-check the actual issue...**

Looking at JSONExplorer.svelte more carefully:
- Line 4: Receives `event` prop correctly
- Line 45-54: Has `$effect()` that watches `event` and rebuilds tree
- Lines 101-206: Renders tree structure

**The code looks correct!** So why isn't it working?

### Potential Issues with JSONExplorer

1. **Effect Not Triggering**:
   - The `$effect()` on line 45 should rebuild tree when `event` changes
   - Auto-expands root level items

2. **Tree Structure**:
   - Uses `buildTree()` function (lines 14-40) to create hierarchical structure
   - Only supports 3 levels deep (root → child → grandchild)

3. **Rendering Logic**:
   - Line 101: Shows placeholder when `!event`
   - Line 119: Iterates over `tree` array
   - **POTENTIAL BUG**: Only shows 2 levels deep (root + children, but grandchildren only show values, not nested structure)

### Identified Issues

**Issue #1**: Limited Tree Depth
- Lines 177-186: Grandchildren don't recursively expand
- Hardcoded to only show 3 levels maximum
- No way to expand deeply nested objects

**Issue #2**: No Deep Expansion
- `buildTree()` recursively creates children, but rendering stops at grandchild level
- Events with deeply nested data won't be fully explorable

**Issue #3**: No Visual Feedback
- No loading state when event changes
- No error boundary if event structure is malformed

---

## Specific Code Changes Needed

### Issue 1: Event Buffer ❌ MISSING FRONTEND HANDLER

**File**: `src/claude_mpm/dashboard-svelte/src/lib/stores/socket.svelte.ts`

**Problem**: No listener for `history` event

**Current Code** (lines 51-60):
```typescript
// Listen for all event types from backend
const eventTypes = ['claude_event', 'hook_event', 'cli_event', 'system_event', 'agent_event', 'build_event'];

eventTypes.forEach(eventType => {
	newSocket.on(eventType, (data: ClaudeEvent) => {
		console.log(`Received ${eventType}:`, data);
		handleEvent(data);
	});
});
```

**Fix Required** - Add after line 60:
```typescript
// Listen for event history sent on connection
newSocket.on('history', (data: { events: ClaudeEvent[], count: number, total_available: number }) => {
	console.log('Received event history:', data);
	// Process each historical event
	if (data.events && Array.isArray(data.events)) {
		data.events.forEach(event => handleEvent(event));
		console.log(`Loaded ${data.count} historical events (${data.total_available} total available)`);
	}
});
```

**Impact**: After adding this listener, dashboard will show last 50 events when client connects

### Issue 2: JSONExplorer Data Inspector

**Problem**: Tree depth limited to 3 levels, no recursive rendering

**Solution**: Make JSONExplorer fully recursive

**File**: `src/claude_mpm/dashboard-svelte/src/lib/components/JSONExplorer.svelte`

**Changes Needed**:

1. **Extract tree node rendering to recursive component** (lines 119-206):
   ```svelte
   <!-- Create TreeNode.svelte component with recursive rendering -->
   <!-- Or use Svelte's {#snippet} feature for inline recursion -->
   ```

2. **Use recursive rendering pattern**:
   ```svelte
   {#snippet treeNode(node, path, depth)}
     {#if node.children && node.children.length > 0}
       <button onclick={() => toggleExpand(path)}>
         <!-- Toggle icon -->
         <span>{node.key}</span>
       </button>
       {#if isExpanded(path)}
         {#each node.children as child, i}
           {@const childPath = `${path}.${i}`}
           {@render treeNode(child, childPath, depth + 1)}
         {/each}
       {/if}
     {:else}
       <span>{node.key}: {formatValue(node.value, node.type)}</span>
     {/if}
   {/snippet}

   {#each tree as node, i}
     {@render treeNode(node, `${i}`, 0)}
   {/each}
   ```

3. **Add depth limiting** (prevent infinite recursion):
   ```svelte
   {#snippet treeNode(node, path, depth)}
     {#if depth > MAX_DEPTH}
       <span class="text-yellow-400">... (depth limit reached)</span>
     {:else if node.children}
       <!-- Recursive rendering -->
     {/if}
   {/snippet}
   ```

4. **Add max depth control**:
   ```svelte
   const MAX_DEPTH = 10; // Configurable
   ```

---

## Root Cause Summary

### Issue 1: Event Buffer ❌ FRONTEND MISSING HANDLER
- Backend sends 50 buffered events on connect ✅
- Event name: `history` ✅
- Format: `{ events: [...], count: N, total_available: N }` ✅
- **Frontend listener for `history` event**: ❌ MISSING

**Fix**: Add `history` event listener to socket.svelte.ts (see changes above)

### Issue 2: JSONExplorer ❌ LIMITED FUNCTIONALITY
- **Root Cause**: Hardcoded 3-level tree rendering
- **Symptom**: Can't explore deeply nested event data
- **Fix**: Implement recursive tree rendering using Svelte 5 `{#snippet}` feature

---

## Additional Findings

### Socket.IO Event Buffer Details

**Event Storage**:
- `main.py` line 87: `self.event_history = deque(maxlen=SystemLimits.MAX_EVENTS_BUFFER)`
- Events added via `core.py` lines 409-414 when received via HTTP API
- Events added via `connection.py` line 509 when received from clients

**Event Structure**:
All events normalized to:
```python
{
  "type": "hook" | "system" | "tool" | "connection" | etc,
  "subtype": "pre_tool_use" | "status" | "welcome" | etc,
  "timestamp": "ISO 8601 string",
  "source": "server" | "claude_hooks" | etc,
  "session_id": "session-id-string",
  "data": { ... }  # Event-specific payload
}
```

### Monitor Server Architecture

**Two Server Implementations Found**:
1. **UnifiedMonitorServer** (`services/monitor/server.py`)
   - Port 8765, combined HTTP + Socket.IO
   - Newer implementation with hot reload support

2. **SocketIOServerCore** (`services/socketio/server/core.py`)
   - Port 8765, modular Socket.IO server
   - Used by main SocketIOServer class

**Event Flow**:
```
Hook Handler (ephemeral process)
    ↓ HTTP POST /api/events
SocketIOServerCore (core.py)
    ↓ Normalize event
EventBus.publish()
    ↓
SocketIOEventBroadcaster
    ↓ sio.emit()
Connected Dashboard Clients
```

---

## Recommended Next Steps

1. **Verify frontend handles `history` event**:
   - Check `socket.svelte.ts` for `history` event listener
   - Verify events are added to store on connect

2. **Fix JSONExplorer recursion**:
   - Implement recursive tree rendering
   - Use Svelte 5 `{#snippet}` feature
   - Add depth limiting
   - Add expand/collapse all buttons

3. **Test event buffer flow**:
   - Connect to dashboard after generating some events
   - Verify `history` event received in browser DevTools
   - Verify events appear in EventStream component

---

## Files Referenced

**Backend**:
- `src/claude_mpm/services/socketio/handlers/connection.py` - Connection handler with event history
- `src/claude_mpm/services/socketio/server/core.py` - Core Socket.IO server
- `src/claude_mpm/services/socketio/server/main.py` - Main SocketIOServer class
- `src/claude_mpm/services/monitor/server.py` - Unified monitor server

**Frontend**:
- `src/claude_mpm/dashboard-svelte/src/routes/+page.svelte` - Main dashboard page
- `src/claude_mpm/dashboard-svelte/src/lib/components/EventStream.svelte` - Event list
- `src/claude_mpm/dashboard-svelte/src/lib/components/JSONExplorer.svelte` - Data inspector (NEEDS FIX)
- `src/claude_mpm/dashboard-svelte/src/lib/stores/socket.svelte.ts` - Socket connection store (check `history` event)

---

## Conclusion

**Issue 1 (Event Buffer)**: ✅ Backend implementation is correct. 50 events sent automatically on connect via `history` event. If not working, investigate frontend socket store.

**Issue 2 (JSONExplorer)**: ❌ Limited to 3-level tree depth. Needs recursive rendering implementation using Svelte 5 snippets for full event data exploration.
