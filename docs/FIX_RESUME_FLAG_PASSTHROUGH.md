# Fix: --resume Flag Not Being Passed to Claude Code

## Issue
The `--resume` flag (Claude's native session resumption flag) was not being properly passed through to Claude Code when users ran commands like:
```bash
claude-mpm run -- --resume session123
```

## Root Cause
The `filter_claude_mpm_args` function in `src/claude_mpm/cli/commands/run.py` was not removing the `--` separator that argparse uses to distinguish between MPM arguments and Claude arguments. This separator was being passed to Claude Code, which doesn't expect it.

## Solution
Modified the `filter_claude_mpm_args` function to:
1. Remove the `--` separator from the argument list before passing to Claude
2. Ensure Claude's native `--resume` and `-r` flags are properly passed through
3. Continue filtering out MPM-specific flags like `--mpm-resume`

## Code Changes
In `src/claude_mpm/cli/commands/run.py`:
- Added logic to skip the `--` separator when filtering arguments
- Updated docstring to explain this behavior

## Testing
Added comprehensive tests in `tests/test_resume_flag_passthrough.py` to verify:
- `--resume` with session ID is passed through
- `--resume` without session ID is passed through  
- `-r` (short form) is passed through
- `--` separator is removed
- MPM-specific flags are still filtered correctly

## Usage Examples

### Claude's Native Resume Flag (now works correctly)
```bash
# Resume with specific session ID
claude-mpm run -- --resume session123

# Resume interactively (Claude will prompt for session)
claude-mpm run -- --resume

# Short form
claude-mpm run -- -r session456
```

### MPM's Session Management (unchanged)
```bash
# Resume last MPM session
claude-mpm run --mpm-resume

# Resume specific MPM session
claude-mpm run --mpm-resume session789
```

## Backward Compatibility
This fix maintains full backward compatibility:
- MPM's `--mpm-resume` flag continues to work for MPM session management
- All other Claude CLI flags continue to be passed through correctly
- MPM-specific flags continue to be filtered out as before