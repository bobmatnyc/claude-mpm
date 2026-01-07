# INFO Logging Still Showing on Pip/Brew Installs - Root Cause Analysis

**Date**: 2025-12-19
**Issue**: Deployed versions (pip install, brew) show INFO logs despite install-type-aware fix
**Related Commit**: 5d5bf165 (fix: resolve SessionStart hook errors and install-type-aware logging)

## Executive Summary

**Root Cause**: `hooks/claude_hooks/memory_integration.py` calls `logging.basicConfig(level=logging.INFO, force=True)` at module import time (line 13-18), which reconfigures the root logger to INFO level **BEFORE** the install-type-aware fix in `core/logger.py` can take effect.

**Impact**: Production installations (pip/brew) show INFO logs when they should be silent (OFF level).

**Fix Location**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/hooks/claude_hooks/memory_integration.py`

## Timeline of Logging Configuration

### Startup Sequence

1. **CLI Entry** (`cli/__init__.py:main()`)
   - Line 53: `argv = setup_early_environment(argv)`

2. **Early Environment Setup** (`cli/startup.py:setup_early_environment()`)
   - Line 129: `logging.getLogger().setLevel(logging.CRITICAL + 1)`
   - **Purpose**: Suppress ALL logging until user preference is known
   - **Effect**: Root logger set to level 51 (CRITICAL+1)

3. **Hooks Synchronization** (`cli/startup.py:run_background_services()`)
   - Line 901: `sync_hooks_on_startup()`
   - **Imports** `hooks/claude_hooks/installer.py`
   - **Which imports** `hooks/claude_hooks/memory_integration.py`

4. **PROBLEM: Hook Module Import** (`hooks/claude_hooks/memory_integration.py`)
   - Lines 11-18:
   ```python
   # Reconfigure logging to INFO level BEFORE kuzu-memory imports
   # This overrides kuzu-memory's WARNING-level basicConfig (fixes 1M-445)
   logging.basicConfig(
       level=logging.INFO,
       format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
       force=True,  # Python 3.8+ - reconfigures root logger
       stream=sys.stderr,
   )
   ```
   - **Effect**: Root logger RECONFIGURED to INFO level (20)
   - **Timing**: Happens at module import time, before logger.py fix runs

5. **Logging Setup** (`cli/__init__.py`)
   - Line 73: `logger = setup_mcp_server_logging(args)`
   - Calls `cli/utils.py:setup_logging(args)`
   - Line 174: Default logging to OFF if not specified
   - Calls `core/logger.py:setup_logging(level='OFF')`

6. **Install-Type-Aware Fix** (`core/logger.py:setup_logging()`)
   - Lines 179-189: Detect deployment context
   - **For production**: Set level to OFF
   - **For development**: Keep INFO
   - **PROBLEM**: This runs AFTER hooks reconfigured root logger to INFO

## Evidence

### Test from Development Environment

```bash
$ python3 -c "
import sys
sys.path.insert(0, 'src')

# Step 1: Early environment setup
from claude_mpm.cli.startup import setup_early_environment
setup_early_environment([])

import logging
print(f'After setup_early_environment: root={logging.getLogger().level}')

# Step 2: Import hooks (THIS IS THE PROBLEM)
from claude_mpm.hooks.claude_hooks import memory_integration
print(f'After importing hooks: root={logging.getLogger().level}')

# Step 3: Setup logging
from claude_mpm.core.logger import setup_logging
logger = setup_logging(level='OFF')
print(f'After setup_logging(OFF): root={logging.getLogger().level}')
print(f'After setup_logging(OFF): logger={logger.level}')
"

# OUTPUT:
After setup_early_environment: root=51    # CRITICAL+1 (correct)
After importing hooks: root=20            # INFO (PROBLEM!)
After setup_logging(OFF): root=20         # Still INFO (too late!)
After setup_logging(OFF): logger=51       # Individual logger is OFF
```

### Why This Affects Production But Not Development

**In development**:
- Install-type-aware fix detects DEVELOPMENT context
- Sets level to INFO anyway
- Hook's INFO level matches, so no visible issue

**In production (pip/brew)**:
- Install-type-aware fix should set level to OFF
- But hooks already set root logger to INFO
- `logger.setLevel(CRITICAL+1)` only affects the `claude_mpm` logger
- Root logger still at INFO level, so child loggers inherit INFO

## Logging Hierarchy Issue

The problem is subtle:

```python
# In core/logger.py:setup_logging()
logger = logging.getLogger(name)  # name = "claude_mpm"
logger.setLevel(CRITICAL + 1)     # Only sets claude_mpm logger level

# But other modules do:
import logging
logger = logging.getLogger(__name__)  # __name__ = "claude_mpm.services.xyz"

# This creates a child logger that inherits from root logger
# If root logger is INFO (from hooks), child inherits INFO
# Even though claude_mpm logger is CRITICAL+1
```

### Child Logger Level Inheritance

From Python logging docs:
> If a level is not explicitly set on a logger, the level of its parent is used instead

Example hierarchy:
```
root logger (level=INFO from hooks)
└── claude_mpm (level=CRITICAL+1 from logger.py)
    └── claude_mpm.services.xyz (level=NOTSET, inherits from root!)
```

The child logger `claude_mpm.services.xyz` has `level=NOTSET` (0), so it inherits from root, NOT from claude_mpm parent.

## Why Hooks Set INFO Level

From `memory_integration.py` comment:
```python
# This overrides kuzu-memory's WARNING-level basicConfig (fixes 1M-445)
```

**Original Problem (1M-445)**: kuzu-memory library calls `basicConfig(level=WARNING)` which was too quiet.

**Fix Applied**: Force INFO level to override kuzu-memory's WARNING.

**Unintended Consequence**: This now overrides our OFF-level default for production.

## Fix Options

### Option 1: Remove Hook's basicConfig (RECOMMENDED)

**Location**: `src/claude_mpm/hooks/claude_hooks/memory_integration.py`

**Change**:
```python
# BEFORE (lines 11-18):
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    force=True,
    stream=sys.stderr,
)

# AFTER:
# Don't reconfigure root logger - respect parent process logging config
# If kuzu-memory sets WARNING level, that's acceptable
# The main CLI will configure logging properly via setup_logging()
```

**Pros**:
- Simple, removes the conflicting configuration
- Hooks should not dictate logging levels
- CLI startup handles logging configuration

**Cons**:
- May bring back 1M-445 issue if kuzu-memory is too quiet
- Need to verify kuzu-memory logging still works

### Option 2: Make Hook Logging Deployment-Aware

**Location**: `src/claude_mpm/hooks/claude_hooks/memory_integration.py`

**Change**:
```python
# Only configure INFO logging in development mode
from claude_mpm.core.unified_paths import PathContext, DeploymentContext

context = PathContext.detect_deployment_context()
if context in (DeploymentContext.DEVELOPMENT, DeploymentContext.EDITABLE_INSTALL):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        force=True,
        stream=sys.stderr,
    )
else:
    # Production: Don't reconfigure, respect parent process logging
    pass
```

**Pros**:
- Preserves development logging behavior
- Production gets proper OFF-level logging
- Deployment-aware like the main fix

**Cons**:
- Adds deployment detection to hooks
- Still overriding root logger (not clean)

### Option 3: Configure Hook Logger Specifically

**Location**: `src/claude_mpm/hooks/claude_hooks/memory_integration.py`

**Change**:
```python
# Instead of reconfiguring root logger, configure our specific logger
hook_logger = logging.getLogger("claude_mpm.hooks")
hook_logger.setLevel(logging.INFO)

# Add handler if needed (only if not already configured)
if not hook_logger.handlers:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    hook_logger.addHandler(handler)
```

**Pros**:
- Doesn't affect root logger
- Hook-specific logging configuration
- More precise control

**Cons**:
- Kuzu-memory may still override root logger
- More complex setup

### Option 4: Defer Hook Logging Until After Main Logging Setup

**Location**: `src/claude_mpm/cli/startup.py`

**Change**:
- Move `sync_hooks_on_startup()` to AFTER `setup_mcp_server_logging(args)`
- Ensure hooks are synced after logging is properly configured

**Pros**:
- Ensures main logging config runs first
- Hooks respect parent process logging level

**Cons**:
- May delay hook availability
- Startup order dependencies

## Recommended Solution

**Use Option 1: Remove Hook's basicConfig**

**Rationale**:
1. Hooks should not dictate process-wide logging configuration
2. CLI startup handles logging properly via install-type-aware fix
3. If kuzu-memory sets WARNING level, that's acceptable (or we fix kuzu-memory)
4. Simplest and cleanest solution

**Implementation**:

```python
# File: src/claude_mpm/hooks/claude_hooks/memory_integration.py
# Lines 11-18: DELETE OR COMMENT OUT

# REMOVED: Don't reconfigure root logger at module import time
# The main CLI process handles logging configuration via setup_logging()
# which includes install-type-aware defaults (OFF for production, INFO for dev)
#
# Original reason for this basicConfig:
# - Override kuzu-memory's WARNING-level default (issue 1M-445)
# However, this conflicts with production OFF-level logging requirement.
#
# If kuzu-memory logging is too quiet, we should:
# 1. Configure kuzu-memory logger specifically (not root logger)
# 2. Or fix kuzu-memory's logging configuration
# 3. Or accept WARNING-level for kuzu-memory (it's a dependency, not our code)
```

**Verification**:

After fix, test:
```bash
# 1. Production install (pipx)
pipx install --force /path/to/claude-mpm
claude-mpm run  # Should show NO INFO logs

# 2. Development install
cd /path/to/claude-mpm
uv run claude-mpm run  # Should show INFO logs (development mode)

# 3. Editable install
pip install -e .
claude-mpm run  # Should show INFO logs (development mode)
```

## Related Files

1. **Hook that causes issue**:
   - `src/claude_mpm/hooks/claude_hooks/memory_integration.py` (line 13-18)

2. **Install-type-aware fix**:
   - `src/claude_mpm/core/logger.py` (line 179-189)

3. **CLI startup**:
   - `src/claude_mpm/cli/__init__.py` (main entry)
   - `src/claude_mpm/cli/startup.py` (setup_early_environment, sync_hooks_on_startup)
   - `src/claude_mpm/cli/utils.py` (setup_logging)

4. **Deployment detection**:
   - `src/claude_mpm/core/unified_paths.py` (PathContext.detect_deployment_context)

## Other Logging Configuration Points Found

During investigation, found these other locations that configure logging:

1. **Root logger in startup.py** (line 129): `logging.getLogger().setLevel(CRITICAL+1)`
   - Purpose: Suppress all logging until preference known
   - Status: Working correctly

2. **Hook memory_integration.py** (line 13): `logging.basicConfig(level=INFO, force=True)`
   - Purpose: Override kuzu-memory WARNING level
   - Status: **THIS IS THE PROBLEM**

3. **Experimental CLI** (line 61): `logging.basicConfig(...)`
   - Location: `src/claude_mpm/experimental/cli_enhancements.py`
   - Status: Experimental code, not used in production

4. **Base command** (line 86-90): `logging.getLogger().setLevel(...)`
   - Location: `src/claude_mpm/cli/shared/base_command.py`
   - Status: Respects user flags, working correctly

5. **MCP server mode** (line 947): `logging.basicConfig(...)`
   - Location: `src/claude_mpm/cli/startup.py:setup_mcp_server_logging`
   - Status: Only for MCP server mode, working correctly

## Testing Checklist

After implementing fix:

- [ ] Test production pipx install: `pipx install --force . && claude-mpm run`
  - Expected: NO INFO logs, only user-facing output

- [ ] Test production pip install: `pip install --force-reinstall . && claude-mpm run`
  - Expected: NO INFO logs, only user-facing output

- [ ] Test development mode: `uv run claude-mpm run`
  - Expected: INFO logs showing startup process

- [ ] Test editable install: `pip install -e . && claude-mpm run`
  - Expected: INFO logs showing startup process

- [ ] Test with --logging=info flag: `claude-mpm run --logging=info`
  - Expected: INFO logs regardless of install type

- [ ] Test with --logging=off flag: `claude-mpm run --logging=off`
  - Expected: NO INFO logs regardless of install type

- [ ] Test kuzu-memory functionality still works
  - Expected: Memory hooks work, no errors

- [ ] Test hooks installation: `claude-mpm configure`
  - Expected: Hooks sync without logging errors

## Conclusion

The install-type-aware fix in `core/logger.py` is correct but runs too late. The hook's `basicConfig(force=True)` reconfigures the root logger before the fix can take effect.

**Fix**: Remove the `basicConfig` call from `memory_integration.py` (Option 1).

**Verification**: Test production install shows no INFO logs, development install shows INFO logs.
