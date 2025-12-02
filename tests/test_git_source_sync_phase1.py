"""Tests for Phase 1 Git Source Sync refactoring.

Tests the new Git Tree API implementation and cache/deployment separation.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from claude_mpm.services.agents.sources.git_source_sync_service import (
    GitSourceSyncService,
)


class TestGitTreeAPIDiscovery:
    """Test Git Tree API for nested directory discovery."""

    @pytest.fixture
    def service(self):
        """Create service with temporary cache directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = GitSourceSyncService(cache_dir=Path(tmpdir))
            yield service

    def test_discover_agents_via_tree_api_success(self, service):
        """Test successful agent discovery via Tree API."""
        # Mock API responses
        mock_refs_response = Mock()
        mock_refs_response.status_code = 200
        mock_refs_response.json.return_value = {"object": {"sha": "abc123def456"}}

        mock_tree_response = Mock()
        mock_tree_response.status_code = 200
        mock_tree_response.json.return_value = {
            "tree": [
                {"type": "blob", "path": "agents/research.md"},
                {"type": "blob", "path": "agents/engineer/core/engineer.md"},
                {"type": "blob", "path": "agents/engineer/core/metadata.json"},
                {"type": "blob", "path": "agents/qa.md"},
                {"type": "blob", "path": "agents/README.md"},  # Should be filtered
                {"type": "tree", "path": "agents/engineer"},  # Directory, not file
                {"type": "blob", "path": "docs/guide.md"},  # Wrong directory
            ]
        }

        with patch.object(service.session, "get") as mock_get:
            mock_get.side_effect = [mock_refs_response, mock_tree_response]

            # Test discovery
            agents = service._discover_agents_via_tree_api(
                "bobmatnyc", "claude-mpm-agents", "main", "agents"
            )

            # Verify results
            assert len(agents) == 4  # research.md, engineer.md, metadata.json, qa.md
            assert "research.md" in agents
            assert "engineer/core/engineer.md" in agents
            assert "engineer/core/metadata.json" in agents
            assert "qa.md" in agents
            assert "README.md" not in agents  # Filtered out

    def test_discover_agents_via_tree_api_rate_limit(self, service):
        """Test handling of rate limit errors."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.json.return_value = {"message": "API rate limit exceeded"}

        with patch.object(service.session, "get", return_value=mock_response):
            with pytest.raises(Exception):
                service._discover_agents_via_tree_api(
                    "bobmatnyc", "claude-mpm-agents", "main", "agents"
                )

    def test_get_agent_list_uses_tree_api(self, service):
        """Test that _get_agent_list uses Tree API."""
        # Mock Tree API responses
        mock_refs_response = Mock()
        mock_refs_response.status_code = 200
        mock_refs_response.json.return_value = {"object": {"sha": "abc123"}}

        mock_tree_response = Mock()
        mock_tree_response.status_code = 200
        mock_tree_response.json.return_value = {
            "tree": [
                {"type": "blob", "path": "agents/research.md"},
                {"type": "blob", "path": "agents/engineer/core/engineer.md"},
            ]
        }

        with patch.object(service.session, "get") as mock_get:
            mock_get.side_effect = [mock_refs_response, mock_tree_response]

            agents = service._get_agent_list()

            # Verify Tree API was called
            assert len(agents) == 2
            assert "engineer/core/engineer.md" in agents


class TestCacheDirectoryStructure:
    """Test cache directory preserves nested structure."""

    @pytest.fixture
    def service(self):
        """Create service with temporary cache directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "cache" / "agents"
            service = GitSourceSyncService(cache_dir=cache_dir)
            yield service

    def test_cache_directory_created(self, service):
        """Test cache directory is created at ~/.claude-mpm/cache/agents/."""
        assert service.cache_dir.exists()
        assert service.cache_dir.name == "agents"
        assert service.cache_dir.parent.name == "cache"

    def test_save_to_cache_preserves_nested_structure(self, service):
        """Test saving nested agent files preserves directory structure."""
        # Save nested agent
        service._save_to_cache("engineer/core/engineer.md", "# Engineer Agent")

        # Verify nested structure preserved
        nested_file = service.cache_dir / "engineer" / "core" / "engineer.md"
        assert nested_file.exists()
        assert nested_file.read_text() == "# Engineer Agent"

    def test_save_to_cache_creates_parent_directories(self, service):
        """Test parent directories are created automatically."""
        service._save_to_cache("deep/nested/path/agent.md", "# Nested Agent")

        nested_file = service.cache_dir / "deep" / "nested" / "path" / "agent.md"
        assert nested_file.exists()


class TestDeploymentFromCache:
    """Test deployment from cache to project directory."""

    @pytest.fixture
    def service_with_cache(self):
        """Create service with cached agents."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "cache"
            service = GitSourceSyncService(cache_dir=cache_dir)

            # Populate cache with test agents
            service._save_to_cache("research.md", "# Research Agent")
            service._save_to_cache("engineer/core/engineer.md", "# Engineer Agent")
            service._save_to_cache("qa.md", "# QA Agent")

            yield service

    @pytest.fixture
    def project_dir(self):
        """Create temporary project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_deploy_agents_to_project(self, service_with_cache, project_dir):
        """Test deploying agents from cache to project."""
        result = service_with_cache.deploy_agents_to_project(project_dir)

        # Verify deployment directory created
        deployment_dir = project_dir / ".claude-mpm" / "agents"
        assert deployment_dir.exists()

        # Verify agents deployed (flattened)
        assert (deployment_dir / "research.md").exists()
        assert (deployment_dir / "engineer.md").exists()  # Flattened from nested
        assert (deployment_dir / "qa.md").exists()

        # Verify results tracking
        assert len(result["deployed"]) == 3
        assert "research.md" in result["deployed"]
        assert "engineer.md" in result["deployed"]

    def test_deploy_agents_flattens_nested_paths(self, service_with_cache, project_dir):
        """Test nested paths are flattened during deployment."""
        service_with_cache.deploy_agents_to_project(project_dir)

        deployment_dir = project_dir / ".claude-mpm" / "agents"

        # Nested path should be flattened
        assert (deployment_dir / "engineer.md").exists()
        assert not (deployment_dir / "engineer" / "core" / "engineer.md").exists()

    def test_deploy_agents_skip_up_to_date(self, service_with_cache, project_dir):
        """Test deployment skips already up-to-date agents."""
        # First deployment
        result1 = service_with_cache.deploy_agents_to_project(project_dir)
        assert len(result1["deployed"]) == 3

        # Second deployment (without force)
        result2 = service_with_cache.deploy_agents_to_project(project_dir)
        assert len(result2["skipped"]) == 3
        assert len(result2["deployed"]) == 0

    def test_deploy_agents_force_redeploy(self, service_with_cache, project_dir):
        """Test force redeployment overwrites existing agents."""
        # First deployment
        service_with_cache.deploy_agents_to_project(project_dir)

        # Force redeployment
        result = service_with_cache.deploy_agents_to_project(project_dir, force=True)
        assert len(result["updated"]) > 0 or len(result["deployed"]) > 0
        assert len(result["skipped"]) == 0

    def test_discover_cached_agents(self, service_with_cache):
        """Test discovering cached agents."""
        agents = service_with_cache._discover_cached_agents()

        assert len(agents) == 3
        assert "research.md" in agents
        assert "engineer/core/engineer.md" in agents
        assert "qa.md" in agents


class TestProgressBarIntegration:
    """Test progress bar works with nested paths."""

    @pytest.fixture
    def service(self):
        """Create service with temporary cache directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = GitSourceSyncService(cache_dir=Path(tmpdir))
            yield service

    def test_sync_agents_progress_bar_with_nested_paths(self, service):
        """Test progress bar shows correct count with nested agents."""
        # Mock Tree API to return nested agents
        mock_refs_response = Mock()
        mock_refs_response.status_code = 200
        mock_refs_response.json.return_value = {"object": {"sha": "abc123"}}

        mock_tree_response = Mock()
        mock_tree_response.status_code = 200
        mock_tree_response.json.return_value = {
            "tree": [
                {"type": "blob", "path": "agents/research.md"},
                {"type": "blob", "path": "agents/engineer/core/engineer.md"},
                {"type": "blob", "path": "agents/qa.md"},
            ]
        }

        # Mock download responses
        mock_download_response = Mock()
        mock_download_response.status_code = 200
        mock_download_response.text = "# Agent Content"
        mock_download_response.headers = {"ETag": "abc123"}

        with patch.object(service.session, "get") as mock_get:
            # First 2 calls are Tree API, rest are downloads
            mock_get.side_effect = [
                mock_refs_response,
                mock_tree_response,
            ] + [mock_download_response] * 3

            # Sync with progress disabled (for testing)
            result = service.sync_agents(show_progress=False)

            # Verify all nested agents synced
            assert result["total_downloaded"] == 3


class TestBackwardCompatibility:
    """Test backward compatibility with existing systems."""

    @pytest.fixture
    def service(self):
        """Create service with temporary cache directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = GitSourceSyncService(cache_dir=Path(tmpdir))
            yield service

    def test_get_cached_agents_dir_returns_cache_directory(self, service):
        """Test get_cached_agents_dir() returns correct cache directory."""
        cache_dir = service.get_cached_agents_dir()
        assert cache_dir == service.cache_dir
        assert cache_dir.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
