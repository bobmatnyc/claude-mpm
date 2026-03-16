# Wire Deployment Gate: Connecting ManifestCache and DeploymentVersionGate to the Pipeline

**Document**: `wire-deployment-gate.md`
**Series**: MPM vs. Agents Versioning (04-wire-deployment-plan)
**Date**: 2026-03-15
**Status**: Implementation-Ready Plan (Amended after Devil's Advocate Review)
**Addresses**: Devil's Advocate Finding A-2 (dead code: DeploymentVersionGate and ManifestCache not wired into pipeline)
**Depends on**: Phase 1 + Phase 2 implementation (complete)
**Revision**: v3 - incorporates 8 devil's advocate findings (DA-1 through DA-5, DA-7 through DA-9); skills out of scope

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
9. [Devil's Advocate Findings (v2)](#9-devils-advocate-findings-v2)

---

## 1. Problem Statement

Phase 2 created two components -- `ManifestCache` and `DeploymentVersionGate` -- that are fully implemented and tested (87 tests cover them), but never called by the production pipeline. They are dead code.

This creates a concrete gap: the manifest compatibility check runs at **sync time** (when agents are fetched from remote), but not at **deploy time** (when cached agents are copied from `~/.claude-mpm/cache/agents/` to `.claude/agents/`).

### The Scenario This Misses

```
Day 1: User runs CLI v5.10.0
       sync_agents() -> fetches manifest -> COMPATIBLE -> agents cached
       reconcile_agents() -> copies cached agents to .claude/agents/

Day 3: Agent repo maintainer bumps min_cli_version to 6.0.0 in the manifest

Day 5: User runs CLI v5.10.0 (same version, did not upgrade)
       sync_agents() -> fetches NEW manifest -> INCOMPATIBLE_WARN -> warns, agents re-cached
       reconcile_agents() -> copies cached agents to .claude/agents/ <- NO CHECK HERE

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
  -> startup_sync.py: sync_agents_on_startup()
    -> git_source_sync_service.py: sync_agents()
      -> _check_manifest_compatibility()     <- WIRED (Phase 1)
        -> ManifestFetcher.fetch()
        -> ManifestChecker.check()
        -> IncompatibleRepoError on hard stop
      -> _get_agent_list()
      -> per-agent fetch
```

### Deploy Pipeline (Currently NOT Wired)

```
startup.py: sync_remote_agents_on_startup()
  -> startup_reconciliation.py: perform_startup_reconciliation()
    -> deployment_reconciler.py: DeploymentReconciler.reconcile_agents()
      -> _get_agent_state(cache_dir, deploy_dir)
      -> [DA-1] auto_discover early return (line 114-123)  <- BYPASSES EVERYTHING
      -> for agent_id in state.to_deploy:
          _deploy_agent(agent_id, cache_dir, deploy_dir)   <- NO CHECK
```

### Key Integration Points

| File | Class/Function | What It Does | Modification Needed |
|------|---------------|--------------|---------------------|
| `git_source_sync_service.py` | `_check_manifest_compatibility()` | Fetches + checks manifest at sync time | Store result in ManifestCache after check |
| `deployment_reconciler.py` | `DeploymentReconciler.reconcile_agents()` | Copies agents from cache to project | Call DeploymentVersionGate before deploying |
| `startup_reconciliation.py` | `perform_startup_reconciliation()` | Orchestrates reconciliation | Pass ManifestCache to DeploymentReconciler |

### Key Architecture Notes

**Two separate SQLite databases in different directories** (DA-8):

| Component | Database Path | Purpose |
|-----------|--------------|---------|
| `ManifestCache` | `~/.claude-mpm/cache/manifest_cache.db` | Manifest compatibility results |
| `AgentSyncState` | `~/.config/claude-mpm/agent_sync.db` | Per-file content hashes, sync history |

This means `rm -rf ~/.claude-mpm/cache/` destroys the manifest cache but preserves sync state. Option B (agent-to-source mapping) would require cross-database coordination.

---

## 3. Goal

Wire ManifestCache and DeploymentVersionGate into the production pipeline so that:

1. **Sync time**: After a successful manifest check, the result is persisted in ManifestCache (SQLite).
2. **Deploy time**: Before copying cached agents to `.claude/agents/`, DeploymentVersionGate reads from ManifestCache and re-validates against the current CLI version.
3. **Hard stop at deploy time**: If the cached manifest says `repo_format_version > MAX_SUPPORTED`, deployment of agents from that source is skipped.
4. **Warning at deploy time**: If the cached manifest says `min_cli_version > current`, a warning is logged but deployment proceeds.
5. **Fail-open**: If ManifestCache has no entry for a source (e.g., legacy cache, first run), deployment proceeds without constraint.
6. **Both code paths covered**: The gate runs for BOTH explicit-config and auto-discover deployment modes (DA-1 fix).

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
ManifestChecker.check()                  [auto_discover?] -> early return (NO CHECK)
        |                                        |
        v                                        v
[result logged/raised]                   for agent in to_deploy:
        |                                    _deploy_agent(agent)  <- no check
        v                                        |
agents fetched to cache                          v
                                         agent copied to .claude/agents/

ManifestCache <- NOT POPULATED           DeploymentVersionGate <- NOT CALLED
```

### After (Proposed, amended per DA-1)

```
SYNC PHASE                              DEPLOY PHASE
-----------                              ------------
ManifestFetcher.fetch()                  DeploymentReconciler.reconcile_agents()
        |                                        |
        v                                        v
ManifestChecker.check()                  _check_deploy_compatibility()   <- NEW (FIRST!)
        |                                        |
        v                                        v
[result logged/raised]                   Read from ManifestCache
        |                                        |
        v                                        v
ManifestCache.store()  <- NEW            [COMPATIBLE]  -> proceed
        |                                [WARN]        -> log warning, proceed
        v                                [HARD STOP]   -> return error, deploy nothing
agents fetched to cache                  [NO ENTRY]    -> proceed (fail-open)
                                         [CACHE INIT FAILED] -> proceed (fail-open)
                                                 |
                                                 v
                                         [auto_discover?] -> early return (unchanged set)
                                         [explicit config] -> deploy loop
                                                 |
                                                 v
                                         for agent in to_deploy:
                                             _deploy_agent(agent)
```

---

## 5. Implementation

### 5.0 Change 0: SQLite Hardening (MUST BE FIRST - DA-3)

> **DA-3 fix**: WAL mode must be enabled BEFORE any concurrent read/write
> operations. Since sync (writer) and deploy (reader) can overlap during
> startup, WAL mode must be the first change implemented.

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

**Why first**: Sync writes to ManifestCache and deploy reads from it. Without WAL mode, the reader could see incomplete writes or hit `database is locked` errors. WAL mode is persistent per-database -- once set, all future connections use it automatically.

### 5.1 Change 1: Persist Manifest Check Results at Sync Time

**File**: `src/claude_mpm/services/agents/sources/git_source_sync_service.py`
**Method**: `_check_manifest_compatibility()`
**Change**: After a successful check (any status except skip), store the result in ManifestCache.

#### 5.1.1 Add ManifestCache import

```python
# Add to existing compatibility imports:
from claude_mpm.services.agents.compatibility.manifest_cache import ManifestCache
```

#### 5.1.2 Initialize ManifestCache in `__init__` (with fail-open guard - DA-2)

> **DA-2 fix**: ManifestCache init can fail (permissions, disk, corrupt DB).
> Failure must not prevent sync from working.

```python
# In GitSourceSyncService.__init__, after self.git_manager initialization:
try:
    self._manifest_cache = ManifestCache()
except Exception as e:
    logger.debug("ManifestCache initialization failed: %s. Cache writes disabled.", e)
    self._manifest_cache = None
```

#### 5.1.3 Store result after check

In `_check_manifest_compatibility()`, after the checker runs and before returning or raising, persist the result. Insert after `result = checker.check(manifest_content, __version__)`:

```python
        # Persist manifest check result for deploy-time validation
        if (
            self._manifest_cache is not None
            and manifest_content is not None
            and result.repo_format_version is not None
        ):
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
- `self._manifest_cache` is checked for None before use (DA-2 fail-open guard)

### 5.2 Change 2: Add Deploy-Time Check to DeploymentReconciler

**File**: `src/claude_mpm/services/agents/deployment/deployment_reconciler.py`
**Method**: `reconcile_agents()`
**Change**: Before the deploy loop AND before the auto-discover early return, check manifest compatibility.

#### 5.2.1 Add imports

```python
from claude_mpm.services.agents.compatibility import (
    CompatibilityResult,
    ManifestCheckResult,
)
from claude_mpm.services.agents.compatibility.deploy_gate import DeploymentVersionGate
from claude_mpm.services.agents.compatibility.manifest_cache import ManifestCache
```

#### 5.2.2 Add DeploymentVersionGate to `__init__` (with fail-open guard - DA-2)

> **DA-2 fix**: ManifestCache init can fail. The entire DeploymentReconciler
> must not crash because of a compatibility cache failure.

```python
def __init__(self, config: Optional[UnifiedConfig] = None):
    self.config = config or self._load_config()
    self.path_manager = get_path_manager()
    # Deploy-time manifest compatibility gate (fail-open on init error)
    try:
        self._manifest_cache = ManifestCache()
        self._deploy_gate = DeploymentVersionGate(manifest_cache=self._manifest_cache)
    except Exception as e:
        logger.debug(
            "ManifestCache initialization failed: %s. Deploy-time checks disabled.", e
        )
        self._manifest_cache = None
        self._deploy_gate = None
```

#### 5.2.3 Add deploy-time check in `reconcile_agents()` -- BEFORE auto-discover (DA-1 fix)

> **DA-1 CRITICAL fix**: The original plan placed the gate after the
> auto-discover early return at line 125. This meant the gate was dead code
> for all auto-discover users (the default mode). The gate MUST run before
> the auto-discover branch.

Insert the manifest compatibility check **immediately after `_get_agent_state()`** and **before the auto-discover check**:

```python
    def reconcile_agents(self, project_path: Optional[Path] = None) -> DeploymentResult:
        project_path = project_path or Path.cwd()
        cache_dir = self.path_manager.get_cache_dir() / "agents"
        deploy_dir = project_path / ".claude" / "agents"

        # Get current state
        state = self._get_agent_state(cache_dir, deploy_dir)

        # [DA-1 FIX] Deploy-time manifest compatibility check
        # MUST run before auto-discover early return to cover all code paths
        blocked_sources = self._check_deploy_compatibility()
        if blocked_sources:
            error_msgs = []
            for source_id in blocked_sources:
                error_msgs.append(
                    f"Agent deployment blocked: source '{source_id}' requires "
                    f"a newer CLI. Run: pip install --upgrade claude-mpm"
                )
            for msg in error_msgs:
                logger.error(msg)
            return DeploymentResult(
                deployed=[], removed=[], unchanged=[], errors=error_msgs
            )

        # Check backward compatibility (auto-discover early return)
        if not self.config.agents.enabled and self.config.agents.auto_discover:
            ...  # existing early return logic unchanged
```

#### 5.2.4 New method: `_check_deploy_compatibility()`

```python
    def _check_deploy_compatibility(self) -> Set[str]:
        """Check cached manifest compatibility before deploying agents.

        Reads all cached manifests and re-validates each against the current
        CLI version.  Returns a set of source_ids whose agents should NOT be
        deployed (hard stop only).  Warnings are logged but do not block.

        Fail-open: Returns empty set if cache is unavailable, uninitialized,
        or if __version__ cannot be determined.

        Returns:
            Set of source_ids to skip during deployment.
        """
        # Fail-open: if deploy gate was not initialized (DA-2)
        if self._deploy_gate is None or self._manifest_cache is None:
            return set()

        # Fail-open: env var skip (rollback Tier 1)
        import os
        if os.environ.get("CLAUDE_MPM_SKIP_COMPAT_CHECK", "").lower() in (
            "1", "true", "yes",
        ):
            return set()

        blocked: Set[str] = set()

        try:
            from claude_mpm import __version__
        except ImportError:
            return blocked  # Can't determine version; fail-open

        # Guard against empty/None __version__ in dev builds (DA-7)
        if not __version__:
            return blocked

        try:
            all_cached = self._manifest_cache.get_all()
        except Exception as e:
            logger.debug("ManifestCache read failed: %s. Skipping deploy gate.", e)
            return blocked

        if not all_cached:
            return blocked  # No cached manifests; fail-open

        for entry in all_cached:
            source_id = entry.get("source_id", "unknown")
            raw_content = entry.get("raw_content")

            try:
                result = self._deploy_gate.check_before_deploy(
                    source_id=source_id,
                    cli_version=__version__,
                    cached_manifest_content=raw_content,
                )
            except Exception as e:
                logger.debug(
                    "Deploy gate check failed for source '%s': %s. Skipping.",
                    source_id, e,
                )
                continue  # Fail-open per source

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

##### Option A: Block ALL deploys if ANY source is blocked (simplest) -- RECOMMENDED

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

> **DA-4 correction**: `AgentSyncState.get_all_tracked_files()` does NOT exist.
> The table is `agent_files` (not `tracked_files`) with columns `(source_id,
> file_path, content_sha, local_path, synced_at, file_size)`. Implementing
> Option B requires:
> 1. Adding a new `get_files_by_source()` method to `AgentSyncState`
> 2. Cross-database coordination (`~/.config/claude-mpm/agent_sync.db` for
>    sync state vs `~/.claude-mpm/cache/manifest_cache.db` for manifests)
> 3. Handling agent ID collisions across sources (same agent from two sources)

Corrected schema reference:

```sql
-- In agent_sync_state.db (NOT tracked_files -- that was incorrect):
CREATE TABLE agent_files (
    source_id TEXT NOT NULL,
    file_path TEXT NOT NULL,        -- e.g., "research.md"
    content_sha TEXT NOT NULL,
    local_path TEXT,
    synced_at TEXT NOT NULL,
    file_size INTEGER,
    PRIMARY KEY (source_id, file_path)
);
```

New method needed in `AgentSyncState`:

```python
    def get_files_by_source(self) -> Dict[str, List[str]]:
        """Get all tracked files grouped by source_id.

        Returns:
            Dict mapping source_id to list of file_path strings.
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT source_id, file_path FROM agent_files ORDER BY source_id"
            )
            result: Dict[str, List[str]] = {}
            for row in cursor.fetchall():
                result.setdefault(row["source_id"], []).append(row["file_path"])
            return result
```

Then in DeploymentReconciler:

```python
    def _get_agent_source_map(self) -> Dict[str, str]:
        """Map agent IDs to their source IDs using AgentSyncState."""
        try:
            from claude_mpm.services.agents.sources.agent_sync_state import AgentSyncState
            state = AgentSyncState()
            mapping = {}
            for source_id, files in state.get_files_by_source().items():
                for filename in files:
                    agent_id = Path(filename).stem
                    mapping[agent_id] = source_id
            return mapping
        except Exception as e:
            logger.debug("Failed to build agent-source map: %s", e)
            return {}  # Fail-open
```

**Pros**: Precise per-agent blocking based on actual source.
**Cons**: Requires new method in AgentSyncState, cross-database coordination, agent ID collision handling. Estimated +2 hours over Option A.

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

The `ManifestCache` uses a well-known default path (`~/.claude-mpm/cache/manifest_cache.db`). Both `GitSourceSyncService` (writer) and `DeploymentReconciler` (reader) will independently connect to the same database. SQLite with WAL mode (Change 0) handles concurrent readers correctly.

No change needed in `startup_reconciliation.py` for the initial wiring.

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

### 6.2 New Tests: Deploy-Time Gate (11 tests -- expanded from 8, DA-1/DA-2/DA-7)

| # | Test | Assert |
|---|------|--------|
| W-6 | Compatible cache entry allows deployment | reconcile_agents deploys normally |
| W-7 | INCOMPATIBLE_HARD blocks all deployments | reconcile_agents returns error, no agents deployed |
| W-8 | INCOMPATIBLE_WARN logs warning, deploys proceed | Warning logged, agents deployed |
| W-9 | Empty cache (no entries) deploys normally (fail-open) | reconcile_agents deploys normally |
| W-10 | Multiple sources, one blocked | All agents blocked (Option A behavior) |
| W-11 | `--no-sync` with CLI downgrade triggers re-validation | Synced with CLI v6.0.0, deploy with v5.10.0: gate re-validates cached manifest against current CLI version and detects INCOMPATIBLE_WARN |
| W-12 | CLI downgrade hard-stop scenario | Synced with v6.0.0 CLI (rfv=1), then rfv bumped to 2 in cache, deploy with v5.10.0 -> hard stop |
| W-13 | DeploymentVersionGate.check_before_deploy reads from cache | Verifies raw_content used for re-check |
| W-14 | **[DA-1]** Auto-discover mode still runs deploy gate | `config.agents.enabled=[], auto_discover=True`: gate executes, hard-stop blocks deploy |
| W-15 | **[DA-2]** ManifestCache init failure -> deploy proceeds (fail-open) | Mock ManifestCache() to raise; reconcile_agents deploys normally |
| W-16 | **[DA-7]** `__version__` is None or empty -> fail-open | Mock `__version__` to `None`; deploy proceeds |

### 6.3 New Tests: WAL Mode and Concurrency (3 tests)

| # | Test | Assert |
|---|------|--------|
| W-17 | WAL mode is set on init | PRAGMA journal_mode returns "wal" |
| W-18 | Concurrent reads during write | Two threads can read while one writes |
| W-19 | Busy timeout handles lock contention | No `database is locked` error under 5s contention |

### 6.4 Test Location

```
tests/services/agents/compatibility/test_wiring.py    # W-1 through W-19
```

### 6.5 Existing Tests

All 170 existing compatibility tests must continue to pass. The wiring changes add behavior without modifying existing behavior.

---

## 7. Rollback Plan

### Tier 1: Disable Deploy-Time Check (Immediate)

The env var `CLAUDE_MPM_SKIP_COMPAT_CHECK` already works for sync-time checks. The deploy-time gate also checks it (Section 5.2.4):

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
# Also remove WAL helper files if present:
rm -f ~/.claude-mpm/cache/manifest_cache.db-wal
rm -f ~/.claude-mpm/cache/manifest_cache.db-shm
```

Forces clean state on next sync. Note: this does NOT affect `AgentSyncState` (stored separately in `~/.config/claude-mpm/agent_sync.db`).

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
| **ManifestCache init crashes reconciler (DA-2)** | Low | **Critical** | **Fixed**: Wrapped in try/except; `_manifest_cache=None` disables gate (fail-open). |
| **Auto-discover bypass (DA-1)** | N/A (was guaranteed) | **Critical** | **Fixed**: Gate moved before auto-discover early return. |
| **WAL not ready for concurrent access (DA-3)** | Medium | High | **Fixed**: WAL mode is now Change 0, implemented first. |
| `__version__` is None/empty in dev (DA-7) | Very Low | Low | Guard added in `_check_deploy_compatibility()`. |

### Estimated Effort (revised per DA-9)

| Task | Lines Changed | Time |
|------|--------------|------|
| 5.0: SQLite WAL mode | ~2 lines in manifest_cache.py | 5 min |
| 5.1: Cache at sync time | ~25 lines in git_source_sync_service.py | 30 min |
| 5.2: Gate at deploy time | ~70 lines in deployment_reconciler.py | 1.5 hours |
| 6: Tests (19 tests) | ~330 lines in test_wiring.py | 3 hours |
| Verification | Full test suite run | 30 min |
| **Total** | **~430 lines** | **~5.5 hours** |

---

## 9. Devil's Advocate Findings (v2)

This section documents all findings from the devil's advocate review and how they were addressed in the amended plan.

### DA-1 (CRITICAL): Auto-Discovery Early Return Bypasses Deploy Gate

**Finding**: The original plan placed the deploy gate at line 125, after the auto-discover early return at line 114-123. Since `auto_discover=True` with empty `agents.enabled` is the DEFAULT configuration, the gate was dead code for most users.

**Fix**: Section 5.2.3 now places the gate call immediately after `_get_agent_state()` and before the auto-discover branch. Test W-14 specifically verifies auto-discover mode triggers the gate.

**Status**: FIXED in plan v2.

### DA-2 (HIGH): ManifestCache Init Failure Crashes All Deployment

**Finding**: `ManifestCache()` constructor creates directories and connects to SQLite. If this fails (permissions, disk full, corrupt DB), the entire `DeploymentReconciler` would fail to construct, preventing all agent deployment.

**Fix**: Sections 5.1.2 and 5.2.2 now wrap `ManifestCache()` in try/except, setting it to `None` on failure. Section 5.2.4's `_check_deploy_compatibility()` checks for `None` and returns empty set (fail-open). Test W-15 verifies this.

**Status**: FIXED in plan v2.

### DA-3 (HIGH): WAL Mode Must Be Wired Before Deploy-Time Reads

**Finding**: Sync (writer) and deploy (reader) overlap during startup. Without WAL mode, the reader could see incomplete writes or hit lock contention.

**Fix**: Implementation reordered. WAL mode is now Section 5.0 (Change 0), explicitly marked as the first change to implement.

**Status**: FIXED in plan v2.

### DA-4 (MEDIUM): `get_all_tracked_files()` Doesn't Exist in AgentSyncState

**Finding**: Option B referenced a non-existent method and an incorrect table name (`tracked_files` vs actual `agent_files`).

**Fix**: Section 5.2.5 Option B corrected with actual schema, correct table name, new method signature (`get_files_by_source()`), and updated effort estimate (+2 hours).

**Status**: FIXED in plan v2.

### DA-5 (MEDIUM): Test W-11 Description Was Misleading

**Finding**: W-11 described "staleness" but the plan has no TTL logic. What it actually tests is re-validation against a different CLI version.

**Fix**: W-11 description rewritten to: "Synced with CLI v6.0.0, deploy with v5.10.0: gate re-validates cached manifest against current CLI version and detects INCOMPATIBLE_WARN". The word "staleness" removed.

**Status**: FIXED in plan v2.

### DA-7 (LOW): `__version__` Edge Case (None/Empty)

**Finding**: In development builds, `__version__` could be None or empty string.

**Fix**: Guard added in Section 5.2.4: `if not __version__: return blocked`. Test W-16 verifies this.

**Status**: FIXED in plan v2.

### DA-8 (LOW): Two SQLite Databases in Different Directories

**Finding**: Plan didn't document that ManifestCache and AgentSyncState live in different directories (`~/.claude-mpm/cache/` vs `~/.config/claude-mpm/`).

**Fix**: Added architecture note in Section 2 (Key Architecture Notes) and updated Tier 3 rollback in Section 7 to clarify which database is affected.

**Status**: FIXED in plan v2.

### DA-9 (LOW): Effort Estimate Too Optimistic

**Finding**: Original estimate (200 lines / 2 hours for tests) was too low given integration test fixture complexity and concurrency testing.

**Fix**: Effort table revised upward: 350 lines / 3.5 hours for tests, total ~450 lines / ~6 hours.

**Status**: FIXED in plan v2.
