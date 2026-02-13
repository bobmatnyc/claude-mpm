"""Tests for configuration API routes (Phase 1: read-only endpoints).

Tests cover all 6 GET endpoints with:
- Happy path: Service returns data, handler returns 200
- Service error: Service raises exception, handler returns 500
- Empty state: Service returns empty data, handler returns 200 with empty arrays
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
        mock_agent_mgr.list_agents.return_value = {"python-engineer": {}}

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
        mock_agent_mgr.list_agents.return_value = {}

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

        with patch(
            "claude_mpm.services.monitor.config_routes._get_skills_deployer",
            return_value=mock_skills_svc,
        ):
            resp = await self.client.request("GET", "/api/config/skills/available")
            assert resp.status == 200
            data = await resp.json()
            assert data["success"] is True
            assert data["total"] == 3
            skills_by_name = {s["name"]: s for s in data["skills"]}
            assert skills_by_name["git-workflow"]["is_deployed"] is True
            assert skills_by_name["tdd"]["is_deployed"] is False
            assert "Cache-Control" in resp.headers

    async def test_skills_available_with_collection_filter(self):
        mock_skills_svc = MagicMock()
        mock_skills_svc.list_available_skills.return_value = {
            "total_skills": 1,
            "skills": [{"name": "tdd", "description": "TDD", "category": "testing"}],
        }
        mock_skills_svc.check_deployed_skills.return_value = {"skills": []}

        with patch(
            "claude_mpm.services.monitor.config_routes._get_skills_deployer",
            return_value=mock_skills_svc,
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
