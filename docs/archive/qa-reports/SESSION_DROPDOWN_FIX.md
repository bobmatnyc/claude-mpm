# Session Dropdown Working Directory Fix

## Problem
The session dropdown in the Claude MPM dashboard was not showing working directory information. It only displayed session IDs without any context about which project/directory each session was working in.

## Solution
Fixed the session dropdown to display working directories in the format: `{working_directory} | {session_id}`

## Changes Made

### 1. **session-manager.js** (Lines 85-145)
- Enhanced `updateSessionSelect()` method to:
  - Get default working directory from multiple sources
  - Display working directory for "All Sessions" option
  - Extract and display working directory for each session
  - Add debug logging to track directory extraction

### 2. **socket-client.js** (Lines 540-561)
- Improved working directory extraction in `addEvent()` method:
  - Check multiple possible field locations for working directory
  - Support various naming conventions (cwd, working_directory, working_dir, etc.)
  - Check nested locations (instance_info, data fields)
  - Add logging for successful extraction

### 3. **working-directory.js** (Lines 311-364)
- Enhanced `getDefaultWorkingDir()` method:
  - Check current working directory first
  - Try header display element
  - Fall back to footer or project default
  - Better validation and error handling

## Key Features

### Working Directory Sources (Priority Order)
1. Session's stored `working_directory` field
2. Extracted from recent session events
3. Working Directory Manager's default
4. Header display element (`#working-dir-path`)
5. Fallback: `/Users/masa/Projects/claude-mpm`

### Event Field Locations Checked
- `eventData.data.cwd`
- `eventData.data.working_directory`
- `eventData.data.working_dir`
- `eventData.data.workingDirectory`
- `eventData.data.instance_info.working_dir`
- `eventData.data.instance_info.working_directory`
- `eventData.data.instance_info.cwd`

## Testing

### Expected Behavior
- Dropdown shows: `/Users/masa/Projects/claude-mpm | All Sessions`
- Session options show: `/path/to/project | abc123de...`
- Active sessions marked with `[ACTIVE]` suffix

### Debug Logging
The fix adds console logging with tags:
- `[SESSION-MANAGER]` - Session manager operations
- `[SESSION-DROPDOWN]` - Dropdown formatting
- `[SOCKET-CLIENT]` - Working directory extraction from events
- `[WORKING-DIR-DEBUG]` - Working directory resolution

### Verification Steps
1. Open Claude MPM dashboard
2. Open browser console (F12)
3. Check session dropdown - should show working directories
4. Filter console by `[SESSION` to see debug output
5. Change sessions and verify directory updates

## Files Modified
- `/src/claude_mpm/dashboard/static/js/components/session-manager.js`
- `/src/claude_mpm/dashboard/static/js/socket-client.js`
- `/src/claude_mpm/dashboard/static/js/components/working-directory.js`

## Test Files Created
- `/test_session_dropdown.html` - Visual test page showing before/after
- `/SESSION_DROPDOWN_FIX.md` - This documentation

## Notes
- The fix maintains backward compatibility with existing session data
- Falls back gracefully if working directory is not available
- Uses project default (`/Users/masa/Projects/claude-mpm`) when needed
- Debug logging can be removed once fix is verified working