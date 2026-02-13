"""Configuration API routes for the Claude MPM Dashboard.

Phase 1: Read-only endpoints for configuration visibility.
All endpoints are GET-only. No mutation operations.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from aiohttp import web

logger = logging.getLogger(__name__)

# Lazy-initialized service singletons (per-process, not per-request)
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
#   3. Return {"success": False, "error": str(e), "code": "SERVICE_ERROR"} on failure


async def handle_project_summary(request: web.Request) -> web.Response:
    """GET /api/config/project/summary - High-level configuration overview."""
    try:

        def _get_summary():
            # Count deployed agents
            agent_mgr = _get_agent_manager()
            deployed_agents = agent_mgr.list_agents(location="project")
            deployed_count = len(deployed_agents)

            # Count available agents (from cache)
            git_mgr = _get_git_source_manager()
            available_agents = git_mgr.list_cached_agents()

            # Count deployed skills
            skills_svc = _get_skills_deployer()
            deployed_skills = skills_svc.check_deployed_skills()

            # Count sources
            from claude_mpm.config.agent_sources import AgentSourceConfiguration
            from claude_mpm.config.skill_sources import SkillSourceConfiguration

            agent_config = AgentSourceConfiguration.load()
            skill_config = SkillSourceConfiguration()
            skill_sources = skill_config.load()

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
                    "agent_sources": len(agent_config.repositories),
                    "skill_sources": len(skill_sources),
                },
            }

        data = await asyncio.to_thread(_get_summary)
        return web.json_response({"success": True, "data": data})
    except Exception as e:
        logger.error(f"Error fetching project summary: {e}")
        return web.json_response(
            {"success": False, "error": str(e), "code": "SERVICE_ERROR"},
            status=500,
        )


async def handle_agents_deployed(request: web.Request) -> web.Response:
    """GET /api/config/agents/deployed - List deployed agents."""
    try:

        def _list_deployed():
            from claude_mpm.config.agent_presets import CORE_AGENTS

            agent_mgr = _get_agent_manager()
            agents_data = agent_mgr.list_agents(location="project")

            # list_agents returns Dict[str, Dict[str, Any]]
            agents_list = [
                {"name": name, **details} for name, details in agents_data.items()
            ]

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
        return web.json_response(
            {
                "success": True,
                "agents": agents,
                "total": len(agents),
            }
        )
    except Exception as e:
        logger.error(f"Error listing deployed agents: {e}")
        return web.json_response(
            {"success": False, "error": str(e), "code": "SERVICE_ERROR"},
            status=500,
        )


async def handle_agents_available(request: web.Request) -> web.Response:
    """GET /api/config/agents/available - List available agents from cache."""
    try:
        search = request.query.get("search", None)

        def _list_available():
            git_mgr = _get_git_source_manager()
            agents = git_mgr.list_cached_agents()

            # Client-side search filter on name/description
            if search:
                search_lower = search.lower()
                agents = [
                    a
                    for a in agents
                    if search_lower in a.get("name", "").lower()
                    or search_lower in a.get("description", "").lower()
                ]

            # Enrich with is_deployed flag by checking project agents
            agent_mgr = _get_agent_manager()
            deployed = agent_mgr.list_agents(location="project")
            deployed_names = set(deployed.keys())

            for agent in agents:
                agent_name = agent.get("name", agent.get("agent_id", ""))
                agent["is_deployed"] = agent_name in deployed_names

            return agents

        agents = await asyncio.to_thread(_list_available)

        response = web.json_response(
            {
                "success": True,
                "agents": agents,
                "total": len(agents),
                "filters_applied": {"search": search} if search else {},
            }
        )
        # Cache hint: available agents change only on sync
        response.headers["Cache-Control"] = "private, max-age=60"
        return response
    except Exception as e:
        logger.error(f"Error listing available agents: {e}")
        return web.json_response(
            {"success": False, "error": str(e), "code": "SERVICE_ERROR"},
            status=500,
        )


async def handle_skills_deployed(request: web.Request) -> web.Response:
    """GET /api/config/skills/deployed - List deployed skills."""
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
                    skills_list.append(
                        {
                            "name": skill_name,
                            "path": skill.get("path", ""),
                            "description": meta.get("description", ""),
                            "category": meta.get("category", "unknown"),
                            "collection": meta.get("collection", ""),
                            "is_user_requested": skill_name in user_requested,
                            "deploy_mode": (
                                "user_defined"
                                if skill_name in user_requested
                                else "agent_referenced"
                            ),
                            "deploy_date": meta.get("deployed_at", ""),
                        }
                    )

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


async def handle_skills_available(request: web.Request) -> web.Response:
    """GET /api/config/skills/available - List available skills from sources."""
    try:
        collection = request.query.get("collection", None)

        def _list_available_skills():
            skills_svc = _get_skills_deployer()
            result = skills_svc.list_available_skills(collection=collection)

            # Mark which are deployed
            deployed = skills_svc.check_deployed_skills()
            deployed_names = {s.get("name", "") for s in deployed.get("skills", [])}

            # Flatten into a flat list for the UI
            flat_skills = []
            skills = result.get("skills", [])
            if isinstance(skills, list):
                for skill in skills:
                    if isinstance(skill, dict):
                        skill["is_deployed"] = skill.get("name", "") in deployed_names
                        flat_skills.append(skill)
            elif isinstance(skills, dict):
                for category, category_skills in skills.items():
                    if isinstance(category_skills, list):
                        for skill in category_skills:
                            if isinstance(skill, dict):
                                skill["category"] = category
                                skill["is_deployed"] = (
                                    skill.get("name", "") in deployed_names
                                )
                                flat_skills.append(skill)

            return flat_skills

        skills = await asyncio.to_thread(_list_available_skills)

        response = web.json_response(
            {
                "success": True,
                "skills": skills,
                "total": len(skills),
                "filters_applied": ({"collection": collection} if collection else {}),
            }
        )
        response.headers["Cache-Control"] = "private, max-age=120"
        return response
    except Exception as e:
        logger.error(f"Error listing available skills: {e}")
        return web.json_response(
            {"success": False, "error": str(e), "code": "SERVICE_ERROR"},
            status=500,
        )


async def handle_sources(request: web.Request) -> web.Response:
    """GET /api/config/sources - Unified list of agent and skill sources."""
    try:

        def _list_sources():
            sources = []

            # Agent sources
            try:
                from claude_mpm.config.agent_sources import (
                    AgentSourceConfiguration,
                )

                agent_config = AgentSourceConfiguration.load()
                for repo in agent_config.repositories:
                    sources.append(
                        {
                            "id": repo.url.split("/")[-1]
                            if hasattr(repo, "url")
                            else "unknown",
                            "type": "agent",
                            "url": getattr(repo, "url", ""),
                            "subdirectory": getattr(repo, "subdirectory", None),
                            "enabled": getattr(repo, "enabled", True),
                            "priority": getattr(repo, "priority", 100),
                        }
                    )
            except Exception as e:
                logger.warning(f"Failed to load agent sources: {e}")

            # Skill sources
            try:
                from claude_mpm.config.skill_sources import (
                    SkillSourceConfiguration,
                )

                skill_config = SkillSourceConfiguration()
                skill_sources = skill_config.load()
                for source in skill_sources:
                    sources.append(
                        {
                            "id": getattr(source, "id", "unknown"),
                            "type": "skill",
                            "url": getattr(source, "url", ""),
                            "branch": getattr(source, "branch", "main"),
                            "enabled": getattr(source, "enabled", True),
                            "priority": getattr(source, "priority", 100),
                        }
                    )
            except Exception as e:
                logger.warning(f"Failed to load skill sources: {e}")

            # Sort by priority (lower number = higher precedence)
            sources.sort(key=lambda s: s.get("priority", 100))
            return sources

        sources = await asyncio.to_thread(_list_sources)
        return web.json_response(
            {
                "success": True,
                "sources": sources,
                "total": len(sources),
            }
        )
    except Exception as e:
        logger.error(f"Error listing sources: {e}")
        return web.json_response(
            {"success": False, "error": str(e), "code": "SERVICE_ERROR"},
            status=500,
        )
