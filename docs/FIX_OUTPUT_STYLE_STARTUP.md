# Output Style Startup Fix

## Problem
The output style was not being set to "Claude MPM" on startup of the claude-mpm application. This occurred because the output style deployment was happening too late in the startup sequence - after Claude Code had already launched.

## Root Cause
The `OutputStyleManager` was only deploying the output style when framework instructions were loaded by the `FrameworkLoader`, which happens after the `ClaudeRunner` initialization completes. By this time, Claude Code may have already started with the default or previously selected output style.

## Solution
Moved the output style deployment to happen earlier in the startup sequence by:

1. **Added `_deploy_output_style()` method** to `ClaudeRunner` class in `src/claude_mpm/core/claude_runner.py`
   - Deploys the output style file to `~/.claude/output-styles/claude-mpm.md`
   - Updates `~/.claude/settings.json` to set `activeOutputStyle: "claude-mpm"`
   - Only runs for Claude Code >= 1.0.83 (which supports output styles)
   - Checks if already deployed to avoid duplication

2. **Called `_deploy_output_style()` in `ClaudeRunner.__init__()`**
   - Executes early in the initialization, before Claude Code launches
   - Ensures the output style is active from the start

## Implementation Details

### The `_deploy_output_style()` method:
- Creates an `OutputStyleManager` instance
- Checks Claude Code version (must be >= 1.0.83)
- Checks if output style is already deployed and active
- Reads existing `OUTPUT_STYLE.md` or extracts from framework instructions
- Deploys the output style using `OutputStyleManager.deploy_output_style()`
- Logs success/failure without interrupting startup

### Key Features:
- **Early deployment**: Happens during `ClaudeRunner` initialization
- **Idempotent**: Checks if already deployed to avoid duplication
- **Resilient**: Catches exceptions to prevent startup failures
- **Version-aware**: Only runs for supported Claude Code versions

## Testing
Created `scripts/test_output_style_startup.py` to verify:
1. Resets output style to "default"
2. Starts claude-mpm briefly
3. Verifies output style is set to "claude-mpm"
4. Confirms output style file exists

## Result
✅ The output style is now automatically set to "Claude MPM" on every startup of the claude-mpm application for Claude Code >= 1.0.83.

## Files Modified
- `src/claude_mpm/core/claude_runner.py` - Added early output style deployment
- `scripts/test_output_style_startup.py` - Created test script (new file)
- `docs/FIX_OUTPUT_STYLE_STARTUP.md` - This documentation (new file)