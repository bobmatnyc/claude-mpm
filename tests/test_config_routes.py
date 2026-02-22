"""Tests for configuration API routes (Phase 1 + Phase 2).

Tests cover all GET endpoints with:
- Happy path: Service returns data, handler returns 200
- Service error: Service raises exception, handler returns 500
- Empty state: Service returns empty data, handler returns 200 with empty arrays

Phase 2 additions:
- Enriched list_agents() with frontmatter fields (Step 1)
- Deployed skills manifest cross-reference (Step 3)
- Agent detail endpoint with path traversal protection (Step 4)
- Skill detail endpoint with path traversal protection (Step 5)
- Agent count enrichment on available skills (Step 6)
"""

from unittest.mock import MagicMock, patch

import pytest
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase


def create_test_app():
    """Create a test aiohttp app with config routes registered."""
    from claude_mpm.services.monitor.config_routes import register_config_routes

    app = web.Application()
    register_config_routes(app)
    return app


class TestProjectSummary(AioHTTPTestCase):
    async def get_application(self):
        return create_test_app()

    async def test_project_summary_success(self):
        mock_agent_mgr = MagicMock()
        mock_agent_mgr.list_agents.return_value = {"agent1": {}, "agent2": {}}

        mock_git_mgr = MagicMock()
        mock_git_mgr.list_cached_agents.return_value = [
            {"name": "a"},
            {"name": "b"},
            {"name": "c"},
        ]

        mock_skills_svc = MagicMock()
        mock_skills_svc.check_deployed_skills.return_value = {
            "deployed_count": 5,
            "skills": [],
        }

        mock_agent_config = MagicMock()
        mock_agent_config.repositories = [MagicMock(), MagicMock()]

        mock_skill_sources = [MagicMock(), MagicMock(), MagicMock()]

        with patch(
            "claude_mpm.services.monitor.config_routes._get_agent_manager",
            return_value=mock_agent_mgr,
        ), patch(
            "claude_mpm.services.monitor.config_routes._get_git_source_manager",
            return_value=mock_git_mgr,
        ), patch(
            "claude_mpm.services.monitor.config_routes._get_skills_deployer",
            return_value=mock_skills_svc,
        ), patch(
            "claude_mpm.services.monitor.config_routes.handle_project_summary.__module__",
            create=True,
        ), patch(
            "claude_mpm.config.agent_sources.AgentSourceConfiguration.load",
            return_value=mock_agent_config,
        ), patch(
            "claude_mpm.config.skill_sources.SkillSourceConfiguration"
        ) as mock_skill_config_cls:
            mock_skill_config_inst = MagicMock()
            mock_skill_config_inst.load.return_value = mock_skill_sources
            mock_skill_config_cls.return_value = mock_skill_config_inst

            resp = await self.client.request("GET", "/api/config/project/summary")
            assert resp.status == 200
            data = await resp.json()
            assert data["success"] is True
            assert data["data"]["agents"]["deployed"] == 2
            assert data["data"]["agents"]["available"] == 3
            assert data["data"]["skills"]["deployed"] == 5
            assert data["data"]["sources"]["agent_sources"] == 2
            assert data["data"]["sources"]["skill_sources"] == 3

    async def test_project_summary_service_error(self):
        with patch(
            "claude_mpm.services.monitor.config_routes._get_agent_manager",
            side_effect=Exception("Service unavailable"),
        ):
            resp = await self.client.request("GET", "/api/config/project/summary")
            assert resp.status == 500
            data = await resp.json()
            assert data["success"] is False
            assert "Service unavailable" in data["error"]
            assert data["code"] == "SERVICE_ERROR"

    async def test_project_summary_empty_state(self):
        mock_agent_mgr = MagicMock()
        mock_agent_mgr.list_agents.return_value = {}

        mock_git_mgr = MagicMock()
        mock_git_mgr.list_cached_agents.return_value = []

        mock_skills_svc = MagicMock()
        mock_skills_svc.check_deployed_skills.return_value = {
            "deployed_count": 0,
            "skills": [],
        }

        mock_agent_config = MagicMock()
        mock_agent_config.repositories = []

        with patch(
            "claude_mpm.services.monitor.config_routes._get_agent_manager",
            return_value=mock_agent_mgr,
        ), patch(
            "claude_mpm.services.monitor.config_routes._get_git_source_manager",
            return_value=mock_git_mgr,
        ), patch(
            "claude_mpm.services.monitor.config_routes._get_skills_deployer",
            return_value=mock_skills_svc,
        ), patch(
            "claude_mpm.config.agent_sources.AgentSourceConfiguration.load",
            return_value=mock_agent_config,
        ), patch(
            "claude_mpm.config.skill_sources.SkillSourceConfiguration"
        ) as mock_skill_config_cls:
            mock_skill_config_inst = MagicMock()
            mock_skill_config_inst.load.return_value = []
            mock_skill_config_cls.return_value = mock_skill_config_inst

            resp = await self.client.request("GET", "/api/config/project/summary")
            assert resp.status == 200
            data = await resp.json()
            assert data["success"] is True
            assert data["data"]["agents"]["deployed"] == 0
            assert data["data"]["agents"]["available"] == 0
            assert data["data"]["skills"]["deployed"] == 0


class TestAgentsDeployed(AioHTTPTestCase):
    async def get_application(self):
        return create_test_app()

    async def test_agents_deployed_success(self):
        mock_agent_mgr = MagicMock()
        mock_agent_mgr.list_agents.return_value = {
            "engineer": {
                "location": "project",
                "path": "/p/.claude/agents/engineer.md",
                "version": "3.0",
                "type": "core",
                "specializations": [],
            },
            "python-engineer": {
                "location": "project",
                "path": "/p/.claude/agents/python-engineer.md",
                "version": "2.5",
                "type": "core",
                "specializations": ["python"],
            },
        }

        with patch(
            "claude_mpm.services.monitor.config_routes._get_agent_manager",
            return_value=mock_agent_mgr,
        ), patch(
            "claude_mpm.config.agent_presets.CORE_AGENTS",
            ["engineer/core/engineer", "universal/research"],
        ):
            resp = await self.client.request("GET", "/api/config/agents/deployed")
            assert resp.status == 200
            data = await resp.json()
            assert data["success"] is True
            assert data["total"] == 2
            agents_by_name = {a["name"]: a for a in data["agents"]}
            assert agents_by_name["engineer"]["is_core"] is True
            assert agents_by_name["python-engineer"]["is_core"] is False

    async def test_agents_deployed_service_error(self):
        with patch(
            "claude_mpm.services.monitor.config_routes._get_agent_manager",
            side_effect=Exception("Cannot read agents"),
        ):
            resp = await self.client.request("GET", "/api/config/agents/deployed")
            assert resp.status == 500
            data = await resp.json()
            assert data["success"] is False
            assert data["code"] == "SERVICE_ERROR"

    async def test_agents_deployed_empty(self):
        mock_agent_mgr = MagicMock()
        mock_agent_mgr.list_agents.return_value = {}

        with patch(
            "claude_mpm.services.monitor.config_routes._get_agent_manager",
            return_value=mock_agent_mgr,
        ):
            resp = await self.client.request("GET", "/api/config/agents/deployed")
            assert resp.status == 200
            data = await resp.json()
            assert data["success"] is True
            assert data["total"] == 0
            assert data["agents"] == []


class TestAgentsAvailable(AioHTTPTestCase):
    async def get_application(self):
        return create_test_app()

    async def test_agents_available_success(self):
        mock_git_mgr = MagicMock()
        mock_git_mgr.list_cached_agents.return_value = [
            {
                "name": "python-engineer",
                "version": "2.5",
                "description": "Python specialist",
            },
            {
                "name": "react-engineer",
                "version": "1.0",
                "description": "React specialist",
            },
        ]

        mock_agent_mgr = MagicMock()
        mock_agent_mgr.list_agent_names.return_value = {"python-engineer"}

        with patch(
            "claude_mpm.services.monitor.config_routes._get_git_source_manager",
            return_value=mock_git_mgr,
        ), patch(
            "claude_mpm.services.monitor.config_routes._get_agent_manager",
            return_value=mock_agent_mgr,
        ):
            resp = await self.client.request("GET", "/api/config/agents/available")
            assert resp.status == 200
            data = await resp.json()
            assert data["success"] is True
            assert data["total"] == 2
            agents_by_name = {a["name"]: a for a in data["agents"]}
            assert agents_by_name["python-engineer"]["is_deployed"] is True
            assert agents_by_name["react-engineer"]["is_deployed"] is False
            assert "Cache-Control" in resp.headers

    async def test_agents_available_with_search(self):
        mock_git_mgr = MagicMock()
        mock_git_mgr.list_cached_agents.return_value = [
            {
                "name": "python-engineer",
                "version": "2.5",
                "description": "Python specialist",
            },
            {
                "name": "react-engineer",
                "version": "1.0",
                "description": "React specialist",
            },
            {
                "name": "golang-engineer",
                "version": "1.0",
                "description": "Go specialist",
            },
        ]

        mock_agent_mgr = MagicMock()
        mock_agent_mgr.list_agent_names.return_value = set()

        with patch(
            "claude_mpm.services.monitor.config_routes._get_git_source_manager",
            return_value=mock_git_mgr,
        ), patch(
            "claude_mpm.services.monitor.config_routes._get_agent_manager",
            return_value=mock_agent_mgr,
        ):
            resp = await self.client.request(
                "GET", "/api/config/agents/available?search=python"
            )
            assert resp.status == 200
            data = await resp.json()
            assert data["success"] is True
            assert data["total"] == 1
            assert data["agents"][0]["name"] == "python-engineer"
            assert data["filters_applied"]["search"] == "python"

    async def test_agents_available_service_error(self):
        with patch(
            "claude_mpm.services.monitor.config_routes._get_git_source_manager",
            side_effect=Exception("Cache not found"),
        ):
            resp = await self.client.request("GET", "/api/config/agents/available")
            assert resp.status == 500
            data = await resp.json()
            assert data["success"] is False
            assert data["code"] == "SERVICE_ERROR"


class TestSkillsDeployed(AioHTTPTestCase):
    async def get_application(self):
        return create_test_app()

    async def test_skills_deployed_success(self):
        mock_skills_svc = MagicMock()
        mock_skills_svc.check_deployed_skills.return_value = {
            "deployed_count": 2,
            "skills": [
                {"name": "git-workflow", "path": "/home/.claude/skills/git-workflow"},
                {"name": "tdd", "path": "/home/.claude/skills/tdd"},
            ],
            "claude_skills_dir": "/home/.claude/skills",
        }

        mock_index = {
            "deployed_skills": {
                "git-workflow": {
                    "description": "Git patterns",
                    "category": "collaboration",
                    "collection": "universal",
                    "deployed_at": "2026-02-10",
                },
                "tdd": {
                    "description": "TDD patterns",
                    "category": "testing",
                    "collection": "universal",
                    "deployed_at": "2026-02-10",
                },
            },
            "user_requested_skills": ["tdd"],
        }

        with patch(
            "claude_mpm.services.monitor.config_routes._get_skills_deployer",
            return_value=mock_skills_svc,
        ), patch(
            "claude_mpm.services.skills.selective_skill_deployer.load_deployment_index",
            return_value=mock_index,
        ):
            resp = await self.client.request("GET", "/api/config/skills/deployed")
            assert resp.status == 200
            data = await resp.json()
            assert data["success"] is True
            assert data["total"] == 2
            skills_by_name = {s["name"]: s for s in data["skills"]}
            assert skills_by_name["tdd"]["is_user_requested"] is True
            assert skills_by_name["tdd"]["deploy_mode"] == "user_defined"
            assert skills_by_name["git-workflow"]["deploy_mode"] == "agent_referenced"

    async def test_skills_deployed_service_error(self):
        with patch(
            "claude_mpm.services.monitor.config_routes._get_skills_deployer",
            side_effect=Exception("Skills dir missing"),
        ):
            resp = await self.client.request("GET", "/api/config/skills/deployed")
            assert resp.status == 500
            data = await resp.json()
            assert data["success"] is False
            assert data["code"] == "SERVICE_ERROR"

    async def test_skills_deployed_empty(self):
        mock_skills_svc = MagicMock()
        mock_skills_svc.check_deployed_skills.return_value = {
            "deployed_count": 0,
            "skills": [],
            "claude_skills_dir": "/home/.claude/skills",
        }

        mock_index = {"deployed_skills": {}, "user_requested_skills": []}

        with patch(
            "claude_mpm.services.monitor.config_routes._get_skills_deployer",
            return_value=mock_skills_svc,
        ), patch(
            "claude_mpm.services.skills.selective_skill_deployer.load_deployment_index",
            return_value=mock_index,
        ):
            resp = await self.client.request("GET", "/api/config/skills/deployed")
            assert resp.status == 200
            data = await resp.json()
            assert data["success"] is True
            assert data["total"] == 0
            assert data["skills"] == []


class TestSkillsAvailable(AioHTTPTestCase):
    async def get_application(self):
        return create_test_app()

    async def test_skills_available_success(self):
        mock_skills_svc = MagicMock()
        mock_skills_svc.list_available_skills.return_value = {
            "total_skills": 3,
            "skills": [
                {
                    "name": "git-workflow",
                    "description": "Git patterns",
                    "category": "collaboration",
                },
                {"name": "tdd", "description": "TDD patterns", "category": "testing"},
                {
                    "name": "debugging",
                    "description": "Debug tools",
                    "category": "debugging",
                },
            ],
        }
        mock_skills_svc.check_deployed_skills.return_value = {
            "skills": [{"name": "git-workflow"}],
        }

        mock_mapper = MagicMock()
        mock_mapper.get_all_links.return_value = {
            "by_agent": {},
            "by_skill": {
                "git-workflow": {"agents": ["engineer"], "sources": ["frontmatter"]},
            },
        }

        with patch(
            "claude_mpm.services.monitor.config_routes._get_skills_deployer",
            return_value=mock_skills_svc,
        ), patch(
            "claude_mpm.services.monitor.config_routes._get_skill_to_agent_mapper",
            return_value=mock_mapper,
        ):
            resp = await self.client.request("GET", "/api/config/skills/available")
            assert resp.status == 200
            data = await resp.json()
            assert data["success"] is True
            assert data["total"] == 3
            skills_by_name = {s["name"]: s for s in data["skills"]}
            assert skills_by_name["git-workflow"]["is_deployed"] is True
            assert skills_by_name["tdd"]["is_deployed"] is False
            # Phase 2 Step 6: verify agent_count enrichment
            assert skills_by_name["git-workflow"]["agent_count"] == 1
            assert skills_by_name["tdd"]["agent_count"] == 0
            assert "Cache-Control" in resp.headers

    async def test_skills_available_with_collection_filter(self):
        mock_skills_svc = MagicMock()
        mock_skills_svc.list_available_skills.return_value = {
            "total_skills": 1,
            "skills": [{"name": "tdd", "description": "TDD", "category": "testing"}],
        }
        mock_skills_svc.check_deployed_skills.return_value = {"skills": []}

        mock_mapper = MagicMock()
        mock_mapper.get_all_links.return_value = {"by_agent": {}, "by_skill": {}}

        with patch(
            "claude_mpm.services.monitor.config_routes._get_skills_deployer",
            return_value=mock_skills_svc,
        ), patch(
            "claude_mpm.services.monitor.config_routes._get_skill_to_agent_mapper",
            return_value=mock_mapper,
        ):
            resp = await self.client.request(
                "GET", "/api/config/skills/available?collection=universal"
            )
            assert resp.status == 200
            data = await resp.json()
            assert data["success"] is True
            assert data["filters_applied"]["collection"] == "universal"
            mock_skills_svc.list_available_skills.assert_called_once_with(
                collection="universal"
            )

    async def test_skills_available_service_error(self):
        with patch(
            "claude_mpm.services.monitor.config_routes._get_skills_deployer",
            side_effect=Exception("GitHub unreachable"),
        ):
            resp = await self.client.request("GET", "/api/config/skills/available")
            assert resp.status == 500
            data = await resp.json()
            assert data["success"] is False
            assert data["code"] == "SERVICE_ERROR"


class TestSources(AioHTTPTestCase):
    async def get_application(self):
        return create_test_app()

    async def test_sources_success(self):
        mock_agent_config = MagicMock()
        mock_repo = MagicMock()
        mock_repo.url = "https://github.com/bobmatnyc/claude-mpm-agents"
        mock_repo.subdirectory = "agents"
        mock_repo.enabled = True
        mock_repo.priority = 100
        mock_agent_config.repositories = [mock_repo]

        mock_skill_source = MagicMock()
        mock_skill_source.id = "system"
        mock_skill_source.url = "https://github.com/bobmatnyc/claude-mpm-skills"
        mock_skill_source.branch = "main"
        mock_skill_source.enabled = True
        mock_skill_source.priority = 0

        with patch(
            "claude_mpm.config.agent_sources.AgentSourceConfiguration.load",
            return_value=mock_agent_config,
        ), patch(
            "claude_mpm.config.skill_sources.SkillSourceConfiguration"
        ) as mock_skill_config_cls:
            mock_skill_config_inst = MagicMock()
            mock_skill_config_inst.load.return_value = [mock_skill_source]
            mock_skill_config_cls.return_value = mock_skill_config_inst

            resp = await self.client.request("GET", "/api/config/sources")
            assert resp.status == 200
            data = await resp.json()
            assert data["success"] is True
            assert data["total"] == 2
            # Sorted by priority - skill source (0) comes before agent source (100)
            assert data["sources"][0]["type"] == "skill"
            assert data["sources"][0]["priority"] == 0
            assert data["sources"][1]["type"] == "agent"
            assert data["sources"][1]["priority"] == 100

    async def test_sources_service_error(self):
        with patch(
            "claude_mpm.config.agent_sources.AgentSourceConfiguration.load",
            side_effect=Exception("Config corrupt"),
        ), patch(
            "claude_mpm.config.skill_sources.SkillSourceConfiguration"
        ) as mock_skill_config_cls:
            mock_skill_config_cls.side_effect = Exception("Config corrupt")

            resp = await self.client.request("GET", "/api/config/sources")
            assert resp.status == 200
            data = await resp.json()
            # Sources endpoint handles individual source errors gracefully
            assert data["success"] is True
            assert data["total"] == 0
            assert data["sources"] == []

    async def test_sources_empty_config(self):
        mock_agent_config = MagicMock()
        mock_agent_config.repositories = []

        with patch(
            "claude_mpm.config.agent_sources.AgentSourceConfiguration.load",
            return_value=mock_agent_config,
        ), patch(
            "claude_mpm.config.skill_sources.SkillSourceConfiguration"
        ) as mock_skill_config_cls:
            mock_skill_config_inst = MagicMock()
            mock_skill_config_inst.load.return_value = []
            mock_skill_config_cls.return_value = mock_skill_config_inst

            resp = await self.client.request("GET", "/api/config/sources")
            assert resp.status == 200
            data = await resp.json()
            assert data["success"] is True
            assert data["total"] == 0
            assert data["sources"] == []


# =============================================================================
# Phase 2: Backend API Enrichment Tests
# =============================================================================


class TestAgentsDeployedEnriched(AioHTTPTestCase):
    """Phase 2 Step 1: Verify enriched fields in deployed agents response."""

    async def get_application(self):
        return create_test_app()

    async def test_deployed_agents_include_enrichment_fields(self):
        """Verify that list_agents() now returns enrichment fields."""
        mock_agent_mgr = MagicMock()
        mock_agent_mgr.list_agents.return_value = {
            "python-engineer": {
                "location": "project",
                "path": "/p/.claude/agents/python-engineer.md",
                "version": "2.5.0",
                "type": "core",
                "specializations": ["python"],
                # Phase 2 enrichment fields:
                "description": "Python 3.12+ specialist",
                "category": "engineering",
                "color": "green",
                "tags": ["python", "async"],
                "resource_tier": "standard",
                "network_access": True,
                "skills_count": 18,
            },
        }

        with patch(
            "claude_mpm.services.monitor.config_routes._get_agent_manager",
            return_value=mock_agent_mgr,
        ), patch(
            "claude_mpm.config.agent_presets.CORE_AGENTS",
            [],
        ):
            resp = await self.client.request("GET", "/api/config/agents/deployed")
            assert resp.status == 200
            data = await resp.json()
            assert data["success"] is True
            agent = data["agents"][0]
            # Existing fields preserved
            assert agent["name"] == "python-engineer"
            assert agent["version"] == "2.5.0"
            assert agent["type"] == "core"
            # New enrichment fields
            assert agent["description"] == "Python 3.12+ specialist"
            assert agent["category"] == "engineering"
            assert agent["color"] == "green"
            assert agent["tags"] == ["python", "async"]
            assert agent["resource_tier"] == "standard"
            assert agent["network_access"] is True
            assert agent["skills_count"] == 18

    async def test_deployed_agents_default_enrichment_values(self):
        """Verify graceful defaults for agents missing optional fields."""
        mock_agent_mgr = MagicMock()
        mock_agent_mgr.list_agents.return_value = {
            "local-ops": {
                "location": "project",
                "path": "/p/.claude/agents/local-ops.md",
                "version": "1.0",
                "type": "core",
                "specializations": [],
                # Defaults from _extract_enrichment_fields
                "description": "",
                "category": "",
                "color": "gray",
                "tags": [],
                "resource_tier": "",
                "network_access": None,
                "skills_count": 0,
            },
        }

        with patch(
            "claude_mpm.services.monitor.config_routes._get_agent_manager",
            return_value=mock_agent_mgr,
        ), patch(
            "claude_mpm.config.agent_presets.CORE_AGENTS",
            [],
        ):
            resp = await self.client.request("GET", "/api/config/agents/deployed")
            assert resp.status == 200
            data = await resp.json()
            agent = data["agents"][0]
            assert agent["color"] == "gray"
            assert agent["tags"] == []
            assert agent["network_access"] is None
            assert agent["skills_count"] == 0


class TestSkillsDeployedEnriched(AioHTTPTestCase):
    """Phase 2 Step 3: Verify manifest cross-reference enrichment."""

    async def get_application(self):
        return create_test_app()

    async def test_deployed_skills_manifest_enrichment(self):
        """Verify that deployed skills get manifest fields added."""
        mock_skills_svc = MagicMock()
        mock_skills_svc.check_deployed_skills.return_value = {
            "deployed_count": 1,
            "skills": [
                {
                    "name": "universal-testing-tdd",
                    "path": "/home/.claude/skills/universal-testing-tdd",
                },
            ],
            "claude_skills_dir": "/home/.claude/skills",
        }
        # Manifest provides rich metadata
        mock_skills_svc.list_available_skills.return_value = {
            "skills": [
                {
                    "name": "tdd",
                    "description": "Comprehensive TDD patterns",
                    "version": "1.0.0",
                    "toolchain": None,
                    "framework": None,
                    "tags": ["testing", "tdd", "quality"],
                    "full_tokens": 3200,
                    "entry_point_tokens": 85,
                },
            ],
        }

        mock_index = {
            "deployed_skills": {
                "universal-testing-tdd": {
                    "description": "",
                    "category": "testing",
                    "collection": "universal",
                    "deployed_at": "2026-02-10",
                },
            },
            "user_requested_skills": [],
        }

        with patch(
            "claude_mpm.services.monitor.config_routes._get_skills_deployer",
            return_value=mock_skills_svc,
        ), patch(
            "claude_mpm.services.skills.selective_skill_deployer.load_deployment_index",
            return_value=mock_index,
        ):
            resp = await self.client.request("GET", "/api/config/skills/deployed")
            assert resp.status == 200
            data = await resp.json()
            assert data["success"] is True
            skill = data["skills"][0]
            # Manifest enrichment via suffix matching
            assert skill["version"] == "1.0.0"
            assert skill["tags"] == ["testing", "tdd", "quality"]
            assert skill["full_tokens"] == 3200
            assert skill["entry_point_tokens"] == 85
            # Description filled from manifest when deployment index has empty
            assert skill["description"] == "Comprehensive TDD patterns"

    async def test_deployed_skills_graceful_without_manifest(self):
        """Verify graceful degradation when manifest is unavailable."""
        mock_skills_svc = MagicMock()
        mock_skills_svc.check_deployed_skills.return_value = {
            "deployed_count": 1,
            "skills": [
                {"name": "custom-skill", "path": "/home/.claude/skills/custom-skill"},
            ],
            "claude_skills_dir": "/home/.claude/skills",
        }
        # Manifest call raises (network error)
        mock_skills_svc.list_available_skills.side_effect = Exception("Network error")

        mock_index = {
            "deployed_skills": {
                "custom-skill": {
                    "description": "Custom skill",
                    "category": "custom",
                    "collection": "",
                    "deployed_at": "2026-02-10",
                },
            },
            "user_requested_skills": ["custom-skill"],
        }

        with patch(
            "claude_mpm.services.monitor.config_routes._get_skills_deployer",
            return_value=mock_skills_svc,
        ), patch(
            "claude_mpm.services.skills.selective_skill_deployer.load_deployment_index",
            return_value=mock_index,
        ):
            resp = await self.client.request("GET", "/api/config/skills/deployed")
            assert resp.status == 200
            data = await resp.json()
            assert data["success"] is True
            skill = data["skills"][0]
            assert skill["name"] == "custom-skill"
            assert skill["description"] == "Custom skill"
            # Manifest fields should NOT be present (graceful degradation)
            assert "version" not in skill
            assert "tags" not in skill


class TestAgentDetail(AioHTTPTestCase):
    """Phase 2 Step 4: Agent detail endpoint tests."""

    async def get_application(self):
        return create_test_app()

    async def test_agent_detail_success(self):
        """Verify full agent detail response with all frontmatter fields."""
        mock_agent_mgr = MagicMock()
        mock_agent_def = MagicMock()
        mock_agent_def.raw_content = """---
name: Python Engineer
agent_id: python-engineer
description: "Python 3.12+ specialist"
version: "2.5.0"
category: engineering
color: green
tags:
  - python
  - async
resource_tier: standard
agent_type: engineer
temperature: 0.2
timeout: 900
capabilities:
  network_access: true
skills:
  required:
    - pytest
    - mypy
  optional:
    - dspy
dependencies:
  python:
    - black>=24.0.0
  system:
    - python3.12+
knowledge:
  domain_expertise:
    - "Python 3.12-3.13 features"
  constraints:
    - "Maximum 5 test files per session"
  best_practices:
    - "100% type coverage"
interactions:
  handoff_agents:
    - qa
    - security
author: Claude MPM Team
schema_version: "1.3.0"
---
# Python Engineer

Content here
"""
        mock_agent_def.metadata = MagicMock()
        mock_agent_def.metadata.version = "2.5.0"
        mock_agent_mgr.read_agent.return_value = mock_agent_def

        with patch(
            "claude_mpm.services.monitor.config_routes._get_agent_manager",
            return_value=mock_agent_mgr,
        ):
            resp = await self.client.request(
                "GET", "/api/config/agents/python-engineer/detail"
            )
            assert resp.status == 200
            data = await resp.json()
            assert data["success"] is True
            d = data["data"]
            assert d["name"] == "Python Engineer"
            assert d["agent_id"] == "python-engineer"
            assert d["description"] == "Python 3.12+ specialist"
            assert d["version"] == "2.5.0"
            assert d["category"] == "engineering"
            assert d["color"] == "green"
            assert d["tags"] == ["python", "async"]
            assert d["resource_tier"] == "standard"
            assert d["agent_type"] == "engineer"
            assert d["temperature"] == 0.2
            assert d["timeout"] == 900
            assert d["network_access"] is True
            assert "pytest" in d["skills"]
            assert "mypy" in d["skills"]
            assert "dspy" in d["skills"]
            assert d["dependencies"]["python"] == ["black>=24.0.0"]
            assert d["dependencies"]["system"] == ["python3.12+"]
            assert "Python 3.12-3.13 features" in d["knowledge"]["domain_expertise"]
            assert d["handoff_agents"] == ["qa", "security"]
            assert d["author"] == "Claude MPM Team"
            assert d["schema_version"] == "1.3.0"

    async def test_agent_detail_not_found(self):
        """Verify 404 response for non-existent agent."""
        mock_agent_mgr = MagicMock()
        mock_agent_mgr.read_agent.return_value = None

        with patch(
            "claude_mpm.services.monitor.config_routes._get_agent_manager",
            return_value=mock_agent_mgr,
        ):
            resp = await self.client.request(
                "GET", "/api/config/agents/nonexistent/detail"
            )
            assert resp.status == 404
            data = await resp.json()
            assert data["success"] is False
            assert data["code"] == "NOT_FOUND"
            assert "nonexistent" in data["error"]

    async def test_agent_detail_minimal_frontmatter(self):
        """Verify graceful defaults for agent with minimal frontmatter."""
        mock_agent_mgr = MagicMock()
        mock_agent_def = MagicMock()
        mock_agent_def.raw_content = """---
type: core
version: "1.0"
---
# Simple Agent

Just a simple agent.
"""
        mock_agent_def.metadata = MagicMock()
        mock_agent_def.metadata.version = "1.0"
        mock_agent_mgr.read_agent.return_value = mock_agent_def

        with patch(
            "claude_mpm.services.monitor.config_routes._get_agent_manager",
            return_value=mock_agent_mgr,
        ):
            resp = await self.client.request(
                "GET", "/api/config/agents/simple-agent/detail"
            )
            assert resp.status == 200
            data = await resp.json()
            d = data["data"]
            assert d["name"] == "simple-agent"
            assert d["color"] == "gray"
            assert d["tags"] == []
            assert d["skills"] == []
            assert d["dependencies"] == {}
            assert d["knowledge"]["domain_expertise"] == []
            assert d["handoff_agents"] == []

    async def test_agent_detail_path_traversal_blocked(self):
        """VP-1-SEC: Verify 400 for path traversal attempts."""
        # These should all be rejected by validate_safe_name()
        traversal_names = [
            "../secret",
            "foo/../../bar",
            "/etc/passwd",
            "..%2F..%2Fetc",
            "agent/../../../secret",
        ]
        for name in traversal_names:
            resp = await self.client.request("GET", f"/api/config/agents/{name}/detail")
            # Path traversal names containing "/" won't match the route at all
            # (aiohttp route matching), so they may get 404.
            # Names like "../secret" that do match should get 400.
            assert resp.status in (
                400,
                404,
            ), f"Expected 400/404 for '{name}', got {resp.status}"

    async def test_agent_detail_invalid_name_characters(self):
        """VP-1-SEC: Verify 400 for names with special characters."""
        resp = await self.client.request("GET", "/api/config/agents/..secret/detail")
        assert resp.status == 400
        data = await resp.json()
        assert data["code"] == "INVALID_NAME"

    async def test_agent_detail_service_error(self):
        """Verify 500 on internal service error."""
        with patch(
            "claude_mpm.services.monitor.config_routes._get_agent_manager",
            side_effect=Exception("Internal error"),
        ):
            resp = await self.client.request(
                "GET", "/api/config/agents/engineer/detail"
            )
            assert resp.status == 500
            data = await resp.json()
            assert data["success"] is False
            assert data["code"] == "SERVICE_ERROR"


class TestSkillDetail(AioHTTPTestCase):
    """Phase 2 Step 5: Skill detail endpoint tests."""

    async def get_application(self):
        return create_test_app()

    async def test_skill_detail_manifest_only(self):
        """Verify skill detail from manifest when not deployed."""
        mock_skills_svc = MagicMock()
        mock_skills_svc.list_available_skills.return_value = {
            "skills": [
                {
                    "name": "tdd",
                    "description": "TDD patterns",
                    "version": "1.0.0",
                    "toolchain": None,
                    "framework": None,
                    "tags": ["testing", "tdd"],
                    "full_tokens": 3200,
                    "entry_point_tokens": 85,
                    "requires": [],
                    "author": "claude-mpm",
                    "updated": "2025-12-15",
                    "source_path": "universal/testing/tdd/SKILL.md",
                },
            ],
        }

        mock_mapper = MagicMock()
        mock_mapper.get_all_links.return_value = {
            "by_agent": {},
            "by_skill": {
                "tdd": {
                    "agents": ["python-engineer", "qa"],
                    "sources": ["frontmatter"],
                },
            },
        }

        with patch(
            "claude_mpm.services.monitor.config_routes._get_skills_deployer",
            return_value=mock_skills_svc,
        ), patch(
            "claude_mpm.services.monitor.config_routes._get_skill_to_agent_mapper",
            return_value=mock_mapper,
        ), patch("pathlib.Path.exists", return_value=False):
            resp = await self.client.request(
                "GET", "/api/config/skills/universal-testing-tdd/detail"
            )
            assert resp.status == 200
            data = await resp.json()
            assert data["success"] is True
            d = data["data"]
            assert d["name"] == "universal-testing-tdd"
            # Manifest enrichment via suffix match (universal-testing-tdd ends with -tdd)
            assert d["version"] == "1.0.0"
            assert d["tags"] == ["testing", "tdd"]
            assert d["full_tokens"] == 3200
            assert d["description"] == "TDD patterns"
            # Agent links
            assert d["agent_count"] == 2
            assert "python-engineer" in d["used_by_agents"]

    async def test_skill_detail_path_traversal_blocked(self):
        """VP-1-SEC: Verify 400 for path traversal in skill names."""
        resp = await self.client.request("GET", "/api/config/skills/..secret/detail")
        assert resp.status == 400
        data = await resp.json()
        assert data["code"] == "INVALID_NAME"

    async def test_skill_detail_invalid_name(self):
        """VP-1-SEC: Verify 400 for names starting with non-alphanumeric."""
        resp = await self.client.request("GET", "/api/config/skills/-bad-name/detail")
        assert resp.status == 400
        data = await resp.json()
        assert data["code"] == "INVALID_NAME"

    async def test_skill_detail_service_error_graceful(self):
        """Verify graceful degradation when skills deployer fails.

        The skill detail endpoint catches individual data source errors
        internally and returns whatever data it can gather.
        """
        with patch(
            "claude_mpm.services.monitor.config_routes._get_skills_deployer",
            side_effect=Exception("Service error"),
        ), patch("pathlib.Path.exists", return_value=False):
            resp = await self.client.request(
                "GET", "/api/config/skills/some-skill/detail"
            )
            # Endpoint degrades gracefully - returns 200 with minimal data
            assert resp.status == 200
            data = await resp.json()
            assert data["success"] is True
            assert data["data"]["name"] == "some-skill"

    async def test_skill_detail_graceful_no_sources(self):
        """Verify minimal response when no data sources available."""
        mock_skills_svc = MagicMock()
        mock_skills_svc.list_available_skills.return_value = {"skills": []}

        mock_mapper = MagicMock()
        mock_mapper.get_all_links.return_value = {"by_agent": {}, "by_skill": {}}

        with patch(
            "claude_mpm.services.monitor.config_routes._get_skills_deployer",
            return_value=mock_skills_svc,
        ), patch(
            "claude_mpm.services.monitor.config_routes._get_skill_to_agent_mapper",
            return_value=mock_mapper,
        ), patch("pathlib.Path.exists", return_value=False):
            resp = await self.client.request(
                "GET", "/api/config/skills/unknown-skill/detail"
            )
            assert resp.status == 200
            data = await resp.json()
            assert data["success"] is True
            d = data["data"]
            assert d["name"] == "unknown-skill"
            assert d["used_by_agents"] == []
            assert d["agent_count"] == 0


class TestSkillsAvailableAgentCount(AioHTTPTestCase):
    """Phase 2 Step 6: Verify agent_count enrichment on available skills."""

    async def get_application(self):
        return create_test_app()

    async def test_agent_count_with_suffix_matching(self):
        """Verify suffix matching for agent_count enrichment."""
        mock_skills_svc = MagicMock()
        mock_skills_svc.list_available_skills.return_value = {
            "skills": [
                {"name": "test-driven-development", "category": "testing"},
            ],
        }
        mock_skills_svc.check_deployed_skills.return_value = {"skills": []}

        mock_mapper = MagicMock()
        mock_mapper.get_all_links.return_value = {
            "by_agent": {},
            "by_skill": {
                # Skill-links uses the short name
                "test-driven-development": {
                    "agents": ["python-engineer", "java-engineer", "qa"],
                    "sources": ["frontmatter"],
                },
            },
        }

        with patch(
            "claude_mpm.services.monitor.config_routes._get_skills_deployer",
            return_value=mock_skills_svc,
        ), patch(
            "claude_mpm.services.monitor.config_routes._get_skill_to_agent_mapper",
            return_value=mock_mapper,
        ):
            resp = await self.client.request("GET", "/api/config/skills/available")
            assert resp.status == 200
            data = await resp.json()
            skill = data["skills"][0]
            assert skill["agent_count"] == 3

    async def test_agent_count_graceful_mapper_error(self):
        """Verify skills still returned when mapper fails."""
        mock_skills_svc = MagicMock()
        mock_skills_svc.list_available_skills.return_value = {
            "skills": [
                {"name": "some-skill", "category": "general"},
            ],
        }
        mock_skills_svc.check_deployed_skills.return_value = {"skills": []}

        mock_mapper = MagicMock()
        mock_mapper.get_all_links.side_effect = Exception("Mapper error")

        with patch(
            "claude_mpm.services.monitor.config_routes._get_skills_deployer",
            return_value=mock_skills_svc,
        ), patch(
            "claude_mpm.services.monitor.config_routes._get_skill_to_agent_mapper",
            return_value=mock_mapper,
        ):
            resp = await self.client.request("GET", "/api/config/skills/available")
            assert resp.status == 200
            data = await resp.json()
            assert data["success"] is True
            assert data["total"] == 1
            # agent_count should NOT be present (graceful degradation)
            assert "agent_count" not in data["skills"][0]


class TestListAgentNames(AioHTTPTestCase):
    """Phase 2 Step 0: Verify list_agent_names() is used for is_deployed check."""

    async def get_application(self):
        return create_test_app()

    async def test_available_agents_uses_list_agent_names(self):
        """Verify handle_agents_available uses list_agent_names not list_agents."""
        mock_git_mgr = MagicMock()
        mock_git_mgr.list_cached_agents.return_value = [
            {"name": "agent-a", "description": "Agent A"},
        ]

        mock_agent_mgr = MagicMock()
        mock_agent_mgr.list_agent_names.return_value = {"agent-a"}

        with patch(
            "claude_mpm.services.monitor.config_routes._get_git_source_manager",
            return_value=mock_git_mgr,
        ), patch(
            "claude_mpm.services.monitor.config_routes._get_agent_manager",
            return_value=mock_agent_mgr,
        ):
            resp = await self.client.request("GET", "/api/config/agents/available")
            assert resp.status == 200
            # Verify list_agent_names was called (not list_agents)
            mock_agent_mgr.list_agent_names.assert_called_once_with(location="project")
            mock_agent_mgr.list_agents.assert_not_called()
