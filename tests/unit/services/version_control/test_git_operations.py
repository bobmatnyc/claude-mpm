"""Comprehensive unit tests for Git Operations service.

This test suite provides complete coverage of the GitOperationsManager class,
testing git command wrappers, branch management, merge operations, and error handling.

Coverage targets:
- Line coverage: >90%
- Branch coverage: >85%
- All error paths tested
- All edge cases covered

Based on: tests/unit/services/cli/test_session_resume_helper.py (Gold Standard)
"""

import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

import pytest

from claude_mpm.services.version_control.git_operations import (
    GitBranchInfo,
    GitOperationError,
    GitOperationResult,
    GitOperationsManager,
)

# ============================================================================
# TEST FIXTURES
# ============================================================================


@pytest.fixture
def temp_git_dir(tmp_path):
    """Create a temporary Git repository."""
    git_dir = tmp_path / "test_repo"
    git_dir.mkdir()
    git_subdir = git_dir / ".git"
    git_subdir.mkdir()
    return git_dir


@pytest.fixture
def mock_logger():
    """Create mock logger."""
    return Mock(spec=logging.Logger)


@pytest.fixture
def git_manager(temp_git_dir, mock_logger):
    """Create GitOperationsManager instance."""
    return GitOperationsManager(str(temp_git_dir), mock_logger)


@pytest.fixture
def mock_subprocess_success():
    """Create successful subprocess result."""
    result = Mock(spec=subprocess.CompletedProcess)
    result.returncode = 0
    result.stdout = "success output"
    result.stderr = ""
    return result


@pytest.fixture
def mock_subprocess_failure():
    """Create failed subprocess result."""
    result = Mock(spec=subprocess.CompletedProcess)
    result.returncode = 1
    result.stdout = ""
    result.stderr = "error message"
    return result


# ============================================================================
# TEST INITIALIZATION
# ============================================================================


class TestGitOperationsManagerInitialization:
    """Tests for GitOperationsManager initialization."""

    def test_init_with_valid_git_repo(self, temp_git_dir, mock_logger):
        """Test initialization with valid Git repository."""
        # Arrange & Act
        manager = GitOperationsManager(str(temp_git_dir), mock_logger)

        # Assert
        assert manager.project_root == temp_git_dir
        assert manager.logger == mock_logger
        assert manager.git_dir == temp_git_dir / ".git"

    def test_init_branch_prefixes_defined(self, git_manager):
        """Test that branch prefixes are defined."""
        # Arrange & Act & Assert
        assert "issue" in git_manager.branch_prefixes
        assert "feature" in git_manager.branch_prefixes
        assert "enhancement" in git_manager.branch_prefixes
        assert "hotfix" in git_manager.branch_prefixes
        assert "epic" in git_manager.branch_prefixes

    def test_init_merge_strategies_defined(self, git_manager):
        """Test that merge strategies are defined."""
        # Arrange & Act & Assert
        assert "merge" in git_manager.merge_strategies
        assert "squash" in git_manager.merge_strategies
        assert "rebase" in git_manager.merge_strategies

    def test_init_raises_error_for_non_git_repo(self, tmp_path, mock_logger):
        """Test initialization raises error for non-Git directory."""
        # Arrange
        non_git_dir = tmp_path / "not_a_repo"
        non_git_dir.mkdir()

        # Act & Assert
        with pytest.raises(GitOperationError, match="Not a Git repository"):
            GitOperationsManager(str(non_git_dir), mock_logger)


# ============================================================================
# TEST GIT REPOSITORY VALIDATION
# ============================================================================


class TestGitRepositoryValidation:
    """Tests for Git repository validation."""

    def test_is_git_repository_true_for_valid_repo(self, git_manager):
        """Test _is_git_repository returns True for valid repo."""
        # Arrange & Act
        result = git_manager._is_git_repository()

        # Assert
        assert result is True

    def test_is_git_repository_false_for_missing_git_dir(self, tmp_path, mock_logger):
        """Test _is_git_repository returns False for missing .git directory."""
        # Arrange
        non_git_dir = tmp_path / "no_git"
        non_git_dir.mkdir()

        # We need to bypass the __init__ validation for this test
        manager = object.__new__(GitOperationsManager)
        manager.project_root = non_git_dir
        manager.git_dir = non_git_dir / ".git"

        # Act
        result = manager._is_git_repository()

        # Assert
        assert result is False


# ============================================================================
# TEST GIT COMMAND EXECUTION
# ============================================================================


class TestGitCommandExecution:
    """Tests for Git command execution."""

    @patch("subprocess.run")
    def test_run_git_command_success(
        self, mock_run, git_manager, mock_subprocess_success
    ):
        """Test successful Git command execution."""
        # Arrange
        mock_run.return_value = mock_subprocess_success

        # Act
        result = git_manager._run_git_command(["status"])

        # Assert
        assert result.returncode == 0
        assert result.stdout == "success output"
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_run_git_command_with_check_true_raises_on_failure(
        self, mock_run, git_manager, mock_subprocess_failure
    ):
        """Test Git command raises exception on failure when check=True."""
        # Arrange
        mock_run.return_value = mock_subprocess_failure

        # Act & Assert
        with pytest.raises(GitOperationError, match="Git command failed"):
            git_manager._run_git_command(["invalid"], check=True)

    @patch("subprocess.run")
    def test_run_git_command_with_check_false_no_exception(
        self, mock_run, git_manager, mock_subprocess_failure
    ):
        """Test Git command doesn't raise exception when check=False."""
        # Arrange
        mock_run.return_value = mock_subprocess_failure

        # Act
        result = git_manager._run_git_command(["status"], check=False)

        # Assert
        assert result.returncode == 1

    @patch("subprocess.run")
    def test_run_git_command_raises_on_git_not_found(self, mock_run, git_manager):
        """Test Git command raises error when git is not installed."""
        # Arrange
        mock_run.side_effect = FileNotFoundError()

        # Act & Assert
        with pytest.raises(GitOperationError, match="Git is not installed"):
            git_manager._run_git_command(["status"])

    @patch("subprocess.run")
    def test_run_git_command_uses_custom_cwd(
        self, mock_run, git_manager, mock_subprocess_success
    ):
        """Test Git command uses custom working directory."""
        # Arrange
        mock_run.return_value = mock_subprocess_success
        custom_cwd = "/custom/path"

        # Act
        git_manager._run_git_command(["status"], cwd=custom_cwd)

        # Assert
        call_args = mock_run.call_args
        assert call_args[1]["cwd"] == custom_cwd

    @patch("subprocess.run")
    def test_run_git_command_logs_debug_message(
        self, mock_run, git_manager, mock_subprocess_success, mock_logger
    ):
        """Test Git command logs debug message."""
        # Arrange
        mock_run.return_value = mock_subprocess_success
        git_manager.logger = mock_logger

        # Act
        git_manager._run_git_command(["status"])

        # Assert
        mock_logger.debug.assert_called_once()


# ============================================================================
# TEST BRANCH OPERATIONS
# ============================================================================


class TestBranchOperations:
    """Tests for branch operations."""

    @patch("subprocess.run")
    def test_get_current_branch(self, mock_run, git_manager, mock_subprocess_success):
        """Test getting current branch name."""
        # Arrange
        mock_subprocess_success.stdout = "main\n"
        mock_run.return_value = mock_subprocess_success

        # Act
        branch = git_manager.get_current_branch()

        # Assert
        assert branch == "main"

    @patch("subprocess.run")
    def test_get_current_branch_fallback_to_rev_parse(self, mock_run, git_manager):
        """Test getting current branch falls back to rev-parse on old git."""
        # Arrange
        failure_result = Mock(spec=subprocess.CompletedProcess)
        failure_result.returncode = 1
        failure_result.stderr = "unknown option"

        success_result = Mock(spec=subprocess.CompletedProcess)
        success_result.returncode = 0
        success_result.stdout = "develop\n"

        mock_run.side_effect = [failure_result, success_result]

        # Act
        branch = git_manager.get_current_branch()

        # Assert
        assert branch == "develop"

    @patch("subprocess.run")
    def test_get_branch_info_current_branch(self, mock_run, git_manager):
        """Test getting information about current branch."""
        # Arrange
        mock_run.side_effect = [
            Mock(returncode=0, stdout="main\n"),  # get_current_branch
            Mock(returncode=0, stdout="main\n"),  # current_branch again
            Mock(returncode=1, stdout=""),  # upstream (not set)
            Mock(returncode=0, stdout="abc123\n"),  # last commit
            Mock(returncode=0, stdout="Initial commit\n"),  # commit message
            Mock(returncode=0, stdout=""),  # status --porcelain
        ]

        # Act
        info = git_manager.get_branch_info()

        # Assert
        assert info.name == "main"
        assert info.current is True

    @patch("subprocess.run")
    def test_get_branch_info_with_upstream(self, mock_run, git_manager):
        """Test getting branch info with upstream tracking."""
        # Arrange
        mock_run.side_effect = [
            Mock(returncode=0, stdout="main\n"),  # get_current_branch
            Mock(returncode=0, stdout="main\n"),  # current_branch again
            Mock(returncode=0, stdout="origin/main\n"),  # upstream
            Mock(returncode=0, stdout="0\t2\n"),  # ahead/behind count
            Mock(returncode=0, stdout="abc123\n"),  # last commit
            Mock(returncode=0, stdout="feat: add feature\n"),  # commit message
            Mock(returncode=0, stdout=""),  # status --porcelain
        ]

        # Act
        info = git_manager.get_branch_info("main")

        # Assert
        assert info.upstream == "origin/main"
        assert info.remote == "origin"
        assert info.behind == 0
        assert info.ahead == 2

    @patch("subprocess.run")
    def test_get_modified_files(self, mock_run, git_manager):
        """Test getting list of modified files."""
        # Arrange
        mock_run.return_value = Mock(
            returncode=0, stdout=" M file1.py\n A file2.py\nD  file3.py\n"
        )

        # Act
        files = git_manager.get_modified_files()

        # Assert
        assert len(files) == 3
        assert "file1.py" in files
        assert "file2.py" in files
        assert "file3.py" in files

    @patch("subprocess.run")
    def test_is_working_directory_clean_true(self, mock_run, git_manager):
        """Test working directory is clean."""
        # Arrange
        mock_run.return_value = Mock(returncode=0, stdout="")

        # Act
        is_clean = git_manager.is_working_directory_clean()

        # Assert
        assert is_clean is True

    @patch("subprocess.run")
    def test_is_working_directory_clean_false(self, mock_run, git_manager):
        """Test working directory has changes."""
        # Arrange
        mock_run.return_value = Mock(returncode=0, stdout=" M file.py\n")

        # Act
        is_clean = git_manager.is_working_directory_clean()

        # Assert
        assert is_clean is False

    @patch("subprocess.run")
    def test_is_file_tracked_true(self, mock_run, git_manager):
        """Test checking if file is tracked."""
        # Arrange
        mock_run.return_value = Mock(returncode=0, stdout="tracked_file.py\n")

        # Act
        is_tracked = git_manager.is_file_tracked("tracked_file.py")

        # Assert
        assert is_tracked is True

    @patch("subprocess.run")
    def test_is_file_tracked_false(self, mock_run, git_manager):
        """Test checking if file is not tracked."""
        # Arrange
        mock_run.return_value = Mock(returncode=0, stdout="")

        # Act
        is_tracked = git_manager.is_file_tracked("untracked_file.py")

        # Assert
        assert is_tracked is False

    def test_is_file_tracked_absolute_path(self, git_manager, temp_git_dir):
        """Test checking tracked file with absolute path."""
        # Arrange
        absolute_path = temp_git_dir / "test.py"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="test.py\n")

            # Act
            is_tracked = git_manager.is_file_tracked(str(absolute_path))

            # Assert
            assert is_tracked is True


# ============================================================================
# TEST BRANCH CREATION
# ============================================================================


class TestBranchCreation:
    """Tests for branch creation operations."""

    @patch("subprocess.run")
    def test_create_branch_success(self, mock_run, git_manager):
        """Test successful branch creation."""
        # Arrange
        mock_run.side_effect = [
            Mock(returncode=0, stdout="main\n"),  # get_current_branch
            Mock(returncode=0, stdout="success\n"),  # checkout -b
            Mock(returncode=0, stdout="success\n"),  # push -u
        ]

        # Act
        result = git_manager.create_branch("TEST-123", branch_type="issue")

        # Assert
        assert result.success is True
        assert "issue/TEST-123" in result.message

    @patch("subprocess.run")
    def test_create_branch_without_switch(self, mock_run, git_manager):
        """Test creating branch without switching to it."""
        # Arrange
        mock_run.side_effect = [
            Mock(returncode=0, stdout="main\n"),  # get_current_branch
            Mock(returncode=0, stdout="success\n"),  # branch (not checkout)
        ]

        # Act
        result = git_manager.create_branch(
            "TEST-123", branch_type="feature", switch_to_branch=False
        )

        # Assert
        assert result.success is True
        assert result.branch_after == "main"

    @patch("subprocess.run")
    def test_create_branch_updates_from_base(self, mock_run, git_manager):
        """Test branch creation updates from base branch."""
        # Arrange
        mock_run.side_effect = [
            Mock(returncode=0, stdout="develop\n"),  # get_current_branch
            Mock(returncode=0, stdout="success\n"),  # checkout main
            Mock(returncode=0, stdout="success\n"),  # pull origin main
            Mock(returncode=0, stdout="success\n"),  # checkout -b
            Mock(returncode=0, stdout="success\n"),  # push -u
        ]

        # Act
        result = git_manager.create_branch(
            "TEST-123", branch_type="feature", base_branch="main"
        )

        # Assert
        assert result.success is True

    @patch("subprocess.run")
    def test_create_branch_handles_failure(self, mock_run, git_manager):
        """Test branch creation handles failure gracefully."""
        # Arrange
        mock_run.side_effect = [
            Mock(returncode=0, stdout="main\n"),  # get_current_branch
            Mock(returncode=1, stderr="error"),  # checkout -b fails
        ]

        # Act
        result = git_manager.create_branch("TEST-123")

        # Assert
        assert result.success is False
        assert "Failed" in result.message


# ============================================================================
# TEST BRANCH SWITCHING
# ============================================================================


class TestBranchSwitching:
    """Tests for branch switching operations."""

    @patch("subprocess.run")
    def test_switch_branch_success(self, mock_run, git_manager):
        """Test successful branch switching."""
        # Arrange
        mock_run.side_effect = [
            Mock(returncode=0, stdout="main\n"),  # get_current_branch
            Mock(returncode=0, stdout=""),  # status --porcelain
            Mock(returncode=0, stdout="Switched to branch\n"),  # checkout
        ]

        # Act
        result = git_manager.switch_branch("develop")

        # Assert
        assert result.success is True
        assert result.branch_after == "develop"

    @patch("subprocess.run")
    def test_switch_branch_fails_with_uncommitted_changes(self, mock_run, git_manager):
        """Test switching fails with uncommitted changes."""
        # Arrange
        mock_run.side_effect = [
            Mock(returncode=0, stdout="main\n"),  # get_current_branch
            Mock(returncode=0, stdout=" M file.py\n"),  # status --porcelain (dirty)
            Mock(returncode=0, stdout=" M file.py\n"),  # get_modified_files
        ]

        # Act
        result = git_manager.switch_branch("develop")

        # Assert
        assert result.success is False
        assert "uncommitted changes" in result.message

    @patch("subprocess.run")
    def test_switch_branch_handles_error(self, mock_run, git_manager):
        """Test switch branch handles Git errors."""
        # Arrange
        mock_run.side_effect = [
            Mock(returncode=0, stdout="main\n"),  # get_current_branch
            Mock(returncode=0, stdout=""),  # status --porcelain
            Mock(returncode=1, stderr="branch not found"),  # checkout fails
        ]

        # Act
        result = git_manager.switch_branch("nonexistent")

        # Assert
        assert result.success is False


# ============================================================================
# TEST MERGE OPERATIONS
# ============================================================================


class TestMergeOperations:
    """Tests for merge operations."""

    @patch("subprocess.run")
    def test_merge_branch_success(self, mock_run, git_manager):
        """Test successful branch merge."""
        # Arrange
        mock_run.side_effect = [
            Mock(returncode=0, stdout="feature-branch\n"),  # get_current_branch
            Mock(returncode=0, stdout="main\n"),  # get_current_branch in switch
            Mock(returncode=0, stdout=""),  # status --porcelain
            Mock(returncode=0, stdout="Switched\n"),  # checkout main
            Mock(returncode=0, stdout="Already up to date\n"),  # pull
            Mock(returncode=0, stdout="Merge made\n"),  # merge
            Mock(returncode=0, stdout="Deleted branch\n"),  # branch -d
            Mock(returncode=0, stdout="success\n"),  # push --delete
        ]

        # Act
        result = git_manager.merge_branch("feature-branch", "main")

        # Assert
        assert result.success is True
        assert "Successfully merged" in result.message

    @patch("subprocess.run")
    def test_merge_branch_with_squash(self, mock_run, git_manager):
        """Test merge with squash strategy."""
        # Arrange
        mock_run.side_effect = [
            Mock(returncode=0, stdout="main\n"),  # get_current_branch
            Mock(returncode=0, stdout="Already up to date\n"),  # pull
            Mock(returncode=0, stdout="Squash commit\n"),  # merge --squash
            Mock(returncode=0, stdout="Deleted branch\n"),  # branch -d
            Mock(returncode=0, stdout="success\n"),  # push --delete
        ]

        # Act
        result = git_manager.merge_branch(
            "feature-branch", "main", merge_strategy="squash"
        )

        # Assert
        assert result.success is True

    @patch("subprocess.run")
    def test_merge_branch_with_rebase(self, mock_run, git_manager):
        """Test merge with rebase strategy."""
        # Arrange
        mock_run.side_effect = [
            Mock(returncode=0, stdout="main\n"),  # get_current_branch
            Mock(returncode=0, stdout="Already up to date\n"),  # pull
            Mock(returncode=0, stdout="Successfully rebased\n"),  # rebase
            Mock(returncode=0, stdout="Deleted branch\n"),  # branch -d
            Mock(returncode=0, stdout="success\n"),  # push --delete
        ]

        # Act
        result = git_manager.merge_branch(
            "feature-branch", "main", merge_strategy="rebase"
        )

        # Assert
        assert result.success is True

    @patch("subprocess.run")
    def test_merge_branch_keeps_source_when_requested(self, mock_run, git_manager):
        """Test merge doesn't delete source branch when requested."""
        # Arrange
        mock_run.side_effect = [
            Mock(returncode=0, stdout="main\n"),  # get_current_branch
            Mock(returncode=0, stdout="Already up to date\n"),  # pull
            Mock(returncode=0, stdout="Merge made\n"),  # merge
        ]

        # Act
        result = git_manager.merge_branch("feature-branch", "main", delete_source=False)

        # Assert
        assert result.success is True
        # Should not call branch -d
        assert len(mock_run.call_args_list) == 3


# ============================================================================
# TEST REMOTE OPERATIONS
# ============================================================================


class TestRemoteOperations:
    """Tests for remote operations."""

    @patch("subprocess.run")
    def test_push_to_remote_success(self, mock_run, git_manager):
        """Test successful push to remote."""
        # Arrange
        mock_run.side_effect = [
            Mock(returncode=0, stdout="main\n"),  # get_current_branch
            Mock(returncode=0, stdout="Everything up-to-date\n"),  # push
        ]

        # Act
        result = git_manager.push_to_remote()

        # Assert
        assert result.success is True

    @patch("subprocess.run")
    def test_push_to_remote_with_upstream(self, mock_run, git_manager):
        """Test push with upstream tracking."""
        # Arrange
        mock_run.side_effect = [
            Mock(returncode=0, stdout="main\n"),  # get_current_branch
            Mock(returncode=0, stdout="Branch set up\n"),  # push -u
        ]

        # Act
        result = git_manager.push_to_remote(set_upstream=True)

        # Assert
        assert result.success is True

    @patch("subprocess.run")
    def test_sync_with_remote_success(self, mock_run, git_manager):
        """Test successful sync with remote."""
        # Arrange
        mock_run.side_effect = [
            Mock(returncode=0, stdout="main\n"),  # get_current_branch
            Mock(returncode=0, stdout="Fetching\n"),  # fetch
            Mock(returncode=0, stdout="Already up-to-date\n"),  # pull
        ]

        # Act
        result = git_manager.sync_with_remote()

        # Assert
        assert result.success is True


# ============================================================================
# TEST CLEANUP OPERATIONS
# ============================================================================


class TestCleanupOperations:
    """Tests for cleanup operations."""

    @patch("subprocess.run")
    def test_cleanup_merged_branches(self, mock_run, git_manager):
        """Test cleaning up merged branches."""
        # Arrange
        mock_run.side_effect = [
            Mock(returncode=0, stdout="main\n"),  # get_current_branch
            Mock(returncode=0, stdout="  feature-1\n  feature-2\n* main\n"),  # merged
            Mock(returncode=0, stdout="Deleted branch\n"),  # delete feature-1
            Mock(returncode=0, stdout="Deleted branch\n"),  # delete feature-2
            Mock(returncode=0, stdout="Pruning origin\n"),  # remote prune
        ]

        # Act
        result = git_manager.cleanup_merged_branches()

        # Assert
        assert result.success is True
        assert "2 merged branches" in result.message


# ============================================================================
# TEST CONFLICT DETECTION
# ============================================================================


class TestConflictDetection:
    """Tests for merge conflict detection."""

    @patch("subprocess.run")
    def test_detect_merge_conflicts_none(self, mock_run, git_manager):
        """Test detecting no merge conflicts."""
        # Arrange
        mock_run.side_effect = [
            Mock(returncode=0, stdout="No conflicts\n"),  # merge-tree
            Mock(returncode=0, stdout="abc123\n"),  # merge-base
        ]

        # Act
        result = git_manager.detect_merge_conflicts("feature", "main")

        # Assert
        assert result["has_conflicts"] is False
        assert result["can_auto_merge"] is True

    @patch("subprocess.run")
    def test_detect_merge_conflicts_found(self, mock_run, git_manager):
        """Test detecting merge conflicts."""
        # Arrange
        conflict_output = "<<<<<<< HEAD\nconflict\n"
        mock_run.side_effect = [
            Mock(returncode=1, stdout=conflict_output),  # merge-tree
            Mock(returncode=0, stdout="abc123\n"),  # merge-base
        ]

        # Act
        result = git_manager.detect_merge_conflicts("feature", "main")

        # Assert
        assert result["has_conflicts"] is True
        assert result["can_auto_merge"] is False


# ============================================================================
# TEST REPOSITORY STATUS
# ============================================================================


class TestRepositoryStatus:
    """Tests for repository status operations."""

    @patch("subprocess.run")
    def test_get_repository_status(self, mock_run, git_manager):
        """Test getting comprehensive repository status."""
        # Arrange
        mock_run.side_effect = [
            Mock(returncode=0, stdout="main\n"),  # get_current_branch (multiple calls)
            Mock(returncode=0, stdout="main\n"),
            Mock(returncode=1, stdout=""),  # upstream
            Mock(returncode=0, stdout="abc123\n"),  # last commit
            Mock(returncode=0, stdout="Initial commit\n"),  # commit message
            Mock(returncode=0, stdout=""),  # status --porcelain
            Mock(returncode=0, stdout="  main\n* develop\n"),  # branch --list
            Mock(returncode=0, stdout="main\n"),  # for main branch info
            Mock(returncode=1, stdout=""),  # upstream for main
            Mock(returncode=0, stdout="abc123\n"),  # commit for main
            Mock(returncode=0, stdout="Initial commit\n"),  # message for main
            Mock(returncode=0, stdout=""),  # status --porcelain
        ]

        # Act
        status = git_manager.get_repository_status()

        # Assert
        assert status["current_branch"] == "main"
        assert status["is_git_repository"] is True
        assert "total_branches" in status


# ============================================================================
# TEST ERROR HANDLING
# ============================================================================


class TestGitOperationError:
    """Tests for GitOperationError exception."""

    def test_git_operation_error_with_all_fields(self):
        """Test GitOperationError with all fields."""
        # Arrange & Act
        error = GitOperationError(
            "Test error", command="git status", output="output text", error="error text"
        )

        # Assert
        assert str(error) == "Test error"
        assert error.command == "git status"
        assert error.output == "output text"
        assert error.error == "error text"

    def test_git_operation_error_minimal(self):
        """Test GitOperationError with minimal fields."""
        # Arrange & Act
        error = GitOperationError("Simple error")

        # Assert
        assert str(error) == "Simple error"
        assert error.command == ""
        assert error.output == ""
        assert error.error == ""


# ============================================================================
# TEST DATA CLASSES
# ============================================================================


class TestGitBranchInfo:
    """Tests for GitBranchInfo dataclass."""

    def test_git_branch_info_creation(self):
        """Test creating GitBranchInfo."""
        # Arrange & Act
        info = GitBranchInfo(
            name="main",
            current=True,
            remote="origin",
            upstream="origin/main",
            last_commit="abc123",
            last_commit_message="Initial commit",
            ahead=2,
            behind=0,
            modified_files=["file.py"],
        )

        # Assert
        assert info.name == "main"
        assert info.current is True
        assert info.ahead == 2
        assert len(info.modified_files) == 1


class TestGitOperationResult:
    """Tests for GitOperationResult dataclass."""

    def test_git_operation_result_creation(self):
        """Test creating GitOperationResult."""
        # Arrange & Act
        result = GitOperationResult(
            success=True,
            operation="create_branch",
            message="Success",
            output="Created branch",
            branch_before="main",
            branch_after="feature",
            execution_time=1.5,
        )

        # Assert
        assert result.success is True
        assert result.operation == "create_branch"
        assert result.execution_time == 1.5
