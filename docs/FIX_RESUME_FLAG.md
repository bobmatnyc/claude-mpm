# Fix: --resume Flag Implementation

## Issue
The `--resume` flag was not working properly in claude-mpm. When users tried to use `claude-mpm --resume` to resume their last Claude Code conversation, the flag was not being passed through to Claude.

## Root Cause
The issue had multiple layers:
1. The bash wrapper script didn't recognize `--resume` as an MPM-handled flag
2. The argument parser didn't have `--resume` defined in the top-level or run subparser
3. The flag wasn't being added to `claude_args` for passing to Claude Code

## Solution
The fix involved changes to multiple files:

### 1. Bash Wrapper Recognition
**File**: `scripts/claude-mpm`
- Added `"--resume"` to the `MPM_FLAGS` array
- This ensures the bash script recognizes `--resume` as a flag that should trigger MPM mode

### 2. Argument Parser Support
**File**: `src/claude_mpm/cli/parsers/base_parser.py`
- Added `--resume` argument to top-level run arguments
- This handles `claude-mpm --resume` (without explicit "run" command)

**File**: `src/claude_mpm/cli/parsers/run_parser.py`
- Added `--resume` argument to run subparser
- This handles `claude-mpm run --resume`

### 3. Command Construction
**File**: `src/claude_mpm/cli/__init__.py`
- Modified `_ensure_run_attributes()` to check for `--resume` flag
- When set, adds `--resume` to `claude_args` list

**File**: `src/claude_mpm/cli/commands/run.py`
- Added logic to include `--resume` in `claude_args` before filtering
- Ensures the flag is passed through to Claude Code

## Implementation Details

### Bash Script Change
```bash
MPM_FLAGS=("--resume" "--mpm-resume" "--logging" ...)
```

### Parser Changes
```python
run_group.add_argument(
    "--resume",
    action="store_true",
    help="Pass --resume flag to Claude Code to resume the last conversation",
)
```

### Command Construction Logic
```python
# In _ensure_run_attributes()
claude_args = getattr(args, "claude_args", [])
if getattr(args, "resume", False):
    if "--resume" not in claude_args:
        claude_args = ["--resume"] + claude_args
args.claude_args = claude_args
```

## Testing
Created comprehensive test scripts to verify the fix:
- `scripts/test_resume_flag_fix.py` - Unit tests for individual components
- `scripts/test_resume_command_build.py` - Integration tests for command building
- `scripts/verify_resume_fix.py` - Simple verification script

All tests confirm that:
1. The bash wrapper recognizes `--resume` as an MPM flag
2. The argument parser correctly parses the flag
3. The flag is properly added to `claude_args`
4. The flag passes through to the final Claude command

## Usage
The following commands now work correctly:
```bash
# Resume last conversation with default MPM setup
claude-mpm --resume

# Explicit run command with resume
claude-mpm run --resume

# Combine with other Claude arguments
claude-mpm --resume -- --model opus

# Combine with MPM session resume
claude-mpm --resume --mpm-resume last
```

## Important Notes
- The `--resume` flag is for Claude Code's native resume functionality
- The `--mpm-resume` flag is for MPM's session management (different feature)
- Both flags can be used together if needed
- The fix maintains backward compatibility with all existing functionality

## Verification
Run the verification script to confirm the fix is working:
```bash
python scripts/verify_resume_fix.py
```

Expected output:
```
✅ Bash wrapper includes --resume in MPM_FLAGS
✅ Parser includes --resume flag
✅ Run subparser includes --resume flag
✅ Filter function correctly handles --resume
✅ _ensure_run_attributes adds --resume to claude_args
```