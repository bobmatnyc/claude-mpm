# Socket.IO Integration Fixes Summary

## Issues Fixed

### 1. Duplicate Browser Opening ✅

**Problem**: Monitor mode was opening 2-3 browser tabs/windows due to multiple browser opening calls.

**Root Cause**: Browser opening logic was present in multiple places:
- `run.py` line 256: `open_in_browser_tab()`
- `claude_runner.py` line 319: exec mode browser opening
- `claude_runner.py` line 434: subprocess mode browser opening  
- `claude_runner.py` line 667: oneshot mode browser opening

**Solution**: 
- Removed browser opening from `run.py` when server already exists
- Removed browser opening from subprocess and oneshot modes in `claude_runner.py`
- Kept browser opening only for exec mode (persistent server case)
- Added explanatory comments about the centralized approach

**Files Modified**:
- `/src/claude_mpm/core/claude_runner.py`
- `/src/claude_mpm/cli/commands/run.py`

### 2. Hook Events Not Reaching Dashboard ✅

**Problem**: Socket.IO server was running and dashboard connected, but hook events weren't being sent.

**Root Cause**: Port mismatch between hook handlers and Socket.IO server:
- Hook handlers hardcoded to port 8765
- ClaudeRunner could be configured to use different ports
- Hook handlers would detect wrong servers (non-Socket.IO servers on ports 8080, 8082)

**Solution**:
- Added dynamic port detection to both hook handlers
- Set `CLAUDE_MPM_SOCKETIO_PORT` environment variable in ClaudeRunner
- Hook handlers now check environment variable first, then scan common ports
- Fixed initialization order in WebSocketHandler (set `_debug` before calling port detection)

**Files Modified**:
- `/src/claude_mpm/hooks/claude_hooks/hook_handler.py`
- `/src/claude_mpm/core/websocket_handler.py`
- `/src/claude_mpm/core/claude_runner.py`

## Verification

### Test Scripts Created:
1. `scripts/test_hook_socketio_connection.py` - Basic connection testing
2. `scripts/test_socketio_server_detailed.py` - Detailed server compatibility testing

### Manual Testing Results:
- ✅ Hook handler connects to Socket.IO server when running
- ✅ Hook events are successfully sent to `/hook` namespace
- ✅ WebSocket logging handler connects and sends logs to `/log` namespace
- ✅ Only one browser window opens in monitor mode
- ✅ Port detection works correctly

## Architecture Improvements

### Dynamic Port Detection:
Hook handlers now use this priority order:
1. `CLAUDE_MPM_SOCKETIO_PORT` environment variable (set by ClaudeRunner)
2. Scan common ports [8765, 8080, 8081, 8082, 8083, 8084, 8085]
3. Default to 8765 if nothing found

### Centralized Browser Management:
- `run.py`: Reports server status, delegates browser opening to ClaudeRunner
- `claude_runner.py`: Opens browser only for exec mode after server is confirmed running
- Subprocess and oneshot modes: No browser opening (assumes already handled)

### Authentication:
- Uses 'dev-token' for development (configurable via `CLAUDE_MPM_SOCKETIO_TOKEN`)
- Connects to appropriate namespaces: `/hook`, `/log`, `/system`

## Usage

### Start Monitor Mode:
```bash
claude-mpm run --monitor
```

### Start with Custom Port:
```bash
claude-mpm run --monitor --websocket-port 8080
```

### Debug Mode:
```bash
CLAUDE_MPM_HOOK_DEBUG=true claude-mpm run --monitor
```

## Next Steps

The Socket.IO integration is now working correctly. Users should see:
1. Single browser window opening in monitor mode
2. Real-time hook events appearing in the dashboard
3. Real-time log messages appearing in the dashboard
4. Proper connection status indicators

All fixes maintain backward compatibility and graceful degradation when Socket.IO is not available.