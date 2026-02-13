# Backend API Specification: Claude MPM Configuration UI

## Part 1: Existing Server Architecture Analysis

### Server Foundation

The `UnifiedMonitorServer` (`src/claude_mpm/services/monitor/server.py`) is an **aiohttp + Socket.IO** server running on a single port (default 8765). It:

- Runs in a **separate daemon thread** with its own event loop
- Uses `socketio.AsyncServer(cors_allowed_origins="*")` for real-time events
- Serves the Svelte SPA from `dashboard/static/svelte-build/`
- Supports hot reload via file watching (optional dev mode)
- Sends heartbeats every 3 minutes to connected clients

### Route Registration Pattern

Routes are registered inside `_setup_http_routes()` (line 520) using `self.app.router.add_*()`:

```python
# All routes registered explicitly on the aiohttp app router
self.app.router.add_get("/", dashboard_index)
self.app.router.add_get("/health", health_check)
self.app.router.add_get("/api/config", config_handler)
self.app.router.add_post("/api/events", api_events_handler)
```

**Key observations:**
- All routes are **inline async functions** defined inside `_setup_http_routes()`
- No decorators, no router objects, no middleware chain
- Handlers are closures that capture `self`, `static_dir`, etc.
- There is **no sub-application or route prefix grouping** mechanism in use

### Existing Routes (Complete Inventory)

| Method | Path | Handler | Purpose |
|--------|------|---------|---------|
| GET | `/` | `dashboard_index` | Serve Svelte SPA index.html |
| GET | `/favicon.svg` | `favicon_handler` | Serve favicon |
| GET | `/health` | `health_check` | Service health + version + uptime |
| GET | `/version.json` | `version_handler` | Version/build info |
| GET | `/api/config` | `config_handler` | Dashboard init config (cwd, git branch, time) |
| GET | `/api/working-directory` | `working_directory_handler` | Current working directory |
| GET | `/api/files` | `api_files_handler` | List directory contents |
| GET | `/api/file/read` | `api_file_read_handler` | Read file content (text + images) |
| GET | `/api/file/diff` | `git_diff_handler` | Git diff for file |
| POST | `/api/events` | `api_events_handler` | Event ingestion from hooks |
| POST | `/api/file` | `api_file_handler` | Read file content (legacy POST) |
| POST | `/api/git-history` | `git_history_handler` | Git history for file |
| GET | `/monitor` | `monitor_page_handler` | Legacy monitor pages |
| GET | `/monitor/{page}` | `monitor_page_handler` | Legacy monitor sub-pages |
| GET | `/_app/{filepath:.*}` | `app_assets_handler` | Svelte compiled assets |
| GET | `/static/{filepath:.*}` | `static_handler` | Legacy static files |

### Request/Response Patterns

**Query parameters** (GET requests):
```python
path = request.query.get("path", str(Path.cwd()))
commit_hash = request.query.get("commit", "")
```

**JSON body** (POST requests):
```python
data = await request.json()
file_path = data.get("path", "")
```

**Success responses:**
```python
# JSON with success flag
return web.json_response({"success": True, "content": content, ...})

# Bare JSON (no success flag)
return web.json_response({"status": "running", "version": "1.0.0", ...})

# No content (for event ingestion)
return web.Response(status=204)
```

**Error responses:**
```python
return web.json_response({"success": False, "error": "message"}, status=400)
return web.json_response({"success": False, "error": "message"}, status=404)
return web.json_response({"success": False, "error": str(e)}, status=500)
```

### Socket.IO Event Patterns

**Event categories** (from `_categorize_event`, line 371):
- `hook_event`: subagent_start, subagent_stop, todo_updated
- `tool_event`: pre_tool, post_tool, tool.start, tool.end
- `session_event`: session.started, session.ended, token_usage_updated
- `response_event`: response.start, response.end
- `agent_event`: agent.delegated, agent.returned
- `file_event`: file.read, file.write, file.edit
- `claude_event`: user_prompt, assistant_message
- `system_event`: system_ready, system_shutdown

**Event emission from HTTP handlers:**
```python
if self.sio:
    await self.sio.emit(event_type, wrapped_event)
```

**Event payload structure:**
```json
{
    "type": "hook_event",
    "subtype": "subagent_start",
    "data": { ... },
    "timestamp": "2025-01-01T00:00:00Z",
    "session_id": "abc123",
    "source": "hook"
}
```

### CORS Configuration

CORS is handled at the Socket.IO level:
```python
self.sio = socketio.AsyncServer(cors_allowed_origins="*")
```

There is **no aiohttp-level CORS middleware**. The new config API routes will need CORS headers added (either via middleware or per-response).

### Authentication

**None.** The server runs locally and trusts all connections. No auth middleware, tokens, or session management.

### Logging Pattern

```python
self.logger = get_logger(__name__)
self.logger.info("Message")
self.logger.error(f"Error: {e}")
self.logger.debug(f"Debug: {detail}")
```

### Service Initialization

Services are **not** pre-initialized or injected into the server. They are either:
1. Created inline in handlers (e.g., `VersionService()`)
2. Imported at function call time (lazy import)

This is the pattern we should follow for config API services.

---

## Part 2: REST API Specification

### API Design Principles

1. **Consistency with existing patterns**: Use `web.json_response()`, follow `{success, data/error}` pattern
2. **Route prefix**: All new routes under `/api/config/` to namespace clearly
3. **Lazy service initialization**: Create services per-request or cache on first use
4. **Socket.IO events**: Emit `config_event` for all state-changing operations
5. **Long-running operations**: Use Socket.IO progress events for sync operations
6. **Error format**: `{"success": false, "error": "message", "code": "ERROR_CODE"}`

### Error Response Format (Consistent Across All Endpoints)

```json
{
    "success": false,
    "error": "Human-readable error message",
    "code": "AGENT_NOT_FOUND",
    "details": {}
}
```

Error codes:
- `NOT_FOUND` - Resource not found
- `VALIDATION_ERROR` - Invalid input
- `SYNC_IN_PROGRESS` - Operation already running
- `SYNC_FAILED` - Sync operation failed
- `DEPLOY_FAILED` - Deployment failed
- `SERVICE_ERROR` - Internal service error
- `CONFLICT` - Resource conflict (e.g., duplicate source)

### Socket.IO Event Format for Config Changes

```json
{
    "type": "config_event",
    "subtype": "agent_deployed|skill_deployed|source_synced|config_updated",
    "data": { ... },
    "timestamp": "2025-01-01T00:00:00.000Z"
}
```

---

## Endpoint Group 1: Agents (`/api/config/agents/`)

### GET `/api/config/agents/available`

List all agents available in the cache (from synced Git sources).

**Service calls:**
- `GitSourceManager().list_cached_agents()`
- `GitSourceManager().list_cached_agents_with_filters(filters=...)` (if filters provided)

**Query parameters:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `category` | string | No | Filter by category (e.g., "engineer/backend") |
| `language` | string | No | Filter by language (e.g., "python") |
| `framework` | string | No | Filter by framework (e.g., "react") |
| `search` | string | No | Search in name/description |

**Success response (200):**
```json
{
    "success": true,
    "agents": [
        {
            "agent_id": "python-engineer",
            "name": "Python Engineer",
            "description": "Python 3.12+ development specialist...",
            "version": "2.5.0",
            "source": "bobmatnyc/claude-mpm-agents",
            "source_url": "https://github.com/bobmatnyc/claude-mpm-agents",
            "priority": 100,
            "category": "engineer/backend",
            "tags": ["python", "backend"],
            "source_file": "/Users/.../.claude-mpm/cache/agents/..."
        }
    ],
    "total": 45,
    "filters_applied": {"language": "python"}
}
```

---

### GET `/api/config/agents/deployed`

List agents currently deployed in the project's `.claude/agents/` directory.

**Service calls:**
- `AgentManager(project_dir=...).list_agents(location="project")`

**Query parameters:** None.

**Success response (200):**
```json
{
    "success": true,
    "agents": [
        {
            "name": "python-engineer",
            "location": "project",
            "path": "/path/to/project/.claude/agents/python-engineer.md",
            "version": "2.5.0",
            "type": "core",
            "specializations": ["python", "backend"]
        }
    ],
    "total": 12,
    "agents_dir": "/path/to/project/.claude/agents"
}
```

---

### GET `/api/config/agents/{agent_name}`

Get detailed information about a specific agent (checks deployed first, then cache).

**Path parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `agent_name` | string | Agent name (e.g., "python-engineer") |

**Service calls:**
- `AgentManager().read_agent(agent_name)` (for deployed)
- `AgentManager().get_agent_api(agent_name)` (API-friendly format)
- `GitSourceManager().list_cached_agents()` + filter (for cached)

**Success response (200):**
```json
{
    "success": true,
    "agent": {
        "name": "python-engineer",
        "title": "Python Engineer",
        "primary_role": "Python 3.12+ development specialist...",
        "capabilities": ["Type-safe implementations", "Async patterns", ...],
        "when_to_use": {
            "select": ["Python backend development", ...],
            "do_not_select": ["Frontend work", ...]
        },
        "authority": {
            "exclusive_write_access": ["*.py files", ...],
            "forbidden_operations": ["Modifying CI/CD", ...],
            "read_access": ["All project files"]
        },
        "metadata": {
            "type": "core",
            "version": "2.5.0",
            "model_preference": "claude-3-sonnet",
            "tags": ["python", "backend"],
            "specializations": ["python", "backend"]
        },
        "deployed": true,
        "deploy_path": "/path/to/.claude/agents/python-engineer.md",
        "source": "bobmatnyc/claude-mpm-agents"
    }
}
```

**Error response (404):**
```json
{
    "success": false,
    "error": "Agent 'nonexistent' not found",
    "code": "NOT_FOUND"
}
```

---

### POST `/api/config/agents/deploy`

Deploy an agent from the cache to the project.

**Request body:**
```json
{
    "agent_name": "python-engineer",
    "force": false
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `agent_name` | string | Yes | Agent to deploy |
| `force` | boolean | No | Force re-deploy if already deployed (default: false) |

**Service calls:**
- Uses `AgentDeploymentService` via `DeploymentServiceWrapper`
- Single agent deploy via `deployment_service.deploy_agent(agent_name, ...)`

**Success response (200):**
```json
{
    "success": true,
    "message": "Agent 'python-engineer' deployed successfully",
    "agent": {
        "name": "python-engineer",
        "path": "/path/to/.claude/agents/python-engineer.md",
        "version": "2.5.0"
    }
}
```

**Socket.IO event emitted:**
```json
{
    "type": "config_event",
    "subtype": "agent_deployed",
    "data": {
        "agent_name": "python-engineer",
        "version": "2.5.0",
        "action": "deploy"
    },
    "timestamp": "2025-01-01T00:00:00Z"
}
```

**Error response (409 - already deployed):**
```json
{
    "success": false,
    "error": "Agent 'python-engineer' is already deployed. Use force=true to redeploy.",
    "code": "CONFLICT"
}
```

---

### DELETE `/api/config/agents/{agent_name}`

Remove (undeploy) an agent from the project.

**Path parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `agent_name` | string | Agent to undeploy |

**Service calls:**
- `AgentManager().delete_agent(agent_name)`

**Success response (200):**
```json
{
    "success": true,
    "message": "Agent 'python-engineer' removed from project"
}
```

**Socket.IO event emitted:**
```json
{
    "type": "config_event",
    "subtype": "agent_undeployed",
    "data": {"agent_name": "python-engineer"},
    "timestamp": "2025-01-01T00:00:00Z"
}
```

---

### POST `/api/config/agents/deploy-collection`

Deploy a predefined collection of agents.

**Request body:**
```json
{
    "collection": "python-fullstack",
    "force": false
}
```

**Service calls:**
- Collection listing via `AutoDeployIndexParser`
- Batch deployment via agent deployment service

**Success response (200):**
```json
{
    "success": true,
    "message": "Collection 'python-fullstack' deployed: 5 agents",
    "deployed": ["python-engineer", "api-qa", "security", ...],
    "failed": [],
    "skipped": []
}
```

---

### GET `/api/config/agents/collections`

List available agent collections.

**Service calls:**
- `AutoDeployIndexParser` to enumerate categories/collections

**Success response (200):**
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
        }
    ],
    "total": 8
}
```

---

## Endpoint Group 2: Skills (`/api/config/skills/`)

### GET `/api/config/skills/available`

List all skills available in the cache (from synced Git sources).

**Service calls:**
- `GitSkillSourceManager(config).get_all_skills()`

**Query parameters:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `source_id` | string | No | Filter by source |
| `tag` | string | No | Filter by tag |
| `search` | string | No | Search in name/description |

**Success response (200):**
```json
{
    "success": true,
    "skills": [
        {
            "skill_id": "systematic-debugging",
            "name": "Systematic Debugging",
            "description": "Systematic debugging methodology...",
            "skill_version": "1.0.0",
            "tags": ["debugging", "universal"],
            "agent_types": ["engineer", "qa"],
            "source_id": "system",
            "source_priority": 0,
            "deployment_name": "universal-debugging-systematic-debugging"
        }
    ],
    "total": 78
}
```

---

### GET `/api/config/skills/deployed`

List skills currently deployed in `~/.claude/skills/`.

**Service calls:**
- Scan `~/.claude/skills/` directory for deployed skills
- Cross-reference with `load_deployment_index()` for tracking data

**Success response (200):**
```json
{
    "success": true,
    "skills": [
        {
            "name": "universal-debugging-systematic-debugging",
            "path": "/Users/.../.claude/skills/universal-debugging-systematic-debugging",
            "deployed_at": "2025-12-22T10:30:00Z",
            "collection": "claude-mpm-skills",
            "is_user_requested": false
        }
    ],
    "total": 25,
    "deployment_mode": "agent_referenced",
    "skills_dir": "/Users/.../.claude/skills"
}
```

---

### GET `/api/config/skills/{skill_id}`

Get detailed information about a specific skill.

**Path parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `skill_id` | string | Skill ID (e.g., "systematic-debugging") |

**Service calls:**
- `SkillDiscoveryService(cache_path).get_skill_metadata(skill_id)`
- Check deployed status in `~/.claude/skills/`

**Success response (200):**
```json
{
    "success": true,
    "skill": {
        "skill_id": "systematic-debugging",
        "name": "Systematic Debugging",
        "description": "Systematic debugging methodology...",
        "skill_version": "1.0.0",
        "tags": ["debugging", "universal"],
        "agent_types": ["engineer", "qa"],
        "content_preview": "First 500 characters of skill body...",
        "deployed": true,
        "deploy_path": "/Users/.../.claude/skills/universal-debugging-systematic-debugging",
        "source_id": "system",
        "resources": []
    }
}
```

---

### POST `/api/config/skills/deploy`

Deploy a skill from the cache.

**Request body:**
```json
{
    "skill_name": "systematic-debugging",
    "force": false,
    "mark_user_requested": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `skill_name` | string | Yes | Skill to deploy |
| `force` | boolean | No | Force re-deploy (default: false) |
| `mark_user_requested` | boolean | No | Mark as user-requested (protects from cleanup, default: true) |

**Service calls:**
- `GitSkillSourceManager.deploy_skills(skill_filter={skill_name})`
- If `mark_user_requested`: `add_user_requested_skill(skill_name, ...)`

**Success response (200):**
```json
{
    "success": true,
    "message": "Skill 'systematic-debugging' deployed successfully",
    "skill": {
        "name": "universal-debugging-systematic-debugging",
        "path": "/Users/.../.claude/skills/universal-debugging-systematic-debugging"
    }
}
```

**Socket.IO event emitted:**
```json
{
    "type": "config_event",
    "subtype": "skill_deployed",
    "data": {"skill_name": "systematic-debugging", "action": "deploy"},
    "timestamp": "2025-01-01T00:00:00Z"
}
```

---

### DELETE `/api/config/skills/{skill_name}`

Remove (undeploy) a skill.

**Path parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `skill_name` | string | Skill deployment name to remove |

**Service calls:**
- `untrack_skill(claude_skills_dir, skill_name)`
- `remove_user_requested_skill(skill_name, ...)`
- Remove directory from `~/.claude/skills/{skill_name}`

**Success response (200):**
```json
{
    "success": true,
    "message": "Skill 'systematic-debugging' removed"
}
```

---

### GET `/api/config/skills/deployment-mode`

Get current skill deployment mode.

**Service calls:**
- `get_skills_to_deploy(config_path)` to determine mode

**Success response (200):**
```json
{
    "success": true,
    "mode": "agent_referenced",
    "description": "Skills are automatically deployed based on agent requirements",
    "agent_referenced_count": 25,
    "user_defined_count": 0
}
```

---

### PUT `/api/config/skills/deployment-mode`

Switch skill deployment mode.

**Request body:**
```json
{
    "mode": "user_defined",
    "skills": ["skill-a", "skill-b"]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `mode` | string | Yes | `"agent_referenced"` or `"user_defined"` |
| `skills` | string[] | Conditional | Required if mode is `"user_defined"` |

**Service calls:**
- Update `configuration.yaml` via `save_agent_skills_to_config()`
- If `user_defined`: Write skills list to `config.skills.user_defined`
- If `agent_referenced`: Clear `config.skills.user_defined` list

**Success response (200):**
```json
{
    "success": true,
    "message": "Deployment mode changed to 'user_defined'",
    "mode": "user_defined",
    "skills_count": 15
}
```

---

## Endpoint Group 3: Git Sources (`/api/config/sources/`)

### GET `/api/config/sources/`

List all configured sources (both agent and skill sources).

**Service calls:**
- `AgentSourceConfiguration.load()` for agent sources
- `SkillSourceConfiguration.load()` for skill sources

**Query parameters:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | No | Filter: `"agent"`, `"skill"`, or `"all"` (default: `"all"`) |

**Success response (200):**
```json
{
    "success": true,
    "sources": {
        "agent_sources": [
            {
                "identifier": "bobmatnyc/claude-mpm-agents/agents",
                "url": "https://github.com/bobmatnyc/claude-mpm-agents",
                "subdirectory": "agents",
                "priority": 100,
                "enabled": true,
                "is_system": true
            }
        ],
        "skill_sources": [
            {
                "id": "system",
                "type": "git",
                "url": "https://github.com/bobmatnyc/claude-mpm-skills",
                "branch": "main",
                "priority": 0,
                "enabled": true,
                "is_system": true
            }
        ]
    },
    "total_agent_sources": 1,
    "total_skill_sources": 2
}
```

---

### POST `/api/config/sources/agent`

Add a new agent source.

**Request body:**
```json
{
    "url": "https://github.com/owner/repo",
    "subdirectory": "agents",
    "priority": 200,
    "enabled": true,
    "skip_test": false
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | string | Yes | GitHub repository URL |
| `subdirectory` | string | No | Subdirectory containing agents |
| `priority` | integer | No | Priority (default: 100, range: 0-1000) |
| `enabled` | boolean | No | Enable immediately (default: true) |
| `skip_test` | boolean | No | Skip access test (default: false) |

**Service calls:**
- `AgentSourceConfiguration.load()` + `add_repository()` + `save()`
- If not `skip_test`: Test access via GitHub API

**Success response (201):**
```json
{
    "success": true,
    "message": "Agent source added: owner/repo/agents",
    "source": {
        "identifier": "owner/repo/agents",
        "url": "https://github.com/owner/repo",
        "priority": 200,
        "enabled": true
    },
    "test_result": {
        "accessible": true,
        "agents_discovered": 12
    }
}
```

**Error response (409 - duplicate):**
```json
{
    "success": false,
    "error": "Source 'owner/repo/agents' already exists",
    "code": "CONFLICT"
}
```

---

### POST `/api/config/sources/skill`

Add a new skill source.

**Request body:**
```json
{
    "id": "custom-skills",
    "url": "https://github.com/owner/skills",
    "branch": "main",
    "priority": 200,
    "enabled": true,
    "token": "$PRIVATE_TOKEN"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | No | Source ID (auto-generated from URL if omitted) |
| `url` | string | Yes | GitHub repository URL |
| `branch` | string | No | Branch (default: "main") |
| `priority` | integer | No | Priority (default: 100) |
| `enabled` | boolean | No | Enable immediately (default: true) |
| `token` | string | No | GitHub token or env var ref (e.g., "$TOKEN") |

**Service calls:**
- `SkillSourceConfiguration.load()` + `add_source()` + `save()`

**Success response (201):**
```json
{
    "success": true,
    "message": "Skill source added: custom-skills",
    "source": {
        "id": "custom-skills",
        "url": "https://github.com/owner/skills",
        "priority": 200,
        "enabled": true
    }
}
```

---

### DELETE `/api/config/sources/{source_type}/{source_id}`

Remove a source.

**Path parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `source_type` | string | `"agent"` or `"skill"` |
| `source_id` | string | Source identifier |

**Service calls:**
- Agent: `AgentSourceConfiguration.load()` + `remove_repository(source_id)` + `save()`
- Skill: `SkillSourceConfiguration.load()` + `remove_source(source_id)` + `save()`

**Success response (200):**
```json
{
    "success": true,
    "message": "Source 'custom-skills' removed"
}
```

---

### PATCH `/api/config/sources/{source_type}/{source_id}`

Update a source (enable/disable, change priority).

**Request body:**
```json
{
    "enabled": false,
    "priority": 50
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `enabled` | boolean | No | Enable/disable source |
| `priority` | integer | No | Update priority |

**Success response (200):**
```json
{
    "success": true,
    "message": "Source updated",
    "source": {
        "id": "custom-skills",
        "enabled": false,
        "priority": 50
    }
}
```

---

### POST `/api/config/sources/{source_type}/{source_id}/sync`

Sync a specific source (long-running).

**Path parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `source_type` | string | `"agent"` or `"skill"` |
| `source_id` | string | Source identifier |

**Query parameters:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `force` | boolean | No | Force re-download (default: false) |

**Implementation:** This is a **long-running operation**. The HTTP response returns immediately with a job ID. Progress is reported via Socket.IO events.

**Service calls:**
- Agent: `GitSourceManager().sync_repository(repo, force=force)`
- Skill: `GitSkillSourceManager(config).sync_source(source_id, force=force)`

**Immediate response (202 Accepted):**
```json
{
    "success": true,
    "message": "Sync started for 'system'",
    "job_id": "sync-system-1703001234",
    "status": "in_progress"
}
```

**Socket.IO progress events:**
```json
{
    "type": "config_event",
    "subtype": "sync_progress",
    "data": {
        "job_id": "sync-system-1703001234",
        "source_id": "system",
        "source_type": "skill",
        "progress": 45,
        "total_files": 272,
        "files_processed": 122,
        "status": "in_progress"
    },
    "timestamp": "2025-01-01T00:00:00Z"
}
```

**Socket.IO completion event:**
```json
{
    "type": "config_event",
    "subtype": "sync_completed",
    "data": {
        "job_id": "sync-system-1703001234",
        "source_id": "system",
        "source_type": "skill",
        "status": "completed",
        "files_updated": 15,
        "files_cached": 257,
        "items_discovered": 78
    },
    "timestamp": "2025-01-01T00:00:00Z"
}
```

---

### POST `/api/config/sources/sync-all`

Sync all enabled sources (long-running).

**Query parameters:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | No | `"agent"`, `"skill"`, or `"all"` (default: "all") |
| `force` | boolean | No | Force re-download (default: false) |

**Service calls:**
- Agent: `GitSourceManager().sync_all_repositories(repos, force=force)`
- Skill: `GitSkillSourceManager(config).sync_all_sources(force=force)`

**Immediate response (202 Accepted):**
```json
{
    "success": true,
    "message": "Sync started for all sources",
    "job_id": "sync-all-1703001234",
    "sources_to_sync": 3
}
```

Progress and completion via Socket.IO events (same format as single sync).

---

### GET `/api/config/sources/sync-status`

Get current sync status.

**Success response (200):**
```json
{
    "success": true,
    "is_syncing": false,
    "last_sync": "2025-01-01T10:30:00Z",
    "active_jobs": [],
    "last_results": {
        "agent_sources": {
            "bobmatnyc/claude-mpm-agents/agents": {
                "synced": true,
                "agents_discovered": 45,
                "timestamp": "2025-01-01T10:30:00Z"
            }
        },
        "skill_sources": {
            "system": {
                "synced": true,
                "skills_discovered": 78,
                "timestamp": "2025-01-01T10:30:00Z"
            }
        }
    }
}
```

---

## Endpoint Group 4: Auto-Configure (`/api/config/auto-configure/`)

### POST `/api/config/auto-configure/detect`

Detect project toolchain.

**Request body:**
```json
{
    "project_path": "/path/to/project"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `project_path` | string | No | Project path (default: cwd) |

**Service calls:**
- `AutoConfigManagerService._analyze_toolchain(project_path)`

**Success response (200):**
```json
{
    "success": true,
    "toolchain": {
        "primary_language": "python",
        "frameworks": [
            {"name": "fastapi", "version": "0.100+", "confidence": 0.95}
        ],
        "deployment_target": {
            "platform": "docker",
            "confidence": 0.8
        },
        "build_tools": ["uv", "pytest"],
        "detected_files": {
            "pyproject.toml": true,
            "Dockerfile": true,
            "package.json": false
        }
    }
}
```

---

### POST `/api/config/auto-configure/preview`

Generate recommendations without applying.

**Request body:**
```json
{
    "project_path": "/path/to/project",
    "min_confidence": 0.8
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `project_path` | string | No | Project path (default: cwd) |
| `min_confidence` | float | No | Minimum confidence (default: 0.8) |

**Service calls:**
- `AutoConfigManagerService().preview_configuration(project_path, min_confidence)`

**Success response (200):**
```json
{
    "success": true,
    "preview": {
        "would_deploy": [
            {
                "agent_id": "python-engineer",
                "agent_name": "Python Engineer",
                "confidence_score": 0.95,
                "reason": "Python project with FastAPI framework detected"
            }
        ],
        "would_skip": [],
        "estimated_deployment_time": 25.0,
        "validation": {
            "is_valid": true,
            "warnings": [],
            "errors": []
        },
        "toolchain_summary": {
            "primary_language": "python",
            "frameworks": ["fastapi"],
            "deployment_target": "docker"
        }
    }
}
```

---

### POST `/api/config/auto-configure/apply`

Apply auto-configuration (deploy recommended agents).

**Request body:**
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
| `project_path` | string | No | Project path (default: cwd) |
| `min_confidence` | float | No | Minimum confidence (default: 0.8) |
| `dry_run` | boolean | No | Preview only (default: false) |
| `agent_overrides` | object | No | Manual include/exclude agents |

**Service calls:**
- `AutoConfigManagerService().auto_configure(project_path, ...)`

**This is a long-running operation.** Returns 202 with Socket.IO progress.

**Immediate response (202):**
```json
{
    "success": true,
    "message": "Auto-configuration started",
    "job_id": "autoconfig-1703001234"
}
```

**Socket.IO progress events:**
```json
{
    "type": "config_event",
    "subtype": "autoconfig_progress",
    "data": {
        "job_id": "autoconfig-1703001234",
        "phase": "deploying",
        "current_agent": "python-engineer",
        "progress": 3,
        "total": 5,
        "status": "in_progress"
    },
    "timestamp": "2025-01-01T00:00:00Z"
}
```

**Socket.IO completion event:**
```json
{
    "type": "config_event",
    "subtype": "autoconfig_completed",
    "data": {
        "job_id": "autoconfig-1703001234",
        "status": "success",
        "deployed_agents": ["python-engineer", "api-qa", "security"],
        "failed_agents": [],
        "duration_ms": 12500
    },
    "timestamp": "2025-01-01T00:00:00Z"
}
```

---

## Endpoint Group 5: Skill-Agent Links (`/api/config/skill-links/`)

### GET `/api/config/skill-links/`

Get skill-to-agent mapping data.

**Service calls:**
- `SkillToAgentMapper().get_mapping_stats()`
- `get_required_skills_from_agents(agents_dir)` for actual deployed state

**Success response (200):**
```json
{
    "success": true,
    "links": {
        "by_agent": {
            "python-engineer": {
                "frontmatter_skills": ["systematic-debugging", "python-core"],
                "content_marker_skills": ["mpm-delegation-patterns"],
                "total": 3
            }
        },
        "by_skill": {
            "systematic-debugging": {
                "agents": ["python-engineer", "typescript-engineer", "qa"],
                "source": "frontmatter"
            }
        }
    },
    "stats": {
        "total_skills": 85,
        "total_agents": 12,
        "avg_agents_per_skill": 3.2,
        "avg_skills_per_agent": 8.5
    }
}
```

---

### GET `/api/config/skill-links/agent/{agent_name}`

Get skills linked to a specific agent.

**Path parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `agent_name` | string | Agent name |

**Service calls:**
- `parse_agent_frontmatter(agent_file)` + `get_skills_from_agent(frontmatter)`
- `extract_skills_from_content(agent_file)` for inline markers

**Success response (200):**
```json
{
    "success": true,
    "agent": "python-engineer",
    "skills": {
        "required": ["systematic-debugging", "python-core"],
        "optional": ["flask-framework"],
        "from_content_markers": ["mpm-delegation-patterns"]
    },
    "total_skills": 4
}
```

---

## Endpoint Group 6: Project Configuration (`/api/config/project/`)

### GET `/api/config/project/`

Get current project configuration.

**Service calls:**
- Read `configuration.yaml` from `.claude-mpm/` directory
- Read agent source config
- Read skill source config

**Success response (200):**
```json
{
    "success": true,
    "config": {
        "project_path": "/path/to/project",
        "skills": {
            "deployment_mode": "agent_referenced",
            "agent_referenced": ["skill-a", "skill-b"],
            "user_defined": []
        },
        "agent_sources": {
            "disable_system_repo": true,
            "repositories_count": 1
        },
        "skill_sources": {
            "sources_count": 2,
            "enabled_count": 2
        },
        "auto_config": {
            "enabled": true,
            "last_run": "2025-01-01T10:00:00Z",
            "deployed_agents_count": 5
        }
    }
}
```

---

### GET `/api/config/project/summary`

Get a quick summary of the project configuration state for the dashboard header.

**Success response (200):**
```json
{
    "success": true,
    "summary": {
        "agents_deployed": 12,
        "agents_available": 45,
        "skills_deployed": 25,
        "skills_available": 78,
        "agent_sources": 1,
        "skill_sources": 2,
        "last_sync": "2025-01-01T10:30:00Z",
        "deployment_mode": "agent_referenced",
        "project_path": "/path/to/project"
    }
}
```

---

## Implementation Guide

### Route Registration Pattern

Add a new method `_setup_config_routes()` called from `_setup_http_routes()`:

```python
def _setup_http_routes(self):
    # ... existing routes ...

    # Configuration management routes (new)
    self._setup_config_routes()

    self.logger.info("HTTP routes registered successfully")

def _setup_config_routes(self):
    """Setup REST API routes for configuration management."""

    # Lazy-initialized service instances
    _services = {}

    def get_git_source_manager():
        if 'git_source_manager' not in _services:
            from claude_mpm.services.agents.git_source_manager import GitSourceManager
            _services['git_source_manager'] = GitSourceManager()
        return _services['git_source_manager']

    def get_skill_source_manager():
        if 'skill_source_manager' not in _services:
            from claude_mpm.config.skill_sources import SkillSourceConfiguration
            from claude_mpm.services.skills.git_skill_source_manager import GitSkillSourceManager
            config = SkillSourceConfiguration.load()
            _services['skill_source_manager'] = GitSkillSourceManager(config)
        return _services['skill_source_manager']

    # --- Agent routes ---
    async def agents_available(request):
        try:
            manager = get_git_source_manager()
            filters = {}
            for key in ['category', 'language', 'framework']:
                val = request.query.get(key)
                if val:
                    filters[key] = val

            if filters:
                agents = manager.list_cached_agents_with_filters(filters=filters)
            else:
                agents = manager.list_cached_agents()

            # Apply search filter
            search = request.query.get('search', '').lower()
            if search:
                agents = [a for a in agents if search in str(a.get('metadata', {}).get('name', '')).lower()
                         or search in str(a.get('agent_id', '')).lower()]

            return web.json_response({
                "success": True,
                "agents": agents,
                "total": len(agents),
                "filters_applied": filters
            })
        except Exception as e:
            self.logger.error(f"Error listing available agents: {e}")
            return web.json_response(
                {"success": False, "error": str(e), "code": "SERVICE_ERROR"},
                status=500
            )

    # Register all config routes
    self.app.router.add_get("/api/config/agents/available", agents_available)
    self.app.router.add_get("/api/config/agents/deployed", agents_deployed)
    self.app.router.add_get("/api/config/agents/collections", agents_collections)
    self.app.router.add_get("/api/config/agents/{agent_name}", agent_detail)
    self.app.router.add_post("/api/config/agents/deploy", agents_deploy)
    self.app.router.add_post("/api/config/agents/deploy-collection", agents_deploy_collection)
    self.app.router.add_delete("/api/config/agents/{agent_name}", agents_undeploy)

    self.app.router.add_get("/api/config/skills/available", skills_available)
    self.app.router.add_get("/api/config/skills/deployed", skills_deployed)
    self.app.router.add_get("/api/config/skills/deployment-mode", skills_deployment_mode_get)
    self.app.router.add_put("/api/config/skills/deployment-mode", skills_deployment_mode_set)
    self.app.router.add_get("/api/config/skills/{skill_id}", skill_detail)
    self.app.router.add_post("/api/config/skills/deploy", skills_deploy)
    self.app.router.add_delete("/api/config/skills/{skill_name}", skills_undeploy)

    self.app.router.add_get("/api/config/sources/", sources_list)
    self.app.router.add_get("/api/config/sources/sync-status", sources_sync_status)
    self.app.router.add_post("/api/config/sources/agent", sources_add_agent)
    self.app.router.add_post("/api/config/sources/skill", sources_add_skill)
    self.app.router.add_post("/api/config/sources/sync-all", sources_sync_all)
    self.app.router.add_post("/api/config/sources/{source_type}/{source_id}/sync", sources_sync_one)
    self.app.router.add_patch("/api/config/sources/{source_type}/{source_id}", sources_update)
    self.app.router.add_delete("/api/config/sources/{source_type}/{source_id}", sources_delete)

    self.app.router.add_post("/api/config/auto-configure/detect", autoconfig_detect)
    self.app.router.add_post("/api/config/auto-configure/preview", autoconfig_preview)
    self.app.router.add_post("/api/config/auto-configure/apply", autoconfig_apply)

    self.app.router.add_get("/api/config/skill-links/", skill_links_list)
    self.app.router.add_get("/api/config/skill-links/agent/{agent_name}", skill_links_agent)

    self.app.router.add_get("/api/config/project/", project_config)
    self.app.router.add_get("/api/config/project/summary", project_summary)

    self.logger.info("Configuration API routes registered (34 endpoints)")
```

### Long-Running Operation Pattern

For sync and auto-configure operations:

```python
# Track active sync jobs
_active_jobs = {}

async def sources_sync_one(request):
    source_type = request.match_info['source_type']
    source_id = request.match_info['source_id']
    force = request.query.get('force', 'false').lower() == 'true'

    job_id = f"sync-{source_id}-{int(time.time())}"

    # Start async task
    async def run_sync():
        try:
            _active_jobs[job_id] = {"status": "in_progress", "started": time.time()}

            if source_type == "agent":
                manager = get_git_source_manager()
                config = AgentSourceConfiguration.load()
                repo = next((r for r in config.repositories if r.identifier == source_id), None)
                if repo:
                    result = manager.sync_repository(repo, force=force, show_progress=False)
            elif source_type == "skill":
                manager = get_skill_source_manager()
                result = manager.sync_source(source_id, force=force)

            # Emit completion event
            if self.sio:
                await self.sio.emit("config_event", {
                    "type": "config_event",
                    "subtype": "sync_completed",
                    "data": {"job_id": job_id, "source_id": source_id, **result},
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
                })

            _active_jobs[job_id] = {"status": "completed", **result}

        except Exception as e:
            _active_jobs[job_id] = {"status": "failed", "error": str(e)}
            if self.sio:
                await self.sio.emit("config_event", {
                    "type": "config_event",
                    "subtype": "sync_failed",
                    "data": {"job_id": job_id, "error": str(e)},
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
                })

    # Fire and forget
    asyncio.create_task(run_sync())

    return web.json_response({
        "success": True,
        "message": f"Sync started for '{source_id}'",
        "job_id": job_id,
        "status": "in_progress"
    }, status=202)
```

### CORS Middleware (Required for New Routes)

Add CORS middleware since existing Socket.IO CORS only covers WebSocket:

```python
@web.middleware
async def cors_middleware(request, handler):
    # Handle preflight
    if request.method == 'OPTIONS':
        response = web.Response()
    else:
        response = await handler(request)

    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

# In _start_async_server():
self.app = web.Application(middlewares=[cors_middleware])
```

### Endpoint Summary Table

| # | Method | Path | Long-Running | Socket.IO Event |
|---|--------|------|:------------:|:---------------:|
| 1 | GET | `/api/config/agents/available` | No | - |
| 2 | GET | `/api/config/agents/deployed` | No | - |
| 3 | GET | `/api/config/agents/collections` | No | - |
| 4 | GET | `/api/config/agents/{agent_name}` | No | - |
| 5 | POST | `/api/config/agents/deploy` | No | `agent_deployed` |
| 6 | POST | `/api/config/agents/deploy-collection` | No | `agent_deployed` (per agent) |
| 7 | DELETE | `/api/config/agents/{agent_name}` | No | `agent_undeployed` |
| 8 | GET | `/api/config/skills/available` | No | - |
| 9 | GET | `/api/config/skills/deployed` | No | - |
| 10 | GET | `/api/config/skills/deployment-mode` | No | - |
| 11 | PUT | `/api/config/skills/deployment-mode` | No | `config_updated` |
| 12 | GET | `/api/config/skills/{skill_id}` | No | - |
| 13 | POST | `/api/config/skills/deploy` | No | `skill_deployed` |
| 14 | DELETE | `/api/config/skills/{skill_name}` | No | `skill_undeployed` |
| 15 | GET | `/api/config/sources/` | No | - |
| 16 | GET | `/api/config/sources/sync-status` | No | - |
| 17 | POST | `/api/config/sources/agent` | No | `source_added` |
| 18 | POST | `/api/config/sources/skill` | No | `source_added` |
| 19 | POST | `/api/config/sources/sync-all` | **Yes** | `sync_progress`/`sync_completed` |
| 20 | POST | `/api/config/sources/{type}/{id}/sync` | **Yes** | `sync_progress`/`sync_completed` |
| 21 | PATCH | `/api/config/sources/{type}/{id}` | No | `source_updated` |
| 22 | DELETE | `/api/config/sources/{type}/{id}` | No | `source_removed` |
| 23 | POST | `/api/config/auto-configure/detect` | No | - |
| 24 | POST | `/api/config/auto-configure/preview` | No | - |
| 25 | POST | `/api/config/auto-configure/apply` | **Yes** | `autoconfig_progress`/`autoconfig_completed` |
| 26 | GET | `/api/config/skill-links/` | No | - |
| 27 | GET | `/api/config/skill-links/agent/{name}` | No | - |
| 28 | GET | `/api/config/project/` | No | - |
| 29 | GET | `/api/config/project/summary` | No | - |

**Total: 29 endpoints** (3 long-running with Socket.IO progress)

---

## Cross-Team Business Rules Integration

> _Added based on findings from data-models-analyst (Task #5, doc: `02-data-models-business-rules.md`)_

### BR-1: Optimistic Concurrency Control (No File Locking)

The system has **no file locking** (BR-10). Only atomic writes are used for skill sources. All write endpoints must implement optimistic concurrency control.

**Implementation pattern — ETag-based concurrency:**

All GET responses for mutable resources include an `ETag` header (or `_etag` field) derived from the file's last-modified timestamp + content hash:

```json
// GET /api/config/sources/ response includes:
{
    "success": true,
    "sources": { ... },
    "_etag": "agent_sources:1703001234:a3f2b1c|skill_sources:1703001300:d4e5f6a"
}
```

All mutating requests (POST, PUT, PATCH, DELETE) on config resources **should** include an `If-Match` header with the ETag:

```
PATCH /api/config/sources/agent/my-source
If-Match: "agent_sources:1703001234:a3f2b1c"
Content-Type: application/json

{"enabled": false}
```

**Conflict response (412 Precondition Failed):**
```json
{
    "success": false,
    "error": "Configuration was modified by another process. Please refresh and retry.",
    "code": "STALE_CONFIG",
    "current_etag": "agent_sources:1703001400:b7c8d9e"
}
```

**If `If-Match` is omitted**, the write proceeds (last-write-wins) for backward compatibility, but the response includes a warning:

```json
{
    "success": true,
    "message": "Source updated (no concurrency check — consider using If-Match header)",
    "_warning": "no_etag_provided"
}
```

**Affected endpoints:** All POST/PUT/PATCH/DELETE on endpoints #5–7 (agents), #11, #13–14 (skills), #17–18, #21–22 (sources), #25 (auto-configure apply), #28 (project config update if added).

---

### BR-2: Three Separate Config File Locations — Unified View

Three config files live in **different directories**:
- `~/.claude-mpm/agent_sources.yaml` — Agent source repositories
- `~/.claude-mpm/skill_sources.yaml` — Skill source repositories
- `.claude-mpm/configuration.yaml` — Project-level config (relative to project root)

The **`GET /api/config/project/`** endpoint (endpoint #28) and **`GET /api/config/project/summary`** (endpoint #29) must present a **unified view** by loading all three files and merging their data:

```json
{
    "success": true,
    "config": {
        "project_path": "/path/to/project",
        "config_files": {
            "agent_sources": {
                "path": "~/.claude-mpm/agent_sources.yaml",
                "exists": true,
                "last_modified": "2025-01-01T10:00:00Z"
            },
            "skill_sources": {
                "path": "~/.claude-mpm/skill_sources.yaml",
                "exists": true,
                "last_modified": "2025-01-01T10:30:00Z"
            },
            "project_config": {
                "path": "/path/to/project/.claude-mpm/configuration.yaml",
                "exists": true,
                "last_modified": "2025-01-01T09:00:00Z"
            }
        },
        "skills": { ... },
        "agent_sources": { ... },
        "skill_sources": { ... }
    }
}
```

---

### BR-3: Core Agents Protection (7 Always-Deployed Agents)

Seven core agents must **always** remain deployed:
- `engineer`, `research`, `qa`, `web-qa`, `documentation`, `ops`, `ticketing-agent`

The **`DELETE /api/config/agents/{agent_name}`** endpoint (#7) must reject undeployment of core agents:

```json
// DELETE /api/config/agents/engineer → 403 Forbidden
{
    "success": false,
    "error": "Cannot undeploy core agent 'engineer'. Core agents are always required.",
    "code": "CORE_AGENT_PROTECTED",
    "core_agents": ["engineer", "research", "qa", "web-qa", "documentation", "ops", "ticketing-agent"]
}
```

The **`GET /api/config/agents/deployed`** response (#2) should flag core agents:

```json
{
    "agents": [
        {
            "name": "engineer",
            "is_core": true,
            "can_undeploy": false,
            ...
        },
        {
            "name": "python-engineer",
            "is_core": false,
            "can_undeploy": true,
            ...
        }
    ]
}
```

---

### BR-4: Dual Config System Mediation (Pydantic + YAML)

The system has two overlapping config representations:
- **Pydantic model** (`UnifiedConfig`) — runtime-validated, typed Python objects
- **Flat YAML files** — on-disk persistence

API endpoints must **read through Pydantic** (for validation) and **write through YAML** (for persistence), ensuring round-trip consistency:

```python
async def project_config_update(request):
    data = await request.json()

    # 1. Load current config through Pydantic (validates structure)
    config = UnifiedConfig.load(project_path)

    # 2. Apply updates to Pydantic model (validates values)
    try:
        config.update(data)
    except ValidationError as e:
        return web.json_response({
            "success": False, "error": str(e), "code": "VALIDATION_ERROR"
        }, status=400)

    # 3. Write back to YAML (persistence)
    config.save()  # Writes to configuration.yaml

    return web.json_response({"success": True, ...})
```

---

### BR-5: Environment Variable Override Indicators

Environment variables can override config file values. API responses must **indicate the source** of each value when env vars are in play:

```json
// GET /api/config/sources/ with env override active
{
    "success": true,
    "sources": {
        "skill_sources": [
            {
                "id": "private-source",
                "url": "https://github.com/corp/skills",
                "token": "***",
                "token_source": "env:GITHUB_PRIVATE_TOKEN",
                "priority": 50,
                "priority_source": "file"
            }
        ]
    }
}
```

Value source indicators:
- `"file"` — Value from YAML config file
- `"env:VAR_NAME"` — Value overridden by environment variable
- `"default"` — Built-in default value (not explicitly set)
- `"computed"` — Value derived from other settings

This applies to endpoints #15 (sources list), #28 (project config), and any config read endpoint where env vars may apply.

---

### BR-6: Agent ID Precedence (Project > User > System)

When agents exist at multiple levels, precedence is: **project > user > system**.

The **`GET /api/config/agents/available`** response (#1) and **`GET /api/config/agents/{agent_name}`** (#4) must indicate precedence:

```json
{
    "success": true,
    "agent": {
        "name": "python-engineer",
        "source_level": "project",
        "overrides": {
            "user_level": true,
            "system_level": true
        },
        "versions_by_level": {
            "project": {"version": "2.6.0", "path": "/project/.claude/agents/python-engineer.md"},
            "user": {"version": "2.5.0", "path": "~/.claude/agents/python-engineer.md"},
            "system": {"version": "2.4.0", "source": "bobmatnyc/claude-mpm-agents"}
        },
        "active_version": "2.6.0",
        "active_source": "project"
    }
}
```

The **deploy endpoint** (#5) should support a `level` parameter:

```json
// POST /api/config/agents/deploy
{
    "agent_name": "python-engineer",
    "level": "project",
    "force": false
}
```

Where `level` is `"project"` (default) or `"user"`.

---

### BR-7: Skill Deployment Mode Semantics

`user_defined` mode **overrides** `agent_referenced` mode entirely. The API must enforce clear semantics:

- **`agent_referenced` mode**: Skills are auto-deployed based on agent frontmatter `required_skills` lists. Adding/removing agents automatically changes deployed skills.
- **`user_defined` mode**: Only explicitly listed skills are deployed. Agent frontmatter skills are **ignored**. Users have full manual control.

The **`PUT /api/config/skills/deployment-mode`** endpoint (#11) must include a **confirmation warning** when switching modes:

```json
// Response when switching from agent_referenced → user_defined:
{
    "success": true,
    "message": "Deployment mode changed to 'user_defined'",
    "mode": "user_defined",
    "warning": "Agent frontmatter skills will no longer be auto-deployed. Only skills in the user_defined list will be active.",
    "impact": {
        "currently_agent_referenced": 25,
        "will_remain_deployed": 3,
        "will_be_orphaned": 22,
        "user_defined_list": ["skill-a", "skill-b", "skill-c"]
    }
}
```

The **`GET /api/config/skills/deployed`** response (#9) must reflect active mode:

```json
{
    "success": true,
    "deployment_mode": "agent_referenced",
    "mode_description": "Skills auto-deployed from agent frontmatter requirements",
    "skills": [...],
    "mode_specific": {
        "agent_referenced_skills": 25,
        "user_requested_overrides": 3,
        "core_skills_always_deployed": 5
    }
}
```

---

### Service-to-Endpoint Mapping

| Service | File | Endpoints Using It |
|---------|------|--------------------|
| `GitSourceManager` | `services/agents/git_source_manager.py` | #1, #4, #19, #20 |
| `AgentManager` | `services/agents/management/agent_management_service.py` | #2, #4, #7 |
| `AgentDeploymentService` | `services/agents/deployment/` | #5, #6 |
| `AutoDeployIndexParser` | `services/agents/auto_deploy_index_parser.py` | #1, #3 |
| `GitSkillSourceManager` | `services/skills/git_skill_source_manager.py` | #8, #13, #19, #20 |
| `SkillDiscoveryService` | `services/skills/skill_discovery_service.py` | #12 |
| `selective_skill_deployer` | `services/skills/selective_skill_deployer.py` | #9, #13, #14 |
| `SkillToAgentMapper` | `services/skills/skill_to_agent_mapper.py` | #26, #27 |
| `AutoConfigManagerService` | `services/agents/auto_config_manager.py` | #23, #24, #25 |
| `AgentSourceConfiguration` | `config/agent_sources.py` | #15, #17, #21, #22 |
| `SkillSourceConfiguration` | `config/skill_sources.py` | #15, #18, #21, #22 |
