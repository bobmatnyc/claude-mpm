# Single-Instance Monitor Implementation

**Date:** 2025-12-12
**Status:** Implemented
**Related Files:**
- `src/claude_mpm/scripts/launch_monitor.py`
- `src/claude_mpm/services/monitor/server.py`
- `src/claude_mpm/services/monitor/daemon_manager.py`

## Overview

The Claude MPM monitor now enforces single-instance behavior, ensuring only ONE server instance runs at a time on the default port (8765).

## Implementation Details

### 1. Default Port: 8765 (Hardcoded)

```python
DEFAULT_PORT = 8765
```

This is the standard port for all Claude MPM monitor instances unless explicitly overridden.

### 2. Health Check Endpoint

The monitor exposes a `/health` endpoint that returns:

```json
{
  "status": "running",
  "service": "claude-mpm-monitor",
  "version": "5.3.1",
  "port": 8765,
  "pid": 12345,
  "uptime": 300
}
```

The `service` field is critical for identifying our service vs. other services on the same port.

### 3. Single-Instance Enforcement Flow

```
User runs: claude-mpm-monitor

1. Check existing monitor on port 8765
   ├─ YES → Reuse existing, open browser
   └─ NO → Continue to step 2

2. Check if port 8765 is available
   ├─ YES → Start new instance
   └─ NO → Fail with error message

3. Start monitor on port 8765
   └─ Bind to port (fails if busy)
```

### 4. Port Selection Logic

**Default behavior (no `--port` flag):**
- Always use port 8765
- Check if our monitor is already running
- If yes: Reuse existing, open browser
- If no: Check if port is free
  - Free: Start new instance
  - Busy: Fail with error

**Explicit port (`--port XXXX`):**
- Use specified port exactly
- Check if our monitor is already running on that port
- If yes: Reuse existing, open browser
- If no: Check if port is free
  - Free: Start new instance
  - Busy: Fail with error

**Never auto-increment** - No fallback to port 8766, 8767, etc.

### 5. User Experience Examples

**First run:**
```bash
$ claude-mpm-monitor
Starting Claude MPM monitor on localhost:8765
Monitor running on port 8765
Opening browser to http://localhost:8765
```

**Second run (reuses existing):**
```bash
$ claude-mpm-monitor
Monitor already running at http://localhost:8765
Opening browser to existing instance: http://localhost:8765
```

**Port busy by another service:**
```bash
$ claude-mpm-monitor
Error: Default port 8765 is already in use by another service.
Please stop the existing service with 'claude-mpm monitor stop'
or specify a different port with --port.
```

**Explicit port:**
```bash
$ claude-mpm-monitor --port 9000
Starting Claude MPM monitor on localhost:9000
Monitor running on port 9000
Opening browser to http://localhost:9000
```

**Explicit port busy:**
```bash
$ claude-mpm-monitor --port 9000
Error: Port 9000 is already in use by another service.
Please stop the existing service or choose a different port.
```

## Testing

Run the test suite to verify single-instance behavior:

```bash
./tools/dev/test_single_instance.sh
```

**Test Coverage:**
1. ✅ First instance starts on default port 8765
2. ✅ Second instance detects existing and reuses
3. ✅ Health endpoint returns correct service name
4. ✅ Port 8765 is occupied (can't double-bind)
5. ✅ Port is released after stop
6. ✅ Explicit port works (e.g., 9000)
7. ✅ Default port remains free when using explicit port
8. ✅ Explicit port fails if busy

## Code Changes

### `launch_monitor.py` (Lines 88-128)

**Before:**
- Separate port checking logic for user-specified vs. default
- Duplicated daemon manager creation

**After:**
- Single daemon manager instance for port checking
- Unified error messages
- Clear distinction between default and explicit port behavior

**Key Change:**
```python
# Create daemon manager once for port checking
daemon_manager = DaemonManager(port=target_port, host=args.host)

if not daemon_manager._is_port_available():
    if user_specified_port:
        # Explicit port error
    else:
        # Default port error
```

## Benefits

1. **No Accidental Multiple Instances:** Only one monitor runs per port
2. **Predictable Port:** Always 8765 unless explicitly overridden
3. **No Port Scanning:** Never auto-increments to find free port
4. **Clear Error Messages:** Users know exactly what's wrong
5. **Fast Reuse:** Existing instance detected instantly via health check

## Multi-Instance Support

While single-instance is enforced **per port**, you can still run multiple monitors on different ports if needed:

```bash
# Terminal 1: Default instance
claude-mpm-monitor  # Runs on 8765

# Terminal 2: Second instance on different port
claude-mpm-monitor --port 9000  # Runs on 9000
```

Each port enforces single-instance behavior independently.

## Stream Selection

**IMPORTANT:** The dashboard supports **multiple streams** via the dropdown selector. Single-instance enforcement is for the **server**, not the streams.

- ✅ One server instance per port
- ✅ Multiple streams accessible from one instance
- ✅ Stream dropdown in dashboard UI

This means users can monitor multiple Claude Code sessions from a single dashboard instance.

## Migration Notes

**No breaking changes** - Existing behavior is preserved:
- Default port remains 8765
- `--port` flag works as before
- `--no-browser` flag works as before
- Dashboard multi-stream support unchanged

**New behavior:**
- Second `claude-mpm-monitor` call reuses existing instance instead of failing
- Clear error when port is busy (instead of trying alternative ports)

## Future Enhancements

Possible improvements for future versions:

1. **Named Instances:** Allow multiple monitors with names (e.g., `--name project1`)
2. **Session Persistence:** Remember which streams were active
3. **Auto-Restart:** Detect and restart crashed instances
4. **Port Discovery:** Command to list all running monitor instances

## Related Documentation

- [Monitor Server Architecture](../architecture/monitor-server.md)
- [Daemon Management](../architecture/daemon-management.md)
- [Health Check API](../api/health-check.md)
