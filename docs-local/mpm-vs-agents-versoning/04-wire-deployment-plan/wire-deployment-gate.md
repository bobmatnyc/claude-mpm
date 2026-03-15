# Wire Deployment Gate: Connecting ManifestCache and DeploymentVersionGate to the Pipeline

**Document**: `wire-deployment-gate.md`
**Series**: MPM vs. Agents Versioning (04-wire-deployment-plan)
**Date**: 2026-03-15
**Status**: Implementation-Ready Plan
**Addresses**: Devil's Advocate Finding A-2 (dead code: DeploymentVersionGate and ManifestCache not wired into pipeline)
**Depends on**: Phase 1 + Phase 2 implementation (complete)

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Current State of the Code](#2-current-state-of-the-code)
3. [Goal](#3-goal)
4. [Data Flow: Before and After](#4-data-flow-before-and-after)
5. [Implementation](#5-implementation)
6. [Test Plan](#6-test-plan)
7. [Rollback Plan](#7-rollback-plan)
8. [Risk Assessment](#8-risk-assessment)

---

## 1. Problem Statement

Phase 2 created two components -- `ManifestCache` and `DeploymentVersionGate` -- that are fully implemented and tested (87 tests cover them), but never called by the production pipeline. They are dead code.

This creates a concrete gap: the manifest compatibility check runs at **sync time** (when agents are fetched from remote), but not at **deploy time** (when cached agents are copied from `~/.claude-mpm/cache/agents/` to `.claude/agents/`).

### The Scenario This Misses

```
Day 1: User runs CLI v5.10.0
       sync_agents() → fetches manifest → COMPATIBLE → agents cached
       reconcile_agents() → copies cached agents to .claude/agents/

Day 3: Agent repo maintainer bumps min_cli_version to 6.0.0 in the manifest

Day 5: User runs CLI v5.10.0 (same version, did not upgrade)
       sync_agents() → fetches NEW manifest → INCOMPATIBLE_WARN → warns, agents re-cached
       reconcile_agents() → copies cached agents to .claude/agents/ ← NO CHECK HERE

       The warning was logged during sync but the deploy proceeds silently.
       If the user had --no-sync (using stale cache), there would be NO check at all.
```

The deploy-time check would catch both cases: it re-validates the cached manifest data before copying agents into the project, ensuring the user sees the warning (or hard stop) at the moment it matters -- when agents are about to be used.

### Why This Matters More Than It Appears

The sync-time check and the deploy-time check serve different purposes:

| Check | Purpose | When It Runs | What It Catches |
|-------|---------|--------------|-----------------|
| Sync-time | "Should I download these agents?" | Every sync (24h TTL) | Incompatible remote repos |
| Deploy-time | "Should I use these cached agents?" | Every startup | Stale cache, --no-sync scenarios, CLI downgrades |

The deploy-time check is the **last line of defense** before agents reach the user's Claude session.

---

## 2. Current State of the Code

### What Exists (Implemented, Tested, Not Wired)

| Component | File | Tests | Status |
|-----------|------|-------|--------|
| `ManifestCache` | `src/claude_mpm/services/agents/compatibility/manifest_cache.py` | 13 tests in `test_phase2.py` | Tested, not called |
| `DeploymentVersionGate` | `src/claude_mpm/services/agents/compatibility/deploy_gate.py` | 8 tests in `test_phase2.py` | Tested, not called |

### Sync Pipeline (Currently Wired)

```
startup.py: sync_remote_agents_on_startup()
  → startup_sync.py: sync_agents_on_startup()
    → git_source_sync_service.py: sync_agents()
      → _check_manifest_compatibility()     ← WIRED (Phase 1)
        → ManifestFetcher.fetch()
        → ManifestChecker.check()
        → IncompatibleRepoError on hard stop
      → _get_agent_list()
      → per-agent fetch
```

### Deploy Pipeline (Currently NOT Wired)

```
startup.py: sync_remote_agents_on_startup()
  → startup_reconciliation.py: perform_startup_reconciliation()
    → deployment_reconciler.py: DeploymentReconciler.reconcile_agents()
      → _get_agent_state(cache_dir, deploy_dir)
      → for agent_id in state.to_deploy:
          _deploy_agent(agent_id, cache_dir, deploy_dir)   ← NO CHECK
```

### Key Integration Points

| File | Class/Function | What It Does | Modification Needed |
|------|---------------|--------------|---------------------|
| `git_source_sync_service.py` | `_check_manifest_compatibility()` | Fetches + checks manifest at sync time | Store result in ManifestCache after check |
| `deployment_reconciler.py` | `DeploymentReconciler.reconcile_agents()` | Copies agents from cache to project | Call DeploymentVersionGate before deploying |
| `startup_reconciliation.py` | `perform_startup_reconciliation()` | Orchestrates reconciliation | Pass ManifestCache to DeploymentReconciler |

---

## 3. Goal

Wire ManifestCache and DeploymentVersionGate into the production pipeline so that:

1. **Sync time**: After a successful manifest check, the result is persisted in ManifestCache (SQLite).
2. **Deploy time**: Before copying cached agents to `.claude/agents/`, DeploymentVersionGate reads from ManifestCache and re-validates against the current CLI version.
3. **Hard stop at deploy time**: If the cached manifest says `repo_format_version > MAX_SUPPORTED`, deployment of agents from that source is skipped.
4. **Warning at deploy time**: If the cached manifest says `min_cli_version > current`, a warning is logged but deployment proceeds.
5. **Fail-open**: If ManifestCache has no entry for a source (e.g., legacy cache, first run), deployment proceeds without constraint.

### Non-Goals

- Changing ManifestCache or DeploymentVersionGate internals (they are already correct)
- Adding per-agent deploy-time checks (future enhancement)
- Changing the sync-time check behavior
- Adding UI prompts or interactive confirmation

---

## 4. Data Flow: Before and After

### Before (Current)

```
SYNC PHASE                              DEPLOY PHASE
-----------                              ------------
ManifestFetcher.fetch()                  DeploymentReconciler.reconcile_agents()
        |                                        |
        v                                        v
ManifestChecker.check()                  for agent in to_deploy:
        |                                    _deploy_agent(agent)  ← no check
        v                                        |
[result logged/raised]                           v
        |                                  agent copied to .claude/agents/
        v
agents fetched to cache

ManifestCache ← NOT POPULATED            DeploymentVersionGate ← NOT CALLED
```

### After (Proposed)

```
SYNC PHASE                              DEPLOY PHASE
-----------                              ------------
ManifestFetcher.fetch()                  DeploymentReconciler.reconcile_agents()
        |                                        |
        v                                        v
ManifestChecker.check()                  DeploymentVersionGate.check_before_deploy()
        |                                        |
        v                                        v
[result logged/raised]                   Read from ManifestCache
        |                                        |
        v                                        v
ManifestCache.store()  ← NEW             [COMPATIBLE]  → proceed with deploy
        |                                [WARN]        → log warning, proceed
        v                                [HARD STOP]   → skip this source's agents
agents fetched to cache                  [NO ENTRY]    → proceed (fail-open)
                                                 |
                                                 v
                                         for agent in to_deploy:
                                             _deploy_agent(agent)
```

---

## 5. Implementation

### 5.1 Change 1: Persist Manifest Check Results at Sync Time

**File**: `src/claude_mpm/services/agents/sources/git_source_sync_service.py`
**Method**: `_check_manifest_compatibility()`
**Change**: After a successful check (any status except skip), store the result in ManifestCache.

#### 5.1.1 Add ManifestCache import

```python
# Add to existing compatibility imports:
from claude_mpm.services.agents.compatibility.manifest_cache import ManifestCache
```

#### 5.1.2 Initialize ManifestCache in `__init__`

```python
# In GitSourceSyncService.__init__, after self.git_manager initialization:
self._manifest_cache = ManifestCache()
```

#### 5.1.3 Store result after check

In `_check_manifest_compatibility()`, after the checker runs and before returning or raising, persist the result. Insert after `result = checker.check(manifest_content, __version__)`:

```python
        # Persist manifest check result for deploy-time validation
        if manifest_content is not None and result.repo_format_version is not None:
            try:
                import yaml
                parsed = yaml.safe_load(manifest_content)
                self._manifest_cache.store(
                    source_id=self.source_id,
                    repo_format_version=result.repo_format_version,
                    min_cli_version=result.min_cli_version or "0.0.0",
                    max_cli_version=(parsed or {}).get("max_cli_version"),
                    compatibility_ranges=(parsed or {}).get("compatibility_ranges"),
                    agent_overrides=(parsed or {}).get("agents"),
                    raw_content=manifest_content,
                )
            except Exception as e:
                # Cache write failure must not break sync (fail-open)
                logger.debug("Failed to cache manifest result: %s", e)
```

**Key decisions**:
- Store happens regardless of compatibility status (even INCOMPATIBLE results are cached for deploy-time re-validation)
- Cache write failures are caught and logged at DEBUG (fail-open)
- `source_id` is used as the cache key (matches `GitSourceSyncService.source_id`)
- `raw_content` is stored so DeploymentVersionGate can re-parse it with a potentially newer ManifestChecker

### 5.2 Change 2: Add Deploy-Time Check to DeploymentReconciler

**File**: `src/claude_mpm/services/agents/deployment/deployment_reconciler.py`
**Method**: `reconcile_agents()`
**Change**: Before the deploy loop, check manifest compatibility for each source's agents.

#### 5.2.1 Add imports

```python
from claude_mpm.services.agents.compatibility import (
    CompatibilityResult,
    ManifestCheckResult,
)
from claude_mpm.services.agents.compatibility.deploy_gate import DeploymentVersionGate
from claude_mpm.services.agents.compatibility.manifest_cache import ManifestCache
```

#### 5.2.2 Add DeploymentVersionGate to `__init__`

```python
def __init__(self, config: Optional[UnifiedConfig] = None):
    self.config = config or self._load_config()
    self.path_manager = get_path_manager()
    # Deploy-time manifest compatibility gate
    self._manifest_cache = ManifestCache()
    self._deploy_gate = DeploymentVersionGate(manifest_cache=self._manifest_cache)
```

#### 5.2.3 Add deploy-time check in `reconcile_agents()`

Insert a manifest compatibility check **before** the deploy loop (after `result = DeploymentResult(...)` and before `for agent_id in state.to_deploy:`):

```python
        # Deploy-time manifest compatibility check
        blocked_sources = self._check_deploy_compatibility()
        # (blocked_sources is a set of source_ids whose agents should be skipped)
```

#### 5.2.4 New method: `_check_deploy_compatibility()`

```python
    def _check_deploy_compatibility(self) -> Set[str]:
        """Check cached manifest compatibility before deploying agents.

        Reads all cached manifests and re-validates each against the current
        CLI version.  Returns a set of source_ids whose agents should NOT be
        deployed (hard stop only).  Warnings are logged but do not block.

        Returns:
            Set of source_ids to skip during deployment.
        """
        blocked: Set[str] = set()

        try:
            from claude_mpm import __version__
        except ImportError:
            return blocked  # Can't determine version; fail-open

        all_cached = self._manifest_cache.get_all()
        if not all_cached:
            return blocked  # No cached manifests; fail-open

        for entry in all_cached:
            source_id = entry.get("source_id", "unknown")
            raw_content = entry.get("raw_content")

            result = self._deploy_gate.check_before_deploy(
                source_id=source_id,
                cli_version=__version__,
                cached_manifest_content=raw_content,
            )

            if result.status == CompatibilityResult.INCOMPATIBLE_HARD:
                logger.error(
                    "Deploy blocked for source '%s': %s",
                    source_id,
                    result.message,
                )
                blocked.add(source_id)
            elif result.status == CompatibilityResult.INCOMPATIBLE_WARN:
                # Warning already logged by DeploymentVersionGate
                pass

        return blocked
```

#### 5.2.5 Challenge: Mapping Agents to Sources

**This is the hardest part of the wiring.**

`DeploymentReconciler` works with agent IDs (e.g., `"python-engineer"`, `"web-qa"`) and has no knowledge of which source each agent came from. The `reconcile_agents()` method iterates over `state.to_deploy` which is a flat `Set[str]` of agent IDs.

`ManifestCache` is keyed by `source_id` (e.g., `"github-remote"`). There is no mapping from agent ID to source ID in the current data model.

**Three options to resolve this**:

##### Option A: Block ALL deploys if ANY source is blocked (simplest)

If `_check_deploy_compatibility()` finds any hard-stopped source, block ALL agent deployments. This is safe but coarse -- a single bad source would block agents from other sources too.

```python
        if blocked_sources:
            for source_id in blocked_sources:
                result.errors.append(
                    f"Agent deployment blocked: source '{source_id}' requires a newer CLI. "
                    f"Run: pip install --upgrade claude-mpm"
                )
            return result  # Return early, deploy nothing
```

**Pros**: Simple, zero risk of deploying incompatible agents.
**Cons**: Over-blocks when multiple sources are configured but only one is incompatible.

##### Option B: Agent-to-source mapping via AgentSyncState (accurate)

`AgentSyncState` (SQLite) already tracks which source each agent file came from via `tracked_files`:

```sql
-- In agent_sync_state.db:
CREATE TABLE tracked_files (
    source_id TEXT,
    filename TEXT,
    content_hash TEXT,
    ...
);
```

We can query this to build an agent-to-source mapping:

```python
    def _get_agent_source_map(self) -> Dict[str, str]:
        """Map agent IDs to their source IDs using AgentSyncState."""
        from claude_mpm.services.agents.sources.agent_sync_state import AgentSyncState
        state = AgentSyncState()
        mapping = {}
        for source_id, files in state.get_all_tracked_files().items():
            for filename in files:
                agent_id = Path(filename).stem
                mapping[agent_id] = source_id
        return mapping
```

Then in `reconcile_agents()`:

```python
        agent_source_map = self._get_agent_source_map()

        for agent_id in state.to_deploy:
            source_id = agent_source_map.get(agent_id)
            if source_id and source_id in blocked_sources:
                error_msg = (
                    f"Agent '{agent_id}' blocked: source '{source_id}' requires "
                    f"a newer CLI. Run: pip install --upgrade claude-mpm"
                )
                logger.warning(error_msg)
                result.errors.append(error_msg)
                continue  # Skip this agent

            # ... existing deploy logic
```

**Pros**: Precise per-agent blocking based on actual source.
**Cons**: Requires reading from AgentSyncState which may not exist on first run. Needs a `get_all_tracked_files()` method (may need to add to AgentSyncState).

##### Option C: Warn-only at deploy time, hard-stop only at sync time (pragmatic)

Since sync-time already handles hard stops (raises `IncompatibleRepoError` which skips the source entirely, so incompatible agents never reach the cache in the first place), the deploy-time check only needs to handle:
- CLI downgrades (user installs older CLI after syncing with newer)
- `--no-sync` scenarios (user skips sync, cache has stale data)

For these cases, a warning is sufficient -- the user is already in degraded territory:

```python
        # Deploy-time check: warn only (hard stops handled at sync time)
        for entry in self._manifest_cache.get_all():
            result = self._deploy_gate.check_before_deploy(
                source_id=entry["source_id"],
                cli_version=__version__,
                cached_manifest_content=entry.get("raw_content"),
            )
            if result.status in (
                CompatibilityResult.INCOMPATIBLE_HARD,
                CompatibilityResult.INCOMPATIBLE_WARN,
            ):
                logger.warning(
                    "Deploy-time compatibility issue for source '%s': %s",
                    entry["source_id"],
                    result.message,
                )
```

**Pros**: Simplest, no agent-to-source mapping needed, no blocking logic.
**Cons**: Doesn't prevent deployment of incompatible agents after CLI downgrade.

#### Recommendation: Option A for Now, Option B Later

Start with Option A (block all if any source blocked). The vast majority of deployments use a single source (`github-remote`). Multi-source users are rare. Option A is correct, safe, and takes 10 lines. Add Option B as a follow-up when multi-source usage grows.

### 5.3 Change 3: Thread ManifestCache Through Startup

**File**: `src/claude_mpm/services/agents/deployment/startup_reconciliation.py`
**Change**: Minimal -- `DeploymentReconciler.__init__` creates its own `ManifestCache` instance. No threading needed unless we want to share the instance with the sync service (optimization, not required).

The `ManifestCache` uses a well-known default path (`~/.claude-mpm/cache/manifest_cache.db`). Both `GitSourceSyncService` (writer) and `DeploymentReconciler` (reader) will independently connect to the same database. SQLite handles concurrent readers correctly.

No change needed in `startup_reconciliation.py` for the initial wiring.

### 5.4 Change 4: SQLite Hardening (from Devil's Advocate C-1)

**File**: `src/claude_mpm/services/agents/compatibility/manifest_cache.py`
**Method**: `_init_db()`
**Change**: Enable WAL mode and set a busy timeout for concurrent access.

```python
    def _init_db(self) -> None:
        """Initialize the manifest_cache table."""
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS manifest_cache (
                    ...
                )
            """)
            conn.commit()
```

---

## 6. Test Plan

### 6.1 New Tests: Sync-Time Cache Population (5 tests)

| # | Test | Assert |
|---|------|--------|
| W-1 | Compatible manifest stored after sync check | ManifestCache.get(source_id) returns entry with correct fields |
| W-2 | Incompatible manifest also stored | Cache entry exists even for INCOMPATIBLE_HARD (needed for deploy-time re-check) |
| W-3 | Cache write failure doesn't break sync | Mock ManifestCache.store to raise; sync_agents still returns results |
| W-4 | No-manifest scenario doesn't write to cache | ManifestCache.get returns None |
| W-5 | Successive syncs update cache entry | last_checked timestamp advances |

### 6.2 New Tests: Deploy-Time Gate (8 tests)

| # | Test | Assert |
|---|------|--------|
| W-6 | Compatible cache entry allows deployment | reconcile_agents deploys normally |
| W-7 | INCOMPATIBLE_HARD blocks all deployments | reconcile_agents returns error, no agents deployed |
| W-8 | INCOMPATIBLE_WARN logs warning, deploys proceed | Warning logged, agents deployed |
| W-9 | Empty cache (no entries) deploys normally (fail-open) | reconcile_agents deploys normally |
| W-10 | Multiple sources, one blocked | All agents blocked (Option A behavior) |
| W-11 | `--no-sync` with stale cache triggers warning | Deploy-time check catches the staleness |
| W-12 | CLI downgrade scenario | Synced with v6.0.0 CLI, deploy with v5.10.0 → warning |
| W-13 | DeploymentVersionGate.check_before_deploy reads from cache | Verifies raw_content used for re-check |

### 6.3 New Tests: WAL Mode and Concurrency (3 tests)

| # | Test | Assert |
|---|------|--------|
| W-14 | WAL mode is set on init | PRAGMA journal_mode returns "wal" |
| W-15 | Concurrent reads during write | Two threads can read while one writes |
| W-16 | Busy timeout handles lock contention | No `database is locked` error under 5s contention |

### 6.4 Test Location

```
tests/services/agents/compatibility/test_wiring.py    # W-1 through W-16
```

### 6.5 Existing Tests

All 170 existing compatibility tests must continue to pass. The wiring changes add behavior without modifying existing behavior.

---

## 7. Rollback Plan

### Tier 1: Disable Deploy-Time Check (Immediate)

The env var `CLAUDE_MPM_SKIP_COMPAT_CHECK` already works for sync-time checks. Extend it to cover deploy-time:

In `DeploymentReconciler._check_deploy_compatibility()`:
```python
        import os
        if os.environ.get("CLAUDE_MPM_SKIP_COMPAT_CHECK", "").lower() in ("1", "true", "yes"):
            return set()  # Skip deploy-time check
```

### Tier 2: Remove Wiring (Minutes)

Revert the three integration points:
1. Remove `ManifestCache.store()` call from `_check_manifest_compatibility()`
2. Remove `_check_deploy_compatibility()` call from `reconcile_agents()`
3. Remove `ManifestCache` / `DeploymentVersionGate` initialization from both classes

The components remain in the codebase (tested, unused) -- back to current state.

### Tier 3: Delete ManifestCache Database (User Self-Service)

```bash
rm ~/.claude-mpm/cache/manifest_cache.db
```

Forces clean state on next sync.

---

## 8. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Cache write slows sync startup | Low | Low | Write is a single SQLite INSERT (~1ms). Wrapped in try/except fail-open. |
| Cache read slows deploy startup | Low | Low | Read is a single SELECT for each source (~1ms). Fail-open on error. |
| Stale cache causes false positive block | Very Low | Medium | Cache is overwritten on every sync. TTL could be added later. |
| WAL mode file permissions issue | Low | Low | WAL creates `-wal` and `-shm` files next to the database. Same directory permissions apply. |
| Option A over-blocks in multi-source | Low | Medium | Acceptable because multi-source is rare. Document in error message to use `--skip-compat-check`. |
| Circular import from lazy `__version__` | Very Low | High | Same pattern used in 8 other places in the codebase. Already validated in Phase 1. |

### Estimated Effort

| Task | Lines Changed | Time |
|------|--------------|------|
| 5.1: Cache at sync time | ~20 lines in git_source_sync_service.py | 30 min |
| 5.2: Gate at deploy time | ~50 lines in deployment_reconciler.py | 1 hour |
| 5.4: SQLite WAL mode | ~2 lines in manifest_cache.py | 5 min |
| 6: Tests | ~200 lines in test_wiring.py | 2 hours |
| Verification | Full test suite run | 30 min |
| **Total** | **~270 lines** | **~4 hours** |

---

## Appendix: Files Changed Summary

| File | Change Type | Description |
|------|------------|-------------|
| `src/claude_mpm/services/agents/sources/git_source_sync_service.py` | Modify | Add ManifestCache import, init, and store call in `_check_manifest_compatibility` |
| `src/claude_mpm/services/agents/deployment/deployment_reconciler.py` | Modify | Add compatibility imports, init ManifestCache + DeploymentVersionGate, add `_check_deploy_compatibility()`, call before deploy loop |
| `src/claude_mpm/services/agents/compatibility/manifest_cache.py` | Modify | Add WAL mode + busy_timeout PRAGMAs in `_init_db()` |
| `tests/services/agents/compatibility/test_wiring.py` | Create | 16 new tests for the wiring |
