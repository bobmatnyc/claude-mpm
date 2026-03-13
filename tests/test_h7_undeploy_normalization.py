"""Tests for H7a-H7d: undeploy path normalization.

Verifies that all four undeploy code paths normalize agent IDs using
the canonical ``normalize_agent_id()`` so that underscore/hyphen
mismatches, ``-agent`` suffixes, and mixed case are handled correctly.
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from claude_mpm.utils.agent_filters import normalize_agent_id

# ---------------------------------------------------------------------------
# Tests for normalize_agent_id standalone function
# ---------------------------------------------------------------------------


class TestNormalizeAgentIdStandalone:
    """Unit tests for the standalone normalize_agent_id function."""

    def test_underscore_to_hyphen(self):
        assert normalize_agent_id("dart_engineer") == "dart-engineer"

    def test_already_normalized(self):
        assert normalize_agent_id("dart-engineer") == "dart-engineer"

    def test_strip_agent_suffix(self):
        assert normalize_agent_id("research-agent") == "research"

    def test_strip_agent_suffix_with_underscores(self):
        assert normalize_agent_id("research_agent") == "research"

    def test_mixed_case(self):
        assert normalize_agent_id("Dart_Engineer") == "dart-engineer"

    def test_spaces_to_hyphens(self):
        assert normalize_agent_id("QA Agent") == "qa"

    def test_path_with_slash(self):
        assert normalize_agent_id("category/dart_engineer") == "dart-engineer"

    def test_strip_md_extension(self):
        assert normalize_agent_id("dart_engineer.md") == "dart-engineer"

    def test_strip_yaml_extension(self):
        assert normalize_agent_id("dart_engineer.yaml") == "dart-engineer"

    def test_empty_string(self):
        assert normalize_agent_id("") == ""

    def test_whitespace_only(self):
        assert normalize_agent_id("   ") == ""

    def test_collapse_multiple_hyphens(self):
        assert normalize_agent_id("dart--engineer") == "dart-engineer"

    def test_strip_leading_trailing_hyphens(self):
        assert normalize_agent_id("-engineer-") == "engineer"


# ---------------------------------------------------------------------------
# H7a: agent_deployment_handler.py undeploy path
# ---------------------------------------------------------------------------


class TestH7aUndeployHandler:
    """Tests that the DELETE /api/config/agents/{agent_name} handler
    normalizes the agent name before constructing the file path."""

    @pytest.mark.asyncio
    async def test_undeploy_normalizes_agent_name(self, tmp_path):
        """Send DELETE for 'dart_engineer', verify it finds 'dart-engineer.md'."""
        from aiohttp import web
        from aiohttp.test_utils import TestClient, TestServer

        import claude_mpm.services.config_api.agent_deployment_handler as handler

        # Reset singletons
        handler._backup_manager = None
        handler._operation_journal = None
        handler._deployment_verifier = None
        handler._agent_deployment_service = None

        app = web.Application()
        event_handler = MagicMock()
        event_handler.emit_config_event = AsyncMock()
        file_watcher = MagicMock()
        handler.register_agent_deployment_routes(app, event_handler, file_watcher)

        # Create a fake agents directory with the normalized filename
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        agent_file = agents_dir / "dart-engineer.md"
        agent_file.write_text("# Dart Engineer\n")

        # Patch DeploymentContext to use our tmp_path
        mock_ctx = MagicMock()
        mock_ctx.agents_dir = agents_dir

        with patch.object(handler, "DeploymentContext") as mock_dc_cls:
            mock_dc_cls.from_request_scope.return_value = mock_ctx

            # Mock safety helpers
            with patch.object(
                handler, "validate_safe_name", return_value=(True, None)
            ), patch.object(
                handler, "validate_path_containment", return_value=(True, None)
            ), patch.object(handler, "_get_backup_manager") as mock_bm, patch.object(
                handler, "_get_operation_journal"
            ) as mock_journal, patch.object(
                handler, "_get_deployment_verifier"
            ) as mock_verifier:
                mock_bm.return_value.create_backup.return_value = MagicMock(
                    backup_path=tmp_path / "backup"
                )
                mock_journal.return_value.record.return_value = None
                mock_verifier.return_value.verify_file_absent.return_value = True

                async with TestClient(TestServer(app)) as client:
                    # DELETE with underscore variant
                    resp = await client.delete(
                        "/api/config/agents/dart_engineer?scope=project"
                    )
                    body = await resp.json()

                    # The handler should have normalized 'dart_engineer' to
                    # 'dart-engineer' and found 'dart-engineer.md'
                    # If normalization works, we should NOT get a 404
                    assert resp.status != 404, (
                        f"Expected handler to normalize 'dart_engineer' to "
                        f"'dart-engineer', but got 404. Body: {body}"
                    )

    @pytest.mark.asyncio
    async def test_undeploy_strips_agent_suffix(self, tmp_path):
        """Send DELETE for 'research-agent', verify it finds 'research.md'."""
        from aiohttp import web
        from aiohttp.test_utils import TestClient, TestServer

        import claude_mpm.services.config_api.agent_deployment_handler as handler

        handler._backup_manager = None
        handler._operation_journal = None
        handler._deployment_verifier = None
        handler._agent_deployment_service = None

        app = web.Application()
        event_handler = MagicMock()
        event_handler.emit_config_event = AsyncMock()
        file_watcher = MagicMock()
        handler.register_agent_deployment_routes(app, event_handler, file_watcher)

        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        agent_file = agents_dir / "research.md"
        agent_file.write_text("# Research Agent\n")

        mock_ctx = MagicMock()
        mock_ctx.agents_dir = agents_dir

        with patch.object(handler, "DeploymentContext") as mock_dc_cls:
            mock_dc_cls.from_request_scope.return_value = mock_ctx

            with patch.object(
                handler, "validate_safe_name", return_value=(True, None)
            ), patch.object(
                handler, "validate_path_containment", return_value=(True, None)
            ), patch.object(handler, "_get_backup_manager") as mock_bm, patch.object(
                handler, "_get_operation_journal"
            ) as mock_journal, patch.object(
                handler, "_get_deployment_verifier"
            ) as mock_verifier:
                mock_bm.return_value.create_backup.return_value = MagicMock(
                    backup_path=tmp_path / "backup"
                )
                mock_journal.return_value.record.return_value = None
                mock_verifier.return_value.verify_file_absent.return_value = True

                async with TestClient(TestServer(app)) as client:
                    resp = await client.delete(
                        "/api/config/agents/research-agent?scope=project"
                    )
                    body = await resp.json()

                    assert resp.status != 404, (
                        f"Expected 'research-agent' to normalize to 'research' "
                        f"and find research.md, but got 404. Body: {body}"
                    )


# ---------------------------------------------------------------------------
# H7b: single_tier_deployment_service.py remove_agent
# ---------------------------------------------------------------------------


class TestH7bSingleTierRemoveAgent:
    """Tests that SingleTierDeploymentService.remove_agent normalizes
    the agent name before constructing the file path."""

    def test_remove_agent_normalizes_name(self, tmp_path):
        """Create 'dart-engineer.md', call remove_agent('dart_engineer'),
        verify the file is deleted."""
        from claude_mpm.services.agents.single_tier_deployment_service import (
            SingleTierDeploymentService,
        )

        deploy_dir = tmp_path / "agents"
        deploy_dir.mkdir()
        agent_file = deploy_dir / "dart-engineer.md"
        agent_file.write_text("# Dart Engineer\n")

        mock_config = Mock()
        mock_config.get_enabled_repositories.return_value = []

        service = SingleTierDeploymentService(
            config=mock_config,
            deployment_dir=deploy_dir,
            cache_root=tmp_path / "cache",
        )

        result = service.remove_agent("dart_engineer")

        assert result is True
        assert not agent_file.exists(), "dart-engineer.md should have been deleted"

    def test_remove_agent_strips_suffix(self, tmp_path):
        """Create 'research.md', call remove_agent('research-agent'),
        verify the file is deleted."""
        from claude_mpm.services.agents.single_tier_deployment_service import (
            SingleTierDeploymentService,
        )

        deploy_dir = tmp_path / "agents"
        deploy_dir.mkdir()
        agent_file = deploy_dir / "research.md"
        agent_file.write_text("# Research\n")

        mock_config = Mock()
        mock_config.get_enabled_repositories.return_value = []

        service = SingleTierDeploymentService(
            config=mock_config,
            deployment_dir=deploy_dir,
            cache_root=tmp_path / "cache",
        )

        result = service.remove_agent("research-agent")

        assert result is True
        assert not agent_file.exists(), "research.md should have been deleted"


# ---------------------------------------------------------------------------
# H7c: deployment_reconciler.py _remove_agent
# ---------------------------------------------------------------------------


class TestH7cDeploymentReconcilerRemoveAgent:
    """Tests that DeploymentReconciler._remove_agent normalizes the
    agent ID before constructing the file path."""

    def test_remove_agent_normalizes_id(self, tmp_path):
        """Create 'dart-engineer.md', call _remove_agent('dart_engineer', dir),
        verify the file is deleted."""
        from claude_mpm.services.agents.deployment.deployment_reconciler import (
            DeploymentReconciler,
        )

        deploy_dir = tmp_path / "agents"
        deploy_dir.mkdir()
        agent_file = deploy_dir / "dart-engineer.md"
        agent_file.write_text("# Dart Engineer\n")

        mock_config = MagicMock()
        reconciler = DeploymentReconciler(config=mock_config)

        reconciler._remove_agent("dart_engineer", deploy_dir)

        assert not agent_file.exists(), "dart-engineer.md should have been deleted"

    def test_remove_agent_strips_suffix(self, tmp_path):
        """Create 'research.md', call _remove_agent('research-agent', dir),
        verify the file is deleted."""
        from claude_mpm.services.agents.deployment.deployment_reconciler import (
            DeploymentReconciler,
        )

        deploy_dir = tmp_path / "agents"
        deploy_dir.mkdir()
        agent_file = deploy_dir / "research.md"
        agent_file.write_text("# Research\n")

        mock_config = MagicMock()
        reconciler = DeploymentReconciler(config=mock_config)

        reconciler._remove_agent("research-agent", deploy_dir)

        assert not agent_file.exists(), "research.md should have been deleted"


# ---------------------------------------------------------------------------
# H7d: configure.py _remove_agents
# ---------------------------------------------------------------------------


class TestH7dConfigureRemoveAgents:
    """Tests that ConfigureCommand._remove_agents normalizes the
    full_agent_id before constructing file names."""

    def test_remove_agents_normalizes_full_agent_id(self, tmp_path):
        """Mock an agent with full_agent_id='dart_engineer', verify it
        tries to remove 'dart-engineer.md'."""
        from claude_mpm.cli.commands.configure_models import AgentConfig

        agent = AgentConfig(
            name="dart_engineer",
            description="Dart Engineer agent",
        )
        agent.is_deployed = True
        agent.full_agent_id = "dart_engineer"

        # Create the normalized file
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        agent_file = agents_dir / "dart-engineer.md"
        agent_file.write_text("# Dart Engineer\n")

        # Patch to use our agents_dir
        from claude_mpm.cli.commands.configure import ConfigureCommand

        cmd = ConfigureCommand.__new__(ConfigureCommand)
        cmd.console = MagicMock()
        cmd._ctx = MagicMock()
        cmd._ctx.agents_dir = agents_dir

        # Patch Prompt.ask to select agent 1 then continue
        with patch("claude_mpm.cli.commands.configure.Prompt") as mock_prompt:
            # First call: select agent #1; second call: press Enter
            mock_prompt.ask.side_effect = ["1", ""]

            cmd._remove_agents([agent])

        # The normalized filename should have been found and removed
        assert not agent_file.exists(), (
            "dart-engineer.md should have been deleted when full_agent_id "
            "was 'dart_engineer'"
        )

    def test_remove_agents_strips_agent_suffix(self, tmp_path):
        """Mock an agent with full_agent_id='research-agent', verify it
        tries to remove 'research.md'."""
        from claude_mpm.cli.commands.configure_models import AgentConfig

        agent = AgentConfig(
            name="research-agent",
            description="Research agent",
        )
        agent.is_deployed = True
        agent.full_agent_id = "research-agent"

        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        agent_file = agents_dir / "research.md"
        agent_file.write_text("# Research\n")

        from claude_mpm.cli.commands.configure import ConfigureCommand

        cmd = ConfigureCommand.__new__(ConfigureCommand)
        cmd.console = MagicMock()
        cmd._ctx = MagicMock()
        cmd._ctx.agents_dir = agents_dir

        with patch("claude_mpm.cli.commands.configure.Prompt") as mock_prompt:
            mock_prompt.ask.side_effect = ["1", ""]

            cmd._remove_agents([agent])

        assert not agent_file.exists(), (
            "research.md should have been deleted when full_agent_id "
            "was 'research-agent'"
        )
