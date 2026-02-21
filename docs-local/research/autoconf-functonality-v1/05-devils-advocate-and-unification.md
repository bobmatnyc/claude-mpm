# Devil's Advocate Analysis & Unification Strategy

**Date**: 2026-02-21
**Branch**: `ui-agents-skills-config` vs `main`
**Role**: Devil's Advocate / Synthesizer
**Sources**: All four prior research documents + independent codebase verification

---

## Part 1: Devil's Advocate — Challenging the Findings

### 1. Assumptions That Might Be Wrong

#### 1.1 "The CLI auto-configure deploys agents" — IT DOES NOT

**This is the single most critical finding the team understated.**

The researchers correctly noted in passing that `_deploy_single_agent()` is a stub (`asyncio.sleep(0.1)`), and that `_rollback_deployment()` just logs. But they did NOT connect the dots to the catastrophic implication: **the entire `AutoConfigManagerService.auto_configure()` agent deployment pipeline is a no-op**.

Evidence chain:
1. `auto_configure.py:385` → `asyncio.run(self.auto_config_manager.auto_configure(...))`
2. `auto_config_manager.py:295` → `await self._deploy_agents(project_path, recommendations, observer)`
3. `auto_config_manager.py:676` → `await self._deploy_single_agent(agent_id, project_path)`
4. `auto_config_manager.py:695-715` → **STUB**: `await asyncio.sleep(0.1)` + debug log

The `self._agent_deployment` (injected `AgentDeploymentService`) is stored at `__init__` line 98 but **never called anywhere in the class**. The TODO at line 674 says "Integrate with actual AgentDeploymentService" — it was never done.

**Impact**: When a user runs `claude-mpm auto-configure --yes`, the command:
- Analyzes the toolchain ✓
- Recommends agents ✓
- Validates configuration ✓
- Archives unused agents ✓ (separate code path)
- **PRETENDS to deploy agents** ✗ (stub sleeps 0.1s, reports success)
- Deploys skills ✓ (separate code path via `_deploy_skills()`)
- Saves config metadata ✓ (records "deployed" agents that weren't actually deployed)

The `auto-config.yaml` would list agents as "deployed" that don't exist on disk. This is pre-existing debt on `main`, NOT introduced by the dashboard branch.

**Why this matters for the comparison**: The researchers compared "CLI deployment" vs "Dashboard deployment" as if they were two working systems. In reality, the CLI's deployment-through-AutoConfigManagerService is broken, while the dashboard's direct `AgentDeploymentService().deploy_agent()` calls actually work. The "Low Risk" assessment of CLI impact assumed the CLI was working correctly.

#### 1.2 "The preview_configuration() rewrite is Medium Risk" — It's Actually Low Risk

The researchers rated the `preview_configuration()` rewrite as "Medium Risk" with the caveat: "if `_generate_recommendations()` on main contained logic BEYOND just calling `recommend_agents()`, the behavior could differ."

I verified: `_generate_recommendations()` at `auto_config_manager.py:612-620` is a pure delegate:

```python
async def _generate_recommendations(self, toolchain, min_confidence):
    if self._agent_recommender is None:
        raise RuntimeError("AgentRecommender not initialized")
    constraints = {"min_confidence": min_confidence}
    return self._agent_recommender.recommend_agents(toolchain, constraints)
```

The branch replaces this with:

```python
if self._agent_recommender is None:
    raise RuntimeError("AgentRecommender not initialized")
constraints = {"min_confidence": min_confidence}
recommendations = self._agent_recommender.recommend_agents(toolchain, constraints)
```

This is **functionally identical**. The rewrite bypasses the async wrapper to call the same synchronous method directly. The `iscoroutinefunction()` + `run_until_complete()` approach on main was fragile (fails when called from worker threads), and the branch's direct approach is both simpler and more robust.

**Downgrade to: Low Risk**.

#### 1.3 "The agent_management_service path change affects auto-configure" — ~~It Does Not~~ The Path Change Does Not Exist

> **CORRECTION (2026-02-21):** Follow-up investigation found that the path change reported in Document 04 Section 2.6 **does not exist**. Both branches have identical code in `agent_management_service.py`. The original analysis was based on a faulty diff comparison. The two directories serve fundamentally different purposes:
>
> - **`.claude-mpm/agents/`** = MPM internal configuration directory for agent templates/source definitions (currently empty on disk)
> - **`.claude/agents/`** = Claude Code runtime deployment target (44 deployed `.md` files)
>
> There IS a pre-existing bug: `get_path_manager().CONFIG_DIR` references a non-existent attribute (should be `CONFIG_DIR_NAME`), but no production code path reaches it.
>
> The devil's advocate conclusion below that this change "Does Not" affect auto-configure was correct in spirit but accepted a false premise -- the path change itself. The corrected conclusion is: there is no path change to assess, so there is no impact at all.

~~The researchers correctly identified the path change from `.claude-mpm/agents/` to `.claude/agents/` in `AgentManager` but were uncertain about its impact on auto-configure.~~ I verified: `AgentManager` is **NOT used by the auto-configure pipeline at all**. The auto-configure pipeline uses:
- `AutoConfigManagerService` → `AgentRecommenderService` → `AgentRegistry` (for validation)
- `AgentReviewService` → `RemoteAgentDiscoveryService` (for review/archival)
- `AgentDeploymentService` (on dashboard; stub on CLI)

None of these depend on `AgentManager.project_dir`. ~~The path change affects `claude-mpm agents list` and other management commands, not auto-configure.~~

~~**However**: This path change IS significant for other commands. If users have agents in `.claude-mpm/agents/`, `claude-mpm agents list` would stop finding them. This deserves a migration note.~~ *(CORRECTION 2026-02-21: Since the path change does not exist, there is no migration concern for other commands. The pre-existing `CONFIG_DIR` bug is a separate issue that affects neither branch.)*

#### 1.4 "config_file_lock provides concurrency safety" — Partially True

The researchers described `ConfigFileLock` as providing "file-level locking for config writes" but didn't investigate WHERE it's actually used. I verified:

**Used by:**
- `config_sources.py` (source CRUD operations) ✓
- `skill_deployment_handler.py` (skill config writes) ✓

**NOT used by:**
- `autoconfig_handler.py` (the auto-configure flow) ✗
- `agent_deployment_handler.py` (agent deploy/undeploy) ✗
- `backup_manager.py` (backup creation) ✗

**Impact**: The most dangerous concurrent operations — auto-configure applying changes and direct agent deployment — have NO file locking. Two simultaneous dashboard `apply_configuration` requests could race on writing to `.claude/agents/`. The `_active_jobs` dict prevents duplicate job IDs but not concurrent deployments for different configs.

#### 1.5 "Low Risk" Ratings Are Overly Optimistic

The CLI Impact Assessment rated the overall risk as "Low Risk (with caveats)." This assessment treats each change in isolation. But interactions between changes compound risk:

- `preview_configuration()` rewrite + ~~`agent_management_service` path change +~~ `single_agent_deployer` multi-source search = ~~three~~ two simultaneous changes to the agent resolution chain *(CORRECTION 2026-02-21: The agent_management_service path change does not exist. See [1.3 correction](#13-the-agent_management_service-path-change-affects-auto-configure--it-does-not-the-path-change-does-not-exist).)*
- Any one is safe individually, but testing must verify them together
- The test suite correction (`0.8 → 0.5` for `_min_confidence_default`) was marked as "test alignment" — but it raises the question: was the test wrong, or was the code changed at some point without updating the test? If the latter, it suggests fragile test coverage.

### 2. Hidden Risks the Team Missed

#### 2.1 Thread Safety of Module-Level Singletons

The dashboard handlers use module-level `_get_*()` lazy singletons:

```python
_toolchain_analyzer = None

def _get_toolchain_analyzer():
    global _toolchain_analyzer
    if _toolchain_analyzer is None:
        _toolchain_analyzer = ToolchainAnalyzerService()
    return _toolchain_analyzer
```

This is a classic **check-then-act race condition**. Two concurrent requests hitting `_get_toolchain_analyzer()` simultaneously could both see `None` and both create instances. In aiohttp with `asyncio.to_thread()`, multiple threads CAN execute concurrently.

**Probability**: Low (aiohttp typically uses a single event loop), but the use of `asyncio.to_thread()` means worker threads ARE running concurrently. If two requests arrive simultaneously and both trigger lazy init, you get two `ToolchainAnalyzerService` instances, with only one stored as the singleton.

**Severity**: Low (double initialization wastes memory but doesn't corrupt state — each instance is independent). But it violates the singleton assumption.

**Fix**: Use `threading.Lock()` around the lazy init, or initialize singletons eagerly at server startup.

#### 2.2 BackupManager Uses `Path.cwd()` at Init Time

The `BackupManager.__init__()` defaults to:
```python
self.agents_dir = agents_dir or resolve_agents_dir(ConfigScope.PROJECT, Path.cwd())
self.skills_dir = skills_dir or resolve_skills_dir()  # defaults to Path.cwd()
```

Since `BackupManager` is a module-level singleton (initialized once), it captures `Path.cwd()` at the time of first request. If the server's working directory changes (unlikely but possible), or if the dashboard is serving multiple projects (a documented future feature per `docs/issues/dashboard-multi-project-awareness.md`), all backups would target the wrong directory.

The `autoconfig_handler.py` creates backups via `_get_backup_manager().create_backup(...)` but the BackupManager's `agents_dir` is locked to the CWD at init time, NOT the `project_path` from the request.

**More critically**: The backup copies `self.agents_dir` (project agents) but the auto-configure deploys to `resolve_agents_dir(ConfigScope.PROJECT, project_path)` where `project_path` comes from the request body. If `project_path != Path.cwd()`, the backup backs up the WRONG directory.

#### 2.3 DeploymentVerifier Also Uses `Path.cwd()` at Init Time

Same issue: `DeploymentVerifier.__init__()` defaults to:
```python
self.default_agents_dir = agents_dir or resolve_agents_dir(ConfigScope.PROJECT, Path.cwd())
```

The verification phase in `_run_auto_configure()` creates a new `DeploymentVerifier()` each time (not the singleton), but the construction again uses `Path.cwd()`, not the `project_path` from the request.

#### 2.4 No Cleanup of Failed Background Tasks

`_active_jobs` tracks in-flight jobs but has no timeout mechanism:
```python
_active_jobs: Dict[str, asyncio.Task] = {}
```

If a background task hangs (e.g., `deploy_agent()` blocks forever on a network call or file lock), the job entry is never cleaned up (the `finally` block only runs when the task completes or raises). There's no watchdog, no max-job limit, and no way to cancel a running job from the API.

#### 2.5 Duplicate AutoConfigManagerService Construction in Apply Flow

The `_run_auto_configure()` background task at Phase 2 calls:
```python
preview = await asyncio.to_thread(_preview)  # _get_auto_config_manager().preview_configuration(...)
```

This calls `preview_configuration()` AGAIN internally, which re-runs `analyze_toolchain()` and `recommend_agents()`. But Phase 1 already called `_get_toolchain_analyzer().analyze_toolchain()` separately. So toolchain analysis runs TWICE:
1. Phase 1: `_detect()` → `_get_toolchain_analyzer().analyze_toolchain(project_path)` → result discarded after progress event
2. Phase 2: `_preview()` → `_get_auto_config_manager().preview_configuration()` → internally calls `analyze_toolchain()` again

The ToolchainAnalyzerService has a 5-minute cache, so the second call is a cache hit. But it's wasteful and the Phase 1 result (`_analysis`) is stored in a variable but never used (it's only there for the progress event).

#### 2.6 Error Event Has Empty deployed_before_failure

When `_run_auto_configure()` fails, it emits:
```python
"deployed_before_failure": [],
```

This is ALWAYS an empty list, even if some agents were deployed before the failure. The actual `deployed_agents` list is only available inside the try block's local scope and isn't captured in the except handler. This means the backup ID is provided for manual restore, but the user has no idea WHICH agents were deployed before the failure.

### 3. Edge Cases and Failure Modes

#### 3.1 Empty Project / No Language Detected

When `analyze_toolchain()` finds no recognizable language:
- **CLI**: Returns `ToolchainAnalysis` with `primary_language="Unknown"`, `overall_confidence=VERY_LOW`
- **AgentRecommenderService**: Falls back to default configuration from YAML (default agents with confidence 0.7)
- **Effect**: Auto-configure still recommends default agents. This is probably fine but should be explicit.

#### 3.2 Massive Project (>100K files)

The `ToolchainAnalyzerService` iterates through detection strategies, each of which globs for files. For a massive monorepo:
- Framework detection (`detect_frameworks()`) globs for `**/*.py`, `**/*.ts`, etc.
- Development tool detection checks for numerous config files
- No explicit timeout or file count limit
- 5-minute cache means a slow first analysis could block the thread for minutes

The dashboard wraps this in `asyncio.to_thread()`, so it won't block the event loop, but it WILL consume a worker thread for the duration.

#### 3.3 Corrupted or Partially Written Config Files

If `auto-config.yaml` or `agent_sources.yaml` is corrupted (e.g., process killed mid-write on main, which doesn't use atomic writes):
- `agent_sources.py` on the branch uses atomic writes (write-to-temp + rename). Good.
- `auto_config_manager.py:790` still uses plain `open()` + `yaml.dump()` — NOT atomic. A crash here corrupts the file.
- The BackupManager writes `metadata.json` with plain `write_text()` — not atomic, but less critical.

#### 3.4 CLI and Dashboard Running Simultaneously

This is the most dangerous scenario. If a user has the dashboard open AND runs `claude-mpm auto-configure` in the terminal:

1. **No coordination**: CLI and dashboard have separate service instances. No shared state. No file locking from the CLI side (CLI doesn't use `config_file_lock`).
2. **Race on .claude/agents/**: Both could write agent files simultaneously. Last write wins.
3. **ConfigFileWatcher false positive**: Dashboard's 5s mtime poll would detect CLI changes as "external changes" and trigger a refresh. This is actually GOOD — it's the intended behavior.
4. **Backup divergence**: Dashboard takes a backup; CLI does not. If CLI corrupts agents, dashboard backup is stale.
5. **auto-config.yaml conflict**: CLI writes this file. Dashboard does not. No conflict, but the metadata could become stale.

#### 3.5 Monorepo / Multi-Project

If `project_path` is a monorepo root with multiple sub-projects:
- `ToolchainAnalyzerService` analyzes the root directory
- It would detect multiple languages but can only report one "primary"
- Recommendations would be for the root, not individual sub-projects
- Dashboard's `project_path` comes from the request body, defaulting to `Path.cwd()`
- No sub-project awareness

#### 3.6 Two Backups in the Same Second

The `BackupManager` handles this:
```python
if backup_dir.exists():
    backup_id = now.strftime("%Y-%m-%dT%H-%M-%S") + "-1"
```

But only handles ONE collision by appending "-1". Three rapid backups in the same second would collide on the "-1" suffix. Low probability but possible under automated testing or rapid UI clicking.

### 4. Pre-existing Technical Debt

#### 4.1 The Parallel Systems Problem Is WORSE Than Reported

The researchers identified four parallel systems. But the full picture is more complex:

| Concern | System 1 (Modern/Auto-configure) | System 2 (Legacy/Other) | System 3 (Dashboard-New) |
|---------|----------------------------------|------------------------|-------------------------|
| **Toolchain Detection** | `ToolchainAnalyzerService` | `ToolchainDetector` (legacy) | — (reuses System 1) |
| **Agent Recommendation** | `AgentRecommenderService` | `AgentRecommendationService` | — (reuses System 1) |
| **Skill Recommendation** | `AGENT_SKILL_MAPPING` (dict) | `SkillRecommendationEngine` (scoring) | — (reuses dict from System 1) |
| **Tech Stack Detection** | `ToolchainAnalyzerService` | `ProjectInspector` | — (reuses System 1) |
| **Agent Deployment** | `AutoConfigManagerService._deploy_single_agent()` (**STUB**) | `AgentDeploymentService` (real) | Direct `AgentDeploymentService` calls |
| **DI Pattern** | Property lazy-load | Varies | Module-level singletons |
| **Path Resolution** | Hardcoded / `get_path_manager()` | `get_path_manager()` | `ConfigScope` enum |
| **Safety** | None (no backup, no lock, no verify) | None | BackupManager, OperationJournal, DeploymentVerifier, ConfigFileLock |

The dashboard branch makes this better by:
- Reusing the correct modern services (System 1)
- Adding safety infrastructure that didn't exist
- Introducing `ConfigScope` for centralized path resolution

The dashboard branch makes this worse by:
- Adding a THIRD DI pattern (module-level singletons alongside property lazy-load and container-based)
- Duplicating the `_get_backup_manager()` / `_get_operation_journal()` / `_get_deployment_verifier()` factory functions across THREE handler modules
- Not consolidating the parallel systems (all four duplications persist)

#### 4.2 Agent Deployment is Fragmented

The actual agent deployment logic exists in THREE places:
1. `AutoConfigManagerService._deploy_single_agent()` — **STUB** (CLI uses this)
2. `AgentDeploymentService.deploy_agent()` — **REAL** (dashboard calls this directly)
3. `SingleAgentDeployer._deploy_single_agent()` — **REAL** (called by AgentDeploymentService)

The dashboard correctly bypasses the stub (#1) and calls the real service (#2). But the CLI still goes through the stub. This means **the CLI and dashboard produce different results for the same auto-configure operation**.

#### 4.3 Skills Deployment Directory Split

| Path | CLI Default | Dashboard Default |
|------|------------|-------------------|
| Skills target | `~/.claude/skills/` (user-level) | `<project>/.claude/skills/` (project-level) |

This is a **design disagreement**, not just a technical gap. The CLI installs skills globally (affecting all projects). The dashboard installs skills per-project (isolated but duplicated). A user who auto-configures via CLI, then checks the dashboard, would see skills as "not deployed" (dashboard checks project dir, CLI deployed to user dir).

### 5. What the "Low Risk" Assessment Ignores

#### 5.1 "Low risk for CLI" ≠ "Low risk overall"

The CLI Impact Assessment correctly concludes that the dashboard branch doesn't break the CLI. But this ignores:

- **The CLI auto-configure agent deployment was already broken** (stub). The branch doesn't fix this.
- **The dashboard introduces 3,000+ lines of new code** with its own bugs, which weren't assessed for quality.
- **Architectural divergence** between CLI and dashboard will make future maintenance harder.

#### 5.2 Dashboard Code Quality Concerns

Issues I found in the dashboard code that weren't assessed:

1. **No rate limiting on API endpoints**: An attacker or misconfigured client could trigger hundreds of simultaneous auto-configure jobs.
2. **`_active_jobs` has no size limit**: Could consume unbounded memory.
3. **`body = {}` fallback on parse failure**: Silent failure when request body is malformed JSON. This is defensive but masks real errors.
4. **Phase 1 result discarded**: Toolchain analysis runs twice (once in Phase 1 for progress, once in Phase 2 via `preview_configuration()`).
5. **`__import__()` used for DeploymentVerifier**: At `autoconfig_handler.py` Phase 6, `__import__("claude_mpm.services.config_api.deployment_verifier", ...)` is used instead of a standard import. This is fragile and bypasses IDE tooling.

#### 5.3 Architectural Patterns That Will Scale Poorly

1. **Module-level singletons**: Adding a new handler requires copy-pasting the `_get_*()` functions. Already duplicated across 3 files.
2. **No DI container**: Each handler independently constructs its dependency tree. Changing a shared service (e.g., adding a constructor parameter to BackupManager) requires updates in 3+ places.
3. **Socket.IO coupling**: The auto-configure flow is tightly coupled to Socket.IO for progress reporting. Testing requires mocking the event handler. Adding a different transport (WebSocket, SSE) would require rewriting the flow.
4. **No request context**: The handlers use `Path.cwd()` as default project path. In a multi-project scenario, this is incorrect. The project path should be a required parameter, not optional.

---

## Part 2: Unification Strategy

### 6. Recommended Architecture

#### 6.1 Single Auto-Configuration Engine

Create a unified `AutoConfigurationEngine` that serves both CLI and dashboard:

```
AutoConfigurationEngine (NEW)
├── analyze(project_path) → ToolchainAnalysis
├── recommend(toolchain, min_confidence) → List[AgentRecommendation]
├── recommend_skills(agent_ids) → List[str]
├── validate(recommendations) → ValidationResult
├── preview(project_path, min_confidence) → ConfigurationPreview
├── apply(project_path, preview, observer) → ConfigurationResult
│   ├── backup(project_path) → BackupResult
│   ├── deploy_agents(agent_ids, project_path) → DeployResult
│   ├── deploy_skills(skill_names, project_path) → DeployResult
│   ├── verify(deployed, project_path) → VerificationResult
│   └── rollback(backup_id) → RestoreResult
└── cancel(job_id) → bool
```

**Key design decisions:**

1. **All methods are synchronous** (no async). The engine does I/O-bound work (file reads, file writes). The caller decides the threading model.
2. **Observer pattern for progress**: Both CLI and dashboard provide their own observer. CLI uses `RichProgressObserver`. Dashboard uses `SocketIOProgressObserver`.
3. **Project path is always required**: No `Path.cwd()` defaults. The caller must specify.
4. **Safety infrastructure is shared**: BackupManager, OperationJournal, DeploymentVerifier are used by both CLI and dashboard, not dashboard-only.

#### 6.2 Async vs Sync Interface

```python
# CLI usage (synchronous):
engine = AutoConfigurationEngine(project_path)
preview = engine.preview(min_confidence=0.5)
result = engine.apply(preview, observer=RichProgressObserver(console))

# Dashboard usage (async wrapper):
async def apply_configuration(request):
    engine = AutoConfigurationEngine(project_path)
    preview = await asyncio.to_thread(engine.preview, min_confidence)
    result = await asyncio.to_thread(engine.apply, preview, observer)
```

The engine itself is synchronous. The dashboard wraps calls in `asyncio.to_thread()`. This eliminates the current problem of mixing async/sync patterns.

#### 6.3 Sharing Safety Infrastructure

```python
# Safety services injected into engine:
engine = AutoConfigurationEngine(
    project_path=project_path,
    backup_manager=BackupManager(project_path=project_path),
    operation_journal=OperationJournal(),
    deployment_verifier=DeploymentVerifier(project_path=project_path),
    agent_deployer=AgentDeploymentService(),
    skills_deployer=SkillsDeployerService(),
)
```

The CLI would use these by default (currently has no safety at all). The `--no-backup` flag could skip backups for advanced users.

### 7. Which Parallel Systems to Consolidate

| Duplicated System | Keep | Remove | Justification |
|-------------------|------|--------|---------------|
| **ToolchainAnalyzerService** (modern) | ✅ Keep | — | Strategy pattern, rich data model, used by both paths |
| **ToolchainDetector** (legacy) | — | ❌ Remove | Simpler but duplicates functionality. Migrate `AgentSelectionService` to use `ToolchainAnalyzerService` |
| **AgentRecommenderService** (YAML-config) | ✅ Keep | — | Configuration-driven, scoring algorithm, used by both paths |
| **AgentRecommendationService** (alt) | — | ❌ Remove | Used only by legacy interactive wizard. Migrate `configure` command to use `AgentRecommenderService` |
| **AGENT_SKILL_MAPPING** (dict) | — | ❌ Remove | Too simplistic. Static mapping doesn't use skill manifest or scoring |
| **SkillRecommendationEngine** (scoring) | ✅ Keep | — | Richer: uses manifest, scoring, priority patterns. Wire into auto-configure |
| **ProjectInspector** (alt tech detection) | — | ❌ Remove | Duplicates `ToolchainAnalyzerService`. Create adapter from `ToolchainAnalysis` → `TechnologyStack` if SkillRecommendationEngine needs it |

### 8. Step-by-Step Refactoring Plan

#### Phase 0: Fix the CLI Deployment Stub (URGENT)
**Risk**: Low | **Verify**: Run `claude-mpm auto-configure --yes` on a Python project, check `.claude/agents/` for files

1. In `AutoConfigManagerService._deploy_agents()`, replace the stub `_deploy_single_agent()` call with actual `AgentDeploymentService.deploy_agent()` call
2. Remove the `_deploy_single_agent()` stub method
3. Pass `agents_dir` from `project_path / ".claude" / "agents"` into the deploy call
4. Test: `claude-mpm auto-configure --preview` shows agents → `--yes` actually creates files in `.claude/agents/`

**Rollback**: Revert the method change. No files are affected (current behavior is a no-op).

#### Phase 1: Extract Shared Skill Recommendation Function
**Risk**: Low | **Verify**: Run both CLI preview and dashboard preview, compare skill lists

1. Create `services/skills/skill_recommender.py` with `recommend_skills_for_agents(agent_ids: List[str]) -> List[str]`
2. This function initially wraps `AGENT_SKILL_MAPPING` (preserving current behavior)
3. Update `auto_configure.py:875-898` to call the shared function
4. Update `autoconfig_handler.py:297-306` and `autoconfig_handler.py:561-569` to call the shared function
5. Test: Same skill recommendations from CLI and dashboard for identical agent sets

**Rollback**: Revert imports. The dict is unchanged.

#### Phase 2: Share Safety Infrastructure with CLI
**Risk**: Medium | **Verify**: Run `claude-mpm auto-configure --yes`, check `~/.claude-mpm/backups/` exists

1. Add `--no-backup` flag to CLI parser (opt-out)
2. In `AutoConfigureCommand._run_full_configuration()`, add BackupManager call before deployment
3. Add DeploymentVerifier call after deployment
4. CLI now creates backups before destructive operations
5. Test: Backup directory created, agent files verified post-deploy

**Rollback**: Remove the backup/verify calls. No CLI behavior change (was previously no-op).

#### Phase 3: Consolidate DI Pattern
**Risk**: Medium | **Verify**: All tests pass, dashboard endpoints respond correctly

1. Create `services/config_api/service_factory.py` with a single `ServiceFactory` class
2. Move all `_get_*()` functions from `autoconfig_handler.py`, `agent_deployment_handler.py`, `skill_deployment_handler.py` into the factory
3. Factory manages singleton lifecycle with proper thread safety (`threading.Lock`)
4. Each handler imports from the factory instead of maintaining its own singletons
5. Test: Hit all endpoints, verify same behavior

**Rollback**: Revert to module-level singletons. Copy `_get_*()` functions back.

#### Phase 4: Wire SkillRecommendationEngine into Auto-Configure
**Risk**: Medium | **Verify**: Compare skill recommendations before/after, ensure quality improves

1. Create adapter: `ToolchainAnalysis` → `TechnologyStack` conversion function
2. In `recommend_skills_for_agents()`, add option to use `SkillRecommendationEngine` when manifest is available
3. Fall back to `AGENT_SKILL_MAPPING` dict when manifest is unavailable
4. Test: With manifest present, recommendations include priority and justification

**Rollback**: Set feature flag to use dict-only path.

#### Phase 5: Remove Legacy Systems
**Risk**: High | **Verify**: Full test suite passes, `claude-mpm configure` still works

1. Migrate `configure` command to use `AgentRecommenderService` instead of `AgentRecommendationService`
2. Migrate `AgentSelectionService` to use `ToolchainAnalyzerService` instead of `ToolchainDetector`
3. Remove `ToolchainDetector`, `AgentRecommendationService`, `ProjectInspector`
4. Remove `AGENT_SKILL_MAPPING` dict (now replaced by `SkillRecommendationEngine` with dict fallback)
5. Test: ALL commands that used legacy services still work

**Rollback**: Re-add legacy files. Imports still work.

#### Phase 6: Unify Path Resolution
**Risk**: Low | **Verify**: Agent/skill paths resolve correctly in all scenarios

> **CORRECTION (2026-02-21):** Item 2 below references `get_path_manager().CONFIG_DIR / "agents"` as a pattern to replace. While this pattern does exist in `agent_management_service.py`, it contains a pre-existing bug: `CONFIG_DIR` is a non-existent attribute (should be `CONFIG_DIR_NAME`). This was NOT introduced by the dashboard branch -- it exists identically on both branches. The recommendation to adopt `resolve_agents_dir()` remains valid but the motivation is fixing the pre-existing bug, not addressing a branch divergence.

1. Adopt `ConfigScope` in CLI commands that currently use hardcoded paths
2. Replace `get_path_manager().CONFIG_DIR / "agents"` patterns with `resolve_agents_dir()` *(Note: `CONFIG_DIR` is a pre-existing bug -- should be `CONFIG_DIR_NAME`. See correction above.)*
3. Ensure both CLI and dashboard use the same path resolution for agents and skills
4. Decide: skills go to project-level or user-level? (Recommendation: project-level with fallback to user-level)
5. Test: Both CLI and dashboard deploy to the same directories

**Rollback**: Revert to hardcoded paths.

### 9. What to Keep, Merge, and Remove

| Component | Action | Justification |
|-----------|--------|---------------|
| `ToolchainAnalyzerService` | **Keep** | Modern, Strategy pattern, used by both paths |
| `ToolchainDetector` | **Remove** | Legacy, replaced by ToolchainAnalyzerService |
| `AgentRecommenderService` | **Keep** | YAML-config driven, scoring algorithm |
| `AgentRecommendationService` | **Remove** | Legacy, migrate consumers to AgentRecommenderService |
| `AGENT_SKILL_MAPPING` dict | **Remove** (Phase 4) | Replace with SkillRecommendationEngine + dict fallback |
| `SkillRecommendationEngine` | **Keep + Promote** | More sophisticated, should be the primary system |
| `ProjectInspector` | **Remove** | Replace with adapter from ToolchainAnalysis |
| `AutoConfigManagerService.auto_configure()` | **Fix** (Phase 0) | Wire to real AgentDeploymentService |
| `AutoConfigManagerService._deploy_single_agent()` | **Remove** | Stub. Replace with real deployment call |
| `AutoConfigManagerService._rollback_deployment()` | **Replace** | Stub. Replace with BackupManager.restore_from_backup() |
| `BackupManager` | **Keep + Share** | Bring to CLI (Phase 2) |
| `OperationJournal` | **Keep + Share** | Bring to CLI (Phase 2) |
| `DeploymentVerifier` | **Keep + Share** | Bring to CLI (Phase 2) |
| `ConfigFileLock` | **Keep + Extend** | Add to autoconfig_handler and agent_deployment_handler |
| `ConfigScope` | **Keep + Adopt** | Adopt in CLI to replace hardcoded paths |
| Module-level singletons | **Merge → ServiceFactory** | Consolidate into single factory (Phase 3) |
| `RichProgressObserver` | **Keep** | CLI-specific, appropriate |
| Socket.IO progress events | **Keep** | Dashboard-specific, appropriate |
| Feature flags (`features.ts`) | **Keep** | Dashboard-specific, good practice |
| `ConfigFileWatcher` | **Keep** | Dashboard-specific, detects external changes |

### 10. Testing Strategy

#### 10.1 Verify Unification Doesn't Break CLI

| Test | Command | Expected |
|------|---------|----------|
| Preview mode | `claude-mpm auto-configure --preview` | Shows toolchain, agents, skills. No files written. |
| Full deploy | `claude-mpm auto-configure --yes` | Creates agent files in `.claude/agents/`, skill files in `.claude/skills/`, backup in `~/.claude-mpm/backups/` |
| Min confidence | `claude-mpm auto-configure --min-confidence 0.0 --preview` | Shows ALL agents regardless of score |
| JSON output | `claude-mpm auto-configure --preview --json` | Valid JSON with expected schema |
| Agents only | `claude-mpm auto-configure --agents-only --yes` | Only agents deployed, no skills |
| Skills only | `claude-mpm auto-configure --skills-only --yes` | Only skills deployed, no agents |
| Empty project | `cd /tmp/empty && claude-mpm auto-configure --preview` | Graceful handling, default recommendations |
| Already configured | Run auto-configure twice | Idempotent, no errors |

#### 10.2 Verify Unification Doesn't Break Dashboard

| Test | Endpoint | Expected |
|------|----------|----------|
| Detect | `POST /api/config/auto-configure/detect` | Returns toolchain analysis |
| Preview | `POST /api/config/auto-configure/preview` | Returns recommendations + skills |
| Apply | `POST /api/config/auto-configure/apply` | Returns 202, emits progress events, creates files |
| Apply dry-run | `POST .../apply {"dry_run": true}` | Returns 202, emits completion, no files written |
| Concurrent applies | Two simultaneous apply requests | Second request should be rejected or queued |
| Invalid project path | `POST .../detect {"project_path": "/nonexistent"}` | Returns 400 |
| Agent deploy | `POST /api/config/agents/deploy {"agent_name": "engineer"}` | Deploys with backup + verify |
| Core agent undeploy | `DELETE /api/config/agents/engineer` | Returns 400 (protected) |

#### 10.3 Integration Test Design

```python
# Key integration test: CLI and Dashboard produce equivalent results
def test_cli_dashboard_equivalence():
    """Both paths should recommend the same agents for the same project."""
    project_path = create_test_project("python-fastapi")

    # CLI path
    cli_preview = run_cli_preview(project_path, min_confidence=0.5)

    # Dashboard path
    api_preview = call_api_preview(project_path, min_confidence=0.5)

    # Results should match
    assert set(cli_preview.would_deploy) == set(api_preview["would_deploy"])
    assert set(cli_preview.skills) == set(api_preview["skill_recommendations"])
```

#### 10.4 Regression Test Checklist

- [ ] All existing tests in `tests/services/agents/test_auto_config_manager.py` pass
- [ ] All existing tests in `tests/e2e/test_autoconfig_full_flow.py` pass
- [ ] All existing tests in `tests/services/config_api/test_autoconfig_*.py` pass
- [ ] `claude-mpm auto-configure --preview` works on Python, Node.js, Rust, Go projects
- [ ] `claude-mpm auto-configure --yes` creates actual agent files (post Phase 0)
- [ ] Dashboard auto-configure creates agent files with backup
- [ ] Skills deployed to consistent directory (project-level) by both paths
- [ ] Backup created before destructive operations by both paths
- [ ] `claude-mpm agents list` shows correct agents after auto-configure
- [ ] `claude-mpm doctor` passes after auto-configure

### 11. Open Questions

1. **Should the CLI auto-configure deployment stub be considered a blocking bug?** The CLI currently "deploys" agents but actually does nothing. Users may not realize agents weren't deployed. Priority: **URGENT**.

2. **Skills directory: project-level or user-level?** The CLI uses `~/.claude/skills/` (shared), the dashboard uses `<project>/.claude/skills/` (isolated). Which is correct? Claude Code supports both. **Recommendation**: Default to project-level (isolated) with `--global` flag for user-level.

3. **Should the CLI use file locking?** The `config_file_lock` exists but the CLI doesn't use it. If both CLI and dashboard modify agents, should they coordinate? **Recommendation**: Yes, at least for config file writes. Agent `.md` file writes are less critical (last write wins is acceptable for idempotent deploys).

4. **Multi-project support timeline**: The `BackupManager` and `DeploymentVerifier` hardcode `Path.cwd()` at init. Is multi-project dashboard support planned? If so, these need to accept `project_path` per-operation.

5. **Should `AgentRecommendationService` and `ToolchainDetector` be removed in this PR or a follow-up?** Removing legacy systems is high-risk. **Recommendation**: Follow-up PR after the dashboard branch is merged and stable.

6. **Should the auto-configure flow use the sophisticated `SkillRecommendationEngine` or continue with `AGENT_SKILL_MAPPING`?** The engine is more capable but adds complexity. **Recommendation**: Phase 4 adds it as an optional enhancement with dict fallback.

7. **How should concurrent auto-configure requests be handled?** Currently no dedup or queuing. **Recommendation**: At minimum, prevent two apply operations for the same project simultaneously. Use job ID + project path as a compound key.

8. ~~**What is the migration path for the `.claude-mpm/agents/` → `.claude/agents/` path change in AgentManager?** Users with agents in the old location need guidance. **Recommendation**: Add a migration check in `claude-mpm doctor` that detects agents in the old path and suggests moving them.~~

> **CORRECTION (2026-02-21):** This question is **moot**. The `.claude-mpm/agents/` to `.claude/agents/` path change does not exist -- both branches have identical code in `agent_management_service.py`. The two directories serve entirely different purposes (`.claude-mpm/agents/` = MPM internal config/templates; `.claude/agents/` = Claude Code runtime deployment target). There is no migration needed because there is no path change. See Document 04, Section 2.6 correction for full details.

---

## Summary: Critical Priorities

| Priority | Issue | Owner | Effort |
|----------|-------|-------|--------|
| **P0** | Fix CLI deployment stub (agents not actually deployed) | Backend | Small |
| **P0** | Decide skills directory (project vs user) | Architecture | Decision |
| **P1** | Add file locking to autoconfig_handler apply flow | Backend | Small |
| **P1** | Fix BackupManager Path.cwd() hardcoding | Backend | Small |
| **P1** | Fix deployed_before_failure empty list in error event | Backend | Small |
| **P2** | Share safety infrastructure with CLI | Backend | Medium |
| **P2** | Consolidate DI pattern into ServiceFactory | Backend | Medium |
| **P2** | Extract shared skill recommendation function | Backend | Small |
| **P3** | Wire SkillRecommendationEngine into auto-configure | Backend | Medium |
| **P3** | Remove legacy parallel systems | Backend | Large |
| **P3** | Add thread safety to singleton initialization | Backend | Small |
