"""Tests for source management API routes (Phase 2: mutation endpoints).

Tests cover add/remove/update/sync operations for agent and skill sources.
All underlying services are mocked to avoid filesystem I/O and Git operations.

Testing pattern follows tests/test_config_routes.py -- uses aiohttp
AioHTTPTestCase with a minimal app that registers only the source routes
with mocked dependencies.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase

# The module under test
from claude_mpm.services.monitor.routes.config_sources import (
    active_sync_tasks,
    register_source_routes,
    sync_status,
)


def _create_source_test_app() -> web.Application:
    """Create a test aiohttp app with mocked source routes registered."""
    app = web.Application()

    # Mock dependencies that register_source_routes captures via closure
    mock_event_handler = AsyncMock()
    mock_event_handler.emit_config_event = AsyncMock()

    mock_file_watcher = MagicMock()
    mock_file_watcher.update_mtime = MagicMock()

    # Store on app for test access
    app["_mock_event_handler"] = mock_event_handler
    app["_mock_file_watcher"] = mock_file_watcher

    register_source_routes(app, mock_event_handler, mock_file_watcher)
    return app


class TestAddAgentSource(AioHTTPTestCase):
    """POST /api/config/sources/agent"""

    async def get_application(self) -> web.Application:
        return _create_source_test_app()

    # 1. test_add_agent_source_success
    async def test_add_agent_source_success(self) -> None:
        """Valid URL returns 201 with source data."""
        mock_repo = MagicMock()
        mock_repo.identifier = "owner/repo/agents"
        mock_repo.url = "https://github.com/owner/repo"
        mock_repo.subdirectory = "agents"
        mock_repo.priority = 500
        mock_repo.enabled = True

        mock_config = MagicMock()
        mock_config.repositories = []
        mock_config.add_repository = MagicMock()
        mock_config.save = MagicMock()

        with patch(
            "claude_mpm.services.monitor.routes.config_sources.config_file_lock",
            MagicMock(),
        ), patch(
            "claude_mpm.config.agent_sources.AgentSourceConfiguration.load",
            return_value=mock_config,
        ), patch(
            "claude_mpm.models.git_repository.GitRepository",
            return_value=mock_repo,
        ):
            resp = await self.client.request(
                "POST",
                "/api/config/sources/agent",
                json={
                    "url": "https://github.com/owner/repo",
                    "subdirectory": "agents",
                    "priority": 500,
                    "enabled": True,
                },
            )

        assert resp.status == 201
        data = await resp.json()
        assert data["success"] is True
        assert "source" in data
        assert data["source"]["url"] == "https://github.com/owner/repo"

    # 2. test_add_agent_source_invalid_url
    async def test_add_agent_source_invalid_url(self) -> None:
        """Non-GitHub URL returns 400 VALIDATION_ERROR."""
        resp = await self.client.request(
            "POST",
            "/api/config/sources/agent",
            json={"url": "https://gitlab.com/owner/repo"},
        )

        assert resp.status == 400
        data = await resp.json()
        assert data["code"] == "VALIDATION_ERROR"
        assert "GitHub" in data["error"]

    # 3. test_add_agent_source_duplicate
    async def test_add_agent_source_duplicate(self) -> None:
        """Same identifier returns 409 CONFLICT."""
        existing_repo = MagicMock()
        existing_repo.identifier = "owner/repo"

        mock_config = MagicMock()
        mock_config.repositories = [existing_repo]

        new_repo = MagicMock()
        new_repo.identifier = "owner/repo"

        with patch(
            "claude_mpm.services.monitor.routes.config_sources.config_file_lock",
            MagicMock(),
        ), patch(
            "claude_mpm.config.agent_sources.AgentSourceConfiguration.load",
            return_value=mock_config,
        ), patch(
            "claude_mpm.models.git_repository.GitRepository",
            return_value=new_repo,
        ):
            resp = await self.client.request(
                "POST",
                "/api/config/sources/agent",
                json={"url": "https://github.com/owner/repo"},
            )

        assert resp.status == 409
        data = await resp.json()
        assert data["code"] == "CONFLICT"
        assert "already exists" in data["error"]

    # 4. test_add_agent_source_priority_out_of_range
    async def test_add_agent_source_priority_out_of_range(self) -> None:
        """Priority 1001 returns 400."""
        resp = await self.client.request(
            "POST",
            "/api/config/sources/agent",
            json={
                "url": "https://github.com/owner/repo",
                "priority": 1001,
            },
        )

        assert resp.status == 400
        data = await resp.json()
        assert data["code"] == "VALIDATION_ERROR"
        assert "Priority" in data["error"]


class TestAddSkillSource(AioHTTPTestCase):
    """POST /api/config/sources/skill"""

    async def get_application(self) -> web.Application:
        return _create_source_test_app()

    # 5. test_add_skill_source_success
    async def test_add_skill_source_success(self) -> None:
        """Valid source returns 201."""
        mock_source = MagicMock()
        mock_source.id = "my-skills"
        mock_source.type = "git"
        mock_source.url = "https://github.com/owner/skills"
        mock_source.branch = "main"
        mock_source.priority = 100
        mock_source.enabled = True

        mock_ssc = MagicMock()
        mock_ssc.add_source = MagicMock()

        with patch(
            "claude_mpm.services.monitor.routes.config_sources.config_file_lock",
            MagicMock(),
        ), patch(
            "claude_mpm.config.skill_sources.SkillSourceConfiguration",
            return_value=mock_ssc,
        ), patch(
            "claude_mpm.config.skill_sources.SkillSource",
            return_value=mock_source,
        ):
            resp = await self.client.request(
                "POST",
                "/api/config/sources/skill",
                json={
                    "url": "https://github.com/owner/skills",
                    "id": "my-skills",
                    "branch": "main",
                    "priority": 100,
                },
            )

        assert resp.status == 201
        data = await resp.json()
        assert data["success"] is True
        assert data["source"]["id"] == "my-skills"

    # 6. test_add_skill_source_invalid_id
    async def test_add_skill_source_invalid_id(self) -> None:
        """ID with spaces returns 400."""
        resp = await self.client.request(
            "POST",
            "/api/config/sources/skill",
            json={
                "url": "https://github.com/owner/skills",
                "id": "my skills",
            },
        )

        assert resp.status == 400
        data = await resp.json()
        assert data["code"] == "VALIDATION_ERROR"
        assert "Source ID" in data["error"]

    # 7. test_add_skill_source_no_token_in_response
    async def test_add_skill_source_no_token_in_response(self) -> None:
        """Token is never included in response body."""
        mock_source = MagicMock()
        mock_source.id = "my-skills"
        mock_source.type = "git"
        mock_source.url = "https://github.com/owner/skills"
        mock_source.branch = "main"
        mock_source.priority = 100
        mock_source.enabled = True

        mock_ssc = MagicMock()
        mock_ssc.add_source = MagicMock()

        with patch(
            "claude_mpm.services.monitor.routes.config_sources.config_file_lock",
            MagicMock(),
        ), patch(
            "claude_mpm.config.skill_sources.SkillSourceConfiguration",
            return_value=mock_ssc,
        ), patch(
            "claude_mpm.config.skill_sources.SkillSource",
            return_value=mock_source,
        ):
            resp = await self.client.request(
                "POST",
                "/api/config/sources/skill",
                json={
                    "url": "https://github.com/owner/skills",
                    "id": "my-skills",
                    "token": "ghp_secret_token_12345",
                },
            )

        assert resp.status == 201
        data = await resp.json()
        # Token must never appear in the response
        response_text = str(data)
        assert "ghp_secret_token_12345" not in response_text
        assert "token" not in data.get("source", {})


class TestRemoveSource(AioHTTPTestCase):
    """DELETE /api/config/sources/{type}"""

    async def get_application(self) -> web.Application:
        return _create_source_test_app()

    # 8. test_remove_source_success
    async def test_remove_source_success(self) -> None:
        """Valid ID returns 200."""
        mock_config = MagicMock()
        mock_config.remove_repository = MagicMock(return_value=True)
        mock_config.save = MagicMock()

        with patch(
            "claude_mpm.services.monitor.routes.config_sources.config_file_lock",
            MagicMock(),
        ), patch(
            "claude_mpm.config.agent_sources.AgentSourceConfiguration.load",
            return_value=mock_config,
        ):
            resp = await self.client.request(
                "DELETE",
                "/api/config/sources/agent?id=custom-source",
            )

        assert resp.status == 200
        data = await resp.json()
        assert data["success"] is True
        assert "custom-source" in data["message"]

    # 9. test_remove_source_not_found
    async def test_remove_source_not_found(self) -> None:
        """Unknown ID returns 404."""
        mock_config = MagicMock()
        mock_config.remove_repository = MagicMock(return_value=False)

        with patch(
            "claude_mpm.services.monitor.routes.config_sources.config_file_lock",
            MagicMock(),
        ), patch(
            "claude_mpm.config.agent_sources.AgentSourceConfiguration.load",
            return_value=mock_config,
        ):
            resp = await self.client.request(
                "DELETE",
                "/api/config/sources/agent?id=nonexistent",
            )

        assert resp.status == 404
        data = await resp.json()
        assert data["code"] == "NOT_FOUND"

    # 10. test_remove_system_source_blocked
    async def test_remove_system_source_blocked(self) -> None:
        """Default source returns 403 PROTECTED_SOURCE."""
        resp = await self.client.request(
            "DELETE",
            "/api/config/sources/agent?id=bobmatnyc/claude-mpm-agents/agents",
        )

        assert resp.status == 403
        data = await resp.json()
        assert data["code"] == "PROTECTED_SOURCE"
        assert (
            "default" in data["error"].lower() or "protected" in data["error"].lower()
        )


class TestUpdateSource(AioHTTPTestCase):
    """PATCH /api/config/sources/{type}"""

    async def get_application(self) -> web.Application:
        return _create_source_test_app()

    # 11. test_update_source_priority
    async def test_update_source_priority(self) -> None:
        """Valid priority update returns 200."""
        mock_repo = MagicMock()
        mock_repo.identifier = "custom-source"
        mock_repo.enabled = True
        mock_repo.priority = 100

        mock_config = MagicMock()
        mock_config.repositories = [mock_repo]
        mock_config.save = MagicMock()

        with patch(
            "claude_mpm.services.monitor.routes.config_sources.config_file_lock",
            MagicMock(),
        ), patch(
            "claude_mpm.config.agent_sources.AgentSourceConfiguration.load",
            return_value=mock_config,
        ):
            resp = await self.client.request(
                "PATCH",
                "/api/config/sources/agent?id=custom-source",
                json={"priority": 200},
            )

        assert resp.status == 200
        data = await resp.json()
        assert data["success"] is True
        assert data["source"]["priority"] == 200

    # 12. test_update_source_disable_system_blocked
    async def test_update_source_disable_system_blocked(self) -> None:
        """Disable default source returns 403."""
        resp = await self.client.request(
            "PATCH",
            "/api/config/sources/skill?id=system",
            json={"enabled": False},
        )

        assert resp.status == 403
        data = await resp.json()
        assert data["code"] == "PROTECTED_SOURCE"


class TestSyncSource(AioHTTPTestCase):
    """POST /api/config/sources/{type}/sync"""

    async def get_application(self) -> web.Application:
        return _create_source_test_app()

    def setUp(self) -> None:
        super().setUp()
        # Clear module-level state before each test
        active_sync_tasks.clear()
        sync_status.clear()

    # 13. test_sync_source_returns_202
    async def test_sync_source_returns_202(self) -> None:
        """Returns 202 with job_id."""
        # Patch the background _run_sync so it doesn't actually do Git ops
        with patch(
            "claude_mpm.services.monitor.routes.config_sources._run_sync",
            new_callable=AsyncMock,
        ):
            resp = await self.client.request(
                "POST",
                "/api/config/sources/agent/sync?id=my-source",
            )

        assert resp.status == 202
        data = await resp.json()
        assert data["success"] is True
        assert "job_id" in data
        assert data["status"] == "in_progress"

    # 14. test_sync_source_not_found_type_validation
    async def test_sync_source_not_found(self) -> None:
        """Missing source id returns 400."""
        resp = await self.client.request(
            "POST",
            "/api/config/sources/agent/sync",
        )

        assert resp.status == 400
        data = await resp.json()
        assert data["code"] == "VALIDATION_ERROR"


class TestSyncAll(AioHTTPTestCase):
    """POST /api/config/sources/sync-all"""

    async def get_application(self) -> web.Application:
        return _create_source_test_app()

    def setUp(self) -> None:
        super().setUp()
        active_sync_tasks.clear()
        sync_status.clear()

    # 15. test_sync_all_returns_202
    async def test_sync_all_returns_202(self) -> None:
        """Returns 202 with source count."""
        mock_agent_config = MagicMock()
        mock_agent_config.get_enabled_repositories.return_value = [
            MagicMock(),
            MagicMock(),
        ]

        mock_ssc = MagicMock()
        mock_skill_1 = MagicMock()
        mock_skill_1.enabled = True
        mock_skill_2 = MagicMock()
        mock_skill_2.enabled = True
        mock_ssc.load.return_value = [mock_skill_1, mock_skill_2]

        with patch(
            "claude_mpm.config.agent_sources.AgentSourceConfiguration.load",
            return_value=mock_agent_config,
        ), patch(
            "claude_mpm.config.skill_sources.SkillSourceConfiguration",
            return_value=mock_ssc,
        ), patch(
            "claude_mpm.services.monitor.routes.config_sources._run_sync_all",
            new_callable=AsyncMock,
        ):
            resp = await self.client.request(
                "POST",
                "/api/config/sources/sync-all",
            )

        assert resp.status == 202
        data = await resp.json()
        assert data["success"] is True
        assert "job_id" in data
        assert data["sources_to_sync"] == 4  # 2 agent + 2 skill


class TestSyncStatus(AioHTTPTestCase):
    """GET /api/config/sources/sync-status"""

    async def get_application(self) -> web.Application:
        return _create_source_test_app()

    def setUp(self) -> None:
        super().setUp()
        active_sync_tasks.clear()
        sync_status.clear()

    # 16. test_sync_status_no_active
    async def test_sync_status_no_active(self) -> None:
        """Returns is_syncing=false when idle."""
        resp = await self.client.request(
            "GET",
            "/api/config/sources/sync-status",
        )

        assert resp.status == 200
        data = await resp.json()
        assert data["success"] is True
        assert data["is_syncing"] is False
        assert data["active_jobs"] == []
