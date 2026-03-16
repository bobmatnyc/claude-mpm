"""Gap-fill test: --no-sync flag in sync_deployment_on_startup().

Captures the current behavior where sync_deployment_on_startup(no_sync=True)
skips the remote agent sync entirely while still running hooks and showing
the agent summary.

This is a characterization test for the --no-sync CLI flag path.
"""

from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.cli.startup import sync_deployment_on_startup

# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


class TestStartupNoSync:
    """Verify --no-sync flag skips agent sync but not hooks/summary."""

    @patch("claude_mpm.cli.startup.show_agent_summary")
    @patch("claude_mpm.cli.startup.sync_remote_agents_on_startup")
    @patch("claude_mpm.cli.startup.sync_hooks_on_startup")
    def test_no_sync_skips_agent_sync(
        self,
        mock_hooks,
        mock_remote_sync,
        mock_summary,
    ):
        """When no_sync=True, sync_remote_agents_on_startup() is NOT called,
        but hooks are still synced and agent summary is still shown."""

        sync_deployment_on_startup(force_sync=False, no_sync=True)

        # sync_remote_agents_on_startup should NOT have been called
        mock_remote_sync.assert_not_called()

        # Hooks should still be synced (always runs regardless of no_sync)
        mock_hooks.assert_called_once()

        # Agent summary should still be shown (always runs regardless of no_sync)
        mock_summary.assert_called_once()

    @patch("claude_mpm.cli.startup.show_agent_summary")
    @patch("claude_mpm.cli.startup.sync_remote_agents_on_startup")
    @patch("claude_mpm.cli.startup.sync_hooks_on_startup")
    @patch(
        "claude_mpm.services.agents.deployment.startup_reconciliation.perform_startup_reconciliation"
    )
    def test_no_sync_skips_reconciliation_too(
        self,
        mock_reconciliation,
        mock_hooks,
        mock_remote_sync,
        mock_summary,
    ):
        """When no_sync=True, not only is sync_remote_agents_on_startup()
        skipped, but perform_startup_reconciliation() is also NOT called.

        This captures the full scope of the --no-sync flag: since
        sync_remote_agents_on_startup is skipped entirely, the
        reconciliation call inside it never executes either.
        """
        sync_deployment_on_startup(force_sync=False, no_sync=True)

        # sync_remote_agents_on_startup should NOT be called
        mock_remote_sync.assert_not_called()

        # perform_startup_reconciliation should also NOT be called
        # because it lives inside sync_remote_agents_on_startup which was skipped
        mock_reconciliation.assert_not_called()
