# Event Filtering Fix for Dashboard Views

## Problem
The filtered dashboard views (agents.html, tools.html, files.html) were not showing data properly because they used simplistic string matching that didn't account for the complex event structure in Claude MPM.

## Root Cause
The original filtering logic used simple `.includes()` checks:
```javascript
// Too simplistic - missed many events
if (type.includes('agent') || type.includes('Agent')) { ... }
```

This approach failed because events have various structures:
- Direct type fields: `type`, `event_type`, `eventType`
- Hook events: `hook_event_name`
- Nested data fields: `data.agent_name`, `data.tool`, `data.file_path`
- Subtype patterns: `pm_task`, `bash_command`, `file_operation`

## Solution: EventFilterService

Created a comprehensive `EventFilterService` class that handles all event variations:

### Key Features

1. **Multi-field Detection**
   - Checks multiple type fields in priority order
   - Examines hook event names
   - Inspects nested data structures
   - Matches against subtype patterns

2. **Configuration-Driven Filtering**
   ```javascript
   eventConfigs = {
       agent: {
           typePatterns: [/agent/i, /subagent/i, /pm_/i, ...],
           hookPatterns: ['SubagentStart', 'AgentInference', ...],
           dataFields: ['agent_name', 'agent_id', ...],
           subtypes: ['agent_deployment', ...]
       },
       // Similar for 'tool' and 'file'
   }
   ```

3. **Event Normalization**
   - Converts various event formats to consistent structure
   - Extracts relevant information based on category
   - Provides clean API for UI components

4. **Performance Optimization**
   - Caches filtering results
   - Efficient pattern matching
   - Minimal overhead

## Implementation

### Files Created/Modified

1. **Created: `/src/claude_mpm/dashboard/static/built/shared/event-filter-service.js`**
   - Core EventFilterService class
   - Comprehensive event detection logic
   - Event normalization methods

2. **Updated: `/src/claude_mpm/dashboard/static/agents.html`**
   - Integrated EventFilterService
   - Replaced simplistic filtering with service calls
   - Added debug statistics

3. **Updated: `/src/claude_mpm/dashboard/static/tools.html`**
   - Same integration as agents.html
   - Tool-specific event handling

4. **Updated: `/src/claude_mpm/dashboard/static/files.html`**
   - Same integration pattern
   - File operation tracking

### Test Scripts Created

1. **`/scripts/test_event_filtering.py`**
   - Sends various event types to test filtering
   - Validates each category receives correct events

2. **`/scripts/verify_event_filtering.py`**
   - Automated verification of filtering logic
   - Tests EventFilterService integration
   - Validates dashboard views

3. **`/scripts/demo_event_filtering.py`**
   - Interactive demo with realistic events
   - Shows filtering in action
   - Continuous event stream for testing

## Usage

### For Users
1. Open dashboard filtered views:
   - http://localhost:8765/static/agents.html
   - http://localhost:8765/static/tools.html
   - http://localhost:8765/static/files.html

2. Events are automatically filtered to the correct view

3. Enable debug mode (Toggle Debug button) to see:
   - Total events received
   - Events filtered for this view
   - Filter statistics

### For Developers

Use EventFilterService in any component:

```javascript
// Initialize service
const eventFilter = new EventFilterService();

// Check event category
if (eventFilter.isEventType(event, 'agent')) {
    // Handle agent event
}

// Normalize event data
const normalized = eventFilter.normalizeEvent(event, 'agent');
console.log(normalized.agent.name); // Consistent access
```

## Testing

Run the test suite:
```bash
# Verify filtering works
python scripts/verify_event_filtering.py

# Interactive demo
python scripts/demo_event_filtering.py

# Send test events
python scripts/test_event_filtering.py
```

## Benefits

1. **Comprehensive Coverage**: Catches all event types, not just obvious ones
2. **Maintainable**: Configuration-driven approach makes it easy to add new event types
3. **Consistent**: Normalization ensures UI components have predictable data
4. **Performant**: Caching and efficient patterns prevent slowdowns
5. **Debuggable**: Built-in debug features help diagnose issues

## Future Improvements

1. Add event type discovery mode to automatically learn new patterns
2. Implement fuzzy matching for ambiguous events
3. Add configurable filter rules via UI
4. Create event type documentation generator
5. Add metrics tracking for event distribution