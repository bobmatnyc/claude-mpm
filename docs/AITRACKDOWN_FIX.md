# AI Trackdown v1.3.x Compatibility Fix for claude-mpm

## Issue Summary

The claude-mpm project has tickets in `tickets/` directory with subdirectories:
- `tickets/epics/` - 3 epic files
- `tickets/issues/` - 11 issue files  
- `tickets/tasks/` - 40 task files

However, ai-trackdown v1.3.0 is only scanning `tickets/tasks/` subdirectory, missing all epics and issues.

## Root Cause

1. **Directory Structure Mismatch**: ai-trackdown v1.3.x expects all ticket types to be in the configured tasks directory, not in subdirectories by type
2. **TaskManager Path Logic**: When it finds `tickets` as the tasks directory, it's only scanning the immediate files and the `tasks` subdirectory

## Solution

The project needs to flatten the ticket structure. Here are the options:

### Option 1: Flatten Directory Structure (RECOMMENDED)
Move all tickets to the root tickets directory:
```bash
# Move all ticket files to root tickets directory
mv tickets/epics/*.md tickets/
mv tickets/issues/*.md tickets/
mv tickets/tasks/*.md tickets/

# Remove empty subdirectories
rmdir tickets/epics tickets/issues tickets/tasks
```

### Option 2: Create a Custom Wrapper Script
Create a wrapper that handles the subdirectory structure:
```bash
#!/bin/bash
# ticket wrapper script that searches all subdirectories
case "$1" in
  issue)
    shift
    case "$1" in
      list)
        find tickets -name "ISS-*.md" -type f | while read f; do
          # Parse and display issue info
        done
        ;;
    esac
    ;;
esac
```

### Option 3: Patch ai-trackdown Locally
Modify the TaskManager to recursively scan all subdirectories.

## Verification

After applying the fix, these commands should work:
```bash
aitrackdown issue list         # Should show 11 issues
aitrackdown task list --epic EP-0003  # Should show linked tasks
aitrackdown task show EP-0003  # Should show epic details with subtasks
```

## Current Workaround

Until the structure is fixed, you can directly access ticket files:
```bash
# View an issue
cat tickets/issues/ISS-0001.md

# List all issues
ls tickets/issues/ISS-*.md

# Search for issues linked to an epic
grep -l "epic: EP-0003" tickets/issues/*.md
```