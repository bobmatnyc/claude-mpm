# Code Tree Debugging Enhancements

## Issue
The code tree in the Claude MPM dashboard was not properly expanding the `src` directory when clicked. The Research agent identified that the frontend sends `code:discover:top_level` but the event handler for `code:top_level:discovered` was missing proper debugging.

## Fixes Applied

### 1. Enhanced Console Logging
Added comprehensive debugging throughout the code tree component to track the flow of data:

#### Node Click Debugging
- Shows node name, path, type, loaded status
- Displays children count and working directory
- Helps identify what node is being clicked

#### Top-Level Discovery Debugging  
- Logs the discovery request being sent with full payload
- Shows received items with names and types
- Displays root node lookup status
- Shows population of root node with children

#### Directory Discovery Debugging
- Logs the received path and children
- Shows path conversion from absolute to relative
- Displays node search results
- Lists children being added

#### Path Resolution Debugging
- `findNodeByPath`: Shows the search path and root node details
- Lists all child paths when searching
- Shows complete tree structure when node not found
- `ensureFullPath`: Traces path conversion step-by-step
- Shows working directory and final constructed path

### 2. Key Debug Points

1. **Request Flow**:
   ```
   📤 Sending top-level discovery request
   📦 Received top-level discovery  
   🔎 Looking for root node
   🌳 Populating root node with children
   ```

2. **Click Handling**:
   ```
   🔍 Node clicked
   🔗 ensureFullPath called
   📤 Sending discovery request
   📥 Received directory discovery
   ```

3. **Error Detection**:
   ```
   ❌ Node with path "X" not found
   (Lists all available paths in tree)
   ```

## Testing

Created `/Users/masa/Projects/claude-mpm/test_code_tree_debug.py` to help test the fixes:

```bash
python test_code_tree_debug.py
```

This script:
1. Starts the dashboard
2. Opens the browser
3. Provides testing instructions
4. Shows what to look for in console logs

## Expected Behavior

With these debugging enhancements:

1. **On Tab Load**: 
   - Root node auto-populates with top-level items
   - Console shows the discovery request and response
   - Tree displays project structure

2. **On Directory Click**:
   - Console shows the node being clicked
   - Path resolution is traced step-by-step  
   - Discovery request is logged
   - Response handling is tracked
   - Tree expands to show contents

3. **On Error**:
   - Clear error messages in console
   - Complete tree structure dumped for analysis
   - Path mismatches are identified

## Benefits

- **Visibility**: Every step of the discovery and expansion process is logged
- **Debugging**: Easy to identify where the flow breaks
- **Path Tracking**: Clear understanding of how paths are resolved
- **Error Detection**: Quick identification of missing nodes or path issues

## Code Locations

All changes were made to:
`/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard/static/js/components/code-tree.js`

Key methods enhanced:
- `onNodeClick()` - Added comprehensive node state logging
- `onTopLevelDiscovered()` - Added item listing and root node tracking  
- `onDirectoryDiscovered()` - Added children listing
- `findNodeByPath()` - Added root node details and child path listing
- `ensureFullPath()` - Added step-by-step path resolution logging
- `autoDiscoverRootLevel()` - Added request payload logging

## Next Steps

With these debugging enhancements in place:
1. Run the test script to observe the actual behavior
2. Check console logs to identify any remaining issues
3. The enhanced logging will pinpoint exactly where the problem occurs
4. Fix can be applied based on the specific issue identified