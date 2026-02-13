# Phase 0: Overview, Prerequisites & Architecture

> **Configuration Management UI for Claude MPM Dashboard**
>
> Master implementation plan covering architecture, prerequisites, cross-cutting concerns, and phased delivery.
>
> Date: 2026-02-13
> Branch: `ui-agents-skills-config`
> Status: PLANNING

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architecture Overview](#2-architecture-overview)
3. [Technology Decisions](#3-technology-decisions)
4. [Phase Summary](#4-phase-summary)
5. [Critical Prerequisites](#5-critical-prerequisites)
6. [Cross-Cutting Concerns](#6-cross-cutting-concerns)
7. [Known Gaps and Open Questions](#7-known-gaps-and-open-questions)
8. [Architectural Decision Records](#8-architectural-decision-records)
9. [Risk Matrix](#9-risk-matrix)
10. [Success Criteria](#10-success-criteria)
11. [Operations That MUST Remain CLI-Only](#11-operations-that-must-remain-cli-only)

---

## 1. Executive Summary

### What We Are Building

A **Configuration Management** tab in the existing Claude MPM dashboard that allows users to view and manage agents, skills, Git sources, and auto-configure settings. These settings are currently only manageable via CLI commands (`claude-mpm agents deploy`, `claude-mpm skills deploy`, `claude-mpm config`, etc.). The dashboard today is a read-only monitoring tool; this project extends it to support configuration state visibility and, incrementally, safe mutation operations.

### Why

- Users who interact with Claude MPM through the dashboard have no visibility into what agents and skills are deployed, where they come from, or what Git sources are configured.
- CLI-only configuration management creates a context switch that interrupts dashboard-centric workflows.
- Auto-configure recommendations are invisible until a user runs a CLI command and reads terminal output.
- Git source sync status, agent precedence, and skill deployment mode are opaque without CLI inspection.

### Expected Outcomes

| Phase | Outcome | Timeline | Risk |
|-------|---------|----------|------|
| Phase 1 | Read-only visibility into all configuration state | 2-3 days | LOW |
| Phase 2 | Safe mutations: source management, simple config edits | 1-2 weeks | MEDIUM |
| Phase 3 | Deploy/undeploy agents and skills via UI | 2-3 weeks | HIGH |
| Phase 4 | Full feature parity: YAML editor, history, bulk operations | Ongoing | HIGHEST |

### Key Constraint

The existing codebase has **zero file-level locking** for configuration files. The dashboard server runs in a daemon thread alongside CLI processes that read and write the same files. Before any write endpoint is exposed, a `ConfigFileLock` mechanism must be implemented. This is the single most important prerequisite.

---

## 2. Architecture Overview

### 2.1 Current State

```
                     +--------------------------+
                     |   Claude Code Session    |
                     |   (reads .claude/agents/ |
                     |    at startup only)      |
                     +-----------+--------------+
                                 |
                     +-----------v--------------+
                     |   Claude MPM CLI         |
                     |   (reads/writes config   |
                     |    files directly)        |
                     +-----------+--------------+
                                 |
              +------------------v-------------------+
              |        Configuration Files           |
              |  .claude-mpm/configuration.yaml      |
              |  ~/.claude-mpm/config/agent_sources   |
              |  ~/.claude-mpm/config/skill_sources   |
              |  .claude/agents/*.md (deployed)       |
              |  ~/.claude/skills/* (deployed)        |
              +------------------+-------------------+
                                 |
                     +-----------v--------------+
                     |  UnifiedMonitorServer    |
                     |  aiohttp + Socket.IO     |
                     |  Port 8765 (daemon thread)|
                     |  16 read-only routes     |
                     +-----------+--------------+
                                 |
                     +-----------v--------------+
                     |  Svelte 5 SPA Frontend   |
                     |  5 monitoring tabs        |
                     |  (Events, Tools, Files,   |
                     |   Agents, Tokens)         |
                     +--------------------------+
```

**Key characteristics of the current system:**

- `server.py` is 65KB / 1,661 lines, the largest Python file in the project. All 16 routes are inline async closures inside `_setup_http_routes()`.
- No router objects, no middleware chain, no sub-applications.
- No authentication (localhost-only, trusted environment).
- CORS is handled only at the Socket.IO level (`cors_allowed_origins="*"`); no aiohttp CORS middleware exists.
- Services are instantiated inline in handlers or lazy-imported, never pre-initialized or injected.
- The frontend has NO router -- it uses a `ViewMode` type union (`'events' | 'tools' | 'files' | 'agents' | 'tokens'`) with `{#if}` conditional blocks.
- State management is a hybrid of Svelte 4 `writable()`/`derived()` stores and Svelte 5 `$state`/`$effect` runes, bridged via manual `.subscribe()` patterns.

### 2.2 Target State

```
                     +--------------------------+
                     |   Claude Code Session    |
                     +-----------+--------------+
                                 |
                     +-----------v--------------+
                     |   Claude MPM CLI         |
                     +--+--------+-----------+--+
                        |        |           |
                        | (shared file lock) |
                        |        |           |
              +---------v--------v-----------v-----------+
              |        Configuration Files               |
              |  (protected by ConfigFileLock)            |
              +--+------^-----------^---+----------------+
                 |      |           |   |
                 |   +--+-----------+---+--+
                 |   |  config_routes.py   |  <-- NEW: separate module
                 |   |  (lazy singletons)   |
                 |   +---+-----+-----------+
                 |       |     |
              +--v-------v-----v-----------------+
              |  UnifiedMonitorServer            |
              |  + config_routes.py (new module) |
              |  + CORS middleware (new)          |
              |  Port 8765                        |
              +--+-------------------------------+
                 |
              +--v-------------------------------+
              |  Svelte 5 SPA Frontend           |
              |  + "Config" tab (new ViewMode)    |
              |  + configStore (new store)         |
              |  + Shared form components (new)    |
              +----------------------------------+
```

**Key architectural changes:**

1. **New `config_routes.py` module** in `src/claude_mpm/services/monitor/` -- all configuration API routes live here, registered onto the aiohttp app from a single `register_config_routes(app, sio)` function.
2. **`ConfigFileLock` context manager** -- wraps `fcntl.flock()` for advisory file locking on all config read-modify-write operations.
3. **CORS middleware** for aiohttp -- applied globally so the Svelte dev server (Vite proxy) and production builds both work.
4. **New `configStore`** on the frontend -- a Svelte store managing configuration state, following the existing `writable()` + `$effect` bridge pattern.
5. **New `ViewMode` value: `'config'`** -- extends the existing tab navigation.
6. **Socket.IO `config_event` channel** -- separate event type for configuration change notifications, distinct from monitoring events.

### 2.3 Key Architectural Decisions

| Decision | Rationale |
|----------|-----------|
| Separate `config_routes.py` module, not inline in `server.py` | `server.py` is already 65KB. Adding 29 more endpoints inline would make it unmaintainable. A separate module with a single registration function keeps the existing architecture intact. |
| Wrap existing services, do not create new config stores | Research found a critical flaw in a proposed `ConfigService` that would create a disconnected `config.json` file. All API endpoints must use the same config loading paths as the CLI: `AgentSourceConfiguration`, `SkillSourceConfiguration`, and `Config` singleton. |
| Lazy singleton pattern for service instantiation | `AgentDeploymentService` creates 14 sub-services on construction. Per-request instantiation is wasteful. Cache service instances per route group, invalidated on config file changes. |
| `asyncio.to_thread()` for all blocking service calls | 9 of 10 backend services are synchronous/blocking. The dashboard runs in an async event loop. All blocking service calls must be wrapped in `asyncio.to_thread()` to avoid stalling the event loop. |
| Phased rollout starting read-only | The system has zero file locking today. Phase 1 delivers immediate value (visibility) with zero concurrency risk while locking infrastructure is built. |

---

## 3. Technology Decisions

### Backend

| Choice | Rationale | Counter-argument |
|--------|-----------|-----------------|
| **aiohttp** (existing) | The dashboard server is already aiohttp. No migration cost. | FastAPI would give OpenAPI docs and dependency injection. **Rebuttal**: Migration would require rewriting all 16 existing routes and the Socket.IO integration. The cost outweighs the benefit for an internal tool. |
| **Socket.IO** (existing) | Real-time event broadcasting is already working for monitoring. Config change events fit the same pattern. | WebSockets without Socket.IO would be lighter. **Rebuttal**: Socket.IO auto-reconnect, room management, and the existing client integration make it the clear choice. |
| **`fcntl.flock()`** for file locking | Advisory locking is sufficient for CLI + dashboard coordination on the same machine. Cross-platform is not needed (macOS/Linux only). | Database-backed locking (SQLite WAL) would be more robust. **Rebuttal**: Introduces a new dependency and complexity for a problem that advisory file locks solve for the single-machine use case. |
| **`asyncio.to_thread()`** for sync services | Standard library, no dependencies. Moves blocking I/O to the default thread pool executor. | Could refactor services to be natively async. **Rebuttal**: 9 services with hundreds of methods would need rewriting. `to_thread()` wrapping is incremental, safe, and preserves the CLI's synchronous usage. |

### Frontend

| Choice | Rationale | Counter-argument |
|--------|-----------|-----------------|
| **Svelte 5 with runes** (existing) | Consistency with the existing dashboard. No migration. | React or Vue would have larger ecosystems for form components. **Rebuttal**: The dashboard is already Svelte 5. Introducing a second framework would double the build complexity and bundle size. |
| **Tailwind CSS v3** (existing) | All existing components use Tailwind. Dual class dark mode pattern (`dark:bg-*`) is established. | A component library (shadcn-svelte, Skeleton) would provide pre-built form components. **Rebuttal**: Adding a component library introduces version compatibility risk. The needed form components (inputs, selects, toggles, modals) are small and benefit from matching the existing aesthetic. |
| **No router** (existing pattern) | The SPA uses `ViewMode` type union with `{#if}` blocks. Adding a router would require rewriting all existing tab navigation. | SvelteKit routing would give URL-based navigation. **Rebuttal**: URL-based routing adds complexity (history management, deep linking, state restoration) that is not needed for a local developer tool. The `ViewMode` pattern works. |
| **`writable()` stores with `$effect` bridge** | Matches the existing `socketStore` pattern exactly. Config data can be consumed identically to monitoring data. | Pure Svelte 5 runes (class-based stores) would be cleaner. **Rebuttal**: Would create two incompatible store patterns in the same app. Consistency with existing stores is more important than purity. Only `themeStore` uses the runes-only pattern. |

---

## 4. Phase Summary

### Phase 1: Read-Only Configuration Dashboard

| Attribute | Value |
|-----------|-------|
| **Risk Level** | LOW |
| **Timeline** | 2-3 days |
| **Prerequisites** | server.py modularization, CORS middleware |
| **File Locking Required** | No (read-only) |

**Deliverables:**
- 6 GET endpoints under `/api/config/`
- 1 new Svelte component (`ConfigView.svelte`) with sub-panels
- New `configStore` for frontend state
- `config` tab in dashboard navigation

**Endpoints:**
```
GET /api/config/overview       -- configuration.yaml contents (file + effective values)
GET /api/config/agents         -- deployed agents list with metadata
GET /api/config/skills         -- deployed skills list with mode info
GET /api/config/sources        -- agent + skill source repositories
GET /api/config/validate       -- validation results (errors + warnings)
GET /api/config/toolchain      -- toolchain detection results
```

---

### Phase 2: Safe Mutations -- Source Management & Simple Config

| Attribute | Value |
|-----------|-------|
| **Risk Level** | MEDIUM |
| **Timeline** | 1-2 weeks |
| **Prerequisites** | ConfigFileLock, file mtime polling, Socket.IO config events |
| **File Locking Required** | Yes |

**Deliverables:**
- 8 mutation endpoints (source CRUD, sync trigger, config settings)
- File locking on all write paths
- Socket.IO `config_event` broadcasting
- "Config changed externally" detection via mtime polling
- Confirmation dialogs for destructive operations

**Endpoints (new):**
```
POST   /api/config/sources/agent           -- add agent source
POST   /api/config/sources/skill           -- add skill source
DELETE /api/config/sources/{type}/{id}     -- remove source
PATCH  /api/config/sources/{type}/{id}     -- toggle enabled, update priority
POST   /api/config/sources/{type}/{id}/sync -- sync single source (202 async)
POST   /api/config/sources/sync-all        -- sync all sources (202 async)
GET    /api/config/sources/sync-status     -- current sync status
PATCH  /api/config/settings                -- update simple settings
```

---

### Phase 3: Deployment Operations

| Attribute | Value |
|-----------|-------|
| **Risk Level** | HIGH |
| **Timeline** | 2-3 weeks |
| **Prerequisites** | Backup/restore in deployment pipeline, operation journal, impact analysis, undo capability |
| **File Locking Required** | Yes |

**Deliverables:**
- Agent deploy/undeploy endpoints
- Skill deploy/undeploy endpoints
- Skill deployment mode switching
- Auto-configure wizard (detect, preview, apply)
- Diff preview before every destructive operation
- "Restart Claude Code required" banner
- Backup/restore cycle for all deploy operations

**Endpoints (new):**
```
POST   /api/config/agents/deploy             -- deploy agent from cache
DELETE /api/config/agents/{agent_name}        -- undeploy agent
POST   /api/config/agents/deploy-collection   -- deploy agent collection
GET    /api/config/agents/collections         -- list available collections
POST   /api/config/skills/deploy             -- deploy skill from cache
DELETE /api/config/skills/{skill_name}        -- undeploy skill
PUT    /api/config/skills/deployment-mode     -- switch skill mode
POST   /api/config/auto-configure/detect      -- detect toolchain
POST   /api/config/auto-configure/preview     -- preview recommendations
POST   /api/config/auto-configure/apply       -- apply recommendations (202)
```

---

### Phase 4: Full Feature Parity

| Attribute | Value |
|-----------|-------|
| **Risk Level** | HIGHEST |
| **Timeline** | Ongoing |
| **Prerequisites** | Audit log, config history/versioning, comprehensive test suite, load testing |

**Deliverables:**
- Direct YAML editor with syntax validation and diff preview
- Configuration history and restore
- Bulk operations (multi-agent/skill deploy/undeploy)
- Import/export configuration
- Pagination for large datasets (200+ agents/skills)
- Agent/skill detail views with full metadata

---

## 5. Critical Prerequisites

These MUST be completed before Phase 1 begins. They form the infrastructure foundation for all subsequent work.

### 5.1 ConfigFileLock Implementation

**Why**: The codebase has zero file-level locking. `AgentSourceConfiguration.save()` uses plain `open("w")` + `yaml.safe_dump()`. `SkillSourceConfiguration.save()` uses temp-file + rename (atomic write, but no read-modify-write lock). With both CLI and dashboard writing the same files, lost updates are guaranteed under concurrent use.

**Approach**: Advisory file locking via `fcntl.flock()` with a sidecar `.lock` file.

**File**: `src/claude_mpm/core/config_file_lock.py`

```python
import fcntl
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

class ConfigFileLockError(Exception):
    """Raised when a config file lock cannot be acquired."""
    pass

@contextmanager
def config_file_lock(
    path: Path,
    timeout: float = 2.0,
    poll_interval: float = 0.05,
):
    """
    Advisory file lock for config read-modify-write operations.

    Uses fcntl.flock() with a sidecar .lock file. The lock is exclusive
    (LOCK_EX) and non-blocking (LOCK_NB) with a polling retry loop.

    Args:
        path: The config file path to lock (lock file is path.lock)
        timeout: Maximum seconds to wait for lock acquisition
        poll_interval: Seconds between retry attempts

    Raises:
        ConfigFileLockError: If lock cannot be acquired within timeout

    Usage:
        with config_file_lock(Path("~/.claude-mpm/config/agent_sources.yaml")):
            data = yaml.safe_load(open(path))
            data["repositories"].append(new_repo)
            with open(path, "w") as f:
                yaml.safe_dump(data, f)
    """
    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_file = open(lock_path, "w")
    deadline = time.monotonic() + timeout

    try:
        while True:
            try:
                fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break  # Lock acquired
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise ConfigFileLockError(
                        f"Cannot acquire lock on {path} after {timeout}s. "
                        f"Another process may be modifying this file."
                    )
                time.sleep(poll_interval)
        yield
    finally:
        fcntl.flock(lock_file, fcntl.LOCK_UN)
        lock_file.close()
```

**Counter-argument**: "Advisory locks are not enforced by the OS -- the CLI will ignore them." **Rebuttal**: True, but the CLI must also be updated to use `ConfigFileLock` in its write paths. This is a single-machine system; advisory locks work when all writers cooperate. The alternative (mandatory file locking) is not portable and not supported by YAML serializers.

**Integration points** (where locks must be applied):
- `AgentSourceConfiguration.save()` at `src/claude_mpm/config/agent_sources.py:126-191`
- `SkillSourceConfiguration.save()` at `src/claude_mpm/config/skill_sources.py:299-370`
- `SkillSourceConfiguration.add_source()` at `src/claude_mpm/config/skill_sources.py:372-401`
- `SkillSourceConfiguration.remove_source()`
- `SkillSourceConfiguration.update_source()`
- All new API write handlers in `config_routes.py`
- `configuration.yaml` write operations via `Config` singleton

### 5.2 server.py Modularization

**Why**: `server.py` is 65KB / 1,661 lines. All routes are inline closures inside `_setup_http_routes()`. Adding 29 more endpoints inline would push it past 100KB and make it unmaintainable.

**Approach**: Extract a new `config_routes.py` module with a single registration function.

**File**: `src/claude_mpm/services/monitor/config_routes.py`

**Registration pattern** (follows the existing inline closure pattern but in a separate file):

```python
# config_routes.py

from aiohttp import web
import asyncio
from typing import Optional
import socketio

def register_config_routes(
    app: web.Application,
    sio: Optional[socketio.AsyncServer] = None,
) -> None:
    """Register all /api/config/* routes on the aiohttp application."""

    # -- Service singletons (lazy initialization) --
    _services = {}

    def _get_service(name: str):
        """Lazy singleton for expensive service instances."""
        if name not in _services:
            if name == "agent_deployment":
                from claude_mpm.services.agents.deployment.agent_deployment import (
                    AgentDeploymentService,
                )
                _services[name] = AgentDeploymentService()
            # ... other services
        return _services[name]

    # -- Route handlers --

    async def config_overview_handler(request: web.Request) -> web.Response:
        """GET /api/config/overview"""
        try:
            result = await asyncio.to_thread(_load_config_overview)
            return web.json_response({"success": True, **result})
        except Exception as e:
            return web.json_response(
                {"success": False, "error": str(e), "code": "SERVICE_ERROR"},
                status=500,
            )

    # ... more handlers ...

    # -- Route registration --
    app.router.add_get("/api/config/overview", config_overview_handler)
    app.router.add_get("/api/config/agents", config_agents_handler)
    # ... more routes ...
```

**Integration in `server.py`**:

```python
# In UnifiedMonitorServer._setup_http_routes(), at the end:
from claude_mpm.services.monitor.config_routes import register_config_routes
register_config_routes(self.app, self.sio)
```

**Counter-argument**: "We could use aiohttp sub-applications for better isolation." **Rebuttal**: Sub-applications change the URL routing behavior and middleware stack. The existing server has no sub-apps. Introducing one creates an inconsistency. A plain module with a registration function is simpler and matches the existing pattern.

### 5.3 CORS Middleware

**Why**: CORS is currently handled only at the Socket.IO level (`cors_allowed_origins="*"`). There is no aiohttp-level CORS middleware. The Svelte dev server (Vite, port 5173) proxies API requests, but production builds served from the same origin do not need CORS. However, during development, direct browser requests to `/api/config/*` endpoints will fail without CORS headers.

**Approach**: Use `aiohttp-cors` package for middleware-level CORS.

```python
# In server.py setup:
import aiohttp_cors

cors = aiohttp_cors.setup(self.app, defaults={
    "*": aiohttp_cors.ResourceOptions(
        allow_credentials=True,
        expose_headers="*",
        allow_headers="*",
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    )
})

# After all routes are registered:
for route in list(self.app.router.routes()):
    cors.add(route)
```

**Counter-argument**: "The Vite proxy handles CORS during development, and production is same-origin. We do not need CORS middleware." **Rebuttal**: This is true for the current setup, but breaks when (a) the dashboard is accessed from a different port during debugging, (b) future integrations need cross-origin access, or (c) error responses bypass the Vite proxy. The middleware is ~10 lines of code and eliminates an entire class of debugging headaches.

**Alternative**: If adding a dependency is undesirable, a simpler approach adds CORS headers via a middleware function:

```python
@web.middleware
async def cors_middleware(request, handler):
    if request.method == "OPTIONS":
        response = web.Response()
    else:
        response = await handler(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response
```

### 5.4 Frontend Infrastructure -- Shared Components Foundation

**Why**: The existing frontend has NO shared form components. No modals, no toasts, no validation patterns, no checkboxes, no toggles. The only reusable component is `CopyButton.svelte`. Configuration management requires forms (inputs, selects, confirmation dialogs) that do not exist today.

**Approach**: Build a minimal shared component library before Phase 1.

**Files to create** in `src/claude_mpm/dashboard-svelte/src/lib/components/shared/`:

| Component | Purpose | Phase Needed |
|-----------|---------|-------------|
| `StatusBadge.svelte` | Green/yellow/red status indicators | Phase 1 |
| `LoadingSpinner.svelte` | Consistent loading state | Phase 1 |
| `EmptyState.svelte` | Standardized empty state pattern | Phase 1 |
| `ConfirmDialog.svelte` | Modal confirmation for destructive ops | Phase 2 |
| `Toast.svelte` | Non-blocking success/error notifications | Phase 2 |
| `FormInput.svelte` | Text input with validation and error display | Phase 2 |
| `FormSelect.svelte` | Dropdown with validation | Phase 2 |
| `Toggle.svelte` | Boolean toggle switch | Phase 2 |

**For Phase 1**, only `StatusBadge`, `LoadingSpinner`, and `EmptyState` are needed. The form components are built as prerequisites for Phase 2.

**Counter-argument**: "Just use inline Tailwind classes like the existing components." **Rebuttal**: The existing monitoring components are read-only displays. Configuration management has forms, validation, confirmation flows, and error states that repeat across every entity type (agents, skills, sources). Without shared components, every form input will have its own inconsistent validation pattern, error display, and dark-mode styling.

---

## 6. Cross-Cutting Concerns

These patterns apply to ALL phases and must be followed consistently.

### 6.1 Async Safety Pattern

**Rule**: Every blocking service call must be wrapped in `asyncio.to_thread()`.

**Blocking services** (9 of 10):
1. `AgentDeploymentService` -- filesystem I/O, network I/O (git sync), subprocess calls
2. `SkillsDeployerService` -- filesystem I/O, git operations
3. `GitSourceManager` -- network I/O (HTTP requests, git operations), 30s timeouts
4. `ToolchainAnalyzerService` -- filesystem scanning, 5-min TTL cache
5. `Config` singleton -- YAML file I/O
6. `ConfigurationService` -- wraps `Config`, same I/O characteristics
7. `SkillsConfig` -- JSON file I/O
8. `SkillToAgentMapper` -- filesystem scanning on initialization
9. `AgentSourceConfiguration` / `SkillSourceConfiguration` -- YAML file I/O

**Only natively async service**: `AutoConfigManagerService`

**Pattern**:

```python
# In config_routes.py handler:
async def config_agents_handler(request: web.Request) -> web.Response:
    try:
        result = await asyncio.to_thread(_list_deployed_agents)
        return web.json_response({"success": True, "agents": result})
    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        return web.json_response(
            {"success": False, "error": str(e), "code": "SERVICE_ERROR"},
            status=500,
        )

def _list_deployed_agents() -> list:
    """Synchronous function run in thread pool."""
    service = AgentDeploymentService()
    # ... blocking calls here
    return agents
```

**Counter-argument**: "The thread pool adds overhead. Just call synchronous functions directly." **Rebuttal**: Calling a blocking function from an async handler stalls the entire event loop. The `AgentDeploymentService` constructor alone creates 14 sub-services and reads filesystem. A single blocking call can freeze the dashboard for seconds, killing Socket.IO heartbeats and causing client disconnects.

### 6.2 Error Handling Strategy

**Consistent error response format** (must match existing patterns in `server.py`):

```json
{
    "success": false,
    "error": "Human-readable error message",
    "code": "ERROR_CODE",
    "details": {}
}
```

**Error codes** (standardized across all config endpoints):

| Code | HTTP Status | When |
|------|-------------|------|
| `NOT_FOUND` | 404 | Agent, skill, or source not found |
| `VALIDATION_ERROR` | 400 | Invalid input (bad URL, out-of-range priority, etc.) |
| `CONFLICT` | 409 | Duplicate source, agent already deployed |
| `SYNC_IN_PROGRESS` | 409 | Sync operation already running for this source |
| `SYNC_FAILED` | 500 | Sync operation failed |
| `DEPLOY_FAILED` | 500 | Deployment operation failed |
| `LOCK_TIMEOUT` | 503 | Could not acquire `ConfigFileLock` within timeout |
| `SERVICE_ERROR` | 500 | Unexpected internal error |

**Frontend error handling pattern** (replaces `alert()` anti-pattern found in research):

```typescript
// In configStore -- centralized error handling
function handleApiError(response: any, context: string): void {
    if (!response.success) {
        errorState.set({
            message: response.error,
            code: response.code,
            context: context,
            timestamp: Date.now(),
        });
    }
}
```

Errors display via a toast notification component, not `alert()` dialogs.

### 6.3 Testing Strategy

#### Unit Tests (Python)

**Framework**: `pytest` + `pytest-asyncio`

| Scope | What to Test | Example |
|-------|-------------|---------|
| `ConfigFileLock` | Lock acquisition, timeout, contention | Two threads contending for same lock file |
| `config_routes.py` handlers | Response format, error codes, service delegation | Mock services, verify JSON response structure |
| Validation logic | Input validation for each endpoint | Invalid URLs, out-of-range priorities, empty names |

**File**: `tests/test_config_routes.py`, `tests/test_config_file_lock.py`

#### Integration Tests (Python)

| Scope | What to Test | Example |
|-------|-------------|---------|
| End-to-end API | HTTP request -> service call -> response | `aiohttp.test_utils.TestClient` against real routes |
| File locking | Concurrent API calls to same config file | Two simultaneous POST requests to add sources |
| Socket.IO events | Config changes emit correct events | Connect Socket.IO client, trigger mutation, verify event |

#### Frontend Tests

| Scope | What to Test | Example |
|-------|-------------|---------|
| Store logic | `configStore` data transformation | Mock fetch, verify store state updates |
| Component rendering | `ConfigView` renders agent list correctly | Vitest + `@testing-library/svelte` |

#### End-to-End Tests (deferred to Phase 3)

Full browser tests (Playwright) for critical workflows: view config, add source, sync, deploy agent.

### 6.4 File Tracking and Git Workflow

**New files by phase:**

```
Phase 0 (Prerequisites):
  src/claude_mpm/core/config_file_lock.py              -- ConfigFileLock
  src/claude_mpm/services/monitor/config_routes.py     -- Route module
  src/claude_mpm/dashboard-svelte/src/lib/components/shared/StatusBadge.svelte
  src/claude_mpm/dashboard-svelte/src/lib/components/shared/LoadingSpinner.svelte
  src/claude_mpm/dashboard-svelte/src/lib/components/shared/EmptyState.svelte
  tests/test_config_file_lock.py

Phase 1 (Read-Only):
  src/claude_mpm/dashboard-svelte/src/lib/stores/config.svelte.ts
  src/claude_mpm/dashboard-svelte/src/lib/components/ConfigView.svelte
  src/claude_mpm/dashboard-svelte/src/lib/types/config.ts
  tests/test_config_routes.py

Phase 2 (Safe Mutations):
  src/claude_mpm/dashboard-svelte/src/lib/components/shared/ConfirmDialog.svelte
  src/claude_mpm/dashboard-svelte/src/lib/components/shared/Toast.svelte
  src/claude_mpm/dashboard-svelte/src/lib/components/shared/FormInput.svelte
  src/claude_mpm/dashboard-svelte/src/lib/components/shared/Toggle.svelte
  tests/test_config_routes_mutations.py
```

**Modified files:**

```
Phase 0:
  src/claude_mpm/services/monitor/server.py            -- import + register config routes, add CORS middleware
  src/claude_mpm/config/agent_sources.py               -- add ConfigFileLock to save()
  src/claude_mpm/config/skill_sources.py               -- add ConfigFileLock to save()/add_source()/etc.

Phase 1:
  src/claude_mpm/dashboard-svelte/src/routes/+page.svelte  -- add 'config' to ViewMode, add tab, add panel
  src/claude_mpm/dashboard-svelte/src/lib/types/events.ts  -- extend ViewMode type (if defined here)
```

**Git workflow**: Feature branch `ui-agents-skills-config` (current). Each phase is a PR sequence. Prerequisites land first as their own PR(s).

### 6.5 Socket.IO Event Architecture for Config Changes

**New event type**: `config_event` (distinct from existing `hook_event`, `tool_event`, etc.)

**Event subtypes:**

| Subtype | Trigger | Phase |
|---------|---------|-------|
| `config_updated` | Any config file mutation | Phase 2 |
| `source_added` | New Git source registered | Phase 2 |
| `source_removed` | Git source removed | Phase 2 |
| `source_updated` | Git source enabled/disabled/priority changed | Phase 2 |
| `sync_started` | Sync operation begins | Phase 2 |
| `sync_progress` | Sync operation progress update | Phase 2 |
| `sync_completed` | Sync operation finished | Phase 2 |
| `sync_failed` | Sync operation failed | Phase 2 |
| `agent_deployed` | Agent deployed to project | Phase 3 |
| `agent_undeployed` | Agent removed from project | Phase 3 |
| `skill_deployed` | Skill deployed | Phase 3 |
| `skill_undeployed` | Skill removed | Phase 3 |

**Event payload structure** (consistent with existing monitoring events):

```json
{
    "type": "config_event",
    "subtype": "source_added",
    "data": {
        "source_type": "agent",
        "source_id": "owner/repo/agents",
        "url": "https://github.com/owner/repo"
    },
    "timestamp": "2026-02-13T10:30:00.000Z"
}
```

**Frontend handling**: The `configStore` subscribes to `config_event` via the Socket.IO connection and refreshes affected data automatically. This prevents the "stale dashboard" problem (Risk ST-1) for same-session changes. For cross-session changes (CLI modifying files), file mtime polling (5-second interval) detects external modifications and triggers a refresh.

---

## 7. Known Gaps and Open Questions

These are unresolved issues from research that need investigation or decisions before or during implementation.

### 7.1 Service Name Discrepancy: AgentManager vs AgentDeploymentService

**Gap**: The backend API specification (Doc 04) references `AgentManager` for `list_agents()` and `read_agent()` operations. The service layer catalog (Doc 01) only documents `AgentDeploymentService`. The file `agent_management_service.py` is mentioned but not cataloged.

**Action**: Verify whether `AgentManager` exists as a separate service or is an alias/wrapper. Check `src/claude_mpm/services/agents/` for the actual class name and method signatures before implementing the deployed agents list endpoint.

**Impact**: Phase 1 (agents list endpoint). Must be resolved before implementation begins.

### 7.2 Source Identifiers Contain Slashes -- URL Path Parameter Problem

**Gap**: Agent source identifiers are formatted as `owner/repo/subdirectory` (e.g., `bobmatnyc/claude-mpm-agents/agents`). This breaks URL path parameters: `DELETE /api/config/sources/agent/bobmatnyc/claude-mpm-agents/agents` would be parsed as 3 path segments.

**Options**:
1. URL-encode the identifier: `bobmatnyc%2Fclaude-mpm-agents%2Fagents` (ugly but correct)
2. Use query parameter instead: `DELETE /api/config/sources/agent?id=bobmatnyc/claude-mpm-agents/agents`
3. Use request body for DELETE (non-standard but avoids the issue)
4. Create a separate short ID (hash-based) for URL purposes

**Recommended**: Option 2 (query parameter) for Phase 2. It is the simplest approach that avoids encoding issues. Revisit with short IDs if the API surface grows.

**Impact**: Phase 2 (source CRUD endpoints).

### 7.3 ETag Computation Method Unspecified

**Gap**: The risk assessment recommends optimistic concurrency via ETag/version tracking, but the existing services have no version tracking mechanism. No config file contains a version field. There is no method to compute ETags from file content.

**Recommended approach**: Use file modification time (`os.path.getmtime()`) as the concurrency token for Phase 1-2. Include `Last-Modified` headers in GET responses. For write operations, accept an `If-Unmodified-Since` header and reject if the file has been modified since the client last read it. Full ETag support (content hash) is deferred to Phase 3.

**Impact**: Phase 2 (concurrency safety for mutations).

### 7.4 Socket.IO Config Events vs Monitoring Events -- Handler Separation

**Gap**: The existing Socket.IO event categorization (`_categorize_event` at server.py:371) has 8 event categories for monitoring. Config events need a separate handling path that does not pollute monitoring event streams.

**Action**: Config events should use a separate event name (`config_event`) rather than being injected into the existing event categories. The frontend `configStore` listens for `config_event` independently of the monitoring `socketStore`.

**Impact**: Phase 1 (event architecture). Must be decided before Socket.IO integration.

### 7.5 YAML Corruption Recovery

**Gap**: The devil's advocate analysis notes that YAML corruption recovery is not addressed. If a partial write corrupts `configuration.yaml` or `agent_sources.yaml`, the system has no recovery mechanism beyond manual editing.

**Recommended**: Before every write operation, create a timestamped backup (e.g., `agent_sources.yaml.bak.1707820200`). Keep the last 3 backups. If a write fails or the YAML becomes unparseable, offer a "Restore from backup" action. This is a Phase 2 deliverable.

**Impact**: Phase 2 (write safety).

### 7.6 GitHub URL Validation Inconsistency

**Gap**: `skill_sources.py` validates that URLs must be `https://github.com/*`. `agent_sources.py` does NOT enforce this validation. The API layer needs consistent validation.

**Action**: Apply GitHub URL validation in the API layer for both agent and skill sources, regardless of whether the underlying service enforces it.

**Impact**: Phase 2 (source creation endpoints).

### 7.7 Pagination Design for Large Datasets

**Gap**: The API specification does not include pagination. With 200+ agents and 78+ skills, list endpoints will return large payloads.

**Recommended**: Add optional `?limit=50&offset=0` query parameters to all list endpoints. Default to returning all results (backward compatible). Add `total` field to all list responses. Cursor-based pagination is deferred to Phase 4 when performance data is available.

**Impact**: Phase 1 (list endpoints should include pagination support from the start).

---

## 8. Architectural Decision Records

### ADR-001: Separate config_routes.py vs Inline in server.py

| Field | Value |
|-------|-------|
| **Status** | DECIDED |
| **Decision** | Create a new `config_routes.py` module with a `register_config_routes(app, sio)` function |
| **Context** | `server.py` is 65KB / 1,661 lines. All existing routes are inline closures. Adding 29 config endpoints inline would push it past 100KB. |
| **Rationale** | Separate module keeps `server.py` unchanged except for a 2-line import + call. New routes are testable in isolation. The registration function pattern is compatible with the existing route setup. |
| **Counter-argument** | Inconsistency: existing routes are inline, new routes are in a module. **Rebuttal**: This is an improvement, not a regression. Future route groups (if any) can follow the same pattern. The inline pattern does not scale. |
| **Consequences** | `config_routes.py` becomes the template for future route modularization. Testing can import and test route handlers directly. |

### ADR-002: ETag vs File mtime for Concurrency Control

| Field | Value |
|-------|-------|
| **Status** | RECOMMENDED (pending Phase 2 implementation) |
| **Decision** | Use file modification time (`os.path.getmtime()`) for Phase 1-2. Implement content-hash ETags in Phase 3+. |
| **Context** | The risk assessment recommends optimistic concurrency. Full ETag implementation requires computing content hashes and managing them across 10 config file paths. File mtime is simpler and covers the primary use case (detecting external modifications). |
| **Rationale** | File mtime covers ~90% of concurrency issues with ~10% of the implementation effort. ETags add value when multiple clients edit the same resource simultaneously, which is a Phase 3+ concern. |
| **Counter-argument** | "File mtime has 1-second resolution on some filesystems and can miss rapid consecutive writes." **Rebuttal**: Config file modifications are human-initiated, not automated. Sub-second resolution is not needed. If it becomes a problem, mtime + file size provides a cheap composite key. |
| **Consequences** | GET responses include `Last-Modified` header from Phase 1. Write operations accept `If-Unmodified-Since` from Phase 2. Full ETags are a Phase 3 upgrade. |

### ADR-003: 29 Endpoints vs Phased Rollout

| Field | Value |
|-------|-------|
| **Status** | DECIDED |
| **Decision** | Start with 6 GET endpoints in Phase 1. Add 8 mutation endpoints in Phase 2. Add remaining in Phase 3-4. |
| **Context** | The API specification defines 29 endpoints across 6 groups. Building all 29 before any are usable would take 4-6 weeks and delay all user value. |
| **Rationale** | Phase 1's 6 GET endpoints deliver immediate value (visibility) with zero risk. Each subsequent phase adds endpoints only after their safety prerequisites are met. |
| **Counter-argument** | "Designing all 29 endpoints upfront ensures API consistency." **Rebuttal**: The full API spec is designed (Doc 04). We are not changing the design, only the implementation order. Phasing reduces risk without sacrificing design coherence. |
| **Consequences** | Frontend must gracefully handle missing endpoints (show "coming soon" or hide unavailable actions). API versioning is not needed since all endpoints are new. |

### ADR-004: Service Instantiation Strategy

| Field | Value |
|-------|-------|
| **Status** | RECOMMENDED (pending Phase 1 implementation) |
| **Decision** | Lazy singleton per route group, cached in a module-level dict, invalidated on config file change detection. |
| **Context** | `AgentDeploymentService` creates 14 sub-services on construction. `GitSourceManager` builds cached metadata. Per-request instantiation wastes CPU and memory. |
| **Rationale** | A lazy singleton avoids construction cost on every request. Invalidation on config file change ensures the singleton does not serve stale state. The dict-based approach is simple and thread-safe for single-writer scenarios (the GIL protects dict assignment). |
| **Counter-argument** | "Singletons make testing harder and can hide stale state." **Rebuttal**: The alternative (per-request instantiation) is a known performance problem. Singletons with explicit invalidation are testable (clear the dict in test setup). Stale state is addressed by mtime-based invalidation. |
| **Consequences** | Service instances persist across requests. Memory usage is higher but bounded. Config changes trigger invalidation. Tests must clear the singleton cache in `setUp`. |

### ADR-005: Pagination Strategy

| Field | Value |
|-------|-------|
| **Status** | RECOMMENDED (implement from Phase 1) |
| **Decision** | Offset-based pagination (`?limit=50&offset=0`) for Phase 1-3. Cursor-based pagination if needed in Phase 4. |
| **Context** | The API specification has no pagination. The devil's advocate analysis flags that 200+ agents/skills lists need pagination. |
| **Rationale** | Offset-based pagination is simple, familiar, and sufficient for datasets under 1,000 items. All list responses already include a `total` field. Adding `limit` and `offset` query parameters is backward-compatible (defaults return all items). |
| **Counter-argument** | "Cursor-based pagination is more efficient for large, changing datasets." **Rebuttal**: Config data changes slowly (user-initiated, not real-time). Offset pagination is adequate. Cursor-based adds complexity (generating opaque cursor tokens, handling invalidation) that is not justified until Phase 4. |
| **Consequences** | All list endpoints accept `limit` and `offset` from Phase 1. Default behavior (no params) returns all items for backward compatibility. |

### ADR-006: Frontend Component Architecture

| Field | Value |
|-------|-------|
| **Status** | RECOMMENDED |
| **Decision** | 3 shared components for Phase 1 (`StatusBadge`, `LoadingSpinner`, `EmptyState`). 1 main config component (`ConfigView.svelte`) with internal sub-panels. Expand to 5-6 shared components for Phase 2 (add form components). |
| **Context** | The frontend has NO shared components except `CopyButton.svelte`. The research proposed 14 components, which the devil's advocate flagged as too many for initial scope. |
| **Rationale** | Phase 1 is read-only, requiring only display components. A single `ConfigView.svelte` with internal `{#if}` blocks for sub-panels (agents, skills, sources, overview) matches the existing pattern in other views (e.g., `FilesView` handles both list and tree). Shared form components are built just-in-time for Phase 2. |
| **Counter-argument** | "A monolithic `ConfigView.svelte` will become unwieldy." **Rebuttal**: If it grows beyond ~500 lines, extract sub-components (e.g., `ConfigAgentsPanel.svelte`, `ConfigSourcesPanel.svelte`). Starting monolithic and extracting is cheaper than designing a component hierarchy prematurely. The existing `+page.svelte` is already large and works. |
| **Consequences** | Phase 1 has 4 new Svelte files. Phase 2 adds 4-5 more (form components + sub-panels if ConfigView grows). Total new components stays under 10 through Phase 2. |

---

## 9. Risk Matrix

Consolidated from the risk assessment (Doc 05), including cross-team findings.

### Risk Severity / Likelihood Matrix

```
                           LIKELIHOOD
                  Low         Medium        High
           +------------+------------+------------+
  Critical |            |            | C-5        |
           +------------+------------+------------+
  High     |            | C-4, O-1   | C-1, ST-1  |
           |            | O-2, C-6   | O-3, UX-1  |
  SEVERITY |            | C-7        |            |
           +------------+------------+------------+
  Medium   | P-3, C-8   | C-3, ST-2  | UX-2, UX-3 |
           |            | ST-3, P-2  | O-5        |
           +------------+------------+------------+
  Low      | O-6        | P-1        |            |
           +------------+------------+------------+
```

### Top Risks by Phase

#### Must Address Before Phase 1

| ID | Risk | Severity | Mitigation | Effort |
|----|------|----------|------------|--------|
| C-5 | No file locking in codebase | Critical | Implement `ConfigFileLock` context manager | 1 day |

**Note**: C-5 is not technically needed for Phase 1 (read-only), but must be completed before Phase 2. Building it in Phase 0 keeps the critical path clear.

#### Must Address Before Phase 2

| ID | Risk | Severity | Mitigation | Effort |
|----|------|----------|------------|--------|
| C-1 | Concurrent CLI + UI config changes | Critical/High | `ConfigFileLock` + file mtime checking | 2 days |
| C-4 | Deploy during active Claude Code session | High | "Restart Required" banner | 1 day |
| ST-1 | Dashboard shows stale config | High | File mtime polling (5s interval) | 4 hours |
| C-6 | Env vars silently override config files | High | Show effective vs file values; flag overrides | 4 hours |
| C-7 | Dual config systems drift | High | Use same config path as CLI; flag discrepancies | 1 day |
| UX-2 | Mode switching data loss | High | Pre-populate `user_defined` from `agent_referenced` | 2 hours |

#### Must Address Before Phase 3

| ID | Risk | Severity | Mitigation | Effort |
|----|------|----------|------------|--------|
| O-2 | Deploy partially writes files | High | Backup-deploy-verify cycle | 2 days |
| O-3 | Auto-configure overwrites manual customizations | High | Diff preview + confirmation + undo | 2 days |
| O-1 | Git sync fails midway -- no rollback | High | Per-source status reporting, individual retry | 4 hours |
| C-2 | Race conditions between config file operations | High | `ConfigFileLock` on all mutating methods | 1 day |

#### Address in Phase 3-4

| ID | Risk | Severity | Mitigation | Effort |
|----|------|----------|------------|--------|
| C-3 | Multiple browser tabs | Medium | Socket.IO broadcast of operation state | 4 hours |
| ST-2 | Socket.IO reconnect state loss | Medium | Fetch state on reconnect | 4 hours |
| P-1 | Large agent lists performance | Low-Medium | Pagination + metadata caching | 1 day |
| P-2 | Git sync timeout | Medium | Async sync with task queue | 1 day |
| ST-3 | Server restart mid-operation | Medium | Operation journal | 2 days |

---

## 10. Success Criteria

### Phase 0 (Prerequisites) -- Complete

- [ ] `ConfigFileLock` context manager passes unit tests (lock acquisition, timeout, contention)
- [ ] `config_routes.py` module exists with `register_config_routes()` function
- [ ] At least 1 test route (e.g., `/api/config/health`) responds correctly
- [ ] CORS middleware is active and verified (OPTIONS preflight returns correct headers)
- [ ] `StatusBadge.svelte`, `LoadingSpinner.svelte`, `EmptyState.svelte` exist and render in dark/light modes
- [ ] `server.py` imports and registers config routes without errors
- [ ] All existing 16 routes continue to function (regression check)

### Phase 1 (Read-Only) -- Complete

- [ ] All 6 GET endpoints return correct data matching CLI output
- [ ] `configuration.yaml` overview shows both file values and effective runtime values
- [ ] Environment variable overrides are flagged in the overview display
- [ ] Agents list shows deployed agents with name, version, source, description
- [ ] Skills list shows deployed skills with deployment mode (`agent_referenced` vs `user_defined`)
- [ ] Sources list shows all agent and skill repositories with enabled/disabled state
- [ ] Validation endpoint returns errors and warnings matching `claude-mpm config validate`
- [ ] Toolchain detection shows detected languages, frameworks, and confidence scores
- [ ] `Config` tab appears in dashboard navigation and renders correctly in dark/light modes
- [ ] Data loads within 2 seconds on a project with 50 agents and 25 skills
- [ ] `Last-Modified` headers are present on all GET responses
- [ ] Optional `limit`/`offset` pagination works on list endpoints

### Phase 2 (Safe Mutations) -- Complete

- [ ] All mutation endpoints are wrapped in `ConfigFileLock`
- [ ] Adding a Git source via UI writes to the correct YAML file and appears in source list
- [ ] Removing a Git source shows a confirmation dialog before proceeding
- [ ] Source sync triggers async operation with real-time Socket.IO progress
- [ ] Config changes from CLI are detected within 5 seconds and dashboard refreshes
- [ ] Multiple browser tabs receive config change events via Socket.IO
- [ ] Write operations return `LOCK_TIMEOUT` (503) if another operation holds the lock
- [ ] "Config changed externally" banner appears when files change outside the dashboard
- [ ] No data loss when source is added/removed/toggled concurrently from CLI and UI

### Phase 3 (Deployment Operations) -- Complete

- [ ] Agent deploy creates the correct `.md` file in `.claude/agents/`
- [ ] Agent undeploy removes the file and shows "Restart Claude Code required" banner
- [ ] Core agents (7: engineer, research, qa, web-qa, documentation, ops, ticketing) cannot be undeployed
- [ ] Skill mode switch pre-populates `user_defined` with current `agent_referenced` skills
- [ ] Auto-configure preview shows diff: what will be added, removed, archived
- [ ] Every deploy operation is preceded by automatic backup
- [ ] Backup can be restored via UI "Undo" action
- [ ] No more than 1 concurrent deploy operation is allowed

### Phase 4 (Full Feature Parity) -- Complete

- [ ] YAML editor validates syntax before save
- [ ] Configuration history shows last 10 changes with timestamps
- [ ] Bulk deploy/undeploy works for up to 20 agents simultaneously
- [ ] All list endpoints perform well with 200+ items (under 3 seconds)
- [ ] All endpoints have corresponding test coverage (80%+ line coverage for config_routes.py)

---

## 11. Operations That MUST Remain CLI-Only

These operations have characteristics that make them unsuitable for a web UI, regardless of phase.

| Operation | CLI Command | Why CLI-Only |
|-----------|------------|--------------|
| **Project initialization** | `claude-mpm init` | Creates directory structures, generates initial config files, sets up hooks. Too many filesystem side effects and interactive prompts. |
| **Hook installation/removal** | `claude-mpm hooks install` | Modifies `.claude/hooks/` directory, requires shell access to validate paths. |
| **OAuth setup** | `claude-mpm auth setup` | Interactive browser-based OAuth flow. Requires redirect URI handling that does not work in an embedded dashboard. |
| **Session management** | `claude-mpm session pause/resume` | Tied to terminal context (stdin/stdout). Sessions are per-terminal, not per-browser-tab. |
| **Global config migration** | `claude-mpm config migrate` | One-time operations that modify config schema versions. Should be deliberate, not accidental via UI. |
| **Package management** | `pip install`, `uv add` | Dependency installation should never be triggered from a monitoring dashboard. |

**Rationale**: These operations either require interactive terminal access, have irreversible side effects best controlled by explicit command-line invocation, or operate at a system level that is inappropriate for a browser-based tool. The dashboard should show the _result_ of these operations (e.g., "Hooks are installed: yes/no") but not trigger them.

---

## Appendix A: Reference Documents

| Document | Path | Purpose |
|----------|------|---------|
| Service Layer API Catalog | `docs/research/ui-for-claude-mpm-configuration-management/01-service-layer-api-catalog.md` | Complete method-by-method reference for all 10 backend services |
| Data Models & Business Rules | `docs/research/ui-for-claude-mpm-configuration-management/02-data-models-business-rules.md` | Configuration schemas, Pydantic models, 15 business rules |
| Frontend Architecture & UX Guide | `docs/research/ui-for-claude-mpm-configuration-management/03-frontend-architecture-ux-guide.md` | Svelte 5 component tree, store patterns, styling system |
| Backend API Specification | `docs/research/ui-for-claude-mpm-configuration-management/04-backend-api-specification.md` | 29 endpoint specifications with request/response formats |
| Risk Assessment & Devil's Advocate | `docs/research/ui-for-claude-mpm-configuration-management/05-risk-assessment-devils-advocate.md` | 21 risks, mitigation strategies, implementation sequence |

## Appendix B: Business Rules Quick Reference

These business rules (from Doc 02) affect API validation and UI behavior across all phases.

| ID | Rule | Affects |
|----|------|---------|
| BR-01 | 7 core agents cannot be undeployed: engineer, research, qa, web-qa, documentation, ops, ticketing | Phase 3: agent removal |
| BR-02 | Agent ID must be unique across all sources | Phase 2: source management |
| BR-03 | `user_defined` skills override `agent_referenced` when non-empty | Phase 3: skill mode switching |
| BR-04 | Priority range 0-1000; lower number = higher precedence | Phase 2: source priority editing |
| BR-05 | Required fields per entity type (name, url for sources; name for agents) | All phases: validation |
| BR-06 | Semver required for agent versions (auto-correction supported) | Phase 1: display; Phase 3: deploy |
| BR-07 | Limits: name 1-50 chars, description 10-200, tokens 1K-200K, temperature 0.0-1.0 | Phase 3: agent/skill editing |
| BR-08 | Naming: kebab-case for agents, PascalCase for tools | Phase 3: validation |
| BR-09 | 10 distinct file path conventions across project and user directories | All phases: path resolution |
| BR-10 | No file locking; last-write-wins (current state -- to be mitigated) | Phase 0: prerequisite |
| BR-11 | Default collection cannot be removed or disabled | Phase 2: source management |
| BR-12 | Model normalization: 12 model IDs mapped to 3 tiers | Phase 1: display |
| BR-13 | Agent precedence modes: STRICT, OVERRIDE, MERGE | Phase 1: display; Phase 3: deploy |
| BR-14 | Skill auto-population from agent frontmatter | Phase 1: display |
| BR-15 | Environment variables (`CLAUDE_MPM_` prefix) override config file values | Phase 1: config overview display |

## Appendix C: Comparable Tools and Lessons

| Tool | Pattern Adopted | Why |
|------|----------------|-----|
| **Terraform Cloud** | Serialized write operations via queue; diff preview before apply | Prevents concurrent modification; user sees impact before committing |
| **ArgoCD** | Git as source of truth; "Sync" as the primary mutation verb | Claude MPM already uses git-based sources. Sync is the natural primary action for Phase 2. |
| **Backstage (Spotify)** | Read-only software catalog with rich browsing/search | Phase 1 is literally this pattern: a catalog of agents and skills with metadata browsing. |
| **Portainer** | Confirmation dialogs for every destructive operation; audit logging | Non-negotiable for Phase 2+ mutation operations. Every delete/deploy shows a confirmation dialog. |

---

**End of Phase 0 Overview Document**

Next documents in this series:
- `01-phase-1-read-only-dashboard.md` -- Detailed implementation plan for Phase 1
- `02-phase-2-safe-mutations.md` -- Detailed implementation plan for Phase 2
- `03-phase-3-deployment-operations.md` -- Detailed implementation plan for Phase 3
- `04-phase-4-full-feature-parity.md` -- Detailed implementation plan for Phase 4
