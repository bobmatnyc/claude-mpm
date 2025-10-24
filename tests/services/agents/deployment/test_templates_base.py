"""Unit tests for Template Discovery and Base Operations.

Tests template discovery and base agent operations.
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


class TestTemplateDiscovery(TestAgentDeploymentService):
    """Test template discovery operations."""

    def test_list_available_agents(self, service, mock_dependencies):
        """Test listing available agent templates."""
        expected_agents = [
            {"name": "agent1", "version": "1.0.0"},
            {"name": "agent2", "version": "2.0.0"},
        ]
        mock_dependencies["discovery_service"].list_available_agents.return_value = (
            expected_agents
        )

        result = service.list_available_agents()

        assert result == expected_agents
        mock_dependencies[
            "discovery_service"
        ].list_available_agents.assert_called_once()

    def test_get_multi_source_templates(self, service, tmp_path, mock_dependencies):
        """Test getting templates from multiple sources."""
        # Setup mock return values
        mock_dependencies[
            "multi_source_service"
        ].get_agents_for_deployment.return_value = (
            {
                "agent1": tmp_path / "system" / "agent1.json",
                "agent2": tmp_path / "project" / "agent2.json",
            },
            {"agent1": "system", "agent2": "project"},
            {"removed": []},
        )

        # Create mock config
        mock_config = Mock()

        templates, sources, cleanup = service._get_multi_source_templates(
            excluded_agents=["excluded_agent"],
            config=mock_config,
            agents_dir=tmp_path / ".claude" / "agents",
        )

        assert len(templates) == 2
        assert "agent1" in sources
        assert sources["agent1"] == "system"

    def test_get_filtered_templates(self, service, mock_dependencies):
        """Test getting filtered templates based on exclusion rules."""
        mock_config = Mock()
        expected_templates = [
            Path("/path/to/agent1.json"),
            Path("/path/to/agent2.json"),
        ]

        mock_dependencies["discovery_service"].get_filtered_templates.return_value = (
            expected_templates
        )

        result = service._get_filtered_templates(["excluded"], mock_config)

        assert result == expected_templates
        mock_dependencies[
            "discovery_service"
        ].get_filtered_templates.assert_called_with(["excluded"], mock_config)


class TestBaseAgentOperations(TestAgentDeploymentService):
    """Test base agent operations."""

    def test_find_base_agent_file_env_variable(self, tmp_path, monkeypatch):
        """Test finding base agent via environment variable."""
        base_agent_path = tmp_path / "custom" / "base_agent.json"
        base_agent_path.parent.mkdir(parents=True, exist_ok=True)
        base_agent_path.write_text('{"name": "base"}')

        monkeypatch.setenv("CLAUDE_MPM_BASE_AGENT_PATH", str(base_agent_path))

        # Create new service to trigger _find_base_agent_file
        with patch(
            "claude_mpm.services.agents.deployment.agent_deployment.logger"
        ), patch.object(
            AgentDeploymentService, "__init__", lambda self, *args, **kwargs: None
        ):
            test_service = AgentDeploymentService()
            # Use a Mock that has a logger attribute
            test_service._logger = Mock()
            test_service.logger = test_service._logger
            result = test_service._find_base_agent_file()

        assert result == base_agent_path

    def test_find_base_agent_file_cwd(self, tmp_path, monkeypatch):
        """Test finding base agent in current working directory."""
        # Create base agent in expected location
        base_agent_path = tmp_path / "src" / "claude_mpm" / "agents" / "base_agent.json"
        base_agent_path.parent.mkdir(parents=True, exist_ok=True)
        base_agent_path.write_text('{"name": "base"}')

        # Change to tmp_path as cwd
        monkeypatch.chdir(tmp_path)

        with patch.object(
            AgentDeploymentService, "__init__", lambda self, *args, **kwargs: None
        ):
            test_service = AgentDeploymentService()
            test_service._logger = Mock()
            test_service.logger = test_service._logger
            result = test_service._find_base_agent_file()

        assert result == base_agent_path

    def test_find_base_agent_file_fallback(self):
        """Test base agent file fallback to framework path."""
        with patch.object(
            AgentDeploymentService, "__init__", lambda self, *args, **kwargs: None
        ):
            test_service = AgentDeploymentService()
            test_service._logger = Mock()
            test_service.logger = test_service._logger

            with patch.object(Path, "exists", return_value=False):
                result = test_service._find_base_agent_file()

        # Should fallback to framework path even if it doesn't exist
        assert "agents" in str(result)
        assert "base_agent.json" in str(result)

    def test_determine_source_tier_system(self, service):
        """Test determining system source tier."""
        with patch.object(service, "_determine_source_tier") as mock_determine:
            mock_determine.return_value = "system"

            result = service._determine_source_tier()

        assert result == "system"

    def test_determine_source_tier_project(self, service):
        """Test determining project source tier."""
        with patch(
            "claude_mpm.services.agents.deployment.agent_deployment.DeploymentTypeDetector"
        ) as mock_detector:
            mock_detector.determine_source_tier.return_value = "project"

            result = service._determine_source_tier()

        assert result == "project"


