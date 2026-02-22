"""Tests for Phase 3 deployment API endpoints.

Tests cover agent deploy/undeploy, batch deploy, skill deploy/undeploy,
mode switch preview/confirm, and auto-configure detect/preview.

Uses aiohttp.test_utils.AioHTTPTestCase following test_config_routes.py patterns.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase


def _mock_event_handler():
    """Create a mock ConfigEventHandler."""
    handler = MagicMock()
    handler.emit_config_event = AsyncMock()
    return handler


def _mock_file_watcher():
    """Create a mock ConfigFileWatcher."""
    watcher = MagicMock()
    watcher.update_mtime = MagicMock()
    return watcher


def _mock_backup_result(backup_id="bk-001"):
    """Create a mock BackupResult."""
    result = MagicMock()
    result.backup_id = backup_id
    result.backup_path = Path("/tmp/backups") / backup_id
    result.files_backed_up = 3
    result.size_bytes = 1024
    return result


def _mock_verification_result(passed=True):
    """Create a mock VerificationResult."""
    result = MagicMock()
    result.passed = passed
    result.timestamp = "2026-02-13T00:00:00+00:00"
    check = MagicMock()
    check.check = "file_exists"
    check.passed = passed
    check.path = "/tmp/agent.md"
    check.details = ""
    result.checks = [check]
    return result


def create_agent_deploy_app():
    """Create test app with agent deployment routes."""
    from claude_mpm.services.config_api.agent_deployment_handler import (
        register_agent_deployment_routes,
    )

    app = web.Application()
    handler = _mock_event_handler()
    watcher = _mock_file_watcher()
    register_agent_deployment_routes(app, handler, watcher)
    return app


def create_skill_deploy_app():
    """Create test app with skill deployment routes."""
    from claude_mpm.services.config_api.skill_deployment_handler import (
        register_skill_deployment_routes,
    )

    app = web.Application()
    handler = _mock_event_handler()
    watcher = _mock_file_watcher()
    register_skill_deployment_routes(app, handler, watcher)
    return app


def create_autoconfig_app():
    """Create test app with autoconfig routes."""
    from claude_mpm.services.config_api.autoconfig_handler import (
        register_autoconfig_routes,
    )

    app = web.Application()
    handler = _mock_event_handler()
    watcher = _mock_file_watcher()
    register_autoconfig_routes(app, handler, watcher)
    return app


# Reset lazy singletons between tests
def _reset_agent_handler_singletons():
    import claude_mpm.services.config_api.agent_deployment_handler as mod

    mod._backup_manager = None
    mod._operation_journal = None
    mod._deployment_verifier = None
    mod._agent_deployment_service = None


def _reset_skill_handler_singletons():
    import claude_mpm.services.config_api.skill_deployment_handler as mod

    mod._backup_manager = None
    mod._operation_journal = None
    mod._deployment_verifier = None
    mod._skills_deployer = None


# ====================================================================
# Agent Deploy Endpoints
# ====================================================================


class TestDeployAgentEndpoint(AioHTTPTestCase):
    async def get_application(self):
        _reset_agent_handler_singletons()
        return create_agent_deploy_app()

    async def test_deploy_agent_success(self):
        """POST /api/config/agents/deploy with valid agent returns 201."""
        mock_backup = _mock_backup_result()
        mock_verification = _mock_verification_result()

        with patch(
            "claude_mpm.services.config_api.agent_deployment_handler._get_backup_manager"
        ) as mock_bm, patch(
            "claude_mpm.services.config_api.agent_deployment_handler._get_operation_journal"
        ) as mock_jl, patch(
            "claude_mpm.services.config_api.agent_deployment_handler._get_deployment_verifier"
        ) as mock_dv, patch(
            "claude_mpm.services.config_api.agent_deployment_handler._get_agent_deployment_service"
        ) as mock_svc, patch(
            "claude_mpm.services.config_api.session_detector.detect_active_claude_sessions",
            return_value=[],
        ), patch("pathlib.Path.exists", return_value=False), patch(
            "pathlib.Path.mkdir"
        ):
            mock_bm.return_value.create_backup.return_value = mock_backup
            mock_jl.return_value.begin_operation.return_value = "op-1"
            mock_svc.return_value.deploy_agent.return_value = True
            mock_dv.return_value.verify_agent_deployed.return_value = mock_verification

            resp = await self.client.request(
                "POST",
                "/api/config/agents/deploy",
                json={"agent_name": "python-engineer"},
            )
            assert resp.status == 201
            data = await resp.json()
            assert data["success"] is True
            assert data["agent_name"] == "python-engineer"
            assert "backup_id" in data
            assert "verification" in data

    async def test_deploy_agent_missing_name(self):
        """POST without agent_name returns 400 VALIDATION_ERROR."""
        resp = await self.client.request(
            "POST",
            "/api/config/agents/deploy",
            json={"force": True},
        )
        assert resp.status == 400
        data = await resp.json()
        assert data["code"] == "VALIDATION_ERROR"

    async def test_deploy_agent_already_deployed(self):
        """POST for deployed agent without force returns 409 CONFLICT."""
        with patch("pathlib.Path.exists", return_value=True):
            resp = await self.client.request(
                "POST",
                "/api/config/agents/deploy",
                json={"agent_name": "existing-agent"},
            )
            assert resp.status == 409
            data = await resp.json()
            assert data["code"] == "CONFLICT"


class TestUndeployAgentEndpoint(AioHTTPTestCase):
    async def get_application(self):
        _reset_agent_handler_singletons()
        return create_agent_deploy_app()

    async def test_undeploy_core_agent_blocked(self):
        """DELETE core agent returns 403 CORE_AGENT_PROTECTED."""
        resp = await self.client.request(
            "DELETE",
            "/api/config/agents/engineer",
        )
        assert resp.status == 403
        data = await resp.json()
        assert data["code"] == "CORE_AGENT_PROTECTED"

    async def test_undeploy_nonexistent_agent(self):
        """DELETE non-deployed agent returns 404."""
        with patch("pathlib.Path.exists", return_value=False):
            resp = await self.client.request(
                "DELETE",
                "/api/config/agents/nonexistent-agent",
            )
            assert resp.status == 404
            data = await resp.json()
            assert data["code"] == "NOT_FOUND"

    async def test_undeploy_agent_success(self):
        """DELETE /api/config/agents/{name} removes non-core agent, returns 200."""
        mock_backup = _mock_backup_result()
        mock_verification = _mock_verification_result()

        with patch(
            "claude_mpm.services.config_api.agent_deployment_handler._get_backup_manager"
        ) as mock_bm, patch(
            "claude_mpm.services.config_api.agent_deployment_handler._get_operation_journal"
        ) as mock_jl, patch(
            "claude_mpm.services.config_api.agent_deployment_handler._get_deployment_verifier"
        ) as mock_dv, patch("pathlib.Path.exists", return_value=True), patch(
            "pathlib.Path.unlink"
        ):
            mock_bm.return_value.create_backup.return_value = mock_backup
            mock_jl.return_value.begin_operation.return_value = "op-2"
            mock_dv.return_value.verify_agent_undeployed.return_value = (
                mock_verification
            )

            resp = await self.client.request(
                "DELETE",
                "/api/config/agents/custom-agent",
            )
            assert resp.status == 200
            data = await resp.json()
            assert data["success"] is True
            assert data["agent_name"] == "custom-agent"


class TestBatchDeployEndpoint(AioHTTPTestCase):
    async def get_application(self):
        _reset_agent_handler_singletons()
        return create_agent_deploy_app()

    async def test_batch_deploy_success(self):
        """POST deploy-collection deploys all agents."""
        mock_backup = _mock_backup_result()
        mock_verification = _mock_verification_result()

        with patch(
            "claude_mpm.services.config_api.agent_deployment_handler._get_backup_manager"
        ) as mock_bm, patch(
            "claude_mpm.services.config_api.agent_deployment_handler._get_operation_journal"
        ) as mock_jl, patch(
            "claude_mpm.services.config_api.agent_deployment_handler._get_deployment_verifier"
        ) as mock_dv, patch(
            "claude_mpm.services.config_api.agent_deployment_handler._get_agent_deployment_service"
        ) as mock_svc, patch("pathlib.Path.mkdir"):
            mock_bm.return_value.create_backup.return_value = mock_backup
            mock_jl.return_value.begin_operation.return_value = "op-batch"
            mock_svc.return_value.deploy_agent.return_value = True
            mock_dv.return_value.verify_agent_deployed.return_value = mock_verification

            resp = await self.client.request(
                "POST",
                "/api/config/agents/deploy-collection",
                json={"agent_names": ["agent-a", "agent-b"]},
            )
            assert resp.status == 200
            data = await resp.json()
            assert data["success"] is True
            assert data["summary"]["total"] == 2
            assert data["summary"]["deployed"] == 2
            assert data["summary"]["failed"] == 0

    async def test_batch_deploy_partial_failure(self):
        """Batch with some failures continues, returns mixed results."""
        mock_backup = _mock_backup_result()
        mock_verification = _mock_verification_result()

        with patch(
            "claude_mpm.services.config_api.agent_deployment_handler._get_backup_manager"
        ) as mock_bm, patch(
            "claude_mpm.services.config_api.agent_deployment_handler._get_operation_journal"
        ) as mock_jl, patch(
            "claude_mpm.services.config_api.agent_deployment_handler._get_deployment_verifier"
        ) as mock_dv, patch(
            "claude_mpm.services.config_api.agent_deployment_handler._get_agent_deployment_service"
        ) as mock_svc, patch("pathlib.Path.mkdir"):
            mock_bm.return_value.create_backup.return_value = mock_backup
            mock_jl.return_value.begin_operation.return_value = "op-batch"
            # First succeeds, second fails
            mock_svc.return_value.deploy_agent.side_effect = [
                True,
                RuntimeError("fail"),
            ]
            mock_dv.return_value.verify_agent_deployed.return_value = mock_verification

            resp = await self.client.request(
                "POST",
                "/api/config/agents/deploy-collection",
                json={"agent_names": ["good-agent", "bad-agent"]},
            )
            assert resp.status == 200
            data = await resp.json()
            assert data["success"] is False  # Not all succeeded
            assert data["summary"]["deployed"] == 1
            assert data["summary"]["failed"] == 1

    async def test_batch_deploy_empty_list(self):
        """Batch with empty list returns 400."""
        resp = await self.client.request(
            "POST",
            "/api/config/agents/deploy-collection",
            json={"agent_names": []},
        )
        assert resp.status == 400
        data = await resp.json()
        assert data["code"] == "VALIDATION_ERROR"


# ====================================================================
# Skill Deploy Endpoints
# ====================================================================


class TestSkillDeployEndpoint(AioHTTPTestCase):
    async def get_application(self):
        _reset_skill_handler_singletons()
        return create_skill_deploy_app()

    async def test_deploy_skill_success(self):
        """POST /api/config/skills/deploy with valid skill returns 201."""
        mock_backup = _mock_backup_result()
        mock_verification = _mock_verification_result()

        with patch(
            "claude_mpm.services.config_api.skill_deployment_handler._get_backup_manager"
        ) as mock_bm, patch(
            "claude_mpm.services.config_api.skill_deployment_handler._get_operation_journal"
        ) as mock_jl, patch(
            "claude_mpm.services.config_api.skill_deployment_handler._get_deployment_verifier"
        ) as mock_dv, patch(
            "claude_mpm.services.config_api.skill_deployment_handler._get_skills_deployer"
        ) as mock_svc:
            mock_bm.return_value.create_backup.return_value = mock_backup
            mock_jl.return_value.begin_operation.return_value = "op-skill"
            mock_svc.return_value.deploy_skills.return_value = {
                "deployed_count": 1,
                "deployed_skills": ["my-skill"],
                "errors": [],
            }
            mock_dv.return_value.verify_skill_deployed.return_value = mock_verification

            resp = await self.client.request(
                "POST",
                "/api/config/skills/deploy",
                json={"skill_name": "my-skill"},
            )
            assert resp.status == 201
            data = await resp.json()
            assert data["success"] is True
            assert data["skill_name"] == "my-skill"

    async def test_deploy_skill_missing_name(self):
        """POST without skill_name returns 400."""
        resp = await self.client.request(
            "POST",
            "/api/config/skills/deploy",
            json={"collection": "universal"},
        )
        assert resp.status == 400
        data = await resp.json()
        assert data["code"] == "VALIDATION_ERROR"

    async def test_undeploy_core_skill_blocked(self):
        """DELETE immutable skill returns 403 IMMUTABLE_SKILL."""
        with patch(
            "claude_mpm.services.config_api.skill_deployment_handler._get_immutable_skills",
            return_value={
                "mpm-delegation-patterns",
                "universal-debugging-systematic-debugging",
            },
        ):
            resp = await self.client.request(
                "DELETE",
                "/api/config/skills/mpm-delegation-patterns",
            )
            assert resp.status == 403
            data = await resp.json()
            assert data["code"] == "IMMUTABLE_SKILL"


# ====================================================================
# Mode Switch Endpoints
# ====================================================================


class TestModeSwitchEndpoint(AioHTTPTestCase):
    async def get_application(self):
        _reset_skill_handler_singletons()
        return create_skill_deploy_app()

    async def test_mode_switch_preview(self):
        """PUT with preview=true returns impact data."""
        with patch(
            "claude_mpm.services.config_api.skill_deployment_handler._get_config_path",
            return_value=Path("/tmp/config.yaml"),
        ), patch(
            "claude_mpm.services.config_api.skill_deployment_handler._load_config",
            return_value={
                "skills": {
                    "deployment_mode": "full",
                    "agent_referenced": ["skill-a"],
                    "user_defined": ["skill-b"],
                },
            },
        ), patch(
            "claude_mpm.services.config_api.skill_deployment_handler._get_immutable_skills",
            return_value={"core-skill"},
        ), patch(
            "claude_mpm.services.config_api.skill_deployment_handler._get_skills_deployer"
        ) as mock_svc:
            mock_svc.return_value.check_deployed_skills.return_value = {
                "skills": [
                    {"name": "skill-a"},
                    {"name": "skill-b"},
                    {"name": "core-skill"},
                    {"name": "extra-skill"},
                ],
            }

            resp = await self.client.request(
                "PUT",
                "/api/config/skills/deployment-mode",
                json={"mode": "selective", "preview": True},
            )
            assert resp.status == 200
            data = await resp.json()
            assert data["success"] is True
            assert data["preview"] is True
            assert "impact" in data

    async def test_mode_switch_invalid_mode(self):
        """PUT with invalid mode returns 400."""
        resp = await self.client.request(
            "PUT",
            "/api/config/skills/deployment-mode",
            json={"mode": "invalid", "preview": True},
        )
        assert resp.status == 400
        data = await resp.json()
        assert data["code"] == "VALIDATION_ERROR"

    async def test_mode_switch_no_preview_or_confirm(self):
        """PUT without preview or confirm returns 400 CONFIRMATION_REQUIRED."""
        resp = await self.client.request(
            "PUT",
            "/api/config/skills/deployment-mode",
            json={"mode": "selective"},
        )
        assert resp.status == 400
        data = await resp.json()
        assert data["code"] == "CONFIRMATION_REQUIRED"


# ====================================================================
# Auto-Configure Endpoints
# ====================================================================


# ====================================================================
# Path Traversal Validation (C-01 / C-02)
# ====================================================================


class TestAgentNameValidation(AioHTTPTestCase):
    """Verify that path traversal attempts are blocked for agents."""

    async def get_application(self):
        _reset_agent_handler_singletons()
        return create_agent_deploy_app()

    async def test_deploy_valid_names_pass(self):
        """Valid agent names are accepted (validation does not block them)."""
        mock_backup = _mock_backup_result()
        mock_verification = _mock_verification_result()

        for name in ["my-agent", "agent_v2", "Research", "a1"]:
            with patch(
                "claude_mpm.services.config_api.agent_deployment_handler._get_backup_manager"
            ) as mock_bm, patch(
                "claude_mpm.services.config_api.agent_deployment_handler._get_operation_journal"
            ) as mock_jl, patch(
                "claude_mpm.services.config_api.agent_deployment_handler._get_deployment_verifier"
            ) as mock_dv, patch(
                "claude_mpm.services.config_api.agent_deployment_handler._get_agent_deployment_service"
            ) as mock_svc, patch(
                "claude_mpm.services.config_api.session_detector.detect_active_claude_sessions",
                return_value=[],
            ), patch("pathlib.Path.exists", return_value=False), patch(
                "pathlib.Path.mkdir"
            ):
                mock_bm.return_value.create_backup.return_value = mock_backup
                mock_jl.return_value.begin_operation.return_value = "op-1"
                mock_svc.return_value.deploy_agent.return_value = True
                mock_dv.return_value.verify_agent_deployed.return_value = (
                    mock_verification
                )

                resp = await self.client.request(
                    "POST",
                    "/api/config/agents/deploy",
                    json={"agent_name": name},
                )
                assert resp.status == 201, (
                    f"Expected 201 for name '{name}', got {resp.status}"
                )

    async def test_deploy_path_traversal_blocked(self):
        """Path traversal attempts via deploy are rejected with 400."""
        traversal_names = [
            "../../etc/passwd",
            "../secret",
            "foo/bar",
            "foo\\bar",
            ".hidden",
            "..double-dot",
        ]
        for name in traversal_names:
            resp = await self.client.request(
                "POST",
                "/api/config/agents/deploy",
                json={"agent_name": name},
            )
            assert resp.status == 400, (
                f"Expected 400 for name '{name}', got {resp.status}"
            )
            data = await resp.json()
            assert data["success"] is False
            assert data["code"] == "VALIDATION_ERROR"

    async def test_deploy_empty_name_blocked(self):
        """Empty agent_name is rejected."""
        resp = await self.client.request(
            "POST",
            "/api/config/agents/deploy",
            json={"agent_name": ""},
        )
        assert resp.status == 400
        data = await resp.json()
        assert data["code"] == "VALIDATION_ERROR"

    async def test_undeploy_path_traversal_blocked(self):
        """Path traversal via undeploy DELETE is rejected with 400."""
        # URL-encoded names that would be decoded by aiohttp
        for name in ["..secret", ".hidden"]:
            resp = await self.client.request(
                "DELETE",
                f"/api/config/agents/{name}",
            )
            assert resp.status == 400, (
                f"Expected 400 for name '{name}', got {resp.status}"
            )
            data = await resp.json()
            assert data["code"] == "VALIDATION_ERROR"


class TestSkillNameValidation(AioHTTPTestCase):
    """Verify that path traversal attempts are blocked for skills."""

    async def get_application(self):
        _reset_skill_handler_singletons()
        return create_skill_deploy_app()

    async def test_deploy_valid_skill_names_pass(self):
        """Valid skill names are accepted (validation does not block them)."""
        mock_backup = _mock_backup_result()
        mock_verification = _mock_verification_result()

        for name in ["my-skill", "skill_v2", "Research", "a1"]:
            with patch(
                "claude_mpm.services.config_api.skill_deployment_handler._get_backup_manager"
            ) as mock_bm, patch(
                "claude_mpm.services.config_api.skill_deployment_handler._get_operation_journal"
            ) as mock_jl, patch(
                "claude_mpm.services.config_api.skill_deployment_handler._get_deployment_verifier"
            ) as mock_dv, patch(
                "claude_mpm.services.config_api.skill_deployment_handler._get_skills_deployer"
            ) as mock_svc:
                mock_bm.return_value.create_backup.return_value = mock_backup
                mock_jl.return_value.begin_operation.return_value = "op-skill"
                mock_svc.return_value.deploy_skills.return_value = {
                    "deployed_count": 1,
                    "deployed_skills": [name],
                    "errors": [],
                }
                mock_dv.return_value.verify_skill_deployed.return_value = (
                    mock_verification
                )

                resp = await self.client.request(
                    "POST",
                    "/api/config/skills/deploy",
                    json={"skill_name": name},
                )
                assert resp.status == 201, (
                    f"Expected 201 for name '{name}', got {resp.status}"
                )

    async def test_deploy_skill_path_traversal_blocked(self):
        """Path traversal attempts via skill deploy are rejected with 400."""
        traversal_names = [
            "../../etc/passwd",
            "../secret",
            "foo/bar",
            "foo\\bar",
            ".hidden",
            "..double-dot",
        ]
        for name in traversal_names:
            resp = await self.client.request(
                "POST",
                "/api/config/skills/deploy",
                json={"skill_name": name},
            )
            assert resp.status == 400, (
                f"Expected 400 for name '{name}', got {resp.status}"
            )
            data = await resp.json()
            assert data["success"] is False
            assert data["code"] == "VALIDATION_ERROR"

    async def test_deploy_skill_empty_name_blocked(self):
        """Empty skill_name is rejected."""
        resp = await self.client.request(
            "POST",
            "/api/config/skills/deploy",
            json={"skill_name": ""},
        )
        assert resp.status == 400
        data = await resp.json()
        assert data["code"] == "VALIDATION_ERROR"

    async def test_undeploy_skill_path_traversal_blocked(self):
        """Path traversal via undeploy DELETE is rejected with 400."""
        for name in ["..secret", ".hidden"]:
            resp = await self.client.request(
                "DELETE",
                f"/api/config/skills/{name}",
            )
            assert resp.status == 400, (
                f"Expected 400 for name '{name}', got {resp.status}"
            )
            data = await resp.json()
            assert data["code"] == "VALIDATION_ERROR"


class TestBatchDeployValidation(AioHTTPTestCase):
    """Verify batch deploy validates each agent name."""

    async def get_application(self):
        _reset_agent_handler_singletons()
        return create_agent_deploy_app()

    async def test_batch_deploy_rejects_traversal_names(self):
        """Batch deploy with traversal names marks them as failed."""
        mock_backup = _mock_backup_result()
        mock_verification = _mock_verification_result()

        with patch(
            "claude_mpm.services.config_api.agent_deployment_handler._get_backup_manager"
        ) as mock_bm, patch(
            "claude_mpm.services.config_api.agent_deployment_handler._get_operation_journal"
        ) as mock_jl, patch(
            "claude_mpm.services.config_api.agent_deployment_handler._get_deployment_verifier"
        ) as mock_dv, patch(
            "claude_mpm.services.config_api.agent_deployment_handler._get_agent_deployment_service"
        ) as mock_svc, patch("pathlib.Path.mkdir"):
            mock_bm.return_value.create_backup.return_value = mock_backup
            mock_jl.return_value.begin_operation.return_value = "op-batch"
            mock_svc.return_value.deploy_agent.return_value = True
            mock_dv.return_value.verify_agent_deployed.return_value = mock_verification

            resp = await self.client.request(
                "POST",
                "/api/config/agents/deploy-collection",
                json={"agent_names": ["good-agent", "../../etc/passwd", ".hidden"]},
            )
            assert resp.status == 200
            data = await resp.json()
            assert data["success"] is False  # Not all succeeded
            assert data["summary"]["deployed"] == 1
            assert data["summary"]["failed"] == 2
            assert "good-agent" in data["deployed_agents"]
            assert "../../etc/passwd" in data["failed_agents"]
            assert ".hidden" in data["failed_agents"]


# ====================================================================
# Validation Unit Tests (no HTTP needed)
# ====================================================================


class TestValidateSafeName:
    """Unit tests for the validate_safe_name utility."""

    def test_valid_names(self):
        from claude_mpm.services.config_api.validation import validate_safe_name

        valid_names = [
            "my-agent",
            "agent_v2",
            "Research",
            "a1",
            "python-engineer",
            "ABC123",
            "test-agent-v3",
        ]
        for name in valid_names:
            is_valid, _msg = validate_safe_name(name, "agent")
            assert is_valid, f"Expected '{name}' to be valid, got error: {msg}"

    def test_path_traversal_rejected(self):
        from claude_mpm.services.config_api.validation import validate_safe_name

        bad_names = [
            "../../etc/passwd",
            "../secret",
            "../../.ssh/authorized_keys",
        ]
        for name in bad_names:
            is_valid, _msg = validate_safe_name(name, "agent")
            assert not is_valid, f"Expected '{name}' to be rejected"

    def test_slashes_rejected(self):
        from claude_mpm.services.config_api.validation import validate_safe_name

        for name in ["foo/bar", "foo\\bar", "a/b/c"]:
            is_valid, _msg = validate_safe_name(name, "agent")
            assert not is_valid, f"Expected '{name}' to be rejected"

    def test_empty_name_rejected(self):
        from claude_mpm.services.config_api.validation import validate_safe_name

        is_valid, _msg = validate_safe_name("", "agent")
        assert not is_valid

    def test_dot_prefixed_rejected(self):
        from claude_mpm.services.config_api.validation import validate_safe_name

        for name in [".hidden", "..double", ".env"]:
            is_valid, _msg = validate_safe_name(name, "agent")
            assert not is_valid, f"Expected '{name}' to be rejected"

    def test_special_chars_rejected(self):
        from claude_mpm.services.config_api.validation import validate_safe_name

        for name in ["agent name", "agent@v2", "agent;drop", "agent&cmd"]:
            is_valid, _msg = validate_safe_name(name, "agent")
            assert not is_valid, f"Expected '{name}' to be rejected"


# ====================================================================
# Auto-Configure Endpoints
# ====================================================================


class TestAutoConfigEndpoints(AioHTTPTestCase):
    async def get_application(self):
        return create_autoconfig_app()

    async def test_autoconfig_detect(self):
        """POST /api/config/auto-configure/detect returns toolchain."""
        mock_analysis = MagicMock()
        mock_analysis.language_detection.primary_language = "Python"
        mock_analysis.language_detection.primary_confidence.value = "high"
        mock_analysis.frameworks = []
        mock_analysis.build_tools = []
        mock_analysis.package_managers = []
        mock_analysis.deployment_target = None
        mock_analysis.overall_confidence.value = "high"
        mock_analysis.metadata = {}

        with patch(
            "claude_mpm.services.config_api.autoconfig_handler._get_toolchain_analyzer"
        ) as mock_analyzer, patch(
            "pathlib.Path.exists",
            return_value=True,
        ):
            mock_analyzer.return_value.analyze_toolchain.return_value = mock_analysis

            resp = await self.client.request(
                "POST",
                "/api/config/auto-configure/detect",
                json={},
            )
            assert resp.status == 200
            data = await resp.json()
            assert data["success"] is True
            assert data["toolchain"]["primary_language"] == "Python"

    async def test_autoconfig_preview(self):
        """POST /api/config/auto-configure/preview returns recommendations."""
        mock_preview = MagicMock()
        mock_preview.would_deploy = ["agent-a", "agent-b"]
        mock_preview.would_skip = []
        mock_preview.deployment_count = 2
        mock_preview.estimated_deployment_time = 5
        mock_preview.requires_confirmation = True
        mock_preview.recommendations = []
        mock_preview.validation_result = None
        mock_preview.detected_toolchain = None
        mock_preview.metadata = {}

        with patch(
            "claude_mpm.services.config_api.autoconfig_handler._get_auto_config_manager"
        ) as mock_mgr, patch(
            "pathlib.Path.exists",
            return_value=True,
        ):
            mock_mgr.return_value.preview_configuration.return_value = mock_preview

            resp = await self.client.request(
                "POST",
                "/api/config/auto-configure/preview",
                json={},
            )
            assert resp.status == 200
            data = await resp.json()
            assert data["success"] is True
            assert data["preview"]["deployment_count"] == 2
            assert data["preview"]["would_deploy"] == ["agent-a", "agent-b"]
