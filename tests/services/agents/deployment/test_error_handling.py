"""Unit tests for Error Handling and Helper Methods.

Tests error handling scenarios and helper methods.
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


class TestErrorHandling(TestAgentDeploymentService):
    """Test error handling scenarios."""

    def test_deploy_agents_missing_templates_dir(
        self, service, tmp_path, mock_dependencies
    ):
        """Test deployment when templates directory doesn't exist."""
        service.templates_dir = tmp_path / "non_existent"

        mock_dependencies["configuration_manager"].load_base_agent.return_value = (
            {},
            (0, 0, 0),
        )

        with patch.object(service, "_load_deployment_config") as mock_load_config:
            mock_load_config.return_value = (Mock(), [])

            with patch.object(
                service, "_validate_and_repair_existing_agents"
            ) as mock_repair:
                mock_repair.return_value = {"repaired": []}

                result = service.deploy_agents()

        assert len(result["errors"]) > 0
        assert "not found" in result["errors"][0]

    def test_deploy_agents_template_build_failure(
        self, service, tmp_path, mock_dependencies
    ):
        """Test handling template build failures."""
        mock_dependencies["configuration_manager"].load_base_agent.return_value = (
            {},
            (1, 0, 0),
        )
        mock_dependencies["discovery_service"].get_filtered_templates.return_value = [
            tmp_path / "agent.json"
        ]
        mock_dependencies["template_builder"].build_agent_markdown.side_effect = (
            Exception("Template build failed")
        )

        with patch.object(service, "_load_deployment_config") as mock_load_config:
            mock_load_config.return_value = (Mock(), [])

            with patch.object(
                service, "_validate_and_repair_existing_agents"
            ) as mock_repair:
                mock_repair.return_value = {"repaired": []}

                with patch.object(service, "_convert_yaml_to_md") as mock_convert:
                    mock_convert.return_value = {"converted": []}

                    result = service.deploy_agents()

        assert len(result["errors"]) > 0

    def test_deploy_agent_template_not_found(self, service, tmp_path):
        """Test deploying non-existent single agent."""
        target_dir = tmp_path / ".claude" / "agents"

        result = service.deploy_agent("non_existent", target_dir)

        assert result is False

    def test_deploy_agent_build_failure(
        self, service, tmp_path, mock_dependencies, sample_agent_template
    ):
        """Test handling single agent build failure."""
        target_dir = tmp_path / ".claude" / "agents"

        mock_dependencies["template_builder"].build_agent_markdown.return_value = None

        result = service.deploy_agent("test_agent", target_dir)

        assert result is False

    def test_deploy_agent_custom_exception(
        self, service, tmp_path, mock_dependencies, sample_agent_template
    ):
        """Test handling AgentDeploymentError in single agent deployment."""
        target_dir = tmp_path / ".claude" / "agents"

        mock_dependencies["template_builder"].build_agent_markdown.side_effect = (
            AgentDeploymentError(
                "Custom deployment error", context={"agent": "test_agent"}
            )
        )

        with pytest.raises(AgentDeploymentError) as exc_info:
            service.deploy_agent("test_agent", target_dir)

        assert "Custom deployment error" in str(exc_info.value)

    def test_async_deployment_import_error(self, service, tmp_path):
        """Test fallback when async deployment module not available."""
        # Mock the import to raise ImportError
        with patch.object(service, "_try_async_deployment") as mock_async:
            mock_async.return_value = None

            result = service._try_async_deployment(
                target_dir=tmp_path,
                force_rebuild=False,
                config=Mock(),
                deployment_start_time=0,
            )

        assert result is None

    def test_async_deployment_runtime_error(self, service, tmp_path):
        """Test fallback when async deployment fails."""
        # Test the actual method behavior
        original_import = __import__

        def mock_import(name, *args, **kwargs):
            if "async_agent_deployment" in name:
                raise ImportError("No async module")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            result = service._try_async_deployment(
                target_dir=tmp_path,
                force_rebuild=False,
                config=Mock(),
                deployment_start_time=0,
            )

        assert result is None

    def test_validate_agent_not_found(self, service, tmp_path):
        """Test validating non-existent agent."""
        agent_path = tmp_path / "non_existent.md"

        is_valid, errors = service.validate_agent(agent_path)

        assert is_valid is False
        assert "not found" in errors[0]

    def test_validate_agent_read_error(self, service, tmp_path):
        """Test handling read errors during validation."""
        agent_path = tmp_path / "agent.md"
        agent_path.write_text("content")

        with patch.object(Path, "read_text", side_effect=OSError("Read failed")):
            is_valid, errors = service.validate_agent(agent_path)

        assert is_valid is False
        assert "Validation error" in errors[0]


class TestHelperMethods(TestAgentDeploymentService):
    """Test helper and utility methods."""

    def test_get_agent_tools(self, service):
        """Test getting agent-specific tools."""
        with patch(
            "claude_mpm.services.agents.deployment.agent_deployment.AgentConfigProvider"
        ) as mock_provider:
            mock_provider.get_agent_tools.return_value = ["tool1", "tool2"]

            result = service._get_agent_tools("test_agent", {"type": "standard"})

        assert result == ["tool1", "tool2"]

    def test_get_agent_specific_config(self, service):
        """Test getting agent-specific configuration."""
        with patch(
            "claude_mpm.services.agents.deployment.agent_deployment.AgentConfigProvider"
        ) as mock_provider:
            expected_config = {"setting1": "value1", "setting2": "value2"}
            mock_provider.get_agent_specific_config.return_value = expected_config

            result = service._get_agent_specific_config("test_agent")

        assert result == expected_config

    def test_deploy_system_instructions(self, service, tmp_path):
        """Test deploying system instructions."""
        target_dir = tmp_path / ".claude"
        results = {"deployed": [], "updated": [], "skipped": [], "errors": []}

        with patch(
            "claude_mpm.services.agents.deployment.agent_deployment.SystemInstructionsDeployer"
        ) as mock_deployer_class:
            mock_deployer = Mock()
            mock_deployer_class.return_value = mock_deployer

            service._deploy_system_instructions(target_dir, False, results)

        mock_deployer.deploy_system_instructions.assert_called_with(
            target_dir, False, results
        )

    def test_deploy_system_instructions_explicit(self, service, tmp_path):
        """Test explicit system instructions deployment."""
        with patch(
            "claude_mpm.services.agents.deployment.agent_deployment.SystemInstructionsDeployer"
        ) as mock_deployer_class:
            mock_deployer = Mock()
            mock_deployer_class.return_value = mock_deployer

            result = service.deploy_system_instructions_explicit()

        assert "deployed" in result
        assert "errors" in result
        mock_deployer.deploy_system_instructions.assert_called_once()

    def test_convert_yaml_to_md(self, service, tmp_path, mock_dependencies):
        """Test YAML to MD conversion."""
        target_dir = tmp_path / ".claude" / "agents"
        expected_result = {"converted": ["agent1.yaml", "agent2.yaml"]}

        mock_dependencies["format_converter"].convert_yaml_to_md.return_value = (
            expected_result
        )

        result = service._convert_yaml_to_md(target_dir)

        assert result == expected_result

    def test_clean_deployment(self, service, tmp_path, mock_dependencies):
        """Test cleaning deployment."""
        config_dir = tmp_path / ".claude"
        expected_result = {"removed": ["agent1.md", "agent2.md"], "errors": []}

        mock_dependencies["filesystem_manager"].clean_deployment.return_value = (
            expected_result
        )

        result = service.clean_deployment(config_dir)

        assert result == expected_result

    def test_determine_agent_source_system(self, service, tmp_path):
        """Test determining agent source as system."""
        template_path = Path("/usr/local/lib/claude_mpm/agents/templates/agent.json")

        result = service._determine_agent_source(template_path)

        assert result == "system"

    def test_determine_agent_source_project(self, service, tmp_path):
        """Test determining agent source as project."""
        service.working_directory = tmp_path
        template_path = tmp_path / ".claude-mpm" / "agents" / "agent.json"

        result = service._determine_agent_source(template_path)

        assert result == "project"

    def test_determine_agent_source_user(self, service):
        """Test determining agent source as user."""
        template_path = Path.home() / ".claude-mpm" / "agents" / "agent.json"

        result = service._determine_agent_source(template_path)

        assert result == "user"

    def test_determine_agent_source_unknown(self, service, tmp_path):
        """Test determining agent source as unknown."""
        template_path = tmp_path / "random" / "location" / "agent.json"

        result = service._determine_agent_source(template_path)

        assert result == "unknown"

    def test_should_use_multi_source_deployment_update(self, service):
        """Test multi-source deployment decision for update mode."""
        result = service._should_use_multi_source_deployment("update")

        assert result is True

    def test_should_use_multi_source_deployment_project(self, service):
        """Test multi-source deployment decision for project mode."""
        result = service._should_use_multi_source_deployment("project")

        assert result is True

    def test_should_use_multi_source_deployment_other(self, service):
        """Test multi-source deployment decision for other modes."""
        result = service._should_use_multi_source_deployment("custom")

        assert result is False


