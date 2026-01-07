# Claude MPM Cache Directory Structure Analysis

**Date**: 2025-12-22
**Researcher**: Research Agent
**Context**: Investigation of cache directory structure and deployed documentation

## Executive Summary

Claude MPM uses **TWO separate cache directories** for agent storage:
1. `~/.claude-mpm/cache/agents/` - **Legacy/Local cache** (outdated, minimal usage)
2. `~/.claude-mpm/cache/remote-agents/` - **Primary cache** (GitHub-synced, actively used)

**Key Finding**: The `remote-agents` directory contains BOTH:
- Flattened agent definitions (built from modular sources)
- Full GitHub repository clone of `bobmatnyc/claude-mpm-agents`
- Currently NO framework documentation deployed with agents

---

## 1. Cache Directory Structure

### 1.1 Overview

```
~/.claude-mpm/cache/
├── agents/                      # Legacy/Local cache (outdated)
│   ├── .etag-cache.json         # HTTP ETag tracking
│   ├── BASE-AGENT.md            # Universal agent instructions
│   ├── documentation/           # EMPTY directory (no agents)
│   ├── universal/               # 5 agents (outdated versions)
│   ├── engineer/                # Engineering agents (outdated)
│   ├── qa/                      # QA agents (outdated)
│   ├── ops/                     # Ops agents (outdated)
│   └── security/                # Security agents (outdated)
│
├── remote-agents/               # PRIMARY cache (GitHub-synced)
│   ├── .etag-cache.json         # HTTP ETag tracking
│   ├── .etag-cache.json.migrated  # Migration marker
│   ├── BASE-AGENT.md            # Universal agent instructions
│   │
│   ├── documentation/           # Documentation agents (DEPLOYED)
│   │   ├── documentation.md     # 386 lines - technical docs agent
│   │   └── ticketing.md         # 1,722 lines - ticketing agent
│   │
│   ├── universal/               # Cross-cutting agents (8 agents)
│   ├── engineer/                # Engineering agents (24 agents)
│   ├── qa/                      # QA agents (3 agents)
│   ├── ops/                     # Ops agents (5 agents)
│   ├── security/                # Security agents (1 agent)
│   ├── claude-mpm/              # MPM framework agents (2 agents)
│   │
│   └── bobmatnyc/               # Full GitHub repos cloned
│       ├── claude-mpm-agents/   # Agent templates repository
│       │   ├── README.md
│       │   ├── CHANGELOG.md
│       │   ├── CONTRIBUTING.md
│       │   ├── AUTO-DEPLOY-INDEX.md
│       │   ├── agents/          # Source agent definitions (modular)
│       │   ├── dist/            # Built agent definitions (flattened)
│       │   ├── templates/       # Reference materials
│       │   ├── docs/research/   # Research outputs
│       │   └── build-agent.py   # Build script
│       │
│       └── claude-mpm-skills/   # Skills repository
│
└── skills/                      # Skills cache
```

### 1.2 Key Differences: `agents/` vs `remote-agents/`

| Aspect | `agents/` (Legacy) | `remote-agents/` (Primary) |
|--------|-------------------|---------------------------|
| **Status** | Outdated, minimal usage | Actively used, GitHub-synced |
| **Source** | Unknown/legacy | GitHub: bobmatnyc/claude-mpm-agents |
| **Documentation agents** | Empty directory (0 agents) | 2 agents deployed (documentation, ticketing) |
| **Update mechanism** | Manual/unknown | Git pull from GitHub |
| **Full repo clone** | No | Yes (bobmatnyc/ subdirectory) |
| **Agent count** | ~20 agents (outdated) | ~43+ agents (current) |
| **Config reference** | Not referenced in config.py | Referenced in config.py line 606-608 |

**Config.py Reference**:
```python
# Line 606-608 in src/claude_mpm/core/config.py
"cache_dir": str(
    Path.home() / ".claude-mpm" / "cache" / "remote-agents"
),
```

### 1.3 Cache Population Mechanism

**Service**: `CacheGitManager` (`src/claude_mpm/services/agents/cache_git_manager.py`)

**Workflow**:
1. **Git Repository Detection**: Searches for `.git` directory in cache path or parents
2. **Repository Clone**: If not exists, clones `github.com/bobmatnyc/claude-mpm-agents`
3. **Periodic Sync**: Git pull before agent deployment/discovery
4. **Agent Extraction**: Flattened agents copied from `dist/agents/` to `remote-agents/`

**Git Operations**:
- `pull_latest()` - Sync latest agents from GitHub
- `get_status()` - Check uncommitted/unpushed changes
- `commit()` / `push()` - User modifications (local customizations)

---

## 2. Documentation Deployment Status

### 2.1 Currently Deployed Documentation

**Location**: `~/.claude-mpm/cache/remote-agents/documentation/`

**Files**:
1. **documentation.md** (386 lines)
   - Memory-efficient documentation generation
   - Semantic search integration
   - Progressive summarization techniques
   - API documentation patterns

2. **ticketing.md** (1,722 lines)
   - Ticket management and tracking
   - Integration with mcp-ticketer
   - Workflow automation
   - Status reporting

**Deployed As**: Full agent definitions (YAML frontmatter + instructions)

### 2.2 Documentation in GitHub Repository

**Repository**: `bobmatnyc/claude-mpm-agents`

**Structure**:
```
claude-mpm-agents/
├── README.md                    # Agent templates overview
├── AGENTS.md                    # Agent catalog
├── CHANGELOG.md                 # Version history (144KB!)
├── CONTRIBUTING.md              # Contribution guidelines
├── IMPLEMENTATION-SUMMARY.md    # Implementation details
├── AUTO-DEPLOY-INDEX.md         # Project type detection rules
├── REORGANIZATION-PLAN.md       # Reorganization strategy
│
├── docs/                        # Documentation directory
│   └── research/                # Research outputs only
│       └── agent-template-library-analysis-2025-11-30.md
│
└── templates/                   # Reference materials (NOT agents)
    ├── AGENT_TEMPLATE_REFERENCE.md  # Template schema
    ├── circuit-breakers.md          # PM violation patterns
    ├── pm-examples.md               # PM behavior examples
    ├── validation-templates.md      # Verification templates
    └── base/                        # BASE-AGENT templates
```

**Current Documentation Types**:
1. **Agent Development**: README, CONTRIBUTING, AGENT_TEMPLATE_REFERENCE
2. **Repository Metadata**: CHANGELOG, IMPLEMENTATION-SUMMARY, REORGANIZATION-PLAN
3. **Reference Materials**: templates/ directory (PM examples, circuit breakers, etc.)
4. **Research Outputs**: docs/research/ (single file)

### 2.3 What Documentation is NOT Deployed

**Missing Framework Documentation**:
- ❌ Agent architecture overview
- ❌ BASE-AGENT.md inheritance system explanation
- ❌ Cache directory structure documentation
- ❌ Agent discovery priority rules
- ❌ How to modify/customize agents
- ❌ How to contribute new agents
- ❌ Build system documentation (build-agent.py)
- ❌ Deployment workflow documentation

**Why Missing**:
- GitHub repo contains development/contribution docs (README, CONTRIBUTING)
- NOT copied to deployed agent cache locations
- Agent definitions are flattened (BASE-AGENT.md merged, not standalone)
- No framework docs in `dist/agents/` output

---

## 3. Recommended Documentation Structure

### 3.1 Deployed Framework Documentation

**Proposal**: Add `/docs/` directory to deployed agent cache

**Structure**:
```
~/.claude-mpm/cache/remote-agents/
├── docs/                        # Framework documentation
│   ├── README.md                # Quick start guide
│   ├── ARCHITECTURE.md          # Cache structure & discovery
│   ├── CUSTOMIZATION.md         # How to modify agents
│   ├── BASE-AGENT-SYSTEM.md     # Inheritance explanation
│   └── CONTRIBUTING.md          # How to contribute agents
│
├── documentation/               # Documentation agents
│   ├── documentation.md
│   └── ticketing.md
│
├── universal/                   # Universal agents
├── engineer/                    # Engineering agents
├── ...
```

**Key Documents**:

#### 3.1.1 `/docs/README.md` - Quick Start
```markdown
# Claude MPM Agents - Quick Start

## What is this directory?

This is your local cache of Claude MPM agents, synced from:
https://github.com/bobmatnyc/claude-mpm-agents

## Directory Structure

- `documentation/` - Documentation generation agents
- `engineer/` - Engineering specialists (Python, Go, React, etc.)
- `qa/` - Quality assurance and testing agents
- `ops/` - Operations and deployment agents
- `universal/` - Cross-cutting agents (research, memory, etc.)

## Discovery Priority

Agents are discovered in this order:
1. Project-specific agents (~/.claude-mpm/agents/{project-name}/)
2. Local customizations (~/.claude-mpm/agents/)
3. Remote agents (this cache)

## Customization

To customize an agent:
1. Copy agent to ~/.claude-mpm/agents/
2. Modify instructions
3. Agent loader prioritizes local copy

See CUSTOMIZATION.md for details.
```

#### 3.1.2 `/docs/ARCHITECTURE.md` - Cache Structure
```markdown
# Claude MPM Cache Architecture

## Overview

Claude MPM uses a multi-tier agent discovery system:

1. **Project-specific agents**: `~/.claude-mpm/agents/{project-name}/`
2. **Local agents**: `~/.claude-mpm/agents/`
3. **Remote agents**: `~/.claude-mpm/cache/remote-agents/` (this directory)

## Cache Sync Mechanism

This cache is a Git repository tracking:
https://github.com/bobmatnyc/claude-mpm-agents

**Update Trigger**: Agents are updated via git pull:
- Before agent deployment
- Via `claude-mpm agents update` command
- Automatic on startup (if >24h since last sync)

## Agent Sources

Remote agents come from two sources:

1. **Flat agents** (root level): Built from modular sources
   - Example: `documentation/documentation.md`
   - BASE-AGENT.md inheritance merged

2. **Full repository** (`bobmatnyc/` subdirectory): Complete GitHub clone
   - Source agents: `bobmatnyc/claude-mpm-agents/agents/`
   - Built agents: `bobmatnyc/claude-mpm-agents/dist/agents/`
   - Templates: `bobmatnyc/claude-mpm-agents/templates/`

## Discovery Process

When you request "documentation agent":

1. Check project-specific: `~/.claude-mpm/agents/my-project/documentation/documentation.md`
2. Check local override: `~/.claude-mpm/agents/documentation/documentation.md`
3. Check remote cache: `~/.claude-mpm/cache/remote-agents/documentation/documentation.md` ✓

Priority: Project > Local > Remote
```

#### 3.1.3 `/docs/BASE-AGENT-SYSTEM.md` - Inheritance
```markdown
# BASE-AGENT.md Inheritance System

## Overview

Agent definitions use a hierarchical inheritance system to reduce duplication.

## How It Works

Each directory can have a `BASE-AGENT.md` file with shared instructions for all agents in that directory.

**Inheritance Chain** (for `engineer/backend/python-engineer.md`):
```
python-engineer.md               # Python-specific (150 lines)
  + engineer/backend/BASE-AGENT.md   # Backend patterns (if exists)
  + engineer/BASE-AGENT.md           # Engineering principles (300 lines)
  + BASE-AGENT.md                    # Universal standards (200 lines)
  ---
  = Final agent (650 lines total)
```

## BASE-AGENT.md Levels

### Root Level (`BASE-AGENT.md`)
Universal instructions for ALL agents:
- Git workflow standards
- Memory routing protocols
- Output format standards
- Quality standards

### Category Level (`engineer/BASE-AGENT.md`)
Shared for agent category:
- Engineer: SOLID principles, code reduction, type safety
- QA: Testing strategies, coverage standards
- Ops: Deployment verification, monitoring

### Agent Level (`engineer/backend/python-engineer.md`)
Agent-specific instructions only.

## Benefits

- ✅ 57% reduction in duplication
- ✅ Consistent standards across categories
- ✅ Update shared instructions once
- ✅ Agent-specific content stays focused
```

#### 3.1.4 `/docs/CUSTOMIZATION.md` - Modification Guide
```markdown
# Customizing Claude MPM Agents

## Local Overrides

To override a remote agent with your customizations:

1. **Copy agent to local directory**:
   ```bash
   mkdir -p ~/.claude-mpm/agents/documentation
   cp ~/.claude-mpm/cache/remote-agents/documentation/documentation.md \
      ~/.claude-mpm/agents/documentation/documentation.md
   ```

2. **Edit instructions**:
   ```bash
   $EDITOR ~/.claude-mpm/agents/documentation/documentation.md
   ```

3. **Agent loader automatically prioritizes local copy** ✓

## Project-Specific Agents

For project-specific customizations:

1. **Copy to project directory**:
   ```bash
   mkdir -p ~/.claude-mpm/agents/my-project/documentation
   cp ~/.claude-mpm/cache/remote-agents/documentation/documentation.md \
      ~/.claude-mpm/agents/my-project/documentation/documentation.md
   ```

2. **Edit instructions** with project-specific requirements

3. **Agent loader uses project-specific version** when in that project ✓

## Creating New Agents

To create a custom agent:

1. **Fork repository**: https://github.com/bobmatnyc/claude-mpm-agents
2. **Add agent to `agents/` directory** with YAML frontmatter
3. **Build flattened version**: `./build-agent.py agents/my-agent.md`
4. **Deploy locally or submit PR**

See CONTRIBUTING.md for full contribution guidelines.
```

### 3.2 Deployment Location Options

**Option A: Separate `docs/` directory in cache** (RECOMMENDED)
```
~/.claude-mpm/cache/remote-agents/
├── docs/                        # Framework documentation
│   ├── README.md
│   ├── ARCHITECTURE.md
│   └── ...
├── documentation/               # Documentation agents
├── universal/
└── ...
```

**Pros**:
- Clear separation between agents and framework docs
- Easy to discover (standard `/docs` convention)
- Can be synced from GitHub repo

**Cons**:
- Requires adding `/docs` to GitHub repo
- Build script needs to copy docs to `dist/`

**Option B: Framework docs in agent format** (NOT RECOMMENDED)
```
~/.claude-mpm/cache/remote-agents/
├── docs-framework/
│   ├── architecture.md          # Fake "agent" with docs
│   └── customization.md
```

**Pros**:
- Reuses existing agent deployment mechanism

**Cons**:
- Confusing (not real agents)
- Pollutes agent namespace
- Harder to maintain

**Option C: Documentation embedded in README** (CURRENT STATE)
```
~/.claude-mpm/cache/remote-agents/
└── bobmatnyc/claude-mpm-agents/
    ├── README.md                # All framework docs here
    └── ...
```

**Pros**:
- Already exists (no changes needed)

**Cons**:
- Not deployed to flat cache structure
- Hidden in `bobmatnyc/` subdirectory
- README is 12KB (too large for quick reference)

---

## 4. Current Deployment Mechanism

### 4.1 Build System

**Script**: `build-agent.py` in `bobmatnyc/claude-mpm-agents/`

**Process**:
1. **Read modular agent** from `agents/{category}/{agent}.md`
2. **Collect BASE-AGENT.md files** from directory hierarchy
3. **Merge content** (agent-specific + BASE-AGENT chain)
4. **Write flattened agent** to `dist/agents/{category}/{agent}.md`
5. **Copy to cache** via Git sync

**Example**:
```bash
# Input
agents/documentation/documentation.md        # 150 lines (agent-specific)
agents/documentation/BASE-AGENT.md           # (if exists)
agents/BASE-AGENT.md                         # 200 lines (universal)

# Build
./build-agent.py agents/documentation/documentation.md

# Output
dist/agents/documentation/documentation.md   # 386 lines (merged)
```

### 4.2 Cache Sync

**Service**: `GitSourceSyncService` (`src/claude_mpm/services/agents/sources/git_source_sync_service.py`)

**Workflow**:
1. Clone `bobmatnyc/claude-mpm-agents` to `~/.claude-mpm/cache/remote-agents/bobmatnyc/`
2. Copy built agents from `dist/agents/` to `~/.claude-mpm/cache/remote-agents/`
3. Track ETags to avoid unnecessary re-downloads

**Trigger Points**:
- Agent deployment (`claude-mpm agents deploy`)
- Agent discovery (`claude-mpm agents list`)
- Startup sync (if >24h since last update)
- Manual update (`claude-mpm agents update`)

---

## 5. Recommendations

### 5.1 Short-Term: Deploy Framework Docs to Cache

**Action**: Add `/docs` directory to `bobmatnyc/claude-mpm-agents` repo

**Files to Add**:
1. `docs/README.md` - Quick start and overview
2. `docs/ARCHITECTURE.md` - Cache structure and discovery
3. `docs/BASE-AGENT-SYSTEM.md` - Inheritance explanation
4. `docs/CUSTOMIZATION.md` - How to modify agents
5. `docs/CONTRIBUTING.md` - How to contribute (from root)

**Build Script Update**:
```python
# In build-agent.py, add:
def copy_docs_to_dist():
    """Copy docs/ directory to dist/ for deployment."""
    shutil.copytree("docs", "dist/docs", dirs_exist_ok=True)
```

**Result**: Users have framework documentation in deployed cache
```
~/.claude-mpm/cache/remote-agents/
├── docs/                        # Framework documentation ✓
│   ├── README.md
│   └── ...
├── documentation/               # Documentation agents
└── ...
```

### 5.2 Medium-Term: Consolidate Cache Directories

**Problem**: TWO cache directories (`agents/` and `remote-agents/`) cause confusion

**Action**: Deprecate `~/.claude-mpm/cache/agents/` directory

**Migration**:
1. Add warning when `agents/` directory detected
2. Provide migration command: `claude-mpm migrate-cache`
3. Remove references to `agents/` in codebase
4. Update documentation to mention only `remote-agents/`

### 5.3 Long-Term: Self-Documenting Cache

**Vision**: Cache directory becomes self-documenting

**Features**:
1. **README at cache root**:
   ```
   ~/.claude-mpm/cache/remote-agents/README.md
   ```
   Quick explanation of directory structure

2. **Category READMEs**:
   ```
   ~/.claude-mpm/cache/remote-agents/engineer/README.md
   ```
   Overview of engineering agents available

3. **Discovery command**:
   ```bash
   claude-mpm agents docs
   # Opens ~/.claude-mpm/cache/remote-agents/docs/README.md
   ```

4. **Interactive documentation**:
   ```bash
   claude-mpm agents explain documentation
   # Shows: Purpose, capabilities, use cases, customization
   ```

---

## 6. Critical Questions - Answered

### Q1: What's in `~/.claude-mpm/cache/agents/` vs `remote-agents/`?

**Answer**:
- `agents/` - **Legacy cache**, outdated, minimal usage (~20 agents)
- `remote-agents/` - **Primary cache**, GitHub-synced, actively used (~43+ agents)

**Different Purposes**:
- `agents/` - Unknown origin, appears to be legacy/manual deployment
- `remote-agents/` - Git-synced from `bobmatnyc/claude-mpm-agents`, automatic updates

**Canonical**: `remote-agents/` is the canonical cache (referenced in config.py)

### Q2: What documentation IS deployed with agents?

**Answer**: Minimal framework documentation deployed

**Currently Deployed**:
- ✅ Agent definitions (flattened with BASE-AGENT.md merged)
- ✅ Documentation agents (2 files, 386 + 1,722 lines)
- ✅ Full GitHub repo clone in `bobmatnyc/` subdirectory

**NOT Deployed to Flat Cache**:
- ❌ README.md (exists in `bobmatnyc/claude-mpm-agents/` only)
- ❌ CONTRIBUTING.md (exists in `bobmatnyc/claude-mpm-agents/` only)
- ❌ Framework architecture docs
- ❌ BASE-AGENT system explanation
- ❌ Cache structure documentation

### Q3: What documentation SHOULD be deployed?

**Answer**: Framework documentation for agent users

**Recommended**:
1. **Quick Start** (`docs/README.md`) - What is this cache? How to use agents?
2. **Architecture** (`docs/ARCHITECTURE.md`) - Discovery priority, cache structure
3. **BASE-AGENT System** (`docs/BASE-AGENT-SYSTEM.md`) - Inheritance explanation
4. **Customization** (`docs/CUSTOMIZATION.md`) - How to modify agents
5. **Contributing** (`docs/CONTRIBUTING.md`) - How to add new agents

**Format**: Markdown documentation (NOT agent definitions)

**Location**: `/docs/` subdirectory in deployed cache

### Q4: Where should deployed docs live?

**Answer**: `~/.claude-mpm/cache/remote-agents/docs/` (Option A)

**Source**: `bobmatnyc/claude-mpm-agents/docs/` (add to GitHub repo)

**Deployment**: Build script copies `docs/` to `dist/docs/` during agent build

**Access**:
```bash
# View framework docs
cat ~/.claude-mpm/cache/remote-agents/docs/README.md

# Or via command
claude-mpm agents docs
```

---

## 7. Implementation Plan

### Phase 1: Add Framework Docs to GitHub Repo

1. **Create `docs/` directory** in `bobmatnyc/claude-mpm-agents`
2. **Write documentation files**:
   - `docs/README.md` - Quick start
   - `docs/ARCHITECTURE.md` - Cache structure
   - `docs/BASE-AGENT-SYSTEM.md` - Inheritance
   - `docs/CUSTOMIZATION.md` - Modification guide
3. **Update build script** to copy `docs/` to `dist/docs/`
4. **Commit and push** to GitHub

### Phase 2: Update Cache Sync to Deploy Docs

1. **Modify `GitSourceSyncService`** to copy `dist/docs/` to cache
2. **Add cache validation** to verify docs deployed
3. **Test sync workflow** with new docs

### Phase 3: Add CLI Command for Docs

1. **Add `claude-mpm agents docs` command**
2. **Display framework documentation** in terminal
3. **Add `--category` flag** for category-specific docs

### Phase 4: Deprecate Legacy Cache

1. **Add migration warning** when `agents/` detected
2. **Provide migration command**: `claude-mpm migrate-cache`
3. **Update documentation** to reference only `remote-agents/`

---

## 8. Conclusion

Claude MPM's cache structure is well-designed but **lacks deployed framework documentation**. The current system has:

**Strengths**:
- ✅ Clear separation between local and remote agents
- ✅ Git-based sync for automatic updates
- ✅ BASE-AGENT.md inheritance reduces duplication
- ✅ Flattened agents ready for deployment

**Gaps**:
- ❌ No framework documentation in deployed cache
- ❌ Legacy `agents/` directory causes confusion
- ❌ Users must navigate to `bobmatnyc/` subdirectory for repo docs
- ❌ No self-documenting cache structure

**Recommendation**: Implement **Phase 1** immediately to deploy framework documentation alongside agents. This provides users with critical context about cache structure, discovery priority, and customization options.

**Next Steps**:
1. Create `docs/` directory in `bobmatnyc/claude-mpm-agents`
2. Write 5 key documentation files (README, ARCHITECTURE, BASE-AGENT-SYSTEM, CUSTOMIZATION, CONTRIBUTING)
3. Update build script to deploy docs to `dist/docs/`
4. Test deployment to verify docs appear in cache
5. Add CLI command for easy doc access
