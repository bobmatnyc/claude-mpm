"""
Tests for Agent Cleanup Service
================================

Comprehensive tests for the agent cleanup service including cleanup operations,
dry-run mode, orphan detection, and error handling.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.services.cli.agent_cleanup_service import (
    AgentCleanupService, IAgentCleanupService)


class TestAgentCleanupService:
    """Test suite for AgentCleanupService."""

    @pytest.fixture
    def mock_deployment_service(self):
        """Create a mock deployment service."""
        service = MagicMock()
        service.clean_deployment = MagicMock(
            return_value={
                "removed": ["agent1", "agent2"],
                "preserved": ["user_agent"],
                "errors": [],
                "success": True,
            }
        )
        return service

    @pytest.fixture
    def mock_multi_source_service(self):
        """Create a mock multi-source deployment service."""
        service = MagicMock()
        service.cleanup_orphaned_agents = MagicMock(
            return_value={
                "orphaned": [
                    {
                        "name": "old_agent",
                        "file": "/path/to/old_agent.md",
                        "version": "1.0.0",
                    }
                ],
                "removed": [],
                "errors": [],
            }
        )
        service.discover_agents_from_all_sources = MagicMock(
            return_value={
                "Agent1": [{"file_path": "/path/to/agent1.md"}],
                "Agent2": [{"file_path": "/path/to/agent2.md"}],
            }
        )
        service.detect_orphaned_agents = MagicMock(
            return_value=[
                {"name": "orphan1", "file": "/path/to/orphan1.md", "version": "1.0.0"}
            ]
        )
        return service

    @pytest.fixture
    def cleanup_service(self, mock_deployment_service):
        """Create a cleanup service with mocked dependencies."""
        return AgentCleanupService(deployment_service=mock_deployment_service)

    def test_interface_compliance(self):
        """Test that AgentCleanupService implements IAgentCleanupService."""
        service = AgentCleanupService()
        assert isinstance(service, IAgentCleanupService)

    def test_clean_deployed_agents_success(
        self, cleanup_service, mock_deployment_service
    ):
        """Test successful cleanup of deployed agents."""
        result = cleanup_service.clean_deployed_agents()

        assert result["success"] is True
        assert result["cleaned_count"] == 2  # Two agents removed
        assert "removed" in result
        assert len(result["removed"]) == 2
        mock_deployment_service.clean_deployment.assert_called_once()

    def test_clean_deployed_agents_with_custom_dir(self, cleanup_service):
        """Test cleanup with custom agents directory."""
        custom_dir = Path("/custom/agents")
        result = cleanup_service.clean_deployed_agents(agents_dir=custom_dir)

        assert result["success"] is True

    def test_clean_deployed_agents_no_method(self, cleanup_service):
        """Test fallback when deployment service lacks clean_deployment method."""
        # Remove the method to test fallback
        del cleanup_service._deployment_service.clean_deployment

        result = cleanup_service.clean_deployed_agents()

        assert result["success"] is False
        assert "does not support cleanup" in result["error"]
        assert result["cleaned_count"] == 0

    def test_clean_deployed_agents_exception(self, cleanup_service):
        """Test error handling in clean_deployed_agents."""
        cleanup_service._deployment_service.clean_deployment.side_effect = Exception(
            "Test error"
        )

        result = cleanup_service.clean_deployed_agents()

        assert result["success"] is False
        assert "Test error" in result["error"]
        assert result["cleaned_count"] == 0

    @patch("claude_mpm.services.cli.agent_cleanup_service.Path")
    def test_clean_orphaned_agents_dry_run(
        self, mock_path, cleanup_service, mock_multi_source_service
    ):
        """Test orphaned agent cleanup in dry-run mode."""
        # Setup path mocks
        mock_agents_dir = MagicMock()
        mock_agents_dir.exists.return_value = True
        mock_path.cwd.return_value = MagicMock()
        mock_path.cwd.return_value.__truediv__.return_value.__truediv__.return_value = (
            mock_agents_dir
        )

        # Patch multi-source service
        with patch.object(
            cleanup_service,
            "_get_multi_source_service",
            return_value=mock_multi_source_service,
        ):
            result = cleanup_service.clean_orphaned_agents(dry_run=True)

        assert result["success"] is True
        assert len(result["orphaned"]) == 1
        assert result["orphaned"][0]["name"] == "old_agent"
        mock_multi_source_service.cleanup_orphaned_agents.assert_called_once_with(
            mock_agents_dir, dry_run=True
        )

    @patch("claude_mpm.services.cli.agent_cleanup_service.Path")
    def test_clean_orphaned_agents_actual_removal(
        self, mock_path, cleanup_service, mock_multi_source_service
    ):
        """Test orphaned agent cleanup with actual removal."""
        # Setup path mocks
        mock_agents_dir = MagicMock()
        mock_agents_dir.exists.return_value = True
        mock_path.cwd.return_value = MagicMock()
        mock_path.cwd.return_value.__truediv__.return_value.__truediv__.return_value = (
            mock_agents_dir
        )

        # Update mock to simulate actual removal
        mock_multi_source_service.cleanup_orphaned_agents.return_value = {
            "orphaned": [
                {
                    "name": "old_agent",
                    "file": "/path/to/old_agent.md",
                    "version": "1.0.0",
                }
            ],
            "removed": ["old_agent"],
            "errors": [],
        }

        # Patch multi-source service
        with patch.object(
            cleanup_service,
            "_get_multi_source_service",
            return_value=mock_multi_source_service,
        ):
            result = cleanup_service.clean_orphaned_agents(dry_run=False)

        assert result["success"] is True
        assert len(result["removed"]) == 1
        assert "old_agent" in result["removed"]
        mock_multi_source_service.cleanup_orphaned_agents.assert_called_once_with(
            mock_agents_dir, dry_run=False
        )

    @patch("claude_mpm.services.cli.agent_cleanup_service.Path")
    def test_clean_orphaned_agents_no_directory(self, mock_path, cleanup_service):
        """Test orphaned cleanup when agents directory doesn't exist."""
        # Setup path mocks
        mock_agents_dir = MagicMock()
        mock_agents_dir.exists.return_value = False
        mock_path.cwd.return_value = MagicMock()
        mock_path.cwd.return_value.__truediv__.return_value.__truediv__.return_value = (
            mock_agents_dir
        )
        mock_path.home.return_value = MagicMock()
        mock_path.home.return_value.__truediv__.return_value.__truediv__.return_value = (
            mock_agents_dir
        )

        result = cleanup_service.clean_orphaned_agents()

        assert result["success"] is True
        assert "not found" in result["message"]
        assert len(result["orphaned"]) == 0
        assert len(result["removed"]) == 0

    @patch("claude_mpm.services.cli.agent_cleanup_service.Path")
    def test_get_orphaned_agents(
        self, mock_path, cleanup_service, mock_multi_source_service
    ):
        """Test finding orphaned agents without removing them."""
        # Setup path mocks
        mock_agents_dir = MagicMock()
        mock_agents_dir.exists.return_value = True
        mock_path.cwd.return_value = MagicMock()
        mock_path.cwd.return_value.__truediv__.return_value.__truediv__.return_value = (
            mock_agents_dir
        )

        # Patch multi-source service
        with patch.object(
            cleanup_service,
            "_get_multi_source_service",
            return_value=mock_multi_source_service,
        ):
            orphaned = cleanup_service.get_orphaned_agents()

        assert len(orphaned) == 1
        assert orphaned[0]["name"] == "orphan1"
        mock_multi_source_service.discover_agents_from_all_sources.assert_called_once()
        mock_multi_source_service.detect_orphaned_agents.assert_called_once()

    @patch("claude_mpm.services.cli.agent_cleanup_service.Path")
    def test_perform_cleanup_all(
        self, mock_path, cleanup_service, mock_multi_source_service
    ):
        """Test performing cleanup of all types."""
        # Setup path mocks
        mock_agents_dir = MagicMock()
        mock_agents_dir.exists.return_value = True
        mock_path.cwd.return_value = MagicMock()
        mock_path.cwd.return_value.__truediv__.return_value.__truediv__.return_value = (
            mock_agents_dir
        )

        # Patch multi-source service
        with patch.object(
            cleanup_service,
            "_get_multi_source_service",
            return_value=mock_multi_source_service,
        ):
            result = cleanup_service.perform_cleanup(cleanup_type="all", dry_run=False)

        assert result["success"] is True
        assert result["cleanup_type"] == "all"
        assert len(result["operations"]) == 2

        # Check deployed cleanup operation
        deployed_op = next(
            op for op in result["operations"] if op["type"] == "deployed"
        )
        assert deployed_op["result"]["success"] is True

        # Check orphaned cleanup operation
        orphaned_op = next(
            op for op in result["operations"] if op["type"] == "orphaned"
        )
        assert "orphaned" in orphaned_op["result"]

    def test_perform_cleanup_deployed_only(self, cleanup_service):
        """Test performing cleanup of deployed agents only."""
        result = cleanup_service.perform_cleanup(cleanup_type="deployed", dry_run=False)

        assert result["success"] is True
        assert result["cleanup_type"] == "deployed"
        assert len(result["operations"]) == 1
        assert result["operations"][0]["type"] == "deployed"

    @patch("claude_mpm.services.cli.agent_cleanup_service.Path")
    def test_perform_cleanup_orphaned_only(
        self, mock_path, cleanup_service, mock_multi_source_service
    ):
        """Test performing cleanup of orphaned agents only."""
        # Setup path mocks
        mock_agents_dir = MagicMock()
        mock_agents_dir.exists.return_value = True
        mock_path.cwd.return_value = MagicMock()
        mock_path.cwd.return_value.__truediv__.return_value.__truediv__.return_value = (
            mock_agents_dir
        )

        # Patch multi-source service
        with patch.object(
            cleanup_service,
            "_get_multi_source_service",
            return_value=mock_multi_source_service,
        ):
            result = cleanup_service.perform_cleanup(
                cleanup_type="orphaned", dry_run=True
            )

        assert result["success"] is True
        assert result["cleanup_type"] == "orphaned"
        assert len(result["operations"]) == 1
        assert result["operations"][0]["type"] == "orphaned"

    def test_perform_cleanup_error_handling(self, cleanup_service):
        """Test error handling in perform_cleanup."""
        cleanup_service._deployment_service.clean_deployment.side_effect = Exception(
            "Test error"
        )

        result = cleanup_service.perform_cleanup(cleanup_type="all")

        # Should still return a result, but with success=False
        assert result["success"] is False
        assert result["total_errors"] > 0

    @patch("claude_mpm.services.cli.agent_cleanup_service.Path")
    def test_validate_cleanup(self, mock_path, cleanup_service):
        """Test cleanup validation."""
        # Setup path mocks
        mock_agents_dir = MagicMock()
        mock_agents_dir.exists.return_value = True

        # Create mock agent files
        mock_agent1 = MagicMock()
        mock_agent1.name = "agent1.md"
        mock_agent1.read_text.return_value = "author: claude-mpm\ncontent"

        mock_agent2 = MagicMock()
        mock_agent2.name = "agent2.md"
        mock_agent2.read_text.return_value = "author: user\ncontent"

        mock_agents_dir.glob.return_value = [mock_agent1, mock_agent2]

        mock_path.cwd.return_value = MagicMock()
        mock_path.cwd.return_value.__truediv__.return_value.__truediv__.return_value = (
            mock_agents_dir
        )

        # Mock get_orphaned_agents
        with patch.object(cleanup_service, "get_orphaned_agents", return_value=[]):
            result = cleanup_service.validate_cleanup()

        assert result["success"] is True
        assert result["exists"] is True
        assert result["deployed_count"] == 1
        assert result["user_created_count"] == 1
        assert result["orphaned_count"] == 0
        assert len(result["info"]) > 0

    @patch("claude_mpm.services.cli.agent_cleanup_service.Path")
    def test_validate_cleanup_with_orphans(self, mock_path, cleanup_service):
        """Test validation with orphaned agents."""
        # Setup path mocks
        mock_agents_dir = MagicMock()
        mock_agents_dir.exists.return_value = True
        mock_agents_dir.glob.return_value = []

        mock_path.cwd.return_value = MagicMock()
        mock_path.cwd.return_value.__truediv__.return_value.__truediv__.return_value = (
            mock_agents_dir
        )

        # Mock get_orphaned_agents to return orphans
        orphaned = [
            {"name": "orphan1", "version": "1.0.0"},
            {"name": "orphan2", "version": "2.0.0"},
        ]
        with patch.object(
            cleanup_service, "get_orphaned_agents", return_value=orphaned
        ):
            result = cleanup_service.validate_cleanup()

        assert result["success"] is True
        assert result["orphaned_count"] == 2
        assert "orphaned_agents" in result
        assert len(result["orphaned_agents"]) == 2
        assert len(result["warnings"]) > 0

    @patch("claude_mpm.services.cli.agent_cleanup_service.Path")
    def test_validate_cleanup_no_directory(self, mock_path, cleanup_service):
        """Test validation when agents directory doesn't exist."""
        # Setup path mocks
        mock_agents_dir = MagicMock()
        mock_agents_dir.exists.return_value = False

        mock_path.cwd.return_value = MagicMock()
        mock_path.cwd.return_value.__truediv__.return_value.__truediv__.return_value = (
            mock_agents_dir
        )
        mock_path.home.return_value = MagicMock()
        mock_path.home.return_value.__truediv__.return_value.__truediv__.return_value = (
            mock_agents_dir
        )

        result = cleanup_service.validate_cleanup()

        assert result["success"] is True
        assert result["exists"] is False
        assert "does not exist" in result["info"][0]

    def test_determine_agents_dir_project_level(self, cleanup_service):
        """Test agents directory determination prefers project level."""
        with patch("claude_mpm.services.cli.agent_cleanup_service.Path") as mock_path:
            mock_project_dir = MagicMock()
            mock_project_dir.exists.return_value = True

            mock_path.cwd.return_value = MagicMock()
            mock_path.cwd.return_value.__truediv__.return_value.__truediv__.return_value = (
                mock_project_dir
            )

            agents_dir = cleanup_service._determine_agents_dir()

            assert agents_dir == mock_project_dir

    def test_determine_agents_dir_home_fallback(self, cleanup_service):
        """Test agents directory falls back to home directory."""
        with patch("claude_mpm.services.cli.agent_cleanup_service.Path") as mock_path:
            mock_project_dir = MagicMock()
            mock_project_dir.exists.return_value = False

            mock_home_dir = MagicMock()

            mock_path.cwd.return_value = MagicMock()
            mock_path.cwd.return_value.__truediv__.return_value.__truediv__.return_value = (
                mock_project_dir
            )
            mock_path.home.return_value = MagicMock()
            mock_path.home.return_value.__truediv__.return_value.__truediv__.return_value = (
                mock_home_dir
            )

            agents_dir = cleanup_service._determine_agents_dir()

            assert agents_dir == mock_home_dir

    def test_determine_agents_dir_explicit(self, cleanup_service):
        """Test explicit agents directory is used when provided."""
        explicit_dir = Path("/explicit/agents")
        agents_dir = cleanup_service._determine_agents_dir(explicit_dir)

        assert agents_dir == explicit_dir
