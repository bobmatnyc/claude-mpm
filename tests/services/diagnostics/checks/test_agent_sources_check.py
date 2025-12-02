"""
Tests for AgentSourcesCheck diagnostic.

WHY: Verify that the agent sources check correctly identifies configuration
issues, validates sources, and provides actionable feedback.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
import yaml

from src.claude_mpm.core.enums import OperationResult, ValidationSeverity
from src.claude_mpm.services.diagnostics.checks.agent_sources_check import \
    AgentSourcesCheck


@pytest.fixture
def config_dir():
    """Create temporary config directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / ".claude-mpm" / "config"
        config_path.mkdir(parents=True)
        yield config_path


@pytest.fixture
def cache_dir():
    """Create temporary cache directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / ".claude-mpm" / "cache" / "remote-agents"
        cache_path.mkdir(parents=True)
        yield cache_path


@pytest.fixture
def mock_config_path(config_dir):
    """Mock config path to use temporary directory."""
    config_file = config_dir / "agent_sources.yaml"
    with patch(
        "src.claude_mpm.services.diagnostics.checks.agent_sources_check.Path.home"
    ) as mock_home:
        mock_home.return_value = config_dir.parent.parent
        yield config_file


@pytest.fixture
def mock_cache_path(cache_dir):
    """Mock cache path to use temporary directory."""
    with patch(
        "src.claude_mpm.services.diagnostics.checks.agent_sources_check.Path.home"
    ) as mock_home:
        mock_home.return_value = cache_dir.parent.parent.parent
        yield cache_dir


class TestAgentSourcesCheck:
    """Test AgentSourcesCheck class."""

    def test_should_run_always_returns_true(self):
        """Check should always run."""
        check = AgentSourcesCheck(verbose=False)
        assert check.should_run() is True

    def test_name_property(self):
        """Check has correct name."""
        check = AgentSourcesCheck(verbose=False)
        assert check.name == "agent_sources_check"

    def test_category_property(self):
        """Check has correct category."""
        check = AgentSourcesCheck(verbose=False)
        assert check.category == "Agent Sources"

    def test_config_file_missing(self, mock_config_path):
        """Test when configuration file doesn't exist."""
        check = AgentSourcesCheck(verbose=False)
        result = check.run()

        assert result.status == ValidationSeverity.ERROR
        assert "not configured" in result.message.lower()
        assert result.fix_command is not None
        assert "source add" in result.fix_command

    def test_config_file_exists(self, mock_config_path):
        """Test when configuration file exists."""
        # Create valid config file
        config_data = {
            "disable_system_repo": False,
            "repositories": [],
        }
        with open(mock_config_path, "w") as f:
            yaml.safe_dump(config_data, f)

        check = AgentSourcesCheck(verbose=False)
        result = check._check_config_file()

        assert result.status == OperationResult.SUCCESS
        assert "Found" in result.message

    def test_config_invalid_yaml(self, mock_config_path):
        """Test when configuration file has invalid YAML."""
        # Create invalid YAML
        with open(mock_config_path, "w") as f:
            f.write("invalid: yaml: content:\n  - broken\n  indentation")

        check = AgentSourcesCheck(verbose=False)
        result = check._check_config_valid()

        assert result.status == ValidationSeverity.ERROR
        assert "Invalid YAML" in result.message

    def test_config_valid_yaml(self, mock_config_path):
        """Test when configuration file has valid YAML."""
        config_data = {
            "disable_system_repo": False,
            "repositories": [],
        }
        with open(mock_config_path, "w") as f:
            yaml.safe_dump(config_data, f)

        check = AgentSourcesCheck(verbose=False)
        result = check._check_config_valid()

        assert result.status == OperationResult.SUCCESS
        assert "valid" in result.message.lower()

    def test_sources_configured_none(self):
        """Test when no sources are configured."""
        from src.claude_mpm.config.agent_sources import \
            AgentSourceConfiguration

        config = AgentSourceConfiguration(disable_system_repo=True, repositories=[])
        check = AgentSourcesCheck(verbose=False)
        result = check._check_sources_configured(config)

        assert result.status == ValidationSeverity.WARNING
        assert "No agent sources" in result.message

    def test_sources_configured_all_disabled(self):
        """Test when sources configured but all disabled."""
        from src.claude_mpm.config.agent_sources import \
            AgentSourceConfiguration
        from src.claude_mpm.models.git_repository import GitRepository

        repo = GitRepository(
            url="https://github.com/test/repo", enabled=False, priority=100
        )
        config = AgentSourceConfiguration(disable_system_repo=True, repositories=[repo])

        check = AgentSourcesCheck(verbose=False)
        result = check._check_sources_configured(config)

        assert result.status == ValidationSeverity.WARNING
        assert "all disabled" in result.message.lower()

    def test_sources_configured_some_enabled(self):
        """Test when sources are properly configured."""
        from src.claude_mpm.config.agent_sources import \
            AgentSourceConfiguration
        from src.claude_mpm.models.git_repository import GitRepository

        repo = GitRepository(
            url="https://github.com/test/repo", enabled=True, priority=100
        )
        config = AgentSourceConfiguration(
            disable_system_repo=False, repositories=[repo]
        )

        check = AgentSourcesCheck(verbose=False)
        result = check._check_sources_configured(config)

        assert result.status == OperationResult.SUCCESS
        assert "2 enabled" in result.message  # System repo + custom repo

    @patch("urllib.request.urlopen")
    def test_repo_accessible_success(self, mock_urlopen):
        """Test repository accessibility check - success."""
        mock_response = Mock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        check = AgentSourcesCheck(verbose=False)
        result = check._check_repo_accessible(
            "https://github.com/test/repo", "test/repo"
        )

        assert result.status == OperationResult.SUCCESS
        assert "Accessible" in result.message

    @patch("urllib.request.urlopen")
    def test_repo_accessible_http_error(self, mock_urlopen):
        """Test repository accessibility check - HTTP error."""
        from urllib.error import HTTPError

        mock_urlopen.side_effect = HTTPError("url", 404, "Not Found", {}, None)

        check = AgentSourcesCheck(verbose=False)
        result = check._check_repo_accessible(
            "https://github.com/test/repo", "test/repo"
        )

        assert result.status == ValidationSeverity.WARNING
        assert "404" in result.message

    @patch("urllib.request.urlopen")
    def test_repo_accessible_network_error(self, mock_urlopen):
        """Test repository accessibility check - network error."""
        from urllib.error import URLError

        mock_urlopen.side_effect = URLError("Network unreachable")

        check = AgentSourcesCheck(verbose=False)
        result = check._check_repo_accessible(
            "https://github.com/test/repo", "test/repo"
        )

        assert result.status == ValidationSeverity.WARNING
        assert "Network error" in result.message

    def test_cache_directory_missing(self, mock_cache_path):
        """Test when cache directory doesn't exist."""
        # Remove the cache directory
        mock_cache_path.rmdir()

        check = AgentSourcesCheck(verbose=False)
        result = check._check_cache_directory()

        assert result.status == ValidationSeverity.WARNING
        assert "does not exist" in result.message

    def test_cache_directory_exists(self, mock_cache_path):
        """Test when cache directory exists and is writable."""
        check = AgentSourcesCheck(verbose=False)
        result = check._check_cache_directory()

        assert result.status == OperationResult.SUCCESS
        assert "healthy" in result.message.lower()

    def test_cache_directory_not_writable(self, mock_cache_path):
        """Test when cache directory is not writable."""
        # Make directory read-only
        import os

        os.chmod(mock_cache_path, 0o444)

        check = AgentSourcesCheck(verbose=False)
        result = check._check_cache_directory()

        assert result.status == ValidationSeverity.ERROR
        assert "not writable" in result.message.lower()

        # Restore permissions for cleanup
        os.chmod(mock_cache_path, 0o755)

    def test_priority_conflicts_none(self):
        """Test when there are no priority conflicts."""
        from src.claude_mpm.config.agent_sources import \
            AgentSourceConfiguration
        from src.claude_mpm.models.git_repository import GitRepository

        repo1 = GitRepository(
            url="https://github.com/test/repo1", enabled=True, priority=10
        )
        repo2 = GitRepository(
            url="https://github.com/test/repo2", enabled=True, priority=20
        )
        config = AgentSourceConfiguration(
            disable_system_repo=True, repositories=[repo1, repo2]
        )

        check = AgentSourcesCheck(verbose=False)
        result = check._check_priority_conflicts(config)

        assert result.status == OperationResult.SUCCESS
        assert "No priority conflicts" in result.message

    def test_priority_conflicts_detected(self):
        """Test when priority conflicts are detected."""
        from src.claude_mpm.config.agent_sources import \
            AgentSourceConfiguration
        from src.claude_mpm.models.git_repository import GitRepository

        repo1 = GitRepository(
            url="https://github.com/test/repo1", enabled=True, priority=100
        )
        repo2 = GitRepository(
            url="https://github.com/test/repo2", enabled=True, priority=100
        )
        config = AgentSourceConfiguration(
            disable_system_repo=False, repositories=[repo1, repo2]
        )

        check = AgentSourcesCheck(verbose=False)
        result = check._check_priority_conflicts(config)

        assert result.status == ValidationSeverity.INFO
        assert "conflict" in result.message.lower()
        assert result.details["conflict_count"] > 0

    def test_priority_conflicts_no_repos(self):
        """Test priority conflicts with no repos."""
        from src.claude_mpm.config.agent_sources import \
            AgentSourceConfiguration

        config = AgentSourceConfiguration(disable_system_repo=True, repositories=[])

        check = AgentSourcesCheck(verbose=False)
        result = check._check_priority_conflicts(config)

        # Should return None for <2 repos
        assert result is None

    @patch(
        "src.claude_mpm.services.agents.single_tier_deployment_service.SingleTierDeploymentService"
    )
    def test_agents_discovered_success(self, mock_service_class):
        """Test successful agent discovery."""
        from src.claude_mpm.config.agent_sources import \
            AgentSourceConfiguration

        # Mock service to return agents
        mock_service = Mock()
        mock_service.list_available_agents.return_value = [
            {"name": "Engineer", "source": "test/repo", "agent_id": "engineer"},
            {"name": "Research", "source": "test/repo", "agent_id": "research"},
        ]
        mock_service_class.return_value = mock_service

        config = AgentSourceConfiguration(disable_system_repo=False, repositories=[])

        check = AgentSourcesCheck(verbose=False)
        result = check._check_agents_discovered(config)

        assert result.status == OperationResult.SUCCESS
        assert result.details["total_agents"] == 2
        assert "Engineer" in result.details["agent_names"]

    @patch(
        "src.claude_mpm.services.agents.single_tier_deployment_service.SingleTierDeploymentService"
    )
    def test_agents_discovered_none(self, mock_service_class):
        """Test when no agents are discovered."""
        from src.claude_mpm.config.agent_sources import \
            AgentSourceConfiguration

        # Mock service to return no agents
        mock_service = Mock()
        mock_service.list_available_agents.return_value = []
        mock_service_class.return_value = mock_service

        config = AgentSourceConfiguration(disable_system_repo=False, repositories=[])

        check = AgentSourcesCheck(verbose=False)
        result = check._check_agents_discovered(config)

        assert result.status == ValidationSeverity.WARNING
        assert "No agents discovered" in result.message
        assert result.fix_command is not None

    @patch(
        "src.claude_mpm.services.agents.single_tier_deployment_service.SingleTierDeploymentService"
    )
    def test_agents_discovered_error(self, mock_service_class):
        """Test when agent discovery fails."""
        from src.claude_mpm.config.agent_sources import \
            AgentSourceConfiguration

        # Mock service to raise exception
        mock_service = Mock()
        mock_service.list_available_agents.side_effect = Exception("Discovery failed")
        mock_service_class.return_value = mock_service

        config = AgentSourceConfiguration(disable_system_repo=False, repositories=[])

        check = AgentSourcesCheck(verbose=False)
        result = check._check_agents_discovered(config)

        assert result.status == ValidationSeverity.WARNING
        assert "failed" in result.message.lower()

    def test_full_run_with_missing_config(self, mock_config_path):
        """Test full check run with missing configuration."""
        check = AgentSourcesCheck(verbose=False)
        result = check.run()

        assert result.status == ValidationSeverity.ERROR
        assert result.category == "Agent Sources"
        assert result.fix_command is not None

    def test_full_run_with_valid_config(self, mock_config_path, mock_cache_path):
        """Test full check run with valid configuration."""
        # Create valid config
        config_data = {
            "disable_system_repo": False,
            "repositories": [
                {
                    "url": "https://github.com/test/repo",
                    "enabled": True,
                    "priority": 50,
                }
            ],
        }
        with open(mock_config_path, "w") as f:
            yaml.safe_dump(config_data, f)

        # Mock repository accessibility and agent discovery
        with patch("urllib.request.urlopen") as mock_urlopen, patch(
            "src.claude_mpm.services.agents.single_tier_deployment_service.SingleTierDeploymentService"
        ) as mock_service_class, patch(
            "src.claude_mpm.services.diagnostics.checks.agent_sources_check.Path.home"
        ) as mock_home:
            # Set home to use temp directory
            mock_home.return_value = mock_config_path.parent.parent.parent

            # Mock successful HTTP requests
            mock_response = Mock()
            mock_response.status = 200
            mock_urlopen.return_value.__enter__.return_value = mock_response

            # Mock successful agent discovery
            mock_service = Mock()
            mock_service.list_available_agents.return_value = [
                {"name": "Engineer", "source": "test/repo", "agent_id": "engineer"}
            ]
            mock_service_class.return_value = mock_service

            check = AgentSourcesCheck(verbose=False)
            result = check.run()

            # Should pass all checks
            assert result.status in (
                OperationResult.SUCCESS,
                ValidationSeverity.WARNING,
            )
            assert result.category == "Agent Sources"

    def test_verbose_mode_includes_sub_results(self, mock_config_path):
        """Test that verbose mode includes sub-results."""
        config_data = {
            "disable_system_repo": False,
            "repositories": [],
        }
        with open(mock_config_path, "w") as f:
            yaml.safe_dump(config_data, f)

        check = AgentSourcesCheck(verbose=True)
        result = check.run()

        # Verbose mode should include sub_results
        assert len(result.sub_results) > 0

    def test_non_verbose_mode_excludes_sub_results(self, mock_config_path):
        """Test that non-verbose mode excludes sub-results."""
        config_data = {
            "disable_system_repo": False,
            "repositories": [],
        }
        with open(mock_config_path, "w") as f:
            yaml.safe_dump(config_data, f)

        check = AgentSourcesCheck(verbose=False)
        result = check.run()

        # Non-verbose mode should exclude sub_results
        assert len(result.sub_results) == 0

    def test_exception_handling(self):
        """Test that exceptions are caught and reported."""
        check = AgentSourcesCheck(verbose=False)

        # Force an exception by mocking Path.home() to raise
        with patch(
            "src.claude_mpm.services.diagnostics.checks.agent_sources_check.Path.home"
        ) as mock_home:
            mock_home.side_effect = Exception("Forced error")

            result = check.run()

            assert result.status == ValidationSeverity.ERROR
            assert "failed" in result.message.lower()
            assert "error" in result.details
