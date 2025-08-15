# Build Tracking System

## Overview

The claude-mpm build tracking system automatically increments build numbers for every code change, providing fine-grained tracking of code evolution. Build numbers are displayed in the version string as `vX.Y.Z-BBBBB` (e.g., `v3.10.0-00042`).

## Components

### 1. BUILD_NUMBER File
- **Location**: `/BUILD_NUMBER` (project root)
- **Format**: Plain text file containing a single integer
- **Purpose**: Stores the current build number
- **Persistence**: Never resets, increments forever

### 2. Build Increment Script
- **Location**: `/scripts/increment_build.py`
- **Purpose**: Intelligently increments build numbers based on code changes
- **Features**:
  - Detects code changes via git diff
  - Only increments for actual code changes (not docs/config)
  - Supports manual forcing and check-only modes

### 3. Git Pre-commit Hook
- **Location**: `/scripts/pre-commit-build.sh` (source)
- **Installed to**: `/.git/hooks/pre-commit`
- **Purpose**: Automatically increments build on code commits
- **Behavior**: 
  - Checks staged files for code changes
  - Increments build number if code changed
  - Adds BUILD_NUMBER to the commit

### 4. Installation Script
- **Location**: `/scripts/install_git_hook.sh`
- **Purpose**: Easy installation/removal of the git hook
- **Features**:
  - Backs up existing hooks
  - Interactive installation
  - Clean uninstall option

## What Counts as Code Changes?

### Included (triggers build increment):
- Python files (`*.py`) in `src/` directory
- Shell scripts (`*.sh`) in `scripts/` directory  
- Python scripts (`*.py`) in `scripts/` directory

### Excluded (does NOT trigger increment):
- Markdown files (`*.md`)
- Documentation in `docs/` directory
- JSON configuration in `agents/templates/`
- The BUILDVERSION file itself
- Test files (configurable)

## Installation

### Automatic Installation
```bash
# Install the git hook
./scripts/install_git_hook.sh

# Verify installation
git config --get core.hooksPath  # Should be empty or .git/hooks
ls -la .git/hooks/pre-commit     # Should exist and be executable
```

### Manual Installation
```bash
# Copy the hook manually
cp scripts/pre-commit-build.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

### Uninstall
```bash
# Remove the hook
./scripts/install_git_hook.sh --remove
```

## Usage

### Automatic Usage (Recommended)
Once the git hook is installed, build numbers increment automatically:
```bash
# Make code changes
edit src/some_module.py

# Commit - build number increments automatically
git add src/some_module.py
git commit -m "feat: add new feature"
# Output: Build number updated to: 43
```

### Manual Usage

#### Check if increment is needed
```bash
python3 scripts/increment_build.py --check-only
```

#### Force increment
```bash
python3 scripts/increment_build.py --force
```

#### Increment based on all changes (not just staged)
```bash
python3 scripts/increment_build.py --all-changes
```

## Version Display

The build number appears in the version string throughout the application:

### Interactive Session
```
╭───────────────────────────────────────────────────╮
│ ✻ Claude MPM - Interactive Session                │
│   Version v3.10.0-00042                           │
│                                                   │
```

### CLI Commands
```bash
$ claude-mpm --version
claude-mpm v3.10.0-00042
```

## Workflow Examples

### Example 1: Feature Development
```bash
# Start with build 42
$ cat BUILDVERSION
42

# Develop feature
$ vim src/claude_mpm/new_feature.py

# Commit - build auto-increments
$ git add src/claude_mpm/new_feature.py
$ git commit -m "feat: implement new feature"
Checking for code changes...
Code changes detected, incrementing build number...
Build number updated to: 43
BUILDVERSION file added to commit

# Version now shows build 43
$ claude-mpm --version
claude-mpm v3.10.0-00043
```

### Example 2: Documentation Only
```bash
# Start with build 43
$ cat BUILDVERSION
43

# Update documentation
$ vim README.md

# Commit - no increment (docs only)
$ git add README.md
$ git commit -m "docs: update readme"
Checking for code changes...
No code changes detected, build number unchanged

# Build stays at 43
$ cat BUILDVERSION
43
```

### Example 3: Mixed Changes
```bash
# Make both code and doc changes
$ vim src/module.py docs/guide.md

# Commit - increments (has code changes)
$ git add .
$ git commit -m "feat: update module with docs"
Checking for code changes...
Code changes detected, incrementing build number...
Build number updated to: 44
Code changes detected in 1 file(s)
  - src/module.py
```

## Troubleshooting

### Build not incrementing
1. Check hook is installed: `ls -la .git/hooks/pre-commit`
2. Verify Python 3 is available: `which python3`
3. Test manually: `python3 scripts/increment_build.py --check-only`
4. Check git staging: `git status`

### Hook not running
1. Ensure hook is executable: `chmod +x .git/hooks/pre-commit`
2. Check for hook bypass: Don't use `git commit --no-verify`
3. Verify git version: `git --version` (need 2.9+)

### Wrong build number
- Build numbers never decrease or reset
- If BUILDVERSION is corrupted, manually edit to correct number
- Check git history: `git log --oneline BUILDVERSION`

### Version not displaying
1. Ensure BUILDVERSION exists in project root
2. Check file permissions: `ls -la BUILDVERSION`
3. Verify content is valid integer: `cat BUILDVERSION`

## Best Practices

1. **Always use the git hook** - Ensures consistency across team
2. **Don't manually edit BUILDVERSION** - Unless fixing corruption
3. **Include BUILDVERSION in commits** - The hook does this automatically
4. **Don't bypass hooks** - Avoid `--no-verify` flag
5. **Monitor build numbers** - Large jumps may indicate issues

## Implementation Details

### Why BUILDVERSION not BUILD_VERSION?
- Simpler, cleaner filename
- Consistent with VERSION file convention
- Easier to type and remember
- No extension to avoid confusion with markdown

### Why 5-digit padding?
- Allows up to 99,999 builds
- Consistent string sorting
- Clean visual alignment
- Future-proof for large projects

### Why separate from semantic version?
- Build numbers track every change
- Semantic versions track API compatibility
- Builds increment on every code commit
- Versions change on feature/fix releases

## Integration Points

The build tracking system integrates with:

1. **ClaudeRunner** (`src/claude_mpm/core/claude_runner.py`)
   - Reads BUILDVERSION in `_get_version()` method
   - Formats as `vX.Y.Z-BBBBB`

2. **Interactive Session** (`src/claude_mpm/core/interactive_session.py`)
   - Displays version with build in welcome message

3. **CLI** (various command modules)
   - Shows build number in version output

4. **Deployment** 
   - Build numbers included in package metadata
   - Useful for debugging production issues

## Future Enhancements

Potential improvements to consider:

1. **Build metadata**: Store timestamp, commit hash with build
2. **Build changelog**: Auto-generate changelog from build increments  
3. **Build tags**: Tag specific builds for releases
4. **Build analytics**: Track build frequency and patterns
5. **CI/CD integration**: Increment builds in CI pipelines
6. **Build rollback**: Ability to reference specific builds
7. **Multi-branch tracking**: Separate build sequences per branch

## Related Documentation

- [Versioning Guide](VERSIONING.md) - Semantic versioning strategy
- [Development Guidelines](../CLAUDE.md) - Overall development practices
- [Deployment Guide](DEPLOY.md) - How builds affect deployment