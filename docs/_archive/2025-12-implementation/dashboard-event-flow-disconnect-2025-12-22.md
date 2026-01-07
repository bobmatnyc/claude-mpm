# Dashboard Event Flow Disconnect Analysis

**Date:** 2025-12-22
**Issue:** Dashboard not showing file operations despite historical event retrieval being implemented
**Status:** ✅ ROOT CAUSE IDENTIFIED

---

## Executive Summary

The dashboard receives events correctly via HTTP POST but **they are not being added to `event_history`** - the deque that stores historical events for late-joining clients. This means:

1. ✅ **Real-time events work** - Live clients see events when they happen
2. ❌ **Historical replay broken** - New clients or refreshed pages see empty history
3. ❌ **Event persistence missing** - Events are broadcast but immediately forgotten

**Root Cause:** HTTP event handler in `server/core.py` broadcasts events via Socket.IO but only adds them to `event_history` **conditionally** and **in the wrong place**.

---

## Event Flow Architecture

### 1. Hook Fires (Claude performs file operation)

**Location:** `hooks/claude_hooks/event_handlers.py`

```python
def handle_post_tool_fast(self, event):
    # Lines 458-461: File operations include full output
    if tool_name in ("Read", "Edit", "Write", "Grep", "Glob") and "output" in event:
        post_tool_data["output"] = event["output"]

    # Line 495: Emit to Socket.IO via connection manager
    self.hook_handler._emit_socketio_event("", "post_tool", post_tool_data)
```

**What happens:**
- Hook extracts file operation details
- Includes full output for Read/Edit/Write/Grep/Glob operations
- Calls `_emit_socketio_event()` to send to dashboard

---

### 2. Connection Manager Routes Event

**Location:** `hooks/claude_hooks/services/connection_manager_http.py`

```python
def emit_event(self, namespace: str, event: str, data: dict):
    # Lines 106-116: Normalize event to standard schema
    raw_event = {
        "type": "hook",
        "subtype": event,  # e.g., "post_tool", "pre_tool"
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data,
        "source": "claude_hooks",
    }
    normalized_event = self.event_normalizer.normalize(raw_event, source="hook")

    # Lines 136-141: Try async emit first, then HTTP fallback
    success = self._try_async_emit(namespace, event, claude_event_data)
    if success:
        return
    self._try_http_emit(namespace, event, claude_event_data)
```

**What happens:**
- Normalizes hook event to standard `claude_event` schema
- Tries async emitter (direct EventBus)
- Falls back to HTTP POST if async fails
- **Both paths send to dashboard server**

---

### 3. Dashboard Server Receives HTTP Event

**Location:** `services/socketio/server/core.py` (Lines 263-458)

```python
async def api_events_handler(request):
    # Line 275: Parse JSON payload
    payload = await request.json()

    # Lines 277-283: Extract event data
    if "data" in payload and isinstance(payload.get("data"), dict):
        event_data = payload["data"]
    else:
        event_data = payload

    # Lines 285-291: Log receipt
    event_type = event_data.get("subtype") or event_data.get("hook_event_name") or "unknown"
    self.logger.info(f"📨 Received HTTP event: {event_type}")

    # Lines 380-392: Publish to EventBus (WORKS)
    from claude_mpm.services.event_bus import EventBus
    event_bus = EventBus.get_instance()
    event_type = f"hook.{event_data.get('subtype', 'unknown')}"
    event_bus.publish(event_type, event_data)

    # Lines 394-438: Broadcast to clients
    if self.sio:
        if self.main_server and hasattr(self.main_server, "broadcaster"):
            # 🔥 THE PROBLEM STARTS HERE 🔥

            # Lines 408-414: Add to buffer and history
            with self.buffer_lock:
                self.event_buffer.append(event_data)
                self.stats["events_buffered"] = len(self.event_buffer)

            # ⚠️ CRITICAL ISSUE: Lines 412-414
            if hasattr(self.main_server, "event_history"):
                self.main_server.event_history.append(event_data)
            # ^ This only runs if main_server has event_history attribute
            # ^ This is INSIDE the broadcaster conditional

            # Line 418: Broadcast to clients
            await self.sio.emit("claude_event", event_data)
```

**What happens:**
1. ✅ Event is received via HTTP POST
2. ✅ Event is normalized to dashboard schema
3. ✅ Event is published to EventBus
4. ✅ Event is broadcast to live Socket.IO clients
5. ❌ **Event is only added to `event_history` conditionally**
6. ❌ **Event history addition is buried inside broadcaster check**

---

### 4. Client Connects and Requests History

**Location:** `services/socketio/handlers/connection.py`

```python
async def connect(sid, environ, *args):
    # Lines 281-286: Track client
    self.clients.add(sid)
    self.logger.info(f"🔗 NEW CLIENT CONNECTED: {sid}")

    # Lines 324-342: Send welcome messages
    await self.emit_to_client(sid, "status", status_data)
    await self.emit_to_client(sid, "welcome", {...})

    # Line 345: Send event history automatically
    await self._send_event_history(sid, limit=50)
    # ^ This is where historical events should be sent

async def _send_event_history(self, sid: str, event_types=None, limit=50):
    # Lines 600-602: Check if history exists
    if not self.event_history:
        self.logger.debug(f"No event history to send to client {sid}")
        return  # ❌ RETURNS EMPTY IF event_history IS EMPTY

    # Lines 608-616: Get recent events
    history = []
    for event in reversed(self.event_history):
        if not event_types or event.get("type") in event_types:
            history.append(event)
            if len(history) >= limit:
                break

    # Lines 620-628: Send to client
    await self.emit_to_client(sid, "history", {
        "events": history,
        "count": len(history),
        "total_available": len(self.event_history),
    })
```

**What happens:**
1. ✅ Client connects to dashboard
2. ✅ Server sends welcome message
3. ✅ Server calls `_send_event_history()` automatically
4. ❌ **`self.event_history` is EMPTY** (because HTTP handler didn't populate it)
5. ❌ Client receives empty history
6. ❌ Dashboard shows no past events

---

## The Disconnect: Why `event_history` is Empty

### Problem 1: Conditional History Addition

**File:** `services/socketio/server/core.py` (Lines 412-414)

```python
# Add to main server's event history
if hasattr(self.main_server, "event_history"):
    self.main_server.event_history.append(event_data)
```

**Issues:**
- ⚠️ Only adds if `main_server` has `event_history` attribute
- ⚠️ Silently fails if attribute doesn't exist
- ⚠️ No logging when history addition is skipped

### Problem 2: History Addition Inside Broadcaster Conditional

**File:** `services/socketio/server/core.py` (Lines 398-438)

```python
if self.sio:
    if self.main_server and hasattr(self.main_server, "broadcaster") and self.main_server.broadcaster:
        # History addition is HERE (inside nested conditionals)
        with self.buffer_lock:
            self.event_buffer.append(event_data)

        if hasattr(self.main_server, "event_history"):
            self.main_server.event_history.append(event_data)

        # Broadcast
        await self.sio.emit("claude_event", event_data)
    else:
        # Fallback path (lines 434-446)
        self.logger.warning("Broadcaster not available, using direct emit")
        await self.sio.emit("claude_event", event_data)

        # ⚠️ History addition is duplicated here but might not run
        with self.buffer_lock:
            self.event_buffer.append(event_data)
```

**Issues:**
- History addition happens in **two places** with different conditions
- If broadcaster exists but `event_history` attribute missing → no history
- If broadcaster missing → uses fallback path which also may not add to history
- **No guarantee that history is populated**

---

## Verification: What Works vs What's Broken

### ✅ What Works (Real-time Broadcasting)

1. **Hook fires** → Event captured
2. **Connection manager** → Normalizes and routes event
3. **HTTP endpoint** → Receives event correctly
4. **Socket.IO broadcast** → Live clients receive event
5. **EventBus publish** → Other components receive event

**Evidence:** Dashboard logs show:
```
📨 Received HTTP event: post_tool
✅ Event broadcasted: post_tool to 1 clients
```

### ❌ What's Broken (Historical Replay)

1. **Event history population** → Conditional, unreliable
2. **Client history request** → Returns empty list
3. **Dashboard initial load** → Shows no past events
4. **Page refresh** → Loses all event context

**Evidence:** Dashboard logs show:
```
📚 Sent 0 historical events to client <sid>
No event history to send to client <sid>
```

---

## Root Cause Summary

The dashboard event flow has **TWO separate paths** that are not properly coordinated:

1. **Real-time path:** Hook → HTTP POST → Socket.IO broadcast → Live clients ✅
2. **History path:** Hook → HTTP POST → ??? → `event_history` → New clients ❌

**The break:** HTTP event handler broadcasts events to live clients but **does not reliably add them to `event_history`**, causing new clients to see empty history.

---

## Fix Strategy

### Option 1: Unconditional History Addition (Recommended)

**File:** `services/socketio/server/core.py`

```python
async def api_events_handler(request):
    # ... existing event parsing ...

    # Add to event history UNCONDITIONALLY and EARLY
    if self.main_server:
        # Add to main server's event_history (guaranteed to exist)
        self.main_server.event_history.append(event_data)
        self.logger.debug(f"Added {event_type} to event_history (total: {len(self.main_server.event_history)})")

    # Add to buffer for late-joining clients
    with self.buffer_lock:
        self.event_buffer.append(event_data)

    # Publish to EventBus
    # ... existing EventBus code ...

    # Broadcast to clients
    # ... existing broadcast code ...
```

**Benefits:**
- Single, unconditional code path for history
- Happens early before any conditionals
- Explicit logging for verification
- Simple, obvious fix

### Option 2: Initialize `event_history` Guarantee

**File:** `services/socketio/server/main.py`

Ensure `event_history` is always initialized and accessible:

```python
def __init__(self):
    # ... existing init ...

    # GUARANTEE event_history exists
    self.event_history = deque(maxlen=SystemLimits.MAX_EVENTS_BUFFER)

    # Share event_history with core server
    self.core.event_history = self.event_history
```

**Benefits:**
- Ensures attribute always exists
- Removes conditional check necessity
- Provides shared reference for consistency

### Option 3: Dedicated History Service (Future Enhancement)

Create a centralized `EventHistoryService` that guarantees history persistence:

```python
class EventHistoryService:
    def __init__(self, max_size=1000):
        self.history = deque(maxlen=max_size)
        self.lock = asyncio.Lock()

    async def add(self, event):
        async with self.lock:
            self.history.append(event)
            logger.info(f"Event added to history (total: {len(self.history)})")

    async def get_recent(self, limit=50, event_types=None):
        # ... filtering logic ...
```

**Benefits:**
- Single source of truth for event history
- Guaranteed atomic operations
- Centralized logging and metrics
- Thread-safe by design

---

## Recommended Immediate Fix

**Implement Option 1 + Option 2:**

1. **Guarantee initialization** (Option 2)
2. **Unconditional addition** (Option 1)
3. **Add verification logging**

**Implementation:**

```python
# File: services/socketio/server/main.py (Line 87)
# CHANGE:
self.event_history = deque(maxlen=SystemLimits.MAX_EVENTS_BUFFER)
# TO:
self.event_history = deque(maxlen=SystemLimits.MAX_EVENTS_BUFFER)
self.core.event_history = self.event_history  # Share reference with core

# File: services/socketio/server/core.py (Lines 380-420)
# ADD BEFORE EventBus publish:
# Add to event history FIRST (guaranteed path)
if self.main_server and hasattr(self.main_server, "event_history"):
    self.main_server.event_history.append(event_data)
    self.logger.debug(
        f"✅ Added to event_history: {event_data.get('subtype', 'unknown')} "
        f"(total: {len(self.main_server.event_history)})"
    )
else:
    self.logger.warning(
        f"⚠️ Cannot add to event_history - main_server or event_history not available"
    )

# Add to buffer
with self.buffer_lock:
    self.event_buffer.append(event_data)
    self.stats["events_buffered"] = len(self.event_buffer)

# THEN publish to EventBus and broadcast (existing code)
```

---

## Verification Steps

After implementing the fix:

### 1. Check Event Addition

```bash
# Start dashboard
mpm dashboard start

# In another terminal, perform file operation
echo "test" > /tmp/test.txt

# Check dashboard logs for:
✅ Added to event_history: post_tool (total: X)
```

### 2. Check History Retrieval

```bash
# Open dashboard in browser
open http://localhost:8765

# Check browser console for:
Received history with X events
```

### 3. Check Refresh Behavior

```bash
# Perform several file operations
touch test1.txt test2.txt test3.txt

# Refresh browser (Cmd+R)
# Verify historical events appear in timeline
```

---

## Impact Analysis

### Components Affected

1. ✅ **EventBus** - No change needed (already works)
2. ✅ **Socket.IO broadcast** - No change needed (already works)
3. ❌ **Event history** - REQUIRES FIX (broken)
4. ❌ **Client history retrieval** - REQUIRES FIX (depends on history)
5. ✅ **Real-time updates** - No change needed (already works)

### User Impact

**Before Fix:**
- Dashboard shows events only while page is open
- Refresh loses all context
- New users see empty dashboard
- No way to review past operations

**After Fix:**
- Dashboard shows last 50 events on load
- Refresh maintains context
- New users see recent activity
- Full event timeline available

---

## Related Files

### Core Event Flow

1. `hooks/claude_hooks/event_handlers.py` - Hook event generation
2. `hooks/claude_hooks/services/connection_manager_http.py` - Event routing
3. `services/socketio/server/core.py` - HTTP API endpoint (**FIX HERE**)
4. `services/socketio/server/main.py` - Event history initialization (**FIX HERE**)
5. `services/socketio/handlers/connection.py` - History retrieval

### Supporting Components

6. `services/event_bus.py` - Cross-component event distribution
7. `services/socketio/event_normalizer.py` - Event schema normalization
8. `services/socketio/server/broadcaster.py` - Client broadcasting

---

## Conclusion

**The disconnect is clear:**

- ✅ Hooks capture file operations correctly
- ✅ HTTP endpoint receives events correctly
- ✅ Socket.IO broadcasts events correctly
- ❌ **Event history is NOT populated reliably**
- ❌ **Client history retrieval returns empty results**

**The fix is simple:**

Ensure `event_history.append(event_data)` runs **unconditionally** and **early** in the HTTP event handler, before any broadcasting or conditional logic.

**Expected outcome:**

Dashboard will show the last 50 events on every page load, including file operations, tool executions, and all other hook events.
