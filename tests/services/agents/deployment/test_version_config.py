"""Test version management and configuration operations.

This module tests version checking, update status determination, configuration
loading, and Claude environment setup.
"""

from unittest.mock import Mock, patch

from conftest import TestAgentDeploymentService


class TestVersionAndConfiguration(TestAgentDeploymentService):
    """Test version management and configuration operations."""

    def test_check_update_status_force_rebuild(
        self, service, tmp_path, mock_dependencies
    ):
        """Test update status check with force rebuild."""
        target_file = tmp_path / "agent.md"
        template_file = tmp_path / "agent.json"

        needs_update, is_migration, reason = service._check_update_status(
            target_file=target_file,
            template_file=template_file,
            base_agent_version=(1, 0, 0),
            force_rebuild=True,
            deployment_mode="update",
        )

        assert needs_update is True
        assert is_migration is False

    def test_check_update_status_project_mode(
        self, service, tmp_path, mock_dependencies
    ):
        """Test update status in project deployment mode."""
        target_file = tmp_path / "agent.md"
        target_file.write_text("---\nname: agent\n---\nContent")
        template_file = tmp_path / "agent.json"

        needs_update, is_migration, reason = service._check_update_status(
            target_file=target_file,
            template_file=template_file,
            base_agent_version=(1, 0, 0),
            force_rebuild=False,
            deployment_mode="project",
        )

        assert needs_update is True

    def test_check_update_status_migration_needed(
        self, service, tmp_path, mock_dependencies
    ):
        """Test detecting migration needed."""
        target_file = tmp_path / "agent.md"
        target_file.write_text("---\nname: agent\nversion: 100\n---\nContent")
        template_file = tmp_path / "agent.json"

        mock_dependencies["version_manager"].check_agent_needs_update.return_value = (
            True,
            "migration needed from serial to semantic",
        )

        needs_update, is_migration, reason = service._check_update_status(
            target_file=target_file,
            template_file=template_file,
            base_agent_version=(1, 0, 0),
            force_rebuild=False,
            deployment_mode="update",
        )

        assert needs_update is True
        assert is_migration is True
        assert "migration needed" in reason

    def test_check_update_status_version_current(
        self, service, tmp_path, mock_dependencies
    ):
        """Test when version is current."""
        target_file = tmp_path / "agent.md"
        target_file.write_text("---\nname: agent\nversion: 1.0.0\n---\nContent")
        template_file = tmp_path / "agent.json"

        mock_dependencies["version_manager"].check_agent_needs_update.return_value = (
            False,
            "version current",
        )

        needs_update, is_migration, reason = service._check_update_status(
            target_file=target_file,
            template_file=template_file,
            base_agent_version=(1, 0, 0),
            force_rebuild=False,
            deployment_mode="update",
        )

        assert needs_update is False
        assert is_migration is False

    def test_load_deployment_config(self, service):
        """Test loading deployment configuration."""
        mock_config = Mock()

        with patch(
            "claude_mpm.services.agents.deployment.agent_deployment.DeploymentConfigLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_loader.load_deployment_config.return_value = (
                mock_config,
                ["excluded_agent"],
            )
            mock_loader_class.return_value = mock_loader

            config, excluded = service._load_deployment_config(mock_config)

        assert config == mock_config
        assert excluded == ["excluded_agent"]

    def test_determine_agents_directory(self, service, tmp_path):
        """Test determining agents directory."""
        with patch(
            "claude_mpm.services.agents.deployment.agent_deployment.AgentsDirectoryResolver"
        ) as mock_resolver_class:
            mock_resolver = Mock()
            expected_dir = tmp_path / ".claude" / "agents"
            mock_resolver.determine_agents_directory.return_value = expected_dir
            mock_resolver_class.return_value = mock_resolver

            result = service._determine_agents_directory(None)

        assert result == expected_dir

    def test_determine_agents_directory_with_target(self, service, tmp_path):
        """Test determining agents directory with explicit target."""
        target_dir = tmp_path / "custom" / "agents"

        with patch(
            "claude_mpm.services.agents.deployment.agent_deployment.AgentsDirectoryResolver"
        ) as mock_resolver_class:
            mock_resolver = Mock()
            mock_resolver.determine_agents_directory.return_value = target_dir
            mock_resolver_class.return_value = mock_resolver

            service._determine_agents_directory(target_dir)

        mock_resolver.determine_agents_directory.assert_called_with(target_dir)

    def test_set_claude_environment(self, service, tmp_path, mock_dependencies):
        """Test setting Claude environment variables."""
        config_dir = tmp_path / ".claude"
        expected_env = {
            "CLAUDE_AGENTS_DIR": str(config_dir / "agents"),
            "CLAUDE_CONFIG_DIR": str(config_dir),
        }

        mock_dependencies["environment_manager"].set_claude_environment.return_value = (
            expected_env
        )

        result = service.set_claude_environment(config_dir)

        assert result == expected_env
        mock_dependencies[
            "environment_manager"
        ].set_claude_environment.assert_called_with(config_dir)

    def test_set_claude_environment_default(self, service, mock_dependencies):
        """Test setting Claude environment with default directory."""
        expected_env = {"CLAUDE_AGENTS_DIR": "/default/agents"}
        mock_dependencies["environment_manager"].set_claude_environment.return_value = (
            expected_env
        )

        result = service.set_claude_environment()

        assert result == expected_env
