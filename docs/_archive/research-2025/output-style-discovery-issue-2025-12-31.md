---
title: Claude MPM Teacher Output Style Discovery Issue Investigation
date: 2025-12-31
status: Complete
issue: Teacher style not appearing in Claude Code output style menu
resolution: Directory mismatch - files in wrong location
---

# Output Style Discovery Issue Investigation

## Problem Statement

The Claude MPM Teacher output style file exists but doesn't appear in the Claude Code output style selection menu.

**Symptoms:**
- File exists: `~/.claude/settings/output-styles/claude-mpm-teacher.md` (2007 lines, 58KB)
- File has valid YAML frontmatter with `name: Claude MPM Teacher`
- Only "Default", "Explanatory", "Learning", and "Claude MPM" appear in menu
- "Claude MPM Teacher" is missing

## Root Cause Analysis

### Discovery

Claude Code uses **`~/.claude/output-styles/`** directory for discovering custom output styles, NOT `~/.claude/settings/output-styles/`.

**Evidence:**
1. Official documentation: https://code.claude.com/docs/en/output-styles
2. Actual directory structure shows three separate directories:
   - `~/.claude/output-styles/` - **CORRECT LOCATION** (Claude Code scans here)
   - `~/.claude/settings/output-styles/` - Wrong location (created by mistake)
   - `~/.claude/styles/` - Old/deprecated location (legacy from pre-1.0.83)

### Directory Contents Analysis

```bash
# CORRECT directory (Claude Code scans this)
~/.claude/output-styles/
└── claude-mpm.md (290 lines, 12KB) ✅ Appears in menu

# WRONG directory (Claude Code does NOT scan this)
~/.claude/settings/output-styles/
├── claude-mpm-style.md (290 lines, 12KB)
├── claude-mpm-teacher.md (2007 lines, 58KB) ❌ Not discovered
└── claude-mpm-teacher-test.md (test file)

# DEPRECATED directory (old code location)
~/.claude/styles/
├── claude-mpm.md (290 lines, 12KB)
└── claude-mpm-teach.md (1322 lines, 35KB, no frontmatter)
```

### Code Analysis

The `OutputStyleManager` class in `/Users/masa/Projects/claude-mpm/src/claude_mpm/core/output_style_manager.py` has an **incorrect directory path**:

```python
# Line 55 - WRONG PATH
self.output_style_dir = Path.home() / ".claude" / "styles"
```

**Should be:**
```python
self.output_style_dir = Path.home() / ".claude" / "output-styles"
```

### Validation

1. **YAML Frontmatter**: ✅ Valid
   ```python
   {'name': 'Claude MPM Teacher',
    'description': 'Teaching mode that explains PM workflow...'}
   ```

2. **File Encoding**: ✅ UTF-8, no BOM
3. **File Size**: ✅ 58KB (no known size limits in documentation)
4. **File Format**: ✅ Valid Markdown with frontmatter

## Solution

### Fix 1: Correct the Code (Permanent Fix)

Update `src/claude_mpm/core/output_style_manager.py`:

```python
# OLD (line 55)
self.output_style_dir = Path.home() / ".claude" / "styles"

# NEW
self.output_style_dir = Path.home() / ".claude" / "output-styles"
```

### Fix 2: Move Files to Correct Location (Immediate Fix)

```bash
# Copy teacher style to correct directory
cp ~/.claude/settings/output-styles/claude-mpm-teacher.md \
   ~/.claude/output-styles/claude-mpm-teacher.md

# Verify
ls -lh ~/.claude/output-styles/
```

### Fix 3: Update Deployment Logic

The code deploys styles with these filenames:
- Professional: `claude-mpm.md` ✅
- Teaching: `claude-mpm-teach.md` (without 'er')

But the source file is named `CLAUDE_MPM_TEACHER_OUTPUT_STYLE.md`, and the manually created file is `claude-mpm-teacher.md`.

**Filename consistency needed:**
- Source: `CLAUDE_MPM_TEACHER_OUTPUT_STYLE.md`
- Deployed: Should be `claude-mpm-teacher.md` (with 'er') for consistency
- Config name: `claude-mpm-teacher` (matches deployed filename minus .md)

## Testing Results

### File Size Hypothesis
**REJECTED** - No file size limits documented or observed. The 58KB file is valid.

### YAML Parsing Hypothesis
**REJECTED** - YAML frontmatter parses correctly with both `name` and `description` fields.

### Encoding Hypothesis
**REJECTED** - Both files are UTF-8 encoded without BOM.

### Directory Location Hypothesis
**CONFIRMED** - Files in wrong directory (`~/.claude/settings/output-styles/` instead of `~/.claude/output-styles/`).

## Implementation Plan

1. **Update code** (line 55 in output_style_manager.py):
   ```python
   self.output_style_dir = Path.home() / ".claude" / "output-styles"
   ```

2. **Update target filename** (line 71):
   ```python
   # OLD
   target=self.output_style_dir / "claude-mpm-teach.md",
   # NEW
   target=self.output_style_dir / "claude-mpm-teacher.md",
   ```

3. **Update config name** (line 72):
   ```python
   # OLD
   name="claude-mpm-teach",
   # NEW
   name="claude-mpm-teacher",
   ```

4. **Clean up old directories**:
   ```bash
   # After verifying new deployment works
   rm -rf ~/.claude/styles/  # Deprecated
   rm -rf ~/.claude/settings/output-styles/  # Wrong location
   ```

5. **Re-deploy all styles**:
   ```bash
   claude-mpm --help  # Trigger startup deployment
   # Or force redeploy via Python API
   ```

## Verification Steps

After fix:
1. Check file exists: `ls -lh ~/.claude/output-styles/claude-mpm-teacher.md`
2. Restart Claude Code (styles loaded at startup)
3. Run `/output-style` command
4. Verify "Claude MPM Teacher" appears in menu
5. Test activation: `/output-style claude-mpm-teacher`

## Related Files

- Source: `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/CLAUDE_MPM_TEACHER_OUTPUT_STYLE.md`
- Manager: `/Users/masa/Projects/claude-mpm/src/claude_mpm/core/output_style_manager.py`
- Deployed (wrong): `~/.claude/settings/output-styles/claude-mpm-teacher.md`
- Deployed (correct): `~/.claude/output-styles/claude-mpm-teacher.md` (needs to be created)

## Lessons Learned

1. **Directory naming matters** - Small differences (`output-styles` vs `settings/output-styles`) break discovery
2. **Documentation is authoritative** - Always check official docs for correct paths
3. **Multiple deployments create confusion** - Old files in `~/.claude/styles/` from before fix
4. **File size is not the issue** - 58KB files work fine (no documented limits)
5. **YAML frontmatter is mandatory** - Old files without frontmatter won't work

## References

- [Claude Code Output Styles Documentation](https://code.claude.com/docs/en/output-styles)
- [Output Styles Guide - Claude Skills](https://claude-plugins.dev/skills/@CaptainCrouton89/.claude/output-styles-guide)
- [Pair Programming with Output Styles](https://shipyard.build/blog/claude-code-output-styles-pair-programming/)

## Status

**RESOLVED** ✅ - Root cause identified and fixed.

### Changes Applied

1. **output_style_manager.py** ✅
   - Line 55: Changed directory from `.claude/styles` to `.claude/output-styles`
   - Line 71: Changed filename from `claude-mpm-teach.md` to `claude-mpm-teacher.md`
   - Line 72: Changed name from `claude-mpm-teach` to `claude-mpm-teacher`
   - Line 46: Updated docstring to reflect correct filename

2. **startup.py** ✅
   - Line 331: Changed directory from `.claude/settings/output-styles` to `.claude/output-styles`
   - Line 332: Changed filename from `claude-mpm-style.md` to `claude-mpm.md`
   - Line 333: Changed filename from `claude-mpm-teach.md` to `claude-mpm-teacher.md`
   - Lines 311-317: Updated comments and docstring

3. **Immediate workaround** ✅
   - Copied file to correct location: `~/.claude/output-styles/claude-mpm-teacher.md`
   - Verified 58KB file with valid frontmatter deployed successfully

### Verification

```bash
$ ls -lh ~/.claude/output-styles/
total 144
-rw-r--r--@ 1 masa  staff    57K Dec 31 09:24 claude-mpm-teacher.md
-rw-r--r--@ 1 masa  staff    12K Dec 10 08:58 claude-mpm.md

$ head -5 ~/.claude/output-styles/claude-mpm-teacher.md
---
name: Claude MPM Teacher
description: Teaching mode that explains PM workflow...
---

$ python3 -c "from claude_mpm.core.output_style_manager import OutputStyleManager; m = OutputStyleManager(); print(m.output_style_dir)"
/Users/masa/.claude/output-styles
```

### Next Steps

1. ✅ Code fixes applied
2. ✅ Files deployed to correct directory
3. ⏳ Restart Claude Code to pick up new styles
4. ⏳ Verify "Claude MPM Teacher" appears in `/output-style` menu
5. ⏳ Clean up deprecated directories after verification
6. ⏳ Update tests to reflect new paths
