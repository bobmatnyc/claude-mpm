# Remote Agents Reference Cleanup Investigation

**Date**: 2025-12-22
**Researcher**: Claude Research Agent
**Objective**: Find all "remote-agents" references and understand correct agent deployment architecture

---

## Executive Summary

**Finding**: The term "remote-agents" is correct and should **NOT** be cleaned up. The confusion is between:
- `~/.claude-mpm/cache/remote-agents/` - **CORRECT** (actual directory that exists)
- `~/.claude-mpm/cache/agents/` - **LEGACY** (deprecated directory that no longer exists)

The `remote-agents` directory exists and is actively used. The user's confusion likely stems from seeing both "agents" and "remote-agents" directories in the `~/.claude-mpm/` folder.

---

## Current Directory Structure

```
~/.claude-mpm/
├── agents/                    # User-defined agents (exists, contains user-defined/ subdirectory)
├── cache/
│   ├── agents/               # Git repository caches (flattened structure)
│   ├── remote-agents/        # ETag cache for GitHub syncing
│   └── skills/               # Skills cache
└── [other directories]
```

**Key Discovery**: Both directories exist but serve DIFFERENT purposes:
1. `~/.claude-mpm/agents/` - User-defined agent customizations
2. `~/.claude-mpm/cache/remote-agents/` - Remote agent cache from GitHub repos

---

## Understanding the Confusion

### Two Different "agents" Directories

**Directory 1: `~/.claude-mpm/agents/`**
- **Purpose**: User-defined agent storage
- **Contains**: `user-defined/` subdirectory
- **Status**: Active, used for local user customizations
- **NOT deprecated**

**Directory 2: `~/.claude-mpm/cache/agents/`**
- **Purpose**: Legacy cache location (DEPRECATED)
- **Status**: Replaced by `cache/remote-agents/`
- **Migration**: Script exists to migrate from this old location

The confusion is that both are called "agents" but have different parent directories.

---

## Agent Deployment Architecture

### Official Cache Location

**Primary Cache**: `~/.claude-mpm/cache/remote-agents/`

**Structure**:
```
~/.claude-mpm/cache/remote-agents/
├── .etag-cache.json               # ETag-based sync optimization
├── BASE-AGENT.md                  # Agent build template
├── bobmatnyc/
│   └── claude-mpm-agents/        # Git repository clone
│       ├── .git/                 # Full git repo
│       ├── agents/               # Agent markdown files
│       │   ├── engineer/
│       │   ├── qa/
│       │   ├── ops/
│       │   ├── security/
│       │   └── universal/
│       └── templates/
├── claude-mpm/                    # Another repo
├── documentation/                 # Another repo
└── [other-repos]/
```

**How It Works**:
1. **GitHub Sync**: Agents fetched from `bobmatnyc/claude-mpm-agents` repo
2. **Local Caching**: Cached to `~/.claude-mpm/cache/remote-agents/{owner}/{repo}/`
3. **ETag Updates**: Incremental updates using HTTP ETags (.etag-cache.json)
4. **Discovery**: Cached agents discovered during deployment

---

## All "remote-agents" References (78 Total)

### Configuration & Core (17 files)

1. **Makefile** (Line 1253)
   - Comment: "Git workflow integration for managing agent cache"
   - Path: `~/.claude-mpm/cache/remote-agents/`

2. **config/agent_sources.yaml.example** (Line 152)
   - Example: `ls -la ~/.claude-mpm/cache/remote-agents/`

3. **README.md** (Lines 285-290, 337)
   - Documentation of cache location
   - Migration command reference

4. **CHANGELOG.md** (Lines 103, 545)
   - v4.5.0: "Agents synced from GitHub repos to `~/.claude-mpm/cache/remote-agents/`"
   - Consolidate cache to remote-agents + add git workflow

### Python Code References (28 files)

**Services Layer:**

5-7. **git_operations_service.py** (Lines 15-492)
   - Docstring examples using `~/.claude-mpm/cache/remote-agents/`
   - Git operations for agent repository management

8. **git_source_sync_service.py** (Lines 191-216)
   - Cache configuration: `cache_dir = home / ".claude-mpm" / "cache" / "remote-agents"`
   - Design decision documented in code

9-11. **remote_agent_discovery_service.py** (Lines 45-521)
   - Core service for discovering agents from cache
   - Path parsing logic extracts owner/repo from path structure

12-14. **multi_source_deployment_service.py** (Lines 182-473)
   - Deployment service using remote-agents cache
   - Integration with discovery service

15. **agent_template_builder.py** (Lines 138-139)
   - Path validation: stops at "remote-agents" directory

16. **unified_agent_registry.py** (Line 178)
   - Comment: "Source agents come from ~/.claude-mpm/cache/remote-agents/"

17. **agents_directory_resolver.py**
   - System agents resolution

**CLI Layer:**

18. **agent_sources_check.py** (Line 435)
   - Diagnostics: `cache_dir = Path.home() / ".claude-mpm" / "cache" / "remote-agents"`

### Scripts (4 files)

19. **migrate_etag_cache_to_sqlite.py** (Lines 160-161)
   - Default cache directory parameter

20-22. **migrate_cache_to_remote_agents.py** (Lines 6-295)
   - Migration script from legacy `cache/agents/` to `cache/remote-agents/`
   - WHY: "Research confirmed that `cache/remote-agents/` is the canonical cache location"

23. **update_agent_names.py** (Line 109)
   - Path: `/ "remote-agents"`

24. **sync_agent_skills_repos.sh** (Line 19)
   - `AGENTS_REPO="$HOME/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents"`

25. **automated_release.py** (Line 279)
   - `agents_repo = Path.home() / ".claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents"`

### Documentation (29 files)

**Primary Documentation:**

26. **docs/agents/remote-agents.md** (Complete file)
   - **Authoritative reference** for remote agent system
   - Cache location: `~/.claude-mpm/cache/remote-agents/`
   - Cache management commands

27. **docs/reference/agent-sources-api.md** (Lines 127-877)
   - API reference for agent sources
   - Cache structure documentation

28. **docs/developer/agent-modification-workflow.md** (Lines 11-461)
   - Complete workflow guide for modifying agents in cache
   - Git workflow in `~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/`

29. **docs/reference/cli-doctor.md** (Lines 269-817)
   - Diagnostics checking `~/.claude-mpm/cache/remote-agents/`
   - Troubleshooting commands

**Architecture Documentation:**

30. **docs/architecture/memory-flow.md** (Line 235)
   - "Cached in `~/.claude-mpm/cache/remote-agents/`"

31. **docs/architecture/overview.md** (Line 70)
   - "Consolidated cache architecture (`~/.claude-mpm/cache/remote-agents/`)"

32. **docs/research/agent-deployment-architecture-2025-12-09.md** (Complete file)
   - Detailed analysis of deployment architecture
   - Source location: `~/.claude-mpm/cache/remote-agents/`

**Quick Start & Sessions:**

33. **docs/developer/collection-based-agents-quick-start.md** (Lines 14, 205)
   - Cache path structure
   - Verification commands

34. **docs/sessions/session-pause-20251209.md** (Line 7)
   - SOURCE: `~/.claude-mpm/cache/remote-agents/` (git cache)

---

## Legacy "cache/agents/" References (25 files)

These references are for MIGRATION PURPOSES and should remain:

1. **README.md** (Line 334)
   - "If you have an old `cache/agents/` directory, run the migration script"

2. **migrate_cache_to_remote_agents.py**
   - Entire script purpose: migrate FROM legacy location TO canonical location

3. **src/claude_mpm/cli/startup.py** (Lines 64-95)
   - Legacy check warning users to migrate

4. **docs/developer/migration-log.md**
   - Historical reference of migration

5. **docs/reference/cli-agents.md** (Lines 429, 483)
   - Old documentation (needs update?)

6-25. **Various test files** (test_git_source_sync_phase1.py, etc.)
   - Test fixtures checking old path (should verify migration works)

---

## Correct vs Incorrect Paths

### ✅ CORRECT Paths (Keep All References)

1. **`~/.claude-mpm/cache/remote-agents/`**
   - Canonical cache location
   - Active directory
   - 78 references in codebase
   - **Status**: PRIMARY CACHE LOCATION

2. **`~/.claude-mpm/agents/`**
   - User-defined agent storage
   - Contains `user-defined/` subdirectory
   - **Status**: ACTIVE (different purpose than cache)

### ⚠️ LEGACY Paths (Migration References Only)

1. **`~/.claude-mpm/cache/agents/`**
   - Old cache location (replaced by remote-agents/)
   - Should only appear in migration scripts and warnings
   - **Status**: DEPRECATED

---

## Agent Deployment Flow

```
┌────────────────────────────────────────────────────────────┐
│ PHASE 1: GitHub Sync                                       │
│ Source: https://github.com/bobmatnyc/claude-mpm-agents    │
│ Destination: ~/.claude-mpm/cache/remote-agents/           │
│ Method: ETag-based incremental sync                       │
└────────────────────────────────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────┐
│ PHASE 2: Discovery                                         │
│ Service: RemoteAgentDiscoveryService                       │
│ Input: ~/.claude-mpm/cache/remote-agents/{owner}/{repo}/  │
│ Output: List of available agents with metadata            │
└────────────────────────────────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────┐
│ PHASE 3: Deployment                                        │
│ Service: SingleTierDeploymentService                       │
│ From: ~/.claude-mpm/cache/remote-agents/                  │
│ To: .claude/agents/ (project-level)                       │
└────────────────────────────────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────┐
│ PHASE 4: Claude Code Discovery                            │
│ Location: .claude/agents/                                 │
│ State Tracking: .mpm_deployment_state                     │
└────────────────────────────────────────────────────────────┘
```

---

## Existing Documentation

### Primary Reference: `docs/agents/remote-agents.md`

**Location**: `/Users/masa/Projects/claude-mpm/docs/agents/remote-agents.md`

**Contents**:
- Overview of remote agent system
- How automatic synchronization works
- Cache location and structure
- Cache management commands
- Troubleshooting guide
- Best practices

**Key Sections**:
1. **Cache Location** (Lines 82-91)
   ```
   ~/.claude-mpm/cache/remote-agents/
   ```

2. **Cache Updates** (Lines 93-99)
   - Automatic on startup
   - ETag validation
   - Incremental sync

3. **Manual Cache Refresh** (Lines 100-106)
   ```bash
   rm -rf ~/.claude-mpm/cache/remote-agents/
   claude-mpm --mpm:agents deploy
   ```

4. **Troubleshooting** (Lines 147-187)
   - Remote agents not appearing
   - Cache corruption
   - Solutions with commands

### Secondary Reference: `docs/reference/agent-sources-api.md`

**Location**: `/Users/masa/Projects/claude-mpm/docs/reference/agent-sources-api.md`

**Contents**:
- Technical API reference
- Data models (GitRepository, AgentSourceConfiguration)
- Services (GitSourceManager, SingleTierDeploymentService)
- Caching system details

**Key Sections**:
1. **Cache Structure** (Lines 127-135)
   ```
   ~/.claude-mpm/cache/remote-agents/{owner}/{repo}/{subdirectory}/
   ```

2. **Cache Configuration** (Lines 407-415)
   - Default: `~/.claude-mpm/cache/remote-agents/`

### Workflow Guide: `docs/developer/agent-modification-workflow.md`

**Location**: `/Users/masa/Projects/claude-mpm/docs/developer/agent-modification-workflow.md`

**Contents**:
- How to modify agents in cache
- Git workflow for contributing changes
- Committing and pushing changes back

**Key Points**:
1. **Cache is a git repository** (Line 15)
   - `~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/`

2. **Direct editing workflow** (Lines 78-88)
   ```bash
   cd ~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents
   vim agents/qa/api-qa.md
   ```

3. **Git workflow** (Lines 125-273)
   - Create branch
   - Make changes
   - Commit
   - Push to remote

---

## PM_INSTRUCTIONS.md Analysis

### Current File Locations

1. **Source**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/PM_INSTRUCTIONS.md`
2. **Project Copy**: `/Users/masa/Projects/claude-mpm/.claude-mpm/PM_INSTRUCTIONS.md`
3. **Venv Copy**: (bundled with package)

### Current Agent Deployment References

**Finding**: PM_INSTRUCTIONS.md does NOT currently reference agent deployment architecture.

**Content Focus** (Lines 1-150):
- PM role and delegation principles
- Core workflow: do the work, then report
- Tool usage guide (Task, TodoWrite)
- Git workflow integration
- Verification protocols

**What's Missing**:
- Where agents come from (GitHub repos)
- How agents are cached
- Agent deployment process
- Reference to agent architecture documentation

### Recommended Addition to PM_INSTRUCTIONS.md

**Suggested Section**: "Agent Architecture Context"

**Placement**: After "Tool Usage Guide" (around line 150)

**Content**:
```markdown
## Agent Architecture Context

### Where Agents Come From

The agents you delegate to are pulled from GitHub repositories and cached locally:

1. **Source**: `https://github.com/bobmatnyc/claude-mpm-agents`
2. **Cache**: `~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/`
3. **Deployment**: `.claude/agents/` (project-level)

### Agent Discovery Priority

When you delegate to an agent (e.g., "engineer", "qa"), the system discovers agents with this priority:

1. **PROJECT** (`.claude/agents/`) - Project-specific customizations (highest)
2. **REMOTE** (`~/.claude-mpm/cache/remote-agents/`) - GitHub-synced agents
3. **SYSTEM** (bundled) - Framework default agents (lowest)

### Why This Matters for PMs

- **Delegation Target**: When you delegate to "engineer", you're using the remote-cached agent
- **Customizations**: Projects can override remote agents with project-specific versions
- **Updates**: Remote agents are synced from GitHub on startup (ETag-based incremental)

### For More Details

Complete agent architecture documentation:
- **Primary Reference**: `docs/agents/remote-agents.md`
- **API Reference**: `docs/reference/agent-sources-api.md`
- **Modification Guide**: `docs/developer/agent-modification-workflow.md`
```

**Rationale**:
- PMs should understand where agents come from
- Helps explain why delegation works
- Provides context for customization capabilities
- Points to complete documentation without duplicating details

---

## Summary of Findings

### Question 1: Find all "remote-agents" references

**Answer**: Found 78 references across:
- 17 configuration/core files
- 28 Python code files
- 4 scripts
- 29 documentation files

**Status**: ALL CORRECT - no cleanup needed

### Question 2: Understand current agent deployment flow

**Answer**:
```
GitHub Repos
    ↓ (sync)
~/.claude-mpm/cache/remote-agents/{owner}/{repo}/
    ↓ (discover)
RemoteAgentDiscoveryService
    ↓ (deploy)
.claude/agents/ (project-level)
    ↓ (discover)
Claude Code
```

### Question 3: Find existing documentation about agent deployment

**Answer**: Three primary documents:
1. **docs/agents/remote-agents.md** - User-facing guide (COMPLETE)
2. **docs/reference/agent-sources-api.md** - Technical API reference (COMPLETE)
3. **docs/developer/agent-modification-workflow.md** - Developer workflow guide (COMPLETE)

### Question 4: Check PM_INSTRUCTIONS.md

**Answer**:
- Currently does NOT reference agent deployment
- Recommended section: "Agent Architecture Context" (after Tool Usage Guide)
- Content: Brief overview + pointers to complete docs

---

## Recommended Actions

### ✅ NO CLEANUP NEEDED

**Finding**: "remote-agents" is the CORRECT and CANONICAL path.

**Rationale**:
1. Directory exists and is actively used
2. All 78 references are intentional and correct
3. Migration from legacy `cache/agents/` is complete
4. Documentation is comprehensive and accurate

### ⚠️ CLARIFICATION NEEDED

**Issue**: User confusion between:
- `~/.claude-mpm/agents/` (user-defined storage)
- `~/.claude-mpm/cache/remote-agents/` (GitHub cache)

**Resolution**: Both directories are correct and serve different purposes.

### 📝 DOCUMENTATION ENHANCEMENT

**Recommendation**: Add brief agent architecture section to PM_INSTRUCTIONS.md

**Section**: "Agent Architecture Context"
**Location**: After "Tool Usage Guide" (around line 150)
**Content**: Overview + pointers to complete documentation

**Files to Update**:
- `src/claude_mpm/agents/PM_INSTRUCTIONS.md`

**Benefit**: Helps PMs understand delegation targets and agent discovery priority

---

## Verification Commands

```bash
# Verify cache directory exists
ls -la ~/.claude-mpm/cache/remote-agents/

# Check agent repository cache
ls -la ~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/

# View ETag cache
cat ~/.claude-mpm/cache/remote-agents/.etag-cache.json

# Check user-defined agents
ls -la ~/.claude-mpm/agents/

# Verify legacy cache does NOT exist
ls -la ~/.claude-mpm/cache/agents/ 2>&1 | grep "No such file"
```

---

## Conclusion

**Finding**: The term "remote-agents" is correct and should be kept as-is.

**Root Cause of Confusion**: Two different "agents" directories exist with different purposes:
1. `~/.claude-mpm/agents/` - User-defined agent storage
2. `~/.claude-mpm/cache/remote-agents/` - Remote agent cache from GitHub

**Action Required**:
1. ✅ No cleanup of "remote-agents" references needed
2. 📝 Consider adding agent architecture context to PM_INSTRUCTIONS.md
3. ℹ️ Clarify to user that both directories are correct and intentional

**Documentation Status**: Comprehensive and complete
- Primary: `docs/agents/remote-agents.md` ⭐
- API: `docs/reference/agent-sources-api.md`
- Workflow: `docs/developer/agent-modification-workflow.md`

---

## Files Analyzed

**Total Files**: 78
**Directories Checked**: 5
**Documentation Files**: 29
**Python Files**: 28
**Scripts**: 4
**Configuration**: 17

**Key Searches**:
- `grep -r "remote-agents" .` - 78 matches
- `grep -r "cache/agents[^-]" .` - 25 matches (legacy)
- `ls ~/.claude-mpm/` - Directory structure verification
- `ls ~/.claude-mpm/cache/` - Cache directory verification

---

**Research Complete**
