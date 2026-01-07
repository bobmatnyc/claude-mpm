# CLI Commands Audit - 2025-12-19

## Investigation Summary

Analysis of three CLI entry points defined in `pyproject.toml` to determine their purpose and necessity.

## Commands Analyzed

### 1. `claude-mpm-ticket`

**Entry Point:** `claude_mpm.cli.ticket_cli:main`

**Status:** ⚠️ REDUNDANT - Should be REMOVED

**Analysis:**
- Defined in `src/claude_mpm/cli/ticket_cli.py`
- Acts as a wrapper that delegates to an external `scripts/ticket.py` module
- The `scripts/ticket.py` wrapper itself just calls `claude-mpm tickets` subcommand
- Creates unnecessary indirection: `claude-mpm-ticket` → `scripts/ticket.py` → `claude-mpm tickets`
- No evidence of external dependencies on this specific command

**Recommendation:** **REMOVE**
- This command duplicates functionality already available via `claude-mpm tickets`
- The wrapper adds no value and creates confusing command naming
- Users should use `claude-mpm tickets <subcommand>` directly

**Migration Path:**
```bash
# Old (redundant):
claude-mpm-ticket create "My ticket"

# New (correct):
claude-mpm tickets create "My ticket"
```

---

### 2. `ticket`

**Entry Point:** `claude_mpm.cli.ticket_cli:main`

**Status:** ⚠️ REDUNDANT - Should be REMOVED

**Analysis:**
- Alias for `claude-mpm-ticket` (same entry point)
- Provides a shorter command name but creates namespace pollution
- Same delegation chain as `claude-mpm-ticket`
- The `scripts/ticket.py` wrapper documentation calls this "backward compatibility"
- No evidence that this was ever a standalone command outside of claude-mpm

**Recommendation:** **REMOVE**
- This is an unnecessary alias that pollutes the global command namespace
- The command `ticket` is too generic and conflicts with other potential tools
- Users should use the properly namespaced `claude-mpm tickets` command

**Migration Path:**
```bash
# Old (redundant):
ticket list

# New (correct):
claude-mpm tickets list
```

---

### 3. `claude-mpm-version`

**Entry Point:** `claude_mpm.scripts.manage_version:main`

**Status:** ❌ BROKEN - Should be REMOVED

**Analysis:**
- Entry point references `claude_mpm.scripts.manage_version` module
- **Module does not exist** - was deleted in commit `9634cbf8` (Aug 18, 2025)
- Deletion reason: "consolidate version management to use only Commitizen"
- Command is broken and will fail with `ModuleNotFoundError` if called
- Version management now handled by Commitizen via `cz bump`

**Evidence:**
```bash
$ claude-mpm-version --help
Traceback (most recent call last):
  File "/path/to/claude-mpm-version", line 4, in <module>
    from claude_mpm.scripts.manage_version import main
ModuleNotFoundError: No module named 'claude_mpm.scripts.manage_version'
```

**Recommendation:** **REMOVE IMMEDIATELY**
- This command has been broken since v3.x (August 2025)
- Version management is now handled by Commitizen
- No functionality to preserve - the module was intentionally deleted

**Replacement:**
```bash
# Old (broken):
claude-mpm-version bump

# New (correct):
cz bump
# or
make bump-patch
make bump-minor
make bump-major
```

---

## Summary Recommendations

| Command | Status | Action | Priority |
|---------|--------|--------|----------|
| `claude-mpm-ticket` | Redundant | REMOVE | Medium |
| `ticket` | Redundant | REMOVE | Medium |
| `claude-mpm-version` | Broken | REMOVE | **HIGH** |

### Proposed `pyproject.toml` Changes

**Current:**
```toml
[project.scripts]
claude-mpm = "claude_mpm.cli:main"
claude-mpm-ticket = "claude_mpm.cli.ticket_cli:main"
ticket = "claude_mpm.cli.ticket_cli:main"
claude-mpm-version = "claude_mpm.scripts.manage_version:main"
claude-mpm-monitor = "claude_mpm.scripts.launch_monitor:main"
claude-mpm-socketio = "claude_mpm.scripts.socketio_daemon:main"
claude-mpm-doctor = "claude_mpm.scripts.mpm_doctor:main"
```

**Recommended:**
```toml
[project.scripts]
claude-mpm = "claude_mpm.cli:main"
claude-mpm-monitor = "claude_mpm.scripts.launch_monitor:main"
claude-mpm-socketio = "claude_mpm.scripts.socketio_daemon:main"
claude-mpm-doctor = "claude_mpm.scripts.mpm_doctor:main"
```

### Files to Remove

After removing the commands from `pyproject.toml`, these files can also be deleted:

1. `src/claude_mpm/cli/ticket_cli.py` - No longer needed
2. `scripts/ticket.py` - Wrapper no longer needed
3. `scripts/ticket` - Shell script wrapper no longer needed

### Breaking Changes Impact

**Low Impact:**
- `claude-mpm-version`: Already broken, so no users can be using it
- `claude-mpm-ticket` and `ticket`: Redundant commands that should never have been used
- Proper command `claude-mpm tickets` remains unchanged and fully functional

### Documentation Updates Needed

1. Remove any references to `claude-mpm-ticket` or `ticket` commands
2. Update any examples to use `claude-mpm tickets` instead
3. Add deprecation notice if phasing out gradually
4. Update README and CLI help text if needed

---

## Testing Verification

### Current Behavior

```bash
# Working command (correct):
$ claude-mpm tickets list
[Shows ticket list]

# Redundant alias #1:
$ claude-mpm-ticket list
[Shows ticket list - via wrapper delegation]

# Redundant alias #2:
$ ticket list
[Shows ticket list - via wrapper delegation]

# Broken command:
$ claude-mpm-version --help
ModuleNotFoundError: No module named 'claude_mpm.scripts.manage_version'
```

### After Cleanup

```bash
# Working command (unchanged):
$ claude-mpm tickets list
[Shows ticket list]

# Removed commands should fail:
$ claude-mpm-ticket list
command not found: claude-mpm-ticket

$ ticket list
command not found: ticket

$ claude-mpm-version --help
command not found: claude-mpm-version
```

---

## Conclusion

All three commands should be removed:

1. **`claude-mpm-version`** is broken and needs immediate removal (HIGH priority)
2. **`claude-mpm-ticket`** and **`ticket`** are redundant and create confusion (MEDIUM priority)

The cleanup will:
- Fix a broken command (`claude-mpm-version`)
- Reduce command namespace pollution (`ticket`)
- Eliminate unnecessary indirection (`claude-mpm-ticket`)
- Simplify the codebase by removing wrapper files
- Improve user experience by having one clear way to access ticket functionality

**Recommended Action:** Create a PR to remove all three commands and their associated wrapper files.
