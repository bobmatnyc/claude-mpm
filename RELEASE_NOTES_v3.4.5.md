# Release Notes v3.4.5

## Overview

Claude MPM version 3.4.5 is a patch release that addresses a critical bug in the Socket.IO server startup functionality.

## Bug Fix

### Fixed: "server is not defined" error in Socket.IO startup

**Issue:** Socket.IO server startup failed with "NameError: name 'server' is not defined" when using daemon-based server management.

**Root Cause:** The code contained references to an undefined `server` variable in the `_start_standalone_socketio_server()` function in `src/claude_mpm/cli/commands/run.py`. This was a remnant from a previous implementation that used inline server objects instead of the current daemon-based approach.

**Resolution:**
- Removed references to undefined `server` variable in daemon-based Socket.IO startup
- Fixed critical bug that prevented Socket.IO monitoring server from starting properly
- Added 'monitor' command to MPM_COMMANDS array for proper command routing
- Improved error handling and startup sequence for Socket.IO daemon processes

**Files Modified:**
- `src/claude_mpm/cli/commands/run.py` - Fixed server startup logic
- `scripts/claude-mpm` - Added monitor command support  
- `src/claude_mpm/cli/__init__.py` - Added monitor command routing

## Installation

### PyPI (Python Package)
```bash
pip install claude-mpm==3.4.5
# or
pip install --upgrade claude-mpm
```

### npm (Node.js Package)  
```bash
npm install -g @bobmatnyc/claude-mpm@3.4.5
# or  
npm install -g @bobmatnyc/claude-mpm@latest
```

## Impact

This bug fix ensures that:
- Socket.IO monitoring functionality works correctly
- `claude-mpm run --monitor` command starts successfully
- Dashboard and real-time monitoring features are accessible
- No regression in existing functionality

## Verification

To verify the fix works:

```bash
# Test Socket.IO monitoring
claude-mpm run --monitor --input "test task" --non-interactive

# Should start successfully without "server is not defined" error
```

## Distribution

- **PyPI**: https://pypi.org/project/claude-mpm/3.4.5/
- **npm**: https://www.npmjs.com/package/@bobmatnyc/claude-mpm/v/3.4.5
- **GitHub**: https://github.com/bobmatnyc/claude-mpm/releases/tag/v3.4.5

---

**Release Date:** August 7, 2025  
**Version:** 3.4.5  
**Type:** Patch Release (Bug Fix)