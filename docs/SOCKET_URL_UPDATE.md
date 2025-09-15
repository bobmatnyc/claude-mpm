# Socket.IO Dynamic URL Update

## Summary
Updated all monitor dashboard pages to use dynamic Socket.IO connection URLs instead of hardcoded `localhost:8765`.

## Problem
The monitor pages were hardcoded to connect to `http://localhost:8765`, which would break if:
- The server was accessed through a proxy
- The server was running on a different port
- The server was accessed from a different host/IP

## Solution
Changed all pages to dynamically construct the Socket.IO URL using the same origin as the page itself:

```javascript
// OLD: Hardcoded URL
const socket = window.DashboardStore.connectSocket(io, 'http://localhost:8765');

// NEW: Dynamic URL based on page origin
const socketUrl = window.location.protocol + '//' + window.location.host;
const socket = window.DashboardStore.connectSocket(io, socketUrl);
```

## Files Updated
1. `/src/claude_mpm/dashboard/static/events.html`
2. `/src/claude_mpm/dashboard/static/agents.html`
3. `/src/claude_mpm/dashboard/static/tools.html`
4. `/src/claude_mpm/dashboard/static/files.html`
5. `/src/claude_mpm/dashboard/static/test-connection-status.html`

## Benefits
- **Environment Agnostic**: Works regardless of where the server is hosted
- **Port Flexible**: Automatically uses the correct port
- **Proxy Compatible**: Works behind reverse proxies
- **Protocol Aware**: Maintains HTTP/HTTPS as appropriate

## Testing
Two test scripts were created to verify the implementation:
- `/scripts/test-dynamic-socket-urls.py` - Verifies all files use dynamic URLs
- `/scripts/test-monitor-socket-connections.py` - Comprehensive test suite

All tests pass successfully.

## Impact
This change ensures the monitor dashboard works correctly in all deployment scenarios without requiring configuration changes.