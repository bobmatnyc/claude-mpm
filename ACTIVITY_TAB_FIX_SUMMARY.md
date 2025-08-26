# Activity Tab Module Loading Fix - Summary

## Problem
The Activity tab was showing the event list instead of the D3 tree visualization because:
1. The `activity-tree.js` module was NOT included in the Vite build configuration
2. It was loaded as a standalone module AFTER the bundled dashboard.js
3. When dashboard.js tried to render the Activity tab, `window.ActivityTree` didn't exist yet
4. This caused a race condition where the Activity tab defaulted to showing events

## Solution Implemented

### 1. Added activity-tree.js to Vite Build Configuration
**File:** `/Users/masa/Projects/claude-mpm/vite.config.js`
- Added `'components/activity-tree'` to the rollupOptions.input configuration
- This ensures the module is built and optimized with the rest of the dashboard

### 2. Updated HTML Template to Use Built Version
**File:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard/templates/index.html`
- Changed from: `/static/js/components/activity-tree.js` (source)
- Changed to: `/static/dist/components/activity-tree.js` (built)
- This ensures the optimized, built version is loaded

### 3. Improved Dashboard.js Activity Tab Handling
**File:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard/static/js/dashboard.js`
- Added robust handling for the ActivityTree class
- Checks for `window.ActivityTree` class availability
- Creates and manages a global `window.activityTreeInstance`
- Includes retry logic if module is not loaded yet
- Maintains backward compatibility with legacy approach

### 4. Fixed Module Export Timing
**File:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard/static/js/components/activity-tree.js`
- Made `window.ActivityTree = ActivityTree` assignment immediate on module load
- Moved DOM event listener setup to a separate function
- Ensures the class is available globally as soon as the module loads
- Stores instance globally as `window.activityTreeInstance` for dashboard access

## Testing Instructions

1. **Build the Dashboard:**
   ```bash
   npm run build
   ```

2. **Clear Browser Cache:**
   - Hard refresh: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows/Linux)
   - Or open Developer Tools > Network tab > check "Disable cache"

3. **Test the Fix:**
   - Navigate to the dashboard (http://localhost:8765)
   - Click on the "Activity" tab
   - Should see the D3 tree visualization, NOT the event list
   - Check browser console for initialization messages

4. **Verify in Console:**
   ```javascript
   // These should all return true:
   window.ActivityTree !== undefined  // Class is available
   window.activityTreeInstance !== undefined  // Instance exists (after clicking tab)
   typeof window.activityTreeInstance.renderWhenVisible === 'function'  // Method exists
   ```

## What Changed
1. **Vite Config:** Added activity-tree to build inputs
2. **HTML Template:** Updated script src to use built version  
3. **Dashboard.js:** Improved Activity tab rendering logic
4. **Activity-tree.js:** Fixed module export timing

## Build Output
The build now generates:
- `/static/dist/components/activity-tree.js` (14.07 kB)
- `/static/dist/components/activity-tree.js.map` (source map for debugging)

## Rollback Instructions
If needed, to rollback:
1. Remove `'components/activity-tree'` from vite.config.js
2. Change HTML template back to `/static/js/components/activity-tree.js`
3. Revert dashboard.js changes to lines 375-388
4. Revert activity-tree.js changes to lines 909-969