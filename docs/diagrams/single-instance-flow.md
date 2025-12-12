# Single-Instance Monitor Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                User runs: claude-mpm-monitor                │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
         ┌────────────────────────┐
         │ Port specified?        │
         └────────┬───────────────┘
                  │
         ┌────────┴────────┐
         │                 │
      YES│                 │NO
         │                 │
         ▼                 ▼
    Use --port         Use DEFAULT_PORT
    (e.g., 9000)       (8765)
         │                 │
         └────────┬────────┘
                  │
                  ▼
         ┌────────────────────────┐
         │ check_existing_monitor │
         │ GET /health endpoint   │
         └────────┬───────────────┘
                  │
         ┌────────┴────────┐
         │                 │
      YES│                 │NO
         │                 │
         ▼                 │
    ┌─────────────┐        │
    │ Reuse       │        │
    │ existing    │        │
    │ instance    │        │
    └──────┬──────┘        │
           │               │
           │               ▼
           │      ┌────────────────────┐
           │      │ _is_port_available │
           │      │ Try binding to port│
           │      └────────┬───────────┘
           │               │
           │      ┌────────┴────────┐
           │      │                 │
           │   YES│                 │NO
           │      │                 │
           │      ▼                 ▼
           │  ┌─────────┐      ┌─────────┐
           │  │ Start   │      │ Fail    │
           │  │ new     │      │ with    │
           │  │ instance│      │ error   │
           │  └────┬────┘      └────┬────┘
           │       │                │
           │       ▼                ▼
           │  ┌─────────┐      "Port XXXX
           │  │ Monitor │       is already
           │  │ running │       in use..."
           │  │ on port │
           │  └────┬────┘
           │       │
           └───────┴─────────────┐
                   │              │
                   ▼              ▼
         ┌──────────────────────────┐
         │ Open browser (if allowed)│
         └──────────────────────────┘
```

## Decision Points

### 1. Port Selection
- **User specified `--port XXXX`**: Use that exact port
- **No `--port` flag**: Use `DEFAULT_PORT = 8765`
- **Never auto-increment**: No fallback to 8766, 8767, etc.

### 2. Existing Monitor Check
- **HTTP GET** to `http://localhost:{port}/health`
- **Success + service match**: Reuse existing instance
- **Failure or service mismatch**: Continue to port check

### 3. Port Availability Check
- **Try binding**: `socket.bind((host, port))`
- **Success**: Port is free, proceed with startup
- **Failure**: Port is busy, fail with clear error

## Error Messages

### Default Port Busy
```
Error: Default port 8765 is already in use by another service.
Please stop the existing service with 'claude-mpm monitor stop'
or specify a different port with --port.
```

### Explicit Port Busy
```
Error: Port 9000 is already in use by another service.
Please stop the existing service or choose a different port.
```

## Success Scenarios

### Scenario A: Fresh Start
```
User: claude-mpm-monitor
  → No existing monitor detected
  → Port 8765 is free
  → Start new instance on port 8765
  → Open browser to http://localhost:8765
```

### Scenario B: Reuse Existing
```
User: claude-mpm-monitor
  → Existing monitor detected at http://localhost:8765/health
  → Reuse that instance
  → Open browser to http://localhost:8765
  → No new instance started
```

### Scenario C: Explicit Port
```
User: claude-mpm-monitor --port 9000
  → No existing monitor on port 9000
  → Port 9000 is free
  → Start new instance on port 9000
  → Open browser to http://localhost:9000
  → Port 8765 remains free (not taken)
```

## Component Responsibilities

### `launch_monitor.py` (Main Entry Point)
- Parse command-line arguments
- Determine target port (default or explicit)
- Check for existing monitor via health endpoint
- Validate port availability
- Start new instance or reuse existing
- Open browser (unless `--no-browser`)

### `DaemonManager` (Port Management)
- `_is_port_available()`: Test port binding
- `cleanup_port_conflicts()`: Kill processes on port
- `is_our_service()`: Check if service is ours
- `is_running()`: Check if daemon is running

### `UnifiedMonitorServer` (HTTP Server)
- Expose `/health` endpoint with service metadata
- Bind to specified port (fails if busy)
- Handle Socket.IO connections
- Serve dashboard static files

## Thread Safety

**Single-instance check is NOT thread-safe** by design:
- Each `claude-mpm-monitor` invocation is a separate process
- Race condition window: ~100ms between health check and port binding
- **Acceptable risk**: Extremely rare in practice
- **Mitigation**: Port binding fails atomically if race occurs

## Multi-Process Coordination

**How multiple launches coordinate:**

1. **Process A** starts first:
   - Health check: No monitor found
   - Port check: Port free
   - Bind to port 8765
   - Write PID file

2. **Process B** starts second:
   - Health check: Monitor found at 8765
   - Reuse Process A's instance
   - Exit without binding

3. **Process C** (different port):
   - Health check: No monitor on 9000
   - Port check: Port 9000 free
   - Bind to port 9000
   - Write PID file (different from A)

**Each port is independent.**

## Cleanup on Exit

```
Monitor shutdown:
  1. Stop accepting new connections
  2. Close Socket.IO server
  3. Stop health monitoring
  4. Release port binding
  5. Remove PID file
  6. Clean up asyncio resources
```

**Port is freed** after shutdown, allowing new instances to bind.

## Performance Characteristics

- **Health check latency**: ~50ms (HTTP request)
- **Port binding check**: ~1ms (socket operation)
- **Total startup overhead**: ~100-200ms
- **Reuse scenario**: ~50ms (just health check)

**Conclusion:** Single-instance check adds minimal overhead.
