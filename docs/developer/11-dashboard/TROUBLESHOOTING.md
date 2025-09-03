# Dashboard Service Troubleshooting Guide

This guide provides solutions for common issues with the Claude MPM dashboard service and debugging procedures for both the stable standalone server and the advanced monitoring system.

## Dashboard Service Overview

The Claude MPM dashboard provides a web interface for monitoring and analysis that runs on **port 8765 by default**. Starting with v4.2.2, the dashboard uses a **stable server by default** that works standalone without requiring monitor dependencies.

**Key Features:**
- **HTTP endpoints** for serving the dashboard interface and static files
- **WebSocket connectivity** via SocketIO for real-time communication
- **Two server implementations:**
  - **Stable Server** (default): Standalone, no monitor required
  - **Advanced Server**: Full featured with monitor integration (port 8766)

**Default Configuration:**
- Port: 8765
- Host: localhost (127.0.0.1)
- Server: Stable (standalone mode)
- Auto-start browser: Yes (unless `--no-browser`)

The stable server provides all essential dashboard functionality and eliminates the dependency issues that previously affected users.

## Common Issues & Solutions

### Dashboard Not Responding on localhost:8765

**Symptoms:**
- Browser shows "This site can't be reached" or "Connection refused"
- Dashboard URL (http://localhost:8765) doesn't load
- No response when accessing the dashboard

**Solutions:**

#### 1. Check if Dashboard is Running
```bash
# Check dashboard status
claude-mpm dashboard status

# Check if port 8765 is in use
lsof -i :8765
# Or on some systems:
netstat -an | grep 8765
```

#### 2. Start Dashboard if Not Running
```bash
# Basic start (stable server, default port 8765)
claude-mpm dashboard start

# Start without auto-opening browser
claude-mpm dashboard start --no-browser

# Start with debug logging
claude-mpm dashboard start --debug
```

#### 3. Port Already in Use
If port 8765 is occupied by another process:

```bash
# Use a different port
claude-mpm dashboard start --port 8080

# Or kill the conflicting process (check what it is first!)
lsof -i :8765  # Find the PID
kill -9 <PID>  # Only if safe to do so
```

### Connection Refused Errors

**Symptoms:**
- Error: "Connection refused to http://localhost:8765"
- Browser fails to connect
- "ERR_CONNECTION_REFUSED" in browser

**Root Causes & Solutions:**

#### 1. Dashboard Server Not Started
```bash
# Start the dashboard
claude-mpm dashboard start
```

#### 2. Wrong Port
```bash
# Check which port dashboard is actually using
claude-mpm dashboard status --verbose

# Open dashboard on the correct port
claude-mpm dashboard open --port <actual-port>
```

#### 3. Host Binding Issues
```bash
# Start with external access (if needed)
claude-mpm dashboard start --host 0.0.0.0

# Or use localhost specifically
claude-mpm dashboard start --host localhost
```

#### 4. Firewall/Security Software
- Check your firewall settings
- Some antivirus software blocks localhost connections
- Try temporarily disabling security software to test

### Port Already in Use Messages

**Error Messages:**
- "Address already in use"
- "Port 8765 is in use, trying port 8766..."
- "[Errno 48] Address already in use"

**Solutions:**

#### 1. Automatic Port Resolution (Built-in)
The dashboard automatically tries ports 8765-8774 if the default is occupied:
```bash
# Just start normally - it will find an available port
claude-mpm dashboard start
```

#### 2. Manual Port Selection
```bash
# Use a specific different port
claude-mpm dashboard start --port 9000

# Check what's using the default port
lsof -i :8765
```

#### 3. Stop Conflicting Service
```bash
# If it's another Claude MPM dashboard:
claude-mpm dashboard stop

# Stop all dashboard instances
claude-mpm dashboard stop --all

# If it's another service, identify and stop safely
```

### Cannot Find Dashboard Files Errors

**Error Messages:**
- "Could not find dashboard files"
- "Dashboard not found" (404 error)
- "Please ensure Claude MPM is properly installed"

**Solutions:**

#### 1. Verify Installation
```bash
# Check if Claude MPM is properly installed
claude-mpm --version

# Reinstall if needed
pip install --upgrade claude-mpm
```

#### 2. Development Installation
If running from source:
```bash
# Install in development mode
pip install -e .

# Or ensure PYTHONPATH includes src/
export PYTHONPATH=/path/to/claude-mpm/src:$PYTHONPATH
```

#### 3. Debug File Location
```bash
# Start with debug to see where files are searched
claude-mpm dashboard start --debug

# Look for "Dashboard path resolved to:" message
```

### Dependencies Missing

**Error Messages:**
- "Missing dependencies. Install with: pip install aiohttp python-socketio"
- "Socket.IO not available"

**Solutions:**
```bash
# Install required dependencies
pip install aiohttp python-socketio

# Or install with monitoring extras
pip install claude-mpm[monitor]

# For development with all dependencies
pip install -e ".[dev,monitor]"
```

## Verification Steps

### How to Check if Dashboard is Running

```bash
# Method 1: Use built-in status command
claude-mpm dashboard status

# Method 2: Check port directly
curl -s http://localhost:8765/ | head -5

# Method 3: Check process list
ps aux | grep dashboard
```

### How to Test Service is Working

```bash
# Test HTTP endpoint
curl -s http://localhost:8765/version.json

# Test static files
curl -s http://localhost:8765/static/css/dashboard.css | head -5

# Test API endpoints
curl -s "http://localhost:8765/api/directory/list?path=."
```

### Debug Mode for Diagnostics

```bash
# Start with full debugging
claude-mpm dashboard start --debug

# This shows:
# - Dashboard file resolution path
# - Server startup process
# - Connection attempts
# - Event handling details
```

## Technical Details

### Two Server Implementations

#### Stable Server (Default)
- **Purpose**: Standalone dashboard without monitor dependencies
- **Port**: 8765 (configurable)
- **Dependencies**: Only aiohttp + python-socketio
- **Features**: HTTP endpoints, SocketIO, mock AST analysis
- **Use Case**: General dashboard access, development, production

```bash
# Explicitly use stable server (default behavior)
claude-mpm dashboard start --stable
```

#### Advanced Server (Optional)
- **Purpose**: Full monitoring integration with event streaming
- **Port**: 8765 (dashboard) + 8766 (monitor service)
- **Dependencies**: Full monitoring stack
- **Features**: Real-time event streaming, comprehensive monitoring
- **Use Case**: Development with full monitoring

```bash
# Use advanced server (requires monitor service)
claude-mpm dashboard start --background  # Uses advanced server
```

### Port Configuration Options

**Default Ports:**
- Dashboard: 8765
- Monitor (if used): 8766

**Port Conflict Resolution:**
The stable server automatically tries ports 8765-8774 if the default is occupied.

**Custom Port Configuration:**
```bash
# Custom dashboard port
claude-mpm dashboard start --port 9000

# Multiple instances on different ports
claude-mpm dashboard start --port 8765 --background
claude-mpm dashboard start --port 8766 --no-browser
```

### Host Binding Options

**Localhost Only (Default - Secure):**
```bash
claude-mpm dashboard start --host localhost
# Or
claude-mpm dashboard start --host 127.0.0.1
```

**External Access (Network Access):**
```bash
claude-mpm dashboard start --host 0.0.0.0
# Dashboard accessible from: http://your-ip:8765
```

**Security Note**: Only use `--host 0.0.0.0` in trusted networks.

## Quick Commands Reference

### Basic Operations
```bash
# Start dashboard (stable server, port 8765)
claude-mpm dashboard start

# Start without opening browser
claude-mpm dashboard start --no-browser

# Start with debug logging
claude-mpm dashboard start --debug

# Check status
claude-mpm dashboard status

# Stop dashboard
claude-mpm dashboard stop

# Open dashboard in browser (starts if needed)
claude-mpm dashboard open
```

### Advanced Options
```bash
# Custom port
claude-mpm dashboard start --port 8080

# External access
claude-mpm dashboard start --host 0.0.0.0

# Background mode (advanced server)
claude-mpm dashboard start --background

# Verbose status with all ports
claude-mpm dashboard status --verbose --show-ports

# Stop specific port
claude-mpm dashboard stop --port 8080

# Stop all instances
claude-mpm dashboard stop --all
```

### Development & Testing
```bash
# Start with maximum debugging
claude-mpm dashboard start --debug --host localhost --port 8765

# Test specific endpoints
curl http://localhost:8765/version.json
curl "http://localhost:8765/api/directory/list?path=."

# Multiple test instances
claude-mpm dashboard start --port 8767 --no-browser &
claude-mpm dashboard start --port 8768 --no-browser &
```

## Legacy Issues (Advanced Server)

*The following section covers advanced server issues. Most users using the stable server (default) won't encounter these problems.*

### File Operations Not Showing in Files Tab

**Note: This issue primarily affects the advanced server with monitor integration.**

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

**Note: This section applies to both server types, but the solutions differ.**

**Symptoms:**
- Dashboard loads but shows no live events  
- Events appear only after page refresh
- Connection status shows disconnected

**For Stable Server (Default):**
The stable server provides mock data and basic SocketIO functionality. Real-time event streaming requires the advanced server with monitor integration.

**For Advanced Server:**

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

## Recent Fixes & Improvements

### Dashboard Service Architecture Changes (v4.2.2+)

**Problem Resolved:**
Prior to v4.2.2, the dashboard service failed for many users because it depended on a monitor server (port 8766) that wasn't running in production environments.

**Solution Implemented:**
- **Stable Server as Default**: The dashboard now uses a stable, standalone server by default
- **No Monitor Dependencies**: Works without requiring monitor service (port 8766)  
- **Automatic Fallback**: Falls back to advanced server if stable server fails
- **Better Error Messages**: Clear guidance when issues occur

**What This Means for Users:**
```bash
# This now works reliably for everyone:
claude-mpm dashboard start

# No longer requires:
# - Monitor service running on port 8766
# - Complex dependency coordination
# - Background service management
```

### Connection Stability Fixes (August 2025)

**Problems Resolved:**
- Clients connecting but immediately disconnecting
- Event handlers not available when clients connected
- Connection health checks timing out incorrectly
- EventBus relay failing on connection issues

**Improvements Made:**
1. **Handler Registration Timing**: Event handlers now register BEFORE server accepts connections
2. **Connection Retry Logic**: Added exponential backoff with 3 retry attempts
3. **Optimized Timing**: Reduced ping intervals (25s) and stale timeouts (90s) for faster issue detection
4. **EventBus Resilience**: Added retry logic for broadcaster connections

**Result**: Much more stable dashboard connections, especially under network stress.

### Automatic Port Conflict Resolution

**Feature Added:**
The stable server automatically resolves port conflicts by trying sequential ports (8765-8774).

**How It Works:**
```bash
claude-mpm dashboard start
# Port 8765 in use? Tries 8766
# Port 8766 in use? Tries 8767
# ... up to 8774
```

**Benefits:**
- No manual intervention needed
- Multiple dashboard instances supported
- Clear messaging about which port was used

## Debugging Procedures

### Step-by-Step Debugging

#### 1. Verify Basic Connectivity

```bash
# Step 1: Check server is running
claude-mpm dashboard status
# Look for: "Dashboard is running at http://localhost:8765"

# Step 2: Test server endpoint (should return HTML)
curl -s http://localhost:8765/ | head -10

# Step 3: Test version endpoint (stable server feature)
curl -s http://localhost:8765/version.json

# Step 4: Test Socket.IO endpoint
curl -s http://localhost:8765/socket.io/
# Should return Socket.IO connection info
```

#### 2. Test Event Flow

**For Stable Server (Default):**
```bash
# Step 1: Start with debug mode
claude-mpm dashboard start --debug --no-browser

# Step 2: In another terminal, test SocketIO connection
# (The stable server provides mock events and responses)

# Step 3: Open dashboard in browser and check browser console
# Look for SocketIO connection messages
```

**For Advanced Server (Monitor Mode):**
```bash
# Step 1: Enable debug logging
export CLAUDE_MPM_HOOK_DEBUG=true

# Step 2: Start dashboard with monitor integration
claude-mpm dashboard start --background

# Step 3: Trigger test events (if available)
# python scripts/test_dashboard_file_viewer.py

# Step 4: Check logs for event flow
# Look for event forwarding and processing
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

This should provide a complete system health check for the dashboard service.

## Additional Command Options

The dashboard start command supports additional options that may not be documented in the help text:

```bash
# Explicit server selection (internal)
claude-mpm dashboard start --stable          # Force stable server (default)
claude-mpm dashboard start --stable-only     # Only try stable, no fallback

# Advanced debugging (internal)
claude-mpm dashboard start --no-fallback     # Don't fallback to advanced server

# These options are available but not exposed in CLI help:
# - --stable: Force stable server mode
# - --stable-only: Only use stable server
# - --no-fallback: Don't fall back to advanced server if stable fails
```

Note: Some options are internal and used by the system for testing and development.

## Summary

The dashboard service has been significantly improved in recent versions:

1. **Stable Server Default**: Works standalone without monitor dependencies
2. **Automatic Port Resolution**: Finds available ports automatically  
3. **Better Error Handling**: Clear messages and troubleshooting guidance
4. **Connection Stability**: Robust retry logic and timing optimizations
5. **Comprehensive Commands**: Full start/stop/status/open command set

For most users, `claude-mpm dashboard start` should work reliably out of the box.