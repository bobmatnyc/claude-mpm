# Agent Deployment Architecture Research

**Date**: 2025-12-09
**Researcher**: Claude Research Agent
**Objective**: Analyze current agent deployment architecture to simplify from multi-location model to 2-location model (source + deployment)

---

## Executive Summary

The current claude-mpm agent deployment system has **3 distinct location types** that need to be simplified to **2 locations**:

1. **SOURCE (Keep)**: `~/.claude-mpm/cache/remote-agents/` - Git repository cache
2. **DEPLOYMENT TARGET (Keep)**: `.claude/agents/` - Claude Code agent discovery location
3. **INTERMEDIATE (Remove)**: `.claude-mpm/agents/` - Legacy intermediate location (currently empty, referenced in code)

**Key Finding**: The `.claude-mpm/agents/` directory is **referenced in 25+ files** but is currently **empty** in the project. It serves no functional purpose and should be removed from the codebase.

---

## Current Architecture Analysis

### 1. Agent Source Location (Git Repository Cache)

**Location**: `~/.claude-mpm/cache/remote-agents/`

**Purpose**:
- Git repository cache synced from GitHub
- Contains agent markdown definitions organized by category
- Managed by `GitSourceManager` and `SingleTierDeploymentService`

**Structure**:
```
~/.claude-mpm/cache/remote-agents/
├── .etag-cache.json                    # ETag-based sync optimization
├── BASE-AGENT.md                       # Build tool (not deployable)
├── bobmatnyc/
│   └── claude-mpm-agents/             # Official agent repository
│       ├── engineer/                   # Category: Engineering agents
│       ├── qa/                         # Category: QA agents
│       ├── ops/                        # Category: Operations agents
│       ├── security/                   # Category: Security agents
│       ├── documentation/              # Category: Documentation agents
│       ├── universal/                  # Category: Universal agents
│       └── claude-mpm/                 # Category: Framework agents
```

**Files Involved**:
- `src/claude_mpm/services/agents/single_tier_deployment_service.py` (Line 88: `cache_root`)
- `src/claude_mpm/services/agents/git_source_manager.py`
- `src/claude_mpm/services/agents/deployment/remote_agent_discovery_service.py`

**Verdict**: ✅ **KEEP** - This is the authoritative source for agents

---

### 2. Agent Deployment Target (Claude Code Discovery)

**Location**: `.claude/agents/` (project-level)

**Purpose**:
- **Primary deployment target** for all agents (system, user, project)
- Claude Code discovers agents from this directory
- Virtual deployment tracking via `.mpm_deployment_state`

**Structure**:
```
.claude/agents/
├── .mpm_deployment_state              # Virtual deployment state (JSON)
├── .dependency_cache                  # Dependency resolution cache
└── [agent-name].md                    # Deployed agent markdown files
```

**Deployment State Example**:
```json
{
  "deployment_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "last_check_time": 1765300540.577624,
  "last_check_results": {
    "agents": {},
    "summary": {
      "total_agents": 0
    }
  },
  "agent_count": 0
}
```

**Files Involved**:
- `src/claude_mpm/services/agents/single_tier_deployment_service.py` (Line 209-210: deployment)
- `src/claude_mpm/services/agents/deployment/agents_directory_resolver.py` (Line 122: default target)
- `src/claude_mpm/utils/agent_filters.py` (Line 126-127: virtual state detection)
- `src/claude_mpm/cli/commands/agent_state_manager.py` (Line 276: deployment check)

**Verdict**: ✅ **KEEP** - This is the standard deployment target

---

### 3. Intermediate Location (Legacy/Deprecated)

**Location**: `.claude-mpm/agents/` (project-level)

**Current Status**:
- **Empty directory** in claude-mpm framework project
- Referenced in **25+ Python files** across the codebase
- Described as "project new architecture" vs ".claude/agents/ legacy"
- **No actual agents deployed here** in current runtime

**Files Referencing This Location**:

#### Detection/Filtering (4 files):
1. `src/claude_mpm/utils/agent_filters.py`
   - Line 9: "Deployed agent detection supports both new (.claude-mpm/agents/) and legacy (.claude/agents/)"
   - Line 166-170: Checks `.claude-mpm/agents/` for deployed agents
   - Line 182: Comment listing as "project new architecture"

2. `src/claude_mpm/cli/commands/agent_state_manager.py`
   - Line 322-331: Checks `.claude-mpm/agents/` for physical agent files

#### Discovery/Loading (8 files):
3. `src/claude_mpm/core/framework/loaders/agent_loader.py`
   - Line 118: "Discover local JSON agent templates from .claude-mpm/agents/ directories"

4. `src/claude_mpm/core/framework/processors/template_processor.py`
   - Line 211-212: Search paths include `.claude-mpm/agents/`

5. `src/claude_mpm/core/unified_agent_registry.py`
   - Line 178: "Also check for local JSON templates in .claude-mpm/agents/"

6. `src/claude_mpm/core/claude_runner.py`
   - Line 304: ".claude-mpm/agents/ should only contain JSON source templates"
   - Line 316: Project agents directory path
   - Line 368-389: Deploy from `.claude-mpm/agents/` to `.claude/agents/`

7. `src/claude_mpm/core/optimized_agent_loader.py`
   - Line 473-474: Search paths

8. `src/claude_mpm/core/optimized_startup.py`
   - Line 370-371: Search paths

9. `src/claude_mpm/agents/agent_loader.py`
   - Line 106-107: "PROJECT: .claude-mpm/agents in the current working directory"

10. `src/claude_mpm/utils/agent_dependency_loader.py`
    - Line 142-143: Search paths for dependencies

#### CLI/Configuration (13+ files):
11. `src/claude_mpm/cli/parsers/agents_parser.py`
12. `src/claude_mpm/cli/interactive/agent_wizard.py`
13. `src/claude_mpm/cli/commands/agents.py`
14. `src/claude_mpm/cli/commands/agent_manager.py`
15. `src/claude_mpm/cli/commands/configure_template_editor.py`
16. `src/claude_mpm/init.py`

#### Services (8+ files):
17. `src/claude_mpm/services/framework_claude_md_generator/section_generators/agents.py`
18. `src/claude_mpm/services/memory/router.py`
19. `src/claude_mpm/services/agents/local_template_manager.py`
20. `src/claude_mpm/services/agents/deployment/pipeline/steps/agent_processing_step.py`
21. `src/claude_mpm/services/agents/deployment/deployment_type_detector.py`
22. `src/claude_mpm/services/agents/deployment/strategies/project_strategy.py`
23. `src/claude_mpm/services/agents/deployment/strategies/user_strategy.py`
24. `src/claude_mpm/services/agents/deployment/multi_source_deployment_service.py`
25. `src/claude_mpm/services/agents/deployment/single_agent_deployer.py`
26. `src/claude_mpm/services/agents/sources/git_source_sync_service.py`

**Verdict**: ❌ **REMOVE** - Unused intermediate location adding complexity

---

## Additional Locations to Verify

### 4. .claude/templates/ Directory

**Location**: `.claude/templates/` (mentioned in comments)

**Status**:
- Comment in `agent_filters.py` Line 179: ".claude/templates/ contains PM instruction templates, NOT deployed agents"
- Used by `SystemInstructionsDeployer` for PM framework templates
- **NOT used for agent deployment** (correctly excluded from agent detection)

**Files Involved**:
- `src/claude_mpm/services/agents/deployment/system_instructions_deployer.py` (Line 117-228: template deployment)
- Deploys to `.claude-mpm/templates/` (not `.claude/templates/`)

**Verdict**: ✅ **CORRECT** - Already excluded from agent deployment logic

---

### 5. ~/.claude/agents/ (User-Level Deployment)

**Location**: `~/.claude/agents/` (user home directory)

**Status**:
- Referenced in `agent_filters.py` Line 189-193
- User-level agent deployment location
- Checked as fallback after project-level `.claude/agents/`

**Purpose**:
- Global user agents available across all projects
- Less common use case (project-level is preferred)

**Verdict**: ⚠️ **CLARIFY** - Needs decision: Keep for user-level agents or remove?

---

## Deployment Flow Analysis

### Current Deployment Workflow

```
┌─────────────────────────────────────────────────────────────┐
│ PHASE 1: Sync from GitHub                                   │
│ ~/.claude-mpm/cache/remote-agents/ ← GitHub API (ETag sync) │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 2: Discovery                                           │
│ RemoteAgentDiscoveryService parses markdown files           │
│ Extracts metadata, categories, agent IDs                    │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 3: Deployment                                          │
│ SingleTierDeploymentService copies agents                   │
│ FROM: ~/.claude-mpm/cache/remote-agents/                    │
│ TO:   .claude/agents/ (project-level)                       │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 4: Claude Code Discovery                              │
│ Claude Code reads agents from .claude/agents/               │
│ Virtual deployment state tracked in .mpm_deployment_state   │
└─────────────────────────────────────────────────────────────┘
```

### Desired 2-Location Model

```
┌──────────────────────────────────────────────┐
│ SOURCE: ~/.claude-mpm/cache/remote-agents/   │
│ - Git repository cache                       │
│ - Synced from GitHub                         │
│ - Read-only (managed by git)                 │
└──────────────────────────────────────────────┘
                    ↓
        Direct deployment (no intermediate)
                    ↓
┌──────────────────────────────────────────────┐
│ DEPLOYMENT: .claude/agents/ (project)        │
│ - Claude Code discovery location             │
│ - Virtual deployment state                   │
│ - All agents deployed here                   │
└──────────────────────────────────────────────┘
```

---

## Code Changes Required

### 1. Remove `.claude-mpm/agents/` References

**Priority**: HIGH
**Impact**: Medium (25+ files affected)

**Files to Modify**:

#### A. Detection/Filtering (remove fallback checks):
- `src/claude_mpm/utils/agent_filters.py`
  - **Line 9**: Update docstring (remove mention of `.claude-mpm/agents/`)
  - **Line 166-170**: Remove check for `new_agents_dir = project_dir / ".claude-mpm" / "agents"`
  - **Line 182-183**: Update comments (remove reference to "project new architecture")

#### B. Discovery/Loading (remove from search paths):
- `src/claude_mpm/core/framework/loaders/agent_loader.py` (Line 118)
- `src/claude_mpm/core/framework/processors/template_processor.py` (Line 211-212)
- `src/claude_mpm/core/unified_agent_registry.py` (Line 178)
- `src/claude_mpm/core/optimized_agent_loader.py` (Line 473-474)
- `src/claude_mpm/core/optimized_startup.py` (Line 370-371)
- `src/claude_mpm/agents/agent_loader.py` (Line 106-107)
- `src/claude_mpm/utils/agent_dependency_loader.py` (Line 142-143)

#### C. CLI/Configuration:
- `src/claude_mpm/cli/commands/agent_state_manager.py` (Line 322-331)
- Review all CLI files for hardcoded paths

#### D. Services:
- Review all deployment strategy files
- Update documentation strings

**Migration Strategy**:
1. Search-and-replace `.claude-mpm/agents` → `.claude/agents` where appropriate
2. Remove checks for `.claude-mpm/agents/` from discovery logic
3. Update all docstrings and comments
4. Update error messages and logging

---

### 2. Clarify User-Level Deployment (~/.claude/agents/)

**Priority**: MEDIUM
**Decision Required**: Should user-level agents be supported?

**Option A: Keep User-Level Support**
- Pros: Global agents across projects
- Cons: Complexity, version conflicts, user confusion

**Option B: Remove User-Level Support**
- Pros: Simpler model (project-only), clearer boundaries
- Cons: Less flexibility for power users

**Recommendation**: **Remove user-level deployment** for simplicity. Users can:
- Deploy agents per-project (`.claude/agents/`)
- Share via Git repository sources (recommended)

**Files to Modify (if removing)**:
- `src/claude_mpm/utils/agent_filters.py` (Line 189-193)
- `src/claude_mpm/cli/commands/agent_state_manager.py` (Line 334-342)
- Remove `Path.home() / ".claude" / "agents"` checks

---

### 3. Update Documentation

**Priority**: HIGH
**Impact**: User-facing

**Files to Update**:
- `CLAUDE.md` (project instructions)
- `docs/developer/agent-modification-workflow.md`
- All deployment documentation
- Architecture diagrams

**Key Messages**:
- **Source**: `~/.claude-mpm/cache/remote-agents/` (Git cache)
- **Deployment**: `.claude/agents/` (project-level)
- **No intermediate locations**
- **User-level deployment removed** (if decided)

---

### 4. Update Tests

**Priority**: HIGH
**Impact**: CI/CD reliability

**Test Updates Required**:
- Remove tests checking `.claude-mpm/agents/`
- Update path assertions in unit tests
- Update integration tests for deployment flow
- Add tests verifying no intermediate directories used

**Test Files to Review**:
- All tests in `tests/` directory referencing `.claude-mpm/agents/`
- Deployment service tests
- Agent discovery tests

---

## Risk Assessment

### Low Risk Changes
✅ **Removing `.claude-mpm/agents/` references**: Directory is empty, no actual functionality broken

### Medium Risk Changes
⚠️ **User-level deployment removal**: May affect power users expecting global agents

### High Risk Changes
🔴 **Agent discovery path changes**: Critical path, must ensure Claude Code still finds agents

---

## Dependencies and Conflicts

### Key Dependencies
1. `SingleTierDeploymentService` → `.claude/agents/` (already correct)
2. `AgentsDirectoryResolver` → `.claude/agents/` (already correct)
3. Claude Code → `.claude/agents/` (external, don't control)

### Potential Conflicts
- Legacy projects with agents in `.claude-mpm/agents/` (migration needed)
- Documentation referring to old paths
- User expectations from previous versions

---

## Recommended Implementation Plan

### Phase 1: Code Cleanup (Low Risk)
1. ✅ Remove `.claude-mpm/agents/` from `agent_filters.py`
2. ✅ Remove from all discovery service search paths
3. ✅ Update docstrings and comments
4. ✅ Update error messages

### Phase 2: Simplification (Medium Risk)
1. ⚠️ Decide on user-level deployment (recommend remove)
2. ⚠️ Remove `~/.claude/agents/` checks if removing user-level
3. ⚠️ Update CLI commands to reflect new model

### Phase 3: Documentation (High Priority)
1. 📝 Update CLAUDE.md with 2-location model
2. 📝 Update developer documentation
3. 📝 Add migration guide for users
4. 📝 Update architecture diagrams

### Phase 4: Testing (Critical)
1. 🧪 Update unit tests
2. 🧪 Update integration tests
3. 🧪 Manual testing of deployment flow
4. 🧪 Verify Claude Code discovers agents

---

## Verification Checklist

Before marking complete, verify:

- [ ] No references to `.claude-mpm/agents/` in code (except migrations)
- [ ] All agent discovery uses `.claude/agents/` only
- [ ] `SingleTierDeploymentService` deploys to `.claude/agents/` (already correct)
- [ ] `agent_filters.py` checks only `.claude/agents/` and virtual state
- [ ] Documentation updated with 2-location model
- [ ] Tests pass with new architecture
- [ ] Claude Code still discovers agents correctly
- [ ] Migration guide exists for users with legacy directories

---

## Conclusion

The claude-mpm agent deployment architecture currently has an **unused intermediate location** (`.claude-mpm/agents/`) that adds complexity without providing value.

**Simplification Target**:
1. **SOURCE**: `~/.claude-mpm/cache/remote-agents/` (Git repository cache)
2. **DEPLOYMENT**: `.claude/agents/` (Claude Code discovery location)

**Action Required**: Remove all references to `.claude-mpm/agents/` across 25+ files, with careful testing to ensure Claude Code agent discovery continues to work correctly.

**Optional**: Decide whether to keep or remove user-level deployment (`~/.claude/agents/`). **Recommendation**: Remove for simplicity.

---

## Files Analyzed

**Total Files Reviewed**: 12
**Key Services**:
- `single_tier_deployment_service.py` (697 lines)
- `system_instructions_deployer.py` (229 lines)
- `agent_filters.py` (282 lines)
- `agent_state_manager.py` (345 lines)
- `agents_directory_resolver.py` (150 lines)

**Search Commands Used**:
- `grep -r "\.claude-mpm/agents"` (25 matches)
- `grep -r "\.claude/agents"` (50+ matches)
- `grep -r "\.claude/templates"` (verified separate use case)
- `grep -r "deployment_state"` (4 matches)

**Verification Commands**:
- `ls -la .claude-mpm/agents/` (empty directory)
- `ls -la .claude/agents/` (contains deployment state)
- `ls -la ~/.claude-mpm/cache/remote-agents/` (active Git cache)
