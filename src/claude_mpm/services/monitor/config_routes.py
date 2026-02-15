"""Configuration API routes for the Claude MPM Dashboard.

Phase 1: Read-only endpoints for configuration visibility.
Phase 4A: Skill-to-Agent linking and configuration validation.
All endpoints are GET-only. No mutation operations.
"""

import asyncio
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from aiohttp import web

from claude_mpm.services.config_api.validation import validate_safe_name
from claude_mpm.services.monitor.pagination import (
    extract_pagination_params,
    paginate,
    paginated_json,
)

logger = logging.getLogger(__name__)

# Lazy-initialized service singletons (per-process, not per-request)
_agent_manager = None
_git_source_manager = None
_skills_deployer_service = None
_skill_to_agent_mapper = None
_config_validation_service = None


def _get_agent_manager(project_dir: Optional[Path] = None):
    """Lazy singleton for AgentManager."""
    global _agent_manager
    if _agent_manager is None:
        from claude_mpm.services.agents.management.agent_management_service import (
            AgentManager,
        )

        agents_dir = project_dir or (Path.cwd() / ".claude" / "agents")
        _agent_manager = AgentManager(project_dir=agents_dir)
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


def _get_skill_to_agent_mapper():
    """Lazy singleton for SkillToAgentMapper."""
    global _skill_to_agent_mapper
    if _skill_to_agent_mapper is None:
        from claude_mpm.services.monitor.handlers.skill_link_handler import (
            SkillToAgentMapper,
        )

        _skill_to_agent_mapper = SkillToAgentMapper()
    return _skill_to_agent_mapper


def _get_config_validation_service():
    """Lazy singleton for ConfigValidationService."""
    global _config_validation_service
    if _config_validation_service is None:
        from claude_mpm.services.config.config_validation_service import (
            ConfigValidationService,
        )

        _config_validation_service = ConfigValidationService()
    return _config_validation_service


def register_config_routes(app: web.Application, server_instance=None):
    """Register all configuration API routes on the aiohttp app.

    Called from UnifiedMonitorServer._setup_http_routes().

    Args:
        app: The aiohttp web application
        server_instance: Optional reference to UnifiedMonitorServer
                        (for accessing working_directory, etc.)
    """
    # Phase 1: Read-only endpoints
    app.router.add_get("/api/config/project/summary", handle_project_summary)
    app.router.add_get("/api/config/agents/deployed", handle_agents_deployed)
    app.router.add_get("/api/config/agents/available", handle_agents_available)
    app.router.add_get("/api/config/skills/deployed", handle_skills_deployed)
    app.router.add_get("/api/config/skills/available", handle_skills_available)
    app.router.add_get("/api/config/sources", handle_sources)

    # Phase 2: Detail endpoints (lazy-loaded rich metadata)
    app.router.add_get("/api/config/agents/{name}/detail", handle_agent_detail)
    app.router.add_get("/api/config/skills/{name}/detail", handle_skill_detail)

    # Phase 4A: Skill-to-Agent linking
    app.router.add_get("/api/config/skill-links/", handle_skill_links)
    app.router.add_get(
        "/api/config/skill-links/agent/{agent_name}", handle_skill_links_agent
    )

    # Phase 4A: Configuration validation
    app.router.add_get("/api/config/validate", handle_validate)

    logger.info("Registered 11 config API routes under /api/config/")


# --- Shared Helpers ---


def _build_manifest_lookup(skills_svc) -> dict:
    """Build a name-to-manifest-entry lookup dict from available skills.

    Handles both flat list and nested dict manifest structures.
    Returns empty dict on any error (graceful degradation).
    """
    manifest_lookup: dict = {}
    try:
        available = skills_svc.list_available_skills()
        available_skills = available.get("skills", [])
        if isinstance(available_skills, list):
            for skill in available_skills:
                if isinstance(skill, dict):
                    manifest_lookup[skill.get("name", "")] = skill
        elif isinstance(available_skills, dict):
            for _category, cat_skills in available_skills.items():
                if isinstance(cat_skills, list):
                    for skill in cat_skills:
                        if isinstance(skill, dict):
                            manifest_lookup[skill.get("name", "")] = skill
    except Exception as e:
        logger.warning(f"Could not load manifest for skill enrichment: {e}")
    return manifest_lookup


def _find_manifest_entry(skill_name: str, manifest_lookup: dict) -> Optional[dict]:
    """Find a manifest entry for a skill, using exact match then suffix match.

    Deployed names are path-normalized (e.g., 'universal-testing-tdd') while
    manifest names are short (e.g., 'test-driven-development'). This function
    tries exact match first, then suffix-based matching.
    """
    entry = manifest_lookup.get(skill_name)
    if entry:
        return entry
    for m_name, m_data in manifest_lookup.items():
        if skill_name.endswith(f"-{m_name}"):
            return m_data
    return None


def _enrich_skill_from_manifest(skill_item: dict, manifest_lookup: dict) -> None:
    """Enrich a deployed skill dict in-place with manifest metadata.

    Adds version, toolchain, framework, tags, full_tokens, entry_point_tokens.
    Fills empty description from manifest if available.
    """
    skill_name = skill_item.get("name", "")
    manifest_entry = _find_manifest_entry(skill_name, manifest_lookup)
    if manifest_entry:
        skill_item["version"] = manifest_entry.get("version", "")
        skill_item["toolchain"] = manifest_entry.get("toolchain")
        skill_item["framework"] = manifest_entry.get("framework")
        skill_item["tags"] = manifest_entry.get("tags", [])
        skill_item["full_tokens"] = manifest_entry.get("full_tokens", 0)
        skill_item["entry_point_tokens"] = manifest_entry.get("entry_point_tokens", 0)
        # Enrich description from manifest if deployment index has empty description
        if not skill_item.get("description") and manifest_entry.get("description"):
            skill_item["description"] = manifest_entry.get("description", "")


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

            # Count deployed skills (use project-level directory to match CLI)
            skills_svc = _get_skills_deployer()
            project_skills_dir = Path.cwd() / ".claude" / "skills"
            deployed_skills = skills_svc.check_deployed_skills(
                skills_dir=project_skills_dir
            )

            # Count sources
            from claude_mpm.config.agent_sources import AgentSourceConfiguration
            from claude_mpm.config.skill_sources import SkillSourceConfiguration

            agent_config = AgentSourceConfiguration.load()
            skill_config = SkillSourceConfiguration()
            skill_sources = skill_config.load()

            # Read deployment mode from project configuration
            config_path = Path.cwd() / ".claude-mpm" / "configuration.yaml"
            if config_path.exists():
                project_cfg = yaml.safe_load(config_path.read_text()) or {}
            else:
                project_cfg = {}
            skills_cfg = project_cfg.get("skills", {})

            return {
                "deployment_mode": skills_cfg.get("deployment_mode", "selective"),
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
    """GET /api/config/agents/available - List available agents from cache.

    Supports pagination: ?limit=50&cursor=<opaque>&sort=asc|desc
    Backward compatible: no limit/cursor returns all items.
    """
    try:
        search = request.query.get("search", None)
        pagination_params = extract_pagination_params(request)

        def _list_available():
            git_mgr = _get_git_source_manager()
            agents = git_mgr.list_cached_agents()

            # Promote metadata fields to root level for frontend compatibility.
            # The discovery service nests name/description under metadata,
            # but the frontend AvailableAgent interface expects them at root.
            for agent in agents:
                metadata = agent.get("metadata", {})
                agent.setdefault(
                    "name", metadata.get("name", agent.get("agent_id", ""))
                )
                agent.setdefault("description", metadata.get("description", ""))

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
            # Use lightweight list_agent_names() to avoid parsing all agent files
            agent_mgr = _get_agent_manager()
            deployed_names = agent_mgr.list_agent_names(location="project")

            for agent in agents:
                agent_name = agent.get("name", agent.get("agent_id", ""))
                agent["is_deployed"] = agent_name in deployed_names

            return agents

        agents = await asyncio.to_thread(_list_available)

        # Apply pagination
        result = paginate(
            agents,
            limit=pagination_params["limit"],
            cursor=pagination_params["cursor"],
            sort_key=lambda a: a.get("name", "").lower(),
            sort_desc=pagination_params["sort_desc"],
        )

        response_data = paginated_json(result, items_key="agents")
        if search:
            response_data["filters_applied"] = {"search": search}

        response = web.json_response(response_data)
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
            # Use project-level skills directory instead of user-level
            # This matches the CLI behavior which reads from $CWD/.claude/skills/
            project_skills_dir = Path.cwd() / ".claude" / "skills"
            deployed = skills_svc.check_deployed_skills(skills_dir=project_skills_dir)

            # Enrich with deployment index metadata if available
            try:
                from claude_mpm.services.skills.selective_skill_deployer import (
                    load_deployment_index,
                )

                skills_dir = project_skills_dir
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

                # Phase 2 Step 3: Cross-reference with manifest for enrichment
                manifest_lookup = _build_manifest_lookup(skills_svc)
                for skill_item in skills_list:
                    _enrich_skill_from_manifest(skill_item, manifest_lookup)

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
    """GET /api/config/skills/available - List available skills from sources.

    Supports pagination: ?limit=50&cursor=<opaque>&sort=asc|desc
    Backward compatible: no limit/cursor returns all items.
    """
    try:
        collection = request.query.get("collection", None)
        pagination_params = extract_pagination_params(request)

        def _list_available_skills():
            skills_svc = _get_skills_deployer()
            result = skills_svc.list_available_skills(collection=collection)

            # Mark which are deployed (use project-level directory)
            project_skills_dir = Path.cwd() / ".claude" / "skills"
            deployed = skills_svc.check_deployed_skills(skills_dir=project_skills_dir)
            deployed_names = {s.get("name", "") for s in deployed.get("skills", [])}

            def _is_skill_deployed(short_name: str) -> bool:
                """Check if a skill is deployed, accounting for path-normalization.

                Deployed directory names are path-normalized (e.g.,
                'universal-main-mcp-builder') while available skill names are
                short manifest names (e.g., 'mcp-builder'). This function
                checks for exact match first, then suffix-based matching.
                """
                if not short_name:
                    return False
                # Exact match (handles already-normalized names)
                if short_name in deployed_names:
                    return True
                # Suffix match: check if any deployed name ends with
                # '-{short_name}' to handle path-normalization
                suffix = f"-{short_name}"
                return any(dn.endswith(suffix) for dn in deployed_names)

            # Flatten into a flat list for the UI
            flat_skills = []
            skills = result.get("skills", [])
            if isinstance(skills, list):
                for skill in skills:
                    if isinstance(skill, dict):
                        skill["is_deployed"] = _is_skill_deployed(skill.get("name", ""))
                        flat_skills.append(skill)
            elif isinstance(skills, dict):
                for category, category_skills in skills.items():
                    if isinstance(category_skills, list):
                        for skill in category_skills:
                            if isinstance(skill, dict):
                                skill["category"] = category
                                skill["is_deployed"] = _is_skill_deployed(
                                    skill.get("name", "")
                                )
                                flat_skills.append(skill)

            # Phase 2 Step 6: Enrich with agent count from skill-links
            try:
                mapper = _get_skill_to_agent_mapper()
                links = mapper.get_all_links()
                by_skill = links.get("by_skill", {})

                for skill in flat_skills:
                    skill_name = skill.get("name", "")
                    skill_data = by_skill.get(skill_name, {})
                    if not skill_data:
                        # Try suffix matching for normalized names
                        for s_name, s_data in by_skill.items():
                            if s_name.endswith(f"-{skill_name}") or skill_name.endswith(
                                f"-{s_name}"
                            ):
                                skill_data = s_data
                                break
                    agents = (
                        skill_data.get("agents", [])
                        if isinstance(skill_data, dict)
                        else []
                    )
                    skill["agent_count"] = len(agents)
            except Exception as e:
                logger.warning(f"Could not load skill-links for agent counts: {e}")
                # Don't fail - just skip enrichment

            return flat_skills

        skills = await asyncio.to_thread(_list_available_skills)

        # Apply pagination
        result = paginate(
            skills,
            limit=pagination_params["limit"],
            cursor=pagination_params["cursor"],
            sort_key=lambda s: s.get("name", "").lower(),
            sort_desc=pagination_params["sort_desc"],
        )

        response_data = paginated_json(result, items_key="skills")
        if collection:
            response_data["filters_applied"] = {"collection": collection}

        response = web.json_response(response_data)
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


# --- Phase 2: Detail Endpoints ---


async def handle_agent_detail(request: web.Request) -> web.Response:
    """GET /api/config/agents/{name}/detail - Full agent metadata for detail panel.

    Returns the complete frontmatter data for a single deployed agent, including
    knowledge, skills list, dependencies, handoff agents, and constraints.
    Path traversal protection via validate_safe_name() (VP-1-SEC).
    """
    try:
        agent_name = request.match_info["name"]

        # MANDATORY: Path traversal protection (VP-1-SEC)
        valid, _err_msg = validate_safe_name(agent_name, "agent")
        if not valid:
            return web.json_response(
                {
                    "success": False,
                    "error": f"Invalid agent name: '{agent_name}'",
                    "code": "INVALID_NAME",
                },
                status=400,
            )

        def _get_detail() -> Optional[Dict[str, Any]]:
            import frontmatter as fm_lib

            agent_mgr = _get_agent_manager()
            agent_def = agent_mgr.read_agent(agent_name)
            if not agent_def:
                return None

            # Parse full frontmatter from raw content
            post = fm_lib.loads(agent_def.raw_content)
            fmdata = post.metadata

            capabilities = fmdata.get("capabilities", {})
            if not isinstance(capabilities, dict):
                capabilities = {}

            knowledge = fmdata.get("knowledge", {})
            if not isinstance(knowledge, dict):
                knowledge = {}

            interactions = fmdata.get("interactions", {})
            if not isinstance(interactions, dict):
                interactions = {}

            # Normalize skills field
            skills_field = fmdata.get("skills", [])
            if isinstance(skills_field, dict):
                skills_list = list(
                    set(
                        (skills_field.get("required") or [])
                        + (skills_field.get("optional") or [])
                    )
                )
            elif isinstance(skills_field, list):
                skills_list = skills_field
            else:
                skills_list = []

            # Normalize dependencies
            dependencies = fmdata.get("dependencies", {})
            if not isinstance(dependencies, dict):
                dependencies = {}

            tags = fmdata.get("tags", [])
            if not isinstance(tags, list):
                tags = []

            return {
                "name": fmdata.get("name", agent_name),
                "agent_id": fmdata.get("agent_id", agent_name),
                "description": fmdata.get("description", ""),
                "version": fmdata.get("version", agent_def.metadata.version),
                "category": fmdata.get("category", ""),
                "color": fmdata.get("color", "gray"),
                "tags": tags,
                "resource_tier": fmdata.get("resource_tier", ""),
                "agent_type": fmdata.get("agent_type", ""),
                "temperature": fmdata.get("temperature"),
                "timeout": fmdata.get("timeout"),
                "network_access": capabilities.get("network_access"),
                "skills": skills_list,
                "dependencies": dependencies,
                "knowledge": {
                    "domain_expertise": knowledge.get("domain_expertise", []),
                    "constraints": knowledge.get("constraints", []),
                    "best_practices": knowledge.get("best_practices", []),
                },
                "handoff_agents": interactions.get("handoff_agents", []),
                "author": fmdata.get("author", ""),
                "schema_version": fmdata.get("schema_version", ""),
            }

        data = await asyncio.to_thread(_get_detail)

        if data is None:
            return web.json_response(
                {
                    "success": False,
                    "error": f"Agent '{agent_name}' not found",
                    "code": "NOT_FOUND",
                },
                status=404,
            )

        return web.json_response({"success": True, "data": data})
    except Exception as e:
        logger.error(
            f"Error fetching agent detail for {request.match_info.get('name', '?')}: {e}"
        )
        return web.json_response(
            {"success": False, "error": str(e), "code": "SERVICE_ERROR"},
            status=500,
        )


async def handle_skill_detail(request: web.Request) -> web.Response:
    """GET /api/config/skills/{name}/detail - Enriched skill metadata for detail panel.

    Combines three data sources: SKILL.md frontmatter, manifest metadata, and
    skill-to-agent links. Path traversal protection via validate_safe_name() (VP-1-SEC).
    """
    try:
        skill_name = request.match_info["name"]

        # MANDATORY: Path traversal protection (VP-1-SEC)
        valid, _err_msg = validate_safe_name(skill_name, "skill")
        if not valid:
            return web.json_response(
                {
                    "success": False,
                    "error": f"Invalid skill name: '{skill_name}'",
                    "code": "INVALID_NAME",
                },
                status=400,
            )

        def _get_skill_detail() -> Dict[str, Any]:
            # Look for the skill in the deployed skills directory
            project_skills_dir = Path.cwd() / ".claude" / "skills"
            skill_dir = project_skills_dir / skill_name
            skill_md = skill_dir / "SKILL.md"

            result: Dict[str, Any] = {"name": skill_name}

            # Parse SKILL.md frontmatter if deployed
            if skill_md.exists():
                try:
                    content = skill_md.read_text(encoding="utf-8")
                    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
                    if match:
                        fm = yaml.safe_load(match.group(1)) or {}
                        result["when_to_use"] = fm.get("when_to_use", "")
                        result["languages"] = fm.get("languages", "")
                        pd = fm.get("progressive_disclosure", {})
                        if isinstance(pd, dict):
                            entry = pd.get("entry_point", {})
                            if isinstance(entry, dict):
                                result["summary"] = entry.get("summary", "")
                                result["quick_start"] = entry.get("quick_start", "")
                            refs = pd.get("references", [])
                            if isinstance(refs, list):
                                result["references"] = [
                                    {
                                        "path": r.get("path", ""),
                                        "purpose": r.get("purpose", ""),
                                    }
                                    for r in refs
                                    if isinstance(r, dict)
                                ]
                        # Frontmatter description/name override
                        result["description"] = fm.get(
                            "description", result.get("description", "")
                        )
                        result["frontmatter_name"] = fm.get("name", "")
                        result["frontmatter_tags"] = fm.get("tags", [])
                except Exception as e:
                    logger.warning(f"Failed to parse SKILL.md for {skill_name}: {e}")

            # Cross-reference with manifest data for baseline fields
            try:
                skills_svc = _get_skills_deployer()
                manifest_lookup = _build_manifest_lookup(skills_svc)
                manifest_entry = _find_manifest_entry(skill_name, manifest_lookup)

                if manifest_entry:
                    result["version"] = manifest_entry.get("version", "")
                    result["toolchain"] = manifest_entry.get("toolchain")
                    result["framework"] = manifest_entry.get("framework")
                    result["tags"] = manifest_entry.get("tags", [])
                    result["full_tokens"] = manifest_entry.get("full_tokens", 0)
                    result["entry_point_tokens"] = manifest_entry.get(
                        "entry_point_tokens", 0
                    )
                    result["requires"] = manifest_entry.get("requires", [])
                    result["author"] = manifest_entry.get("author", "")
                    result["updated"] = manifest_entry.get("updated", "")
                    result["source_path"] = manifest_entry.get("source_path", "")
                    if not result.get("description"):
                        result["description"] = manifest_entry.get("description", "")
            except Exception as e:
                logger.warning(f"Could not load manifest for skill detail: {e}")

            # Get agent usage from skill-links
            try:
                mapper = _get_skill_to_agent_mapper()
                links = mapper.get_all_links()
                by_skill = links.get("by_skill", {})
                # Try exact match, then suffix match
                skill_agents = by_skill.get(skill_name, {})
                if not skill_agents:
                    for s_name, s_data in by_skill.items():
                        if skill_name.endswith(f"-{s_name}") or s_name.endswith(
                            f"-{skill_name}"
                        ):
                            skill_agents = s_data
                            break
                result["used_by_agents"] = (
                    skill_agents.get("agents", [])
                    if isinstance(skill_agents, dict)
                    else []
                )
                result["agent_count"] = len(result["used_by_agents"])
            except Exception as e:
                logger.warning(f"Could not load skill-links for {skill_name}: {e}")
                result["used_by_agents"] = []
                result["agent_count"] = 0

            return result

        data = await asyncio.to_thread(_get_skill_detail)
        return web.json_response({"success": True, "data": data})
    except Exception as e:
        logger.error(
            f"Error fetching skill detail for {request.match_info.get('name', '?')}: {e}"
        )
        return web.json_response(
            {"success": False, "error": str(e), "code": "SERVICE_ERROR"},
            status=500,
        )


# --- Phase 4A: Skill-to-Agent Linking ---


async def handle_skill_links(request: web.Request) -> web.Response:
    """GET /api/config/skill-links/ - Full bidirectional skill-agent mapping.

    Returns by_agent mapping, by_skill mapping, and aggregate stats.
    Supports pagination on by_agent: ?limit=50&cursor=<opaque>&sort=asc|desc
    Backward compatible: no params returns all.
    """
    try:
        pagination_params = extract_pagination_params(request)

        def _get_links():
            mapper = _get_skill_to_agent_mapper()
            links = mapper.get_all_links()
            stats = mapper.get_stats()
            return links, stats

        links, stats = await asyncio.to_thread(_get_links)

        # Paginate by_agent entries
        by_agent = links.get("by_agent", {})
        agent_items = [
            {"agent_name": name, **data} for name, data in sorted(by_agent.items())
        ]

        result = paginate(
            agent_items,
            limit=pagination_params["limit"],
            cursor=pagination_params["cursor"],
            sort_key=lambda a: a["agent_name"].lower(),
            sort_desc=pagination_params["sort_desc"],
        )

        response_data = {
            "success": True,
            "by_agent": result.items,
            "by_skill": links.get("by_skill", {}),
            "stats": stats,
            "total_agents": result.total,
        }

        if result.limit is not None:
            response_data["pagination"] = {
                "has_more": result.has_more,
                "next_cursor": result.next_cursor,
                "limit": result.limit,
            }

        response = web.json_response(response_data)
        response.headers["Cache-Control"] = "private, max-age=30"
        return response
    except Exception as e:
        logger.error(f"Error fetching skill links: {e}")
        return web.json_response(
            {"success": False, "error": str(e), "code": "SERVICE_ERROR"},
            status=500,
        )


async def handle_skill_links_agent(request: web.Request) -> web.Response:
    """GET /api/config/skill-links/agent/{agent_name} - Per-agent skills."""
    try:
        agent_name = request.match_info["agent_name"]

        def _get_agent_skills():
            mapper = _get_skill_to_agent_mapper()
            return mapper.get_agent_skills(agent_name)

        result = await asyncio.to_thread(_get_agent_skills)

        if result is None:
            return web.json_response(
                {
                    "success": False,
                    "error": f"Agent '{agent_name}' not found",
                    "code": "NOT_FOUND",
                },
                status=404,
            )

        return web.json_response({"success": True, "data": result})
    except Exception as e:
        logger.error(
            f"Error fetching agent skills for {request.match_info.get('agent_name', '?')}: {e}"
        )
        return web.json_response(
            {"success": False, "error": str(e), "code": "SERVICE_ERROR"},
            status=500,
        )


# --- Phase 4A: Configuration Validation ---


async def handle_validate(request: web.Request) -> web.Response:
    """GET /api/config/validate - Run configuration validation.

    Returns categorized issues with severity, path, message, and suggestion.
    Results are cached for 60 seconds.
    """
    try:

        def _validate():
            svc = _get_config_validation_service()
            return svc.validate_cached()

        data = await asyncio.to_thread(_validate)
        return web.json_response(data)
    except Exception as e:
        logger.error(f"Error running config validation: {e}")
        return web.json_response(
            {"success": False, "error": str(e), "code": "SERVICE_ERROR"},
            status=500,
        )
