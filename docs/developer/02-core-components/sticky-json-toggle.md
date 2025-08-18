# Sticky JSON Toggle Feature

## Overview

The Sticky JSON Toggle feature provides a persistent Raw JSON visibility state across all events in the Claude MPM dashboard. When toggled, the JSON display preference applies to all current and future events, significantly improving the debugging workflow.

## Features

### Global State Management
- **Persistent State**: Toggle state is maintained across all events
- **localStorage Persistence**: Preference survives page refreshes
- **Real-time Updates**: All JSON sections update simultaneously when toggled

### Visual Indicators
- **"(Sticky)" Label**: Shows when JSON is globally expanded
- **Blue Highlight**: Active state uses blue color scheme (#4299e1)
- **Arrow Direction**: ▼ for collapsed, ▲ for expanded

### User Experience
- **Single Click Control**: One toggle affects all events
- **New Event Respect**: Incoming events automatically adopt current state
- **Keyboard Support**: Enter/Space keys work on focused toggle

## Implementation Details

### Core Components

#### 1. ModuleViewer Class (`module-viewer.js`)
```javascript
// Global state property
this.globalJsonExpanded = localStorage.getItem('dashboard-json-expanded') === 'true';

// Toggle method affects all events
toggleJsonSection() {
    this.globalJsonExpanded = !this.globalJsonExpanded;
    localStorage.setItem('dashboard-json-expanded', this.globalJsonExpanded.toString());
    this.updateAllJsonSections();
}
```

#### 2. CSS Styling (`dashboard.css`)
```css
/* Active state styling */
.json-toggle-header[aria-expanded="true"] {
    background: linear-gradient(135deg, #e6f3ff 0%, #d4e9ff 100%);
    border-color: #4299e1;
}

/* Sticky indicator */
.json-toggle-header[aria-expanded="true"] .json-toggle-text::after {
    content: ' (Sticky)';
    color: #4299e1;
}
```

### State Flow

1. **User Clicks Toggle** → `toggleJsonSection()` called
2. **Global State Updated** → `this.globalJsonExpanded` flipped
3. **localStorage Updated** → State persisted for future sessions
4. **All Sections Updated** → `updateAllJsonSections()` applies to DOM
5. **Event Dispatched** → `jsonToggleChanged` notifies other components

### New Event Handling

When new events arrive:
1. `createCollapsibleJsonSection()` checks `globalJsonExpanded`
2. Initial display state set based on global preference
3. `initializeJsonToggle()` ensures consistency

## Usage

### For Users
1. Click any "Raw JSON" toggle button
2. All events show/hide JSON simultaneously
3. State persists across:
   - Different events
   - Tab switches
   - Page refreshes
   - New event arrivals

### For Developers
```javascript
// Check current state
const isExpanded = moduleViewer.globalJsonExpanded;

// Listen for changes
document.addEventListener('jsonToggleChanged', (e) => {
    console.log('JSON visibility:', e.detail.expanded);
});

// Programmatically toggle
moduleViewer.toggleJsonSection();
```

## Testing

Run the test script to verify functionality:
```bash
./scripts/test_sticky_json_toggle.py
```

The test verifies:
- Toggle affects all events
- State persists for new events
- localStorage saves preference
- Visual indicators work correctly

## Benefits

1. **Improved Debugging**: No need to toggle each event individually
2. **Consistent View**: All events show same level of detail
3. **Time Saving**: One click controls entire dashboard
4. **Persistent Preference**: Settings survive page refreshes
5. **Clear Visual Feedback**: Users know when sticky mode is active

## Browser Compatibility

- localStorage: All modern browsers
- CSS Gradients: All modern browsers
- aria-expanded: Accessibility support in all modern browsers

## Performance Considerations

- **DOM Updates**: Batch updates using `updateAllJsonSections()`
- **Smooth Scrolling**: Limited to first visible element
- **Event Delegation**: Single keyboard listener for all toggles
- **Minimal Reflow**: CSS transitions handle visual changes

## Future Enhancements

Potential improvements:
- Animate expand/collapse transitions
- Add tooltip explaining sticky behavior
- Provide keyboard shortcut (e.g., Ctrl+J) for global toggle
- Remember per-session overrides
- Add option to disable sticky behavior