# Browser Control Guide for Claude MPM Monitor

## The Problem
When running multiple test scripts that use `--monitor` or open the dashboard directly, each one opens a new browser window/tab, cluttering your screen.

## The Solution
Use the `CLAUDE_MPM_NO_BROWSER` environment variable to suppress automatic browser opening.

## For Test Scripts

### 1. Scripts using `--monitor` flag

Add this at the beginning of your test script:
```python
import os
os.environ['CLAUDE_MPM_NO_BROWSER'] = '1'
```

### 2. Scripts opening dashboard directly

Instead of:
```python
import webbrowser
dashboard_url = f"file://{dashboard_path}?autoconnect=true&port=8765"
webbrowser.open(dashboard_url)
```

Do this:
```python
import webbrowser
dashboard_url = f"file://{dashboard_path}?autoconnect=true&port=8765"

# Only open if not suppressed
if os.environ.get('CLAUDE_MPM_NO_BROWSER') != '1':
    webbrowser.open(dashboard_url)
else:
    print(f"Dashboard available at: {dashboard_url}")
```

## For Command Line Usage

### Normal usage (opens browser):
```bash
claude-mpm run --monitor
```

### Suppress browser opening:
```bash
export CLAUDE_MPM_NO_BROWSER=1
claude-mpm run --monitor
```

### One-time suppression:
```bash
CLAUDE_MPM_NO_BROWSER=1 claude-mpm run --monitor
```

## Benefits
- No more multiple browser windows
- Dashboard URL is still displayed for manual access
- Tests can run without UI interruption
- Production use remains unchanged

## Example Test Script
```python
#!/usr/bin/env python3
import os
import subprocess

# Suppress browser opening for this test
os.environ['CLAUDE_MPM_NO_BROWSER'] = '1'

# Now run commands that would normally open browser
subprocess.run(['claude-mpm', 'run', '--monitor', '-i', 'test'])
# Browser will NOT open, but dashboard URL will be shown
```