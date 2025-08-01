# Troubleshooting Guide

This guide helps diagnose and fix common issues with the Claude MPM Dashboard and WebSocket system.

## Common Issues

### Dashboard Won't Connect

#### Symptoms
- "WebSocket connection failed" error
- Dashboard shows "Disconnected" status
- No events appearing

#### Solutions

1. **Check WebSocket server is running**:
   ```bash
   ps aux | grep websocket.*8765
   ```

2. **Start the server manually**:
   ```bash
   python scripts/websocket_server_production.py
   ```

3. **Fix IPv6/IPv4 issues**:
   - Dashboard connects to `ws://127.0.0.1:8765`
   - NOT `ws://localhost:8765` (IPv6 issues)

4. **Check port availability**:
   ```bash
   lsof -i :8765
   ```

5. **Kill existing processes**:
   ```bash
   lsof -ti :8765 | xargs kill -9
   ```

### Keystroke Latency

#### Symptoms
- Typing feels sluggish
- Delayed response to keystrokes
- UI freezing

#### Solutions

1. **Ensure optimized handler is used**:
   ```bash
   # Check hook_handler.py contains ClaudeHookHandler
   grep "class ClaudeHookHandler" src/claude_mpm/hooks/claude_hooks/hook_handler.py
   ```

2. **Check for blocking operations**:
   ```bash
   # Look for .result() calls
   grep -n "\.result(" src/claude_mpm/services/websocket_server.py
   ```

3. **Clear Python cache**:
   ```bash
   find . -name "*.pyc" -delete
   find . -name "__pycache__" -type d -exec rm -rf {} +
   ```

### Events Not Appearing

#### Symptoms
- Dashboard connected but no events
- Hook handler running but silent
- Missing specific event types

#### Solutions

1. **Check hook configuration**:
   ```bash
   cat .claude/settings.json | jq '.hooks'
   ```

2. **Test hook handler directly**:
   ```bash
   echo '{"hook_event_name": "UserPromptSubmit", "prompt": "test"}' | \
   python src/claude_mpm/hooks/claude_hooks/hook_handler.py
   ```

3. **Monitor WebSocket traffic**:
   ```bash
   python scripts/monitor_websocket_events.py
   ```

4. **Check session filtering**:
   - Dashboard URL should match session
   - Use `?session=global` for all events

### Hook Errors

#### Symptoms
- "PreToolUse:Edit failed with status code 1"
- Import errors in hook handler
- NameError exceptions

#### Solutions

1. **Check Python path**:
   ```bash
   # In hook_wrapper.sh
   export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"
   ```

2. **Verify imports**:
   ```python
   # Test imports
   python -c "from claude_mpm.services.websocket_server import get_websocket_server"
   ```

3. **Check virtual environment**:
   ```bash
   which python
   pip list | grep websockets
   ```

## Diagnostic Tools

### WebSocket Connection Test

```bash
# Test basic connection
python scripts/verify_websocket_connection.py

# Expected output:
# Connecting to ws://127.0.0.1:8765...
# ✅ Connected successfully!
```

### Hook Handler Test

```bash
# Test hook processing
cat > test_event.json << EOF
{
  "hook_event_name": "UserPromptSubmit",
  "prompt": "Test prompt",
  "session_id": "test-123",
  "cwd": "/tmp"
}
EOF

cat test_event.json | python src/claude_mpm/hooks/claude_hooks/hook_handler.py
# Should output: {"action": "continue"}
```

### WebSocket Monitor

```bash
# Real-time event monitoring
python scripts/monitor_websocket_events.py

# In another terminal, trigger events
python scripts/test_hook_broadcast_simple.py
```

### Process Check

```bash
# Check all related processes
ps aux | grep -E "claude|websocket|8765" | grep -v grep

# Check port usage
netstat -an | grep 8765
lsof -i :8765
```

## Debug Logging

### Enable Debug Mode

```bash
# For hook handler (not recommended - causes latency)
export CLAUDE_MPM_HOOK_DEBUG=true

# For WebSocket server
export PYTHONUNBUFFERED=1
python -u scripts/websocket_server_production.py
```

### Check Log Files

```bash
# Hook debug log (if enabled)
tail -f /tmp/claude-mpm-hook.log

# WebSocket server log
tail -f /tmp/websocket_manager.log

# Python errors
tail -f ~/.claude-mpm/logs/error.log
```

## Performance Diagnostics

### Measure Hook Latency

```python
# measure_hook_latency.py
import time
import subprocess
import json

event = {
    "hook_event_name": "UserPromptSubmit",
    "prompt": "test"
}

start = time.perf_counter()
result = subprocess.run(
    ["python", "src/claude_mpm/hooks/claude_hooks/hook_handler.py"],
    input=json.dumps(event),
    capture_output=True,
    text=True
)
end = time.perf_counter()

print(f"Hook latency: {(end - start) * 1000:.2f}ms")
```

### Monitor WebSocket Performance

```python
# monitor_ws_performance.py
import asyncio
import websockets
import time
import statistics

async def measure_latency():
    times = []
    
    async with websockets.connect("ws://127.0.0.1:8765") as ws:
        for i in range(100):
            start = time.perf_counter()
            await ws.ping()
            await ws.pong()
            times.append(time.perf_counter() - start)
            
    print(f"Median latency: {statistics.median(times)*1000:.2f}ms")
    print(f"P99 latency: {statistics.quantiles(times, n=100)[98]*1000:.2f}ms")

asyncio.run(measure_latency())
```

## Recovery Procedures

### Full Reset

```bash
# 1. Stop all processes
pkill -f "websocket.*8765"
pkill -f "claude-mpm"

# 2. Clear cache
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +

# 3. Clear logs
rm -f /tmp/claude-mpm-hook.log
rm -f /tmp/websocket*.log

# 4. Restart WebSocket server
python scripts/websocket_server_manager.py &

# 5. Test connection
python scripts/verify_websocket_connection.py
```

### Reinstall Hooks

```bash
# 1. Backup current settings
cp .claude/settings.json .claude/settings.json.bak

# 2. Reinstall hooks
claude-mpm init

# 3. Verify configuration
cat .claude/settings.json
```

## Known Issues

### Issue: WebSocket v15 Deprecation Warnings

**Symptom**: 
```
DeprecationWarning: websockets.WebSocketServerProtocol is deprecated
```

**Status**: Cosmetic issue, doesn't affect functionality

**Fix**: Will be addressed in future update

### Issue: "Unknown command: None" in logs

**Symptom**: 
```
Unknown command: None
```

**Status**: Harmless, related to nohup output redirection

**Fix**: Can be ignored

### Issue: Multiple Claude Sessions

**Problem**: Events from different sessions appear in dashboard

**Solution**: Use session filtering
```
?session=your-session-id
```

## Getting Help

### Collect Diagnostic Information

```bash
# System info
uname -a
python --version
pip show websockets

# Process info
ps aux | grep -E "claude|websocket"

# Port info
lsof -i :8765

# Recent errors
tail -100 /tmp/claude-mpm-hook.log 2>/dev/null
```

### Report Issues

Include:
1. Error messages
2. Steps to reproduce
3. System information
4. Relevant log files

### Quick Fixes

1. **Restart everything**: Often solves transient issues
2. **Check basics**: Server running, correct port, proper URL
3. **Clear cache**: Python cache can cause import errors
4. **Update dependencies**: `pip install -U websockets`