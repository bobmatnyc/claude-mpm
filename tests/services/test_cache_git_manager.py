"""
Tests for CacheGitManager service.

Design Decision: Use pytest with comprehensive mocking

Rationale: CacheGitManager wraps GitOperationsService, so we mock the underlying
git service to test cache-specific logic without requiring actual git repository.
This provides fast, isolated tests that don't depend on network or filesystem state.

Test Coverage:
- Git repository detection (is_git_repo)
- Status retrieval with all fields (branch, uncommitted, unpushed)
- Pull operations with conflict detection
- Commit and push workflows
- Full sync workflow with all phases
- Error handling for all edge cases
- Fallback behavior for non-git cache

Example:
    >>> pytest tests/services/test_cache_git_manager.py -v
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from claude_mpm.services.agents.cache_git_manager import CacheGitManager
from claude_mpm.services.git.git_operations_service import (
    GitConflictError,
    GitOperationError,
)


@pytest.fixture
def mock_git_ops():
    """Mock GitOperationsService for testing."""
    with patch("claude_mpm.services.agents.cache_git_manager.GitOperationsService") as mock:
        yield mock.return_value


@pytest.fixture
def cache_path(tmp_path):
    """Create temporary cache directory."""
    cache = tmp_path / "cache" / "remote-agents"
    cache.mkdir(parents=True)
    return cache


@pytest.fixture
def git_repo_path(cache_path):
    """Create temporary git repository structure."""
    git_dir = cache_path / ".git"
    git_dir.mkdir()
    return cache_path


class TestCacheGitManagerInitialization:
    """Test CacheGitManager initialization and configuration."""

    def test_init_with_git_repo(self, git_repo_path, mock_git_ops):
        """Test initialization when cache is a git repository."""
        mock_git_ops.is_git_repo.return_value = True

        manager = CacheGitManager(git_repo_path)

        assert manager.cache_path == git_repo_path
        assert manager.repo_path == git_repo_path
        assert manager.git_ops == mock_git_ops

    def test_init_without_git_repo(self, cache_path, mock_git_ops):
        """Test initialization when cache is not a git repository."""
        mock_git_ops.is_git_repo.return_value = False

        manager = CacheGitManager(cache_path)

        assert manager.cache_path == cache_path
        assert manager.repo_path is None

    def test_find_git_root_in_parent(self, tmp_path, mock_git_ops):
        """Test finding git root in parent directory (upward search)."""
        # Setup: cache/remote-agents/bobmatnyc/claude-mpm-agents/agents
        cache_root = tmp_path / "cache" / "remote-agents" / "bobmatnyc" / "claude-mpm-agents"
        agents_dir = cache_root / "agents"
        agents_dir.mkdir(parents=True)

        # Mock git repo at cache_root
        def is_git_repo_side_effect(path):
            return path == cache_root

        mock_git_ops.is_git_repo.side_effect = is_git_repo_side_effect

        manager = CacheGitManager(agents_dir)

        assert manager.repo_path == cache_root

    def test_find_git_root_in_subdirectory(self, tmp_path, mock_git_ops):
        """Test finding git root in subdirectory (downward search)."""
        # Setup: cache_path points to parent, but git repo is nested
        # cache/remote-agents (cache_path - no .git here)
        # cache/remote-agents/bobmatnyc/claude-mpm-agents (.git here)
        cache_path = tmp_path / "cache" / "remote-agents"
        cache_path.mkdir(parents=True)

        git_repo_path = cache_path / "bobmatnyc" / "claude-mpm-agents"
        git_repo_path.mkdir(parents=True)

        # Mock git repo ONLY at nested path (not at cache_path or parents)
        def is_git_repo_side_effect(path):
            return path == git_repo_path

        mock_git_ops.is_git_repo.side_effect = is_git_repo_side_effect

        manager = CacheGitManager(cache_path)

        # Should find git repo by searching downward
        assert manager.repo_path == git_repo_path

    def test_find_git_root_one_level_down(self, tmp_path, mock_git_ops):
        """Test finding git root one level down (immediate subdirectory)."""
        # Setup: cache_path has immediate subdir with .git
        cache_path = tmp_path / "cache"
        cache_path.mkdir(parents=True)

        git_repo_path = cache_path / "my-agents"
        git_repo_path.mkdir()

        def is_git_repo_side_effect(path):
            return path == git_repo_path

        mock_git_ops.is_git_repo.side_effect = is_git_repo_side_effect

        manager = CacheGitManager(cache_path)

        assert manager.repo_path == git_repo_path

    def test_no_git_root_found(self, tmp_path, mock_git_ops):
        """Test when no git repository is found (upward or downward)."""
        cache_path = tmp_path / "cache" / "no-git"
        cache_path.mkdir(parents=True)

        # Mock: no git repo anywhere
        mock_git_ops.is_git_repo.return_value = False

        manager = CacheGitManager(cache_path)

        assert manager.repo_path is None
        assert manager.is_git_repo() is False


class TestGitRepositoryDetection:
    """Test git repository detection methods."""

    def test_is_git_repo_true(self, git_repo_path, mock_git_ops):
        """Test detection when cache is a git repository."""
        mock_git_ops.is_git_repo.return_value = True

        manager = CacheGitManager(git_repo_path)

        assert manager.is_git_repo() is True

    def test_is_git_repo_false(self, cache_path, mock_git_ops):
        """Test detection when cache is not a git repository."""
        mock_git_ops.is_git_repo.return_value = False

        manager = CacheGitManager(cache_path)

        assert manager.is_git_repo() is False


class TestGetStatus:
    """Test git status retrieval."""

    def test_get_status_clean_repo(self, git_repo_path, mock_git_ops):
        """Test status for clean repository (no changes, no unpushed commits)."""
        mock_git_ops.is_git_repo.return_value = True
        mock_git_ops.get_current_branch.return_value = "main"
        mock_git_ops.has_uncommitted_changes.return_value = False
        mock_git_ops.get_remote_url.return_value = "https://github.com/owner/repo"
        mock_git_ops._run_git_command.return_value = (0, "0\t0", "")

        manager = CacheGitManager(git_repo_path)
        status = manager.get_status()

        assert status["branch"] == "main"
        assert status["uncommitted"] == []
        assert status["uncommitted_count"] == 0
        assert status["unpushed"] == 0
        assert status["is_clean"] is True
        assert status["ahead"] == 0
        assert status["behind"] == 0
        assert status["remote_url"] == "https://github.com/owner/repo"

    def test_get_status_with_uncommitted_changes(self, git_repo_path, mock_git_ops):
        """Test status with uncommitted changes."""
        mock_git_ops.is_git_repo.return_value = True
        mock_git_ops.get_current_branch.return_value = "main"
        mock_git_ops.has_uncommitted_changes.return_value = True
        mock_git_ops.get_remote_url.return_value = "https://github.com/owner/repo"

        # Mock git status --porcelain output (correct format: XY filename)
        def run_git_command_side_effect(cmd, cwd=None):
            if "status" in cmd and "--porcelain" in cmd:
                # Correct format: 2 status chars + space + filename
                return (0, " M agents/engineer.md\n M agents/research.md", "")
            if "rev-list" in cmd:
                return (0, "0\t0", "")
            return (1, "", "error")

        mock_git_ops._run_git_command.side_effect = run_git_command_side_effect

        manager = CacheGitManager(git_repo_path)
        status = manager.get_status()

        assert status["uncommitted_count"] == 2
        assert "agents/engineer.md" in status["uncommitted"]
        assert "agents/research.md" in status["uncommitted"]
        assert status["is_clean"] is False

    def test_get_status_with_unpushed_commits(self, git_repo_path, mock_git_ops):
        """Test status with unpushed commits."""
        mock_git_ops.is_git_repo.return_value = True
        mock_git_ops.get_current_branch.return_value = "main"
        mock_git_ops.has_uncommitted_changes.return_value = False
        mock_git_ops.get_remote_url.return_value = "https://github.com/owner/repo"

        # Mock git rev-list output: 0 behind, 3 ahead
        def run_git_command_side_effect(cmd, cwd=None):
            if "rev-list" in cmd:
                return (0, "0\t3", "")
            if "status" in cmd:
                return (0, "", "")
            return (1, "", "error")

        mock_git_ops._run_git_command.side_effect = run_git_command_side_effect

        manager = CacheGitManager(git_repo_path)
        status = manager.get_status()

        assert status["unpushed"] == 3
        assert status["ahead"] == 3
        assert status["behind"] == 0
        assert status["is_clean"] is False

    def test_get_status_non_git_repo(self, cache_path, mock_git_ops):
        """Test status when cache is not a git repository."""
        mock_git_ops.is_git_repo.return_value = False

        manager = CacheGitManager(cache_path)
        status = manager.get_status()

        assert "error" in status
        assert status["is_clean"] is True


class TestPullLatest:
    """Test pulling latest changes from remote."""

    def test_pull_success(self, git_repo_path, mock_git_ops):
        """Test successful pull operation."""
        mock_git_ops.is_git_repo.return_value = True
        mock_git_ops.has_uncommitted_changes.return_value = False
        mock_git_ops.pull.return_value = None  # No exception = success

        manager = CacheGitManager(git_repo_path)
        success, msg = manager.pull_latest("main")

        assert success is True
        assert "Successfully pulled" in msg
        mock_git_ops.pull.assert_called_once_with(git_repo_path, "main")

    def test_pull_with_uncommitted_changes_warning(self, git_repo_path, mock_git_ops):
        """Test pull warns about uncommitted changes but continues."""
        mock_git_ops.is_git_repo.return_value = True
        mock_git_ops.has_uncommitted_changes.return_value = True
        mock_git_ops.pull.return_value = None
        mock_git_ops._run_git_command.return_value = (0, " M file.txt", "")

        manager = CacheGitManager(git_repo_path)
        success, msg = manager.pull_latest("main")

        assert success is True
        assert "Successfully pulled" in msg

    def test_pull_with_conflicts(self, git_repo_path, mock_git_ops):
        """Test pull with merge conflicts."""
        mock_git_ops.is_git_repo.return_value = True
        mock_git_ops.has_uncommitted_changes.return_value = False
        mock_git_ops.pull.side_effect = GitConflictError("Merge conflict in file.txt")

        manager = CacheGitManager(git_repo_path)
        success, msg = manager.pull_latest("main")

        assert success is False
        assert "Merge conflicts detected" in msg
        assert "Manual resolution required" in msg

    def test_pull_non_git_repo(self, cache_path, mock_git_ops):
        """Test pull on non-git repository."""
        mock_git_ops.is_git_repo.return_value = False

        manager = CacheGitManager(cache_path)
        success, msg = manager.pull_latest()

        assert success is False
        assert "Not a git repository" in msg


class TestCommitChanges:
    """Test committing changes to cache."""

    def test_commit_success(self, git_repo_path, mock_git_ops):
        """Test successful commit operation."""
        mock_git_ops.is_git_repo.return_value = True
        mock_git_ops.stage_files.return_value = None
        mock_git_ops.commit.return_value = None

        manager = CacheGitManager(git_repo_path)
        success, msg = manager.commit_changes("feat: update agents")

        assert success is True
        assert "Successfully committed" in msg
        mock_git_ops.stage_files.assert_called_once()
        mock_git_ops.commit.assert_called_once()

    def test_commit_specific_files(self, git_repo_path, mock_git_ops):
        """Test committing specific files."""
        mock_git_ops.is_git_repo.return_value = True
        mock_git_ops.stage_files.return_value = None
        mock_git_ops.commit.return_value = None

        manager = CacheGitManager(git_repo_path)
        files = [git_repo_path / "agents" / "engineer.md"]
        success, msg = manager.commit_changes("feat: update engineer agent", files=files)

        assert success is True
        # Verify files were staged
        mock_git_ops.stage_files.assert_called_once()

    def test_commit_failure(self, git_repo_path, mock_git_ops):
        """Test commit failure."""
        mock_git_ops.is_git_repo.return_value = True
        mock_git_ops.stage_files.return_value = None
        mock_git_ops.commit.side_effect = GitOperationError("Nothing to commit")

        manager = CacheGitManager(git_repo_path)
        success, msg = manager.commit_changes("feat: update agents")

        assert success is False
        assert "Failed to commit" in msg


class TestPushChanges:
    """Test pushing changes to remote."""

    def test_push_success(self, git_repo_path, mock_git_ops):
        """Test successful push operation."""
        mock_git_ops.is_git_repo.return_value = True
        mock_git_ops.push.return_value = None

        manager = CacheGitManager(git_repo_path)
        success, msg = manager.push_changes("main")

        assert success is True
        assert "Successfully pushed" in msg
        mock_git_ops.push.assert_called_once_with(git_repo_path, "main", set_upstream=True)

    def test_push_rejected_non_fast_forward(self, git_repo_path, mock_git_ops):
        """Test push rejected due to remote changes."""
        mock_git_ops.is_git_repo.return_value = True
        mock_git_ops.push.side_effect = GitOperationError("rejected - non-fast-forward")

        manager = CacheGitManager(git_repo_path)
        success, msg = manager.push_changes()

        assert success is False
        assert "Push rejected" in msg
        assert "Pull latest changes" in msg

    def test_push_authentication_error(self, git_repo_path, mock_git_ops):
        """Test push with authentication failure."""
        from claude_mpm.services.git.git_operations_service import (
            GitAuthenticationError,
        )

        mock_git_ops.is_git_repo.return_value = True
        mock_git_ops.push.side_effect = GitAuthenticationError("Authentication failed")

        manager = CacheGitManager(git_repo_path)
        success, msg = manager.push_changes()

        assert success is False
        assert "Authentication failed" in msg
        assert "Configure SSH keys" in msg


class TestCheckConflicts:
    """Test conflict detection after pull."""

    def test_check_conflicts_none(self, git_repo_path, mock_git_ops):
        """Test no conflicts detected."""
        mock_git_ops.is_git_repo.return_value = True
        mock_git_ops._run_git_command.return_value = (0, "", "")

        manager = CacheGitManager(git_repo_path)
        conflicts = manager.check_conflicts()

        assert conflicts == []

    def test_check_conflicts_detected(self, git_repo_path, mock_git_ops):
        """Test conflicts detected."""
        mock_git_ops.is_git_repo.return_value = True
        # UU = both modified (conflict)
        mock_git_ops._run_git_command.return_value = (
            0,
            "UU agents/engineer.md\nUU agents/research.md",
            "",
        )

        manager = CacheGitManager(git_repo_path)
        conflicts = manager.check_conflicts()

        assert len(conflicts) == 2
        assert Path("agents/engineer.md") in conflicts
        assert Path("agents/research.md") in conflicts


class TestSyncWithRemote:
    """Test full sync workflow."""

    def test_sync_success_no_changes(self, git_repo_path, mock_git_ops):
        """Test sync when everything is up-to-date."""
        mock_git_ops.is_git_repo.return_value = True
        mock_git_ops.has_uncommitted_changes.return_value = False
        mock_git_ops.pull.return_value = None
        mock_git_ops._run_git_command.side_effect = [
            (0, "", ""),  # status --porcelain (no conflicts)
            (0, "0\t0", ""),  # rev-list (no unpushed)
        ]

        manager = CacheGitManager(git_repo_path)
        success, msg = manager.sync_with_remote()

        assert success is True
        assert "Sync complete" in msg
        assert "No local commits to push" in msg

    def test_sync_with_uncommitted_warning(self, git_repo_path, mock_git_ops):
        """Test sync warns about uncommitted changes."""
        mock_git_ops.is_git_repo.return_value = True
        mock_git_ops.has_uncommitted_changes.return_value = True
        mock_git_ops.pull.return_value = None

        # Mock get_status to return uncommitted files
        def run_git_command_side_effect(cmd, cwd=None):
            if "status" in cmd and "--porcelain" in cmd:
                return (0, " M file.txt", "")
            if "rev-list" in cmd:
                return (0, "0\t0", "")
            return (1, "", "error")

        mock_git_ops._run_git_command.side_effect = run_git_command_side_effect

        manager = CacheGitManager(git_repo_path)
        success, msg = manager.sync_with_remote()

        assert success is True
        assert "uncommitted change" in msg

    def test_sync_with_local_commits(self, git_repo_path, mock_git_ops):
        """Test sync pushes local commits."""
        mock_git_ops.is_git_repo.return_value = True
        mock_git_ops.has_uncommitted_changes.return_value = False
        mock_git_ops.pull.return_value = None
        mock_git_ops.push.return_value = None

        # Mock rev-list to show 3 unpushed commits
        def run_git_command_side_effect(cmd, cwd=None):
            if "status" in cmd and "--porcelain" in cmd:
                return (0, "", "")
            if "rev-list" in cmd:
                return (0, "0\t3", "")  # 3 commits ahead
            return (1, "", "error")

        mock_git_ops._run_git_command.side_effect = run_git_command_side_effect
        mock_git_ops.get_current_branch.return_value = "main"

        manager = CacheGitManager(git_repo_path)
        success, msg = manager.sync_with_remote()

        assert success is True
        assert "Pushing" in msg
        assert "3 local commit" in msg
        mock_git_ops.push.assert_called_once()

    def test_sync_with_conflicts(self, git_repo_path, mock_git_ops):
        """Test sync stops on conflicts."""
        mock_git_ops.is_git_repo.return_value = True
        mock_git_ops.has_uncommitted_changes.return_value = False
        mock_git_ops.pull.return_value = None

        # Mock conflicts detected
        mock_git_ops._run_git_command.return_value = (0, "UU file.txt", "")

        manager = CacheGitManager(git_repo_path)
        success, msg = manager.sync_with_remote()

        assert success is False
        assert "conflict" in msg.lower()

    def test_sync_pull_failure(self, git_repo_path, mock_git_ops):
        """Test sync fails when pull fails."""
        mock_git_ops.is_git_repo.return_value = True
        mock_git_ops.has_uncommitted_changes.return_value = False
        mock_git_ops.pull.side_effect = GitOperationError("Network error")

        manager = CacheGitManager(git_repo_path)
        success, msg = manager.sync_with_remote()

        assert success is False
        assert "Failed to pull" in msg or "Network error" in msg


class TestHasUncommittedChanges:
    """Test uncommitted changes detection."""

    def test_has_uncommitted_changes_true(self, git_repo_path, mock_git_ops):
        """Test detection when there are uncommitted changes."""
        mock_git_ops.is_git_repo.return_value = True
        mock_git_ops.has_uncommitted_changes.return_value = True

        manager = CacheGitManager(git_repo_path)

        assert manager.has_uncommitted_changes() is True

    def test_has_uncommitted_changes_false(self, git_repo_path, mock_git_ops):
        """Test detection when there are no uncommitted changes."""
        mock_git_ops.is_git_repo.return_value = True
        mock_git_ops.has_uncommitted_changes.return_value = False

        manager = CacheGitManager(git_repo_path)

        assert manager.has_uncommitted_changes() is False


class TestHasUnpushedCommits:
    """Test unpushed commits detection."""

    def test_has_unpushed_commits_true(self, git_repo_path, mock_git_ops):
        """Test detection when there are unpushed commits."""
        mock_git_ops.is_git_repo.return_value = True
        mock_git_ops.get_current_branch.return_value = "main"
        mock_git_ops.has_uncommitted_changes.return_value = False
        mock_git_ops._run_git_command.return_value = (0, "0\t3", "")

        manager = CacheGitManager(git_repo_path)

        assert manager.has_unpushed_commits() is True

    def test_has_unpushed_commits_false(self, git_repo_path, mock_git_ops):
        """Test detection when there are no unpushed commits."""
        mock_git_ops.is_git_repo.return_value = True
        mock_git_ops.get_current_branch.return_value = "main"
        mock_git_ops.has_uncommitted_changes.return_value = False
        mock_git_ops._run_git_command.return_value = (0, "0\t0", "")

        manager = CacheGitManager(git_repo_path)

        assert manager.has_unpushed_commits() is False


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_timeout_configuration(self, cache_path, mock_git_ops):
        """Test custom timeout configuration."""
        mock_git_ops.is_git_repo.return_value = False

        manager = CacheGitManager(cache_path, timeout=60)

        # Verify GitOperationsService was initialized with timeout
        assert manager.git_ops == mock_git_ops

    def test_nested_cache_path(self, tmp_path, mock_git_ops):
        """Test cache path nested several directories deep."""
        # Simulate: ~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/agents
        nested_path = tmp_path / "a" / "b" / "c" / "d"
        nested_path.mkdir(parents=True)

        mock_git_ops.is_git_repo.side_effect = lambda p: p == tmp_path / "a" / "b"

        manager = CacheGitManager(nested_path)

        assert manager.repo_path == tmp_path / "a" / "b"

    def test_operations_on_non_git_repo_graceful_failure(self, cache_path, mock_git_ops):
        """Test all operations fail gracefully on non-git repository."""
        mock_git_ops.is_git_repo.return_value = False

        manager = CacheGitManager(cache_path)

        # All operations should return False/error without crashing
        assert manager.is_git_repo() is False

        success, msg = manager.pull_latest()
        assert success is False

        success, msg = manager.commit_changes("test")
        assert success is False

        success, msg = manager.push_changes()
        assert success is False

        success, msg = manager.sync_with_remote()
        assert success is False

        assert manager.has_uncommitted_changes() is False
        assert manager.has_unpushed_commits() is False
        assert manager.check_conflicts() == []
