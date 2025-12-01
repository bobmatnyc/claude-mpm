# Claude MPM CLI Command Structure Review

**Date**: 2025-12-01
**Version**: v5.0.0
**Reviewer**: Claude (Engineer Agent)

## Executive Summary

This review examines the current CLI command structure for inconsistencies, redundancies, and opportunities for improvement. Overall, the CLI is functional and well-organized, but there are several areas where consistency could be improved.

## Current Command Structure

### Top-Level Commands (25 total)

```
claude-mpm [COMMAND]

Core Commands:
  - run                   (default command)
  - agents                (22 subcommands)
  - skills                (15 subcommands)
  - tickets               (ticket management)

Source Management:
  - source                (agent source repositories)
  - agent-source          (agent source repositories)
  - skill-source          (skill source repositories)

Configuration:
  - auto-configure        (agent auto-config)
  - configure             (interactive config)
  - config                (validate/manage config)

Tooling:
  - mcp                   (MCP Gateway)
  - mcp-pipx-config       (MCP pipx setup)
  - agent-manager         (agent lifecycle)
  - memory                (agent memory)
  - monitor               (Socket.IO monitoring)
  - dashboard             (web dashboard)
  - local-deploy          (local dev deployments)

Analysis:
  - analyze               (code analysis + mermaid)
  - analyze-code          (AST tree + metrics)
  - mpm-search            (semantic search)
  - aggregate             (event aggregator)

Maintenance:
  - doctor                (diagnostics)
  - cleanup-memory        (clean conversation history)
  - uninstall             (remove components)
  - upgrade               (update version)
  - verify                (verify MCP services)
  - hook-errors           (hook diagnostics)
  - debug                 (dev debugging)

Project Setup:
  - mpm-init              (project initialization)
```

## Identified Inconsistencies

### 1. Naming Convention Inconsistencies

#### Kebab-Case vs Single-Word
- ✅ **Consistent kebab-case**: `agent-source`, `skill-source`, `mcp-pipx-config`, `cleanup-memory`
- ❌ **Inconsistent single-word**: `agents`, `skills`, `tickets`, `monitor`
- 📝 **Observation**: Core commands use single words, utility commands use kebab-case

#### Subcommand Naming Patterns
**Agents subcommands**:
- `cleanup` (single word)
- `cleanup-orphaned` (kebab-case)
- `deps-list`, `deps-fix` (prefix-action)
- `deploy`, `deploy-all`, `deploy-minimal`, `deploy-auto` (action-scope)
- `migrate-to-project` (full description)

**Skills subcommands**:
- `collection-list`, `collection-add`, `collection-remove` (prefix-action)
- `deploy-github` (action-scope)

**Recommendation**: Standardize on one pattern:
- Option A: Always use prefix-action (`deps-list`, `collection-list`)
- Option B: Use single words for primary actions, kebab-case for variants (`cleanup` vs `cleanup-orphaned`)

### 2. Command Duplication and Redundancy

#### Source Management Commands
**Current**:
```
- source          (agent source repositories)
- agent-source    (agent source repositories)
- skill-source    (skill source repositories)
```

**Issue**: `source` and `agent-source` have identical descriptions.

**Recommendation**:
- Remove `source` as a top-level command (or make it an alias)
- Keep `agent-source` and `skill-source` as separate top-level commands
- **OR** merge into: `agents source` and `skills source` as subcommands

#### Auto-Configuration Commands
**Current**:
```
Top-level:
- auto-configure    (agent auto-config)

Agents subcommands:
- detect            (detect toolchain)
- recommend         (show recommendations)
- deploy-auto       (auto-detect and deploy)
```

**Issue**: `auto-configure` is top-level but relates to agents. `detect`, `recommend`, and `deploy-auto` are agent subcommands but do similar work.

**Recommendation**:
- Move `auto-configure` → `agents auto-configure` (alias to `deploy-auto`)
- Keep `agents detect` and `agents recommend` as separate exploration commands
- Keep `agents deploy-auto` as the full automation command

#### Analysis Commands
**Current**:
```
- analyze           (code analysis + mermaid)
- analyze-code      (AST tree + metrics)
```

**Issue**: Two similar analysis commands at top level.

**Recommendation**:
- Make `analyze-code` a subcommand of `analyze` → `analyze ast`
- Add `analyze mermaid` as explicit subcommand
- **OR** keep separate but rename `analyze-code` → `analyze-ast` for clarity

### 3. Deploy Command Proliferation

**Agents Deploy Commands** (4 variants):
```
- agents deploy             (standard deployment)
- agents deploy-all         (deploy from all sources)
- agents deploy-minimal     (6 core agents)
- agents deploy-auto        (detect + deploy)
```

**Skills Deploy Commands** (2 variants):
```
- skills deploy             (bundled skills)
- skills deploy-github      (GitHub skills)
```

**Recommendation**:
- Add flags instead of separate commands:
  - `agents deploy --all`
  - `agents deploy --minimal`
  - `agents deploy --auto`
- Keep `deploy-all`, `deploy-minimal`, `deploy-auto` as aliases for backward compatibility

### 4. Cleanup Command Ambiguity

**Current**:
```
Top-level:
- cleanup-memory    (aliases: cleanup, clean)

Agents subcommands:
- cleanup           (sync, install, remove old agents)
- cleanup-orphaned  (remove agents without templates)
```

**Issue**: `cleanup-memory` has `cleanup` alias, which conflicts conceptually with `agents cleanup`.

**Recommendation**:
- Remove `cleanup` alias from `cleanup-memory`
- Keep only `clean` alias for `cleanup-memory`
- This makes `agents cleanup` the primary cleanup command for agents

### 5. Inconsistent Command Grouping

**Current Structure**:
```
Top-level: agent-source, skill-source
Subcommands: agents, skills
```

**Recommendation**: Consider moving source management to subcommands:
```
agents source add <url>
agents source list
agents source remove <id>

skills source add <url>
skills source list
skills source remove <id>
```

This creates a more intuitive hierarchy:
- `agents` → everything agent-related
- `skills` → everything skill-related

### 6. Command Aliases Inconsistencies

**Commands with aliases**:
- `analyze` → `analysis`, `code-analyze`
- `mpm-search` → `search`
- `cleanup-memory` → `cleanup`, `clean`
- `doctor` → `diagnose`, `check-health`

**Commands without aliases (but could benefit)**:
- `agents` (could have `agent`)
- `skills` (could have `skill`)
- `tickets` (could have `ticket`, `ticketing`)

**Recommendation**: Add common aliases for frequently used commands:
- `agent` → `agents`
- `skill` → `skills`
- `ticket` → `tickets`

## Proposed Changes (Prioritized)

### 🔴 High Priority (Breaking Changes - Next Major Version)

1. **Consolidate Source Commands**
   ```
   Remove: claude-mpm source
   Rename: agent-source → agents source (subcommand)
   Rename: skill-source → skills source (subcommand)
   ```

2. **Move Auto-Configure to Agents**
   ```
   Remove: claude-mpm auto-configure
   Add: claude-mpm agents auto-configure (alias to deploy-auto)
   ```

3. **Fix Cleanup Ambiguity**
   ```
   Remove 'cleanup' alias from cleanup-memory
   Keep only 'clean' alias for cleanup-memory
   ```

### 🟡 Medium Priority (Non-Breaking - Can Do Now)

4. **Add Common Aliases**
   ```
   Add: agent → agents
   Add: skill → skills
   Add: ticket → tickets
   ```

5. **Consolidate Deploy Commands with Flags**
   ```
   Keep existing commands as aliases
   Add: agents deploy --all
   Add: agents deploy --minimal
   Add: agents deploy --auto
   ```

6. **Standardize Analysis Commands**
   ```
   Keep: analyze (with subcommands)
   Add: analyze ast (current analyze-code)
   Add: analyze mermaid
   Keep: analyze-code as deprecated alias
   ```

### 🟢 Low Priority (Documentation Only)

7. **Document Command Patterns**
   - Create style guide for new commands
   - Document when to use kebab-case vs single-word
   - Document when to create subcommands vs flags

8. **Add Help Text Improvements**
   - Ensure all commands have clear descriptions
   - Add examples to help text
   - Improve consistency in help formatting

## Implementation Strategy

### Phase 1: Non-Breaking Changes (Current Release)
- Add aliases (`agent`, `skill`, `ticket`)
- Add deploy flags (`--all`, `--minimal`, `--auto`)
- Fix cleanup-memory aliases (remove `cleanup` alias)
- Document current patterns

### Phase 2: Deprecation Warnings (Next Minor Release)
- Add deprecation warnings for:
  - `claude-mpm source` → "Use 'agents source' or 'skills source'"
  - `claude-mpm auto-configure` → "Use 'agents auto-configure' or 'agents deploy-auto'"
  - `analyze-code` → "Use 'analyze ast'"

### Phase 3: Breaking Changes (Next Major Release v6.0.0)
- Remove deprecated commands
- Move source commands to subcommands
- Consolidate deploy commands
- Restructure analysis commands

## Command Naming Style Guide (Proposed)

### For New Commands

1. **Top-Level Commands**: Use single words or kebab-case for major feature areas
   - ✅ `agents`, `skills`, `tickets`
   - ✅ `agent-source`, `skill-source` (until moved to subcommands)

2. **Subcommands**: Use single words for primary actions, kebab-case for variants
   - ✅ Primary: `list`, `deploy`, `create`, `edit`, `delete`
   - ✅ Variants: `deploy-all`, `deploy-minimal`, `cleanup-orphaned`

3. **Prefixed Subcommands**: Use consistent prefix-action pattern
   - ✅ `deps-list`, `deps-fix`, `deps-check`
   - ✅ `collection-list`, `collection-add`, `collection-remove`

4. **Aliases**: Provide common aliases for frequently used commands
   - ✅ Short forms: `agent` → `agents`
   - ✅ Alternative names: `diagnose` → `doctor`

## Conclusion

The Claude MPM CLI is well-structured with a logical hierarchy, but has grown organically and could benefit from consolidation and consistency improvements. The proposed changes prioritize backward compatibility while improving the user experience.

**Next Steps**:
1. Implement Phase 1 changes (non-breaking)
2. Create comprehensive migration guide
3. Update documentation with new patterns
4. Plan Phase 2 deprecation timeline
5. Gather user feedback before Phase 3 breaking changes

**Estimated Impact**:
- Phase 1: Low risk, high value (aliases and flags)
- Phase 2: Medium risk, medium value (deprecation warnings)
- Phase 3: High risk, high value (breaking changes for v6.0.0)
