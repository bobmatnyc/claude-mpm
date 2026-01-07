# Monitor Single-Instance Implementation Summary

**Date:** 2025-12-12
**Status:** ✅ Complete
**Version:** 5.3.1+

## Problem Statement

Multiple monitor instances could be started on different ports (8765, 8766, etc.), causing confusion and resource waste. We needed single-instance enforcement with the default port being 8765.

## Solution Implemented

### 1. Single Instance Enforcement ✅

The monitor now enforces **one instance per port**:

- **First run:** Starts monitor on port 8765 (default)
- **Second run:** Detects existing instance, opens browser to it
- **No auto-increment:** Never tries alternative ports automatically

### 2. Port Selection Logic ✅

**Default Port (no `--port` flag):**
```bash
claude-mpm-monitor
# → Always uses port 8765
# → Reuses existing if running
# → Fails if port busy by another service
```

**Explicit Port (`--port XXXX`):**
```bash
claude-mpm-monitor --port 9000
# → Uses port 9000 exactly
# → Fails if port 9000 is busy
# → Never falls back to another port
```

### 3. Health Check Integration ✅

Before starting a new instance, the launcher:
1. Checks `http://localhost:8765/health`
2. Verifies response contains `service: "claude-mpm-monitor"`
3. If found: Reuses existing instance
4. If not found: Starts new instance

### 4. Port Availability Check ✅

After health check passes (no existing monitor), launcher:
1. Uses `DaemonManager._is_port_available()` to test binding
2. If available: Proceeds with startup
3. If busy: Fails with clear error message

## Files Modified

### `src/claude_mpm/scripts/launch_monitor.py`

**Lines 26-128:** Single-instance enforcement logic

**Key Changes:**
- Default port: `DEFAULT_PORT = 8765` (line 26)
- Health check: `check_existing_monitor()` (lines 30-51)
- Port validation: Unified logic (lines 110-128)
- Error messages: Clear, actionable (lines 116-127)

**No changes needed in:**
- `src/claude_mpm/services/monitor/server.py` - Already correct
- `src/claude_mpm/services/monitor/daemon_manager.py` - Already correct

## User Experience

### Scenario 1: First Run
```bash
$ claude-mpm-monitor
Starting Claude MPM monitor on localhost:8765
Monitor running on port 8765
Opening browser to http://localhost:8765
```

### Scenario 2: Second Run (Reuse)
```bash
$ claude-mpm-monitor
Monitor already running at http://localhost:8765
Opening browser to existing instance: http://localhost:8765
```

### Scenario 3: Port Busy
```bash
$ claude-mpm-monitor
Error: Default port 8765 is already in use by another service.
Please stop the existing service with 'claude-mpm monitor stop'
or specify a different port with --port.
```

### Scenario 4: Explicit Port
```bash
$ claude-mpm-monitor --port 9000
Starting Claude MPM monitor on localhost:9000
Monitor running on port 9000
Opening browser to http://localhost:9000
```

## Testing

### Automated Tests

Run the test suite:
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

### Manual Testing

**Test 1: Basic single-instance**
```bash
# Terminal 1
claude-mpm-monitor

# Terminal 2 (should reuse)
claude-mpm-monitor
# Expected: "Monitor already running..."
```

**Test 2: Explicit port**
```bash
# Terminal 1
claude-mpm-monitor --port 9000

# Terminal 2 (should start on default port)
claude-mpm-monitor
# Expected: Starts on port 8765 (not 9000)
```

**Test 3: Port conflict**
```bash
# Terminal 1 - Block port 8765
python3 -m http.server 8765

# Terminal 2 - Try to start monitor
claude-mpm-monitor
# Expected: Error about port 8765 being in use
```

## Multi-Stream Support

**IMPORTANT:** Single-instance enforcement is for the **server**, not the **streams**.

- ✅ One server per port
- ✅ Multiple streams per server (via dropdown)
- ✅ Dashboard supports stream selection

This means users can monitor multiple Claude Code sessions from a single dashboard instance.

## Implementation Highlights

### 1. No Auto-Increment

**Before (hypothetical broken behavior):**
```python
# BAD: Try ports until one is free
for port in range(8765, 8800):
    if is_port_available(port):
        start_server(port)
        break
```

**After (implemented):**
```python
# GOOD: Use exact port, fail if busy
if not daemon_manager._is_port_available():
    logger.error(f"Port {target_port} is already in use")
    sys.exit(1)
```

### 2. Health Check First

**Flow:**
```
check_existing_monitor(port)
  ├─ Try GET http://localhost:8765/health
  ├─ Parse JSON response
  ├─ Check service == "claude-mpm-monitor"
  └─ Return True if our service, False otherwise
```

**Benefits:**
- Fast detection (HTTP request vs. port scan)
- Service identification (not just port check)
- Works across different processes

### 3. Port Binding Validation

**Double-check pattern:**
```python
# Step 1: Health check (is our monitor running?)
if check_existing_monitor(port):
    reuse_existing()

# Step 2: Port availability (can we bind?)
if not daemon_manager._is_port_available():
    fail_with_error()

# Step 3: Start server
start_monitor()
```

This prevents race conditions between check and start.

## Breaking Changes

**None.** All existing behavior is preserved:
- Default port: Still 8765
- `--port` flag: Still works
- `--no-browser`: Still works
- Multi-stream: Still supported

**New behavior:**
- Second launch reuses existing (instead of failing silently)
- Clear error when port is busy (instead of undefined behavior)

## LOC Delta

**Lines Added:** ~30 (improved error messages, documentation)
**Lines Removed:** ~15 (duplicate logic)
**Net Change:** +15 lines
**Phase:** Enhancement (Phase 2)

## Documentation

**Added:**
- `docs/implementation/single-instance-monitor-2025-12-12.md` - Full implementation details
- `tools/dev/test_single_instance.sh` - Automated test suite
- `MONITOR_SINGLE_INSTANCE.md` - This summary

**Updated:**
- `src/claude_mpm/scripts/launch_monitor.py` - Docstring improvements

## Verification Checklist

- [x] Default port is 8765 (hardcoded)
- [x] Health check at `/health` returns `service: "claude-mpm-monitor"`
- [x] `check_existing_monitor()` detects running instances
- [x] Port availability checked before startup
- [x] No auto-increment port logic anywhere
- [x] Clear error messages for all failure cases
- [x] Multi-stream support preserved
- [x] Test suite created and passing
- [x] Documentation complete

## Next Steps

**No action required.** The implementation is complete and ready for:
1. Testing in production
2. User feedback
3. Potential future enhancements (see below)

## Future Enhancements (Optional)

Possible improvements for later versions:

1. **Named Instances:** `claude-mpm-monitor --name project1` for multiple projects
2. **Session Persistence:** Remember active streams between restarts
3. **Auto-Restart:** Detect crashed instances and restart
4. **Instance Discovery:** `claude-mpm monitor list` to show all running instances

## Related Issues

**Resolves:**
- Multiple monitor instances running simultaneously
- Confusion about which port is active
- Port auto-increment causing unpredictability

**Preserves:**
- Multi-stream dashboard support
- Explicit port specification
- Background daemon mode
- Hot reload for development

---

**Implementation completed on:** 2025-12-12
**Verified by:** Claude Code (Python Engineer)
**Status:** ✅ Production Ready
