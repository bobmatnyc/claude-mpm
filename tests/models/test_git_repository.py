"""Unit tests for GitRepository model."""

import pytest
from pathlib import Path
from datetime import datetime
from src.claude_mpm.models.git_repository import GitRepository


class TestGitRepositoryValidation:
    """Test GitRepository validation."""

    def test_create_with_minimal_params(self):
        """Test creating repository with minimal required parameters."""
        repo = GitRepository(url="https://github.com/owner/repo")

        assert repo.url == "https://github.com/owner/repo"
        assert repo.subdirectory is None
        assert repo.enabled is True
        assert repo.priority == 100
        assert repo.last_synced is None
        assert repo.etag is None

    def test_create_with_all_params(self):
        """Test creating repository with all parameters."""
        now = datetime.now()
        repo = GitRepository(
            url="https://github.com/owner/repo",
            subdirectory="agents/backend",
            enabled=False,
            priority=50,
            last_synced=now,
            etag="abc123"
        )

        assert repo.url == "https://github.com/owner/repo"
        assert repo.subdirectory == "agents/backend"
        assert repo.enabled is False
        assert repo.priority == 50
        assert repo.last_synced == now
        assert repo.etag == "abc123"

    def test_validation_empty_url(self):
        """Test validation rejects empty URL."""
        errors = GitRepository(url="").validate()

        assert len(errors) > 0
        assert any("URL" in error for error in errors)

    def test_validation_invalid_url_format(self):
        """Test validation rejects invalid URL formats."""
        invalid_urls = [
            "not-a-url",
            "ftp://github.com/owner/repo",
            "github.com/owner/repo",  # Missing protocol
        ]

        for url in invalid_urls:
            repo = GitRepository(url=url)
            errors = repo.validate()
            assert len(errors) > 0, f"Expected validation error for: {url}"

    def test_validation_negative_priority(self):
        """Test validation rejects negative priority."""
        repo = GitRepository(
            url="https://github.com/owner/repo",
            priority=-1
        )
        errors = repo.validate()

        assert len(errors) > 0
        assert any("priority" in error.lower() for error in errors)

    def test_validation_priority_too_high(self):
        """Test validation warns about priority > 1000."""
        repo = GitRepository(
            url="https://github.com/owner/repo",
            priority=1001
        )
        errors = repo.validate()

        # Warning, not error
        assert len(errors) > 0
        assert any("priority" in error.lower() for error in errors)

    def test_validation_subdirectory_absolute_path(self):
        """Test validation rejects absolute subdirectory paths."""
        repo = GitRepository(
            url="https://github.com/owner/repo",
            subdirectory="/absolute/path"
        )
        errors = repo.validate()

        assert len(errors) > 0
        assert any("subdirectory" in error.lower() for error in errors)

    def test_validation_success(self):
        """Test validation passes for valid repository."""
        repo = GitRepository(
            url="https://github.com/owner/repo",
            subdirectory="agents",
            priority=50
        )
        errors = repo.validate()

        assert len(errors) == 0


class TestGitRepositoryIdentifier:
    """Test GitRepository identifier generation."""

    def test_identifier_with_subdirectory(self):
        """Test identifier includes subdirectory."""
        repo = GitRepository(
            url="https://github.com/owner/repo",
            subdirectory="agents/backend"
        )

        assert repo.identifier == "owner/repo/agents/backend"

    def test_identifier_without_subdirectory(self):
        """Test identifier without subdirectory."""
        repo = GitRepository(url="https://github.com/owner/repo")

        assert repo.identifier == "owner/repo"

    def test_identifier_extracts_from_url(self):
        """Test identifier correctly parses GitHub URLs."""
        test_cases = [
            ("https://github.com/owner/repo", "owner/repo"),
            ("https://github.com/owner/repo.git", "owner/repo"),
            ("https://github.com/owner-name/repo-name", "owner-name/repo-name"),
        ]

        for url, expected_base in test_cases:
            repo = GitRepository(url=url)
            assert repo.identifier == expected_base


class TestGitRepositoryCachePath:
    """Test GitRepository cache path generation."""

    def test_cache_path_default_location(self):
        """Test cache path uses default location."""
        repo = GitRepository(
            url="https://github.com/owner/repo",
            subdirectory="agents"
        )
        cache_path = repo.cache_path

        # Should be ~/.claude-mpm/cache/remote-agents/owner/repo/agents/
        assert cache_path.parts[-5:] == ("cache", "remote-agents", "owner", "repo", "agents")
        assert cache_path.is_absolute()

    def test_cache_path_without_subdirectory(self):
        """Test cache path without subdirectory."""
        repo = GitRepository(url="https://github.com/owner/repo")
        cache_path = repo.cache_path

        # Should be ~/.claude-mpm/cache/remote-agents/owner/repo/
        assert cache_path.parts[-4:] == ("cache", "remote-agents", "owner", "repo")

    def test_cache_path_with_nested_subdirectory(self):
        """Test cache path with nested subdirectory."""
        repo = GitRepository(
            url="https://github.com/owner/repo",
            subdirectory="tools/agents/backend"
        )
        cache_path = repo.cache_path

        assert cache_path.parts[-7:] == ("cache", "remote-agents", "owner", "repo", "tools", "agents", "backend")

    def test_cache_path_is_absolute(self):
        """Test cache path is always absolute."""
        repo = GitRepository(url="https://github.com/owner/repo")
        assert repo.cache_path.is_absolute()


class TestGitRepositoryEquality:
    """Test GitRepository equality comparison."""

    def test_equality_same_url_and_subdirectory(self):
        """Test repositories with same URL and subdirectory are equal."""
        repo1 = GitRepository(
            url="https://github.com/owner/repo",
            subdirectory="agents"
        )
        repo2 = GitRepository(
            url="https://github.com/owner/repo",
            subdirectory="agents"
        )

        # Identifier should be same
        assert repo1.identifier == repo2.identifier

    def test_inequality_different_subdirectory(self):
        """Test repositories with different subdirectories are not equal."""
        repo1 = GitRepository(
            url="https://github.com/owner/repo",
            subdirectory="agents"
        )
        repo2 = GitRepository(
            url="https://github.com/owner/repo",
            subdirectory="tools"
        )

        assert repo1.identifier != repo2.identifier

    def test_inequality_different_url(self):
        """Test repositories with different URLs are not equal."""
        repo1 = GitRepository(url="https://github.com/owner1/repo")
        repo2 = GitRepository(url="https://github.com/owner2/repo")

        assert repo1.identifier != repo2.identifier


class TestGitRepositoryPriority:
    """Test GitRepository priority handling."""

    def test_default_priority(self):
        """Test default priority is 100."""
        repo = GitRepository(url="https://github.com/owner/repo")
        assert repo.priority == 100

    def test_lower_priority_means_higher_precedence(self):
        """Test that lower priority number means higher precedence in sorting."""
        high_priority_repo = GitRepository(
            url="https://github.com/owner/repo1",
            priority=50
        )
        low_priority_repo = GitRepository(
            url="https://github.com/owner/repo2",
            priority=100
        )

        repos = sorted([low_priority_repo, high_priority_repo], key=lambda r: r.priority)

        # Lower number should come first
        assert repos[0].priority == 50
        assert repos[1].priority == 100
