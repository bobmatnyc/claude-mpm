# Event Emission Architecture

## Overview

This document defines the **single-path event emission architecture** implemented to eliminate duplicate events and improve performance in the Claude MPM hook system.

## 🎯 **Core Principle: Single Emission Path**

**CRITICAL**: Events must flow through **ONE primary path** with **ONE fallback path** only. Multiple parallel emission paths create duplicate events.

## Architecture Diagram

```
Hook Handler → ConnectionManager → Direct Socket.IO → Dashboard
                                ↓ (fallback only)
                              HTTP POST → Monitor Server → Dashboard
```

## Event Flow

### 1. Hook Event Generation
- Claude Code triggers hook events (PreToolUse, PostToolUse, etc.)
- Hook handler receives event via stdin
- Event is processed once by ClaudeHookHandler

### 2. Event Emission (Single Path)
```python
# PRIMARY PATH: Direct Socket.IO
if self.connection_pool:
    try:
        self.connection_pool.emit("claude_event", event_data)
        return  # SUCCESS - no fallback needed
    except Exception:
        # Fall through to HTTP fallback
        pass

# FALLBACK PATH: HTTP POST (only if direct fails)
self._try_http_fallback(event_data)
```

### 3. Event Reception
- Monitor server receives events via Socket.IO or HTTP
- Events are normalized and broadcast to dashboard clients
- Dashboard displays events in real-time

## 🚫 **Anti-Patterns (FORBIDDEN)**

### ❌ Multiple Parallel Emission Paths
```python
# WRONG - Creates duplicates
self.connection_pool.emit("claude_event", data)  # Path 1
self.event_bus.publish("hook.event", data)       # Path 2 (duplicate!)
self.http_client.post("/events", data)           # Path 3 (duplicate!)
```

### ❌ EventBus Relay Pattern
```python
# WRONG - EventBus relay re-emits events already sent directly
event_bus.publish("hook.event", data)  # Original emission
# ... later in relay ...
socketio.emit("claude_event", data)    # Duplicate emission!
```

### ❌ Buffering Without Deduplication
```python
# WRONG - Multiple buffers can create duplicates
buffer1.append(event)  # Hook handler buffer
buffer2.append(event)  # EventBus buffer
buffer3.append(event)  # Socket.IO buffer
```

## ✅ **Correct Implementation**

### Connection Manager Service
```python
class ConnectionManagerService:
    def emit_event(self, namespace: str, event: str, data: dict):
        """Single-path emission with HTTP fallback."""
        
        # Normalize event data
        event_data = self.event_normalizer.normalize(raw_event).to_dict()
        
        # PRIMARY: Direct Socket.IO (ultra-low latency)
        if self.connection_pool:
            try:
                self.connection_pool.emit("claude_event", event_data)
                return  # Success - no fallback needed
            except Exception as e:
                if DEBUG:
                    print(f"⚠️ Direct emission failed: {e}")
        
        # FALLBACK: HTTP POST (reliability)
        self._try_http_fallback(event_data)
    
    def _try_http_fallback(self, event_data: dict):
        """HTTP fallback when direct Socket.IO fails."""
        try:
            response = requests.post(
                "http://localhost:8765/api/events",
                json=event_data,
                timeout=2.0
            )
            if response.status_code in [200, 204]:
                if DEBUG:
                    print("✅ HTTP fallback successful")
        except Exception as e:
            if DEBUG:
                print(f"⚠️ HTTP fallback failed: {e}")
```

## Performance Characteristics

### Direct Socket.IO Path
- **Latency**: ~0.1ms (in-process)
- **Throughput**: 10,000+ events/second
- **Memory**: Minimal (no buffering)
- **Reliability**: High (connection pooling)

### HTTP Fallback Path
- **Latency**: ~2-5ms (cross-process)
- **Throughput**: 1,000+ events/second
- **Memory**: Minimal (stateless)
- **Reliability**: Very high (HTTP protocol)

## Debugging and Monitoring

### Debug Mode
```bash
export CLAUDE_MPM_HOOK_DEBUG=true
```

### Expected Log Output (Single Event)
```
[2025-09-03T23:04:01.582175] Processing hook event: PreToolUse (PID: 10835)
✅ Async emit successful: pre_tool
```

### Warning Signs (Duplicates)
```
# BAD - Multiple emissions for same event
✅ Emitted via connection pool: pre_tool
✅ Published to EventBus: hook.pre_tool
✅ HTTP POST successful: pre_tool
```

## Testing Guidelines

### Unit Tests
- Test single emission path only
- Mock connection failures to test fallback
- Verify no duplicate emissions

### Integration Tests
- Monitor dashboard for duplicate events
- Check event timestamps for uniqueness
- Verify event ordering

### Performance Tests
- Measure emission latency
- Test under high event volume
- Verify memory usage remains stable

## Migration Notes

### From EventBus Architecture
1. **Remove EventBus imports** from connection managers
2. **Remove EventBus initialization** code
3. **Remove EventBus emission calls**
4. **Remove EventBus relay services**
5. **Update tests** to expect single emission path

### Backward Compatibility
- Connection pool interface unchanged
- Event data format unchanged
- Dashboard API unchanged
- Only emission path simplified

## Maintenance Guidelines

### Code Reviews
- ✅ Verify single emission path
- ✅ Check for EventBus references (forbidden)
- ✅ Ensure proper fallback handling
- ✅ Validate event normalization

### Performance Monitoring
- Track emission latency
- Monitor duplicate event rates (should be 0%)
- Watch memory usage trends
- Alert on fallback usage spikes

### Future Enhancements
- Consider event batching for high volume
- Add emission retry logic
- Implement event compression
- Add emission metrics collection

## Troubleshooting

### No Events Reaching Dashboard
1. Check Socket.IO connection pool
2. Verify HTTP fallback endpoint
3. Check monitor server status
4. Review hook handler logs

### Duplicate Events (Should Not Happen)
1. **CRITICAL**: Check for EventBus references
2. Verify single emission path
3. Check for multiple connection managers
4. Review event normalization logic

### Performance Issues
1. Monitor direct vs fallback usage
2. Check connection pool health
3. Review event data size
4. Verify no memory leaks

## Version History

- **v4.0.25+**: Single-path architecture implemented
- **Pre-v4.0.25**: EventBus multi-path architecture (deprecated)

---

**Remember**: The key to stability is maintaining the **single emission path principle**. Any deviation from this pattern risks reintroducing duplicate events.
