"""Test that agent deployment respects configuration.yaml settings.

This test verifies the fix where agent deployment now uses the reconciliation
service that respects the agents.enabled list and include_universal setting.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestAgentStartupConfigRespect:
    """Test agent deployment respects configuration settings."""

    def test_deployment_respects_agents_enabled_list(self):
        """Verify only agents in agents.enabled list are deployed."""
        from claude_mpm.cli.startup import sync_remote_agents_on_startup

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            cache_dir = tmp_path / ".claude-mpm" / "cache" / "agents"
            cache_dir.mkdir(parents=True)

            # Create several agents in cache
            (cache_dir / "engineer.md").write_text("# Engineer")
            (cache_dir / "qa.md").write_text("# QA")
            (cache_dir / "security.md").write_text("# Security")
            (cache_dir / "ops.md").write_text("# Ops")

            with patch(
                "claude_mpm.services.agents.startup_sync.sync_agents_on_startup"
            ) as mock_sync, patch(
                "claude_mpm.services.agents.deployment.startup_reconciliation.perform_startup_reconciliation"
            ) as mock_reconcile, patch(
                "claude_mpm.core.unified_config.UnifiedConfig"
            ) as mock_config_class, patch(
                "pathlib.Path.home", return_value=tmp_path
            ), patch("pathlib.Path.cwd", return_value=tmp_path):
                # Mock sync success
                mock_sync.return_value = {
                    "enabled": True,
                    "sources_synced": 1,
                    "total_downloaded": 4,
                    "cache_hits": 0,
                    "errors": [],
                    "duration_ms": 1000,
                }

                # Mock config to have specific enabled agents
                mock_config = MagicMock()
                mock_config.agents.enabled = ["engineer", "qa"]
                mock_config.agents.required = ["research"]
                mock_config.agents.include_universal = False
                mock_config_class.return_value = mock_config

                # Mock reconciliation result
                mock_reconcile.return_value = (
                    MagicMock(
                        deployed=["engineer", "qa", "research"],
                        removed=["security", "ops"],
                        unchanged=[],
                        errors=[],
                    ),
                    MagicMock(deployed=[], removed=[], unchanged=[], errors=[]),
                )

                # Run the function
                sync_remote_agents_on_startup()

                # Verify reconciliation was called with correct config
                mock_reconcile.assert_called_once()
                call_kwargs = mock_reconcile.call_args[1]
                assert "config" in call_kwargs
                assert call_kwargs["config"].agents.enabled == ["engineer", "qa"]

    def test_deployment_respects_include_universal_setting(self):
        """Verify include_universal setting is respected."""
        from claude_mpm.cli.startup import sync_remote_agents_on_startup

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            cache_dir = tmp_path / ".claude-mpm" / "cache" / "agents"
            cache_dir.mkdir(parents=True)

            # Create agents including universal ones
            (cache_dir / "engineer.md").write_text(
                "---\ntoolchain: python\n---\n# Engineer"
            )
            (cache_dir / "universal-testing.md").write_text(
                "---\ntoolchain: universal\n---\n# Universal Testing"
            )

            with patch(
                "claude_mpm.services.agents.startup_sync.sync_agents_on_startup"
            ) as mock_sync, patch(
                "claude_mpm.services.agents.deployment.startup_reconciliation.perform_startup_reconciliation"
            ) as mock_reconcile, patch(
                "claude_mpm.core.unified_config.UnifiedConfig"
            ) as mock_config_class, patch(
                "pathlib.Path.home", return_value=tmp_path
            ), patch("pathlib.Path.cwd", return_value=tmp_path):
                # Mock sync success
                mock_sync.return_value = {
                    "enabled": True,
                    "sources_synced": 1,
                    "total_downloaded": 2,
                    "cache_hits": 0,
                    "errors": [],
                    "duration_ms": 500,
                }

                # Mock config with include_universal=True
                mock_config = MagicMock()
                mock_config.agents.enabled = ["engineer"]
                mock_config.agents.required = []
                mock_config.agents.include_universal = True
                mock_config_class.return_value = mock_config

                # Mock reconciliation result
                mock_reconcile.return_value = (
                    MagicMock(
                        deployed=["engineer", "universal-testing"],
                        removed=[],
                        unchanged=[],
                        errors=[],
                    ),
                    MagicMock(deployed=[], removed=[], unchanged=[], errors=[]),
                )

                # Run the function
                sync_remote_agents_on_startup()

                # Verify reconciliation was called with include_universal=True
                mock_reconcile.assert_called_once()
                call_kwargs = mock_reconcile.call_args[1]
                assert call_kwargs["config"].agents.include_universal is True

    def test_deployment_profile_override_config(self):
        """Verify profile settings override configuration.yaml."""
        from claude_mpm.cli.startup import sync_remote_agents_on_startup

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            with patch(
                "claude_mpm.services.agents.startup_sync.sync_agents_on_startup"
            ) as mock_sync, patch(
                "claude_mpm.services.agents.deployment.startup_reconciliation.perform_startup_reconciliation"
            ) as mock_reconcile, patch(
                "claude_mpm.core.unified_config.UnifiedConfig"
            ) as mock_config_class, patch(
                "claude_mpm.services.profile_manager.ProfileManager"
            ) as mock_profile_manager_class, patch(
                "pathlib.Path.cwd", return_value=tmp_path
            ), patch(
                "claude_mpm.core.shared.config_loader.ConfigLoader"
            ) as mock_config_loader_class:
                # Mock profile manager with active profile
                mock_profile_manager = MagicMock()
                mock_profile = MagicMock()
                mock_profile.get_enabled_agents.return_value = {"qa", "security"}
                mock_profile_manager.active_profile = mock_profile
                mock_profile_manager_class.return_value = mock_profile_manager

                # Mock config loader
                mock_config_loader = MagicMock()
                mock_config_loader.load_main_config.return_value = {
                    "active_profile": "test-profile"
                }
                mock_config_loader_class.return_value = mock_config_loader

                # Mock profile load success
                mock_profile_manager.load_profile.return_value = True
                mock_profile_manager.get_filtering_summary.return_value = {
                    "enabled_agents_count": 2
                }

                # Mock sync success
                mock_sync.return_value = {
                    "enabled": True,
                    "sources_synced": 1,
                    "total_downloaded": 2,
                    "cache_hits": 0,
                    "errors": [],
                    "duration_ms": 500,
                }

                # Mock config (will be overridden by profile)
                mock_config = MagicMock()
                mock_config.agents.enabled = ["engineer"]  # Original config
                mock_config.agents.required = []
                mock_config.agents.include_universal = False
                mock_config_class.return_value = mock_config

                # Mock reconciliation result
                mock_reconcile.return_value = (
                    MagicMock(
                        deployed=["qa", "security"], removed=[], unchanged=[], errors=[]
                    ),
                    MagicMock(deployed=[], removed=[], unchanged=[], errors=[]),
                )

                # Run the function
                sync_remote_agents_on_startup()

                # Verify config was overridden with profile's enabled agents
                # The list() conversion happens in the code
                assert mock_config.agents.enabled == ["qa", "security"] or set(
                    mock_config.agents.enabled
                ) == {"qa", "security"}

    def test_deployment_empty_config_with_auto_discover(self):
        """Verify backward compatibility: empty enabled list with auto_discover."""
        from claude_mpm.cli.startup import sync_remote_agents_on_startup

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            with patch(
                "claude_mpm.services.agents.startup_sync.sync_agents_on_startup"
            ) as mock_sync, patch(
                "claude_mpm.services.agents.deployment.startup_reconciliation.perform_startup_reconciliation"
            ) as mock_reconcile, patch(
                "claude_mpm.core.unified_config.UnifiedConfig"
            ) as mock_config_class, patch("pathlib.Path.cwd", return_value=tmp_path):
                # Mock sync success
                mock_sync.return_value = {
                    "enabled": True,
                    "sources_synced": 1,
                    "total_downloaded": 5,
                    "cache_hits": 0,
                    "errors": [],
                    "duration_ms": 800,
                }

                # Mock config with empty enabled list and auto_discover=True
                mock_config = MagicMock()
                mock_config.agents.enabled = []
                mock_config.agents.required = []
                mock_config.agents.include_universal = False
                mock_config.agents.auto_discover = True
                mock_config_class.return_value = mock_config

                # Mock reconciliation result (should not remove anything in auto-discover mode)
                mock_reconcile.return_value = (
                    MagicMock(deployed=[], removed=[], unchanged=[], errors=[]),
                    MagicMock(deployed=[], removed=[], unchanged=[], errors=[]),
                )

                # Run the function
                sync_remote_agents_on_startup()

                # Verify reconciliation was called
                mock_reconcile.assert_called_once()
                # In auto_discover mode, reconciler should see empty enabled list
                call_kwargs = mock_reconcile.call_args[1]
                assert call_kwargs["config"].agents.enabled == []
                assert call_kwargs["config"].agents.auto_discover is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
