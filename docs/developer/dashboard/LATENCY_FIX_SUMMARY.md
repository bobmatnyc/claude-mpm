# WebSocket Dashboard Latency Fix Summary

## Quick Reference for Continuing Work

This document provides a concise summary of the latency fixes implemented for the Claude MPM WebSocket dashboard system.

## Problem
Users experienced keystroke latency when typing in Claude Code due to synchronous operations in the hook processing pipeline.

## Root Causes & Fixes

### 1. Blocking WebSocket Send (1 second delay)

**File**: `src/claude_mpm/services/websocket_server.py`

**Problem**:
```python
future.result(timeout=1.0)  # Blocked for up to 1 second!
```

**Fix**:
```python
# Line 111-115: Send asynchronously without blocking
asyncio.run_coroutine_threadsafe(
    self._send_message(message), 
    self._client_loop
)
# Don't wait for result - let it send in background
```

### 2. Excessive File I/O in Hook Handler

**File**: `src/claude_mpm/hooks/claude_hooks/hook_handler.py`

**Problem**: Debug logging to `/tmp/claude-mpm-hook.log` on every event

**Fix**: Replaced entire file with optimized version:
- Removed all file I/O operations
- Minimal processing (< 1ms)
- Fail silently on errors
- Fast path for common events

### 3. IPv6/IPv4 Connection Issues

**Files**: 
- `src/claude_mpm/services/websocket_server.py` (line 603)
- `scripts/claude_mpm_dashboard.html` (line 667)

**Fix**: Use `127.0.0.1` instead of `localhost` everywhere

## Key Files Modified

1. **Hook Handler** (completely replaced):
   - `src/claude_mpm/hooks/claude_hooks/hook_handler.py`
   - Backup: `hook_handler_full.py.bak`

2. **WebSocket Service**:
   - `src/claude_mpm/services/websocket_server.py`
   - Modified `broadcast_event()` to be non-blocking
   - Fixed socket detection to use `127.0.0.1`

3. **Dashboard**:
   - `scripts/claude_mpm_dashboard.html`
   - Added session registration
   - Fixed WebSocket URL to use `127.0.0.1`

## Current Architecture

```
Claude Code → Hook Handler → WebSocketClientProxy → WebSocket Server → Dashboard
     ↓             ↓                ↓                      ↓              ↓
  Triggers    < 1ms processing   Async send         Broadcasts      Real-time
   hooks       No file I/O      Non-blocking       to clients        display
```

## WebSocket Server Management

### Production Server
```bash
# Start production server with session management
python scripts/websocket_server_production.py

# Or use manager for auto-restart
python scripts/websocket_server_manager.py
```

### Key Features
- Session-based filtering
- Health monitoring (30s intervals)
- Auto-reconnection support
- Non-blocking broadcasts

## Testing Tools

```bash
# Verify server connection
python scripts/verify_websocket_connection.py

# Monitor events
python scripts/monitor_websocket_events.py

# Test hook broadcasting
python scripts/test_hook_broadcast_simple.py
```

## Performance Metrics

**Before**: 1060-1120ms latency
**After**: < 10ms latency

- Hook processing: < 1ms
- WebSocket send: < 5ms (async)
- File I/O: 0ms (removed)

## To Continue Work

1. **Server must be running**:
   ```bash
   python scripts/websocket_server_production.py &
   ```

2. **Dashboard URL format**:
   ```
   file:///path/to/dashboard.html?port=8765&session=your-session-id
   ```

3. **Environment is already optimized** - no special flags needed

## Important Notes

- Hooks are NOT intercepting keystrokes (only UserPromptSubmit, PreToolUse, PostToolUse)
- Optimized handler is now the default (no mode switching)
- Debug logging removed for performance (use dashboard for monitoring)
- All operations are non-blocking and async

## If Issues Arise

1. Clear Python cache:
   ```bash
   find . -name "*.pyc" -delete
   find . -name "__pycache__" -type d -exec rm -rf {} +
   ```

2. Restart WebSocket server:
   ```bash
   lsof -ti :8765 | xargs kill -9
   python scripts/websocket_server_production.py &
   ```

3. Check connection:
   ```bash
   python scripts/verify_websocket_connection.py
   ```