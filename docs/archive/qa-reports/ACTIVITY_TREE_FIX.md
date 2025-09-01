# Activity Tree Socket Integration Fix

## Problem
The Activity tree component was failing with the error:
```
window.socketClient.on is not a function
```

This occurred because the `SocketClient` class didn't expose the standard Socket.IO `on()` and `off()` methods that the Activity tree was trying to use.

## Root Cause Analysis
1. The `SocketClient` class wrapped the Socket.IO instance but didn't proxy the `on()` and `off()` methods
2. The Activity tree was trying to subscribe to a non-existent 'hook_event' socket event
3. The actual event name emitted by the server is 'claude_event', which gets transformed to include `hook_event_name` field

## Solution Implemented

### 1. Added `on()` and `off()` methods to SocketClient
In `src/claude_mpm/dashboard/static/js/socket-client.js`:

```javascript
/**
 * Subscribe to socket events (proxy to underlying socket)
 * @param {string} event - Event name
 * @param {Function} callback - Callback function
 */
on(event, callback) {
    if (this.socket) {
        return this.socket.on(event, callback);
    } else {
        console.warn(`Cannot subscribe to '${event}': socket not initialized`);
    }
}

/**
 * Unsubscribe from socket events (proxy to underlying socket)
 * @param {string} event - Event name
 * @param {Function} callback - Callback function (optional)
 */
off(event, callback) {
    if (this.socket) {
        return this.socket.off(event, callback);
    } else {
        console.warn(`Cannot unsubscribe from '${event}': socket not initialized`);
    }
}
```

### 2. Fixed Activity Tree Event Subscription
In `src/claude_mpm/dashboard/static/js/components/activity-tree.js`:

Changed from trying to subscribe to a non-existent 'hook_event' to using the proper `onEventUpdate` callback pattern:

```javascript
// OLD (broken):
window.socketClient.on('hook_event', (event) => {
    this.processEvent(event);
});

// NEW (working):
window.socketClient.onEventUpdate((events) => {
    // Process only the new events since last update
    const newEventCount = events.length - this.events.length;
    if (newEventCount > 0) {
        const newEvents = events.slice(this.events.length);
        newEvents.forEach(event => {
            if (event.hook_event_name) {
                this.processEvent(event);
            }
        });
        this.events = [...events];
    }
});
```

## Benefits of This Fix

1. **Backward Compatibility**: The new `on()` and `off()` methods make SocketClient compatible with standard Socket.IO patterns
2. **Proper Event Flow**: Activity tree now receives events through the correct channel
3. **Event Filtering**: Only processes events that have `hook_event_name` field (relevant hook events)
4. **Prevents Duplicates**: Tracks processed events to avoid reprocessing

## Testing Recommendations

1. Open the dashboard and navigate to the Activity tab
2. Perform actions that generate hook events (TodoWrite, SubagentStart, etc.)
3. Verify that the Activity tree updates without errors
4. Check browser console for proper event processing logs

## Files Modified

1. `/src/claude_mpm/dashboard/static/js/socket-client.js` - Added `on()` and `off()` methods
2. `/src/claude_mpm/dashboard/static/js/components/activity-tree.js` - Fixed event subscription pattern