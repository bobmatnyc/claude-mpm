# Skills UX Alignment Analysis

**Date**: 2025-12-02
**Context**: Verify skills command has same UX improvements as agents command
**Status**: ❌ **MISALIGNMENT DETECTED**

---

## Current State Comparison

### Agents Command (`claude-mpm configure`)

**UX Features** (Recently implemented):
1. ✅ Interactive checkbox interface (questionary.checkbox)
2. ✅ Status column showing Installed/Available in main table
3. ✅ Pre-selection for installed agents (checked=True)
4. ✅ Simplified checkbox labels (removed `[Installed]` / `[Available]` text)
5. ✅ While loop allowing adjustment after selection
6. ✅ Apply/Adjust/Cancel menu instead of simple yes/no
7. ✅ Deployment status detection using `get_deployed_agent_ids()`

**Implementation**: `src/claude_mpm/cli/commands/configure.py`
- Lines 341-346: Set is_deployed attribute
- Lines 1057-1247: Checkbox selection with while loop
- Lines 1069-1080: Simplified checkbox choices
- Lines 1140-1158: Apply/Adjust/Cancel menu

### Skills Command (`claude-mpm skills deploy-github`)

**UX Features** (Current):
1. ❌ No interactive checkbox interface
2. ❌ No status column in main table
3. ❌ Command-line arguments only (--toolchain, --all, --force)
4. ❌ No pre-selection based on deployment status
5. ❌ No adjustment option
6. ❌ No Apply/Adjust/Cancel menu
7. ❌ No deployment status detection

**Implementation**: `src/claude_mpm/cli/commands/skills.py`
- Lines 532-605: `_deploy_from_github()` - uses command arguments only
- Lines 607-655: `_list_available_github_skills()` - shows tables but no interaction
- Lines 657-697: `_check_deployed_skills()` - shows deployed skills in table

---

## Specific Differences

| Feature | Agents Command | Skills Command | Alignment Needed? |
|---------|---------------|----------------|-------------------|
| Interactive selection | ✅ Checkbox interface | ❌ CLI args only | ✅ YES |
| Status display | ✅ Status column | ❌ None | ✅ YES |
| Pre-selection | ✅ checked=True | ❌ N/A | ✅ YES |
| Adjust option | ✅ While loop + menu | ❌ None | ✅ YES |
| Deployment detection | ✅ get_deployed_agent_ids() | ✅ check_deployed_skills() | ⚠️ PARTIAL |
| Simplified labels | ✅ Checkbox state only | ❌ N/A | ✅ YES |

---

## Architecture Differences

### Agents: Interactive Flow

```
configure.py:run()
    ↓
Discover agents → Set is_deployed attribute
    ↓
While True:
    ↓
    Display checkbox (pre-selected if installed)
    ↓
    User selects/unselects
    ↓
    Show selections
    ↓
    Apply/Adjust/Cancel menu
    ↓
    if Adjust: continue (loop back)
    if Apply: break, execute deployment
    if Cancel: return
```

### Skills: Command-Line Flow

```
skills.py:_deploy_from_github()
    ↓
Parse CLI arguments (--toolchain, --all, --force)
    ↓
Call skills_deployer.deploy_skills()
    ↓
Display results (deployed/skipped/errors)
    ↓
Done (no adjustment option)
```

---

## Recommended Changes for Skills

### Option 1: Add Interactive Mode (Recommended)

**Create new command**: `claude-mpm skills configure` (matching agents)

**Features**:
1. Interactive checkbox selection like agents
2. Status column showing Installed/Available
3. Pre-selection for installed skills
4. Apply/Adjust/Cancel menu
5. While loop for adjustment
6. Leverage existing `check_deployed_skills()` for status detection

**Implementation**:
- New method: `_configure_skills()` in skills.py
- Reuse patterns from configure.py
- Keep existing `deploy-github` command for CLI automation

### Option 2: Enhance Existing Command

**Modify**: `claude-mpm skills deploy-github`

**Features**:
1. Add `--interactive` flag
2. If --interactive: Use checkbox interface
3. If not --interactive: Keep current CLI args behavior
4. Backward compatible with existing scripts

### Option 3: Separate Commands (Hybrid)

**Keep both**:
- `claude-mpm skills deploy-github`: CLI args (automation)
- `claude-mpm skills configure`: Interactive (user-friendly)

**Benefits**:
- Clear separation of concerns
- Matches agents pattern (`configure` for interactive)
- Preserves automation capability

---

## Implementation Roadmap

### Phase 1: Status Detection (EASY)

**Task**: Add deployment status to skills list display
**Files**: `src/claude_mpm/cli/commands/skills.py`
**Changes**:
1. Use `check_deployed_skills()` to get deployed set
2. Add Status column to skills table in `_list_skills()`
3. Show "Installed" (green) or "Available" for each skill

**Estimate**: 30 minutes

### Phase 2: Interactive Mode (MEDIUM)

**Task**: Create `skills configure` command with checkbox interface
**Files**: `src/claude_mpm/cli/commands/skills.py`
**Changes**:
1. Add `_configure_skills()` method
2. Implement checkbox selection (copy from configure.py pattern)
3. Add Apply/Adjust/Cancel menu
4. Add while loop for adjustment
5. Pre-select installed skills

**Estimate**: 2-3 hours

### Phase 3: Parser Updates (EASY)

**Task**: Update CLI parser to support new command
**Files**: `src/claude_mpm/cli/parsers/skills_parser.py`
**Changes**:
1. Add `configure` subcommand to skills parser
2. Route to `_configure_skills()` method

**Estimate**: 30 minutes

---

## User Request Interpretation

**Original request**: 
> "let's also verify skills works the same way"

**Interpretation**:
- "same way" = same UX improvements as agents
- This includes: checkbox interface, status display, adjust option, pre-selection

**Current finding**: Skills does NOT work the same way - significant UX gap exists

---

## Recommendation

**Implement Option 3** (Separate Commands - Hybrid approach):

1. ✅ Keep `skills deploy-github` for CLI automation (existing users)
2. ✅ Add `skills configure` for interactive mode (matching agents UX)
3. ✅ Status column in both commands
4. ✅ Clear documentation on when to use each

**Rationale**:
- Matches agents pattern (configure = interactive)
- Preserves backward compatibility
- Provides automation capability
- Best user experience

---

## Next Steps

1. **Confirm approach with user** - Which option (1, 2, or 3)?
2. **Implement Phase 1** - Add status display to skills list
3. **Implement Phase 2** - Create interactive configure command
4. **Update documentation** - Document new workflow
5. **Test with presets** - Verify MIN/MAX presets work with new UX

---

**Analysis Date**: 2025-12-02
**Engineer**: Claude Code (Sonnet 4.5)
**Related Tickets**: 1M-502 Phase 2 - UX Improvements

