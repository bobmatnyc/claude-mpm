# Auto-Configuration Dashboard/REST API Code Path

**Branch**: `ui-agents-skills-config` (commit `0188c08d`)
**Date**: 2026-02-21
**Scope**: Complete investigation of the NEW dashboard REST API + Svelte UI code path for auto-configuration

---

## 1. Executive Summary

The `ui-agents-skills-config` branch introduces a **complete new dashboard-based auto-configuration system** consisting of:

- **~18 new Svelte UI components** in `dashboard-svelte/src/lib/components/config/`
- **~8 new Python backend modules** in `services/config_api/` and `services/monitor/`
- **~40+ new REST API endpoints** under `/api/config/*`
- **Socket.IO real-time event infrastructure** for progress tracking
- **Safety infrastructure** (backups, journals, verification) not present in CLI

The dashboard path **partially reuses** core auto-config services (`AutoConfigManagerService`, `ToolchainAnalyzerService`, `AgentRecommenderService`) but wraps them in a **completely new API layer** with its own serialization, error handling, dependency injection (lazy singletons), and event-driven asynchronous workflow.

---

## 2. Branch Change Summary

### 2.1 Commits (30 unique to branch)

Key feature commits:
```
9a7f6cf2 feat: implement Phase 3 deployment operations for config dashboard
7a939642 feat: implement Phase 4A foundation infrastructure, skill-to-agent linking, and config validation
c9e88ad3 feat: implement Phase 1 frontend quick wins for config dashboard
db25da5f feat: implement Phase 3 rich detail panels with filters, search, and version detection
ae75a507 feat(autoconf): wire skill deployment into API auto-configure path
4390ac74 feat(dashboard): implement Phase 4 UI messaging for auto-configure
b9673651 feat(testing): implement comprehensive Phase 5 test suite for auto-configure v2
177d9f94 fix(auto-configure): fix broken preview/apply flows with full DI and schema alignment
37814bd7 feat(core): add ConfigScope enum and path resolvers for Claude Code dirs
```

### 2.2 New Files (not in main)

**Backend (Python):**
| File | Purpose | Lines |
|------|---------|-------|
| `services/config_api/__init__.py` | Package init, exports all handlers | ~65 |
| `services/config_api/autoconfig_handler.py` | Auto-configure REST endpoints (detect/preview/apply) | ~450 |
| `services/config_api/agent_deployment_handler.py` | Agent deploy/undeploy REST endpoints | ~200+ |
| `services/config_api/skill_deployment_handler.py` | Skill deploy/undeploy/mode-switch REST endpoints | ~200+ |
| `services/config_api/backup_manager.py` | Pre-operation backup system | ~80+ |
| `services/config_api/deployment_verifier.py` | Post-deployment filesystem verification | ~80+ |
| `services/config_api/operation_journal.py` | Crash-recovery operation journal | N/A |
| `services/config_api/session_detector.py` | Active Claude Code session detection | N/A |
| `services/config_api/validation.py` | Input validation (safe names, path containment) | N/A |
| `services/monitor/config_routes.py` | Phase 1 read-only config endpoints (11 routes) | ~1050+ |
| `services/monitor/routes/config_sources.py` | Phase 2 source CRUD mutation endpoints (7 routes) | ~920 |
| `services/monitor/handlers/config_handler.py` | Socket.IO ConfigEventHandler + ConfigFileWatcher | ~120 |
| `services/monitor/handlers/skill_link_handler.py` | Skill-to-agent mapping handler | N/A |
| `core/config_scope.py` | ConfigScope enum + path resolvers | ~105 |
| `core/config_file_lock.py` | File-level locking for config writes | N/A |

**Frontend (Svelte/TypeScript):**
| File | Purpose |
|------|---------|
| `components/config/ConfigView.svelte` | Main config tab container (left/right split) |
| `components/config/AutoConfigPreview.svelte` | 2-step auto-configure modal (detect+apply) |
| `components/config/DeploymentPipeline.svelte` | Visual pipeline progress indicator |
| `components/config/AgentsList.svelte` | Agent list with deploy/undeploy |
| `components/config/AgentDetailPanel.svelte` | Rich agent detail panel |
| `components/config/AgentFilterBar.svelte` | Agent filtering controls |
| `components/config/AgentSkillPanel.svelte` | Agent-skill relationship panel |
| `components/config/SkillsList.svelte` | Skill list with deploy/undeploy |
| `components/config/SkillDetailPanel.svelte` | Rich skill detail panel |
| `components/config/SkillFilterBar.svelte` | Skill filtering controls |
| `components/config/SkillChip.svelte` | Skill display chip |
| `components/config/SkillChipList.svelte` | Skill chip collection |
| `components/config/SkillChipWithStatus.svelte` | Skill chip with deployment status |
| `components/config/SkillLinksView.svelte` | Skill-to-agent link browser |
| `components/config/SourcesList.svelte` | Source repository management |
| `components/config/SourceForm.svelte` | Add/edit source form |
| `components/config/ModeSwitch.svelte` | Deployment mode selector |
| `components/config/SyncProgress.svelte` | Source sync progress display |
| `components/config/ValidationPanel.svelte` | Config validation status panel |
| `components/config/ValidationIssueCard.svelte` | Individual validation issue card |
| `stores/config.svelte.ts` | Config Svelte store (state + API calls) |
| `stores/config/skillLinks.svelte.ts` | Skill links sub-store |
| `stores/toast.svelte.ts` | Toast notification store |
| `config/features.ts` | Feature flags for progressive rollout |
| Various `shared/` components | Reusable UI primitives |

### 2.3 Modified Files

| File | Change |
|------|--------|
| `cli/commands/auto_configure.py` | Bug fix: `args.min_confidence` falsy check (0.0 was treated as None) |
| `config/agent_sources.py` | Source configuration changes |
| `services/monitor/server.py` | Route registration + CORS + config event infrastructure |
| `dashboard-svelte/src/routes/+page.svelte` | Added "Config" tab + Socket.IO config_event listener |

---

## 3. REST API Endpoints (Complete Catalog)

### 3.1 Read-Only Endpoints (Phase 1) - `config_routes.py`

Registered by `register_config_routes()`:

| Method | Endpoint | Handler | Description |
|--------|----------|---------|-------------|
| GET | `/api/config/project/summary` | `handle_project_summary` | Agent/skill/source counts + deployment mode |
| GET | `/api/config/agents/deployed` | `handle_agents_deployed` | List deployed agents with metadata |
| GET | `/api/config/agents/available` | `handle_agents_available` | List available (undeployed) agents |
| GET | `/api/config/skills/deployed` | `handle_skills_deployed` | List deployed skills with enrichment |
| GET | `/api/config/skills/available` | `handle_skills_available` | List available skills from manifest |
| GET | `/api/config/sources` | `handle_sources` | List agent + skill repository sources |
| GET | `/api/config/agents/{name}/detail` | `handle_agent_detail` | Full agent metadata (YAML parsed) |
| GET | `/api/config/skills/{name}/detail` | `handle_skill_detail` | Full skill metadata + content |
| GET | `/api/config/skill-links/` | `handle_skill_links` | All skill-to-agent mappings |
| GET | `/api/config/skill-links/agent/{name}` | `handle_skill_links_agent` | Skills for specific agent |
| GET | `/api/config/validate` | `handle_validate` | Configuration validation check |

### 3.2 Source Management (Phase 2) - `config_sources.py`

Registered by `register_source_routes()`:

| Method | Endpoint | Handler | Description |
|--------|----------|---------|-------------|
| POST | `/api/config/sources/agent` | `add_agent_source` | Add agent repository source |
| POST | `/api/config/sources/skill` | `add_skill_source` | Add skill collection source |
| DELETE | `/api/config/sources/{type}` | `remove_source` | Remove a source |
| PATCH | `/api/config/sources/{type}` | `update_source` | Update source properties |
| POST | `/api/config/sources/{type}/sync` | `sync_source` | Trigger source sync |
| POST | `/api/config/sources/sync-all` | `sync_all_sources` | Sync all enabled sources |
| GET | `/api/config/sources/sync-status` | `get_sync_status` | Get sync status for a source |

### 3.3 Agent Deployment (Phase 3) - `agent_deployment_handler.py`

Registered by `register_agent_deployment_routes()`:

| Method | Endpoint | Handler | Description |
|--------|----------|---------|-------------|
| POST | `/api/config/agents/deploy` | `deploy_agent` | Deploy single agent |
| DELETE | `/api/config/agents/{name}` | (undeploy) | Undeploy agent |
| POST | `/api/config/agents/deploy-collection` | (batch) | Batch deploy agents |

### 3.4 Skill Deployment (Phase 3) - `skill_deployment_handler.py`

Registered by `register_skill_deployment_routes()`:

| Method | Endpoint | Handler | Description |
|--------|----------|---------|-------------|
| POST | `/api/config/skills/deploy` | `deploy_skill` | Deploy single skill |
| DELETE | `/api/config/skills/{name}` | (undeploy) | Undeploy skill |
| GET | `/api/config/skills/deployment-mode` | | Get current mode |
| PUT | `/api/config/skills/deployment-mode` | | Switch deployment mode |
| GET | `/api/config/active-sessions` | | Check active Claude sessions |

### 3.5 Auto-Configure (Phase 3) - `autoconfig_handler.py`

Registered by `register_autoconfig_routes()`:

| Method | Endpoint | Handler | Description |
|--------|----------|---------|-------------|
| POST | `/api/config/auto-configure/detect` | `detect_toolchain` | Analyze project toolchain |
| POST | `/api/config/auto-configure/preview` | `preview_configuration` | Preview recommendations |
| POST | `/api/config/auto-configure/apply` | `apply_configuration` | Apply auto-config (async, returns 202) |

---

## 4. Auto-Configure Data Flow

### 4.1 Detection Flow

```
Dashboard UI                    REST API                          Backend Services
─────────────────────────────────────────────────────────────────────────────────
AutoConfigPreview.svelte        autoconfig_handler.py             project/toolchain_analyzer.py
│                               │                                 │
│  analyzeProject()             │                                 │
│──► detectToolchain()          │                                 │
│    │                          │                                 │
│    │  POST /auto-configure/   │                                 │
│    │       detect             │                                 │
│    │──────────────────────────►│                                │
│    │                          │  _get_toolchain_analyzer()      │
│    │                          │──► (lazy singleton)             │
│    │                          │                                 │
│    │                          │  asyncio.to_thread(_detect)     │
│    │                          │──────────────────────────────────►│
│    │                          │                                 │  analyze_toolchain(path)
│    │                          │◄──────────────────────────────────│
│    │                          │                                 │
│    │                          │  _toolchain_to_dict(analysis)   │
│    │    { toolchain: {...} }  │  (serialization)                │
│    │◄──────────────────────────│                                │
│    │                          │                                 │
│  toolchain = result           │                                 │
│                               │                                 │
│  previewAutoConfig()          │                                 │
│    │                          │                                 │
│    │  POST /auto-configure/   │                                 │
│    │       preview            │                                 │
│    │──────────────────────────►│                                │
│    │                          │  _get_auto_config_manager()     │
│    │                          │──► (lazy singleton w/ DI)       │
│    │                          │     ├─ ToolchainAnalyzerService │
│    │                          │     ├─ AgentRecommenderService  │
│    │                          │     └─ AgentRegistry (optional) │
│    │                          │                                 │
│    │                          │  asyncio.to_thread(_preview)    │
│    │                          │──►mgr.preview_configuration()   │
│    │                          │                                 │
│    │                          │  _recommend_skills_for_preview()│
│    │                          │──► AGENT_SKILL_MAPPING lookup   │
│    │                          │                                 │
│    │    { preview: {...} }    │  _preview_to_dict(preview)      │
│    │◄──────────────────────────│                                │
│    │                          │                                 │
│  previewData = result         │                                 │
```

### 4.2 Apply Flow (Async with Socket.IO Progress)

```
Dashboard UI                    REST API                          Background Task
─────────────────────────────────────────────────────────────────────────────────
AutoConfigPreview.svelte        autoconfig_handler.py             _run_auto_configure()
│                               │                                 │
│  handleApply()                │                                 │
│──► applyAutoConfig()          │                                 │
│    │                          │                                 │
│    │  POST /auto-configure/   │                                 │
│    │       apply              │                                 │
│    │──────────────────────────►│                                │
│    │                          │  job_id = generate_uuid()       │
│    │                          │  asyncio.create_task(...)       │──────────────────►│
│    │    HTTP 202              │                                 │                   │
│    │    { job_id: "..." }     │                                 │                   │
│    │◄──────────────────────────│                                │                   │
│    │                          │                                 │                   │
│──► waitForAutoConfig(job_id)  │                                 │ Phase 1: detect   │
│    │  (Promise, listens to    │                                 │──► toolchain      │
│    │   Socket.IO events)      │                                 │                   │
│    │                          │                                 │ Phase 2: recommend│
│    │                          │  Socket.IO: autoconfig_progress │──► preview_config  │
│    │◄─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─│◄─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─│                   │
│    │  handleProgress(data)    │                                 │ Phase 3: backup   │
│    │                          │                                 │──► BackupManager  │
│    │                          │                                 │                   │
│    │                          │  Socket.IO: autoconfig_progress │ Phase 4: deploy   │
│    │◄─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─│◄─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─│──► for each agent  │
│    │  pipelineStages update   │                                 │    deploy_agent() │
│    │                          │                                 │                   │
│    │                          │  Socket.IO: autoconfig_progress │ Phase 5: skills   │
│    │◄─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─│◄─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─│──► deploy_skills() │
│    │                          │                                 │                   │
│    │                          │  Socket.IO: autoconfig_progress │ Phase 6: verify   │
│    │◄─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─│◄─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─│──► DeploymentVer. │
│    │                          │                                 │                   │
│    │                          │  Socket.IO: autoconfig_completed│◄──────────────────│
│    │◄─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─│◄─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─│                   │
│    │                          │                                 │                   │
│  applyResult = data           │                                 │                   │
│  Refresh all stores           │                                 │                   │
│  Show success toast           │                                 │                   │
```

---

## 5. Core Logic Reuse Analysis

### 5.1 Shared Services (Reused from CLI)

| Service | CLI Usage | Dashboard API Usage | Same Instance? |
|---------|-----------|---------------------|----------------|
| `ToolchainAnalyzerService` | `auto_configure.py:197` | `autoconfig_handler.py:_get_toolchain_analyzer()` | No - separate lazy singletons |
| `AutoConfigManagerService` | `auto_configure.py` (via container) | `autoconfig_handler.py:_get_auto_config_manager()` | No - separate instantiation |
| `AgentRecommenderService` | Via `AutoConfigManagerService` | Via `AutoConfigManagerService` | Transitively shared |
| `AgentDeploymentService` | Not directly | `agent_deployment_handler.py` | Dashboard-only direct usage |
| `SkillsDeployerService` | CLI startup | `skill_deployment_handler.py`, `autoconfig_handler.py` | No - separate singletons |
| `AGENT_SKILL_MAPPING` | `skills_wizard.py` | `autoconfig_handler.py:_recommend_skills_for_preview()` | Same data, imported from same module |

### 5.2 Dashboard-ONLY Components (Not in CLI)

| Component | Purpose | Why Not In CLI |
|-----------|---------|----------------|
| `BackupManager` | Pre-operation filesystem backups | CLI has no backup/restore |
| `OperationJournal` | Crash-recovery journal | CLI operations are synchronous |
| `DeploymentVerifier` | Post-deploy filesystem checks | CLI trusts service return values |
| `ConfigEventHandler` | Socket.IO real-time events | CLI uses console output |
| `ConfigFileWatcher` | External change detection | CLI is ephemeral |
| `ConfigScope` enum | Project vs user path resolution | CLI uses hardcoded paths |
| `config_file_lock` | File-level locking | CLI has no concurrent access |
| `validation.py` | Safe name + path containment checks | CLI validates in argparse |

### 5.3 Key Differences in Auto-Configure Flow

| Aspect | CLI Path | Dashboard API Path |
|--------|----------|--------------------|
| **Entry point** | `AutoConfigureCommand.execute()` | `POST /api/config/auto-configure/apply` |
| **Execution model** | Synchronous (blocking) | Async background task with `asyncio.create_task` |
| **Progress reporting** | Console print statements | Socket.IO events (`autoconfig_progress`) |
| **Result delivery** | Return code + console output | Socket.IO event (`autoconfig_completed`) + HTTP 202 |
| **Skill deployment** | Not included in auto-configure | Integrated as Phase 5 of the pipeline |
| **Backup before apply** | None | `BackupManager.create_backup()` |
| **Post-deploy verification** | None | `DeploymentVerifier.verify_agent_deployed()` |
| **Safety validation** | Argparse validation only | `validate_safe_name()` + `validate_path_containment()` |
| **Error recovery** | CLI exits with error code | `OperationJournal` + backup restore |
| **User confirmation** | Interactive Y/N prompt | Type "apply" in UI modal |
| **Concurrency** | Single-threaded | `asyncio.to_thread()` for blocking calls |
| **min_confidence default** | 0.5 (fixed after bug fix) | 0.5 (aligned in `e13b7afc`) |

---

## 6. Dashboard UI Architecture

### 6.1 Tab Structure

The "Config" tab is added to `+page.svelte` as a new `ViewMode`:

```
+page.svelte (ViewMode = 'config')
├── Left Panel: ConfigView panelSide="left"
│   ├── Summary Cards (agent/skill/source counts)
│   ├── Auto-Configure Button → opens AutoConfigPreview modal
│   ├── Sub-tabs: Agents | Skills | Sources | Skill Links
│   ├── ValidationPanel (always visible)
│   └── List Component (AgentsList / SkillsList / SourcesList / SkillLinksView)
│
└── Right Panel: ConfigView panelSide="right"
    ├── AgentDetailPanel (when agent selected)
    ├── SkillDetailPanel (when skill selected)
    ├── Source Detail (inline, when source selected)
    └── Empty State (nothing selected)
```

### 6.2 Auto-Configure Modal Flow (AutoConfigPreview.svelte)

```
Step 1: Detect & Recommend
├── "Analyze Project" button → detectToolchain() + previewAutoConfig()
├── Shows: Detected toolchain (language, frameworks, build tools)
├── Shows: Recommended agents with confidence scores
├── Shows: Recommended skills (from AGENT_SKILL_MAPPING)
├── Shows: Validation status (passed/errors/warnings)
└── "Next: Review Changes" button → Step 2

Step 2: Review & Apply
├── Shows: Agents to deploy (green badges)
├── Shows: Agents skipped - low confidence (amber badges)
├── Shows: Skills to deploy (green badges)
├── Shows: Estimated deployment time
├── Type "apply" confirmation input
├── "Apply Auto-Configuration" button → handleApply()
│   ├── Sends POST /api/config/auto-configure/apply
│   ├── Gets job_id back (HTTP 202)
│   ├── Subscribes to Socket.IO autoconfig events
│   ├── DeploymentPipeline shows progress: Detect → Recommend → Backup → Agents → Skills → Verify
│   └── On completion: shows success + "Restart Required" notice
└── On error: shows error message, pipeline stage marked as failed
```

### 6.3 Real-Time Event System

```
Backend (Python)                     Socket.IO                     Frontend (Svelte)
─────────────────────────────────────────────────────────────────────────────────────
ConfigEventHandler.emit_config_event()
    ↓
sio.emit("config_event", {...})  ───────►  +page.svelte: sock.on('config_event')
                                                              ↓
                                                         handleConfigEvent()
                                                              ↓
                                                         Switch on operation:
                                                         ├─ autoconfig_progress → _notifyAutoConfigListeners()
                                                         ├─ autoconfig_completed → resolve waitForAutoConfigCompletion()
                                                         ├─ autoconfig_failed → reject waitForAutoConfigCompletion()
                                                         ├─ agent_deployed → refresh agent stores
                                                         ├─ skill_deployed → refresh skill stores
                                                         ├─ sync_progress → update syncStatus store
                                                         └─ external_change → toast + refresh sources
```

---

## 7. Response Formats

### 7.1 Toolchain Detection Response

```json
{
  "success": true,
  "toolchain": {
    "primary_language": "Python",
    "primary_confidence": "HIGH",
    "frameworks": [
      { "name": "FastAPI", "version": "0.100+", "framework_type": "web", "confidence": "HIGH" }
    ],
    "build_tools": [{ "name": "uv", "confidence": "HIGH" }],
    "package_managers": [{ "name": "pip", "confidence": "HIGH" }],
    "deployment_target": { "target_type": "docker", "platform": "Docker", "confidence": "MEDIUM" },
    "overall_confidence": "HIGH",
    "metadata": {}
  }
}
```

### 7.2 Preview Response

```json
{
  "success": true,
  "preview": {
    "would_deploy": ["python-engineer", "fastapi-specialist"],
    "would_skip": ["generic-web-dev"],
    "deployment_count": 2,
    "estimated_deployment_time": 10.0,
    "requires_confirmation": true,
    "recommendations": [
      {
        "agent_id": "python-engineer",
        "agent_name": "Python Engineer",
        "confidence_score": 0.92,
        "rationale": "Primary language is Python with FastAPI framework",
        "match_reasons": ["Python detected", "FastAPI framework"],
        "deployment_priority": 1
      }
    ],
    "validation": {
      "is_valid": true,
      "error_count": 0,
      "warning_count": 1
    },
    "toolchain": { "..." },
    "skill_recommendations": ["fastapi-local-dev", "test-driven-development"],
    "would_deploy_skills": ["fastapi-local-dev", "test-driven-development"],
    "metadata": {}
  }
}
```

### 7.3 Apply Response (HTTP 202)

```json
{
  "success": true,
  "message": "Auto-configure started",
  "job_id": "autoconfig-1740150000-abc123",
  "status": "in_progress"
}
```

### 7.4 Socket.IO Completion Event

```json
{
  "type": "config_event",
  "operation": "autoconfig_completed",
  "entity_type": "autoconfig",
  "entity_id": "autoconfig-1740150000-abc123",
  "status": "completed",
  "data": {
    "job_id": "autoconfig-1740150000-abc123",
    "deployed_agents": ["python-engineer", "fastapi-specialist"],
    "failed_agents": [],
    "deployed_skills": ["fastapi-local-dev", "test-driven-development"],
    "skill_errors": [],
    "needs_restart": true,
    "backup_id": "backup-20260221-123456",
    "duration_ms": 8432,
    "verification": {
      "python-engineer": { "passed": true },
      "fastapi-specialist": { "passed": true }
    }
  },
  "timestamp": "2026-02-21T12:00:00.000Z"
}
```

---

## 8. Dependency Injection Pattern

### 8.1 Dashboard API: Lazy Singletons

The dashboard uses a module-level lazy singleton pattern for all services:

```python
# autoconfig_handler.py
_toolchain_analyzer = None
_auto_config_manager = None

def _get_toolchain_analyzer():
    global _toolchain_analyzer
    if _toolchain_analyzer is None:
        from claude_mpm.services.project.toolchain_analyzer import ToolchainAnalyzerService
        _toolchain_analyzer = ToolchainAnalyzerService()
    return _toolchain_analyzer

def _get_auto_config_manager():
    global _auto_config_manager
    if _auto_config_manager is None:
        toolchain_analyzer = _get_toolchain_analyzer()
        agent_recommender = AgentRecommenderService()
        agent_registry = AgentRegistry()  # optional, graceful degradation
        _auto_config_manager = AutoConfigManagerService(
            toolchain_analyzer=toolchain_analyzer,
            agent_recommender=agent_recommender,
            agent_registry=agent_registry,
        )
    return _auto_config_manager
```

### 8.2 CLI: Container-Based DI

The CLI uses a service container pattern:

```python
# auto_configure.py
auto_config_mgr = AutoConfigManagerService(container=container)
result = await auto_config_mgr.auto_configure(project_path, ...)
```

### 8.3 Implication

The same core services are instantiated **independently** in CLI and Dashboard contexts. They share no state at runtime. Configuration changes made via the dashboard would be detected by the CLI only through filesystem changes.

---

## 9. Safety Infrastructure (Dashboard-Only)

### 9.1 Backup Protocol

Every destructive operation follows: **backup → journal → execute → verify → prune**

```
BackupManager.create_backup("auto_configure", "config", job_id)
    → Creates ~/.claude-mpm/backups/{backup_id}/
    → Copies agents/, skills/, config/ directories
    → Writes metadata.json
    → Returns BackupResult with backup_id
    → Auto-prunes to MAX_BACKUPS=5
```

### 9.2 Operation Journal

```
OperationJournal.begin_operation("deploy_agent", "agent", agent_name, backup_id)
    → Records operation start in journal file
    → Returns operation_id
    → On success: complete_operation(op_id)
    → On failure: fail_operation(op_id, error)
    → Enables crash recovery: incomplete journal entries can be detected on restart
```

### 9.3 Deployment Verification

```
DeploymentVerifier.verify_agent_deployed(agent_name)
    → Check 1: File exists at agents_dir/{agent_name}.md
    → Check 2: File has valid YAML frontmatter
    → Check 3: Required fields present (name, description)
    → Check 4: File size non-zero and < 10 MB
    → Returns VerificationResult with per-check details
```

### 9.4 Input Validation (Security)

```python
# C-01: validate_safe_name(agent_name, "agent")
#   - No path separators (/, \)
#   - No path traversal (..)
#   - ASCII-safe characters only
#   - Prevents injection attacks

# C-02: validate_path_containment(agent_path, agents_dir, "agent")
#   - Ensures resolved path is within expected directory
#   - Defence in depth against path traversal
```

---

## 10. Skill Deployment in Auto-Configure

The dashboard auto-configure path adds a **Phase 5: Skill Deployment** that does NOT exist in the CLI auto-configure:

```python
# autoconfig_handler.py:_run_auto_configure() - Phase 5
def _recommend_and_deploy_skills():
    from claude_mpm.cli.interactive.skills_wizard import AGENT_SKILL_MAPPING

    recommended_skills = set()
    for agent_id in would_deploy:
        agent_skills = AGENT_SKILL_MAPPING.get(agent_id, [])
        recommended_skills.update(agent_skills)

    svc = _get_skills_deployer()
    project_skills_dir = resolve_skills_dir(ConfigScope.PROJECT, project_path)
    return svc.deploy_skills(skill_names=sorted(recommended_skills), ...)
```

This imports `AGENT_SKILL_MAPPING` from the CLI's `skills_wizard.py` - a direct cross-module dependency. The mapping is a static dict that associates agent IDs with recommended skills.

Skills are deployed to **project-scoped** directory (`.claude/skills/`) using the new `ConfigScope` enum, not the user-level `~/.claude/skills/`.

---

## 11. Route Registration in server.py

The branch modifies `UnifiedMonitorServer._setup_http_routes()` to register all new routes:

```python
# server.py (diff from main)

# Phase 2: Config event infrastructure
from claude_mpm.services.monitor.handlers.config_handler import (
    ConfigEventHandler, ConfigFileWatcher,
)
self.config_event_handler = ConfigEventHandler(self.sio)
self.config_file_watcher = ConfigFileWatcher(self.config_event_handler)
self.config_file_watcher.start()

# Phase 1: Read-only config routes
register_config_routes(self.app, server_instance=self)

# Phase 2: Source mutation routes
register_source_routes(self.app, self.config_event_handler, self.config_file_watcher)

# Phase 3: Deployment routes
register_agent_deployment_routes(self.app, self.config_event_handler, self.config_file_watcher)
register_skill_deployment_routes(self.app, self.config_event_handler, self.config_file_watcher)
register_autoconfig_routes(self.app, self.config_event_handler, self.config_file_watcher)
```

Also adds:
- **CORS middleware** for Vite dev server cross-origin requests
- **ConfigFileWatcher cleanup** on server shutdown

---

## 12. Feature Flags

The dashboard uses feature flags in `features.ts` for progressive rollout:

```typescript
export const FEATURES = {
    RICH_DETAIL_PANELS: true,      // Phase 3A
    FILTER_DROPDOWNS: true,         // Phase 3B
    VERSION_MISMATCH: true,         // Phase 3B
    COLLABORATION_LINKS: true,      // Phase 3C
    SKILL_LINKS_MERGE: true,        // Phase 3C
    SEARCH_ENHANCEMENTS: true,      // Phase 3B
};
```

These flags allow disabling individual UI features without removing code, enabling safe incremental rollout.

---

## 13. Testing Coverage

The branch adds test files (on the branch, not main):

| Test File | Coverage |
|-----------|----------|
| `tests/services/config_api/test_autoconfig_defaults.py` | Default min_confidence values |
| `tests/services/config_api/test_autoconfig_events.py` | Socket.IO event emission |
| `tests/services/config_api/test_autoconfig_integration.py` | End-to-end auto-configure flow |
| `tests/services/config_api/test_autoconfig_skill_deployment.py` | Skill deployment in auto-configure |
| `tests/test_config_api_business_rules.py` | Business rules (core agents, etc.) |
| `tests/test_config_api_deployment.py` | Agent deployment operations |
| `tests/test_config_api_rollback.py` | Rollback on failure |
| `tests/test_config_routes.py` | Read-only config routes |
| `dashboard-svelte/src/lib/components/config/__tests__/SkillChip.test.ts` | Svelte component test |

---

## 14. Key Observations

1. **Skill deployment is dashboard-only**: The CLI auto-configure does NOT deploy skills. The dashboard adds this as Phase 5, using `AGENT_SKILL_MAPPING` from the CLI's skills wizard.

2. **Safety infrastructure is dashboard-only**: Backup, journal, verification, and file locking are exclusive to the dashboard path. The CLI has none of these protections.

3. **Async model divergence**: CLI is synchronous/blocking. Dashboard uses `asyncio.create_task()` with `asyncio.to_thread()` wrappers, returning HTTP 202 and delivering results via Socket.IO.

4. **Separate instantiation**: Core services (ToolchainAnalyzer, AutoConfigManager, AgentRecommender) are instantiated independently in CLI and dashboard contexts with different DI patterns.

5. **Path resolution centralized**: New `ConfigScope` enum centralizes project-vs-user path resolution, used by dashboard handlers. CLI still uses scattered hardcoded paths.

6. **CORS added**: The branch adds CORS middleware to the aiohttp server, enabling Vite dev server to communicate with the API during development.

7. **ConfigFileWatcher**: Dashboard monitors config files for external changes (5s polling), enabling the UI to refresh when CLI modifies files.

8. **Bug fix in CLI**: The branch fixes a bug where `min_confidence=0.0` was treated as falsy (None), now correctly uses `is not None` check.
