# Git History Integration - Startup Banner

## Overview

The Claude MPM CLI startup banner now displays the 3 most recent git commits in the "Recent activity" section, providing immediate context about recent project changes.

## Features

### Display Format

The git commits are displayed using the format:
```
hash • relative_time • commit_message
```

Example:
```
00d599e1 • 2 hours ago • feat: add light/dark theme support
f04e3673 • 1 day ago • fix: resolve critical Svelte 5 store error
ce9e345f • 3 days ago • chore: bump version to 4.24.4
```

### Layout Integration

The commits are displayed in the "Recent activity" section of the banner:

- **Line 1**: "Recent activity" header
- **Line 2**: "Welcome back {username}!" + First commit
- **Line 3**: Empty left panel + Second commit (or empty if <2 commits)
- **Line 4**: Empty left panel + Third commit (or empty if <3 commits)
- **Line 5**: Separator line

### Truncation

Long commit messages are automatically truncated to fit the right panel width:
- Maximum width: `right_panel_width - 2`
- Truncated messages end with "..." ellipsis
- Ensures no layout overflow or formatting issues

## Error Handling

The implementation fails silently in all error scenarios, displaying "No recent activity" instead:

1. **Not a git repository**: Shows "No recent activity"
2. **Git not installed**: Shows "No recent activity"
3. **Git command fails**: Shows "No recent activity"
4. **Command timeout** (2 seconds): Shows "No recent activity"
5. **No commits in repository**: Shows "No recent activity"

## Implementation Details

### Core Function

```python
def _get_recent_commits(max_commits: int = 3) -> List[str]:
    """
    Get recent git commits for display in startup banner.

    Returns:
        List of formatted commit strings or empty list on any error
    """
```

### Git Command

```bash
git log --format=%h • %ar • %s -3
```

- `%h`: Abbreviated commit hash (short)
- `%ar`: Relative time (e.g., "2 hours ago")
- `%s`: Commit subject (first line of message)
- `-3`: Limit to 3 most recent commits

### Subprocess Settings

```python
subprocess.run(
    ["git", "log", "--format=%h • %ar • %s", "-3"],
    capture_output=True,  # Capture stdout
    text=True,            # Return string, not bytes
    check=True,           # Raise on non-zero exit
    timeout=2,            # 2 second timeout
)
```

## Testing Scenarios

### Test Coverage

The implementation includes comprehensive tests for:

1. ✅ Not a git repository
2. ✅ Git command failure
3. ✅ Command timeout
4. ✅ Correct commit format parsing
5. ✅ Respecting max_commits parameter
6. ✅ Empty git log output
7. ✅ Filtering empty lines
8. ✅ Banner displays "No recent activity" when no commits
9. ✅ Banner displays commits when available
10. ✅ Long commit message truncation
11. ✅ Partial commits (< 3) with padding
12. ✅ Git command format validation
13. ✅ Timeout setting verification
14. ✅ Output capture settings

### Test Results

```bash
$ python -m pytest tests/test_startup_git_integration.py -v
============================= test session starts ==============================
...
15 passed in 0.30s
```

## Usage Examples

### In a Git Repository

```bash
$ python -m claude_mpm.cli run
Launching Claude Multi-agent Product Manager (claude-mpm)...

╭─── Claude MPM v4.24.4 ──────────────────────────────────────╮
│                         │ Recent activity                  │
│   Welcome back masa!    │ a3f5b7c • 2 hours ago • fix: bug │
│                         │ b2d8e9f • 1 day ago • feat: new  │
│                         │ c1a4f3d • 3 days ago • docs      │
│                         │ ─────────────────────────────────│
│     ▐▛███▜▌ ▐▛███▜▌     │ What's new                       │
...
```

### Not in a Git Repository

```bash
$ cd /tmp
$ python -m claude_mpm.cli run
Launching Claude Multi-agent Product Manager (claude-mpm)...

╭─── Claude MPM v4.24.4 ──────────────────────────────────────╮
│                         │ Recent activity                  │
│   Welcome back masa!    │ No recent activity               │
│                         │                                  │
│                         │                                  │
│                         │ ─────────────────────────────────│
...
```

### With Fewer Than 3 Commits

```bash
# Git repo with only 1 commit
╭─── Claude MPM v4.24.4 ──────────────────────────────────────╮
│                         │ Recent activity                  │
│   Welcome back masa!    │ a3f5b7c • 2 hours ago • Initial  │
│                         │                                  │
│                         │                                  │
│                         │ ─────────────────────────────────│
...
```

## File Changes

### Modified Files

1. **`src/claude_mpm/cli/startup_display.py`**
   - Added `subprocess` import
   - Added `is_git_repository` import
   - Added `_get_recent_commits()` helper function
   - Modified `display_startup_banner()` to integrate git commits
   - Updated line numbering comments

### New Files

2. **`tests/test_startup_git_integration.py`**
   - Comprehensive test suite (15 tests)
   - Tests all error scenarios
   - Tests display integration
   - Tests git command format

## Performance Considerations

- **Timeout**: 2 second timeout prevents hanging on slow git operations
- **Fail Silent**: No user-visible errors on git failures
- **Minimal Overhead**: Only runs on startup, not in hot path
- **Repository Check**: Fast check before running git command

## Future Enhancements

Potential future improvements:

1. **Configurable commit count**: Allow users to configure number of commits shown
2. **Branch indicator**: Show current branch name in display
3. **Colorized output**: Use different colors for different commit types (feat, fix, etc.)
4. **Author filtering**: Option to show only user's own commits
5. **Time range filtering**: Option to show commits from specific time range

## Dependencies

- **Python standard library**: `subprocess`, `os`, `re`, `shutil`, `pathlib`
- **Internal utilities**: `claude_mpm.utils.git_analyzer.is_git_repository`
- **External**: Git must be installed and in PATH (optional, fails silently if missing)

## Compatibility

- **Git versions**: Works with all modern git versions (2.0+)
- **Operating systems**: Linux, macOS, Windows
- **Python versions**: Python 3.8+
- **Terminal widths**: Adapts to terminal width (75% of actual width, 100-200 char range)
