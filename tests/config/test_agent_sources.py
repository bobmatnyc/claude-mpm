"""Unit tests for AgentSourceConfiguration."""

import pytest
from pathlib import Path
import tempfile
import yaml
from src.claude_mpm.config.agent_sources import AgentSourceConfiguration
from src.claude_mpm.models.git_repository import GitRepository


class TestAgentSourceConfigurationCreation:
    """Test AgentSourceConfiguration creation."""

    def test_create_default_configuration(self):
        """Test creating configuration with defaults."""
        config = AgentSourceConfiguration()

        assert config.disable_system_repo is False
        assert len(config.repositories) == 0

    def test_create_with_custom_repos(self):
        """Test creating configuration with custom repositories."""
        repo = GitRepository(url="https://github.com/owner/repo")
        config = AgentSourceConfiguration(repositories=[repo])

        assert len(config.repositories) == 1
        assert config.repositories[0].url == "https://github.com/owner/repo"

    def test_create_with_system_repo_disabled(self):
        """Test creating configuration with system repo disabled."""
        config = AgentSourceConfiguration(disable_system_repo=True)

        assert config.disable_system_repo is True
        assert config.get_system_repo() is None


class TestAgentSourceConfigurationSystemRepo:
    """Test system repository handling."""

    def test_get_system_repo_enabled(self):
        """Test getting system repository when enabled."""
        config = AgentSourceConfiguration(disable_system_repo=False)
        system_repo = config.get_system_repo()

        assert system_repo is not None
        assert "bobmatnyc/claude-mpm-agents" in system_repo.url
        assert system_repo.enabled is True
        assert system_repo.priority == 100

    def test_get_system_repo_disabled(self):
        """Test getting system repository when disabled."""
        config = AgentSourceConfiguration(disable_system_repo=True)
        system_repo = config.get_system_repo()

        assert system_repo is None

    def test_get_enabled_repositories_includes_system(self):
        """Test enabled repositories includes system repo."""
        config = AgentSourceConfiguration(disable_system_repo=False)
        enabled = config.get_enabled_repositories()

        # Should include system repo
        assert len(enabled) >= 1
        assert any("bobmatnyc/claude-mpm-agents" in r.url for r in enabled)

    def test_get_enabled_repositories_excludes_system(self):
        """Test enabled repositories excludes system when disabled."""
        config = AgentSourceConfiguration(disable_system_repo=True)
        enabled = config.get_enabled_repositories()

        # Should not include system repo
        assert not any("bobmatnyc/claude-mpm-agents" in r.url for r in enabled)

    def test_get_enabled_repositories_sorted_by_priority(self):
        """Test enabled repositories are sorted by priority."""
        repo1 = GitRepository(url="https://github.com/owner/repo1", priority=200)
        repo2 = GitRepository(url="https://github.com/owner/repo2", priority=50)
        repo3 = GitRepository(url="https://github.com/owner/repo3", priority=100)

        config = AgentSourceConfiguration(
            disable_system_repo=True,
            repositories=[repo1, repo2, repo3]
        )
        enabled = config.get_enabled_repositories()

        # Should be sorted: 50, 100, 200 (lower priority first)
        assert enabled[0].priority == 50
        assert enabled[1].priority == 100
        assert enabled[2].priority == 200


class TestAgentSourceConfigurationRepositoryManagement:
    """Test repository management operations."""

    def test_add_repository(self):
        """Test adding a repository."""
        config = AgentSourceConfiguration()
        repo = GitRepository(url="https://github.com/owner/repo")

        config.add_repository(repo)

        assert len(config.repositories) == 1
        assert config.repositories[0].url == "https://github.com/owner/repo"

    def test_add_multiple_repositories(self):
        """Test adding multiple repositories."""
        config = AgentSourceConfiguration()

        repo1 = GitRepository(url="https://github.com/owner/repo1")
        repo2 = GitRepository(url="https://github.com/owner/repo2")

        config.add_repository(repo1)
        config.add_repository(repo2)

        assert len(config.repositories) == 2

    def test_remove_repository_by_identifier(self):
        """Test removing a repository by identifier."""
        repo = GitRepository(
            url="https://github.com/owner/repo",
            subdirectory="agents"
        )
        config = AgentSourceConfiguration(repositories=[repo])

        removed = config.remove_repository("owner/repo/agents")

        assert removed is True
        assert len(config.repositories) == 0

    def test_remove_repository_not_found(self):
        """Test removing non-existent repository returns False."""
        config = AgentSourceConfiguration()

        removed = config.remove_repository("owner/nonexistent")

        assert removed is False

    def test_remove_repository_case_sensitive(self):
        """Test repository removal is case-sensitive."""
        repo = GitRepository(url="https://github.com/owner/repo")
        config = AgentSourceConfiguration(repositories=[repo])

        # Try with different case
        removed = config.remove_repository("Owner/Repo")

        # Should not remove (case mismatch)
        assert removed is False
        assert len(config.repositories) == 1


class TestAgentSourceConfigurationDisabledRepos:
    """Test handling of disabled repositories."""

    def test_get_enabled_repositories_excludes_disabled(self):
        """Test disabled repositories are excluded."""
        repo1 = GitRepository(url="https://github.com/owner/repo1", enabled=True)
        repo2 = GitRepository(url="https://github.com/owner/repo2", enabled=False)
        repo3 = GitRepository(url="https://github.com/owner/repo3", enabled=True)

        config = AgentSourceConfiguration(
            disable_system_repo=True,
            repositories=[repo1, repo2, repo3]
        )
        enabled = config.get_enabled_repositories()

        # Should only include enabled repos
        assert len(enabled) == 2
        assert repo1 in enabled
        assert repo2 not in enabled
        assert repo3 in enabled


class TestAgentSourceConfigurationYAMLPersistence:
    """Test YAML loading and saving."""

    def test_save_to_yaml(self):
        """Test saving configuration to YAML file."""
        repo = GitRepository(
            url="https://github.com/owner/repo",
            subdirectory="agents",
            priority=50
        )
        config = AgentSourceConfiguration(
            disable_system_repo=False,
            repositories=[repo]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "agent_sources.yaml"
            config.save(config_path)

            # Verify file exists and is valid YAML
            assert config_path.exists()

            with open(config_path) as f:
                data = yaml.safe_load(f)

            assert "disable_system_repo" in data
            assert "repositories" in data
            assert len(data["repositories"]) == 1

    def test_load_from_yaml(self):
        """Test loading configuration from YAML file."""
        yaml_content = """
disable_system_repo: false
repositories:
  - url: https://github.com/owner/repo1
    subdirectory: agents
    enabled: true
    priority: 50
  - url: https://github.com/owner/repo2
    subdirectory: tools/agents
    enabled: false
    priority: 100
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "agent_sources.yaml"
            config_path.write_text(yaml_content)

            config = AgentSourceConfiguration.load(config_path)

            assert config.disable_system_repo is False
            assert len(config.repositories) == 2
            assert config.repositories[0].priority == 50
            assert config.repositories[1].enabled is False

    def test_load_from_nonexistent_file(self):
        """Test loading from non-existent file returns defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "nonexistent.yaml"

            config = AgentSourceConfiguration.load(config_path)

            # Should return default configuration
            assert config.disable_system_repo is False
            assert len(config.repositories) == 0

    def test_load_with_default_path(self):
        """Test loading with default path (~/.claude-mpm/config/agent_sources.yaml)."""
        # This will load from default location or return defaults
        config = AgentSourceConfiguration.load()

        assert config is not None
        assert isinstance(config, AgentSourceConfiguration)

    def test_save_and_load_roundtrip(self):
        """Test save and load roundtrip preserves data."""
        repo1 = GitRepository(
            url="https://github.com/owner/repo1",
            subdirectory="agents",
            priority=50,
            enabled=True
        )
        repo2 = GitRepository(
            url="https://github.com/owner/repo2",
            subdirectory="tools",
            priority=100,
            enabled=False
        )

        original = AgentSourceConfiguration(
            disable_system_repo=True,
            repositories=[repo1, repo2]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"

            # Save
            original.save(config_path)

            # Load
            loaded = AgentSourceConfiguration.load(config_path)

            # Verify
            assert loaded.disable_system_repo == original.disable_system_repo
            assert len(loaded.repositories) == len(original.repositories)
            assert loaded.repositories[0].url == original.repositories[0].url
            assert loaded.repositories[0].priority == original.repositories[0].priority
            assert loaded.repositories[1].enabled == original.repositories[1].enabled


class TestAgentSourceConfigurationValidation:
    """Test configuration validation."""

    def test_validate_all_repositories(self):
        """Test validation checks all repositories."""
        valid_repo = GitRepository(url="https://github.com/owner/repo1")
        invalid_repo = GitRepository(url="")  # Invalid empty URL

        config = AgentSourceConfiguration(repositories=[valid_repo, invalid_repo])

        errors = config.validate()

        # Should have errors from invalid repository
        assert len(errors) > 0
        assert any("URL" in error for error in errors)

    def test_validate_duplicate_identifiers(self):
        """Test validation detects duplicate repository identifiers."""
        repo1 = GitRepository(
            url="https://github.com/owner/repo",
            subdirectory="agents"
        )
        repo2 = GitRepository(
            url="https://github.com/owner/repo",
            subdirectory="agents"
        )

        config = AgentSourceConfiguration(repositories=[repo1, repo2])

        errors = config.validate()

        # Should detect duplicate
        assert len(errors) > 0
        assert any("duplicate" in error.lower() for error in errors)

    def test_validate_success(self):
        """Test validation passes for valid configuration."""
        repo = GitRepository(
            url="https://github.com/owner/repo",
            subdirectory="agents",
            priority=50
        )

        config = AgentSourceConfiguration(repositories=[repo])

        errors = config.validate()

        assert len(errors) == 0
