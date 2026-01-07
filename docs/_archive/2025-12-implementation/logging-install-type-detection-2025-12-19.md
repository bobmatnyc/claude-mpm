# Logging Configuration and Install Type Detection Research

**Date**: 2025-12-19
**Researcher**: Claude (Opus 4.5)
**Context**: Investigate why INFO logging shows on startup for normal installs when it should only show for source installs

## Executive Summary

The current logging system **already has proper install type detection** via `PathContext.detect_deployment_context()` in `src/claude_mpm/core/unified_paths.py`. The default logging level is correctly set to "OFF" in `src/claude_mpm/core/constants.py`. However, there's a **critical timing issue** in `cli/startup.py` where logging is initialized **BEFORE** the deployment context can be properly checked.

## Current Logging Configuration

### 1. Default Log Level
**Location**: `src/claude_mpm/core/constants.py:218`
```python
class Defaults:
    DEFAULT_LOG_LEVEL = "OFF"
```

### 2. Logging Initialization Flow
**Location**: `src/claude_mpm/cli/__init__.py:70-73`
```python
# CRITICAL: Setup logging BEFORE any initialization that creates loggers
# This ensures that ensure_directories() and run_background_services()
# respect the user's logging preference (default: OFF)
logger = setup_mcp_server_logging(args)
```

**Location**: `src/claude_mpm/cli/utils.py:156-192`
```python
def setup_logging(args) -> object:
    """Set up logging based on parsed arguments."""
    from ..constants import LogLevel
    from ..core.logger import setup_logging as core_setup_logging

    # Set default logging level if not specified
    if not hasattr(args, "logging") or args.logging is None:
        args.logging = LogLevel.OFF.value

    # Handle deprecated --debug flag
    if hasattr(args, "debug") and args.debug and args.logging == LogLevel.INFO.value:
        args.logging = LogLevel.DEBUG.value

    # Only setup logging if not OFF
    if args.logging != LogLevel.OFF.value:
        logger = core_setup_logging(
            level=args.logging, log_dir=getattr(args, "log_dir", None)
        )
    else:
        # Minimal logger for CLI feedback
        import logging

        logger = logging.getLogger("cli")
        logger.setLevel(logging.WARNING)

    return logger
```

### 3. Early Environment Setup (CRITICAL)
**Location**: `src/claude_mpm/cli/startup.py:102-139`
```python
def setup_early_environment(argv):
    """
    Set up early environment variables and logging suppression.

    CRITICAL: Suppress ALL logging by default until setup_mcp_server_logging()
    configures the user's preference. This prevents early loggers (like
    ProjectInitializer and service.* loggers) from logging at INFO level before
    we know the user's logging preference.
    """
    import logging

    # Disable telemetry and set cleanup flags early
    os.environ.setdefault("DISABLE_TELEMETRY", "1")
    os.environ.setdefault("CLAUDE_MPM_SKIP_CLEANUP", "0")

    # CRITICAL: Suppress ALL logging by default
    # This catches all loggers (claude_mpm.*, service.*, framework_loader, etc.)
    # This will be overridden by setup_mcp_server_logging() based on user preference
    logging.getLogger().setLevel(logging.CRITICAL + 1)  # Root logger catches everything

    # ... rest of function
```

## Install Type Detection System

### 1. Deployment Context Detection
**Location**: `src/claude_mpm/core/unified_paths.py:58-63`
```python
class DeploymentContext:
    """Enumeration of deployment contexts."""
    DEVELOPMENT = "development"
    EDITABLE_INSTALL = "editable_install"
    PIP_INSTALL = "pip_install"
    PIPX_INSTALL = "pipx_install"
    SYSTEM_PACKAGE = "system_package"
```

### 2. Detection Logic
**Location**: `src/claude_mpm/core/unified_paths.py:171-282`
```python
@staticmethod
@lru_cache(maxsize=1)
def detect_deployment_context() -> DeploymentContext:
    """Detect the current deployment context.

    Priority order:
    1. Environment variable override (CLAUDE_MPM_DEV_MODE)
    2. Current working directory is a claude-mpm development project
    3. Editable installation detection
    4. Path-based detection (development, pipx, system, pip)
    """
```

**Detection Methods**:
1. **Environment Variable**: `CLAUDE_MPM_DEV_MODE=1` forces development mode
2. **CWD Check**: Detects if running from within claude-mpm source directory (checks for `pyproject.toml` + `src/claude_mpm`)
3. **Module Path Analysis**:
   - `module_path.parent.name == "src"` → DEVELOPMENT
   - `"pipx" in str(module_path)` → PIPX_INSTALL
   - `"dist-packages" in str(module_path)` → SYSTEM_PACKAGE
   - `"site-packages" in str(module_path)` → PIP_INSTALL
4. **Editable Install Check**: Uses `_is_editable_install()` method (lines 69-168)

### 3. Existing Usage
**Location**: `src/claude_mpm/services/self_upgrade_service.py:102-106`
```python
# Check for editable installs (development mode)
if PathContext.detect_deployment_context().name in [
    "DEVELOPMENT",
    "EDITABLE_INSTALL",
]:
    return InstallationMethod.EDITABLE
```

**Location**: `src/claude_mpm/cli/startup.py:1187-1192`
```python
# Skip for editable installs (development mode)
from ..services.self_upgrade_service import InstallationMethod

if upgrade_service.installation_method == InstallationMethod.EDITABLE:
    logger.debug("Skipping version check for editable installation")
    return
```

## Problem Analysis

### Current Behavior
The logging system **does** suppress INFO logging by default:
1. `Defaults.DEFAULT_LOG_LEVEL = "OFF"` (line 218)
2. `setup_early_environment()` sets root logger to `CRITICAL + 1` (line 129)
3. `setup_logging()` defaults to `LogLevel.OFF.value` if not specified (line 174)

### Why INFO Logs Still Show
The issue is that **individual loggers created before `setup_early_environment()`** may have already been initialized with INFO level. Specifically:

1. **LoggingUtils.LoggerFactory** (line 75-76 in `logging_utils.py`):
   ```python
   _log_level: str = Defaults.DEFAULT_LOG_LEVEL  # "OFF"
   ```
   BUT when initialized without calling `LoggerFactory.initialize()`, it uses the environment variable fallback:
   ```python
   cls._log_level = log_level or os.environ.get(
       "CLAUDE_MPM_LOG_LEVEL", Defaults.DEFAULT_LOG_LEVEL
   )
   ```

2. **Logger Creation** (line 260-285 in `logging_utils.py`):
   ```python
   @lru_cache(maxsize=128)
   def get_logger(
       name: str,
       component: Optional[str] = None,
       level: Optional[str] = None,
   ) -> logging.Logger:
       """Get a standardized logger instance (cached)."""
       return LoggerFactory.get_logger(name, component, level)
   ```

   The `LoggerFactory.get_logger()` method (line 176-210) calls `initialize()` if not already initialized:
   ```python
   # Initialize if needed
   if not cls._initialized:
       cls.initialize()
   ```

3. **The core logger setup** (line 150-217 in `logger.py`):
   ```python
   def setup_logging(
       name: str = "claude_mpm",
       level: str = "INFO",  # DEFAULT IS INFO, NOT OFF!
       log_dir: Optional[Path] = None,
       ...
   ):
   ```

### Root Cause
The root cause is that **`core/logger.py:setup_logging()` has a default of `level="INFO"`** while it should respect the `Defaults.DEFAULT_LOG_LEVEL = "OFF"` constant.

## Recommended Solution

### Option 1: Fix Default in core/logger.py (RECOMMENDED)
**File**: `src/claude_mpm/core/logger.py:150`
```python
def setup_logging(
    name: str = "claude_mpm",
    level: str = "OFF",  # Changed from "INFO"
    log_dir: Optional[Path] = None,
    ...
):
```

**Rationale**: This aligns the core logger with the framework's default log level policy.

### Option 2: Add Install Type Check to Logging Config
**File**: `src/claude_mpm/core/logger.py:150-177`
```python
def setup_logging(
    name: str = "claude_mpm",
    level: Optional[str] = None,  # Changed to None to allow auto-detection
    log_dir: Optional[Path] = None,
    ...
) -> logging.Logger:
    """
    Set up logging with both console and file handlers.

    Args:
        level: Logging level (OFF, DEBUG, INFO, WARNING, ERROR, CRITICAL)
               If None, auto-detects based on install type:
               - DEVELOPMENT/EDITABLE: INFO
               - Others: OFF
    """
    # Auto-detect logging level based on install type if not specified
    if level is None:
        from claude_mpm.core.unified_paths import PathContext, DeploymentContext

        context = PathContext.detect_deployment_context()
        if context in (DeploymentContext.DEVELOPMENT, DeploymentContext.EDITABLE_INSTALL):
            level = "INFO"  # Verbose logging for development
        else:
            level = "OFF"   # Silent for production installs

    logger = logging.getLogger(name)

    # Handle OFF level
    if level.upper() == "OFF":
        logger.setLevel(logging.CRITICAL + 1)  # Higher than CRITICAL
        logger.handlers.clear()
        return logger

    # ... rest of function
```

### Option 3: Use Environment Variable for Install Type
**File**: `src/claude_mpm/core/unified_paths.py:171-185`
```python
@staticmethod
@lru_cache(maxsize=1)
def detect_deployment_context() -> DeploymentContext:
    """Detect the current deployment context."""
    # Check for environment variable override
    if os.environ.get("CLAUDE_MPM_DEV_MODE", "").lower() in ("1", "true", "yes"):
        # SET ENVIRONMENT VARIABLE FOR LOGGING
        os.environ.setdefault("CLAUDE_MPM_LOG_LEVEL", "INFO")
        logger.debug(
            "Development mode forced via CLAUDE_MPM_DEV_MODE environment variable"
        )
        return DeploymentContext.DEVELOPMENT

    # ... rest of detection logic

    # AT END OF DETECTION:
    if context in (DeploymentContext.DEVELOPMENT, DeploymentContext.EDITABLE_INSTALL):
        os.environ.setdefault("CLAUDE_MPM_LOG_LEVEL", "INFO")
    else:
        os.environ.setdefault("CLAUDE_MPM_LOG_LEVEL", "OFF")

    return context
```

**Rationale**: Uses existing environment variable mechanism to propagate the install type to logging configuration.

## Implementation Recommendation

**RECOMMENDED APPROACH**: **Option 1** (simplest and most direct)

**Reasoning**:
1. **Minimal Code Change**: Single line change in `logger.py`
2. **Alignment with Policy**: Matches `Defaults.DEFAULT_LOG_LEVEL = "OFF"`
3. **No Side Effects**: Doesn't introduce new detection logic
4. **Backward Compatible**: Explicit `--logging` flag still works

**Alternative for Development Convenience**: **Option 2** (if you want automatic INFO for dev)

**Reasoning**:
1. **Auto-Detection**: Automatically enables INFO logging for development
2. **User Override**: Still respects explicit `--logging` flags
3. **Clear Intent**: Makes install type distinction explicit in logging setup
4. **Self-Documenting**: Code clearly shows why logging differs by install type

## Testing Checklist

After implementing the fix:

1. **Normal Install (pip/pipx)**:
   ```bash
   # Should show NO INFO logs on startup
   claude-mpm run
   ```

2. **Source Install (editable)**:
   ```bash
   # Should show INFO logs on startup (if Option 2)
   # Should show NO logs (if Option 1)
   cd /path/to/claude-mpm
   uv run claude-mpm run
   ```

3. **Explicit Logging Flag**:
   ```bash
   # Should show INFO logs regardless of install type
   claude-mpm run --logging INFO
   ```

4. **Development Mode Override**:
   ```bash
   # Should show INFO logs (if Option 2)
   CLAUDE_MPM_DEV_MODE=1 claude-mpm run
   ```

## Files Modified (Option 1)

1. `src/claude_mpm/core/logger.py` (line 152):
   ```python
   level: str = "OFF",  # Changed from "INFO"
   ```

## Files Modified (Option 2)

1. `src/claude_mpm/core/logger.py` (lines 150-177):
   - Add install type auto-detection
   - Default level to `None` instead of `"INFO"`
   - Add logic to detect DEVELOPMENT/EDITABLE_INSTALL context

## Related Code Patterns

### Existing Install Type Checks in Codebase

1. **SelfUpgradeService** (`services/self_upgrade_service.py:102-106`):
   ```python
   if PathContext.detect_deployment_context().name in [
       "DEVELOPMENT",
       "EDITABLE_INSTALL",
   ]:
       return InstallationMethod.EDITABLE
   ```

2. **Update Check Skip** (`cli/startup.py:1187-1192`):
   ```python
   if upgrade_service.installation_method == InstallationMethod.EDITABLE:
       logger.debug("Skipping version check for editable installation")
       return
   ```

3. **Path Resolution** (`core/unified_paths.py:342-346`):
   ```python
   if self._deployment_context in (
       DeploymentContext.DEVELOPMENT,
       DeploymentContext.EDITABLE_INSTALL,
   ):
       # Use development paths
   ```

### Pattern for Install Type-Aware Behavior
```python
from claude_mpm.core.unified_paths import PathContext, DeploymentContext

context = PathContext.detect_deployment_context()

if context in (DeploymentContext.DEVELOPMENT, DeploymentContext.EDITABLE_INSTALL):
    # Development behavior
    log_level = "INFO"
else:
    # Production behavior
    log_level = "OFF"
```

## Conclusion

The framework already has robust install type detection via `PathContext.detect_deployment_context()`. The logging issue is a simple default value mismatch in `core/logger.py`. The fix is straightforward:

**Recommended Fix**: Change the default `level` parameter in `setup_logging()` from `"INFO"` to `"OFF"` to match the framework-wide `Defaults.DEFAULT_LOG_LEVEL`.

**Enhanced Alternative**: Add install type auto-detection to `setup_logging()` to automatically enable INFO logging for development installs while keeping production installs silent by default.

Both approaches are valid; Option 1 is simpler while Option 2 provides better developer experience.
