# Claude MPM Dependency Installation Issue Investigation

**Date**: 2026-01-02
**Investigator**: Research Agent
**Issue**: "26 agent dependencies missing" with installation failing

## Executive Summary

The dependency installation mechanism in Claude MPM fails when invoked through `uv run` because the installer uses `uv pip install` without specifying the virtual environment context. The error message "No virtual environment found; run `uv venv` to create an environment, or pass `--system` to install into a non-virtual environment" occurs because `uv pip` requires explicit virtual environment specification.

## Root Cause Analysis

### Issue Location

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/utils/robust_installer.py`
**Lines**: 336-338, 709-710

```python
# UV tool environments don't have pip; use uv pip instead
if self.is_uv_tool:
    base_cmd = ["uv", "pip", "install"]
    logger.debug("Using 'uv pip install' for UV tool environment")
```

### The Problem

1. **UV Detection Logic** (`_check_uv_tool_installation()` in line 265-292):
   - Checks for `UV_TOOL_DIR` environment variable
   - Checks if executable path contains `.local/share/uv/tools/`
   - Returns `True` if running in UV tool environment

2. **Installation Command Construction**:
   - When `is_uv_tool` is `True`, uses: `["uv", "pip", "install"]`
   - This command requires either:
     - An active virtual environment to be specified with `--python`
     - The `--system` flag to install system-wide
     - Or it must be run from within an activated virtual environment

3. **Actual Environment** (verified via testing):
   ```
   Executable: /Users/masa/Projects/claude-mpm/.venv/bin/python3
   Prefix: /Users/masa/Projects/claude-mpm/.venv
   Base Prefix: /Users/masa/.local/share/uv/python/cpython-3.11.14-macos-aarch64-none
   VIRTUAL_ENV: /Users/masa/Projects/claude-mpm/.venv
   ```
   - **The `.venv` virtual environment EXISTS and IS active**
   - But `uv pip install` doesn't automatically detect it

### Why This Happens

The `uv pip` command is context-sensitive and doesn't automatically use the current Python environment when called as a subprocess. When you run `uv pip install <package>`, it:

1. Looks for explicit `--python` flag pointing to a virtual environment
2. Checks if it's being run with the `--system` flag
3. Otherwise errors with: "No virtual environment found"

However, the code constructs the command as `["uv", "pip", "install", <packages>]` without:
- The `--python` flag pointing to the `.venv` environment
- The `--system` flag
- Being run from within the activated environment context

## Code Flow Analysis

### Startup Dependency Check Flow

1. **Entry Point**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/commands/run.py` (lines 808-890)
   ```python
   # Get or check dependencies
   results, was_cached = smart_checker.get_or_check_dependencies(
       loader=loader,
       force_check=getattr(args, "force_check_dependencies", False),
   )

   # Show summary if there are missing dependencies
   if results["summary"]["missing_python"]:
       missing_count = len(results["summary"]["missing_python"])
       print(f"⚠️  {missing_count} agent dependencies missing")
   ```

2. **Dependency Loader**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/utils/agent_dependency_loader.py`
   - `load_and_check()` (line 832-865): Discovery and analysis
   - `install_missing_dependencies()` (line 670-830): Installation logic
   - Delegates to `RobustPackageInstaller` for actual installation

3. **Robust Installer**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/utils/robust_installer.py`
   - `_check_uv_tool_installation()` (line 265-292): Detects UV environment
   - `_build_install_command()` (line 335-378): Constructs install command
   - `install_packages()` (line 432-663): Executes installation

### Environment Detection Flaw

The `in_virtualenv` property (lines 225-237) checks:
```python
@property
def in_virtualenv(self) -> bool:
    """Check if running in a virtual environment."""
    return (
        (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix)
        or (hasattr(sys, "real_prefix"))
        or (os.environ.get("VIRTUAL_ENV") is not None)
    )
```

This DOES correctly detect the virtual environment, BUT:
- The check happens AFTER the `is_uv_tool` check
- When `is_uv_tool` is True, it uses `uv pip install` regardless of `in_virtualenv`
- The UV command doesn't inherit the virtual environment context

## Recommended Fix

### Option 1: Use `--python` flag with `uv pip` (Recommended)

Modify `_build_install_command()` in `robust_installer.py`:

```python
# UV tool environments don't have pip; use uv pip instead
if self.is_uv_tool:
    base_cmd = ["uv", "pip", "install"]
    # CRITICAL FIX: Specify virtual environment explicitly if one exists
    if self.in_virtualenv:
        # Use the current Python executable's virtual environment
        base_cmd.extend(["--python", sys.prefix])
        logger.debug(f"Using 'uv pip install --python {sys.prefix}' for UV tool + venv")
    else:
        # No venv, require explicit --system flag
        base_cmd.append("--system")
        logger.debug("Using 'uv pip install --system' for UV tool environment")
else:
    base_cmd = [sys.executable, "-m", "pip", "install"]
```

### Option 2: Prefer `python -m pip` when in virtual environment

Modify the detection order to prefer standard pip when a virtual environment is available:

```python
# Check environment in priority order
if self.in_virtualenv:
    # In virtualenv - use standard pip for reliability
    base_cmd = [sys.executable, "-m", "pip", "install"]
    logger.debug("Installing in virtualenv using standard pip")
elif self.is_uv_tool:
    # UV tool without venv - use uv pip with --system
    base_cmd = ["uv", "pip", "install", "--system"]
    logger.debug("Using 'uv pip install --system' for UV tool environment")
else:
    base_cmd = [sys.executable, "-m", "pip", "install"]
```

### Option 3: Use `uv run` wrapper (Most reliable for UV environments)

Instead of calling `uv pip install` directly, use `uv run python -m pip install`:

```python
if self.is_uv_tool:
    # Use uv run to ensure correct environment context
    base_cmd = ["uv", "run", "python", "-m", "pip", "install"]
    logger.debug("Using 'uv run python -m pip install' for UV tool environment")
else:
    base_cmd = [sys.executable, "-m", "pip", "install"]
```

This approach:
- Automatically uses the virtual environment if present
- Works consistently with UV's project management
- Avoids the "no virtual environment" error
- Most similar to how the user invokes Claude MPM (`uv run claude-mpm`)

## Testing Verification

To verify the fix works:

```bash
# Test with UV tool environment
cd /Users/masa/Projects/claude-mpm
uv run claude-mpm run --force-check-dependencies

# Should now install dependencies successfully to .venv
```

## Impact Assessment

**Severity**: High
**Affects**: All users running Claude MPM via `uv tool` or `uv run`
**Workaround**: Users can manually install with `uv pip install --python .venv <packages>`

## Related Files

- `/Users/masa/Projects/claude-mpm/src/claude_mpm/utils/robust_installer.py` - Main fix location
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/utils/agent_dependency_loader.py` - Fallback installer (lines 757-825)
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/commands/run.py` - User-facing error location
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/cli/agent_dependency_service.py` - Service layer

## Implementation Priority

**Recommended**: Option 3 (`uv run python -m pip install`)

**Reasoning**:
1. Most consistent with user's invocation method
2. Automatically handles virtual environment context
3. Works in both UV tool and regular environments
4. Minimal code changes required
5. Future-proof for UV's evolving toolchain

## Additional Notes

The same logic flaw exists in two places:
1. `RobustPackageInstaller._build_install_command()` (lines 335-378)
2. `RobustPackageInstaller._install_batch()` (lines 706-730)

Both need the same fix applied for consistency.
