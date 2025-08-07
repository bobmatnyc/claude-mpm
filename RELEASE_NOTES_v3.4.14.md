# Claude MPM v3.4.14 Release Notes

**Release Date:** August 7, 2025
**Release Type:** Patch Release - Critical Socket.IO Monitoring Fixes

## 🚨 Critical Fixes

This patch release resolves critical issues that prevented the Socket.IO monitoring feature from functioning properly. These fixes are essential for users who want to use the real-time monitoring dashboard and Socket.IO server functionality.

### Socket.IO Startup Fix
- **Fixed:** Added missing `aiohttp-cors` dependency to `pyproject.toml`
- **Impact:** Resolves `ModuleNotFoundError: No module named 'aiohttp_cors'` that prevented Socket.IO server from starting
- **Affected Users:** All users attempting to use monitoring features (`claude-mpm monitor` or `claude-mpm-socketio`)

### Dashboard Path Resolution Fix
- **Fixed:** Enhanced dashboard template path resolution with fallback logic in `socketio_server.py`
- **Impact:** Fixes "Dashboard not found" errors in installed environments where the path included an incorrect extra "src/" component
- **Details:** Implemented three-tier path resolution:
  1. Module-relative path (works in installed environments)
  2. Project root path (works in development environments) 
  3. Package installation path (fallback for edge cases)

### Package Distribution Fix
- **Fixed:** Updated both `MANIFEST.in` and `pyproject.toml` to properly include dashboard files
- **Impact:** Ensures dashboard templates and static files are included in the distributed package
- **Files Added to Distribution:**
  - `src/claude_mpm/dashboard/*.html`
  - `src/claude_mpm/dashboard/templates/*.html`
  - `src/claude_mpm/dashboard/static/*.css`
  - `src/claude_mpm/dashboard/static/*.js`
  - All nested component files in `dashboard/static/js/components/`

## 🔧 Technical Details

### Dependencies Updated
- Added `aiohttp-cors>=0.8.0` as a required dependency

### Files Modified
- `pyproject.toml` - Added dependency and updated package data
- `MANIFEST.in` - Added recursive includes for dashboard files
- `src/claude_mpm/services/socketio_server.py` - Enhanced path resolution logic

## 🧪 Quality Assurance

- Package successfully built and uploaded to PyPI
- Package successfully published to npm registry as `@bobmatnyc/claude-mpm@3.4.14`
- Version synchronization maintained between PyPI and npm distributions
- Dashboard files verified in package contents

## 📦 Installation

### From PyPI (Python Package)
```bash
pip install claude-mpm==3.4.14
# or upgrade existing installation
pip install --upgrade claude-mpm
```

### From npm (Node.js wrapper)
```bash
npm install -g @bobmatnyc/claude-mpm@3.4.14
# or upgrade existing installation  
npm update -g @bobmatnyc/claude-mpm
```

## 🚀 Verification

After upgrading, verify the fixes by testing Socket.IO monitoring:

```bash
# Test Socket.IO server startup
claude-mpm monitor

# Access dashboard (should load without errors)
# Navigate to http://localhost:8080 in your browser
```

## 🐛 Bug Reports

If you encounter any issues with v3.4.14, please report them on our [GitHub Issues](https://github.com/bobmatnyc/claude-mpm/issues) page.

## 📚 Documentation

- [Socket.IO Monitoring Guide](docs/developer/dashboard/README.md)
- [Deployment Documentation](docs/DEPLOY.md)
- [Troubleshooting Guide](docs/user/04-reference/troubleshooting.md)

---

**Previous Version:** v3.4.13
**Next Planned Release:** v3.4.15 (minor enhancements and improvements)