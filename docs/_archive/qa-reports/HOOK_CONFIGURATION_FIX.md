# Hook Configuration Fix - Complete

## Problem Resolved
The Claude Code UI was showing "No matchers configured yet" because hooks were configured in the wrong file:
- ❌ **Wrong**: `~/.claude/settings.json` 
- ✅ **Correct**: `~/.claude/settings.local.json`

Claude Code reads hook configuration from `settings.local.json`, not `settings.json`.

## Changes Made

### 1. Updated HookInstaller Class
**File**: `src/claude_mpm/hooks/claude_hooks/installer.py`

- Changed `self.settings_file` from `settings.json` to `settings.local.json`
- Added `self.old_settings_file` reference for migration
- Updated `_update_claude_settings()` to:
  - Use `settings.local.json` as primary config file
  - Preserve existing permissions and mcpServers
  - Add proper matcher configuration for tool events
  - Clean up old hooks from `settings.json`
- Added `_cleanup_old_settings()` method to remove hooks from old file
- Updated `uninstall_hooks()` to handle both file locations
- Enhanced `get_status()` to check both files and warn about misconfigurations

### 2. Hook Configuration Structure
The correct structure in `settings.local.json`:

```json
{
  "permissions": { ... },
  "enableAllProjectMcpServers": false,
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "*",  // Required for tool events
        "hooks": [
          {
            "type": "command",
            "command": "/path/to/claude-hook-handler.sh"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "*",  // Required for tool events
        "hooks": [ ... ]
      }
    ],
    // Non-tool events don't need matchers
    "Stop": [
      {
        "hooks": [ ... ]
      }
    ],
    "SubagentStop": [ ... ],
    "SubagentStart": [ ... ],
    "UserPromptSubmit": [ ... ]
  },
  "mcpServers": { ... }
}
```

### 3. Key Differences
- **Tool events** (PreToolUse, PostToolUse): Require `"matcher": "*"` field
- **Non-tool events** (Stop, SubagentStop, etc.): Don't need matcher field
- **Matcher value**: Use `"*"` to match all tools (shows in Claude Code UI)

## Installation Commands

### Install/Reinstall Hooks
```bash
# Install hooks (moves configuration to correct file)
python -m claude_mpm configure --install-hooks

# Force reinstall if already installed
python -m claude_mpm configure --install-hooks --force
```

### Verify Installation
```bash
# Check hook installation status
python -m claude_mpm configure --verify-hooks

# Run comprehensive verification
python test_hook_verification.py
```

### Start Monitoring
```bash
# Start the SocketIO server for event monitoring
python -m claude_mpm monitor

# Open dashboard in browser
open http://localhost:8765
```

## Verification Results

✅ **All checks passed:**
- Hooks configured in `settings.local.json`
- Matchers properly set for tool events
- Hook handler script exists and is executable
- SocketIO server running on port 8765
- Events will be captured and displayed in dashboard

## What This Fixes

1. **Claude Code UI**: Now shows configured matchers instead of "No matchers configured yet"
2. **Hook Events**: Properly trigger for all tool usage (PreToolUse/PostToolUse)
3. **Dashboard Monitoring**: Events are sent to SocketIO server and displayed in real-time
4. **Configuration Location**: Hooks in correct file that Claude Code actually reads

## Testing

When you use any tool in Claude Code:
1. PreToolUse event fires with the tool details
2. Tool executes
3. PostToolUse event fires with results
4. Events appear in dashboard at http://localhost:8765

The `"*"` matcher ensures all tools trigger these hooks.

## Files Created/Modified

- **Modified**: `src/claude_mpm/hooks/claude_hooks/installer.py`
- **Modified**: `~/.claude/settings.local.json` (hooks added)
- **Modified**: `~/.claude/settings.json` (hooks removed)
- **Created**: `test_hook_verification.py` (verification script)
- **Created**: `HOOK_CONFIGURATION_FIX.md` (this document)

## Future Notes

- Always configure hooks in `settings.local.json`, not `settings.json`
- Tool events require matcher field, non-tool events don't
- Use `"*"` as matcher to capture all tools
- The installer now automatically handles migration from old to new location