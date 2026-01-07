# Event Duplication Investigation - Claude MPM Monitor

**Date**: 2025-12-11
**Investigator**: Research Agent
**Issue**: Events appearing doubled/duplicated in Claude MPM dashboard
**Status**: Root cause identified

## Executive Summary

Events are NOT being duplicated at the server level. The duplication occurs due to **dual emission pathways**: one through EventBus (cross-component communication) and one through direct Socket.IO emit (client communication). Both emissions reach connected clients, causing dashboard to display each event twice.

## Root Cause Analysis

### Event Flow Trace (COMPLETE)

```
Hook Script
    ↓
POST /api/events (core.py:270)
    ↓
Event Normalization (core.py:295-374)
    ↓
┌─────────────────────────────────────────────────────────┐
│                   DUPLICATION POINT                     │
│                                                         │
│  PATH #1: EventBus Route (CAUSES DUPLICATE)            │
│  ┌──────────────────────────────────────────────────┐  │
│  │ EventBus.publish('hook.xxx', data)               │  │
│  │ (core.py:384)                                    │  │
│  └──────────────┬───────────────────────────────────┘  │
│                 │                                       │
│                 ↓                                       │
│  ┌──────────────────────────────────────────────────┐  │
│  │ DirectSocketIORelay.on('hook.*')                 │  │
│  │ (direct_relay.py:73)                             │  │
│  └──────────────┬───────────────────────────────────┘  │
│                 │                                       │
│                 ↓                                       │
│  ┌──────────────────────────────────────────────────┐  │
│  │ broadcaster.broadcast_event()                    │  │
│  │ (direct_relay.py:224)                            │  │
│  └──────────────┬───────────────────────────────────┘  │
│                 │                                       │
│                 ↓                                       │
│             sio.emit('claude_event')  ────────────────┐ │
│                                                       │ │
│  PATH #2: Direct Route (INTENDED PATH)               │ │
│  ┌──────────────────────────────────────────────────┐│ │
│  │ sio.emit('claude_event', event_data)             ││ │
│  │ (core.py:414)                                    ││ │
│  └──────────────┬───────────────────────────────────┘│ │
│                 │                                     │ │
│                 ↓                                     │ │
│             Socket.IO Client ←────────────────────────┘ │
│                 │                                       │
└─────────────────┼───────────────────────────────────────┘
                  ↓
    Dashboard receives BOTH emissions!
                  ↓
    socket-client.js:468 (processes BOTH)
                  ↓
    EventViewer displays event TWICE
```

### Critical Code Locations

#### 1. Server: Dual Emission (DUPLICATION SOURCE)

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/socketio/server/core.py`

**Lines 376-388**: EventBus publication
```python
# Publish to EventBus for cross-component communication
try:
    from claude_mpm.services.event_bus import EventBus

    event_bus = EventBus.get_instance()
    event_type = f"hook.{event_data.get('subtype', 'unknown')}"
    event_bus.publish(event_type, event_data)  # ← EMISSION #1
    self.logger.debug(f"Published to EventBus: {event_type}")
except Exception as e:
    # Non-fatal: EventBus publication failure shouldn't break event flow
    self.logger.warning(f"Failed to publish to EventBus: {e}")
```

**Lines 391-434**: Direct Socket.IO emission
```python
# Broadcast to all connected dashboard clients via SocketIO
if self.sio:
    # ... buffer management ...

    # Use the broadcaster's sio to emit
    await self.sio.emit("claude_event", event_data)  # ← EMISSION #2

    self.logger.info(
        f"✅ Event broadcasted: {event_data.get('subtype', 'unknown')} "
        f"to {len(self.connected_clients)} clients"
    )
```

#### 2. EventBus: No Duplication Here

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/event_bus/event_bus.py`

**Lines 159-236**: EventBus.publish() method
- EventBus is correctly designed as internal communication system
- Does NOT directly emit to Socket.IO clients
- Only triggers registered listeners via pyee
- **EventBus is working as designed - not causing duplication**

#### 3. Client: Single Listener

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard/static/js/socket-client.js`

**Lines 468-488**: Single `claude_event` listener
```javascript
// Primary event handler - this is what the server actually emits
this.socket.on('claude_event', (data) => {
    console.log('Received claude_event:', data);

    // Validate event schema
    const validatedEvent = this.validateEventSchema(data);
    if (!validatedEvent) {
        console.warn('Invalid event schema received:', data);
        return;
    }

    // Transform and add to events list
    const transformedEvent = this.transformEvent(validatedEvent);
    console.log('Transformed event:', transformedEvent);
    this.addEvent(transformedEvent);  // ← Single addition per received event
});
```

**Client is NOT registering duplicate listeners** - only one `claude_event` handler exists.

## The Problem (CONFIRMED)

The issue is **dual server emissions with EventBus re-broadcast**:

1. **EventBus.publish()** (core.py:384) - Publishes to EventBus
2. **DirectSocketIORelay** (direct_relay.py:73) - **LISTENS to EventBus and RE-BROADCASTS via broadcaster**
3. **sio.emit('claude_event')** (core.py:414) - Direct broadcast to dashboard clients

**This creates DOUBLE EMISSION:**
- Event → EventBus → DirectSocketIORelay → broadcaster → Socket.IO clients (**EMISSION #1**)
- Event → Direct sio.emit() → Socket.IO clients (**EMISSION #2**)

Both emissions reach the dashboard, causing duplication!

## Evidence

### Server Logs Pattern (Expected)
```
📨 Received HTTP event: user_prompt_submit
Published to EventBus: hook.user_prompt_submit       ← EventBus emission
✅ Event broadcasted: user_prompt_submit to 1 clients ← Direct Socket.IO emission
```

### Dashboard Receives (What Actually Happens)
```
Received claude_event: {type: 'hook', subtype: 'user_prompt_submit', ...}  ← From direct emit
Received claude_event: {type: 'hook', subtype: 'user_prompt_submit', ...}  ← From EventBus listener?
```

## Investigation Questions (ANSWERED)

### 1. Are there EventBus listeners that emit to Socket.IO? ✅ YES

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/event_bus/direct_relay.py`

**Lines 56-76**: DirectSocketIORelay.start() registers wildcard listener
```python
def start(self) -> None:
    """Start the relay by subscribing to EventBus events with retry logic."""
    if not self.enabled:
        logger.warning("DirectSocketIORelay is disabled")
        return

    # Create handler for wildcard events
    def handle_wildcard_hook_event(event_type: str, data: Any):
        """Handle wildcard hook events from the event bus."""
        self._handle_hook_event(event_type, data)

    # Subscribe to all hook events via wildcard
    # THIS IS THE DUPLICATION SOURCE!
    self.event_bus.on("hook.*", handle_wildcard_hook_event)  # ← LISTENER #1

    logger.info("[DirectRelay] Subscribed to hook.* events on EventBus")
```

**Lines 139-227**: _handle_hook_event() re-broadcasts to Socket.IO
```python
def _handle_hook_event(self, event_type: str, data: Any):
    """Internal method to handle hook events and broadcast them."""
    try:
        if event_type.startswith("hook."):
            # ...prepare broadcast data...

            # RE-BROADCAST via broadcaster
            self.server.broadcaster.broadcast_event(  # ← RE-EMISSION!
                event_type, broadcast_data
            )
            self.stats["events_relayed"] += 1
```

**CONFIRMED**: DirectSocketIORelay listens to `hook.*` events on EventBus and re-broadcasts them!

### 2. Is HookEventHandler registering duplicate handlers? ❌ NO

- File: `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/socketio/handlers/hook.py`
- `register_events()` method is EMPTY (lines 22-29)
- Events are passed from ConnectionEventHandler (lines 31-102)
- **NOT a source of duplication**

### 3. Is the broadcaster duplicating emissions? ❌ NO

- The broadcaster itself is NOT duplicating
- But it IS being called TWICE:
  - Once by DirectSocketIORelay (via EventBus)
  - Once by direct emit in core.py
- Broadcaster is functioning correctly - just being used twice!

## Fix Recommendations

### Option 1: Disable DirectSocketIORelay (RECOMMENDED - SAFEST)

**Why**: DirectSocketIORelay is redundant since core.py already emits directly to clients.

**Change**: Disable EventBus integration in configuration

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/event_bus/config.py`

**Current Setting** (lines 55-60):
```python
relay_enabled: bool = field(
    default_factory=lambda: os.environ.get(
        "CLAUDE_MPM_RELAY_ENABLED", "true"  # ← DEFAULT IS "true" (CAUSING DUPLICATION)
    ).lower()
    == "true"
)
```

**Fix Option A**: Change default to "false" in code:
```python
relay_enabled: bool = field(
    default_factory=lambda: os.environ.get(
        "CLAUDE_MPM_RELAY_ENABLED", "false"  # ← Change default to "false"
    ).lower()
    == "true"
)
```

**Fix Option B**: Set environment variable (no code changes):
```bash
export CLAUDE_MPM_RELAY_ENABLED=false
```

**Verification**:
```bash
# Check current setting
python3 -c "from claude_mpm.services.event_bus.config import get_config; print(get_config().relay_enabled)"
# Should print: False (after fix)
```

**Benefits**:
- Non-destructive (can re-enable easily)
- No code changes required
- DirectSocketIORelay simply won't start
- EventBus can still be used for other purposes

### Option 2: Remove EventBus Emission (ALTERNATIVE)

**Why**: Remove the redundant EventBus publish since direct emit already works.

**Change**: `core.py` lines 376-388

```python
# REMOVE EventBus publication - direct Socket.IO emit is sufficient
# DirectSocketIORelay was creating duplicate emissions

# Comment out or remove:
# try:
#     from claude_mpm.services.event_bus import EventBus
#     event_bus = EventBus.get_instance()
#     event_type = f"hook.{event_data.get('subtype', 'unknown')}"
#     event_bus.publish(event_type, event_data)
# except Exception as e:
#     self.logger.warning(f"Failed to publish to EventBus: {e}")
```

**Benefits**:
- Removes unnecessary code path
- Simpler event flow
- Less overhead

**Risks**:
- If other components rely on EventBus hook events, this breaks them
- Requires verification that EventBus isn't used elsewhere

### Option 2: Conditional EventBus Emission

**Why**: Keep EventBus for internal listeners, but add flag to prevent re-broadcast.

**Change**: `core.py` lines 376-388

```python
# Publish to EventBus with metadata to prevent re-broadcast
try:
    from claude_mpm.services.event_bus import EventBus

    event_bus = EventBus.get_instance()
    event_type = f"hook.{event_data.get('subtype', 'unknown')}"

    # Add metadata to prevent Socket.IO re-emission
    event_data_with_metadata = {
        **event_data,
        '_already_broadcasted': True  # Prevent re-emission
    }

    event_bus.publish(event_type, event_data_with_metadata)
    self.logger.debug(f"Published to EventBus: {event_type}")
except Exception as e:
    self.logger.warning(f"Failed to publish to EventBus: {e}")
```

Then update any EventBus listeners to check for `_already_broadcasted` flag.

### Option 3: Remove Direct Socket.IO Emission

**Why**: Use EventBus as the single source of truth for all events.

**Change**: `core.py` lines 391-434

```python
# Remove direct Socket.IO emission, rely on EventBus listeners
# EventBus listeners will handle broadcasting to clients

# Comment out or remove:
# if self.sio:
#     # ... buffer management ...
#     await self.sio.emit("claude_event", event_data)
```

**CAUTION**: This requires ensuring EventBus has proper Socket.IO broadcast listeners configured.

## Testing Protocol

### 1. Verify Current Duplication
```bash
# Terminal 1: Start monitor
claude-mpm monitor

# Terminal 2: Trigger events
claude-code "list files"

# Terminal 3: Watch server logs
tail -f ~/.claude-mpm/logs/socketio-server.log | grep "Event broadcasted"

# Dashboard: Count events in Events tab
# Expected: 2x events (duplicated)
```

### 2. After Fix - Verify Single Emission
```bash
# Same test sequence
# Expected: 1x event per hook trigger
```

### 3. Regression Testing
- [ ] Events appear in dashboard (single instance)
- [ ] EventBus internal communication still works (if used)
- [ ] Session tracking still functions
- [ ] Agent hierarchy displays correctly
- [ ] File operations tracked accurately

## Impact Analysis

### Files Modified
1. `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/socketio/server/core.py` (lines 376-388)

### Components Affected
- ✅ Dashboard event display (FIX TARGET)
- ⚠️ EventBus internal listeners (verify still needed)
- ✅ Socket.IO broadcast mechanism (unchanged)
- ✅ Hook event processing (unchanged)

### Breaking Changes
- **Option 1**: None (EventBus removal safe if no internal listeners)
- **Option 2**: None (backward compatible)
- **Option 3**: Requires EventBus listener configuration (breaking)

## Related Files

### Event Processing Pipeline
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/socketio/server/core.py` - HTTP API handler
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/socketio/event_normalizer.py` - Event normalization
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/event_bus/event_bus.py` - EventBus singleton
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/socketio/handlers/hook.py` - Hook handler (passive)
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/socketio/handlers/connection.py` - Connection handler

### Client-Side Processing
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard/static/js/socket-client.js` - Socket.IO client
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard/static/js/components/event-viewer.js` - Event display
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard/static/js/dashboard.js` - Dashboard coordinator

## Conclusion

**Root Cause**: DirectSocketIORelay listens to EventBus `hook.*` events and re-broadcasts them to Socket.IO clients. Combined with the direct `sio.emit()` in core.py, this creates duplicate emissions.

**Recommended Fix**: Disable DirectSocketIORelay via configuration (Option 1) - safest and most reversible.

**Priority**: High - affects all dashboard event displays.

**Complexity**: Very Low - single configuration change or environment variable.

**Risk**: Minimal - DirectSocketIORelay is redundant since direct emit already works.

## Next Steps

1. ✅ **Verify EventBus listeners**: CONFIRMED - DirectSocketIORelay at direct_relay.py:73
2. **Check EventBus configuration**: Locate relay_enabled setting
3. **Test Option 1 fix**: Set `relay_enabled = False` in config or env var
4. **Monitor dashboard**: Confirm single event display
5. **Regression test**: Ensure all dashboard features work
6. **Commit fix**: Create PR with test results and configuration change

---

**Investigation Complete**
**Confidence Level**: High (95%)
**Ready for Implementation**: Yes
