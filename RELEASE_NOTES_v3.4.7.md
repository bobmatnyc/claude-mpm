# Claude MPM v3.4.7 Release Notes

**Release Date:** August 7, 2025  
**Type:** Patch Release (Bug Fixes)

## 🐛 Critical Bug Fixes

This patch release resolves two critical issues affecting user experience in installed environments:

### 1. Version Display Resolution 
**Problem:** Users experiencing "Version unavailable" or incorrect version display
**Solution:** Implemented robust 3-tier fallback system for version determination

- **Tier 1:** Git tag-based version detection (for development environments)
- **Tier 2:** VERSION file reading (for installed packages)  
- **Tier 3:** Package metadata fallback (ultimate safety net)

**Impact:** All users will now see correct version information in CLI and interactive mode

### 2. Socket.IO Daemon Path Resolution
**Problem:** Socket.IO monitoring failing in installed packages due to incorrect path resolution
**Solution:** Fixed daemon script path detection for installed environments

- Added `socketio_daemon.py` to proper package structure (`src/claude_mpm/scripts/`)
- Updated `MANIFEST.in` to include package scripts in distribution
- Enhanced path resolution to work in both development and installed environments

**Impact:** Socket.IO monitoring now works correctly in all installation scenarios

## 🔧 Technical Details

### Files Modified:
- `src/claude_mpm/core/claude_runner.py` - Enhanced version determination logic
- `src/claude_mpm/scripts/socketio_daemon.py` - New proper package location
- `MANIFEST.in` - Include package scripts in distribution

### Installation Methods Verified:
- ✅ pip install from PyPI
- ✅ pip install from source
- ✅ npm install global wrapper
- ✅ Development editable install

## 📦 Distribution Channels

This release is available on both distribution channels:

- **PyPI:** `pip install claude-mpm==3.4.7`
- **npm:** `npm install -g @bobmatnyc/claude-mpm@3.4.7`

## 🚨 Upgrade Recommendation

**Immediate upgrade recommended** for all users experiencing:
- Version display issues
- Socket.IO monitoring failures
- "Script not found" errors

## 📋 Verification Commands

After upgrading, verify the fixes:

```bash
# Verify version display
claude-mpm --version

# Test Socket.IO monitoring (if applicable)
claude-mpm monitor --help

# Verify basic functionality
claude-mpm --help
```

## 🔗 Links

- **PyPI Package:** https://pypi.org/project/claude-mpm/3.4.7/
- **npm Package:** https://www.npmjs.com/package/@bobmatnyc/claude-mpm/v/3.4.7
- **GitHub Release:** [v3.4.7](https://github.com/bobmatnyc/claude-mpm/releases/tag/v3.4.7)

---

*This release maintains full backward compatibility. No configuration or workflow changes required.*