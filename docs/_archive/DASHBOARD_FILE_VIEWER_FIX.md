# Dashboard File Viewer Fix

## Issue
The Socket.IO dashboard's Files tab wasn't showing file operations because tool names were coming in lowercase from events, but the file-tool-tracker.js was checking for capitalized names.

## Root Cause
The `isFileOperation()` function in `file-tool-tracker.js` was doing case-sensitive comparisons:
- Events from Claude hooks send tool names like "read", "write", "edit" (lowercase)
- The code was checking for exact matches against lowercase tool names
- But the tool_name field was not being converted to lowercase before comparison

## Solution Applied

### 1. Case-Insensitive Tool Name Matching
Updated `src/claude_mpm/dashboard/static/js/components/file-tool-tracker.js`:
- Line 333: Convert tool_name to lowercase before checking against file tools array
- This ensures both "Read" and "read" are recognized as file operations

### 2. Support for New Tools
Added support for newer Claude Code tools:
- Glob - file pattern matching
- LS - directory listing  
- NotebookEdit - Jupyter notebook editing
- MultiEdit - multiple edits in one operation

### 3. Cache Busting
Added version query parameters to JavaScript files in `src/claude_mpm/dashboard/templates/index.html`:
- `file-tool-tracker.js?v=1.1` - forces browsers to load the updated version
- Prevents stale cached versions from being used

## Testing

Created test script at `scripts/test_dashboard_file_viewer.py` that:
1. Connects to the Socket.IO server on port 8765
2. Sends test file operation events for all supported tools
3. Includes test for lowercase tool names (the original issue)
4. Verifies all operations appear in the Files tab

### How to Test
```bash
# Start the dashboard
./claude-mpm dashboard

# Open browser to http://localhost:8765

# Run the test script
python scripts/test_dashboard_file_viewer.py

# Check the Files tab - should show 8 file operations
```

## Files Modified
- `/src/claude_mpm/dashboard/static/js/components/file-tool-tracker.js` - Fixed case sensitivity
- `/src/claude_mpm/dashboard/templates/index.html` - Added cache busting
- `/scripts/test_dashboard_file_viewer.py` - Created test script

## Verification
The fix ensures that file operations from Claude Code (which sends lowercase tool names) are properly tracked and displayed in the dashboard's Files tab.