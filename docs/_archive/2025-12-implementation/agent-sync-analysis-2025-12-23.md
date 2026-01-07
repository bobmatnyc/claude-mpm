# Agent Repository Sync Analysis

**Date**: 2025-12-23
**Main Repo Version**: v5.4.23
**Last Agents Repo Sync**: v5.4.14
**Repository**: bobmatnyc/claude-mpm-agents

## Executive Summary

The claude-mpm-agents repository is **9 versions behind** (v5.4.14 → v5.4.23). A sync script exists at `scripts/sync_agent_skills_repos.sh` that automates the push workflow. Analysis identified **4 core agent files** and **13 template files** that need syncing.

## Repository Structure

### Main Repo (`claude-mpm`)
```
src/claude_mpm/agents/
├── BASE_AGENT.md                    # Core agent foundation
├── BASE_ENGINEER.md                 # Engineer-specific base
├── PM_INSTRUCTIONS.md               # Project manager instructions
├── WORKFLOW.md                      # Workflow documentation
├── MEMORY.md                        # Memory system docs
├── CLAUDE_MPM_OUTPUT_STYLE.md       # Output formatting guide
├── CLAUDE_MPM_TEACHER_OUTPUT_STYLE.md  # Teacher-specific output
└── templates/                       # Template ecosystem
    ├── README.md
    ├── circuit-breakers.md
    ├── context-management-examples.md
    ├── git-file-tracking.md
    ├── pm-examples.md
    ├── pm-red-flags.md
    ├── pr-workflow-examples.md
    ├── research-gate-examples.md
    ├── response-format.md
    ├── structured-questions-examples.md
    ├── ticket-completeness-examples.md
    ├── ticketing-examples.md
    └── validation-templates.md
```

### Agents Repo (`claude-mpm-agents`)
```
agents/
├── BASE-AGENT.md                    # Maps to BASE_AGENT.md
├── claude-mpm/                      # PM and core agents
├── documentation/
├── engineer/
├── ops/
├── qa/
├── security/
└── universal/
```

## Files Modified Since v5.4.14

### Core Agent Files (4 files)
1. **BASE_AGENT.md** - 18 commits since v5.4.14
   - Added proactive code quality improvements
   - Enhanced delegation rules
   - Updated with Chrome DevTools requirements

2. **BASE_ENGINEER.md** - Updates to engineer-specific behaviors

3. **PM_INSTRUCTIONS.md** - Extensive updates (consolidation + fixes)
   - Consolidated instructions (40e5dd60)
   - Fixed P0/P1 issues (684b49c5)
   - Added ops agent consolidation (6951daab)
   - Mandated Chrome DevTools MCP (10d24f0b)
   - Added forbidden MCP tools section (99f642c3)
   - Enhanced ticketing delegation (0872411a)
   - Optimized for Claude 4.5 (f214df0c)

4. **CLAUDE_MPM_TEACHER_OUTPUT_STYLE.md** - Output style updates

### Template Files (3 modified since v5.4.14)
- **circuit-breakers.md** - Upgraded to proactive blocking (9f820feb)
- **pm-examples.md** - PM delegation updates (3c79289e)
- **ticketing-examples.md** - Verification enforcement (0872411a)

### Files NOT Changed Since v5.4.14
- WORKFLOW.md
- MEMORY.md
- CLAUDE_MPM_OUTPUT_STYLE.md
- templates/README.md
- templates/context-management-examples.md
- templates/git-file-tracking.md
- templates/pm-red-flags.md
- templates/pr-workflow-examples.md
- templates/research-gate-examples.md
- templates/response-format.md
- templates/structured-questions-examples.md
- templates/ticket-completeness-examples.md
- templates/validation-templates.md

## Existing Sync Mechanism

### Script: `scripts/sync_agent_skills_repos.sh`

**Location**: `/Users/masa/Projects/claude-mpm/scripts/sync_agent_skills_repos.sh`

**Capabilities**:
- Syncs both agents and skills repositories
- Supports `--dry-run` mode for testing
- Automatic git workflow (fetch, pull, commit, push)
- Excludes `.etag_cache.json` files
- Auto-commit with version-tagged messages
- Interactive push confirmation

**Usage**:
```bash
# Dry run (preview changes)
./scripts/sync_agent_skills_repos.sh --dry-run

# Full sync (interactive)
./scripts/sync_agent_skills_repos.sh

# Via Makefile
make sync-repos              # Interactive sync
make sync-repos-dry-run      # Preview only
```

**Target Locations**:
- Agents: `~/.claude-mpm/cache/agents/bobmatnyc/claude-mpm-agents`
- Skills: `~/.claude-mpm/cache/skills/system`

**Workflow Steps**:
1. Fetch and prune remote references
2. Stash uncommitted changes
3. Pull latest from remote with rebase
4. Restore stashed changes
5. Add and commit changes (excluding .etag_cache.json)
6. Push to remote (with confirmation)

## File Mapping Strategy

### Direct Mappings (core files)
```
SOURCE → DESTINATION

Main Repo                           Agents Repo
---------------------------------------------------
BASE_AGENT.md                    →  agents/BASE-AGENT.md
BASE_ENGINEER.md                 →  templates/BASE-ENGINEER.md (or agents/engineer/BASE-ENGINEER.md)
PM_INSTRUCTIONS.md               →  templates/PM-INSTRUCTIONS.md (or agents/claude-mpm/)
WORKFLOW.md                      →  docs/WORKFLOW.md
```

### Template Files
The templates directory appears to be a **main repo exclusive** feature. The agents repo uses a different structure with built agents rather than templates.

**Decision Required**: Should templates be synced to agents repo?
- **Option A**: Add `templates/` directory to agents repo
- **Option B**: Keep templates main-repo-only (current approach)
- **Recommendation**: Option B - templates are for agent *building*, agents repo contains *built* agents

## Sync Complexity Analysis

### Current State
The sync script expects the agents repo to be checked out at:
```
~/.claude-mpm/cache/agents/bobmatnyc/claude-mpm-agents
```

**Issue Found**: Local cache is NOT a git repository
```bash
$ cd ~/.claude-mpm/cache/agents/bobmatnyc/claude-mpm-agents
$ git status
fatal: not a git repository (or any of the parent directories): .git
```

This suggests the sync script expects a **cloned repository**, but the cache contains fetched files without git metadata.

### Root Cause
Claude MPM downloads agents as files via HTTP/API (using .etag caching), NOT via git clone. The sync script assumes a git workflow that doesn't match the current agent deployment model.

## Recommended Sync Approach

### For v5.4.23 Release

**Manual Sync Required** (one-time):

1. **Clone agents repo locally** (if not already done):
   ```bash
   cd ~/Projects
   git clone https://github.com/bobmatnyc/claude-mpm-agents.git
   cd claude-mpm-agents
   ```

2. **Sync changed files manually**:
   ```bash
   # From main repo root
   cp src/claude_mpm/agents/BASE_AGENT.md \
      ~/Projects/claude-mpm-agents/agents/BASE-AGENT.md

   cp src/claude_mpm/agents/PM_INSTRUCTIONS.md \
      ~/Projects/claude-mpm-agents/templates/PM-INSTRUCTIONS.md

   cp src/claude_mpm/agents/BASE_ENGINEER.md \
      ~/Projects/claude-mpm-agents/templates/BASE-ENGINEER.md

   cp src/claude_mpm/agents/CLAUDE_MPM_TEACHER_OUTPUT_STYLE.md \
      ~/Projects/claude-mpm-agents/templates/CLAUDE_MPM_TEACHER_OUTPUT_STYLE.md
   ```

3. **Commit and push**:
   ```bash
   cd ~/Projects/claude-mpm-agents
   git add -A
   git commit -m "chore: sync agents for v5.4.23 release

   - Updated BASE-AGENT.md with proactive quality improvements
   - Updated PM-INSTRUCTIONS.md with consolidation and fixes
   - Updated BASE-ENGINEER.md
   - Updated CLAUDE_MPM_TEACHER_OUTPUT_STYLE.md

   Synced from claude-mpm v5.4.23 (9 versions since v5.4.14)

   🤖 Generated with [Claude MPM](https://github.com/bobmatnyc/claude-mpm)

   Co-Authored-By: Claude <noreply@anthropic.com>"

   git push origin main
   ```

### Script Integration Fix

**Issue**: `sync_agent_skills_repos.sh` expects git repos but cache uses HTTP downloads.

**Solution Options**:

**Option A: Modify Script for Cache Directory**
Update script to handle non-git cache directories:
```bash
# Add git clone if directory is not a git repo
if [ ! -d "$AGENTS_REPO/.git" ]; then
    echo "Cache is not a git repo, cloning..."
    rm -rf "$AGENTS_REPO"
    git clone https://github.com/bobmatnyc/claude-mpm-agents.git "$AGENTS_REPO"
fi
```

**Option B: Use Separate Working Directory**
Keep cache separate from sync workflow:
```bash
AGENTS_SYNC_DIR="$HOME/Projects/claude-mpm-agents"
AGENTS_CACHE_DIR="$HOME/.claude-mpm/cache/agents/bobmatnyc/claude-mpm-agents"
```

**Recommendation**: Option B - Cleaner separation of concerns

## Files to Sync for v5.4.23

### Priority 1: Core Changes (MUST sync)
```
src/claude_mpm/agents/BASE_AGENT.md
src/claude_mpm/agents/PM_INSTRUCTIONS.md
src/claude_mpm/agents/BASE_ENGINEER.md
src/claude_mpm/agents/CLAUDE_MPM_TEACHER_OUTPUT_STYLE.md
```

### Priority 2: Template Updates (SHOULD sync if templates exist in agents repo)
```
src/claude_mpm/agents/templates/circuit-breakers.md
src/claude_mpm/agents/templates/pm-examples.md
src/claude_mpm/agents/templates/ticketing-examples.md
```

### Priority 3: Unchanged but Complete (OPTIONAL - for completeness)
```
src/claude_mpm/agents/WORKFLOW.md
src/claude_mpm/agents/MEMORY.md
src/claude_mpm/agents/CLAUDE_MPM_OUTPUT_STYLE.md
src/claude_mpm/agents/templates/README.md
src/claude_mpm/agents/templates/context-management-examples.md
src/claude_mpm/agents/templates/git-file-tracking.md
src/claude_mpm/agents/templates/pm-red-flags.md
src/claude_mpm/agents/templates/pr-workflow-examples.md
src/claude_mpm/agents/templates/research-gate-examples.md
src/claude_mpm/agents/templates/response-format.md
src/claude_mpm/agents/templates/structured-questions-examples.md
src/claude_mpm/agents/templates/ticket-completeness-examples.md
src/claude_mpm/agents/templates/validation-templates.md
```

## Destination Path Mapping

Based on agents repo structure:

| Source File | Destination Path in Agents Repo |
|------------|----------------------------------|
| BASE_AGENT.md | `agents/BASE-AGENT.md` |
| PM_INSTRUCTIONS.md | `templates/PM-INSTRUCTIONS.md` OR `agents/claude-mpm/pm/instructions.md` |
| BASE_ENGINEER.md | `templates/BASE-ENGINEER.md` OR `agents/engineer/BASE-ENGINEER.md` |
| CLAUDE_MPM_TEACHER_OUTPUT_STYLE.md | `templates/CLAUDE_MPM_TEACHER_OUTPUT_STYLE.md` |
| templates/*.md | `templates/*.md` (if templates dir exists) |

**Note**: Exact destinations depend on agents repo structure preferences. Need to verify with maintainer or examine existing patterns.

## Recommended Push Script

Create `scripts/push_to_agents_repo.sh`:

```bash
#!/bin/bash
set -e

# Configuration
MAIN_REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AGENTS_REPO="$HOME/Projects/claude-mpm-agents"
VERSION=$(cat "$MAIN_REPO_ROOT/VERSION")

echo "🔄 Syncing agents repo for v$VERSION"

# Ensure agents repo exists and is up to date
if [ ! -d "$AGENTS_REPO" ]; then
    echo "❌ Agents repo not found at $AGENTS_REPO"
    echo "Clone it first: git clone https://github.com/bobmatnyc/claude-mpm-agents.git ~/Projects/claude-mpm-agents"
    exit 1
fi

cd "$AGENTS_REPO"
git fetch origin
git checkout main
git pull origin main

# Sync core files
echo "📋 Syncing core agent files..."
cp "$MAIN_REPO_ROOT/src/claude_mpm/agents/BASE_AGENT.md" agents/BASE-AGENT.md
cp "$MAIN_REPO_ROOT/src/claude_mpm/agents/PM_INSTRUCTIONS.md" templates/PM-INSTRUCTIONS.md
cp "$MAIN_REPO_ROOT/src/claude_mpm/agents/BASE_ENGINEER.md" templates/BASE-ENGINEER.md
cp "$MAIN_REPO_ROOT/src/claude_mpm/agents/CLAUDE_MPM_TEACHER_OUTPUT_STYLE.md" templates/CLAUDE_MPM_TEACHER_OUTPUT_STYLE.md

# Sync templates (if templates dir exists)
if [ -d "$AGENTS_REPO/templates" ]; then
    echo "📋 Syncing template files..."
    cp -r "$MAIN_REPO_ROOT/src/claude_mpm/agents/templates/"* "$AGENTS_REPO/templates/" 2>/dev/null || true
fi

# Show changes
echo "📊 Changes to commit:"
git status --short

# Commit
echo "💾 Committing changes..."
git add -A
git commit -m "chore: sync agents for v$VERSION release

- Synchronized changes for release v$VERSION
- Auto-committed by push_to_agents_repo.sh

🤖 Generated with [Claude MPM](https://github.com/bobmatnyc/claude-mpm)

Co-Authored-By: Claude <noreply@anthropic.com>"

# Push
echo "📤 Pushing to origin/main..."
git push origin main

echo "✅ Sync complete for v$VERSION"
```

## Next Steps

1. **Verify agent repo structure** - Check if templates should go in `templates/` or individual agent directories
2. **Test sync script** - Run with `--dry-run` first
3. **Manual sync for v5.4.23** - Copy 4 core files to agents repo
4. **Update sync automation** - Integrate into release workflow
5. **Add to Makefile** - Create `make push-agents` target

## Key Findings

### Positive
✅ Existing sync script handles git workflow well
✅ Clear commit message format with version tracking
✅ Dry-run mode available for testing
✅ Interactive confirmation before push
✅ Excludes cache files (.etag_cache.json)

### Issues
❌ Script assumes git repos but cache uses HTTP downloads
❌ Agent repo structure differs from main repo (underscores vs dashes)
❌ No clear mapping for templates directory
❌ 9 versions behind (v5.4.14 → v5.4.23)

### Recommendations
🎯 Use separate working directory for git operations
🎯 Manual sync for v5.4.23 (4 core files)
🎯 Document destination path conventions
🎯 Integrate sync into release workflow
🎯 Consider automating via GitHub Actions
