# Display Order Fix: Banner Before Progress Bar

## Problem
The "Launching Claude..." progress bar was appearing BEFORE the welcome banner, creating a confusing user experience where the first thing users saw was the progress indicator instead of the welcome message.

## Solution
Reordered the initialization sequence in `src/claude_mpm/cli/__init__.py` to display the banner BEFORE starting background services and their associated progress indicators.

## Changes Made

### 1. `/src/claude_mpm/cli/__init__.py` (lines 75-99)
**Before:**
```python
ensure_directories()
if not should_skip_background_services(args, processed_argv):
    # Show progress bar
    launch_progress = ProgressBar(...)
    # ... run background services ...

# Display banner
if should_show_banner(args):
    display_startup_banner(__version__, logging_level)
```

**After:**
```python
ensure_directories()

# Display banner FIRST
if should_show_banner(args):
    display_startup_banner(__version__, logging_level)

if not should_skip_background_services(args, processed_argv):
    # Show progress bar
    launch_progress = ProgressBar(...)
    # ... run background services ...
```

### 2. `/src/claude_mpm/cli/startup_display.py` (line 267)
Updated comment to reflect correct behavior:
```python
# Note: Banner is shown BEFORE "Launching Claude..." progress bar (in cli/__init__.py)
# This ensures users see welcome message before background services start
```

## Verified Display Order

### Test 1: Normal Command (`agents list`)
```
✓ Found existing .claude-mpm/ directory

╭─── Claude MPM v5.0.0 ───────────────────────╮
│   Welcome back masa!    │ Recent activity   │
│     🛸 🛸              │ What's new         │
│ Sonnet 4.5 · Claude MPM │ ──────────────    │
╰─────────────────────────────────────────────╯

Checking MCP configuration...
Syncing agents 45/45 (100%)
Syncing skills 306/306 (100%)
✓ Runtime skills linked
✓ Output style configured
Launching Claude: Ready
```

**✅ Correct Order:**
1. Banner displays first with welcome message
2. Background services run (MCP, sync agents/skills)
3. "Launching Claude: Ready" message at the end

### Test 2: Help/Version Commands
```bash
$ claude-mpm --version
claude-mpm 5.0.0-build.534

$ claude-mpm --help
usage: claude-mpm [-h] [--version] ...
```

**✅ Banner correctly skipped** for utility commands (`--help`, `--version`, `doctor`, `info`, `config`)

## Testing Performed
- ✅ `make lint-fix` - All fixes applied
- ✅ `make quality` - All linting checks passed
- ✅ Manual testing of multiple command types
- ✅ Verified banner appears before progress indicators
- ✅ Verified utility commands skip banner correctly

## Visual Comparison

### Before (Incorrect)
```
Launching Claude [█████████] Ready  ← Shown first (confusing)

╭─── Claude MPM v5.0.0 ───────────╮
│   Welcome back masa!            │  ← Shown after (wrong)
╰─────────────────────────────────╯
```

### After (Correct)
```
╭─── Claude MPM v5.0.0 ───────────╮
│   Welcome back masa!            │  ← Shown first (correct)
╰─────────────────────────────────╯

Launching Claude [█████████] Ready  ← Shown after (correct)
```

## Files Modified
1. `src/claude_mpm/cli/__init__.py` - Reordered banner and progress bar
2. `src/claude_mpm/cli/startup_display.py` - Updated comment

## Impact
- **User Experience**: Much clearer startup flow with welcome message first
- **Code Logic**: No breaking changes, just reordered execution
- **Performance**: No impact, same operations in different order
- **Compatibility**: Fully backward compatible

## Commit Message
```
fix: display banner before progress bar during startup

Previously, the "Launching Claude..." progress bar appeared
before the welcome banner, creating confusion. Now the banner
displays first, followed by the progress indicators.

Changes:
- Move display_startup_banner() before run_background_services()
- Update comment in startup_display.py to reflect correct order
- Verified with multiple command types (agents, help, version, doctor)

Impact: Better UX with welcome message appearing first
```
