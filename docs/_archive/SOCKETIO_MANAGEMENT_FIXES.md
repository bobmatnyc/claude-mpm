# Socket.IO Management Scripts Integration Fixes

## Overview
Fixed the Socket.IO management scripts to work properly together and resolve the stop command issues identified in the research.

## Problems Resolved

### 1. PID Extraction Issues
- **Problem**: socketio_server_manager expected specific JSON health response format but daemon served different format
- **Fix**: Added compatibility layer to detect daemon-style servers and extract PID from daemon PID file

### 2. Different PID File Locations
- **Problem**: Scripts used different PID file locations:
  - Daemon: `~/.claude-mpm/socketio-server.pid`  
  - Manager: `/tmp/claude_mpm_socketio_{port}.pid`
- **Fix**: Manager now checks both locations and uses appropriate fallback mechanisms

### 3. Stop Command Failures
- **Problem**: Manager couldn't stop daemon-style servers because it couldn't extract PID
- **Fix**: Implemented fallback to daemon PID file when HTTP PID extraction fails

### 4. Management Style Conflicts
- **Problem**: No coordination between scripts, could have conflicting servers
- **Fix**: Added conflict detection and resolution guidance

## Key Improvements Made

### socketio_server_manager.py Enhancements

#### 1. Daemon Compatibility Layer
```python
def get_server_info(self, port: int) -> Optional[Dict]:
    # Check if this is a daemon-style response (no 'pid' field)
    if 'pid' not in data and 'status' in data:
        # Try to get PID from daemon PID file
        daemon_pid = self._get_daemon_pid()
        if daemon_pid:
            data['pid'] = daemon_pid
            data['management_style'] = 'daemon'
```

#### 2. Enhanced Stop Functionality
```python
def stop_server(self, port: int = None, server_id: str = None) -> bool:
    # Try HTTP-based stop first
    # If HTTP method failed, try daemon stop
    if management_style == 'daemon' or not pid:
        return self._try_daemon_stop(port)
```

#### 3. Improved Status Display
- Shows management style (HTTP vs Daemon) with different icons
- Provides appropriate stop commands for each management style
- Warns about conflicts between management approaches

#### 4. New Diagnose Command
```bash
python socketio_server_manager.py diagnose --port 8765
```
- Detects conflicts between HTTP and daemon servers
- Suggests resolution steps
- Shows management style comparison

### socketio_daemon.py Enhancements

#### 1. Conflict Detection
```python
def start_server():
    # Check for HTTP-managed server conflict
    try:
        response = requests.get("http://localhost:8765/health", timeout=1.0)
        if response.status_code == 200:
            print("⚠️  HTTP-managed server already running")
            print("   Stop it first: socketio_server_manager.py stop --port 8765")
```

#### 2. Enhanced Status Display
- Shows management style and integration info
- Detects potential conflicts with HTTP-managed servers
- Provides appropriate management commands

## Usage Examples

### Check Server Status (Both Styles)
```bash
# Using manager (works with both management styles)
python src/claude_mpm/scripts/socketio_server_manager.py status -v

# Using daemon (daemon-specific)
python src/claude_mpm/scripts/socketio_daemon.py status
```

### Stop Server (Automatic Fallback)
```bash
# This now tries HTTP first, then daemon fallback
python src/claude_mpm/scripts/socketio_server_manager.py stop --port 8765
```

### Diagnose Conflicts
```bash
# New diagnostic tool
python src/claude_mpm/scripts/socketio_server_manager.py diagnose --port 8765
```

## Error Messages and Guidance

### Before Fixes
```
❌ Failed to stop server on port 8765
```

### After Fixes
```
🔄 Attempting daemon-style stop...
❌ No daemon server found (no PID file at ~/.claude-mpm/socketio-server.pid)
💡 Try using the socketio_daemon.py stop command if this is a daemon-managed server
```

## Backward Compatibility

- Both scripts continue to work independently
- Existing workflows are preserved
- New features are additive, not breaking

## Testing

Created comprehensive integration test: `tests/test_socketio_management_integration.py`

Run tests:
```bash
python tests/test_socketio_management_integration.py
```

## Key Benefits

1. **Unified Management**: Single interface works with both management styles
2. **Clear Error Messages**: Helpful guidance when operations fail
3. **Conflict Resolution**: Automatic detection and resolution suggestions
4. **Better UX**: Clear indication of which management style is in use
5. **Fallback Mechanisms**: Robust operation even when primary methods fail

## Management Style Comparison

| Feature | HTTP-Managed | Daemon-Managed |
|---------|-------------|----------------|
| **API Access** | Full HTTP API | Basic process signals |
| **Multi-instance** | Yes | No (single instance) |
| **Statistics** | Detailed stats | Basic process info |
| **Complexity** | Higher | Lower |
| **Dependencies** | HTTP client required | Minimal |
| **Best for** | Development/Testing | Production/Simple deployments |

## Resolution Commands

### If HTTP Server is Running
```bash
python src/claude_mpm/scripts/socketio_server_manager.py stop --port 8765
```

### If Daemon Server is Running  
```bash
python src/claude_mpm/scripts/socketio_daemon.py stop
```

### If Conflict Detected
```bash
python src/claude_mpm/scripts/socketio_server_manager.py diagnose
```

The fixes ensure both scripts work harmoniously together while maintaining their individual strengths and use cases.