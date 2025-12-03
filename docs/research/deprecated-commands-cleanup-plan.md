# Deprecated Commands Cleanup Plan

**Date**: 2025-12-02
**Context**: Identify and remove all deprecated CLI commands and slash commands before v5.1 release
**Status**: 🔍 IN PROGRESS

---

## Deprecated Items Identified

### 1. CLI Commands

#### ⚠️ `claude-mpm agents manage` (DEPRECATED)
**Status**: Redirects to `claude-mpm config`
**Location**: `src/claude_mpm/cli/commands/agents.py:_manage_local_agents()`
**Replacement**: `claude-mpm config` (Agent Management menu option)
**Documentation**: `docs/AGENTS_MANAGE_REDIRECT.md`

**Action**: Complete removal (not just redirect)

**Files to Modify**:
- `src/claude_mpm/cli/commands/agents.py` - Remove `_manage_local_agents()` method
- `src/claude_mpm/cli/parsers/agents_parser.py` - Remove `manage` subparser
- `src/claude_mpm/cli/interactive/agent_wizard.py` - Remove AgentWizard class (if unused elsewhere)
- `tests/test_agents_manage_redirect.py` - Remove redirect tests
- `docs/AGENTS_MANAGE_REDIRECT.md` - Move to archive or remove

---

#### ⚠️ `claude-mpm config` (old standalone function - DEPRECATED)
**Status**: Replaced by unified config command
**Location**: `src/claude_mpm/cli/commands/config.py:448-457`
**Replacement**: New `ConfigureCommand` class with menu system
**Note**: Function marked as "no longer used by the CLI"

**Action**: Remove deprecated function

**Code to Remove**:
```python
def config(args) -> CommandResult:
    """
    Execute config command.

    DEPRECATED: This function is no longer used by the CLI. The 'config' command
    now uses ConfigureCommand class instead.
    """
```

---

#### ⚠️ `/mpm-resume` slash command (DEPRECATED)
**Status**: Renamed to `/mpm-session-resume`
**Location**: Multiple files mention "resume is deprecated, use context instead"
**Files**:
- `src/claude_mpm/cli/commands/mpm_init_handler.py:37` - Warning message
- `src/claude_mpm/cli/commands/mpm_init_cli.py:236` - Note about deprecation

**Action**: Remove old `/mpm-resume` slash command if it still exists

---

#### User-Level Agents (`~/.claude-mpm/agents/`) - DEPRECATED
**Status**: System moved to single-tier Git-based agents
**Location**: `src/claude_mpm/cli/commands/agents.py:1849`
**Replacement**: Git-based agent deployment only

**Action**: Complete removal of user-level agent support

**Files to Check**:
- Agent discovery code
- Agent deployment code
- Configuration files referencing user-level paths

---

### 2. Slash Commands to Review

Based on research docs, need to verify these slash commands exist and check deprecation status:

#### Potential Deprecated Slash Commands
- `/mpm-resume` → Should be `/mpm-session-resume`
- `/mpm-config` → Should be `/mpm-config-view`
- `/mpm-agents` → Should be `/mpm-agents-list`
- `/mpm-organize` → Should be `/mpm-ticket-organize`
- `/mpm-ticket` → Should be `/mpm-ticket-view`
- `/mpm-auto-configure` → Should be `/mpm-agents-auto-configure`

**Action**: Audit all slash commands in `.claude-mpm/commands/` directory

---

### 3. Documentation to Update

#### Files Mentioning Deprecated Features
1. `docs/AGENTS_MANAGE_REDIRECT.md` - Archive or remove
2. `docs/research/agent-source-git-first-migration.md` - Update to reflect current state
3. `docs/research/agent-deployment-single-tier-migration-2025-11-30.md` - Update
4. `docs/guides/single-tier-agent-system.md` - Verify accuracy
5. `docs/developer/pre-publish-checklist.md` - Remove deprecated command references

---

## Cleanup Tasks

### Phase 1: Identify All Deprecated Items ✅ IN PROGRESS
- [x] Search codebase for "DEPRECATED" markers
- [x] Review recent research documents
- [x] Check CLI command structure
- [ ] Audit slash commands directory
- [ ] Review agent deployment paths
- [ ] Check configuration file structures

### Phase 2: Remove Deprecated CLI Commands
- [ ] Remove `claude-mpm agents manage` implementation
  - [ ] Remove `_manage_local_agents()` method from `agents.py`
  - [ ] Remove `manage` subparser from `agents_parser.py`
  - [ ] Remove or deprecate `AgentWizard` class
  - [ ] Remove redirect tests
- [ ] Remove deprecated `config()` function from `config.py`
- [ ] Remove user-level agent support code
  - [ ] Remove `~/.claude-mpm/agents/` discovery
  - [ ] Remove user-level deployment code
  - [ ] Update configuration to remove user-level paths

### Phase 3: Remove Deprecated Slash Commands
- [ ] Audit `.claude-mpm/commands/` directory
- [ ] Remove `/mpm-resume` if exists
- [ ] Remove other deprecated slash commands
- [ ] Update slash command routing if needed

### Phase 4: Update Documentation
- [ ] Archive `docs/AGENTS_MANAGE_REDIRECT.md`
- [ ] Update migration docs to remove deprecation notices
- [ ] Update user guides to show current commands only
- [ ] Update CLI help text
- [ ] Update README.md if affected

### Phase 5: Update Tests
- [ ] Remove tests for deprecated commands
- [ ] Update tests that reference old commands
- [ ] Add tests verifying deprecated commands removed
- [ ] Run full test suite

### Phase 6: Code Quality
- [ ] Run `make pre-publish` to verify linting
- [ ] Run full test suite
- [ ] Verify no breaking changes to active commands
- [ ] Update CHANGELOG.md with removals

---

## Breaking Changes Assessment

### Commands Being Removed
1. ✅ `claude-mpm agents manage` - Users already redirected to `claude-mpm config`
2. ✅ Deprecated `config()` function - Not exposed to users
3. ✅ `/mpm-resume` - Users already have `/mpm-session-resume`
4. ⚠️ User-level agents - May affect users with `~/.claude-mpm/agents/` setups

### Migration Path for Users

#### For `claude-mpm agents manage` Users
**Before**: `claude-mpm agents manage`
**After**: `claude-mpm config` → Select "Agent Management"

**Communication**: Already in place (redirect message)

#### For `/mpm-resume` Users
**Before**: `/mpm-resume`
**After**: `/mpm-session-resume`

**Communication**: Warning message already shows

#### For User-Level Agent Users
**Before**: Agents in `~/.claude-mpm/agents/`
**After**: Git-based agents in `.claude/agents/`

**Communication**: Need migration guide

---

## Risk Assessment

### Low Risk Removals ✅
- Deprecated `config()` function (internal only)
- `/mpm-resume` slash command (replacement exists)
- `claude-mpm agents manage` (redirect in place)

### Medium Risk Removals ⚠️
- User-level agent support (may affect some users)

### High Risk Removals ❌
- None identified

---

## Implementation Strategy

### Conservative Approach (Recommended)
1. **Remove truly obsolete code** (deprecated functions not in use)
2. **Keep redirects for CLI commands** (maintain for 1-2 more versions)
3. **Remove user-level agent code** (if usage is confirmed low)
4. **Update documentation** (remove confusing deprecated references)

### Aggressive Approach (Not Recommended Yet)
1. Remove all deprecated code immediately
2. Risk: May break workflows for users who haven't migrated

---

## Success Criteria

- [ ] All `DEPRECATED` markers removed from codebase (or confirmed intentional)
- [ ] All deprecated CLI commands removed or clearly marked
- [ ] All deprecated slash commands removed
- [ ] Documentation updated to show only current commands
- [ ] Tests pass with deprecated code removed
- [ ] CHANGELOG.md documents all removals
- [ ] Migration guide created for affected users

---

## Next Steps

1. **Audit slash commands directory** - Identify which deprecated slash commands exist
2. **Check user-level agent usage** - Determine impact of removing support
3. **Create removal PR** - Implement removals with tests
4. **Update docs** - Remove deprecated command references
5. **Release v5.1** - With cleanup complete

---

**Analysis Date**: 2025-12-02
**Engineer**: Claude Code (Sonnet 4.5)
**Related**: v5.1 release preparation
