"""Unit tests for Integration Scenarios.

Tests multi-source integration and deployment integration scenarios.
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


class TestMultiSourceIntegration(TestAgentDeploymentService):
    """Test multi-source deployment integration."""

    def test_get_multi_source_templates_with_comparison(
        self, service, tmp_path, mock_dependencies
    ):
        """Test multi-source templates with deployed version comparison."""
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)

        # Create existing deployed agent
        deployed_agent = agents_dir / "existing.md"
        deployed_agent.write_text("---\nname: existing\nversion: 1.0.0\n---\nContent")

        # Setup mock returns
        mock_dependencies[
            "multi_source_service"
        ].get_agents_for_deployment.return_value = (
            {"existing": tmp_path / "templates" / "existing.json"},
            {"existing": "system"},
            {"removed": []},
        )

        mock_dependencies[
            "multi_source_service"
        ].compare_deployed_versions.return_value = {
            "version_upgrades": ["existing"],
            "source_changes": [],
            "needs_update": ["existing"],
            "new_agents": [],
        }

        templates, sources, cleanup = service._get_multi_source_templates(
            excluded_agents=[],
            config=Mock(),
            agents_dir=agents_dir,
            force_rebuild=False,
        )

        assert len(templates) == 1
        mock_dependencies[
            "multi_source_service"
        ].compare_deployed_versions.assert_called_once()

    def test_get_multi_source_templates_force_rebuild(
        self, service, tmp_path, mock_dependencies
    ):
        """Test multi-source templates with force rebuild."""
        agents_dir = tmp_path / ".claude" / "agents"

        mock_dependencies[
            "multi_source_service"
        ].get_agents_for_deployment.return_value = (
            {
                "agent1": tmp_path / "templates" / "agent1.json",
                "agent2": tmp_path / "templates" / "agent2.json",
            },
            {"agent1": "system", "agent2": "project"},
            {"removed": []},
        )

        templates, sources, cleanup = service._get_multi_source_templates(
            excluded_agents=[], config=Mock(), agents_dir=agents_dir, force_rebuild=True
        )

        # With force_rebuild, all agents should be included
        assert len(templates) == 2


class TestDeploymentIntegration(TestAgentDeploymentService):
    """Test full deployment integration scenarios."""

    def test_full_deployment_cycle(self, service, tmp_path, mock_dependencies):
        """Test complete deployment cycle with all operations."""
        target_dir = tmp_path / ".claude" / "agents"

        # Setup comprehensive mocks
        mock_dependencies["configuration_manager"].load_base_agent.return_value = (
            {"base_version": "1.0.0", "settings": {}},
            (1, 0, 0),
        )

        template_file = tmp_path / "templates" / "complete_agent.json"
        template_file.parent.mkdir(parents=True, exist_ok=True)
        template_file.write_text(
            json.dumps(
                {
                    "name": "complete_agent",
                    "version": "2.0.0",
                    "description": "Complete test agent",
                }
            )
        )

        mock_dependencies["discovery_service"].get_filtered_templates.return_value = [
            template_file
        ]
        mock_dependencies["version_manager"].check_agent_needs_update.return_value = (
            True,
            "new agent",
        )
        mock_dependencies["template_builder"].build_agent_markdown.return_value = (
            "---\nname: complete_agent\nversion: 2.0.0\n---\nAgent content"
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

                result = service.deploy_agents(
                    target_dir=target_dir, force_rebuild=False
                )

        # Verify full deployment cycle
        assert result["target_dir"] == str(target_dir)
        assert len(result["deployed"]) > 0 or len(result["updated"]) > 0
        assert "metrics" in result
        assert result["metrics"]["start_time"] is not None

    def test_deployment_with_exclusions(self, service, tmp_path, mock_dependencies):
        """Test deployment with agent exclusions."""
        mock_config = Mock()
        mock_config.agent.excluded_agents = ["excluded_agent"]

        mock_dependencies["configuration_manager"].load_base_agent.return_value = (
            {},
            (1, 0, 0),
        )
        mock_dependencies["discovery_service"].get_filtered_templates.return_value = []

        with patch.object(service, "_load_deployment_config") as mock_load_config:
            mock_load_config.return_value = (mock_config, ["excluded_agent"])

            with patch.object(
                service, "_validate_and_repair_existing_agents"
            ) as mock_repair:
                mock_repair.return_value = {"repaired": []}

                with patch.object(service, "_convert_yaml_to_md") as mock_convert:
                    mock_convert.return_value = {"converted": []}

                    service.deploy_agents(config=mock_config)

        # Verify excluded agents were passed to discovery service
        mock_dependencies["discovery_service"].get_filtered_templates.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
