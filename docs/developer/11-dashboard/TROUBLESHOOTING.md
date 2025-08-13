# Socket.IO Dashboard Troubleshooting Guide

This guide provides solutions for common issues with the Socket.IO dashboard and debugging procedures for the real-time monitoring system.

## Common Issues & Solutions

### File Operations Not Showing in Files Tab

**Symptoms:**
- Dashboard connects successfully
- Events appear in Events tab
- Files tab remains empty or shows no file operations

**Root Causes & Solutions:**

#### 1. Tool Name Case Sensitivity Issue

**Problem**: Claude Code sends lowercase tool names ("read", "write") but dashboard expects capitalized names.

**Solution**: This was fixed in file-tool-tracker.js v1.1. Verify you have the latest version:

```bash
# Check cache busting in dashboard HTML
grep "file-tool-tracker.js" src/claude_mpm/dashboard/templates/index.html
# Should show: file-tool-tracker.js?v=1.1 or higher
```

**Force Update**:
```bash
# Clear browser cache and reload dashboard
# Or use Ctrl+F5 (hard reload)
```

#### 2. Event Format Mismatch

**Problem**: Events don't contain expected tool_name or file_path fields.

**Debug Steps**:
```javascript
// Open browser console in dashboard
// Check raw events in Events tab for structure
console.log('Event structure:', event);

// Look for:
// - event.tool_name (should exist for file operations)
// - event.tool_parameters.file_path (should contain file path)
// - event.type === 'hook' and event.subtype in ['pre_tool', 'post_tool']
```

**Solution**: Verify hook configuration is properly sending structured events.

#### 3. Missing Tool Support

**Problem**: Newer Claude Code tools not recognized by file tracker.

**Supported Tools** (case-insensitive):
- Read, Write, Edit, MultiEdit, NotebookEdit
- Grep, Glob, LS  
- Bash (with file operation detection)

**Add New Tool Support**:
```javascript
// Edit: src/claude_mpm/dashboard/static/js/components/file-tool-tracker.js
// Line ~332: Add new tool to fileTools array
const fileTools = ['read', 'write', 'edit', 'grep', 'multiedit', 'glob', 'ls', 'bash', 'notebookedit', 'newtool'];
```

### Dashboard Not Updating in Real-Time

**Symptoms:**
- Dashboard loads but shows no live events
- Events appear only after page refresh
- Connection status shows disconnected

**Solutions:**

#### 1. Socket.IO Server Not Running

**Check Server Status**:
```bash
# Verify Socket.IO server is running
netstat -an | grep 8765
# Should show: tcp4  0  0  127.0.0.1.8765  *.*  LISTEN

# Check server process
ps aux | grep socketio
```

**Start Server**:
```bash
# If not running, start with monitor flag
./claude-mpm --monitor

# Or start standalone server
python scripts/socketio_server_manager.py
```

#### 2. Port Conflicts

**Problem**: Port 8765 is already in use by another process.

**Check Port Usage**:
```bash
lsof -i :8765
# Shows what process is using port 8765
```

**Solutions**:
```bash
# Option 1: Kill conflicting process
sudo kill -9 <PID>

# Option 2: Use different port
export SOCKETIO_PORT=8766
./claude-mpm --monitor

# Option 3: Use available port finder
./claude-mpm --monitor --port auto
```

#### 3. Browser Connection Issues

**Check Browser Console**:
```javascript
// Look for connection errors in browser console
// Common errors:
// - "Failed to connect to Socket.IO server"
// - "Connection refused"
// - "WebSocket connection failed"
```

**Solutions**:
```bash
# 1. Verify dashboard URL
# Should be: http://localhost:8765 (not https://)

# 2. Check firewall/security software
# May block localhost connections

# 3. Try different browser
# Chrome, Firefox, Safari should all work
```

### Events Not Received from Claude Code

**Symptoms:**
- Dashboard connects successfully
- No events appear in any tab
- Socket.IO server shows no incoming events

**Debugging Steps:**

#### 1. Verify Hook Configuration

**Check Hook Setup**:
```bash
# Look for hook configuration
cat .claude/settings.json | grep -A 10 hooks

# Should contain claude-mpm hook wrapper
# Example hook:
{
  "hooks": {
    "UserPromptSubmit": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "/path/to/hook_wrapper.sh"
      }]
    }]
  }
}
```

**Manual Hook Test**:
```bash
# Test hook wrapper directly
./src/claude_mpm/hooks/claude_hooks/hook_wrapper.sh test_event '{"type":"test","message":"hello"}'

# Should show connection attempt to Socket.IO server
```

#### 2. Check Hook Handler Process

**Enable Debug Mode**:
```bash
export CLAUDE_MPM_HOOK_DEBUG=true
./claude-mpm --monitor

# This enables detailed hook logging
```

**Check Hook Logs**:
```bash
# Look for hook execution in logs
# Should show:
# - Hook triggered for events
# - Socket.IO connection attempts
# - Event forwarding attempts
```

#### 3. Test Event Injection

**Use Test Script**:
```bash
# Send test events directly to dashboard
python scripts/test_dashboard_file_viewer.py

# Should generate 8 test file operations
# Verify these appear in Files tab
```

### Dashboard Performance Issues

**Symptoms:**
- Dashboard becomes slow with many events
- Browser becomes unresponsive
- High memory usage

**Solutions:**

#### 1. Clear Event History

**In Dashboard**:
```javascript
// Use browser console to clear events
dashboard.clearEvents();

// Or use keyboard shortcut
// Ctrl+R (if implemented)
```

**Server-side**:
```bash
# Restart Socket.IO server to clear history
./claude-mpm --monitor  # Restart with fresh state
```

#### 2. Event Filtering

**Filter by Session**:
```
# Add session filter to URL
http://localhost:8765?session=specific-session-id

# Or use dashboard search/filter UI
```

**Limit Event Types**:
```javascript
// In browser console, filter out noisy events
dashboard.setEventFilter(['hook', 'agent', 'tool']);  // Only show these types
```

#### 3. Reduce Event Frequency

**Disable Debug Events**:
```bash
# Turn off debug mode to reduce event volume
unset CLAUDE_MPM_HOOK_DEBUG
./claude-mpm --monitor
```

## Error Messages and Solutions

### "Socket.IO not available"

**Full Error**: "❌ Socket.IO not available. Install with: pip install python-socketio"

**Solution**:
```bash
# Install Socket.IO dependencies
pip install python-socketio aiohttp

# Or install with monitoring extras
pip install -e ".[monitor]"
```

### "Connection refused"

**Full Error**: "ConnectionError: Connection refused to http://localhost:8765"

**Causes & Solutions**:

1. **Server not running**:
   ```bash
   ./claude-mpm --monitor  # Start server
   ```

2. **Wrong port**:
   ```bash
   # Check which port server is actually using
   ps aux | grep claude-mpm | grep monitor
   
   # Look for port in output, adjust browser URL accordingly
   ```

3. **Permission issues**:
   ```bash
   # Check if another process is blocking port
   sudo lsof -i :8765
   ```

### "Failed to load dashboard assets"

**Error**: Dashboard loads but CSS/JS files return 404

**Solution**:
```bash
# Verify dashboard files exist
ls -la src/claude_mpm/dashboard/static/
ls -la src/claude_mpm/dashboard/templates/

# Check file permissions
chmod -R 644 src/claude_mpm/dashboard/static/*
chmod 644 src/claude_mpm/dashboard/templates/index.html
```

### "Events appearing with wrong timestamps"

**Problem**: Events show incorrect or inconsistent timestamps

**Causes & Solutions**:

1. **Timezone issues**:
   ```javascript
   // Dashboard uses local time, events might be UTC
   // Check browser console for timestamp format
   console.log('Event timestamp:', event.timestamp);
   ```

2. **Clock skew**:
   ```bash
   # Sync system clock
   sudo ntpdate -s time.nist.gov  # macOS/Linux
   ```

3. **Event processing delay**:
   ```bash
   # Check if events are severely delayed
   # Enable debug mode to see processing timestamps
   export CLAUDE_MPM_HOOK_DEBUG=true
   ```

## Debugging Procedures

### Step-by-Step Debugging

#### 1. Verify Basic Connectivity

```bash
# Step 1: Check server is running
./claude-mpm --monitor
# Look for: "Socket.IO server started on port 8765"

# Step 2: Test server endpoint
curl http://localhost:8765/
# Should return dashboard HTML

# Step 3: Test Socket.IO endpoint
curl http://localhost:8765/socket.io/
# Should return Socket.IO info
```

#### 2. Test Event Flow

```bash
# Step 1: Enable debug logging
export CLAUDE_MPM_HOOK_DEBUG=true

# Step 2: Start dashboard with logging
./claude-mpm --monitor 2>&1 | tee dashboard.log

# Step 3: Trigger test events
python scripts/test_dashboard_file_viewer.py

# Step 4: Check logs for event flow
grep -i "socket" dashboard.log
grep -i "event" dashboard.log
```

#### 3. Browser Debugging

**Open Browser Developer Tools**:

1. **Console Tab**: Check for JavaScript errors
2. **Network Tab**: Monitor Socket.IO connections
3. **Application Tab**: Check Socket.IO connection status

**Useful Console Commands**:
```javascript
// Check Socket.IO connection
socket.connected

// Monitor events
socket.on('claude_event', (data) => {
    console.log('Received event:', data);
});

// Check dashboard state
dashboard.getStats()  // If dashboard object exists
```

#### 4. Server-Side Debugging

**Enable Detailed Logging**:
```python
# Add to socketio_server.py for debugging
import logging
logging.getLogger('socketio').setLevel(logging.DEBUG)
logging.getLogger('engineio').setLevel(logging.DEBUG)
```

**Monitor Server Events**:
```bash
# Watch server logs in real-time
tail -f dashboard.log | grep -E "(socket|event|connection)"
```

### Performance Debugging

#### Memory Usage Analysis

**Browser Memory**:
```javascript
// Check dashboard memory usage
console.log('Events stored:', dashboard.events.length);
console.log('Memory estimate:', dashboard.events.length * 1000, 'bytes');

// Force garbage collection (Chrome DevTools)
// Memory tab > Collect garbage button
```

**Server Memory**:
```bash
# Check server process memory
ps aux | grep claude-mpm | head -1

# Monitor over time
watch 'ps aux | grep claude-mpm | head -1'
```

#### Connection Performance

**Measure Event Latency**:
```javascript
// Time event processing in browser
let startTime = Date.now();
socket.on('claude_event', (data) => {
    let latency = Date.now() - data.timestamp;
    console.log('Event latency:', latency, 'ms');
});
```

**Monitor Connection Quality**:
```javascript
// Check connection stats
socket.on('connect', () => {
    console.log('Connected at:', new Date());
});

socket.on('disconnect', (reason) => {
    console.log('Disconnected:', reason, 'at:', new Date());
});
```

## Advanced Troubleshooting

### Log Analysis

**Important Log Patterns**:
```bash
# Successful patterns to look for:
grep "Socket.IO server started" dashboard.log
grep "Client connected" dashboard.log
grep "Event forwarded" dashboard.log

# Error patterns to watch for:
grep -i "error" dashboard.log
grep -i "failed" dashboard.log
grep -i "refused" dashboard.log
```

### Network Debugging

**Check Network Interface**:
```bash
# Verify localhost binding
netstat -an | grep 127.0.0.1:8765

# Check for IPv6 issues
netstat -an | grep ::1:8765
```

**Test with Different Tools**:
```bash
# Test Socket.IO with curl
curl -v http://localhost:8765/socket.io/?transport=polling

# Test with websocket client
npm install -g wscat
wscat -c ws://localhost:8765/socket.io/?transport=websocket
```

### Configuration Debugging

**Verify Configuration Files**:
```bash
# Check for configuration conflicts
find . -name "*.json" -exec grep -l "8765" {} \;
find . -name "*.yaml" -exec grep -l "8765" {} \;

# Check environment variables
env | grep -i socket
env | grep -i port
```

## Recovery Procedures

### Clean Reset

**Full Dashboard Reset**:
```bash
# 1. Stop all claude-mpm processes
pkill -f claude-mpm

# 2. Clear any stale sockets
rm -f /tmp/claude-mpm-*.sock

# 3. Clear browser cache
# Ctrl+F5 or clear browser data

# 4. Restart with fresh state
./claude-mpm --monitor
```

### Emergency Debugging Mode

**Minimal Debug Setup**:
```bash
# Start with maximum logging
export CLAUDE_MPM_HOOK_DEBUG=true
export SOCKETIO_DEBUG=true
export PYTHONPATH=$(pwd)/src

# Run with Python directly for full stack traces
python -m claude_mpm.cli.commands.monitor --port 8765 --debug
```

## Getting Help

### Information to Gather

When reporting issues, include:

1. **Environment Info**:
   ```bash
   python --version
   pip list | grep -E "(socketio|aiohttp|claude-mpm)"
   uname -a
   ```

2. **Configuration**:
   ```bash
   # Sanitized configuration (remove sensitive data)
   cat .claude/settings.json | head -20
   env | grep -E "(CLAUDE|SOCKET|PORT)"
   ```

3. **Error Logs**:
   ```bash
   # Last 50 lines of relevant logs
   tail -50 dashboard.log
   ```

4. **Browser Info**:
   - Browser type and version
   - Console errors (JavaScript)
   - Network tab errors

### Diagnostic Script

**Run Comprehensive Diagnostic**:
```bash
# Create diagnostic report
./scripts/diagnose_dashboard.py > dashboard_diagnostic.txt
```

This should provide a complete system health check for the Socket.IO dashboard.