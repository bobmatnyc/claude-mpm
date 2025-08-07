# Claude MPM v3.4.11 Release Notes

**Release Date:** August 7, 2025

## 🚨 Critical Fix: Socket.IO Daemon Import Path Issue

This patch release resolves a critical issue that prevented the Socket.IO monitoring server from starting in installed environments, particularly with pipx installations.

## 🔧 Key Fixes

### Socket.IO Daemon Import Path Resolution
- **Fixed** import path detection for both development and installed environments
- **Added** site-packages path detection for pipx/pip installations
- **Enhanced** error messages with debugging information for import failures
- **Resolved** the externally-managed-environment error that prevented server startup

### Performance Improvements
- **Reduced** Socket.IO startup timeouts from 90 seconds to ~15 seconds
- **Optimized** connection retry parameters:
  - max_attempts: 30 → 12 (provides ~15 second total timeout)
  - initial_delay: 1.0s → 0.75s (balanced startup time)
  - max_delay: 3.0s → 2.0s (sufficient for binding delays)

## 🎯 Impact

This release specifically addresses issues where:
- Users with pipx installations couldn't start the Socket.IO monitoring server
- Python path context was lost in daemon fork scenarios  
- Import failures occurred in installed environments vs development environments
- Long timeouts caused poor user experience during server startup

## 📦 Installation

```bash
# Update via pip
pip install --upgrade claude-mpm

# Update via pipx
pipx upgrade claude-mpm

# Update via npm
npm update -g @bobmatnyc/claude-mpm
```

## 🧪 Testing

After upgrading, test the Socket.IO monitoring server:

```bash
# Test Socket.IO server startup
claude-mpm --socketio run -i "test task" --non-interactive

# Check for successful server startup in logs
# Should see "Socket.IO server started successfully" without long delays
```

## 🔗 Related Issues

This release builds upon the dependency fixes in v3.4.10 and completes the Socket.IO monitoring system reliability improvements.

---

**Next Release:** v3.4.12 and v3.4.13 contain package.json version synchronization updates.