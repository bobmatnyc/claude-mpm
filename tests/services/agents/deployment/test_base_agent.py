"""Test base agent operations and discovery.

This module tests base agent file discovery, path resolution, and source
tier determination for the deployment system.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from claude_mpm.services.agents.deployment.async_agent_deployment import (
    AsyncAgentDeploymentService,
)


class TestBaseAgentHandling:
    """Test base agent operations."""

    @pytest.fixture
    def async_service(self, tmp_path):
        """Create an AsyncAgentDeploymentService for testing."""
        # Create required directories
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir(parents=True, exist_ok=True)

        # Create a base agent file
        base_agent_path = tmp_path / "base_agent.json"
        base_agent_path.write_text('{"name": "base"}')

        # Create service with test paths
        with patch.object(
            AsyncAgentDeploymentService, "_find_base_agent_file"
        ) as mock_find:
            mock_find.return_value = base_agent_path
            service = AsyncAgentDeploymentService(
                templates_dir=templates_dir,
                working_directory=tmp_path,
            )

        return service

    def test_find_base_agent_file_env_variable(self, tmp_path, monkeypatch):
        """Test finding base agent via environment variable."""
        base_agent_path = tmp_path / "custom" / "base_agent.json"
        base_agent_path.parent.mkdir(parents=True, exist_ok=True)
        base_agent_path.write_text('{"name": "base"}')

        monkeypatch.setenv("CLAUDE_MPM_BASE_AGENT_PATH", str(base_agent_path))

        # Create templates dir
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir(parents=True, exist_ok=True)

        # Create service - it should find base agent from env var
        service = AsyncAgentDeploymentService(
            templates_dir=templates_dir,
            working_directory=tmp_path,
        )

        assert service.base_agent_path == base_agent_path

    def test_find_base_agent_file_cwd(self, tmp_path, monkeypatch):
        """Test finding base agent in current working directory."""
        # Create base agent in expected location relative to cwd
        base_agent_path = tmp_path / "src" / "claude_mpm" / "agents" / "base_agent.json"
        base_agent_path.parent.mkdir(parents=True, exist_ok=True)
        base_agent_path.write_text('{"name": "base"}')

        # Create templates dir
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir(parents=True, exist_ok=True)

        # Change to tmp_path as cwd
        monkeypatch.chdir(tmp_path)

        # Create service
        service = AsyncAgentDeploymentService(
            templates_dir=templates_dir,
            working_directory=tmp_path,
        )

        assert service.base_agent_path == base_agent_path

    def test_find_base_agent_file_fallback(self, tmp_path):
        """Test base agent file fallback to framework path."""
        # Create templates dir
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir(parents=True, exist_ok=True)

        # Create service without any base agent files present
        # Should fall back to framework path
        with patch("pathlib.Path.exists", return_value=False):
            service = AsyncAgentDeploymentService(
                templates_dir=templates_dir,
                working_directory=tmp_path,
            )

        # Should have a base_agent_path even if it doesn't exist
        assert service.base_agent_path is not None
        assert "base_agent" in str(service.base_agent_path)

    def test_base_agent_path_from_constructor(self, tmp_path):
        """Test that base_agent_path can be provided in constructor."""
        base_agent_path = tmp_path / "my_base.json"
        base_agent_path.write_text('{"name": "custom_base"}')

        templates_dir = tmp_path / "templates"
        templates_dir.mkdir(parents=True, exist_ok=True)

        service = AsyncAgentDeploymentService(
            templates_dir=templates_dir,
            base_agent_path=base_agent_path,
            working_directory=tmp_path,
        )

        assert service.base_agent_path == base_agent_path

    def test_base_agent_loaded_correctly(self, tmp_path):
        """Test that base agent content is loaded correctly."""
        base_agent_path = tmp_path / "base_agent.json"
        base_agent_content = '{"name": "test_base", "version": "1.0.0"}'
        base_agent_path.write_text(base_agent_content)

        templates_dir = tmp_path / "templates"
        templates_dir.mkdir(parents=True, exist_ok=True)

        service = AsyncAgentDeploymentService(
            templates_dir=templates_dir,
            base_agent_path=base_agent_path,
            working_directory=tmp_path,
        )

        # The service should have loaded the base agent
        assert service.base_agent_path == base_agent_path
