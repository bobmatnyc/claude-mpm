# Pipx Path Detection Fix

## Problem

When users have both a pipx installation and a development installation of claude-mpm, the system was incorrectly using pipx paths even when running from the development directory. This caused issues where:

1. The `claude-mpm` command in PATH points to the pipx version
2. The pipx version uses its own installation paths instead of development paths
3. Developers couldn't easily test their local changes

## Solution

Enhanced the deployment context detection in `src/claude_mpm/core/unified_paths.py` with:

### 1. Environment Variable Override
- Added `CLAUDE_MPM_DEV_MODE` environment variable support
- Setting `CLAUDE_MPM_DEV_MODE=1` (or `true`, `yes`) forces development mode
- Takes highest priority in detection logic

### 2. Editable Installation Detection
- New `_is_editable_install()` method checks for:
  - Presence of `pyproject.toml` in parent directories
  - `.pth` files pointing to source directory (pip editable installs)
  - Direct source installation (`src/` directory structure)
  - Current working directory within a development project

### 3. Working Directory Detection
- When running from within the claude-mpm development directory, the system now:
  - Detects the development project structure
  - Prefers local development paths over pipx installation
  - Works even when invoked through the pipx symlink

### 4. Development Wrapper Script
- Created `scripts/claude-mpm-dev` wrapper for explicit development mode
- Automatically sets `CLAUDE_MPM_DEV_MODE=1`
- Adds `src` to `PYTHONPATH`
- Ensures development paths are always used

## Usage

### Method 1: Automatic Detection
When in the development directory, the system automatically detects and uses development paths:
```bash
cd /Users/masa/Projects/claude-mpm
claude-mpm run  # Uses development paths automatically
```

### Method 2: Environment Variable
Force development mode from anywhere:
```bash
CLAUDE_MPM_DEV_MODE=1 claude-mpm run
```

### Method 3: Development Wrapper
Use the dedicated development script:
```bash
./scripts/claude-mpm-dev run
```

## Testing

Test the path detection with provided test scripts:

```bash
# Test basic path detection
PYTHONPATH=src python3 scripts/test_path_detection.py

# Test pipx scenario
python3 scripts/test_pipx_scenario.py

# Run unit tests
python3 -m pytest tests/test_path_detection_fix.py
```

## Implementation Details

### Detection Priority Order
1. `CLAUDE_MPM_DEV_MODE` environment variable (highest priority)
2. Editable installation detection
3. Path-based detection (development, pipx, system, pip)

### Key Changes

1. **PathContext._is_editable_install()**: New method for comprehensive editable install detection
2. **PathContext.detect_deployment_context()**: Enhanced with environment variable and working directory checks
3. **UnifiedPathManager.framework_root**: Improved to check working directory for development projects
4. **UnifiedPathManager.package_root**: Always uses source directory in development mode

### Logging

The system now logs deployment context detection at INFO level:
- "Development mode forced via CLAUDE_MPM_DEV_MODE environment variable"
- "Detected editable/development installation"
- "Running pipx from development directory, using development mode"
- "UnifiedPathManager initialized with context: [context]"

## Backward Compatibility

This fix maintains full backward compatibility:
- Existing pipx installations continue to work normally
- Development installations work as before
- New detection only activates when needed
- No changes required to existing configurations

## Troubleshooting

If path detection isn't working as expected:

1. **Check deployment context**: 
   ```python
   from claude_mpm.core.unified_paths import PathContext
   print(PathContext.detect_deployment_context())
   ```

2. **Force development mode**:
   ```bash
   export CLAUDE_MPM_DEV_MODE=1
   ```

3. **Clear path caches**:
   ```python
   from claude_mpm.core.unified_paths import get_path_manager
   get_path_manager().clear_cache()
   ```

4. **Verify paths**:
   ```python
   from claude_mpm.core.unified_paths import get_path_manager
   pm = get_path_manager()
   print(f"Framework root: {pm.framework_root}")
   print(f"Package root: {pm.package_root}")
   ```