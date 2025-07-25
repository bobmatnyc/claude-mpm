# Deployment Guide

This guide covers versioning, building, and deploying Claude MPM to various distribution channels.

## Local Development Deployment

For local development and testing, use the enhanced deployment script:

```bash
# Basic installation
./scripts/deploy_local.sh

# Force reinstallation (skip prompts)
./scripts/deploy_local.sh --force

# View help
./scripts/deploy_local.sh --help
```

The enhanced deployment script provides:
- **Automatic virtual environment setup** - Creates or updates venv with correct Python version
- **Smart reinstallation** - Detects existing installations and offers to update
- **PATH configuration** - Automatically adds `~/.local/bin` to PATH if needed
- **Shell aliases** - Creates convenient shortcuts like `mpm` for `claude-mpm`
- **Comprehensive verification** - Tests all imports and commands after installation
- **Multi-shell support** - Works with bash and zsh, detects shell type automatically

### Quick Start After Installation

```bash
# Using the wrapper (recommended - auto-activates venv)
./claude-mpm                      # Interactive mode
./claude-mpm run -i "Your prompt" # Non-interactive mode

# Using global command (if PATH is set up)
claude-mpm agents                 # List available agents
claude-mpm --debug run -i "Test"  # Run with debug output

# Using aliases (if configured)
mpm                              # Short for claude-mpm
mpm-run -i "Your prompt"         # Run command
mpm-debug                        # Run with debug enabled
```

### Alternative: Basic Installation

If you prefer a simpler installation without the enhanced features:

```bash
# Use the basic install script
./install.sh
```

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

### Unified Release Script (Recommended)

The easiest way to release Claude MPM is using the unified release script that handles all aspects of the release:

```bash
# Dry run to see what will happen
./scripts/release.py patch --dry-run

# Release a patch version
./scripts/release.py patch

# Release a minor version
./scripts/release.py minor

# Release a major version
./scripts/release.py major

# Test with TestPyPI first
./scripts/release.py patch --test-pypi

# Skip tests (emergency release only)
./scripts/release.py patch --skip-tests
```

The unified release script will:
1. Run pre-release checks (clean working directory, correct branch)
2. Run the test suite
3. Bump the version using semantic versioning
4. **Automatically synchronize package.json version with Python version**
5. Commit and tag the changes
6. Build Python distributions
7. Publish to PyPI (or TestPyPI)
8. Publish to npm registry as @bobmatnyc/claude-mpm
9. Create a GitHub release with changelog
10. Verify package availability on both PyPI and npm

**Important Notes:**
- The script ensures npm and PyPI versions are always synchronized
- Use `--dry-run` to preview all changes before executing
- Version synchronization can be verified anytime with `./scripts/check_version_sync.py`
- The script will abort if versions are already out of sync (run check_version_sync.py first)

### Manual Release Process

If you need to release manually, follow these steps:

#### 1. Prepare Release

```bash
# Ensure clean working directory
git status

# Check version synchronization
./scripts/check_version_sync.py

# Run tests
./scripts/run_all_tests.sh

# Update version and changelog
./scripts/manage_version.py auto

# Update package.json version to match
npm version $(cat VERSION) --no-git-tag-version

# Review changes
git show HEAD
cat CHANGELOG.md
```

#### 2. Push Release

```bash
# Push commits and tags
git push origin main
git push origin --tags
```

#### 3. Build Distributions

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

#### Project-Specific Installation

For installing Claude MPM within a specific project's virtual environment:

```bash
# Development install (editable mode)
pip install -e .

# Production install from source
pip install .

# Install from PyPI
pip install claude-mpm

# Install specific version
pip install claude-mpm==1.0.0
```

#### Global Installation for All Projects

For system-wide availability across all projects, use pipx or the provided Makefile:

**Using pipx (Recommended for Users):**
```bash
# Install pipx if not already installed
python3 -m pip install --user pipx
python3 -m pipx ensurepath

# Install Claude MPM globally from PyPI
pipx install claude-mpm

# Or install from local source
pipx install .
```

**Using Makefile (Automated Setup):**

For developers working on claude-mpm:
```bash
# Development installation (RECOMMENDED FOR DEVELOPERS)
make install-dev

# This will:
# - Create a virtual environment in ~/.claude-mpm/
# - Install Claude MPM in editable mode (pip install -e .)
# - Set up the shell wrapper function
# - Configure PATH and shell integration
# - Your local code changes will be reflected immediately
```

For users who want the stable PyPI version:
```bash
# Production installation from PyPI
make install

# This will:
# - Create a virtual environment in ~/.claude-mpm/
# - Install Claude MPM from PyPI (latest stable version)
# - Set up the shell wrapper function
# - Configure PATH and shell integration
```

**Important Note for Developers:**
- Use `make install-dev` to work with your local code changes
- Changes to your source code will be immediately available without reinstalling
- Use `make install` only if you specifically want the published PyPI version

**Manual Shell Wrapper Setup:**

Add this function to your shell configuration (`~/.bashrc`, `~/.zshrc`, etc.):

```bash
claude-mpm() {
    if [ -f "$HOME/.claude-mpm/venv/bin/activate" ]; then
        source "$HOME/.claude-mpm/venv/bin/activate"
        command claude-mpm "$@"
        deactivate
    else
        echo "Claude MPM not found. Run 'make install' from the project directory."
        return 1
    fi
}
```

**Benefits of Global Installation:**
- Available in any directory without activation
- Isolated from project dependencies
- Automatic virtual environment management
- Clean PATH with single entry point
- Easy updates via `pipx upgrade claude-mpm`

**Quick Start After Global Installation:**
```bash
# From any directory
claude-mpm --help
claude-mpm agents list
claude-mpm run -i "Your task here" --non-interactive
```

### GitHub Release

1. Go to [GitHub Releases](https://github.com/yourusername/claude-mpm/releases)
2. Click "Draft a new release"
3. Select the version tag (e.g., `v1.0.0`)
4. Title: `Claude MPM v1.0.0`
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

When using the unified release script (`./scripts/release.py`), all items are handled automatically:

- [ ] All tests passing (`./scripts/run_all_tests.sh`)
- [ ] Version bumped (`./scripts/manage_version.py auto`)
- [ ] package.json version synchronized
- [ ] CHANGELOG.md updated
- [ ] Git tag created and pushed
- [ ] Python package built (`python -m build`)
- [ ] PyPI deployment successful
- [ ] npm deployment successful
- [ ] GitHub release created
- [ ] Post-deployment verification completed
- [ ] Documentation updated if needed

For manual releases, check each item individually.

## Rollback Procedure

If issues are discovered after deployment:

### PyPI Rollback

```bash
# Cannot delete, but can yank a release
pip install twine
twine yank claude-mpm==1.0.0

# Upload fixed version with higher number
./scripts/manage_version.py bump --bump-type patch
python -m build
twine upload dist/*
```

### npm Rollback

```bash
# Deprecate broken version
npm deprecate claude-mpm@1.0.0 "Critical bug, use 1.0.1"

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