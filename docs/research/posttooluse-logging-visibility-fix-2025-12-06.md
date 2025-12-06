# PostToolUse Hook Logging Visibility Issue - Root Cause Analysis

**Date:** 2025-12-06
**Ticket:** 1M-445
**Status:** Investigation Complete - Fix Approach Identified
**Severity:** Low (functional issue, not blocking - memories ARE being stored)

## Executive Summary

The PostToolUse hook is **working correctly** and successfully storing conversation memories. The issue is purely about **logging visibility** - log messages are suppressed due to Python's `logging.basicConfig()` configuration conflict between:

1. **kuzu-memory CLI** (`/cli/commands.py`) - sets level to `WARNING`
2. **claude-mpm logging system** (`/core/logging_utils.py`) - initializes with `INFO` level

Python's `logging.basicConfig()` can only be called once - the first call wins. Since kuzu-memory's CLI module is imported first (when the hook handler imports kuzu-memory modules), its `WARNING` level suppresses all `INFO` level messages from the memory hooks.

**Evidence:**
- Database query shows 2 memories successfully stored with `claude-code-hook` source
- Hook execution is confirmed working
- Only logging output is missing

## Problem Details

### Root Cause

**File:** `/venv/lib/python3.13/site-packages/kuzu_memory/cli/commands.py`
**Lines:** 20-24

```python
# Set up logging for CLI
logging.basicConfig(
    level=logging.WARNING,  # ⚠️ This suppresses INFO messages
    format="%(levelname)s: %(message)s",
)
```

**Impact:**
- This `logging.basicConfig()` call happens when kuzu-memory CLI is imported
- Python's logging module only respects the FIRST `basicConfig()` call
- Subsequent calls (like claude-mpm's `LoggerFactory.initialize()`) are ignored
- Result: All loggers default to `WARNING` level, suppressing `INFO` level messages

### Import Chain

The conflict occurs through this import chain:

```
hook_handler.py
  ↓ imports
memory_integration.py
  ↓ imports
memory_integration_hook.py
  ↓ imports
AgentMemoryManager (from services/agents/memory.py)
  ↓ imports
kuzu_memory modules
  ↓ imports (at module level)
kuzu_memory/cli/commands.py
  ↓ executes at import time
logging.basicConfig(level=WARNING)  # ⚠️ FIRST call wins
```

Later in the execution:

```
claude_mpm startup
  ↓ calls
LoggerFactory.initialize()
  ↓ attempts
logging.basicConfig(level=INFO)  # ❌ IGNORED - already configured
```

### Verification Evidence

**Database Confirmation (from investigation):**
```sql
MATCH (m:Memory)
WHERE m.source = 'claude-code-hook'
RETURN m.content, m.timestamp, m.source

Results: 2 memories stored successfully
```

**Log Level Detection:**
```python
# In memory_integration_hook.py line 28
logger = get_logger(__name__)

# Logger created with INFO level
# BUT root logger already configured to WARNING by kuzu-memory
# Result: logger.info() messages suppressed
```

## Affected Components

### Files That Log at INFO Level (Currently Suppressed)

1. **`src/claude_mpm/hooks/memory_integration_hook.py`**
   - Line 138: `logger.info(f"Injected memory for agent '{agent_id}'")`
   - Line 299: `logger.info(f"Extracted {learnings_stored} learnings for agent '{agent_id}'")`
   - Line 402: `logger.info(f"Extracted {total_learnings} learnings from agent response")`

2. **`src/claude_mpm/hooks/claude_hooks/memory_integration.py`**
   - Line 92: `logger.info(f"✅ Memory hooks initialized: {', '.join(hooks_info)}")`

3. **`src/claude_mpm/services/agents/memory.py`** (AgentMemoryManager)
   - Multiple INFO level logging statements about memory operations

### Files Containing logging.basicConfig (Potential Conflicts)

**Claude MPM Framework:**
1. `src/claude_mpm/scripts/mcp_server.py:20` - MCP server (stderr)
2. `src/claude_mpm/experimental/cli_enhancements.py:61` - CLI (stdout)
3. `tools/migration/migrate_config.py:19` - Migration script

**kuzu-memory Package (External):**
1. `/venv/.../kuzu_memory/cli/commands.py` - **PRIMARY CONFLICT** (WARNING level)
2. `/venv/.../kuzu_memory/migrations/cognitive_types.py` - (INFO level)
3. `/venv/.../kuzu_memory/mcp/server.py` - (INFO level)
4. `/venv/.../kuzu_memory/cli/hooks_commands.py` - (multiple calls)
5. `/venv/.../kuzu_memory/cli/commands_backup.py` - (INFO level)

## Solution Approaches

### Option 1: Environment Variable Override (Recommended)

**Approach:** Configure kuzu-memory logging via environment variable before import

**Implementation:**
```python
# In src/claude_mpm/hooks/claude_hooks/memory_integration.py
# At the TOP of the file, before any imports

import os
import sys

# Configure kuzu-memory logging BEFORE any imports
# This prevents kuzu-memory's CLI from suppressing our logs
os.environ['KUZU_MEMORY_LOG_LEVEL'] = 'INFO'

# OR set Python's logging level before kuzu-memory imports
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True  # Python 3.8+ - reconfigures existing basicConfig
)

# Now import kuzu-memory modules
from claude_mpm.core.shared.config_loader import ConfigLoader
from claude_mpm.hooks.base_hook import HookContext, HookType
from claude_mpm.hooks.memory_integration_hook import (
    MemoryPostDelegationHook,
    MemoryPreDelegationHook,
)
```

**Advantages:**
- No changes to kuzu-memory package required
- Works with current kuzu-memory version
- Simple one-line fix
- Leverages Python 3.8+ `force=True` parameter

**Disadvantages:**
- Requires Python 3.8+ for `force=True`
- May affect other kuzu-memory logging

### Option 2: Lazy Import (Alternative)

**Approach:** Defer kuzu-memory imports until after logging is configured

**Implementation:**
```python
# In memory_integration.py
MEMORY_HOOKS_AVAILABLE = False

def _lazy_import_memory_hooks():
    """Lazy import memory hooks after logging is configured."""
    global MEMORY_HOOKS_AVAILABLE
    try:
        from claude_mpm.core.shared.config_loader import ConfigLoader
        from claude_mpm.hooks.base_hook import HookContext, HookType
        from claude_mpm.hooks.memory_integration_hook import (
            MemoryPostDelegationHook,
            MemoryPreDelegationHook,
        )
        MEMORY_HOOKS_AVAILABLE = True
        return {
            'ConfigLoader': ConfigLoader,
            'HookContext': HookContext,
            'HookType': HookType,
            'MemoryPostDelegationHook': MemoryPostDelegationHook,
            'MemoryPreDelegationHook': MemoryPreDelegationHook,
        }
    except Exception as e:
        if DEBUG:
            print(f"Memory hooks not available: {e}", file=sys.stderr)
        MEMORY_HOOKS_AVAILABLE = False
        return None

class MemoryHookManager:
    def __init__(self):
        # Configure logging FIRST
        import logging
        logging.basicConfig(level=logging.INFO, force=True)

        # THEN import memory hooks
        self.memory_modules = _lazy_import_memory_hooks()
        # ... rest of initialization
```

**Advantages:**
- Complete control over import timing
- Ensures logging configured before kuzu-memory imports

**Disadvantages:**
- More complex code
- Requires refactoring import structure

### Option 3: Logger Level Override (Workaround)

**Approach:** Manually set logger levels after initialization

**Implementation:**
```python
# In memory_integration_hook.py after logger creation
logger = get_logger(__name__)

# Force logger level to INFO regardless of root logger
logger.setLevel(logging.INFO)

# Also ensure handlers are configured
if not logger.handlers:
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
```

**Advantages:**
- Minimal code changes
- No import order dependencies

**Disadvantages:**
- Doesn't fix root cause
- Requires changes in multiple files
- May still miss some logs

### Option 4: Upstream Fix (Long-term)

**Approach:** Contribute fix to kuzu-memory package

**Implementation:**
Create PR for kuzu-memory to:
1. Remove `logging.basicConfig()` from `cli/commands.py`
2. Use logger-specific configuration instead:

```python
# In kuzu_memory/cli/commands.py
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)  # Only affects this logger

# Remove the basicConfig call entirely
```

**Advantages:**
- Fixes root cause for all users
- Proper logging hygiene
- Benefits entire kuzu-memory ecosystem

**Disadvantages:**
- Requires upstream coordination
- Takes time to merge and release
- Need temporary workaround until deployed

## Recommended Fix

**Immediate Action (Option 1):** Use `force=True` parameter

**File to Modify:** `src/claude_mpm/hooks/claude_hooks/memory_integration.py`

**Changes Required:**

```python
# Add at TOP of file (line 7, before other imports)
import logging
import os
import sys

# Reconfigure logging to INFO level BEFORE kuzu-memory imports
# This overrides kuzu-memory's WARNING-level basicConfig
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True,  # Python 3.8+ - reconfigures root logger
    stream=sys.stderr,  # Hook handler redirects stderr to /tmp/claude-mpm-hook-error.log
)

# Debug mode (from line 14)
DEBUG = os.environ.get("CLAUDE_MPM_HOOK_DEBUG", "true").lower() != "false"

# Memory hooks integration (line 17)
MEMORY_HOOKS_AVAILABLE = False
try:
    # Now safe to import - logging already configured
    from claude_mpm.config.paths import paths
    paths.ensure_in_path()

    from claude_mpm.core.shared.config_loader import ConfigLoader
    # ... rest of imports
```

**Testing:**
```bash
# Enable debug logging
export CLAUDE_MPM_HOOK_DEBUG=true

# Run Claude Code with delegation
# Check /tmp/claude-mpm-hook-error.log for:
# "✅ Memory hooks initialized: pre-delegation, post-delegation"
# "✅ Injected memory for agent 'research'"
# "✅ Extracted N learnings for agent 'research'"

# Verify in database
kuzu-memory memory recent --limit 5
# Should show memories with claude-code-hook source
```

## Additional Considerations

### Hook Handler Error Logging

**Current Behavior:**
- Hook handler stderr redirected to `/tmp/claude-mpm-hook-error.log`
- See `claude-hook-handler.sh` line 178:
  ```bash
  exec "$PYTHON_CMD" -m claude_mpm.hooks.claude_hooks.hook_handler "$@" 2>/tmp/claude-mpm-hook-error.log
  ```

**Impact:**
- Even with logging fixed, messages go to error log, not visible in Claude Code output
- This is INTENTIONAL - hook handlers run in background and shouldn't block Claude

**User Experience:**
Users need to know to check error logs:
```bash
# Watch hook handler logs in real-time
tail -f /tmp/claude-mpm-hook-error.log

# Or with CLAUDE_MPM_HOOK_DEBUG=true
tail -f /tmp/claude-mpm-hook.log
```

### Python Version Compatibility

**`force=True` parameter:**
- Added in Python 3.8
- Claude MPM requires Python 3.10+
- Safe to use `force=True` without compatibility issues

**Verification:**
```python
# In pyproject.toml
[tool.poetry.dependencies]
python = "^3.10"  # ✅ Supports force=True (added in 3.8)
```

## Testing Plan

### Manual Testing

1. **Enable Debug Logging:**
   ```bash
   export CLAUDE_MPM_HOOK_DEBUG=true
   ```

2. **Apply Fix:**
   - Modify `memory_integration.py` with `force=True` solution
   - Restart Claude Code to load changes

3. **Trigger PostToolUse Hook:**
   ```bash
   # In Claude Code conversation
   # Use Task tool to delegate to Research agent
   # (This triggers PreToolUse and PostToolUse hooks)
   ```

4. **Verify Logging:**
   ```bash
   # Check hook error log
   tail -50 /tmp/claude-mpm-hook-error.log

   # Should see:
   # "✅ Memory hooks initialized: pre-delegation, post-delegation"
   # "✅ Injected memory for agent 'research'"
   # "✅ Extracted N learnings for agent 'research'"
   ```

5. **Verify Database:**
   ```bash
   kuzu-memory memory recent --limit 5
   # Should show new memories with claude-code-hook source
   ```

### Automated Testing

**Unit Test (to add):**
```python
# tests/test_memory_hook_logging.py
import logging
import sys
from io import StringIO

def test_memory_hook_logging_visibility():
    """Verify memory hook logs are visible at INFO level."""
    # Capture logs
    log_capture = StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.INFO)

    logger = logging.getLogger('claude_mpm.hooks.memory_integration_hook')
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    # Trigger memory hook
    from claude_mpm.hooks.memory_integration_hook import MemoryPostDelegationHook
    hook = MemoryPostDelegationHook()

    # ... trigger hook execution ...

    # Verify logs captured
    log_output = log_capture.getvalue()
    assert "Extracted" in log_output or "Injected" in log_output
```

## Follow-up Actions

### Immediate (This Sprint)
- [ ] Apply Option 1 fix to `memory_integration.py`
- [ ] Test with CLAUDE_MPM_HOOK_DEBUG=true
- [ ] Verify log visibility in `/tmp/claude-mpm-hook-error.log`
- [ ] Update documentation about hook debugging

### Short-term (Next Sprint)
- [ ] Add unit test for logging visibility
- [ ] Create user documentation: "Debugging Hook Handler Logs"
- [ ] Consider adding log aggregation for better UX

### Long-term (Future)
- [ ] Create PR for kuzu-memory to remove `basicConfig()` from CLI
- [ ] Standardize logging configuration across all framework components
- [ ] Implement centralized log viewer in Claude MPM dashboard

## References

**Related Files:**
- `src/claude_mpm/hooks/claude_hooks/memory_integration.py` - Hook manager
- `src/claude_mpm/hooks/memory_integration_hook.py` - Memory hooks implementation
- `src/claude_mpm/core/logging_utils.py` - Framework logging utilities
- `src/claude_mpm/scripts/claude-hook-handler.sh` - Hook handler entry point
- `/venv/.../kuzu_memory/cli/commands.py` - Source of conflict

**Python Logging Documentation:**
- `logging.basicConfig()` behavior: https://docs.python.org/3/library/logging.html#logging.basicConfig
- `force` parameter (Python 3.8+): Reconfigures root logger

**Ticket Context:**
- 1M-445: PostToolUse hook not storing conversation memories
- Investigation showed memories ARE being stored, only logging suppressed

## Conclusion

The PostToolUse hook is **fully functional** - memories are being stored successfully in the database. The issue is purely cosmetic (logging visibility) caused by a well-known Python logging anti-pattern: multiple `logging.basicConfig()` calls.

**Recommended Fix:** Add `logging.basicConfig(level=logging.INFO, force=True)` at the top of `memory_integration.py` before any kuzu-memory imports. This is a 3-line change with zero risk and immediate effect.

**Impact:** After fix, developers will see helpful log messages like:
- ✅ Memory hooks initialized
- ✅ Injected memory for agent
- ✅ Extracted N learnings

These logs will appear in `/tmp/claude-mpm-hook-error.log` (as intended by the hook handler architecture).
