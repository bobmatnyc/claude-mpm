# Agent Event Tracking Fix Summary

## Problem
The claude-mpm dashboard was showing "0" events for all agents in the Agents tab, despite agents being actively used.

## Root Cause Analysis
Based on research findings, the issue was caused by:

1. **Socket.IO Connection Failures**: The hook handler was failing to establish or maintain Socket.IO connections to port 8765, preventing events from reaching the dashboard.

2. **Missing Event Count Property**: The dashboard was trying to display `eventCount` but the actual property from `getUniqueAgentInstances()` was `totalEventCount`.

3. **Insufficient Event Emission**: SubagentStart events were not being emitted, making it harder to track agent delegations.

## Fixes Implemented

### 1. Improved Socket.IO Connection Reliability (`hook_handler.py`)

#### Enhanced Connection Logic
- Implemented retry logic with exponential backoff (3 attempts)
- Increased connection timeout to 1.0 seconds for stability
- Enabled auto-reconnection in Socket.IO client
- Better connection state tracking and recovery

#### Code Changes:
```python
# Before: Single attempt, no retry, short timeout
self.sio_client.connect(f'http://localhost:{port}', wait=False, wait_timeout=0.5)

# After: Multiple attempts, exponential backoff, proper wait
for attempt in range(max_retries):
    self.sio_client.connect(f'http://localhost:{port}', wait=True, wait_timeout=1.0)
    # ... with retry logic and exponential backoff
```

### 2. Enhanced Event Emission and Logging

#### Improved Error Handling
- Added comprehensive logging for debugging
- Automatic reconnection for critical events (subagent_stop, pre_tool)
- Better error recovery with immediate retry for failed emissions

#### Added SubagentStart Events
- Now emitting `subagent_start` events when Task delegation begins
- Provides better tracking of agent lifecycle
- Includes agent type, session ID, and task details

### 3. Fixed Event Count Display (`event-processor.js`)

#### Corrected Property Reference
```javascript
// Before: Using wrong property name
const eventCount = instance.eventCount || 0;

// After: Using correct property with fallback
const eventCount = instance.totalEventCount || instance.eventCount || 0;
```

### 4. Enhanced Agent Inference (`agent-inference.js`)

#### Added Support for SubagentStart Events
- Now recognizing and processing SubagentStart events from Socket.IO
- Improved agent type detection and normalization
- Better logging for debugging agent delegations

#### Added Debug Logging
- Logs Task delegations for visibility
- Logs SubagentStop events for tracking
- Logs SubagentStart events from Socket.IO

## Testing

### Test Script Created
Created `/scripts/test_agent_event_tracking.py` to verify:
1. Socket.IO connection reliability
2. Agent event emission (subagent_start/stop)
3. Multiple agent delegations
4. Event counting in dashboard

### How to Test
```bash
# Run the test script
./scripts/test_agent_event_tracking.py

# Then check the dashboard
# 1. Open http://localhost:8080
# 2. Navigate to Agents tab
# 3. Verify agents show event counts > 0
```

## Technical Details

### Socket.IO Event Flow
1. Claude Code triggers hook events
2. Hook handler processes events in `hook_handler.py`
3. Events are emitted via Socket.IO to port 8765
4. Dashboard receives events via `socket-client.js`
5. Agent inference processes events in `agent-inference.js`
6. Event processor displays counts in `event-processor.js`

### Event Types for Agent Tracking
- `hook.pre_tool` with `tool_name: 'Task'` - Agent delegation start
- `hook.subagent_start` - Explicit agent start event (new)
- `hook.subagent_stop` - Agent delegation end
- `delegation_details` in pre_tool events - Contains agent type info

## Impact
- Agents now properly show event counts in the dashboard
- Better visibility into agent delegations and activity
- Improved debugging capabilities with comprehensive logging
- More reliable Socket.IO connection handling

## Future Improvements
1. Consider adding persistent event storage for historical analysis
2. Add real-time event count updates without page refresh
3. Implement agent performance metrics (duration, success rate)
4. Add agent delegation visualization (timeline view)