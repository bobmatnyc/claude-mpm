"""Source management API routes for the Claude MPM Dashboard.

Phase 2: Mutation endpoints for agent and skill source management.
Provides CRUD operations, sync triggers, and sync status polling.

All mutation endpoints:
- Acquire an advisory file lock via config_file_lock()
- Wrap blocking I/O in asyncio.to_thread()
- Emit Socket.IO config_event notifications
- Call config_file_watcher.update_mtime() after writes
"""

import asyncio
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from aiohttp import web

from claude_mpm.core.config_file_lock import (
    ConfigFileLockTimeout,
    config_file_lock,
)
from claude_mpm.core.logging_config import get_logger

logger = get_logger(__name__)

# GitHub URL validation pattern
GITHUB_URL_PATTERN = re.compile(
    r"^https://github\.com/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+/?$"
)

# Skill source ID validation pattern
SKILL_ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")

# Default/system source identifiers that cannot be removed or disabled (BR-11)
PROTECTED_AGENT_SOURCES = {"bobmatnyc/claude-mpm-agents/agents"}
PROTECTED_SKILL_SOURCES = {"system", "anthropic-official"}

# Module-level state for sync operations
active_sync_tasks: Dict[str, asyncio.Task] = {}
sync_status: Dict[str, Dict[str, Any]] = {}


def register_source_routes(app, config_event_handler, config_file_watcher):
    """Register all source management routes on the aiohttp app.

    Args:
        app: The aiohttp web application.
        config_event_handler: ConfigEventHandler instance for Socket.IO events.
        config_file_watcher: ConfigFileWatcher instance for mtime tracking.
    """
    # Capture references in closure for handler access
    _handler = config_event_handler
    _watcher = config_file_watcher

    # --- POST /api/config/sources/agent ---
    async def add_agent_source(request: web.Request) -> web.Response:
        """Add a new agent source (Git repository)."""
        try:
            body = await request.json()
        except Exception:
            return _error_response(400, "Invalid JSON body", "VALIDATION_ERROR")

        url = body.get("url", "").strip()
        subdirectory = body.get("subdirectory")
        priority = body.get("priority", 500)
        enabled = body.get("enabled", True)

        # Validate URL
        if not url or not GITHUB_URL_PATTERN.match(url):
            return _error_response(
                400,
                "URL must be a valid GitHub repository URL "
                "(https://github.com/owner/repo)",
                "VALIDATION_ERROR",
            )

        # Validate priority (BR-04)
        if not isinstance(priority, int) or priority < 0 or priority > 1000:
            return _error_response(
                400,
                "Priority must be an integer between 0 and 1000",
                "VALIDATION_ERROR",
            )

        # Validate subdirectory
        if subdirectory is not None:
            subdirectory = subdirectory.strip()
            if subdirectory.startswith("/") or ".." in subdirectory:
                return _error_response(
                    400,
                    "Subdirectory must be a relative path without '..' traversal",
                    "VALIDATION_ERROR",
                )

        try:

            def _add():
                from claude_mpm.config.agent_sources import AgentSourceConfiguration
                from claude_mpm.models.git_repository import GitRepository

                config_path = (
                    Path.home() / ".claude-mpm" / "config" / "agent_sources.yaml"
                )

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
                            raise ValueError(
                                f"Source '{repo.identifier}' already exists"
                            )

                    config.add_repository(repo)
                    config.save(config_path)

                return {
                    "identifier": repo.identifier,
                    "url": repo.url,
                    "subdirectory": repo.subdirectory,
                    "priority": repo.priority,
                    "enabled": repo.enabled,
                }

            source_data = await asyncio.to_thread(_add)

            # Update mtime to prevent false external-change alert
            config_path = Path.home() / ".claude-mpm" / "config" / "agent_sources.yaml"
            _watcher.update_mtime(config_path)

            # Emit Socket.IO event
            await _handler.emit_config_event(
                operation="source_added",
                entity_type="agent_source",
                entity_id=source_data["identifier"],
                status="completed",
                data={"url": source_data["url"], "priority": source_data["priority"]},
            )

            return web.json_response(
                {
                    "success": True,
                    "message": f"Agent source added: {source_data['identifier']}",
                    "source": source_data,
                },
                status=201,
            )

        except ConfigFileLockTimeout as e:
            return _error_response(423, str(e), "LOCK_TIMEOUT")
        except ValueError as e:
            error_msg = str(e)
            if "already exists" in error_msg:
                return _error_response(409, error_msg, "CONFLICT")
            return _error_response(400, error_msg, "VALIDATION_ERROR")
        except Exception as e:
            logger.error(f"Error adding agent source: {e}")
            return _error_response(500, str(e), "SERVICE_ERROR")

    # --- POST /api/config/sources/skill ---
    async def add_skill_source(request: web.Request) -> web.Response:
        """Add a new skill source (Git repository)."""
        try:
            body = await request.json()
        except Exception:
            return _error_response(400, "Invalid JSON body", "VALIDATION_ERROR")

        url = body.get("url", "").strip()
        source_id = body.get("id", "").strip()
        branch = body.get("branch", "main").strip()
        priority = body.get("priority", 100)
        enabled = body.get("enabled", True)
        token = body.get("token")

        # Validate URL
        if not url or not GITHUB_URL_PATTERN.match(url):
            return _error_response(
                400,
                "URL must be a valid GitHub repository URL "
                "(https://github.com/owner/repo)",
                "VALIDATION_ERROR",
            )

        # Auto-generate ID from URL if not provided
        if not source_id:
            # Extract owner/repo from URL and create ID like "owner-repo"
            parts = url.rstrip("/").split("/")
            if len(parts) >= 2:
                source_id = f"{parts[-2]}-{parts[-1]}"
            else:
                source_id = "custom"

        # Validate ID format
        if not SKILL_ID_PATTERN.match(source_id):
            return _error_response(
                400,
                "Source ID must start with alphanumeric and contain only "
                "alphanumeric, hyphens, or underscores",
                "VALIDATION_ERROR",
            )

        # Validate priority (BR-04)
        if not isinstance(priority, int) or priority < 0 or priority > 1000:
            return _error_response(
                400,
                "Priority must be an integer between 0 and 1000",
                "VALIDATION_ERROR",
            )

        # Validate branch
        if not branch:
            return _error_response(
                400, "Branch name cannot be empty", "VALIDATION_ERROR"
            )

        try:

            def _add():
                from claude_mpm.config.skill_sources import (
                    SkillSource,
                    SkillSourceConfiguration,
                )

                config_path = (
                    Path.home() / ".claude-mpm" / "config" / "skill_sources.yaml"
                )

                with config_file_lock(config_path):
                    ssc = SkillSourceConfiguration(config_path)
                    source = SkillSource(
                        id=source_id,
                        type="git",
                        url=url,
                        branch=branch,
                        priority=priority,
                        enabled=enabled,
                        token=token,
                    )
                    # add_source validates and checks ID uniqueness internally
                    ssc.add_source(source)

                return {
                    "id": source.id,
                    "type": source.type,
                    "url": source.url,
                    "branch": source.branch,
                    "priority": source.priority,
                    "enabled": source.enabled,
                    # token is NEVER returned (write-only)
                }

            source_data = await asyncio.to_thread(_add)

            # Update mtime
            config_path = Path.home() / ".claude-mpm" / "config" / "skill_sources.yaml"
            _watcher.update_mtime(config_path)

            # Emit Socket.IO event
            await _handler.emit_config_event(
                operation="source_added",
                entity_type="skill_source",
                entity_id=source_data["id"],
                status="completed",
                data={"url": source_data["url"], "priority": source_data["priority"]},
            )

            return web.json_response(
                {
                    "success": True,
                    "message": f"Skill source added: {source_data['id']}",
                    "source": source_data,
                },
                status=201,
            )

        except ConfigFileLockTimeout as e:
            return _error_response(423, str(e), "LOCK_TIMEOUT")
        except ValueError as e:
            error_msg = str(e)
            if "already exists" in error_msg:
                return _error_response(409, error_msg, "CONFLICT")
            return _error_response(400, error_msg, "VALIDATION_ERROR")
        except Exception as e:
            logger.error(f"Error adding skill source: {e}")
            return _error_response(500, str(e), "SERVICE_ERROR")

    # --- DELETE /api/config/sources/{type} ---
    async def remove_source(request: web.Request) -> web.Response:
        """Remove an agent or skill source."""
        source_type = request.match_info["type"]
        source_id = request.query.get("id", "").strip()

        # Validate type
        if source_type not in ("agent", "skill"):
            return _error_response(
                400, "Type must be 'agent' or 'skill'", "VALIDATION_ERROR"
            )

        # Validate id present
        if not source_id:
            return _error_response(
                400, "Query parameter 'id' is required", "VALIDATION_ERROR"
            )

        # Check protected sources (BR-11)
        if source_type == "agent" and source_id in PROTECTED_AGENT_SOURCES:
            return _error_response(
                403,
                f"Cannot remove default source '{source_id}'. Default sources are protected.",
                "PROTECTED_SOURCE",
            )
        if source_type == "skill" and source_id in PROTECTED_SKILL_SOURCES:
            return _error_response(
                403,
                f"Cannot remove default source '{source_id}'. Default sources are protected.",
                "PROTECTED_SOURCE",
            )

        try:

            def _remove():
                if source_type == "agent":
                    from claude_mpm.config.agent_sources import (
                        AgentSourceConfiguration,
                    )

                    config_path = (
                        Path.home() / ".claude-mpm" / "config" / "agent_sources.yaml"
                    )

                    with config_file_lock(config_path):
                        config = AgentSourceConfiguration.load(config_path)
                        removed = config.remove_repository(source_id)
                        if not removed:
                            raise ValueError(f"Source '{source_id}' not found")
                        config.save(config_path)

                    return config_path

                # skill
                from claude_mpm.config.skill_sources import (
                    SkillSourceConfiguration,
                )

                config_path = (
                    Path.home() / ".claude-mpm" / "config" / "skill_sources.yaml"
                )

                with config_file_lock(config_path):
                    ssc = SkillSourceConfiguration(config_path)
                    removed = ssc.remove_source(source_id)
                    if not removed:
                        raise ValueError(f"Source '{source_id}' not found")
                    # remove_source calls save() internally

                return config_path

            written_config_path = await asyncio.to_thread(_remove)

            # Update mtime
            _watcher.update_mtime(written_config_path)

            # Emit event
            await _handler.emit_config_event(
                operation="source_removed",
                entity_type=f"{source_type}_source",
                entity_id=source_id,
                status="completed",
            )

            return web.json_response(
                {
                    "success": True,
                    "message": f"Source '{source_id}' removed",
                    "orphaned_items": [],
                }
            )

        except ConfigFileLockTimeout as e:
            return _error_response(423, str(e), "LOCK_TIMEOUT")
        except ValueError as e:
            error_msg = str(e)
            if "not found" in error_msg:
                return _error_response(404, error_msg, "NOT_FOUND")
            return _error_response(400, error_msg, "VALIDATION_ERROR")
        except Exception as e:
            logger.error(f"Error removing source: {e}")
            return _error_response(500, str(e), "SERVICE_ERROR")

    # --- PATCH /api/config/sources/{type} ---
    async def update_source(request: web.Request) -> web.Response:
        """Update an agent or skill source (enabled, priority)."""
        source_type = request.match_info["type"]
        source_id = request.query.get("id", "").strip()

        # Validate type
        if source_type not in ("agent", "skill"):
            return _error_response(
                400, "Type must be 'agent' or 'skill'", "VALIDATION_ERROR"
            )

        # Validate id present
        if not source_id:
            return _error_response(
                400, "Query parameter 'id' is required", "VALIDATION_ERROR"
            )

        try:
            body = await request.json()
        except Exception:
            return _error_response(400, "Invalid JSON body", "VALIDATION_ERROR")

        enabled = body.get("enabled")
        priority = body.get("priority")

        # Must provide at least one updatable field
        if enabled is None and priority is None:
            return _error_response(
                400,
                "At least one of 'enabled' or 'priority' must be provided",
                "VALIDATION_ERROR",
            )

        # Validate priority (BR-04)
        if priority is not None:
            if not isinstance(priority, int) or priority < 0 or priority > 1000:
                return _error_response(
                    400,
                    "Priority must be an integer between 0 and 1000",
                    "VALIDATION_ERROR",
                )

        # Check protected sources cannot be disabled (BR-11)
        if enabled is False:
            if source_type == "agent" and source_id in PROTECTED_AGENT_SOURCES:
                return _error_response(
                    403,
                    f"Cannot disable default source '{source_id}'. "
                    "Default sources are protected.",
                    "PROTECTED_SOURCE",
                )
            if source_type == "skill" and source_id in PROTECTED_SKILL_SOURCES:
                return _error_response(
                    403,
                    f"Cannot disable default source '{source_id}'. "
                    "Default sources are protected.",
                    "PROTECTED_SOURCE",
                )

        try:

            def _update():
                if source_type == "agent":
                    from claude_mpm.config.agent_sources import (
                        AgentSourceConfiguration,
                    )

                    config_path = (
                        Path.home() / ".claude-mpm" / "config" / "agent_sources.yaml"
                    )

                    with config_file_lock(config_path):
                        config = AgentSourceConfiguration.load(config_path)

                        target = None
                        for repo in config.repositories:
                            if repo.identifier == source_id:
                                target = repo
                                break

                        if target is None:
                            raise ValueError(f"Source '{source_id}' not found")

                        if enabled is not None:
                            target.enabled = enabled
                        if priority is not None:
                            target.priority = priority

                        config.save(config_path)

                    return config_path, {
                        "identifier": target.identifier,
                        "enabled": target.enabled,
                        "priority": target.priority,
                    }

                # skill
                from claude_mpm.config.skill_sources import (
                    SkillSourceConfiguration,
                )

                config_path = (
                    Path.home() / ".claude-mpm" / "config" / "skill_sources.yaml"
                )

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

                return config_path, {
                    "id": target.id,
                    "enabled": target.enabled,
                    "priority": target.priority,
                }

            written_config_path, source_data = await asyncio.to_thread(_update)

            # Update mtime
            _watcher.update_mtime(written_config_path)

            # Emit event
            await _handler.emit_config_event(
                operation="source_updated",
                entity_type=f"{source_type}_source",
                entity_id=source_id,
                status="completed",
                data=source_data,
            )

            return web.json_response(
                {
                    "success": True,
                    "message": "Source updated",
                    "source": source_data,
                }
            )

        except ConfigFileLockTimeout as e:
            return _error_response(423, str(e), "LOCK_TIMEOUT")
        except ValueError as e:
            error_msg = str(e)
            if "not found" in error_msg:
                return _error_response(404, error_msg, "NOT_FOUND")
            return _error_response(400, error_msg, "VALIDATION_ERROR")
        except Exception as e:
            logger.error(f"Error updating source: {e}")
            return _error_response(500, str(e), "SERVICE_ERROR")

    # --- POST /api/config/sources/{type}/sync ---
    async def sync_source(request: web.Request) -> web.Response:
        """Trigger sync for a single source. Returns 202 immediately."""
        source_type = request.match_info["type"]
        source_id = request.query.get("id", "").strip()
        force = request.query.get("force", "false").lower() == "true"

        # Validate type
        if source_type not in ("agent", "skill"):
            return _error_response(
                400, "Type must be 'agent' or 'skill'", "VALIDATION_ERROR"
            )

        # Validate id present
        if not source_id:
            return _error_response(
                400, "Query parameter 'id' is required", "VALIDATION_ERROR"
            )

        # Check for already running sync for this source
        for job_id, task in active_sync_tasks.items():
            if source_id in job_id and not task.done():
                return _error_response(
                    409,
                    f"Sync already in progress for '{source_id}'",
                    "SYNC_IN_PROGRESS",
                )

        # Generate job ID
        job_id = f"sync-{source_id}-{int(time.time())}"

        # Launch background task
        task = asyncio.create_task(
            _run_sync(source_type, source_id, force, job_id, _handler)
        )
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

    # --- POST /api/config/sources/sync-all ---
    async def sync_all_sources(request: web.Request) -> web.Response:
        """Trigger sync for all enabled sources. Returns 202 immediately."""
        source_type_filter = request.query.get("type", "all")
        force = request.query.get("force", "false").lower() == "true"

        if source_type_filter not in ("agent", "skill", "all"):
            return _error_response(
                400,
                "Type must be 'agent', 'skill', or 'all'",
                "VALIDATION_ERROR",
            )

        job_id = f"sync-all-{int(time.time())}"

        # Count sources to sync
        def _count_sources():
            count = 0
            if source_type_filter in ("all", "agent"):
                from claude_mpm.config.agent_sources import AgentSourceConfiguration

                config = AgentSourceConfiguration.load()
                count += len(config.get_enabled_repositories())
            if source_type_filter in ("all", "skill"):
                from claude_mpm.config.skill_sources import SkillSourceConfiguration

                ssc = SkillSourceConfiguration()
                for source in ssc.load():
                    if source.enabled:
                        count += 1
            return count

        try:
            sources_count = await asyncio.to_thread(_count_sources)
        except Exception:
            sources_count = 0

        # Launch background task
        task = asyncio.create_task(
            _run_sync_all(source_type_filter, force, job_id, _handler)
        )
        active_sync_tasks[job_id] = task

        return web.json_response(
            {
                "success": True,
                "message": "Sync started for all sources",
                "job_id": job_id,
                "sources_to_sync": sources_count,
            },
            status=202,
        )

    # --- GET /api/config/sources/sync-status ---
    async def get_sync_status(request: web.Request) -> web.Response:
        """Return current sync state (polling fallback for Socket.IO)."""
        active_jobs = []
        for job_id, task in list(active_sync_tasks.items()):
            if not task.done():
                job_info = sync_status.get(job_id, {})
                active_jobs.append(
                    {
                        "job_id": job_id,
                        "started_at": job_info.get("started_at", ""),
                        "sources_total": job_info.get("sources_total", 0),
                        "sources_completed": job_info.get("sources_completed", 0),
                    }
                )

        return web.json_response(
            {
                "success": True,
                "is_syncing": len(active_jobs) > 0,
                "active_jobs": active_jobs,
                "last_results": sync_status.get("last_results", {}),
            }
        )

    # Register all routes
    app.router.add_post("/api/config/sources/agent", add_agent_source)
    app.router.add_post("/api/config/sources/skill", add_skill_source)
    app.router.add_delete("/api/config/sources/{type}", remove_source)
    app.router.add_patch("/api/config/sources/{type}", update_source)
    app.router.add_post("/api/config/sources/{type}/sync", sync_source)
    app.router.add_post("/api/config/sources/sync-all", sync_all_sources)
    app.router.add_get("/api/config/sources/sync-status", get_sync_status)

    logger.info("Registered 7 source management routes under /api/config/sources/")


# --- Background sync helpers ---


async def _run_sync(
    source_type: str,
    source_id: str,
    force: bool,
    job_id: str,
    handler,
) -> None:
    """Background sync task. Runs blocking Git ops in thread pool."""
    try:
        sync_status[job_id] = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "sources_total": 1,
            "sources_completed": 0,
        }

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

        sync_status[job_id]["sources_completed"] = 1

        # Store last result
        results_key = f"{source_type}_sources"
        if "last_results" not in sync_status:
            sync_status["last_results"] = {}
        if results_key not in sync_status["last_results"]:
            sync_status["last_results"][results_key] = {}
        sync_status["last_results"][results_key][source_id] = {
            "status": "completed",
            "items_discovered": result.get("items_discovered", 0),
            "last_sync": datetime.now(timezone.utc).isoformat(),
        }

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
        logger.error(f"Sync failed for {source_type}/{source_id}: {e}")
        await handler.emit_config_event(
            operation="sync_failed",
            entity_type=f"{source_type}_source",
            entity_id=source_id,
            status="failed",
            data={"job_id": job_id, "error": str(e)},
        )
    finally:
        active_sync_tasks.pop(job_id, None)


async def _run_sync_all(
    source_type_filter: str,
    force: bool,
    job_id: str,
    handler,
) -> None:
    """Background task to sync all enabled sources sequentially."""
    try:

        def _gather_sources():
            sources_to_sync = []
            if source_type_filter in ("all", "agent"):
                from claude_mpm.config.agent_sources import AgentSourceConfiguration

                config = AgentSourceConfiguration.load()
                for repo in config.get_enabled_repositories():
                    sources_to_sync.append(("agent", repo.identifier))

            if source_type_filter in ("all", "skill"):
                from claude_mpm.config.skill_sources import SkillSourceConfiguration

                ssc = SkillSourceConfiguration()
                for source in ssc.load():
                    if source.enabled:
                        sources_to_sync.append(("skill", source.id))

            return sources_to_sync

        sources_to_sync = await asyncio.to_thread(_gather_sources)
        total = len(sources_to_sync)

        sync_status[job_id] = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "sources_total": total,
            "sources_completed": 0,
        }

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
                    "progress_pct": int(((idx + 1) / total) * 100) if total > 0 else 0,
                },
            )
            try:
                result = await asyncio.to_thread(
                    _sync_source_blocking, stype, sid, force
                )
                sync_status[job_id]["sources_completed"] = idx + 1

                # Store last result
                results_key = f"{stype}_sources"
                if "last_results" not in sync_status:
                    sync_status["last_results"] = {}
                if results_key not in sync_status["last_results"]:
                    sync_status["last_results"][results_key] = {}
                sync_status["last_results"][results_key][sid] = {
                    "status": "completed",
                    "items_discovered": result.get("items_discovered", 0),
                    "last_sync": datetime.now(timezone.utc).isoformat(),
                }

            except Exception as e:
                logger.error(f"Sync failed for {stype}/{sid}: {e}")
                await handler.emit_config_event(
                    operation="sync_failed",
                    entity_type=f"{stype}_source",
                    entity_id=sid,
                    status="failed",
                    data={"job_id": job_id, "error": str(e)},
                )
                # Continue with next source -- don't abort entire sync-all

        # Emit overall completion
        await handler.emit_config_event(
            operation="sync_all_completed",
            entity_type="config",
            status="completed",
            data={
                "job_id": job_id,
                "sources_total": total,
                "sources_completed": sync_status.get(job_id, {}).get(
                    "sources_completed", 0
                ),
            },
        )

    except Exception as e:
        logger.error(f"Sync-all failed: {e}")
        await handler.emit_config_event(
            operation="sync_all_failed",
            entity_type="config",
            status="failed",
            data={"job_id": job_id, "error": str(e)},
        )
    finally:
        active_sync_tasks.pop(job_id, None)


def _sync_source_blocking(
    source_type: str, source_id: str, force: bool
) -> Dict[str, Any]:
    """Blocking sync operation -- called via asyncio.to_thread."""
    import time as time_mod

    start = time_mod.time()

    if source_type == "agent":
        from claude_mpm.config.agent_sources import AgentSourceConfiguration
        from claude_mpm.services.agents.git_source_manager import GitSourceManager

        config = AgentSourceConfiguration.load()
        repos = [
            r for r in config.get_enabled_repositories() if r.identifier == source_id
        ]
        if not repos:
            raise ValueError(f"Agent source '{source_id}' not found or not enabled")
        manager = GitSourceManager()
        result = manager.sync_repository(repos[0], force=force)
        items = result.get("agents_discovered", 0) if isinstance(result, dict) else 0

    elif source_type == "skill":
        from claude_mpm.services.skills.git_skill_source_manager import (
            GitSkillSourceManager,
        )

        manager = GitSkillSourceManager()
        result = manager.sync_source(source_id, force=force)
        items = result.get("skills_discovered", 0) if isinstance(result, dict) else 0

    else:
        raise ValueError(f"Invalid source type: {source_type}")

    elapsed_ms = int((time_mod.time() - start) * 1000)
    return {"items_discovered": items, "duration_ms": elapsed_ms}


def _error_response(status: int, error: str, code: str) -> web.Response:
    """Create a standardized error response."""
    return web.json_response(
        {"success": False, "error": error, "code": code},
        status=status,
    )
