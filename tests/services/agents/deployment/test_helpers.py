"""Test helper methods and utility functions.

This module tests various helper methods including agent-specific configuration,
tool resolution, system instructions deployment, format conversion, and
source determination.
"""

from pathlib import Path
from unittest.mock import Mock, patch

from conftest import TestAgentDeploymentService


class TestHelperMethods(TestAgentDeploymentService):
    """Test helper and utility methods."""

    def test_get_agent_tools(self, service):
        """Test getting agent-specific tools."""
        with patch(
            "claude_mpm.services.agents.deployment.agent_config_provider.AgentConfigProvider"
        ) as mock_provider:
            mock_provider.get_agent_tools.return_value = ["tool1", "tool2"]

            result = service._get_agent_tools("test_agent", {"type": "standard"})

        assert result == ["tool1", "tool2"]

    def test_get_agent_specific_config(self, service):
        """Test getting agent-specific configuration."""
        with patch(
            "claude_mpm.services.agents.deployment.agent_config_provider.AgentConfigProvider"
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
            "claude_mpm.services.agents.deployment.system_instructions_deployer.SystemInstructionsDeployer"
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
            "claude_mpm.services.agents.deployment.system_instructions_deployer.SystemInstructionsDeployer"
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
