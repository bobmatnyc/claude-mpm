# Fix for Duplicate Continue Messages in Hook System

## Problem
Multiple `{"action": "continue"}` messages were being output from the hook system, causing issues with Claude Code's hook processing. Three identical continue messages appeared in hook output, particularly visible in PreToolUse:Bash hook wrapper output.

## Root Cause Analysis

### Issue 1: Multiple Hook Registrations
The `install_hooks.py` script was registering the same `hook_wrapper.sh` for ALL event types (UserPromptSubmit, PreToolUse, PostToolUse, Stop, SubagentStop). When Claude Code processes an event, it may call all registered hooks, resulting in multiple invocations of the same script.

### Issue 2: Multiple Continue Sources
The continue message could be output from multiple places:
1. Normal execution path in `handle()` method
2. Exception handler in `main()` function
3. Shell wrapper if Python handler fails

### Issue 3: No Duplicate Detection
When the same hook handler was invoked multiple times for the same event, each invocation would process the event and emit to Socket.IO, causing duplicate processing.

## Solution Implemented

### 1. Duplicate Event Detection
Added duplicate detection logic to skip processing events that have been seen within the last 100ms:
- Track recent events with timestamps in a deque
- Generate unique event keys based on event type, session ID, and key parameters
- Skip processing (but still output continue) for duplicate events

### 2. Single Continue Output Per Invocation
Ensured only one continue message is output per invocation:
- Added `_continue_sent` flag to track if continue has been output
- Modified exception handler to check flag before outputting continue
- Added explicit exit after successful execution in wrapper script

### 3. Event Key Generation
Implemented smart event key generation that creates unique identifiers for events:
- PreToolUse: Includes tool name and relevant parameters
- Task delegations: Includes agent type and prompt preview
- UserPromptSubmit: Includes prompt preview
- Other events: Use event type and session ID

## Code Changes

### `/src/claude_mpm/hooks/claude_hooks/hook_handler.py`
- Added global `_recent_events` deque to track recent events
- Added `_get_event_key()` method to generate unique event identifiers
- Modified `handle()` to check for and skip duplicate events
- Fixed exception handler to respect `_continue_printed` flag

### `/src/claude_mpm/hooks/claude_hooks/hook_wrapper.sh`
- Added explicit `exit 0` after successful execution
- Ensured wrapper only outputs continue on Python handler failure

## Testing
Created comprehensive test scripts:
- `test_hook_duplicate_fix.py`: Verifies each invocation outputs exactly one continue
- `test_hook_duplicate_detection.py`: Verifies duplicate detection logic works correctly

## Results
✅ Each hook invocation now outputs exactly one `{"action": "continue"}`
✅ Duplicate events within 100ms are detected and skipped
✅ Socket.IO events are only emitted once per unique event
✅ No false positives after the 100ms window

## Impact
This fix ensures:
1. Clean hook output without duplicate continue messages
2. Proper event processing without duplicates
3. Better performance by skipping redundant processing
4. Maintained compatibility with Claude Code's hook system