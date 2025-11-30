# Single-Tier Agent System

Complete guide to Claude MPM's new Git-based, single-tier agent system.

## Table of Contents

- [Overview](#overview)
- [Key Concepts](#key-concepts)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [Using Agent Sources](#using-agent-sources)
- [Deploying Agents](#deploying-agents)
- [Custom-Only Mode](#custom-only-mode)
- [Migration from 4-Tier System](#migration-from-4-tier-system)
- [Troubleshooting](#troubleshooting)
- [Examples](#examples)
- [CLI Reference](#cli-reference)
- [FAQ](#faq)

## Overview

Claude MPM's new single-tier agent system simplifies agent management by replacing the complex 4-tier hierarchy with a streamlined Git-based approach. All agents come from Git repositories and deploy to a single location: `.claude/agents/`.

### Why Single-Tier?

**Old System (4-tier)** was complex:
```
PROJECT > REMOTE > USER > SYSTEM
├─ .claude-mpm/agents/      (project agents)
├─ ~/.claude-mpm/cache/     (remote cached agents)
├─ ~/.claude-mpm/agents/    (user agents, DEPRECATED)
└─ System templates         (embedded in package)
```

**New System (single-tier)** is simple:
```
Git Sources → .claude/agents/ (single deployment target)
└─ Priority-based conflict resolution
  └─ All sources equal, priority determines precedence
```

### Key Benefits

- **Simpler**: One deployment location, clear precedence rules
- **Flexible**: Add unlimited Git repositories as sources
- **Transparent**: All agents come from Git with full version history
- **Efficient**: ETag-based caching reduces bandwidth by ~95%
- **Automatic**: System repository syncs on startup with zero configuration

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Claude MPM Startup                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│           Git Source Manager (New in v5.0)                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  1. Load Configuration                                │   │
│  │     - AgentSourceConfiguration                        │   │
│  │     - ~/.claude-mpm/config/agent_sources.yaml        │   │
│  └──────────────────────────────────────────────────────┘   │
│                         │                                    │
│                         ▼                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  2. Sync Git Repositories                             │   │
│  │     - System repo: bobmatnyc/claude-mpm-agents       │   │
│  │     - Custom repos: User-defined                      │   │
│  │     - ETag-based HTTP caching                         │   │
│  └──────────────────────────────────────────────────────┘   │
│                         │                                    │
│                         ▼                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  3. Deploy Agents                                     │   │
│  │     - Priority-based resolution                       │   │
│  │     - Copy to .claude/agents/                         │   │
│  │     - Selection modes: all/minimal/auto               │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Key Concepts

### Git-Based Agent Sources

Agents are stored in Git repositories as Markdown files with YAML frontmatter. This provides:

- **Version Control**: Full history and change tracking
- **Collaboration**: Easy to share and contribute agents
- **Validation**: Markdown format with structured metadata
- **Distribution**: Simple HTTP access via GitHub

**Repository Structure Example**:
```
claude-mpm-agents/
└── agents/
    ├── engineer.md
    ├── documentation.md
    ├── qa.md
    ├── research.md
    └── ops.md
```

### Single-Tier Deployment

All agents deploy to **one location**: `.claude/agents/` in your project directory.

**Benefits**:
- No complex precedence rules
- Easy to inspect what's deployed
- Clear project-level agent configuration
- Consistent behavior across environments

### Agent Source Priority

When multiple repositories provide the same agent, **priority determines which version is used**:

- **Lower number = Higher precedence**
- **Default system repository has priority 100**
- **Custom repositories can override (priority < 100) or supplement (priority > 100)**

**Priority Ranges**:
- `0-49`: **Override system agents** (custom implementations)
- `50-99`: **High priority custom agents**
- `100`: **Default system repository**
- `101+`: **Supplementary repositories**

### Subdirectory Support

Point to agents within larger repositories (monorepo support):

```yaml
repositories:
  - url: https://github.com/company/monorepo
    subdirectory: tools/agents  # Only sync this directory
    priority: 100
```

Cache structure: `~/.claude-mpm/cache/remote-agents/company/monorepo/tools/agents/`

## Getting Started

### Quick Start

The system works **automatically** with zero configuration:

```bash
# System repository syncs on first startup
claude-mpm --help

# Check which agents are available
claude-mpm agents available

# Deploy all agents (default behavior)
claude-mpm agents deploy-all

# Deploy minimal configuration (6 core agents)
claude-mpm agents deploy-minimal

# Auto-detect toolchain and deploy matching agents
claude-mpm agents deploy-auto
```

### Default Behavior

Without configuration, Claude MPM:
1. **Syncs** system repository: `bobmatnyc/claude-mpm-agents`
2. **Caches** to: `~/.claude-mpm/cache/remote-agents/`
3. **Deploys** to: `.claude/agents/`
4. **Includes** all available agents

### Adding Custom Repositories

```bash
# Add your company's agent repository
claude-mpm source add https://github.com/mycompany/agents --priority 50

# Sync immediately
claude-mpm source sync mycompany/agents

# Deploy agents
claude-mpm agents deploy-all
```

## Configuration

### Default Configuration

No configuration file is required. The system uses defaults:

- **System Repository**: `https://github.com/bobmatnyc/claude-mpm-agents/agents`
- **Cache Directory**: `~/.claude-mpm/cache/remote-agents/`
- **Deployment Directory**: `.claude/agents/`
- **Selection Mode**: Deploy all agents

### Custom Configuration

Create `~/.claude-mpm/config/agent_sources.yaml`:

```yaml
# Disable default system repository (optional)
disable_system_repo: false

# Add custom repositories
repositories:
  # High priority - overrides system agents
  - url: https://github.com/mycompany/critical-agents
    subdirectory: null
    enabled: true
    priority: 10

  # Normal priority - supplements system agents
  - url: https://github.com/mycompany/custom-agents
    subdirectory: agents
    enabled: true
    priority: 90

  # Low priority - fallback agents
  - url: https://github.com/community/contrib-agents
    subdirectory: null
    enabled: true
    priority: 150
```

### Configuration Fields

**`disable_system_repo`** (boolean, default: `false`)
- If `true`, don't include default system repository
- Requires at least one custom repository
- Use for corporate environments or custom-only setups

**`repositories`** (list of repository configurations)
Each repository has:

- **`url`** (string, required): GitHub repository URL
  - Format: `https://github.com/owner/repo`
  - Must be a valid GitHub URL

- **`subdirectory`** (string, optional): Subdirectory within repository
  - Use for monorepo structures
  - Example: `tools/agents`, `backend/agents`
  - Must be relative path (no leading `/`)

- **`enabled`** (boolean, default: `true`)
  - If `false`, repository is ignored
  - Use to temporarily disable sources

- **`priority`** (integer, default: `100`)
  - Lower number = higher precedence
  - Range: `0-1000` (values > 1000 trigger warning)
  - System repository has priority `100`

## Using Agent Sources

### Managing Repositories

#### List Configured Sources

```bash
# Show enabled repositories
claude-mpm source list

# Show all repositories (including disabled)
claude-mpm source list --all

# Example output:
# ┌─────────────────────────────┬──────────┬─────────┬─────────────┐
# │ Repository                  │ Priority │ Enabled │ Last Synced │
# ├─────────────────────────────┼──────────┼─────────┼─────────────┤
# │ bobmatnyc/claude-mpm-agents │ 100      │ Yes     │ 2025-11-30  │
# │ mycompany/agents            │ 50       │ Yes     │ 2025-11-30  │
# └─────────────────────────────┴──────────┴─────────┴─────────────┘
```

#### Add Repository

```bash
# Add repository with default priority (100)
claude-mpm source add https://github.com/mycompany/agents

# Add with custom priority (override system agents)
claude-mpm source add https://github.com/mycompany/agents --priority 50

# Add monorepo subdirectory
claude-mpm source add https://github.com/company/monorepo \
  --subdirectory tools/agents \
  --priority 100
```

#### Remove Repository

```bash
# Remove by repository identifier
claude-mpm source remove mycompany/agents

# Remove with subdirectory
claude-mpm source remove company/monorepo/tools/agents
```

#### Enable/Disable Repository

```bash
# Temporarily disable repository
claude-mpm source disable mycompany/agents

# Re-enable repository
claude-mpm source enable mycompany/agents
```

#### Set Repository Priority

```bash
# Change priority (lower = higher precedence)
claude-mpm source set-priority mycompany/agents 50

# Give highest precedence
claude-mpm source set-priority mycompany/critical-agents 10

# Lower precedence than system
claude-mpm source set-priority community/contrib 150
```

#### Sync Repositories

```bash
# Sync all enabled repositories
claude-mpm source sync

# Sync specific repository
claude-mpm source sync mycompany/agents

# Force re-download (bypass ETag cache)
claude-mpm source sync --force

# Force sync specific repository
claude-mpm source sync mycompany/agents --force
```

#### Get Repository Information

```bash
# Show repository details
claude-mpm source info mycompany/agents

# Example output:
# Repository: mycompany/agents
# URL: https://github.com/mycompany/agents
# Priority: 50
# Enabled: Yes
# Last Synced: 2025-11-30 10:30:00
# Cache Path: ~/.claude-mpm/cache/remote-agents/mycompany/agents
# Agents Available: 12
```

### Repository Priority System

Priority determines which agent version is used when multiple sources provide the same agent.

**Priority Rules**:
1. **Lower number = higher precedence**
2. **System repository defaults to priority 100**
3. **Ties are broken by configuration order**

**Common Priority Patterns**:

```yaml
# Override specific agents (custom implementations)
- url: https://github.com/company/custom-engineer
  priority: 10  # Highest precedence

# High priority agents (quality-assured)
- url: https://github.com/company/qa-agents
  priority: 50

# Default system agents
# (priority 100, automatically included)

# Supplementary agents (optional features)
- url: https://github.com/community/contrib
  priority: 150  # Lowest precedence
```

**Example Conflict Resolution**:

Agent `engineer.md` exists in three repositories:

1. `company/critical-agents` (priority: `10`) ← **WINS**
2. `bobmatnyc/claude-mpm-agents` (priority: `100`)
3. `community/contrib` (priority: `150`)

Result: `engineer.md` from `company/critical-agents` is deployed.

### Subdirectory Support

Use subdirectories to:
- **Point to agents in monorepos**
- **Organize agents in larger repositories**
- **Share single repository across teams**

**Example: Monorepo Structure**

```
company/monorepo/
├── backend/
├── frontend/
└── tools/
    ├── agents/           ← Point here
    │   ├── engineer.md
    │   └── ops.md
    └── scripts/
```

**Configuration**:
```yaml
repositories:
  - url: https://github.com/company/monorepo
    subdirectory: tools/agents
    priority: 100
```

**Cache Path**: `~/.claude-mpm/cache/remote-agents/company/monorepo/tools/agents/`

**Sync URL**: `https://raw.githubusercontent.com/company/monorepo/main/tools/agents/`

## Deploying Agents

### Deploy All Agents (Default)

Deploy **all available agents** from configured sources:

```bash
# Deploy all agents
claude-mpm agents deploy-all

# Preview what would be deployed (dry-run)
claude-mpm agents deploy-all --dry-run

# Force re-sync before deployment
claude-mpm agents deploy-all --force-sync

# Example output:
# Syncing 2 agent sources...
# ✓ bobmatnyc/claude-mpm-agents (12 agents)
# ✓ mycompany/agents (5 agents)
#
# Deploying 17 agents to .claude/agents/...
# ✓ engineer.md (from mycompany/agents, priority 50)
# ✓ documentation.md (from bobmatnyc/claude-mpm-agents)
# ✓ qa.md (from bobmatnyc/claude-mpm-agents)
# ...
#
# Deployment complete: 17 agents deployed
```

### Deploy Minimal Configuration

Deploy exactly **6 core agents** for basic workflow:

```bash
# Deploy minimal agent set
claude-mpm agents deploy-minimal

# Preview first
claude-mpm agents deploy-minimal --dry-run

# Force re-sync
claude-mpm agents deploy-minimal --force-sync
```

**Minimal Agent Set**:
1. **`engineer`** - General implementation and coding
2. **`documentation`** - Documentation creation and updates
3. **`qa`** - Quality assurance and testing
4. **`research`** - Codebase analysis and investigation
5. **`ops`** - Deployment and operations
6. **`ticketing`** - Ticket management and tracking

**Use Cases**:
- Small projects with simple needs
- Getting started with Claude MPM
- Reducing agent count for performance
- Minimalist development workflow

### Deploy Auto-Configure

Automatically detect project toolchain and deploy matching agents:

```bash
# Auto-detect from current directory
claude-mpm agents deploy-auto

# Specify project path
claude-mpm agents deploy-auto --path /path/to/project

# Preview recommendations (dry-run)
claude-mpm agents deploy-auto --dry-run

# Example output:
# Detecting project toolchain...
#
# Detected Toolchain:
# - Languages: Python, JavaScript
# - Frameworks: FastAPI, React
# - Build Tools: Make, Docker, npm
#
# Recommended Agents:
# Core (6): engineer, documentation, qa, research, ops, ticketing
# Python (2): python-engineer, python-ops
# JavaScript (2): react-engineer, frontend-engineer
# Operations (1): local-ops-agent
#
# Total: 11 agents recommended
#
# Deploying to .claude/agents/...
# ✓ 11 agents deployed
```

**Toolchain Detection**:

Auto-configure scans your project for:

**Languages**:
- Python (`.py`, `requirements.txt`, `pyproject.toml`)
- JavaScript (`.js`, `package.json`)
- TypeScript (`.ts`, `tsconfig.json`)
- Go (`.go`, `go.mod`)
- Rust (`.rs`, `Cargo.toml`)
- Java (`.java`, `pom.xml`, `build.gradle`)
- Ruby (`.rb`, `Gemfile`)
- PHP (`.php`, `composer.json`)

**Frameworks**:
- FastAPI (`from fastapi import`)
- Django (`django.conf`, `manage.py`)
- Flask (`from flask import`)
- React (`react`, `"next"` in package.json)
- Next.js (`next.config.js`)
- Express (`express` in package.json)
- Spring Boot (`@SpringBootApplication`)
- Rails (`Gemfile` with `rails`)

**Build Tools**:
- Make (`Makefile`)
- Docker (`Dockerfile`, `docker-compose.yml`)
- npm/yarn (`package.json`)
- pip (`requirements.txt`)
- Gradle (`build.gradle`)
- Maven (`pom.xml`)

**Agent Mapping Examples**:

```
Python + FastAPI → python-engineer, python-ops, ops
React + Next.js → react-engineer, nextjs-engineer, frontend-engineer
Go + Docker → golang-engineer, ops, local-ops-agent
Ruby + Rails → ruby-engineer, rails-engineer, ops
```

### Deploy Specific Agent

```bash
# Deploy single agent by name
claude-mpm agents deploy engineer

# Deploy from specific source
claude-mpm agents deploy python-engineer --source mycompany/agents

# Deploy multiple agents
claude-mpm agents deploy engineer qa documentation
```

### List Available Agents

```bash
# List all available agents from all sources
claude-mpm agents available

# Example output:
# Available Agents (17 total):
#
# From bobmatnyc/claude-mpm-agents (priority: 100):
#   engineer, documentation, qa, research, ops, ticketing,
#   python-engineer, react-engineer, golang-engineer, ...
#
# From mycompany/agents (priority: 50):
#   engineer (override), custom-agent, internal-tools

# Filter by source
claude-mpm agents available --source bobmatnyc/claude-mpm-agents

# Show agent details
claude-mpm agents available --verbose
```

## Custom-Only Mode

Disable the default system repository to use **only your private agents**.

### Configuration

```yaml
# ~/.claude-mpm/config/agent_sources.yaml
disable_system_repo: true

repositories:
  - url: https://github.com/mycompany/private-agents
    priority: 100
    enabled: true
```

### Use Cases

- **Corporate Environments**: Private agents only, no public repos
- **Security Requirements**: Full control over agent sources
- **Custom Implementations**: Complete replacement of system agents
- **Isolated Development**: Test custom agents without system repo

### Requirements

- **At least one custom repository must be configured**
- Custom repository must provide all required agents
- Consider including minimal agent set at minimum

### Setup Workflow

```bash
# 1. Add your private repository
claude-mpm source add https://github.com/mycompany/private-agents --priority 100

# 2. Disable system repository
cat > ~/.claude-mpm/config/agent_sources.yaml << EOF
disable_system_repo: true
repositories:
  - url: https://github.com/mycompany/private-agents
    priority: 100
    enabled: true
EOF

# 3. Sync and deploy
claude-mpm source sync
claude-mpm agents deploy-all

# 4. Verify
claude-mpm agents available
```

## Migration from 4-Tier System

### What Changed

**Old System (4-tier)**:
```
PROJECT > REMOTE > USER > SYSTEM
├─ .claude-mpm/agents/      (project agents, highest priority)
├─ ~/.claude-mpm/cache/     (remote cached agents)
├─ ~/.claude-mpm/agents/    (user agents, DEPRECATED)
└─ System templates         (embedded, lowest priority)
```

**New System (single-tier)**:
```
Git Sources → .claude/agents/ (single deployment target)
└─ Priority-based conflict resolution
  └─ All sources equal, priority determines precedence
```

### Key Differences

| Aspect | Old (4-tier) | New (single-tier) |
|--------|-------------|-------------------|
| **Deployment Target** | 4 locations | 1 location (`.claude/agents/`) |
| **Priority** | Tier-based (PROJECT > REMOTE > USER > SYSTEM) | Priority number (lower = higher) |
| **Configuration** | Complex tier precedence | Simple YAML configuration |
| **System Agents** | Embedded in package | Git repository |
| **User Agents** | `~/.claude-mpm/agents/` | DEPRECATED (use project or Git) |
| **Custom Agents** | Limited to project directory | Unlimited Git repositories |

### Migration Steps

**Good News**: Migration is **automatic** for most users!

1. **Configuration automatically migrates** on first run of v5.0
2. **No action needed** for most users (system repo works automatically)
3. **Custom repositories**: Add via `claude-mpm source add`
4. **User-level agents** (deprecated): Migrate to project-level or Git repository

### Detailed Migration

#### Step 1: Understand Your Current Setup

Check what agents you're using:

```bash
# Before upgrade (v4.x)
ls .claude-mpm/agents/       # Project agents
ls ~/.claude-mpm/agents/     # User agents (if any)
```

#### Step 2: Upgrade to v5.0

```bash
# Upgrade Claude MPM
pip install --upgrade claude-mpm

# Or via Homebrew
brew upgrade claude-mpm
```

#### Step 3: First Run (Automatic Migration)

```bash
# Run any command to trigger migration
claude-mpm --version

# System automatically:
# - Creates AgentSourceConfiguration
# - Syncs system repository
# - Caches to ~/.claude-mpm/cache/remote-agents/
```

#### Step 4: Add Custom Repositories (If Needed)

```bash
# Add your custom repository
claude-mpm source add https://github.com/mycompany/agents --priority 50

# Sync immediately
claude-mpm source sync
```

#### Step 5: Migrate User-Level Agents (If Any)

**Option A: Move to Project Level**

```bash
# Copy user agents to project
mkdir -p .claude-mpm/agents/
cp ~/.claude-mpm/agents/*.md .claude-mpm/agents/

# Create Git repository for project agents
cd .claude-mpm
git init
git add agents/
git commit -m "Add project-specific agents"
```

**Option B: Create Custom Repository**

```bash
# Create Git repository for agents
mkdir my-claude-agents
cd my-claude-agents
git init

# Move agents
cp ~/.claude-mpm/agents/*.md .
git add *.md
git commit -m "Initial agent collection"

# Push to GitHub
gh repo create --private
git push origin main

# Add to Claude MPM
claude-mpm source add https://github.com/yourusername/my-claude-agents --priority 50
```

#### Step 6: Deploy New Configuration

```bash
# Deploy all agents
claude-mpm agents deploy-all

# Or deploy minimal
claude-mpm agents deploy-minimal

# Or auto-detect
claude-mpm agents deploy-auto
```

#### Step 7: Clean Up (Optional)

```bash
# Remove old user-level agents directory (after verifying new system works)
rm -rf ~/.claude-mpm/agents/

# Note: This directory is DEPRECATED and will be removed in v6.0
```

### Deprecation Notice

**User-level agents** (`~/.claude-mpm/agents/`) are **DEPRECATED**:

- **Current Status**: Still supported in v5.x (warning emitted)
- **Removal**: Will be removed in v6.0.0
- **Timeline**: v6.0 expected in Q2 2026
- **Action Required**: Migrate to project-level or Git repository

**Why Deprecated?**:
- Complexity: Adds unnecessary tier to precedence
- Confusion: Users unclear about tier precedence
- Limited: Not shareable or versioned
- Redundant: Git sources provide better solution

## Troubleshooting

### Agents Not Appearing

**Symptom**: Deployed agents don't show up in Claude Desktop

**Possible Causes**:
1. Agents not deployed to correct directory
2. Claude Desktop not restarted
3. Sync failed
4. Cache corruption

**Solutions**:

```bash
# 1. Check sources configured
claude-mpm source list

# 2. Force re-sync
claude-mpm source sync --force

# 3. Check cache directory
ls ~/.claude-mpm/cache/remote-agents/

# 4. Check deployment directory
ls .claude/agents/

# 5. Re-deploy agents
claude-mpm agents deploy-all --force-sync

# 6. Verify agent content
cat .claude/agents/engineer.md | head -20

# 7. Restart Claude Desktop
```

### Priority Conflicts

**Symptom**: Wrong agent version is deployed (not the one you expected)

**Cause**: Priority ordering unclear

**Solution**: Check priority ordering:

```bash
# List sources with priorities
claude-mpm source list

# Example output:
# ┌─────────────────────────────┬──────────┐
# │ Repository                  │ Priority │
# ├─────────────────────────────┼──────────┤
# │ company/critical-agents     │ 10       │ ← Highest precedence
# │ company/custom-agents       │ 50       │
# │ bobmatnyc/claude-mpm-agents │ 100      │
# │ community/contrib-agents    │ 150      │ ← Lowest precedence
# └─────────────────────────────┴──────────┘

# Adjust priorities as needed
claude-mpm source set-priority company/custom-agents 90
```

**Remember**: Lower priority number = higher precedence

### Sync Failures

**Symptom**: Source sync errors or hangs

**Common Causes**:
- Network issues
- Invalid repository URL
- Repository doesn't exist
- Subdirectory path wrong
- GitHub API rate limiting
- Authentication required for private repos

**Solutions**:

```bash
# 1. Check repository info
claude-mpm source info mycompany/agents

# 2. Test URL manually
curl -I https://github.com/mycompany/agents

# 3. Verify subdirectory exists in repo
curl -I https://raw.githubusercontent.com/mycompany/agents/main/tools/agents/

# 4. Check network connectivity
ping github.com

# 5. Check GitHub API rate limit
curl -I https://api.github.com/rate_limit

# 6. For private repos, check authentication
gh auth status

# 7. Try force sync
claude-mpm source sync mycompany/agents --force

# 8. Check logs for detailed error
claude-mpm --debug source sync mycompany/agents 2>&1 | tail -50
```

### Auto-Configure Not Finding Agents

**Symptom**: Auto-configure doesn't recommend expected agents

**Possible Causes**:
1. Toolchain not detected correctly
2. Agents not available in sources
3. Agent naming mismatch

**Solutions**:

```bash
# 1. Check available agents
claude-mpm agents available

# 2. Ensure sources are synced
claude-mpm source sync --force

# 3. Check what toolchain was detected (use --dry-run)
claude-mpm agents deploy-auto --dry-run

# 4. Manually verify toolchain detection
# Check for expected files:
ls requirements.txt package.json Dockerfile Makefile

# 5. Deploy specific agents manually if needed
claude-mpm agents deploy python-engineer react-engineer

# 6. Check agent naming in your sources
ls ~/.claude-mpm/cache/remote-agents/*/
```

### Cache Issues

**Symptom**: Old agents appear even after sync

**Cause**: Cache corruption or stale data

**Solution**: Clear cache and re-sync:

```bash
# 1. Clear all cached agents
rm -rf ~/.claude-mpm/cache/remote-agents/

# 2. Force re-sync
claude-mpm source sync --force

# 3. Re-deploy
claude-mpm agents deploy-all

# 4. Verify
claude-mpm agents available
```

### Configuration Errors

**Symptom**: Error loading configuration file

**Cause**: Invalid YAML syntax or configuration values

**Solution**: Validate configuration:

```bash
# 1. Check YAML syntax
cat ~/.claude-mpm/config/agent_sources.yaml | python3 -m yaml

# 2. Validate configuration
# (Run claude-mpm with debug logging)
claude-mpm --debug source list

# 3. Fix common YAML issues:
# - Incorrect indentation (must be spaces, not tabs)
# - Missing quotes around URLs
# - Invalid priority values (must be integer)

# 4. Example valid configuration:
cat > ~/.claude-mpm/config/agent_sources.yaml << 'EOF'
disable_system_repo: false
repositories:
  - url: https://github.com/mycompany/agents
    subdirectory: null
    enabled: true
    priority: 100
EOF

# 5. Verify configuration loads
claude-mpm source list
```

## Examples

### Example 1: Company With Custom Agents

**Scenario**: Acme Corp wants to use system agents plus custom company agents

**Configuration**:

```yaml
# ~/.claude-mpm/config/agent_sources.yaml
disable_system_repo: false  # Keep system agents

repositories:
  # Custom agents override system where they conflict
  - url: https://github.com/acme-corp/agents
    priority: 50  # Higher than system (100)
    enabled: true
```

**Workflow**:

```bash
# Add repository
claude-mpm source add https://github.com/acme-corp/agents --priority 50

# Sync
claude-mpm source sync

# Deploy
claude-mpm agents deploy-all

# Result: Custom engineer.md from acme-corp overrides system engineer.md
# System agents without acme-corp equivalents are included
```

**Outcome**:
- Acme's `engineer.md` deployed (priority 50)
- System's `documentation.md`, `qa.md`, etc. deployed (priority 100)
- Total: Mix of custom and system agents

### Example 2: Monorepo Setup

**Scenario**: Large company with monorepo structure

**Repository Structure**:
```
acme-corp/monorepo/
├── backend/
├── frontend/
└── tools/
    ├── agents/           ← Point here
    │   ├── engineer.md
    │   └── ops.md
    └── scripts/
```

**Configuration**:

```yaml
repositories:
  - url: https://github.com/acme-corp/monorepo
    subdirectory: tools/agents  # Point to subdirectory
    priority: 100
```

**Workflow**:

```bash
# Add monorepo with subdirectory
claude-mpm source add https://github.com/acme-corp/monorepo \
  --subdirectory tools/agents \
  --priority 100

# Sync
claude-mpm source sync

# Check cache path
ls ~/.claude-mpm/cache/remote-agents/acme-corp/monorepo/tools/agents/

# Deploy
claude-mpm agents deploy-all
```

**Cache Path**: `~/.claude-mpm/cache/remote-agents/acme-corp/monorepo/tools/agents/`

**Sync URL**: `https://raw.githubusercontent.com/acme-corp/monorepo/main/tools/agents/`

### Example 3: Private Agents Only

**Scenario**: Security-conscious company wants only private agents

**Configuration**:

```yaml
# ~/.claude-mpm/config/agent_sources.yaml
disable_system_repo: true  # Don't use public system repo

repositories:
  - url: https://github.com/acme-corp/private-agents
    priority: 100
    enabled: true
```

**Workflow**:

```bash
# 1. Ensure private repository has all required agents
# (At minimum: engineer, documentation, qa, research, ops, ticketing)

# 2. Add private repository
claude-mpm source add https://github.com/acme-corp/private-agents --priority 100

# 3. Disable system repository
cat > ~/.claude-mpm/config/agent_sources.yaml << EOF
disable_system_repo: true
repositories:
  - url: https://github.com/acme-corp/private-agents
    priority: 100
    enabled: true
EOF

# 4. Sync and deploy
claude-mpm source sync
claude-mpm agents deploy-all

# 5. Verify only private agents
claude-mpm agents available
# Should show: "From acme-corp/private-agents (priority: 100): ..."
```

**Security Benefits**:
- No external dependencies
- Full control over agent code
- Internal review and approval process
- Compliance with corporate policies

### Example 4: Multi-Team Setup

**Scenario**: Different teams need different agent sets

**Team Structure**:
- **Backend Team**: Python, Go engineers
- **Frontend Team**: React, Next.js engineers
- **DevOps Team**: Operations, infrastructure agents

**Configuration**:

```yaml
repositories:
  # Core agents (all teams)
  - url: https://github.com/company/core-agents
    priority: 50
    enabled: true

  # Backend agents
  - url: https://github.com/company/backend-agents
    subdirectory: agents
    priority: 60
    enabled: true

  # Frontend agents
  - url: https://github.com/company/frontend-agents
    subdirectory: agents
    priority: 60
    enabled: true

  # DevOps agents
  - url: https://github.com/company/devops-agents
    priority: 60
    enabled: true

  # System agents (fallback)
  # (priority 100, automatically included)
```

**Per-Team Workflow**:

```bash
# Backend team member
claude-mpm agents deploy-auto  # Auto-detects Python/Go
# Deploys: core + backend + system

# Frontend team member
claude-mpm agents deploy-auto  # Auto-detects React/Next.js
# Deploys: core + frontend + system

# DevOps team member
claude-mpm agents deploy-all  # All agents
# Deploys: core + backend + frontend + devops + system
```

## CLI Reference

### Source Management Commands

#### `claude-mpm source add`

Add a new agent repository source.

```bash
claude-mpm source add <url> [options]
```

**Arguments**:
- `url`: GitHub repository URL (required)

**Options**:
- `--priority <number>`: Priority (default: 100, lower = higher precedence)
- `--subdirectory <path>`: Subdirectory within repository
- `--disabled`: Add as disabled (don't sync/deploy)

**Examples**:
```bash
claude-mpm source add https://github.com/mycompany/agents
claude-mpm source add https://github.com/mycompany/agents --priority 50
claude-mpm source add https://github.com/company/monorepo --subdirectory tools/agents
```

#### `claude-mpm source remove`

Remove an agent repository source.

```bash
claude-mpm source remove <identifier>
```

**Arguments**:
- `identifier`: Repository identifier (e.g., `owner/repo` or `owner/repo/subdirectory`)

**Examples**:
```bash
claude-mpm source remove mycompany/agents
claude-mpm source remove company/monorepo/tools/agents
```

#### `claude-mpm source list`

List configured agent sources.

```bash
claude-mpm source list [options]
```

**Options**:
- `--all`: Include disabled repositories
- `--verbose`: Show detailed information

**Examples**:
```bash
claude-mpm source list
claude-mpm source list --all
claude-mpm source list --verbose
```

#### `claude-mpm source info`

Show detailed information about a source.

```bash
claude-mpm source info <identifier>
```

**Arguments**:
- `identifier`: Repository identifier

**Examples**:
```bash
claude-mpm source info mycompany/agents
```

#### `claude-mpm source enable`

Enable a disabled repository source.

```bash
claude-mpm source enable <identifier>
```

**Arguments**:
- `identifier`: Repository identifier

**Examples**:
```bash
claude-mpm source enable mycompany/agents
```

#### `claude-mpm source disable`

Disable a repository source.

```bash
claude-mpm source disable <identifier>
```

**Arguments**:
- `identifier`: Repository identifier

**Examples**:
```bash
claude-mpm source disable mycompany/agents
```

#### `claude-mpm source set-priority`

Change repository priority.

```bash
claude-mpm source set-priority <identifier> <priority>
```

**Arguments**:
- `identifier`: Repository identifier
- `priority`: New priority (integer, 0-1000)

**Examples**:
```bash
claude-mpm source set-priority mycompany/agents 50
claude-mpm source set-priority community/contrib 150
```

#### `claude-mpm source sync`

Sync agent sources from Git repositories.

```bash
claude-mpm source sync [identifier] [options]
```

**Arguments**:
- `identifier`: Optional repository identifier (sync all if omitted)

**Options**:
- `--force`: Force re-download (bypass ETag cache)

**Examples**:
```bash
claude-mpm source sync                    # Sync all
claude-mpm source sync mycompany/agents   # Sync specific
claude-mpm source sync --force            # Force all
```

### Agent Deployment Commands

#### `claude-mpm agents deploy-all`

Deploy all available agents from all sources.

```bash
claude-mpm agents deploy-all [options]
```

**Options**:
- `--dry-run`: Preview without deploying
- `--force-sync`: Force re-sync before deployment

**Examples**:
```bash
claude-mpm agents deploy-all
claude-mpm agents deploy-all --dry-run
claude-mpm agents deploy-all --force-sync
```

#### `claude-mpm agents deploy-minimal`

Deploy minimal configuration (6 core agents).

```bash
claude-mpm agents deploy-minimal [options]
```

**Options**:
- `--dry-run`: Preview without deploying
- `--force-sync`: Force re-sync before deployment

**Examples**:
```bash
claude-mpm agents deploy-minimal
claude-mpm agents deploy-minimal --dry-run
```

#### `claude-mpm agents deploy-auto`

Auto-detect toolchain and deploy matching agents.

```bash
claude-mpm agents deploy-auto [options]
```

**Options**:
- `--path <directory>`: Project path (default: current directory)
- `--dry-run`: Preview without deploying
- `--force-sync`: Force re-sync before deployment

**Examples**:
```bash
claude-mpm agents deploy-auto
claude-mpm agents deploy-auto --path /path/to/project
claude-mpm agents deploy-auto --dry-run
```

#### `claude-mpm agents deploy`

Deploy specific agent(s).

```bash
claude-mpm agents deploy <agent-name> [agent-name...] [options]
```

**Arguments**:
- `agent-name`: Agent name(s) to deploy

**Options**:
- `--source <identifier>`: Deploy from specific source

**Examples**:
```bash
claude-mpm agents deploy engineer
claude-mpm agents deploy engineer qa documentation
claude-mpm agents deploy python-engineer --source mycompany/agents
```

#### `claude-mpm agents available`

List available agents from all sources.

```bash
claude-mpm agents available [options]
```

**Options**:
- `--source <identifier>`: Filter by source
- `--verbose`: Show detailed information

**Examples**:
```bash
claude-mpm agents available
claude-mpm agents available --source bobmatnyc/claude-mpm-agents
claude-mpm agents available --verbose
```

## FAQ

### General Questions

**Q: Do I need to configure anything to use the new system?**

A: No! The system works automatically with zero configuration. The default system repository syncs on first startup, and you can immediately deploy agents.

**Q: What happened to the 4-tier system?**

A: It has been replaced by the simpler single-tier system. All agents now deploy to `.claude/agents/` with priority-based conflict resolution instead of tier-based precedence.

**Q: Are my existing agents still supported?**

A: Yes. Project-level agents (`.claude-mpm/agents/`) are fully supported. User-level agents (`~/.claude-mpm/agents/`) are deprecated but still work in v5.x.

**Q: When will user-level agents be removed?**

A: User-level agents will be removed in v6.0.0 (expected Q2 2026). Migrate to project-level or Git repositories before then.

### Configuration Questions

**Q: How do I disable the system repository?**

A: Set `disable_system_repo: true` in `~/.claude-mpm/config/agent_sources.yaml`. You must configure at least one custom repository.

**Q: Can I use multiple custom repositories?**

A: Yes! Add as many repositories as needed with `claude-mpm source add`. Use priority to control precedence.

**Q: What does priority mean?**

A: Lower priority number = higher precedence. If multiple sources provide the same agent, the one with the lowest priority wins.

**Q: What's a good priority for my custom agents?**

A:
- **Override system agents**: `0-49`
- **High priority custom**: `50-99`
- **System agents**: `100` (default)
- **Supplementary agents**: `101+`

**Q: Can I use private GitHub repositories?**

A: Not currently. Private repository support is planned for v5.1. For now, use organization-scoped public repositories or internal Git hosting.

### Deployment Questions

**Q: Which deployment mode should I use?**

A:
- **`deploy-all`**: Default, includes all available agents
- **`deploy-minimal`**: Small projects, 6 core agents only
- **`deploy-auto`**: Let Claude MPM detect your toolchain and recommend agents

**Q: How do I add a language-specific agent?**

A: Use `deploy-auto` to automatically detect your toolchain, or `deploy` to manually add specific agents:
```bash
claude-mpm agents deploy python-engineer react-engineer
```

**Q: Can I mix system and custom agents?**

A: Yes! This is the default behavior. System agents provide base functionality, and custom agents supplement or override.

**Q: What happens if two sources provide the same agent?**

A: The agent from the source with **lower priority** (higher precedence) is deployed. Ties are broken by configuration order.

### Sync Questions

**Q: How often are agents synced?**

A: Agents sync automatically on Claude MPM startup. You can manually sync with `claude-mpm source sync`.

**Q: Does syncing use a lot of bandwidth?**

A: No. ETag-based caching reduces bandwidth by ~95% after the first sync. Typical sync completes in 100-200ms.

**Q: What happens if sync fails?**

A: Claude MPM uses cached agents from previous sync. The system continues working offline with locally cached agents.

**Q: How do I force a fresh download?**

A: Use `claude-mpm source sync --force` to bypass ETag cache and re-download all agents.

### Troubleshooting Questions

**Q: Agents aren't showing up in Claude Desktop. What do I check?**

A:
1. Run `claude-mpm agents available` to verify agents are synced
2. Run `ls .claude/agents/` to verify agents are deployed
3. Restart Claude Desktop
4. Try `claude-mpm agents deploy-all --force-sync`

**Q: The wrong agent version is being deployed. How do I fix this?**

A: Check priority with `claude-mpm source list`. Lower priority = higher precedence. Adjust with `claude-mpm source set-priority`.

**Q: Sync is failing with network errors. What should I do?**

A:
1. Check network: `ping github.com`
2. Check URL: `claude-mpm source info <identifier>`
3. Check GitHub status: `https://www.githubstatus.com`
4. Use cached agents (sync failure doesn't block usage)

**Q: Auto-configure isn't detecting my toolchain. Why?**

A: Check that your project has recognizable marker files:
- Python: `requirements.txt`, `pyproject.toml`
- JavaScript: `package.json`
- Docker: `Dockerfile`
- Make: `Makefile`

Use `claude-mpm agents deploy-auto --dry-run` to see what's detected.

### Advanced Questions

**Q: Can I create my own agent repository?**

A: Yes! Create a Git repository with Markdown agent files and add it with `claude-mpm source add`. See [Creating Custom Agents](../developer/custom-agents.md) for details.

**Q: Can I use agents from a subdirectory in a monorepo?**

A: Yes! Use the `--subdirectory` option:
```bash
claude-mpm source add https://github.com/company/monorepo --subdirectory tools/agents
```

**Q: How does ETag caching work?**

A: Claude MPM stores the HTTP ETag from GitHub for each agent file. On subsequent syncs, it sends "If-None-Match" headers. GitHub returns "304 Not Modified" if unchanged, saving bandwidth.

**Q: Where are agents cached?**

A: `~/.claude-mpm/cache/remote-agents/{owner}/{repo}/{subdirectory}/`

**Q: Can I inspect the cached agents?**

A: Yes! They're Markdown files:
```bash
ls ~/.claude-mpm/cache/remote-agents/
cat ~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/agents/engineer.md
```

---

## Related Documentation

- **[Agent Synchronization Guide](agent-synchronization.md)** - Detailed sync mechanism
- **[Configuration Reference](../reference/configuration.md)** - Complete configuration options
- **[Agent Sources API](../reference/agent-sources-api.md)** - Technical API reference
- **[Single-Tier Design](../architecture/single-tier-design.md)** - Architecture deep-dive
- **[Creating Custom Agents](../developer/custom-agents.md)** - Build your own agents

---

**Need Help?**

- Run `claude-mpm doctor` for diagnostics
- Check [Troubleshooting Guide](../user/troubleshooting.md)
- Report issues: [GitHub Issues](https://github.com/bobmatnyc/claude-mpm/issues)
