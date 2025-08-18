# Release Process

This document describes the release process for Claude MPM, including changelog management, version bumping, and automated release creation.

## Overview

Claude MPM follows a structured release process that ensures:
- Consistent versioning across all files
- Comprehensive changelog documentation
- Automated release notes generation
- Proper Git tagging and GitHub releases

## Prerequisites

### Required Tools

1. **Commitizen** - For version bumping and changelog updates
   ```bash
   pip install commitizen
   ```

2. **Pre-commit** - For commit message validation
   ```bash
   pip install pre-commit
   pre-commit install
   ```

3. **Git** - Configured with push access to the repository

## Release Workflow

### 1. Development Phase

During development, follow these practices:

#### Commit Message Format

Use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - New features (triggers minor version bump)
- `fix:` - Bug fixes (triggers patch version bump)
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `perf:` - Performance improvements
- `test:` - Test additions or changes
- `chore:` - Build process or auxiliary tool changes
- `feat!:` or `BREAKING CHANGE:` - Breaking changes (triggers major version bump)

Examples:
```bash
git commit -m "feat: add webhook support for notifications"
git commit -m "fix: resolve memory leak in agent deployment"
git commit -m "feat!: redesign API authentication (BREAKING CHANGE)"
```

#### Update Unreleased Section

As you work, add entries to the `[Unreleased]` section of CHANGELOG.md:

```markdown
## [Unreleased]

### Added
- Webhook support for real-time notifications
- New dashboard metrics view

### Fixed
- Memory leak in agent deployment service
- Socket.IO connection stability issues

### Changed
- Improved error messages for better debugging

### Removed
- Deprecated v1 API endpoints
```

### 2. Pre-Release Checks

Before creating a release, verify everything is ready:

```bash
# Run the release workflow check
./scripts/release_workflow.sh check

# This will verify:
# - CHANGELOG.md has [Unreleased] section with content
# - Version consistency across files
# - No uncommitted changes
# - Structure linting passes
```

### 3. Create Release

#### Automatic Version Bump (Recommended)

Let Commitizen determine the version based on commits:

```bash
# Commitizen will analyze commits and bump accordingly
cz bump

# Or specify the bump type explicitly
cz bump --patch     # 4.0.3 -> 4.0.4
cz bump --minor     # 4.0.3 -> 4.1.0
cz bump --major     # 4.0.3 -> 5.0.0
```

This will:
1. Analyze commit messages since last tag
2. Determine appropriate version bump
3. Update VERSION file
4. Update package.json version
5. Update pyproject.toml version
6. Move [Unreleased] content to new version section in CHANGELOG.md
7. Create a commit with message like "bump: version 4.0.3 → 4.0.4"
8. Create a Git tag (e.g., `v4.0.4`)

#### Manual Version Bump

If you need to manually control the version:

1. Update VERSION file
2. Update package.json version field
3. Update pyproject.toml [tool.commitizen] version
4. Move [Unreleased] content to new version section in CHANGELOG.md
5. Add comparison link at bottom of CHANGELOG.md
6. Commit changes: `git commit -m "bump: version X.Y.Z"`
7. Create tag: `git tag -a vX.Y.Z -m "Release version X.Y.Z"`

### 4. Push Release

```bash
# Push commits and tags
git push origin main
git push origin --tags
```

### 5. Automated Release Creation

Once the tag is pushed, GitHub Actions will automatically:

1. Extract release notes from CHANGELOG.md for the tagged version
2. Create a GitHub Release with:
   - Release title: `v{version}`
   - Release notes from CHANGELOG.md
   - Installation instructions
   - Comparison link to previous version
3. Mark as pre-release if version contains `alpha`, `beta`, or `rc`

### 6. Publish to PyPI

For stable releases, publish to PyPI:

```bash
# Build the package
python -m build

# Upload to PyPI (requires PyPI credentials)
python -m twine upload dist/*
```

## Release Types

### Patch Release (X.Y.Z+1)

For bug fixes and minor improvements:
- No breaking changes
- No new features
- Examples: `4.0.3` → `4.0.4`

### Minor Release (X.Y+1.0)

For new features and enhancements:
- New functionality added
- Backward compatible
- Examples: `4.0.3` → `4.1.0`

### Major Release (X+1.0.0)

For breaking changes:
- API changes
- Removed features
- Major architectural changes
- Examples: `4.0.3` → `5.0.0`

### Pre-releases

For testing before stable release:
- Alpha: `5.0.0-alpha.1`
- Beta: `5.0.0-beta.1`
- Release Candidate: `5.0.0-rc.1`

## Changelog Management

### Structure

CHANGELOG.md follows [Keep a Changelog](https://keepachangelog.com/) format:

```markdown
## [Unreleased]

### Added
- New features

### Changed
- Changes to existing functionality

### Deprecated
- Features to be removed in future versions

### Removed
- Removed features

### Fixed
- Bug fixes

### Security
- Security fixes

## [4.0.3] - 2025-08-17

### Fixed
- Socket.IO dashboard issues
...

[Unreleased]: https://github.com/bobmatnyc/claude-mpm/compare/v4.0.3...HEAD
[4.0.3]: https://github.com/bobmatnyc/claude-mpm/compare/v4.0.2...v4.0.3
```

### Best Practices

1. **Keep [Unreleased] Updated**: Add entries as you merge PRs
2. **Be Descriptive**: Write changelog entries for users, not developers
3. **Group Related Changes**: Organize by impact type
4. **Include PR/Issue Numbers**: Reference GitHub issues when relevant
5. **Document Breaking Changes**: Clearly mark and explain breaking changes

## Validation Tools

### Structure Linter

The project includes a structure linter that validates:
- CHANGELOG.md format and requirements
- Version consistency across files
- Presence of [Unreleased] section
- Comparison links

Run manually:
```bash
python tools/dev/structure_linter.py --verbose
```

### Pre-commit Hooks

Commitizen validates commit messages:
```bash
# Install hooks
pre-commit install

# Commit messages will be validated automatically
git commit -m "invalid message"  # Will be rejected
git commit -m "fix: valid message"  # Will be accepted
```

### Release Workflow Script

Helper script for release management:
```bash
# Check release readiness
./scripts/release_workflow.sh check

# View changelog
./scripts/release_workflow.sh changelog

# Validate recent commits
./scripts/release_workflow.sh validate
```

## Troubleshooting

### Version Mismatch

If versions are out of sync:
1. Check VERSION file (source of truth)
2. Update package.json to match
3. Update pyproject.toml [tool.commitizen] version
4. Run structure linter to verify

### Missing Changelog Entry

If current version is not in CHANGELOG:
1. Add version section to CHANGELOG.md
2. Move appropriate content from [Unreleased]
3. Add comparison link at bottom

### Failed Release

If GitHub Actions fails to create release:
1. Check that tag follows format `vX.Y.Z`
2. Verify CHANGELOG.md has section for the version
3. Check GitHub Actions logs for specific errors

## Quick Reference

### Complete Release in 5 Steps

```bash
# 1. Check readiness
./scripts/release_workflow.sh check

# 2. Create release
cz bump

# 3. Push to GitHub
git push && git push --tags

# 4. Verify GitHub Release
# Check https://github.com/bobmatnyc/claude-mpm/releases

# 5. Publish to PyPI (if stable)
python -m build && python -m twine upload dist/*
```

## Related Documentation

- [CHANGELOG.md](../CHANGELOG.md) - Project changelog
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guidelines
- [VERSIONING.md](VERSIONING.md) - Versioning strategy
- [Conventional Commits](https://www.conventionalcommits.org/) - Commit message specification