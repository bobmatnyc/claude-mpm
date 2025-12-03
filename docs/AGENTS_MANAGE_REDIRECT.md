# Agent Management Redirect Implementation

## Overview

The `claude-mpm agents manage` command now redirects to the unified `claude-mpm config` interface. This provides users with a better experience by consolidating all configuration options in one place.

**Note**: This is a **redirect**, not a deprecation. The command still works and provides helpful guidance to users, making the transition to the new unified interface smooth and user-friendly.

## Changes Made

### 1. Modified `src/claude_mpm/cli/commands/agents.py`

**Method**: `_manage_local_agents()`

**Before**: Launched the AgentWizard interactive menu directly.

**After**: Shows a friendly redirect message and offers to launch `claude-mpm config` instead.

```python
def _manage_local_agents(self, args) -> CommandResult:
    """Redirect to main configuration interface (DEPRECATED)."""
    # Shows friendly message with benefits of config interface
    # Prompts user to launch config
    # If yes: launches ConfigureCommand
    # If no: shows hint to run config later
```

**Features**:
- ✅ Friendly redirect message in a styled box
- ✅ Lists benefits of unified config interface
- ✅ Interactive prompt to launch config immediately
- ✅ Graceful fallback if user declines

### 2. Updated `src/claude_mpm/cli/parsers/agents_parser.py`

**Changes**:
1. Added deprecation notice to main `agents` parser description
2. Updated `manage` subcommand help text to show "(Deprecated)"
3. Added detailed deprecation description and epilog to `manage` parser

**Help Text Updates**:
```
Available commands:
  discover    Discover available agents from configured sources
  deploy      Deploy agents to your project
  list        List available agents
  manage      (Deprecated) Use 'claude-mpm config' instead
```

**Manage Command Help**:
```
usage: claude-mpm agents manage [-h]

Manage locally deployed agents. Note: This command has been deprecated.
Please use 'claude-mpm config' for the enhanced configuration interface.

options:
  -h, --help  show this help message and exit

DEPRECATION NOTICE:
This command has been deprecated in favor of 'claude-mpm config' which provides
a unified interface for managing agents, skills, templates, and behavior settings.
```

### 3. Updated `src/claude_mpm/cli/interactive/agent_wizard.py`

**Change**: Added deprecation notice to `AgentWizard` class docstring.

```python
class AgentWizard:
    """
    Interactive wizard for agent creation and management.

    DEPRECATED: This interface has been superseded by the unified
    configuration interface. Please use 'claude-mpm config' instead.

    This class is retained for backward compatibility but will be
    removed in a future version.
    """
```

### 4. Created Tests `tests/test_agents_manage_redirect.py`

**Test Coverage**:
1. ✅ Test that declining the prompt returns success
2. ✅ Test that confirming the prompt launches config command
3. ✅ Test that help text shows deprecation notice

All tests pass successfully.

## User Experience

### Running `claude-mpm agents manage`

**Output**:
```
╭─────────────────────────────────────────╮
│  Agent Management Has Moved!            │
╰─────────────────────────────────────────╯

For a better experience with integrated configuration:
  • Agent management
  • Skills management
  • Template editing
  • Behavior configuration
  • Startup settings

Please use: claude-mpm config

Launch configuration interface now? [Y/n]:
```

**If User Confirms (Y)**:
- Automatically launches `claude-mpm config`
- Shows the unified configuration menu with Agent Management option

**If User Declines (n)**:
- Shows hint: "Run 'claude-mpm config' anytime to access agent management"
- Returns success (non-breaking)

### Help Text

**`claude-mpm agents --help`**:
Shows deprecation notice in description and command list.

**`claude-mpm agents manage --help`**:
Shows full deprecation notice with detailed explanation.

## Backward Compatibility

✅ **No Breaking Changes**:
- Command still works (doesn't error)
- Redirects gracefully to new interface
- User can decline and no harm done
- All other `agents` commands work normally

✅ **Preserved Commands**:
- `claude-mpm agents discover` - ✅ Working
- `claude-mpm agents deploy` - ✅ Working
- `claude-mpm agents list` - ✅ Working
- All other subcommands - ✅ Working

## Migration Path

**Recommended Workflow**:
1. User runs `claude-mpm agents manage` (old habit)
2. Sees friendly message explaining change
3. Confirms to launch config interface
4. Sees all available options in unified menu
5. Learns new command: `claude-mpm config`
6. Next time uses `claude-mpm config` directly

## Benefits

1. **Unified Interface**: All configuration in one place
2. **Better Discovery**: Users find skills, templates, and behavior settings
3. **Consistent UX**: Same menu style across all config options
4. **Forward-Compatible**: Easy to add new config options to single interface
5. **Clear Deprecation Path**: Users guided to new command, not blocked

## Code Quality

✅ All linting checks pass
✅ All formatting checks pass
✅ All tests pass (3/3)
✅ No breaking changes to existing commands
✅ Clean error handling
✅ Rich console formatting

## Future Cleanup

In a future major version (e.g., v5.0.0), the `agents manage` command can be completely removed:
- Remove `_manage_local_agents()` method
- Remove `manage` subparser
- Remove AgentWizard class (if no other dependencies)

This provides users time to transition to the new `claude-mpm config` command.

## Success Criteria

All criteria met:

- ✅ `claude-mpm agents manage` shows friendly redirect message
- ✅ User can choose to launch config or cancel
- ✅ If confirmed, config interface launches automatically
- ✅ Help text shows deprecation notices
- ✅ CLI commands (discover, deploy, list) still work
- ✅ No breaking changes to existing workflows
- ✅ Tests verify all functionality
- ✅ Code quality checks pass
