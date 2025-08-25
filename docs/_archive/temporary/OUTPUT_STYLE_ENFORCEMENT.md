# Output Style Enforcement System

## Overview

Claude MPM implements a robust enforcement mechanism to ensure the `claude-mpm` output style is always active when using Claude Code >= 1.0.83. This prevents users from accidentally switching to a different output style that would break the PM delegation framework.

## Key Features

### 1. Automatic Deployment
- Detects Claude Code version on startup
- Automatically deploys `claude-mpm.md` to `~/.claude/output-styles/` for Claude >= 1.0.83
- Falls back to framework injection for older versions

### 2. Continuous Enforcement
- **Initial Activation**: Always sets `activeOutputStyle: "claude-mpm"` in settings.json on startup
- **Change Detection**: Monitors for user changes to the output style
- **Automatic Re-enforcement**: Restores `claude-mpm` style if user selects a different style
- **Enforcement Tracking**: Counts how many times the style has been re-enforced

### 3. User Notifications
- Clear logging when style is enforced
- Warning messages when user changes are detected
- Status display showing enforcement count
- Visual indicators (✅, ⚠️, ℹ️) for different states

## Implementation Details

### OutputStyleManager Class

The `OutputStyleManager` class in `src/claude_mpm/core/output_style_manager.py` handles:

1. **Version Detection**: Detects Claude Code version via `claude --version`
2. **Style Extraction**: Extracts PM delegation rules from INSTRUCTIONS.md and BASE_PM.md
3. **Deployment**: Writes claude-mpm.md to output-styles directory
4. **Activation**: Updates settings.json to activate the style
5. **Enforcement**: Monitors and restores the style if changed

### Key Methods

```python
# Deploy and activate the style
manager.deploy_output_style(content)  # Always replaces and activates

# Check and enforce periodically
manager.enforce_style_periodically()  # Checks every 5 seconds

# Force immediate check (for testing)
manager.enforce_style_periodically(force_check=True)

# Log current status
manager.log_enforcement_status()
```

### Integration Points

1. **Framework Loader** (`framework_loader.py`):
   - Initializes OutputStyleManager on startup
   - Deploys and activates style during initialization
   - Logs enforcement status

2. **Interactive Session** (`interactive_session.py`):
   - Calls `_enforce_output_style()` before launching Claude
   - Displays enforcement status in welcome message
   - Shows enforcement count if style was re-enforced

## Enforcement Logic

### Detection and Re-enforcement Flow

1. **Startup**:
   ```
   Initialize → Deploy Style → Activate in settings.json → Log Status
   ```

2. **Runtime Monitoring**:
   ```
   Check settings.json → Detect change → Log warning → Update to claude-mpm → Write settings → Update counter
   ```

3. **User Change Scenario**:
   - User selects different style in Claude Code menu
   - Claude Code updates settings.json
   - OutputStyleManager detects change on next check
   - Automatically restores claude-mpm style
   - Logs warning with enforcement count

## Status Messages

### Success States
- `✅ Claude MPM output style is active and enforced`
- `✅ Activated claude-mpm output style (was: <previous>)`
- `✅ Output style deployed to Claude Code >= 1.0.83`

### Warning States
- `⚠️ Output style was changed from 'claude-mpm' to '<style>' - re-enforcing claude-mpm style`
- `⚠️ Detected style change to '<style>' - enforcing claude-mpm`
- `⚠️ Output style is '<style>' - will be enforced to 'claude-mpm'`

### Info States
- `ℹ️ Style has been re-enforced N times this session`
- `📁 Output style file exists: <path>`
- `📝 Output style will be created at: <path>`

## Testing

### Test Scripts

1. **test_output_style_enforcement.py**: Comprehensive test suite for enforcement mechanism
2. **test_style_integration.py**: Integration test with framework
3. **test_runtime_enforcement.sh**: Shell script for runtime testing
4. **debug_enforcement.py**: Debug tool for troubleshooting

### Running Tests

```bash
# Run enforcement tests
python scripts/test_output_style_enforcement.py

# Test integration
python scripts/test_style_integration.py

# Debug enforcement
python scripts/debug_enforcement.py
```

## Limitations

### Known Issues

1. **Menu Display**: Cannot control Claude Code's /output-style menu display
   - The menu is part of Claude Code's native UI
   - We can only control what's in settings.json
   - User may see different styles in menu but claude-mpm will be enforced

2. **Timing**: 5-second check interval to avoid excessive file I/O
   - User may temporarily see wrong style for up to 5 seconds
   - Can be overridden with `force_check=True` for immediate enforcement

3. **Persistence**: Enforcement only active while claude-mpm is running
   - Style remains set after claude-mpm exits
   - But won't be re-enforced if user changes it outside claude-mpm session

## Troubleshooting

### Style Not Being Enforced

1. Check Claude version:
   ```bash
   claude --version  # Should be >= 1.0.83
   ```

2. Verify settings.json:
   ```bash
   cat ~/.claude/settings.json | jq '.activeOutputStyle'
   ```

3. Check deployment:
   ```bash
   ls -la ~/.claude/output-styles/claude-mpm.md
   ```

4. Run debug script:
   ```bash
   python scripts/debug_enforcement.py
   ```

### Enforcement Counter Not Updating

The counter only increments when:
- User changes from claude-mpm to another style
- The change is detected by the enforcement check
- The style is successfully restored to claude-mpm

### Logs Not Showing

Enforcement logs are at INFO and WARNING level. Ensure logging is configured:
```python
import logging
logging.basicConfig(level=logging.INFO)
```

## Future Improvements

1. **Real-time Monitoring**: Use file system watchers for immediate detection
2. **User Preference**: Add config option to disable enforcement if desired
3. **Style Backup**: Save user's preferred style and restore on exit
4. **Menu Integration**: Work with Claude Code team for native menu integration
5. **Performance**: Optimize file I/O for faster checks