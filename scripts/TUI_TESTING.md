# TUI Testing Guide

## Running the TUI

There are two ways to test the TUI:

### 1. Using the test script (recommended for debugging)
```bash
python scripts/test_tui.py
```
This will show debug logging in the console to help diagnose issues.

### 2. Using the ListView test script
```bash
python scripts/test_listview.py
```
This minimal test app helps verify ListView event handling works correctly.

### 3. Using the actual command (production)
```bash
./scripts/claude-mpm configure --tui
```

## Event Handling Fix Summary

The ListView selection events have been fixed with multiple approaches:

1. **Primary Handler**: `on_list_view_selected` method catches ListView.Selected events
2. **Keyboard Support**: Enter key triggers `action_select_nav` when ListView has focus
3. **Fallback**: Index-based selection ensures navigation works even if item IDs aren't accessible
4. **Debug Logging**: All handlers include logging to help diagnose event flow

## How Navigation Works

1. **Mouse Click**: Click on a menu item → triggers ListView.Selected → switches screen
2. **Keyboard (Arrow + Enter)**: 
   - Arrow keys change ListView index/highlight
   - Enter key triggers action_select_nav → switches to selected screen
3. **Keyboard Shortcuts**: Ctrl+A/T/B/S directly navigate to specific screens

## Debug Output

When running with test scripts, you'll see debug messages like:
- `ListView.Selected event triggered`
- `Switching to screen: [screen_name]`
- `Nav index changed from X to Y`

These help verify events are firing correctly.

## Interaction Methods

All of these should work:
- Click menu items with mouse
- Use arrow keys + Enter
- Use Ctrl+A/T/B/S shortcuts
- Tab to navigate between UI elements

## Known Issues Addressed

- Event handlers now properly check for sender/item IDs
- Index-based fallback ensures selection works even without IDs
- Enter key binding only activates when ListView has focus
- Multiple event handler approaches provide redundancy