# Auto-Configuration: CLI vs Dashboard Code Path Comparison

**Date**: 2026-02-21
**Branch**: `ui-agents-skills-config` (contains both CLI and Dashboard code)
**Sources**: `01-main-branch-cli-path.md`, `02-dashboard-branch-api-path.md`, plus direct codebase verification

---

## 1. Shared Code (Used by BOTH Paths)

These modules are imported and executed by **both** the CLI and Dashboard auto-configure flows:

| Module | Class/Function | CLI Import Location | Dashboard Import Location | Notes |
|--------|---------------|---------------------|---------------------------|-------|
| `services/project/toolchain_analyzer.py` | `ToolchainAnalyzerService` | `cli/commands/auto_configure.py:125` | `services/config_api/autoconfig_handler.py:41-46` | **Separate instances** - not shared at runtime |
| `services/project/detection_strategies.py` | `PythonDetectionStrategy`, `NodeJSDetectionStrategy`, `RustDetectionStrategy`, `GoDetectionStrategy` | Via `ToolchainAnalyzerService._register_default_strategies()` | Same (via same `ToolchainAnalyzerService`) | Identical strategy set |
| `services/agents/auto_config_manager.py` | `AutoConfigManagerService` | `cli/commands/auto_configure.py:122` | `services/config_api/autoconfig_handler.py:53-84` | **Separate instances** with different DI |
| `services/agents/recommender.py` | `AgentRecommenderService` | `cli/commands/auto_configure.py:123` | `services/config_api/autoconfig_handler.py:57-62` | **Separate instances** |
| `services/agents/registry.py` | `AgentRegistry` | `cli/commands/auto_configure.py:124` (required) | `services/config_api/autoconfig_handler.py:68-74` (optional) | CLI requires it; dashboard degrades gracefully |
| `config/agent_capabilities.yaml` | (data file) | Via `AgentRecommenderService` | Via `AgentRecommenderService` | Same YAML config |
| `services/core/models/toolchain.py` | `ToolchainAnalysis`, `LanguageDetection`, etc. | Via `ToolchainAnalyzerService` | Via `ToolchainAnalyzerService` | Same data models |
| `services/core/models/agent_config.py` | `AgentRecommendation`, `ConfigurationPreview`, `ConfigurationResult`, `ValidationResult` | Direct usage in command | Via `AutoConfigManagerService` (serialized to dict) | Dashboard adds serialization layer |
| `cli/interactive/skills_wizard.py` | `AGENT_SKILL_MAPPING` | `cli/commands/auto_configure.py:888` | `services/config_api/autoconfig_handler.py:299,563` | **Same data dict** - dashboard imports from CLI module |
| `services/skills_deployer.py` | `SkillsDeployerService` | `cli/commands/auto_configure.py:153` | `services/config_api/autoconfig_handler.py:106-108` | **Separate instances**; dashboard passes `skills_dir` override |
| `services/agents/observers.py` | `NullObserver`, `IDeploymentObserver` | `cli/commands/auto_configure.py:33` | Not used | CLI defines `RichProgressObserver`; Dashboard uses Socket.IO instead |

### Runtime Sharing Summary

Despite importing the same modules, the CLI and Dashboard **never share service instances at runtime**. Each path creates its own:
- `ToolchainAnalyzerService` (each has independent 5-min cache)
- `AutoConfigManagerService`
- `AgentRecommenderService`
- `SkillsDeployerService`

Communication between paths occurs **only through the filesystem** (deployed `.md` files, skills directories, config YAML).

---

## 2. Duplicated Logic (Reimplemented Instead of Reused)

These are cases where the **same concept** is implemented differently in each path:

| Concept | CLI Implementation | Dashboard Implementation | Duplication Type |
|---------|-------------------|--------------------------|------------------|
| **Skill recommendation from agents** | `AutoConfigureCommand._recommend_skills()` at `auto_configure.py:875-898` | `autoconfig_handler.py:297-306` (`_recommend_skills_for_preview`) and `autoconfig_handler.py:561-569` (`_recommend_and_deploy_skills`) | Logic duplicated 3x total (1 CLI + 2 dashboard). All iterate `AGENT_SKILL_MAPPING` identically |
| **Service instantiation (DI)** | `@property` lazy-loading on `AutoConfigureCommand` at `auto_configure.py:118-156` | Module-level `_get_*()` lazy singletons in `autoconfig_handler.py:38-109` | Same services, different DI patterns |
| **Serialization of `ConfigurationPreview`** | Direct attribute access in `_display_preview()` / `_output_preview_json()` at `auto_configure.py:407-834` | `_preview_to_dict()` at `autoconfig_handler.py:175-215` | CLI reads dataclass attrs directly; Dashboard serializes to dict for JSON |
| **Serialization of `ToolchainAnalysis`** | Rich table rendering in `_display_preview()` at `auto_configure.py:431-461` | `_toolchain_to_dict()` at `autoconfig_handler.py:119-172` | CLI renders to terminal; Dashboard serializes to dict |
| **Error handling pattern** | `try/except` with `CommandResult.error_result()` | `try/except` with `_error_response(status, error, code)` | Different error response shapes |
| **Progress reporting** | `RichProgressObserver` (Observer pattern) at `auto_configure.py:37-97` | `_emit_progress()` (Socket.IO events) at `autoconfig_handler.py:391-418` | Fundamentally different transport mechanisms |
| **User confirmation** | Interactive `y/n/s` prompt at `auto_configure.py:554-607` | Type "apply" in UI modal (`AutoConfigPreview.svelte`) | UI-specific, not really duplicated |
| **min_confidence default** | `auto_configure.py:198-201` (0.5) | `autoconfig_handler.py:280,341` (0.5) | Same default, hardcoded in both places |

### Key Extraction Opportunity

The skill-recommendation-from-agents logic is the strongest candidate for deduplication. A shared function like:

```python
def recommend_skills_for_agents(agent_ids: List[str]) -> List[str]:
    from claude_mpm.cli.interactive.skills_wizard import AGENT_SKILL_MAPPING
    skills = set()
    for aid in agent_ids:
        skills.update(AGENT_SKILL_MAPPING.get(aid, []))
    return sorted(skills)
```

...would eliminate 3 near-identical implementations.

---

## 3. Dashboard-Only Features

These features exist **exclusively** in the dashboard path:

### 3.1 Safety Infrastructure

| Feature | Module | Purpose | Lines |
|---------|--------|---------|-------|
| **BackupManager** | `services/config_api/backup_manager.py` | Timestamped backup of agents/, skills/, config/ before destructive ops. Auto-prunes to 5 backups. Atomic rename via tempdir. | 380 lines |
| **OperationJournal** | `services/config_api/operation_journal.py` | Write-ahead log for crash recovery. Records `begin_operation` → `complete_operation` / `fail_operation`. Detects incomplete ops on restart. | 263 lines |
| **DeploymentVerifier** | `services/config_api/deployment_verifier.py` | Post-deploy filesystem verification: file exists, valid YAML frontmatter, required fields, size check (<10MB). | 382 lines |
| **ConfigFileLock** | `core/config_file_lock.py` | POSIX advisory file locking (`fcntl.flock`) to prevent concurrent writes from CLI + Dashboard. 5s timeout, PID written to lock file. | 134 lines |

### 3.2 Input Validation / Security

| Feature | Module | Purpose |
|---------|--------|---------|
| **validate_safe_name()** | `services/config_api/validation.py:16-45` | Regex check: `[a-zA-Z0-9][a-zA-Z0-9_-]*`. Rejects path separators, traversal, special chars. |
| **validate_path_containment()** | `services/config_api/validation.py:48-78` | Resolves symlinks and verifies path stays within expected parent directory. Defence-in-depth against path traversal. |
| **CORE_AGENTS list** | `agent_deployment_handler.py:28-35` | Prevents undeploying critical agents (engineer, research, qa, web-qa, documentation, ops, ticketing). |

### 3.3 Async Execution Model

| Feature | Location | How It Works |
|---------|----------|-------------|
| **Background task** | `autoconfig_handler.py:353-362` | `asyncio.create_task(_run_auto_configure(...))` - returns HTTP 202 immediately |
| **asyncio.to_thread()** | Used throughout `autoconfig_handler.py` | Wraps synchronous service calls to avoid blocking the event loop |
| **Job tracking** | `autoconfig_handler.py:35` | `_active_jobs: Dict[str, asyncio.Task]` dict tracks in-flight jobs by ID |

### 3.4 Real-Time Event System

| Feature | Module | Purpose |
|---------|--------|---------|
| **ConfigEventHandler** | `services/monitor/handlers/config_handler.py:31-73` | Emits `config_event` Socket.IO events with structured payload (operation, entity_type, entity_id, status, data, timestamp) |
| **ConfigFileWatcher** | `services/monitor/handlers/config_handler.py:76-172` | Polls config file mtimes every 5s; emits `external_change` event when CLI modifies files. Has `update_mtime()` to suppress false positives from own writes. |
| **6-phase pipeline events** | `autoconfig_handler.py:391-418` | Emits `autoconfig_progress` events for: detecting(1) → recommending(2) → validating(3) → deploying(4) → deploying_skills(5) → verifying(6) |
| **Completion/failure events** | `autoconfig_handler.py:620-663` | `autoconfig_completed` with full results or `autoconfig_failed` with error + rollback info |

### 3.5 ConfigScope Path Resolution

| Feature | Module | Purpose |
|---------|--------|---------|
| **ConfigScope enum** | `core/config_scope.py:20-28` | `PROJECT` vs `USER` scope. `str`-based enum for backward compatibility. |
| **resolve_agents_dir()** | `core/config_scope.py:31-44` | `PROJECT` → `<project>/.claude/agents/`, `USER` → `~/.claude/agents/` |
| **resolve_skills_dir()** | `core/config_scope.py:47-68` | `PROJECT` → `<project>/.claude/skills/`, `USER` → `~/.claude/skills/` |
| **resolve_archive_dir()** | `core/config_scope.py:71-85` | Appends `/unused/` to agents dir |
| **resolve_config_dir()** | `core/config_scope.py:88-101` | `PROJECT` → `<project>/.claude-mpm/`, `USER` → `~/.claude-mpm/` |

### 3.6 Session Detection

| Feature | Module | Purpose |
|---------|--------|---------|
| **detect_active_claude_sessions()** | `services/config_api/session_detector.py` | Scans `ps aux` for claude-related processes. Fail-open design (returns empty list on error). Used to warn users before operations. |

### 3.7 Skill Deployment During Auto-Configure

The CLI auto-configure command recommends skills but **deployment is a separate step** (called from `_run_full_configuration` at `auto_configure.py:396-400`). The dashboard integrates skill deployment as **Phase 5** of the `_run_auto_configure()` background task at `autoconfig_handler.py:549-590`, making it a single atomic operation.

### 3.8 Feature Flags

| Feature | Module | Purpose |
|---------|--------|---------|
| **FEATURES object** | `dashboard-svelte/src/config/features.ts` | Progressive rollout flags for UI features (RICH_DETAIL_PANELS, FILTER_DROPDOWNS, etc.) |

---

## 4. CLI-Only Features

These features exist **exclusively** in the CLI path:

| Feature | Location | Purpose | Dashboard Equivalent |
|---------|----------|---------|---------------------|
| **Agent review/archival** | `auto_configure.py:917-973` via `AgentReviewService` | Categorizes existing agents (managed/outdated/custom/unused), archives unused to `.claude/agents/unused/` | None - dashboard does not review/archive existing agents during auto-configure |
| **Remote agent discovery** | `auto_configure.py:941` via `RemoteAgentDiscoveryService` | Discovers managed agents from `~/.claude-mpm/cache/agents/` | None |
| **Rich terminal UI** | `auto_configure.py:37-97` (`RichProgressObserver`) + `_display_preview()` | Progress bars, spinner, styled tables, confidence bars | Dashboard uses Svelte components instead |
| **Plain text fallback** | `auto_configure.py:507-552` | Fallback when `rich` not installed | N/A (dashboard always has Svelte) |
| **Interactive selection (y/n/s)** | `auto_configure.py:554-607` | Terminal prompt with y/n/s options (`s` = select, not implemented) | Dashboard uses modal with type-to-confirm |
| **`--agents-only` / `--skills-only` flags** | `auto_configure_parser.py` | Separate agent-only or skill-only modes | Dashboard always runs both |
| **JSON output mode (`--json`)** | `auto_configure.py:765-873` | Machine-readable output for scripting | Dashboard returns JSON by default (it's a REST API) |
| **`AgentDeploymentService` injection** | `auto_configure.py:133-138` | Passes `agent_deployment` to `AutoConfigManagerService` | Dashboard instantiates `AgentDeploymentService` directly per-agent in Phase 4 |
| **Observer pattern for progress** | `auto_configure.py:384` `RichProgressObserver` | `IDeploymentObserver` callbacks during deployment | Dashboard uses Socket.IO events instead |
| **Restart notification display** | `auto_configure.py:1016-1052` | Terminal message with restart instructions | Dashboard shows in-modal notification |
| **AgentRegistry required** | `auto_configure.py:124` | `AgentRegistry()` imported unconditionally (will fail if unavailable) | Dashboard wraps in try/except with graceful degradation |

---

## 5. Divergent Behavior

Cases where the **same operation** produces **different results**:

### 5.1 min_confidence=0.0 Bug

| Aspect | CLI (main branch) | CLI (ui-agents-skills-config) | Dashboard |
|--------|-------------------|-------------------------------|-----------|
| `min_confidence=0.0` handling | **BUG**: `if args.min_confidence:` evaluates `0.0` as falsy, falls back to `0.5` | **FIXED**: `if args.min_confidence is not None:` correctly uses `0.0` | Always correct: `body.get("min_confidence", 0.5)` - explicit `0.0` is preserved |
| **Impact** | Users cannot set confidence to 0.0 to see all agents | Fixed on dashboard branch | Never had the bug |

### 5.2 Skill Deployment Target Directory

| Aspect | CLI Path | Dashboard Path |
|--------|----------|----------------|
| **Default target** | `~/.claude/skills/` (user-level, `SkillsDeployerService.CLAUDE_SKILLS_DIR`) | `<project>/.claude/skills/` (project-scoped, via `resolve_skills_dir(ConfigScope.PROJECT)`) |
| **Implication** | Skills shared across all projects | Skills isolated per project |
| **Code location** | `auto_configure.py:910` → `self.skills_deployer.deploy_skills(...)` (no `skills_dir` override) | `autoconfig_handler.py:576-581` → `svc.deploy_skills(skills_dir=project_skills_dir)` |

### 5.3 AgentRegistry Handling

| Aspect | CLI Path | Dashboard Path |
|--------|----------|----------------|
| **Import** | `from ...services.agents.registry import AgentRegistry` (bare import, no try/except) at `auto_configure.py:124` | Wrapped in `try/except` with warning at `autoconfig_handler.py:67-74` |
| **On failure** | **Crash**: ImportError propagates, command fails | **Degrade**: `agent_registry=None` passed to `AutoConfigManagerService`, validation skips agent existence checks |

### 5.4 Agent Deployment Mechanism

| Aspect | CLI Path | Dashboard Path |
|--------|----------|----------------|
| **How** | Via `AutoConfigManagerService.auto_configure()` (async, uses `asyncio.run()`) at `auto_configure.py:385-393` | Direct `AgentDeploymentService().deploy_agent()` per agent in Phase 4 loop at `autoconfig_handler.py:529-547` |
| **Error handling** | Rollback via `_rollback_deployment()` (stub, just logs) | Per-agent try/except, failed agents tracked, backup available for manual restore |
| **Path resolution** | Uses internal `_deploy_agents()` in `AutoConfigManagerService` | Uses `resolve_agents_dir(ConfigScope.PROJECT, project_path)` for explicit path control |

### 5.5 Configuration Persistence

| Aspect | CLI Path | Dashboard Path |
|--------|----------|----------------|
| **Saved metadata** | `AutoConfigManagerService._save_configuration()` → `.claude-mpm/auto-config.yaml` (toolchain snapshot, deployed agents, overrides) | None - dashboard does not save auto-config metadata to YAML |
| **Backup** | None | `BackupManager.create_backup()` before every apply |

### 5.6 Skill Deployment in Auto-Configure Pipeline

| Aspect | CLI Path | Dashboard Path |
|--------|----------|----------------|
| **Integration** | Sequential but separate: agents deployed via `auto_config_manager.auto_configure()`, then skills via `_deploy_skills()` at `auto_configure.py:396-400` | Integrated as Phase 5 of `_run_auto_configure()` background task at `autoconfig_handler.py:549-590` |
| **Atomicity** | Non-atomic: agent deployment and skill deployment are separate operations | More cohesive: part of single background task with unified progress tracking |
| **Error isolation** | Skill errors don't affect agent deployment result | Skill errors tracked separately (`skill_errors` list) but don't fail the entire job |

---

## 6. Data Model Comparison

### 6.1 Auto-Configure Input Parameters

| Parameter | CLI | Dashboard | Notes |
|-----------|-----|-----------|-------|
| `project_path` | `args.project_path` or `Path.cwd()` | `body.get("project_path", str(Path.cwd()))` | Same logic |
| `min_confidence` | `args.min_confidence` or `0.5` | `body.get("min_confidence", 0.5)` | Same default; CLI had 0.0 bug (fixed on branch) |
| `dry_run` | `args.preview` flag | `body.get("dry_run", False)` | Different parameter name |
| `skip_confirmation` | `args.yes` flag | N/A (UI confirmation) | CLI-specific |
| `json_output` | `args.json` flag | N/A (always JSON) | CLI-specific |
| `configure_agents` | `not args.skills_only` | Always True | CLI-only granularity |
| `configure_skills` | `not args.agents_only` | Always True | CLI-only granularity |

### 6.2 Preview Response Structure

**CLI (`_output_preview_json`)**:
```json
{
  "agents": {
    "detected_toolchain": { "components": [...] },
    "recommendations": [{ "agent_id", "confidence", "reasoning" }],
    "validation": { "is_valid", "issues": [...] }
  },
  "skills": {
    "recommendations": ["skill-name-1", "skill-name-2"]
  }
}
```

**Dashboard (`_preview_to_dict`)**:
```json
{
  "success": true,
  "preview": {
    "would_deploy": ["agent-1", "agent-2"],
    "would_skip": ["agent-3"],
    "deployment_count": 2,
    "estimated_deployment_time": 10.0,
    "requires_confirmation": true,
    "recommendations": [{ "agent_id", "agent_name", "confidence_score", "rationale", "match_reasons", "deployment_priority" }],
    "validation": { "is_valid", "error_count", "warning_count" },
    "toolchain": { "primary_language", "primary_confidence", "frameworks", ... },
    "skill_recommendations": ["skill-1", "skill-2"],
    "would_deploy_skills": ["skill-1", "skill-2"],
    "metadata": {}
  }
}
```

**Key differences**:
- Dashboard wraps in `{ success, preview }` envelope
- Dashboard includes `would_deploy` / `would_skip` / `deployment_count` at top level
- Dashboard includes `estimated_deployment_time` and `requires_confirmation`
- Dashboard has richer recommendation fields (`agent_name`, `rationale`, `deployment_priority`)
- Dashboard includes `toolchain` as nested object (CLI puts it under `agents.detected_toolchain`)
- Dashboard duplicates skills as both `skill_recommendations` and `would_deploy_skills`

### 6.3 Apply Result Structure

**CLI (`_output_result_json`)**:
```json
{
  "agents": {
    "status": "SUCCESS",
    "deployed_agents": ["agent-1"],
    "failed_agents": [],
    "errors": {}
  },
  "skills": {
    "deployed": ["skill-1"],
    "errors": []
  }
}
```

**Dashboard (Socket.IO `autoconfig_completed` event)**:
```json
{
  "type": "config_event",
  "operation": "autoconfig_completed",
  "entity_type": "autoconfig",
  "entity_id": "autoconfig-1740150000-abc123",
  "status": "completed",
  "data": {
    "job_id": "autoconfig-1740150000-abc123",
    "deployed_agents": ["agent-1"],
    "failed_agents": [],
    "deployed_skills": ["skill-1"],
    "skill_errors": [],
    "needs_restart": true,
    "backup_id": "2026-02-21T12-00-00",
    "duration_ms": 8432,
    "verification": { "agent-1": { "passed": true } }
  },
  "timestamp": "2026-02-21T12:00:00.000Z"
}
```

**Key differences**:
- Dashboard adds `job_id`, `backup_id`, `duration_ms`, `verification`, `needs_restart`
- Dashboard wraps in Socket.IO event envelope (`type`, `operation`, `entity_type`, `timestamp`)
- Dashboard has per-agent verification results
- CLI uses `OperationResult` enum status; Dashboard uses string "completed"/"failed"

---

## 7. Instantiation & Dependency Injection

### 7.1 CLI: Property-Based Lazy Loading

```
AutoConfigureCommand (BaseCommand)
 ├── @property auto_config_manager → AutoConfigManagerService(
 │       toolchain_analyzer=ToolchainAnalyzerService(),    # new instance
 │       agent_recommender=AgentRecommenderService(),      # new instance
 │       agent_registry=AgentRegistry(),                   # new instance (REQUIRED)
 │       agent_deployment=AgentDeploymentService(),        # new instance (optional)
 │   )
 └── @property skills_deployer → SkillsDeployerService()   # new instance
```

- Instances created per-command execution
- Tied to `AutoConfigureCommand` object lifecycle
- `AgentRegistry` import is not guarded - will fail if unavailable
- `AgentDeploymentService` import guarded with try/except

### 7.2 Dashboard: Module-Level Lazy Singletons

```
autoconfig_handler.py (module level)
 ├── _get_toolchain_analyzer() → ToolchainAnalyzerService()   # singleton
 ├── _get_auto_config_manager() → AutoConfigManagerService(
 │       toolchain_analyzer=_get_toolchain_analyzer(),         # reuses singleton
 │       agent_recommender=AgentRecommenderService(),          # new instance
 │       agent_registry=AgentRegistry() | None,                # optional, guarded
 │   )
 ├── _get_backup_manager() → BackupManager()                   # singleton
 └── _get_skills_deployer() → SkillsDeployerService()          # singleton
```

- Singletons persist for server lifetime (not per-request)
- `_reset_auto_config_manager()` available for testing/error recovery
- `AgentRegistry` wrapped in try/except with graceful degradation
- `ToolchainAnalyzerService` is **shared** between `_get_toolchain_analyzer()` and `_get_auto_config_manager()` (dashboard reuses)
- `AgentDeploymentService` NOT injected into `AutoConfigManagerService` - dashboard deploys agents **directly** in its Phase 4 loop

### 7.3 Additional Dashboard DI Patterns

Each deployment handler has its own set of lazy singletons:

```
agent_deployment_handler.py          skill_deployment_handler.py
 ├── _get_backup_manager()            ├── _get_backup_manager()        # DUPLICATED
 ├── _get_operation_journal()         ├── _get_operation_journal()     # DUPLICATED
 ├── _get_deployment_verifier()       ├── _get_deployment_verifier()   # DUPLICATED
 └── _get_agent_deployment_service()  └── _get_skills_deployer()
```

The `_get_backup_manager()`, `_get_operation_journal()`, and `_get_deployment_verifier()` factory functions are **duplicated** across `agent_deployment_handler.py`, `skill_deployment_handler.py`, and `autoconfig_handler.py`. Each creates its own singleton, but since they're module-level globals, they create **separate instances** per module. This means BackupManager, OperationJournal, and DeploymentVerifier each have up to 3 instances at runtime.

---

## 8. Pre-existing Duplication on main Branch

The main branch already has **multiple parallel systems** before the dashboard code was added. Here's which ones each path uses:

### 8.1 Two Toolchain Detectors

| System | File | Used by CLI auto-configure? | Used by Dashboard? | Used by Other? |
|--------|------|----------------------------|--------------------|----|
| `ToolchainDetector` (legacy) | `services/agents/toolchain_detector.py` | **No** | **No** | Yes - `AgentSelectionService` at `agent_selection_service.py:103,307` |
| `ToolchainAnalyzerService` (modern) | `services/project/toolchain_analyzer.py` | **Yes** | **Yes** | - |

Both paths correctly use the modern `ToolchainAnalyzerService`. The legacy `ToolchainDetector` is used only by `AgentSelectionService` (the older interactive configure wizard).

### 8.2 Two Agent Recommenders

| System | File | Used by CLI auto-configure? | Used by Dashboard? | Used by Other? |
|--------|------|----------------------------|--------------------|----|
| `AgentRecommendationService` | `services/agents/agent_recommendation_service.py` | **No** | **No** | Yes - `cli/commands/configure.py:161-164` (interactive wizard) |
| `AgentRecommenderService` | `services/agents/recommender.py` | **Yes** (via `AutoConfigManagerService`) | **Yes** (via `AutoConfigManagerService`) | - |

Both paths use `AgentRecommenderService` (YAML-config driven, scoring algorithm). `AgentRecommendationService` is used only by the older interactive `configure` command.

### 8.3 Two Skill Recommendation Systems

| System | File | Used by CLI auto-configure? | Used by Dashboard? | Used by Other? |
|--------|------|----------------------------|--------------------|----|
| `AGENT_SKILL_MAPPING` (simple dict) | `cli/interactive/skills_wizard.py:52-74` | **Yes** (at `auto_configure.py:888`) | **Yes** (at `autoconfig_handler.py:299,563`) | - |
| `SkillRecommendationEngine` (scoring) | `services/skills/skill_recommendation_engine.py` | **No** | **No** | Yes - `cli/commands/skills.py:1423-1478` (skills recommend subcommand) |

Both paths use the **simple dict mapping**. The sophisticated `SkillRecommendationEngine` with scoring, priority patterns, and manifest-based filtering is **NOT** wired into either auto-configure path.

### 8.4 Two Tech Stack Detectors

| System | File | Used by CLI auto-configure? | Used by Dashboard? | Used by Other? |
|--------|------|----------------------------|--------------------|----|
| `ToolchainAnalyzerService` | `services/project/toolchain_analyzer.py` | **Yes** | **Yes** | - |
| `ProjectInspector` + `TechnologyStack` | `services/skills/project_inspector.py` | **No** | **No** | Yes - by `SkillRecommendationEngine` |

Different data models: `ToolchainAnalysis` (rich, with `LanguageDetection`, `Framework`, etc.) vs `TechnologyStack` (simple `Dict[str, float]` for languages, frameworks, tools, databases).

### 8.5 Pre-existing Duplication Summary

```
                         CLI Auto-Configure    Dashboard Auto-Configure    Other Commands
                         ──────────────────    ────────────────────────    ──────────────
Toolchain Detection:     ToolchainAnalyzer ◄── ToolchainAnalyzer          ToolchainDetector (legacy)
Agent Recommendation:    AgentRecommender  ◄── AgentRecommender           AgentRecommendationService (alt)
Skill Recommendation:    AGENT_SKILL_MAP   ◄── AGENT_SKILL_MAP            SkillRecommendationEngine (alt)
Tech Stack Detection:    ToolchainAnalyzer ◄── ToolchainAnalyzer          ProjectInspector (alt)
```

The CLI and Dashboard auto-configure paths consistently use the **same** set of modern services. The alternative/legacy systems are used by other, older commands (`configure`, `skills recommend`).

---

## 9. Architecture Gap Analysis

### 9.1 What Should Be Shared But Isn't

| Gap | Impact | Unification Approach |
|-----|--------|---------------------|
| Skill recommendation function | 3 duplicate implementations | Extract `recommend_skills_for_agents(agent_ids) -> List[str]` to shared service |
| Safety infrastructure (backup/journal/verify) | CLI has zero safety | Either share infrastructure or accept the gap is intentional |
| ConfigScope path resolution | CLI uses hardcoded `Path.cwd() / ".claude" / "agents"` etc. | Adopt ConfigScope in CLI `_review_project_agents()` and `_archive_agents()` |
| Input validation | CLI relies on argparse only | Share `validate_safe_name` / `validate_path_containment` for filesystem ops |
| _get_* singleton factories | Duplicated across 3 handler modules | Move to shared factory module or DI container |

### 9.2 Intentional Divergence (Likely Correct)

| Divergence | Why It's Probably OK |
|------------|---------------------|
| Async vs sync execution model | CLI is ephemeral (run once), Dashboard is long-running server |
| Socket.IO vs terminal output | Different UI transports, necessarily different |
| HTTP 202 + background task vs blocking | Appropriate for each context |
| Feature flags (dashboard) | Only UI needs progressive rollout |
| ConfigFileWatcher (dashboard) | CLI doesn't need to watch for external changes |
| Session detection (dashboard) | CLI is itself a Claude Code session |

### 9.3 Risk Assessment

| Risk | Severity | Description |
|------|----------|-------------|
| Skill deployment directory divergence | **HIGH** | CLI deploys to `~/.claude/skills/` (user-level); Dashboard deploys to `<project>/.claude/skills/` (project-level). Users who auto-configure via CLI then switch to Dashboard (or vice versa) will get skills in different locations. |
| No backup in CLI | **MEDIUM** | CLI can overwrite agents with no recovery path. Dashboard has full backup/restore. |
| AgentRegistry crash in CLI | **MEDIUM** | CLI doesn't guard the `AgentRegistry` import; if it fails, the entire auto-configure crashes. Dashboard degrades gracefully. |
| 3 separate BackupManager instances | **LOW** | Each handler module creates its own BackupManager singleton. They all default to `~/.claude-mpm/backups/` so they write to the same directory, but concurrent operations from different handlers could theoretically collide. |
| No agent review in Dashboard | **LOW** | Dashboard doesn't review/archive existing agents during auto-configure. Could leave outdated agents deployed. |

---

## 10. Summary Table

| Dimension | CLI Path | Dashboard Path |
|-----------|----------|----------------|
| **Entry point** | `AutoConfigureCommand.run(args)` | `POST /api/config/auto-configure/apply` |
| **Execution** | Synchronous (`asyncio.run()` for deploy) | Async background task (`asyncio.create_task`) |
| **Progress** | Rich terminal + Observer pattern | Socket.IO events (6-phase pipeline) |
| **Confirmation** | Interactive y/n/s prompt | Type "apply" in modal |
| **Backup** | None | BackupManager (timestamped, auto-prune) |
| **Verification** | None | DeploymentVerifier (4-check per agent) |
| **Crash recovery** | None | OperationJournal (write-ahead log) |
| **File locking** | None | ConfigFileLock (POSIX fcntl.flock) |
| **Input validation** | argparse only | validate_safe_name + validate_path_containment |
| **Skills target** | `~/.claude/skills/` (user) | `<project>/.claude/skills/` (project) |
| **Agent review** | Yes (categorize + archive unused) | No |
| **AgentRegistry** | Required (will crash if missing) | Optional (graceful degradation) |
| **DI pattern** | Property lazy-load on command instance | Module-level lazy singletons |
| **Config persistence** | `.claude-mpm/auto-config.yaml` | None |
| **Shared core services** | ToolchainAnalyzer, AutoConfigManager, AgentRecommender, AGENT_SKILL_MAPPING | Same |
| **Session detection** | No | Yes (ps aux scan) |
| **External change detection** | No | ConfigFileWatcher (5s mtime poll) |
