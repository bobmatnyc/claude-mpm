# Publishing Guide

Complete guide for publishing Claude MPM to PyPI with secure, automated methods.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Initial Setup](#initial-setup)
- [Publishing Workflow](#publishing-workflow)
- [Verification](#verification)
- [Security Best Practices](#security-best-practices)
- [Troubleshooting](#troubleshooting)
- [Complete Workflow Example](#complete-workflow-example)

## Overview

This guide covers the complete process of publishing Claude MPM to PyPI, from initial setup through verification. The publishing system provides:

- Secure API token management via `.env.local`
- Automated validation and safety checks
- Clear progress indicators and error messages
- Integration with existing release workflow

## Prerequisites

Before you can publish to PyPI, you need:

1. PyPI account with access to the `claude-mpm` project
2. API token with project permissions
3. Distribution files built and ready
4. All quality gates passing

## Initial Setup

### 1. PyPI API Token

1. Log in to [PyPI](https://pypi.org/)
2. Go to Account Settings → API tokens
3. Create a new API token:
   - **Scope**: Project-specific for `claude-mpm` (recommended)
   - **Token name**: Something memorable (e.g., "claude-mpm-publishing")
4. Copy the token (starts with `pypi-`)
   - **Important**: You can only see this token once!
   - Save it securely before closing the page

### 2. Store Credentials Securely

Create a `.env.local` file in the project root:

```bash
# Create .env.local with your API token
echo "PYPI_API_KEY=pypi-AgEI...your-token-here..." > .env.local

# Set secure permissions (readable/writable only by you)
chmod 600 .env.local
```

**IMPORTANT Security Checks**:

```bash
# Verify .env.local is in .gitignore
grep "\.env\.local" .gitignore || echo ".env.local" >> .gitignore

# Verify git won't track it
git check-ignore .env.local
# Should output: .env.local

# Verify it's not already tracked
git status .env.local
# Should show: error (not tracked)
```

The `.gitignore` already includes `.env.*` pattern which covers `.env.local`.

### 3. Verify Setup

Run the verification script to confirm everything is configured correctly:

```bash
./scripts/verify_publish_setup.sh
```

This safe, read-only script checks:
- `.env.local` file exists
- File has secure permissions (600)
- File is gitignored and not tracked
- API key is present and correctly formatted
- Distribution files exist
- Required tools are installed (twine, git, python)

All checks should pass with ✓ before publishing.

### 4. Publishing Scripts

The setup includes two scripts:

**Verification Script** (`scripts/verify_publish_setup.sh`):
- Safe, read-only validation
- Checks 9 different aspects
- Returns appropriate exit codes for automation
- Run anytime to verify setup

**Publishing Script** (`scripts/publish_to_pypi.sh`):
- Automated PyPI publishing
- Validates prerequisites before uploading
- Secure credential handling (never echoes API key)
- Clear, colored output with progress
- Confirmation prompt before uploading

### 5. Makefile Integration

A convenient Makefile target is available:

```bash
make publish-pypi
```

This runs the publishing script with proper environment setup.

## Publishing Workflow

### Option 1: Using Makefile (Recommended)

```bash
make publish-pypi
```

### Option 2: Direct Script Execution

```bash
./scripts/publish_to_pypi.sh
```

### Option 3: Verify Then Publish

```bash
./scripts/verify_publish_setup.sh && make publish-pypi
```

### What Happens During Publishing

The publishing script performs these steps:

1. ✓ Verify you're in the project root directory
2. ✓ Load credentials from `.env.local`
3. ✓ Validate the PYPI_API_KEY exists and is properly formatted
4. ✓ Read version from `VERSION` file
5. ✓ Verify distribution files exist
6. ✓ Show file sizes and version information
7. ✓ Prompt for confirmation
8. ✓ Install twine if not present
9. ✓ Upload to PyPI using secure token authentication
10. ✓ Display success message with verification links

### Example Output

```
========================================
  Claude MPM - PyPI Publishing Script
========================================

✓ Running from project root
✓ Loaded .env.local
✓ PYPI_API_KEY found (279 characters)
Publishing version: 4.18.0
✓ Found wheel: dist/claude_mpm-4.18.0-py3-none-any.whl
✓ Found tarball: dist/claude_mpm-4.18.0.tar.gz
  Wheel size: 3.1M
  Tarball size: 2.6M
✓ Twine is available

Ready to upload to PyPI:
  Package: claude-mpm
  Version: 4.18.0
  Files: 2 (wheel + tarball)

Continue with upload? [y/N]: y

Uploading to PyPI...
This may take a moment...

========================================
  ✓ Successfully published to PyPI!
========================================

Package available at:
  https://pypi.org/project/claude-mpm/4.18.0/

Test installation with:
  pip install --upgrade claude-mpm
  pip install claude-mpm==4.18.0
```

### Manual Publishing (Alternative)

If you prefer to publish manually without the script:

```bash
# Load environment variables
source .env.local

# Upload using twine directly
twine upload \
    --username __token__ \
    --password "$PYPI_API_KEY" \
    dist/claude_mpm-*.whl \
    dist/claude_mpm-*.tar.gz
```

## Verification

After publishing, verify the package is available and working correctly.

### 1. Check PyPI Page

Visit: `https://pypi.org/project/claude-mpm/`

Verify:
- Correct version is displayed
- Description renders properly
- Links work correctly
- Package files are present (wheel + tarball)
- File sizes are reasonable

### 2. Test Installation

In a clean environment:

```bash
# Create test environment
python -m venv test_env
source test_env/bin/activate  # or: test_env\Scripts\activate on Windows

# Install from PyPI
pip install claude-mpm==4.18.0

# Verify installation
claude-mpm --version

# Test basic functionality
claude-mpm --help

# Clean up
deactivate
rm -rf test_env
```

### 3. Upgrade Test

If users already have the package:

```bash
pip install --upgrade claude-mpm
```

Verify the new version is installed:

```bash
pip show claude-mpm | grep Version
```

## Security Best Practices

### API Token Security

1. **Never commit** `.env.local` to version control
   - Already protected by `.gitignore` pattern `.env.*`
   - Verify with `git check-ignore .env.local`

2. **Use project-scoped tokens** when possible
   - Limits damage if token is compromised
   - Easier to revoke and replace

3. **Rotate tokens periodically** (every 90-180 days)
   - Create new token on PyPI
   - Update `.env.local` with new token
   - Revoke old token

4. **Revoke tokens immediately** if compromised
   - Go to PyPI account settings
   - Delete the compromised token
   - Generate new token and update `.env.local`

5. **Don't share tokens** via email, Slack, or other channels
   - Use secure password managers for backup storage
   - Each developer should have their own token

6. **Store backup token** securely
   - Use password manager (1Password, LastPass, etc.)
   - Needed if you lose access to `.env.local`

### File Permissions

Ensure `.env.local` has restricted permissions:

```bash
chmod 600 .env.local
```

This makes it readable/writable only by you (owner).

Verify permissions:

```bash
ls -la .env.local
# Should show: -rw-------
```

### Git Safety

Multiple layers protect against accidentally committing credentials:

```bash
# Check git status (should not include .env.local)
git status

# Verify .env.local is ignored
git check-ignore .env.local
# Should output: .env.local

# Double-check what would be committed
git add -n .
# Should NOT include .env.local

# Verify gitignore pattern
grep "\.env\.\*" .gitignore
# Should show the .env.* pattern
```

## Troubleshooting

### Error: PYPI_API_KEY not found in .env.local

**Solution**:
1. Ensure `.env.local` exists in project root
2. Check the file contains: `PYPI_API_KEY=pypi-...`
3. No spaces around the `=` sign
4. Token is on a single line
5. File is readable: `cat .env.local`

### Error: Invalid API token

**Symptoms**:
```
403 Forbidden: Invalid or expired token
```

**Solution**:
1. Verify token was copied correctly (starts with `pypi-`)
2. Check token hasn't expired
3. Ensure token has permission for `claude-mpm` project
4. Token must be project-scoped or account-wide
5. Generate a new token if needed

### Error: Version already exists on PyPI

**Symptoms**:
```
400 Bad Request: File already exists
```

**Solution**:
1. PyPI doesn't allow re-uploading the same version
2. You must bump the version number:
   ```bash
   # Increment build number
   make increment-build

   # Or bump patch version
   make auto-patch

   # Or use version script
   ./scripts/manage_version.py bump patch
   ```
3. Rebuild distribution files:
   ```bash
   make safe-release-build
   ```
4. Publish the new version

### Error: Distribution files not found

**Symptoms**:
```
Error: Wheel file not found: dist/claude_mpm-X.Y.Z-py3-none-any.whl
```

**Solution**:
1. Run build first:
   ```bash
   make safe-release-build
   ```
2. Verify `dist/` directory contains files:
   ```bash
   ls -lh dist/
   ```
3. Check files match current version:
   ```bash
   cat VERSION
   ls -1 dist/
   ```

### Error: Twine not installed

**Symptoms**:
```
twine: command not found
```

**Solution**:
The script auto-installs twine, but you can install manually:
```bash
pip install twine
```

Verify installation:
```bash
twine --version
```

### Error: Permission denied on .env.local

**Symptoms**:
```
Permission denied: .env.local
```

**Solution**:
```bash
# Fix file permissions
chmod 600 .env.local

# Verify
ls -la .env.local
# Should show: -rw-------
```

### Network/Upload Failures

**Symptoms**:
- Connection timeouts
- SSL errors
- Slow uploads
- Interrupted transfers

**Solution**:
1. Check your internet connection
2. Try again (transient network issues are common)
3. Check PyPI status: https://status.python.org/
4. Use `--verbose` flag for more details:
   ```bash
   twine upload --verbose --username __token__ --password "$PYPI_API_KEY" dist/*
   ```
5. Check firewall/proxy settings
6. Try from different network if problems persist

## Complete Workflow Example

Here's the recommended end-to-end workflow for publishing a new release:

```bash
# 1. Ensure working directory is clean
git status  # Should show no uncommitted changes

# 2. Run pre-publish cleanup and quality checks
make pre-publish
# This automatically runs cleanup, then all quality gates

# 3. Bump version
./scripts/manage_version.py bump patch
# Or: make auto-patch
# Or: make increment-build

# 4. Update CHANGELOG.md
# (manually add release notes)

# 5. Commit version changes
git add VERSION CHANGELOG.md
git commit -m "chore: bump version to X.Y.Z"

# 6. Build distribution files with quality checks
make safe-release-build
# This runs tests, linting, security scan, then builds

# 7. Verify build artifacts
ls -lh dist/
# Should show wheel and tarball files

# 8. Publish to PyPI
make publish-pypi
# Or: ./scripts/publish_to_pypi.sh

# 9. Verify publication
# Visit https://pypi.org/project/claude-mpm/

# 10. Test installation in clean environment
python -m venv test_env
source test_env/bin/activate
pip install --upgrade claude-mpm
claude-mpm --version
deactivate
rm -rf test_env

# 11. Create git tag
git tag vX.Y.Z
git push origin vX.Y.Z

# 12. Create GitHub release
gh release create vX.Y.Z \
    --title "Release X.Y.Z" \
    --notes "$(cat CHANGELOG.md | head -n 50)"

# 13. Push changes
git push origin main
```

## Related Documentation

- [Pre-Publish Checklist](./pre-publish-checklist.md) - Quick checklist for publishing
- [Release Process](../RELEASE_PROCESS.md) - Complete release workflow
- [Version Management](../VERSION_MANAGEMENT.md) - Version numbering scheme
- [Quality Gates](../QUALITY_GATES.md) - Pre-release checks
- [PyPI Package](https://pypi.org/project/claude-mpm/) - Published package

## Support

If you encounter issues not covered here:

1. Check the [Troubleshooting](#troubleshooting) section above
2. Run verification script: `./scripts/verify_publish_setup.sh`
3. Review PyPI's [packaging guide](https://packaging.python.org/tutorials/packaging-projects/)
4. Check [PyPI status page](https://status.python.org/)
5. Open an issue on GitHub with:
   - Error message
   - Output from verification script
   - Steps to reproduce
