"""Tests for business rule enforcement in deployment API.

Tests cover:
- BR-01: 7 core agents cannot be undeployed
- Immutable skills (PM_CORE_SKILLS and CORE_SKILLS) cannot be undeployed
- Mode business rules (user_defined overrides, empty list blocking)
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase

from claude_mpm.services.config_api.agent_deployment_handler import CORE_AGENTS


def _mock_event_handler():
    handler = MagicMock()
    handler.emit_config_event = AsyncMock()
    return handler


def _mock_file_watcher():
    watcher = MagicMock()
    watcher.update_mtime = MagicMock()
    return watcher


def _reset_agent_singletons():
    import claude_mpm.services.config_api.agent_deployment_handler as mod

    mod._backup_manager = None
    mod._operation_journal = None
    mod._deployment_verifier = None
    mod._agent_deployment_service = None


def _reset_skill_singletons():
    import claude_mpm.services.config_api.skill_deployment_handler as mod

    mod._backup_manager = None
    mod._operation_journal = None
    mod._deployment_verifier = None
    mod._skills_deployer = None


def create_agent_app():
    from claude_mpm.services.config_api.agent_deployment_handler import (
        register_agent_deployment_routes,
    )

    app = web.Application()
    register_agent_deployment_routes(app, _mock_event_handler(), _mock_file_watcher())
    return app


def create_skill_app():
    from claude_mpm.services.config_api.skill_deployment_handler import (
        register_skill_deployment_routes,
    )

    app = web.Application()
    register_skill_deployment_routes(app, _mock_event_handler(), _mock_file_watcher())
    return app


class TestCoreAgentProtection(AioHTTPTestCase):
    """Test BR-01: 7 core agents cannot be undeployed."""

    async def get_application(self):
        _reset_agent_singletons()
        return create_agent_app()

    def test_core_agents_list_complete(self):
        """Verify all 7 expected core agents are defined."""
        expected = {
            "engineer",
            "research",
            "qa",
            "web-qa",
            "documentation",
            "ops",
            "ticketing",
        }
        assert set(CORE_AGENTS) == expected
        assert len(CORE_AGENTS) == 7

    async def test_all_seven_core_agents_return_403(self):
        """Each of 7 core agents returns 403 on undeploy."""
        for agent_name in CORE_AGENTS:
            resp = await self.client.request(
                "DELETE",
                f"/api/config/agents/{agent_name}",
            )
            assert resp.status == 403, (
                f"Expected 403 for core agent '{agent_name}', got {resp.status}"
            )
            data = await resp.json()
            assert data["code"] == "CORE_AGENT_PROTECTED"
            assert data["success"] is False


class TestImmutableSkillProtection(AioHTTPTestCase):
    """Test PM_CORE_SKILLS and CORE_SKILLS cannot be undeployed."""

    async def get_application(self):
        _reset_skill_singletons()
        return create_skill_app()

    async def test_pm_core_skills_immutable(self):
        """PM core skills return 403."""
        pm_core = [
            "mpm-delegation-patterns",
            "mpm-verification-protocols",
            "mpm-git-file-tracking",
        ]
        with patch(
            "claude_mpm.services.config_api.skill_deployment_handler._get_immutable_skills",
            return_value=set(pm_core),
        ):
            for skill in pm_core:
                resp = await self.client.request(
                    "DELETE",
                    f"/api/config/skills/{skill}",
                )
                assert resp.status == 403, f"Expected 403 for PM skill '{skill}'"
                data = await resp.json()
                assert data["code"] == "IMMUTABLE_SKILL"

    async def test_core_skills_immutable(self):
        """Core skills return 403."""
        core_skills = [
            "universal-debugging-systematic-debugging",
            "universal-testing-test-driven-development",
            "toolchains-typescript-core",
        ]
        with patch(
            "claude_mpm.services.config_api.skill_deployment_handler._get_immutable_skills",
            return_value=set(core_skills),
        ):
            for skill in core_skills:
                resp = await self.client.request(
                    "DELETE",
                    f"/api/config/skills/{skill}",
                )
                assert resp.status == 403, f"Expected 403 for core skill '{skill}'"
                data = await resp.json()
                assert data["code"] == "IMMUTABLE_SKILL"

    async def test_user_skill_can_be_undeployed(self):
        """Non-immutable skills are not blocked by immutability check."""
        mock_backup = MagicMock()
        mock_backup.backup_id = "bk-001"
        mock_verification = MagicMock()
        mock_verification.passed = True
        mock_verification.timestamp = "2026-02-13T00:00:00"
        mock_verification.checks = []

        with patch(
            "claude_mpm.services.config_api.skill_deployment_handler._get_immutable_skills",
            return_value={"mpm-delegation-patterns"},
        ), patch(
            "claude_mpm.services.config_api.skill_deployment_handler._get_backup_manager"
        ) as mock_bm, patch(
            "claude_mpm.services.config_api.skill_deployment_handler._get_operation_journal"
        ) as mock_jl, patch(
            "claude_mpm.services.config_api.skill_deployment_handler._get_deployment_verifier"
        ) as mock_dv, patch(
            "claude_mpm.services.config_api.skill_deployment_handler._get_skills_deployer"
        ) as mock_svc:
            mock_bm.return_value.create_backup.return_value = mock_backup
            mock_jl.return_value.begin_operation.return_value = "op-1"
            mock_svc.return_value.remove_skills.return_value = {"errors": []}
            mock_dv.return_value.verify_skill_undeployed.return_value = (
                mock_verification
            )

            resp = await self.client.request(
                "DELETE",
                "/api/config/skills/my-custom-skill",
            )
            assert resp.status == 200
            data = await resp.json()
            assert data["success"] is True


class TestModeBusinessRules(AioHTTPTestCase):
    """Test mode switch business rules."""

    async def get_application(self):
        _reset_skill_singletons()
        return create_skill_app()

    async def test_empty_user_defined_blocked(self):
        """Cannot switch to selective with empty allowed skill lists."""
        with patch(
            "claude_mpm.services.config_api.skill_deployment_handler._get_config_path",
            return_value=Path("/tmp/config.yaml"),
        ), patch(
            "claude_mpm.services.config_api.skill_deployment_handler._load_config",
            return_value={
                "skills": {
                    "deployment_mode": "full",
                    "agent_referenced": [],
                    "user_defined": [],
                },
            },
        ), patch(
            "claude_mpm.services.config_api.skill_deployment_handler._get_immutable_skills",
            return_value=set(),  # Empty immutable set for this test
        ), patch(
            "claude_mpm.services.config_api.skill_deployment_handler._get_skills_deployer"
        ) as mock_svc:
            mock_svc.return_value.check_deployed_skills.return_value = {
                "skills": [{"name": "skill-a"}],
            }

            resp = await self.client.request(
                "PUT",
                "/api/config/skills/deployment-mode",
                json={"mode": "selective", "preview": True},
            )
            assert resp.status == 400
            data = await resp.json()
            assert data["code"] == "EMPTY_SKILL_LIST"

    async def test_already_in_mode_returns_409(self):
        """Switching to current mode returns 409 ALREADY_IN_MODE."""
        with patch(
            "claude_mpm.services.config_api.skill_deployment_handler._get_config_path",
            return_value=Path("/tmp/config.yaml"),
        ), patch(
            "claude_mpm.services.config_api.skill_deployment_handler._load_config",
            return_value={
                "skills": {"deployment_mode": "selective"},
            },
        ):
            resp = await self.client.request(
                "PUT",
                "/api/config/skills/deployment-mode",
                json={"mode": "selective", "preview": True},
            )
            assert resp.status == 409
            data = await resp.json()
            assert data["code"] == "ALREADY_IN_MODE"
