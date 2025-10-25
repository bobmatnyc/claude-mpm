"""Test error handling scenarios in agent deployment.

This module tests various error conditions including missing directories,
template build failures, async deployment errors, and validation failures.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from conftest import TestAgentDeploymentService

from claude_mpm.core.exceptions import AgentDeploymentError


class TestErrorHandling(TestAgentDeploymentService):
    """Test error handling scenarios in agent deployment."""

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
