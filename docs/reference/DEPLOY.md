# Deployment and Release Guide

This document describes the deployment and release process for Claude MPM.

## Table of Contents

- [Version Management](#version-management)
- [Release Workflow](#release-workflow)
- [Publishing Channels](#publishing-channels)
- [Homebrew Tap Updates](#homebrew-tap-updates)
- [Post-Release Verification](#post-release-verification)
- [Troubleshooting](#troubleshooting)

---

## Version Management

Claude MPM uses a dual tracking system for versions and builds:

### Version Files

- **`VERSION`**: Semantic version only (e.g., `4.8.0`)
- **`BUILD_NUMBER`**: Serial build number (e.g., `275`)
- **`src/claude_mpm/VERSION`**: Package-level version (synced with root)

### Version Formats

Different contexts use different version display formats:

- **Development**: `4.8.0+build.275` (PEP 440 compliant)
- **UI/Logging**: `v4.8.0-build.275` (user-friendly)
- **PyPI Release**: `4.8.0` (clean semantic version)

### Conventional Commits

Version bumps follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` → Minor version bump (new features)
- `fix:` → Patch version bump (bug fixes)
- `feat!:` or `BREAKING CHANGE:` → Major version bump
- `perf:`, `refactor:`, `docs:` → Patch version bump

### Manual Version Management

```bash
# Show current version
./scripts/manage_version.py show

# Increment version
./scripts/manage_version.py increment patch
./scripts/manage_version.py increment minor
./scripts/manage_version.py increment major

# Increment build number only
./scripts/manage_version.py build

# Sync version files
make sync-versions
```

---

## Release Workflow

Claude MPM follows a 6-phase release workflow (see `src/claude_mpm/agents/WORKFLOW.md` for details):

### Quick Release Commands

```bash
# Standard release process (commitizen)
make release-patch     # Bug fix release (X.Y.Z+1)
make release-minor     # Feature release (X.Y+1.0)
make release-major     # Breaking change release (X+1.0.0)

# After preparation, publish
make release-publish   # Publish to PyPI, Homebrew, npm, and GitHub

# Alternative: Automated release (no commitizen)
make auto-patch        # Automated patch release
make auto-minor        # Automated minor release
make auto-major        # Automated major release
```

### Manual Release Steps

1. **Pre-release checks**:
   ```bash
   make release-check
   make pre-publish
   ```

2. **Build package**:
   ```bash
   make safe-release-build
   ```

3. **Publish to PyPI**:
   ```bash
   make publish-pypi
   ```

4. **Update Homebrew (automatic)**:
   ```bash
   # Automatically triggered by release-publish
   # Or manually:
   make update-homebrew-tap
   ```

5. **Create GitHub release**:
   ```bash
   VERSION=$(cat VERSION)
   gh release create "v${VERSION}" \
     --title "Claude MPM v${VERSION}" \
     --notes-from-tag \
     dist/*
   ```

6. **Verify release**:
   ```bash
   make release-verify
   ```

---

## Publishing Channels

### PyPI (Python Package Index)

**Primary distribution channel** for pip installations.

**Publishing**:
```bash
# Using Makefile (recommended)
make publish-pypi

# Manual with twine
python -m twine upload dist/*
```

**Verification**:
```bash
pip install claude-mpm==$(cat VERSION)
claude-mpm --version
```

**URL**: https://pypi.org/project/claude-mpm/

---

### Homebrew Tap

**macOS package manager** for easy installation.

**Repository**: https://github.com/bobmatnyc/homebrew-tools

#### Automated Update Process

After publishing to PyPI, the Homebrew tap is automatically updated:

1. **Automatic Trigger**: `make release-publish` includes Homebrew update
2. **Script Execution**: `scripts/update_homebrew_tap.sh` runs automatically
3. **Process**:
   - Waits for PyPI package availability (retry with backoff)
   - Fetches SHA256 from PyPI
   - Updates `Formula/claude-mpm.rb`
   - Runs local tests (syntax check, brew audit)
   - Commits changes with conventional commit message
   - Prompts for push confirmation (Phase 1)

#### Manual Homebrew Update

If automation fails, update manually:

```bash
# Clone or navigate to homebrew-tools repository
cd /path/to/homebrew-tools

# Run update script
./scripts/update_formula.sh $(cat VERSION)

# Review changes
git diff Formula/claude-mpm.rb

# Test formula locally
brew install --build-from-source ./Formula/claude-mpm.rb
brew test claude-mpm

# Commit and push
git add Formula/claude-mpm.rb
git commit -m "feat: update to v$(cat VERSION)

🤖👥 Generated with [Claude MPM](https://github.com/bobmatnyc/claude-mpm)

Co-Authored-By: Claude <noreply@anthropic.com>"
git push origin main
```

#### Testing Homebrew Updates

```bash
# Dry run (no changes)
make update-homebrew-tap-dry-run

# Or directly:
./scripts/update_homebrew_tap.sh $(cat VERSION) --dry-run

# Test with skip flags
./scripts/update_homebrew_tap.sh $(cat VERSION) --skip-tests --dry-run
```

#### Homebrew Update Options

```bash
# Standard update with confirmation
./scripts/update_homebrew_tap.sh 4.23.0

# Dry run (test without changes)
./scripts/update_homebrew_tap.sh 4.23.0 --dry-run

# Auto-push (no confirmation prompt)
./scripts/update_homebrew_tap.sh 4.23.0 --auto-push

# Skip local tests
./scripts/update_homebrew_tap.sh 4.23.0 --skip-tests

# Regenerate dependency resources
./scripts/update_homebrew_tap.sh 4.23.0 --regenerate-resources
```

#### Verification

```bash
# Update tap and install
brew tap bobmatnyc/tools
brew upgrade claude-mpm
claude-mpm --version
```

**Important**: Homebrew update failures are **non-blocking**. PyPI releases always succeed even if Homebrew automation encounters issues. Manual fallback instructions are provided in error messages.

---

### npm (Node Package Manager)

**Optional distribution channel** for Node.js projects.

**Publishing**:
```bash
# Automatically attempted by release-publish
npm publish

# Or manually
cd /path/to/claude-mpm
npm publish
```

**Verification**:
```bash
npm install -g @bobmatnyc/claude-mpm@$(cat VERSION)
claude-mpm --version
```

---

### GitHub Releases

**Release artifacts and release notes** on GitHub.

**Creating**:
```bash
VERSION=$(cat VERSION)
gh release create "v${VERSION}" \
  --title "Claude MPM v${VERSION}" \
  --notes-from-tag \
  dist/*
```

**Verification**:
- Visit: https://github.com/bobmatnyc/claude-mpm/releases
- Check latest release matches current version

---

## Post-Release Verification

### Verification Checklist

After releasing, verify all distribution channels:

- [ ] **PyPI**: Package installable via pip
- [ ] **Homebrew**: Formula updated and installable
- [ ] **npm**: Package published (if applicable)
- [ ] **GitHub**: Release created with artifacts
- [ ] **Version**: All installations report correct version

### Automated Verification

```bash
make release-verify
```

This displays verification links for all channels:
- PyPI package URL
- npm package URL
- GitHub release URL

### Manual Verification

```bash
# Test PyPI installation
python -m venv /tmp/test-install
source /tmp/test-install/bin/activate
pip install claude-mpm==$(cat VERSION)
claude-mpm --version
deactivate
rm -rf /tmp/test-install

# Test Homebrew installation (macOS)
brew tap bobmatnyc/tools
brew upgrade claude-mpm
claude-mpm --version

# Test npm installation
npm install -g @bobmatnyc/claude-mpm@$(cat VERSION)
claude-mpm --version
```

---

## Troubleshooting

### PyPI Upload Failures

**Issue**: `twine upload` fails with authentication error

**Solution**:
1. Check credentials in `.env.local`:
   ```bash
   TWINE_USERNAME=__token__
   TWINE_PASSWORD=pypi-...
   ```
2. Verify token has upload permissions
3. Re-run: `make publish-pypi`

---

### Homebrew Update Failures

**Issue**: Homebrew tap update fails during release

**Impact**: Non-blocking - PyPI release continues

**Solutions**:

1. **Check logs**:
   ```bash
   cat /tmp/homebrew-tap-update.log
   ```

2. **Manual update**:
   ```bash
   cd /path/to/homebrew-tools
   ./scripts/update_formula.sh $(cat VERSION)
   ```

3. **Common issues**:
   - **PyPI package not available**: Wait 5 minutes for CDN propagation
   - **Network failure**: Check GitHub connectivity
   - **Git conflicts**: Clean up homebrew-tools working directory
   - **Permission denied**: Verify GitHub push access

4. **Detailed troubleshooting**: See [HOMEBREW_UPDATE_TROUBLESHOOTING.md](HOMEBREW_UPDATE_TROUBLESHOOTING.md)

---

### GitHub Release Creation Failures

**Issue**: `gh release create` fails

**Solution**:
1. Check GitHub CLI authentication:
   ```bash
   gh auth status
   gh auth login
   ```
2. Verify repository access
3. Re-run release creation:
   ```bash
   VERSION=$(cat VERSION)
   gh release create "v${VERSION}" \
     --title "Claude MPM v${VERSION}" \
     --notes-from-tag \
     dist/*
   ```

---

### Version Inconsistency

**Issue**: VERSION files out of sync

**Solution**:
```bash
# Sync version files
make sync-versions

# Or manually:
VERSION=$(cat VERSION)
echo "$VERSION" > src/claude_mpm/VERSION
```

---

### Build Failures

**Issue**: `make safe-release-build` fails

**Solution**:
1. Run quality checks:
   ```bash
   make quality
   ```
2. Fix linting errors:
   ```bash
   make lint-fix
   ```
3. Run tests:
   ```bash
   make release-test
   ```
4. Retry build:
   ```bash
   make safe-release-build
   ```

---

## Release Checklist

Use this checklist for manual releases:

- [ ] All changes committed and pushed
- [ ] Quality gate passed (`make pre-publish`)
- [ ] Security scan clean (no secrets in diff)
- [ ] Version incremented appropriately
- [ ] CHANGELOG updated (if using manual process)
- [ ] Build artifacts created (`make safe-release-build`)
- [ ] Published to PyPI (`make publish-pypi`)
- [ ] Homebrew tap updated (automatic or manual)
- [ ] npm published (if applicable)
- [ ] GitHub release created
- [ ] All installations verified
- [ ] Documentation updated

---

## Additional Resources

- **Workflow Details**: [src/claude_mpm/agents/WORKFLOW.md](../../src/claude_mpm/agents/WORKFLOW.md)
- **Homebrew Troubleshooting**: [HOMEBREW_UPDATE_TROUBLESHOOTING.md](HOMEBREW_UPDATE_TROUBLESHOOTING.md)
- **Development Guidelines**: [../../CLAUDE.md](../../CLAUDE.md)
- **Version Management**: [VERSIONING.md](VERSIONING.md)

---

**Last Updated**: 2025-11-13
**Version**: 4.8.0
