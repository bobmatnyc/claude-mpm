# Version Management Guide

Claude MPM uses automated semantic versioning based on git tags and conventional commits.

## Overview

The project uses `setuptools-scm` for automatic version detection from git, which means:
- Version is derived from git tags (format: `v0.5.0`)
- Between releases, versions include commit count: `0.5.0.post2+g1234567`
- Dirty working directories add `.dirty` suffix
- No manual version updates needed in code

## Version Sources

1. **Primary**: Git tags (managed by setuptools-scm)
2. **Canonical**: `VERSION` file (kept in sync via pre-commit hook)
3. **Runtime**: `src/claude_mpm/_version.py` (auto-generated)
4. **Package**: `pyproject.toml` uses dynamic versioning

## Version Management Script

Use `scripts/manage_version.py` for version operations:

### Check Current Version
```bash
./scripts/manage_version.py check
```

### Automatic Version Bump
Analyzes commits and bumps appropriately:
```bash
# Dry run to see what would happen
./scripts/manage_version.py auto --dry-run

# Actually bump version, update changelog, commit, and tag
./scripts/manage_version.py auto
```

### Manual Version Bump
```bash
# Bump specific version component
./scripts/manage_version.py bump --bump-type minor
./scripts/manage_version.py bump --bump-type major
./scripts/manage_version.py bump --bump-type patch
```

### Update Changelog Only
```bash
./scripts/manage_version.py changelog
```

### Create Tag for Current Version
```bash
./scripts/manage_version.py tag
```

## Conventional Commits

The project follows [Conventional Commits](https://www.conventionalcommits.org/) for automatic versioning:

### Commit Format
```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Types and Version Impact

- **feat**: New feature → Minor version bump
- **fix**: Bug fix → Patch version bump
- **perf**: Performance improvement → Patch version bump
- **BREAKING CHANGE**: Breaking change → Major version bump

Other types (docs, style, refactor, test, build, ci, chore) don't trigger version bumps.

### Examples
```bash
# Minor version bump (0.5.0 → 0.6.0)
git commit -m "feat(agents): add new data analysis agent"

# Patch version bump (0.5.0 → 0.5.1)
git commit -m "fix(logging): correct session duration calculation"

# Major version bump (0.5.0 → 1.0.0)
git commit -m "feat!: redesign agent communication protocol

BREAKING CHANGE: Agent API has changed, update all custom agents"
```

## Release Process

### 1. Ensure Clean Working Directory
```bash
git status  # Should be clean
```

### 2. Run Version Bump
```bash
# Automatic based on commits
./scripts/manage_version.py auto

# Or manual for specific bump
./scripts/manage_version.py bump --bump-type minor
```

This will:
- Calculate new version
- Update VERSION file
- Generate CHANGELOG entry
- Commit changes
- Create git tag

### 3. Review Changes
```bash
git show HEAD  # Review version commit
cat CHANGELOG.md  # Check changelog entry
```

### 4. Push to Remote
```bash
git push origin main
git push origin --tags
```

### 5. Build and Publish (if needed)
```bash
# Build package
python -m build

# Publish to PyPI
python -m twine upload dist/*
```

## Pre-commit Hook

The project includes a pre-commit hook that automatically updates the VERSION file.

### Enable the Hook
```bash
git config core.hooksPath .githooks
```

### Manual Update
```bash
# Update VERSION file to match current git version
python -c "from setuptools_scm import get_version; print(get_version())" > VERSION
```

## Version Display

Version is shown in multiple places:
- CLI: `claude-mpm --version`
- Interactive mode: Startup banner
- Logs: Session metadata
- Package: `claude_mpm.__version__`

## Troubleshooting

### Version Shows as 0.0.0
- No git tags exist
- Not in a git repository
- setuptools-scm not installed

### Version Shows .dirty Suffix
- Uncommitted changes in working directory
- Commit or stash changes for clean version

### Tag Not Recognized
- Ensure tag format is `v0.5.0` (with 'v' prefix)
- Push tags to remote: `git push --tags`

### Different Versions in Different Places
- Run `./scripts/manage_version.py check` to diagnose
- Ensure pre-commit hook is enabled
- Manually sync with VERSION file if needed

## Best Practices

1. **Use Conventional Commits**: Enables automatic version determination
2. **Tag Releases**: Always tag releases with `v` prefix
3. **Keep Changelog Updated**: Run version script to auto-generate entries
4. **Review Before Release**: Use `--dry-run` to preview changes
5. **Sync After Clone**: Run `git fetch --tags` to get all version tags