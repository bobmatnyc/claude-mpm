# Deployment Guide

This guide covers versioning, building, and deploying Claude MPM to various distribution channels.

## Overview

Claude MPM uses a **Make-based release system** that provides:

- ✅ **One-command releases** - `make release-patch` handles everything
- ✅ **Multi-channel publishing** - PyPI, npm, and GitHub simultaneously
- ✅ **Version synchronization** - All version files kept in sync automatically
- ✅ **Safety checks** - Prerequisites, tests, and confirmations
- ✅ **Incremental builds** - Only rebuilds what's necessary
- ✅ **Standard tooling** - Uses Make, commitizen, and GitHub CLI

**Quick Start:**
```bash
make release-patch      # Bug fix release
make release-publish    # Publish to all channels
```

See the [Release Process](#release-process) section for complete details.

## Local Development Deployment

This section covers setting up claude-mpm for local development, making it accessible from anywhere on your system.

### Quick Start with Enhanced Deployment Script

The recommended way to set up claude-mpm for local development is using the enhanced deployment script:

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

### Running Claude MPM After Installation

Once installed, you have several ways to run claude-mpm:

#### 1. Using the Project Wrapper (Recommended for Development)
```bash
# From the project directory - auto-activates venv
./claude-mpm                      # Interactive mode
./claude-mpm run -i "Your prompt" # Non-interactive mode
./claude-mpm agents list          # List available agents
```

#### 2. Using Global Command (After PATH Setup)
```bash
# From anywhere on your system
claude-mpm                        # Interactive mode
claude-mpm agents                 # List available agents
claude-mpm --debug run -i "Test"  # Run with debug output
claude-mpm --logging INFO         # Run with specific log level
```

#### 3. Using Shell Aliases (If Configured)
```bash
# Short aliases for common commands
mpm                              # Short for claude-mpm
mpm-run -i "Your prompt"         # Run command
mpm-debug                        # Run with debug enabled
mpm-agents                       # List agents
```

### Manual Installation Steps

If you prefer manual installation or need to understand what the script does:

#### Step 1: Create and Activate Virtual Environment
```bash
# Create virtual environment
python3 -m venv venv

# Activate it (bash/zsh)
source venv/bin/activate

# Activate it (fish shell)
source venv/bin/activate.fish

# Activate it (Windows PowerShell)
venv\Scripts\Activate.ps1
```

#### Step 2: Install Claude MPM
```bash
# Development install (editable mode - recommended for developers)
pip install -e .

# Or production install
pip install .
```

#### Step 3: Configure PATH (Optional but Recommended)
```bash
# Add to ~/.bashrc or ~/.zshrc
export PATH="$HOME/.local/bin:$PATH"

# For fish shell (~/.config/fish/config.fish)
set -gx PATH $HOME/.local/bin $PATH

# Reload shell configuration
source ~/.bashrc  # or ~/.zshrc
```

#### Step 4: Create Shell Aliases (Optional)
```bash
# Add to ~/.bashrc or ~/.zshrc
alias mpm='claude-mpm'
alias mpm-run='claude-mpm run'
alias mpm-debug='claude-mpm --debug'
alias mpm-agents='claude-mpm agents list'

# Reload shell configuration
source ~/.bashrc  # or ~/.zshrc
```

### Virtual Environment Activation for Different Shells

When working with the project directly, you'll need to activate the virtual environment:

#### Bash/Zsh
```bash
source venv/bin/activate
# To deactivate
deactivate
```

#### Fish Shell
```fish
source venv/bin/activate.fish
# To deactivate
deactivate
```

#### Windows Command Prompt
```cmd
venv\Scripts\activate.bat
# To deactivate
deactivate
```

#### Windows PowerShell
```powershell
venv\Scripts\Activate.ps1
# To deactivate
deactivate
```

### Troubleshooting Common Issues

#### "command not found" Error
```bash
# Check if claude-mpm is in PATH
which claude-mpm

# If not found, ensure PATH is set correctly
echo $PATH | grep -q "$HOME/.local/bin" || echo "PATH not configured"

# Quick fix - add to current session
export PATH="$HOME/.local/bin:$PATH"

# Permanent fix - add to shell config
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

#### Virtual Environment Issues
```bash
# Check if venv exists and is activated
echo $VIRTUAL_ENV

# Recreate venv if corrupted
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

#### Import Errors
```bash
# Ensure proper installation
pip show claude-mpm

# Reinstall if needed
pip uninstall claude-mpm -y
pip install -e .

# Verify PYTHONPATH includes src/
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

#### Permission Errors
```bash
# If installing globally without sudo
pip install --user claude-mpm

# Or use pipx for isolated global install
pipx install claude-mpm
```

### Alternative: Basic Installation Script

For a simpler installation without the enhanced features:

```bash
# Use the basic install script
./install.sh
```

This script performs a minimal installation without PATH configuration or shell aliases.

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

### Make-Based Release System (Recommended)

Claude MPM uses a comprehensive Make-based release system that integrates with existing build tools and provides a streamlined workflow. This replaces the previous Python script approach with faster, more reliable Make targets.

#### Quick Start

```bash
# Most common: patch release (bug fixes)
make release-patch

# After review, publish the release
make release-publish

# Or do both in one step
make release-full
```

#### Release Types

**Patch Release (Bug Fixes)**
```bash
make release-patch    # 4.0.4 → 4.0.5
```

**Minor Release (New Features)**
```bash
make release-minor    # 4.0.4 → 4.1.0
```

**Major Release (Breaking Changes)**
```bash
make release-major    # 4.0.4 → 5.0.0
```

#### Complete Workflow

**1. Preparation**
```bash
# Check if environment is ready
make release-check

# Run tests
make release-test

# Preview what would happen (dry run)
make release-dry-run
```

**2. Create Release**
```bash
# Choose one based on your changes
make release-patch   # Bug fixes
make release-minor   # New features
make release-major   # Breaking changes
```

This will:
- ✅ Check prerequisites (git, python, cz, gh)
- ✅ Verify clean working directory
- ✅ Run test suite
- ✅ Bump version using commitizen
- ✅ Sync all version files (VERSION, src/claude_mpm/VERSION, package.json)
- ✅ Build Python package
- ✅ Prepare for publishing

**3. Publish Release**
```bash
make release-publish
```

This will:
- 📤 Publish to PyPI
- 📤 Publish to npm as @bobmatnyc/claude-mpm
- 🏷️ Create GitHub release with changelog
- 🔍 Show verification links

**4. Verify Release**
```bash
make release-verify
```

#### Testing and Safety

```bash
# Test on TestPyPI first
make release-test-pypi

# See what would happen without making changes
make release-dry-run

# Get help on all release targets
make release-help
```

#### Prerequisites

The release system requires these tools:

- **git** - Version control
- **python** - Python interpreter
- **cz** (commitizen) - Version bumping and changelog
- **gh** (GitHub CLI) - GitHub releases
- **twine** - PyPI publishing (optional)
- **npm** - npm publishing (optional)

Install missing tools:
```bash
# Commitizen
pip install commitizen

# GitHub CLI
# macOS: brew install gh
# Other: https://cli.github.com/

# Twine
pip install twine
```

#### Advantages of Make-Based System

- ✅ **Faster** - No Python startup overhead
- ✅ **Simpler** - Standard Make syntax
- ✅ **Integrated** - Works with existing Makefile
- ✅ **Incremental** - Only runs necessary steps
- ✅ **Parallel** - Can run independent tasks in parallel
- ✅ **Universal** - Make is available everywhere

#### Version Synchronization

The release system automatically synchronizes versions across:

- `VERSION` (root file - primary source)
- `src/claude_mpm/VERSION` (package distribution)
- `package.json` (npm package)
- `pyproject.toml` (commitizen tracking)

**Important Notes:**
- All version files are kept in perfect sync automatically
- Use `make release-check` to verify environment readiness
- Use `make release-dry-run` to preview changes before executing
- The system will abort if working directory is not clean

### Legacy Release Script (Deprecated)

The previous Python-based release script (`./scripts/release.py`) is still available but deprecated in favor of the Make-based system. The Make targets provide the same functionality with better performance and integration.

### Manual Release Process (Advanced)

If you need to release manually or understand the individual steps, you can run them separately:

#### 1. Prepare Release

```bash
# Check prerequisites and environment
make release-check

# Run test suite
make release-test

# Manually bump version using commitizen
cz bump --patch  # or --minor, --major

# Sync version files
make release-sync-versions

# Review changes
git show HEAD
cat CHANGELOG.md
```

#### 2. Build and Publish

```bash
# Build Python package
make release-build

# Publish to PyPI
python -m twine upload dist/*

# Publish to npm (optional)
npm publish

# Create GitHub release
VERSION=$(cat VERSION)
gh release create "v$VERSION" \
  --title "Claude MPM v$VERSION" \
  --notes-from-tag \
  dist/*
```

#### 3. Verify Release

```bash
# Show verification links
make release-verify

# Test installation
pip install --upgrade claude-mpm
claude-mpm --version
```

#### Individual Make Targets

For granular control, use individual targets:

```bash
make release-check          # Check prerequisites
make release-test           # Run test suite
make release-build          # Build package only
make release-sync-versions  # Sync version files
make release-verify         # Show verification links
```

## Distribution Channels

Claude MPM is distributed via both PyPI and npm to provide flexible installation options for different user environments.

### Dual Distribution Strategy

Claude MPM follows a dual distribution strategy:
- **PyPI**: Primary distribution channel for the Python package
- **npm**: Secondary distribution channel providing a wrapper that installs the Python package

The npm package (@bobmatnyc/claude-mpm) serves as a convenient wrapper that:
- Ensures Python is available on the system
- Installs the Python package from PyPI
- Provides the same CLI interface as the pip installation
- Maintains version synchronization with the PyPI package

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

The npm package is published as **@bobmatnyc/claude-mpm**:

```bash
# Update package.json version (automated via script)
npm version $(cat VERSION)

# Publish to npm
npm publish

# Tag as latest
npm dist-tag add @bobmatnyc/claude-mpm@$(cat VERSION) latest
```

**Important Notes:**
- The npm package name is scoped: `@bobmatnyc/claude-mpm`
- Version numbers are automatically synchronized between PyPI and npm
- The release.py script handles both PyPI and npm publishing

### Installation Options

Claude MPM can be installed via pip or npm, depending on your preference and environment:

#### Installing via pip (Recommended for Python developers)

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

#### Installing via npm (Alternative method)

For users who prefer npm or want a system-wide installation:

```bash
# Install from npm registry
npm install -g @bobmatnyc/claude-mpm

# Install specific version
npm install -g @bobmatnyc/claude-mpm@1.0.0

# Install locally in a project
npm install @bobmatnyc/claude-mpm
```

**Note**: The npm package automatically handles Python dependencies and provides the same `claude-mpm` command-line interface.

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
open https://www.npmjs.com/package/@bobmatnyc/claude-mpm

# Test installation
npm install -g @bobmatnyc/claude-mpm
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

When using the Make-based release system (`make release-patch/minor/major`), all items are handled automatically:

### Pre-Deployment Documentation Cleanup

**IMPORTANT: Complete documentation cleanup BEFORE starting the deployment process to ensure clean documentation is included in the release.**

- [ ] **Documentation Organization Audit**
  - [ ] Consolidate duplicate agent documentation (AGENTS.md and PROJECT_AGENTS.md should be merged)
  - [ ] Verify all files follow STRUCTURE.md naming conventions (no spaces, consistent casing)
  - [ ] Archive outdated content to `docs/archive/` directory
  - [ ] Remove deprecated "legacy format" references from all documentation
  - [ ] Ensure all numbered directories (`01-`, `02-`, etc.) have README.md index files
  
- [ ] **Documentation Content Validation**
  - [ ] Validate all internal documentation links work (no broken references)
  - [ ] Verify files are in correct directories per STRUCTURE.md guidelines
  - [ ] Update cross-references between documentation files
  - [ ] Check for redundant documentation (e.g., multiple deployment guides, duplicate QA reports)
  - [ ] Ensure consistency in terminology and formatting across all docs
  
- [ ] **Documentation Cleanup Script** (if available)
  - [ ] Run documentation audit script: `./scripts/audit_documentation.py` (create if doesn't exist)
  - [ ] Review audit report for any remaining issues
  - [ ] Address all critical documentation issues before proceeding

### Release Process

**Using Make-based system (Recommended):**

```bash
# Complete release workflow
make release-patch     # or release-minor/release-major
make release-publish   # or use release-full for both steps
```

**Automated checklist (handled by Make targets):**

- [ ] Prerequisites checked (`make release-check`)
- [ ] All tests passing (`make release-test`)
- [ ] Version bumped using commitizen (`cz bump`)
- [ ] All version files synchronized (`make release-sync-versions`)
- [ ] CHANGELOG.md updated (by commitizen)
- [ ] Git tag created and pushed (by commitizen)
- [ ] Python package built (`make release-build`)
- [ ] PyPI deployment successful (`make release-publish`)
- [ ] npm deployment successful (`make release-publish`)
- [ ] GitHub release created (`make release-publish`)
- [ ] Post-deployment verification completed (`make release-verify`)
- [ ] Documentation updated if needed

**Manual verification:**

- [ ] Check PyPI: https://pypi.org/project/claude-mpm/
- [ ] Check npm: https://www.npmjs.com/package/@bobmatnyc/claude-mpm
- [ ] Check GitHub: https://github.com/bobmatnyc/claude-mpm/releases
- [ ] Test installation: `pip install --upgrade claude-mpm`

For manual releases, use individual Make targets or check each item individually.

## Rollback Procedure

If issues are discovered after deployment:

### Quick Fix Release (Recommended)

```bash
# Create a patch release with the fix
make release-patch
make release-publish
```

This is the fastest way to address issues since you cannot delete published packages.

### Manual Rollback Steps

**PyPI Rollback:**
```bash
# Cannot delete, but can yank a release
pip install twine
twine yank claude-mpm==4.0.4 "Critical bug, use 4.0.5"

# Create fixed version using Make system
make release-patch      # Automatically bumps to 4.0.5
make release-publish    # Publishes fix
```

**npm Rollback:**
```bash
# Deprecate broken version
npm deprecate @bobmatnyc/claude-mpm@4.0.4 "Critical bug, use 4.0.5"

# Fixed version is published automatically by make release-publish
```

**GitHub Release:**
```bash
# Mark release as pre-release or draft
gh release edit v4.0.4 --prerelease

# Or delete the release (keeps the tag)
gh release delete v4.0.4
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

Version is automatically shown with build numbers (v3.9.5+):
- CLI: `claude-mpm --version` → `claude-mpm v3.9.5-build.275`
- Interactive mode: Startup banner → `Version v3.9.5-build.275`
- Log files: Session metadata → `v3.9.5-build.275`
- Python: `import claude_mpm; print(claude_mpm.__version__)` → `3.9.5+build.275`
- Development context: PEP 440 compliant format for dependencies
- Release context: Clean semantic version for PyPI

## Troubleshooting

### Version Mismatch
- Ensure `git fetch --tags` to get all tags
- Run `./scripts/manage_version.py check`
- Verify VERSION file matches git tag
- Check BUILD_NUMBER file is properly synchronized (v3.9.5+)

### Build Failures
- Clear build directories: `rm -rf build/ dist/ *.egg-info`
- Ensure setuptools-scm installed: `pip install setuptools-scm`
- Check for uncommitted changes (causes .dirty suffix)

### Upload Failures
- Verify PyPI/npm credentials
- Check network connectivity
- Ensure unique version number

### Memory Issues (v3.9.5+)
- **Large .claude.json files**: Can cause 2GB+ memory usage with --resume
- **Solution**: Use `claude-mpm cleanup-memory` command
- **Usage**: `claude-mpm cleanup-memory --days 30 --max-size 500KB`
- **Safe operation**: Archives old conversations, keeps recent ones active
- **Automatic cleanup**: Recommended to run periodically

## Security Considerations

1. **API Tokens**: Never commit tokens to repository
2. **2FA**: Enable on PyPI and npm accounts
3. **GPG Signing**: Sign git tags for releases
4. **SBOM**: Consider generating Software Bill of Materials

## Agent Deployment and Versioning

### Agent Version Management

Claude MPM agents use semantic versioning (major.minor.patch) for consistent version tracking:

```bash
# Deploy agents (includes automatic version migration)
claude-mpm agents deploy

# Verify agent versions and check for updates
claude-mpm agents verify

# Force rebuild all agents (useful for version migrations)
claude-mpm agents deploy --force-rebuild

# List agents with version information
claude-mpm agents list
```

### Agent Version Migration

The deployment system automatically migrates agents from old version formats:
- **Old format**: `0002-0005` (serial versioning)
- **New format**: `2.1.0` (semantic versioning)

Migration happens automatically during deployment when old formats are detected.

### Agent Update Detection

Agents are automatically updated when:
1. Template version increases
2. Old version format is detected
3. Base agent version changes
4. Force rebuild flag is used

## Related Documentation

- [RELEASE_MAKE.md](./RELEASE_MAKE.md) - **Detailed Make-based release guide**
- [VERSIONING.md](./VERSIONING.md) - Detailed version management (includes agent versioning)
- [CHANGELOG.md](../CHANGELOG.md) - Release history
- [QA.md](./QA.md) - Testing procedures
- [STRUCTURE.md](./STRUCTURE.md) - Project organization

## Quick Reference

**Most Common Release Commands:**
```bash
make release-help       # Show all release options
make release-dry-run    # Preview what would happen
make release-patch      # Bug fix release (4.0.4 → 4.0.5)
make release-minor      # Feature release (4.0.4 → 4.1.0)
make release-major      # Breaking change (4.0.4 → 5.0.0)
make release-publish    # Publish prepared release
make release-full       # Complete patch release + publish
```

**Prerequisites:**
```bash
# Install required tools
pip install commitizen twine
brew install gh  # or visit https://cli.github.com/
```

**Help:**
```bash
make help           # Show all Makefile targets
make release-help   # Show detailed release help
```