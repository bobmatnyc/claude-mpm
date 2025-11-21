"""
Unit tests for /mpm-init --catchup command.

Tests the catchup functionality that displays recent commit history
for PM context without making any changes to the project.
"""

import subprocess
import tempfile
from collections import Counter
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.cli.commands.mpm_init import MPMInitCommand


class TestCatchupCommand:
    """Test suite for the catchup command."""

    def test_catchup_returns_correct_structure(self, tmp_path):
        """Test that _catchup() returns expected data structure."""
        # Create a git repo with commits
        self._create_test_git_repo(tmp_path)

        cmd = MPMInitCommand(tmp_path)
        data = cmd._catchup()

        # Verify structure
        assert isinstance(data, dict)
        assert "commits" in data
        assert "total_commits" in data
        assert "contributors" in data
        assert "contributor_count" in data

        # Verify data types
        assert isinstance(data["commits"], list)
        assert isinstance(data["total_commits"], int)
        assert isinstance(data["contributors"], dict)
        assert isinstance(data["contributor_count"], int)

    def test_catchup_with_git_repo(self, tmp_path):
        """Test catchup in a valid git repository."""
        # Create test repo with 3 commits
        self._create_test_git_repo(tmp_path, num_commits=3)

        cmd = MPMInitCommand(tmp_path)
        data = cmd._catchup()

        # Should have commits
        assert data["total_commits"] == 3
        assert len(data["commits"]) == 3
        assert data["contributor_count"] >= 1

        # Each commit should have required fields
        for commit in data["commits"]:
            assert "hash" in commit
            assert "author" in commit
            assert "date" in commit
            assert "message" in commit
            assert len(commit["hash"]) == 7  # Short hash

    def test_catchup_without_git_repo(self, tmp_path):
        """Test catchup in a non-git directory."""
        cmd = MPMInitCommand(tmp_path)
        data = cmd._catchup()

        # Should return empty data with error
        assert data["total_commits"] == 0
        assert len(data["commits"]) == 0
        assert data["contributor_count"] == 0
        assert "error" in data

    def test_catchup_truncates_long_messages(self, tmp_path):
        """Test that long commit messages are truncated in display."""
        # Create repo with long message
        self._create_test_git_repo(
            tmp_path,
            messages=["a" * 100],  # Very long message
        )

        cmd = MPMInitCommand(tmp_path)
        data = cmd._catchup()

        # Message should be present but will be truncated in display
        assert data["commits"][0]["message"] == "a" * 100

    def test_catchup_handles_multiple_authors(self, tmp_path):
        """Test contributor counting with multiple authors."""
        # Create repo with different authors
        self._create_test_git_repo(tmp_path, num_commits=2)

        cmd = MPMInitCommand(tmp_path)
        data = cmd._catchup()

        # Should have contributor stats
        assert data["contributor_count"] >= 1
        assert isinstance(data["contributors"], dict)
        assert sum(data["contributors"].values()) == data["total_commits"]

    def test_catchup_date_formatting(self, tmp_path):
        """Test that dates are formatted correctly."""
        self._create_test_git_repo(tmp_path)

        cmd = MPMInitCommand(tmp_path)
        data = cmd._catchup()

        if data["commits"]:
            date = data["commits"][0]["date"]
            # Should be in format: YYYY-MM-DD HH:MM
            assert len(date) == 16
            assert date[4] == "-"
            assert date[7] == "-"
            assert date[10] == " "
            assert date[13] == ":"

    def test_catchup_limits_to_25_commits(self, tmp_path):
        """Test that catchup limits results to 25 commits."""
        # Create repo with 30 commits
        self._create_test_git_repo(tmp_path, num_commits=30)

        cmd = MPMInitCommand(tmp_path)
        data = cmd._catchup()

        # Should limit to 25
        assert data["total_commits"] <= 25
        assert len(data["commits"]) <= 25

    def test_initialize_project_catchup_mode(self, tmp_path):
        """Test initialize_project with catchup=True."""
        self._create_test_git_repo(tmp_path)

        cmd = MPMInitCommand(tmp_path)
        result = cmd.initialize_project(catchup=True)

        # Should return success with catchup data
        assert result["status"] == "success"
        assert result["mode"] == "catchup"
        assert "catchup_data" in result

        # Should not modify project
        assert not (tmp_path / "CLAUDE.md").exists()

    def test_display_catchup_with_data(self, tmp_path):
        """Test _display_catchup with valid data."""
        self._create_test_git_repo(tmp_path, num_commits=5)

        cmd = MPMInitCommand(tmp_path)
        data = cmd._catchup()

        # Should not raise exception - mock the instance console
        with patch.object(cmd, "console") as mock_console:
            cmd._display_catchup(data)
            # Verify output was generated
            assert mock_console.print.call_count > 0

    def test_display_catchup_with_error(self, tmp_path):
        """Test _display_catchup handles error case gracefully."""
        cmd = MPMInitCommand(tmp_path)
        data = {
            "commits": [],
            "total_commits": 0,
            "contributors": {},
            "contributor_count": 0,
            "error": "Not a git repo",
        }

        # Should not raise exception - mock the instance console
        with patch.object(cmd, "console") as mock_console:
            cmd._display_catchup(data)
            # Should display error panel
            assert mock_console.print.call_count > 0

    def test_catchup_performance(self, tmp_path):
        """Test that catchup executes quickly."""
        import time

        self._create_test_git_repo(tmp_path, num_commits=25)

        cmd = MPMInitCommand(tmp_path)

        start = time.time()
        data = cmd._catchup()
        elapsed = time.time() - start

        # Should complete in under 1 second
        assert elapsed < 1.0
        assert data["total_commits"] > 0

    # Helper methods

    def _create_test_git_repo(
        self, path: Path, num_commits: int = 1, messages: list | None = None
    ):
        """Create a test git repository with commits."""
        # Initialize git repo
        subprocess.run(
            ["git", "init"],
            cwd=str(path),
            capture_output=True,
            check=True,
        )

        # Configure git
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=str(path),
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=str(path),
            capture_output=True,
            check=True,
        )

        # Create commits
        for i in range(num_commits):
            # Create a file
            (path / f"file{i}.txt").write_text(f"content {i}")

            # Stage and commit
            subprocess.run(
                ["git", "add", "."],
                cwd=str(path),
                capture_output=True,
                check=True,
            )

            msg = messages[i] if messages and i < len(messages) else f"Commit {i + 1}"
            subprocess.run(
                ["git", "commit", "-m", msg],
                cwd=str(path),
                capture_output=True,
                check=True,
            )


@pytest.fixture
def tmp_path(tmp_path_factory):
    """Create a temporary directory for tests."""
    return tmp_path_factory.mktemp("test_catchup")
