# Dashboard Stability Solution: HTTP POST Event Flow

## Problem Statement

The dashboard was experiencing constant disconnection issues due to the ephemeral nature of hook handlers. Each hook handler process spawns, runs for less than 1 second, and terminates. This lifecycle is incompatible with persistent SocketIO connections, causing:

- Constant connect/disconnect cycles
- Lost events during connection establishment
- Dashboard instability and missing events
- Complex connection pool management overhead

## Root Cause

Hook handlers are **ephemeral processes** that:
- Spawn for each Claude Code event
- Live for < 1 second
- Die immediately after processing
- Cannot maintain persistent connections

## Solution: Stateless HTTP POST

We've implemented a stable solution that embraces the ephemeral nature of hook handlers:

### Architecture

```
┌─────────────────┐  HTTP POST   ┌──────────────────┐  WebSocket  ┌────────────┐
│  Hook Handler   │──────────────►│  SocketIO Server │────────────►│  Dashboard │
│  (ephemeral)    │  /api/events  │   (persistent)   │  broadcast  │   (client) │
└─────────────────┘               └──────────────────┘             └────────────┘
```

### Key Changes

1. **Hook Handlers**: Use simple HTTP POST requests (fire-and-forget pattern)
2. **SocketIO Server**: Added `/api/events` HTTP endpoint to receive events
3. **Dashboard**: Maintains stable WebSocket connection to server (unchanged)

## Implementation Details

### 1. HTTP-Based Connection Manager

Located at: `src/claude_mpm/hooks/claude_hooks/services/connection_manager_http.py`

- Uses `requests.post()` with 500ms timeout
- Fire-and-forget pattern (doesn't wait for response)
- No connection management needed
- Gracefully handles server unavailability

### 2. Server HTTP API Endpoint

Added to: `src/claude_mpm/services/socketio/server/core.py`

```python
# POST /api/events endpoint
- Receives JSON events from hook handlers
- Broadcasts to all connected dashboard clients
- Returns 204 No Content for success
- Buffers events for late-joining clients
```

### 3. Backward Compatibility

- EventBus integration remains for in-process subscribers
- Dashboard WebSocket connection unchanged
- All existing event formats preserved

## Benefits

1. **Stability**: No more disconnection issues
2. **Simplicity**: Stateless communication matches process lifecycle
3. **Performance**: Minimal overhead, no handshakes
4. **Reliability**: Server handles buffering and retries
5. **Scalability**: Can handle many ephemeral processes

## Testing

### Run Tests

```bash
# Test HTTP event flow
python scripts/test_http_event_flow.py

# Test hook handler integration
python scripts/test_hook_http_integration.py

# Monitor dashboard events
python scripts/monitor_dashboard_events.py
```

### Expected Results

All tests should pass with:
- ✅ Events delivered successfully
- ✅ No disconnection errors
- ✅ Rapid-fire events handled correctly

## Configuration

### Environment Variables

- `CLAUDE_MPM_SERVER_HOST`: Server hostname (default: localhost)
- `CLAUDE_MPM_SERVER_PORT`: Server port (default: 8765)
- `CLAUDE_MPM_HOOK_DEBUG`: Enable debug output (default: true)

### Server Requirements

The SocketIO server must be running with the HTTP API endpoint enabled. This is automatic in the latest version.

## Migration Guide

If you're upgrading from the old SocketIO connection pool approach:

1. **No code changes needed**: The system automatically uses the new HTTP approach
2. **Server restart required**: Restart the SocketIO server to enable the HTTP endpoint
3. **Verify functionality**: Run the test scripts to confirm events are flowing

## Troubleshooting

### No Events Appearing

1. Check server is running: `curl http://localhost:8765/`
2. Verify HTTP endpoint: `curl -X POST http://localhost:8765/api/events -H "Content-Type: application/json" -d '{"test": "event"}'`
3. Run monitor script: `python scripts/monitor_dashboard_events.py`

### Server Not Available

- Hook handlers gracefully handle server unavailability
- Events are lost if server is down (acceptable trade-off for stability)
- Start server with: `claude-mpm server start`

### Debug Mode

Enable debug output to see event flow:
```bash
export CLAUDE_MPM_HOOK_DEBUG=true
```

## Architecture Decision Record (ADR)

### Decision

Use stateless HTTP POST for hook handler → server communication instead of persistent SocketIO connections.

### Context

Hook handlers are ephemeral processes with sub-second lifetimes, incompatible with connection-oriented protocols.

### Consequences

**Positive:**
- Eliminates disconnection issues completely
- Simplifies implementation
- Matches natural process lifecycle
- Better performance (no handshakes)

**Negative:**
- Events lost if server is down (rare)
- Slightly higher latency (negligible in practice)

**Neutral:**
- Different communication pattern for different components

### Status

✅ **Implemented and tested** - This solution permanently fixes dashboard stability issues.

## Summary

The HTTP POST solution provides a stable, simple, and performant way for ephemeral hook handlers to communicate with the persistent SocketIO server. By embracing the stateless nature of hook handlers rather than fighting it, we've eliminated disconnection issues while maintaining full functionality.