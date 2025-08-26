# Hook Configuration Fix Summary

## Issues Fixed

### 1. **AttributeError in Hook Handler** ✅
**Problem**: `'ClaudeHookHandler' object has no attribute '_git_branch_cache'`
- The `event_handlers.py` module was accessing `_git_branch_cache` and `_git_branch_cache_time` attributes
- These attributes were never initialized in the `ClaudeHookHandler` class

**Solution**: Added initialization in `hook_handler.py`:
```python
# Initialize git branch cache (used by event_handlers)
self._git_branch_cache = {}
self._git_branch_cache_time = {}
```

### 2. **Settings File Configuration** ✅
**Problem**: Installer was using wrong settings file
- Hook installer was configured to use `settings.local.json`
- But Claude Code actually reads hooks from `settings.json` (as evidenced by working hooks)
- This created confusion about which file was the source of truth

**Solution**: Updated `installer.py` to use `settings.json`:
- Changed `self.settings_file = self.claude_dir / "settings.local.json"` 
- To `self.settings_file = self.claude_dir / "settings.json"`
- Updated all references and warning messages accordingly
- Removed duplicate hooks from `settings.local.json`

## Files Modified

1. `/Users/masa/Projects/claude-mpm/src/claude_mpm/hooks/claude_hooks/hook_handler.py`
   - Added `_git_branch_cache` and `_git_branch_cache_time` initialization

2. `/Users/masa/Projects/claude-mpm/src/claude_mpm/hooks/claude_hooks/installer.py`
   - Changed settings file from `settings.local.json` to `settings.json`
   - Updated warning messages and status reporting

3. `/Users/masa/.claude/settings.local.json`
   - Removed duplicate hooks configuration (kept in `settings.json` only)

## Verification

The hooks are now working correctly as shown in the logs:
- Events are being received and processed
- No more AttributeError
- Events are successfully emitted via HTTP POST and EventBus
- Dashboard should now receive hook events properly

## Current Status

✅ Hooks configured in correct file (`settings.json`)
✅ Handler processes events without errors
✅ Events flow properly to SocketIO/dashboard
✅ No duplicate configuration confusion