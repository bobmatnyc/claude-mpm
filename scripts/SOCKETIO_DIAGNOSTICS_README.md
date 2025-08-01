# Socket.IO Diagnostic Suite

This directory contains comprehensive diagnostic tools to identify where the Socket.IO event flow is breaking down in the Claude MPM system.

## Problem Description

Users report losing connection and never seeing events in the Socket.IO dashboard. The diagnostic suite helps identify exactly where the event flow breaks down.

## Diagnostic Scripts

### 1. Main Diagnostic Runner
```bash
python scripts/run_socketio_diagnostics.py
```
**Purpose**: Orchestrates all diagnostic tests in the correct order
**What it tests**: Complete event flow from hook -> server -> dashboard

### 2. Server-Side Event Monitor
```bash
python scripts/diagnostic_socketio_server_monitor.py
```
**Purpose**: Enhanced Socket.IO server with detailed logging
**What it shows**: 
- All incoming connections and their namespaces
- All events being emitted to clients
- Client authentication attempts
- Event broadcast success/failure

### 3. Hook Handler Event Test
```bash
python scripts/diagnostic_hook_handler_test.py
python scripts/diagnostic_hook_handler_test.py --continuous 30
```
**Purpose**: Simulates the hook handler's event sending process
**What it tests**:
- Socket.IO client connection establishment
- Authentication with dev-token
- Event emission to correct namespaces (/hook, /system)
- Connection persistence and reconnection

### 4. Dashboard Namespace Test
```bash
# Open in browser
open scripts/diagnostic_dashboard_namespace_test.html
```
**Purpose**: Comprehensive dashboard that tests all namespace connections
**What it shows**:
- Connection status for all namespaces
- Real-time event reception
- Event log with timestamps
- Connection statistics

### 5. End-to-End Flow Test
```bash
python scripts/diagnostic_end_to_end_test.py
python scripts/diagnostic_end_to_end_test.py --events 20
```
**Purpose**: Tests the complete event pipeline
**What it tests**:
- Starts its own diagnostic server
- Simulates hook handler events
- Tests dashboard connections
- Measures timing and reliability

### 6. Connection & Authentication Test
```bash
python scripts/diagnostic_connection_auth_test.py
```
**Purpose**: Focused testing of connection/auth issues
**What it tests**:
- Basic connection without authentication
- Valid authentication (dev-token)
- Invalid authentication handling
- Namespace-specific authentication
- Connection timeout behavior
- Reconnection behavior

## Quick Start

1. **Install dependencies**:
   ```bash
   pip install python-socketio[asyncio_client] aiohttp
   ```

2. **Run complete diagnostic**:
   ```bash
   python scripts/run_socketio_diagnostics.py
   ```

3. **For quick server monitoring**:
   ```bash
   # Terminal 1: Start diagnostic server
   python scripts/diagnostic_socketio_server_monitor.py
   
   # Terminal 2: Test hook handler
   python scripts/diagnostic_hook_handler_test.py --continuous 10
   
   # Browser: Open dashboard test
   open scripts/diagnostic_dashboard_namespace_test.html
   ```

## Expected Behavior

### Healthy System
- All connections succeed with proper authentication
- Hook handler connects to `/hook` and `/system` namespaces
- Events flow from hook -> server -> dashboard
- Dashboard shows real-time event reception
- No authentication or connection errors

### Common Issues & Solutions

#### Issue: "Connection refused" errors
**Cause**: Socket.IO server not running
**Solution**: Start the server first or check port conflicts

#### Issue: "Invalid authentication token" errors  
**Cause**: Token mismatch between client and server
**Solution**: Verify both use 'dev-token' or check CLAUDE_MPM_SOCKETIO_TOKEN

#### Issue: Hook connects but dashboard doesn't receive events
**Cause**: Namespace routing issues
**Solution**: Check that dashboard listens to correct namespaces

#### Issue: Events sent but not received
**Cause**: Room-based broadcasting not working
**Solution**: Verify clients join the correct rooms

#### Issue: Connection timeouts
**Cause**: Server performance or network issues
**Solution**: Check server logs and increase timeout values

## Debugging Tips

1. **Enable debug logging**:
   ```bash
   CLAUDE_MPM_HOOK_DEBUG=true python scripts/diagnostic_hook_handler_test.py
   ```

2. **Check server status**:
   ```bash
   curl http://localhost:8765/health
   ```

3. **Monitor real-time events**:
   - Use the diagnostic server monitor
   - Open browser developer tools on dashboard
   - Check Socket.IO admin UI integration

4. **Test individual components**:
   - Run each diagnostic script separately
   - Start with connection/auth test
   - Progress through hook handler and dashboard tests

## File Locations

- **Diagnostic Scripts**: `/Users/masa/Projects/claude-mpm/scripts/diagnostic_*.py`
- **Dashboard Test**: `/Users/masa/Projects/claude-mpm/scripts/diagnostic_dashboard_namespace_test.html`
- **Main Runner**: `/Users/masa/Projects/claude-mpm/scripts/run_socketio_diagnostics.py`
- **Actual Server**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/websocket_server.py`
- **Hook Handler**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/hooks/claude_hooks/hook_handler.py`

## Integration with Claude MPM

To test with the actual claude-mpm system:

1. Start diagnostic server monitor:
   ```bash
   python scripts/diagnostic_socketio_server_monitor.py
   ```

2. Run claude-mpm in another terminal:
   ```bash
   ./claude-mpm run -i "test prompt" --non-interactive
   ```

3. Watch for hook events in the diagnostic server output

4. Open dashboard to see if events appear

This should reveal exactly where the event flow breaks down in the real system.