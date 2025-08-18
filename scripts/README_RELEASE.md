# Release Scripts

This directory contains scripts related to the release process.

## release_workflow.sh

A comprehensive helper script for managing releases.

### Quick Start

```bash
# Check if ready for release
./scripts/release_workflow.sh check

# View current changelog
./scripts/release_workflow.sh changelog

# Validate commit messages
./scripts/release_workflow.sh validate

# Prepare a release (requires commitizen)
./scripts/release_workflow.sh prepare [patch|minor|major]
```

### Features

- **check**: Validates release readiness
  - Checks for uncommitted changes
  - Verifies version consistency
  - Validates changelog format
  - Checks for existing tags

- **changelog**: Views current changelog entries
  - Shows [Unreleased] section content
  - Displays latest release notes

- **validate**: Checks commit message format
  - Validates conventional commit format
  - Shows which commits will trigger version bumps

- **prepare**: Creates a new release
  - Runs commitizen to bump version
  - Updates all version files
  - Moves [Unreleased] content to new version
  - Creates commit and tag

## Related Documentation

- [Release Process](../docs/RELEASE_PROCESS.md) - Complete release documentation
- [CHANGELOG.md](../CHANGELOG.md) - Project changelog
- [Structure Linting](../docs/STRUCTURE_LINTING.md) - Includes changelog validation