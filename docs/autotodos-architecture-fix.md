# AutoTodos Architecture Fix

**Date**: 2026-01-08
**Issue**: Delegation patterns were incorrectly treated as todos instead of PM violations

## Problem

The autotodos architecture had two event types backwards:

### OLD (INCORRECT) Model:
1. **Delegation anti-patterns** (PM says "make sure to...", "you'll need to run...")
   → Created `autotodo.delegation` events
   → Shown as todos in `autotodos list`
   → **WRONG**: These are PM mistakes, not actionable work items

2. **Script/coding errors** (hook fails with exit code 1, syntax errors)
   → Created `autotodo.error` events
   → Shown as todos in `autotodos list`
   → **CORRECT**: These are actionable items for delegation

### NEW (CORRECT) Model:
1. **Delegation anti-patterns** → `pm.violation` events
   - Type: PM behavior errors
   - Display: Shown via `autotodos violations` command
   - Purpose: Flag PM mistakes for immediate correction
   - Not actionable work items - these are errors in PM behavior

2. **Script/coding errors** → `autotodo.error` events
   - Type: Actionable work items
   - Display: Shown via `autotodos list` command
   - Purpose: Create todos for PM to delegate fixing

## Key Insight

**Delegation patterns = PM doing something wrong → needs correction (error)**
**Script failures = Something broke → needs fixing (todo)**

## Changes Made

### 1. Event Handler (`src/claude_mpm/hooks/claude_hooks/event_handlers.py`)
- Changed `_scan_for_delegation_patterns()` to create `pm.violation` events
- Updated docstring to clarify difference between violations and todos
- Changed event type from `autotodo.delegation` to `pm.violation`

### 2. CLI Commands (`src/claude_mpm/cli/commands/autotodos.py`)
- Updated `get_autotodos()` to ONLY return `autotodo.error` events
- Removed delegation event handling from todos list
- Added new `violations` command to show PM violations separately
- Updated `status` command to show both errors and violations
- Updated `clear` command to support `--event-type violation`
- Updated `scan` command to save as `pm.violation` instead of `autotodo.delegation`

### 3. Parser (`src/claude_mpm/cli/parsers/base_parser.py`)
- Added `"violations"` to autotodos command choices
- Changed event-type choices from `["error", "delegation", "all"]` to `["error", "violation", "all"]`

### 4. Executor (`src/claude_mpm/cli/executor.py`)
- Added `list_pm_violations` to imports
- Added `"violations"` handler mapping
- Added argument handling for violations command

### 5. Migration Script
- Created `/tmp/migrate_delegation_events.py` to convert existing events
- Migrated 9 `autotodo.delegation` events to `pm.violation` events
- Updated payload structure to match new violation format

## New Event Types

### `autotodo.error`
```json
{
  "event_type": "autotodo.error",
  "payload": {
    "error_type": "syntax_error",
    "hook_type": "PreToolUse",
    "details": "Unexpected token",
    "full_message": "SyntaxError: Unexpected token...",
    "suggested_fix": "Fix syntax error in...",
    "source": "hook_manager"
  },
  "status": "pending"
}
```

### `pm.violation`
```json
{
  "event_type": "pm.violation",
  "payload": {
    "violation_type": "delegation_anti_pattern",
    "pattern_type": "Task",
    "original_text": "You'll need to run npm install",
    "suggested_action": "Task: run npm install",
    "action": "run npm install",
    "source": "delegation_detector",
    "severity": "warning",
    "message": "PM asked user to do something manually: You'll need to run npm install..."
  },
  "status": "pending"
}
```

## Usage Examples

### Check Status
```bash
claude-mpm autotodos status
```
Shows:
- Pending Todos (script errors): 0
- Pending Violations (PM errors): 5

### View Script Errors (Todos)
```bash
claude-mpm autotodos list
```
Shows only `autotodo.error` events - actionable work items for delegation

### View PM Violations
```bash
claude-mpm autotodos violations
```
Shows only `pm.violation` events - PM behavior errors that need correction

### Scan for Violations
```bash
claude-mpm autotodos scan "Make sure to run the tests"
claude-mpm autotodos scan -f response.txt --save
```

### Clear Events
```bash
claude-mpm autotodos clear --event-type error      # Clear script errors
claude-mpm autotodos clear --event-type violation  # Clear PM violations
claude-mpm autotodos clear -y                      # Clear all
```

## Architecture Benefits

1. **Clear Separation**: Violations vs. todos are distinct concepts
2. **Correct Workflows**:
   - Violations → PM corrects behavior immediately
   - Errors → PM delegates fixing to agents
3. **Better UX**: Separate commands for different purposes
4. **Extensible**: Can add more violation types (security, best practices, etc.)

## Future Enhancements

1. Add real-time PM violation warnings during agent execution
2. Create violation severity levels (warning, error, critical)
3. Add PM behavior coaching tips based on violations
4. Integrate violations into PM evaluation/scoring system
5. Add more violation types beyond delegation anti-patterns

## Migration Path for Existing Systems

If you have existing `autotodo.delegation` events, run:

```bash
python /tmp/migrate_delegation_events.py
```

This script will:
1. Load existing event log
2. Convert `autotodo.delegation` → `pm.violation`
3. Update payload structure to match new format
4. Save migrated events

## Testing

Verified with:
- `autotodos status` - Shows correct separation
- `autotodos list` - Only shows script errors (empty)
- `autotodos violations` - Shows PM violations (5 detected)
- `autotodos clear --event-type violation -y` - Clears violations
- Final status confirms all events cleared

## Related Files

- `src/claude_mpm/hooks/claude_hooks/event_handlers.py`
- `src/claude_mpm/cli/commands/autotodos.py`
- `src/claude_mpm/cli/parsers/base_parser.py`
- `src/claude_mpm/cli/executor.py`
- `src/claude_mpm/core/hook_manager.py` (already correct)
- `src/claude_mpm/services/event_log.py` (no changes needed)

## Summary

The fix properly separates two distinct concepts:
- **PM Violations**: Behavioral errors where PM asks user to do things manually
- **Script Errors**: Technical failures that need delegation to agents

This aligns the system with the correct mental model and enables proper workflows for each type of issue.
