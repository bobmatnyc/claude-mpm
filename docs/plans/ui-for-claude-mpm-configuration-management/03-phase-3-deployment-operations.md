# Phase 3: Deployment Operations

> **Implementation Plan for Agent/Skill Deployment, Mode Switching, and Auto-Configure Preview**
>
> Date: 2026-02-13
> Branch: `ui-agents-skills-config`
> Status: Planning
> Risk Level: HIGH

---

## Table of Contents

1. [Phase Summary](#1-phase-summary)
2. [Prerequisites](#2-prerequisites)
3. [Backend Implementation](#3-backend-implementation)
4. [Frontend Implementation](#4-frontend-implementation)
5. [Safety Mechanisms](#5-safety-mechanisms)
6. [Rollback Strategy](#6-rollback-strategy)
7. [Testing Plan](#7-testing-plan)
8. [Definition of Done](#8-definition-of-done)
9. [Devil's Advocate Notes](#9-devils-advocate-notes)
10. [Files Created/Modified](#10-files-createdmodified)
11. [Estimated Effort Breakdown](#11-estimated-effort-breakdown)

---

## 1. Phase Summary

**Goal**: Allow deploying/undeploying agents and skills, switching skill deployment modes (agent_referenced vs user_defined), and previewing auto-configuration recommendations from the dashboard UI.

**Timeline**: 2-3 weeks

**Risk Level**: HIGH -- Deployment operations change runtime behavior and affect active Claude Code sessions.

**Dependencies**: Phase 1 (read-only dashboard) and Phase 2 (source management, `ConfigFileLock`, shared UI components) must be complete.

### Why HIGH Risk

- Deploying/undeploying agents changes what Claude Code can use in future sessions
- No hot-reload: changes require Claude Code session restart to take effect (Risk C-4 from risk assessment)
- Mode switching (`agent_referenced` to `user_defined`) changes ALL skill deployment logic and can result in an empty skill list (Risk UX-2)
- Auto-configure can overwrite manual customizations (Risk O-3)
- Partial deployment failures can leave an inconsistent state in `.claude/agents/` or `~/.claude/skills/` (Risk O-2)
- Active Claude Code sessions will not pick up configuration changes until restarted
- Concurrent CLI + UI operations can cause lost updates without proper coordination (Risk C-1)

### Phase 3 Scope at a Glance

| Category | Endpoints | Components | New Files |
|----------|-----------|------------|-----------|
| Agent Operations | 4 | 1 updated + 1 new | 2 backend, 1 frontend |
| Skill Operations | 4 | 1 updated + 1 new | 2 backend, 1 frontend |
| Auto-Configure | 3 | 1 new | 1 backend, 1 frontend |
| Safety Infrastructure | 0 | 2 new | 4 backend, 2 frontend |
| **Total** | **11** | **6 updated/new** | **~12** |

---

## 2. Prerequisites

These must be built during the first week before any deployment endpoint is exposed. All are blocking.

### 2.1 Backup/Restore Pipeline Integration

`AgentFileSystemManager` already has `backup_agents_directory()` and `restore_agents_from_backup()` methods (identified in risk assessment, Risk O-2). However, these are NOT automatically invoked during deployment. Phase 3 requires integrating them into every deployment flow.

**Approach**:

```
backup -> deploy -> verify -> (rollback on failure OR prune old backups on success)
```

**Backup storage**: `~/.claude-mpm/backups/{timestamp}/`

Directory structure per backup:
```
~/.claude-mpm/backups/
  2026-02-15T10-30-00/
    agents/              # Copy of .claude/agents/ at backup time
      engineer.md
      research.md
      ...
    skills/              # Copy of ~/.claude/skills/ at backup time
      universal-debugging-systematic-debugging/
      ...
    config/              # Copy of configuration files
      configuration.yaml
    metadata.json        # { created_at, operation, entity_type, entity_id, files_backed_up }
```

**Retention policy**: Keep last 5 backups, auto-prune older ones after successful operations. Implemented as a utility function called at the end of each successful deployment.

**Implementation file**: `src/claude_mpm/services/config_api/backup_manager.py`

```python
class BackupManager:
    BACKUP_ROOT = Path.home() / ".claude-mpm" / "backups"
    MAX_BACKUPS = 5

    def create_backup(
        self, operation: str, entity_type: str, entity_id: str
    ) -> BackupResult:
        """Create a timestamped backup before a destructive operation."""
        ...

    def restore_from_backup(self, backup_id: str) -> RestoreResult:
        """Restore agents/skills/config from a named backup."""
        ...

    def list_backups(self) -> List[BackupMetadata]:
        """List available backups with metadata."""
        ...

    def prune_old_backups(self) -> int:
        """Remove backups beyond MAX_BACKUPS retention. Returns count removed."""
        ...
```

**BackupResult dataclass**:
```python
@dataclass
class BackupResult:
    backup_id: str          # Timestamp-based ID
    backup_path: Path       # Full path to backup directory
    files_backed_up: int    # Number of files copied
    size_bytes: int         # Total backup size
    created_at: str         # ISO timestamp
    operation: str          # "deploy_agent", "undeploy_agent", etc.
    entity_type: str        # "agent", "skill", "config"
    entity_id: str          # Name of entity being modified
```

### 2.2 Operation Journal

Provides crash recovery. Before executing any destructive operation, write intent to a journal file. On server startup, check for incomplete operations and surface them to the user.

**File**: `~/.claude-mpm/.operation-journal.json`

**Schema**:
```json
{
  "version": "1.0",
  "entries": [
    {
      "id": "op-1708000000-abc123",
      "operation": "deploy_agent",
      "entity_type": "agent",
      "entity_id": "python-engineer",
      "started_at": "2026-02-15T10:30:00Z",
      "status": "in_progress",
      "backup_id": "2026-02-15T10-30-00",
      "rollback_info": {
        "backup_path": "~/.claude-mpm/backups/2026-02-15T10-30-00/",
        "files_to_restore": [".claude/agents/python-engineer.md"]
      },
      "completed_at": null,
      "error": null
    }
  ]
}
```

**Status transitions**: `pending` -> `in_progress` -> `completed` | `failed` | `rolled_back`

**Recovery logic** (runs on server startup):
1. Read journal file
2. Find entries with `status: "in_progress"` (indicates crash during operation)
3. For each incomplete entry:
   - Check if the operation's target files exist and are valid
   - If target is inconsistent: mark as `needs_rollback`, surface warning in dashboard
   - If target is consistent: mark as `completed` (operation finished before journal updated)
4. Do NOT auto-rollback -- surface to user and let them decide

**Implementation file**: `src/claude_mpm/services/config_api/operation_journal.py`

```python
class OperationJournal:
    JOURNAL_PATH = Path.home() / ".claude-mpm" / ".operation-journal.json"

    def begin_operation(
        self, operation: str, entity_type: str, entity_id: str,
        backup_id: str, rollback_info: dict
    ) -> str:
        """Write intent before execution. Returns operation ID."""
        ...

    def complete_operation(self, operation_id: str) -> None:
        """Mark operation as completed."""
        ...

    def fail_operation(self, operation_id: str, error: str) -> None:
        """Mark operation as failed."""
        ...

    def check_incomplete_operations(self) -> List[JournalEntry]:
        """Find operations that were interrupted (status=in_progress)."""
        ...

    def mark_rolled_back(self, operation_id: str) -> None:
        """Mark an incomplete operation as rolled back."""
        ...
```

> **Devil's advocate note**: The operation journal adds complexity. For Phase 3, consider whether a simpler approach (just backups without journal) is sufficient. The journal is most valuable when the server crashes mid-deploy, which is a low-probability event. See [Section 9, Note 5](#9-devils-advocate-notes).

### 2.3 Active Session Detection

Check for running Claude Code processes and show a warning banner in the dashboard when configuration changes are made. This is informational only -- it does not block operations.

**Detection method**:
```python
import subprocess

def detect_active_claude_sessions() -> List[Dict[str, str]]:
    """Check for running Claude Code processes.

    Returns list of detected sessions with pid and command info.
    """
    try:
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True, text=True, timeout=5
        )
        # Look for claude-related processes
        sessions = []
        for line in result.stdout.splitlines():
            if any(pattern in line.lower() for pattern in [
                "claude", "claude-code", "claude_code"
            ]):
                parts = line.split()
                if len(parts) >= 2:
                    sessions.append({
                        "pid": parts[1],
                        "command": " ".join(parts[10:]) if len(parts) > 10 else "claude"
                    })
        return sessions
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []  # Fail open -- don't block if detection fails
```

**API endpoint**: `GET /api/config/active-sessions`

**Response**:
```json
{
  "success": true,
  "active_sessions": [
    { "pid": "12345", "command": "claude --project /path/to/project" }
  ],
  "has_active_sessions": true,
  "warning_message": "Active Claude Code sessions detected. Configuration changes will take effect on next session start."
}
```

**Frontend integration**: An amber warning banner rendered at the top of ConfigView when `has_active_sessions` is true. Auto-refreshes on each config operation (call the endpoint after every deploy/undeploy/mode-switch).

> **Warning**: Active session detection via `ps` is brittle. Process names vary across operating systems and Claude Code versions. The detection patterns may need updating. This should be treated as best-effort, not a guarantee. See [Section 9, Note 4](#9-devils-advocate-notes).

### 2.4 Post-Deployment Verification

After every deploy or undeploy operation, verify the result before returning success. Verification is entity-type-specific.

**Agent verification** (after deploy):
1. Target file exists at expected path (`.claude/agents/{name}.md`)
2. File is parseable (valid YAML frontmatter + markdown body)
3. Required frontmatter fields present (`name`, `description`, `version`, `model`)
4. File size is non-zero and reasonable (< 10MB per `SecurityConfig.max_file_size_mb`)

**Agent verification** (after undeploy):
1. Target file no longer exists
2. No orphaned related files

**Skill verification** (after deploy):
1. Target directory exists at expected path (`~/.claude/skills/{deployment_name}/`)
2. Directory contains at least one file
3. Main skill file is parseable

**Skill verification** (after undeploy):
1. Target directory no longer exists
2. Deployment tracking index updated (`.mpm-deployed-skills.json`)

**Mode switch verification**:
1. Configuration file (`configuration.yaml`) reflects new mode
2. `skills.user_defined` or `skills.agent_referenced` list matches expected state
3. Configuration file is parseable after write

**Verification response schema** (included in every deployment API response):
```json
{
  "verification": {
    "passed": true,
    "checks": [
      { "check": "file_exists", "passed": true, "path": ".claude/agents/python-engineer.md" },
      { "check": "parse_valid", "passed": true, "details": "YAML frontmatter parsed successfully" },
      { "check": "required_fields", "passed": true, "details": "name, description, version, model present" }
    ],
    "timestamp": "2026-02-15T10:30:05Z"
  }
}
```

**Implementation file**: `src/claude_mpm/services/config_api/deployment_verifier.py`

---

## 3. Backend Implementation

All endpoints are registered under `/api/config/` in the `_setup_config_routes()` method of `UnifiedMonitorServer`, following the pattern established in Phase 2.

### 3.1 Agent Endpoints (4 Endpoints)

#### Endpoint 1: `POST /api/config/agents/deploy`

Deploy a single agent from the cache to the project.

**Service**: `AgentDeploymentService.deploy_agent()`

**Flow**: Detect sessions -> Backup -> Copy from cache to `.claude/agents/` -> Verify -> Respond

**Request**:
```json
{
  "agent_name": "python-engineer",
  "source_id": "bobmatnyc/claude-mpm-agents/agents",
  "force": false
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `agent_name` | string | Yes | Name of agent to deploy |
| `source_id` | string | No | Specific source to deploy from (uses highest priority if omitted) |
| `force` | boolean | No | Force re-deploy if already deployed (default: false) |

**Implementation pattern** (BLOCKING -- must use `asyncio.to_thread()`):
```python
async def agents_deploy(request):
    data = await request.json()
    agent_name = data.get("agent_name")
    source_id = data.get("source_id")
    force = data.get("force", False)

    if not agent_name:
        return web.json_response(
            {"success": False, "error": "agent_name is required", "code": "VALIDATION_ERROR"},
            status=400
        )

    # Check if already deployed (unless force=True)
    agents_dir = Path.cwd() / ".claude" / "agents"
    agent_path = agents_dir / f"{agent_name}.md"
    if agent_path.exists() and not force:
        return web.json_response(
            {"success": False,
             "error": f"Agent '{agent_name}' is already deployed. Use force=true to redeploy.",
             "code": "CONFLICT"},
            status=409
        )

    # Check agent exists in cache
    # Backup -> Deploy -> Verify (all in thread)
    result = await asyncio.to_thread(_deploy_agent_sync, agent_name, source_id, force)

    # Emit Socket.IO event
    if self.sio and result["success"]:
        await self.sio.emit("config_event", {
            "type": "config_event",
            "subtype": "agent_deployed",
            "data": {"agent_name": agent_name, "action": "deploy"},
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    status_code = 200 if result["success"] else result.get("status_code", 500)
    return web.json_response(result, status=status_code)
```

**Success response (200)**:
```json
{
  "success": true,
  "message": "Agent 'python-engineer' deployed successfully",
  "agent_name": "python-engineer",
  "file_path": "/path/to/project/.claude/agents/python-engineer.md",
  "backup_id": "2026-02-15T10-30-00",
  "verification": {
    "passed": true,
    "checks": [
      { "check": "file_exists", "passed": true },
      { "check": "parse_valid", "passed": true },
      { "check": "required_fields", "passed": true }
    ]
  },
  "active_sessions_warning": true
}
```

**Error responses**:

| Status | Code | Condition |
|--------|------|-----------|
| 400 | `VALIDATION_ERROR` | Missing `agent_name` |
| 404 | `NOT_FOUND` | Agent not found in cache |
| 409 | `CONFLICT` | Already deployed (without `force=true`) |
| 500 | `DEPLOY_FAILED` | Deployment or verification failure |

---

#### Endpoint 2: `DELETE /api/config/agents/{agent_name}`

Undeploy an agent from the project. Enforces BR-01: core agents cannot be undeployed.

**Business Rule BR-01 enforcement**:
```python
CORE_AGENTS = ["engineer", "research", "qa", "web-qa", "documentation", "ops", "ticketing"]

if agent_name in CORE_AGENTS:
    return web.json_response({
        "success": False,
        "error": f"Cannot undeploy core agent '{agent_name}'. Core agents are always required.",
        "code": "CORE_AGENT_PROTECTED",
        "core_agents": CORE_AGENTS
    }, status=403)
```

**Flow**: Check not core -> Backup -> Remove from `.claude/agents/` -> Verify removed -> Respond

**Success response (200)**:
```json
{
  "success": true,
  "message": "Agent 'python-engineer' removed from project",
  "agent_name": "python-engineer",
  "backup_id": "2026-02-15T10-31-00",
  "active_sessions_warning": true
}
```

**Error responses**:

| Status | Code | Condition |
|--------|------|-----------|
| 403 | `CORE_AGENT_PROTECTED` | Attempting to undeploy a core agent |
| 404 | `NOT_FOUND` | Agent not currently deployed |
| 500 | `SERVICE_ERROR` | File removal failed |

---

#### Endpoint 3: `POST /api/config/agents/deploy-collection`

Batch deploy multiple agents. Deploys sequentially (not parallel) for filesystem safety.

**Request**:
```json
{
  "agents": ["python-engineer", "api-qa", "security"],
  "source_id": "bobmatnyc/claude-mpm-agents/agents",
  "force": false
}
```

**Implementation notes**:
- Deploy agents one at a time in sequence
- If one fails, continue with remaining agents (do not abort the batch)
- Each agent gets its own backup entry
- Return per-agent results plus a summary

**Success response (200)**:
```json
{
  "success": true,
  "results": [
    { "agent_name": "python-engineer", "status": "deployed", "error": null },
    { "agent_name": "api-qa", "status": "deployed", "error": null },
    { "agent_name": "security", "status": "skipped", "error": "Already deployed" }
  ],
  "summary": {
    "deployed": 2,
    "failed": 0,
    "skipped": 1,
    "total": 3
  },
  "backup_id": "2026-02-15T10-32-00",
  "active_sessions_warning": true
}
```

> **Warning**: Batch deploy of 20+ agents at once could take 30+ seconds. Progress feedback is essential. The endpoint should emit Socket.IO progress events per-agent during batch deployment. See [Section 9, Note 3](#9-devils-advocate-notes).

---

#### Endpoint 4: `GET /api/config/agents/collections`

List agent collections from source metadata. Used for the "Deploy Collection" UI.

**Service**: `AutoDeployIndexParser` to enumerate categories/collections from cached source metadata.

**Success response (200)**:
```json
{
  "success": true,
  "collections": [
    {
      "id": "python-fullstack",
      "name": "Python Full-Stack",
      "description": "Complete Python development team",
      "agent_count": 5,
      "agents": ["python-engineer", "api-qa", "security", "ops", "version-control"]
    },
    {
      "id": "frontend-react",
      "name": "React Frontend",
      "description": "React + TypeScript frontend team",
      "agent_count": 4,
      "agents": ["react-engineer", "web-qa", "ui-ux", "accessibility"]
    }
  ],
  "total": 8
}
```

---

### 3.2 Skill Endpoints (4 Endpoints)

#### Endpoint 5: `POST /api/config/skills/deploy`

Deploy a single skill from the cache.

**Service**: `SkillsDeployerService`

**Request**:
```json
{
  "skill_name": "systematic-debugging",
  "mark_user_requested": true,
  "force": false
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `skill_name` | string | Yes | Skill to deploy |
| `mark_user_requested` | boolean | No | Add to `user_defined` list in config (default: true) |
| `force` | boolean | No | Force re-deploy (default: false) |

**Business logic for `mark_user_requested`**:
- When `true`: adds the skill to the `skills.user_defined` list in `configuration.yaml`
- This persists the skill across redeployments -- it will not be cleaned up as an orphan
- Uses `ConfigFileLock` when writing to `configuration.yaml`

**BLOCKING** -- must use `asyncio.to_thread()`

**Success response (200)**:
```json
{
  "success": true,
  "message": "Skill 'systematic-debugging' deployed successfully",
  "skill_name": "systematic-debugging",
  "deploy_path": "/Users/user/.claude/skills/universal-debugging-systematic-debugging",
  "user_requested": true,
  "verification": {
    "passed": true,
    "checks": [
      { "check": "directory_exists", "passed": true },
      { "check": "has_skill_files", "passed": true }
    ]
  }
}
```

---

#### Endpoint 6: `DELETE /api/config/skills/{skill_name}`

Undeploy a skill. Enforces immutability of `PM_CORE_SKILLS` and `CORE_SKILLS`.

**Business rule**: `PM_CORE_SKILLS` (10 skills) and `CORE_SKILLS` (27 skills) are immutable. Return 403 if attempted.

**Immutable skill check**:
```python
from claude_mpm.services.skills.selective_skill_deployer import PM_CORE_SKILLS, CORE_SKILLS

immutable_skills = PM_CORE_SKILLS | CORE_SKILLS  # Union of both sets

# Normalize skill_name for comparison (strip prefix patterns)
if normalized_skill_name in immutable_skills:
    return web.json_response({
        "success": False,
        "error": f"Cannot undeploy system skill '{skill_name}'. This skill is required by the framework.",
        "code": "IMMUTABLE_SKILL",
        "immutable_reason": "PM_CORE_SKILL" if normalized_skill_name in PM_CORE_SKILLS else "CORE_SKILL"
    }, status=403)
```

**Success response (200)**:
```json
{
  "success": true,
  "message": "Skill 'custom-workflow' removed",
  "skill_name": "custom-workflow",
  "backup_id": "2026-02-15T10-35-00"
}
```

**Error responses**:

| Status | Code | Condition |
|--------|------|-----------|
| 403 | `IMMUTABLE_SKILL` | Attempting to undeploy a core/PM skill |
| 404 | `NOT_FOUND` | Skill not currently deployed |
| 500 | `SERVICE_ERROR` | Removal failed |

---

#### Endpoint 7: `GET /api/config/skills/deployment-mode`

Return the current skill deployment mode with context.

**Success response (200)**:
```json
{
  "success": true,
  "mode": "agent_referenced",
  "skill_counts": {
    "agent_referenced": 25,
    "user_defined": 3,
    "pm_core": 10,
    "core": 27,
    "total_deployed": 42
  },
  "explanation": "Skills are automatically deployed based on agent frontmatter requirements. 3 skills are additionally user-requested."
}
```

---

#### Endpoint 8: `PUT /api/config/skills/deployment-mode`

Switch between `agent_referenced` and `user_defined` deployment modes.

**This is a DANGEROUS OPERATION** requiring two-step confirmation.

**Request (preview)**:
```json
{
  "mode": "user_defined",
  "preview": true
}
```

**Request (confirm)**:
```json
{
  "mode": "user_defined",
  "confirm": true,
  "skills": ["skill-a", "skill-b", "skill-c"]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `mode` | string | Yes | `"agent_referenced"` or `"user_defined"` |
| `preview` | boolean | No | Return impact preview without applying (default: false) |
| `confirm` | boolean | No | Required to actually apply the change (default: false) |
| `skills` | string[] | Conditional | Required when confirming switch to `user_defined` |

**Two-step flow**:

**Step 1 -- Preview** (`preview: true`):
```json
{
  "success": true,
  "preview": true,
  "current_mode": "agent_referenced",
  "new_mode": "user_defined",
  "impact": {
    "skills_added": [],
    "skills_removed": ["react-testing", "django-core", "...15 more"],
    "skills_unchanged": ["systematic-debugging", "git-workflow", "test-driven-development"],
    "total_after_switch": 3,
    "warning": "Switching to user_defined mode with only 3 skills. 17 agent-referenced skills will no longer be deployed."
  }
}
```

**Step 2 -- Confirm** (`confirm: true`):
- Requires `ConfigFileLock` on `configuration.yaml`
- Backs up current configuration before switching
- Writes new mode and skill list to config
- Verifies config file after write

**Risk UX-2 guard**: If switching to `user_defined` and the provided `skills` list is empty:
```json
{
  "success": false,
  "error": "Cannot switch to user_defined mode with an empty skill list. This would remove ALL skills. Pre-populate from current agent_referenced list or provide at least one skill.",
  "code": "EMPTY_SKILL_LIST",
  "suggestion": "Use preview=true first to see the current agent_referenced skills, then include them in the skills array."
}
```

**Confirm success response (200)**:
```json
{
  "success": true,
  "message": "Deployment mode changed to 'user_defined'",
  "mode": "user_defined",
  "skills_count": 15,
  "backup_id": "2026-02-15T10-40-00",
  "active_sessions_warning": true
}
```

**Error responses**:

| Status | Code | Condition |
|--------|------|-----------|
| 400 | `VALIDATION_ERROR` | Invalid mode value |
| 400 | `EMPTY_SKILL_LIST` | user_defined with empty skills list |
| 400 | `CONFIRMATION_REQUIRED` | Neither `preview` nor `confirm` set to true |
| 409 | `ALREADY_IN_MODE` | Already in the requested mode |
| 500 | `SERVICE_ERROR` | Config write failed |

---

### 3.3 Auto-Configure Endpoints (3 Endpoints)

#### Endpoint 9: `POST /api/config/auto-configure/detect`

Detect the project toolchain. Fast operation with 5-minute TTL cache.

**Service**: `ToolchainAnalyzerService.analyze_toolchain()`

**BLOCKING** -- must use `asyncio.to_thread()`

**Request**:
```json
{
  "project_path": "/path/to/project"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `project_path` | string | No | Project root (default: server's working directory) |

**Success response (200)**:
```json
{
  "success": true,
  "toolchain": {
    "primary_language": "python",
    "primary_confidence": 0.95,
    "secondary_languages": ["javascript", "shell"],
    "frameworks": [
      { "name": "fastapi", "version": "0.100+", "type": "web", "confidence": 0.95 },
      { "name": "svelte", "version": "5.x", "type": "frontend", "confidence": 0.85 }
    ],
    "build_tools": [
      { "name": "uv", "confidence": 0.9 },
      { "name": "npm", "confidence": 0.8 }
    ],
    "package_managers": [
      { "name": "uv", "confidence": 0.9 },
      { "name": "npm", "confidence": 0.8 }
    ],
    "deployment_target": {
      "platform": "docker",
      "target_type": "container",
      "confidence": 0.8,
      "requires_ops_agent": true
    },
    "overall_confidence": "HIGH",
    "cached": false,
    "analysis_duration_ms": 450
  }
}
```

---

#### Endpoint 10: `POST /api/config/auto-configure/preview`

Get recommendations without applying them. Returns what would change if auto-configure were applied.

**Service**: `AutoConfigManagerService.preview_configuration()`

> **Warning**: `preview_configuration()` uses `asyncio.get_event_loop().run_until_complete()` internally. This conflicts with the running event loop in the aiohttp server. MUST wrap in `asyncio.to_thread()` to run in a separate thread with its own event loop.

**Request**:
```json
{
  "project_path": "/path/to/project",
  "min_confidence": 0.8
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `project_path` | string | No | Project root (default: cwd) |
| `min_confidence` | float | No | Minimum confidence threshold, 0.0-1.0 (default: 0.8) |

**Success response (200)**:
```json
{
  "success": true,
  "preview": {
    "recommended_agents": [
      {
        "agent_id": "python-engineer",
        "agent_name": "Python Engineer",
        "confidence_score": 0.95,
        "reason": "Python project with FastAPI framework detected",
        "currently_deployed": false
      },
      {
        "agent_id": "engineer",
        "agent_name": "Engineer Agent",
        "confidence_score": 0.90,
        "reason": "Core engineering agent for any software project",
        "currently_deployed": true
      }
    ],
    "recommended_skills": [
      {
        "skill_id": "fastapi-local-dev",
        "reason": "FastAPI framework detected",
        "confidence": 0.9
      }
    ],
    "changes": {
      "agents_to_add": ["python-engineer", "api-qa"],
      "agents_to_remove": [],
      "agents_unchanged": ["engineer", "research", "qa", "documentation", "ops", "ticketing"],
      "skills_to_add": ["fastapi-local-dev", "python-core"],
      "skills_to_remove": [],
      "skills_unchanged": ["systematic-debugging", "test-driven-development"]
    },
    "rationale": {
      "python-engineer": "Python 3.12+ detected via pyproject.toml; FastAPI as primary framework",
      "api-qa": "REST API project detected; API-specific QA agent recommended"
    },
    "validation": {
      "is_valid": true,
      "warnings": [],
      "errors": []
    },
    "estimated_deployment_time_seconds": 25.0,
    "toolchain_summary": {
      "primary_language": "python",
      "frameworks": ["fastapi", "svelte"],
      "deployment_target": "docker"
    }
  }
}
```

> **Warning (Risk O-3)**: Preview may recommend removing manually customized agents. The response must clearly distinguish between auto-recommended and manually-deployed agents so the frontend can highlight potential conflicts. The `currently_deployed` field serves this purpose.

---

#### Endpoint 11: `POST /api/config/auto-configure/apply`

Apply auto-configuration. This is a long-running operation.

**Service**: `AutoConfigManagerService.auto_configure()` -- the ONLY natively async method in the service layer.

**Request**:
```json
{
  "project_path": "/path/to/project",
  "min_confidence": 0.8,
  "dry_run": false,
  "agent_overrides": {
    "exclude": ["security"],
    "include": ["custom-agent"]
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `project_path` | string | No | Project root (default: cwd) |
| `min_confidence` | float | No | Minimum confidence (default: 0.8) |
| `dry_run` | boolean | No | Preview only, no deployment (default: false) |
| `agent_overrides` | object | No | Manual include/exclude overrides |

**Immediate response (202 Accepted)**:
```json
{
  "success": true,
  "message": "Auto-configuration started",
  "job_id": "autoconfig-1708000000",
  "status": "in_progress"
}
```

**Socket.IO progress events** (emitted during execution):

Phase progression: `detecting` -> `recommending` -> `validating` -> `deploying` -> `verifying`

```json
{
  "type": "config_event",
  "subtype": "autoconfig_progress",
  "data": {
    "job_id": "autoconfig-1708000000",
    "phase": "deploying",
    "phase_number": 4,
    "total_phases": 5,
    "current_item": "python-engineer",
    "items_completed": 2,
    "items_total": 5,
    "status": "in_progress"
  },
  "timestamp": "2026-02-15T10:45:03Z"
}
```

**Socket.IO completion event**:
```json
{
  "type": "config_event",
  "subtype": "autoconfig_completed",
  "data": {
    "job_id": "autoconfig-1708000000",
    "status": "success",
    "deployed_agents": ["python-engineer", "api-qa"],
    "failed_agents": [],
    "deployed_skills": ["fastapi-local-dev"],
    "backup_id": "2026-02-15T10-45-00",
    "duration_ms": 12500,
    "verification": {
      "passed": true,
      "agents_verified": 2,
      "skills_verified": 1
    }
  },
  "timestamp": "2026-02-15T10:45:12Z"
}
```

**Socket.IO failure event**:
```json
{
  "type": "config_event",
  "subtype": "autoconfig_failed",
  "data": {
    "job_id": "autoconfig-1708000000",
    "status": "failed",
    "error": "Deployment verification failed for agent 'python-engineer'",
    "deployed_before_failure": ["api-qa"],
    "rollback_available": true,
    "backup_id": "2026-02-15T10-45-00"
  },
  "timestamp": "2026-02-15T10:45:08Z"
}
```

**Full backup** is created before applying. If verification fails after deployment, the backup is available for rollback via `POST /api/config/auto-configure/rollback` (or use the backup manager directly).

> **Devil's advocate note**: Auto-configure apply in the UI is the highest-risk operation in Phase 3. Consider keeping it CLI-only and only exposing the detect + preview endpoints in the UI. Users would see the recommendations and then run `claude-mpm config auto` in terminal. See [Section 9, Note 1](#9-devils-advocate-notes).

---

### 3.4 Business Rule Enforcement Summary

| Rule | Endpoint | Enforcement | HTTP Status |
|------|----------|-------------|-------------|
| BR-01: Core agents immutable | `DELETE /api/config/agents/{name}` | Check against 7-agent list before any operation | 403 |
| BR-03: user_defined overrides agent_referenced | `PUT /api/config/skills/deployment-mode` | Preview shows impact; empty list blocked | 400 |
| BR-04: Priority-based resolution | `POST /api/config/agents/deploy` | Uses `source_id` or highest-priority source | N/A |
| BR-10: No file locking | All write endpoints | `ConfigFileLock` from Phase 2 wraps all config writes | 409 on lock contention |
| BR-11: Default collection protection | Implicit in deploy flows | Default collection cannot be removed | 403 |
| PM_CORE_SKILLS immutable | `DELETE /api/config/skills/{name}` | Check against PM_CORE_SKILLS + CORE_SKILLS sets | 403 |
| Concurrent operation safety | All write endpoints | Operation journal + backup before each write | 500 on conflict |

### 3.5 Error Codes Reference

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Invalid request body or parameters |
| `EMPTY_SKILL_LIST` | 400 | Mode switch to user_defined with empty skills |
| `CONFIRMATION_REQUIRED` | 400 | Dangerous operation requires explicit confirm flag |
| `CORE_AGENT_PROTECTED` | 403 | Attempt to undeploy a core agent |
| `IMMUTABLE_SKILL` | 403 | Attempt to undeploy a core/PM skill |
| `NOT_FOUND` | 404 | Agent or skill not found in cache or deployment |
| `CONFLICT` | 409 | Agent already deployed (without force flag) |
| `ALREADY_IN_MODE` | 409 | Already in the requested deployment mode |
| `STALE_CONFIG` | 412 | Config modified externally (ETag mismatch) |
| `DEPLOY_FAILED` | 500 | Deployment operation failed |
| `VERIFICATION_FAILED` | 500 | Post-deployment verification failed |
| `SERVICE_ERROR` | 500 | Internal service error |

---

## 4. Frontend Implementation

### 4.1 Updated AgentsList.svelte -- Deploy/Undeploy Actions

**Current state** (from Phase 1): Read-only list of deployed and available agents.

**Phase 3 additions**:
- "Deploy" button on available (not yet deployed) agents
- "Undeploy" button on deployed agents, except core agents
- Core agents (BR-01) marked with a lock icon and disabled undeploy button
- Confirmation modal before undeploy
- Loading state during deploy/undeploy operations
- "Deploy Collection" button that opens collection selector

**Agent row layout** (deployed agent):
```
[ lock icon ] engineer      v3.9.1   core    [  Undeploy  ] (disabled, grayed out)
              python-eng    v2.5.0   custom  [  Undeploy  ] (enabled, red on hover)
```

**Agent row layout** (available, not deployed):
```
              react-eng     v1.2.0   available  [  Deploy  ] (enabled, cyan)
```

**Core agent tooltip**: "This is a core agent required by the system. It cannot be undeployed."

**Deploy button behavior**:
1. Click "Deploy" -> Button shows spinner + "Deploying..."
2. Call `POST /api/config/agents/deploy` with `{ agent_name, force: false }`
3. On success: Move agent from "Available" to "Deployed" section, show success toast
4. On 409 (already deployed): Show "Already deployed. Force redeploy?" dialog
5. On error: Show error toast, restore button state

**Undeploy button behavior**:
1. Click "Undeploy" -> Open `ConfirmDialog` with agent name
2. User types agent name to confirm (destructive operation pattern)
3. Call `DELETE /api/config/agents/{agent_name}`
4. On success: Move agent from "Deployed" to "Available" section, show success toast
5. On 403 (core agent): Show error explaining core protection (should not happen if UI disables correctly)

### 4.2 Updated SkillsList.svelte -- Deploy/Undeploy + Mode Indicator

**Phase 3 additions**:
- Deploy/undeploy actions (similar to agents)
- Prominent mode badge showing current deployment mode (`agent_referenced` or `user_defined`)
- "Switch Mode" button that opens ModeSwitch component
- `user_requested` flag shown as a badge on individually requested skills
- Immutable skills (PM_CORE_SKILLS, CORE_SKILLS) shown with lock icon, undeploy disabled

**Mode badge layout** (top of skills list):
```
Deployment Mode: [ agent_referenced ]  [ Switch Mode ]

  or

Deployment Mode: [ user_defined ]  [ Switch Mode ]
```

Badge color: `agent_referenced` = blue, `user_defined` = purple.

**Skill row with user_requested flag**:
```
systematic-debugging   v1.0   deployed   [ user requested ]  [  Undeploy  ]
mpm-delegation-patterns v1.0  deployed   [ system ]           [ locked ]
```

### 4.3 config/ModeSwitch.svelte -- Deployment Mode Switching

A dedicated component for the two-step mode switching flow.

**Two-step flow**:

**Step 1 -- Preview**:
- User clicks "Switch Mode" from SkillsList
- ModeSwitch component opens (modal or inline expandable)
- Shows current mode and proposed mode
- Calls `PUT /api/config/skills/deployment-mode` with `{ mode: "user_defined", preview: true }`
- Displays impact preview:
  - Skills that will be ADDED (green)
  - Skills that will be REMOVED (red)
  - Skills that remain UNCHANGED (gray)
- If switching to `user_defined` with empty list, shows prominent red warning callout:
  "Switching to user_defined mode with no skills specified will remove all auto-deployed skills. Pre-populate from current list?"
  - Offers a "Copy current skills to user_defined" helper button

**Step 2 -- Confirm**:
- User reviews impact and clicks "Confirm Switch"
- A confirmation checkbox: "I understand this will change X skills"
- Checkbox must be checked before "Confirm Switch" becomes enabled
- On confirm: Calls `PUT /api/config/skills/deployment-mode` with `{ mode: "user_defined", confirm: true, skills: [...] }`
- Shows spinner during operation
- On success: Updates mode badge, refreshes skill list, shows toast
- Cancel is always available and returns to Step 1

**Component structure**:
```svelte
<script lang="ts">
  let step = $state<'preview' | 'confirm'>('preview');
  let impact = $state<ModeImpactPreview | null>(null);
  let confirmed = $state(false);
  let loading = $state(false);
  // ...
</script>

{#if step === 'preview'}
  <!-- Impact preview display -->
  <!-- "Next" button to move to confirm -->
{:else if step === 'confirm'}
  <!-- Confirmation checkbox -->
  <!-- "Confirm Switch" button (disabled until checkbox checked) -->
{/if}
```

### 4.4 config/DeploymentPipeline.svelte -- Visual Deployment Status

A reusable component that visualizes the deployment pipeline stages.

**Pipeline stages**: `Source` -> `Cache` -> `Deploy` -> `Verify`

Each stage shows status: `pending` | `active` | `success` | `failed`

**Visual representation**:
```
 [ Source ]  ----->  [ Cache ]  ----->  [ Deploy ]  ----->  [ Verify ]
    done               done              active              pending
```

**Stage icons/colors**:
- `pending`: gray circle, gray connector
- `active`: blue/cyan pulsing circle, animated connector
- `success`: green checkmark circle, green connector
- `failed`: red X circle, red connector

**Props**:
```typescript
interface PipelineStage {
  name: string;
  status: 'pending' | 'active' | 'success' | 'failed';
  detail?: string;  // e.g., "python-engineer.md" or "2 of 5 agents"
}

let { stages, compact = false }: {
  stages: PipelineStage[];
  compact?: boolean;
} = $props();
```

**Usage contexts**:
- **Inline mode** (`compact=true`): Used within agent/skill list rows to show deployment status of individual items
- **Full mode** (`compact=false`): Used in batch deployment and auto-configure flows to show overall pipeline progress

### 4.5 config/AutoConfigPreview.svelte -- Auto-Configure Wizard

The most complex UI component in Phase 3. A 4-step wizard for auto-configuration.

**Step 1 -- Detect toolchain**:
- "Analyze Project" button
- Calls `POST /api/config/auto-configure/detect`
- Shows detected toolchain with confidence levels:
  - Primary language (with confidence badge)
  - Frameworks detected (with versions)
  - Build tools
  - Deployment target
- Confidence color coding: HIGH = green, MEDIUM = yellow, LOW = red
- "Next: View Recommendations" button

**Step 2 -- View recommendations**:
- Calls `POST /api/config/auto-configure/preview`
- Lists recommended agents with:
  - Agent name and description
  - Confidence score
  - Rationale (why this agent is recommended)
  - Checkbox to include/exclude from deployment
  - "Currently deployed" indicator
- Lists recommended skills similarly
- "Next: Review Changes" button

**Step 3 -- Preview changes (diff view)**:
- Shows diff-like view of what will change:
  - Agents to add (green `+` prefix)
  - Agents to remove (red `-` prefix)
  - Agents unchanged (gray, collapsed by default)
  - Skills to add/remove/unchanged
- Shows total counts and estimated deployment time
- "Apply Auto-Configuration" button (prominent, requires scrolling past all changes)

**Step 4 -- Apply (progress display)**:
- Calls `POST /api/config/auto-configure/apply`
- Shows `DeploymentPipeline` with progress from Socket.IO events
- Phase indicator: Detecting -> Recommending -> Validating -> Deploying -> Verifying
- Per-agent/skill progress within the deploying phase
- On success: Shows summary with backup location
- On failure: Shows error with "Rollback" button
- Rollback button restores from the backup created at the start

**Wizard navigation**:
- "Back" button on every step (except during active operations in Step 4)
- "Cancel" always available (with confirmation if in Step 4)
- Step indicator at top (1 of 4, 2 of 4, etc.)
- User controls the pace -- no auto-advancement

> **Devil's advocate note**: The 4-step wizard is the most complex frontend component. Consider simplifying to 2 steps for Phase 3: (1) Detect + Preview combined, (2) Apply. The full 4-step can be deferred to Phase 4 when the UX is validated. See [Section 9, Note 6](#9-devils-advocate-notes).

### 4.6 shared/ConfirmDialog.svelte -- Destructive Operation Confirmation

Extends the `Modal.svelte` component from Phase 2 for destructive operations.

**Design**:
- Red-tinted header with warning icon
- Operation description in plain language
- "Type X to confirm" pattern for the most dangerous operations:
  - Undeploy agent: type agent name
  - Mode switch: type "switch"
  - Auto-configure apply: type "apply"
- Confirm button is disabled until the confirmation text matches
- Confirm button is styled as destructive (red background)
- Cancel button is always prominent and easily accessible

**Props**:
```typescript
let {
  open = false,
  title = 'Confirm Action',
  description = '',
  confirmText = '',         // Text user must type to confirm (empty = no typing required)
  confirmLabel = 'Confirm', // Button label
  onConfirm,
  onCancel,
  destructive = true,       // Red styling
}: { ... } = $props();
```

**Usage example** (undeploy agent):
```svelte
<ConfirmDialog
  open={showUndeploy}
  title="Undeploy Agent"
  description="Remove '{agentName}' from the project? This agent will no longer be available in Claude Code sessions."
  confirmText={agentName}
  confirmLabel="Undeploy"
  onConfirm={handleUndeploy}
  onCancel={() => showUndeploy = false}
/>
```

### 4.7 Active Session Warning Banner

Rendered at the top of ConfigView when Claude Code processes are detected.

**Visual design**:
- Amber/yellow background
- Warning triangle icon
- Message: "Active Claude Code sessions detected. Configuration changes will take effect on next session start."
- Dismiss button (X icon) -- dismisses for current session, reappears on next config operation
- Non-blocking -- does not prevent operations

**Implementation**:
```svelte
{#if hasActiveSessions}
  <div class="px-4 py-3 bg-yellow-50 dark:bg-yellow-900/20 border-b border-yellow-200 dark:border-yellow-800
    flex items-center gap-3">
    <svg class="w-5 h-5 text-yellow-600 dark:text-yellow-400 shrink-0" ...>
      <!-- warning triangle icon -->
    </svg>
    <p class="text-sm text-yellow-700 dark:text-yellow-300 flex-1">
      Active Claude Code sessions detected. Configuration changes will take effect on next session start.
    </p>
    <button
      onclick={() => hasActiveSessions = false}
      class="text-yellow-600 dark:text-yellow-400 hover:text-yellow-800 dark:hover:text-yellow-200"
    >
      <svg class="w-4 h-4" ...><!-- X icon --></svg>
    </button>
  </div>
{/if}
```

**Refresh behavior**: Call `GET /api/config/active-sessions` after every deploy/undeploy/mode-switch operation to update the banner state.

---

## 5. Safety Mechanisms

### 5.1 Backup Before Every Destructive Operation

Every endpoint that modifies files creates a backup before making changes:

| Operation | What Gets Backed Up |
|-----------|-------------------|
| Deploy agent | Current `.claude/agents/` directory |
| Undeploy agent | Current `.claude/agents/` directory |
| Batch deploy | Current `.claude/agents/` directory |
| Deploy skill | Current `~/.claude/skills/` directory |
| Undeploy skill | Current `~/.claude/skills/` directory |
| Mode switch | Current `configuration.yaml` |
| Auto-configure apply | `.claude/agents/` + `~/.claude/skills/` + `configuration.yaml` |

Backup is created by `BackupManager.create_backup()` before any file modification. If the operation fails, the backup is available for rollback.

### 5.2 Operation Journal for Crash Recovery

Every destructive operation writes intent to the journal before execution:

```
1. Journal: write entry (status: in_progress)
2. Backup: create backup
3. Execute: perform the operation
4. Verify: post-deployment verification
5. Journal: update entry (status: completed | failed)
```

If the server crashes between steps 1 and 5, the journal entry remains `in_progress`. On next server startup, the dashboard shows a warning: "Incomplete operation detected: deploying python-engineer. [Rollback] [Mark as Resolved]"

### 5.3 Two-Step Confirmation for Dangerous Operations

Operations classified as "dangerous" require explicit two-step confirmation:

| Operation | Danger Level | Confirmation Pattern |
|-----------|-------------|---------------------|
| Undeploy agent | Medium | Type agent name to confirm |
| Undeploy skill | Medium | Single confirm click |
| Mode switch | High | Preview impact + "I understand" checkbox + type "switch" |
| Auto-configure apply | Very High | Preview all changes + "I understand" checkbox + type "apply" |
| Batch deploy (10+) | Medium | Preview count + single confirm click |

### 5.4 Core Agent Protection (BR-01)

The 7 core agents cannot be undeployed via the UI:

```
engineer, research, qa, web-qa, documentation, ops, ticketing
```

**Enforcement layers**:
1. **Frontend**: Undeploy button disabled with lock icon and tooltip
2. **Backend**: `DELETE` endpoint returns 403 with `CORE_AGENT_PROTECTED` code
3. **Double-check**: Even with `force=true`, core agents cannot be removed

### 5.5 Immutable Skill Protection

`PM_CORE_SKILLS` (10 skills) and `CORE_SKILLS` (27 skills) cannot be undeployed:

**Enforcement layers**:
1. **Frontend**: Undeploy button disabled with "System" badge and lock icon
2. **Backend**: `DELETE` endpoint returns 403 with `IMMUTABLE_SKILL` code

### 5.6 Active Session Warning

Non-blocking informational warning that does not prevent operations but ensures users are aware that changes require a session restart.

**Detection**: `ps aux | grep claude` on each config operation
**Display**: Amber banner at top of ConfigView
**Behavior**: Informational only; does not block operations

---

## 6. Rollback Strategy

### 6.1 Agent Deploy Rollback

**Trigger**: Verification fails after deploying an agent file.

**Steps**:
1. Read backup metadata to find backed-up agent files
2. Remove the newly deployed agent file from `.claude/agents/`
3. Restore the previous version (if it existed before) from backup
4. Update journal entry to `rolled_back`
5. Return error response with `rollback_performed: true`

**Manual rollback** (if automatic fails):
```bash
# Backup location is returned in the API response
cp ~/.claude-mpm/backups/{backup_id}/agents/{agent}.md .claude/agents/
```

### 6.2 Agent Undeploy Rollback

**Trigger**: Post-undeploy verification shows file still exists (deletion failed).

**Steps**:
1. No rollback needed -- the file was not removed
2. Return error response indicating the undeploy failed
3. Journal entry updated to `failed`

**If file was removed but verification of broader state fails**:
1. Restore the agent file from backup
2. Return error response with `rollback_performed: true`

### 6.3 Skill Deploy Rollback

Similar to agent deploy. If verification fails:
1. Remove the deployed skill directory from `~/.claude/skills/`
2. Restore previous version from backup (if any)
3. Update deployment tracking index

### 6.4 Skill Undeploy Rollback

Similar to agent undeploy. If removal fails, report error without rollback.

### 6.5 Mode Switch Rollback

**Trigger**: Config file verification fails after writing new mode.

**Steps**:
1. Restore `configuration.yaml` from backup
2. Verify restored config is parseable
3. Return error response with `rollback_performed: true`

**If restore also fails**: Return critical error with backup file location for manual recovery.

### 6.6 Auto-Configure Rollback

**Trigger**: Any verification failure during the multi-step apply process, or user clicks "Rollback" after apply.

**Steps**:
1. Remove all agents deployed during auto-configure from `.claude/agents/`
2. Remove all skills deployed during auto-configure from `~/.claude/skills/`
3. Restore previous agent/skill/config files from backup
4. Verify restored state
5. Emit Socket.IO event: `autoconfig_rolled_back`

**Rollback endpoint** (optional, may be combined with backup manager):
```
POST /api/config/auto-configure/rollback
{ "job_id": "autoconfig-1708000000" }
```

**Response**:
```json
{
  "success": true,
  "message": "Auto-configuration rolled back successfully",
  "restored_agents": ["python-engineer", "api-qa"],
  "restored_skills": ["fastapi-local-dev"],
  "backup_id": "2026-02-15T10-45-00"
}
```

---

## 7. Testing Plan

### 7.1 Backend: Deployment Operation Tests

**Test file**: `tests/test_config_api_deployment.py`

| Test | Description | Expected |
|------|-------------|----------|
| `test_deploy_agent_success` | Deploy available agent from cache | 200, file exists, verification passes |
| `test_deploy_agent_not_in_cache` | Deploy agent not in any source | 404 |
| `test_deploy_agent_already_deployed` | Deploy already-deployed agent without force | 409 |
| `test_deploy_agent_force_redeploy` | Deploy already-deployed agent with force=true | 200, file updated |
| `test_undeploy_agent_success` | Remove non-core deployed agent | 200, file removed |
| `test_undeploy_core_agent_blocked` | Attempt to undeploy "engineer" | 403, CORE_AGENT_PROTECTED |
| `test_undeploy_all_seven_core_agents` | Attempt each core agent individually | All return 403 |
| `test_undeploy_nonexistent_agent` | Undeploy agent that's not deployed | 404 |
| `test_batch_deploy_success` | Deploy 3 agents in sequence | 200, all three deployed |
| `test_batch_deploy_partial_failure` | Deploy 3 agents, one fails | 200, 2 deployed + 1 failed |
| `test_deploy_skill_success` | Deploy skill with mark_user_requested=true | 200, directory exists, config updated |
| `test_undeploy_core_skill_blocked` | Undeploy PM_CORE_SKILL | 403, IMMUTABLE_SKILL |
| `test_mode_switch_preview` | Preview mode switch impact | 200, impact data returned |
| `test_mode_switch_empty_list_blocked` | Switch to user_defined with empty skills | 400, EMPTY_SKILL_LIST |
| `test_mode_switch_confirm` | Full mode switch with confirm | 200, config updated |
| `test_autoconfig_detect` | Detect toolchain on project | 200, toolchain data returned |
| `test_autoconfig_preview` | Preview auto-configure recommendations | 200, preview data returned |

### 7.2 Backend: Business Rule Tests

| Test | Business Rule | Expected |
|------|--------------|----------|
| `test_br01_all_core_agents` | BR-01 | All 7 core agents return 403 on undeploy |
| `test_br03_user_defined_overrides` | BR-03 | Mode switch correctly applies precedence |
| `test_pm_core_skills_immutable` | PM_CORE_SKILLS | All 10 PM core skills return 403 on undeploy |
| `test_core_skills_immutable` | CORE_SKILLS | All 27 core skills return 403 on undeploy |
| `test_config_file_lock_used` | BR-10 | Config writes acquire ConfigFileLock |
| `test_concurrent_deploy_serialized` | C-1 | Two concurrent deploys don't corrupt state |

### 7.3 Backend: Rollback Tests

| Test | Description | Expected |
|------|-------------|----------|
| `test_deploy_creates_backup` | Deploy creates backup before modifying files | Backup directory exists with correct files |
| `test_failed_deploy_triggers_rollback` | Simulate deploy failure after file write | Original state restored from backup |
| `test_journal_records_operations` | Every deploy writes to journal | Journal contains entry with correct metadata |
| `test_incomplete_journal_detected` | Simulate crash (leave journal in_progress) | `check_incomplete_operations()` returns the entry |
| `test_backup_pruning` | Create 7 backups | Only last 5 remain after pruning |
| `test_mode_switch_rollback` | Simulate config write failure during mode switch | Previous config restored |

### 7.4 Frontend: Manual Testing Checklist

**AgentsList with deploy/undeploy**:
- [ ] Core agents show lock icon, undeploy button disabled
- [ ] Available agents show "Deploy" button
- [ ] Click "Deploy" shows loading state, completes successfully
- [ ] Deploy error shows toast notification
- [ ] Click "Undeploy" opens confirmation dialog
- [ ] Type agent name to confirm undeploy
- [ ] Undeploy success removes agent from deployed list
- [ ] Cancel undeploy closes dialog without action
- [ ] Active session warning appears when sessions detected

**SkillsList with mode**:
- [ ] Mode badge shows correctly (agent_referenced or user_defined)
- [ ] Immutable skills show lock icon, undeploy disabled
- [ ] user_requested skills show badge
- [ ] Deploy/undeploy actions work correctly

**ModeSwitch**:
- [ ] Preview step shows impact correctly
- [ ] Switching to user_defined with empty list shows error
- [ ] "Copy current skills" helper populates list
- [ ] Confirm step requires checkbox + confirmation text
- [ ] Successful switch updates mode badge and skill list
- [ ] Cancel returns to preview step

**AutoConfigPreview**:
- [ ] Step 1: Detect shows toolchain with confidence colors
- [ ] Step 2: Recommendations have checkboxes for include/exclude
- [ ] Step 3: Diff view shows changes clearly (green/red)
- [ ] Step 4: Progress bar updates via Socket.IO
- [ ] Back button works on steps 1-3
- [ ] Cancel with confirmation on step 4
- [ ] Success shows backup location
- [ ] Failure shows rollback button

**ConfirmDialog**:
- [ ] Red header with warning icon for destructive ops
- [ ] Confirm button disabled until text typed
- [ ] Escape key closes dialog
- [ ] Backdrop click closes dialog

### 7.5 Integration Tests

| Test | Flow | Verification |
|------|------|-------------|
| Deploy via UI, verify in filesystem | Deploy agent from UI -> check `.claude/agents/` | File exists with correct content |
| Deploy via UI, use in Claude Code | Deploy agent -> start new Claude session -> verify agent available | Agent responds to delegation |
| Undeploy via UI, verify removed | Undeploy agent -> check filesystem | File removed |
| Mode switch via UI, verify config | Switch mode -> check `configuration.yaml` | Config reflects new mode |
| Auto-configure preview accuracy | Preview -> verify recommendations match toolchain | Recommendations are relevant |

### 7.6 Safety Tests

| Test | Scenario | Expected |
|------|----------|----------|
| Concurrent CLI + UI deploy | Run `claude-mpm agents deploy` while clicking Deploy in UI | Both succeed or one gets lock contention (409), no corruption |
| Deploy during source sync | Start source sync, then deploy agent | Deploy uses current cache, sync doesn't interfere |
| Undeploy while Claude session active | Undeploy agent during active session | Undeploy succeeds, warning shown, session unaffected until restart |
| Mode switch with empty user_defined | Switch to user_defined with empty list | Blocked by UI and backend |
| Batch deploy interruption | Start batch of 10, close browser mid-deploy | Completed agents remain, incomplete ones rolled back |
| Auto-configure with custom agents | Auto-configure project that has manually deployed agents | Preview shows manual agents, doesn't remove them without explicit confirmation |

### 7.7 Edge Cases

| Edge Case | Expected Behavior |
|-----------|-------------------|
| Deploy agent that was just undeployed | Should succeed (not in conflict state) |
| Undeploy agent then immediately re-deploy | Should succeed |
| Mode switch twice rapidly | Second request should see first is complete, proceed normally |
| Auto-configure on project with no detectable toolchain | Detect returns low confidence, recommendations are minimal |
| Deploy with invalid source_id | 404 with helpful error message |
| Batch deploy with all agents already deployed (no force) | All skipped, summary shows 0 deployed |
| Mode switch from user_defined back to agent_referenced | Skills list is re-populated from agent frontmatter |
| Network failure during auto-configure apply | Operation fails, backup available for rollback |

---

## 8. Definition of Done

### Acceptance Criteria

**Agent Operations**:
- [ ] Users can deploy available agents from the dashboard
- [ ] Users can undeploy non-core agents with confirmation
- [ ] Core agents (7) are visually protected and cannot be undeployed
- [ ] Batch deploy works for agent collections
- [ ] Every deploy/undeploy creates a backup
- [ ] Post-deployment verification runs automatically
- [ ] Active session warning displayed when applicable

**Skill Operations**:
- [ ] Users can deploy available skills with optional user_requested flag
- [ ] Users can undeploy non-core skills with confirmation
- [ ] PM_CORE_SKILLS and CORE_SKILLS are visually protected and cannot be undeployed
- [ ] Current deployment mode is clearly displayed
- [ ] Mode switch flow (preview -> confirm) works end-to-end

**Auto-Configure**:
- [ ] Toolchain detection returns accurate results with confidence levels
- [ ] Preview shows recommended agents/skills with rationale
- [ ] Diff view clearly shows what will change
- [ ] Apply executes with Socket.IO progress updates
- [ ] Rollback is available if apply fails or user requests it

**Safety**:
- [ ] Backup created before every destructive operation
- [ ] Operation journal tracks all operations
- [ ] Rollback successfully restores previous state
- [ ] Two-step confirmation for all dangerous operations
- [ ] ConfigFileLock used for all config file writes
- [ ] No data loss from concurrent CLI + UI operations (tested)

**Quality**:
- [ ] All backend endpoint tests pass
- [ ] All business rule tests pass
- [ ] All rollback tests pass
- [ ] Manual frontend testing checklist complete
- [ ] At least one end-to-end integration test passes (deploy via UI, verify in Claude Code)
- [ ] No regressions in Phase 1 or Phase 2 functionality

---

## 9. Devil's Advocate Notes

These are intentional challenges to the plan. Each should be discussed before implementation begins.

### Note 1: Auto-configure apply is the highest-risk operation

Auto-configure apply in the UI is the riskiest operation in Phase 3. It combines toolchain detection, agent recommendation, skill recommendation, multi-file deployment, and config modification into one long-running flow. A bug at any stage could leave the system in an inconsistent state.

**Consideration**: Keep auto-configure apply as CLI-only for Phase 3 and only expose detect + preview in the dashboard. Users see recommendations in the UI and run `claude-mpm config auto` in terminal. The UI becomes a "recommendation engine" rather than a "deployment engine."

**Counter-argument**: The 4-step wizard with explicit confirmation at each step provides enough guardrails. The backup + rollback infrastructure makes recovery possible. And CLI-only defeats the purpose of having a dashboard.

**Recommendation**: Implement the full wizard but add a prominent "Advanced Operation" label and make the Apply step opt-in via a settings toggle (default: off for first release).

### Note 2: Mode switching to user_defined with empty list

Switching to `user_defined` mode with an empty skill list is functionally equivalent to "remove all skills." This is almost certainly never the user's intent.

**Consideration**: The backend MUST reject empty lists. The frontend MUST pre-populate the user_defined list from the current agent_referenced list when the user initiates a switch. The "I understand" checkbox must include the specific count of skills that will be affected.

**Recommendation**: Implemented as described. The `EMPTY_SKILL_LIST` error code blocks the operation at the API level.

### Note 3: Batch deploy of 20+ agents takes 30+ seconds

Large batch deploys (deploying an entire collection of agents) involve sequential filesystem operations that can take considerable time.

**Consideration**: Need Socket.IO progress events per-agent during batch deployment. The UI should show a progress bar with "Deploying agent 3 of 20: python-engineer..." and allow cancellation.

**Recommendation**: Implemented via Socket.IO `agent_deploy_progress` events emitted during the batch loop. Frontend DeploymentPipeline component handles display.

### Note 4: Active session detection via `ps` is brittle

Process names vary. On macOS, Claude Code might appear as `Electron`, `Claude`, or under a different process tree. On Linux, it might be different again. The `ps aux | grep claude` approach will produce false positives (matching the grep itself, matching "claude" in file paths) and false negatives (Claude running under a different process name).

**Consideration**: This is best-effort detection. False positives (showing the warning when no session is active) are harmless -- they just add noise. False negatives (not showing the warning when a session IS active) are more concerning but also not dangerous since the warning is informational.

**Recommendation**: Implement with current approach but document that it's imprecise. Consider integrating with the Socket.IO event stream to detect active sessions more reliably (check for recent `session_event` emissions).

### Note 5: Operation journal adds complexity -- is it worth it?

The operation journal is designed for crash recovery. But server crashes during a deploy operation are rare (low probability). The journal adds filesystem I/O on every operation and recovery logic that must be tested and maintained.

**Consideration**: For Phase 3, a simpler approach may suffice: just create backups without journal tracking. If the server crashes, the user can manually restore from the latest backup. The journal is more valuable in Phase 4 when the system handles more complex multi-step operations.

**Counter-argument**: Without the journal, there's no way to detect that an operation was interrupted. The user may not even know a backup was created. The journal provides the "something went wrong" detection that triggers the recovery flow.

**Recommendation**: Implement a minimal journal (just intent + status, skip rollback_info for Phase 3). Full journal with rollback metadata in Phase 4.

### Note 6: The 4-step auto-configure wizard is complex

The AutoConfigPreview component has 4 steps, each with different data requirements, loading states, and error handling. This is the most complex UI component in the entire dashboard.

**Consideration**: Simplify to 2 steps for Phase 3: (1) Detect + Recommend combined (one API call), (2) Review + Apply (diff view + confirmation). The 4-step version adds granularity but also adds navigation complexity and more potential failure points.

**Counter-argument**: The 4-step version gives users more control and understanding of what's happening. Combining steps may make the UI feel overwhelming rather than progressive.

**Recommendation**: Start with 2 steps for the initial implementation. Expand to 4 steps if user feedback indicates the combined view is too dense.

### Note 7: What happens if user deploys agent, starts Claude session, then undeploys?

The Claude Code session has a stale reference to the agent. Delegation to that agent will fail silently or produce confusing errors.

**Consideration**: This is inherent to the "no hot-reload" architecture. The active session warning mitigates this but doesn't prevent it. There is no technical solution short of implementing hot-reload in Claude Code itself.

**Recommendation**: Accept this limitation. Ensure the active session warning is clear: "Changes take effect on next session start. Running sessions use cached configuration." Consider adding a "Session Restart Guide" help link.

---

## 10. Files Created/Modified

### New Backend Files

| File | Purpose |
|------|---------|
| `src/claude_mpm/services/config_api/backup_manager.py` | Backup/restore pipeline for deployment operations |
| `src/claude_mpm/services/config_api/operation_journal.py` | Operation journal for crash recovery |
| `src/claude_mpm/services/config_api/deployment_verifier.py` | Post-deployment verification checks |
| `src/claude_mpm/services/config_api/session_detector.py` | Active Claude Code session detection |
| `src/claude_mpm/services/config_api/agent_deployment_handler.py` | HTTP handler logic for agent deploy/undeploy endpoints |
| `src/claude_mpm/services/config_api/skill_deployment_handler.py` | HTTP handler logic for skill deploy/undeploy + mode switch endpoints |
| `src/claude_mpm/services/config_api/autoconfig_handler.py` | HTTP handler logic for auto-configure endpoints |

### Modified Backend Files

| File | Changes |
|------|---------|
| `src/claude_mpm/services/monitor/server.py` | Register 11 new routes in `_setup_config_routes()` |
| `src/claude_mpm/services/config_api/__init__.py` | Export new handler modules |

### New Frontend Files

| File | Purpose |
|------|---------|
| `src/claude_mpm/dashboard-svelte/src/lib/components/config/ModeSwitch.svelte` | Two-step deployment mode switching |
| `src/claude_mpm/dashboard-svelte/src/lib/components/config/DeploymentPipeline.svelte` | Visual pipeline status indicator |
| `src/claude_mpm/dashboard-svelte/src/lib/components/config/AutoConfigPreview.svelte` | Auto-configure wizard (2-4 steps) |
| `src/claude_mpm/dashboard-svelte/src/lib/components/shared/ConfirmDialog.svelte` | Destructive operation confirmation modal |

### Modified Frontend Files

| File | Changes |
|------|---------|
| `src/claude_mpm/dashboard-svelte/src/lib/components/config/AgentsList.svelte` | Add deploy/undeploy buttons, core agent protection, loading states |
| `src/claude_mpm/dashboard-svelte/src/lib/components/config/SkillsList.svelte` | Add deploy/undeploy buttons, mode badge, immutable skill protection |
| `src/claude_mpm/dashboard-svelte/src/lib/components/config/ConfigView.svelte` | Add active session warning banner, integrate new sub-components |
| `src/claude_mpm/dashboard-svelte/src/lib/stores/config.svelte.ts` | Add deploy/undeploy actions, mode switch actions, autoconfig actions |

### New Test Files

| File | Purpose |
|------|---------|
| `tests/test_config_api_deployment.py` | Backend deployment operation tests |
| `tests/test_config_api_business_rules.py` | Business rule enforcement tests |
| `tests/test_config_api_rollback.py` | Backup and rollback tests |
| `tests/test_backup_manager.py` | BackupManager unit tests |
| `tests/test_operation_journal.py` | OperationJournal unit tests |
| `tests/test_deployment_verifier.py` | Verification check tests |

---

## 11. Estimated Effort Breakdown

### Week 1: Prerequisites + Agent Endpoints

| Task | Estimate | Risk |
|------|----------|------|
| BackupManager implementation + tests | 1 day | Low |
| OperationJournal (minimal version) + tests | 0.5 day | Low |
| DeploymentVerifier + tests | 0.5 day | Low |
| Active session detection + endpoint | 0.5 day | Low |
| Agent deploy endpoint (POST) | 1 day | Medium |
| Agent undeploy endpoint (DELETE) with BR-01 | 0.5 day | Low |
| Agent batch deploy endpoint (POST) | 0.5 day | Medium |
| Agent collections endpoint (GET) | 0.5 day | Low |
| **Week 1 subtotal** | **5 days** | |

### Week 2: Skill Endpoints + Frontend Updates

| Task | Estimate | Risk |
|------|----------|------|
| Skill deploy endpoint (POST) | 0.5 day | Medium |
| Skill undeploy endpoint (DELETE) with immutable check | 0.5 day | Low |
| Deployment mode GET endpoint | 0.5 day | Low |
| Deployment mode PUT endpoint (two-step) | 1 day | High |
| AgentsList.svelte updates (deploy/undeploy) | 1 day | Medium |
| SkillsList.svelte updates (deploy/undeploy/mode) | 1 day | Medium |
| ConfirmDialog.svelte | 0.5 day | Low |
| ModeSwitch.svelte (preview + confirm) | 1 day | High |
| **Week 2 subtotal** | **6 days** | |

### Week 3: Auto-Configure + Integration + Testing

| Task | Estimate | Risk |
|------|----------|------|
| Auto-configure detect endpoint | 0.5 day | Low |
| Auto-configure preview endpoint | 1 day | Medium |
| Auto-configure apply endpoint (long-running) | 1 day | High |
| DeploymentPipeline.svelte | 0.5 day | Low |
| AutoConfigPreview.svelte (2-step version) | 1.5 days | High |
| Active session warning banner | 0.5 day | Low |
| Integration testing (all flows) | 1 day | Medium |
| Safety testing (concurrent ops, rollback) | 0.5 day | Medium |
| Bug fixes and polish | 1 day | Medium |
| **Week 3 subtotal** | **7.5 days** | |

### Total: ~18.5 days (approximately 3 weeks)

**Buffer recommendation**: Add 20% buffer for unexpected issues. Target 3.5 weeks if possible.

**Critical path**: The mode switch endpoint (week 2) and auto-configure apply (week 3) are the highest-risk items. If either encounters significant issues, they should be descoped to Phase 4 rather than delaying the entire phase.

---

*End of Phase 3 Implementation Plan*

*Research documents referenced:*
- `/Users/mac/workspace/claude-mpm-fork/docs/research/ui-for-claude-mpm-configuration-management/01-service-layer-api-catalog.md`
- `/Users/mac/workspace/claude-mpm-fork/docs/research/ui-for-claude-mpm-configuration-management/02-data-models-business-rules.md`
- `/Users/mac/workspace/claude-mpm-fork/docs/research/ui-for-claude-mpm-configuration-management/03-frontend-architecture-ux-guide.md`
- `/Users/mac/workspace/claude-mpm-fork/docs/research/ui-for-claude-mpm-configuration-management/04-backend-api-specification.md`
- `/Users/mac/workspace/claude-mpm-fork/docs/research/ui-for-claude-mpm-configuration-management/05-risk-assessment-devils-advocate.md`
