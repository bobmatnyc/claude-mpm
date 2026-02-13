# Phase 1: Read-Only Configuration Visibility

> **Implementation Plan for Claude MPM Dashboard Configuration UI**
>
> Date: 2026-02-13
> Branch: `ui-agents-skills-config`
> Status: Implementation-ready
> Research Docs: `docs/research/ui-for-claude-mpm-configuration-management/01-05`

---

## 1. Phase Summary

**Goal**: Give users visibility into their current configuration state through the dashboard. Users can see what agents are deployed, what skills are active, and where everything is sourced from -- all without any mutation operations.

**Timeline**: 2-3 days (1 day backend, 1-2 days frontend)

**Risk Level**: LOW. Every endpoint is read-only. There are zero concurrency risks, zero file-write risks, zero state-corruption risks. The only failure modes are "data doesn't load" or "service throws during read," both of which result in a harmless error message.

**Key Deliverables**:
- 6 new GET-only API endpoints under `/api/config/`
- 1 new Svelte store (`config.svelte.ts`)
- 5 new Svelte components (in a `config/` subdirectory)
- 2 shared utility components (`Badge.svelte`, `SearchInput.svelte`)
- CORS middleware for aiohttp (required for Vite dev proxy)
- New "Config" tab in the dashboard navigation

**Non-Goals (explicitly deferred to Phase 2+)**:
- No deploy/undeploy operations
- No source add/remove/edit
- No skill install/uninstall
- No configuration file mutations of any kind
- No Socket.IO real-time config event streaming (wired but non-functional)

---

## 2. Prerequisites

Before any implementation work begins, these items must be in place.

### 2.1 CORS Middleware for aiohttp

The Vite dev server runs on `localhost:5173`, while the Python backend runs on `localhost:8765`. The Vite config already proxies `/api` and `/socket.io` requests, but when running in production (where the Svelte build is served from the Python server itself), CORS headers are still needed for any cross-origin scenario.

Socket.IO already has CORS configured:
```python
self.sio = socketio.AsyncServer(cors_allowed_origins="*")
```

But the aiohttp HTTP routes have **no CORS middleware**. This must be added before the config endpoints will work from the Vite dev server without the proxy (e.g., direct browser fetch).

**Action**: Add CORS middleware to `server.py` during route setup. See Section 3.2 for implementation.

### 2.2 Directory Creation

Create the `config/` subdirectory for frontend components:
```
src/claude_mpm/dashboard-svelte/src/lib/components/config/
```

This establishes a precedent for grouping related components by feature, which the current flat structure (12 components in one directory) will need as the dashboard grows.

### 2.3 Verify Service Availability

Before writing endpoint handlers, confirm that the following services can be instantiated without side effects:

| Service | File | Constructor Side Effects |
|---------|------|------------------------|
| `AgentDeploymentService` | `services/agents/deployment/agent_deployment.py:59` | Creates 13 sub-services, reads filesystem. **Must call in `asyncio.to_thread()`** |
| `AgentManager` | `services/agents/management/agent_management_service.py:39` | Lighter. Needs `project_dir` parameter |
| `GitSourceManager` | `services/agents/git_source_manager.py:19` | Needs `AgentSourceConfiguration`. Reads config files |
| `SkillsDeployerService` | `services/skills_deployer.py:39` | Needs config. Reads filesystem |
| `AgentSourceConfiguration` | `config/agent_sources.py:16` | Dataclass. Reads `~/.claude-mpm/config/agent_sources.yaml` |
| `SkillSourceConfiguration` | `config/skill_sources.py:177` | Reads `~/.claude-mpm/config/skill_sources.yaml` |

All of these perform filesystem reads during construction. None are async. Every instantiation must be wrapped in `asyncio.to_thread()` from the async route handlers.

---

## 3. Backend Implementation

### 3.1 New File: `config_routes.py`

**Location**: `src/claude_mpm/services/monitor/config_routes.py`

**Rationale**: The main `server.py` is already 65KB. Adding 6 endpoints with their handler functions inline would push it past 70KB and make navigation painful. A separate route module follows the pattern of extracting concerns into focused files.

**Structure**:

```python
"""Configuration API routes for the Claude MPM Dashboard.

Phase 1: Read-only endpoints for configuration visibility.
All endpoints are GET-only. No mutation operations.
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

from aiohttp import web

logger = logging.getLogger(__name__)

# Lazy-initialized service singletons (per-process, not per-request)
_agent_deployment_service = None
_agent_manager = None
_git_source_manager = None
_skills_deployer_service = None


def _get_agent_manager(project_dir: Optional[Path] = None):
    """Lazy singleton for AgentManager."""
    global _agent_manager
    if _agent_manager is None:
        from claude_mpm.services.agents.management.agent_management_service import (
            AgentManager,
        )
        _agent_manager = AgentManager(project_dir=project_dir or Path.cwd())
    return _agent_manager


def _get_git_source_manager():
    """Lazy singleton for GitSourceManager."""
    global _git_source_manager
    if _git_source_manager is None:
        from claude_mpm.services.agents.git_source_manager import GitSourceManager
        _git_source_manager = GitSourceManager()
    return _git_source_manager


def _get_skills_deployer():
    """Lazy singleton for SkillsDeployerService."""
    global _skills_deployer_service
    if _skills_deployer_service is None:
        from claude_mpm.services.skills_deployer import SkillsDeployerService
        _skills_deployer_service = SkillsDeployerService()
    return _skills_deployer_service


def register_config_routes(app: web.Application, server_instance=None):
    """Register all configuration API routes on the aiohttp app.

    Called from UnifiedMonitorServer._setup_http_routes().

    Args:
        app: The aiohttp web application
        server_instance: Optional reference to UnifiedMonitorServer
                        (for accessing working_directory, etc.)
    """
    app.router.add_get("/api/config/project/summary", handle_project_summary)
    app.router.add_get("/api/config/agents/deployed", handle_agents_deployed)
    app.router.add_get("/api/config/agents/available", handle_agents_available)
    app.router.add_get("/api/config/skills/deployed", handle_skills_deployed)
    app.router.add_get("/api/config/skills/available", handle_skills_available)
    app.router.add_get("/api/config/sources", handle_sources)

    logger.info("Registered 6 config API routes under /api/config/")


# --- Endpoint Handlers ---
# Each follows the same async safety pattern:
#   1. Wrap blocking service calls in asyncio.to_thread()
#   2. Return {"success": True, "data": ...} on success
#   3. Return {"success": False, "error": str(e)} on failure


async def handle_project_summary(request: web.Request) -> web.Response:
    ...

async def handle_agents_deployed(request: web.Request) -> web.Response:
    ...

async def handle_agents_available(request: web.Request) -> web.Response:
    ...

async def handle_skills_deployed(request: web.Request) -> web.Response:
    ...

async def handle_skills_available(request: web.Request) -> web.Response:
    ...

async def handle_sources(request: web.Request) -> web.Response:
    ...
```

### 3.2 CORS Middleware

**Add to**: `src/claude_mpm/services/monitor/server.py`, inside the `_setup_http_routes()` method, before any route registration.

```python
@web.middleware
async def cors_middleware(request, handler):
    """Add CORS headers to all responses. Required for Vite dev server proxy."""
    if request.method == "OPTIONS":
        return web.Response(headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, If-None-Match",
        })
    response = await handler(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response
```

**Registration** (in `server.py` `__init__` or before app creation):
```python
self.app = web.Application(middlewares=[cors_middleware])
```

Note: Phase 1 only needs `GET` and `OPTIONS` in the CORS allow-methods. When Phase 2 adds mutation endpoints, expand to include `POST, PUT, PATCH, DELETE` and add `If-Match` to allowed headers.

### 3.3 Registration from `server.py`

**In `_setup_http_routes()` (around line 520)**, add at the end of the method:

```python
# Register config API routes (Phase 1: read-only)
from claude_mpm.services.monitor.config_routes import register_config_routes
register_config_routes(self.app, server_instance=self)
```

This follows the existing pattern of lazy imports within methods (seen in the existing handlers that import `VersionService()` inline).

### 3.4 Endpoint Specifications

#### 3.4.1 `GET /api/config/project/summary`

**Purpose**: High-level configuration overview for the dashboard summary cards.

**Handler**:
```python
async def handle_project_summary(request: web.Request) -> web.Response:
    try:
        def _get_summary():
            from claude_mpm.core.config import Config
            config = Config()

            # Count deployed agents
            agent_mgr = _get_agent_manager()
            deployed_agents = agent_mgr.list_agents(location="project")
            deployed_count = len(deployed_agents) if isinstance(deployed_agents, list) else len(deployed_agents.keys())

            # Count available agents (from cache)
            git_mgr = _get_git_source_manager()
            available_agents = git_mgr.list_cached_agents()

            # Count deployed skills
            skills_svc = _get_skills_deployer()
            deployed_skills = skills_svc.check_deployed_skills()

            # Count sources
            from claude_mpm.config.agent_sources import AgentSourceConfiguration
            from claude_mpm.config.skill_sources import SkillSourceConfiguration
            agent_sources = AgentSourceConfiguration()
            skill_sources = SkillSourceConfiguration()

            return {
                "agents": {
                    "deployed": deployed_count,
                    "available": len(available_agents),
                },
                "skills": {
                    "deployed": deployed_skills.get("deployed_count", 0),
                    "available": 0,  # Requires network call; omit in summary
                },
                "sources": {
                    "agent_sources": len(agent_sources.repositories) if hasattr(agent_sources, 'repositories') else 0,
                    "skill_sources": len(skill_sources.sources) if hasattr(skill_sources, 'sources') else 0,
                },
                "deployment_mode": getattr(config, 'environment', 'production'),
            }

        data = await asyncio.to_thread(_get_summary)
        return web.json_response({"success": True, "data": data})
    except Exception as e:
        logger.error(f"Error fetching project summary: {e}")
        return web.json_response(
            {"success": False, "error": str(e), "code": "SERVICE_ERROR"},
            status=500,
        )
```

**Response Schema**:
```json
{
    "success": true,
    "data": {
        "agents": {
            "deployed": 12,
            "available": 87
        },
        "skills": {
            "deployed": 15,
            "available": 0
        },
        "sources": {
            "agent_sources": 2,
            "skill_sources": 2
        },
        "deployment_mode": "production"
    }
}
```

#### 3.4.2 `GET /api/config/agents/deployed`

**Purpose**: List all agents currently deployed in the project's `.claude/agents/` directory.

**Handler**:
```python
async def handle_agents_deployed(request: web.Request) -> web.Response:
    try:
        def _list_deployed():
            from claude_mpm.config.agent_presets import CORE_AGENTS

            agent_mgr = _get_agent_manager()
            agents_data = agent_mgr.list_agents(location="project")

            # Normalize: list_agents returns Dict[str, Dict] or List
            if isinstance(agents_data, dict):
                agents_list = [
                    {"name": name, **details}
                    for name, details in agents_data.items()
                ]
            else:
                agents_list = agents_data

            # Determine core agent names for flagging
            core_names = set()
            for agent_id in CORE_AGENTS:
                # CORE_AGENTS uses paths like "engineer/core/engineer"
                # Deployed agent names are stems like "engineer"
                parts = agent_id.split("/")
                core_names.add(parts[-1])

            # Enrich with is_core flag
            for agent in agents_list:
                agent_name = agent.get("name", "")
                agent["is_core"] = agent_name in core_names

            return agents_list

        agents = await asyncio.to_thread(_list_deployed)
        return web.json_response({
            "success": True,
            "agents": agents,
            "total": len(agents),
        })
    except Exception as e:
        logger.error(f"Error listing deployed agents: {e}")
        return web.json_response(
            {"success": False, "error": str(e), "code": "SERVICE_ERROR"},
            status=500,
        )
```

**Response Schema**:
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
            "specializations": ["python", "backend"],
            "is_core": false
        },
        {
            "name": "engineer",
            "location": "project",
            "path": "/path/to/project/.claude/agents/engineer.md",
            "version": "3.0.0",
            "type": "core",
            "is_core": true
        }
    ],
    "total": 12
}
```

**Note on `AgentManager` vs `AgentDeploymentService`**: Research Doc 04 references `AgentManager(project_dir=...).list_agents(location="project")`. The actual service at `services/agents/management/agent_management_service.py:265` confirms `list_agents(location)` exists and returns `Dict[str, Dict[str, Any]]`. This is the correct service for deployed agent enumeration. `AgentDeploymentService` is for deploy/undeploy operations (Phase 2+).

#### 3.4.3 `GET /api/config/agents/available`

**Purpose**: List all agents in the Git cache (`~/.claude-mpm/cache/agents/`).

**Handler**:
```python
async def handle_agents_available(request: web.Request) -> web.Response:
    try:
        search = request.query.get("search", None)

        def _list_available():
            git_mgr = _get_git_source_manager()
            if search:
                agents = git_mgr.list_cached_agents_with_filters(
                    filters={"search": search}
                )
            else:
                agents = git_mgr.list_cached_agents()

            # Enrich with is_deployed flag by checking project agents
            agent_mgr = _get_agent_manager()
            deployed = agent_mgr.list_agents(location="project")
            deployed_names = set()
            if isinstance(deployed, dict):
                deployed_names = set(deployed.keys())
            else:
                deployed_names = {a.get("name", "") for a in deployed}

            for agent in agents:
                agent_name = agent.get("name", agent.get("agent_id", ""))
                agent["is_deployed"] = agent_name in deployed_names

            return agents

        agents = await asyncio.to_thread(_list_available)

        response = web.json_response({
            "success": True,
            "agents": agents,
            "total": len(agents),
            "filters_applied": {"search": search} if search else {},
        })
        # Cache hint: available agents change only on sync
        response.headers["Cache-Control"] = "private, max-age=60"
        return response
    except Exception as e:
        logger.error(f"Error listing available agents: {e}")
        return web.json_response(
            {"success": False, "error": str(e), "code": "SERVICE_ERROR"},
            status=500,
        )
```

**Response Schema**:
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
            "is_deployed": true
        }
    ],
    "total": 87,
    "filters_applied": {}
}
```

**Performance Concern**: With 100+ agents in the cache, this endpoint may take 2-3 seconds due to filesystem scanning and YAML/MD frontmatter parsing. The `Cache-Control: private, max-age=60` header tells the browser to cache the response for 60 seconds. The frontend should also show a loading spinner and avoid re-fetching on every tab switch.

#### 3.4.4 `GET /api/config/skills/deployed`

**Purpose**: List all skills currently deployed in `~/.claude/skills/`.

**Handler**:
```python
async def handle_skills_deployed(request: web.Request) -> web.Response:
    try:
        def _list_deployed_skills():
            skills_svc = _get_skills_deployer()
            deployed = skills_svc.check_deployed_skills()

            # Enrich with deployment index metadata if available
            try:
                from claude_mpm.services.skills.selective_skill_deployer import (
                    load_deployment_index,
                )
                skills_dir = Path.home() / ".claude" / "skills"
                index = load_deployment_index(skills_dir)

                deployed_meta = index.get("deployed_skills", {})
                user_requested = set(index.get("user_requested_skills", []))

                skills_list = []
                for skill in deployed.get("skills", []):
                    skill_name = skill.get("name", "")
                    meta = deployed_meta.get(skill_name, {})
                    skills_list.append({
                        "name": skill_name,
                        "path": skill.get("path", ""),
                        "description": meta.get("description", ""),
                        "category": meta.get("category", "unknown"),
                        "collection": meta.get("collection", ""),
                        "is_user_requested": skill_name in user_requested,
                        "deploy_mode": (
                            "user_defined" if skill_name in user_requested
                            else "agent_referenced"
                        ),
                        "deploy_date": meta.get("deployed_at", ""),
                    })

                return {
                    "skills": skills_list,
                    "total": len(skills_list),
                    "claude_skills_dir": str(deployed.get("claude_skills_dir", "")),
                }
            except ImportError:
                # Fallback: return basic deployed skills without metadata
                return deployed

        data = await asyncio.to_thread(_list_deployed_skills)
        return web.json_response({"success": True, **data})
    except Exception as e:
        logger.error(f"Error listing deployed skills: {e}")
        return web.json_response(
            {"success": False, "error": str(e), "code": "SERVICE_ERROR"},
            status=500,
        )
```

**Response Schema**:
```json
{
    "success": true,
    "skills": [
        {
            "name": "git-workflow",
            "path": "/Users/user/.claude/skills/universal-collaboration-git-workflow",
            "description": "Essential Git patterns for effective version control",
            "category": "collaboration",
            "collection": "universal",
            "is_user_requested": false,
            "deploy_mode": "agent_referenced",
            "deploy_date": "2026-02-10T14:32:00Z"
        }
    ],
    "total": 15,
    "claude_skills_dir": "/Users/user/.claude/skills"
}
```

#### 3.4.5 `GET /api/config/skills/available`

**Purpose**: List all skills available from configured skill sources.

**Handler**:
```python
async def handle_skills_available(request: web.Request) -> web.Response:
    try:
        collection = request.query.get("collection", None)

        def _list_available_skills():
            skills_svc = _get_skills_deployer()
            result = skills_svc.list_available_skills(collection=collection)

            # Mark which are deployed
            deployed = skills_svc.check_deployed_skills()
            deployed_names = {
                s.get("name", "") for s in deployed.get("skills", [])
            }

            # Flatten the categorized result into a flat list for the UI
            flat_skills = []
            categories = result.get("categories", result.get("skills", {}))
            if isinstance(categories, dict):
                for category, skills in categories.items():
                    if isinstance(skills, list):
                        for skill in skills:
                            skill["category"] = category
                            skill["is_deployed"] = skill.get("name", "") in deployed_names
                            flat_skills.append(skill)
            elif isinstance(categories, list):
                for skill in categories:
                    skill["is_deployed"] = skill.get("name", "") in deployed_names
                    flat_skills.append(skill)

            return flat_skills

        skills = await asyncio.to_thread(_list_available_skills)

        response = web.json_response({
            "success": True,
            "skills": skills,
            "total": len(skills),
            "filters_applied": {"collection": collection} if collection else {},
        })
        response.headers["Cache-Control"] = "private, max-age=120"
        return response
    except Exception as e:
        logger.error(f"Error listing available skills: {e}")
        return web.json_response(
            {"success": False, "error": str(e), "code": "SERVICE_ERROR"},
            status=500,
        )
```

**Response Schema**:
```json
{
    "success": true,
    "skills": [
        {
            "name": "test-driven-development",
            "description": "TDD patterns and practices",
            "category": "testing",
            "collection": "universal",
            "is_deployed": true
        }
    ],
    "total": 45,
    "filters_applied": {}
}
```

**Performance Concern**: `list_available_skills()` makes HTTP calls to GitHub to download the skill manifest. This is a blocking network operation that can take 3-5 seconds. The `Cache-Control: private, max-age=120` header is set to 2 minutes. The frontend should cache this aggressively and show a distinct "Loading from GitHub..." state.

#### 3.4.6 `GET /api/config/sources`

**Purpose**: Unified list of both agent and skill sources, sorted by priority.

**Handler**:
```python
async def handle_sources(request: web.Request) -> web.Response:
    try:
        def _list_sources():
            from claude_mpm.config.agent_sources import AgentSourceConfiguration
            from claude_mpm.config.skill_sources import SkillSourceConfiguration

            sources = []

            # Agent sources
            try:
                agent_config = AgentSourceConfiguration()
                for repo in getattr(agent_config, 'repositories', []):
                    sources.append({
                        "id": repo.url.split("/")[-1] if hasattr(repo, 'url') else "unknown",
                        "type": "agent",
                        "url": getattr(repo, 'url', ''),
                        "subdirectory": getattr(repo, 'subdirectory', None),
                        "enabled": getattr(repo, 'enabled', True),
                        "priority": getattr(repo, 'priority', 100),
                    })
            except Exception as e:
                logger.warning(f"Failed to load agent sources: {e}")

            # Skill sources
            try:
                skill_config = SkillSourceConfiguration()
                for source in getattr(skill_config, 'sources', []):
                    sources.append({
                        "id": getattr(source, 'id', 'unknown'),
                        "type": "skill",
                        "url": getattr(source, 'url', ''),
                        "branch": getattr(source, 'branch', 'main'),
                        "enabled": getattr(source, 'enabled', True),
                        "priority": getattr(source, 'priority', 100),
                    })
            except Exception as e:
                logger.warning(f"Failed to load skill sources: {e}")

            # Sort by priority (lower number = higher precedence)
            sources.sort(key=lambda s: s.get("priority", 100))
            return sources

        sources = await asyncio.to_thread(_list_sources)
        return web.json_response({
            "success": True,
            "sources": sources,
            "total": len(sources),
        })
    except Exception as e:
        logger.error(f"Error listing sources: {e}")
        return web.json_response(
            {"success": False, "error": str(e), "code": "SERVICE_ERROR"},
            status=500,
        )
```

**Response Schema**:
```json
{
    "success": true,
    "sources": [
        {
            "id": "system",
            "type": "skill",
            "url": "https://github.com/bobmatnyc/claude-mpm-skills",
            "branch": "main",
            "enabled": true,
            "priority": 0
        },
        {
            "id": "claude-mpm-agents",
            "type": "agent",
            "url": "https://github.com/bobmatnyc/claude-mpm-agents",
            "subdirectory": "agents",
            "enabled": true,
            "priority": 100
        }
    ],
    "total": 4
}
```

### 3.5 Error Handling Pattern

All endpoints follow a consistent error contract:

```python
# Success
{"success": True, "data": ..., ...}     # HTTP 200

# Client error (Phase 1 has none; reserved for Phase 2)
{"success": False, "error": "...", "code": "VALIDATION_ERROR"}  # HTTP 400

# Server error
{"success": False, "error": "...", "code": "SERVICE_ERROR"}     # HTTP 500
```

The `code` field enables the frontend to programmatically distinguish error types without parsing the `error` message string.

### 3.6 Service Instantiation Strategy

**Pattern**: Lazy module-level singletons with thread-safe initialization.

Services are created on first use and reused across requests. This avoids:
- Creating services on every request (wasteful -- constructors read the filesystem)
- Creating services at import time (breaks if config files don't exist yet)
- Injecting services from `server.py` (tight coupling)

**Thread safety note**: Python's GIL protects against race conditions in the singleton check (`if _service is None`). Even if two `asyncio.to_thread()` calls run concurrently, the worst case is two services are created and one overwrites the other -- not a correctness issue for read-only singletons.

**Singleton invalidation**: If the user modifies config files while the dashboard is running, the singletons will hold stale data. Phase 1 accepts this limitation. Phase 2 should add a `/api/config/refresh` endpoint that resets the singletons by setting them back to `None`.

---

## 4. Frontend Implementation

### 4.1 Store: `config.svelte.ts`

**File**: `src/claude_mpm/dashboard-svelte/src/lib/stores/config.svelte.ts`

**Pattern**: Traditional Svelte `writable()` stores, matching the existing `socket.svelte.ts` and `tools.svelte.ts` conventions. Not Svelte 5 runes (only `theme.svelte.ts` uses runes in this codebase).

```typescript
import { writable, get } from 'svelte/store';

// --- Types ---

export interface ProjectSummary {
    agents: { deployed: number; available: number };
    skills: { deployed: number; available: number };
    sources: { agent_sources: number; skill_sources: number };
    deployment_mode: string;
}

export interface DeployedAgent {
    name: string;
    location: string;
    path: string;
    version: string;
    type: string;
    specializations?: string[];
    is_core: boolean;
}

export interface AvailableAgent {
    agent_id: string;
    name: string;
    description: string;
    version: string;
    source: string;
    source_url: string;
    priority: number;
    category: string;
    tags: string[];
    is_deployed: boolean;
}

export interface DeployedSkill {
    name: string;
    path: string;
    description: string;
    category: string;
    collection: string;
    is_user_requested: boolean;
    deploy_mode: 'agent_referenced' | 'user_defined';
    deploy_date: string;
}

export interface AvailableSkill {
    name: string;
    description: string;
    category: string;
    collection: string;
    is_deployed: boolean;
}

export interface ConfigSource {
    id: string;
    type: 'agent' | 'skill';
    url: string;
    subdirectory?: string;
    branch?: string;
    enabled: boolean;
    priority: number;
}

export interface LoadingState {
    summary: boolean;
    deployedAgents: boolean;
    availableAgents: boolean;
    deployedSkills: boolean;
    availableSkills: boolean;
    sources: boolean;
}

export interface ConfigError {
    resource: string;
    message: string;
    timestamp: number;
}

// --- Stores ---

export const projectSummary = writable<ProjectSummary | null>(null);
export const deployedAgents = writable<DeployedAgent[]>([]);
export const availableAgents = writable<AvailableAgent[]>([]);
export const deployedSkills = writable<DeployedSkill[]>([]);
export const availableSkills = writable<AvailableSkill[]>([]);
export const configSources = writable<ConfigSource[]>([]);
export const loading = writable<LoadingState>({
    summary: false,
    deployedAgents: false,
    availableAgents: false,
    deployedSkills: false,
    availableSkills: false,
    sources: false,
});
export const errors = writable<ConfigError[]>([]);

// --- Fetch Functions ---

const API_BASE = '/api/config';

async function fetchJSON(url: string): Promise<any> {
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    const data = await response.json();
    if (!data.success) {
        throw new Error(data.error || 'Unknown error');
    }
    return data;
}

function addError(resource: string, message: string) {
    errors.update(errs => [
        ...errs.slice(-4),  // Keep last 5 errors max
        { resource, message, timestamp: Date.now() },
    ]);
}

export async function fetchProjectSummary() {
    loading.update(l => ({ ...l, summary: true }));
    try {
        const data = await fetchJSON(`${API_BASE}/project/summary`);
        projectSummary.set(data.data);
    } catch (e: any) {
        addError('summary', e.message);
    } finally {
        loading.update(l => ({ ...l, summary: false }));
    }
}

export async function fetchDeployedAgents() {
    loading.update(l => ({ ...l, deployedAgents: true }));
    try {
        const data = await fetchJSON(`${API_BASE}/agents/deployed`);
        deployedAgents.set(data.agents);
    } catch (e: any) {
        addError('deployedAgents', e.message);
    } finally {
        loading.update(l => ({ ...l, deployedAgents: false }));
    }
}

export async function fetchAvailableAgents(search?: string) {
    loading.update(l => ({ ...l, availableAgents: true }));
    try {
        const url = search
            ? `${API_BASE}/agents/available?search=${encodeURIComponent(search)}`
            : `${API_BASE}/agents/available`;
        const data = await fetchJSON(url);
        availableAgents.set(data.agents);
    } catch (e: any) {
        addError('availableAgents', e.message);
    } finally {
        loading.update(l => ({ ...l, availableAgents: false }));
    }
}

export async function fetchDeployedSkills() {
    loading.update(l => ({ ...l, deployedSkills: true }));
    try {
        const data = await fetchJSON(`${API_BASE}/skills/deployed`);
        deployedSkills.set(data.skills);
    } catch (e: any) {
        addError('deployedSkills', e.message);
    } finally {
        loading.update(l => ({ ...l, deployedSkills: false }));
    }
}

export async function fetchAvailableSkills(collection?: string) {
    loading.update(l => ({ ...l, availableSkills: true }));
    try {
        const url = collection
            ? `${API_BASE}/skills/available?collection=${encodeURIComponent(collection)}`
            : `${API_BASE}/skills/available`;
        const data = await fetchJSON(url);
        availableSkills.set(data.skills);
    } catch (e: any) {
        addError('availableSkills', e.message);
    } finally {
        loading.update(l => ({ ...l, availableSkills: false }));
    }
}

export async function fetchSources() {
    loading.update(l => ({ ...l, sources: true }));
    try {
        const data = await fetchJSON(`${API_BASE}/sources`);
        configSources.set(data.sources);
    } catch (e: any) {
        addError('sources', e.message);
    } finally {
        loading.update(l => ({ ...l, sources: false }));
    }
}

/** Fetch all config data. Called when config tab is first opened. */
export async function fetchAllConfig() {
    await Promise.all([
        fetchProjectSummary(),
        fetchDeployedAgents(),
        fetchSources(),
    ]);
    // Defer heavier fetches (these may take 2-5 seconds)
    fetchAvailableAgents();
    fetchDeployedSkills();
    fetchAvailableSkills();
}
```

### 4.2 Adding the "Config" Tab (6 Steps)

All changes are in `src/claude_mpm/dashboard-svelte/src/routes/+page.svelte`.

**Step 1: Extend ViewMode type union**

```typescript
// Line 20 - change from:
type ViewMode = 'events' | 'tools' | 'files' | 'agents' | 'tokens';

// To:
type ViewMode = 'events' | 'tools' | 'files' | 'agents' | 'tokens' | 'config';
```

**Step 2: Add imports at the top of `<script>` block**

```typescript
import ConfigView from '$lib/components/config/ConfigView.svelte';
```

**Step 3: Add button in the tab bar** (after the Agents button, around line 227)

```svelte
<button
    onclick={() => viewMode = 'config'}
    class="tab"
    class:active={viewMode === 'config'}
>
    Config
</button>
```

**Step 4: Add `{:else if}` block in left panel** (around line 262, before `{/if}`)

```svelte
{:else if viewMode === 'config'}
    <ConfigView panelSide="left" />
```

**Step 5: Add `{:else if}` block in right panel** (around line 311, before `{:else}`)

```svelte
{:else if viewMode === 'config'}
    <ConfigView panelSide="right" />
```

Note: `ConfigView` handles both left and right panel rendering internally via the `panelSide` prop, which keeps the `+page.svelte` additions minimal.

**Step 6: Update selection-clearing `$effect`** (around line 109)

Add a new branch:
```typescript
} else if (viewMode === 'config') {
    selectedEvent = null;
    selectedTool = null;
    selectedFile = null;
    selectedAgent = null;
}
```

### 4.3 Component: `ConfigView.svelte`

**File**: `src/claude_mpm/dashboard-svelte/src/lib/components/config/ConfigView.svelte`

**Purpose**: Main container for the Config tab. Renders differently based on `panelSide` prop.

```svelte
<script lang="ts">
    import { onMount } from 'svelte';
    import {
        projectSummary, loading, errors,
        deployedAgents, availableAgents,
        deployedSkills, availableSkills,
        configSources,
        fetchAllConfig,
        type DeployedAgent, type AvailableAgent,
        type DeployedSkill, type AvailableSkill,
        type ConfigSource,
    } from '$lib/stores/config.svelte';
    import AgentsList from './AgentsList.svelte';
    import SkillsList from './SkillsList.svelte';
    import SourcesList from './SourcesList.svelte';

    interface Props {
        panelSide: 'left' | 'right';
    }

    let { panelSide }: Props = $props();

    type ConfigSubTab = 'agents' | 'skills' | 'sources';
    let subTab = $state<ConfigSubTab>('agents');

    // Selected items for detail view in right panel
    let selectedAgent = $state<DeployedAgent | AvailableAgent | null>(null);
    let selectedSkill = $state<DeployedSkill | AvailableSkill | null>(null);
    let selectedSource = $state<ConfigSource | null>(null);

    // Store subscriptions (hybrid Svelte 4/5 pattern)
    let summaryData = $state<...>(null);
    let loadingState = $state<...>({...});
    // ... (subscribe to each store via $effect + .subscribe())

    let hasFetched = false;

    onMount(() => {
        if (!hasFetched) {
            fetchAllConfig();
            hasFetched = true;
        }
    });
</script>
```

**Left Panel Rendering** (`panelSide === 'left'`):
- Summary cards row at top (agent count, skill count, source count)
- Sub-tab bar: Agents | Skills | Sources
- Sub-tab content: renders `AgentsList`, `SkillsList`, or `SourcesList`

**Right Panel Rendering** (`panelSide === 'right'`):
- Detail view for the currently selected item
- Agent detail: full metadata, version, specializations, source info
- Skill detail: description, category, deployment mode, timestamps
- Source detail: URL, priority, enabled status, branch
- Empty state: "Select an item from the list to view details"

### 4.4 Component: `AgentsList.svelte`

**File**: `src/claude_mpm/dashboard-svelte/src/lib/components/config/AgentsList.svelte`

**Purpose**: Two-section collapsible list of deployed and available agents.

**Props**:
```typescript
interface Props {
    deployedAgents: DeployedAgent[];
    availableAgents: AvailableAgent[];
    loading: { deployedAgents: boolean; availableAgents: boolean };
    onSelect: (agent: DeployedAgent | AvailableAgent) => void;
    selectedAgent: DeployedAgent | AvailableAgent | null;
}
```

**State**:
- `deployedExpanded: boolean = true` -- Section collapse toggle
- `availableExpanded: boolean = true` -- Section collapse toggle
- `searchQuery: string = ''` -- Filters both lists by name

**Rendering**:
- Search input at top (uses `SearchInput` shared component)
- "Deployed (N)" section header with chevron toggle
  - Each agent row: name, version badge, model tier badge, "Core" badge if `is_core`
  - Core agents show a lock icon and non-removable indicator
  - Click handler calls `onSelect(agent)`
  - Selected agent highlighted with `bg-cyan-50 dark:bg-cyan-900/20`
- "Available (N)" section header with chevron toggle
  - Each agent row: name, description (truncated to 80 chars), source badge, "Deployed" checkmark if `is_deployed`
  - Click handler calls `onSelect(agent)`
- Loading spinner when data is being fetched
- Empty state when no agents match search

### 4.5 Component: `SkillsList.svelte`

**File**: `src/claude_mpm/dashboard-svelte/src/lib/components/config/SkillsList.svelte`

**Purpose**: Two-section collapsible list of deployed and available skills.

**Props**:
```typescript
interface Props {
    deployedSkills: DeployedSkill[];
    availableSkills: AvailableSkill[];
    loading: { deployedSkills: boolean; availableSkills: boolean };
    onSelect: (skill: DeployedSkill | AvailableSkill) => void;
    selectedSkill: DeployedSkill | AvailableSkill | null;
}
```

**Rendering**:
- Search input at top
- "Deployed (N)" section
  - Each skill row: name, category badge, collection source label
  - Deploy mode label: "Agent Referenced" (blue) or "User Defined" (green)
  - `is_user_requested` indicator
- "Available (N)" section
  - Each skill row: name, category badge, "Deployed" checkmark if `is_deployed`
- Loading spinner, empty state

### 4.6 Component: `SourcesList.svelte`

**File**: `src/claude_mpm/dashboard-svelte/src/lib/components/config/SourcesList.svelte`

**Purpose**: Unified list of agent and skill sources sorted by priority.

**Props**:
```typescript
interface Props {
    sources: ConfigSource[];
    loading: boolean;
    onSelect: (source: ConfigSource) => void;
    selectedSource: ConfigSource | null;
}
```

**Rendering**:
- No search input (sources list is typically small, 2-5 items)
- Each source row:
  - Type badge: "Agent" (purple) or "Skill" (teal)
  - URL (truncated, showing `owner/repo` portion)
  - Priority number with visual indicator (lower = higher precedence, shown with ascending bars)
  - Enabled/disabled toggle indicator (read-only -- just shows state)
  - Disabled sources shown at 50% opacity with "Disabled" label
- Click handler calls `onSelect(source)`

### 4.7 Shared Components

#### `Badge.svelte`

**File**: `src/claude_mpm/dashboard-svelte/src/lib/components/Badge.svelte`

```svelte
<script lang="ts">
    interface Props {
        text: string;
        variant?: 'default' | 'primary' | 'success' | 'warning' | 'danger' | 'info';
        size?: 'sm' | 'md';
    }

    let { text, variant = 'default', size = 'sm' }: Props = $props();

    const variantClasses: Record<string, string> = {
        default: 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300',
        primary: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-200',
        success: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
        warning: 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200',
        danger: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
        info: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
    };

    const sizeClasses: Record<string, string> = {
        sm: 'px-2 py-0.5 text-xs',
        md: 'px-2.5 py-1 text-sm',
    };
</script>

<span class="inline-flex items-center rounded-full font-medium {variantClasses[variant]} {sizeClasses[size]}">
    {text}
</span>
```

#### `SearchInput.svelte`

**File**: `src/claude_mpm/dashboard-svelte/src/lib/components/SearchInput.svelte`

```svelte
<script lang="ts">
    interface Props {
        value: string;
        placeholder?: string;
        onInput: (value: string) => void;
    }

    let { value, placeholder = 'Search...', onInput }: Props = $props();

    let debounceTimer: ReturnType<typeof setTimeout>;

    function handleInput(e: Event) {
        const target = e.target as HTMLInputElement;
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            onInput(target.value);
        }, 200);
    }
</script>

<div class="relative">
    <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" ...>
        <!-- Search icon SVG path -->
    </svg>
    <input
        type="text"
        {value}
        {placeholder}
        oninput={handleInput}
        class="w-full pl-9 pr-3 py-2 text-sm bg-white dark:bg-slate-800
               border border-slate-200 dark:border-slate-700 rounded-md
               text-slate-900 dark:text-slate-100
               placeholder-slate-400 dark:placeholder-slate-500
               focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
    />
</div>
```

### 4.8 Styling Approach

All styling uses the existing Tailwind CSS patterns found in the current dashboard:

| Element | Light Mode | Dark Mode |
|---------|-----------|-----------|
| Background (main) | `bg-slate-50` | `bg-slate-900` |
| Background (panel) | `bg-white` | `bg-slate-800` |
| Text (primary) | `text-slate-900` | `text-slate-100` |
| Text (secondary) | `text-slate-500` | `text-slate-400` |
| Border | `border-slate-200` | `border-slate-700` |
| Active/accent | `bg-cyan-600 text-white` | `bg-cyan-600 text-white` |
| List dividers | `divide-y divide-slate-200` | `divide-y divide-slate-700` |
| Badges | `rounded-full px-2 py-0.5 text-xs font-medium` | (same structure, variant colors) |
| Selected item | `bg-cyan-50` | `bg-cyan-900/20` |
| Hover | `hover:bg-slate-50` | `hover:bg-slate-700/50` |

No custom CSS is needed. Tailwind utility classes only.

---

## 5. Data Flow

End-to-end request flow from user interaction to rendered data.

### 5.1 Initial Load (User clicks "Config" tab)

```
1. User clicks "Config" tab button in +page.svelte
2. viewMode state changes to 'config'
3. $effect clears all other selections (selectedEvent, selectedTool, etc.)
4. Left panel renders <ConfigView panelSide="left" />
5. Right panel renders <ConfigView panelSide="right" />
6. ConfigView.onMount() calls fetchAllConfig()
7. fetchAllConfig() fires 3 parallel requests + 3 deferred requests:

   [PARALLEL - immediate]
   ├── GET /api/config/project/summary
   ├── GET /api/config/agents/deployed
   └── GET /api/config/sources

   [DEFERRED - after parallel completes]
   ├── GET /api/config/agents/available     (may take 2-3s)
   ├── GET /api/config/skills/deployed
   └── GET /api/config/skills/available     (may take 3-5s, network call)

8. Each fetch function:
   a. Sets loading.{resource} = true
   b. Calls fetch() to the Python backend
   c. Vite dev proxy forwards /api/* to localhost:8765
   d. aiohttp handles the request, CORS middleware adds headers
   e. Handler wraps service call in asyncio.to_thread()
   f. Service reads filesystem/network, returns data
   g. Handler returns web.json_response({success: true, ...})
   h. Frontend parses response, updates writable() store
   i. Sets loading.{resource} = false
   j. On error: adds to errors store, shows error message

9. Store updates trigger Svelte reactivity:
   - ConfigView subscribes to stores via $effect + .subscribe()
   - List components receive data as props
   - Summary cards update with counts
   - Loading spinners appear/disappear per resource
```

### 5.2 User Selects an Agent

```
1. User clicks agent row in AgentsList
2. AgentsList calls onSelect(agent)
3. ConfigView updates selectedAgent state
4. Right panel re-renders with agent detail view
5. Detail view shows: name, version, description, specializations, source, path
6. No additional API calls needed (all data already fetched)
```

### 5.3 User Searches Available Agents

```
1. User types in SearchInput
2. 200ms debounce fires onInput callback
3. AgentsList updates searchQuery state
4. Client-side filter: availableAgents.filter(a => a.name.includes(query))
5. List re-renders with filtered results
6. No API call needed (client-side filtering)
```

---

## 6. Testing Plan

### 6.1 Backend: pytest Async Tests

**File**: `tests/test_config_routes.py`

Each endpoint needs at minimum:
- **Happy path**: Service returns data, handler returns 200 with expected schema
- **Service error**: Service raises exception, handler returns 500 with error message
- **Empty state**: Service returns empty list, handler returns 200 with empty array

**Test structure using aiohttp test client**:

```python
import pytest
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
from aiohttp import web
from unittest.mock import patch, MagicMock


class TestConfigRoutes(AioHTTPTestCase):
    async def get_application(self):
        from claude_mpm.services.monitor.config_routes import register_config_routes
        app = web.Application()
        register_config_routes(app)
        return app

    @unittest_run_loop
    async def test_project_summary_success(self):
        with patch('claude_mpm.services.monitor.config_routes._get_agent_manager') as mock:
            mock.return_value.list_agents.return_value = {"agent1": {}, "agent2": {}}
            resp = await self.client.request("GET", "/api/config/project/summary")
            assert resp.status == 200
            data = await resp.json()
            assert data["success"] is True
            assert "agents" in data["data"]

    @unittest_run_loop
    async def test_agents_deployed_success(self):
        ...

    @unittest_run_loop
    async def test_agents_deployed_service_error(self):
        ...

    @unittest_run_loop
    async def test_agents_available_with_search(self):
        ...

    @unittest_run_loop
    async def test_sources_empty_config(self):
        ...
```

**Estimated tests**: 18 tests (3 per endpoint x 6 endpoints).

### 6.2 Frontend: Manual Testing Checklist

No frontend test framework exists in this project. This is accepted tech debt for Phase 1.

**Manual verification checklist**:

- [ ] Config tab appears in navigation bar between "Agents" and the hidden "Tokens" tab
- [ ] Clicking "Config" tab shows the config view in both panels
- [ ] Summary cards show correct counts (cross-reference with CLI: `claude-mpm agents list`, `claude-mpm skills list`)
- [ ] Deployed agents list shows all agents from `.claude/agents/`
- [ ] Core agents (engineer, research, qa, web-qa, documentation, ops, ticketing, mpm-agent-manager, mpm-skills-manager) show "Core" badge
- [ ] Available agents list loads (may take 2-3 seconds)
- [ ] Available agents with `is_deployed: true` show a "Deployed" checkmark
- [ ] Deployed skills list shows all skills from `~/.claude/skills/`
- [ ] Skills show correct deploy_mode: "Agent Referenced" or "User Defined"
- [ ] Available skills list loads (may take 3-5 seconds, network call)
- [ ] Sources list shows both agent and skill sources, sorted by priority
- [ ] Disabled sources appear at reduced opacity
- [ ] Clicking any list item shows its detail in the right panel
- [ ] Search input filters agents and skills by name (client-side)
- [ ] Search input has 200ms debounce (no flickering while typing)
- [ ] Loading spinners appear during data fetch
- [ ] Error messages appear when backend is unreachable
- [ ] Dark mode renders correctly (toggle theme, verify all text is readable)
- [ ] Light mode renders correctly
- [ ] Switching to another tab and back to Config does not re-fetch data
- [ ] Resizing the panel divider works as expected

### 6.3 Integration: Vite Dev Proxy Verification

- [ ] Start Python backend: `claude-mpm dashboard` (runs on port 8765)
- [ ] Start Vite dev server: `cd src/claude_mpm/dashboard-svelte && npm run dev` (runs on port 5173)
- [ ] Open `http://localhost:5173` in browser
- [ ] Verify all `/api/config/*` requests are proxied to 8765
- [ ] Check browser Network tab: no CORS errors
- [ ] Verify Socket.IO connection still works (events still stream)

### 6.4 Production Build Verification

- [ ] Run `npm run build` in dashboard-svelte directory
- [ ] Start `claude-mpm dashboard` (serves built Svelte from Python)
- [ ] Open `http://localhost:8765` in browser
- [ ] Verify Config tab works identically to dev mode

---

## 7. Definition of Done

Phase 1 is complete when ALL of the following are true:

1. **6 API endpoints** respond correctly to GET requests and return valid JSON matching the documented schemas
2. **CORS middleware** is active and Vite dev proxy works without CORS errors
3. **Config tab** appears in the dashboard navigation and renders without errors
4. **Summary cards** display correct counts matching CLI output
5. **Agent lists** (deployed + available) render with correct data, badges, and core agent indicators
6. **Skill lists** (deployed + available) render with correct data and deploy mode labels
7. **Sources list** renders with correct source types, priorities, and enabled/disabled states
8. **Detail view** (right panel) shows full information for any selected item
9. **Search** filters agent and skill lists by name
10. **Loading states** appear during data fetch and disappear when complete
11. **Error states** appear when the backend is unreachable or returns errors
12. **Dark mode** and **light mode** both render correctly
13. **No console errors** in the browser dev tools during normal usage
14. **Backend tests** pass: `pytest tests/test_config_routes.py` (18 tests)
15. **Manual testing checklist** fully completed (Section 6.2)

---

## 8. Devil's Advocate Notes

### DA-1: "6 endpoints may be too many for day 1"

**The concern**: Building all 6 endpoints plus their frontend consumers in 1 day of backend work is ambitious. If any service behaves unexpectedly, debugging eats the schedule.

**Why this approach**: The endpoints are simple GET wrappers around existing services. There are no new business logic, no data transformations beyond flattening/enriching, no mutation operations. The `asyncio.to_thread()` pattern is identical for all 6.

**Fallback**: If running behind, ship with just 3 endpoints on day 1:
1. `/api/config/project/summary` -- Proves the pattern works end-to-end
2. `/api/config/agents/deployed` -- Most critical data for users
3. `/api/config/sources` -- Simplest implementation (reads config files only)

Then add the remaining 3 on day 2 before starting frontend work.

### DA-2: "AgentManager vs AgentDeploymentService gap"

**The concern**: Research Doc 04 references `AgentManager(project_dir=...).list_agents(location="project")`, but there was ambiguity about whether this service exists as documented.

**Verified**: The `AgentManager` class exists at `src/claude_mpm/services/agents/management/agent_management_service.py:39`. Its `list_agents(location)` method is at line 265 and returns `Dict[str, Dict[str, Any]]`. This is the correct service for listing deployed agents.

`AgentDeploymentService` (at `services/agents/deployment/agent_deployment.py:59`) is for deploy/undeploy operations and is NOT needed in Phase 1.

**What could go wrong**: `AgentManager.__init__` takes `framework_dir` and `project_dir` optional params. If `project_dir` defaults to something unexpected (not `Path.cwd()`), the deployed agents list will be empty. Test by checking the returned `path` field against the actual `.claude/agents/` directory.

### DA-3: "100+ agent list may need pagination"

**The concern**: `GitSourceManager.list_cached_agents()` scans `~/.claude-mpm/cache/agents/` and parses YAML/MD frontmatter for each file. With 100+ agents, this takes 2-3 seconds and returns a large JSON payload.

**Why no pagination in Phase 1**: The list is rendered client-side with virtual scrolling not required (100 items in a scrollable div is fine for modern browsers). Pagination adds complexity to both backend (cursor/offset logic) and frontend (pagination controls, state management).

**What could go wrong**: If a user has 500+ agents in cache (unlikely but possible with many sources), the response could be 1MB+ and parsing could take 5+ seconds.

**Fallback**: Add `Cache-Control: private, max-age=60` header (already in the plan). The frontend caches the store data and does not re-fetch on tab switches. If performance is still an issue, add `?limit=100&offset=0` pagination in a fast-follow.

### DA-4: "No frontend tests exist"

**The concern**: Adding 5 new components with no test coverage means regressions will only be caught by manual testing.

**Why this is accepted**: The existing 12 components have zero tests. Introducing a test framework (Vitest/Testing Library) for 5 new components when the other 12 are untested creates an inconsistent codebase. The investment to set up Vitest, configure JSDOM/happy-dom, and write meaningful component tests is estimated at 1-2 days -- which exceeds the Phase 1 budget.

**What could go wrong**: A future refactor breaks the Config tab and nobody notices until a user reports it.

**Mitigation**: The manual testing checklist (Section 6.2) covers all critical paths. A Phase 2 or Phase 3 task should add Vitest with component tests for all dashboard components, not just the config ones.

### DA-5: "The flat component structure may not scale"

**The concern**: Currently all 12 components live in `src/lib/components/` with no subdirectories. Adding 5 more to the flat structure increases cognitive load.

**Why this approach**: Creating a `config/` subdirectory establishes a precedent for feature-based grouping. The shared components (`Badge.svelte`, `SearchInput.svelte`) stay in the root `components/` directory since they are reusable across features.

**What could go wrong**: Other developers may continue adding components to the flat root instead of creating subdirectories for their features. This is a team convention issue, not a technical one.

**Mitigation**: Document the convention in a brief comment in the components directory or in the project's contributing guide.

### DA-6: "Lazy singletons may serve stale data"

**The concern**: If a user modifies config files via CLI while the dashboard is running (e.g., `claude-mpm agents deploy new-agent`), the module-level service singletons in `config_routes.py` will not reflect the changes.

**Why this approach**: Per-request service construction (creating `AgentManager` on every request) would add 200-500ms per request due to filesystem reads in the constructor. For read-only Phase 1, stale data for a few minutes is acceptable.

**Fallback**: Phase 2 should add a singleton invalidation mechanism, either:
- A `/api/config/refresh` endpoint that sets all singletons to `None`
- A file-watcher that detects config file changes and invalidates automatically
- Socket.IO event emission from CLI that the dashboard consumes to trigger refresh

### DA-7: "Skills available endpoint makes network calls"

**The concern**: `SkillsDeployerService.list_available_skills()` downloads the skill manifest from GitHub. This is a 3-5 second blocking network call that could timeout or fail if GitHub is down.

**Why this approach**: There is no local cache of the skill manifest in the current codebase. The service always fetches from GitHub.

**What could go wrong**: GitHub rate limiting (60 requests/hour for unauthenticated), network timeouts, transient failures. Each opens the Config tab and triggers this call.

**Mitigation**:
- `Cache-Control: private, max-age=120` header (2-minute browser cache)
- Frontend: do not re-fetch on tab switches (store already has data)
- Frontend: show "Loading from GitHub..." distinct state vs generic loading spinner
- Error handling: show "Could not load available skills" with a retry button, do not block the rest of the Config tab

---

## 9. Files Created/Modified

### New Files (9 files)

| # | File Path | Type | Purpose |
|---|-----------|------|---------|
| 1 | `src/claude_mpm/services/monitor/config_routes.py` | Python | 6 GET endpoint handlers + route registration |
| 2 | `src/claude_mpm/dashboard-svelte/src/lib/stores/config.svelte.ts` | TypeScript | Config store with types, writable stores, fetch functions |
| 3 | `src/claude_mpm/dashboard-svelte/src/lib/components/config/ConfigView.svelte` | Svelte | Main config tab container (left + right panel) |
| 4 | `src/claude_mpm/dashboard-svelte/src/lib/components/config/AgentsList.svelte` | Svelte | Deployed + available agents list with search |
| 5 | `src/claude_mpm/dashboard-svelte/src/lib/components/config/SkillsList.svelte` | Svelte | Deployed + available skills list with search |
| 6 | `src/claude_mpm/dashboard-svelte/src/lib/components/config/SourcesList.svelte` | Svelte | Unified agent + skill sources list |
| 7 | `src/claude_mpm/dashboard-svelte/src/lib/components/Badge.svelte` | Svelte | Reusable badge component (shared) |
| 8 | `src/claude_mpm/dashboard-svelte/src/lib/components/SearchInput.svelte` | Svelte | Reusable search input with debounce (shared) |
| 9 | `tests/test_config_routes.py` | Python | pytest async tests for all 6 endpoints |

### Modified Files (2 files)

| # | File Path | Change |
|---|-----------|--------|
| 1 | `src/claude_mpm/services/monitor/server.py` | Add CORS middleware; add `register_config_routes()` call in `_setup_http_routes()` |
| 2 | `src/claude_mpm/dashboard-svelte/src/routes/+page.svelte` | Extend ViewMode type, add Config tab button, add `{:else if}` blocks for left/right panels, update selection-clearing `$effect`, add import |

### Files NOT Modified (important boundaries)

- No changes to any service classes (`AgentManager`, `GitSourceManager`, `SkillsDeployerService`, etc.)
- No changes to any config classes (`AgentSourceConfiguration`, `SkillSourceConfiguration`)
- No changes to any existing Svelte stores (`socket.svelte.ts`, `tools.svelte.ts`, etc.)
- No changes to `vite.config.ts` (existing `/api` proxy already covers `/api/config/*`)
- No changes to `package.json` (no new npm dependencies needed)

---

## 10. Estimated Effort Breakdown

### Backend (Day 1) -- 8 hours

| Task | Hours | Notes |
|------|-------|-------|
| Create `config_routes.py` with route registration scaffold | 0.5 | File structure, imports, registration function |
| Add CORS middleware to `server.py` | 0.5 | Middleware function + app configuration |
| Implement `/api/config/project/summary` | 1.0 | Aggregates from multiple services; most complex handler |
| Implement `/api/config/agents/deployed` | 1.0 | AgentManager integration + core agent flagging |
| Implement `/api/config/agents/available` | 1.0 | GitSourceManager + is_deployed cross-reference |
| Implement `/api/config/skills/deployed` | 1.0 | SkillsDeployerService + deployment index enrichment |
| Implement `/api/config/skills/available` | 1.0 | SkillsDeployerService + network call handling |
| Implement `/api/config/sources` | 0.5 | Config file reads only; simplest endpoint |
| Manual endpoint testing with curl | 1.0 | Verify each endpoint returns expected JSON |
| Write pytest async tests | 0.5 | 18 tests with mocked services |

### Frontend (Days 2-3) -- 12 hours

| Task | Hours | Notes |
|------|-------|-------|
| Create `config.svelte.ts` store | 1.5 | Types, stores, fetch functions, error handling |
| Create `Badge.svelte` shared component | 0.5 | Simple component, multiple variants |
| Create `SearchInput.svelte` shared component | 0.5 | Input with debounce and search icon |
| Add Config tab to `+page.svelte` (6 steps) | 1.0 | Type change, button, panels, $effect update |
| Create `ConfigView.svelte` main container | 2.0 | Sub-tab navigation, summary cards, left/right rendering |
| Create `AgentsList.svelte` | 2.0 | Two collapsible sections, search, selection, badges |
| Create `SkillsList.svelte` | 1.5 | Similar to AgentsList but with deploy mode labels |
| Create `SourcesList.svelte` | 1.0 | Simpler list, priority indicators, enabled/disabled |
| Styling pass (dark mode, light mode) | 1.0 | Verify all Tailwind classes work in both modes |
| Manual testing (full checklist) | 1.0 | Section 6.2 verification |
| Integration testing (Vite dev proxy) | 0.5 | Section 6.3 verification |

### Total: 20 hours across 2-3 days

**Buffer**: The 20-hour estimate assumes no service integration surprises. If an `AgentManager` constructor fails due to missing config files in the dev environment, add 1-2 hours for debugging. The fallback plan (DA-1) of shipping 3 endpoints first provides schedule protection.
