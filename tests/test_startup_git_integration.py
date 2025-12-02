"""
Tests for git history integration in startup banner.

This module tests the _get_recent_commits() function and its integration
into the startup banner display.
"""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.cli.startup_display import _get_recent_commits, display_startup_banner


class TestGetRecentCommits:
    """Tests for _get_recent_commits() function."""

    def test_returns_empty_list_when_not_git_repo(self):
        """Should return empty list when not in a git repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch(
                "claude_mpm.cli.startup_display.is_git_repository", return_value=False
            ):
                commits = _get_recent_commits()
                assert commits == []

    def test_returns_empty_list_on_subprocess_error(self):
        """Should return empty list when git command fails."""
        with patch(
            "claude_mpm.cli.startup_display.is_git_repository", return_value=True
        ):
            with patch(
                "subprocess.run", side_effect=subprocess.CalledProcessError(1, "git")
            ):
                commits = _get_recent_commits()
                assert commits == []

    def test_returns_empty_list_on_timeout(self):
        """Should return empty list when git command times out."""
        with patch(
            "claude_mpm.cli.startup_display.is_git_repository", return_value=True
        ):
            with patch(
                "subprocess.run", side_effect=subprocess.TimeoutExpired("git", 2)
            ):
                commits = _get_recent_commits()
                assert commits == []

    def test_returns_commits_in_correct_format(self):
        """Should return commits in 'hash • relative_time • message' format."""
        mock_output = "a3f5b7c • 2 hours ago • fix: resolve critical error\n"
        mock_output += "b2d8e9f • 1 day ago • feat: add new feature\n"
        mock_output += "c1a4f3d • 3 days ago • docs: update README\n"

        with patch(
            "claude_mpm.cli.startup_display.is_git_repository", return_value=True
        ):
            with patch(
                "subprocess.run",
                return_value=MagicMock(stdout=mock_output, returncode=0),
            ):
                commits = _get_recent_commits(max_commits=3)
                assert len(commits) == 3
                assert (
                    commits[0] == "a3f5b7c • 2 hours ago • fix: resolve critical error"
                )
                assert commits[1] == "b2d8e9f • 1 day ago • feat: add new feature"
                assert commits[2] == "c1a4f3d • 3 days ago • docs: update README"

    def test_respects_max_commits_parameter(self):
        """Should limit returned commits to max_commits parameter."""
        mock_output = "a3f5b7c • 2 hours ago • commit 1\n"
        mock_output += "b2d8e9f • 1 day ago • commit 2\n"
        mock_output += "c1a4f3d • 3 days ago • commit 3\n"
        mock_output += "d5e6f7a • 4 days ago • commit 4\n"
        mock_output += "e8f9a1b • 5 days ago • commit 5\n"

        with patch(
            "claude_mpm.cli.startup_display.is_git_repository", return_value=True
        ):
            with patch(
                "subprocess.run",
                return_value=MagicMock(stdout=mock_output, returncode=0),
            ):
                commits = _get_recent_commits(max_commits=2)
                assert len(commits) == 2
                assert commits[0] == "a3f5b7c • 2 hours ago • commit 1"
                assert commits[1] == "b2d8e9f • 1 day ago • commit 2"

    def test_handles_empty_git_log_output(self):
        """Should return empty list when git log returns no commits."""
        with patch(
            "claude_mpm.cli.startup_display.is_git_repository", return_value=True
        ):
            with patch(
                "subprocess.run", return_value=MagicMock(stdout="", returncode=0)
            ):
                commits = _get_recent_commits()
                assert commits == []

    def test_filters_empty_lines(self):
        """Should filter out empty lines from git log output."""
        mock_output = (
            "a3f5b7c • 2 hours ago • commit 1\n\n\nb2d8e9f • 1 day ago • commit 2\n\n"
        )

        with patch(
            "claude_mpm.cli.startup_display.is_git_repository", return_value=True
        ):
            with patch(
                "subprocess.run",
                return_value=MagicMock(stdout=mock_output, returncode=0),
            ):
                commits = _get_recent_commits()
                assert len(commits) == 2
                assert commits[0] == "a3f5b7c • 2 hours ago • commit 1"
                assert commits[1] == "b2d8e9f • 1 day ago • commit 2"


class TestStartupBannerGitIntegration:
    """Tests for git integration in display_startup_banner()."""

    def test_displays_no_recent_activity_when_no_commits(self, capsys):
        """Should display 'No recent activity' when no commits available."""
        with patch(
            "claude_mpm.cli.startup_display._get_recent_commits", return_value=[]
        ):
            display_startup_banner(version="4.24.4", logging_level="OFF")
            captured = capsys.readouterr()
            assert "No recent activity" in captured.out

    def test_displays_commits_when_available(self, capsys):
        """Should display commits in Recent activity section."""
        mock_commits = [
            "a3f5b7c • 2 hours ago • fix: bug",
            "b2d8e9f • 1 day ago • feat: new",
            "c1a4f3d • 3 days ago • docs: update",
        ]

        with patch(
            "claude_mpm.cli.startup_display._get_recent_commits",
            return_value=mock_commits,
        ):
            display_startup_banner(version="4.24.4", logging_level="OFF")
            captured = capsys.readouterr()
            assert "a3f5b7c • 2 hours ago • fix: bug" in captured.out
            assert "b2d8e9f • 1 day ago • feat: new" in captured.out
            assert "c1a4f3d • 3 days ago • docs: update" in captured.out
            assert "No recent activity" not in captured.out

    def test_truncates_long_commit_messages(self, capsys):
        """Should truncate very long commit messages with ellipsis."""
        long_message = "a" * 200  # 200 character message
        mock_commits = [f"a3f5b7c • 2 hours ago • {long_message}"]

        with patch(
            "claude_mpm.cli.startup_display._get_recent_commits",
            return_value=mock_commits,
        ):
            display_startup_banner(version="4.24.4", logging_level="OFF")
            captured = capsys.readouterr()
            # Should contain truncated version with ellipsis
            assert "..." in captured.out
            # Should not overflow the panel
            lines = captured.out.split("\n")
            for line in lines:
                # Account for ANSI codes, max terminal width is ~200
                assert len(line) < 250

    def test_handles_partial_commits(self, capsys):
        """Should pad with empty lines when fewer than 3 commits."""
        mock_commits = ["a3f5b7c • 2 hours ago • fix: bug"]

        with patch(
            "claude_mpm.cli.startup_display._get_recent_commits",
            return_value=mock_commits,
        ):
            display_startup_banner(version="4.24.4", logging_level="OFF")
            captured = capsys.readouterr()
            # Should show the one commit
            assert "a3f5b7c • 2 hours ago • fix: bug" in captured.out
            # Should not crash or show errors
            assert "Error" not in captured.out

    def test_calls_get_recent_commits_with_correct_max(self):
        """Should call _get_recent_commits with max_commits=3."""
        with patch(
            "claude_mpm.cli.startup_display._get_recent_commits", return_value=[]
        ) as mock_get_commits:
            display_startup_banner(version="4.24.4", logging_level="OFF")
            mock_get_commits.assert_called_once_with(max_commits=3)


class TestGitCommandFormat:
    """Tests for git command execution format."""

    def test_git_command_uses_correct_format(self):
        """Should use correct git log format string."""
        with patch(
            "claude_mpm.cli.startup_display.is_git_repository", return_value=True
        ):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(stdout="", returncode=0)
                _get_recent_commits(max_commits=3)

                # Verify the git command was called with correct format
                call_args = mock_run.call_args[0][0]
                assert call_args[0] == "git"
                assert call_args[1] == "log"
                assert "--format=%h • %ar • %s" in call_args
                assert "-3" in call_args

    def test_git_command_has_timeout(self):
        """Should set 2 second timeout on git command."""
        with patch(
            "claude_mpm.cli.startup_display.is_git_repository", return_value=True
        ):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(stdout="", returncode=0)
                _get_recent_commits()

                # Verify timeout was set
                call_kwargs = mock_run.call_args[1]
                assert call_kwargs["timeout"] == 2

    def test_git_command_captures_output(self):
        """Should capture stdout as text."""
        with patch(
            "claude_mpm.cli.startup_display.is_git_repository", return_value=True
        ):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(stdout="", returncode=0)
                _get_recent_commits()

                # Verify output capture settings
                call_kwargs = mock_run.call_args[1]
                assert call_kwargs["capture_output"] is True
                assert call_kwargs["text"] is True
                assert call_kwargs["check"] is True
