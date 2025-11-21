# Testing Checklist for Dashboard2

## Build Verification

- [x] `npm install` completes without errors
- [x] `npm run build` completes successfully
- [x] No Svelte compiler warnings
- [x] No accessibility warnings
- [x] `dist/index.html` exists
- [x] `dist/assets/*.js` exists
- [x] `dist/assets/*.css` exists

## Development Server Testing

Run `npm run dev` and verify:

- [ ] Dev server starts on port 5173
- [ ] Dashboard loads at `http://localhost:5173`
- [ ] No console errors on page load
- [ ] Hot Module Replacement (HMR) works on file changes

## UI Components

### Header
- [ ] Title displays: "Claude MPM Dashboard"
- [ ] Version displays: "v2.0"
- [ ] Connection status indicator is visible
- [ ] Status text shows "Disconnected" initially
- [ ] Port number displays correctly
- [ ] Indicator color is red when disconnected

### Sidebar
- [ ] All 5 tabs are visible: Events, Agents, Files, Tools, Activity
- [ ] Each tab has an icon
- [ ] Events tab is active by default
- [ ] Clicking tabs switches active state
- [ ] Active tab has blue highlight
- [ ] Hover effects work correctly

### Main Content
- [ ] Events tab content loads
- [ ] Other tabs show placeholder content
- [ ] Placeholder icons display correctly
- [ ] Content area fills remaining space

## Socket.IO Connection

### Local Connection (port 8765)
- [ ] Connection status changes to "Connecting..." on startup
- [ ] Status changes to "Connected" when server is available
- [ ] Indicator turns green on connection
- [ ] Port number matches server (8765)
- [ ] Status shows "Disconnected" when server unavailable
- [ ] Status shows "Reconnecting..." when connection lost
- [ ] Indicator turns yellow during reconnection
- [ ] Auto-reconnect works after temporary disconnection

### Console Logging
Check browser console for:
- [ ] Socket.IO connection events logged
- [ ] No connection errors (if server running)
- [ ] Event reception logged
- [ ] No JavaScript errors

## Events Tab Functionality

### Empty State
- [ ] Empty state displays when no events
- [ ] "Waiting for events..." message shown
- [ ] Hint text displays
- [ ] Icon (📡) is visible

### Event Display
- [ ] Events appear when received
- [ ] Events display in reverse chronological order (newest first)
- [ ] Event time is formatted correctly (HH:MM:SS.mmm)
- [ ] Event source badge displays with correct color:
  - Hook: Blue (#3b82f6)
  - System: Green (#10b981)
  - API: Orange (#f59e0b)
- [ ] Event summary shows type and subtype
- [ ] Event item is clickable

### Event Expansion
- [ ] Clicking event expands JSON details
- [ ] Expand icon changes from ▶ to ▼
- [ ] JSON is formatted with syntax highlighting
- [ ] JSON is scrollable horizontally if needed
- [ ] Clicking again collapses the event
- [ ] Only one event expanded at a time (optional behavior)

### Event Statistics
- [ ] "Total" counter increments with each event
- [ ] "Displayed" counter shows current count
- [ ] Numbers update in real-time
- [ ] Clear button appears when events exist
- [ ] Clear button removes all events
- [ ] Counters reset after clearing

### Auto-scroll
- [ ] New events auto-scroll to top
- [ ] User can scroll manually
- [ ] Auto-scroll doesn't interfere with manual scrolling

## Event Reception Testing

### Test with Mock Events

You can test event reception by running this in the browser console:

```javascript
// Simulate a claude_event
window.dispatchEvent(new CustomEvent('test-socket-event', {
  detail: {
    source: 'hook',
    type: 'tool',
    subtype: 'pre_tool',
    timestamp: new Date().toISOString(),
    data: {
      tool_name: 'test_tool',
      params: { test: true }
    }
  }
}));
```

Or emit directly via Socket.IO if connected:
```javascript
// Get socket from console
const socket = io('http://localhost:8765');
socket.emit('claude_event', {
  source: 'hook',
  type: 'test',
  subtype: 'console_test',
  timestamp: new Date().toISOString(),
  data: { message: 'Test from console' }
});
```

### Real Event Testing
- [ ] Trigger a Claude Code hook event
- [ ] Event appears in dashboard immediately
- [ ] Event data is complete and accurate
- [ ] Timestamp is correct
- [ ] Event can be expanded to view full JSON
- [ ] Multiple events display correctly
- [ ] High-frequency events don't cause UI lag

### Heartbeat Events
- [ ] Server heartbeat events appear (every 3 minutes)
- [ ] Heartbeat has "system" source
- [ ] Heartbeat data includes uptime
- [ ] Heartbeat data includes connected clients

## Performance Testing

### Large Event Loads
- [ ] Dashboard handles 100 events smoothly
- [ ] Dashboard handles 1000 events (max buffer)
- [ ] Events beyond 1000 are trimmed correctly
- [ ] No memory leaks with continuous events
- [ ] Scrolling remains smooth with full buffer

### Network
- [ ] Dashboard works on slow connections
- [ ] Reconnection works after network interruption
- [ ] Events buffer during disconnection (if implemented)
- [ ] No duplicate events after reconnection

## Cross-Browser Testing

- [ ] Chrome/Chromium (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)

Check for:
- [ ] Layout renders correctly
- [ ] WebSocket/Socket.IO works
- [ ] No console errors
- [ ] Animations work smoothly

## Accessibility Testing

- [ ] Keyboard navigation works
- [ ] Tab key moves through interactive elements
- [ ] Enter/Space activates buttons
- [ ] Screen reader can read content
- [ ] Color contrast meets WCAG standards
- [ ] Focus indicators are visible

## Responsive Design

Test at different viewport sizes:
- [ ] 1920x1080 (Full HD)
- [ ] 1366x768 (Laptop)
- [ ] 1024x768 (Tablet landscape)

Verify:
- [ ] Layout doesn't break
- [ ] All content is accessible
- [ ] No horizontal scrolling
- [ ] Sidebar width is appropriate

## Production Build Testing

After running `npm run build`:

1. **Static File Serving**:
   - [ ] Serve dist/ with a simple HTTP server
   - [ ] Dashboard loads correctly
   - [ ] Assets load from correct paths
   - [ ] No 404 errors for assets

2. **Integration Testing**:
   - [ ] Flask serves dashboard correctly
   - [ ] Base path `/dashboard2/` works
   - [ ] Assets load with correct paths
   - [ ] Socket.IO connects to correct port

3. **Size Optimization**:
   - [ ] Total bundle size < 100KB (gzipped)
   - [ ] Initial load time < 2 seconds
   - [ ] No unnecessary dependencies bundled

## Error Handling

Test error scenarios:
- [ ] Server not available: Shows "Disconnected" status
- [ ] Server crashes: Shows reconnection status
- [ ] Invalid event data: Handles gracefully (no crashes)
- [ ] Malformed JSON: Displays error or skips event
- [ ] Network timeout: Retries connection

## Console Checks

Verify no errors for:
- [ ] Component initialization
- [ ] Socket.IO connection
- [ ] Event handling
- [ ] State updates
- [ ] DOM updates

## Final Production Checklist

Before deploying:
- [ ] Run `npm run build` with no warnings
- [ ] Test built files locally
- [ ] Verify all features work in production build
- [ ] Check browser console for errors
- [ ] Test Socket.IO connection
- [ ] Verify events display correctly
- [ ] Test on target deployment environment
- [ ] Document any known issues
- [ ] Update version number if needed

## Known Issues

Document any issues found during testing:

1. **Issue**: [Description]
   - **Severity**: Low/Medium/High
   - **Workaround**: [If available]
   - **Fix plan**: [If scheduled]

## Performance Benchmarks

Record baseline performance:
- Initial load time: ___ms
- Time to Socket.IO connection: ___ms
- Average event processing time: ___ms
- Memory usage with 1000 events: ___MB
- FPS during scrolling: ___

## Test Results Summary

Date: ___________
Tester: ___________
Environment: ___________

- Total tests: ___
- Passed: ___
- Failed: ___
- Skipped: ___

**Overall Status**: ⬜ Pass | ⬜ Fail | ⬜ Partial

**Notes**:
