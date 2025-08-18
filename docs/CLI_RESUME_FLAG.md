# CLI Resume Flag Documentation

## Overview

As of version 4.0.14, Claude MPM properly handles both Claude's native `--resume` flag and MPM's session management functionality through separate flags.

## Flags

### `--resume` (Claude Native)
- **Purpose**: Passes through to Claude Desktop's native resume functionality
- **Usage**: `claude-mpm run --resume`
- **Behavior**: Opens Claude's native resume screen showing recent conversations

### `--mpm-resume` (MPM Session Management)
- **Purpose**: Resume a specific MPM session with context
- **Usage**: 
  - `claude-mpm run --mpm-resume` - Resume last session
  - `claude-mpm run --mpm-resume SESSION_ID` - Resume specific session
- **Behavior**: Restores MPM session context, agent history, and related metadata

## Migration Guide

If you were previously using `--resume` for MPM session management:

**Before (v4.0.13 and earlier):**
```bash
# This incorrectly tried to use MPM session management
claude-mpm run --resume last
claude-mpm run --resume session123
```

**After (v4.0.14+):**
```bash
# Use --mpm-resume for MPM session management
claude-mpm run --mpm-resume last
claude-mpm run --mpm-resume session123

# Use --resume for Claude's native functionality
claude-mpm run --resume
```

## Technical Details

### Why This Change?

Previously, the `--resume` flag was incorrectly captured by MPM and filtered out, preventing it from reaching Claude's native CLI. This caused user confusion as they expected `claude-mpm run --resume` to show Claude's native resume screen.

### Implementation

The fix involved:
1. Renaming MPM's internal `--resume` to `--mpm-resume`
2. Removing `--resume` from the `mpm_flags` filter set
3. Updating all internal references to use `mpm_resume`
4. Ensuring backward compatibility for existing MPM session management

### Testing

Run the test script to verify the implementation:
```bash
python scripts/test_resume_fix.py
```

## Examples

```bash
# Open Claude's native resume screen
claude-mpm run --resume

# Resume last MPM session with context
claude-mpm run --mpm-resume

# Resume specific MPM session
claude-mpm run --mpm-resume abc123def456

# List available MPM sessions
claude-mpm sessions

# Both flags can technically be used together (edge case)
# --resume passes to Claude, --mpm-resume handled by MPM
claude-mpm run --resume --mpm-resume last
```