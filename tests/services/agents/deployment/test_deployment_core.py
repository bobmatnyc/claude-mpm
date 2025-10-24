"""Unit tests for Core Deployment Operations.

Tests the AgentDeploymentService base functionality and deployment operations.
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


class TestDeploymentOperations(TestAgentDeploymentService):
    """Test deployment operations."""

    def test_deploy_agents_basic(self, service, tmp_path, mock_dependencies):
        """Test basic agent deployment with default settings."""
        target_dir = tmp_path / ".claude" / "agents"

        # Setup mocks
        mock_dependencies["configuration_manager"].load_base_agent.return_value = (
            {"base_version": "1.0.0"},
            (1, 0, 0),
        )
        mock_dependencies["discovery_service"].get_filtered_templates.return_value = [
            tmp_path / "templates" / "agent1.json",
            tmp_path / "templates" / "agent2.json",
        ]
        mock_dependencies["version_manager"].check_agent_needs_update.return_value = (
            True,
            "version outdated",
        )
        mock_dependencies["template_builder"].build_agent_markdown.return_value = (
            "---\nname: agent\n---\nAgent content"
        )
        mock_dependencies["format_converter"].convert_yaml_to_md.return_value = {
            "converted": []
        }

        with patch.object(service, "_load_deployment_config") as mock_load_config:
            mock_load_config.return_value = (Mock(), [])

            with patch.object(
                service, "_validate_and_repair_existing_agents"
            ) as mock_repair:
                mock_repair.return_value = {"repaired": []}

                result = service.deploy_agents(target_dir=target_dir)

        assert result["target_dir"] == str(target_dir)
        assert "deployed" in result
        assert "updated" in result
        assert "skipped" in result
        assert "errors" in result

    def test_deploy_agents_project_mode(self, service, tmp_path, mock_dependencies):
        """Test deployment in project mode (always deploy regardless of version)."""
        target_dir = tmp_path / ".claude" / "agents"

        # Setup mocks
        mock_dependencies["configuration_manager"].load_base_agent.return_value = (
            {"base_version": "1.0.0"},
            (1, 0, 0),
        )
        mock_dependencies[
            "multi_source_service"
        ].get_agents_for_deployment.return_value = (
            {"agent1": tmp_path / "templates" / "agent1.json"},
            {"agent1": "system"},
            {"removed": []},
        )
        mock_dependencies["template_builder"].build_agent_markdown.return_value = (
            "---\nname: agent1\n---\nAgent content"
        )

        with patch.object(service, "_load_deployment_config") as mock_load_config:
            mock_load_config.return_value = (Mock(), [])

            with patch.object(
                service, "_validate_and_repair_existing_agents"
            ) as mock_repair:
                mock_repair.return_value = {"repaired": []}

                with patch.object(service, "_convert_yaml_to_md") as mock_convert:
                    mock_convert.return_value = {"converted": []}

                    result = service.deploy_agents(
                        target_dir=target_dir, deployment_mode="project"
                    )

        # Check that multi-source deployment was used (project mode uses multi-source)
        assert mock_dependencies[
            "multi_source_service"
        ].get_agents_for_deployment.called
        # The result should contain agent_sources if multi-source was used
        if "multi_source" in result:
            assert result["multi_source"] is True
            assert "agent_sources" in result

    def test_deploy_agents_update_mode(self, service, tmp_path, mock_dependencies):
        """Test deployment in update mode (version-aware updates)."""
        target_dir = tmp_path / ".claude" / "agents"

        # Create existing agent file
        target_dir.mkdir(parents=True, exist_ok=True)
        existing_agent = target_dir / "existing_agent.md"
        existing_agent.write_text(
            "---\nname: existing_agent\nversion: 1.0.0\n---\nOld content"
        )

        # Setup mocks
        mock_dependencies["configuration_manager"].load_base_agent.return_value = (
            {"base_version": "1.0.0"},
            (1, 0, 0),
        )
        mock_dependencies[
            "multi_source_service"
        ].get_agents_for_deployment.return_value = (
            {"existing_agent": tmp_path / "templates" / "existing_agent.json"},
            {"existing_agent": "system"},
            {"removed": []},
        )
        mock_dependencies["version_manager"].check_agent_needs_update.return_value = (
            False,
            "version current",
        )

        with patch.object(service, "_load_deployment_config") as mock_load_config:
            mock_load_config.return_value = (Mock(), [])

            with patch.object(
                service, "_validate_and_repair_existing_agents"
            ) as mock_repair:
                mock_repair.return_value = {"repaired": []}

                with patch.object(service, "_convert_yaml_to_md") as mock_convert:
                    mock_convert.return_value = {"converted": []}

                    result = service.deploy_agents(
                        target_dir=target_dir, deployment_mode="update"
                    )

        # In update mode, up-to-date agents should be skipped
        assert len(result["skipped"]) > 0 or len(result["deployed"]) == 0

    def test_deploy_agents_with_async(self, service, tmp_path, mock_dependencies):
        """Test async deployment attempt."""
        target_dir = tmp_path / ".claude" / "agents"

        # Mock successful async deployment
        async_result = {
            "target_dir": str(target_dir),
            "deployed": ["agent1"],
            "errors": [],
            "metrics": {"deployment_method": "async", "duration_ms": 100},
        }

        with patch.object(service, "_try_async_deployment") as mock_async:
            mock_async.return_value = async_result

            result = service.deploy_agents(target_dir=target_dir, use_async=True)

        assert result == async_result
        mock_async.assert_called_once()

    def test_deploy_agent_single(
        self, service, tmp_path, mock_dependencies, sample_agent_template
    ):
        """Test deploying a single agent."""
        target_dir = tmp_path / ".claude" / "agents"

        # Setup mocks
        mock_dependencies["version_manager"].check_agent_needs_update.return_value = (
            True,
            "needs update",
        )
        mock_dependencies["version_manager"].parse_version.return_value = (2, 0, 0)
        mock_dependencies["template_builder"].build_agent_markdown.return_value = (
            "---\nname: test_agent\n---\nAgent content"
        )

        result = service.deploy_agent("test_agent", target_dir)

        assert result is True
        mock_dependencies["template_builder"].build_agent_markdown.assert_called()

    def test_deploy_agent_not_found(self, service, tmp_path):
        """Test deploying a non-existent agent."""
        target_dir = tmp_path / ".claude" / "agents"

        result = service.deploy_agent("non_existent_agent", target_dir)

        assert result is False

    def test_deploy_agent_force_rebuild(
        self, service, tmp_path, mock_dependencies, sample_agent_template
    ):
        """Test force rebuilding a single agent."""
        target_dir = tmp_path / ".claude" / "agents"
        target_dir.mkdir(parents=True, exist_ok=True)

        # Create existing agent
        existing_agent = target_dir / "test_agent.md"
        existing_agent.write_text(
            "---\nname: test_agent\nversion: 2.0.0\n---\nOld content"
        )

        # Setup mocks
        mock_dependencies["template_builder"].build_agent_markdown.return_value = (
            "---\nname: test_agent\nversion: 2.0.0\n---\nNew content"
        )

        result = service.deploy_agent("test_agent", target_dir, force_rebuild=True)

        assert result is True
        # Should build regardless of version check when force_rebuild is True


