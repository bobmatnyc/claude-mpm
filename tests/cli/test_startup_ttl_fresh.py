"""Gap-fill test: TTL-fresh sync skip in sync_remote_agents_on_startup().

Captures the current behavior where sync_remote_agents_on_startup() returns
early (skips all network activity) when:
1. force_sync is False
2. _is_sync_fresh("agents") returns True
3. _agent_sources_changed_since_last_sync() returns False

This is a characterization test for the TTL-based skip logic.
"""

from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.cli.startup import sync_remote_agents_on_startup

# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


class TestStartupTTLFresh:
    """Verify TTL-fresh condition skips sync entirely."""

    @patch("claude_mpm.cli.startup.check_legacy_cache")
    @patch(
        "claude_mpm.cli.startup._agent_sources_changed_since_last_sync",
        return_value=False,
    )
    @patch("claude_mpm.cli.startup._is_sync_fresh", return_value=True)
    def test_ttl_fresh_skips_sync(
        self,
        mock_is_fresh,
        mock_sources_changed,
        mock_legacy_cache,
    ):
        """When last sync is within TTL and sources unchanged, the function
        returns immediately without calling sync_agents_on_startup()."""

        with patch(
            "claude_mpm.services.agents.startup_sync.sync_agents_on_startup"
        ) as mock_sync:
            sync_remote_agents_on_startup(force_sync=False)

            # sync_agents_on_startup should NOT have been called because
            # the TTL check short-circuited the function
            mock_sync.assert_not_called()

        # Verify the TTL helpers were consulted
        mock_is_fresh.assert_called_once_with("agents")
        mock_sources_changed.assert_called_once()

        # Legacy cache check should still run (it's before the TTL check)
        mock_legacy_cache.assert_called_once()

    @patch("claude_mpm.cli.startup.check_legacy_cache")
    @patch(
        "claude_mpm.cli.startup._agent_sources_changed_since_last_sync",
        return_value=False,
    )
    @patch("claude_mpm.cli.startup._is_sync_fresh", return_value=True)
    def test_ttl_force_sync_bypasses_ttl(
        self,
        mock_is_fresh,
        mock_sources_changed,
        mock_legacy_cache,
    ):
        """When force_sync=True, the TTL check is bypassed and
        sync_agents_on_startup() IS called even though _is_sync_fresh
        returns True.

        This captures the force_sync override behavior at
        startup.py:1008-1012 where the TTL guard is short-circuited.
        """
        # Mock the lazy imports inside sync_remote_agents_on_startup
        mock_config_loader_cls = MagicMock()
        mock_config_instance = MagicMock()
        mock_config_instance.load_main_config.return_value = {}
        mock_config_loader_cls.return_value = mock_config_instance

        mock_pm_cls = MagicMock()

        with (
            patch(
                "claude_mpm.core.shared.config_loader.ConfigLoader",
                mock_config_loader_cls,
            ),
            patch(
                "claude_mpm.services.profile_manager.ProfileManager",
                mock_pm_cls,
            ),
            patch(
                "claude_mpm.services.agents.startup_sync.sync_agents_on_startup",
                return_value={"enabled": False, "sources_synced": 0},
            ) as mock_sync,
        ):
            sync_remote_agents_on_startup(force_sync=True)

            # sync_agents_on_startup SHOULD be called because force_sync
            # bypasses the TTL check
            mock_sync.assert_called_once()
