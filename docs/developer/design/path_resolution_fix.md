# Path Resolution Fix for pipx Installations

## Problem Summary

The claude-mpm path resolution was failing in pipx installations because it incorrectly assumed a development structure (`src/claude_mpm/`) existed in all environments. In pipx/pip installations, packages are installed directly in `site-packages/claude_mpm/` without the `src/` directory.

## Root Cause

Two path resolution systems had the same incorrect assumption:

1. **`/src/claude_mpm/utils/paths.py`** - PathResolver class
2. **`/src/claude_mpm/config/paths.py`** - ClaudeMPMPaths class

Both were searching for `site-packages/claude_mpm/src/claude_mpm/agents` (doesn't exist) instead of `site-packages/claude_mpm/agents` (correct location).

## Solution Implementation

### 1. PathResolver Fixes (`utils/paths.py`)

#### Framework Root Detection
- **Development**: Returns project root when `src/` directory exists
- **Installed**: Returns the claude_mpm package directory itself
- **Logic**: Checks if module parent is named 'src' to detect development environment

#### Agents Directory Resolution
- **Primary**: Try importlib.resources for most reliable package resource access
- **Development**: Check `framework_root/src/claude_mpm/agents`
- **Installed**: Check `framework_root/agents` (framework_root is already claude_mpm)
- **Fallback**: Additional paths for edge cases

#### New Resource Method
Added `get_package_resource_path()` method that:
- Uses importlib.resources for Python 3.9+ (most reliable)
- Falls back to file system detection for older Python versions
- Handles both development and installed environments transparently

### 2. ClaudeMPMPaths Fixes (`config/paths.py`)

#### Installation Detection
- Added `_is_installed` flag to track environment type
- Detects installation by checking for 'site-packages' or 'dist-packages' in path
- Uses different path resolution strategies based on environment

#### Directory Properties
- **Installed environments**: 
  - Package directories resolve directly under claude_mpm
  - User directories (logs, temp) use `~/.claude-mpm/`
  - Project-specific directories use current working directory
- **Development environments**:
  - All paths resolve relative to project root as before

## Testing

### Test Coverage
1. **Development environment**: All tests pass ✅
2. **Path resolver tests**: 18 tests passing ✅
3. **Agent deployment tests**: Paths resolve correctly ✅
4. **New test script**: Validates both PathResolver and ClaudeMPMPaths

### Test Scenarios Covered
- Development structure: `/path/to/project/src/claude_mpm/`
- pip install: `site-packages/claude_mpm/`
- pipx install: `.local/pipx/venvs/claude-mpm/lib/pythonX.Y/site-packages/claude_mpm/`
- Editable install: `pip install -e .`

## Installation Types Supported

| Installation Type | Package Location | Agents Path |
|------------------|------------------|-------------|
| Development | `project/src/claude_mpm/` | `project/src/claude_mpm/agents/` |
| Editable (`pip install -e .`) | `project/src/claude_mpm/` | `project/src/claude_mpm/agents/` |
| pip install | `site-packages/claude_mpm/` | `site-packages/claude_mpm/agents/` |
| pipx install | `pipx/venvs/.../site-packages/claude_mpm/` | `pipx/venvs/.../site-packages/claude_mpm/agents/` |
| System package | `dist-packages/claude_mpm/` | `dist-packages/claude_mpm/agents/` |

## API Usage

### Recommended Approach
```python
from claude_mpm.utils.paths import PathResolver

# Get package resources (works in all environments)
templates_dir = PathResolver.get_package_resource_path('agents/templates')
specific_file = PathResolver.get_package_resource_path('agents/templates/engineer.json')

# Get agents directory (backward compatible)
agents_dir = PathResolver.get_agents_dir()
```

### Legacy Support
```python
from claude_mpm.config.paths import paths

# Still works, now environment-aware
agents_dir = paths.agents_dir
```

## Benefits

1. **Universal Compatibility**: Works across all installation methods
2. **No Breaking Changes**: Maintains backward compatibility
3. **Robust Detection**: Uses multiple strategies with fallbacks
4. **Future-Proof**: Uses importlib.resources when available
5. **Clear Separation**: Different strategies for package vs user resources

## Migration Guide

For code using path resolution:

1. **Prefer PathResolver** over ClaudeMPMPaths for new code
2. **Use get_package_resource_path()** for accessing package resources
3. **No changes needed** for existing code - backward compatibility maintained
4. **Clear caches** after installation type changes: `PathResolver.clear_cache()`

## Implementation Notes

- Both path systems updated to ensure consistency
- Uses Python's importlib.resources for future compatibility
- Graceful fallbacks for older Python versions
- Comprehensive error messages for debugging path issues
- Caching preserved for performance

## Future Improvements

1. Consider migrating all path resolution to PathResolver
2. Add more comprehensive importlib.resources usage
3. Consider using pkg_resources as additional fallback
4. Add environment variable override for testing different scenarios