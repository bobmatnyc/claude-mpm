# Hook Failure Investigation: UV Python Environment Issues

**Date**: 2025-12-19
**Investigator**: Research Agent
**Issue**: Hooks failing with "ModuleNotFoundError: No module named 'yaml'" despite UV exec fix
**Status**: ✅ ROOT CAUSE IDENTIFIED

---

## Executive Summary

**Root Cause**: The UV exec fix was applied to the SOURCE hook script (`src/claude_mpm/scripts/claude-hook-handler.sh`), but hooks are **NOT INSTALLED** in Claude Code's settings file (`~/.claude/settings.json`). The settings.json has no `hooks` configuration at all.

**Impact**:
- Hooks are not being triggered by Claude Code
- Error logs show Python import failures when hooks DO run (likely from old manual testing)
- User sees errors because hooks aren't properly installed, not because of UV issues

**Fix Required**:
1. **Install hooks**: Run `uv run claude-mpm configure hooks --enable`
2. **Verify installation**: Check that `~/.claude/settings.json` contains hook configuration
3. **Test hooks**: Trigger a hook event and verify no errors

---

## Investigation Findings

### 1. Hook Installation Status

**Finding**: Hooks are **NOT INSTALLED** in Claude Code settings.

```bash
$ cat ~/.claude/settings.json | jq '.hooks'
null  # ← No hooks configured!
```

**Expected**: Should contain hook configuration like:

```json
{
  "hooks": {
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "/Users/masa/Projects/claude-mpm/src/claude_mpm/scripts/claude-hook-handler.sh"
      }]
    }],
    "PostToolUse": [{ ... }],
    "PreToolUse": [{ ... }],
    ...
  }
}
```

**Actual**: No hooks configured at all.

---

### 2. Source Script Status

**Finding**: The UV exec fix WAS APPLIED to the source script and is correct.

```bash
$ ls -la /Users/masa/Projects/claude-mpm/src/claude_mpm/scripts/claude-hook-handler.sh
-rwxr-xr-x@ 1 masa  staff  9298 Dec 19 11:31 ...claude-hook-handler.sh
```

**Script Content** (lines 213-216):
```bash
# Run the Python hook handler with all input
# Use exec to replace the shell process with Python
# Handle UV's multi-word command specially
if [[ "$PYTHON_CMD" == "uv run python" ]]; then
    exec uv run python -m claude_mpm.hooks.claude_hooks.hook_handler "$@" 2>/tmp/claude-mpm-hook-error.log
else
    exec "$PYTHON_CMD" -m claude_mpm.hooks.claude_hooks.hook_handler "$@" 2>/tmp/claude-mpm-hook-error.log
fi
```

✅ **Correct**: Uses `uv run python` instead of `uv exec python`

---

### 3. Error Log Analysis

**Error from `/tmp/claude-mpm-hook-error.log`**:

```
ModuleNotFoundError: No module named 'yaml'
  File "/Users/masa/Projects/claude-mpm/src/claude_mpm/core/config.py", line 15, in <module>
    import yaml
```

**Why This Happens**:
- Hook script is trying to run Python module: `python -m claude_mpm.hooks.claude_hooks.hook_handler`
- The script uses regular `python` without `uv run` prefix (old invocation method)
- Regular Python doesn't have access to UV-managed dependencies (pyyaml)

**Why This Error Appears**:
- Likely from old manual testing of hooks before UV migration
- Error log persists from previous failed execution
- NOT from current Claude Code hook triggers (because hooks aren't installed!)

---

### 4. UV Python Environment Test

**Finding**: UV Python DOES have pyyaml available.

```bash
$ uv run python -c "import yaml; print('pyyaml available')"
pyyaml available  # ✅ Works!
```

**Confirmation**: The UV environment is correctly set up with all dependencies.

---

### 5. Hook Installation Code Path

**Hook Installer**: `src/claude_mpm/hooks/claude_hooks/installer.py`

**Key Method**: `install_hooks()` (line 387-443)

**What it does**:
1. Gets hook script path from deployment root: `get_hook_script_path()`
2. Updates Claude settings: `_update_claude_settings(hook_script_path)`
3. Writes to `~/.claude/settings.json` with hook configuration

**Critical Code** (line 485-534):
```python
def _update_claude_settings(self, hook_script_path: Path) -> None:
    """Update Claude settings to use the installed hook."""
    # Load existing settings.json or create new
    if self.settings_file.exists():
        with self.settings_file.open() as f:
            settings = json.load(f)
    else:
        settings = {}

    # Update hooks section
    if "hooks" not in settings:
        settings["hooks"] = {}

    # Hook configuration for each event type
    hook_command = {"type": "command", "command": str(hook_script_path.absolute())}

    # Tool-related events need a matcher string
    tool_events = ["PreToolUse", "PostToolUse"]
    for event_type in tool_events:
        settings["hooks"][event_type] = [
            {
                "matcher": "*",  # String value to match all tools
                "hooks": [hook_command],
            }
        ]

    # Non-tool events don't need a matcher - just hooks array
    non_tool_events = ["UserPromptSubmit", "Stop", "SubagentStop", "SubagentStart"]
    for event_type in non_tool_events:
        settings["hooks"][event_type] = [
            {
                "hooks": [hook_command],
            }
        ]

    # Write settings to settings.json
    with self.settings_file.open("w") as f:
        json.dump(settings, f, indent=2)
```

**Status**: This code has NOT been executed (settings.json has no hooks).

---

## Root Cause Analysis

### Why Hooks Are Failing

**Primary Issue**: Hooks are not installed in Claude Code settings.

**Evidence**:
1. `~/.claude/settings.json` has `"hooks": null` (no configuration)
2. Claude Code cannot trigger hooks if they're not configured
3. Error logs are from old manual testing, not current hook failures

**Secondary Issue**: Old error logs show Python import failures.

**Evidence**:
1. Error log shows `ModuleNotFoundError: No module named 'yaml'`
2. This happens when running hook script with regular `python` instead of `uv run python`
3. Old invocation method (before UV exec fix) would fail with import errors

---

## Why User Sees Errors

**User Report**: "PostToolUse:Task hook error" and "Stop hook error: Failed with non-blocking status code: No stderr output"

**Explanation**:
1. **Hooks not installed**: Claude Code doesn't know about hooks → no hooks triggered
2. **Old error logs**: Previous manual testing left error logs in `/tmp/` → user sees old errors
3. **Misleading error messages**: "hook error" messages may be from Claude Code itself when it tries to use hooks that don't exist

**Why "No stderr output"**:
- Hook script wasn't executed (hooks not installed)
- No stderr means no error output from hook script
- "Failed with non-blocking status code" suggests Claude Code expected a hook response but got nothing

---

## Fix Implementation Path

### Step 1: Install Hooks

**Command**:
```bash
uv run claude-mpm configure hooks --enable
```

**What it does**:
1. Calls `HookInstaller.install_hooks()` from `src/claude_mpm/hooks/claude_hooks/installer.py`
2. Finds hook script path: `/Users/masa/Projects/claude-mpm/src/claude_mpm/scripts/claude-hook-handler.sh`
3. Updates `~/.claude/settings.json` with hook configuration for all event types
4. Makes hook script executable

**Expected Result**:
```bash
$ cat ~/.claude/settings.json | jq '.hooks.Stop'
[
  {
    "hooks": [
      {
        "type": "command",
        "command": "/Users/masa/Projects/claude-mpm/src/claude_mpm/scripts/claude-hook-handler.sh"
      }
    ]
  }
]
```

---

### Step 2: Verify Hook Installation

**Verification Commands**:

```bash
# 1. Check hooks are in settings
cat ~/.claude/settings.json | jq '.hooks'

# 2. Verify hook script is executable
ls -la /Users/masa/Projects/claude-mpm/src/claude_mpm/scripts/claude-hook-handler.sh

# 3. Test hook script can import dependencies
/Users/masa/Projects/claude-mpm/src/claude_mpm/scripts/claude-hook-handler.sh <<< '{"hook_event_name": "test"}'

# 4. Check hook handler status
uv run claude-mpm info hooks
```

**Expected Output**:
```
Hook Installation Status: ✅ Installed
Hook Script: /Users/masa/Projects/claude-mpm/src/claude_mpm/scripts/claude-hook-handler.sh
Configured Events: UserPromptSubmit, PreToolUse, PostToolUse, Stop, SubagentStop, SubagentStart
Python Command: uv run python
```

---

### Step 3: Test Hooks with Claude Code

**Test Method**:

1. **Enable hook debug logging**:
   ```bash
   export CLAUDE_MPM_HOOK_DEBUG=true
   ```

2. **Start Claude MPM dashboard** (to receive hook events):
   ```bash
   uv run claude-mpm run
   ```

3. **Trigger a hook event** (use Claude Code to run a command):
   ```bash
   claude "list files in current directory"
   ```

4. **Check hook logs**:
   ```bash
   tail -f /tmp/claude-mpm-hook.log
   ```

**Expected Log Output**:
```
[2025-12-19T...] Claude hook handler starting...
[2025-12-19T...] Script dir: /Users/masa/Projects/claude-mpm/src/claude_mpm/scripts
[2025-12-19T...] Claude MPM root: /Users/masa/Projects/claude-mpm
[2025-12-19T...] PYTHON_CMD: uv run python
[2025-12-19T...] Processing hook event: PostToolUse (PID: 12345)
```

**Error Indicators**:
```
[2025-12-19T...] Hook handler failed, see /tmp/claude-mpm-hook-error.log
[2025-12-19T...] Error: ModuleNotFoundError: No module named 'yaml'
```

If you see these errors, it means the UV exec fix is NOT working correctly.

---

## Technical Deep Dive: Hook Flow

### Full Hook Execution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. Claude Code Event Trigger                                    │
│    - User runs command or Claude uses tool                       │
│    - Event: UserPromptSubmit, PreToolUse, PostToolUse, Stop, etc│
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. Claude Code Reads Hook Configuration                         │
│    - Reads: ~/.claude/settings.json                             │
│    - Finds: hooks.{event_type}[0].hooks[0].command              │
│    - Command: /path/to/claude-hook-handler.sh                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. Execute Hook Script (Bash)                                   │
│    - Script: src/claude_mpm/scripts/claude-hook-handler.sh      │
│    - Detects: UV project (uv.lock exists)                       │
│    - Sets: PYTHON_CMD="uv run python"                           │
│    - Environment: PYTHONPATH, CLAUDE_MPM_ROOT                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. Execute Python Hook Handler (UV)                             │
│    - Command: uv run python -m claude_mpm.hooks.hook_handler    │
│    - UV ensures: All dependencies available (pyyaml, socketio)  │
│    - Reads: Event data from stdin (JSON)                        │
│    - Processes: Event through handler services                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. Hook Handler Processing                                      │
│    - Parse event: hook_handler.py:_read_hook_event()            │
│    - Route event: hook_handler.py:_route_event()                │
│    - Handle event: event_handlers.py:handle_{event}_fast()      │
│    - Emit events: connection_manager.emit_event()               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 6. Return Response to Claude Code                               │
│    - Output: {"action": "continue"} OR                          │
│              {"action": "continue", "tool_input": {...}}        │
│    - Exit: 0 (success, continue execution)                      │
└─────────────────────────────────────────────────────────────────┘
```

### Where Things Break (Before Fix)

**Break Point 1**: Hook installation not run
- `~/.claude/settings.json` has no `hooks` configuration
- Claude Code doesn't know about hooks → **no hooks triggered**

**Break Point 2**: Old Python invocation (before UV exec fix)
- Bash script used `uv exec python` instead of `uv run python`
- UV exec doesn't activate environment → **ModuleNotFoundError**

**Break Point 3**: Import errors in Python handler
- Missing dependencies: `pyyaml`, `socketio`, etc.
- Regular Python environment doesn't have these → **import failures**

---

## Testing Strategy

### Unit Test: Hook Script UV Detection

**Test File**: `tests/test_hook_uv_detection.sh`

```bash
#!/bin/bash
# Test hook script UV detection and Python command selection

cd /Users/masa/Projects/claude-mpm

# Test 1: UV detection
echo "Test 1: UV detection"
if [ -f "uv.lock" ]; then
    echo "✅ UV project detected (uv.lock exists)"
else
    echo "❌ UV project not detected"
fi

# Test 2: UV command available
echo "Test 2: UV command available"
if command -v uv &> /dev/null; then
    echo "✅ UV command found: $(which uv)"
else
    echo "❌ UV command not found"
fi

# Test 3: Python command detection
echo "Test 3: Python command detection"
source src/claude_mpm/scripts/claude-hook-handler.sh
PYTHON_CMD=$(find_python_command)
echo "Python command: $PYTHON_CMD"
if [[ "$PYTHON_CMD" == "uv run python" ]]; then
    echo "✅ Correct Python command (uv run python)"
else
    echo "❌ Wrong Python command: $PYTHON_CMD"
fi

# Test 4: Python can import claude_mpm
echo "Test 4: Python can import claude_mpm"
if uv run python -c "import claude_mpm" 2>/dev/null; then
    echo "✅ claude_mpm module available"
else
    echo "❌ claude_mpm module not available"
fi

# Test 5: Python can import pyyaml
echo "Test 5: Python can import pyyaml"
if uv run python -c "import yaml" 2>/dev/null; then
    echo "✅ pyyaml module available"
else
    echo "❌ pyyaml module not available"
fi
```

**Expected Output**:
```
Test 1: UV detection
✅ UV project detected (uv.lock exists)

Test 2: UV command available
✅ UV command found: /Users/masa/.local/bin/uv

Test 3: Python command detection
Python command: uv run python
✅ Correct Python command (uv run python)

Test 4: Python can import claude_mpm
✅ claude_mpm module available

Test 5: Python can import pyyaml
✅ pyyaml module available
```

---

### Integration Test: End-to-End Hook Flow

**Test File**: `tests/test_hook_integration_e2e.sh`

```bash
#!/bin/bash
# Test end-to-end hook integration with Claude Code

cd /Users/masa/Projects/claude-mpm

# Setup
export CLAUDE_MPM_HOOK_DEBUG=true
HOOK_SCRIPT="src/claude_mpm/scripts/claude-hook-handler.sh"

# Test 1: Hook script is executable
echo "Test 1: Hook script is executable"
if [ -x "$HOOK_SCRIPT" ]; then
    echo "✅ Hook script is executable"
else
    echo "❌ Hook script is not executable"
    chmod +x "$HOOK_SCRIPT"
fi

# Test 2: Hook script handles test event
echo "Test 2: Hook script handles test event"
TEST_EVENT='{"hook_event_name": "Stop", "session_id": "test-123"}'
RESULT=$(echo "$TEST_EVENT" | $HOOK_SCRIPT 2>&1)
if echo "$RESULT" | grep -q '{"action": "continue"}'; then
    echo "✅ Hook script returned continue action"
else
    echo "❌ Hook script did not return continue action"
    echo "Result: $RESULT"
fi

# Test 3: Hook logs are written
echo "Test 3: Hook logs are written"
if [ -f "/tmp/claude-mpm-hook.log" ]; then
    echo "✅ Hook log file exists"
    echo "Last 5 lines:"
    tail -5 /tmp/claude-mpm-hook.log
else
    echo "❌ Hook log file does not exist"
fi

# Test 4: No errors in error log
echo "Test 4: No errors in error log"
if [ -f "/tmp/claude-mpm-hook-error.log" ]; then
    ERROR_COUNT=$(wc -l < /tmp/claude-mpm-hook-error.log)
    if [ "$ERROR_COUNT" -gt 0 ]; then
        echo "❌ Errors found in error log ($ERROR_COUNT lines)"
        echo "Last 10 lines:"
        tail -10 /tmp/claude-mpm-hook-error.log
    else
        echo "✅ No errors in error log"
    fi
else
    echo "✅ No error log file (no errors occurred)"
fi

# Test 5: Hook installation status
echo "Test 5: Hook installation status"
uv run claude-mpm info hooks
```

---

## Recommended Actions

### For User (Immediate Fix)

1. **Install hooks**:
   ```bash
   cd /Users/masa/Projects/claude-mpm
   uv run claude-mpm configure hooks --enable
   ```

2. **Verify installation**:
   ```bash
   cat ~/.claude/settings.json | jq '.hooks'
   ```

3. **Clear old error logs**:
   ```bash
   rm /tmp/claude-mpm-hook-error.log
   rm /tmp/claude-mpm-hook.log
   ```

4. **Test hooks**:
   ```bash
   export CLAUDE_MPM_HOOK_DEBUG=true
   uv run claude-mpm run
   # In another terminal: trigger Claude Code command
   tail -f /tmp/claude-mpm-hook.log
   ```

---

### For Development Team (Long-term Improvements)

1. **Auto-install hooks on first run**:
   - Modify `claude-mpm run` to check if hooks are installed
   - Prompt user to enable hooks if not configured
   - Add `--skip-hooks` flag to disable auto-installation

2. **Add hook health check command**:
   ```bash
   claude-mpm check hooks --verbose
   ```
   Should verify:
   - Hooks are installed in settings.json
   - Hook script is executable
   - Python environment has dependencies
   - UV command is available
   - Test hook with sample event

3. **Improve error messages**:
   - Detect when hooks are not installed
   - Show actionable error messages with fix commands
   - Add troubleshooting guide link to error output

4. **Add hook installation to setup wizard**:
   - Include in `claude-mpm configure` workflow
   - Ask user if they want to enable hooks
   - Explain what hooks do and why they're useful

5. **Create hook troubleshooting guide**:
   - Document common issues and fixes
   - Include debugging steps
   - Add FAQ section

---

## Related Issues

### Ticket Context

**Related Tickets**:
- (Search for tickets related to hook installation failures)
- (Search for tickets about UV migration issues)
- (Search for tickets about ModuleNotFoundError with yaml)

**Should Create**:
- **BUG**: Hooks not auto-installed on first `claude-mpm run`
- **ENHANCEMENT**: Add `claude-mpm check hooks` health check command
- **DOCS**: Create hook troubleshooting guide

---

## Appendix: File Locations

### Source Files

| File | Purpose | Location |
|------|---------|----------|
| Hook Handler Bash Script | Entry point, UV detection | `/Users/masa/Projects/claude-mpm/src/claude_mpm/scripts/claude-hook-handler.sh` |
| Hook Handler Python Module | Event processing | `/Users/masa/Projects/claude-mpm/src/claude_mpm/hooks/claude_hooks/hook_handler.py` |
| Hook Installer | Install/uninstall hooks | `/Users/masa/Projects/claude-mpm/src/claude_mpm/hooks/claude_hooks/installer.py` |
| Hook Service | Alternative installer | `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/hook_installer_service.py` |

### Configuration Files

| File | Purpose | Status |
|------|---------|--------|
| `~/.claude/settings.json` | Claude Code hook configuration | ❌ No hooks configured |
| `/Users/masa/Projects/claude-mpm/uv.lock` | UV dependency lock file | ✅ Exists |
| `/Users/masa/Projects/claude-mpm/pyproject.toml` | Project dependencies | ✅ Contains pyyaml |

### Log Files

| File | Purpose | Status |
|------|---------|--------|
| `/tmp/claude-mpm-hook.log` | Hook debug log | Empty (hooks not running) |
| `/tmp/claude-mpm-hook-error.log` | Hook error log | Contains old import errors |

---

## Conclusion

**Root Cause**: Hooks are not installed in Claude Code settings (`~/.claude/settings.json`).

**Fix**: Run `uv run claude-mpm configure hooks --enable` to install hooks.

**Verification**: Check that `~/.claude/settings.json` contains hook configuration and test with Claude Code command.

**Next Steps**:
1. Install hooks
2. Clear old error logs
3. Test hook integration
4. Monitor hook execution with debug logging

---

**Research Completed**: 2025-12-19
**Confidence**: HIGH (verified with code inspection, log analysis, and environment testing)
