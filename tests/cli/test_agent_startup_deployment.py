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

    @pytest.fixture(autouse=True)
    def bypass_sync_ttl(self):
        """Ensure tests always exercise the sync path regardless of TTL state."""
        with patch("claude_mpm.cli.startup._is_sync_fresh", return_value=False):
            yield

    def test_sync_remote_agents_two_phase_deployment(self):
        """Verify agents are both synced to cache AND deployed to ~/.claude/agents/.

        This test verifies the fix for the critical bug where agents were synced
        to cache but never deployed to the target directory.
        NOTE: Implementation now uses perform_startup_reconciliation instead of
        AgentDeploymentService directly.
        """
        from claude_mpm.cli.startup import sync_remote_agents_on_startup
        from claude_mpm.services.agents.deployment.deployment_reconciler import (
            DeploymentResult,
        )

        with ExitStack() as stack:
            mock_sync_agents = stack.enter_context(
                patch("claude_mpm.services.agents.startup_sync.sync_agents_on_startup")
            )
            mock_reconcile = stack.enter_context(
                patch(
                    "claude_mpm.services.agents.deployment.startup_reconciliation.perform_startup_reconciliation",
                    return_value=(
                        DeploymentResult(
                            deployed=["agent1", "agent2", "agent3"],
                            removed=[],
                            unchanged=[],
                            errors=[],
                        ),
                        DeploymentResult(
                            deployed=[], removed=[], unchanged=[], errors=[]
                        ),
                    ),
                )
            )
            mock_progress_bar = stack.enter_context(
                patch("claude_mpm.utils.progress.ProgressBar")
            )
            # Mock ConfigLoader to return config with no active_profile
            mock_config_loader = stack.enter_context(
                patch("claude_mpm.core.shared.config_loader.ConfigLoader")
            )
            mock_main_config = MagicMock()
            mock_main_config.get.return_value = None
            mock_config_loader.return_value.load_main_config.return_value = (
                mock_main_config
            )
            tmp_dir = stack.enter_context(tempfile.TemporaryDirectory())
            # Setup mocks
            tmp_path = Path(tmp_dir)
            cache_dir = tmp_path / ".claude-mpm" / "cache" / "agents"
            cache_dir.mkdir(parents=True)

            # Create some agent MD files in cache to simulate synced agents
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

            # Mock progress bar
            mock_progress_instance = MagicMock()
            mock_progress_bar.return_value = mock_progress_instance

            # Mock Path.home() to use our temp directory
            with patch("pathlib.Path.home", return_value=tmp_path):
                # Run the function
                sync_remote_agents_on_startup()

                # CRITICAL VERIFICATION: Phase 1 (Sync) was called
                mock_sync_agents.assert_called_once()

                # CRITICAL VERIFICATION: Phase 2 (Deployment via reconciliation) was called
                mock_reconcile.assert_called_once()

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
            # Mock the new reconciliation function to raise an exception
            mock_reconcile = stack.enter_context(
                patch(
                    "claude_mpm.services.agents.deployment.startup_reconciliation.perform_startup_reconciliation",
                    side_effect=Exception("Reconciliation failed"),
                )
            )
            # Mock ConfigLoader to return config with no active_profile
            mock_config_loader = stack.enter_context(
                patch("claude_mpm.core.shared.config_loader.ConfigLoader")
            )
            mock_main_config = MagicMock()
            mock_main_config.get.return_value = None
            mock_config_loader.return_value.load_main_config.return_value = (
                mock_main_config
            )
            tmp_dir = stack.enter_context(tempfile.TemporaryDirectory())
            # Setup mocks
            tmp_path = Path(tmp_dir)
            cache_dir = tmp_path / ".claude-mpm" / "cache" / "agents"
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

            # Mock Path.home()
            with patch("pathlib.Path.home", return_value=tmp_path):
                # Run the function - should NOT raise exception
                sync_remote_agents_on_startup()

                # Verify sync was attempted
                mock_sync_agents.assert_called_once()

                # Reconciliation was attempted but failed gracefully
                mock_reconcile.assert_called_once()

    def test_sync_remote_agents_skips_deployment_if_no_agents_in_cache(self):
        """Verify reconciliation is called even if cache is empty (reconciler handles empty case).

        NOTE: With the new reconciliation-based approach, perform_startup_reconciliation
        IS called when sync succeeds (sources_synced > 0). The reconciler internally
        handles the case where the cache is empty.
        """
        from claude_mpm.cli.startup import sync_remote_agents_on_startup
        from claude_mpm.services.agents.deployment.deployment_reconciler import (
            DeploymentResult,
        )

        with ExitStack() as stack:
            mock_sync_agents = stack.enter_context(
                patch("claude_mpm.services.agents.startup_sync.sync_agents_on_startup")
            )
            mock_reconcile = stack.enter_context(
                patch(
                    "claude_mpm.services.agents.deployment.startup_reconciliation.perform_startup_reconciliation",
                    return_value=(
                        DeploymentResult(
                            deployed=[], removed=[], unchanged=[], errors=[]
                        ),
                        DeploymentResult(
                            deployed=[], removed=[], unchanged=[], errors=[]
                        ),
                    ),
                )
            )
            # Mock ConfigLoader to return config with no active_profile
            mock_config_loader = stack.enter_context(
                patch("claude_mpm.core.shared.config_loader.ConfigLoader")
            )
            mock_main_config = MagicMock()
            mock_main_config.get.return_value = None
            mock_config_loader.return_value.load_main_config.return_value = (
                mock_main_config
            )
            tmp_dir = stack.enter_context(tempfile.TemporaryDirectory())
            # Setup mocks
            tmp_path = Path(tmp_dir)
            cache_dir = tmp_path / ".claude-mpm" / "cache" / "agents"
            cache_dir.mkdir(parents=True)

            # Cache directory exists but is EMPTY

            # Mock sync returning success with sources_synced=1
            mock_sync_agents.return_value = {
                "enabled": True,
                "sources_synced": 1,
                "total_downloaded": 0,  # No downloads but sources synced
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

                # Reconciliation IS called (sources_synced > 0) even with empty cache
                mock_reconcile.assert_called_once()

    def test_sync_remote_agents_displays_deployment_errors_to_user(self):
        """Verify deployment errors are displayed to the user when on a TTY.

        The new implementation shows errors via print() only when sys.stdout.isatty()
        returns True. Errors are stored in agent_result.errors (DeploymentResult).
        """
        from claude_mpm.cli.startup import sync_remote_agents_on_startup
        from claude_mpm.services.agents.deployment.deployment_reconciler import (
            DeploymentResult,
        )

        with ExitStack() as stack:
            mock_sync_agents = stack.enter_context(
                patch("claude_mpm.services.agents.startup_sync.sync_agents_on_startup")
            )
            # Mock reconciliation to return errors
            mock_reconcile = stack.enter_context(
                patch(
                    "claude_mpm.services.agents.deployment.startup_reconciliation.perform_startup_reconciliation",
                    return_value=(
                        DeploymentResult(
                            deployed=[],
                            removed=[],
                            unchanged=[],
                            errors=[
                                "agent1.md: Failed to parse template: JSONDecodeError",
                                "agent2.md: Failed to parse template: Invalid frontmatter",
                            ],
                        ),
                        DeploymentResult(
                            deployed=[], removed=[], unchanged=[], errors=[]
                        ),
                    ),
                )
            )
            # Mock ConfigLoader to return config with no active_profile
            mock_config_loader = stack.enter_context(
                patch("claude_mpm.core.shared.config_loader.ConfigLoader")
            )
            mock_main_config = MagicMock()
            mock_main_config.get.return_value = None
            mock_config_loader.return_value.load_main_config.return_value = (
                mock_main_config
            )
            # Mock isatty to return True so errors are printed
            stack.enter_context(patch("sys.stdout.isatty", return_value=True))
            mock_print = stack.enter_context(patch("builtins.print"))
            tmp_dir = stack.enter_context(tempfile.TemporaryDirectory())
            # Setup mocks
            tmp_path = Path(tmp_dir)
            cache_dir = tmp_path / ".claude-mpm" / "cache" / "agents"
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

            # Mock Path.home()
            with patch("pathlib.Path.home", return_value=tmp_path):
                # Run the function
                sync_remote_agents_on_startup()

                # CRITICAL VERIFICATION: Errors should be displayed to user via print()
                print_calls = [str(call) for call in mock_print.call_args_list]

                # Verify reconciliation was called (errors come from reconciler)
                mock_reconcile.assert_called_once()

                # Verify error header is displayed (only when isatty=True)
                assert any("Agent Deployment Errors" in call for call in print_calls), (
                    f"Error header not displayed to user. Print calls: {print_calls}"
                )

                # Verify specific errors are shown
                assert any("agent1.md" in call for call in print_calls), (
                    "First error not displayed to user"
                )
                assert any("agent2.md" in call for call in print_calls), (
                    "Second error not displayed to user"
                )

                # Verify summary message is shown
                assert any("Failed to deploy" in call for call in print_calls), (
                    "Summary message not displayed to user"
                )

    def test_sync_remote_agents_no_error_display_when_successful(self):
        """Verify no error messages are shown when deployment succeeds."""
        from claude_mpm.cli.startup import sync_remote_agents_on_startup
        from claude_mpm.services.agents.deployment.deployment_reconciler import (
            DeploymentResult,
        )

        with ExitStack() as stack:
            mock_sync_agents = stack.enter_context(
                patch("claude_mpm.services.agents.startup_sync.sync_agents_on_startup")
            )
            # Mock the reconciliation function (Phase 2 code path)
            # CRITICAL: Must mock perform_startup_reconciliation, NOT
            # AgentDeploymentService. Phase 2 changed the code to use
            # reconciliation. Without this mock, the REAL reconciliation
            # runs against Path.cwd() and deletes deployed agents.
            mock_reconcile = stack.enter_context(
                patch(
                    "claude_mpm.services.agents.deployment.startup_reconciliation.perform_startup_reconciliation",
                    return_value=(
                        DeploymentResult(
                            deployed=["agent1"],
                            removed=[],
                            unchanged=[],
                            errors=[],  # No errors
                        ),
                        DeploymentResult(
                            deployed=[], removed=[], unchanged=[], errors=[]
                        ),
                    ),
                )
            )
            # Mock ConfigLoader to return config with no active_profile
            mock_config_loader = stack.enter_context(
                patch("claude_mpm.core.shared.config_loader.ConfigLoader")
            )
            mock_main_config = MagicMock()
            mock_main_config.get.return_value = None
            mock_config_loader.return_value.load_main_config.return_value = (
                mock_main_config
            )
            mock_print = stack.enter_context(patch("builtins.print"))
            tmp_dir = stack.enter_context(tempfile.TemporaryDirectory())
            # Setup mocks
            tmp_path = Path(tmp_dir)
            cache_dir = tmp_path / ".claude-mpm" / "cache" / "agents"
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

            # Mock Path.home()
            with patch("pathlib.Path.home", return_value=tmp_path):
                # Run the function
                sync_remote_agents_on_startup()

                # CRITICAL VERIFICATION: No error messages should be displayed
                print_calls = [str(call) for call in mock_print.call_args_list]

                # Verify reconciliation was called (no errors)
                mock_reconcile.assert_called_once()

                # Verify error messages are NOT shown
                assert not any(
                    "Agent Deployment Errors" in call for call in print_calls
                ), "Error header shown when no errors occurred"
                assert not any("Failed to deploy" in call for call in print_calls), (
                    "Failure message shown when deployment succeeded"
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
