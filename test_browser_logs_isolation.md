# Browser Logs Tab Isolation Test

## Test Procedure

1. **Open Dashboard**
   - Navigate to http://localhost:8765 in your browser
   - Open Developer Console (F12 or Cmd+Option+I)

2. **Verify Version Markers**
   - In browser console, you should see:
     - `[BROWSER-LOG-VIEWER v2.0] CONSTRUCTOR CALLED - INITIALIZING WITH AGGRESSIVE ISOLATION`
     - `[BROWSER-LOG-VIEWER v2.0] INIT CALLED - NUCLEAR CLEARING CONTAINER`
     - `[BROWSER-LOG-VIEWER v2.0] RENDER CALLED - FORCING CLEAN CONTENT`
     - `[UI-STATE v2] 🚨 SWITCHING TO BROWSER LOGS - NUCLEAR MODE ACTIVATED`

3. **Click Browser Logs Tab**
   - Click on the "Browser Logs" tab
   - Console should show nuclear clearing messages
   - Tab should display:
     - "BROWSER LOGS ONLY - VERSION 2.0"
     - "⚠️ HOOK EVENTS ARE BLOCKED HERE ⚠️"

4. **Verify Isolation**
   - NO hook events should appear in Browser Logs tab
   - Check that Events tab still shows hook events normally
   - Switch between tabs to verify isolation persists

5. **Force Refresh Test**
   - Do a hard refresh (Cmd+Shift+R or Ctrl+Shift+F5)
   - Verify cache-busting URLs load:
     - browser-log-viewer.js?v=2.0-NUCLEAR
     - ui-state-manager.js?v=2.0-NUCLEAR

## Expected Results

✅ **Browser Logs Tab**
- Shows ONLY browser console logs
- Displays version 2.0 header
- Shows warning about blocked hooks
- NO [hook] events visible

✅ **Events Tab**
- Shows all events including [hook] events
- Normal operation unchanged

✅ **Console Output**
- Nuclear protection messages visible
- Version 2.0 markers present
- Contamination blocking alerts when switching tabs

## If Test Fails

If hook events still appear in Browser Logs:
1. Check browser cache - do hard refresh
2. Verify monitor is using updated files
3. Check console for error messages
4. Inspect DOM to see if events-list is present

## Nuclear Option

If standard fix doesn't work, we can rename the file:
- Rename browser-log-viewer.js to browser-log-viewer-v2.js
- Update all references in index.html
- This forces browser to load new file regardless of cache