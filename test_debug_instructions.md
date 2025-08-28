# Debug Testing Instructions for Dotfile Filtering

## Setup
1. Start the dashboard: `./scripts/claude-mpm dashboard`
2. Open browser: http://localhost:5000
3. Open Browser Developer Console (F12 or Cmd+Option+I)
4. Navigate to the Code tab

## What to Check

### In Browser Console
You should see debug messages like:
```
[DEBUG] Show hidden files checkbox value: false
[DEBUG] Checkbox element: <input type="checkbox" id="show-hidden-files">
[DEBUG] Sending discovery request with payload: {
  path: "/Users/masa/Projects/claude-mpm",
  depth: "top_level",
  languages: [],
  ignore_patterns: "",
  show_hidden_files: false
}
```

### In Terminal (Server Logs)
You should see messages like:
```
[DEBUG] handle_discover_top_level: Received show_hidden_files=False from frontend
[DEBUG] handle_discover_top_level: Full request data: {...}
INFO: Dotfile check: .github, show_hidden=False, in_exceptions=False, result=True
INFO: Dotfile check: .ai-trackdown, show_hidden=False, in_exceptions=False, result=True
```

## Expected Behavior
When `show_hidden_files=false` (checkbox unchecked):
- `.github` should have `result=True` (ignored/hidden)
- `.ai-trackdown` should have `result=True` (ignored/hidden)
- `.gitignore` should have `result=False` (shown - it's an exception)

## Testing Steps
1. **Initial Load**: Check console/logs when page first loads
2. **Toggle Checkbox**: Check "Show hidden files" and watch for new discovery request
3. **Verify Values**: Ensure show_hidden_files matches checkbox state

## If Dotfiles Still Show
Check if:
1. Frontend is sending `show_hidden_files: false`
2. Backend is receiving `show_hidden_files=False`
3. Backend logs show `result=True` for dotfiles (meaning they should be hidden)
4. But they still appear in the UI

This would indicate the filtering is happening but the filtered results aren't being properly sent back to the frontend.