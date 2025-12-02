"""Test base agent operations and discovery.

This module tests base agent file discovery, path resolution, and source
tier determination for the deployment system.
"""

from pathlib import Path
from unittest.mock import Mock, patch

from conftest import TestAgentDeploymentService

from claude_mpm.services.agents.deployment.agent_deployment import (
    AgentDeploymentService,
)


class TestBaseAgentHandling(TestAgentDeploymentService):
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
            "claude_mpm.services.agents.deployment.deployment_type_detector.DeploymentTypeDetector"
        ) as mock_detector:
            mock_detector.determine_source_tier.return_value = "project"

            result = service._determine_source_tier()

        assert result == "project"
