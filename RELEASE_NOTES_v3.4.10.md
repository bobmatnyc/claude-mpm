# Claude MPM v3.4.10 Release Notes

**Release Date**: August 7, 2025  
**Release Type**: Patch Release  

## Overview

This patch release resolves a critical dependency installation issue that prevented Socket.IO monitoring features from working properly on macOS systems using pipx installations.

## 🐛 Critical Bug Fix

### Socket.IO Dependencies Now Core Requirements

**Issue**: Users on macOS using `pipx install claude-mpm` encountered an "externally-managed-environment" error when the system tried to install optional Socket.IO dependencies for monitoring features.

**Root Cause**: Socket.IO dependencies (python-socketio, aiohttp, python-engineio) were listed as optional dependencies in the [project.optional-dependencies] monitor group, causing them to not be installed automatically with the main package.

**Resolution**: Moved all Socket.IO dependencies from optional to required dependencies in the main dependency list.

## 📦 Changes Made

### Dependencies Updated
- **python-socketio** ≥5.0.0: Moved from optional to required
- **aiohttp** ≥3.8.0: Moved from optional to required  
- **python-engineio** ≥4.0.0: Moved from optional to required

### Files Modified
- `pyproject.toml`: Dependency reorganization
- `CHANGELOG.md`: Updated with detailed fix information
- `package.json`: Version synchronization
- `VERSION`: Bumped to 3.4.10

## 🎯 Impact

### Before This Fix
```bash
pipx install claude-mpm
claude-mpm monitor  # ❌ Failed with dependency errors
```

### After This Fix
```bash
pipx install claude-mpm
claude-mpm monitor  # ✅ Works immediately
```

## ✅ Benefits

1. **Out-of-the-box monitoring**: Socket.IO monitoring works immediately after installation
2. **pipx compatibility**: No more externally-managed-environment errors on macOS
3. **Simplified installation**: No need to manually install optional dependencies
4. **Better user experience**: Monitoring features are always available

## 📋 Installation & Upgrade

### New Installations
```bash
# PyPI (recommended)
pip install claude-mpm==3.4.10
pipx install claude-mpm==3.4.10

# npm (alternative)
npm install -g @bobmatnyc/claude-mpm@3.4.10
```

### Upgrading Existing Installations
```bash
# PyPI
pip install --upgrade claude-mpm
pipx upgrade claude-mpm

# npm
npm install -g @bobmatnyc/claude-mpm@latest
```

## 🧪 Testing

After installation, verify the fix works:

```bash
# Test basic functionality
claude-mpm --version

# Test monitoring (should work without errors)
claude-mpm monitor --help

# Test Socket.IO server startup
claude-mpm monitor --start-server --port 8080
```

## 🔗 Links

- **PyPI Package**: https://pypi.org/project/claude-mpm/3.4.10/
- **npm Package**: https://www.npmjs.com/package/@bobmatnyc/claude-mpm/v/3.4.10
- **GitHub Release**: https://github.com/bobmatnyc/claude-mpm/releases/tag/v3.4.10
- **GitHub Issues**: Report issues at https://github.com/bobmatnyc/claude-mpm/issues

## 📈 Version History

- **v3.4.9** (Previous): Base monitoring functionality
- **v3.4.10** (Current): Socket.IO dependencies as core requirements
- **Next**: Additional monitoring enhancements planned

## 🤝 Community

This fix addresses feedback from macOS users who couldn't use monitoring features after clean installations. Thank you to the community for reporting this issue!

---

**Note**: This is a backward-compatible patch that only affects dependency installation. No breaking changes to existing APIs or functionality.