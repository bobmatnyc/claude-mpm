# Output Style Configuration Analysis

**Date**: 2025-01-05
**Issue**: Output style not being set to "Claude-MPM" when launching new instance
**Researcher**: Claude Code Research Agent

## Summary

The output style setting is configured in two separate places with different behaviors:

1. **`deploy_output_style_on_startup()`** (startup.py:303-381) - Copies .md files but **DOES NOT activate** the style
2. **`ClaudeRunner._deploy_output_style()`** (claude_runner.py:705-789) - Both copies files **AND activates** the style
3. **`OutputStyleManager._activate_output_style()`** (output_style_manager.py:303-349) - Sets `activeOutputStyle` in `~/.claude/settings.json`

## Problem Identification

### Root Cause

The `deploy_output_style_on_startup()` function runs during **every** `mpm` command execution but only copies the `.md` files to `~/.claude/output-styles/` directory. It **does not** set the `activeOutputStyle` field in `~/.claude/settings.json`.

The `ClaudeRunner._deploy_output_style()` method does activate the style, but it's **only called** when:
- Running `mpm run` command (the default when you type `mpm`)
- The ClaudeRunner is instantiated

### Code Flow

```
mpm (any command)
  └─> run_background_services() [startup.py:1484]
       └─> deploy_output_style_on_startup() [startup.py:303-381]
            ├─> Copies claude-mpm.md to ~/.claude/output-styles/
            ├─> Copies claude-mpm-teacher.md to ~/.claude/output-styles/
            └─> ❌ DOES NOT set activeOutputStyle in settings.json

mpm run
  └─> ClaudeRunner.__init__() [claude_runner.py:195]
       └─> _deploy_output_style() [claude_runner.py:705-789]
            ├─> Check if already active (lines 733-742)
            ├─> Deploy output style file
            └─> ✅ DOES activate via OutputStyleManager.deploy_output_style()
                 └─> _activate_output_style() [output_style_manager.py:303-349]
                      └─> Sets activeOutputStyle in settings.json
```

## File Locations

### Key Files

1. **`src/claude_mpm/cli/startup.py`**
   - Line 303-381: `deploy_output_style_on_startup()`
   - Line 1484: Called from `run_background_services()`
   - **Issue**: Only copies files, doesn't activate style

2. **`src/claude_mpm/core/claude_runner.py`**
   - Line 195: Calls `_deploy_output_style()` in `__init__`
   - Line 705-789: `_deploy_output_style()` method
   - Line 733-742: Early return check if already active
   - Line 763: Calls `output_style_manager.deploy_output_style()` with `activate=True` (default)

3. **`src/claude_mpm/core/output_style_manager.py`**
   - Line 253-301: `deploy_output_style()` method
   - Line 257: `activate: bool = True` (default parameter)
   - Line 294-295: Calls `_activate_output_style()` if `activate=True`
   - Line 303-349: `_activate_output_style()` method
   - Line 329: **Sets `activeOutputStyle` in settings.json**
   - Line 56: Settings file path: `Path.home() / ".claude" / "settings.json"`

### Settings File

- **Location**: `~/.claude/settings.json`
- **Key Field**: `activeOutputStyle` (should be `"claude-mpm"`)
- **Created/Updated By**: `OutputStyleManager._activate_output_style()`

### Output Style Files

- **Source Files** (in package):
  - `src/claude_mpm/agents/CLAUDE_MPM_OUTPUT_STYLE.md` (professional)
  - `src/claude_mpm/agents/CLAUDE_MPM_TEACHER_OUTPUT_STYLE.md` (teaching)

- **Deployment Target** (user-level):
  - `~/.claude/output-styles/claude-mpm.md` (professional)
  - `~/.claude/output-styles/claude-mpm-teacher.md` (teaching)

## Why It Might Not Be Set

### Scenario 1: First Launch (New Installation)

```
User runs: mpm (any command for first time)
  1. deploy_output_style_on_startup() copies files ✓
  2. But does NOT set activeOutputStyle in settings.json ✗
  3. ClaudeRunner NOT instantiated (unless running `mpm run`)
  4. Result: Files exist but style not active
```

### Scenario 2: Early Return in ClaudeRunner

```
User runs: mpm run (second time)
  1. deploy_output_style_on_startup() detects files exist (up to date)
  2. Skips deployment (line 350-353)
  3. ClaudeRunner._deploy_output_style() called
  4. Checks settings.json (line 733)
  5. If activeOutputStyle != "claude-mpm":
     - Continues to deploy and activate ✓
  6. If activeOutputStyle == "claude-mpm" AND file exists:
     - Returns early (line 742) ✓
```

### Scenario 3: User Changed Style

```
User manually changes activeOutputStyle to "default"
  1. Next mpm run:
     - ClaudeRunner checks settings (line 733)
     - Finds activeOutputStyle = "default" (not "claude-mpm")
     - Continues to re-activate claude-mpm ✓
```

## Solution Options

### Option 1: Add Activation to deploy_output_style_on_startup()

**Modify**: `src/claude_mpm/cli/startup.py:303-381`

Add activation logic to `deploy_output_style_on_startup()`:

```python
def deploy_output_style_on_startup():
    # ... existing file deployment code ...

    # After deploying files, activate the professional style
    from claude_mpm.core.output_style_manager import OutputStyleManager
    manager = OutputStyleManager()
    if manager.supports_output_styles():
        manager._activate_output_style("claude-mpm")
```

**Pros**:
- Works for all commands, not just `mpm run`
- Consistent activation on every startup
- Fixes first-launch issue

**Cons**:
- Adds overhead to all commands
- Imports OutputStyleManager on every startup

### Option 2: Remove Early Return Check in ClaudeRunner

**Modify**: `src/claude_mpm/core/claude_runner.py:726-744`

Remove or modify the early return check to always activate:

```python
# Remove lines 726-744 early return check
# OR change to only check file existence, not activeOutputStyle
```

**Pros**:
- Ensures activation on every `mpm run`
- Simple change

**Cons**:
- Only fixes `mpm run`, not other commands
- Doesn't help first launch if user runs different command

### Option 3: Separate Activation Command

**Add**: New CLI command `mpm configure output-style activate`

Create dedicated command to activate output style.

**Pros**:
- User control
- Clear intent

**Cons**:
- Requires user action
- Not automatic
- Doesn't solve "expected to work automatically" issue

## Recommended Solution

**Option 1** is recommended because:
1. It ensures activation happens for all commands
2. Fixes the first-launch issue
3. The overhead is minimal (only runs if Claude Code >= 1.0.83)
4. Aligns with existing design (already imports OutputStyleManager in some flows)

## Implementation Details

### Current Activation Flow

```python
# output_style_manager.py:303-349
def _activate_output_style(self, style_name: str = "claude-mpm") -> bool:
    settings = {}
    if self.settings_file.exists():
        try:
            settings = json.loads(self.settings_file.read_text())
        except json.JSONDecodeError:
            self.logger.warning("Could not parse existing settings.json")

    current_style = settings.get("activeOutputStyle")

    if current_style != style_name:
        settings["activeOutputStyle"] = style_name
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)
        self.settings_file.write_text(json.dumps(settings, indent=2))
        self.logger.info(f"✅ Activated {style_name} output style")
    else:
        self.logger.debug(f"{style_name} output style already active")

    return True
```

### Proposed Change to startup.py

```python
def deploy_output_style_on_startup():
    """Deploy and activate claude-mpm output styles on CLI startup."""
    try:
        import shutil
        from pathlib import Path

        # ... existing file deployment code (lines 324-366) ...

        # NEW: Activate the professional style after deployment
        from claude_mpm.core.output_style_manager import OutputStyleManager

        manager = OutputStyleManager()
        if manager.supports_output_styles():
            # Only activate if Claude Code version supports it (>= 1.0.83)
            manager._activate_output_style("claude-mpm")

    except Exception as e:
        # Non-critical - log but don't fail startup
        from ..core.logger import get_logger
        logger = get_logger("cli")
        logger.debug(f"Failed to deploy/activate output styles: {e}")
```

## Testing Verification

To verify the fix:

1. **Check settings.json**: `cat ~/.claude/settings.json | jq .activeOutputStyle`
   - Should return: `"claude-mpm"`

2. **Check output style files exist**:
   ```bash
   ls -la ~/.claude/output-styles/
   # Should show: claude-mpm.md and claude-mpm-teacher.md
   ```

3. **Test first launch**:
   ```bash
   # Remove settings to simulate first launch
   mv ~/.claude/settings.json ~/.claude/settings.json.backup

   # Run any mpm command
   mpm --version

   # Check if activeOutputStyle is set
   cat ~/.claude/settings.json | jq .activeOutputStyle
   ```

4. **Test style change detection**:
   ```bash
   # Change style manually
   jq '.activeOutputStyle = "default"' ~/.claude/settings.json > tmp.json
   mv tmp.json ~/.claude/settings.json

   # Run mpm
   mpm run

   # Verify it's back to claude-mpm
   cat ~/.claude/settings.json | jq .activeOutputStyle
   ```

## Related Code

### Version Detection

```python
# output_style_manager.py:175-185
def supports_output_styles(self) -> bool:
    """Check if Claude Code supports output styles (>= 1.0.83)."""
    if not self.claude_version:
        return False
    return self._compare_versions(self.claude_version, "1.0.83") >= 0
```

### Version Detection Caching

```python
# output_style_manager.py:26-27
_CACHED_CLAUDE_VERSION: Optional[str] = None
_VERSION_DETECTED: bool = False
```

## Additional Notes

- Claude Code reads output styles from `~/.claude/output-styles/` directory
- The `activeOutputStyle` field in `settings.json` tells Claude Code which style to use
- Output style deployment is non-blocking and should not fail startup
- The system supports two styles: `claude-mpm` (professional) and `claude-mpm-teacher` (teaching)
- Style files must have YAML frontmatter to be recognized by Claude Code
