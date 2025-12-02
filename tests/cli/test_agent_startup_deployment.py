"""Tests for agent deployment during startup.

This test verifies that the critical bug fix for agent deployment is working:
- Phase 1: Agents are synced to cache (~/.claude-mpm/cache/remote-agents/)
- Phase 2: Agents are deployed from cache to ~/.claude/agents/

The bug was that Phase 2 was completely missing, resulting in agents being
synced but never deployed.
"""

import tempfile
from contextlib import ExitStack
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

        with ExitStack() as stack:
            mock_sync_agents = stack.enter_context(
                patch("claude_mpm.services.agents.startup_sync.sync_agents_on_startup")
            )
            mock_deployment_service_class = stack.enter_context(
                patch(
                    "claude_mpm.services.agents.deployment.agent_deployment.AgentDeploymentService"
                )
            )
            mock_progress_bar = stack.enter_context(
                patch("claude_mpm.utils.progress.ProgressBar")
            )
            tmp_dir = stack.enter_context(tempfile.TemporaryDirectory())
            # Setup mocks
            tmp_path = Path(tmp_dir)
            cache_dir = tmp_path / ".claude-mpm" / "cache" / "remote-agents"
            cache_dir.mkdir(parents=True)

            # Create some agent MD files in cache to simulate synced agents
            # Note: Code counts .md files, not .json files
            (cache_dir / "agent1.md").write_text("# Agent 1")
            (cache_dir / "agent2.md").write_text("# Agent 2")
            (cache_dir / "agent3.md").write_text("# Agent 3")

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

        with ExitStack() as stack:
            mock_sync_agents = stack.enter_context(
                patch("claude_mpm.services.agents.startup_sync.sync_agents_on_startup")
            )
            mock_deployment_service_class = stack.enter_context(
                patch(
                    "claude_mpm.services.agents.deployment.agent_deployment.AgentDeploymentService"
                )
            )
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

        with ExitStack() as stack:
            mock_sync_agents = stack.enter_context(
                patch("claude_mpm.services.agents.startup_sync.sync_agents_on_startup")
            )
            mock_deployment_service_class = stack.enter_context(
                patch(
                    "claude_mpm.services.agents.deployment.agent_deployment.AgentDeploymentService"
                )
            )
            mock_progress_bar = stack.enter_context(
                patch("claude_mpm.utils.progress.ProgressBar")
            )
            tmp_dir = stack.enter_context(tempfile.TemporaryDirectory())
            # Setup mocks
            tmp_path = Path(tmp_dir)
            cache_dir = tmp_path / ".claude-mpm" / "cache" / "remote-agents"
            cache_dir.mkdir(parents=True)

            # Create agent in cache
            (cache_dir / "agent1.md").write_text("# Agent 1")

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

        with ExitStack() as stack:
            mock_sync_agents = stack.enter_context(
                patch("claude_mpm.services.agents.startup_sync.sync_agents_on_startup")
            )
            mock_deployment_service_class = stack.enter_context(
                patch(
                    "claude_mpm.services.agents.deployment.agent_deployment.AgentDeploymentService"
                )
            )
            tmp_dir = stack.enter_context(tempfile.TemporaryDirectory())
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

    def test_sync_remote_agents_displays_deployment_errors_to_user(self):
        """Verify deployment errors are displayed to the user, not just logged.

        This test verifies the fix for the issue where deployment errors were
        logged but never shown to the user, making it appear that everything
        succeeded when in fact all agents failed to deploy.
        """
        from claude_mpm.cli.startup import sync_remote_agents_on_startup

        with ExitStack() as stack:
            mock_sync_agents = stack.enter_context(
                patch("claude_mpm.services.agents.startup_sync.sync_agents_on_startup")
            )
            mock_deployment_service_class = stack.enter_context(
                patch(
                    "claude_mpm.services.agents.deployment.agent_deployment.AgentDeploymentService"
                )
            )
            mock_progress_bar = stack.enter_context(
                patch("claude_mpm.utils.progress.ProgressBar")
            )
            mock_print = stack.enter_context(patch("builtins.print"))
            tmp_dir = stack.enter_context(tempfile.TemporaryDirectory())
            # Setup mocks
            tmp_path = Path(tmp_dir)
            cache_dir = tmp_path / ".claude-mpm" / "cache" / "remote-agents"
            cache_dir.mkdir(parents=True)

            # Create agent files in cache
            (cache_dir / "agent1.md").write_text("# Agent 1")
            (cache_dir / "agent2.md").write_text("# Agent 2")

            # Mock sync returning success
            mock_sync_agents.return_value = {
                "enabled": True,
                "sources_synced": 1,
                "total_downloaded": 2,
                "cache_hits": 0,
                "errors": [],
                "duration_ms": 500,
            }

            # Mock deployment service to return errors
            mock_deployment_service = MagicMock()
            mock_deployment_service_class.return_value = mock_deployment_service

            # Simulate deployment with errors
            mock_deployment_service.deploy_agents.return_value = {
                "deployed": [],
                "updated": [],
                "skipped": [],
                "errors": [
                    "agent1.md: Failed to parse template: JSONDecodeError",
                    "agent2.md: Failed to parse template: Invalid frontmatter",
                ],
                "total": 2,
            }

            # Mock progress bar
            mock_progress_instance = MagicMock()
            mock_progress_bar.return_value = mock_progress_instance

            # Mock Path.home()
            with patch("pathlib.Path.home", return_value=tmp_path):
                # Run the function
                sync_remote_agents_on_startup()

                # CRITICAL VERIFICATION: Errors should be displayed to user via print()
                # Check that print was called with error messages
                print_calls = [str(call) for call in mock_print.call_args_list]
                print_output = "\n".join(print_calls)

                # Verify error header is displayed
                assert any(
                    "Agent Deployment Errors" in call for call in print_calls
                ), "Error header not displayed to user"

                # Verify specific errors are shown
                assert any(
                    "agent1.md" in call for call in print_calls
                ), "First error not displayed to user"
                assert any(
                    "agent2.md" in call for call in print_calls
                ), "Second error not displayed to user"

                # Verify summary message is shown
                assert any(
                    "Failed to deploy" in call for call in print_calls
                ), "Summary message not displayed to user"

    def test_sync_remote_agents_no_error_display_when_successful(self):
        """Verify no error messages are shown when deployment succeeds."""
        from claude_mpm.cli.startup import sync_remote_agents_on_startup

        with ExitStack() as stack:
            mock_sync_agents = stack.enter_context(
                patch("claude_mpm.services.agents.startup_sync.sync_agents_on_startup")
            )
            mock_deployment_service_class = stack.enter_context(
                patch(
                    "claude_mpm.services.agents.deployment.agent_deployment.AgentDeploymentService"
                )
            )
            mock_progress_bar = stack.enter_context(
                patch("claude_mpm.utils.progress.ProgressBar")
            )
            mock_print = stack.enter_context(patch("builtins.print"))
            tmp_dir = stack.enter_context(tempfile.TemporaryDirectory())
            # Setup mocks
            tmp_path = Path(tmp_dir)
            cache_dir = tmp_path / ".claude-mpm" / "cache" / "remote-agents"
            cache_dir.mkdir(parents=True)

            # Create agent file in cache
            (cache_dir / "agent1.md").write_text("# Agent 1")

            # Mock sync returning success
            mock_sync_agents.return_value = {
                "enabled": True,
                "sources_synced": 1,
                "total_downloaded": 1,
                "cache_hits": 0,
                "errors": [],
                "duration_ms": 500,
            }

            # Mock deployment service to return success (no errors)
            mock_deployment_service = MagicMock()
            mock_deployment_service_class.return_value = mock_deployment_service

            mock_deployment_service.deploy_agents.return_value = {
                "deployed": ["agent1"],
                "updated": [],
                "skipped": [],
                "errors": [],  # No errors
                "total": 1,
            }

            # Mock progress bar
            mock_progress_instance = MagicMock()
            mock_progress_bar.return_value = mock_progress_instance

            # Mock Path.home()
            with patch("pathlib.Path.home", return_value=tmp_path):
                # Run the function
                sync_remote_agents_on_startup()

                # CRITICAL VERIFICATION: No error messages should be displayed
                print_calls = [str(call) for call in mock_print.call_args_list]

                # Verify error messages are NOT shown
                assert not any(
                    "Agent Deployment Errors" in call for call in print_calls
                ), "Error header shown when no errors occurred"
                assert not any(
                    "Failed to deploy" in call for call in print_calls
                ), "Failure message shown when deployment succeeded"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
