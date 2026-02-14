"""Agent deployment API routes for the Claude MPM Dashboard.

Phase 3: Endpoint handlers for deploying/undeploying agents and
managing agent collections. Every destructive operation follows the
safety protocol: backup -> journal -> execute -> verify -> prune.

All blocking service calls are wrapped in asyncio.to_thread().
"""

import asyncio
import time
from pathlib import Path
from typing import Any, Dict

from aiohttp import web

from claude_mpm.core.logging_config import get_logger
from claude_mpm.services.config_api.validation import (
    validate_path_containment,
    validate_safe_name,
)

logger = get_logger(__name__)

# Agents that cannot be undeployed (BR-01)
CORE_AGENTS = [
    "engineer",
    "research",
    "qa",
    "web-qa",
    "documentation",
    "ops",
    "ticketing",
]

# Lazy-initialized service singletons
_backup_manager = None
_operation_journal = None
_deployment_verifier = None
_agent_deployment_service = None


def _get_backup_manager():
    global _backup_manager
    if _backup_manager is None:
        from claude_mpm.services.config_api.backup_manager import BackupManager

        _backup_manager = BackupManager()
    return _backup_manager


def _get_operation_journal():
    global _operation_journal
    if _operation_journal is None:
        from claude_mpm.services.config_api.operation_journal import OperationJournal

        _operation_journal = OperationJournal()
    return _operation_journal


def _get_deployment_verifier():
    global _deployment_verifier
    if _deployment_verifier is None:
        from claude_mpm.services.config_api.deployment_verifier import (
            DeploymentVerifier,
        )

        _deployment_verifier = DeploymentVerifier()
    return _deployment_verifier


def _get_agent_deployment_service():
    global _agent_deployment_service
    if _agent_deployment_service is None:
        from claude_mpm.services.agents.deployment.agent_deployment import (
            AgentDeploymentService,
        )

        _agent_deployment_service = AgentDeploymentService()
    return _agent_deployment_service


def _error_response(status: int, error: str, code: str) -> web.Response:
    return web.json_response(
        {"success": False, "error": error, "code": code},
        status=status,
    )


def _verification_to_dict(result) -> Dict[str, Any]:
    """Convert a VerificationResult to a JSON-serialisable dict."""
    return {
        "passed": result.passed,
        "timestamp": result.timestamp,
        "checks": [
            {
                "check": c.check,
                "passed": c.passed,
                "path": c.path,
                "details": c.details,
            }
            for c in result.checks
        ],
    }


def register_agent_deployment_routes(app, config_event_handler, config_file_watcher):
    """Register agent deployment routes on the aiohttp app.

    Args:
        app: The aiohttp web application.
        config_event_handler: ConfigEventHandler for Socket.IO events.
        config_file_watcher: ConfigFileWatcher for mtime tracking.
    """
    _handler = config_event_handler

    # ------------------------------------------------------------------
    # POST /api/config/agents/deploy
    # ------------------------------------------------------------------
    async def deploy_agent(request: web.Request) -> web.Response:
        """Deploy an agent from cache to the project."""
        try:
            body = await request.json()
        except Exception:
            return _error_response(400, "Invalid JSON body", "VALIDATION_ERROR")

        agent_name = body.get("agent_name", "").strip()
        _source_id = body.get("source_id")
        force = body.get("force", False)

        if not agent_name:
            return _error_response(400, "agent_name is required", "VALIDATION_ERROR")

        # C-01: Validate agent name to prevent path traversal
        valid, err_msg = validate_safe_name(agent_name, "agent")
        if not valid:
            return _error_response(400, err_msg, "VALIDATION_ERROR")

        agents_dir = Path.cwd() / ".claude" / "agents"
        agent_path = agents_dir / f"{agent_name}.md"

        # Path containment check (defence in depth)
        valid, err_msg = validate_path_containment(agent_path, agents_dir, "agent")
        if not valid:
            return _error_response(400, err_msg, "VALIDATION_ERROR")

        # Conflict check
        if agent_path.exists() and not force:
            return _error_response(
                409,
                f"Agent '{agent_name}' already deployed. Use force=true to redeploy.",
                "CONFLICT",
            )

        try:

            def _deploy_sync():
                backup_mgr = _get_backup_manager()
                journal = _get_operation_journal()
                verifier = _get_deployment_verifier()
                svc = _get_agent_deployment_service()

                # 1. Backup
                backup = backup_mgr.create_backup("deploy_agent", "agent", agent_name)

                # 2. Journal
                op_id = journal.begin_operation(
                    "deploy_agent", "agent", agent_name, backup.backup_id
                )

                try:
                    # 3. Deploy via service
                    agents_dir.mkdir(parents=True, exist_ok=True)
                    success = svc.deploy_agent(
                        agent_name, agents_dir, force_rebuild=force
                    )

                    if not success:
                        raise RuntimeError(
                            f"AgentDeploymentService.deploy_agent returned False for '{agent_name}'"
                        )

                    # 4. Verify
                    verification = verifier.verify_agent_deployed(agent_name)

                    # 5. Complete journal
                    journal.complete_operation(op_id)

                    return {
                        "backup_id": backup.backup_id,
                        "verification": _verification_to_dict(verification),
                    }

                except Exception as exc:
                    journal.fail_operation(op_id, str(exc))
                    raise

            result = await asyncio.to_thread(_deploy_sync)

            # Detect active sessions (non-blocking best effort)
            try:
                from claude_mpm.services.config_api.session_detector import (
                    detect_active_claude_sessions,
                )

                sessions = await asyncio.to_thread(detect_active_claude_sessions)
            except Exception:
                sessions = []

            # Socket.IO event
            await _handler.emit_config_event(
                operation="agent_deployed",
                entity_type="agent",
                entity_id=agent_name,
                status="completed",
                data={"agent_name": agent_name, "action": "deploy"},
            )

            return web.json_response(
                {
                    "success": True,
                    "message": f"Agent '{agent_name}' deployed successfully",
                    "agent_name": agent_name,
                    "backup_id": result["backup_id"],
                    "verification": result["verification"],
                    "active_sessions_warning": len(sessions) > 0,
                    "active_sessions": sessions,
                },
                status=201,
            )

        except Exception as e:
            logger.error("Error deploying agent '%s': %s", agent_name, e)
            return _error_response(500, str(e), "DEPLOY_FAILED")

    # ------------------------------------------------------------------
    # DELETE /api/config/agents/{agent_name}
    # ------------------------------------------------------------------
    async def undeploy_agent(request: web.Request) -> web.Response:
        """Remove a deployed agent."""
        agent_name = request.match_info["agent_name"]

        # C-01: Validate agent name to prevent path traversal
        valid, err_msg = validate_safe_name(agent_name, "agent")
        if not valid:
            return _error_response(400, err_msg, "VALIDATION_ERROR")

        # BR-01: core agent protection
        if agent_name in CORE_AGENTS:
            return _error_response(
                403,
                f"Cannot undeploy core agent '{agent_name}'. "
                "Core agents are protected.",
                "CORE_AGENT_PROTECTED",
            )

        agents_dir = Path.cwd() / ".claude" / "agents"
        agent_path = agents_dir / f"{agent_name}.md"

        # Path containment check (defence in depth)
        valid, err_msg = validate_path_containment(agent_path, agents_dir, "agent")
        if not valid:
            return _error_response(400, err_msg, "VALIDATION_ERROR")

        if not agent_path.exists():
            return _error_response(
                404,
                f"Agent '{agent_name}' is not deployed",
                "NOT_FOUND",
            )

        try:

            def _undeploy_sync():
                backup_mgr = _get_backup_manager()
                journal = _get_operation_journal()
                verifier = _get_deployment_verifier()

                # 1. Backup
                backup = backup_mgr.create_backup("undeploy_agent", "agent", agent_name)

                # 2. Journal
                op_id = journal.begin_operation(
                    "undeploy_agent", "agent", agent_name, backup.backup_id
                )

                try:
                    # 3. Remove file
                    agent_path.unlink()

                    # 4. Verify removal
                    verification = verifier.verify_agent_undeployed(agent_name)

                    # 5. Complete
                    journal.complete_operation(op_id)

                    return {
                        "backup_id": backup.backup_id,
                        "verification": _verification_to_dict(verification),
                    }

                except Exception as exc:
                    journal.fail_operation(op_id, str(exc))
                    raise

            result = await asyncio.to_thread(_undeploy_sync)

            # Socket.IO event
            await _handler.emit_config_event(
                operation="agent_undeployed",
                entity_type="agent",
                entity_id=agent_name,
                status="completed",
                data={"agent_name": agent_name, "action": "undeploy"},
            )

            return web.json_response(
                {
                    "success": True,
                    "message": f"Agent '{agent_name}' undeployed",
                    "agent_name": agent_name,
                    "backup_id": result["backup_id"],
                    "verification": result["verification"],
                }
            )

        except Exception as e:
            logger.error("Error undeploying agent '%s': %s", agent_name, e)
            return _error_response(500, str(e), "SERVICE_ERROR")

    # ------------------------------------------------------------------
    # POST /api/config/agents/deploy-collection
    # ------------------------------------------------------------------
    async def deploy_collection(request: web.Request) -> web.Response:
        """Batch deploy agents. Sequential, continues on individual failure."""
        try:
            body = await request.json()
        except Exception:
            return _error_response(400, "Invalid JSON body", "VALIDATION_ERROR")

        agent_names = body.get("agent_names", [])
        _source_id = body.get("source_id")
        force = body.get("force", False)

        if not agent_names or not isinstance(agent_names, list):
            return _error_response(
                400, "agent_names must be a non-empty list", "VALIDATION_ERROR"
            )

        results = []
        deployed = []
        failed = []
        start_time = time.time()

        for idx, agent_name in enumerate(agent_names):
            # C-01: Validate each agent name to prevent path traversal
            valid, err_msg = validate_safe_name(agent_name, "agent")
            if not valid:
                failed.append(agent_name)
                results.append(
                    {"agent_name": agent_name, "success": False, "error": err_msg}
                )
                logger.warning(
                    "Batch deploy: agent '%s' rejected: %s", agent_name, err_msg
                )
                continue

            try:

                def _deploy_one(name=agent_name):
                    agents_dir = Path.cwd() / ".claude" / "agents"
                    agents_dir.mkdir(parents=True, exist_ok=True)

                    backup_mgr = _get_backup_manager()
                    journal = _get_operation_journal()
                    verifier = _get_deployment_verifier()
                    svc = _get_agent_deployment_service()

                    backup = backup_mgr.create_backup(
                        "deploy_agent_batch", "agent", name
                    )
                    op_id = journal.begin_operation(
                        "deploy_agent_batch", "agent", name, backup.backup_id
                    )
                    try:
                        success = svc.deploy_agent(
                            name, agents_dir, force_rebuild=force
                        )
                        if not success:
                            raise RuntimeError(
                                f"deploy_agent returned False for '{name}'"
                            )
                        verification = verifier.verify_agent_deployed(name)
                        journal.complete_operation(op_id)
                        return {
                            "success": True,
                            "verification": _verification_to_dict(verification),
                        }
                    except Exception as exc:
                        journal.fail_operation(op_id, str(exc))
                        raise

                result = await asyncio.to_thread(_deploy_one)
                deployed.append(agent_name)
                results.append({"agent_name": agent_name, **result})

                # Per-agent Socket.IO progress
                await _handler.emit_config_event(
                    operation="agent_deployed",
                    entity_type="agent",
                    entity_id=agent_name,
                    status="completed",
                    data={
                        "agent_name": agent_name,
                        "action": "deploy",
                        "batch_progress": f"{idx + 1}/{len(agent_names)}",
                    },
                )

            except Exception as e:
                failed.append(agent_name)
                results.append(
                    {"agent_name": agent_name, "success": False, "error": str(e)}
                )
                logger.warning("Batch deploy: agent '%s' failed: %s", agent_name, e)

        duration_ms = int((time.time() - start_time) * 1000)

        return web.json_response(
            {
                "success": len(failed) == 0,
                "results": results,
                "summary": {
                    "total": len(agent_names),
                    "deployed": len(deployed),
                    "failed": len(failed),
                    "duration_ms": duration_ms,
                },
                "deployed_agents": deployed,
                "failed_agents": failed,
            }
        )

    # ------------------------------------------------------------------
    # GET /api/config/agents/collections
    # ------------------------------------------------------------------
    async def list_collections(request: web.Request) -> web.Response:
        """List agent collections from source metadata."""
        try:

            def _list():
                from claude_mpm.config.agent_sources import AgentSourceConfiguration

                config = AgentSourceConfiguration.load()
                collections = []
                for repo in config.repositories:
                    collections.append(
                        {
                            "id": repo.identifier,
                            "url": getattr(repo, "url", ""),
                            "subdirectory": getattr(repo, "subdirectory", None),
                            "enabled": getattr(repo, "enabled", True),
                            "priority": getattr(repo, "priority", 100),
                        }
                    )
                return collections

            collections = await asyncio.to_thread(_list)
            return web.json_response(
                {
                    "success": True,
                    "collections": collections,
                    "total": len(collections),
                }
            )

        except Exception as e:
            logger.error("Error listing agent collections: %s", e)
            return _error_response(500, str(e), "SERVICE_ERROR")

    # ------------------------------------------------------------------
    # GET /api/config/active-sessions
    # ------------------------------------------------------------------
    async def get_active_sessions(request: web.Request) -> web.Response:
        """Detect active Claude Code sessions."""
        try:
            from claude_mpm.services.config_api.session_detector import (
                detect_active_claude_sessions,
            )

            sessions = await asyncio.to_thread(detect_active_claude_sessions)

            has_active = len(sessions) > 0
            warning = (
                "Active Claude Code sessions detected. "
                "Changes may not take effect until sessions are restarted."
                if has_active
                else ""
            )

            return web.json_response(
                {
                    "success": True,
                    "active_sessions": sessions,
                    "has_active_sessions": has_active,
                    "warning_message": warning,
                }
            )

        except Exception as e:
            logger.error("Error detecting active sessions: %s", e)
            return _error_response(500, str(e), "SERVICE_ERROR")

    # Register routes
    app.router.add_post("/api/config/agents/deploy", deploy_agent)
    app.router.add_delete("/api/config/agents/{agent_name}", undeploy_agent)
    app.router.add_post("/api/config/agents/deploy-collection", deploy_collection)
    app.router.add_get("/api/config/agents/collections", list_collections)
    app.router.add_get("/api/config/active-sessions", get_active_sessions)

    logger.info(
        "Registered 5 agent deployment routes under /api/config/agents/ "
        "(+ /api/config/active-sessions)"
    )
