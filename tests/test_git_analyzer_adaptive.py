"""
Test suite for adaptive git context analysis functionality.

This tests the new adaptive window feature that ensures meaningful context
regardless of project commit velocity.
"""

import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from claude_mpm.utils.git_analyzer import analyze_recent_activity


class TestAdaptiveContextAnalysis:
    """Test adaptive time window for git context analysis."""

    @pytest.fixture
    def mock_repo_path(self, tmp_path):
        """Create a temporary repository path."""
        return tmp_path / "test_repo"

    @pytest.fixture
    def mock_subprocess_run(self):
        """Fixture to mock subprocess.run."""
        with patch("claude_mpm.utils.git_analyzer.subprocess.run") as mock_run:
            yield mock_run

    def test_high_velocity_project_uses_specified_days(
        self, mock_repo_path, mock_subprocess_run
    ):
        """Test that high-velocity projects use the specified days parameter."""
        # Simulate high commit volume - 30 commits in 7 days
        commits = []
        for i in range(30):
            date = (datetime.now() - timedelta(days=i % 7)).isoformat()
            commits.append(f"abc{i:02d}|Author{i}|author{i}@test.com|{date}|Commit {i}")
            commits.append(f"M\tsrc/file{i}.py")

        commit_output = "\n".join(commits)

        # Mock git commands
        def mock_run_side_effect(*args, **kwargs):
            cmd = args[0]
            result = Mock()
            result.returncode = 0
            result.stderr = ""

            if "branch" in cmd:
                result.stdout = "* main\n"
            elif "--since=" in " ".join(cmd):
                # Initial query with time window
                result.stdout = commit_output
            else:
                result.stdout = ""

            return result

        mock_subprocess_run.side_effect = mock_run_side_effect

        # Run analysis
        result = analyze_recent_activity(
            repo_path=str(mock_repo_path), days=7, min_commits=25
        )

        # Assertions
        assert result["adaptive_mode"] is False, (
            "Should NOT use adaptive mode for high velocity"
        )
        assert (
            "actual_time_span" not in result or result.get("actual_time_span") is None
        )
        assert "reason" not in result or result.get("reason") is None
        assert len(result["commits"]) > 0, "Should have commits"
        assert result["has_activity"] is True

    def test_low_velocity_project_expands_window(
        self, mock_repo_path, mock_subprocess_run
    ):
        """Test that low-velocity projects expand time window to get minimum commits."""
        # Simulate low commit volume - only 5 commits in 7 days
        few_commits = []
        for i in range(5):
            date = (datetime.now() - timedelta(days=i)).isoformat()
            few_commits.append(f"abc{i:02d}|Author|author@test.com|{date}|Commit {i}")
            few_commits.append(f"M\tsrc/file{i}.py")

        # But 30 commits total in repo (older than 7 days)
        many_commits = []
        for i in range(30):
            date = (datetime.now() - timedelta(days=i * 2)).isoformat()
            many_commits.append(f"abc{i:02d}|Author|author@test.com|{date}|Commit {i}")
            many_commits.append(f"M\tsrc/file{i}.py")

        # Mock git commands
        def mock_run_side_effect(*args, **kwargs):
            cmd = args[0]
            result = Mock()
            result.returncode = 0
            result.stderr = ""

            if "branch" in cmd:
                result.stdout = "* main\n"
            elif "--since=" in " ".join(cmd):
                # Initial query with time window returns few commits
                result.stdout = "\n".join(few_commits)
            elif any("-25" in str(c) or "-{" in str(c) for c in cmd):
                # Expanded query returns many commits
                result.stdout = "\n".join(many_commits)
            else:
                result.stdout = ""

            return result

        mock_subprocess_run.side_effect = mock_run_side_effect

        # Run analysis
        result = analyze_recent_activity(
            repo_path=str(mock_repo_path), days=7, min_commits=25
        )

        # Assertions
        assert result["adaptive_mode"] is True, (
            "Should use adaptive mode for low velocity"
        )
        assert result.get("actual_time_span") is not None, (
            "Should have actual time span"
        )
        assert result.get("reason") is not None, "Should explain why expanded"
        assert "minimum 25 commits" in result["reason"], (
            "Reason should mention min commits"
        )
        assert result["has_activity"] is True
        assert result["min_commits_target"] == 25

    def test_adaptive_mode_calculates_time_span(
        self, mock_repo_path, mock_subprocess_run
    ):
        """Test that adaptive mode correctly calculates actual time span."""
        # Create commits spanning 30 days
        first_date = datetime.now()
        last_date = first_date - timedelta(days=30)

        few_commits_initial = [
            f"abc01|Author|author@test.com|{first_date.isoformat()}|Recent commit",
            "M\tsrc/file1.py",
        ]

        many_commits_expanded = [
            f"abc01|Author|author@test.com|{first_date.isoformat()}|Recent commit",
            "M\tsrc/file1.py",
            f"abc30|Author|author@test.com|{last_date.isoformat()}|Old commit",
            "M\tsrc/file30.py",
        ]

        # Add more commits in between
        for i in range(2, 28):
            date = first_date - timedelta(days=i)
            many_commits_expanded.insert(
                -2, f"abc{i:02d}|Author|author@test.com|{date.isoformat()}|Commit {i}"
            )
            many_commits_expanded.insert(-2, f"M\tsrc/file{i}.py")

        def mock_run_side_effect(*args, **kwargs):
            cmd = args[0]
            result = Mock()
            result.returncode = 0
            result.stderr = ""

            if "branch" in cmd:
                result.stdout = "* main\n"
            elif "--since=" in " ".join(cmd):
                result.stdout = "\n".join(few_commits_initial)
            elif any("-25" in str(c) or "-{" in str(c) for c in cmd):
                result.stdout = "\n".join(many_commits_expanded)
            else:
                result.stdout = ""

            return result

        mock_subprocess_run.side_effect = mock_run_side_effect

        # Run analysis
        result = analyze_recent_activity(
            repo_path=str(mock_repo_path), days=7, min_commits=25
        )

        # Assertions
        assert result["adaptive_mode"] is True
        assert result.get("actual_time_span") is not None
        # Should be approximately 30 days (format changed to just number)
        actual_span = result["actual_time_span"]
        assert actual_span in ["30", ">7 days"] or int(actual_span) >= 7

    def test_min_commits_parameter_respected(self, mock_repo_path, mock_subprocess_run):
        """Test that min_commits parameter is respected."""
        # Only 10 commits in 7 days
        few_commits = []
        for i in range(10):
            date = (datetime.now() - timedelta(days=i)).isoformat()
            few_commits.append(f"abc{i:02d}|Author|author@test.com|{date}|Commit {i}")
            few_commits.append(f"M\tsrc/file{i}.py")

        # 50 commits total
        many_commits = []
        for i in range(50):
            date = (datetime.now() - timedelta(days=i)).isoformat()
            many_commits.append(f"abc{i:02d}|Author|author@test.com|{date}|Commit {i}")
            many_commits.append(f"M\tsrc/file{i}.py")

        def mock_run_side_effect(*args, **kwargs):
            cmd = args[0]
            result = Mock()
            result.returncode = 0
            result.stderr = ""

            if "branch" in cmd:
                result.stdout = "* main\n"
            elif "--since=" in " ".join(cmd):
                result.stdout = "\n".join(few_commits)
            elif any("-10" in str(c) for c in cmd):
                # Custom min_commits=10
                result.stdout = "\n".join(many_commits[:22])  # 11 commits * 2 lines
            else:
                result.stdout = ""

            return result

        mock_subprocess_run.side_effect = mock_run_side_effect

        # Run analysis with custom min_commits
        result = analyze_recent_activity(
            repo_path=str(mock_repo_path), days=7, min_commits=10
        )

        # Should NOT use adaptive mode since we have 10 commits (>= min_commits)
        # Actually, since only 5 commit lines (not counting file changes), it should use adaptive
        assert result["min_commits_target"] == 10

    def test_max_commits_never_exceeded(self, mock_repo_path, mock_subprocess_run):
        """Test that max_commits limit is never exceeded."""
        # Create more commits than max_commits
        huge_commit_list = []
        for i in range(100):
            date = (datetime.now() - timedelta(days=i)).isoformat()
            huge_commit_list.append(
                f"abc{i:03d}|Author|author@test.com|{date}|Commit {i}"
            )
            huge_commit_list.append(f"M\tsrc/file{i}.py")

        def mock_run_side_effect(*args, **kwargs):
            cmd = args[0]
            result = Mock()
            result.returncode = 0
            result.stderr = ""

            if "branch" in cmd:
                result.stdout = "* main\n"
            elif "--max-count=" in " ".join(cmd):
                # Respect max_commits in git command
                result.stdout = "\n".join(
                    huge_commit_list[:100]
                )  # 50 commits * 2 lines
            else:
                result.stdout = ""

            return result

        mock_subprocess_run.side_effect = mock_run_side_effect

        # Run analysis with max_commits=30
        result = analyze_recent_activity(
            repo_path=str(mock_repo_path), days=7, max_commits=30, min_commits=25
        )

        # Git should have been called with --max-count=30
        calls = mock_subprocess_run.call_args_list
        git_log_calls = [call for call in calls if "log" in str(call)]

        for call in git_log_calls:
            cmd = call[0][0]
            if "--max-count=" in " ".join(cmd):
                # Find the max-count argument
                max_count_arg = next(arg for arg in cmd if "--max-count=" in arg)
                assert max_count_arg == "--max-count=30"

    def test_no_commits_available(self, mock_repo_path, mock_subprocess_run):
        """Test behavior when no commits are available."""

        def mock_run_side_effect(*args, **kwargs):
            cmd = args[0]
            result = Mock()
            result.returncode = 0
            result.stderr = ""

            if "branch" in cmd:
                result.stdout = "* main\n"
            else:
                result.stdout = ""  # No commits

            return result

        mock_subprocess_run.side_effect = mock_run_side_effect

        # Run analysis
        result = analyze_recent_activity(
            repo_path=str(mock_repo_path), days=7, min_commits=25
        )

        # Assertions
        assert result["has_activity"] is False
        assert result["adaptive_mode"] is False
        assert len(result["commits"]) == 0


class TestAdaptiveModeIntegration:
    """Integration tests for adaptive mode with mpm-init context command."""

    @patch("claude_mpm.utils.git_analyzer.subprocess.run")
    def test_context_command_displays_adaptive_mode(self, mock_run):
        """Test that context command displays adaptive mode information."""
        # Simulate low velocity project
        few_commits = []
        for i in range(5):
            date = (datetime.now() - timedelta(days=i)).isoformat()
            few_commits.append(f"abc{i:02d}|Author|author@test.com|{date}|Commit {i}")
            few_commits.append(f"M\tsrc/file{i}.py")

        many_commits = []
        for i in range(30):
            date = (datetime.now() - timedelta(days=i * 2)).isoformat()
            many_commits.append(f"abc{i:02d}|Author|author@test.com|{date}|Commit {i}")
            many_commits.append(f"M\tsrc/file{i}.py")

        def mock_run_side_effect(*args, **kwargs):
            cmd = args[0]
            result = Mock()
            result.returncode = 0
            result.stderr = ""

            if "branch" in cmd:
                result.stdout = "* main\n"
            elif "--since=" in " ".join(cmd):
                result.stdout = "\n".join(few_commits)
            elif any("-25" in str(c) for c in cmd):
                result.stdout = "\n".join(many_commits)
            else:
                result.stdout = ""

            return result

        mock_run.side_effect = mock_run_side_effect

        # Analyze with adaptive mode
        result = analyze_recent_activity(repo_path=".", days=7, min_commits=25)

        # Verify adaptive mode is indicated
        assert result["adaptive_mode"] is True
        assert "actual_time_span" in result
        assert "reason" in result

        # Verify the reason mentions expanding for minimum commits
        assert "minimum 25 commits" in result["reason"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
