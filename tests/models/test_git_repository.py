"""Unit tests for GitRepository model."""

from datetime import datetime
from pathlib import Path

import pytest

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
            etag="abc123",
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
        repo = GitRepository(url="https://github.com/owner/repo", priority=-1)
        errors = repo.validate()

        assert len(errors) > 0
        assert any("priority" in error.lower() for error in errors)

    def test_validation_priority_too_high(self):
        """Test validation warns about priority > 1000."""
        repo = GitRepository(url="https://github.com/owner/repo", priority=1001)
        errors = repo.validate()

        # Warning, not error
        assert len(errors) > 0
        assert any("priority" in error.lower() for error in errors)

    def test_validation_subdirectory_absolute_path(self):
        """Test validation rejects absolute subdirectory paths."""
        repo = GitRepository(
            url="https://github.com/owner/repo", subdirectory="/absolute/path"
        )
        errors = repo.validate()

        assert len(errors) > 0
        assert any("subdirectory" in error.lower() for error in errors)

    def test_validation_success(self):
        """Test validation passes for valid repository."""
        repo = GitRepository(
            url="https://github.com/owner/repo", subdirectory="agents", priority=50
        )
        errors = repo.validate()

        assert len(errors) == 0


class TestGitRepositoryIdentifier:
    """Test GitRepository identifier generation."""

    def test_identifier_with_subdirectory(self):
        """Test identifier includes branch and subdirectory."""
        repo = GitRepository(
            url="https://github.com/owner/repo", subdirectory="agents/backend"
        )

        assert repo.identifier == "owner/repo/main/agents/backend"

    def test_identifier_without_subdirectory(self):
        """Test identifier includes branch even without subdirectory."""
        repo = GitRepository(url="https://github.com/owner/repo")

        assert repo.identifier == "owner/repo/main"

    def test_identifier_extracts_from_url(self):
        """Test identifier correctly parses GitHub URLs and includes branch."""
        test_cases = [
            ("https://github.com/owner/repo", "owner/repo/main"),
            ("https://github.com/owner/repo.git", "owner/repo/main"),
            ("https://github.com/owner-name/repo-name", "owner-name/repo-name/main"),
        ]

        for url, expected_base in test_cases:
            repo = GitRepository(url=url)
            assert repo.identifier == expected_base


class TestGitRepositoryCachePath:
    """Test GitRepository cache path generation."""

    def test_cache_path_default_location(self):
        """Test cache path uses default location including branch segment."""
        repo = GitRepository(url="https://github.com/owner/repo", subdirectory="agents")
        cache_path = repo.cache_path

        # Should be ~/.claude-mpm/cache/agents/owner/repo/main/agents
        assert cache_path.parts[-6:] == (
            "cache",
            "agents",
            "owner",
            "repo",
            "main",
            "agents",
        )
        assert cache_path.is_absolute()

    def test_cache_path_without_subdirectory(self):
        """Test cache path without subdirectory still includes branch segment."""
        repo = GitRepository(url="https://github.com/owner/repo")
        cache_path = repo.cache_path

        # Should be ~/.claude-mpm/cache/agents/owner/repo/main
        assert cache_path.parts[-5:] == ("cache", "agents", "owner", "repo", "main")

    def test_cache_path_with_nested_subdirectory(self):
        """Test cache path with nested subdirectory includes branch between repo and subdir."""
        repo = GitRepository(
            url="https://github.com/owner/repo", subdirectory="tools/agents/backend"
        )
        cache_path = repo.cache_path

        assert cache_path.parts[-8:] == (
            "cache",
            "agents",
            "owner",
            "repo",
            "main",
            "tools",
            "agents",
            "backend",
        )

    def test_cache_path_is_absolute(self):
        """Test cache path is always absolute."""
        repo = GitRepository(url="https://github.com/owner/repo")
        assert repo.cache_path.is_absolute()


class TestGitRepositoryEquality:
    """Test GitRepository equality comparison."""

    def test_equality_same_url_and_subdirectory(self):
        """Test repositories with same URL and subdirectory are equal."""
        repo1 = GitRepository(
            url="https://github.com/owner/repo", subdirectory="agents"
        )
        repo2 = GitRepository(
            url="https://github.com/owner/repo", subdirectory="agents"
        )

        # Identifier should be same
        assert repo1.identifier == repo2.identifier

    def test_inequality_different_subdirectory(self):
        """Test repositories with different subdirectories are not equal."""
        repo1 = GitRepository(
            url="https://github.com/owner/repo", subdirectory="agents"
        )
        repo2 = GitRepository(url="https://github.com/owner/repo", subdirectory="tools")

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
            url="https://github.com/owner/repo1", priority=50
        )
        low_priority_repo = GitRepository(
            url="https://github.com/owner/repo2", priority=100
        )

        repos = sorted(
            [low_priority_repo, high_priority_repo], key=lambda r: r.priority
        )

        # Lower number should come first
        assert repos[0].priority == 50
        assert repos[1].priority == 100


class TestGitRepositoryBranch:
    """Test GitRepository branch field: default, validation, and isolation."""

    def test_branch_default_is_main(self):
        """GitRepository defaults branch to 'main' when not specified."""
        repo = GitRepository(url="https://github.com/owner/repo")
        assert repo.branch == "main"

    def test_branch_can_be_set(self):
        """GitRepository accepts an explicit branch name."""
        repo = GitRepository(url="https://github.com/owner/repo", branch="develop")
        assert repo.branch == "develop"

    def test_branch_tag_names_work(self):
        """Tag names can be used as branch values (they work in raw GitHub URLs)."""
        repo = GitRepository(url="https://github.com/owner/repo", branch="v2.0.0")
        assert repo.branch == "v2.0.0"
        errors = repo.validate()
        assert len(errors) == 0

    def test_branch_in_identifier(self):
        """Branch appears between repo-name and subdirectory in the identifier."""
        repo = GitRepository(
            url="https://github.com/owner/repo",
            subdirectory="agents",
            branch="develop",
        )
        assert repo.identifier == "owner/repo/develop/agents"

    def test_branch_in_identifier_no_subdirectory(self):
        """Branch appears as the third segment when there is no subdirectory."""
        repo = GitRepository(url="https://github.com/owner/repo", branch="staging")
        assert repo.identifier == "owner/repo/staging"

    def test_branch_in_cache_path(self):
        """Branch segment is present between repo directory and subdirectory."""
        repo = GitRepository(
            url="https://github.com/owner/repo",
            subdirectory="agents",
            branch="develop",
        )
        cache_path = repo.cache_path
        # …/cache/agents/owner/repo/develop/agents
        assert cache_path.parts[-6:] == (
            "cache",
            "agents",
            "owner",
            "repo",
            "develop",
            "agents",
        )

    def test_branch_in_cache_path_no_subdirectory(self):
        """Branch segment is the final directory component when no subdirectory is given."""
        repo = GitRepository(url="https://github.com/owner/repo", branch="staging")
        cache_path = repo.cache_path
        # …/cache/agents/owner/repo/staging
        assert cache_path.parts[-5:] == ("cache", "agents", "owner", "repo", "staging")

    def test_branch_validation_rejects_slash(self):
        """Branch names containing '/' are rejected (they break raw GitHub URL parsing)."""
        repo = GitRepository(url="https://github.com/owner/repo", branch="feature/v2")
        errors = repo.validate()
        assert len(errors) > 0
        assert any("/" in error for error in errors)
        # Error message should suggest the workaround
        assert any("git branch -m" in error for error in errors)

    def test_branch_validation_rejects_empty(self):
        """Empty branch names are rejected."""
        repo = GitRepository(url="https://github.com/owner/repo", branch="")
        errors = repo.validate()
        assert len(errors) > 0
        assert any("branch" in error.lower() for error in errors)

    def test_branch_validation_rejects_whitespace_only(self):
        """Whitespace-only branch names are rejected."""
        repo = GitRepository(url="https://github.com/owner/repo", branch="   ")
        errors = repo.validate()
        assert len(errors) > 0
        assert any("branch" in error.lower() for error in errors)

    def test_same_repo_different_branches_different_identifiers(self):
        """Same URL + different branch produces different identifiers."""
        repo_main = GitRepository(url="https://github.com/owner/repo", branch="main")
        repo_staging = GitRepository(
            url="https://github.com/owner/repo", branch="staging"
        )
        assert repo_main.identifier != repo_staging.identifier

    def test_same_repo_different_branches_different_cache_paths(self):
        """Same URL + different branch produces different cache paths."""
        repo_main = GitRepository(url="https://github.com/owner/repo", branch="main")
        repo_staging = GitRepository(
            url="https://github.com/owner/repo", branch="staging"
        )
        assert repo_main.cache_path != repo_staging.cache_path
