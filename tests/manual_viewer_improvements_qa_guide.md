# Manual QA Testing Guide: Viewer Improvements

## Overview
This guide provides step-by-step manual testing procedures to validate the viewer improvements implemented in the Claude MPM dashboard.

## Original Requirements
1. **VIEWER should be in the blue file path bar** - Users should be able to click the blue file path bar to open a file browser overlay
2. **DIFF viewer should be attached to each EDIT tool use** - Each Edit/MultiEdit event should have an inline diff viewer showing only the changes for that specific edit

## Pre-Testing Setup

### 1. Environment Setup
```bash
# Ensure the dashboard is running
cd /Users/masa/Projects/claude-mpm
python -m claude_mpm.dashboard.server

# Open browser and navigate to dashboard
# URL: http://localhost:8765
```

### 2. Generate Test Data (if needed)
To properly test Edit diff viewers, you need Edit/MultiEdit events. Run some file operations:
```bash
# Create test file operations to generate Edit events
echo "original content" > test_file.txt
# Then make some edits using Claude with Edit tool
```

---

## Test Suite 1: File Path Bar Viewer

### Test 1.1: Clickable Blue File Path Bar
**Expected**: Blue file path bar should be clickable and trigger file viewer overlay

**Steps**:
1. Open the dashboard
2. Locate the blue file path bar in the header (should show current working directory)
3. Click on the blue file path text (NOT the change directory button)

**Expected Results**:
- ✅ File path text is visually clickable (cursor changes to pointer)
- ✅ Clicking opens a directory viewer overlay
- ✅ Overlay appears below the blue file path bar
- ✅ Overlay shows directory contents (files and folders)

**Pass/Fail**: ⬜

**Notes**: ________________________________

### Test 1.2: Overlay Positioning and Layout
**Expected**: Overlay should be properly positioned and styled

**Steps**:
1. Click the blue file path bar to open overlay
2. Observe overlay position and styling

**Expected Results**:
- ✅ Overlay appears directly below the blue file path bar
- ✅ Overlay has proper styling (white background, border, shadow)
- ✅ Overlay has header with title and close button
- ✅ Overlay has proper width (400-600px) and max height (400px)
- ✅ Overlay has footer with usage hint

**Pass/Fail**: ⬜

**Notes**: ________________________________

### Test 1.3: Directory Navigation
**Expected**: Users should be able to navigate directories within the overlay

**Steps**:
1. Open the file path overlay
2. Look for directory items (folders) in the list
3. Click on a directory item
4. Observe the overlay content updates

**Expected Results**:
- ✅ Directory items are distinguishable from files (folder icon 📁)
- ✅ Clicking a directory updates the overlay content to show that directory's contents
- ✅ Parent directory ".." link is available when not in root
- ✅ File path in header updates to show current directory

**Pass/Fail**: ⬜

**Notes**: ________________________________

### Test 1.4: File Selection
**Expected**: Users should be able to view files by clicking them

**Steps**:
1. Open the file path overlay
2. Click on a file (not directory)
3. Observe what happens

**Expected Results**:
- ✅ Clicking a file opens the file viewer modal
- ✅ File viewer modal shows file contents
- ✅ Directory overlay closes when file viewer opens

**Pass/Fail**: ⬜

**Notes**: ________________________________

### Test 1.5: Shift+Click Directory Change
**Expected**: Shift+clicking the file path bar should open directory change dialog

**Steps**:
1. Hold Shift key
2. Click on the blue file path bar
3. Observe what happens

**Expected Results**:
- ✅ A prompt dialog appears asking for new working directory
- ✅ Entering a valid directory path changes the working directory
- ✅ File path bar updates to show new directory
- ✅ Regular click (without Shift) still opens the overlay

**Pass/Fail**: ⬜

**Notes**: ________________________________

### Test 1.6: Click Outside to Close
**Expected**: Clicking outside the overlay should close it

**Steps**:
1. Open the file path overlay
2. Click somewhere outside the overlay (on the dashboard background)

**Expected Results**:
- ✅ Overlay closes when clicking outside
- ✅ Overlay closes when pressing Escape key
- ✅ Close button (✕) in overlay header works

**Pass/Fail**: ⬜

**Notes**: ________________________________

### Test 1.7: Responsive Behavior
**Expected**: Overlay should adapt to different screen sizes

**Steps**:
1. Open overlay on desktop/full screen
2. Resize browser window to mobile size (375px width)
3. Open overlay again

**Expected Results**:
- ✅ Overlay adapts width to smaller screens
- ✅ Overlay positioning adjusts to stay within viewport
- ✅ Text and icons remain readable on small screens
- ✅ Touch interactions work on mobile devices

**Pass/Fail**: ⬜

**Notes**: ________________________________

---

## Test Suite 2: Edit Tool Diff Viewers

### Test 2.1: Edit Events Have Diff Viewers
**Expected**: Edit and MultiEdit events should show inline diff viewers

**Steps**:
1. Switch to "Events" tab
2. Look for events that mention "Edit" or "MultiEdit" tools
3. Examine the event display

**Expected Results**:
- ✅ Edit tool events have a collapsible diff section below the event content
- ✅ Diff section has a toggle header with icon (📋) and "Show edit" text
- ✅ MultiEdit events show "Show X edits" where X is the number of edits
- ✅ Non-Edit events (Bash, Read, etc.) do NOT have diff viewers

**Pass/Fail**: ⬜

**Notes**: ________________________________

### Test 2.2: Diff Toggle Functionality
**Expected**: Diff viewers should expand/collapse when clicked

**Steps**:
1. Find an Edit event with diff viewer
2. Click on the diff toggle header (📋 "Show edit")
3. Click again to collapse

**Expected Results**:
- ✅ Clicking toggle expands diff viewer to show diff content
- ✅ Arrow icon changes from ▼ to ▲ when expanded
- ✅ Clicking again collapses the diff viewer
- ✅ Multiple diff viewers can be open simultaneously
- ✅ Clicking diff toggle does NOT select/highlight the parent event

**Pass/Fail**: ⬜

**Notes**: ________________________________

### Test 2.3: Diff Content Display
**Expected**: Expanded diff should show old_string → new_string changes

**Steps**:
1. Expand a diff viewer for an Edit event
2. Examine the diff content

**Expected Results**:
- ✅ Diff shows lines with proper coloring:
  - Green background/text for additions (lines starting with +)
  - Red background/text for removals (lines starting with -)
  - Gray text for unchanged context lines
- ✅ Diff content is in a dark-themed code block
- ✅ Diff content uses monospace font
- ✅ Diff scrolls vertically if content is long (max 200px height)

**Pass/Fail**: ⬜

**Notes**: ________________________________

### Test 2.4: MultiEdit Events
**Expected**: MultiEdit events should show multiple edit sections

**Steps**:
1. Find a MultiEdit event (if available)
2. Expand its diff viewer
3. Examine the content

**Expected Results**:
- ✅ MultiEdit shows multiple "Edit 1", "Edit 2", etc. sections
- ✅ Each edit section shows its own diff
- ✅ All edits are from the same MultiEdit operation
- ✅ Toggle text shows correct count (e.g., "Show 3 edits")

**Pass/Fail**: ⬜

**Notes**: ________________________________

### Test 2.5: Diff Viewer Isolation
**Expected**: Each diff viewer should show only the changes for that specific Edit event

**Steps**:
1. Find multiple Edit events in the list
2. Compare their diff viewers
3. Verify content isolation

**Expected Results**:
- ✅ Each diff viewer shows only the changes made by that specific Edit call
- ✅ Diff viewers don't show changes from other Edit operations
- ✅ File paths in diffs correspond to the files being edited in that event
- ✅ Timestamp and operation details match the parent event

**Pass/Fail**: ⬜

**Notes**: ________________________________

### Test 2.6: Event Selection Integration
**Expected**: Diff viewers should not interfere with event selection

**Steps**:
1. Click on an Edit event (not on the diff toggle) to select it
2. Verify event is highlighted and details appear in module viewer
3. Click the diff toggle to expand/collapse diff
4. Verify event selection state

**Expected Results**:
- ✅ Clicking event content (outside diff toggle) selects the event
- ✅ Selected event is highlighted with blue background
- ✅ Event details appear in right-side module viewer
- ✅ Clicking diff toggle does NOT change event selection
- ✅ Diff viewer can be toggled while event is selected

**Pass/Fail**: ⬜

**Notes**: ________________________________

---

## Test Suite 3: Integration Testing

### Test 3.1: Browser Console Errors
**Expected**: No JavaScript errors should appear in browser console

**Steps**:
1. Open browser Developer Tools (F12)
2. Go to Console tab
3. Clear console
4. Interact with both viewer features
5. Check for errors

**Expected Results**:
- ✅ No JavaScript errors appear when using file path viewer
- ✅ No JavaScript errors appear when toggling diff viewers
- ✅ No network errors for missing resources
- ✅ Only expected warnings (if any) appear

**Pass/Fail**: ⬜

**Notes**: ________________________________

### Test 3.2: Keyboard Navigation
**Expected**: Existing keyboard navigation should still work

**Steps**:
1. Switch to Events tab
2. Use arrow keys (↑/↓) to navigate events
3. Press Enter to select an event

**Expected Results**:
- ✅ Arrow keys still navigate between events
- ✅ Selected event is highlighted
- ✅ Enter key still selects events
- ✅ Keyboard navigation is not broken by new viewer features

**Pass/Fail**: ⬜

**Notes**: ________________________________

### Test 3.3: Tab Switching
**Expected**: Dashboard tab switching should still work normally

**Steps**:
1. Click between Events, Agents, Tools, Files tabs
2. Verify content switches correctly

**Expected Results**:
- ✅ All tabs are clickable and functional
- ✅ Tab content displays correctly
- ✅ New viewer features don't interfere with tab functionality
- ✅ File path viewer works from all tabs

**Pass/Fail**: ⬜

**Notes**: ________________________________

### Test 3.4: Modal Systems
**Expected**: Existing modal systems should work properly

**Steps**:
1. Open file viewer modal (from file path overlay or other means)
2. Open any other modals in the system
3. Test modal closing behavior

**Expected Results**:
- ✅ File viewer modal opens and displays correctly
- ✅ Other modals (if any) still function
- ✅ Modals close properly with close buttons or Escape key
- ✅ Modal overlays don't conflict with each other

**Pass/Fail**: ⬜

**Notes**: ________________________________

---

## Test Suite 4: Edge Cases

### Test 4.1: Empty Directory
**Expected**: File path viewer should handle empty directories gracefully

**Steps**:
1. Navigate to an empty directory (or create one)
2. Click file path bar to open overlay

**Expected Results**:
- ✅ Overlay opens without errors
- ✅ Shows "Empty directory" message or similar
- ✅ Parent directory link is still available (if not in root)
- ✅ Overlay closes properly

**Pass/Fail**: ⬜

**Notes**: ________________________________

### Test 4.2: Long File Paths
**Expected**: Very long file paths should be handled gracefully

**Steps**:
1. Navigate to a directory with very long path names
2. Open file path overlay
3. Check display and functionality

**Expected Results**:
- ✅ Long paths are truncated or wrapped appropriately
- ✅ Overlay doesn't extend beyond screen boundaries
- ✅ Text remains readable
- ✅ Functionality is not impaired

**Pass/Fail**: ⬜

**Notes**: ________________________________

### Test 4.3: Special Characters in Paths
**Expected**: Paths with special characters should work correctly

**Steps**:
1. Test with paths containing spaces, dashes, underscores, brackets, etc.
2. Open file path overlay and navigate

**Expected Results**:
- ✅ Special characters display correctly
- ✅ Files/directories with special characters are clickable
- ✅ Navigation works properly
- ✅ No encoding issues appear

**Pass/Fail**: ⬜

**Notes**: ________________________________

### Test 4.4: Large Diffs
**Expected**: Very large diff content should be handled properly

**Steps**:
1. Find an Edit event with a large diff (many lines changed)
2. Expand the diff viewer

**Expected Results**:
- ✅ Large diffs are scrollable within the diff container
- ✅ Performance remains acceptable
- ✅ Diff container respects max-height limits
- ✅ Scrollbars appear when needed

**Pass/Fail**: ⬜

**Notes**: ________________________________

### Test 4.5: Rapid Interactions
**Expected**: Rapid clicking/toggling should not cause issues

**Steps**:
1. Rapidly click the file path bar multiple times
2. Rapidly toggle multiple diff viewers
3. Test simultaneous interactions

**Expected Results**:
- ✅ System remains stable under rapid interactions
- ✅ No duplicate overlays or broken states occur
- ✅ Events are handled correctly
- ✅ UI remains responsive

**Pass/Fail**: ⬜

**Notes**: ________________________________

---

## Overall Assessment

### Requirements Summary

#### Requirement 1: VIEWER in blue file path bar
- **Status**: ⬜ MET / ⬜ NOT MET
- **Evidence**: 
  - Clickable path bar: ⬜ Pass ⬜ Fail
  - Overlay opens: ⬜ Pass ⬜ Fail  
  - Proper positioning: ⬜ Pass ⬜ Fail
  - Navigation works: ⬜ Pass ⬜ Fail
  - Close functionality: ⬜ Pass ⬜ Fail

#### Requirement 2: DIFF viewer attached to EDIT tool use
- **Status**: ⬜ MET / ⬜ NOT MET  
- **Evidence**:
  - Diff viewers present on Edit events: ⬜ Pass ⬜ Fail
  - Toggle functionality: ⬜ Pass ⬜ Fail
  - Correct diff content: ⬜ Pass ⬜ Fail
  - Isolation per edit: ⬜ Pass ⬜ Fail
  - Non-Edit events excluded: ⬜ Pass ⬜ Fail

### Overall Test Results
- **Total Tests**: 25
- **Passed**: ___
- **Failed**: ___
- **Success Rate**: ___%

### Critical Issues Found
1. ________________________________
2. ________________________________
3. ________________________________

### Recommendations
1. ________________________________
2. ________________________________
3. ________________________________

### Final QA Sign-off
- ⬜ **PASS** - Implementation meets requirements and quality standards
- ⬜ **CONDITIONAL PASS** - Minor issues that don't block deployment
- ⬜ **FAIL** - Significant issues that must be addressed

**Tester**: _________________ **Date**: _________________ **Signature**: _________________

---

## Appendix: Code Locations

### File Path Bar Viewer Implementation
- **JavaScript**: `/src/claude_mpm/dashboard/static/js/components/working-directory.js`
  - Lines 359-622: File path viewer overlay functionality
  - Lines 425-449: Click outside handler
  - Lines 456-555: Directory loading and display

- **CSS**: `/src/claude_mpm/dashboard/static/css/dashboard.css`  
  - Lines 214-333: Directory viewer overlay styles

### Edit Diff Viewer Implementation
- **JavaScript**: `/src/claude_mpm/dashboard/static/js/components/event-viewer.js`
  - Lines 768-910: Inline edit diff viewer creation
  - Lines 842-878: Diff HTML generation
  - Lines 885-899: Toggle functionality

- **CSS**: `/src/claude_mpm/dashboard/static/css/dashboard.css`
  - Lines 2602-2689: Inline edit diff viewer styles

### Integration Points
- **HTML**: `/src/claude_mpm/dashboard/index.html` - Main dashboard structure
- **Dashboard Coordinator**: `/src/claude_mpm/dashboard/static/js/dashboard.js` - Module coordination