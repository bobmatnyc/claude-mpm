"""Tests for agent deployment during startup.

This test verifies that the critical bug fix for agent deployment is working:
- Phase 1: Agents are synced to cache (~/.claude-mpm/cache/remote-agents/)
- Phase 2: Agents are deployed from cache to ~/.claude/agents/

The bug was that Phase 2 was completely missing, resulting in agents being
synced but never deployed.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestAgentStartupDeployment:
    """Test agent deployment during startup."""

    def test_sync_remote_agents_two_phase_deployment(self):
        """Verify agents are both synced to cache AND deployed to ~/.claude/agents/.

        This test verifies the fix for the critical bug where agents were synced
        to cache but never deployed to the target directory.
        """
        from claude_mpm.cli.startup import sync_remote_agents_on_startup

        with (
            patch(
                "claude_mpm.services.agents.startup_sync.sync_agents_on_startup"
            ) as mock_sync_agents,
            patch(
                "claude_mpm.services.agents.deployment.agent_deployment.AgentDeploymentService"
            ) as mock_deployment_service_class,
            patch("claude_mpm.utils.progress.ProgressBar") as mock_progress_bar,
            tempfile.TemporaryDirectory() as tmp_dir,
        ):
            # Setup mocks
            tmp_path = Path(tmp_dir)
            cache_dir = tmp_path / ".claude-mpm" / "cache" / "remote-agents"
            cache_dir.mkdir(parents=True)

            # Create some agent JSON files in cache to simulate synced agents
            (cache_dir / "agent1.json").write_text('{"name": "agent1"}')
            (cache_dir / "agent2.json").write_text('{"name": "agent2"}')
            (cache_dir / "agent3.json").write_text('{"name": "agent3"}')

            # Mock sync phase (Phase 1) - return successful sync
            mock_sync_agents.return_value = {
                "enabled": True,
                "sources_synced": 1,
                "total_downloaded": 3,
                "cache_hits": 0,
                "errors": [],
                "duration_ms": 1000,
            }

            # Mock deployment service (Phase 2)
            mock_deployment_service = MagicMock()
            mock_deployment_service_class.return_value = mock_deployment_service

            # Mock deploy_agents to return successful deployment
            mock_deployment_service.deploy_agents.return_value = {
                "deployed": ["agent1", "agent2"],
                "updated": ["agent3"],
                "skipped": [],
                "errors": [],
                "total": 3,
            }

            # Mock progress bar
            mock_progress_instance = MagicMock()
            mock_progress_bar.return_value = mock_progress_instance

            # Mock Path.home() to use our temp directory
            with patch("pathlib.Path.home", return_value=tmp_path):
                # Run the function
                sync_remote_agents_on_startup()

                # CRITICAL VERIFICATION: Phase 1 (Sync) was called
                mock_sync_agents.assert_called_once()

                # CRITICAL VERIFICATION: Phase 2 (Deployment) was called
                # This is the bug fix - deployment service should be instantiated
                mock_deployment_service_class.assert_called_once()

                # CRITICAL VERIFICATION: deploy_agents was called with correct params
                mock_deployment_service.deploy_agents.assert_called_once()

                # Verify deployment was called with correct target directory
                call_kwargs = mock_deployment_service.deploy_agents.call_args[1]
                assert "target_dir" in call_kwargs
                assert str(call_kwargs["target_dir"]).endswith(".claude/agents")

                # Verify deployment mode is correct (version-aware updates)
                assert call_kwargs["deployment_mode"] == "update"
                assert call_kwargs["force_rebuild"] is False

                # CRITICAL VERIFICATION: Progress bar was created for deployment
                assert mock_progress_bar.called
                progress_call_kwargs = mock_progress_bar.call_args[1]
                assert progress_call_kwargs["prefix"] == "Deploying agents"

    def test_sync_remote_agents_handles_no_sync_results(self):
        """Verify deployment is skipped if sync was not enabled or failed."""
        from claude_mpm.cli.startup import sync_remote_agents_on_startup

        with (
            patch(
                "claude_mpm.services.agents.startup_sync.sync_agents_on_startup"
            ) as mock_sync_agents,
            patch(
                "claude_mpm.services.agents.deployment.agent_deployment.AgentDeploymentService"
            ) as mock_deployment_service_class,
        ):
            # Mock sync returning disabled/no results
            mock_sync_agents.return_value = {
                "enabled": False,
                "sources_synced": 0,
                "total_downloaded": 0,
                "cache_hits": 0,
                "errors": [],
                "duration_ms": 0,
            }

            # Run the function
            sync_remote_agents_on_startup()

            # Verify sync was attempted
            mock_sync_agents.assert_called_once()

            # CRITICAL: Deployment should NOT be called if sync was disabled
            mock_deployment_service_class.assert_not_called()

    def test_sync_remote_agents_handles_deployment_failure_gracefully(self):
        """Verify deployment failures don't crash startup."""
        from claude_mpm.cli.startup import sync_remote_agents_on_startup

        with (
            patch(
                "claude_mpm.services.agents.startup_sync.sync_agents_on_startup"
            ) as mock_sync_agents,
            patch(
                "claude_mpm.services.agents.deployment.agent_deployment.AgentDeploymentService"
            ) as mock_deployment_service_class,
            patch("claude_mpm.utils.progress.ProgressBar") as mock_progress_bar,
            tempfile.TemporaryDirectory() as tmp_dir,
        ):
            # Setup mocks
            tmp_path = Path(tmp_dir)
            cache_dir = tmp_path / ".claude-mpm" / "cache" / "remote-agents"
            cache_dir.mkdir(parents=True)

            # Create agent in cache
            (cache_dir / "agent1.json").write_text('{"name": "agent1"}')

            # Mock sync returning success
            mock_sync_agents.return_value = {
                "enabled": True,
                "sources_synced": 1,
                "total_downloaded": 1,
                "cache_hits": 0,
                "errors": [],
                "duration_ms": 500,
            }

            # Mock deployment service to raise exception
            mock_deployment_service = MagicMock()
            mock_deployment_service_class.return_value = mock_deployment_service
            mock_deployment_service.deploy_agents.side_effect = Exception(
                "Deployment failed"
            )

            # Mock progress bar
            mock_progress_instance = MagicMock()
            mock_progress_bar.return_value = mock_progress_instance

            # Mock Path.home()
            with patch("pathlib.Path.home", return_value=tmp_path):
                # Run the function - should NOT raise exception
                sync_remote_agents_on_startup()

                # Verify sync was attempted
                mock_sync_agents.assert_called_once()

                # Deployment was attempted but failed gracefully
                mock_deployment_service_class.assert_called_once()
                mock_deployment_service.deploy_agents.assert_called_once()

    def test_sync_remote_agents_skips_deployment_if_no_agents_in_cache(self):
        """Verify deployment is skipped if cache is empty."""
        from claude_mpm.cli.startup import sync_remote_agents_on_startup

        with (
            patch(
                "claude_mpm.services.agents.startup_sync.sync_agents_on_startup"
            ) as mock_sync_agents,
            patch(
                "claude_mpm.services.agents.deployment.agent_deployment.AgentDeploymentService"
            ) as mock_deployment_service_class,
            tempfile.TemporaryDirectory() as tmp_dir,
        ):
            # Setup mocks
            tmp_path = Path(tmp_dir)
            cache_dir = tmp_path / ".claude-mpm" / "cache" / "remote-agents"
            cache_dir.mkdir(parents=True)

            # Cache directory exists but is EMPTY

            # Mock sync returning success
            mock_sync_agents.return_value = {
                "enabled": True,
                "sources_synced": 1,
                "total_downloaded": 0,  # No downloads
                "cache_hits": 0,
                "errors": [],
                "duration_ms": 200,
            }

            # Mock Path.home()
            with patch("pathlib.Path.home", return_value=tmp_path):
                # Run the function
                sync_remote_agents_on_startup()

                # Verify sync was attempted
                mock_sync_agents.assert_called_once()

                # Deployment service IS instantiated, but deploy_agents should NOT be called
                # if cache is empty (no agents to deploy)
                mock_deployment_service_class.assert_called_once()
                mock_deployment_service_class.return_value.deploy_agents.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
