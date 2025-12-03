# Cache Update Workflow Analysis: Git Repository Management

**Date:** 2025-12-03
**Researcher:** Research Agent (Claude)
**Status:** Complete
**Ticket Reference:** N/A (exploratory research)

---

## Executive Summary

Investigation of the current cache update workflow reveals a **mature git-based sync system** for agents and skills that uses ETag-based caching and SQLite state tracking. However, **git operations within the cache are read-only** — the framework syncs FROM GitHub but does NOT commit/push changes back. The cache at `~/.claude-mpm/cache/remote-agents/` is a **fully functional git repository** that can be manually edited and pushed, but the framework deployment scripts have **zero git workflow integration**.

### Key Findings

✅ **What Works:**
- Robust ETag-based sync with GitHub API (Git Tree API)
- SQLite state tracking for incremental updates
- Progress bars and error handling
- Automatic discovery of 50+ agents via recursive git tree API
- Separate cache and deployment architecture (2-phase)

❌ **What's Missing:**
- No deploy scripts that commit/push cache changes
- No automated workflow for agent/skill updates from cache
- No pull-before-deploy safeguards
- No merge conflict detection
- No integration with `make` targets for cache sync

---

## 1. Current State Analysis

### 1.1 Cache Directory Structure

The cache is organized with **git repositories as the atomic unit**:

```
~/.claude-mpm/cache/
├── remote-agents/
│   ├── bobmatnyc/
│   │   └── claude-mpm-agents/        # ← Git repository (origin: github.com)
│   │       ├── .git/                 # Full git metadata
│   │       ├── agents/               # 50+ agent files (nested structure)
│   │       │   ├── engineer/
│   │       │   │   ├── backend/
│   │       │   │   ├── frontend/
│   │       │   │   └── core/
│   │       │   ├── qa/
│   │       │   └── ...
│   │       ├── templates/
│   │       ├── build-agent.py        # Agent composition script
│   │       └── AUTO-DEPLOY-INDEX.md  # Agent catalog
│   └── [other-owner]/
│       └── [other-repo]/
└── skills/
    └── system/                        # NOT a git repo (download-only)
        ├── .etag_cache.json          # ETag cache for HTTP 304
        ├── toolchains/
        ├── universal/
        └── ... (272 files)

```

**Key Observation:**
- **Agents cache:** `remote-agents/bobmatnyc/claude-mpm-agents/` is a **full git repository**
- **Skills cache:** `skills/system/` is **NOT a git repo** (downloads as flat files)
- Git metadata lives at the **repository level**, not project root

### 1.2 Current Sync Architecture

The framework implements a **2-phase sync model**:

```
Phase 1: GitHub → Cache (git_source_sync_service.py)
┌─────────────────────────────────────────────────────┐
│ GitHub API (Tree API)                               │
│   ↓ Discover all files (recursive)                  │
│ Raw URLs (raw.githubusercontent.com)                │
│   ↓ Download with ETag caching                      │
│ ~/.claude-mpm/cache/remote-agents/                  │
│   ↓ Save to cache (preserves structure)             │
│ SQLite State Tracking (agent_sync_state.py)         │
│   ↓ Track SHA-256, sync history, ETags              │
│ Cache Ready                                          │
└─────────────────────────────────────────────────────┘

Phase 2: Cache → Deployment (agent_deployment.py)
┌─────────────────────────────────────────────────────┐
│ Cache (nested structure)                             │
│   ↓ Copy from cache                                  │
│ ~/.claude/agents/ (flat structure)                   │
│   ↓ Flatten paths (engineer/core → engineer)         │
│ Deployed Agents (ready for use)                      │
└─────────────────────────────────────────────────────┘
```

**Performance Characteristics:**
- First sync (50 agents): ~5-10 seconds
- Incremental sync (ETag hits): ~1-2 seconds
- Agent discovery: ~500ms (single Tree API call)
- Deployment copy: ~10ms for 50 agents

### 1.3 Git Operations in Code

**Evidence of Git Operations:**

```python
# src/claude_mpm/services/agents/sources/git_source_sync_service.py
class GitSourceSyncService:
    """Service for syncing agent templates from remote Git repositories."""

    def sync_agents(self, force_refresh: bool = False):
        """Sync agents from remote Git repository with SQLite state tracking."""
        # Uses GitHub API + raw URLs (NOT git clone/pull)
        # Downloads files individually with ETag caching
        # Tracks state in SQLite (NOT git commits)
```

```python
# src/claude_mpm/services/version_control/git_operations.py
class GitOperationsManager:
    """Manages Git operations for the Version Control Agent."""
    # Provides git operations for PROJECT repositories
    # NOT used for cache directory management
    # Focus: branch, merge, remote operations for user projects
```

**Key Finding:** Git operations exist but are for **user projects**, not cache management.

---

## 2. Deploy Scripts Analysis

### 2.1 Makefile Targets

**Relevant Deploy Targets:**

```makefile
# Makefile (lines 447-449)
deploy-commands: ## Force deploy commands to ~/.claude/commands/ for testing
	@echo "$(YELLOW)Deploying commands for local testing...$(NC)"
	@python -c "from claude_mpm.services.command_deployment_service import deploy_commands_on_startup; deploy_commands_on_startup(force=True); print('$(GREEN)✅ Commands deployed to ~/.claude/commands/$(NC)')"
```

**Analysis:**
- ✅ Deploys slash commands from framework to `~/.claude/commands/`
- ❌ Does NOT touch cache directories
- ❌ No git operations (push, pull, commit)

### 2.2 Local Deploy Script

**File:** `scripts/deploy_local.sh` (444 lines)

**What it Does:**
1. ✅ Creates virtual environment
2. ✅ Installs claude-mpm in dev mode (`pip install -e .`)
3. ✅ Sets up PATH and aliases
4. ✅ Initializes `~/.claude-mpm/` directories
5. ❌ Does NOT sync agents/skills from remote
6. ❌ Does NOT touch git repositories in cache

**Key Functions:**
```bash
initialize_claude_mpm() {
    print_step "Initializing claude-mpm directories..."
    cd "$PROJECT_ROOT"
    source venv/bin/activate

    if python -c "from claude_mpm.init import ensure_directories; ensure_directories()" 2>/dev/null; then
        print_success "Initialized claude-mpm directories"
    else
        print_warning "Could not initialize directories (will be created on first run)"
    fi
}
```

**Missing:** No cache sync or git operations.

### 2.3 Startup Sync

**File:** `src/claude_mpm/services/agents/startup_sync.py`

The framework **automatically syncs on startup** via:
- `GitSourceSyncService.sync_agents()` (agents)
- `GitSkillSourceManager.sync_all_sources()` (skills)

**Trigger:** First run or when cache is stale (ETag mismatch)

**Git Operations:** NONE — uses HTTP downloads with ETag caching

---

## 3. Gap Analysis

### 3.1 Critical Gaps

#### ❌ No Cache-to-Remote Push Workflow

**Current Behavior:**
```bash
# Developer workflow (manual)
cd ~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents
git status                     # Shows modified files
git add agents/engineer.md
git commit -m "feat: update engineer agent"
git push origin main           # ✅ Works (git repo is functional)
```

**Framework Behavior:**
```bash
# Next startup
claude-mpm agents deploy       # ❌ Overwrites local changes
# Sync pulls latest from GitHub, discarding uncommitted edits
```

**Problem:** User edits in cache are **lost on next sync** unless manually committed/pushed.

#### ❌ No Pre-Deploy Git Pull

**Expected Workflow:**
```bash
# Before deploying agents
cd ~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents
git pull origin main           # Fetch latest changes
cd -
claude-mpm agents deploy       # Deploy fresh content
```

**Current Workflow:**
```bash
claude-mpm agents deploy       # Deploys from stale cache
# No git pull, only ETag checks on individual files
```

**Risk:** Deploying outdated agents if:
- Cache was synced days ago
- GitHub has newer commits
- ETag cache prevents re-download

#### ❌ No Merge Conflict Detection

**Scenario:**
1. Developer edits `engineer.md` in cache (uncommitted)
2. Upstream GitHub has conflicting changes
3. Next sync overwrites local changes (no merge, no warning)

**Expected:** Git merge conflict detection + resolution workflow

#### ❌ No Build Script Integration

**Observation:** `~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/build-agent.py` exists but is **never called** by framework.

**Purpose:** Combines agent-specific content with BASE-AGENT.md hierarchy.

**Integration Gap:** Deploy scripts don't build agents before deployment.

### 3.2 Skills Cache Differences

**Skills cache is NOT a git repository:**

```bash
$ ls -la ~/.claude-mpm/cache/skills/system/.git
# No .git directory

$ ls ~/.claude-mpm/cache/skills/system/
# Flat file structure with .etag_cache.json
```

**Implications:**
- ✅ Simpler structure (no git complexity)
- ❌ Can't track local modifications
- ❌ No version history
- ❌ Manual edits lost on next sync

**Design Decision:** Skills use **download-only model** vs. agents' **git-repo model**.

---

## 4. Recommended Workflow

### 4.1 Developer Workflow (Proposed)

```bash
# 1. Make changes to cached agents
cd ~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents
vim agents/engineer.md                # Edit agent
./build-agent.py agents/engineer.md   # Build with BASE-AGENT.md inheritance

# 2. Commit locally
git add agents/engineer.md
git commit -m "feat: enhance engineer agent with new capabilities"

# 3. Push to remote (optional: create PR)
git push origin main                  # Direct push (if permissions)
# OR
git push origin feature/engineer-updates  # Create branch + PR

# 4. Deploy (framework syncs automatically)
cd ~/Projects/claude-mpm
claude-mpm agents deploy              # Fetches latest, deploys
```

### 4.2 Automated Workflow (Ideal)

**Makefile Integration:**

```makefile
# New targets for cache management

agents-cache-sync: ## Sync agents cache from remote (git pull)
	@echo "$(YELLOW)Syncing agents cache...$(NC)"
	@cd ~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents && git pull origin main
	@echo "$(GREEN)✓ Cache synced from remote$(NC)"

agents-cache-status: ## Check git status of agents cache
	@echo "$(BLUE)Agents Cache Status:$(NC)"
	@cd ~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents && git status

agents-cache-push: ## Commit and push cache changes (interactive)
	@echo "$(YELLOW)⚠️  This will commit and push ALL changes in agents cache$(NC)"
	@cd ~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents && git add -A
	@cd ~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents && git commit
	@cd ~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents && git push origin main
	@echo "$(GREEN)✓ Cache changes pushed to remote$(NC)"

agents-deploy-safe: agents-cache-sync ## Deploy agents with pre-sync
	@echo "$(YELLOW)Deploying agents from synced cache...$(NC)"
	@claude-mpm agents deploy
```

**Python Service Integration:**

```python
# src/claude_mpm/services/agents/cache_git_manager.py (NEW)

class CacheGitManager:
    """Manages git operations for agent/skill caches."""

    def sync_cache_from_remote(self, cache_path: Path) -> Dict[str, Any]:
        """Pull latest changes from remote git repository."""
        # git pull origin main
        # Handle merge conflicts
        # Return sync results

    def commit_cache_changes(self, cache_path: Path, message: str) -> bool:
        """Commit local changes to cache repository."""
        # git add -A
        # git commit -m message
        # Return success/failure

    def push_cache_changes(self, cache_path: Path) -> bool:
        """Push committed changes to remote repository."""
        # git push origin main
        # Handle authentication
        # Return success/failure

    def check_cache_dirty(self, cache_path: Path) -> List[str]:
        """Check for uncommitted changes in cache."""
        # git status --porcelain
        # Return list of modified files
```

---

## 5. Implementation Plan

### Phase 1: Add Git Awareness (2-3 hours)

**Goal:** Detect git operations in cache without automating them.

**Tasks:**
1. Add `check_cache_dirty()` to GitSourceSyncService
2. Warn user if cache has uncommitted changes before sync
3. Add `--force` flag to override warnings
4. Update CLI with cache status commands

**Files to Modify:**
- `src/claude_mpm/services/agents/sources/git_source_sync_service.py`
- `src/claude_mpm/cli/commands/agents.py`

**Deliverables:**
- `claude-mpm agents cache-status` command
- Pre-sync warning: "Cache has uncommitted changes, use --force to overwrite"

### Phase 2: Add Makefile Targets (1 hour)

**Goal:** Provide manual git workflow shortcuts.

**Tasks:**
1. Add `agents-cache-sync`, `agents-cache-status`, `agents-cache-push` targets
2. Add `skills-cache-sync` (if skills become git-based)
3. Document in `make help`

**Files to Modify:**
- `Makefile` (around line 450, after `deploy-commands`)

### Phase 3: Automated Pre-Deploy Sync (2-3 hours)

**Goal:** Auto-sync cache before deployment.

**Tasks:**
1. Add `CacheGitManager` service
2. Integrate with `GitSourceSyncService.sync_agents()`
3. Add `git pull` before HTTP sync (if cache is git repo)
4. Handle merge conflicts gracefully (abort and inform user)

**Files to Modify:**
- `src/claude_mpm/services/agents/sources/git_source_sync_service.py`
- `src/claude_mpm/services/agents/cache_git_manager.py` (NEW)

**Deliverables:**
- Automatic `git pull` before agent deploy
- Merge conflict detection + user notification
- Fallback to HTTP sync if git operations fail

### Phase 4: Build Script Integration (3-4 hours)

**Goal:** Use `build-agent.py` during deployment.

**Tasks:**
1. Detect `build-agent.py` in cache repositories
2. Run build process after sync, before deployment
3. Cache built agents separately (avoid re-building on every deploy)
4. Update deployment to use built agents

**Files to Modify:**
- `src/claude_mpm/services/agents/deployment/agent_deployment.py`
- `src/claude_mpm/services/agents/sources/git_source_sync_service.py`

**Deliverables:**
- Built agents with BASE-AGENT.md inheritance
- Deployment uses flattened agent definitions
- Build cache to avoid redundant processing

### Phase 5: Skills Cache Git Migration (4-5 hours)

**Goal:** Convert skills cache to git-based model (optional).

**Decision Point:** Evaluate trade-offs:
- ✅ Consistency with agents workflow
- ✅ Version tracking for manual edits
- ❌ Increased complexity (272 files, nested structure)
- ❌ Storage overhead (git metadata + files)

**Tasks (if proceeding):**
1. Convert skills sources to git clone instead of HTTP downloads
2. Update `GitSkillSourceManager` to use `CacheGitManager`
3. Migrate existing caches to git repos
4. Update sync logic to use `git pull`

**Alternative:** Keep skills download-only, document limitation.

---

## 6. Risks and Mitigations

### Risk 1: Merge Conflicts

**Scenario:** User edits cache, upstream has conflicting changes.

**Mitigation:**
- Detect conflicts during `git pull`
- Abort deployment, inform user with clear error message
- Provide conflict resolution commands
- Fallback: Use HTTP sync to overwrite (with `--force`)

### Risk 2: Authentication Failures

**Scenario:** `git push` requires credentials (SSH keys, PAT).

**Mitigation:**
- Check git remote authentication before operations
- Provide clear setup instructions (SSH keys, GitHub CLI)
- Support both HTTPS and SSH URLs
- Graceful degradation: Allow read-only cache usage

### Risk 3: Cache Corruption

**Scenario:** Git repository in cache becomes corrupted.

**Mitigation:**
- Implement cache validation checks
- Provide `claude-mpm agents cache-reset` command
- Re-clone repository from scratch
- Backup `.etag-cache.json` and SQLite state

### Risk 4: Performance Degradation

**Scenario:** Git operations slow down deployment.

**Mitigation:**
- Run git operations asynchronously (background sync)
- Cache git status checks (5-minute TTL)
- Skip git operations for non-repo caches
- Provide `--skip-sync` flag for offline use

---

## 7. Testing Strategy

### 7.1 Unit Tests

```python
# tests/services/test_cache_git_manager.py

def test_sync_cache_from_remote():
    """Test git pull operation on cache repository."""
    # Setup: Create mock git repo
    # Execute: sync_cache_from_remote()
    # Verify: Latest commit pulled

def test_commit_cache_changes():
    """Test committing local changes to cache."""
    # Setup: Modify cache files
    # Execute: commit_cache_changes()
    # Verify: Changes committed with message

def test_merge_conflict_detection():
    """Test handling of merge conflicts during sync."""
    # Setup: Create conflicting changes
    # Execute: sync_cache_from_remote()
    # Verify: Conflict detected, sync aborted
```

### 7.2 Integration Tests

```python
# tests/integration/test_cache_workflow.py

def test_full_update_workflow():
    """Test complete agent update workflow."""
    # 1. Edit agent in cache
    # 2. Commit locally
    # 3. Sync with remote
    # 4. Deploy agents
    # Verify: Updated agent deployed correctly

def test_conflict_resolution():
    """Test workflow with merge conflicts."""
    # 1. Edit agent in cache
    # 2. Upstream pushes conflicting changes
    # 3. Attempt sync
    # Verify: Conflict detected, user informed
```

### 7.3 Manual Testing Checklist

- [ ] Edit agent in cache (`~/.claude-mpm/cache/remote-agents/...`)
- [ ] Run `claude-mpm agents cache-status` (shows modified files)
- [ ] Commit changes: `git commit -m "test"`
- [ ] Push changes: `git push origin main`
- [ ] Sync cache: `make agents-cache-sync`
- [ ] Deploy agents: `claude-mpm agents deploy`
- [ ] Verify deployed agent has latest changes

---

## 8. Documentation Updates Needed

### 8.1 Developer Guide

**New Section:** `docs/AGENT_DEVELOPMENT.md`

```markdown
# Agent Development Workflow

## Editing Agents in Cache

Claude MPM caches agent definitions in git repositories at:
`~/.claude-mpm/cache/remote-agents/{owner}/{repo}/`

### Making Changes

1. Navigate to cache repository:
   ```bash
   cd ~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents
   ```

2. Edit agent files:
   ```bash
   vim agents/engineer/backend/python-engineer.md
   ```

3. Build agent (if using BASE-AGENT.md):
   ```bash
   ./build-agent.py agents/engineer/backend/python-engineer.md
   ```

4. Test locally:
   ```bash
   claude-mpm agents deploy --force
   claude-mpm run -a engineer "test prompt"
   ```

5. Commit changes:
   ```bash
   git add agents/engineer/backend/python-engineer.md
   git commit -m "feat: enhance Python engineer with FastAPI support"
   ```

6. Push to remote:
   ```bash
   git push origin main
   ```

### Syncing Updates

To pull latest agent updates:
```bash
make agents-cache-sync
claude-mpm agents deploy
```

To check cache status:
```bash
make agents-cache-status
```
```

### 8.2 Makefile Help Text

```makefile
agents-cache-sync: ## Sync agents cache from remote (git pull)
agents-cache-status: ## Check git status of agents cache
agents-cache-push: ## Commit and push cache changes (interactive)
agents-deploy-safe: agents-cache-sync ## Deploy agents with pre-sync
```

---

## 9. Alternative Approaches

### Option A: Keep Current Workflow (HTTP-Only)

**Rationale:** Avoid git complexity, maintain simple HTTP sync model.

**Pros:**
- ✅ No authentication required
- ✅ Works with any remote source (not just GitHub)
- ✅ Simpler error handling (HTTP status codes)
- ✅ No merge conflicts

**Cons:**
- ❌ Can't track local modifications
- ❌ No version history
- ❌ Manual edits lost on sync
- ❌ Inconsistent with git repo structure already in cache

**Verdict:** Not recommended — cache already has `.git/` directory.

### Option B: Hybrid Approach (Recommended)

**Rationale:** Preserve HTTP sync for initial setup, add git operations for advanced users.

**Implementation:**
1. Check if cache is git repository
2. If yes: Use git operations (`pull`, `commit`, `push`)
3. If no: Use HTTP sync (current behavior)
4. Provide flag: `--sync-method=[git|http|auto]`

**Pros:**
- ✅ Backward compatible (HTTP sync still works)
- ✅ Enables advanced workflows (git operations)
- ✅ Graceful degradation (fallback to HTTP)
- ✅ Flexible for different cache types

**Verdict:** **Recommended approach**

### Option C: Full Git-Based Workflow

**Rationale:** Use `git clone` instead of HTTP downloads, full git operations.

**Pros:**
- ✅ Native git experience
- ✅ Full version history
- ✅ Branch/tag support
- ✅ Consistent with developer expectations

**Cons:**
- ❌ Requires git authentication
- ❌ Slower initial sync (clones full history)
- ❌ More complex error handling
- ❌ Breaking change for existing users

**Verdict:** Not recommended for initial implementation (too disruptive).

---

## 10. Conclusion

### Summary of Findings

The claude-mpm framework has a **robust sync system** for agents and skills but **zero git workflow integration** for cache management. The cache at `~/.claude-mpm/cache/remote-agents/` is a **functional git repository** that developers can manually edit and push, but the framework:

1. ❌ Does NOT commit local cache changes
2. ❌ Does NOT pull before syncing
3. ❌ Does NOT detect merge conflicts
4. ❌ Does NOT use build scripts in cache

### Recommended Implementation

**Hybrid Approach (Option B):**
- Detect git repository in cache
- Add git awareness (check for uncommitted changes)
- Provide Makefile shortcuts for manual operations
- Add optional automated git sync (with fallback to HTTP)
- Preserve backward compatibility

**Estimated Effort:** 10-15 hours (spread across 5 phases)

**Priority:** Medium-High (enables advanced agent development workflows)

### Next Steps for Engineer

**Immediate Actions:**
1. Review this research document
2. Decide on implementation approach (recommend Hybrid)
3. Create implementation tickets for 5 phases
4. Prioritize Phase 1 (Git Awareness) for initial release

**Files to Create:**
- `src/claude_mpm/services/agents/cache_git_manager.py`
- `docs/AGENT_DEVELOPMENT.md`
- `tests/services/test_cache_git_manager.py`

**Files to Modify:**
- `Makefile` (add cache management targets)
- `src/claude_mpm/services/agents/sources/git_source_sync_service.py`
- `src/claude_mpm/cli/commands/agents.py`

---

## Appendix: File References

### Key Source Files Analyzed

1. **Sync Services:**
   - `src/claude_mpm/services/agents/sources/git_source_sync_service.py` (1056 lines)
   - `src/claude_mpm/services/agents/git_source_manager.py` (630 lines)
   - `src/claude_mpm/services/skills/git_skill_source_manager.py` (1170 lines)

2. **Deploy Scripts:**
   - `Makefile` (1224 lines)
   - `scripts/deploy_local.sh` (444 lines)
   - `scripts/migrate_cache_to_remote_agents.py` (406 lines)

3. **Git Operations:**
   - `src/claude_mpm/services/version_control/git_operations.py` (200+ lines)
   - Note: Used for project repos, NOT cache management

4. **Cache Structure:**
   - `~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/` (git repo)
   - `~/.claude-mpm/cache/skills/system/` (flat files)

### External References

- GitHub API Documentation: https://docs.github.com/en/rest/git/trees
- Git Tree API Pattern: Used successfully in agent sync
- ETag-based HTTP Caching: RFC 7232

---

**End of Research Report**
