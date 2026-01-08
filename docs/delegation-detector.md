# Delegation Pattern Detector

## Overview

The delegation pattern detector identifies when the PM asks the user to do something manually instead of delegating to an agent. This helps enforce the delegation principle and surfaces opportunities for better task management.

## Problem

PM outputs like:
- "Make sure .env.local is in your .gitignore"
- "You'll need to run npm install"
- "Please run the tests manually"
- "Remember to update the README"

These violate the delegation principle - the PM should delegate these tasks to appropriate agents instead of asking the user to do them manually.

## Solution

The delegation detector scans PM responses for delegation anti-patterns and:
1. Identifies manual instructions
2. Extracts actionable tasks
3. Formats them as autotodos
4. Allows PM to see and delegate properly

## Usage

### Scan text for patterns

```bash
# Scan text directly
claude-mpm autotodos scan "Make sure .env.local is in .gitignore"

# Scan from file
claude-mpm autotodos scan -f response.txt

# Scan from stdin
echo "You'll need to run npm install" | claude-mpm autotodos scan

# Save detections to event log
claude-mpm autotodos scan "Remember to update the README" --save

# JSON output for programmatic use
claude-mpm autotodos scan "You should verify deployment" --format json
```

### View and manage delegation todos

```bash
# List all autotodos (includes delegation patterns)
claude-mpm autotodos list

# Clear delegation-specific todos
claude-mpm autotodos clear --event-type delegation

# Clear all autotodos (errors + delegation)
claude-mpm autotodos clear --event-type all
```

## Detected Patterns

The detector catches these common delegation anti-patterns:

| Pattern | Example | Suggested Todo |
|---------|---------|----------------|
| Make sure | "Make sure tests pass" | Verify: tests pass |
| You'll need to | "You'll need to run npm install" | Task: run npm install |
| Please run/execute | "Please run the tests" | Execute: the tests |
| Remember to | "Remember to update docs" | Task: update docs |
| Don't forget | "Don't forget to commit" | Task: commit |
| You should/can/could | "You should verify deployment" | Suggested: verify deployment |
| Be sure to | "Be sure to restart server" | Task: restart server |
| You may want to | "You may want to check logs" | Suggested: check logs |
| It's important to | "It's important to test" | Task: test |

## Architecture

### Components

1. **DelegationDetector** (`src/claude_mpm/services/delegation_detector.py`)
   - Pattern-based detection using regex
   - Extracts actionable tasks from PM output
   - Formats detections as autotodos

2. **Event Log Integration** (`src/claude_mpm/services/event_log.py`)
   - Stores detections as `autotodo.delegation` events
   - Persistent storage with pending/resolved status
   - Supports filtering and cleanup

3. **CLI Commands** (`src/claude_mpm/cli/commands/autotodos.py`)
   - `scan` - Detect delegation patterns
   - `list` - View all autotodos (errors + delegation)
   - `clear` - Clear by event type (error/delegation/all)

### Event Flow

```
PM Response
    ↓
Scan for patterns (manual or automatic)
    ↓
Detect delegation anti-patterns
    ↓
Save to event log (optional with --save)
    ↓
PM sees in autotodos list
    ↓
PM delegates to appropriate agent
    ↓
Mark as resolved when delegated
```

## Integration Points

### Future Enhancements

1. **Automatic Scanning** - Hook into PM response pipeline to auto-scan outputs
2. **PM Reminder System** - Surface delegation todos in PM context
3. **Analytics** - Track delegation patterns over time
4. **Custom Patterns** - Allow users to define project-specific patterns

### Hook Integration (Future)

Could be integrated into PostToolUse hook to automatically scan PM responses:

```python
# In PostToolUse hook
if tool_use["name"] == "respond_to_user":
    response_text = tool_use["content"]
    detector = get_delegation_detector()
    detections = detector.detect_user_delegation(response_text)

    if detections:
        event_log = get_event_log()
        for detection in detections:
            event_log.append_event(
                event_type="autotodo.delegation",
                payload=detection,
                status="pending"
            )
```

## Files Modified

- `src/claude_mpm/services/delegation_detector.py` - New detector service
- `src/claude_mpm/cli/commands/autotodos.py` - Added scan command, delegation event handling
- `src/claude_mpm/cli/parsers/base_parser.py` - Added scan subcommand and arguments
- `src/claude_mpm/cli/executor.py` - Added scan handler and delegation event type support
- `src/claude_mpm/services/event_log.py` - Existing event log (no changes needed)

## Testing

Run the test examples:

```bash
# Test basic detection
claude-mpm autotodos scan "Make sure .env.local is in .gitignore"

# Test save functionality
claude-mpm autotodos scan "You'll need to run npm install" --save

# Verify in list
claude-mpm autotodos list

# Test clear by type
claude-mpm autotodos clear --event-type delegation -y
```

## Design Decisions

### Why Pattern-Based Detection?

- Simple and extensible (add new patterns easily)
- No ML dependencies or complexity
- Clear and predictable behavior
- Easy to customize for project-specific needs

### Why Event-Driven Architecture?

- Decouple detection from consumption
- Persistent storage with status tracking
- Supports multiple consumers (CLI, dashboard, PM context)
- Consistent with existing autotodos design

### Why Optional Saving?

- Allows "dry run" mode for testing patterns
- User controls when to create autotodos
- Reduces noise from false positives
- Enables iterative pattern refinement

## LOC Delta

```
Added: 347 lines (delegation_detector.py + autotodos.py scan command)
Removed: 0 lines
Net Change: +347 lines
```

**Note**: This is a new feature adding functionality, not a refactoring task, so net positive LOC is expected.
