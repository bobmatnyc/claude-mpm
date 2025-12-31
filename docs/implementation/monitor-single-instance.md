# Monitor Single Instance Enforcement

## Overview

The Claude MPM monitor now enforces **single instance behavior** - only ONE monitor server runs at a time on the default port (8765).

## Behavior

### Default Port (8765)

**First run:**
```bash
claude-mpm-monitor
# ✅ Starts monitor on port 8765
# Opens browser to http://localhost:8765
```

**Second run (monitor already running):**
```bash
claude-mpm-monitor
# ℹ️  Monitor already running at http://localhost:8765
# Opens browser to existing instance
# Does NOT start a new instance
```

**Explicit port specification:**
```bash
claude-mpm-monitor --port 9000
# ✅ Starts monitor on port 9000 (if available)
# ❌ Fails if port 9000 is busy
```

### Port Selection Rules

1. **No `--port` flag**: Uses default port 8765
   - If 8765 is free → Start new instance
   - If 8765 has our monitor → Reuse existing, open browser
   - If 8765 has other service → **FAIL** with clear error

2. **With `--port XXXX` flag**: Uses specified port
   - If port is free → Start new instance
   - If port is busy → **FAIL** with clear error
   - **Never** auto-increment to find free port

3. **No Auto-Increment**: We will never silently pick a different port
   - Old behavior: "Port 8765 busy, using 8766 instead"
   - New behavior: "Port 8765 busy, please stop existing service or use --port"

## Examples

### Scenario 1: Normal Startup

```bash
# Terminal 1: Start monitor
$ claude-mpm-monitor
INFO: Starting Claude MPM monitor on localhost:8765
INFO: Monitor running on port 8765
INFO: Opening browser to http://localhost:8765

# Terminal 2: Try to start another monitor
$ claude-mpm-monitor
INFO: Monitor already running at http://localhost:8765
INFO: Opening browser to existing instance: http://localhost:8765
# (exits successfully, no new instance started)
```

### Scenario 2: Port Conflict with External Service

```bash
# Some other service is using port 8765
$ claude-mpm-monitor
ERROR: Default port 8765 is already in use.
ERROR: Please stop the existing service with 'claude-mpm monitor stop'
ERROR: or specify a different port with --port.
# (exits with error code 1)
```

### Scenario 3: Explicit Port

```bash
# Start on specific port
$ claude-mpm-monitor --port 9000
INFO: Starting Claude MPM monitor on localhost:9000
INFO: Monitor running on port 9000

# Try same port again
$ claude-mpm-monitor --port 9000
INFO: Monitor already running at http://localhost:9000
INFO: Opening browser to existing instance
```

### Scenario 4: Background Daemon

```bash
# Start as daemon
$ claude-mpm-monitor --background
INFO: Monitor daemon started in background on port 8765

# Try to start another (foreground)
$ claude-mpm-monitor
INFO: Monitor already running at http://localhost:8765
INFO: Opening browser to existing instance: http://localhost:8765

# Stop daemon
$ claude-mpm monitor stop
INFO: Stopping daemon with PID 12345
```

## Health Check Endpoint

The monitor exposes a `/health` endpoint that returns:

```json
{
  "status": "running",
  "service": "claude-mpm-monitor",
  "version": "5.3.1",
  "port": 8765,
  "pid": 12345,
  "uptime": 3600
}
```

This endpoint is used to:
1. Detect existing monitor instances
2. Verify the service is our claude-mpm-monitor (not another service)
3. Enable smart reuse behavior

## Implementation Details

### Changes Made

**File: `src/claude_mpm/scripts/launch_monitor.py`**

1. **Added `check_existing_monitor()` function**:
   - Checks `/health` endpoint for existing monitor
   - Verifies `service` field equals `"claude-mpm-monitor"`
   - Returns `True` if monitor already running

2. **Changed default port behavior**:
   - `--port` default changed from `8765` to `None`
   - `None` triggers single-instance check
   - Explicit port value skips reuse check (fails if busy)

3. **Removed auto-increment logic**:
   - No longer calls `PortManager.find_available_port()`
   - Uses exact port or fails with clear error
   - Never silently picks alternative port

4. **Added early-exit on existing instance**:
   - If monitor detected on target port → log message, open browser, exit
   - No new instance started
   - Clean exit (return code 0)

### Health Check Implementation

**File: `src/claude_mpm/services/monitor/server.py`**

The `/health` endpoint (already existed) returns:

```python
{
    "status": ServiceState.RUNNING,
    "service": "claude-mpm-monitor",  # Key identifier
    "version": version,
    "port": self.port,
    "pid": os.getpid(),
    "uptime": int(time.time() - self.server_start_time),
}
```

The `service: "claude-mpm-monitor"` field is critical for detection.

### Port Availability Check

**File: `src/claude_mpm/services/monitor/daemon_manager.py`**

Uses `DaemonManager._is_port_available()` to check if port is free:

```python
def _is_port_available(self) -> bool:
    """Check if the port is available for binding."""
    try:
        test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        test_sock.bind((bind_host, self.port))
        test_sock.close()
        return True
    except OSError:
        return False
```

## Migration Guide

### Old Behavior (v5.3.0 and earlier)

```bash
# Start first monitor
$ claude-mpm-monitor
# Starts on port 8765

# Start second monitor
$ claude-mpm-monitor
# Port 8765 is in use, using port 8766 instead
# (creates SECOND instance on different port)
```

**Problem**: Multiple monitor instances running simultaneously, causing confusion.

### New Behavior (v5.3.1+)

```bash
# Start first monitor
$ claude-mpm-monitor
# Starts on port 8765

# Start second monitor
$ claude-mpm-monitor
# Monitor already running at http://localhost:8765
# (reuses existing instance, NO second instance)
```

**Benefit**: Single source of truth, predictable port, no duplicate instances.

## Troubleshooting

### Monitor Won't Start - Port Busy

**Error:**
```
ERROR: Default port 8765 is already in use.
ERROR: Please stop the existing service with 'claude-mpm monitor stop'
ERROR: or specify a different port with --port.
```

**Solutions:**

1. **Stop existing monitor:**
   ```bash
   claude-mpm monitor stop
   ```

2. **Check what's using port 8765:**
   ```bash
   lsof -i :8765
   # or
   sudo lsof -i :8765
   ```

3. **Use different port:**
   ```bash
   claude-mpm-monitor --port 9000
   ```

### Health Check Fails But Port is Busy

**Scenario:** Port 8765 is busy, but health check returns nothing.

**Cause:** Another service (not claude-mpm-monitor) is using port 8765.

**Solution:**
```bash
# Find what's using the port
lsof -i :8765

# Stop that service or use different port
claude-mpm-monitor --port 9000
```

### Multiple Ports in Use

**Scenario:** You have monitors on multiple ports (8765, 8766, 8767).

**Cleanup:**
```bash
# Stop all monitors
pkill -f "claude-mpm.*monitor"

# Or stop specific ports
claude-mpm monitor stop --port 8765
claude-mpm monitor stop --port 8766
claude-mpm monitor stop --port 8767

# Verify all stopped
lsof -i :8765-8770
```

## Testing

Run the test suite to verify single-instance behavior:

```bash
./tools/dev/test_monitor_single_instance.sh
```

**Expected output:**
```
=== Testing Monitor Single Instance Enforcement ===

Test 1: Starting first monitor on default port 8765...
✅ Test 1 PASSED: Monitor running on port 8765

Test 2: Attempting to start second monitor (should reuse existing)...
✅ Test 2 PASSED: Second monitor detected existing instance

Test 3: Stopping first monitor...
✅ Test 3 PASSED: Port 8765 is now free

Test 4: Starting monitor on explicit port 9000...
✅ Test 4 PASSED: Monitor running on port 9000

Test 5: Attempting to start second monitor on port 9000 (should fail or reuse)...
✅ Test 5 PASSED: Port conflict detected correctly

=== All Tests Passed! ===
```

## Architecture Decisions

### Why Health Check Instead of PID File?

**PID File Approach:**
- ❌ Doesn't detect orphaned processes
- ❌ Can be stale (process died but file remains)
- ❌ Requires file I/O and cleanup logic

**Health Check Approach:**
- ✅ Verifies service is actually running
- ✅ Confirms it's our service (via `service` field)
- ✅ No file management required
- ✅ Works across different start methods (foreground, daemon)

### Why Default Port 8765?

1. **Convention**: Default WebSocket port range (8000-9000)
2. **Memorability**: Easy to remember (8765 = sequential digits)
3. **Conflict-Free**: Unlikely to conflict with common services
4. **Consistency**: Same port used across all Claude MPM installations

### Why No Auto-Increment?

**Old behavior problems:**
- 🐛 Multiple instances on different ports (confusing)
- 🐛 Dashboard shows events from one instance only
- 🐛 Port number unpredictable (was it 8765? 8766?)
- 🐛 Hard to script/automate (which port is monitor on?)

**New behavior benefits:**
- ✅ Single instance = single source of truth
- ✅ Predictable port = easier automation
- ✅ Explicit failures = clearer error messages
- ✅ Reuse existing = faster startup

## Related Files

- `src/claude_mpm/scripts/launch_monitor.py` - Main entry point (modified)
- `src/claude_mpm/services/monitor/daemon.py` - Daemon lifecycle
- `src/claude_mpm/services/monitor/daemon_manager.py` - Port management
- `src/claude_mpm/services/monitor/server.py` - Health endpoint
- `tools/dev/test_monitor_single_instance.sh` - Test suite

## Version History

- **v5.3.1**: Added single-instance enforcement
- **v5.3.0**: Multi-instance behavior (port auto-increment)
