# Build Tracking System

The claude-mpm project uses an automatic build tracking system that assigns a unique build number to every code change. This helps with debugging, deployment tracking, and identifying specific builds.

## Overview

- **Build Number**: A monotonically increasing integer that increments with each code change
- **Version Formats**:
  - **Development**: `3.9.5+build.275` (PEP 440 compliant)
  - **UI/Logging**: `v3.9.5-build.275` (human-readable)
  - **PyPI Release**: `3.9.5` (clean semantic version)
- **Storage**: 
  - Semantic version in `VERSION` file
  - Build number in `BUILD_NUMBER` file

## Installation

### Quick Setup

Run the installation script from the project root:

```bash
./scripts/install_build_hook.sh
```

This will install the git pre-commit hook that automatically increments build numbers.

### Manual Setup

If you prefer to set up manually:

1. Copy the pre-commit hook:
   ```bash
   cp scripts/pre-commit-build.sh .git/hooks/pre-commit
   chmod +x .git/hooks/pre-commit
   ```

2. Verify the BUILD_NUMBER file exists:
   ```bash
   cat BUILD_NUMBER  # Should show current build number
   ```

## How It Works

### Automatic Incrementing

The build number automatically increments when:
- You commit changes to Python files (`*.py`) in the `src/` directory
- You commit changes to shell scripts (`*.sh`) in the `scripts/` directory

The build number does NOT increment for:
- Documentation changes (`*.md` files)
- Configuration changes (JSON files in `agents/templates/`)
- Changes in the `docs/` directory
- Test file changes (optional, configurable)

### Manual Operations

**Check current build number:**
```bash
cat BUILD_VERSION
```

**Force increment (for testing or manual builds):**
```bash
python3 scripts/increment_build.py --force
```

**See version with build number:**
```bash
./claude-mpm run --version
# Output: Version v3.9.0-00001
```

## Components

### 1. BUILD_VERSION File
- Location: Project root
- Content: Single integer (current build number)
- Never resets, increments forever
- Tracked in git for reproducibility

### 2. increment_build.py Script
- Location: `scripts/increment_build.py`
- Purpose: Increments build number when code changes detected
- Usage:
  ```bash
  python3 scripts/increment_build.py [--force]
  ```
- Exit codes:
  - 0: Success (incremented or no code changes)
  - 1: Error occurred

### 3. Git Pre-commit Hook
- Location: `.git/hooks/pre-commit` (after installation)
- Source: `scripts/pre-commit-build.sh`
- Runs automatically before each commit
- Checks for code changes and increments if needed

### 4. Version Display Integration
- Modified `_get_version()` method in `src/claude_mpm/core/claude_runner.py`
- Reads both VERSION and BUILD_VERSION files
- Formats as: `vX.Y.Z-BBBBB`
- Falls back to version without build if BUILD_VERSION not found

## Workflow Integration

### Developer Workflow

1. Make code changes
2. Stage changes: `git add .`
3. Commit: `git commit -m "feat: add new feature"`
   - Pre-commit hook runs automatically
   - If code changes detected, build increments
   - BUILD_VERSION file is staged automatically
4. Push changes: `git push`

### CI/CD Integration

The build number can be used in CI/CD pipelines:

```bash
# Get current build number
BUILD_NUM=$(cat BUILD_VERSION)

# Use in Docker tags
docker build -t myapp:v3.9.0-${BUILD_NUM} .

# Use in artifact naming
tar -czf release-v3.9.0-${BUILD_NUM}.tar.gz dist/
```

## Troubleshooting

### Build number not incrementing

1. Check if hook is installed:
   ```bash
   ls -la .git/hooks/pre-commit
   ```

2. Check if hook is executable:
   ```bash
   chmod +x .git/hooks/pre-commit
   ```

3. Test manually:
   ```bash
   python3 scripts/increment_build.py
   ```

### Wrong build number shown

1. Ensure BUILD_VERSION file exists:
   ```bash
   ls -la BUILD_VERSION
   ```

2. Check file permissions:
   ```bash
   chmod 644 BUILD_VERSION
   ```

3. Verify Python can read it:
   ```python
   python3 -c "print(open('BUILD_VERSION').read())"
   ```

### Removing the System

To disable build tracking:

```bash
# Remove the git hook
rm .git/hooks/pre-commit

# Optionally remove BUILD_VERSION from tracking
git rm BUILD_VERSION
git commit -m "chore: remove build tracking"
```

## Best Practices

1. **Don't manually edit BUILD_VERSION** - Let the system manage it
2. **Commit BUILD_VERSION changes** - Include it in your commits for reproducibility
3. **Use in deployments** - Tag Docker images and releases with build numbers
4. **Monitor build gaps** - Large jumps might indicate many uncommitted changes

## Technical Details

### Code Change Detection

The system uses git diff to detect changes:
- `git diff --cached --name-only`: Staged files
- `git diff --name-only`: Unstaged files

Files are considered "code" if they match:
- `src/**/*.py`: Python source files
- `scripts/*.sh`: Shell scripts

### Build Number Format

- Stored as plain integer in BUILD_VERSION
- Displayed as 5-digit zero-padded string
- Range: 00001 to 99999 (then rolls to 100000+)
- Never resets or decrements

### Performance Impact

- Minimal overhead: ~50ms added to commit time
- Only runs on commit, not on other git operations
- Caches git operations for efficiency

## Future Enhancements

Potential improvements for the build tracking system:

- [ ] Add build metadata (timestamp, author, branch)
- [ ] Support for build number ranges in queries
- [ ] Integration with release notes generation
- [ ] Build number validation in CI/CD
- [ ] Automatic build tagging in git

## Support

For issues or questions about the build tracking system:
1. Check this documentation
2. Run diagnostics: `python3 scripts/increment_build.py --force`
3. Check logs: The increment script outputs to stdout/stderr
4. File an issue with the `build-tracking` label