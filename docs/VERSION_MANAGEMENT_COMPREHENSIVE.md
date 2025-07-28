# Comprehensive Version Management Documentation

This document provides a detailed overview of the version management system in Claude MPM, including implementation details, workflows, and strategies.

## Overview

Claude MPM implements a sophisticated version management system that ensures consistency across multiple distribution channels (PyPI, npm, GitHub) while supporting both automated and manual release workflows.

## Version Management Architecture

### 1. Core Components

#### Primary Version Sources
- **Git Tags**: Ultimate source of truth (format: `v1.2.3`)
- **setuptools-scm**: Derives version from git state dynamically
- **VERSION File**: Static file for quick version access
- **package.json**: npm distribution version (synchronized)

#### Version Scripts
1. **manage_version.py**: Core version management script
   - Uses setuptools-scm for git-based versioning
   - Implements conventional commit parsing
   - Handles changelog generation
   - Supports automatic and manual version bumping

2. **release.py**: Unified release automation
   - Orchestrates complete release workflow
   - Ensures PyPI/npm version synchronization
   - Handles multi-channel distribution
   - Provides rollback guidance

3. **check_version_sync.py**: Version synchronization checker
   - Verifies consistency across version files
   - Used in CI/CD pipelines
   - Prevents version mismatches

### 2. Semantic Versioning Implementation

#### Version Format
```
MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]
```

- **MAJOR**: Breaking API changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)
- **PRERELEASE**: Optional (alpha, beta, rc)
- **BUILD**: Optional metadata (ignored in comparisons)

#### Development Versions
Between releases, versions include commit information:
```
1.2.3.post4+g1234567[.dirty]
```
- `.postN`: N commits since last tag
- `+gHASH`: Git commit hash
- `.dirty`: Uncommitted changes present

### 3. Conventional Commits Integration

#### Commit Format
```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

#### Version Bump Mapping
- `feat:` → MINOR version bump
- `fix:` → PATCH version bump
- `perf:` → PATCH version bump
- `BREAKING CHANGE:` or `feat!:` → MAJOR version bump
- Other types → No automatic bump

### 4. Release Automation Workflow

#### Pre-Release Phase
1. **Working Directory Check**: Ensure clean git state
2. **Branch Verification**: Confirm on main branch
3. **Version Sync Check**: Verify PyPI/npm alignment
4. **Test Suite Execution**: Run all tests

#### Version Update Phase
1. **Analyze Commits**: Determine bump type from conventional commits
2. **Bump Version**: Update version using semantic rules
3. **Update VERSION File**: Maintain static version reference
4. **Generate Changelog**: Create entry from commits
5. **Update package.json**: Synchronize npm version
6. **Commit Changes**: Stage and commit version updates
7. **Create Git Tag**: Annotated tag with version

#### Distribution Phase
1. **Build Packages**: Create wheel and source distributions
2. **Publish to PyPI**: Upload Python packages
3. **Publish to npm**: Upload npm wrapper package
4. **Create GitHub Release**: Generate release with changelog
5. **Verify Availability**: Check package accessibility

### 5. Git Hooks Integration

#### Pre-Commit Hook
- **Purpose**: Keep VERSION file synchronized with git state
- **Process**:
  1. Detect current version via setuptools-scm
  2. Compare with VERSION file
  3. Update if different
  4. Stage changes automatically
- **Benefits**: Prevents version desynchronization

### 6. Version Synchronization Strategy

#### Multi-Channel Consistency
- **Python (PyPI)**: Uses VERSION file as canonical source
- **Node.js (npm)**: package.json synchronized during release
- **Git**: Tags provide historical version tracking
- **Documentation**: Automated changelog generation

#### Synchronization Points
1. **Pre-commit hook**: Updates VERSION file
2. **Release script**: Updates package.json
3. **Version check**: Validates all sources match

### 7. Agent Version Management

#### Agent Versioning System
- **Format**: Semantic versioning (2.1.0)
- **Storage**: Agent template JSON files
- **Migration**: Automatic from old formats (serial, integer)

#### Version Migration Examples
- `0002-0005` → `2.1.0` (serial format)
- `5` → `2.1.0` (integer format)
- Missing version → `1.0.0` (default)

#### Deployment Triggers
1. Template version > deployed version
2. Old format detected (triggers migration)
3. Force rebuild flag used
4. Base agent version changed

### 8. Version Compatibility and Migration

#### Backward Compatibility
- Supports manual version management
- Handles missing git tags gracefully
- Provides sensible defaults
- Works in non-git environments

#### Forward Compatibility
- CI/CD ready automation
- Extensible for new version sources
- Plugin architecture for custom workflows
- API-first design

### 9. Error Handling and Recovery

#### Common Issues and Solutions

1. **Version Mismatch**
   - Detection: check_version_sync.py
   - Resolution: release.py auto-synchronizes
   - Prevention: Pre-commit hooks

2. **Failed Release**
   - PyPI: Cannot delete, use yanking
   - npm: Deprecate and publish fix
   - Git: Tags are immutable

3. **Development Versions**
   - Handled by setuptools-scm
   - Cleaned during release
   - Visible in VERSION file

### 10. Best Practices

#### Development Workflow
1. Use conventional commits consistently
2. Enable git hooks: `git config core.hooksPath .githooks`
3. Run version checks before releases
4. Review changelog entries

#### Release Workflow
1. Always use release.py for releases
2. Test with --dry-run first
3. Verify package availability post-release
4. Document any manual interventions

#### Version Management
1. Never edit VERSION file manually
2. Use semantic versioning strictly
3. Tag all releases in git
4. Keep changelog updated

## Command Reference

### Version Checking
```bash
# Check current version
./scripts/manage_version.py check

# Verify version synchronization
./scripts/check_version_sync.py
```

### Version Bumping
```bash
# Automatic bump based on commits
./scripts/manage_version.py auto

# Manual version bump
./scripts/manage_version.py bump --bump-type minor
```

### Release Process
```bash
# Dry run release
./scripts/release.py patch --dry-run

# Execute release
./scripts/release.py minor

# Test release with TestPyPI
./scripts/release.py patch --test-pypi
```

### Agent Version Management
```bash
# Deploy agents with version updates
claude-mpm agents deploy

# Verify agent versions
claude-mpm agents verify

# Force version migration
claude-mpm agents deploy --force-rebuild
```

## Version File Locations

| File | Purpose | Format | Updated By |
|------|---------|--------|------------|
| VERSION | Python/PyPI version | X.Y.Z | manage_version.py, git hooks |
| package.json | npm version | "version": "X.Y.Z" | release.py |
| Git tags | Version history | vX.Y.Z | manage_version.py |
| Agent JSONs | Agent versions | "agent_version": "X.Y.Z" | Deployment system |

## Integration Points

### CI/CD Integration
- Version detection from git tags
- Automated changelog generation
- Multi-platform distribution
- Version validation checks

### Development Tools
- Pre-commit hooks for version sync
- IDE integration via VERSION file
- Build system integration
- Test framework version checks

## Troubleshooting Guide

### Version Not Updating
1. Check git hooks enabled
2. Verify setuptools-scm installed
3. Ensure git tags pushed
4. Run manual version sync

### Release Failures
1. Check credentials (PyPI, npm)
2. Verify version uniqueness
3. Ensure clean working directory
4. Review error logs

### Version Mismatches
1. Run check_version_sync.py
2. Use release.py for fixes
3. Check git hook configuration
4. Verify all files committed

## Future Enhancements

### Planned Improvements
1. Automated security scanning integration
2. Multi-branch version management
3. Beta/RC channel automation
4. Version rollback automation
5. Enhanced CI/CD templates

### Extension Points
- Custom version bump rules
- Additional file format support
- Plugin system for version sources
- API for version queries

This comprehensive version management system ensures Claude MPM maintains consistent, predictable versioning across all distribution channels while supporting both automated and manual workflows.