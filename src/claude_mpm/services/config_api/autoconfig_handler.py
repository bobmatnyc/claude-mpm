"""Auto-configure API routes for the Claude MPM Dashboard.

Phase 3: Endpoint handlers for toolchain detection, configuration
preview, and long-running auto-configure apply with Socket.IO progress.

All blocking service calls are wrapped in asyncio.to_thread() because
the underlying services (ToolchainAnalyzerService, AutoConfigManagerService)
use synchronous or run_until_complete patterns internally.
"""

import asyncio
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from aiohttp import web

from claude_mpm.core.config_scope import (
    ConfigScope,
    resolve_agents_dir,
    resolve_skills_dir,
)
from claude_mpm.core.logging_config import get_logger

logger = get_logger(__name__)

# Lazy-initialized service singletons
_toolchain_analyzer = None
_auto_config_manager = None
_backup_manager = None
_skills_deployer = None

# In-flight auto-configure jobs
_active_jobs: Dict[str, asyncio.Task] = {}


def _get_toolchain_analyzer():
    global _toolchain_analyzer
    if _toolchain_analyzer is None:
        from claude_mpm.services.project.toolchain_analyzer import (
            ToolchainAnalyzerService,
        )

        _toolchain_analyzer = ToolchainAnalyzerService()
    return _toolchain_analyzer


def _get_auto_config_manager():
    global _auto_config_manager
    if _auto_config_manager is None:
        try:
            from claude_mpm.services.agents.auto_config_manager import (
                AutoConfigManagerService,
            )
            from claude_mpm.services.agents.recommender import (
                AgentRecommenderService,
            )

            # Reuse the existing toolchain analyzer singleton
            toolchain_analyzer = _get_toolchain_analyzer()
            agent_recommender = AgentRecommenderService()

            # AgentRegistry improves validation quality (Issue #9)
            # but is not strictly required -- degrade gracefully if unavailable
            agent_registry = None
            try:
                from claude_mpm.services.agents.registry import AgentRegistry

                agent_registry = AgentRegistry()
            except Exception:
                logger.warning(
                    "AgentRegistry not available; validation will skip agent existence checks"
                )

            _auto_config_manager = AutoConfigManagerService(
                toolchain_analyzer=toolchain_analyzer,
                agent_recommender=agent_recommender,
                agent_registry=agent_registry,
            )
        except Exception:
            # Do NOT cache a broken instance -- let next request retry (Issue #7)
            logger.error("Failed to initialize AutoConfigManagerService", exc_info=True)
            raise
    return _auto_config_manager


def _reset_auto_config_manager():
    """Reset the auto-config manager singleton (for testing and error recovery)."""
    global _auto_config_manager
    _auto_config_manager = None


def _get_backup_manager():
    global _backup_manager
    if _backup_manager is None:
        from claude_mpm.services.config_api.backup_manager import BackupManager

        _backup_manager = BackupManager()
    return _backup_manager


def _get_skills_deployer():
    global _skills_deployer
    if _skills_deployer is None:
        from claude_mpm.services.skills_deployer import SkillsDeployerService

        _skills_deployer = SkillsDeployerService()
    return _skills_deployer


def _error_response(status: int, error: str, code: str) -> web.Response:
    return web.json_response(
        {"success": False, "error": error, "code": code},
        status=status,
    )


def _toolchain_to_dict(analysis) -> Dict[str, Any]:
    """Serialise a ToolchainAnalysis to a JSON-safe dict."""
    result: Dict[str, Any] = {
        "primary_language": getattr(
            analysis.language_detection, "primary_language", "Unknown"
        ),
        "primary_confidence": getattr(
            analysis.language_detection.primary_confidence, "value", "unknown"
        ),
    }

    # Frameworks
    result["frameworks"] = [
        {
            "name": fw.name,
            "version": fw.version,
            "framework_type": getattr(fw, "framework_type", ""),
            "confidence": getattr(fw.confidence, "value", "unknown"),
        }
        for fw in (analysis.frameworks or [])
    ]

    # Build tools
    result["build_tools"] = [
        {"name": bt.name, "confidence": getattr(bt.confidence, "value", "unknown")}
        for bt in (analysis.build_tools or [])
    ]

    # Package managers
    result["package_managers"] = [
        {"name": pm.name, "confidence": getattr(pm.confidence, "value", "unknown")}
        for pm in (analysis.package_managers or [])
    ]

    # Deployment target
    dt = analysis.deployment_target
    if dt:
        result["deployment_target"] = {
            "target_type": dt.target_type,
            "platform": dt.platform,
            "confidence": getattr(dt.confidence, "value", "unknown"),
        }
    else:
        result["deployment_target"] = None

    # Overall confidence
    result["overall_confidence"] = getattr(
        analysis.overall_confidence, "value", "unknown"
    )

    # Metadata
    result["metadata"] = analysis.metadata or {}

    return result


def _preview_to_dict(preview) -> Dict[str, Any]:
    """Serialise a ConfigurationPreview to a JSON-safe dict."""
    result: Dict[str, Any] = {
        "would_deploy": preview.would_deploy,
        "would_skip": preview.would_skip,
        "deployment_count": preview.deployment_count,
        "estimated_deployment_time": preview.estimated_deployment_time,
        "requires_confirmation": preview.requires_confirmation,
    }

    # Recommendations
    result["recommendations"] = []
    for rec in preview.recommendations or []:
        result["recommendations"].append(
            {
                "agent_id": rec.agent_id,
                "agent_name": rec.agent_name,
                "confidence_score": rec.confidence_score,
                "rationale": rec.reasoning,
                "match_reasons": rec.match_reasons,
                "deployment_priority": rec.deployment_priority,
            }
        )

    # Validation
    vr = preview.validation_result
    if vr:
        result["validation"] = {
            "is_valid": vr.is_valid,
            "error_count": vr.error_count,
            "warning_count": vr.warning_count,
        }
    else:
        result["validation"] = None

    # Toolchain
    if preview.detected_toolchain:
        result["toolchain"] = _toolchain_to_dict(preview.detected_toolchain)

    result["metadata"] = preview.metadata or {}
    return result


def register_autoconfig_routes(app, config_event_handler, config_file_watcher):
    """Register auto-configure routes on the aiohttp app.

    Args:
        app: The aiohttp web application.
        config_event_handler: ConfigEventHandler for Socket.IO events.
        config_file_watcher: ConfigFileWatcher for mtime tracking.
    """
    _handler = config_event_handler

    # ------------------------------------------------------------------
    # POST /api/config/auto-configure/detect
    # ------------------------------------------------------------------
    async def detect_toolchain(request: web.Request) -> web.Response:
        """Detect project toolchain. Uses the analyser's 5-min TTL cache."""
        try:
            body = {}
            try:
                body = await request.json()
            except Exception:  # nosec B110
                pass  # Body is optional for detect

            project_path = Path(body.get("project_path", str(Path.cwd())))

            if not project_path.exists():
                return _error_response(
                    400,
                    f"Project path does not exist: {project_path}",
                    "VALIDATION_ERROR",
                )

            def _detect():
                analyzer = _get_toolchain_analyzer()
                return analyzer.analyze_toolchain(project_path)

            analysis = await asyncio.to_thread(_detect)
            data = _toolchain_to_dict(analysis)

            return web.json_response({"success": True, "toolchain": data})

        except Exception as e:
            logger.error("Error detecting toolchain: %s", e)
            return _error_response(500, str(e), "SERVICE_ERROR")

    # ------------------------------------------------------------------
    # POST /api/config/auto-configure/preview
    # ------------------------------------------------------------------
    async def preview_configuration(request: web.Request) -> web.Response:
        """Get configuration recommendations without applying.

        Uses asyncio.to_thread() because preview_configuration
        performs blocking synchronous work (toolchain analysis,
        agent recommendation) that would block the event loop.
        """
        try:
            body = {}
            try:
                body = await request.json()
            except Exception:  # nosec B110
                pass

            project_path = Path(body.get("project_path", str(Path.cwd())))
            min_confidence = body.get("min_confidence", 0.5)

            if not project_path.exists():
                return _error_response(
                    400,
                    f"Project path does not exist: {project_path}",
                    "VALIDATION_ERROR",
                )

            def _preview():
                mgr = _get_auto_config_manager()
                return mgr.preview_configuration(project_path, min_confidence)

            preview = await asyncio.to_thread(_preview)
            data = _preview_to_dict(preview)

            # Add skill recommendations based on detected agents
            def _recommend_skills_for_preview():
                from claude_mpm.cli.interactive.skills_wizard import (
                    AGENT_SKILL_MAPPING,
                )

                recommended = set()
                for rec in preview.recommendations or []:
                    agent_skills = AGENT_SKILL_MAPPING.get(rec.agent_id, [])
                    recommended.update(agent_skills)
                return sorted(recommended)

            try:
                skill_recs = await asyncio.to_thread(_recommend_skills_for_preview)
            except Exception as e:
                logger.warning("Skill recommendation failed: %s", e)
                skill_recs = []

            data["skill_recommendations"] = skill_recs
            data["would_deploy_skills"] = skill_recs

            return web.json_response({"success": True, "preview": data})

        except Exception as e:
            logger.error("Error generating preview: %s", e)
            return _error_response(500, str(e), "SERVICE_ERROR")

    # ------------------------------------------------------------------
    # POST /api/config/auto-configure/apply
    # ------------------------------------------------------------------
    async def apply_configuration(request: web.Request) -> web.Response:
        """Long-running auto-configure. Returns 202 immediately.

        Emits Socket.IO progress events through the phases:
        detecting -> recommending -> validating -> deploying -> verifying
        """
        try:
            body = {}
            try:
                body = await request.json()
            except Exception:  # nosec B110
                pass

            project_path = Path(body.get("project_path", str(Path.cwd())))
            dry_run = body.get("dry_run", False)
            min_confidence = body.get("min_confidence", 0.5)

            if not project_path.exists():
                return _error_response(
                    400,
                    f"Project path does not exist: {project_path}",
                    "VALIDATION_ERROR",
                )

            job_id = f"autoconfig-{int(time.time())}-{uuid.uuid4().hex[:6]}"

            # Launch background task
            task = asyncio.create_task(
                _run_auto_configure(
                    job_id=job_id,
                    project_path=project_path,
                    dry_run=dry_run,
                    min_confidence=min_confidence,
                    handler=_handler,
                )
            )
            _active_jobs[job_id] = task

            return web.json_response(
                {
                    "success": True,
                    "message": "Auto-configure started",
                    "job_id": job_id,
                    "status": "in_progress",
                },
                status=202,
            )

        except Exception as e:
            logger.error("Error starting auto-configure: %s", e)
            return _error_response(500, str(e), "SERVICE_ERROR")

    # Register routes
    app.router.add_post("/api/config/auto-configure/detect", detect_toolchain)
    app.router.add_post("/api/config/auto-configure/preview", preview_configuration)
    app.router.add_post("/api/config/auto-configure/apply", apply_configuration)

    logger.info("Registered 3 auto-configure routes under /api/config/auto-configure/")


# ---------------------------------------------------------------------------
# Background auto-configure runner
# ---------------------------------------------------------------------------


async def _emit_progress(
    handler,
    job_id: str,
    phase: str,
    phase_number: int,
    total_phases: int,
    status: str = "in_progress",
    current_item: str = "",
    items_completed: int = 0,
    items_total: int = 0,
) -> None:
    """Emit an autoconfig_progress Socket.IO event."""
    await handler.emit_config_event(
        operation="autoconfig_progress",
        entity_type="autoconfig",
        entity_id=job_id,
        status=status,
        data={
            "job_id": job_id,
            "phase": phase,
            "phase_number": phase_number,
            "total_phases": total_phases,
            "current_item": current_item,
            "items_completed": items_completed,
            "items_total": items_total,
            "status": status,
        },
    )


async def _run_auto_configure(
    job_id: str,
    project_path: Path,
    dry_run: bool,
    min_confidence: float,
    handler,
) -> None:
    """Background task that runs the full auto-configure workflow."""
    start_time = time.time()
    total_phases = 6
    backup_id: Optional[str] = None

    try:
        # Phase 1: Detecting
        await _emit_progress(handler, job_id, "detecting", 1, total_phases)

        def _detect():
            return _get_toolchain_analyzer().analyze_toolchain(project_path)

        _analysis = await asyncio.to_thread(_detect)

        # Phase 2: Recommending
        await _emit_progress(handler, job_id, "recommending", 2, total_phases)

        def _preview():
            return _get_auto_config_manager().preview_configuration(
                project_path, min_confidence
            )

        preview = await asyncio.to_thread(_preview)

        _recommendations = preview.recommendations or []
        would_deploy = preview.would_deploy or []

        if not would_deploy:
            # Nothing to deploy - complete early
            await handler.emit_config_event(
                operation="autoconfig_completed",
                entity_type="autoconfig",
                entity_id=job_id,
                status="completed",
                data={
                    "job_id": job_id,
                    "deployed_agents": [],
                    "failed_agents": [],
                    "deployed_skills": [],
                    "skill_errors": [],
                    "needs_restart": False,
                    "backup_id": None,
                    "duration_ms": int((time.time() - start_time) * 1000),
                    "message": "No agents recommended for deployment",
                },
            )
            return

        # Phase 3: Validating
        await _emit_progress(
            handler,
            job_id,
            "validating",
            3,
            total_phases,
            items_total=len(would_deploy),
        )

        # Backup before applying
        def _backup():
            return _get_backup_manager().create_backup(
                "auto_configure", "config", job_id
            )

        backup_result = await asyncio.to_thread(_backup)
        backup_id = backup_result.backup_id

        if dry_run:
            await handler.emit_config_event(
                operation="autoconfig_completed",
                entity_type="autoconfig",
                entity_id=job_id,
                status="completed",
                data={
                    "job_id": job_id,
                    "dry_run": True,
                    "would_deploy": would_deploy,
                    "backup_id": backup_id,
                    "duration_ms": int((time.time() - start_time) * 1000),
                },
            )
            return

        # Phase 4: Deploying
        deployed_agents = []
        failed_agents = []

        for idx, agent_id in enumerate(would_deploy):
            await _emit_progress(
                handler,
                job_id,
                "deploying",
                4,
                total_phases,
                current_item=agent_id,
                items_completed=idx,
                items_total=len(would_deploy),
            )

            try:

                def _deploy_one(name=agent_id):
                    from claude_mpm.services.agents.deployment.agent_deployment import (
                        AgentDeploymentService,
                    )

                    svc = AgentDeploymentService()
                    agents_dir = resolve_agents_dir(ConfigScope.PROJECT, project_path)
                    agents_dir.mkdir(parents=True, exist_ok=True)
                    return svc.deploy_agent(name, agents_dir, force_rebuild=False)

                success = await asyncio.to_thread(_deploy_one)
                if success:
                    deployed_agents.append(agent_id)
                else:
                    failed_agents.append(agent_id)

            except Exception as e:
                logger.warning("Auto-configure: failed to deploy '%s': %s", agent_id, e)
                failed_agents.append(agent_id)

        # Phase 5: Skill Deployment
        await _emit_progress(
            handler,
            job_id,
            "deploying_skills",
            5,
            total_phases,
        )

        deployed_skills = []
        skill_errors = []

        def _recommend_and_deploy_skills():
            from claude_mpm.cli.interactive.skills_wizard import (
                AGENT_SKILL_MAPPING,
            )

            recommended_skills = set()
            for agent_id in would_deploy:
                agent_skills = AGENT_SKILL_MAPPING.get(agent_id, [])
                recommended_skills.update(agent_skills)

            if not recommended_skills:
                return {"deployed_skills": [], "errors": []}

            svc = _get_skills_deployer()
            # Deploy skills to project-scoped directory instead of ~/.claude/skills/
            project_skills_dir = resolve_skills_dir(ConfigScope.PROJECT, project_path)
            project_skills_dir.mkdir(parents=True, exist_ok=True)
            return svc.deploy_skills(
                skill_names=sorted(recommended_skills),
                force=False,
                skills_dir=project_skills_dir,
            )

        try:
            skills_result = await asyncio.to_thread(_recommend_and_deploy_skills)
            deployed_skills = skills_result.get("deployed_skills", [])
            skill_errors = skills_result.get("errors", [])
        except Exception as e:
            logger.warning("Auto-configure %s: skill deployment failed: %s", job_id, e)
            skill_errors = [str(e)]

        # Phase 6: Verifying
        await _emit_progress(
            handler,
            job_id,
            "verifying",
            6,
            total_phases,
            items_completed=len(deployed_agents),
            items_total=len(would_deploy),
        )

        def _verify():
            verifier_mod = __import__(
                "claude_mpm.services.config_api.deployment_verifier",
                fromlist=["DeploymentVerifier"],
            )
            verifier = verifier_mod.DeploymentVerifier()
            results = {}
            for name in deployed_agents:
                vr = verifier.verify_agent_deployed(name)
                results[name] = {"passed": vr.passed}
            return results

        verification = await asyncio.to_thread(_verify)

        duration_ms = int((time.time() - start_time) * 1000)

        # Emit completion event
        await handler.emit_config_event(
            operation="autoconfig_completed",
            entity_type="autoconfig",
            entity_id=job_id,
            status="completed",
            data={
                "job_id": job_id,
                "deployed_agents": deployed_agents,
                "failed_agents": failed_agents,
                "deployed_skills": deployed_skills,
                "skill_errors": skill_errors,
                "needs_restart": bool(deployed_agents or deployed_skills),
                "backup_id": backup_id,
                "duration_ms": duration_ms,
                "verification": verification,
            },
        )

        logger.info(
            "Auto-configure %s completed: %d agents deployed, %d failed, "
            "%d skills deployed, %d skill errors (%dms)",
            job_id,
            len(deployed_agents),
            len(failed_agents),
            len(deployed_skills),
            len(skill_errors),
            duration_ms,
        )

    except Exception as e:
        logger.error("Auto-configure %s failed: %s", job_id, e)
        await handler.emit_config_event(
            operation="autoconfig_failed",
            entity_type="autoconfig",
            entity_id=job_id,
            status="failed",
            data={
                "job_id": job_id,
                "error": str(e),
                "deployed_before_failure": [],
                "rollback_available": backup_id is not None,
                "backup_id": backup_id,
            },
        )

    finally:
        _active_jobs.pop(job_id, None)
