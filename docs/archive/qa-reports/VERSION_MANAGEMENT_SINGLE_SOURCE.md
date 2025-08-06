# Single Source Version Management

## Overview

The claude-mpm project now uses a single source of truth for version management: the `VERSION` file at the project root.

## Implementation Summary

### 1. VERSION File
- Location: `/VERSION`
- Contains: Simple version string (e.g., `3.0.1`)
- Purpose: Single source of truth for all version information

### 2. Python Package Version
- **pyproject.toml**: Removed setuptools-scm, set version as dynamic
- **setup.py**: Reads directly from VERSION file
- **src/claude_mpm/__init__.py**: Reads from VERSION file
- **src/claude_mpm/cli/utils.py**: Version reading logic consolidated in CLI utilities

### 3. Removed Components
- **_version.py**: Deleted and added to .gitignore
- **setuptools-scm**: Removed from build requirements
- **Git-based versioning**: No longer used for package versioning

### 4. Pre-commit Hook
- Simplified to only sync VERSION file to package.json
- No longer generates version from git
- Ensures npm package stays in sync

### 5. Version Management Script
- **scripts/manage_version.py**: Updated to work with VERSION file
- Still supports semantic versioning bumps
- Creates git tags for releases

## Usage

### Checking Version
```bash
cat VERSION
# or
python -c "from claude_mpm import __version__; print(__version__)"
```

### Updating Version
1. Manual update:
   ```bash
   echo "3.0.2" > VERSION
   ```

2. Using manage_version.py:
   ```bash
   python scripts/manage_version.py bump --bump-type patch
   ```

### Testing Version Consistency
```bash
python scripts/test_version_management.py
```

## Benefits

1. **Simplicity**: One file to update, no complex build-time generation
2. **Reliability**: No dependency on git state or build tools
3. **Transparency**: Version is immediately visible in VERSION file
4. **Compatibility**: Works in all environments (git, no-git, CI/CD)
5. **Consistency**: All components read from the same source

## Migration Notes

- The VERSION file is now the only place to update version numbers
- Git tags are still created for releases but don't affect package version
- The pre-commit hook automatically syncs to package.json
- No build-time version generation means faster builds