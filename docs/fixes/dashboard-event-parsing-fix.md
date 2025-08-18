# Dashboard Event Parsing Fix

## Issue Description
Dashboard events were displaying as "unknown" due to critical fields (`type`, `subtype`, `timestamp`, `id`) being overwritten by fields from the event's `data` object.

## Root Cause
In `/src/claude_mpm/dashboard/static/js/socket-client.js`, the `transformEvent` function was copying ALL fields from `event.data` to the top level without protecting critical fields:

```javascript
// PROBLEMATIC CODE (lines 500-505)
Object.keys(eventData.data).forEach(key => {
    transformedEvent[key] = eventData.data[key];  // This overwrites everything!
});
```

This caused issues like:
- `hook.pre_tool` events with `data.type = "something"` would become type "something"
- Events would lose their proper type/subtype and display as "unknown"
- Timestamps could be overwritten by different timestamps in data

## Solution Implemented

### 1. Protected Fields List
Created a list of fields that should NEVER be overwritten:
- `type`
- `subtype` 
- `timestamp`
- `id`
- `event`
- `event_type`
- `originalEventName`

### 2. Conditional Copying
Modified the field copying logic to skip protected fields:

```javascript
// FIXED CODE
const protectedFields = ['type', 'subtype', 'timestamp', 'id', 'event', 'event_type', 'originalEventName'];

Object.keys(eventData.data).forEach(key => {
    if (!protectedFields.includes(key)) {
        transformedEvent[key] = eventData.data[key];
    } else {
        console.warn(`Protected field '${key}' in data object was not copied to top level`);
    }
});
```

### 3. Original Event Name Preservation
Added `originalEventName` field to preserve the original event name for display fallback:

```javascript
if (!eventData.type && eventData.event) {
    transformedEvent.originalEventName = eventData.event;
} else if (eventData.type) {
    transformedEvent.originalEventName = eventData.type;
}
```

### 4. Improved Display Logic
Enhanced the event viewer to use `originalEventName` as a fallback:

```javascript
formatEventType(event) {
    if (event.type && event.subtype) {
        return `${event.type}.${event.subtype}`;
    }
    if (event.type) {
        return event.type;
    }
    if (event.originalEventName) {
        return event.originalEventName;  // New fallback
    }
    return 'unknown';
}
```

## Files Modified
1. `/src/claude_mpm/dashboard/static/js/socket-client.js` - Main fix for field protection
2. `/src/claude_mpm/dashboard/static/js/components/event-viewer.js` - Improved display logic

## Testing

### Unit Tests
Created comprehensive unit tests in:
- `/tests/dashboard/test_event_field_protection.py` - Tests field protection logic

### Validation Scripts
- `/scripts/test_event_transform_logic.py` - Python simulation of JS logic
- `/scripts/validate_event_fix.py` - Comprehensive validation suite
- `/scripts/demo_event_fix.py` - Simple demonstration of the fix

### Test Coverage
The fix handles:
- Hook events with conflicting type/subtype in data
- Legacy event formats (SubagentStart, UserPrompt, etc.)
- Session events with subtype conflicts
- Events with timestamp/id conflicts
- Dotted type formats (e.g., `hook.pre_tool`)
- Complex nested events

## Verification
To verify the fix works:

1. Build the dashboard: `npm run build:dashboard`
2. Run the demo: `python scripts/demo_event_fix.py`
3. Open http://localhost:8080
4. Check that events display with correct types (not "unknown")

## Impact
- ✅ Events now display with correct types
- ✅ Critical fields are protected from overwriting
- ✅ Backward compatibility maintained
- ✅ Data fields still copied to top level (except protected ones)
- ✅ Original event names preserved for display

## Performance
No performance impact - the fix only adds a simple array check during event transformation.