"""
Unit Tests for GitOperationsService
====================================

Tests git operations abstraction layer used for PR workflow automation.
Mocks subprocess calls to avoid actual git operations during testing.
"""

import subprocess
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from claude_mpm.services.git.git_operations_service import (
    GitAuthenticationError,
    GitConflictError,
    GitOperationError,
    GitOperationsService,
)


class TestGitOperationsService(unittest.TestCase):
    """Test suite for GitOperationsService."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = GitOperationsService(timeout=5)
        self.test_repo_path = Path("/tmp/test-repo")

    @patch("subprocess.run")
    def test_is_git_repo_success(self, mock_run):
        """Test checking if directory is a git repo."""
        # Mock successful git rev-parse
        mock_run.return_value = Mock(returncode=0, stdout=".git\n", stderr="")

        result = self.service.is_git_repo(self.test_repo_path)

        self.assertTrue(result)
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        self.assertEqual(call_args[0][0], ["git", "rev-parse", "--git-dir"])

    @patch("subprocess.run")
    def test_is_git_repo_failure(self, mock_run):
        """Test checking non-git directory."""
        # Mock failed git rev-parse
        mock_run.return_value = Mock(
            returncode=128, stdout="", stderr="not a git repository"
        )

        result = self.service.is_git_repo(self.test_repo_path)

        self.assertFalse(result)

    @patch("subprocess.run")
    def test_get_current_branch(self, mock_run):
        """Test getting current branch name."""
        # Mock git commands
        mock_run.side_effect = [
            Mock(returncode=0, stdout=".git\n", stderr=""),  # is_git_repo check
            Mock(returncode=0, stdout="main\n", stderr=""),  # branch --show-current
        ]

        branch = self.service.get_current_branch(self.test_repo_path)

        self.assertEqual(branch, "main")

    @patch("subprocess.run")
    def test_get_current_branch_error(self, mock_run):
        """Test getting branch name when command fails."""
        # Mock git commands
        mock_run.side_effect = [
            Mock(returncode=0, stdout=".git\n", stderr=""),  # is_git_repo check
            Mock(
                returncode=128, stdout="", stderr="fatal: not a git repository"
            ),  # branch command fails
        ]

        with self.assertRaises(GitOperationError) as context:
            self.service.get_current_branch(self.test_repo_path)

        self.assertIn("Failed to get current branch", str(context.exception))

    @patch("subprocess.run")
    def test_has_uncommitted_changes_true(self, mock_run):
        """Test detecting uncommitted changes."""
        # Mock git commands
        mock_run.side_effect = [
            Mock(returncode=0, stdout=".git\n", stderr=""),  # is_git_repo check
            Mock(returncode=0, stdout="M file.py\n", stderr=""),  # status --porcelain
        ]

        result = self.service.has_uncommitted_changes(self.test_repo_path)

        self.assertTrue(result)

    @patch("subprocess.run")
    def test_has_uncommitted_changes_false(self, mock_run):
        """Test detecting clean working directory."""
        # Mock git commands
        mock_run.side_effect = [
            Mock(returncode=0, stdout=".git\n", stderr=""),  # is_git_repo check
            Mock(returncode=0, stdout="", stderr=""),  # status --porcelain (empty)
        ]

        result = self.service.has_uncommitted_changes(self.test_repo_path)

        self.assertFalse(result)

    @patch("subprocess.run")
    def test_create_and_checkout_branch_success(self, mock_run):
        """Test creating and checking out a new branch."""
        # Mock git commands sequence
        mock_run.side_effect = [
            Mock(returncode=0, stdout=".git\n", stderr=""),  # is_git_repo check
            Mock(returncode=0, stdout="develop\n", stderr=""),  # get current branch
            Mock(returncode=0, stdout="", stderr=""),  # checkout main
            Mock(returncode=0, stdout="", stderr=""),  # pull origin main
            Mock(returncode=0, stdout="", stderr=""),  # checkout -b new-branch
        ]

        result = self.service.create_and_checkout_branch(
            self.test_repo_path, "improve/research-memory", "main"
        )

        self.assertTrue(result)
        # Verify checkout -b was called
        checkout_call = [
            call
            for call in mock_run.call_args_list
            if "checkout" in call[0][0] and "-b" in call[0][0]
        ]
        self.assertEqual(len(checkout_call), 1)

    @patch("subprocess.run")
    def test_create_and_checkout_branch_rollback_on_failure(self, mock_run):
        """Test rollback when branch creation fails."""
        # Mock git commands with failure on checkout -b
        mock_run.side_effect = [
            Mock(returncode=0, stdout=".git\n", stderr=""),  # is_git_repo check
            Mock(returncode=0, stdout="main\n", stderr=""),  # get current branch
            Mock(returncode=0, stdout="", stderr=""),  # checkout main
            Mock(returncode=0, stdout="", stderr=""),  # pull origin main
            Mock(
                returncode=128, stdout="", stderr="branch already exists"
            ),  # checkout -b fails
            Mock(returncode=0, stdout="", stderr=""),  # rollback checkout
        ]

        with self.assertRaises(GitOperationError):
            self.service.create_and_checkout_branch(
                self.test_repo_path, "existing-branch", "main"
            )

    @patch("subprocess.run")
    def test_stage_files_success(self, mock_run):
        """Test staging files for commit."""
        # Mock git commands
        mock_run.side_effect = [
            Mock(returncode=0, stdout=".git\n", stderr=""),  # is_git_repo check
            Mock(returncode=0, stdout="", stderr=""),  # git add
        ]

        result = self.service.stage_files(self.test_repo_path, ["file1.py", "file2.md"])

        self.assertTrue(result)
        # Verify git add was called with correct files
        add_call = mock_run.call_args_list[-1]
        self.assertIn("add", add_call[0][0])
        self.assertIn("file1.py", add_call[0][0])
        self.assertIn("file2.md", add_call[0][0])

    @patch("subprocess.run")
    def test_stage_files_empty_list(self, mock_run):
        """Test staging with empty file list."""
        # Mock git commands
        mock_run.return_value = Mock(returncode=0, stdout=".git\n", stderr="")

        with self.assertRaises(GitOperationError) as context:
            self.service.stage_files(self.test_repo_path, [])

        self.assertIn("No files specified", str(context.exception))

    @patch("subprocess.run")
    def test_commit_success(self, mock_run):
        """Test committing changes."""
        # Mock git commands
        mock_run.side_effect = [
            Mock(returncode=0, stdout=".git\n", stderr=""),  # is_git_repo check
            Mock(
                returncode=0, stdout="[main abc123] commit message\n", stderr=""
            ),  # commit
        ]

        result = self.service.commit(
            self.test_repo_path, "feat(agent): improve research agent"
        )

        self.assertTrue(result)

    @patch("subprocess.run")
    def test_commit_empty_message(self, mock_run):
        """Test commit with empty message."""
        # Mock git commands
        mock_run.return_value = Mock(returncode=0, stdout=".git\n", stderr="")

        with self.assertRaises(GitOperationError) as context:
            self.service.commit(self.test_repo_path, "")

        self.assertIn("Commit message cannot be empty", str(context.exception))

    @patch("subprocess.run")
    def test_commit_nothing_to_commit(self, mock_run):
        """Test commit when there are no changes."""
        # Mock git commands
        mock_run.side_effect = [
            Mock(returncode=0, stdout=".git\n", stderr=""),  # is_git_repo check
            Mock(returncode=1, stdout="", stderr="nothing to commit"),  # commit fails
        ]

        with self.assertRaises(GitOperationError) as context:
            self.service.commit(self.test_repo_path, "test commit")

        self.assertIn("No changes to commit", str(context.exception))

    @patch("subprocess.run")
    def test_push_success(self, mock_run):
        """Test pushing branch to remote."""
        # Mock git commands
        mock_run.side_effect = [
            Mock(returncode=0, stdout=".git\n", stderr=""),  # is_git_repo check
            Mock(returncode=0, stdout="", stderr=""),  # push
        ]

        result = self.service.push(self.test_repo_path, "improve/research-memory")

        self.assertTrue(result)
        # Verify push command
        push_call = mock_run.call_args_list[-1]
        self.assertIn("push", push_call[0][0])
        self.assertIn("-u", push_call[0][0])
        self.assertIn("origin", push_call[0][0])

    @patch("subprocess.run")
    def test_push_authentication_error(self, mock_run):
        """Test push with authentication failure."""
        # Mock git commands
        mock_run.side_effect = [
            Mock(returncode=0, stdout=".git\n", stderr=""),  # is_git_repo check
            Mock(
                returncode=128, stdout="", stderr="authentication failed"
            ),  # push fails
        ]

        with self.assertRaises(GitAuthenticationError) as context:
            self.service.push(self.test_repo_path, "improve/research-memory")

        self.assertIn("Git authentication failed", str(context.exception))

    @patch("subprocess.run")
    def test_pull_success(self, mock_run):
        """Test pulling from remote."""
        # Mock git commands
        mock_run.side_effect = [
            Mock(returncode=0, stdout=".git\n", stderr=""),  # is_git_repo check
            Mock(returncode=0, stdout="Already up to date.\n", stderr=""),  # pull
        ]

        result = self.service.pull(self.test_repo_path, "main")

        self.assertTrue(result)

    @patch("subprocess.run")
    def test_pull_conflict_error(self, mock_run):
        """Test pull with merge conflicts."""
        # Mock git commands
        mock_run.side_effect = [
            Mock(returncode=0, stdout=".git\n", stderr=""),  # is_git_repo check
            Mock(
                returncode=1, stdout="", stderr="CONFLICT: merge conflict in file.py"
            ),  # pull fails
        ]

        with self.assertRaises(GitConflictError) as context:
            self.service.pull(self.test_repo_path, "main")

        self.assertIn("Merge conflicts detected", str(context.exception))

    @patch("subprocess.run")
    def test_get_remote_url(self, mock_run):
        """Test getting remote URL."""
        # Mock git commands
        mock_run.side_effect = [
            Mock(returncode=0, stdout=".git\n", stderr=""),  # is_git_repo check
            Mock(
                returncode=0,
                stdout="git@github.com:bobmatnyc/claude-mpm-agents.git\n",
                stderr="",
            ),  # config get remote.origin.url
        ]

        url = self.service.get_remote_url(self.test_repo_path)

        self.assertEqual(url, "git@github.com:bobmatnyc/claude-mpm-agents.git")

    @patch("subprocess.run")
    def test_get_remote_url_not_configured(self, mock_run):
        """Test getting remote URL when not configured."""
        # Mock git commands
        mock_run.side_effect = [
            Mock(returncode=0, stdout=".git\n", stderr=""),  # is_git_repo check
            Mock(returncode=1, stdout="", stderr=""),  # config get fails
        ]

        url = self.service.get_remote_url(self.test_repo_path)

        self.assertIsNone(url)

    @patch("subprocess.run")
    def test_validate_repo_success(self, mock_run):
        """Test validating repository configuration."""
        # Mock git commands
        mock_run.side_effect = [
            Mock(returncode=0, stdout=".git\n", stderr=""),  # is_git_repo check
            Mock(
                returncode=0,
                stdout="git@github.com:bobmatnyc/claude-mpm-agents.git\n",
                stderr="",
            ),  # get remote URL
        ]

        # Mock path.exists()
        with patch.object(Path, "exists", return_value=True):
            valid, message = self.service.validate_repo(self.test_repo_path)

        self.assertTrue(valid)
        self.assertEqual(message, "Repository is valid")

    @patch("subprocess.run")
    def test_validate_repo_no_remote(self, mock_run):
        """Test validating repo without remote configured."""
        # Mock git commands
        mock_run.side_effect = [
            Mock(returncode=0, stdout=".git\n", stderr=""),  # is_git_repo check
            Mock(returncode=1, stdout="", stderr=""),  # get remote URL fails
        ]

        # Mock path.exists()
        with patch.object(Path, "exists", return_value=True):
            valid, message = self.service.validate_repo(self.test_repo_path)

        self.assertFalse(valid)
        self.assertIn("No remote origin configured", message)

    def test_validate_repo_path_not_exists(self):
        """Test validating non-existent path."""
        with patch.object(Path, "exists", return_value=False):
            valid, message = self.service.validate_repo(self.test_repo_path)

        self.assertFalse(valid)
        self.assertIn("does not exist", message)

    @patch("subprocess.run")
    def test_timeout_handling(self, mock_run):
        """Test handling of command timeouts."""
        # Mock timeout
        mock_run.side_effect = subprocess.TimeoutExpired("git", 5)

        with self.assertRaises(GitOperationError) as context:
            self.service.is_git_repo(self.test_repo_path)

        self.assertIn("timed out", str(context.exception))

    @patch("subprocess.run")
    def test_rollback_changes(self, mock_run):
        """Test rollback mechanism."""
        # Mock git commands
        mock_run.side_effect = [
            Mock(returncode=0, stdout="", stderr=""),  # reset --hard
            Mock(returncode=0, stdout="", stderr=""),  # checkout original branch
        ]

        result = self.service.rollback_changes(self.test_repo_path, "main")

        self.assertTrue(result)
        # Verify reset and checkout were called
        self.assertEqual(len(mock_run.call_args_list), 2)
        reset_call = mock_run.call_args_list[0]
        self.assertIn("reset", reset_call[0][0])
        self.assertIn("--hard", reset_call[0][0])


if __name__ == "__main__":
    unittest.main()
