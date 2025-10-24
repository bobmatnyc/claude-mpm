"""Unit tests for Version Management and Configuration.

Tests version management and configuration handling.
"""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from claude_mpm.core.config import Config
from claude_mpm.core.exceptions import AgentDeploymentError
from claude_mpm.services.agents.deployment.agent_deployment import (
    AgentDeploymentService,
)


class TestAgentDeploymentService:
    """Test suite for AgentDeploymentService."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration object."""
        config = Mock(spec=Config)
        config.get = Mock(return_value=None)
        config.agent = Mock()
        config.agent.excluded_agents = []
        config.agent.exclude_agents = []
        config.agent.case_sensitive = False
        config.agent.exclude_dependencies = False
        return config

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock instances of all helper services."""
        return {
            "template_builder": Mock(),
            "version_manager": Mock(),
            "metrics_collector": Mock(),
            "environment_manager": Mock(),
            "validator": Mock(),
            "filesystem_manager": Mock(),
            "discovery_service": Mock(),
            "multi_source_service": Mock(),
            "configuration_manager": Mock(),
            "format_converter": Mock(),
        }

    @pytest.fixture
    def service(self, tmp_path, mock_config, mock_dependencies):
        """Create an AgentDeploymentService instance with mocked dependencies."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir(parents=True, exist_ok=True)

        base_agent_path = tmp_path / "base_agent.json"
        base_agent_data = {
            "name": "base_agent",
            "version": "1.0.0",
            "base_version": "1.0.0",
        }
        base_agent_path.write_text(json.dumps(base_agent_data))

        working_dir = tmp_path / "working"
        working_dir.mkdir(parents=True, exist_ok=True)

        # Patch the service's dependencies
        with patch.multiple(
            "claude_mpm.services.agents.deployment.agent_deployment",
            AgentTemplateBuilder=Mock(
                return_value=mock_dependencies["template_builder"]
            ),
            AgentVersionManager=Mock(return_value=mock_dependencies["version_manager"]),
            AgentMetricsCollector=Mock(
                return_value=mock_dependencies["metrics_collector"]
            ),
            AgentEnvironmentManager=Mock(
                return_value=mock_dependencies["environment_manager"]
            ),
            AgentValidator=Mock(return_value=mock_dependencies["validator"]),
            AgentFileSystemManager=Mock(
                return_value=mock_dependencies["filesystem_manager"]
            ),
            AgentDiscoveryService=Mock(
                return_value=mock_dependencies["discovery_service"]
            ),
            MultiSourceAgentDeploymentService=Mock(
                return_value=mock_dependencies["multi_source_service"]
            ),
            AgentConfigurationManager=Mock(
                return_value=mock_dependencies["configuration_manager"]
            ),
            AgentFormatConverter=Mock(
                return_value=mock_dependencies["format_converter"]
            ),
        ):
            service = AgentDeploymentService(
                templates_dir=templates_dir,
                base_agent_path=base_agent_path,
                working_directory=working_dir,
                config=mock_config,
            )

            # Inject mock dependencies - these override the ones created during __init__
            for name, mock_obj in mock_dependencies.items():
                setattr(service, name, mock_obj)

            # Ensure templates_dir and working_directory are set
            service.templates_dir = templates_dir
            service.working_directory = working_dir

            return service

    @pytest.fixture
    def sample_agent_template(self, tmp_path):
        """Create a sample agent template file."""
        template_file = tmp_path / "templates" / "test_agent.json"
        template_file.parent.mkdir(parents=True, exist_ok=True)
        template_data = {
            "name": "test_agent",
            "version": "2.0.0",
            "description": "Test agent",
            "tools": ["tool1", "tool2"],
        }
        template_file.write_text(json.dumps(template_data))
        return template_file


class TestVersionManagement(TestAgentDeploymentService):
    """Test version management operations."""

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


class TestConfiguration(TestAgentDeploymentService):
    """Test configuration handling."""

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


