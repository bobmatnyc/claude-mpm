# Agents/Skills CLI Structure Research & New Workflow Design

**Date**: 2025-12-01
**Researcher**: Claude Research Agent
**Objective**: Research current agents/skills CLI structure and design new workflow integrating AUTO-DEPLOY-INDEX.md

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current State Analysis](#current-state-analysis)
3. [AUTO-DEPLOY-INDEX.md Structure](#auto-deploy-indexmd-structure)
4. [Proposed New CLI Command Tree](#proposed-new-cli-command-tree)
5. [User Journey Examples](#user-journey-examples)
6. [Implementation Roadmap](#implementation-roadmap)

---

## Executive Summary

### Key Findings

1. **Current CLI is fragmented**: Agents and skills have separate command structures with parallel implementations
2. **Source management exists** but lacks cohesive workflow for discovery → selection → deployment
3. **AUTO-DEPLOY-INDEX.md** provides rich categorization but isn't exposed via CLI
4. **No preset system**: Users must manually select agents; no "python-dev" or "web-dev" shortcuts
5. **Skills CLI is more mature**: Collection management, toolchain filtering already implemented

### Critical Gaps

- ❌ **No unified source management**: `agent-source` and `skill-source` are separate
- ❌ **No discovery workflow**: Can't browse available agents from configured sources
- ❌ **No preset categories**: Can't deploy "python-dev" or "react-fullstack" profiles
- ❌ **No AUTO-DEPLOY integration**: Rich categorization data not accessible via CLI
- ❌ **Manual selection required**: Users must know exact agent names

### Recommended Approach

**Option A: Unified Workflow** (Recommended)
```bash
claude-mpm sources add https://github.com/org/agents-repo
claude-mpm browse --category python  # Discover available
claude-mpm deploy --preset python-dev  # Deploy by preset
claude-mpm deploy --agent engineer/backend/python-engineer  # Deploy specific
```

**Option B: Parallel Commands** (Current state)
```bash
claude-mpm agent-source add <url>
claude-mpm agents available --category python
claude-mpm agents deploy --preset python-dev
```

---

## Current State Analysis

### 1. Agents CLI Commands

**File**: `src/claude_mpm/cli/commands/agents.py` (1,894 lines)

**Current Commands**:

```
claude-mpm agents                    # Show agent versions (default)
claude-mpm agents list               # List available or deployed agents
  --system                           # List system agents
  --deployed                         # List deployed agents
  --by-tier                          # Group by precedence (PROJECT > USER > SYSTEM)
claude-mpm agents deploy             # Deploy system and project agents
  --force                            # Force redeploy
claude-mpm agents clean              # Clean deployed agents
claude-mpm agents view <name>        # View agent details
claude-mpm agents fix <name>         # Fix agent frontmatter issues
  --dry-run                          # Preview fixes
  --all                              # Fix all agents

# Dependency Management
claude-mpm agents deps-check [agent] # Check agent dependencies
claude-mpm agents deps-install       # Install missing dependencies
claude-mpm agents deps-list          # List all dependencies
claude-mpm agents deps-fix           # Fix dependency issues with retry

# Cleanup & Migration
claude-mpm agents cleanup            # Advanced cleanup with orphan detection
claude-mpm agents cleanup-orphaned   # Remove orphaned agents
claude-mpm agents migrate-to-project # DEPRECATED: Migrate user agents to project

# Local Agent Management
claude-mpm agents create             # Create local agent
  --interactive                      # Interactive wizard
  --agent-id <id>                    # Non-interactive creation
claude-mpm agents edit <id>          # Edit local agent
  --interactive                      # Interactive editor
claude-mpm agents delete <id>...     # Delete local agent(s)
  --force                            # Skip confirmation
claude-mpm agents manage             # Interactive management menu
claude-mpm agents configure          # Configure deployment settings
  --enable/--disable                 # Enable/disable specific agents
  --show                             # Show current settings

# Auto-Configuration (TSK-0054 Phase 5)
claude-mpm agents detect             # Detect project toolchain
claude-mpm agents recommend          # Recommend agents based on toolchain

# Agent Selection Modes (Phase 3: 1M-382)
claude-mpm agents deploy-minimal     # Deploy 6 core agents
claude-mpm agents deploy-auto        # Auto-detect + deploy matching agents

# Source Management (Phase 2: 1M-442)
claude-mpm agents available          # List agents from configured sources
  --source <id>                      # Filter by source
  --format json|table|simple         # Output format
```

**Agent Selection Service** (`src/claude_mpm/services/agents/agent_selection_service.py`):
- `deploy_minimal_configuration()` - Deploys 6 core agents: engineer, documentation, qa, research, ops, ticketing
- `deploy_auto_configure()` - Auto-detects toolchain and deploys matching agents
- Uses toolchain detector to identify languages, frameworks, build tools

### 2. Agent Source CLI Commands

**File**: `src/claude_mpm/cli/commands/agent_source.py` (775 lines)

**Current Commands**:

```
claude-mpm agent-source add <url>    # Add new agent source
  --priority <0-1000>                # Source priority (lower = higher precedence)
  --subdirectory <path>              # Subdirectory within repo
  --disabled                         # Add but don't enable
  --test                             # Test only, don't save
  --no-test                          # Skip testing (not recommended)

claude-mpm agent-source list         # List configured sources
  --by-priority                      # Sort by priority
  --enabled-only                     # Show only enabled
  --json                             # JSON output

claude-mpm agent-source remove <id>  # Remove source
  --force                            # Skip confirmation

claude-mpm agent-source update       # Update (sync) all sources
claude-mpm agent-source update <id>  # Update specific source
  --force                            # Force sync even if cache fresh

claude-mpm agent-source enable <id>  # Enable source
claude-mpm agent-source disable <id> # Disable source

claude-mpm agent-source show <id>    # Show source details
  --agents                           # List agents from source
```

**Key Features**:
- ✅ **Immediate testing on add**: Tests GitHub API access and syncs to validate
- ✅ **ETag-based caching**: Incremental updates using HTTP ETags
- ✅ **Priority system**: Lower number = higher precedence
- ✅ **System repo always available**: `https://github.com/bobmatnyc/claude-mpm-agents`

**Git Source Manager** (`src/claude_mpm/services/agents/git_source_manager.py`):
- `sync_repository()` - Syncs single repo with ETag caching
- `sync_all_repositories()` - Syncs multiple repos in priority order
- `list_cached_agents()` - Lists discovered agents with optional repo filter

### 3. Skills CLI Commands

**File**: `src/claude_mpm/cli/commands/skills.py` (923 lines)

**Current Commands**:

```
claude-mpm skills                    # List available skills (default)
claude-mpm skills list               # List bundled skills
  --agent <name>                     # Filter by agent
  --category <name>                  # Filter by category
  --verbose                          # Show descriptions

claude-mpm skills deploy             # Deploy bundled skills
  --force                            # Force redeploy
  --skills <names>                   # Deploy specific skills

claude-mpm skills validate <name>    # Validate skill structure
  --strict                           # Treat warnings as errors

claude-mpm skills update             # Check for/install updates
  --check-only                       # Check without installing
  --force                            # Force update

claude-mpm skills info <name>        # Show detailed skill info
  --show-content                     # Display skill content

claude-mpm skills config             # Manage skills configuration
  --scope project|user               # Configuration scope
  --edit                             # Open in editor
  --path                             # Show config path

# GitHub Skills Deployment
claude-mpm skills deploy-github      # Deploy from GitHub
  --collection <name>                # Specific collection
  --toolchain <lang>                 # Filter by language
  --categories <cat>...              # Filter by categories
  --force                            # Force redeploy
  --all                              # Deploy all available

claude-mpm skills list-available     # List GitHub skills
  --collection <name>                # Specific collection
  --verbose                          # Show details by category/toolchain

claude-mpm skills check-deployed     # Check deployed skills status
claude-mpm skills remove <names>...  # Remove deployed skills
  --all                              # Remove all

# Collection Management
claude-mpm skills collection-list             # List all collections
claude-mpm skills collection-add <name> <url> # Add new collection
  --priority <N>                              # Collection priority
claude-mpm skills collection-remove <name>    # Remove collection
claude-mpm skills collection-enable <name>    # Enable collection
claude-mpm skills collection-disable <name>   # Disable collection
claude-mpm skills collection-set-default <name> # Set default collection
```

**Key Features**:
- ✅ **Collection management**: Multiple skill repositories with priorities
- ✅ **Toolchain filtering**: Deploy skills matching detected language
- ✅ **Category-based discovery**: Browse by categories (testing, deployment, etc.)
- ✅ **Default collection**: System-managed vs. custom collections

**Skills Deployer Service** (`src/claude_mpm/services/skills_deployer.py`):
- `deploy_skills()` - Deploy with toolchain/category filters
- `list_available_skills()` - Browse available skills from collections
- `check_deployed_skills()` - Verify deployed skills in ~/.claude/skills/

### 4. Skill Source CLI Commands

**File**: `src/claude_mpm/cli/commands/skill_source.py` (695 lines)

**Current Commands**:

```
claude-mpm skill-source add <url>    # Add skill source
  --priority <0-1000>                # Source priority
  --branch <branch>                  # Git branch (default: main)
  --disabled                         # Add but don't enable
  --test                             # Test only
  --no-test                          # Skip testing

claude-mpm skill-source list         # List configured sources
  --by-priority                      # Sort by priority
  --enabled-only                     # Show only enabled
  --json                             # JSON output

claude-mpm skill-source remove <id>  # Remove source
  --force                            # Skip confirmation

claude-mpm skill-source update [id]  # Update sources
  --force                            # Force sync

claude-mpm skill-source enable <id>  # Enable source
claude-mpm skill-source disable <id> # Disable source

claude-mpm skill-source show <id>    # Show source details
  --skills                           # List skills from source
```

**Parallel Implementation**:
- Nearly identical to `agent-source` commands
- Uses `SkillSourceConfiguration` instead of `AgentSourceConfiguration`
- Same GitHub API testing and sync patterns
- Same priority system and ETag caching

---

## AUTO-DEPLOY-INDEX.md Structure

**File**: `~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/AUTO-DEPLOY-INDEX.md`

### Agent Categorization

**Universal Agents** (Always deployed):
```
Claude MPM Framework:
  - claude-mpm/mpm-agent-manager

Universal:
  - universal/memory-manager
  - universal/research
  - universal/code-analyzer

Documentation:
  - documentation/documentation
  - documentation/ticketing
```

**Language-Specific Detection**:

| Language | Indicator Files | Core Agents | Optional Agents |
|----------|----------------|-------------|-----------------|
| Python | `pyproject.toml`, `requirements.txt`, `setup.py` | `engineer/backend/python-engineer`, `qa/qa`, `ops/core/ops`, `security/security` | `engineer/backend/data-engineer` (if dbt/airflow) |
| JavaScript/TypeScript | `package.json` | `qa/qa`, `ops/core/ops`, `security/security` | Conditional on dependencies (see below) |
| Rust | `Cargo.toml` | `engineer/backend/rust-engineer`, `qa/qa`, `ops/core/ops`, `security/security` | `engineer/mobile/tauri-engineer` (if `src-tauri/`) |
| Go | `go.mod`, `go.sum` | `engineer/backend/golang-engineer`, `qa/qa`, `ops/core/ops`, `security/security` | |
| Java | `pom.xml`, `build.gradle` | `engineer/backend/java-engineer`, `qa/qa`, `ops/core/ops`, `security/security` | |
| Ruby | `Gemfile` | `engineer/backend/ruby-engineer`, `qa/qa`, `ops/core/ops`, `security/security` | |
| PHP | `composer.json` | `engineer/backend/php-engineer`, `qa/qa`, `ops/core/ops`, `security/security` | |
| Dart/Flutter | `pubspec.yaml` | `engineer/mobile/dart-engineer`, `qa/qa`, `ops/core/ops` | |

**Framework-Specific Detection** (JavaScript/TypeScript):

| Framework | Dependency | Agents |
|-----------|-----------|---------|
| React | `"react"` | `engineer/frontend/react-engineer`, `qa/web-qa` |
| Next.js | `"next"` | `engineer/frontend/nextjs-engineer`, `qa/web-qa`, `ops/platform/vercel-ops` (if `vercel.json`) |
| Svelte | `"svelte"` | `engineer/frontend/svelte-engineer`, `qa/web-qa` |
| Node.js Backend | `"express"`, `"fastify"`, `"koa"` | `engineer/backend/javascript-engineer`, `qa/api-qa` |
| TypeScript | `"typescript"` in devDeps | `engineer/data/typescript-engineer` |

**Platform-Specific Detection**:

| Platform | Indicator Files | Agents |
|----------|----------------|---------|
| Vercel | `vercel.json` | `ops/platform/vercel-ops` |
| GCP | `cloudbuild.yaml`, `app.yaml` | `ops/platform/gcp-ops` |
| Clerk Auth | `.env` with `CLERK_*` | `ops/platform/clerk-ops` |
| Docker | `Dockerfile`, `docker-compose.yml` | `ops/platform/local-ops` |
| PM2 | `ecosystem.config.js` | `ops/platform/local-ops` |

**Specialized Detection**:

| Specialization | Indicator Files | Agents |
|----------------|----------------|---------|
| Data Engineering | `dbt_project.yml`, `airflow.cfg`, `prefect.yaml` | `engineer/data/data-engineer` |
| Image Processing | `sharp`, `Pillow` dependencies | `engineer/specialized/imagemagick` |
| Build Optimization | `Makefile`, `webpack.config.js`, `vite.config.ts` | `engineer/specialized/agentic-coder-optimizer` |
| Version Control | `.git/` directory | `ops/tooling/version-control` |

### Detection Priority

```
1. Universal agents (always deployed first)
2. Language-specific agents (based on primary language)
3. Framework-specific agents (based on dependencies)
4. Platform-specific agents (based on deployment targets)
5. Specialized agents (based on specific tools/libraries)
```

### Preset Categories (Inferred from AUTO-DEPLOY-INDEX.md)

**Minimal Preset** (Micro Projects):
```
- universal/memory-manager
- universal/research
- documentation/documentation
- engineer/{detected-language}
- qa/qa
- ops/core/ops
```

**Standard Preset** (Most Projects):
```
All detected agents based on AUTO-DEPLOY-INDEX.md rules
```

**Full Preset** (Enterprise Projects):
```
All detected agents + specialized agents:
- engineer/specialized/refactoring-engineer
- engineer/specialized/agentic-coder-optimizer
- universal/product-owner
```

---

## Proposed New CLI Command Tree

### Design Decision: Unified vs. Parallel Commands

**Recommendation**: **Parallel Commands** (Option B)

**Rationale**:
1. ✅ **Backward compatibility**: Existing `agent-source` and `skill-source` remain unchanged
2. ✅ **Gradual adoption**: Users can migrate at their own pace
3. ✅ **Clear separation**: Agents vs. skills have different deployment targets (`.claude/agents/` vs `.claude/skills/`)
4. ✅ **Less disruptive**: No major refactoring of existing codebase

**Trade-offs**:
- ❌ **Duplicated commands**: `agent-source` and `skill-source` have nearly identical interfaces
- ❌ **Cognitive load**: Users must remember which command set applies

### Proposed Agent Commands

```bash
# === SOURCE MANAGEMENT (Existing - No Changes) ===
claude-mpm agent-source add <url> [--priority N] [--subdirectory PATH]
claude-mpm agent-source list [--by-priority] [--enabled-only] [--json]
claude-mpm agent-source remove <id> [--force]
claude-mpm agent-source update [id] [--force]
claude-mpm agent-source enable <id>
claude-mpm agent-source disable <id>
claude-mpm agent-source show <id> [--agents]

# === DISCOVERY & BROWSING (NEW) ===
claude-mpm agents discover                     # Discover agents from all sources
  --source <id>                                # Filter by specific source
  --category <category>                        # Filter by category (see categories below)
  --language <lang>                            # Filter by language (python, javascript, rust, etc.)
  --framework <framework>                      # Filter by framework (react, nextjs, django, etc.)
  --platform <platform>                        # Filter by platform (vercel, gcp, docker, etc.)
  --specialization <spec>                      # Filter by specialization (data, security, mobile, etc.)
  --format table|json|simple                   # Output format
  --verbose                                    # Show descriptions and metadata

# Categories for --category filter:
#   - universal (memory-manager, research, code-analyzer)
#   - engineer (all engineering agents)
#   - engineer/backend (python, rust, golang, java, ruby, php, javascript)
#   - engineer/frontend (react, nextjs, svelte, web-ui)
#   - engineer/mobile (dart, tauri)
#   - engineer/data (data-engineer, typescript-engineer)
#   - engineer/specialized (refactoring, optimization, imagemagick)
#   - qa (qa, api-qa, web-qa)
#   - ops (core ops, platform ops, tooling)
#   - ops/platform (vercel, gcp, clerk, local)
#   - ops/tooling (version-control)
#   - documentation (documentation, ticketing)
#   - security (security)

# === PRESET DEPLOYMENT (NEW) ===
claude-mpm agents deploy --preset <preset-name> [--dry-run]

# Available Presets:
#   minimal       - 6 core agents (engineer, documentation, qa, research, ops, ticketing)
#   auto          - Auto-detect toolchain + deploy matching agents
#   python-dev    - Python backend development stack
#   python-fullstack - Python backend + React frontend
#   javascript-backend - Node.js/Express backend development
#   react-dev     - React frontend development
#   nextjs-fullstack - Next.js full-stack development
#   rust-dev      - Rust systems development
#   golang-dev    - Go backend development
#   java-dev      - Java/Spring Boot development
#   mobile-flutter - Flutter mobile development
#   data-eng      - Data engineering (dbt, airflow, etc.)

# === CUSTOM SELECTION (NEW) ===
claude-mpm agents select                       # Interactive multi-select UI
claude-mpm agents select --agent <agent-path>... # Select specific agents
  --agent engineer/backend/python-engineer
  --agent qa/qa
  --agent ops/core/ops

# === DEPLOYMENT (Enhanced) ===
claude-mpm agents deploy                       # Deploy selected agents
  --preset <preset-name>                       # Deploy by preset
  --agent <agent-path>...                      # Deploy specific agents
  --from-selection                             # Deploy from previous 'select'
  --force                                      # Force redeploy
  --dry-run                                    # Preview deployment

# === AUTO-CONFIGURATION (Existing - Enhanced) ===
claude-mpm agents detect                       # Detect project toolchain
  --path <project-path>                        # Project to analyze (default: .)
  --output json|yaml|table                     # Output format
  --save-config                                # Save to .claude-mpm/agent-config.json

claude-mpm agents recommend                    # Recommend agents based on toolchain
  --path <project-path>                        # Project to analyze (default: .)
  --preset minimal|standard|full               # Recommendation level
  --output json|yaml|table                     # Output format

claude-mpm agents auto-deploy                  # Detect + deploy in one command
  --path <project-path>                        # Project to analyze (default: .)
  --preset standard                            # Deployment level (minimal|standard|full)
  --dry-run                                    # Preview without deploying
  --interactive                                # Interactive confirmation

# === EXISTING COMMANDS (No Changes) ===
claude-mpm agents list [--system|--deployed|--by-tier]
claude-mpm agents view <name>
claude-mpm agents fix <name> [--dry-run] [--all]
claude-mpm agents deps-check [agent]
claude-mpm agents deps-install [agent]
claude-mpm agents deps-list
claude-mpm agents deps-fix
claude-mpm agents cleanup
claude-mpm agents cleanup-orphaned
claude-mpm agents create [--interactive]
claude-mpm agents edit <id> [--interactive]
claude-mpm agents delete <id>... [--force]
claude-mpm agents manage
claude-mpm agents configure [--enable/--disable]
```

### Proposed Skill Commands

```bash
# === SOURCE MANAGEMENT (Existing - No Changes) ===
claude-mpm skill-source add <url> [--priority N] [--branch BRANCH]
claude-mpm skill-source list [--by-priority] [--enabled-only] [--json]
claude-mpm skill-source remove <id> [--force]
claude-mpm skill-source update [id] [--force]
claude-mpm skill-source enable <id>
claude-mpm skill-source disable <id>
claude-mpm skill-source show <id> [--skills]

# === DISCOVERY & BROWSING (NEW - Align with agents) ===
claude-mpm skills discover                     # Discover skills from all sources
  --source <id>                                # Filter by specific source
  --category <category>                        # Filter by category
  --toolchain <lang>                           # Filter by language
  --format table|json|simple                   # Output format
  --verbose                                    # Show descriptions

# === PRESET DEPLOYMENT (NEW - Align with agents) ===
claude-mpm skills deploy --preset <preset-name> [--dry-run]

# Available Presets:
#   python-dev    - Python development skills
#   javascript-dev - JavaScript/TypeScript skills
#   react-dev     - React development skills
#   nextjs-dev    - Next.js development skills
#   rust-dev      - Rust development skills
#   testing       - Testing and QA skills
#   deployment    - Deployment and ops skills

# === EXISTING COMMANDS (Keep as-is) ===
claude-mpm skills list [--agent NAME] [--category NAME]
claude-mpm skills deploy [--force] [--skills NAMES]
claude-mpm skills validate <name> [--strict]
claude-mpm skills update [--check-only]
claude-mpm skills info <name> [--show-content]
claude-mpm skills config [--scope project|user] [--edit]
claude-mpm skills deploy-github [--collection NAME] [--toolchain LANG]
claude-mpm skills list-available [--collection NAME]
claude-mpm skills check-deployed
claude-mpm skills remove <names>... [--all]
claude-mpm skills collection-list
claude-mpm skills collection-add <name> <url> [--priority N]
claude-mpm skills collection-remove <name>
claude-mpm skills collection-enable <name>
claude-mpm skills collection-disable <name>
claude-mpm skills collection-set-default <name>
```

### Configuration File: `.claude-mpm/agent-config.json`

**Purpose**: Store user selections and preset overrides

```json
{
  "version": "1.0",
  "auto_deploy": true,
  "selected_preset": "python-fullstack",
  "custom_agents": [
    "engineer/backend/python-engineer",
    "engineer/frontend/react-engineer",
    "qa/qa",
    "qa/web-qa",
    "ops/core/ops",
    "security/security"
  ],
  "excluded_agents": [
    "engineer/specialized/refactoring-engineer"
  ],
  "deployment_options": {
    "force": false,
    "skip_dependencies": false,
    "dry_run": false
  },
  "last_auto_detect": {
    "timestamp": "2025-12-01T10:30:00Z",
    "detected_languages": ["python", "javascript"],
    "detected_frameworks": ["fastapi", "react"],
    "detected_platforms": ["vercel", "docker"]
  }
}
```

---

## User Journey Examples

### Example 1: New User - Python Project Auto-Setup

**Scenario**: User starts new Python FastAPI project, wants auto-deployment

```bash
# Step 1: Initialize project with Claude MPM
$ cd my-fastapi-project
$ claude-mpm init

# Step 2: Auto-detect and deploy
$ claude-mpm agents auto-deploy
🔍 Detecting project toolchain...

Detected:
  Languages: Python
  Frameworks: FastAPI
  Build Tools: poetry
  Platforms: Docker

Recommended Preset: python-dev

Agents to deploy (8 total):
  Universal:
    ✓ universal/memory-manager
    ✓ universal/research
    ✓ documentation/documentation
  Engineering:
    ✓ engineer/backend/python-engineer
  QA:
    ✓ qa/qa
    ✓ qa/api-qa
  Ops:
    ✓ ops/core/ops
    ✓ ops/platform/local-ops (Docker detected)
  Security:
    ✓ security/security

Deploy these agents? [Y/n]: y

✅ Deployed 8 agents successfully
💡 Agents are now available in Claude Code

# Step 3: Verify deployment
$ claude-mpm agents list --deployed
📋 Deployed Agents (8):
  ✓ universal/memory-manager
  ✓ universal/research
  ✓ documentation/documentation
  ✓ engineer/backend/python-engineer
  ✓ qa/qa
  ✓ qa/api-qa
  ✓ ops/core/ops
  ✓ ops/platform/local-ops
  ✓ security/security
```

### Example 2: Experienced User - Custom Agent Selection

**Scenario**: User wants specific agents for Next.js project

```bash
# Step 1: Browse available agents
$ claude-mpm agents discover --framework nextjs
📚 Agents from configured sources (5 matching 'nextjs'):

Engineering:
  • engineer/frontend/nextjs-engineer
    Next.js full-stack development specialist
    Source: bobmatnyc/claude-mpm-agents

  • engineer/frontend/react-engineer
    React component development
    Source: bobmatnyc/claude-mpm-agents

QA:
  • qa/web-qa
    Browser testing and E2E automation
    Source: bobmatnyc/claude-mpm-agents

Ops:
  • ops/platform/vercel-ops
    Vercel deployment and configuration
    Source: bobmatnyc/claude-mpm-agents

  • ops/tooling/version-control
    Git operations and workflows
    Source: bobmatnyc/claude-mpm-agents

# Step 2: Interactive selection
$ claude-mpm agents select
🎯 Select agents to deploy:

[ ] Universal
  [x] memory-manager
  [x] research
  [ ] code-analyzer

[x] Engineering
  [x] frontend/nextjs-engineer
  [x] frontend/react-engineer
  [ ] backend/python-engineer

[x] QA
  [x] qa
  [x] web-qa
  [ ] api-qa

[x] Ops
  [x] core/ops
  [x] platform/vercel-ops
  [ ] platform/local-ops

[ ] Security
  [ ] security

[Continue] [Cancel]

✅ Selected 8 agents
💾 Saved selection to .claude-mpm/agent-config.json

# Step 3: Deploy selection
$ claude-mpm agents deploy --from-selection
🚀 Deploying 8 agents...
✅ Deployed 8 agents successfully

# Alternative: Direct deployment
$ claude-mpm agents deploy \
    --agent universal/memory-manager \
    --agent universal/research \
    --agent engineer/frontend/nextjs-engineer \
    --agent engineer/frontend/react-engineer \
    --agent qa/qa \
    --agent qa/web-qa \
    --agent ops/core/ops \
    --agent ops/platform/vercel-ops
```

### Example 3: Team Lead - Preset Deployment

**Scenario**: Team lead wants consistent setup across team

```bash
# Step 1: Add team's custom agent source
$ claude-mpm agent-source add https://github.com/company/team-agents \
    --subdirectory agents \
    --priority 10

🔍 Testing repository access: https://github.com/company/team-agents
✅ Repository accessible
🔍 Testing sync and agent discovery...
✅ Sync successful
   Discovered 12 agents

✅ Added agent source: team-agents
   URL: https://github.com/company/team-agents
   Subdirectory: agents
   Priority: 10
   Status: enabled

# Step 2: Deploy using preset
$ claude-mpm agents deploy --preset python-fullstack --dry-run

🔍 DRY RUN: Preview agent deployment

Preset: python-fullstack

Sources:
  • team-agents (priority: 10)
  • bobmatnyc/claude-mpm-agents (priority: 100)

Agents to deploy (12 total):
  Universal (3):
    ✓ universal/memory-manager (from bobmatnyc)
    ✓ universal/research (from bobmatnyc)
    ✓ universal/code-analyzer (from team-agents) [OVERRIDES bobmatnyc]

  Documentation (2):
    ✓ documentation/documentation (from bobmatnyc)
    ✓ documentation/ticketing (from team-agents) [OVERRIDES bobmatnyc]

  Engineering (3):
    ✓ engineer/backend/python-engineer (from team-agents) [OVERRIDES bobmatnyc]
    ✓ engineer/frontend/react-engineer (from bobmatnyc)
    ✓ engineer/data/typescript-engineer (from team-agents)

  QA (2):
    ✓ qa/qa (from bobmatnyc)
    ✓ qa/web-qa (from bobmatnyc)

  Ops (2):
    ✓ ops/core/ops (from bobmatnyc)
    ✓ ops/platform/vercel-ops (from bobmatnyc)

💡 This is a dry run. Run without --dry-run to deploy.

# Step 3: Deploy for real
$ claude-mpm agents deploy --preset python-fullstack
✅ Deployed 12 agents successfully

# Step 4: Share with team
$ cat .claude-mpm/agent-config.json
{
  "version": "1.0",
  "auto_deploy": true,
  "selected_preset": "python-fullstack",
  "sources": [
    {
      "url": "https://github.com/company/team-agents",
      "subdirectory": "agents",
      "priority": 10
    }
  ]
}

# Team members can now:
$ git clone <repo>
$ cd <repo>
$ claude-mpm agents deploy --from-config
✅ Deployed 12 agents from team configuration
```

### Example 4: Power User - Multi-Source Discovery

**Scenario**: User wants to browse agents from multiple sources

```bash
# Step 1: Add multiple sources
$ claude-mpm agent-source add https://github.com/org1/specialized-agents \
    --priority 50 \
    --subdirectory agents

$ claude-mpm agent-source add https://github.com/org2/data-agents \
    --priority 60

# Step 2: List configured sources
$ claude-mpm agent-source list --by-priority
📚 Configured Agent Sources (3 total):

  ✅ bobmatnyc/claude-mpm-agents (Enabled) [System]
     URL: https://github.com/bobmatnyc/claude-mpm-agents
     Priority: 100

  ✅ specialized-agents (Enabled)
     URL: https://github.com/org1/specialized-agents
     Subdirectory: agents
     Priority: 50

  ✅ data-agents (Enabled)
     URL: https://github.com/org2/data-agents
     Priority: 60

💡 Lower priority number = higher precedence

# Step 3: Discover agents by category
$ claude-mpm agents discover --category engineer/data --verbose
📚 Agents from configured sources (8 matching 'engineer/data'):

Data Engineering (5):
  • engineer/data/data-engineer
    Source: bobmatnyc/claude-mpm-agents (priority: 100)
    Version: 1.2.0
    Description: Data pipeline engineering with dbt, Airflow, Prefect

  • engineer/data/data-engineer
    Source: data-agents (priority: 60) [HIGHER PRIORITY]
    Version: 2.0.0
    Description: Advanced data engineering with Spark, Databricks

  • engineer/data/dbt-engineer
    Source: data-agents (priority: 60)
    Version: 1.0.0
    Description: dbt transformation specialist

  • engineer/data/airflow-engineer
    Source: data-agents (priority: 60)
    Version: 1.0.0
    Description: Apache Airflow orchestration

  • engineer/data/spark-engineer
    Source: data-agents (priority: 60)
    Version: 1.5.0
    Description: Apache Spark data processing

TypeScript (3):
  • engineer/data/typescript-engineer
    Source: bobmatnyc/claude-mpm-agents (priority: 100)
    Version: 1.1.0
    Description: TypeScript development with advanced types

  • engineer/data/typescript-engineer
    Source: specialized-agents (priority: 50) [HIGHEST PRIORITY]
    Version: 2.5.0
    Description: Enterprise TypeScript with monorepo support

  • engineer/data/graphql-engineer
    Source: specialized-agents (priority: 50)
    Version: 1.0.0
    Description: GraphQL schema design and federation

⚠️  Priority Conflicts:
  • engineer/data/data-engineer found in 2 sources
    → data-agents (priority: 60) will be used
  • engineer/data/typescript-engineer found in 2 sources
    → specialized-agents (priority: 50) will be used

# Step 4: Deploy specific agent from specific source
$ claude-mpm agents deploy --agent engineer/data/data-engineer --source data-agents
✅ Deployed engineer/data/data-engineer (v2.0.0) from data-agents

# Step 5: Show agent from specific source
$ claude-mpm agent-source show data-agents --agents
📚 Agent Source: data-agents

  Status: ✅ Enabled
  URL: https://github.com/org2/data-agents
  Priority: 60

  Agents (8):

    - engineer/data/data-engineer
      Version: 2.0.0

    - engineer/data/dbt-engineer
      Version: 1.0.0

    - engineer/data/airflow-engineer
      Version: 1.0.0

    - engineer/data/spark-engineer
      Version: 1.5.0

    - engineer/data/kafka-engineer
      Version: 1.0.0

    - engineer/data/flink-engineer
      Version: 0.9.0

    - qa/data-qa
      Version: 1.2.0

    - ops/data-ops
      Version: 1.1.0
```

---

## Implementation Roadmap

### Phase 1: Discovery & Browsing (Week 1-2)

**Goal**: Enable users to browse available agents from configured sources

**Tasks**:

1. **Create `agents discover` command**
   - File: `src/claude_mpm/cli/commands/agents_discover.py`
   - Use existing `GitSourceManager.list_cached_agents()` for data source
   - Add filtering: `--category`, `--language`, `--framework`, `--platform`, `--source`
   - Output formats: `table` (default), `json`, `simple`
   - Support `--verbose` for descriptions and metadata

2. **Parse AUTO-DEPLOY-INDEX.md for category mappings**
   - File: `src/claude_mpm/services/agents/auto_deploy_index_parser.py`
   - Extract category → agent mappings
   - Extract language/framework → agent mappings
   - Cache parsed data for performance

3. **Add filtering to `GitSourceManager`**
   - Method: `list_cached_agents(repo_identifier=None, filters={})`
   - Support filters: `category`, `language`, `framework`, `platform`
   - Return structured data with source attribution

4. **CLI Parser updates**
   - File: `src/claude_mpm/cli/parsers/agents_parser.py`
   - Add `discover` subcommand with filter arguments
   - Validate filter values against known categories

5. **Testing**
   - Unit tests: `tests/cli/commands/test_agents_discover.py`
   - Integration tests with mock repositories
   - E2E tests with real agent sources

**Deliverables**:
- ✅ `claude-mpm agents discover` works with filters
- ✅ Category filtering based on AUTO-DEPLOY-INDEX.md
- ✅ Source attribution in output
- ✅ JSON/YAML output for scripting

---

### Phase 2: Preset System (Week 3-4)

**Goal**: Enable preset-based deployment (minimal, python-dev, nextjs-fullstack, etc.)

**Tasks**:

1. **Define preset configurations**
   - File: `src/claude_mpm/config/agent_presets.py`
   - Define preset dictionary with agent lists
   - Support dynamic presets based on AUTO-DEPLOY-INDEX.md
   - Example:
     ```python
     PRESETS = {
         "minimal": ["universal/memory-manager", "universal/research", ...],
         "python-dev": lambda: get_python_dev_agents(),
         "nextjs-fullstack": lambda: get_nextjs_fullstack_agents(),
     }
     ```

2. **Create `AgentPresetService`**
   - File: `src/claude_mpm/services/agents/agent_preset_service.py`
   - Method: `get_preset(name) -> List[str]`
   - Method: `list_presets() -> Dict[str, str]`
   - Method: `validate_preset(name) -> bool`
   - Method: `resolve_agents(preset_name, sources) -> List[AgentDefinition]`

3. **Enhance `agents deploy` command**
   - Support `--preset <preset-name>` flag
   - Validate preset name against available presets
   - Show preview of agents to deploy
   - Support `--dry-run` for preview without deployment

4. **CLI Parser updates**
   - Add `--preset` argument to `agents deploy` subcommand
   - Add validation for preset names
   - Integrate with existing deployment logic

5. **Testing**
   - Unit tests: `tests/services/agents/test_agent_preset_service.py`
   - Integration tests for preset deployment
   - E2E tests with different presets

**Deliverables**:
- ✅ `claude-mpm agents deploy --preset <preset-name>` works
- ✅ 8-10 predefined presets (minimal, python-dev, nextjs-fullstack, etc.)
- ✅ Dry-run mode shows preview
- ✅ Preset validation and error messages

---

### Phase 3: Interactive Selection (Week 5-6)

**Goal**: Enable interactive multi-select UI for agent selection

**Tasks**:

1. **Create `agents select` command**
   - File: `src/claude_mpm/cli/commands/agents_select.py`
   - Use `rich` library for interactive UI
   - Tree-based selection by category
   - Support arrow keys navigation
   - Support spacebar to toggle selection
   - Support "a" to select all, "n" to select none
   - Save selection to `.claude-mpm/agent-config.json`

2. **Create selection UI widget**
   - File: `src/claude_mpm/cli/widgets/agent_selector.py`
   - Use `rich.tree.Tree` or `rich.table.Table`
   - Checkbox-style selection
   - Category grouping
   - Show source attribution

3. **Enhance deployment with `--from-selection`**
   - Read selection from `.claude-mpm/agent-config.json`
   - Validate selected agents still available
   - Deploy selected agents

4. **CLI Parser updates**
   - Add `select` subcommand
   - Add `--from-selection` flag to `deploy`
   - Add `--agent` multi-value argument for direct selection

5. **Testing**
   - Unit tests: `tests/cli/commands/test_agents_select.py`
   - Mock interactive UI for automated testing
   - Integration tests with selection persistence

**Deliverables**:
- ✅ `claude-mpm agents select` interactive UI works
- ✅ Selection saved to configuration file
- ✅ `claude-mpm agents deploy --from-selection` works
- ✅ Direct selection via `--agent` works

---

### Phase 4: Auto-Deploy Integration (Week 7-8)

**Goal**: Integrate AUTO-DEPLOY-INDEX.md logic into auto-deploy

**Tasks**:

1. **Create `AutoDeployIndexService`**
   - File: `src/claude_mpm/services/agents/auto_deploy_index_service.py`
   - Parse AUTO-DEPLOY-INDEX.md
   - Method: `detect_project_type(path) -> ProjectMetadata`
   - Method: `get_recommended_agents(metadata) -> List[str]`
   - Method: `apply_detection_rules(indicators) -> List[str]`

2. **Enhance `ToolchainDetector`**
   - File: `src/claude_mpm/services/agents/toolchain_detector.py`
   - Use AUTO-DEPLOY-INDEX.md detection rules
   - Detect indicator files (pyproject.toml, package.json, etc.)
   - Parse dependencies from package.json, pyproject.toml
   - Detect platform files (vercel.json, Dockerfile, etc.)

3. **Create `agents auto-deploy` command**
   - File: `src/claude_mpm/cli/commands/agents_auto_deploy.py`
   - Combine detect + deploy in one step
   - Support `--preset minimal|standard|full` for deployment level
   - Support `--interactive` for confirmation
   - Support `--dry-run` for preview

4. **Enhance `agents detect` command**
   - Show detection results with category breakdown
   - Support `--save-config` to save detection to config file
   - Show recommended agents based on detection

5. **Testing**
   - Unit tests: `tests/services/agents/test_auto_deploy_index_service.py`
   - Integration tests with sample projects
   - E2E tests for auto-deploy workflow

**Deliverables**:
- ✅ `claude-mpm agents auto-deploy` works
- ✅ AUTO-DEPLOY-INDEX.md rules fully integrated
- ✅ Multi-language project detection
- ✅ Platform and framework detection
- ✅ Interactive confirmation mode

---

### Phase 5: Skills Parity (Week 9-10)

**Goal**: Apply same workflow to skills management

**Tasks**:

1. **Create `skills discover` command**
   - File: `src/claude_mpm/cli/commands/skills_discover.py`
   - Mirror agents discover functionality
   - Filter by `--category`, `--toolchain`, `--source`

2. **Create skill presets**
   - File: `src/claude_mpm/config/skill_presets.py`
   - Define presets: `python-dev`, `javascript-dev`, `testing`, `deployment`
   - Integrate with `SkillDiscoveryService`

3. **Create `skills select` command**
   - File: `src/claude_mpm/cli/commands/skills_select.py`
   - Interactive multi-select UI for skills
   - Save to `.claude-mpm/skill-config.json`

4. **Enhance `skills deploy` command**
   - Support `--preset <preset-name>`
   - Support `--from-selection`
   - Support `--skill <skill-path>...`

5. **Testing**
   - Unit tests for skills discovery and selection
   - Integration tests with skill sources
   - E2E tests for full workflow

**Deliverables**:
- ✅ Skills have same discovery workflow as agents
- ✅ Skills have preset system
- ✅ Skills have interactive selection
- ✅ Full parity with agents workflow

---

### Phase 6: Documentation & Polish (Week 11-12)

**Goal**: Comprehensive documentation and UX improvements

**Tasks**:

1. **User Documentation**
   - File: `docs/user-guide/agents-workflow.md`
   - Complete workflow guide
   - Example scenarios
   - Preset reference
   - Category reference

2. **Developer Documentation**
   - File: `docs/developer/agents-architecture.md`
   - Architecture diagrams
   - Service descriptions
   - Extension points

3. **CLI Help Improvements**
   - Enhanced help messages
   - Examples in help output
   - Better error messages

4. **Migration Guide**
   - File: `docs/migration/agents-v5-workflow.md`
   - Guide for upgrading from old workflow
   - Breaking changes
   - Deprecation timeline

5. **Testing & QA**
   - Full integration test suite
   - Performance testing
   - User acceptance testing

**Deliverables**:
- ✅ Complete user documentation
- ✅ Developer documentation
- ✅ Migration guide
- ✅ Comprehensive test coverage
- ✅ UX polish and error handling

---

## Implementation Priority

**Must-Have (MVP)**:
1. ✅ Phase 1: Discovery & Browsing
2. ✅ Phase 2: Preset System
3. ✅ Phase 4: Auto-Deploy Integration

**Should-Have (v1.0)**:
1. ✅ Phase 3: Interactive Selection
2. ✅ Phase 5: Skills Parity

**Nice-to-Have (v1.1)**:
1. ✅ Phase 6: Documentation & Polish
2. ⚠️ Advanced filtering (regex, OR/AND logic)
3. ⚠️ Agent versioning and updates
4. ⚠️ Diff view before deployment

---

## Key Design Decisions

### 1. Parallel Commands (agent-source vs. skill-source)

**Decision**: Keep separate `agent-source` and `skill-source` commands

**Rationale**:
- ✅ Backward compatibility
- ✅ Clear separation (different deployment targets)
- ✅ Gradual adoption path

**Alternative Considered**: Unified `sources` command
- ❌ Breaking change for existing users
- ❌ More complex implementation
- ❌ Confusion about deployment targets

### 2. AUTO-DEPLOY-INDEX.md as Source of Truth

**Decision**: Parse AUTO-DEPLOY-INDEX.md at runtime for category mappings

**Rationale**:
- ✅ Single source of truth for categorization
- ✅ Easy to update without code changes
- ✅ Community can contribute via GitHub

**Alternative Considered**: Hardcode category mappings in code
- ❌ Requires code changes for updates
- ❌ Less flexible
- ❌ Harder to contribute

### 3. Interactive Selection with rich Library

**Decision**: Use `rich` library for interactive selection UI

**Rationale**:
- ✅ Already a dependency
- ✅ Cross-platform support
- ✅ Beautiful TUI components

**Alternative Considered**: Custom CLI prompts
- ❌ More code to maintain
- ❌ Less polished UI
- ❌ Platform-specific issues

### 4. Preset System Design

**Decision**: Define presets as Python code with dynamic resolution

**Rationale**:
- ✅ Flexible (can be functions)
- ✅ Easy to test
- ✅ Type-safe

**Alternative Considered**: YAML/JSON preset files
- ❌ Less flexible
- ❌ Harder to validate
- ❌ No dynamic resolution

### 5. Configuration File Format

**Decision**: Use JSON for `.claude-mpm/agent-config.json`

**Rationale**:
- ✅ Already using JSON elsewhere
- ✅ Easy to parse and validate
- ✅ Human-readable

**Alternative Considered**: YAML
- ✅ More human-friendly syntax
- ❌ Adds dependency
- ❌ Inconsistent with existing config

---

## Success Metrics

### User Experience
- ⏱️ **Time to first deployment**: < 2 minutes from project init
- 📊 **User satisfaction**: > 90% positive feedback
- 🎯 **Discovery success rate**: Users find desired agents in < 3 steps

### Technical
- ✅ **Test coverage**: > 85% for new code
- ⚡ **Performance**: `agents discover` < 500ms
- 🔧 **Error rate**: < 1% failed deployments

### Adoption
- 📈 **Usage**: > 50% of users adopt new workflow within 3 months
- 📚 **Documentation**: Complete user guide and examples
- 🎓 **Support**: < 5 support tickets per week related to new workflow

---

## Risks & Mitigation

### Risk 1: Breaking Changes

**Risk**: New workflow breaks existing automation

**Mitigation**:
- ✅ Keep existing commands unchanged
- ✅ Add deprecation warnings
- ✅ Provide migration guide
- ✅ Support both workflows during transition period (6 months)

### Risk 2: Performance

**Risk**: Parsing AUTO-DEPLOY-INDEX.md on every command is slow

**Mitigation**:
- ✅ Cache parsed data
- ✅ Invalidate cache on file modification
- ✅ Lazy loading of category mappings
- ✅ Benchmark and optimize

### Risk 3: Complexity

**Risk**: Too many options confuse users

**Mitigation**:
- ✅ Start with simple defaults
- ✅ Progressive disclosure in help
- ✅ Clear documentation with examples
- ✅ Interactive mode guides users

### Risk 4: Source Conflicts

**Risk**: Multiple sources provide same agent with different content

**Mitigation**:
- ✅ Priority system (lower = higher precedence)
- ✅ Clear warnings about conflicts
- ✅ `--source` flag to force specific source
- ✅ Show source attribution in all outputs

---

## Appendix

### A. Command Cheat Sheet

```bash
# === Quick Start ===
claude-mpm agents auto-deploy                # Detect + deploy in one step
claude-mpm agents deploy --preset minimal   # Deploy core agents only
claude-mpm agents deploy --preset python-dev # Deploy Python stack

# === Discovery ===
claude-mpm agents discover                         # Browse all agents
claude-mpm agents discover --category engineer/backend # Filter by category
claude-mpm agents discover --language python       # Filter by language
claude-mpm agents discover --framework nextjs      # Filter by framework

# === Selection ===
claude-mpm agents select                     # Interactive multi-select
claude-mpm agents select --agent engineer/backend/python-engineer --agent qa/qa

# === Deployment ===
claude-mpm agents deploy --preset <name>     # Deploy by preset
claude-mpm agents deploy --from-selection    # Deploy selected agents
claude-mpm agents deploy --dry-run           # Preview without deploying

# === Source Management ===
claude-mpm agent-source add <url>            # Add new source
claude-mpm agent-source list --by-priority   # List sources
claude-mpm agent-source update               # Sync all sources
claude-mpm agent-source show <id> --agents   # Show agents from source

# === Auto-Configuration ===
claude-mpm agents detect                     # Detect toolchain
claude-mpm agents recommend                  # Get recommendations
claude-mpm agents auto-deploy --interactive  # Detect + confirm + deploy
```

### B. Preset Definitions

**Minimal** (6 agents):
- universal/memory-manager
- universal/research
- documentation/documentation
- engineer/{detected-language}
- qa/qa
- ops/core/ops

**Python-Dev** (8 agents):
- All from Minimal +
- engineer/backend/python-engineer
- qa/api-qa
- ops/platform/local-ops (if Docker)
- security/security

**Python-Fullstack** (12 agents):
- All from Python-Dev +
- engineer/frontend/react-engineer
- qa/web-qa
- ops/platform/vercel-ops (if Vercel)
- documentation/ticketing

**NextJS-Fullstack** (13 agents):
- All from Minimal +
- engineer/frontend/nextjs-engineer
- engineer/frontend/react-engineer
- engineer/data/typescript-engineer
- qa/web-qa
- ops/platform/vercel-ops
- security/security

**Rust-Dev** (7 agents):
- All from Minimal +
- engineer/backend/rust-engineer
- security/security

**Data-Engineering** (10 agents):
- All from Minimal +
- engineer/backend/python-engineer
- engineer/data/data-engineer
- qa/data-qa
- ops/data-ops

**Full** (20+ agents):
- All detected agents based on AUTO-DEPLOY-INDEX.md
- All specialized agents
- All platform agents

### C. Category Reference

**Universal**:
- universal/memory-manager
- universal/research
- universal/code-analyzer

**Documentation**:
- documentation/documentation
- documentation/ticketing

**Engineer/Backend**:
- engineer/backend/python-engineer
- engineer/backend/rust-engineer
- engineer/backend/golang-engineer
- engineer/backend/java-engineer
- engineer/backend/ruby-engineer
- engineer/backend/php-engineer
- engineer/backend/javascript-engineer

**Engineer/Frontend**:
- engineer/frontend/react-engineer
- engineer/frontend/nextjs-engineer
- engineer/frontend/svelte-engineer
- engineer/frontend/web-ui

**Engineer/Mobile**:
- engineer/mobile/dart-engineer
- engineer/mobile/tauri-engineer

**Engineer/Data**:
- engineer/data/data-engineer
- engineer/data/typescript-engineer

**Engineer/Specialized**:
- engineer/specialized/refactoring-engineer
- engineer/specialized/agentic-coder-optimizer
- engineer/specialized/imagemagick

**QA**:
- qa/qa
- qa/api-qa
- qa/web-qa
- qa/data-qa

**Ops/Core**:
- ops/core/ops

**Ops/Platform**:
- ops/platform/vercel-ops
- ops/platform/gcp-ops
- ops/platform/clerk-ops
- ops/platform/local-ops

**Ops/Tooling**:
- ops/tooling/version-control

**Security**:
- security/security

---

## Summary

This research provides a comprehensive analysis of the current agents/skills CLI structure and proposes a new workflow that:

1. ✅ **Maintains backward compatibility** with existing commands
2. ✅ **Integrates AUTO-DEPLOY-INDEX.md** for rich categorization
3. ✅ **Provides discovery workflow** for browsing available agents
4. ✅ **Enables preset-based deployment** for common scenarios
5. ✅ **Supports interactive selection** for custom configurations
6. ✅ **Achieves skills parity** with same workflow for both agents and skills

The proposed implementation roadmap spans 12 weeks across 6 phases, with clear deliverables and success metrics. The design prioritizes user experience while maintaining the flexibility needed for power users and team deployments.

**Next Steps**:
1. Review and approve proposed command structure
2. Begin Phase 1 implementation (Discovery & Browsing)
3. Create detailed technical specifications for each phase
4. Set up project board for tracking implementation progress

---

**Research Complete**
**Saved to**: `/Users/masa/Projects/claude-mpm/docs/research/agents-skills-cli-structure-research-2025-12-01.md`
