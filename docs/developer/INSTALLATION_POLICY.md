# Installation Policy

## Always Install from PyPI

**Policy**: Claude MPM should always be installed from PyPI, never from local wheel files.

### Why This Matters

When `uv tool` installs from a local file path (e.g., `dist/claude_mpm-5.7.9-py3-none-any.whl`), it stores that file path as the installation source. Future `uv tool update` commands will fail if that specific file no longer exists.

**Problem:**
```bash
$ uv tool update claude-mpm
error: Failed to upgrade claude-mpm
  Caused by: Distribution not found at: file:///path/to/dist/claude_mpm-5.7.9-py3-none-any.whl
```

### Correct Installation Methods

**For Users:**
```bash
# Install latest version from PyPI
uv tool install claude-mpm

# Install specific version
uv tool install claude-mpm==5.7.10

# Upgrade to latest
uv tool upgrade claude-mpm
```

**For Development/Testing:**
```bash
# Use editable install (links to source, not a wheel file)
uv tool install --editable .

# Or install from PyPI even during development
uv tool install --force claude-mpm
```

### Publishing Workflow

After building and publishing to PyPI:

```bash
# ✅ CORRECT: Install from PyPI to test
uv tool install --force claude-mpm

# ❌ WRONG: Don't install from local wheel
# uv tool install --force dist/claude_mpm-5.7.10-py3-none-any.whl
```

### Documentation Standards

**In all documentation, use PyPI installation commands:**

✅ **CORRECT**:
```markdown
Install claude-mpm:
\`\`\`bash
uv tool install claude-mpm
\`\`\`
```

❌ **WRONG**:
```markdown
Install claude-mpm:
\`\`\`bash
uv tool install dist/claude_mpm-5.7.10-py3-none-any.whl
\`\`\`
```

### Scripts and Automation

All scripts that reference installation should use PyPI:

**Good Example:**
```bash
#!/bin/bash
# Install latest from PyPI
uv tool install --force claude-mpm
```

**Bad Example:**
```bash
#!/bin/bash
# DON'T DO THIS
uv tool install --force dist/claude_mpm-*.whl
```

### Testing Releases

**Correct process:**

1. Build package: `python3 -m build --wheel`
2. Publish to PyPI: `./scripts/publish_to_pypi.sh`
3. **Wait for PyPI to propagate** (~30 seconds)
4. Install from PyPI: `uv tool install --force claude-mpm`
5. Test the installed package

**Why wait?** PyPI needs time to make the new version available. Installing immediately after upload may grab the old version.

### Troubleshooting

**If you accidentally installed from a local file:**

```bash
# Reinstall from PyPI
uv tool uninstall claude-mpm
uv tool install claude-mpm

# Or force reinstall
uv tool install --force claude-mpm
```

**Verify installation source:**
```bash
# Check where uv tool thinks the package comes from
uv tool list | grep claude-mpm
```

If you see `file:///...`, you're installed from a local file. Reinstall from PyPI.

### Developer Convenience

For active development with frequent changes:

```bash
# Use editable install (best for development)
cd /path/to/claude-mpm
uv tool install --editable .

# Changes take effect immediately (no reinstall needed)
# But published releases still use PyPI
```

### Summary

- ✅ **DO**: Install from PyPI (`uv tool install claude-mpm`)
- ✅ **DO**: Use editable install for development (`uv tool install --editable .`)
- ❌ **DON'T**: Install from local wheel files (`dist/*.whl`)
- ❌ **DON'T**: Reference local paths in documentation
- ❌ **DON'T**: Create workflows that depend on local wheel files

This ensures consistent behavior, working updates, and prevents installation source errors.

---

**Last Updated:** 2026-02-08
**Policy Established:** v5.7.10
