# PackageInstallerService UV Detection Fix

## Problem

The `PackageInstallerService` was using a fixed priority: `pipx > uv > pip`, which caused kuzu-memory setup to use pipx even in uv-based projects. This resulted in incorrect install paths like:

```
/Users/masa/.local/pipx/venvs/kuzu-memory/bin/kuzu-memory
```

Instead of using uv's tool installation, which is the correct approach for uv projects.

## Root Cause

The `_detect_installer()` method (line 97-122 in `package_installer.py`) checked for pipx first without considering if we're in a uv project. The comment at line 100 showed the hardcoded priority:

```python
Priority: pipx > uv > pip
```

## Solution

Updated the priority logic to **detect uv projects first** and adjust priority accordingly:

### New Priority Logic

**In uv projects** (when any of these conditions are true):
- `uv.lock` exists in current directory or parent directories
- `sys.executable` contains "uv" (running in uv environment)
- `sys.path` contains paths with "uv"
- `pyproject.toml` has `[tool.uv]` section

**Priority:** `uv > pipx > pip`

**Outside uv projects:**

**Priority:** `pipx > uv > pip` (original behavior)

### Implementation Details

The fix adds four detection methods to identify uv projects:

1. **Method 1:** Check for `uv.lock` in current directory or parent directories
2. **Method 2:** Check if `sys.executable` contains "uv"
3. **Method 3:** Check if `sys.path` contains directories with "uv"
4. **Method 4:** Check `pyproject.toml` for `[tool.uv]` section

Once a uv project is detected, the installer priority is adjusted accordingly.

### Code Changes

#### Updated `_detect_installer()` method:

```python
def _detect_installer(self) -> InstallerType:
    """Detect the best available installer.

    Priority:
    - In uv projects: uv > pipx > pip
    - Otherwise: pipx > uv > pip

    Returns:
        The detected installer type.
    """
    # ... detection logic with 4 methods ...

    # Adjust priority based on project type
    if in_uv_project:
        # In uv projects: prioritize uv
        if "uv" in sys.executable or any("uv" in str(p) for p in sys.path):
            self._detected_installer = InstallerType.UV
        elif "pipx" in detected_methods:
            self._detected_installer = InstallerType.PIPX
        else:
            self._detected_installer = InstallerType.PIP
    else:
        # Outside uv projects: use traditional priority
        if "pipx" in detected_methods:
            self._detected_installer = InstallerType.PIPX
        elif any("uv" in str(p) for p in sys.path) or "uv" in sys.executable:
            self._detected_installer = InstallerType.UV
        else:
            self._detected_installer = InstallerType.PIP

    return self._detected_installer
```

## Testing

### Unit Tests

Created `tests/unit/services/test_package_installer_uv_detection_simple.py` with tests for:

1. ✅ Real-world uv project detection (in claude-mpm repo with uv.lock)
2. ✅ UV project marker detection (uv.lock file)
3. ✅ Priority documentation (expected behavior)
4. ✅ Parent directory detection (finds uv.lock in parents)

All tests pass:

```bash
$ uv run pytest tests/unit/services/test_package_installer_uv_detection_simple.py -v
============================= test session starts ==============================
...
tests/unit/services/test_package_installer_uv_detection_simple.py::TestUvProjectDetectionSimple::test_real_world_uv_project_detection PASSED
tests/unit/services/test_package_installer_uv_detection_simple.py::TestUvProjectDetectionSimple::test_uv_project_marker_detection PASSED
tests/unit/services/test_package_installer_uv_detection_simple.py::TestUvProjectDetectionSimple::test_priority_documentation PASSED
tests/unit/services/test_package_installer_uv_detection_simple.py::TestUvProjectDetectionSimple::test_parent_directory_detection PASSED
============================== 4 passed in 0.36s =======================================
```

### Verification

Tested in claude-mpm repository (which has uv.lock):

```bash
$ python -c "
import sys
sys.path.insert(0, 'src')
from claude_mpm.services.package_installer import PackageInstallerService
installer = PackageInstallerService()
print(f'Detected: {installer.installer_type}')
"

Detected: uv
```

## Expected Behavior After Fix

### In claude-mpm repo (has uv.lock):
- ✅ Uses **uv** for installations
- ✅ Config shows correct path: `/Users/masa/.local/bin/kuzu-memory`
- ❌ NOT: `/Users/masa/.local/pipx/venvs/kuzu-memory/bin/kuzu-memory`

### In non-uv projects:
- ✅ Uses **pipx** if available (preserves original behavior)
- ✅ Falls back to **uv** then **pip** if pipx unavailable

## Benefits

1. **Respects project package manager:** uv projects use uv installations
2. **Correct install paths:** Tools installed via uv are in expected locations
3. **Backward compatible:** Non-uv projects still prefer pipx (original behavior)
4. **Robust detection:** Four methods to identify uv projects
5. **Parent directory search:** Works in subdirectories of uv projects

## Related Files

- **Modified:** `src/claude_mpm/services/package_installer.py` (lines 97-167)
- **Added:** `tests/unit/services/test_package_installer_uv_detection_simple.py`
- **Documentation:** This file (`PACKAGE_INSTALLER_UV_FIX.md`)

## Verification Commands

```bash
# Test in uv project (claude-mpm)
uv run claude-mpm setup kuzu-memory

# Should use uv, not pipx
# Config path: /Users/masa/.local/bin/kuzu-memory (uv path)
```
