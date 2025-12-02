"""
Unit Tests for GitHubCLIService
================================

Tests GitHub CLI integration for PR creation and management.
Mocks subprocess calls and shutil.which to avoid actual gh CLI operations.
"""

import subprocess
import unittest
from unittest.mock import Mock, patch

from claude_mpm.services.github.github_cli_service import (
    GitHubAuthenticationError, GitHubCLIError, GitHubCLINotInstalledError,
    GitHubCLIService)


class TestGitHubCLIService(unittest.TestCase):
    """Test suite for GitHubCLIService."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = GitHubCLIService(timeout=5)

    @patch("shutil.which")
    def test_is_gh_installed_true(self, mock_which):
        """Test detecting gh CLI installation."""
        mock_which.return_value = "/usr/local/bin/gh"

        result = self.service.is_gh_installed()

        self.assertTrue(result)
        mock_which.assert_called_once_with("gh")

    @patch("shutil.which")
    def test_is_gh_installed_false(self, mock_which):
        """Test detecting gh CLI not installed."""
        mock_which.return_value = None

        result = self.service.is_gh_installed()

        self.assertFalse(result)

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_is_authenticated_true(self, mock_run, mock_which):
        """Test checking authentication status."""
        mock_which.return_value = "/usr/local/bin/gh"
        mock_run.return_value = Mock(
            returncode=0, stdout="Logged in to github.com\n", stderr=""
        )

        result = self.service.is_authenticated()

        self.assertTrue(result)
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        self.assertEqual(call_args, ["gh", "auth", "status"])

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_is_authenticated_false(self, mock_run, mock_which):
        """Test checking authentication when not authenticated."""
        mock_which.return_value = "/usr/local/bin/gh"
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="Not logged in")

        result = self.service.is_authenticated()

        self.assertFalse(result)

    @patch("shutil.which")
    def test_is_authenticated_not_installed(self, mock_which):
        """Test authentication check when gh CLI not installed."""
        mock_which.return_value = None

        with self.assertRaises(GitHubCLINotInstalledError) as context:
            self.service.is_authenticated()

        self.assertIn("not installed", str(context.exception))

    def test_get_installation_instructions(self):
        """Test getting installation instructions."""
        instructions = self.service.get_installation_instructions()

        # Should contain platform-specific instructions
        self.assertIn("macOS", instructions)
        self.assertIn("Linux", instructions)
        self.assertIn("Windows", instructions)
        self.assertIn("brew install gh", instructions)
        self.assertIn("gh auth login", instructions)

    def test_get_authentication_instructions(self):
        """Test getting authentication instructions."""
        instructions = self.service.get_authentication_instructions()

        self.assertIn("gh auth login", instructions)
        self.assertIn("authenticate", instructions.lower())

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_create_pr_success(self, mock_run, mock_which):
        """Test creating PR successfully."""
        mock_which.return_value = "/usr/local/bin/gh"
        mock_run.side_effect = [
            Mock(returncode=0, stdout="Logged in\n", stderr=""),  # auth status check
            Mock(
                returncode=0,
                stdout="https://github.com/owner/repo/pull/123\n",
                stderr="",
            ),  # pr create
        ]

        pr_url = self.service.create_pr(
            repo="owner/repo",
            title="feat(agent): improve research",
            body="## Problem\nDescription",
            base="main",
        )

        self.assertEqual(pr_url, "https://github.com/owner/repo/pull/123")

        # Verify pr create command
        pr_create_call = mock_run.call_args_list[-1]
        call_args = pr_create_call[0][0]
        self.assertIn("gh", call_args)
        self.assertIn("pr", call_args)
        self.assertIn("create", call_args)
        self.assertIn("--repo", call_args)
        self.assertIn("owner/repo", call_args)

    @patch("shutil.which")
    def test_create_pr_not_installed(self, mock_which):
        """Test creating PR when gh CLI not installed."""
        mock_which.return_value = None

        with self.assertRaises(GitHubCLINotInstalledError):
            self.service.create_pr(
                repo="owner/repo",
                title="test",
                body="test",
            )

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_create_pr_not_authenticated(self, mock_run, mock_which):
        """Test creating PR when not authenticated."""
        mock_which.return_value = "/usr/local/bin/gh"
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="Not logged in")

        with self.assertRaises(GitHubAuthenticationError) as context:
            self.service.create_pr(
                repo="owner/repo",
                title="test",
                body="test",
            )

        self.assertIn("not authenticated", str(context.exception))

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_create_pr_with_draft(self, mock_run, mock_which):
        """Test creating draft PR."""
        mock_which.return_value = "/usr/local/bin/gh"
        mock_run.side_effect = [
            Mock(returncode=0, stdout="Logged in\n", stderr=""),
            Mock(
                returncode=0,
                stdout="https://github.com/owner/repo/pull/123\n",
                stderr="",
            ),
        ]

        pr_url = self.service.create_pr(
            repo="owner/repo",
            title="test",
            body="test",
            draft=True,
        )

        # Verify --draft flag was included
        pr_create_call = mock_run.call_args_list[-1]
        call_args = pr_create_call[0][0]
        self.assertIn("--draft", call_args)

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_create_pr_with_head_branch(self, mock_run, mock_which):
        """Test creating PR with explicit head branch."""
        mock_which.return_value = "/usr/local/bin/gh"
        mock_run.side_effect = [
            Mock(returncode=0, stdout="Logged in\n", stderr=""),
            Mock(
                returncode=0,
                stdout="https://github.com/owner/repo/pull/123\n",
                stderr="",
            ),
        ]

        pr_url = self.service.create_pr(
            repo="owner/repo",
            title="test",
            body="test",
            head="improve/research",
        )

        # Verify --head flag was included
        pr_create_call = mock_run.call_args_list[-1]
        call_args = pr_create_call[0][0]
        self.assertIn("--head", call_args)
        self.assertIn("improve/research", call_args)

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_create_pr_command_fails(self, mock_run, mock_which):
        """Test creating PR when gh command fails."""
        mock_which.return_value = "/usr/local/bin/gh"
        mock_run.side_effect = [
            Mock(returncode=0, stdout="Logged in\n", stderr=""),
            Mock(returncode=1, stdout="", stderr="failed to create PR"),
        ]

        with self.assertRaises(GitHubCLIError) as context:
            self.service.create_pr(
                repo="owner/repo",
                title="test",
                body="test",
            )

        self.assertIn("Failed to create PR", str(context.exception))

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_create_pr_timeout(self, mock_run, mock_which):
        """Test creating PR with timeout."""
        mock_which.return_value = "/usr/local/bin/gh"
        mock_run.side_effect = [
            Mock(returncode=0, stdout="Logged in\n", stderr=""),
            subprocess.TimeoutExpired("gh", 5),
        ]

        with self.assertRaises(GitHubCLIError) as context:
            self.service.create_pr(
                repo="owner/repo",
                title="test",
                body="test",
            )

        self.assertIn("timed out", str(context.exception))

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_check_pr_exists_true(self, mock_run, mock_which):
        """Test checking if PR exists."""
        mock_which.return_value = "/usr/local/bin/gh"
        mock_run.return_value = Mock(
            returncode=0,
            stdout="https://github.com/owner/repo/pull/123\n",
            stderr="",
        )

        pr_url = self.service.check_pr_exists(
            repo="owner/repo",
            head="improve/research",
            base="main",
        )

        self.assertEqual(pr_url, "https://github.com/owner/repo/pull/123")

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_check_pr_exists_false(self, mock_run, mock_which):
        """Test checking if PR exists when it doesn't."""
        mock_which.return_value = "/usr/local/bin/gh"
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        pr_url = self.service.check_pr_exists(
            repo="owner/repo",
            head="improve/research",
            base="main",
        )

        self.assertIsNone(pr_url)

    @patch("shutil.which")
    def test_check_pr_exists_not_installed(self, mock_which):
        """Test checking PR existence when gh CLI not installed."""
        mock_which.return_value = None

        with self.assertRaises(GitHubCLINotInstalledError):
            self.service.check_pr_exists(
                repo="owner/repo",
                head="improve/research",
            )

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_get_pr_status(self, mock_run, mock_which):
        """Test getting PR status."""
        mock_which.return_value = "/usr/local/bin/gh"
        mock_run.return_value = Mock(
            returncode=0,
            stdout='{"title":"Test PR","state":"open","url":"https://github.com/owner/repo/pull/123","number":123}\n',
            stderr="",
        )

        status = self.service.get_pr_status("https://github.com/owner/repo/pull/123")

        self.assertIsNotNone(status)
        self.assertEqual(status["title"], "Test PR")
        self.assertEqual(status["state"], "open")
        self.assertEqual(status["number"], 123)

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_get_pr_status_failure(self, mock_run, mock_which):
        """Test getting PR status when command fails."""
        mock_which.return_value = "/usr/local/bin/gh"
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="PR not found")

        status = self.service.get_pr_status("https://github.com/owner/repo/pull/999")

        self.assertIsNone(status)

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_validate_environment_success(self, mock_run, mock_which):
        """Test validating environment when everything is ready."""
        mock_which.return_value = "/usr/local/bin/gh"
        mock_run.return_value = Mock(returncode=0, stdout="Logged in\n", stderr="")

        valid, message = self.service.validate_environment()

        self.assertTrue(valid)
        self.assertEqual(message, "GitHub CLI is ready")

    @patch("shutil.which")
    def test_validate_environment_not_installed(self, mock_which):
        """Test validating environment when gh CLI not installed."""
        mock_which.return_value = None

        valid, message = self.service.validate_environment()

        self.assertFalse(valid)
        self.assertIn("not installed", message)

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_validate_environment_not_authenticated(self, mock_run, mock_which):
        """Test validating environment when not authenticated."""
        mock_which.return_value = "/usr/local/bin/gh"
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="Not logged in")

        valid, message = self.service.validate_environment()

        self.assertFalse(valid)
        self.assertIn("not authenticated", message)

    @patch("subprocess.run")
    def test_run_gh_command_success(self, mock_run):
        """Test running gh command successfully."""
        mock_run.return_value = Mock(returncode=0, stdout="output\n", stderr="")

        returncode, stdout, _stderr = self.service._run_gh_command(
            ["gh", "auth", "status"]
        )

        self.assertEqual(returncode, 0)
        self.assertEqual(stdout, "output\n")

    @patch("subprocess.run")
    def test_run_gh_command_timeout(self, mock_run):
        """Test running gh command with timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("gh", 5)

        with self.assertRaises(subprocess.TimeoutExpired):
            self.service._run_gh_command(["gh", "auth", "status"])

    @patch("subprocess.run")
    def test_run_gh_command_exception(self, mock_run):
        """Test running gh command with exception."""
        mock_run.side_effect = Exception("Command failed")

        with self.assertRaises(GitHubCLIError):
            self.service._run_gh_command(["gh", "auth", "status"])


if __name__ == "__main__":
    unittest.main()
