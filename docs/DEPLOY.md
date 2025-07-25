# Deployment Guide

This guide covers versioning, building, and deploying Claude MPM to various distribution channels.

## Version Management

Claude MPM uses automated semantic versioning based on git tags. See [VERSIONING.md](./VERSIONING.md) for detailed version management.

### Quick Version Commands

```bash
# Check current version
./scripts/manage_version.py check

# Auto-bump version based on commits
./scripts/manage_version.py auto

# Manual version bump
./scripts/manage_version.py bump --bump-type minor
```

## Release Process

### 1. Prepare Release

```bash
# Ensure clean working directory
git status

# Run tests
./scripts/run_all_tests.sh

# Update version and changelog
./scripts/manage_version.py auto

# Review changes
git show HEAD
cat CHANGELOG.md
```

### 2. Push Release

```bash
# Push commits and tags
git push origin main
git push origin --tags
```

### 3. Build Distributions

```bash
# Clean previous builds
rm -rf dist/ build/

# Build Python package
python -m build

# Verify build
ls -la dist/
```

## Distribution Channels

### PyPI Deployment

```bash
# Test deployment (TestPyPI)
python -m twine upload --repository testpypi dist/*

# Production deployment
python -m twine upload dist/*
```

**Configuration** (`.pypirc`):
```ini
[pypi]
username = __token__
password = pypi-YOUR-TOKEN-HERE

[testpypi]
username = __token__
password = pypi-TEST-TOKEN-HERE
```

### npm Deployment

```bash
# Update package.json version (automated via script)
npm version $(cat VERSION)

# Publish to npm
npm publish

# Tag as latest
npm dist-tag add claude-mpm@$(cat VERSION) latest
```

### Local Installation

```bash
# Development install
pip install -e .

# Production install from source
pip install .

# Install from PyPI
pip install claude-mpm
```

### GitHub Release

1. Go to [GitHub Releases](https://github.com/yourusername/claude-mpm/releases)
2. Click "Draft a new release"
3. Select the version tag (e.g., `v0.5.0`)
4. Title: `Claude MPM v0.5.0`
5. Copy changelog entry for description
6. Attach distribution files from `dist/`
7. Publish release

## Post-Deployment Verification

### 1. PyPI Verification

```bash
# Check PyPI page
open https://pypi.org/project/claude-mpm/

# Test installation
pip install --upgrade claude-mpm
claude-mpm --version
```

### 2. npm Verification

```bash
# Check npm page
open https://www.npmjs.com/package/claude-mpm

# Test installation
npm install -g claude-mpm
claude-mpm --version
```

### 3. Functional Testing

```bash
# Test basic functionality
claude-mpm --help

# Test with logging
claude-mpm --logging DEBUG -i "test task" --non-interactive

# Verify agents
claude-mpm agents list
```

## Deployment Checklist

- [ ] All tests passing (`./scripts/run_all_tests.sh`)
- [ ] Version bumped (`./scripts/manage_version.py auto`)
- [ ] CHANGELOG.md updated
- [ ] Git tag created and pushed
- [ ] Python package built (`python -m build`)
- [ ] PyPI deployment successful
- [ ] npm deployment successful (if applicable)
- [ ] GitHub release created
- [ ] Post-deployment verification completed
- [ ] Documentation updated if needed

## Rollback Procedure

If issues are discovered after deployment:

### PyPI Rollback

```bash
# Cannot delete, but can yank a release
pip install twine
twine yank claude-mpm==0.5.0

# Upload fixed version with higher number
./scripts/manage_version.py bump --bump-type patch
python -m build
twine upload dist/*
```

### npm Rollback

```bash
# Deprecate broken version
npm deprecate claude-mpm@0.5.0 "Critical bug, use 0.5.1"

# Publish fixed version
npm version patch
npm publish
```

## Automated Deployment (CI/CD)

### GitHub Actions Example

Create `.github/workflows/release.yml`:

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0  # Need full history for setuptools-scm
          
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          
      - name: Install dependencies
        run: |
          pip install build twine
          
      - name: Build package
        run: python -m build
        
      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }}
        run: twine upload dist/*
        
      - name: Create GitHub Release
        uses: softprops/action-gh-release@v1
        with:
          files: dist/*
          body_path: CHANGELOG.md
```

## Version Information Display

Version is automatically shown in:
- CLI: `claude-mpm --version`
- Interactive mode startup banner
- Log files (session metadata)
- Python: `import claude_mpm; print(claude_mpm.__version__)`

## Troubleshooting

### Version Mismatch
- Ensure `git fetch --tags` to get all tags
- Run `./scripts/manage_version.py check`
- Verify VERSION file matches git tag

### Build Failures
- Clear build directories: `rm -rf build/ dist/ *.egg-info`
- Ensure setuptools-scm installed: `pip install setuptools-scm`
- Check for uncommitted changes (causes .dirty suffix)

### Upload Failures
- Verify PyPI/npm credentials
- Check network connectivity
- Ensure unique version number

## Security Considerations

1. **API Tokens**: Never commit tokens to repository
2. **2FA**: Enable on PyPI and npm accounts
3. **GPG Signing**: Sign git tags for releases
4. **SBOM**: Consider generating Software Bill of Materials

## Related Documentation

- [VERSIONING.md](./VERSIONING.md) - Detailed version management
- [CHANGELOG.md](../CHANGELOG.md) - Release history
- [QA.md](./QA.md) - Testing procedures
- [STRUCTURE.md](./STRUCTURE.md) - Project organization