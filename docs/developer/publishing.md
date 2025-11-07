# Publishing to PyPI

This guide covers publishing Claude MPM to PyPI using secure, automated methods.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Automated Publishing](#automated-publishing)
- [Manual Publishing](#manual-publishing)
- [Verification](#verification)
- [Security Best Practices](#security-best-practices)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### 1. PyPI API Token

1. Log in to [PyPI](https://pypi.org/)
2. Go to Account Settings → API tokens
3. Create a new API token with scope for the `claude-mpm` project
4. Copy the token (starts with `pypi-`)

### 2. Store Credentials Securely

Create a `.env.local` file in the project root:

```bash
# .env.local (NEVER commit this file!)
PYPI_API_KEY=pypi-AgEI...your-token-here...
```

**IMPORTANT**: Verify `.env.local` is in `.gitignore`:

```bash
grep "\.env\.local" .gitignore || echo ".env.local" >> .gitignore
```

The `.gitignore` already includes `.env.*` pattern which covers `.env.local`.

### 3. Build Distribution Files

Before publishing, ensure you have built the distribution files:

```bash
# Run quality checks and build
make safe-release-build
```

This will create files in `dist/`:
- `claude_mpm-X.Y.Z-py3-none-any.whl`
- `claude_mpm-X.Y.Z.tar.gz`

## Automated Publishing

The recommended way to publish is using the automated script.

### Using the Script Directly

```bash
./scripts/publish_to_pypi.sh
```

### Using Makefile Target

```bash
make publish-pypi
```

### What It Does

The script will:

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

## Manual Publishing

If you prefer to publish manually, you can use twine directly:

```bash
# Load environment variables
source .env.local

# Upload using twine
twine upload \
    --username __token__ \
    --password "$PYPI_API_KEY" \
    dist/claude_mpm-*.whl \
    dist/claude_mpm-*.tar.gz
```

## Verification

After publishing, verify the package is available:

### 1. Check PyPI Page

Visit: `https://pypi.org/project/claude-mpm/`

Verify:
- Correct version is displayed
- Description renders properly
- Links work correctly
- Package files are present

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

# Clean up
deactivate
rm -rf test_env
```

### 3. Upgrade Test

If users already have the package:

```bash
pip install --upgrade claude-mpm
```

## Security Best Practices

### API Token Security

1. **Never commit** `.env.local` to version control
2. **Use project-scoped tokens** (not account-wide) when possible
3. **Rotate tokens periodically** (every 90-180 days)
4. **Revoke tokens immediately** if compromised
5. **Don't share tokens** via email, Slack, or other channels
6. **Store backup token** securely (password manager) in case of emergency

### File Permissions

Ensure `.env.local` has restricted permissions:

```bash
chmod 600 .env.local
```

This makes it readable/writable only by you.

### Git Safety

Verify `.env.local` won't be committed:

```bash
# Check git status
git status

# Verify .env.local is ignored
git check-ignore .env.local
# Should output: .env.local

# Double-check what would be committed
git add -n .
# Should NOT include .env.local
```

## Troubleshooting

### Error: PYPI_API_KEY not found in .env.local

**Solution**:
1. Ensure `.env.local` exists in project root
2. Check the file contains: `PYPI_API_KEY=pypi-...`
3. No spaces around the `=` sign
4. Token is on a single line

### Error: Invalid API token

**Symptoms**:
```
403 Forbidden: Invalid or expired token
```

**Solution**:
1. Verify token was copied correctly (starts with `pypi-`)
2. Check token hasn't expired
3. Ensure token has permission for `claude-mpm` project
4. Generate a new token if needed

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
   ```
3. Rebuild and publish the new version

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

### Network/Upload Failures

**Symptoms**:
- Connection timeouts
- SSL errors
- Slow uploads

**Solution**:
1. Check your internet connection
2. Try again (transient network issues)
3. Check PyPI status: https://status.python.org/
4. Use `--verbose` flag for more details:
   ```bash
   twine upload --verbose --username __token__ --password "$PYPI_API_KEY" dist/*
   ```

## Complete Publishing Workflow

Here's the recommended end-to-end workflow:

```bash
# 1. Ensure code is ready
git status  # Should be clean

# 2. Run pre-publish cleanup and quality checks
make pre-publish  # Cleanup + all checks pass

# 3. Build with quality checks
make safe-release-build

# 4. Verify build artifacts
ls -lh dist/

# 5. Publish to PyPI
make publish-pypi
# Or: ./scripts/publish_to_pypi.sh

# 6. Verify publication
# Visit https://pypi.org/project/claude-mpm/

# 7. Test installation
pip install --upgrade claude-mpm
claude-mpm --version

# 8. Tag and push (if not already done)
git tag v4.18.0
git push origin v4.18.0
```

**Note**: The `make pre-publish` target automatically cleans up temporary files (`.DS_Store`, `__pycache__`, test artifacts) before running quality checks. See [Pre-Publish Cleanup](./pre-publish-cleanup.md) for details.

## Related Documentation

- [Pre-Publish Cleanup](./pre-publish-cleanup.md) - Automated cleanup process
- [Publishing Quick Start](./publishing-quickstart.md) - Quick reference guide
- [Release Management](../RELEASE_PROCESS.md) - Complete release workflow
- [Version Management](../VERSION_MANAGEMENT.md) - Version numbering scheme
- [Quality Gates](../QUALITY_GATES.md) - Pre-release checks
- [PyPI Package](https://pypi.org/project/claude-mpm/) - Published package

## Support

If you encounter issues not covered here:

1. Check the [troubleshooting section](#troubleshooting)
2. Review PyPI's [publishing guide](https://packaging.python.org/tutorials/packaging-projects/)
3. Open an issue on GitHub with error details
