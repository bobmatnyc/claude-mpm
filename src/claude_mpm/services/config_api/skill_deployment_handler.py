"""Skill deployment API routes for the Claude MPM Dashboard.

Phase 3: Endpoint handlers for deploying/undeploying skills and
switching deployment modes. Every destructive operation follows the
safety protocol: backup -> journal -> execute -> verify -> prune.

All blocking service calls are wrapped in asyncio.to_thread().
ConfigFileLock is used for all configuration file writes.
"""

import asyncio
from pathlib import Path
from typing import Any

import yaml
from aiohttp import web

from claude_mpm.core.config_file_lock import (
    ConfigFileLockTimeout,
    config_file_lock,
)
from claude_mpm.core.deployment_context import DeploymentContext
from claude_mpm.core.logging_config import get_logger
from claude_mpm.services.config_api.validation import validate_safe_name

logger = get_logger(__name__)

# Lazy-initialized service singletons
_backup_manager = None
_operation_journal = None
_deployment_verifier = None
_skills_deployer = None


def _get_backup_manager():
    """Return the module-level BackupManager singleton, creating it on first call.

    WHY: Lazy initialisation avoids importing BackupManager at module load time and
    ensures that DeploymentContext.from_project() is called only once, reusing the
    same skills_dir across all route handlers in this module.
    WHAT: Creates BackupManager seeded with the project skills directory; caches it.
    TEST: Call twice; assert both return values are the same object (identity check).
    """
    global _backup_manager
    if _backup_manager is None:
        from claude_mpm.services.config_api.backup_manager import BackupManager

        ctx = DeploymentContext.from_project()
        _backup_manager = BackupManager(skills_dir=ctx.skills_dir)
    return _backup_manager


def _get_operation_journal():
    """Return the module-level OperationJournal singleton, creating it on first call.

    WHY: A single shared journal ensures all skill operations in this process are
    recorded in the same log without competing initialisation.
    WHAT: Lazily imports and instantiates OperationJournal; caches in module global.
    TEST: Call twice; assert both return values are the same object.
    """
    global _operation_journal
    if _operation_journal is None:
        from claude_mpm.services.config_api.operation_journal import OperationJournal

        _operation_journal = OperationJournal()
    return _operation_journal


def _get_deployment_verifier():
    """Return the module-level DeploymentVerifier singleton, creating it on first call.

    WHY: Verification is needed after every deploy/undeploy; a singleton avoids repeated
    construction overhead across the many route handlers in this module.
    WHAT: Lazily imports and instantiates DeploymentVerifier; caches in module global.
    TEST: Call twice; assert both return values are the same object.
    """
    global _deployment_verifier
    if _deployment_verifier is None:
        from claude_mpm.services.config_api.deployment_verifier import (
            DeploymentVerifier,
        )

        _deployment_verifier = DeploymentVerifier()
    return _deployment_verifier


def _get_skills_deployer():
    """Return the module-level SkillsDeployerService singleton, creating it on first call.

    WHY: Skills deployment service is used in every deploy/undeploy route; a singleton
    avoids re-initialisation and allows internal caches to persist across requests.
    WHAT: Lazily imports and instantiates SkillsDeployerService; caches in module global.
    TEST: Call twice; assert both return values are the same object.
    """
    global _skills_deployer
    if _skills_deployer is None:
        from claude_mpm.services.skills_deployer import SkillsDeployerService

        _skills_deployer = SkillsDeployerService()
    return _skills_deployer


def _get_immutable_skills():
    """Return the union of PM_CORE_SKILLS and CORE_SKILLS."""
    from claude_mpm.services.skills.selective_skill_deployer import (
        CORE_SKILLS,
        PM_CORE_SKILLS,
    )

    return PM_CORE_SKILLS | CORE_SKILLS


def _error_response(status: int, error: str, code: str) -> web.Response:
    """Build a standardised JSON error response for skill deployment API endpoints.

    WHY: Consistent error shape lets front-end code rely on a single schema for all
    failure responses instead of handling ad-hoc formats from each handler.
    WHAT: Returns a web.Response with JSON body ``{success: false, error: ..., code: ...}``
    and the given HTTP status code.
    TEST: Call with (409, "already deployed", "CONFLICT"); assert response.status==409
    and parsed JSON contains the expected keys with those values.
    """
    return web.json_response(
        {"success": False, "error": error, "code": code},
        status=status,
    )


def _verification_to_dict(result) -> dict[str, Any]:
    """Convert a VerificationResult object to a JSON-serialisable dict.

    WHY: VerificationResult is a domain object that cannot be directly serialised to
    JSON; this adapter makes it safe to embed in API responses.
    WHAT: Extracts passed flag, timestamp, and list of check dicts from the result object.
    TEST: Build a mock VerificationResult with known passed/checks values; call this;
    assert the returned dict mirrors those values exactly.
    """
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


def _get_config_path() -> Path:
    """Return the project configuration.yaml path."""
    return Path.cwd() / ".claude-mpm" / "configuration.yaml"


def _load_config(config_path: Path) -> dict:
    """Load configuration.yaml safely."""
    if not config_path.exists():
        return {}
    return yaml.safe_load(config_path.read_text()) or {}


def register_skill_deployment_routes(app, config_event_handler, config_file_watcher):
    """Register skill deployment routes on the aiohttp app.

    Args:
        app: The aiohttp web application.
        config_event_handler: ConfigEventHandler for Socket.IO events.
        config_file_watcher: ConfigFileWatcher for mtime tracking.
    """
    _handler = config_event_handler
    _watcher = config_file_watcher

    # ------------------------------------------------------------------
    # POST /api/config/skills/deploy
    # ------------------------------------------------------------------
    async def deploy_skill(request: web.Request) -> web.Response:
        """Deploy a skill from cache."""
        try:
            body = await request.json()
        except Exception:
            return _error_response(400, "Invalid JSON body", "VALIDATION_ERROR")

        skill_name = body.get("skill_name", "").strip()
        collection = body.get("collection")
        mark_user_requested = body.get("mark_user_requested", False)
        force = body.get("force", False)

        # Scope validation (R-3: null-safe)
        scope_str = body.get("scope", "project") or "project"
        try:
            ctx = DeploymentContext.from_request_scope(scope_str)
        except ValueError as e:
            return _error_response(400, str(e), "VALIDATION_ERROR")

        if not skill_name:
            return _error_response(400, "skill_name is required", "VALIDATION_ERROR")

        # C-02: Validate skill name to prevent path traversal
        valid, err_msg = validate_safe_name(skill_name, "skill")
        if not valid:
            return _error_response(400, err_msg, "VALIDATION_ERROR")

        try:

            def _deploy_sync():
                skills_dir = ctx.skills_dir

                backup_mgr = _get_backup_manager()
                journal = _get_operation_journal()
                verifier = _get_deployment_verifier()
                svc = _get_skills_deployer()

                # 1. Backup
                backup = backup_mgr.create_backup("deploy_skill", "skill", skill_name)

                # 2. Journal
                op_id = journal.begin_operation(
                    "deploy_skill", "skill", skill_name, backup.backup_id
                )

                try:
                    # 3. Deploy
                    result = svc.deploy_skills(
                        collection=collection,
                        skill_names=[skill_name],
                        force=force,
                        selective=False,
                    )

                    if result.get("errors"):
                        raise RuntimeError(
                            f"Skill deployment errors: {result['errors']}"
                        )

                    # 3b. Mark user-requested in config
                    if mark_user_requested:
                        config_path = ctx.configuration_yaml
                        with config_file_lock(config_path):
                            cfg = _load_config(config_path)
                            skills_cfg = cfg.setdefault("skills", {})
                            user_defined = skills_cfg.setdefault("user_defined", [])
                            if skill_name not in user_defined:
                                user_defined.append(skill_name)
                            config_path.parent.mkdir(parents=True, exist_ok=True)
                            config_path.write_text(
                                yaml.dump(
                                    cfg, default_flow_style=False, sort_keys=False
                                )
                            )

                    # 4. Verify
                    verification = verifier.verify_skill_deployed(
                        skill_name, skills_dir=skills_dir
                    )

                    # 5. Complete
                    journal.complete_operation(op_id)

                    return {
                        "backup_id": backup.backup_id,
                        "deploy_result": {
                            "deployed_count": result.get("deployed_count", 0),
                            "deployed_skills": result.get("deployed_skills", []),
                        },
                        "verification": _verification_to_dict(verification),
                    }

                except Exception as exc:
                    journal.fail_operation(op_id, str(exc))
                    raise

            result = await asyncio.to_thread(_deploy_sync)

            if mark_user_requested:
                _watcher.update_mtime(ctx.configuration_yaml)

            await _handler.emit_config_event(
                operation="skill_deployed",
                entity_type="skill",
                entity_id=skill_name,
                status="completed",
                data={"skill_name": skill_name, "action": "deploy", "scope": scope_str},
            )

            return web.json_response(
                {
                    "success": True,
                    "message": f"Skill '{skill_name}' deployed successfully",
                    "skill_name": skill_name,
                    "scope": scope_str,
                    **result,
                },
                status=201,
            )

        except ConfigFileLockTimeout as e:
            return _error_response(423, str(e), "LOCK_TIMEOUT")
        except Exception as e:
            logger.error("Error deploying skill '%s': %s", skill_name, e)
            return _error_response(500, str(e), "DEPLOY_FAILED")

    # ------------------------------------------------------------------
    # DELETE /api/config/skills/{skill_name}
    # ------------------------------------------------------------------
    async def undeploy_skill(request: web.Request) -> web.Response:
        """Remove a deployed skill."""
        skill_name = request.match_info["skill_name"]

        # Scope validation (query param for DELETE)
        scope_str = request.rel_url.query.get("scope", "project") or "project"
        try:
            ctx = DeploymentContext.from_request_scope(scope_str)
        except ValueError as e:
            return _error_response(400, str(e), "VALIDATION_ERROR")

        # C-02: Validate skill name to prevent path traversal
        valid, err_msg = validate_safe_name(skill_name, "skill")
        if not valid:
            return _error_response(400, err_msg, "VALIDATION_ERROR")

        # Immutability check
        immutable = _get_immutable_skills()
        if skill_name in immutable:
            return _error_response(
                403,
                f"Cannot undeploy immutable skill '{skill_name}'. "
                "Core/PM skills are protected.",
                "IMMUTABLE_SKILL",
            )

        try:

            def _undeploy_sync():
                skills_dir = ctx.skills_dir

                backup_mgr = _get_backup_manager()
                journal = _get_operation_journal()
                verifier = _get_deployment_verifier()
                svc = _get_skills_deployer()

                # 1. Backup
                backup = backup_mgr.create_backup("undeploy_skill", "skill", skill_name)

                # 2. Journal
                op_id = journal.begin_operation(
                    "undeploy_skill", "skill", skill_name, backup.backup_id
                )

                try:
                    # 3. Remove
                    result = svc.remove_skills([skill_name])

                    if result.get("errors"):
                        raise RuntimeError(f"Skill removal errors: {result['errors']}")

                    # 4. Verify
                    verification = verifier.verify_skill_undeployed(
                        skill_name, skills_dir=skills_dir
                    )

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

            await _handler.emit_config_event(
                operation="skill_undeployed",
                entity_type="skill",
                entity_id=skill_name,
                status="completed",
                data={
                    "skill_name": skill_name,
                    "action": "undeploy",
                    "scope": scope_str,
                },
            )

            return web.json_response(
                {
                    "success": True,
                    "message": f"Skill '{skill_name}' undeployed",
                    "skill_name": skill_name,
                    "scope": scope_str,
                    **result,
                }
            )

        except Exception as e:
            logger.error("Error undeploying skill '%s': %s", skill_name, e)
            return _error_response(500, str(e), "SERVICE_ERROR")

    # ------------------------------------------------------------------
    # GET /api/config/skills/deployment-mode
    # ------------------------------------------------------------------
    async def get_deployment_mode(request: web.Request) -> web.Response:
        """Return current skill deployment mode with counts."""
        # Scope validation (query param for GET)
        scope_str = request.rel_url.query.get("scope", "project") or "project"
        try:
            ctx = DeploymentContext.from_request_scope(scope_str)
        except ValueError as e:
            return _error_response(400, str(e), "VALIDATION_ERROR")

        try:

            def _get_mode():
                config_path = ctx.configuration_yaml
                cfg = _load_config(config_path)
                skills_cfg = cfg.get("skills", {})

                mode = skills_cfg.get("deployment_mode", "selective")
                agent_referenced = skills_cfg.get("agent_referenced", [])
                user_defined = skills_cfg.get("user_defined", [])

                # Count deployed
                svc = _get_skills_deployer()
                deployed = svc.check_deployed_skills()

                # Count core skills
                _immutable = _get_immutable_skills()
                from claude_mpm.services.skills.selective_skill_deployer import (
                    CORE_SKILLS,
                    PM_CORE_SKILLS,
                )

                return {
                    "mode": mode,
                    "counts": {
                        "agent_referenced": len(agent_referenced),
                        "user_defined": len(user_defined),
                        "pm_core": len(PM_CORE_SKILLS),
                        "core": len(CORE_SKILLS),
                        "total_deployed": deployed.get("deployed_count", 0),
                    },
                    "explanation": (
                        "selective: Only agent-referenced + user-defined + core skills"
                        if mode == "selective"
                        else "full: All available skills are deployed"
                    ),
                }

            data = await asyncio.to_thread(_get_mode)
            return web.json_response({"success": True, "scope": scope_str, **data})

        except Exception as e:
            logger.error("Error getting deployment mode: %s", e)
            return _error_response(500, str(e), "SERVICE_ERROR")

    # ------------------------------------------------------------------
    # PUT /api/config/skills/deployment-mode
    # ------------------------------------------------------------------
    async def set_deployment_mode(request: web.Request) -> web.Response:
        """Two-step mode switch: preview=true -> impact, confirm=true -> apply."""
        try:
            body = await request.json()
        except Exception:
            return _error_response(400, "Invalid JSON body", "VALIDATION_ERROR")

        target_mode = body.get("mode", "").strip()
        preview = body.get("preview", False)
        confirm = body.get("confirm", False)
        _skill_list = body.get("skill_list")  # For selective mode

        # Scope validation (R-3: null-safe)
        scope_str = body.get("scope", "project") or "project"
        try:
            ctx = DeploymentContext.from_request_scope(scope_str)
        except ValueError as e:
            return _error_response(400, str(e), "VALIDATION_ERROR")

        if target_mode not in ("selective", "full"):
            return _error_response(
                400,
                "mode must be 'selective' or 'full'",
                "VALIDATION_ERROR",
            )

        if not preview and not confirm:
            return _error_response(
                400,
                "Either preview=true or confirm=true is required",
                "CONFIRMATION_REQUIRED",
            )

        try:

            def _check_current():
                config_path = ctx.configuration_yaml
                cfg = _load_config(config_path)
                return cfg.get("skills", {}).get("deployment_mode", "selective")

            current_mode = await asyncio.to_thread(_check_current)

            if current_mode == target_mode:
                return _error_response(
                    409,
                    f"Already in '{target_mode}' mode",
                    "ALREADY_IN_MODE",
                )

            # Preview: show impact without applying
            if preview:

                def _preview():
                    svc = _get_skills_deployer()
                    deployed = svc.check_deployed_skills()
                    deployed_names = {
                        s.get("name", "") for s in deployed.get("skills", [])
                    }

                    if target_mode == "selective":
                        config_path = ctx.configuration_yaml
                        cfg = _load_config(config_path)
                        skills_cfg = cfg.get("skills", {})
                        allowed = set(skills_cfg.get("agent_referenced", []))
                        allowed |= set(skills_cfg.get("user_defined", []))
                        allowed |= _get_immutable_skills()

                        would_remove = deployed_names - allowed
                        would_keep = deployed_names & allowed

                        if not allowed:
                            return {
                                "error": True,
                                "code": "EMPTY_SKILL_LIST",
                                "message": "No skills would remain after switching to selective mode",
                            }

                        return {
                            "error": False,
                            "target_mode": target_mode,
                            "impact": {
                                "would_remove": sorted(would_remove),
                                "would_keep": sorted(would_keep),
                                "remove_count": len(would_remove),
                                "keep_count": len(would_keep),
                            },
                        }
                    # full mode: nothing removed, all deployed
                    return {
                        "error": False,
                        "target_mode": target_mode,
                        "impact": {
                            "would_remove": [],
                            "would_keep": sorted(deployed_names),
                            "remove_count": 0,
                            "keep_count": len(deployed_names),
                            "note": "All available skills will be deployed on next sync",
                        },
                    }

                preview_data = await asyncio.to_thread(_preview)

                if (
                    preview_data.get("error")
                    and preview_data.get("code") == "EMPTY_SKILL_LIST"
                ):
                    return _error_response(
                        400, preview_data["message"], "EMPTY_SKILL_LIST"
                    )

                return web.json_response(
                    {"success": True, "preview": True, **preview_data}
                )

            # Confirm: apply the mode switch
            if confirm:

                def _apply():
                    config_path = ctx.configuration_yaml
                    backup_mgr = _get_backup_manager()
                    journal = _get_operation_journal()
                    verifier = _get_deployment_verifier()

                    # Backup
                    backup = backup_mgr.create_backup(
                        "mode_switch", "config", f"mode:{target_mode}"
                    )

                    op_id = journal.begin_operation(
                        "mode_switch",
                        "config",
                        f"mode:{target_mode}",
                        backup.backup_id,
                    )

                    try:
                        with config_file_lock(config_path):
                            cfg = _load_config(config_path)
                            skills_cfg = cfg.setdefault("skills", {})

                            # Block empty skill list on selective
                            if target_mode == "selective":
                                allowed = set(skills_cfg.get("agent_referenced", []))
                                allowed |= set(skills_cfg.get("user_defined", []))
                                allowed |= _get_immutable_skills()
                                if not allowed:
                                    raise ValueError(
                                        "Cannot switch to selective mode: "
                                        "no skills in agent_referenced or user_defined"
                                    )

                            skills_cfg["deployment_mode"] = target_mode
                            config_path.parent.mkdir(parents=True, exist_ok=True)
                            config_path.write_text(
                                yaml.dump(
                                    cfg, default_flow_style=False, sort_keys=False
                                )
                            )

                        verification = verifier.verify_mode_switch(
                            target_mode, config_path
                        )

                        journal.complete_operation(op_id)

                        return {
                            "backup_id": backup.backup_id,
                            "verification": _verification_to_dict(verification),
                        }

                    except Exception as exc:
                        journal.fail_operation(op_id, str(exc))
                        raise

                result = await asyncio.to_thread(_apply)

                _watcher.update_mtime(ctx.configuration_yaml)

                await _handler.emit_config_event(
                    operation="mode_switched",
                    entity_type="config",
                    entity_id=f"mode:{target_mode}",
                    status="completed",
                    data={"new_mode": target_mode, "scope": scope_str},
                )

                return web.json_response(
                    {
                        "success": True,
                        "message": f"Deployment mode switched to '{target_mode}'",
                        "mode": target_mode,
                        "scope": scope_str,
                        **result,
                    }
                )

        except ConfigFileLockTimeout as e:
            return _error_response(423, str(e), "LOCK_TIMEOUT")
        except ValueError as e:
            error_msg = str(e)
            if "no skills" in error_msg.lower():
                return _error_response(400, error_msg, "EMPTY_SKILL_LIST")
            return _error_response(400, error_msg, "VALIDATION_ERROR")
        except Exception as e:
            logger.error("Error switching deployment mode: %s", e)
            return _error_response(500, str(e), "SERVICE_ERROR")

    # Register routes
    app.router.add_post("/api/config/skills/deploy", deploy_skill)
    app.router.add_delete("/api/config/skills/{skill_name}", undeploy_skill)
    app.router.add_get("/api/config/skills/deployment-mode", get_deployment_mode)
    app.router.add_put("/api/config/skills/deployment-mode", set_deployment_mode)

    logger.info("Registered 4 skill deployment routes under /api/config/skills/")
