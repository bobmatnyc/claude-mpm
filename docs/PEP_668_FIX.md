# PEP 668 Fix Implementation

## Overview

This document describes the implementation of PEP 668 support in claude-mpm's dependency installation system.

## Problem

Claude-mpm was encountering failures when trying to install agent dependencies in Python environments managed by system package managers (like Homebrew's Python 3.13). These environments implement PEP 668, which prevents pip from installing packages globally to avoid conflicts with the system package manager.

### Error Encountered

```
error: externally-managed-environment

× This environment is externally managed
╰─> To install Python packages system-wide, try brew install
    xyz, where xyz is the package you are trying to install.
```

## Solution

We've implemented automatic PEP 668 detection and handling in the `robust_installer.py` module. When a PEP 668 managed environment is detected, the installer automatically adds the necessary flags to bypass the restrictions while warning users about best practices.

## Implementation Details

### 1. Detection Method

The installer checks for the presence of an `EXTERNALLY-MANAGED` marker file in Python's stdlib directory:

```python
def _check_pep668_managed(self) -> bool:
    stdlib_path = sysconfig.get_path('stdlib')
    marker_file = Path(stdlib_path) / 'EXTERNALLY-MANAGED'
    
    if marker_file.exists():
        return True
    
    # Also check parent directory (some installations place it there)
    parent_marker = marker_file.parent.parent / 'EXTERNALLY-MANAGED'
    if parent_marker.exists():
        return True
    
    return False
```

### 2. Automatic Flag Addition

When PEP 668 is detected, the installer automatically adds `--break-system-packages --user` flags to all pip commands:

```python
if self.is_pep668_managed:
    cmd.extend(["--break-system-packages", "--user"])
```

### 3. User Warning

Users are warned about the PEP 668 environment and encouraged to use virtual environments:

```
⚠️  PEP 668 MANAGED ENVIRONMENT DETECTED
Your Python installation is marked as externally managed (PEP 668).
This typically means you're using a system Python managed by Homebrew, apt, etc.

Installing packages with --break-system-packages --user flags...

RECOMMENDED: Use a virtual environment instead:
  python -m venv .venv
  source .venv/bin/activate  # On Windows: .venv\Scripts\activate
  pip install claude-mpm
```

## Files Modified

1. **`src/claude_mpm/utils/robust_installer.py`**
   - Added `_check_pep668_managed()` method to detect PEP 668 environments
   - Added `_show_pep668_warning()` method to display user warnings
   - Modified `_build_install_command()` to add flags when needed
   - Modified `_attempt_batch_install()` for batch installations
   - Updated `get_report()` to include PEP 668 status

2. **`src/claude_mpm/utils/agent_dependency_loader.py`**
   - Updated fallback installation code to handle PEP 668
   - Added PEP 668 detection and flag addition in the ImportError handler

3. **`tests/test_pep668_handling.py`** (new file)
   - Comprehensive unit tests for PEP 668 detection and handling
   - Tests for command generation with and without PEP 668
   - Tests for warning display and report generation

## Behavior Changes

### Before Fix
- Installation failed with "externally-managed-environment" error
- No workaround available without manual intervention
- All 45 agent dependencies would fail to install

### After Fix
- Automatic detection of PEP 668 environments
- Transparent handling with appropriate flags
- Clear warning to users about the situation
- Suggestion to use virtual environments as best practice
- Installation proceeds successfully with user-level packages

## Best Practices

While the fix allows installations to proceed, users should be encouraged to use virtual environments for better isolation:

```bash
# Create virtual environment
python -m venv .venv

# Activate it
source .venv/bin/activate  # On macOS/Linux
# or
.venv\Scripts\activate  # On Windows

# Install claude-mpm
pip install claude-mpm
```

## Testing

The fix has been tested with:
- Python 3.13 with Homebrew (PEP 668 managed)
- Automated unit tests covering all scenarios
- Manual verification of package installation

All tests pass and packages install successfully in PEP 668 environments.

## Future Considerations

1. **Virtual Environment Detection**: Could add detection for when already in a virtual environment to skip warnings
2. **Configuration Option**: Could add a config option to control PEP 668 handling behavior
3. **Alternative Strategies**: Could explore using pipx for isolated installations

## References

- [PEP 668 - Marking Python base environments as "externally managed"](https://peps.python.org/pep-0668/)
- [pip documentation on externally managed environments](https://pip.pypa.io/en/stable/cli/pip_install/#externally-managed-environments)