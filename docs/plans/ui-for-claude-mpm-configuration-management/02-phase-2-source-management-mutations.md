# Phase 2: Source Management & Safe Mutations

## Implementation Plan for Claude MPM Dashboard Configuration UI

**Date**: 2026-02-13
**Phase**: 2 of 5
**Branch**: `ui-agents-skills-config`
**Timeline**: 1-2 weeks (7-10 working days)
**Risk Level**: MEDIUM -- introduces file writes, concurrency concerns
**Dependencies**: Phase 1 must be complete (read-only views working)

---

## 1. Phase Summary

Phase 2 introduces **mutation operations** to the configuration dashboard. Users will be able to:

- Add, edit, remove, enable/disable Git sources for both agents and skills
- Trigger Git sync (single source or all) with real-time progress
- View sync status and handle external configuration changes

This is the **first phase that writes to config files**, which means the primary engineering challenge is preventing data corruption from concurrent writes (CLI + UI, multiple browser tabs, external editor).

**What ships at the end of Phase 2:**
- `ConfigFileLock` context manager for safe file-level locking
- 7 new REST endpoints for source CRUD and sync operations
- Socket.IO `config_event` infrastructure for real-time UI updates
- File mtime polling for external change detection
- 4 new shared Svelte components (Modal, Toast, Badge, ProgressBar)
- 3 new config-specific components (SourceForm, SyncProgress, updated SourcesList)
- Config store with mutation functions and optimistic UI

**What does NOT ship in Phase 2:**
- Agent/skill deployment mutations (Phase 3)
- Auto-configure (Phase 4)
- Settings editor (Phase 5)

---

## 2. Prerequisites

### 2.1 ConfigFileLock Implementation (Critical Path)

The entire codebase has **zero file locking** for configuration writes. Verified by scanning all of `src/claude_mpm/services/` -- the only locks found are thread-level locks in the event bus singleton. This must be built before any mutation endpoint can be implemented.

**File**: `src/claude_mpm/core/config_file_lock.py` (new)

```python
"""Advisory file locking for configuration file mutations.

Uses fcntl.flock() for POSIX advisory locking. This prevents concurrent
writes from CLI + UI, multiple browser tabs, or external tools.

Design decisions:
- POSIX advisory locks (fcntl.flock), not mandatory locks
- Separate .lock file (not locking the config file itself)
- 5-second timeout with non-blocking retry loop
- Context manager pattern for exception-safe usage
- Per-file granularity (lock agent_sources.yaml independently from skill_sources.yaml)

Limitations:
- POSIX-only (macOS, Linux). Not Windows-compatible.
- Advisory locks require all writers to cooperate (CLI must also use this)
- NFS file systems may not support flock reliably
"""

import fcntl
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from claude_mpm.core.logging_config import get_logger

logger = get_logger(__name__)


class ConfigFileLockError(Exception):
    """Raised when a config file lock cannot be acquired."""
    pass


class ConfigFileLockTimeout(ConfigFileLockError):
    """Raised when lock acquisition times out."""
    pass


@contextmanager
def config_file_lock(
    config_path: Path,
    timeout: float = 5.0,
    poll_interval: float = 0.1,
) -> Generator[None, None, None]:
    """Acquire an advisory file lock on a configuration file.

    Args:
        config_path: Path to the config file being modified.
                     The lock file will be created at config_path.with_suffix('.lock').
        timeout: Maximum seconds to wait for lock acquisition.
                 Default 5.0s -- fail fast, don't block the UI.
        poll_interval: Seconds between lock retry attempts.

    Yields:
        None -- the lock is held for the duration of the with block.

    Raises:
        ConfigFileLockTimeout: If lock cannot be acquired within timeout.
        ConfigFileLockError: If lock file cannot be created or other I/O error.

    Usage:
        with config_file_lock(Path("~/.claude-mpm/config/agent_sources.yaml")):
            config = AgentSourceConfiguration.load()
            config.add_repository(repo)
            config.save()
    """
    lock_path = config_path.with_suffix(config_path.suffix + ".lock")

    # Ensure parent directory exists (config file may not exist yet)
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    lock_fd = None
    start_time = time.monotonic()

    try:
        # Open (or create) the lock file
        lock_fd = open(lock_path, "w")

        # Retry loop with timeout
        while True:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                logger.debug(f"Lock acquired: {lock_path}")
                break
            except (IOError, OSError):
                elapsed = time.monotonic() - start_time
                if elapsed >= timeout:
                    raise ConfigFileLockTimeout(
                        f"Could not acquire lock on {config_path} "
                        f"after {timeout}s. Another process may be "
                        f"modifying this file."
                    )
                time.sleep(poll_interval)

        # Write PID to lock file for debugging stale locks
        lock_fd.seek(0)
        lock_fd.truncate()
        lock_fd.write(f"{os.getpid()}\n")
        lock_fd.flush()

        yield

    except ConfigFileLockError:
        raise
    except Exception as e:
        raise ConfigFileLockError(
            f"Error managing lock for {config_path}: {e}"
        ) from e
    finally:
        if lock_fd is not None:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
                lock_fd.close()
                logger.debug(f"Lock released: {lock_path}")
            except Exception:
                pass  # Best effort cleanup


def get_config_file_mtime(config_path: Path) -> float:
    """Get the modification time of a config file.

    Returns 0.0 if the file does not exist.
    Used for external change detection (mtime polling).

    Args:
        config_path: Path to the configuration file.

    Returns:
        File modification time as a float (seconds since epoch),
        or 0.0 if file does not exist.
    """
    try:
        return config_path.stat().st_mtime
    except FileNotFoundError:
        return 0.0
```

**Required import to add**: `import os` at the top of the file.

**Integration points:**
1. Wrap `AgentSourceConfiguration.load()` + mutation + `.save()` cycles
2. Wrap `SkillSourceConfiguration.load()` + mutation + `.save()` cycles
3. Wrap `configuration.yaml` read-modify-write cycles (Phase 5, but infrastructure built now)

**Testing requirements for ConfigFileLock:**
- Unit test: acquire lock, verify lock file exists, release, verify cleanup
- Unit test: second lock attempt within timeout raises `ConfigFileLockTimeout`
- Unit test: lock released on exception inside with block
- Stress test: 10 concurrent processes attempting to lock the same file -- exactly 1 succeeds at a time
- Edge test: lock on non-existent file's parent directory (should create it)
- Edge test: stale lock file from crashed process (flock is automatically released on fd close/process death)

---

### 2.2 Socket.IO Config Event Infrastructure

**File**: `src/claude_mpm/services/monitor/handlers/config_handler.py` (new)

A lightweight handler for emitting configuration change events via Socket.IO. Separated from the monitoring event handlers to avoid polluting the event store.

```python
"""Socket.IO event handler for configuration changes.

Emits config_event events for:
- Source CRUD operations (add, update, remove)
- Sync progress and completion
- External config file changes (detected by mtime polling)

Event schema:
{
    "type": "config_event",
    "operation": str,        # "source_added", "source_removed", "sync_progress", etc.
    "entity_type": str,      # "agent_source", "skill_source", "config"
    "entity_id": str | None, # Source ID or None for global events
    "status": str,           # "started", "progress", "completed", "failed"
    "data": dict,            # Operation-specific payload
    "timestamp": str         # ISO 8601
}
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from claude_mpm.core.logging_config import get_logger

logger = get_logger(__name__)


class ConfigEventHandler:
    """Handles emission of config_event Socket.IO events."""

    def __init__(self, sio):
        """Initialize with Socket.IO server instance.

        Args:
            sio: socketio.AsyncServer instance from UnifiedMonitorServer.
        """
        self.sio = sio

    async def emit_config_event(
        self,
        operation: str,
        entity_type: str,
        status: str,
        entity_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit a config_event to all connected clients.

        Args:
            operation: What happened (e.g., "source_added", "sync_progress")
            entity_type: What was affected ("agent_source", "skill_source")
            status: Current state ("started", "progress", "completed", "failed")
            entity_id: Optional identifier of the specific entity
            data: Optional additional payload
        """
        event = {
            "type": "config_event",
            "operation": operation,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "status": status,
            "data": data or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            await self.sio.emit("config_event", event)
            logger.debug(f"Config event emitted: {operation}/{entity_type}/{status}")
        except Exception as e:
            logger.error(f"Failed to emit config event: {e}")
```

**Registration** in `server.py`:
```python
# In UnifiedMonitorServer.__init__ or _setup_http_routes:
from claude_mpm.services.monitor.handlers.config_handler import ConfigEventHandler
self.config_event_handler = ConfigEventHandler(self.sio)
```

---

### 2.3 File Mtime Polling for External Change Detection

**File**: Added to `src/claude_mpm/services/monitor/handlers/config_handler.py`

```python
class ConfigFileWatcher:
    """Polls config files for external modification (mtime changes).

    Runs as an asyncio background task. When a config file's mtime changes
    (from CLI, editor, or another process), emits a config_event so the
    frontend can refresh.

    Watched files:
    - ~/.claude-mpm/config/agent_sources.yaml
    - ~/.claude-mpm/config/skill_sources.yaml
    - ~/.claude-mpm/configuration.yaml (or project-level equivalent)

    Poll interval: 5 seconds.
    """

    def __init__(self, config_event_handler: ConfigEventHandler):
        self.handler = config_event_handler
        self.poll_interval = 5.0
        self._mtimes: Dict[str, float] = {}
        self._task: Optional[asyncio.Task] = None
        self._watched_files = self._get_watched_files()

    def _get_watched_files(self) -> list:
        """Return list of config file paths to watch."""
        home = Path.home()
        return [
            home / ".claude-mpm" / "config" / "agent_sources.yaml",
            home / ".claude-mpm" / "config" / "skill_sources.yaml",
            home / ".claude-mpm" / "configuration.yaml",
        ]

    def start(self) -> None:
        """Start the mtime polling loop as a background task."""
        # Initialize mtimes
        for f in self._watched_files:
            self._mtimes[str(f)] = get_config_file_mtime(f)
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("Config file watcher started")

    async def stop(self) -> None:
        """Stop the polling loop."""
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            logger.info("Config file watcher stopped")

    async def _poll_loop(self) -> None:
        """Main polling loop -- checks mtimes every poll_interval seconds."""
        while True:
            await asyncio.sleep(self.poll_interval)
            for file_path in self._watched_files:
                key = str(file_path)
                current_mtime = get_config_file_mtime(file_path)
                previous_mtime = self._mtimes.get(key, 0.0)

                if current_mtime > previous_mtime and previous_mtime > 0.0:
                    # File was modified externally
                    entity_type = self._classify_file(file_path)
                    await self.handler.emit_config_event(
                        operation="external_change",
                        entity_type=entity_type,
                        status="completed",
                        data={
                            "file": str(file_path),
                            "previous_mtime": previous_mtime,
                            "current_mtime": current_mtime,
                        },
                    )
                    logger.info(f"External change detected: {file_path}")

                self._mtimes[key] = current_mtime

    def update_mtime(self, config_path: Path) -> None:
        """Update stored mtime after a known write (prevents false alerts).

        Call this after the API writes to a config file so the watcher
        doesn't treat our own write as an external change.

        Args:
            config_path: Path to the file that was just written.
        """
        key = str(config_path)
        self._mtimes[key] = get_config_file_mtime(config_path)

    @staticmethod
    def _classify_file(file_path: Path) -> str:
        """Classify a config file path into an entity_type string."""
        name = file_path.name
        if "agent_sources" in name:
            return "agent_source"
        elif "skill_sources" in name:
            return "skill_source"
        else:
            return "config"
```

---

## 3. Backend Implementation

All endpoints follow the existing `_setup_http_routes()` pattern in `server.py`: inline async handler functions registered via `self.app.router.add_*()`, returning `web.json_response()`.

**New file**: `src/claude_mpm/services/monitor/routes/config_sources.py`

This file exports a `register_source_routes(app, sio, config_event_handler, config_file_watcher)` function that registers all source management routes on the aiohttp app.

### 3.1 POST `/api/config/sources/agent` -- Add Agent Source

**Handler signature:**
```python
async def add_agent_source(request: web.Request) -> web.Response:
```

**Request body (JSON):**
```json
{
    "url": "https://github.com/owner/repo",
    "subdirectory": "agents",
    "priority": 200,
    "enabled": true
}
```

| Field | Type | Required | Default | Validation |
|-------|------|----------|---------|------------|
| `url` | string | Yes | -- | Must match `^https://github\.com/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+/?$` |
| `subdirectory` | string | No | `null` | Must be relative path (no leading `/`), no `..` traversal |
| `priority` | integer | No | `500` | Range: 0-1000 |
| `enabled` | boolean | No | `true` | -- |

**Service calls:**
```python
# Inside asyncio.to_thread() since load/save are blocking I/O
def _add_agent_source(url, subdirectory, priority, enabled):
    config_path = Path.home() / ".claude-mpm" / "config" / "agent_sources.yaml"

    with config_file_lock(config_path):
        config = AgentSourceConfiguration.load(config_path)

        repo = GitRepository(
            url=url,
            subdirectory=subdirectory,
            enabled=enabled,
            priority=priority,
        )

        # Uniqueness check
        for existing in config.repositories:
            if existing.identifier == repo.identifier:
                raise ValueError(f"Source '{repo.identifier}' already exists")

        config.add_repository(repo)
        config.save(config_path)

    return repo
```

**Success response (201 Created):**
```json
{
    "success": true,
    "message": "Agent source added: owner/repo/agents",
    "source": {
        "identifier": "owner/repo/agents",
        "url": "https://github.com/owner/repo",
        "subdirectory": "agents",
        "priority": 200,
        "enabled": true
    }
}
```

**Error responses:**

| Status | Code | Condition |
|--------|------|-----------|
| 400 | `VALIDATION_ERROR` | URL doesn't match GitHub pattern, priority out of range, subdirectory has `..` |
| 409 | `CONFLICT` | Source with same identifier already exists |
| 423 | `LOCK_TIMEOUT` | Could not acquire file lock within 5 seconds |
| 500 | `SERVICE_ERROR` | Unexpected I/O or YAML error |

```json
{
    "success": false,
    "error": "Source 'owner/repo/agents' already exists",
    "code": "CONFLICT"
}
```

**Socket.IO event emitted:**
```json
{
    "type": "config_event",
    "operation": "source_added",
    "entity_type": "agent_source",
    "entity_id": "owner/repo/agents",
    "status": "completed",
    "data": {
        "url": "https://github.com/owner/repo",
        "priority": 200
    },
    "timestamp": "2026-02-13T10:30:00.000Z"
}
```

**Post-emit:** Call `config_file_watcher.update_mtime(config_path)` to prevent false external-change alerts.

---

### 3.2 POST `/api/config/sources/skill` -- Add Skill Source

**Handler signature:**
```python
async def add_skill_source(request: web.Request) -> web.Response:
```

**Request body (JSON):**
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

| Field | Type | Required | Default | Validation |
|-------|------|----------|---------|------------|
| `id` | string | No | Auto-generated from URL (`owner-skills`) | Must match `^[a-zA-Z0-9][a-zA-Z0-9_-]*$` |
| `url` | string | Yes | -- | Must match `^https://github\.com/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+/?$` |
| `branch` | string | No | `"main"` | Non-empty string |
| `priority` | integer | No | `100` | Range: 0-1000 |
| `enabled` | boolean | No | `true` | -- |
| `token` | string | No | `null` | If starts with `$`, treated as env var reference; otherwise direct token |

**NOTE**: `type` is always `"git"` -- the only supported source type. Do not accept it as user input; set it server-side.

**Service calls:**
```python
def _add_skill_source(id, url, branch, priority, enabled, token):
    config_path = Path.home() / ".claude-mpm" / "config" / "skill_sources.yaml"

    with config_file_lock(config_path):
        ssc = SkillSourceConfiguration(config_path)
        source = SkillSource(
            id=id,
            type="git",
            url=url,
            branch=branch,
            priority=priority,
            enabled=enabled,
            token=token,
        )
        # Validates and checks ID uniqueness internally
        ssc.add_source(source)
        # add_source calls save() internally (load -> append -> save)

    return source
```

**Success response (201 Created):**
```json
{
    "success": true,
    "message": "Skill source added: custom-skills",
    "source": {
        "id": "custom-skills",
        "type": "git",
        "url": "https://github.com/owner/skills",
        "branch": "main",
        "priority": 200,
        "enabled": true
    }
}
```

**Note**: The `token` field is **never** returned in API responses. Tokens are write-only from the UI perspective.

**Error responses:**

| Status | Code | Condition |
|--------|------|-----------|
| 400 | `VALIDATION_ERROR` | Invalid ID format, invalid URL, bad branch, priority out of range |
| 409 | `CONFLICT` | Source with ID already exists |
| 423 | `LOCK_TIMEOUT` | Could not acquire file lock within 5 seconds |
| 500 | `SERVICE_ERROR` | Unexpected error |

---

### 3.3 DELETE `/api/config/sources/{type}` -- Remove Source

**URL encoding concern**: Source IDs like `bobmatnyc/claude-mpm-agents/agents` contain slashes, which break URL path parameters. **Solution**: Use a query parameter for the source ID instead of a path segment.

**Actual endpoint**: `DELETE /api/config/sources/{type}?id={source_id}`

**Handler signature:**
```python
async def remove_source(request: web.Request) -> web.Response:
```

**Path parameters:**

| Param | Type | Validation |
|-------|------|------------|
| `type` | string | Must be `"agent"` or `"skill"` |

**Query parameters:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Source identifier (URL-encoded if contains special chars) |

**Business rules:**
- **BR-11**: Default/system sources cannot be removed. For skill sources, check if the source is one of the defaults (`system`, `anthropic-official`). For agent sources, check if it's the default repository (`bobmatnyc/claude-mpm-agents/agents`).
- Pre-check: warn if removing this source would orphan deployed agents/skills. The response includes an `orphaned_items` array.

**Service calls:**
```python
def _remove_agent_source(identifier):
    config_path = Path.home() / ".claude-mpm" / "config" / "agent_sources.yaml"

    with config_file_lock(config_path):
        config = AgentSourceConfiguration.load(config_path)
        removed = config.remove_repository(identifier)
        if not removed:
            raise ValueError(f"Source '{identifier}' not found")
        config.save(config_path)


def _remove_skill_source(source_id):
    config_path = Path.home() / ".claude-mpm" / "config" / "skill_sources.yaml"

    with config_file_lock(config_path):
        ssc = SkillSourceConfiguration(config_path)
        removed = ssc.remove_source(source_id)
        if not removed:
            raise ValueError(f"Source '{source_id}' not found")
        # remove_source calls save() internally
```

**Success response (200 OK):**
```json
{
    "success": true,
    "message": "Source 'custom-skills' removed",
    "orphaned_items": []
}
```

**Error responses:**

| Status | Code | Condition |
|--------|------|-----------|
| 400 | `VALIDATION_ERROR` | `type` is not `"agent"` or `"skill"`, or `id` query param missing |
| 403 | `PROTECTED_SOURCE` | Attempting to remove a default/system source (BR-11) |
| 404 | `NOT_FOUND` | Source with given ID not found |
| 423 | `LOCK_TIMEOUT` | Could not acquire file lock |

```json
{
    "success": false,
    "error": "Cannot remove default source 'system'. Default sources are protected.",
    "code": "PROTECTED_SOURCE"
}
```

---

### 3.4 PATCH `/api/config/sources/{type}` -- Update Source

**Actual endpoint**: `PATCH /api/config/sources/{type}?id={source_id}`

Same query-parameter approach as DELETE for the source ID.

**Handler signature:**
```python
async def update_source(request: web.Request) -> web.Response:
```

**Request body (JSON):**
```json
{
    "enabled": false,
    "priority": 50
}
```

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `enabled` | boolean | No | -- |
| `priority` | integer | No | Range: 0-1000 (BR-04) |

**Business rules:**
- **BR-11**: Default/system sources cannot be disabled. Priority CAN be changed on system sources.
- **BR-04**: Priority must be in 0-1000 range.

**Service calls (agent):**
```python
def _update_agent_source(identifier, enabled=None, priority=None):
    config_path = Path.home() / ".claude-mpm" / "config" / "agent_sources.yaml"

    with config_file_lock(config_path):
        config = AgentSourceConfiguration.load(config_path)

        target = None
        for repo in config.repositories:
            if repo.identifier == identifier:
                target = repo
                break

        if target is None:
            raise ValueError(f"Source '{identifier}' not found")

        if enabled is not None:
            target.enabled = enabled
        if priority is not None:
            target.priority = priority

        config.save(config_path)

    return target
```

**Service calls (skill):**
```python
def _update_skill_source(source_id, enabled=None, priority=None):
    config_path = Path.home() / ".claude-mpm" / "config" / "skill_sources.yaml"

    with config_file_lock(config_path):
        ssc = SkillSourceConfiguration(config_path)
        sources = ssc.load()

        target = None
        for source in sources:
            if source.id == source_id:
                target = source
                break

        if target is None:
            raise ValueError(f"Source '{source_id}' not found")

        if enabled is not None:
            target.enabled = enabled
        if priority is not None:
            target.priority = priority

        ssc.save(sources)

    return target
```

**Success response (200 OK):**
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

**Error responses:**

| Status | Code | Condition |
|--------|------|-----------|
| 400 | `VALIDATION_ERROR` | Priority out of range, no updateable fields provided |
| 403 | `PROTECTED_SOURCE` | Attempting to disable a default source (BR-11) |
| 404 | `NOT_FOUND` | Source not found |
| 423 | `LOCK_TIMEOUT` | Lock contention |

---

### 3.5 POST `/api/config/sources/{type}/sync` -- Sync Single Source

**Actual endpoint**: `POST /api/config/sources/{type}/sync?id={source_id}`

**Handler signature:**
```python
async def sync_source(request: web.Request) -> web.Response:
```

**Query parameters:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Source identifier |
| `force` | boolean | No | Force re-download (default: false) |

**This is a long-running operation.** The HTTP response returns immediately (202 Accepted). Progress is reported via Socket.IO `config_event` events.

**Implementation pattern:**
```python
async def sync_source(request):
    source_type = request.match_info["type"]
    source_id = request.query.get("id")
    force = request.query.get("force", "false").lower() == "true"

    # Validate source exists
    # ... (validation code)

    # Generate job ID
    job_id = f"sync-{source_id}-{int(time.time())}"

    # Launch background task
    task = asyncio.create_task(
        _run_sync(source_type, source_id, force, job_id, config_event_handler)
    )

    # Store task reference for cancellation support
    active_sync_tasks[job_id] = task

    return web.json_response(
        {
            "success": True,
            "message": f"Sync started for '{source_id}'",
            "job_id": job_id,
            "status": "in_progress",
        },
        status=202,
    )


async def _run_sync(source_type, source_id, force, job_id, handler):
    """Background sync task. Runs in asyncio.to_thread for blocking Git ops."""
    try:
        await handler.emit_config_event(
            operation="sync_progress",
            entity_type=f"{source_type}_source",
            entity_id=source_id,
            status="started",
            data={"job_id": job_id, "progress": 0},
        )

        # Blocking Git operation -- run in thread pool
        result = await asyncio.to_thread(
            _sync_source_blocking, source_type, source_id, force
        )

        await handler.emit_config_event(
            operation="sync_completed",
            entity_type=f"{source_type}_source",
            entity_id=source_id,
            status="completed",
            data={
                "job_id": job_id,
                "items_discovered": result.get("items_discovered", 0),
                "duration_ms": result.get("duration_ms", 0),
            },
        )
    except Exception as e:
        await handler.emit_config_event(
            operation="sync_failed",
            entity_type=f"{source_type}_source",
            entity_id=source_id,
            status="failed",
            data={"job_id": job_id, "error": str(e)},
        )
    finally:
        active_sync_tasks.pop(job_id, None)


def _sync_source_blocking(source_type, source_id, force):
    """Blocking sync operation -- called via asyncio.to_thread."""
    import time as time_mod
    start = time_mod.time()

    if source_type == "agent":
        config = AgentSourceConfiguration.load()
        repos = [r for r in config.get_enabled_repositories() if r.identifier == source_id]
        if not repos:
            raise ValueError(f"Agent source '{source_id}' not found or not enabled")
        manager = GitSourceManager()
        result = manager.sync_repository(repos[0], force=force)
        items = result.get("agents_discovered", 0) if isinstance(result, dict) else 0
    elif source_type == "skill":
        from claude_mpm.services.skills.git_skill_source_manager import GitSkillSourceManager
        manager = GitSkillSourceManager()
        result = manager.sync_source(source_id, force=force)
        items = result.get("skills_discovered", 0) if isinstance(result, dict) else 0
    else:
        raise ValueError(f"Invalid source type: {source_type}")

    elapsed_ms = int((time_mod.time() - start) * 1000)
    return {"items_discovered": items, "duration_ms": elapsed_ms}
```

**Immediate response (202 Accepted):**
```json
{
    "success": true,
    "message": "Sync started for 'system'",
    "job_id": "sync-system-1707825000",
    "status": "in_progress"
}
```

**Socket.IO progress events:**
```json
{
    "type": "config_event",
    "operation": "sync_progress",
    "entity_type": "skill_source",
    "entity_id": "system",
    "status": "started",
    "data": {
        "job_id": "sync-system-1707825000",
        "progress": 0
    },
    "timestamp": "2026-02-13T10:30:00.000Z"
}
```

**Socket.IO completion event:**
```json
{
    "type": "config_event",
    "operation": "sync_completed",
    "entity_type": "skill_source",
    "entity_id": "system",
    "status": "completed",
    "data": {
        "job_id": "sync-system-1707825000",
        "items_discovered": 78,
        "duration_ms": 12500
    },
    "timestamp": "2026-02-13T10:30:12.500Z"
}
```

**Socket.IO failure event:**
```json
{
    "type": "config_event",
    "operation": "sync_failed",
    "entity_type": "skill_source",
    "entity_id": "system",
    "status": "failed",
    "data": {
        "job_id": "sync-system-1707825000",
        "error": "Repository not accessible: HTTP 404"
    },
    "timestamp": "2026-02-13T10:30:05.000Z"
}
```

**Error responses (synchronous, before task launch):**

| Status | Code | Condition |
|--------|------|-----------|
| 400 | `VALIDATION_ERROR` | Invalid type or missing id |
| 404 | `NOT_FOUND` | Source not found |
| 409 | `SYNC_IN_PROGRESS` | Sync already running for this source |

---

### 3.6 POST `/api/config/sources/sync-all` -- Sync All Enabled Sources

**Handler signature:**
```python
async def sync_all_sources(request: web.Request) -> web.Response:
```

**Query parameters:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | No | `"agent"`, `"skill"`, or `"all"` (default: `"all"`) |
| `force` | boolean | No | Force re-download (default: false) |

**Implementation:** Creates a single background task that syncs sources sequentially in priority order (lower priority number first). Emits per-source progress events.

```python
async def _run_sync_all(source_type_filter, force, job_id, handler):
    sources_to_sync = []

    if source_type_filter in ("all", "agent"):
        config = AgentSourceConfiguration.load()
        for repo in config.get_enabled_repositories():
            sources_to_sync.append(("agent", repo.identifier))

    if source_type_filter in ("all", "skill"):
        ssc = SkillSourceConfiguration()
        for source in ssc.load():
            if source.enabled:
                sources_to_sync.append(("skill", source.id))

    # Sort by priority (already sorted by get_enabled_repositories / load)
    total = len(sources_to_sync)

    for idx, (stype, sid) in enumerate(sources_to_sync):
        await handler.emit_config_event(
            operation="sync_progress",
            entity_type=f"{stype}_source",
            entity_id=sid,
            status="progress",
            data={
                "job_id": job_id,
                "current": idx + 1,
                "total": total,
                "progress_pct": int(((idx + 1) / total) * 100),
            },
        )
        try:
            await asyncio.to_thread(_sync_source_blocking, stype, sid, force)
        except Exception as e:
            await handler.emit_config_event(
                operation="sync_failed",
                entity_type=f"{stype}_source",
                entity_id=sid,
                status="failed",
                data={"job_id": job_id, "error": str(e)},
            )
            # Continue with next source -- don't abort entire sync-all
```

**Immediate response (202 Accepted):**
```json
{
    "success": true,
    "message": "Sync started for all sources",
    "job_id": "sync-all-1707825000",
    "sources_to_sync": 3
}
```

**Cancellation support:** The task reference is stored in `active_sync_tasks[job_id]`. A future endpoint or Socket.IO event can call `task.cancel()`.

---

### 3.7 GET `/api/config/sources/sync-status` -- Current Sync State

**Handler signature:**
```python
async def get_sync_status(request: web.Request) -> web.Response:
```

**No request parameters.**

This endpoint is a **polling fallback** for when Socket.IO disconnects. It returns the current state of all sync operations.

**Implementation:** Maintain a module-level dict `sync_status: Dict[str, Dict]` that is updated by `_run_sync` / `_run_sync_all`. Read it here.

**Success response (200 OK):**
```json
{
    "success": true,
    "is_syncing": true,
    "active_jobs": [
        {
            "job_id": "sync-all-1707825000",
            "started_at": "2026-02-13T10:30:00.000Z",
            "sources_total": 3,
            "sources_completed": 1
        }
    ],
    "last_results": {
        "agent_sources": {
            "bobmatnyc/claude-mpm-agents/agents": {
                "status": "completed",
                "items_discovered": 45,
                "last_sync": "2026-02-13T10:30:00.000Z"
            }
        },
        "skill_sources": {
            "system": {
                "status": "syncing",
                "items_discovered": null,
                "last_sync": "2026-02-13T09:00:00.000Z"
            }
        }
    }
}
```

---

### 3.8 Route Registration Summary

**In `src/claude_mpm/services/monitor/routes/config_sources.py`:**

```python
def register_source_routes(app, config_event_handler, config_file_watcher):
    """Register all source management routes on the aiohttp app."""

    # Source CRUD
    app.router.add_post("/api/config/sources/agent", add_agent_source)
    app.router.add_post("/api/config/sources/skill", add_skill_source)
    app.router.add_delete("/api/config/sources/{type}", remove_source)
    app.router.add_patch("/api/config/sources/{type}", update_source)

    # Sync operations
    app.router.add_post("/api/config/sources/{type}/sync", sync_source)
    app.router.add_post("/api/config/sources/sync-all", sync_all_sources)
    app.router.add_get("/api/config/sources/sync-status", get_sync_status)
```

**Called from `server.py` in `_setup_http_routes()`:**
```python
from claude_mpm.services.monitor.routes.config_sources import register_source_routes
register_source_routes(self.app, self.config_event_handler, self.config_file_watcher)
```

---

## 4. Frontend Implementation

### 4.1 Shared Components

All shared components go in `src/claude_mpm/dashboard-svelte/src/lib/components/shared/`.

#### 4.1.1 Modal.svelte

**Purpose**: Confirmation dialogs, form containers, warning displays.

**Props:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `open` | `boolean` | `false` | Whether the modal is visible |
| `title` | `string` | `""` | Modal header text |
| `size` | `"sm" \| "md" \| "lg"` | `"md"` | Width: sm=384px, md=512px, lg=640px |
| `closeOnBackdrop` | `boolean` | `true` | Close when clicking backdrop |
| `closeOnEscape` | `boolean` | `true` | Close on Escape key |

**Slots:**
- `default` -- modal body content
- `footer` -- action buttons area

**Behavior:**
- Escape key closes the modal (if `closeOnEscape` is true)
- Focus trap: Tab/Shift+Tab cycles through focusable elements inside the modal
- Backdrop click closes (if `closeOnBackdrop` is true)
- Emits `onclose` event

**Styling:**
- Backdrop: `bg-slate-900/50` with `backdrop-blur-sm`
- Card: `bg-slate-800 border border-slate-700 rounded-lg shadow-xl`
- Header: `px-6 py-4 border-b border-slate-700` with title in `text-lg font-semibold text-slate-100`
- Body: `px-6 py-4`
- Footer: `px-6 py-4 border-t border-slate-700 flex justify-end gap-3`

**Skeleton:**
```svelte
<script lang="ts">
    let {
        open = $bindable(false),
        title = "",
        size = "md" as "sm" | "md" | "lg",
        closeOnBackdrop = true,
        closeOnEscape = true,
        onclose,
    }: {
        open: boolean;
        title: string;
        size?: "sm" | "md" | "lg";
        closeOnBackdrop?: boolean;
        closeOnEscape?: boolean;
        onclose?: () => void;
    } = $props();

    const sizeClasses = { sm: "max-w-sm", md: "max-w-lg", lg: "max-w-xl" };

    function close() {
        open = false;
        onclose?.();
    }

    function handleKeydown(e: KeyboardEvent) {
        if (e.key === "Escape" && closeOnEscape) close();
    }
</script>

{#if open}
<div class="fixed inset-0 z-50 flex items-center justify-center">
    <!-- Backdrop -->
    <div
        class="absolute inset-0 bg-slate-900/50 backdrop-blur-sm"
        onclick={() => closeOnBackdrop && close()}
        role="presentation"
    />
    <!-- Modal card -->
    <div
        class="relative {sizeClasses[size]} w-full mx-4 bg-slate-800 border border-slate-700 rounded-lg shadow-xl"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onkeydown={handleKeydown}
    >
        {#if title}
        <div class="px-6 py-4 border-b border-slate-700">
            <h2 class="text-lg font-semibold text-slate-100">{title}</h2>
        </div>
        {/if}
        <div class="px-6 py-4">
            <slot />
        </div>
        <div class="px-6 py-4 border-t border-slate-700 flex justify-end gap-3">
            <slot name="footer" />
        </div>
    </div>
</div>
{/if}
```

---

#### 4.1.2 Toast.svelte + toastStore

**Purpose**: Transient notifications for success/error/warning/info.

**Toast Store** (`src/lib/stores/toast.svelte.ts`):

```typescript
type ToastType = "success" | "error" | "warning" | "info";

interface Toast {
    id: string;
    type: ToastType;
    message: string;
    duration: number;  // ms, 0 = no auto-dismiss
}

class ToastStore {
    toasts = $state<Toast[]>([]);

    add(type: ToastType, message: string, duration: number = 5000) {
        const id = crypto.randomUUID();
        this.toasts = [...this.toasts, { id, type, message, duration }];

        if (duration > 0) {
            setTimeout(() => this.remove(id), duration);
        }

        return id;
    }

    remove(id: string) {
        this.toasts = this.toasts.filter(t => t.id !== id);
    }

    success(message: string) { return this.add("success", message); }
    error(message: string) { return this.add("error", message, 8000); }
    warning(message: string) { return this.add("warning", message, 6000); }
    info(message: string) { return this.add("info", message); }
}

export const toastStore = new ToastStore();
```

**Toast Component** (`src/lib/components/shared/Toast.svelte`):

| Visual | Color |
|--------|-------|
| success | `bg-emerald-500/10 border-emerald-500/30 text-emerald-400` |
| error | `bg-red-500/10 border-red-500/30 text-red-400` |
| warning | `bg-amber-500/10 border-amber-500/30 text-amber-400` |
| info | `bg-cyan-500/10 border-cyan-500/30 text-cyan-400` |

**Position**: Fixed bottom-right (`fixed bottom-4 right-4 z-[60]`). Toasts stack vertically with `gap-2`.

---

#### 4.1.3 Badge.svelte

**Purpose**: Status indicators for sources and sync state.

**Props:**

| Prop | Type | Default |
|------|------|---------|
| `variant` | `"default" \| "success" \| "warning" \| "error" \| "info"` | `"default"` |
| `size` | `"sm" \| "md"` | `"sm"` |

**Colors:**
- default: `bg-slate-700 text-slate-300`
- success: `bg-emerald-500/10 text-emerald-400`
- warning: `bg-amber-500/10 text-amber-400`
- error: `bg-red-500/10 text-red-400`
- info: `bg-cyan-500/10 text-cyan-400`

**Sizes:**
- sm: `text-xs px-2 py-0.5`
- md: `text-sm px-2.5 py-1`

---

#### 4.1.4 ProgressBar.svelte

**Purpose**: Sync progress visualization.

**Props:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `value` | `number` | `0` | Progress percentage (0-100) |
| `indeterminate` | `boolean` | `false` | Show animated indeterminate state |
| `label` | `string` | `""` | Text label above the bar |
| `size` | `"sm" \| "md"` | `"sm"` | Height: sm=4px, md=8px |

**Styling:**
- Track: `bg-slate-700 rounded-full overflow-hidden`
- Fill: `bg-cyan-500 rounded-full transition-all duration-300`
- Indeterminate: CSS animation sliding gradient left-to-right

---

### 4.2 Config-Specific Components

All config components go in `src/claude_mpm/dashboard-svelte/src/lib/components/config/`.

#### 4.2.1 SourceForm.svelte

**Purpose**: Add/edit source form, rendered inside Modal.

**Props:**

| Prop | Type | Description |
|------|------|-------------|
| `mode` | `"add" \| "edit"` | Form mode |
| `sourceType` | `"agent" \| "skill"` | Which type of source |
| `initialData` | `Partial<AgentSource \| SkillSource> \| null` | Pre-populated data for edit mode |
| `onsubmit` | `(data) => Promise<void>` | Submission callback |
| `oncancel` | `() => void` | Cancel callback |

**Agent source fields:**

| Field | Label | Type | Required | Validation | Placeholder |
|-------|-------|------|----------|------------|-------------|
| `url` | Repository URL | text input | Yes | `^https://github\.com/.+/.+$` | `https://github.com/owner/repo` |
| `subdirectory` | Subdirectory | text input | No | No leading `/`, no `..` | `agents` |
| `priority` | Priority | number input | No | 0-1000 | `500` |
| `enabled` | Enabled | checkbox/toggle | No | -- | checked |

**Skill source fields:**

| Field | Label | Type | Required | Validation | Placeholder |
|-------|-------|------|----------|------------|-------------|
| `id` | Source ID | text input | Yes (add), disabled (edit) | `^[a-zA-Z0-9][a-zA-Z0-9_-]*$` | `my-custom-skills` |
| `url` | Repository URL | text input | Yes | `^https://github\.com/.+/.+$` | `https://github.com/owner/repo` |
| `branch` | Branch | text input | No | Non-empty | `main` |
| `priority` | Priority | number input | No | 0-1000 | `100` |
| `enabled` | Enabled | checkbox/toggle | No | -- | checked |
| `token` | GitHub Token | password input | No | -- | `$GITHUB_TOKEN or token value` |

**Validation behavior:**
- Real-time validation on blur
- Error messages displayed below each field in `text-red-400 text-xs`
- Submit button disabled until all required fields valid
- On submit: call `onsubmit(data)`, show loading spinner on button, handle error via toastStore

**Submit flow:**
```
User fills form -> clicks "Add Source"
  -> button shows spinner, disabled
  -> calls onsubmit(formData)
  -> onsubmit calls configStore.addSource(type, data)
  -> configStore makes POST /api/config/sources/{type}
  -> on 201: toastStore.success("Source added"), close modal
  -> on error: toastStore.error(errorMessage), re-enable button
```

---

#### 4.2.2 SyncProgress.svelte

**Purpose**: Real-time sync status display with per-source progress.

**Props:**

| Prop | Type | Description |
|------|------|-------------|
| `sources` | `Source[]` | All configured sources (from config store) |

**State:**

```typescript
interface SyncState {
    [sourceId: string]: {
        status: "idle" | "syncing" | "completed" | "failed";
        progress: number;        // 0-100
        lastSync: string | null;  // ISO timestamp
        error: string | null;
        jobId: string | null;
    };
}
```

**Socket.IO subscription:**
```typescript
// In onMount or $effect, listen for config_event
socket.on("config_event", (event) => {
    if (event.operation === "sync_progress" || event.operation === "sync_completed" || event.operation === "sync_failed") {
        updateSyncState(event.entity_id, event);
    }
});
```

**UI elements:**
- "Sync All" button at top -- disabled when any sync is in progress
- Per-source row:
  - Source name and type badge
  - Status: idle (gray), syncing (animated cyan), completed (green checkmark), failed (red X)
  - When syncing: ProgressBar component with percentage
  - When failed: error message + "Retry" button
  - Last sync timestamp (relative: "2 minutes ago")

---

#### 4.2.3 Updated SourcesList.svelte

The read-only `SourcesList.svelte` from Phase 1 is updated to include mutation actions.

**New elements per source card:**

| Action | Button | Condition | Behavior |
|--------|--------|-----------|----------|
| Edit | Pencil icon | Always | Opens SourceForm in "edit" mode in Modal |
| Enable/Disable | Toggle switch | Not system source | Calls PATCH with `{enabled: !current}` |
| Remove | Trash icon | Not system source | Opens confirmation Modal with orphan warning |
| Sync | Refresh icon | Source enabled | Calls POST sync for this source |

**System source protection (BR-11):**
- System/default sources show a lock icon instead of toggle/trash buttons
- Tooltip: "Default source cannot be removed or disabled"

**Add Source button:**
- Positioned at top of the sources list
- Dropdown or segmented button: "Add Agent Source" / "Add Skill Source"
- Opens SourceForm in "add" mode in Modal

**External change detection:**
- Listen for `config_event` with `operation: "external_change"`
- Show toast: "Configuration changed externally. Refreshing..."
- Auto-reload source list from `GET /api/config/sources/`

---

### 4.3 Config Store Updates

**File**: `src/claude_mpm/dashboard-svelte/src/lib/stores/config.svelte.ts`

This store (created in Phase 1 for read operations) is extended with mutation functions.

```typescript
class ConfigStore {
    // Existing from Phase 1
    sources = $state<Sources>({ agent_sources: [], skill_sources: [] });
    loading = $state(false);
    error = $state<string | null>(null);

    // New in Phase 2
    syncStatus = $state<Record<string, SyncState>>({});
    mutating = $state(false);  // True during any CRUD operation

    // --- Mutation Functions ---

    async addSource(type: "agent" | "skill", data: Record<string, any>): Promise<void> {
        this.mutating = true;
        try {
            const response = await fetch(`/api/config/sources/${type}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data),
            });
            const result = await response.json();
            if (!result.success) {
                throw new Error(result.error || "Failed to add source");
            }
            // Optimistic UI: add to local state immediately
            // (Socket.IO event will confirm or we refetch)
            await this.fetchSources();
            toastStore.success(result.message);
        } catch (e) {
            toastStore.error(e instanceof Error ? e.message : "Failed to add source");
            throw e;
        } finally {
            this.mutating = false;
        }
    }

    async updateSource(type: "agent" | "skill", id: string, updates: Record<string, any>): Promise<void> {
        this.mutating = true;
        const encodedId = encodeURIComponent(id);
        try {
            const response = await fetch(`/api/config/sources/${type}?id=${encodedId}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(updates),
            });
            const result = await response.json();
            if (!result.success) throw new Error(result.error);
            await this.fetchSources();
            toastStore.success(result.message);
        } catch (e) {
            toastStore.error(e instanceof Error ? e.message : "Failed to update source");
            throw e;
        } finally {
            this.mutating = false;
        }
    }

    async removeSource(type: "agent" | "skill", id: string): Promise<void> {
        this.mutating = true;
        const encodedId = encodeURIComponent(id);
        try {
            const response = await fetch(`/api/config/sources/${type}?id=${encodedId}`, {
                method: "DELETE",
            });
            const result = await response.json();
            if (!result.success) throw new Error(result.error);
            await this.fetchSources();
            toastStore.success(result.message);
        } catch (e) {
            toastStore.error(e instanceof Error ? e.message : "Failed to remove source");
            throw e;
        } finally {
            this.mutating = false;
        }
    }

    async syncSource(type: "agent" | "skill", id: string, force: boolean = false): Promise<void> {
        const encodedId = encodeURIComponent(id);
        const forceParam = force ? "&force=true" : "";
        try {
            const response = await fetch(
                `/api/config/sources/${type}/sync?id=${encodedId}${forceParam}`,
                { method: "POST" }
            );
            const result = await response.json();
            if (!result.success) throw new Error(result.error);
            // Update local sync state -- progress will come via Socket.IO
            this.syncStatus[id] = {
                status: "syncing",
                progress: 0,
                lastSync: null,
                error: null,
                jobId: result.job_id,
            };
        } catch (e) {
            toastStore.error(e instanceof Error ? e.message : "Failed to start sync");
        }
    }

    async syncAllSources(force: boolean = false): Promise<void> {
        try {
            const forceParam = force ? "?force=true" : "";
            const response = await fetch(`/api/config/sources/sync-all${forceParam}`, {
                method: "POST",
            });
            const result = await response.json();
            if (!result.success) throw new Error(result.error);
            toastStore.info(result.message);
        } catch (e) {
            toastStore.error(e instanceof Error ? e.message : "Failed to start sync");
        }
    }

    // --- Socket.IO Event Handlers ---

    handleConfigEvent(event: ConfigEvent): void {
        switch (event.operation) {
            case "source_added":
            case "source_removed":
            case "source_updated":
                // Refetch sources to ensure consistency
                this.fetchSources();
                break;

            case "sync_progress":
            case "sync_completed":
            case "sync_failed":
                this.updateSyncStatus(event);
                break;

            case "external_change":
                toastStore.warning("Configuration changed externally. Refreshing...");
                this.fetchSources();
                break;
        }
    }

    private updateSyncStatus(event: ConfigEvent): void {
        const id = event.entity_id;
        if (!id) return;

        if (event.operation === "sync_completed") {
            this.syncStatus[id] = {
                status: "completed",
                progress: 100,
                lastSync: event.timestamp,
                error: null,
                jobId: event.data?.job_id,
            };
            // Refetch sources after sync completes (may have new items)
            this.fetchSources();
        } else if (event.operation === "sync_failed") {
            this.syncStatus[id] = {
                status: "failed",
                progress: 0,
                lastSync: this.syncStatus[id]?.lastSync ?? null,
                error: event.data?.error ?? "Sync failed",
                jobId: event.data?.job_id,
            };
        } else if (event.operation === "sync_progress") {
            this.syncStatus[id] = {
                status: "syncing",
                progress: event.data?.progress_pct ?? event.data?.progress ?? 0,
                lastSync: this.syncStatus[id]?.lastSync ?? null,
                error: null,
                jobId: event.data?.job_id,
            };
        }
    }
}
```

**Socket.IO subscription (in `+layout.svelte` or `+page.svelte`):**
```typescript
socket.on("config_event", (event) => {
    configStore.handleConfigEvent(event);
});
```

---

## 5. Concurrency Strategy

### 5.1 Server-Side: ConfigFileLock

All config file mutations (add, update, remove source) acquire an exclusive advisory file lock before the read-modify-write cycle. This prevents:

- **CLI + UI concurrent writes**: If the CLI is saving while the UI tries to save, one waits (up to 5s) and the other succeeds first.
- **Multiple browser tabs**: Both tabs' requests hit the same server process; the lock serializes them.

**Lock scope**: Per-config-file. `agent_sources.yaml` and `skill_sources.yaml` have independent locks. A user can add an agent source and a skill source simultaneously without blocking.

**Lock timeout**: 5 seconds. If a lock cannot be acquired in 5 seconds, the operation fails with 423 status. This is aggressive by design -- we don't want the UI to hang.

### 5.2 External Change Detection: File Mtime Polling

The `ConfigFileWatcher` polls config file mtimes every 5 seconds. When a file's mtime changes (from CLI, editor, or another process) and the change was NOT from our API (tracked via `update_mtime()`), a `config_event` with `operation: "external_change"` is emitted.

**Frontend reaction:**
1. Show toast: "Configuration changed externally. Refreshing..."
2. Re-fetch sources from `GET /api/config/sources/`
3. If a mutation form is open, show warning: "Configuration changed. Your edits may conflict."

### 5.3 Optimistic UI with Rollback

For fast user feedback, the config store updates local state immediately after a successful API call, then re-fetches from the server to confirm. If the re-fetch shows a different state (due to concurrent changes), the store updates to the authoritative server state.

**Flow:**
```
1. User clicks "Disable source X"
2. UI immediately toggles switch to disabled (optimistic)
3. PATCH /api/config/sources/skill?id=X with {enabled: false}
4a. 200 OK -> fetchSources() to confirm
4b. 4xx/5xx -> revert switch to enabled, show toast error
```

### 5.4 Socket.IO Broadcasting for Multi-Tab

When any mutation succeeds, the backend emits a `config_event` to all connected Socket.IO clients. This means:
- Tab A adds a source -> Tab B receives `source_added` event -> Tab B refreshes its source list
- CLI changes config file -> mtime polling detects it -> all tabs receive `external_change` event

**Limitation**: If Socket.IO disconnects during a mutation, the other tab won't know about the change until the mtime poller detects it (up to 5 seconds) or the user manually refreshes.

---

## 6. Data Flow

### 6.1 Mutation Lifecycle

```
User Action (click "Add Source")
    |
    v
SourceForm validates input
    |
    v
configStore.addSource("skill", data)
    |
    v
POST /api/config/sources/skill  (HTTP request)
    |
    v
Handler validates request body (URL regex, priority range, ID format)
    |  400 if invalid
    v
asyncio.to_thread(_add_skill_source, ...)  (offload blocking I/O)
    |
    v
config_file_lock(skill_sources.yaml)  (acquire exclusive lock)
    |  423 if lock timeout
    v
SkillSourceConfiguration.load()  (read current file)
    |
    v
Uniqueness check (ID already exists?)
    |  409 if duplicate
    v
SkillSourceConfiguration.add_source(source)  (modify in-memory)
    |
    v
SkillSourceConfiguration.save()  (write temp file + atomic rename)
    |
    v
Lock released (context manager exit)
    |
    v
config_file_watcher.update_mtime(path)  (prevent false external_change)
    |
    v
config_event_handler.emit_config_event("source_added", ...)  (Socket.IO broadcast)
    |
    v
201 Created response to HTTP caller
    |
    v
configStore receives 201 -> fetchSources() -> UI updates
    |
    v
Other tabs receive config_event -> their configStore also refreshes
```

### 6.2 Sync Lifecycle

```
User clicks "Sync" on source X
    |
    v
configStore.syncSource("skill", "X")
    |
    v
POST /api/config/sources/skill/sync?id=X  (HTTP request)
    |
    v
Handler validates source exists and is enabled
    |
    v
asyncio.create_task(_run_sync(...))  (launch background task)
    |
    v
202 Accepted returned immediately with job_id
    |
    v
configStore sets syncStatus[X] = {status: "syncing", progress: 0}
    |
    v
Background task: emit config_event("sync_progress", status="started")
    |
    v
asyncio.to_thread(_sync_source_blocking, ...)  (blocking Git operation)
    |
    v
On success: emit config_event("sync_completed", items_discovered=78)
    |
    v
configStore.handleConfigEvent -> syncStatus[X] = {status: "completed", progress: 100}
    |
    v
SyncProgress component updates: shows green checkmark + "78 items discovered"
```

---

## 7. Testing Plan

### 7.1 Backend: pytest for Each Endpoint

**File**: `tests/unit/services/monitor/routes/test_config_sources.py`

| Test | Description | Method |
|------|-------------|--------|
| `test_add_agent_source_success` | Valid URL, returns 201 with source data | POST agent |
| `test_add_agent_source_invalid_url` | Non-GitHub URL returns 400 | POST agent |
| `test_add_agent_source_duplicate` | Same URL returns 409 CONFLICT | POST agent |
| `test_add_agent_source_priority_out_of_range` | Priority 1001 returns 400 | POST agent |
| `test_add_skill_source_success` | Valid source, returns 201 | POST skill |
| `test_add_skill_source_invalid_id` | ID with spaces returns 400 | POST skill |
| `test_add_skill_source_duplicate_id` | Same ID returns 409 | POST skill |
| `test_add_skill_source_no_token_in_response` | Token field never in response body | POST skill |
| `test_remove_agent_source_success` | Valid ID, returns 200 | DELETE agent |
| `test_remove_agent_source_not_found` | Unknown ID returns 404 | DELETE agent |
| `test_remove_system_source_blocked` | Default source returns 403 | DELETE agent |
| `test_remove_skill_source_success` | Valid ID, returns 200 | DELETE skill |
| `test_update_source_priority` | Change priority, verify in file | PATCH |
| `test_update_source_disable` | Disable source, verify in file | PATCH |
| `test_update_system_source_disable_blocked` | Disable default returns 403 | PATCH |
| `test_sync_source_returns_202` | Sync returns 202 with job_id | POST sync |
| `test_sync_source_not_found` | Unknown source returns 404 | POST sync |
| `test_sync_source_already_syncing` | Returns 409 SYNC_IN_PROGRESS | POST sync |
| `test_sync_all_returns_202` | Returns 202 with source count | POST sync-all |
| `test_sync_status_no_active_jobs` | Returns is_syncing=false | GET sync-status |

### 7.2 ConfigFileLock: Concurrent Write Tests

**File**: `tests/unit/core/test_config_file_lock.py`

| Test | Description |
|------|-------------|
| `test_lock_acquire_release` | Acquire lock, verify lock file exists, release, verify cleanup |
| `test_lock_blocks_concurrent` | Two threads: first acquires lock, second blocks then succeeds after release |
| `test_lock_timeout` | Second lock attempt within timeout raises `ConfigFileLockTimeout` |
| `test_lock_released_on_exception` | Exception inside `with` block still releases lock |
| `test_lock_nonexistent_directory` | Lock on file in non-existent directory creates directory |
| `test_lock_stale_recovery` | flock is automatically released when file descriptor is closed (simulated crash) |
| `test_concurrent_10_processes` | Stress: 10 concurrent threads, each does lock + read + write + unlock. File content is consistent after all complete. |
| `test_lock_different_files_independent` | Lock on agent_sources.yaml does NOT block lock on skill_sources.yaml |

### 7.3 Frontend: Manual Testing Checklist

| # | Scenario | Expected Result |
|---|----------|-----------------|
| 1 | Click "Add Agent Source", fill valid URL, submit | Source appears in list, success toast shown |
| 2 | Click "Add Agent Source", enter invalid URL | Submit button disabled, error shown under field |
| 3 | Click "Add Agent Source" with duplicate URL | Error toast with "already exists" message |
| 4 | Click enable/disable toggle on custom source | Toggle reflects new state, success toast |
| 5 | Click enable/disable toggle on system source | Toggle is disabled/hidden, no action |
| 6 | Click "Remove" on custom source | Confirmation modal appears |
| 7 | Confirm removal | Source disappears, success toast |
| 8 | Click "Remove" on system source | Button is disabled/hidden |
| 9 | Click "Sync" on source | Progress bar appears, percentage updates |
| 10 | Sync completes | Green checkmark, "N items discovered" shown |
| 11 | Sync fails | Red X, error message, "Retry" button appears |
| 12 | Click "Sync All" | All enabled sources start syncing sequentially |
| 13 | Modify config file externally (vi) | Toast "Config changed externally", list refreshes |
| 14 | Open two browser tabs, add source in Tab A | Tab B receives update, shows new source |
| 15 | Modal: press Escape | Modal closes |
| 16 | Modal: click backdrop | Modal closes |
| 17 | Toast auto-dismisses after 5 seconds | Toast fades out |

### 7.4 Integration: CLI + UI Concurrent Usage

| # | Scenario | Expected Result |
|---|----------|-----------------|
| 1 | Dashboard open. Run `claude-mpm agents deploy` in CLI. | Dashboard detects external change within 5s, refreshes |
| 2 | Dashboard adding source. CLI modifies same file simultaneously. | One operation succeeds, other retries or errors with lock timeout |
| 3 | Dashboard syncing. CLI syncs same source. | Both proceed independently (Git operations are idempotent) |

---

## 8. Rollback Strategy

### 8.1 Failed Source Addition

If `POST /api/config/sources/{type}` fails after acquiring the lock but before or during write:
- The lock is released automatically (context manager)
- The config file is unchanged (load happened, but save either didn't run or used atomic write)
- For skill sources: temp file is cleaned up in the `except` block of `SkillSourceConfiguration.save()`
- For agent sources: plain `open("w")` may leave a partial write. **Mitigation**: Standardize agent sources to use atomic writes (temp + rename), same as skill sources. This is a code change to `AgentSourceConfiguration.save()`.

### 8.2 Failed Source Removal

If removal fails after the lock:
- Source is not removed (load succeeded but save failed)
- No data loss -- worst case is the source remains

### 8.3 Failed Sync

If `_run_sync` crashes:
- The `finally` block removes the task from `active_sync_tasks`
- A `sync_failed` config_event is emitted with the error
- The cache directory may be in an inconsistent state if Git was mid-clone
- **Mitigation**: Sync to a temporary directory first, then atomic move on success. (Enhancement for Git sync -- requires modifying `GitSourceManager.sync_repository()` to support a staging directory.)

### 8.4 Atomic Write Standardization

**Action item**: Modify `AgentSourceConfiguration.save()` to use the same temp-file + rename pattern as `SkillSourceConfiguration.save()`. This eliminates the inconsistency risk noted in research.

```python
# In AgentSourceConfiguration.save():
# Replace: with open(config_path, "w") as f:
# With:
temp_path = config_path.with_suffix(".yaml.tmp")
with open(temp_path, "w") as f:
    # ... write YAML ...
temp_path.replace(config_path)
```

---

## 9. Definition of Done

### 9.1 Prerequisites

- [ ] `ConfigFileLock` context manager implemented and tested
- [ ] `ConfigEventHandler` class implemented
- [ ] `ConfigFileWatcher` class implemented with mtime polling
- [ ] Both registered in `server.py` initialization
- [ ] `AgentSourceConfiguration.save()` updated to use atomic writes (temp + rename)

### 9.2 Backend Endpoints

- [ ] `POST /api/config/sources/agent` -- creates agent source, validates URL, checks uniqueness, emits Socket.IO event
- [ ] `POST /api/config/sources/skill` -- creates skill source, validates all fields, never returns token, emits Socket.IO event
- [ ] `DELETE /api/config/sources/{type}?id=` -- removes source, blocks system sources (BR-11), emits Socket.IO event
- [ ] `PATCH /api/config/sources/{type}?id=` -- updates source, blocks system disable (BR-11), validates priority (BR-04)
- [ ] `POST /api/config/sources/{type}/sync?id=` -- returns 202, background sync, emits progress/completion/failure events
- [ ] `POST /api/config/sources/sync-all` -- returns 202, sequential sync by priority, per-source progress events
- [ ] `GET /api/config/sources/sync-status` -- returns current sync state for all sources

### 9.3 Frontend Components

- [ ] `Modal.svelte` -- opens/closes, backdrop click, Escape key, focus management
- [ ] `Toast.svelte` + `toastStore` -- success/error/warning/info, auto-dismiss, stacking
- [ ] `Badge.svelte` -- variant colors, two sizes
- [ ] `ProgressBar.svelte` -- determinate and indeterminate modes
- [ ] `SourceForm.svelte` -- dynamic fields per type, validation, submission with loading state
- [ ] `SyncProgress.svelte` -- per-source progress, Socket.IO subscription, retry button
- [ ] `SourcesList.svelte` (updated) -- add/edit/toggle/remove/sync buttons, system source protection, external change toast

### 9.4 Store

- [ ] `configStore` extended with `addSource`, `updateSource`, `removeSource`, `syncSource`, `syncAllSources`
- [ ] `configStore` handles `config_event` Socket.IO events for real-time updates
- [ ] `configStore` handles `external_change` events with toast notification and refresh
- [ ] `toastStore` implemented with Svelte 5 runes

### 9.5 Integration

- [ ] Socket.IO `config_event` events flow from backend to frontend for all mutation operations
- [ ] Mtime polling detects CLI changes within 5 seconds and triggers frontend refresh
- [ ] Two browser tabs: mutation in one tab reflected in the other within 2 seconds
- [ ] All mutation operations use `ConfigFileLock` -- no unprotected config file writes

---

## 10. Devil's Advocate Notes

### DA-1: fcntl.flock() is POSIX-only

`fcntl.flock()` works on macOS and Linux but NOT on Windows. This means the dashboard cannot be used on Windows for source management.

**Assessment**: Acceptable for the current user base. Claude MPM is primarily used on macOS and Linux developer machines. Windows is not a supported platform for the CLI either.

**If Windows support becomes needed**: Replace `fcntl.flock()` with `portalocker` library, which provides a cross-platform `lock()` function. The `ConfigFileLock` API would not change.

### DA-2: 5-second lock timeout may be too aggressive

Git sync writes (in `_sync_source_blocking`) are long-running but do NOT hold the config file lock. Only the CRUD operations (add/update/remove source) hold the lock, and those are fast (read YAML + modify + write YAML, typically < 100ms).

**Assessment**: 5 seconds is more than sufficient for CRUD operations. The sync operation runs without holding a config lock.

**Edge case**: If the disk is slow (NFS, encrypted volume), YAML write could take > 100ms. But 5 seconds still provides a generous buffer.

### DA-3: Source IDs with slashes break URL path parameters

Agent source identifiers like `bobmatnyc/claude-mpm-agents/agents` contain forward slashes, which would be interpreted as path separators.

**Resolution**: Use query parameters (`?id=bobmatnyc/claude-mpm-agents/agents`) instead of path parameters for the source ID. The `type` remains a path parameter since it's always `"agent"` or `"skill"` (no special characters). The frontend URL-encodes the query parameter value with `encodeURIComponent()`.

### DA-4: Optimistic UI can show stale state if Socket.IO disconnects

If Socket.IO disconnects during a mutation, Tab B won't receive the `config_event`. It will show stale state until:
- The mtime poller detects the change (up to 5 seconds)
- The user manually refreshes
- Socket.IO reconnects and the tab refreshes

**Assessment**: Acceptable for MVP. The mtime poller provides a 5-second safety net. For production, consider adding a `fetchSources()` call on Socket.IO reconnect.

### DA-5: Atomic writes inconsistency between agent and skill sources

`SkillSourceConfiguration.save()` uses temp file + rename (atomic). `AgentSourceConfiguration.save()` uses plain `open("w")` (non-atomic). If the process crashes during an agent source save, the file could be left in a partial state.

**Resolution**: Part of Phase 2 prerequisites. Modify `AgentSourceConfiguration.save()` to use the same temp + rename pattern. Added to the Definition of Done.

### DA-6: File mtime polling at 5s interval

Up to 5 seconds of stale display if an external process modifies a config file. The user could make a decision based on stale data, then their write overwrites the external change.

**Assessment**: Acceptable for the following reasons:
1. The `ConfigFileLock` prevents concurrent writes even if the UI doesn't know about the external change
2. The lock ensures read-modify-write atomicity, so the worst case is that the user overwrites the external change knowingly (after the toast appears)
3. 5 seconds matches common polling intervals in similar tools (VS Code settings sync, etc.)

**Enhancement for later**: Use `watchdog` (already a dependency) or `kqueue`/`inotify` for sub-second detection. Not needed for MVP.

### DA-7: CLI does not use ConfigFileLock

The CLI currently writes config files without any file locking. Until the CLI is also updated to use `ConfigFileLock`, concurrent CLI + UI writes are still vulnerable to the lost-update problem -- the lock only protects against concurrent UI writes.

**Assessment**: Partially mitigated. The CLI write operations are fast (< 100ms), so the race window is small. The mtime poller will detect CLI changes and refresh the UI. For production safety, the CLI should be updated to use `ConfigFileLock` as well (separate PR).

**Priority**: Medium. CLI users who also use the dashboard are power users who understand the risk. The toast notification ("Config changed externally") provides awareness.

---

## 11. Files Created/Modified

### New Files

| File | Purpose |
|------|---------|
| `src/claude_mpm/core/config_file_lock.py` | ConfigFileLock context manager + ConfigFileLockError exceptions + get_config_file_mtime helper |
| `src/claude_mpm/services/monitor/handlers/config_handler.py` | ConfigEventHandler (Socket.IO emitter) + ConfigFileWatcher (mtime poller) |
| `src/claude_mpm/services/monitor/routes/config_sources.py` | 7 source management route handlers + registration function |
| `src/claude_mpm/dashboard-svelte/src/lib/components/shared/Modal.svelte` | Modal dialog component |
| `src/claude_mpm/dashboard-svelte/src/lib/components/shared/Toast.svelte` | Toast notification component |
| `src/claude_mpm/dashboard-svelte/src/lib/components/shared/Badge.svelte` | Status badge component |
| `src/claude_mpm/dashboard-svelte/src/lib/components/shared/ProgressBar.svelte` | Progress bar component |
| `src/claude_mpm/dashboard-svelte/src/lib/components/config/SourceForm.svelte` | Add/edit source form |
| `src/claude_mpm/dashboard-svelte/src/lib/components/config/SyncProgress.svelte` | Sync status display |
| `src/claude_mpm/dashboard-svelte/src/lib/stores/toast.svelte.ts` | Toast notification store |
| `tests/unit/core/test_config_file_lock.py` | ConfigFileLock unit tests |
| `tests/unit/services/monitor/routes/test_config_sources.py` | Source endpoint tests |

### Modified Files

| File | Change |
|------|--------|
| `src/claude_mpm/config/agent_sources.py` | Update `save()` to use atomic writes (temp + rename) |
| `src/claude_mpm/services/monitor/server.py` | Initialize `ConfigEventHandler`, `ConfigFileWatcher`; call `register_source_routes()` |
| `src/claude_mpm/dashboard-svelte/src/lib/stores/config.svelte.ts` | Add mutation functions, Socket.IO event handlers, sync status state |
| `src/claude_mpm/dashboard-svelte/src/lib/components/config/SourcesList.svelte` | Add action buttons, modal triggers, external change handling |
| `src/claude_mpm/dashboard-svelte/src/routes/+page.svelte` | Add Socket.IO subscription for `config_event` |
| `src/claude_mpm/dashboard-svelte/src/routes/+layout.svelte` | Register `config_event` Socket.IO listener on connect |

---

## 12. Estimated Effort Breakdown

| Task | Estimate | Depends On |
|------|----------|------------|
| **Prerequisites** | | |
| ConfigFileLock implementation | 3h | -- |
| ConfigFileLock tests | 2h | ConfigFileLock |
| AgentSourceConfiguration atomic write update | 1h | -- |
| ConfigEventHandler + ConfigFileWatcher | 3h | -- |
| server.py integration (init + registration) | 1h | ConfigEventHandler |
| **Backend Endpoints** | | |
| POST /sources/agent handler | 2h | ConfigFileLock |
| POST /sources/skill handler | 2h | ConfigFileLock |
| DELETE /sources/{type} handler | 2h | ConfigFileLock |
| PATCH /sources/{type} handler | 2h | ConfigFileLock |
| POST /sources/{type}/sync handler | 3h | ConfigEventHandler |
| POST /sources/sync-all handler | 2h | sync handler |
| GET /sources/sync-status handler | 1h | sync handler |
| Backend endpoint tests | 4h | All endpoints |
| **Frontend Components** | | |
| Modal.svelte | 2h | -- |
| Toast.svelte + toastStore | 2h | -- |
| Badge.svelte | 0.5h | -- |
| ProgressBar.svelte | 1h | -- |
| SourceForm.svelte | 3h | Modal |
| SyncProgress.svelte | 2h | ProgressBar |
| SourcesList.svelte mutations | 3h | Modal, Toast, Badge |
| Config store mutations + Socket.IO | 3h | toastStore |
| Socket.IO config_event integration | 1h | Config store |
| **Testing & Polish** | | |
| Manual testing (all 17 scenarios) | 3h | All frontend |
| CLI + UI integration testing | 2h | All backend |
| Bug fixes and polish | 4h | Testing |
| **Total** | **~52h** | **~7-8 working days** |

---

## Appendix A: Validation Regex Patterns

```python
# GitHub URL validation
GITHUB_URL_PATTERN = r"^https://github\.com/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+/?$"

# Skill source ID validation
SKILL_SOURCE_ID_PATTERN = r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$"

# Subdirectory validation (relative path, no traversal)
SUBDIRECTORY_PATTERN = r"^[a-zA-Z0-9][a-zA-Z0-9_/./-]*$"
# Additional check: must not contain ".."
```

## Appendix B: Error Response Format

All error responses follow this format:

```json
{
    "success": false,
    "error": "Human-readable error message",
    "code": "ERROR_CODE",
    "details": {}
}
```

Error codes used in Phase 2:

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Invalid input (URL, priority, ID format) |
| `PROTECTED_SOURCE` | 403 | Attempting to remove/disable a system source |
| `NOT_FOUND` | 404 | Source with given ID not found |
| `CONFLICT` | 409 | Duplicate source (same URL or ID) |
| `SYNC_IN_PROGRESS` | 409 | Sync already running for this source |
| `LOCK_TIMEOUT` | 423 | Could not acquire config file lock |
| `SERVICE_ERROR` | 500 | Unexpected internal error |
