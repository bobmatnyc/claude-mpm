"""Unit tests for skills startup synchronization.

Tests the startup integration of GitSkillSourceManager to ensure
skill templates are synchronized correctly on Claude MPM initialization.
"""

from unittest.mock import MagicMock, patch

import pytest


class TestSyncRemoteSkillsOnStartup:
    """Test suite for sync_remote_skills_on_startup function."""

    @patch("claude_mpm.services.skills.git_skill_source_manager.GitSkillSourceManager")
    @patch("claude_mpm.config.skill_sources.SkillSourceConfiguration")
    def test_successful_skills_sync(self, mock_config_class, mock_manager_class):
        """Test successful synchronization of skills."""
        from claude_mpm.cli.startup import sync_remote_skills_on_startup

        # Mock configuration
        mock_config = MagicMock()
        mock_config_class.return_value = mock_config

        # Mock enabled sources
        mock_source = MagicMock()
        mock_source.id = "system"
        mock_source.url = "https://github.com/bobmatnyc/claude-mpm-skills"
        mock_source.branch = "main"
        mock_config.get_enabled_sources.return_value = [mock_source]

        # Mock manager
        mock_manager = MagicMock()
        mock_manager._discover_repository_files_via_tree_api.return_value = [
            "file1.md",
            "file2.md",
        ]
        mock_manager.sync_all_sources.return_value = {
            "synced_count": 2,
            "failed_count": 0,
            "total_files_updated": 3,
            "total_files_cached": 1,
            "sources": {
                "system": {
                    "synced": True,
                    "skills_discovered": 15,
                    "files_updated": 3,
                },
                "custom": {
                    "synced": True,
                    "skills_discovered": 5,
                    "files_updated": 1,
                },
            },
        }
        mock_manager.get_all_skills.return_value = []
        mock_manager_class.return_value = mock_manager

        # Call function - should not raise exception
        sync_remote_skills_on_startup()

        # Verify configuration was loaded
        mock_config_class.assert_called_once()

        # Verify manager was created
        mock_manager_class.assert_called_once_with(mock_config)

        # Verify sync was called with force=False and progress_callback
        call_args = mock_manager.sync_all_sources.call_args
        assert call_args[1]["force"] is False
        assert "progress_callback" in call_args[1]

    @patch("claude_mpm.services.skills.git_skill_source_manager.GitSkillSourceManager")
    @patch("claude_mpm.config.skill_sources.SkillSourceConfiguration")
    def test_no_sources_synced(self, mock_config_class, mock_manager_class):
        """Test when no skill sources are synced."""
        from claude_mpm.cli.startup import sync_remote_skills_on_startup

        mock_config = MagicMock()
        mock_config_class.return_value = mock_config

        mock_manager = MagicMock()
        mock_manager.sync_all_sources.return_value = {
            "synced_count": 0,
            "failed_count": 0,
            "sources": {},
        }
        mock_manager_class.return_value = mock_manager

        # Should not raise exception
        sync_remote_skills_on_startup()

        # Verify sync was called
        mock_manager.sync_all_sources.assert_called_once()

    @patch("claude_mpm.services.skills.git_skill_source_manager.GitSkillSourceManager")
    @patch("claude_mpm.config.skill_sources.SkillSourceConfiguration")
    def test_partial_sync_failure(self, mock_config_class, mock_manager_class):
        """Test handling of partial sync failures."""
        from claude_mpm.cli.startup import sync_remote_skills_on_startup

        mock_config = MagicMock()
        mock_config_class.return_value = mock_config

        mock_manager = MagicMock()
        mock_manager.sync_all_sources.return_value = {
            "synced_count": 1,
            "failed_count": 1,
            "sources": {
                "system": {
                    "synced": True,
                    "skills_discovered": 15,
                },
                "broken": {
                    "synced": False,
                    "error": "Network timeout",
                },
            },
        }
        mock_manager_class.return_value = mock_manager

        # Should not raise exception even with failures
        sync_remote_skills_on_startup()

        # Verify sync was attempted
        mock_manager.sync_all_sources.assert_called_once()

    @patch("claude_mpm.config.skill_sources.SkillSourceConfiguration")
    def test_graceful_exception_handling(self, mock_config_class):
        """Test that exceptions don't crash startup."""
        from claude_mpm.cli.startup import sync_remote_skills_on_startup

        # Make configuration raise exception
        mock_config_class.side_effect = Exception("Config load failed")

        # Should not raise exception
        sync_remote_skills_on_startup()

        # Verify configuration was attempted
        mock_config_class.assert_called_once()

    @patch("claude_mpm.services.skills.git_skill_source_manager.GitSkillSourceManager")
    @patch("claude_mpm.config.skill_sources.SkillSourceConfiguration")
    def test_manager_exception_handling(self, mock_config_class, mock_manager_class):
        """Test handling of exceptions during sync."""
        from claude_mpm.cli.startup import sync_remote_skills_on_startup

        mock_config = MagicMock()
        mock_config_class.return_value = mock_config

        mock_manager = MagicMock()
        mock_manager.sync_all_sources.side_effect = Exception("Sync failed")
        mock_manager_class.return_value = mock_manager

        # Should not raise exception
        sync_remote_skills_on_startup()

        # Verify sync was attempted
        mock_manager.sync_all_sources.assert_called_once()


class TestTwoPhaseProgressBars:
    """Test suite for two-phase progress bars during skill sync."""

    @patch("claude_mpm.utils.progress.ProgressBar")
    @patch("claude_mpm.services.skills.git_skill_source_manager.GitSkillSourceManager")
    @patch("claude_mpm.config.skill_sources.SkillSourceConfiguration")
    def test_two_progress_bars_created(
        self, mock_config_class, mock_manager_class, mock_progress_class
    ):
        """Test that two separate progress bars are created for sync and deploy."""
        from claude_mpm.cli.startup import sync_remote_skills_on_startup

        # Mock configuration
        mock_config = MagicMock()
        mock_source = MagicMock()
        mock_source.id = "system"
        mock_source.url = "https://github.com/bobmatnyc/claude-mpm-skills"
        mock_source.branch = "main"
        mock_config.get_enabled_sources.return_value = [mock_source]
        mock_config_class.return_value = mock_config

        # Mock manager
        mock_manager = MagicMock()
        mock_manager._discover_repository_files_via_tree_api.return_value = [
            "file1.md",
            "file2.md",
        ]
        mock_manager.sync_all_sources.return_value = {
            "synced_count": 1,
            "failed_count": 0,
            "total_files_updated": 1,
            "total_files_cached": 1,
        }
        mock_manager.get_all_skills.return_value = [
            {"name": "skill1", "deployment_name": "skill1"},
            {"name": "skill2", "deployment_name": "skill2"},
        ]
        mock_manager.deploy_skills.return_value = {
            "deployed_count": 2,
            "skipped_count": 0,
            "errors": [],
        }
        mock_manager_class.return_value = mock_manager

        # Mock progress bars
        sync_progress = MagicMock()
        deploy_progress = MagicMock()
        mock_progress_class.side_effect = [sync_progress, deploy_progress]

        # Call function
        sync_remote_skills_on_startup()

        # Verify two progress bars were created
        assert (
            mock_progress_class.call_count == 2
        ), "Should create 2 progress bars (sync + deploy)"

        # Verify sync progress bar configuration
        sync_call = mock_progress_class.call_args_list[0]
        assert sync_call[1]["prefix"] == "Syncing skills"
        assert sync_call[1]["total"] > 0

        # Verify deploy progress bar configuration
        deploy_call = mock_progress_class.call_args_list[1]
        assert deploy_call[1]["prefix"] == "Deploying skills"
        assert deploy_call[1]["total"] == 2

        # Verify both progress bars finished
        sync_progress.finish.assert_called_once()
        deploy_progress.finish.assert_called_once()

    @patch("claude_mpm.utils.progress.ProgressBar")
    @patch("claude_mpm.services.skills.git_skill_source_manager.GitSkillSourceManager")
    @patch("claude_mpm.config.skill_sources.SkillSourceConfiguration")
    def test_progress_callback_invoked_during_sync(
        self, mock_config_class, mock_manager_class, mock_progress_class
    ):
        """Test that progress callback is passed to sync_all_sources."""
        from claude_mpm.cli.startup import sync_remote_skills_on_startup

        # Mock configuration
        mock_config = MagicMock()
        mock_source = MagicMock()
        mock_source.id = "system"
        mock_source.url = "https://github.com/bobmatnyc/claude-mpm-skills"
        mock_source.branch = "main"
        mock_config.get_enabled_sources.return_value = [mock_source]
        mock_config_class.return_value = mock_config

        # Mock manager
        mock_manager = MagicMock()
        mock_manager._discover_repository_files_via_tree_api.return_value = ["file1.md"]
        mock_manager.sync_all_sources.return_value = {
            "synced_count": 1,
            "failed_count": 0,
            "total_files_updated": 1,
            "total_files_cached": 0,
        }
        mock_manager.get_all_skills.return_value = []
        mock_manager_class.return_value = mock_manager

        # Mock progress bar
        sync_progress = MagicMock()
        mock_progress_class.return_value = sync_progress

        # Call function
        sync_remote_skills_on_startup()

        # Verify sync_all_sources was called with progress callback
        call_args = mock_manager.sync_all_sources.call_args
        assert "progress_callback" in call_args[1]
        assert callable(call_args[1]["progress_callback"])

    @patch("claude_mpm.utils.progress.ProgressBar")
    @patch("claude_mpm.services.skills.git_skill_source_manager.GitSkillSourceManager")
    @patch("claude_mpm.config.skill_sources.SkillSourceConfiguration")
    def test_progress_callback_invoked_during_deploy(
        self, mock_config_class, mock_manager_class, mock_progress_class
    ):
        """Test that progress callback is passed to deploy_skills."""
        from claude_mpm.cli.startup import sync_remote_skills_on_startup

        # Mock configuration
        mock_config = MagicMock()
        mock_source = MagicMock()
        mock_source.id = "system"
        mock_source.url = "https://github.com/bobmatnyc/claude-mpm-skills"
        mock_source.branch = "main"
        mock_config.get_enabled_sources.return_value = [mock_source]
        mock_config_class.return_value = mock_config

        # Mock manager
        mock_manager = MagicMock()
        mock_manager._discover_repository_files_via_tree_api.return_value = ["file1.md"]
        mock_manager.sync_all_sources.return_value = {
            "synced_count": 1,
            "failed_count": 0,
            "total_files_updated": 1,
            "total_files_cached": 0,
        }
        mock_manager.get_all_skills.return_value = [
            {"name": "skill1", "deployment_name": "skill1"}
        ]
        mock_manager.deploy_skills.return_value = {
            "deployed_count": 1,
            "skipped_count": 0,
            "errors": [],
        }
        mock_manager_class.return_value = mock_manager

        # Mock progress bars
        sync_progress = MagicMock()
        deploy_progress = MagicMock()
        mock_progress_class.side_effect = [sync_progress, deploy_progress]

        # Call function
        sync_remote_skills_on_startup()

        # Verify deploy_skills was called with progress callback
        call_args = mock_manager.deploy_skills.call_args
        assert "progress_callback" in call_args[1]
        assert callable(call_args[1]["progress_callback"])

    @patch("claude_mpm.utils.progress.ProgressBar")
    @patch("claude_mpm.services.skills.git_skill_source_manager.GitSkillSourceManager")
    @patch("claude_mpm.config.skill_sources.SkillSourceConfiguration")
    def test_no_deploy_when_no_sync_results(
        self, mock_config_class, mock_manager_class, mock_progress_class
    ):
        """Test that deployment is skipped when no sources were synced."""
        from claude_mpm.cli.startup import sync_remote_skills_on_startup

        # Mock configuration
        mock_config = MagicMock()
        mock_source = MagicMock()
        mock_source.id = "system"
        mock_source.url = "https://github.com/bobmatnyc/claude-mpm-skills"
        mock_source.branch = "main"
        mock_config.get_enabled_sources.return_value = [mock_source]
        mock_config_class.return_value = mock_config

        # Mock manager with no sync results
        mock_manager = MagicMock()
        mock_manager._discover_repository_files_via_tree_api.return_value = []
        mock_manager.sync_all_sources.return_value = {
            "synced_count": 0,  # No sources synced
            "failed_count": 0,
            "total_files_updated": 0,
            "total_files_cached": 0,
        }
        mock_manager_class.return_value = mock_manager

        # Mock progress bar
        sync_progress = MagicMock()
        mock_progress_class.return_value = sync_progress

        # Call function
        sync_remote_skills_on_startup()

        # Verify deploy_skills was NOT called
        mock_manager.deploy_skills.assert_not_called()

        # Verify only one progress bar created (sync only)
        assert mock_progress_class.call_count == 1
