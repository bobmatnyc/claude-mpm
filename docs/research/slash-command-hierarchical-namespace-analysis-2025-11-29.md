# Slash Command Hierarchical Namespace Analysis

**Ticket**: 1M-400
**Date**: 2025-11-29
**Research Type**: Architecture Analysis & Migration Planning
**Status**: Complete

## Executive Summary

This research analyzes Claude MPM's current flat slash command structure and provides a comprehensive plan for migrating to a hierarchical namespace system (e.g., `/mpm/agents:list` instead of `/mpm-agents`).

**⚠️ CRITICAL FINDING**: Claude Code's documented hierarchical namespace feature (`/prefix:namespace:command`) is **non-functional** as of version 2.0.25+ (GitHub issue #2422). This significantly impacts the migration strategy and requires alternative approaches.

### Key Findings

1. **Current State**: 15 flat slash commands deployed from `src/claude_mpm/commands/` to `~/.claude/commands/`
2. **Installation Logic**: Simple flat-file copy via `CommandDeploymentService.deploy_commands()`
3. **Claude Code Limitation**: Subdirectory-based namespacing is broken; commands in subdirectories are not recognized
4. **Recommended Approach**: File-based namespacing (e.g., `mpm-agents-list.md`) rather than directory-based until Claude Code fixes the bug

### Migration Recommendation

**DEFER hierarchical directory structure** until Claude Code issue #2422 is resolved. Instead:
- Use enhanced file naming: `mpm-agents-list.md`, `mpm-config-view.md`
- Group related commands with shared prefixes
- Add metadata in frontmatter for future migration
- Monitor GitHub issue for resolution
- Prepare migration tooling for when feature becomes available

---

## 1. Current State Analysis

### 1.1 Slash Command Inventory

**Location**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/commands/`
**Deployment Target**: `~/.claude/commands/`
**Total Commands**: 15 markdown files

#### Complete Command List

| Command File | Command Name | Category | Description |
|--------------|--------------|----------|-------------|
| `mpm.md` | `/mpm` | Core | Main MPM entry point |
| `mpm-agents.md` | `/mpm-agents` | Agents | List available agents |
| `mpm-agents-detect.md` | `/mpm-agents-detect` | Agents | Detect project stack |
| `mpm-agents-recommend.md` | `/mpm-agents-recommend` | Agents | Recommend agents |
| `mpm-auto-configure.md` | `/mpm-auto-configure` | Config | Auto-configure agents |
| `mpm-config.md` | `/mpm-config` | Config | View/validate config |
| `mpm-doctor.md` | `/mpm-doctor` | System | Run diagnostics |
| `mpm-help.md` | `/mpm-help` | System | Show help |
| `mpm-init.md` | `/mpm-init` | System | Initialize project |
| `mpm-monitor.md` | `/mpm-monitor` | System | Launch monitoring |
| `mpm-organize.md` | `/mpm-organize` | Tickets | Organize tickets |
| `mpm-resume.md` | `/mpm-resume` | Session | Create resume file |
| `mpm-status.md` | `/mpm-status` | System | Show system status |
| `mpm-ticket.md` | `/mpm-ticket` | Tickets | Ticket workflows |
| `mpm-version.md` | `/mpm-version` | System | Show version info |

#### Command Categories (Logical Grouping)

```
/mpm/
├── agents/           # Agent management (4 commands)
│   ├── list          # mpm-agents.md
│   ├── detect        # mpm-agents-detect.md
│   ├── recommend     # mpm-agents-recommend.md
│   └── auto-config   # mpm-auto-configure.md
│
├── config/           # Configuration management (1 command)
│   └── view          # mpm-config.md
│
├── ticket/           # Ticketing workflows (2 commands)
│   ├── organize      # mpm-organize.md
│   └── workflows     # mpm-ticket.md
│
├── session/          # Session management (1 command)
│   └── resume        # mpm-resume.md
│
└── system/           # System commands (6 commands)
    ├── doctor        # mpm-doctor.md
    ├── help          # mpm-help.md
    ├── init          # mpm-init.md
    ├── monitor       # mpm-monitor.md
    ├── status        # mpm-status.md
    └── version       # mpm-version.md
```

### 1.2 Command Structure Analysis

**No YAML Frontmatter Found**: Currently, slash commands are plain markdown with no structured metadata. Only 2 files (`mpm-ticket.md`, `mpm-init.md`) contain YAML frontmatter markers (`---`), but these appear unused.

**Current Structure Pattern**:
```markdown
# <Command Title>

<Brief description>

## Usage
...

## Description
...

## Implementation
...
```

### 1.3 Installation Logic Analysis

**Service**: `CommandDeploymentService` (`src/claude_mpm/services/command_deployment_service.py`)

**Key Methods**:
1. `deploy_commands(force: bool)` - Main deployment method
2. `list_available_commands()` - List source commands
3. `list_deployed_commands()` - List deployed commands
4. `remove_deployed_commands()` - Uninstall commands

**Current Installation Algorithm**:

```python
# Simplified pseudocode
def deploy_commands(force):
    source_dir = "src/claude_mpm/commands/"
    target_dir = "~/.claude/commands/"

    # Get all .md files from source
    command_files = source_dir.glob("*.md")

    for source_file in command_files:
        target_file = target_dir / source_file.name

        # Skip if target exists and is newer (unless force)
        if target_file.exists() and not force:
            if source_file.mtime <= target_file.mtime:
                continue

        # Copy file preserving metadata
        shutil.copy2(source_file, target_file)
```

**Key Characteristics**:
- ✅ Simple flat-file copy operation
- ✅ Timestamp-based update detection
- ✅ Creates target directory if missing
- ✅ Force flag for overwriting
- ❌ No support for subdirectories (only `*.md` in root)
- ❌ No namespace processing
- ❌ No frontmatter parsing

---

## 2. Claude Code Hierarchical Commands Research

### 2.1 Official Documentation

**Source**: [Claude Code Docs - Slash Commands](https://docs.claude.com/en/docs/claude-code/slash-commands)

**Documented Behavior**:
- Commands support namespacing through subdirectories
- Format: `<prefix>:<namespace>:<command>`
- Example: `.claude/commands/frontend/component.md` → `/project:frontend:component`

**Command Locations**:
1. **Project commands**: `.claude/commands/` (prefix: `/project:`)
2. **Personal commands**: `~/.claude/commands/` (prefix: `/user:`)

**Precedence Hierarchy**:
1. Project subfolders: `./<subfolder>/.claude/commands/` (highest)
2. Project root: `./.claude/commands/`
3. Home directory: `~/.claude/commands/` (lowest)

### 2.2 Reality: GitHub Issue #2422

**Issue**: [Slash command namespacing with subdirectories not working as documented](https://github.com/anthropics/claude-code/issues/2422)

**Status**:
- Reported: June 21, 2025
- Still open as of November 29, 2025
- Affects: Claude Code 1.0.31 → 2.0.25+
- Labels: `bug`, `has-repro`, `area:core`, `platform:macos`

**Problem Summary**:
- Commands in subdirectories **are NOT recognized** by Claude Code
- They don't appear in autocomplete
- Invoking via documented syntax (`/user:namespace:command`) fails with "command not found"
- Only flat commands in root directories work

**Reproduction**:
```bash
# This DOES NOT WORK despite documentation
mkdir -p ~/.claude/commands/test-namespace/
echo "# Test Command" > ~/.claude/commands/test-namespace/test.md

# Expected (per docs): /user:test-namespace:test
# Actual: Command not found
```

**Community Workarounds**:
- Use flat naming with prefixes: `namespace-command.md`
- Avoid subdirectories entirely
- Use symlinks for monorepo structures (see Daniel Corin's article)

### 2.3 Alternative Approach: Daniel Corin's Hierarchy Pattern

**Source**: [Thought Eddies - Custom Slash Commands Hierarchy](https://www.danielcorin.com/til/anthropic/custom-slash-commands-hierarchy/)

**Working Pattern** (without subdirectory namespaces):
- Symlinks to maintain shared command sets
- Manual namespace prefixes in filenames
- Precedence-based overrides using directory hierarchy

**Monorepo Symlink Pattern**:
```bash
# Link parent commands into subfolder
cd subfolder/
ln -sf "$(realpath ../.claude)" .claude

# Organize home commands without conflicts
mkdir -p .claude/commands/home
ln -sf ~/.claude/commands/* .claude/commands/home/
```

---

## 3. Proposed Hierarchical Structure

### 3.1 DEFERRED: Directory-Based Hierarchy (Blocked by Bug)

**⚠️ NOT RECOMMENDED UNTIL ISSUE #2422 IS RESOLVED**

```
src/claude_mpm/commands/
└── mpm/
    ├── mpm.md                    # /mpm (root command)
    │
    ├── agents/
    │   ├── list.md               # /mpm/agents:list
    │   ├── detect.md             # /mpm/agents:detect
    │   ├── recommend.md          # /mpm/agents:recommend
    │   └── auto-configure.md     # /mpm/agents:auto-configure
    │
    ├── config/
    │   ├── view.md               # /mpm/config:view
    │   ├── validate.md           # /mpm/config:validate
    │   └── status.md             # /mpm/config:status
    │
    ├── ticket/
    │   ├── organize.md           # /mpm/ticket:organize
    │   └── workflows.md          # /mpm/ticket:workflows
    │
    ├── session/
    │   └── resume.md             # /mpm/session:resume
    │
    └── system/
        ├── doctor.md             # /mpm/system:doctor
        ├── help.md               # /mpm/system:help
        ├── init.md               # /mpm/system:init
        ├── monitor.md            # /mpm/system:monitor
        ├── status.md             # /mpm/system:status
        └── version.md            # /mpm/system:version
```

**Why Deferred**:
- Claude Code cannot recognize commands in subdirectories
- No autocomplete support for namespaced commands
- Runtime invocation fails even with correct syntax
- Would result in **broken user experience**

### 3.2 RECOMMENDED: Enhanced Flat Naming (Migration-Ready)

**Immediate Implementation** (works with current Claude Code):

```
src/claude_mpm/commands/
├── mpm.md                        # /mpm
├── mpm-agents-list.md            # /mpm-agents-list
├── mpm-agents-detect.md          # /mpm-agents-detect (unchanged)
├── mpm-agents-recommend.md       # /mpm-agents-recommend (unchanged)
├── mpm-agents-auto-configure.md  # /mpm-agents-auto-configure
├── mpm-config-view.md            # /mpm-config-view
├── mpm-config-validate.md        # /mpm-config-validate (new split)
├── mpm-config-status.md          # /mpm-config-status (new split)
├── mpm-doctor.md                 # /mpm-doctor (unchanged)
├── mpm-help.md                   # /mpm-help (unchanged)
├── mpm-init.md                   # /mpm-init (unchanged)
├── mpm-monitor.md                # /mpm-monitor (unchanged)
├── mpm-organize.md               # /mpm-organize (unchanged)
├── mpm-resume.md                 # /mpm-resume (unchanged)
├── mpm-status.md                 # /mpm-status (unchanged)
├── mpm-ticket-organize.md        # /mpm-ticket-organize
├── mpm-ticket-workflows.md       # /mpm-ticket-workflows
└── mpm-version.md                # /mpm-version (unchanged)
```

**Benefits**:
- ✅ Works with current Claude Code (no bug dependency)
- ✅ Maintains clear namespace grouping via prefixes
- ✅ Searchable and autocomplete-friendly
- ✅ Easy to migrate to directories when bug is fixed
- ✅ Backward compatible (can keep old names as aliases)

### 3.3 Future Migration: YAML Frontmatter for Namespace Metadata

**Prepare for future directory-based migration** by adding frontmatter:

```yaml
---
namespace: mpm/agents
command: list
aliases:
  - mpm-agents
  - mpm-agents-list
category: agents
deprecated_names:
  - mpm-agents  # Remove in v5.0.0
migration_target: /mpm/agents:list
---
# List Available Agents

...
```

**Frontmatter Schema**:
```yaml
---
namespace: string           # Logical namespace (e.g., "mpm/agents")
command: string             # Command name within namespace (e.g., "list")
aliases: string[]           # Alternative invocation names
category: string            # Grouping category
deprecated_names: string[]  # Old names to phase out
migration_target: string    # Future hierarchical command path
depends_on: string[]        # Dependencies (agents, skills, MCP servers)
version: string             # Command schema version
---
```

---

## 4. Installation Logic Changes

### 4.1 Current Implementation Issues

**Problem**: `CommandDeploymentService.deploy_commands()` only handles flat files:

```python
# Line 74: Only finds files in root directory
command_files = list(self.source_dir.glob("*.md"))
```

**Limitations**:
1. No recursive directory traversal
2. No namespace path preservation
3. No subdirectory creation in target
4. No frontmatter parsing for metadata

### 4.2 Required Changes for Hierarchical Structure (DEFERRED)

**⚠️ NOT IMPLEMENTED until issue #2422 is resolved**

**Modified Algorithm**:
```python
def deploy_commands(self, force: bool = False) -> Dict[str, Any]:
    """Deploy commands preserving directory hierarchy."""

    # Use recursive glob to find all .md files
    command_files = list(self.source_dir.rglob("*.md"))

    for source_file in command_files:
        # Calculate relative path to preserve hierarchy
        relative_path = source_file.relative_to(self.source_dir)
        target_file = self.target_dir / relative_path

        # Create parent directories in target
        target_file.parent.mkdir(parents=True, exist_ok=True)

        # Copy with timestamp check
        if self._should_deploy(source_file, target_file, force):
            shutil.copy2(source_file, target_file)
            result["deployed"].append(str(relative_path))
```

**Key Changes**:
1. `glob("*.md")` → `rglob("*.md")` (recursive search)
2. Preserve relative path structure in target
3. Create subdirectories in `~/.claude/commands/` as needed
4. Track relative paths in deployment results

### 4.3 Backward Compatibility Layer

**Dual Deployment Strategy** (when hierarchy is implemented):

```python
def deploy_with_backward_compatibility(self):
    """Deploy both hierarchical and flat aliases during migration period."""

    for source_file in self.source_dir.rglob("*.md"):
        relative_path = source_file.relative_to(self.source_dir)

        # Deploy to hierarchical location
        hierarchical_target = self.target_dir / relative_path
        self._deploy_file(source_file, hierarchical_target)

        # Parse frontmatter for backward compatibility
        frontmatter = self._parse_frontmatter(source_file)
        if "deprecated_names" in frontmatter:
            # Create symlinks for old command names
            for old_name in frontmatter["deprecated_names"]:
                alias_target = self.target_dir / f"{old_name}.md"
                self._create_alias(hierarchical_target, alias_target)
```

**Alias Creation Options**:
1. **Symlinks** (Unix/macOS): `ln -s mpm/agents/list.md mpm-agents.md`
2. **File copies** (Windows-compatible): Duplicate with deprecation notice
3. **Redirect stubs**: Minimal file that tells user to use new command

---

## 5. Migration Strategy

### 5.1 Phase 1: Enhanced Flat Naming (IMMEDIATE)

**Goal**: Improve command organization without relying on broken Claude Code features.

**Steps**:
1. **Rename commands** to use enhanced prefixes:
   - `mpm-agents.md` → `mpm-agents-list.md`
   - Split `mpm-config.md` → `mpm-config-view.md`, `mpm-config-validate.md`, `mpm-config-status.md`
   - Split `mpm-ticket.md` → `mpm-ticket-organize.md`, `mpm-ticket-workflows.md`

2. **Add YAML frontmatter** to all commands:
   ```yaml
   ---
   namespace: mpm/agents
   command: list
   category: agents
   aliases: [mpm-agents]
   migration_target: /mpm/agents:list
   ---
   ```

3. **Keep old files as deprecated aliases**:
   - `mpm-agents.md` becomes a stub pointing to `mpm-agents-list.md`
   - Add deprecation warnings in command content

4. **Update documentation**:
   - README with new command names
   - Migration guide for users
   - Changelog entry explaining enhanced naming

**Timeline**: Can be implemented immediately in v4.27.0+

**Risk**: Low (no dependency on broken features)

### 5.2 Phase 2: Monitor Claude Code Issue (ONGOING)

**Goal**: Track resolution of GitHub issue #2422.

**Actions**:
1. **Subscribe to issue notifications**: Add team members to watch list
2. **Test with each Claude Code release**: Automated test suite for namespace functionality
3. **Maintain migration tooling**: Keep directory-based structure ready to deploy

**Test Script**:
```bash
#!/bin/bash
# test-hierarchical-commands.sh

mkdir -p ~/.claude/commands/test-hierarchy/agents
echo "# Test Agent Command" > ~/.claude/commands/test-hierarchy/agents/test.md

# Test invocation (will fail until bug is fixed)
claude-code "Run /user:test-hierarchy:agents:test"

if [ $? -eq 0 ]; then
    echo "✅ Hierarchical namespaces are working! Issue #2422 is resolved."
    exit 0
else
    echo "❌ Hierarchical namespaces still broken. Continue monitoring."
    exit 1
fi
```

**Trigger Points**:
- Claude Code minor version releases (e.g., 2.1.0, 2.2.0)
- GitHub issue status changes
- Community reports of fix

### 5.3 Phase 3: Full Hierarchical Migration (FUTURE)

**Goal**: Implement directory-based structure once Claude Code supports it.

**Prerequisites**:
- ✅ Issue #2422 is resolved and verified
- ✅ Claude Code version with fix is widely adopted (95%+ of users)
- ✅ Migration tooling is tested and ready

**Steps**:
1. **Create hierarchical directory structure**:
   ```bash
   src/claude_mpm/commands/
   └── mpm/
       ├── agents/
       ├── config/
       ├── ticket/
       ├── session/
       └── system/
   ```

2. **Move command files** to subdirectories:
   - `mpm-agents-list.md` → `mpm/agents/list.md`
   - Update frontmatter with new paths
   - Keep migration metadata

3. **Update `CommandDeploymentService`**:
   - Implement recursive deployment (section 4.2)
   - Add backward compatibility layer (section 4.3)
   - Preserve symlinks/aliases during migration

4. **Deploy with dual support**:
   - Hierarchical commands: `/mpm/agents:list`
   - Flat aliases: `/mpm-agents-list` (deprecated)
   - Legacy aliases: `/mpm-agents` (deprecated)

5. **User communication**:
   - Release notes explaining migration
   - Update command in all documentation
   - Deprecation timeline (keep aliases for 2 major versions)

6. **Gradual alias removal**:
   - v5.0.0: Add deprecation warnings to flat commands
   - v5.1.0: Remove legacy single-dash aliases (`/mpm-agents`)
   - v6.0.0: Remove enhanced flat aliases (`/mpm-agents-list`)

**Timeline**: Estimated 6-12 months after issue resolution

---

## 6. Backward Compatibility Plan

### 6.1 Alias Strategy

**Three-Tier Alias System**:

1. **Legacy aliases** (current names):
   - `/mpm-agents` → Stub file with deprecation warning
   - Removed in v5.1.0 (6 months after Phase 1)

2. **Enhanced flat aliases** (Phase 1 names):
   - `/mpm-agents-list` → Symlink to `mpm/agents/list.md`
   - Removed in v6.0.0 (12 months after Phase 3)

3. **Hierarchical commands** (target names):
   - `/mpm/agents:list` → Primary invocation method
   - Permanent (no deprecation)

**Deprecation Warning Template**:
```markdown
# ⚠️ DEPRECATED: Use `/mpm-agents-list` instead

This command has been renamed for better organization.

**Old Command**: `/mpm-agents`
**New Command**: `/mpm-agents-list`
**Future Command**: `/mpm/agents:list` (when Claude Code supports hierarchical namespaces)

This alias will be removed in Claude MPM v5.1.0 (scheduled for June 2026).

---

<original command content>
```

### 6.2 Migration Guide for Users

**Auto-Migration Script** (included in Claude MPM):

```bash
#!/bin/bash
# migrate-commands.sh

echo "Migrating Claude MPM commands to enhanced naming..."

# Backup existing commands
cp -r ~/.claude/commands/mpm* ~/.claude/commands/backup-$(date +%Y%m%d)/

# Deploy new commands
claude-mpm commands deploy --force

# Report migration status
echo "✅ Migration complete!"
echo ""
echo "Command changes:"
echo "  /mpm-agents        → /mpm-agents-list"
echo "  /mpm-config        → /mpm-config-view"
echo "  /mpm-ticket        → /mpm-ticket-organize"
echo ""
echo "Old commands are still available but will show deprecation warnings."
echo "They will be removed in v5.1.0 (June 2026)."
```

**User Documentation**:

```markdown
## Migrating to Enhanced Command Names

Claude MPM v4.27.0 introduces enhanced command naming for better organization:

### What Changed

| Old Command | New Command | Notes |
|-------------|-------------|-------|
| `/mpm-agents` | `/mpm-agents-list` | More explicit |
| `/mpm-config` | `/mpm-config-view` | Separated by function |
| `/mpm-ticket` | `/mpm-ticket-organize` | Workflow-specific |

### Migration Steps

1. **Automatic** (recommended):
   ```bash
   claude-mpm commands deploy --force
   ```

2. **Manual** (if needed):
   - Delete old commands: `rm ~/.claude/commands/mpm-*.md`
   - Redeploy: `claude-mpm commands deploy`

### Backward Compatibility

- Old command names continue to work with deprecation warnings
- Aliases will be removed in v5.1.0 (June 2026)
- Update your documentation and scripts to use new names

### Future: Hierarchical Namespaces

When Claude Code adds support for hierarchical namespaces (GitHub issue #2422), commands will migrate to:

- `/mpm/agents:list` (instead of `/mpm-agents-list`)
- `/mpm/config:view` (instead of `/mpm-config-view`)
- `/mpm/ticket:organize` (instead of `/mpm-ticket-organize`)

Claude MPM will handle this transition automatically with backward-compatible aliases.
```

---

## 7. Testing Strategy

### 7.1 Unit Tests for CommandDeploymentService

**Test Coverage Areas**:

1. **Flat deployment** (current functionality):
   ```python
   def test_deploy_flat_commands():
       """Verify flat command deployment works as expected."""
       service = CommandDeploymentService()
       result = service.deploy_commands()
       assert result["success"] == True
       assert len(result["deployed"]) == 15
   ```

2. **Hierarchical deployment** (future functionality):
   ```python
   def test_deploy_hierarchical_commands():
       """Verify hierarchical structure is preserved."""
       service = CommandDeploymentService()
       result = service.deploy_commands()

       # Check subdirectories were created
       assert (service.target_dir / "mpm" / "agents").exists()
       assert (service.target_dir / "mpm" / "config").exists()

       # Check files are in correct locations
       assert (service.target_dir / "mpm" / "agents" / "list.md").exists()
   ```

3. **Backward compatibility**:
   ```python
   def test_backward_compatible_aliases():
       """Verify legacy aliases are created during migration."""
       service = CommandDeploymentService()
       service.deploy_with_backward_compatibility()

       # Check hierarchical command exists
       assert (service.target_dir / "mpm" / "agents" / "list.md").exists()

       # Check legacy alias exists
       assert (service.target_dir / "mpm-agents-list.md").exists()
   ```

4. **Frontmatter parsing**:
   ```python
   def test_frontmatter_parsing():
       """Verify YAML frontmatter is correctly parsed."""
       service = CommandDeploymentService()
       metadata = service._parse_frontmatter(Path("mpm-agents-list.md"))

       assert metadata["namespace"] == "mpm/agents"
       assert metadata["command"] == "list"
       assert "mpm-agents" in metadata["aliases"]
   ```

### 7.2 Integration Tests

**Test Suite**: `tests/integration/test_command_deployment.py`

```python
def test_end_to_end_command_deployment(tmp_path):
    """Test complete command deployment workflow."""
    # Setup temporary source and target directories
    source_dir = tmp_path / "source" / "commands"
    target_dir = tmp_path / "target" / "commands"
    source_dir.mkdir(parents=True)
    target_dir.mkdir(parents=True)

    # Create test command with frontmatter
    command_content = """---
namespace: mpm/agents
command: list
aliases: [mpm-agents]
---
# List Agents
Test command content
"""
    (source_dir / "mpm-agents-list.md").write_text(command_content)

    # Deploy commands
    service = CommandDeploymentService()
    service.source_dir = source_dir
    service.target_dir = target_dir
    result = service.deploy_commands()

    # Verify deployment
    assert result["success"]
    assert (target_dir / "mpm-agents-list.md").exists()

    # Verify content preserved
    deployed_content = (target_dir / "mpm-agents-list.md").read_text()
    assert "namespace: mpm/agents" in deployed_content

def test_hierarchical_namespace_verification():
    """Test that hierarchical commands work in Claude Code (when supported)."""
    # This test will FAIL until issue #2422 is resolved
    # Keep it as a canary to detect when the feature is fixed

    result = subprocess.run(
        ["claude-code", "test", "/project:mpm:agents:list"],
        capture_output=True,
        text=True
    )

    # Expected to fail until bug is fixed
    if result.returncode == 0:
        print("✅ Hierarchical namespaces are working! Update migration plan.")
    else:
        print("❌ Hierarchical namespaces still broken (expected).")
```

### 7.3 Manual Testing Checklist

**Phase 1 Testing** (Enhanced Flat Naming):

- [ ] Deploy commands: `claude-mpm commands deploy --force`
- [ ] Verify all 15+ commands are deployed to `~/.claude/commands/`
- [ ] Test command invocation:
  - [ ] `/mpm-agents-list` works
  - [ ] `/mpm-config-view` works
  - [ ] `/mpm-ticket-organize` works
- [ ] Verify autocomplete shows new command names
- [ ] Test legacy aliases show deprecation warnings
- [ ] Check help text is correct in all commands

**Phase 3 Testing** (Hierarchical Migration - FUTURE):

- [ ] Verify Claude Code version supports hierarchical namespaces
- [ ] Deploy commands: `claude-mpm commands deploy --hierarchical`
- [ ] Check subdirectories created in `~/.claude/commands/mpm/`
- [ ] Test hierarchical invocation:
  - [ ] `/mpm/agents:list` works
  - [ ] `/mpm/config:view` works
  - [ ] `/mpm/ticket:organize` works
- [ ] Verify backward compatibility:
  - [ ] `/mpm-agents-list` still works (alias)
  - [ ] `/mpm-agents` shows deprecation warning
- [ ] Check autocomplete shows both hierarchical and flat commands
- [ ] Test precedence: hierarchical commands override flat aliases

---

## 8. Risks and Considerations

### 8.1 High-Priority Risks

1. **Claude Code Bug Dependency** ⚠️ **CRITICAL**
   - **Risk**: Issue #2422 may take months or years to fix
   - **Impact**: Cannot implement directory-based hierarchy until resolved
   - **Mitigation**: Use enhanced flat naming (Phase 1) as interim solution
   - **Contingency**: Maintain flat structure indefinitely if bug is never fixed

2. **User Confusion During Migration**
   - **Risk**: Multiple command names for same functionality
   - **Impact**: Users unsure which command to use
   - **Mitigation**: Clear deprecation warnings, migration guide, auto-update script
   - **Contingency**: Extend alias support period if adoption is slow

3. **Breaking Changes for Power Users**
   - **Risk**: Scripts and automation rely on old command names
   - **Impact**: User workflows break after upgrade
   - **Mitigation**: Long deprecation period (2 major versions), backward compatibility layer
   - **Contingency**: Provide rollback instructions to previous version

### 8.2 Medium-Priority Risks

4. **Installation Complexity Increase**
   - **Risk**: Hierarchical deployment logic is more complex
   - **Impact**: More edge cases, potential bugs in deployment
   - **Mitigation**: Comprehensive test suite, gradual rollout
   - **Contingency**: Revert to flat deployment if critical bugs found

5. **Documentation Fragmentation**
   - **Risk**: Docs reference mix of old and new command names
   - **Impact**: User confusion, support burden
   - **Mitigation**: Automated doc updates, search-and-replace tooling
   - **Contingency**: Maintain separate doc versions for different Claude MPM versions

6. **Symlink Support on Windows**
   - **Risk**: Windows requires admin privileges for symlinks
   - **Impact**: Backward compatibility aliases may not work on Windows
   - **Mitigation**: Use file copies instead of symlinks on Windows
   - **Contingency**: Provide PowerShell scripts for manual alias creation

### 8.3 Low-Priority Risks

7. **Command Name Collisions**
   - **Risk**: New naming scheme conflicts with user's custom commands
   - **Impact**: User commands shadowed by MPM commands
   - **Mitigation**: Use unique `mpm-` prefix, document namespace reservation
   - **Contingency**: Provide command priority override mechanism

8. **Frontmatter Parsing Errors**
   - **Risk**: Invalid YAML causes deployment failures
   - **Impact**: Commands fail to deploy or work incorrectly
   - **Mitigation**: Schema validation, graceful error handling
   - **Contingency**: Fall back to filename-based metadata if frontmatter is invalid

---

## 9. Recommended Action Plan

### Immediate Actions (Week 1)

1. **Create GitHub issue** for Phase 1 migration:
   - Title: "Implement enhanced flat command naming"
   - Reference this research document
   - Link to upstream issue #2422

2. **Update `CommandDeploymentService`**:
   - Add frontmatter parsing capability
   - Add unit tests for new functionality
   - No functional changes yet (backward compatible)

3. **Design command naming convention**:
   - Finalize naming for split commands (`mpm-config-view`, `mpm-config-validate`)
   - Document namespace → flat name mapping rules
   - Get team approval on naming scheme

### Short-Term Actions (Sprint 1-2)

4. **Implement Phase 1: Enhanced Flat Naming**:
   - Rename existing commands to enhanced names
   - Add YAML frontmatter to all commands
   - Create deprecated aliases with warnings
   - Update all documentation and examples

5. **Write migration guide**:
   - User-facing migration documentation
   - Auto-migration script
   - Changelog entry explaining changes

6. **Test migration path**:
   - Test on local development environment
   - Test on fresh installation
   - Test upgrade from v4.26.x to v4.27.0

### Medium-Term Actions (Sprint 3-6)

7. **Monitor Claude Code issue #2422**:
   - Set up GitHub notifications
   - Add automated test for namespace functionality
   - Test with each new Claude Code release

8. **Prepare Phase 3 tooling** (in advance):
   - Implement hierarchical deployment logic (behind feature flag)
   - Create directory structure migration script
   - Write integration tests for hierarchical commands

9. **Gather user feedback**:
   - Survey users about command naming preferences
   - Collect reports of migration issues
   - Adjust deprecation timeline if needed

### Long-Term Actions (6+ months)

10. **Execute Phase 3 migration** (when issue #2422 is resolved):
    - Enable hierarchical deployment feature flag
    - Deploy with backward compatibility layer
    - Announce migration with clear timeline

11. **Gradual alias deprecation**:
    - v5.0.0: Add warnings to flat aliases
    - v5.1.0: Remove legacy aliases (`/mpm-agents`)
    - v6.0.0: Remove enhanced flat aliases (`/mpm-agents-list`)

12. **Post-migration cleanup**:
    - Remove deprecated code paths
    - Simplify deployment logic
    - Archive migration documentation

---

## 10. Appendix

### A. Command Mapping Table (Flat → Hierarchical)

| Current Flat | Phase 1 Enhanced | Phase 3 Hierarchical | Category |
|--------------|------------------|----------------------|----------|
| `/mpm` | `/mpm` | `/mpm` | Core |
| `/mpm-agents` | `/mpm-agents-list` | `/mpm/agents:list` | Agents |
| `/mpm-agents-detect` | (unchanged) | `/mpm/agents:detect` | Agents |
| `/mpm-agents-recommend` | (unchanged) | `/mpm/agents:recommend` | Agents |
| `/mpm-auto-configure` | `/mpm-agents-auto-configure` | `/mpm/agents:auto-configure` | Agents |
| `/mpm-config` | `/mpm-config-view` | `/mpm/config:view` | Config |
| (new) | `/mpm-config-validate` | `/mpm/config:validate` | Config |
| (new) | `/mpm-config-status` | `/mpm/config:status` | Config |
| `/mpm-doctor` | (unchanged) | `/mpm/system:doctor` | System |
| `/mpm-help` | (unchanged) | `/mpm/system:help` | System |
| `/mpm-init` | (unchanged) | `/mpm/system:init` | System |
| `/mpm-monitor` | (unchanged) | `/mpm/system:monitor` | System |
| `/mpm-organize` | `/mpm-ticket-organize` | `/mpm/ticket:organize` | Tickets |
| `/mpm-resume` | `/mpm-session-resume` | `/mpm/session:resume` | Session |
| `/mpm-status` | (unchanged) | `/mpm/system:status` | System |
| `/mpm-ticket` | `/mpm-ticket-workflows` | `/mpm/ticket:workflows` | Tickets |
| `/mpm-version` | (unchanged) | `/mpm/system:version` | System |

### B. YAML Frontmatter Schema

```yaml
# Complete frontmatter schema for slash commands
---
# Required fields
namespace: string              # Logical namespace (e.g., "mpm/agents")
command: string                # Command name within namespace (e.g., "list")
category: string               # Category for organization (agents|config|ticket|session|system)

# Optional fields
aliases: string[]              # Alternative command names
deprecated_names: string[]     # Old names being phased out
migration_target: string       # Future command path (e.g., "/mpm/agents:list")
version: string                # Command schema version (default: "1.0")
depends_on:                    # Dependencies
  agents: string[]             # Required agents
  skills: string[]             # Required skills
  mcp_servers: string[]        # Required MCP servers
  tools: string[]              # Required tools
min_mpm_version: string        # Minimum Claude MPM version required
max_mpm_version: string        # Maximum compatible version (for deprecation)
description: string            # Brief description (alternative to markdown H1)
tags: string[]                 # Searchable tags
author: string                 # Command author
license: string                # License (if custom command)
---
```

### C. Files Requiring Modification

**Source Files to Update**:

1. `src/claude_mpm/services/command_deployment_service.py`
   - Add `_parse_frontmatter()` method
   - Add `deploy_with_backward_compatibility()` method
   - Modify `deploy_commands()` to support hierarchical paths (future)
   - Add `_create_alias()` helper method

2. `src/claude_mpm/commands/*.md` (all 15 files)
   - Add YAML frontmatter to each command
   - Update documentation sections as needed
   - Rename files for Phase 1 enhanced naming

3. `src/claude_mpm/cli/commands/local_deploy.py`
   - Update command deployment invocation
   - Add migration status reporting
   - Handle deprecation warnings

4. `tests/services/test_command_deployment_service.py`
   - Add tests for frontmatter parsing
   - Add tests for hierarchical deployment (future)
   - Add tests for backward compatibility

5. `docs/README.md` and related documentation
   - Update command reference tables
   - Add migration guide
   - Update examples to use new command names

**New Files to Create**:

1. `docs/research/slash-command-hierarchical-namespace-analysis-2025-11-29.md` ← This document
2. `docs/guides/slash-command-migration-guide.md` - User-facing migration documentation
3. `scripts/migrate-commands.sh` - Auto-migration script
4. `scripts/test-hierarchical-namespaces.sh` - Test script for issue #2422
5. `tests/integration/test_command_hierarchy.py` - Integration tests

### D. References

1. **Claude Code Official Documentation**
   - [Slash Commands](https://docs.claude.com/en/docs/claude-code/slash-commands)

2. **GitHub Issues**
   - [Issue #2422: Slash command namespacing not working](https://github.com/anthropics/claude-code/issues/2422)

3. **Community Articles**
   - [Daniel Corin: Custom Slash Commands Hierarchy](https://www.danielcorin.com/til/anthropic/custom-slash-commands-hierarchy/)
   - [AI Engineer Guide: Custom Commands](https://aiengineerguide.com/blog/claude-code-custom-command/)

4. **Claude MPM Source Code**
   - `src/claude_mpm/services/command_deployment_service.py`
   - `src/claude_mpm/commands/` directory

---

## Conclusion

This research provides a comprehensive analysis of Claude MPM's slash command structure and a pragmatic migration strategy that accounts for the current limitations of Claude Code's hierarchical namespace feature.

**Key Takeaways**:

1. **Immediate Action**: Implement Phase 1 (enhanced flat naming) to improve organization without dependency on broken Claude Code features.

2. **Monitor Upstream**: Track GitHub issue #2422 for resolution, test with each Claude Code release.

3. **Prepare for Future**: Design hierarchical structure and migration tooling now, deploy when feature becomes available.

4. **User Experience First**: Maintain backward compatibility throughout migration, provide clear deprecation timeline.

The recommended approach balances immediate improvements with long-term architectural goals, ensuring Claude MPM delivers value to users today while positioning for a cleaner hierarchical structure in the future.

**Next Steps**: Create implementation ticket, get team approval on Phase 1 naming scheme, begin development in next sprint.

---

**Research Completed**: 2025-11-29
**Ticket**: 1M-400
**Status**: Ready for implementation
**Attachments**: To be linked to ticket via ticketing agent
