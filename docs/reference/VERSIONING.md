# Version Management Guide

Claude MPM uses automated semantic versioning based on git tags and conventional commits.

## Overview

The project uses `setuptools-scm` for automatic version detection from git, which means:
- Version is derived from git tags (format: `v1.0.0`)
- Between releases, versions include commit count: `1.0.0.post2+g1234567`
- Dirty working directories add `.dirty` suffix
- No manual version updates needed in code

Claude MPM implements a sophisticated version management system that ensures consistency across multiple distribution channels (PyPI, npm, GitHub) while supporting both automated and manual release workflows.

## Version Sources

1. **Primary**: Git tags (managed by setuptools-scm) - Ultimate source of truth
2. **Canonical**: `VERSION` file (semantic version only, e.g., "3.9.5")
3. **Build Tracking**: `BUILD_NUMBER` file (serial build number, e.g., "275")
4. **Runtime**: `src/claude_mpm/_version.py` (auto-generated)
5. **Package**: `pyproject.toml` uses dynamic versioning
6. **npm Distribution**: `package.json` (synchronized during releases)

### Dual Tracking System (v3.9.5+)

As of v3.9.5, Claude MPM implements a dual tracking system:
- **VERSION**: Semantic version for releases (3.9.5)
- **BUILD_NUMBER**: Serial build counter for every code change (275)
- **Combined Display**: Three format variants:
  - Development: `3.9.5+build.275` (PEP 440 compliant for Python packages)
  - UI/Logging: `v3.9.5-build.275` (user-friendly display)
  - PyPI Release: `3.9.5` (clean semantic version for releases)

## Version Management Script

Use `scripts/manage_version.py` for version operations:

### Check Current Version
```bash
./scripts/manage_version.py check
```

### Build Number Management
```bash
# Check current build number
cat BUILD_NUMBER

# Check if build increment is needed
python scripts/increment_build.py --check-only

# Force build increment
python scripts/increment_build.py --force

# Install git hook for automatic build increments
./scripts/install_git_hook.sh
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
# Minor version bump (1.0.0 → 1.1.0)
git commit -m "feat(agents): add new data analysis agent"

# Patch version bump (1.0.0 → 1.0.1)
git commit -m "fix(logging): correct session duration calculation"

# Major version bump (1.0.0 → 2.0.0)
git commit -m "feat!: redesign agent communication protocol

BREAKING CHANGE: Agent API has changed, update all custom agents"
```

## Version Management Scripts

### Core Scripts
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

### 5. Build and Publish

#### Automated Release (Recommended)
```bash
# Full release workflow with all checks
./scripts/release.py

# Dry run to preview changes
./scripts/release.py --dry-run
```

The release script handles:
- Pre-release validation
- Version synchronization
- Package building
- PyPI and npm publishing
- GitHub release creation
- Post-release verification

#### Manual Release
```bash
# Build package
python -m build

# Publish to PyPI
python -m twine upload dist/*

# Publish to npm (if applicable)
npm publish
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

Version is shown in multiple places with build numbers (v3.9.5+):
- CLI: `claude-mpm --version` → `claude-mpm v3.9.5-build.275`
- Interactive mode: Startup banner → `Version v3.9.5-build.275`
- Logs: Session metadata → `v3.9.5-build.275`
- Package: `claude_mpm.__version__` → `3.9.5+build.275` (PEP 440)
- Development: `3.9.5+build.275` (for dependency resolution)
- PyPI Release: `3.9.5` (clean version for public releases)

## Troubleshooting

### Version Shows as 0.0.0
- No git tags exist
- Not in a git repository
- setuptools-scm not installed

### Version Shows .dirty Suffix
- Uncommitted changes in working directory
- Commit or stash changes for clean version

### Tag Not Recognized
- Ensure tag format is `v1.0.0` (with 'v' prefix)
- Push tags to remote: `git push --tags`

### Different Versions in Different Places
- Run `./scripts/manage_version.py check` to diagnose
- Ensure pre-commit hook is enabled for VERSION file
- Ensure git hook is installed for BUILD_NUMBER: `./scripts/install_git_hook.sh`
- Check both VERSION and BUILD_NUMBER files are current
- Manually sync with files if needed

## Development Versions

With the dual tracking system (v3.9.5+), development versions show:
```
3.9.5+build.275[.dirty]
```
- `3.9.5`: Current semantic version
- `build.275`: Build number (increments with each code change)
- `.dirty`: Uncommitted changes present

Legacy format (pre-v3.9.5) included commit information:
```
1.2.3.post4+g1234567[.dirty]
```
- `.postN`: N commits since last tag
- `+gHASH`: Git commit hash
- `.dirty`: Uncommitted changes present

## Release Automation Workflow

### Pre-Release Phase
1. **Working Directory Check**: Ensure clean git state
2. **Branch Verification**: Confirm on main branch
3. **Version Sync Check**: Verify PyPI/npm alignment
4. **Test Suite Execution**: Run all tests

### Version Update Phase
1. **Analyze Commits**: Determine bump type from conventional commits
2. **Bump Version**: Update version using semantic rules
3. **Update VERSION File**: Maintain static version reference
4. **Generate Changelog**: Create entry from commits
5. **Update package.json**: Synchronize npm version
6. **Commit Changes**: Stage and commit version updates
7. **Create Git Tag**: Annotated tag with version

### Distribution Phase
1. **Build Packages**: Create wheel and source distributions
2. **Publish to PyPI**: Upload Python packages
3. **Publish to npm**: Upload npm wrapper package
4. **Create GitHub Release**: Generate release with changelog
5. **Verify Availability**: Check package accessibility

## Best Practices

1. **Use Conventional Commits**: Enables automatic version determination
2. **Tag Releases**: Always tag releases with `v` prefix
3. **Keep Changelog Updated**: Run version script to auto-generate entries
4. **Review Before Release**: Use `--dry-run` to preview changes
5. **Sync After Clone**: Run `git fetch --tags` to get all version tags
6. **Version Consistency**: Always use release.py for multi-channel releases
7. **Pre-release Testing**: Run full test suite before releases

## Agent Version Management

Claude MPM uses semantic versioning for agent templates, providing a standardized and predictable versioning system.

### Agent Version Format

Agent versions follow semantic versioning (major.minor.patch):
- **Format**: `2.1.0`
- **Major**: Breaking changes to agent behavior or API
- **Minor**: New capabilities or enhancements
- **Patch**: Bug fixes or minor improvements

### Version Storage

Agent versions are stored in the template JSON files:
```json
{
  "schema_version": "1.0.0",
  "agent_id": "research_agent",
  "agent_version": "2.1.0",  // Semantic version
  "metadata": {
    "name": "Research Agent",
    "updated_at": "2025-07-27T10:30:00.000000Z"
  }
}
```

### Automatic Version Migration

The agent deployment system automatically detects and migrates agents from old version formats:

#### Old Formats Detected
1. **Serial format**: `0002-0005` (base-agent versions)
2. **Missing version**: No version field in YAML frontmatter
3. **Integer format**: Simple integer versions like `5`
4. **Separate fields**: `agent_version: 5` in metadata

#### Migration Process
When old formats are detected:
1. System logs the detection of old format
2. Converts to semantic version (e.g., `5` → `2.1.0`)
3. Updates the deployed agent file automatically
4. Reports migration in deployment results

### Version Comparison

The system uses tuple-based semantic version comparison:
```python
# Version comparison examples
(2, 1, 0) > (2, 0, 0)  # True (newer minor version)
(2, 1, 0) > (1, 9, 9)  # True (newer major version)
(2, 1, 1) > (2, 1, 0)  # True (newer patch version)
```

### Deployment Behavior

Agents are redeployed when:
1. **Version increase**: Template version > deployed version
2. **Format migration**: Old format detected (automatic migration)
3. **Force flag**: `--force-rebuild` option used
4. **Base version update**: Base agent template updated

### Version Display

Agent versions are shown in:
- Deployed agent YAML frontmatter
- `claude-mpm agents list` command output
- Deployment verification reports
- Agent metadata fields

### Updating Agent Versions

To update an agent version:

1. **Edit template JSON**:
   ```json
   {
     "agent_version": "2.2.0",  // Increment version
     "metadata": {
       "updated_at": "2025-07-27T12:00:00.000000Z"
     }
   }
   ```

2. **Deploy agents**:
   ```bash
   # Deploy with automatic migration
   claude-mpm agents deploy
   
   # Force rebuild all agents
   claude-mpm agents deploy --force-rebuild
   ```

3. **Verify deployment**:
   ```bash
   claude-mpm agents verify
   ```

### Migration Command

To explicitly migrate agents to semantic versioning:
```bash
# Check for agents needing migration
claude-mpm agents verify

# Deploy (includes automatic migration)
claude-mpm agents deploy

# Force migration of all agents
claude-mpm agents deploy --force-rebuild
```