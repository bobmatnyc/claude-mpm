"""Unit tests for SingleTierDeploymentService.

This test suite covers:
- deploy_all_agents with multiple repositories
- Priority-based conflict resolution
- deploy_agent with specific source
- list_available_agents filtering
- sync_sources with force flag
- remove_agent
- Dry run mode
- Error handling
"""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.claude_mpm.config.agent_sources import AgentSourceConfiguration
from src.claude_mpm.models.git_repository import GitRepository
from src.claude_mpm.services.agents.single_tier_deployment_service import \
    SingleTierDeploymentService


@pytest.fixture
def mock_config():
    """Create mock AgentSourceConfiguration."""
    config = Mock(spec=AgentSourceConfiguration)

    # Create mock repositories
    repo1 = GitRepository(
        url="https://github.com/owner1/repo1",
        subdirectory="agents",
        enabled=True,
        priority=100,
    )
    repo2 = GitRepository(
        url="https://github.com/owner2/repo2",
        enabled=True,
        priority=50,  # Higher precedence
    )

    config.get_enabled_repositories.return_value = [repo1, repo2]

    return config


@pytest.fixture
def mock_deployment_dir(tmp_path):
    """Create temporary deployment directory."""
    deploy_dir = tmp_path / "deployment"
    deploy_dir.mkdir()
    return deploy_dir


@pytest.fixture
def mock_cache_root(tmp_path):
    """Create temporary cache root."""
    cache_root = tmp_path / "cache"
    cache_root.mkdir()
    return cache_root


@pytest.fixture
def service(mock_config, mock_deployment_dir, mock_cache_root):
    """Create SingleTierDeploymentService instance."""
    return SingleTierDeploymentService(
        config=mock_config,
        deployment_dir=mock_deployment_dir,
        cache_root=mock_cache_root,
    )


class TestDeployAllAgents:
    """Test deploy_all_agents method."""

    def test_deploy_all_agents_success(
        self, service, mock_deployment_dir, mock_cache_root
    ):
        """Test successful deployment of all agents."""
        # Create mock agent files in cache
        repo1_cache = mock_cache_root / "owner1" / "repo1" / "agents"
        repo1_cache.mkdir(parents=True)
        (repo1_cache / "engineer.md").write_text("# Engineer\n\nTest agent")

        repo2_cache = mock_cache_root / "owner2" / "repo2"
        repo2_cache.mkdir(parents=True)
        (repo2_cache / "research.md").write_text("# Research\n\nTest agent")

        with patch.object(
            service.git_source_manager, "sync_all_repositories"
        ) as mock_sync:
            mock_sync.return_value = {
                "owner1/repo1/agents": {"synced": True, "files_updated": 1},
                "owner2/repo2": {"synced": True, "files_updated": 1},
            }

            with patch.object(service, "_discover_agents_in_repo") as mock_discover:
                mock_discover.side_effect = [
                    [
                        {
                            "agent_id": "engineer",
                            "metadata": {"name": "Engineer"},
                            "source_file": str(repo1_cache / "engineer.md"),
                            "repository": "owner1/repo1/agents",
                            "priority": 100,
                        }
                    ],
                    [
                        {
                            "agent_id": "research",
                            "metadata": {"name": "Research"},
                            "source_file": str(repo2_cache / "research.md"),
                            "repository": "owner2/repo2",
                            "priority": 50,
                        }
                    ],
                ]

                result = service.deploy_all_agents(force_sync=False, dry_run=False)

        # Verify results
        assert result["synced_repos"] == 2
        assert result["discovered_agents"] == 2
        assert result["deployed_agents"] == 2
        assert result["skipped_agents"] == 0
        assert result["conflicts_resolved"] == 0
        assert len(result["agents"]) == 2

        # Verify deployment
        assert (mock_deployment_dir / "engineer.md").exists()
        assert (mock_deployment_dir / "research.md").exists()

    def test_deploy_all_agents_dry_run(self, service):
        """Test dry run mode doesn't deploy files."""
        with patch.object(
            service.git_source_manager, "sync_all_repositories"
        ) as mock_sync:
            mock_sync.return_value = {
                "owner1/repo1/agents": {"synced": True, "files_updated": 1},
            }

            with patch.object(service, "_discover_agents_in_repo") as mock_discover:
                mock_discover.return_value = [
                    {
                        "agent_id": "engineer",
                        "metadata": {"name": "Engineer"},
                        "source_file": "/fake/path/engineer.md",
                        "repository": "owner1/repo1/agents",
                        "priority": 100,
                    }
                ]

                result = service.deploy_all_agents(force_sync=False, dry_run=True)

        # Verify no deployment
        assert result["deployed_agents"] == 0
        assert result["skipped_agents"] == 1
        assert result["agents"][0]["dry_run"] is True

    def test_deploy_all_agents_no_repos(self, mock_deployment_dir, mock_cache_root):
        """Test with no enabled repositories."""
        config = Mock(spec=AgentSourceConfiguration)
        config.get_enabled_repositories.return_value = []

        service = SingleTierDeploymentService(
            config=config,
            deployment_dir=mock_deployment_dir,
            cache_root=mock_cache_root,
        )

        result = service.deploy_all_agents()

        assert result["synced_repos"] == 0
        assert result["discovered_agents"] == 0
        assert result["deployed_agents"] == 0

    def test_deploy_all_agents_with_conflict_resolution(self, service, mock_cache_root):
        """Test priority-based conflict resolution."""
        # Both repos have an "engineer" agent
        with patch.object(
            service.git_source_manager, "sync_all_repositories"
        ) as mock_sync:
            mock_sync.return_value = {
                "owner1/repo1/agents": {"synced": True},
                "owner2/repo2": {"synced": True},
            }

            with patch.object(service, "_discover_agents_in_repo") as mock_discover:
                mock_discover.side_effect = [
                    [
                        {
                            "agent_id": "engineer",
                            "metadata": {"name": "Engineer"},
                            "source_file": "/fake/path1/engineer.md",
                            "repository": "owner1/repo1/agents",
                            "priority": 100,
                        }
                    ],
                    [
                        {
                            "agent_id": "engineer",
                            "metadata": {"name": "Engineer"},
                            "source_file": "/fake/path2/engineer.md",
                            "repository": "owner2/repo2",
                            "priority": 50,  # Higher precedence
                        }
                    ],
                ]

                with patch.object(service, "_deploy_agent_file") as mock_deploy:
                    mock_deploy.return_value = True
                    result = service.deploy_all_agents()

        # Verify conflict resolution
        assert result["conflicts_resolved"] == 1
        assert result["deployed_agents"] == 1

        # Verify higher priority agent was chosen (lower priority number)
        assert result["agents"][0]["source"] == "owner2/repo2"
        assert result["agents"][0]["priority"] == 50


class TestDeployAgent:
    """Test deploy_agent method."""

    def test_deploy_agent_success(self, service, mock_deployment_dir):
        """Test deploying a specific agent."""
        with patch.object(service, "_discover_agents_in_repo") as mock_discover:
            mock_discover.return_value = [
                {
                    "agent_id": "engineer",
                    "metadata": {"name": "Engineer"},
                    "source_file": "/fake/path/engineer.md",
                    "repository": "owner1/repo1/agents",
                    "priority": 100,
                }
            ]

            with patch.object(service, "_deploy_agent_file") as mock_deploy:
                mock_deploy.return_value = True
                result = service.deploy_agent("engineer")

        assert result["deployed"] is True
        assert result["agent_name"] == "Engineer"
        assert result["source"] == "owner1/repo1/agents"

    def test_deploy_agent_not_found(self, service):
        """Test deploying non-existent agent."""
        with patch.object(service, "_discover_agents_in_repo") as mock_discover:
            mock_discover.return_value = []

            result = service.deploy_agent("nonexistent")

        assert result["deployed"] is False
        assert "not found" in result["error"].lower()

    def test_deploy_agent_with_specific_source(self, service, mock_config):
        """Test deploying from specific source repository."""
        with patch.object(service, "_discover_agents_in_repo") as mock_discover:
            mock_discover.return_value = [
                {
                    "agent_id": "engineer",
                    "metadata": {"name": "Engineer"},
                    "source_file": "/fake/path/engineer.md",
                    "repository": "owner1/repo1/agents",
                    "priority": 100,
                }
            ]

            with patch.object(service, "_deploy_agent_file") as mock_deploy:
                mock_deploy.return_value = True
                result = service.deploy_agent(
                    "engineer", source_repo="owner1/repo1/agents"
                )

        assert result["deployed"] is True

    def test_deploy_agent_source_not_found(self, service):
        """Test deploying with non-existent source."""
        result = service.deploy_agent("engineer", source_repo="nonexistent/repo")

        assert result["deployed"] is False
        assert "not found" in result["error"].lower()


class TestListAvailableAgents:
    """Test list_available_agents method."""

    def test_list_available_agents_all(self, service):
        """Test listing all available agents."""
        with patch.object(service, "_discover_agents_in_repo") as mock_discover:
            mock_discover.side_effect = [
                [
                    {
                        "agent_id": "engineer",
                        "metadata": {
                            "name": "Engineer",
                            "description": "Python specialist",
                        },
                        "model": "sonnet",
                        "version": "1.0.0",
                        "repository": "owner1/repo1/agents",
                        "priority": 100,
                    }
                ],
                [
                    {
                        "agent_id": "research",
                        "metadata": {
                            "name": "Research",
                            "description": "Research agent",
                        },
                        "model": "opus",
                        "version": "1.0.0",
                        "repository": "owner2/repo2",
                        "priority": 50,
                    }
                ],
            ]

            result = service.list_available_agents()

        assert len(result) == 2
        assert result[0]["name"] == "Engineer"
        assert result[0]["source"] == "owner1/repo1/agents"
        assert result[1]["name"] == "Research"
        assert result[1]["source"] == "owner2/repo2"

    def test_list_available_agents_filtered(self, service, mock_config):
        """Test listing agents from specific source."""
        # Override config to return specific repo
        specific_repo = GitRepository(
            url="https://github.com/owner1/repo1",
            subdirectory="agents",
            enabled=True,
            priority=100,
        )
        mock_config.get_enabled_repositories.return_value = [specific_repo]

        with patch.object(service, "_discover_agents_in_repo") as mock_discover:
            mock_discover.return_value = [
                {
                    "agent_id": "engineer",
                    "metadata": {"name": "Engineer", "description": "Test"},
                    "model": "sonnet",
                    "version": "1.0.0",
                    "repository": "owner1/repo1/agents",
                    "priority": 100,
                }
            ]

            result = service.list_available_agents(source_repo="owner1/repo1/agents")

        assert len(result) == 1
        assert result[0]["source"] == "owner1/repo1/agents"


class TestGetDeployedAgents:
    """Test get_deployed_agents method."""

    def test_get_deployed_agents(self, service, mock_deployment_dir):
        """Test listing deployed agents."""
        # Create deployed agent files
        (mock_deployment_dir / "engineer.md").write_text("# Engineer\n\nTest")
        (mock_deployment_dir / "research.md").write_text("# Research Agent\n\nTest")

        result = service.get_deployed_agents()

        assert len(result) == 2
        assert any(a["agent_id"] == "engineer" for a in result)
        assert any(a["agent_id"] == "research" for a in result)

    def test_get_deployed_agents_empty(self, service, mock_deployment_dir):
        """Test with no deployed agents."""
        result = service.get_deployed_agents()
        assert len(result) == 0


class TestRemoveAgent:
    """Test remove_agent method."""

    def test_remove_agent_success(self, service, mock_deployment_dir):
        """Test successful agent removal."""
        agent_file = mock_deployment_dir / "engineer.md"
        agent_file.write_text("# Engineer\n\nTest")

        result = service.remove_agent("engineer")

        assert result is True
        assert not agent_file.exists()

    def test_remove_agent_not_found(self, service):
        """Test removing non-existent agent."""
        result = service.remove_agent("nonexistent")
        assert result is False


class TestSyncSources:
    """Test sync_sources method."""

    def test_sync_sources_all(self, service):
        """Test syncing all sources."""
        with patch.object(
            service.git_source_manager, "sync_all_repositories"
        ) as mock_sync:
            mock_sync.return_value = {
                "owner1/repo1/agents": {"synced": True, "files_updated": 2},
                "owner2/repo2": {"synced": True, "files_updated": 1},
            }

            result = service.sync_sources(force=False)

        assert len(result) == 2
        assert result["owner1/repo1/agents"]["synced"] is True

    def test_sync_sources_specific_repo(self, service, mock_config):
        """Test syncing specific repository."""
        specific_repo = GitRepository(
            url="https://github.com/owner1/repo1",
            subdirectory="agents",
            enabled=True,
            priority=100,
        )
        mock_config.get_enabled_repositories.return_value = [specific_repo]

        with patch.object(
            service.git_source_manager, "sync_all_repositories"
        ) as mock_sync:
            mock_sync.return_value = {
                "owner1/repo1/agents": {"synced": True, "files_updated": 2},
            }

            result = service.sync_sources(repo_identifier="owner1/repo1/agents")

        assert len(result) == 1
        assert "owner1/repo1/agents" in result

    def test_sync_sources_repo_not_found(self, service, mock_config):
        """Test syncing non-existent repository."""
        mock_config.get_enabled_repositories.return_value = []

        result = service.sync_sources(repo_identifier="nonexistent/repo")

        assert result["nonexistent/repo"]["synced"] is False
        assert "not found" in result["nonexistent/repo"]["error"].lower()


class TestResolveConflicts:
    """Test _resolve_conflicts method."""

    def test_resolve_conflicts_no_conflicts(self, service):
        """Test with no conflicts."""
        agents = [
            {
                "metadata": {"name": "Engineer"},
                "priority": 100,
                "repository": "owner1/repo1",
            },
            {
                "metadata": {"name": "Research"},
                "priority": 50,
                "repository": "owner2/repo2",
            },
        ]

        resolved, count = service._resolve_conflicts(agents)

        assert len(resolved) == 2
        assert count == 0

    def test_resolve_conflicts_with_conflicts(self, service):
        """Test priority-based conflict resolution."""
        agents = [
            {
                "metadata": {"name": "Engineer"},
                "priority": 100,
                "repository": "owner1/repo1",
            },
            {
                "metadata": {"name": "Engineer"},
                "priority": 50,  # Higher precedence (lower number)
                "repository": "owner2/repo2",
            },
        ]

        resolved, count = service._resolve_conflicts(agents)

        assert len(resolved) == 1
        assert count == 1
        assert resolved[0]["repository"] == "owner2/repo2"  # Lower priority wins
        assert resolved[0]["priority"] == 50


class TestDeployAgentFile:
    """Test _deploy_agent_file method."""

    def test_deploy_agent_file_success(self, service, mock_deployment_dir, tmp_path):
        """Test successful file deployment."""
        # Create source file
        source_file = tmp_path / "engineer.md"
        source_file.write_text("# Engineer\n\nTest content")

        agent = {
            "agent_id": "engineer",
            "source_file": str(source_file),
        }

        result = service._deploy_agent_file(agent)

        assert result is True
        assert (mock_deployment_dir / "engineer.md").exists()
        assert (
            mock_deployment_dir / "engineer.md"
        ).read_text() == "# Engineer\n\nTest content"

    def test_deploy_agent_file_source_not_found(self, service):
        """Test deployment with missing source file."""
        agent = {
            "agent_id": "engineer",
            "source_file": "/nonexistent/path/engineer.md",
        }

        result = service._deploy_agent_file(agent)

        assert result is False


class TestErrorHandling:
    """Test error handling in various scenarios."""

    def test_deploy_all_agents_sync_failure(self, service):
        """Test handling of sync failures."""
        with patch.object(
            service.git_source_manager, "sync_all_repositories"
        ) as mock_sync:
            mock_sync.return_value = {
                "owner1/repo1/agents": {"synced": False, "error": "Network error"},
            }

            with patch.object(service, "_discover_agents_in_repo") as mock_discover:
                mock_discover.return_value = []

                result = service.deploy_all_agents()

        # Should continue despite sync failure
        assert result["synced_repos"] == 0
        assert result["deployed_agents"] == 0

    def test_deploy_agent_discovery_failure(self, service):
        """Test handling of discovery failures."""
        with patch.object(service, "_discover_agents_in_repo") as mock_discover:
            mock_discover.side_effect = Exception("Discovery failed")

            result = service.deploy_agent("engineer")

        assert result["deployed"] is False
        assert "not found" in result["error"].lower()
