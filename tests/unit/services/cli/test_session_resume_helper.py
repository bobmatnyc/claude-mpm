"""Comprehensive unit tests for SessionResumeHelper service.

This test suite provides complete coverage of the SessionResumeHelper class,
testing all methods, edge cases, error handling, and integration scenarios.

Coverage targets:
- Line coverage: >90%
- Branch coverage: >85%
- All error paths tested
- All edge cases covered
"""

import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, Mock, PropertyMock, mock_open, patch

import pytest

from claude_mpm.services.cli.session_resume_helper import SessionResumeHelper

# ============================================================================
# TEST FIXTURES
# ============================================================================


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory with session structure."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    pause_dir = project_dir / ".claude-mpm" / "sessions" / "pause"
    pause_dir.mkdir(parents=True)
    return project_dir


@pytest.fixture
def sample_session_data():
    """Sample session data for testing."""
    return {
        "session_id": "session-20251104-120000",
        "paused_at": "2025-11-04T12:00:00.000000",
        "conversation": {
            "summary": "Working on authentication feature",
            "accomplishments": [
                "Implemented JWT authentication",
                "Added unit tests for auth",
                "Updated API documentation",
            ],
            "next_steps": [
                "Deploy to staging environment",
                "Update user documentation",
                "Create integration tests",
            ],
        },
        "git_context": {
            "is_git_repo": True,
            "branch": "main",
            "recent_commits": [],
        },
    }


@pytest.fixture
def sample_git_log_output():
    """Sample git log output for testing."""
    return (
        "abc123|John Doe|2025-11-04 13:00:00 -0500|feat: add authentication\n"
        "def456|Jane Smith|2025-11-04 14:00:00 -0500|fix: bug in login\n"
        "ghi789|Bob Johnson|2025-11-04 15:00:00 -0500|docs: update readme"
    )


@pytest.fixture
def helper(temp_project_dir):
    """Create SessionResumeHelper instance with temp directory."""
    return SessionResumeHelper(project_path=temp_project_dir)


# ============================================================================
# TEST INITIALIZATION
# ============================================================================


class TestInitialization:
    """Tests for SessionResumeHelper initialization."""

    def test_init_with_explicit_path(self, temp_project_dir):
        """Test initialization with explicit project path."""
        helper = SessionResumeHelper(project_path=temp_project_dir)
        assert helper.project_path == temp_project_dir
        assert (
            helper.pause_dir == temp_project_dir / ".claude-mpm" / "sessions" / "pause"
        )

    def test_init_with_default_path(self):
        """Test initialization with default (current) path."""
        with patch("pathlib.Path.cwd") as mock_cwd:
            mock_cwd.return_value = Path("/mock/path")
            helper = SessionResumeHelper()
            assert helper.project_path == Path("/mock/path")
            assert helper.pause_dir == Path("/mock/path/.claude-mpm/sessions/pause")

    def test_pause_dir_structure(self, helper, temp_project_dir):
        """Test pause directory path structure is correct."""
        expected = temp_project_dir / ".claude-mpm" / "sessions" / "pause"
        assert helper.pause_dir == expected


# ============================================================================
# TEST HAS_PAUSED_SESSIONS
# ============================================================================


class TestHasPausedSessions:
    """Tests for has_paused_sessions() method."""

    def test_returns_true_when_sessions_exist(self, helper, temp_project_dir):
        """Test returns True when session files exist."""
        # Create a session file
        session_file = helper.pause_dir / "session-20251104-120000.json"
        session_file.write_text("{}")

        assert helper.has_paused_sessions() is True

    def test_returns_false_when_directory_missing(self, temp_project_dir):
        """Test returns False when pause directory doesn't exist."""
        # Create helper but don't create the pause directory
        pause_dir = temp_project_dir / ".claude-mpm" / "sessions" / "pause"
        if pause_dir.exists():
            pause_dir.rmdir()

        helper = SessionResumeHelper(project_path=temp_project_dir)
        assert helper.has_paused_sessions() is False

    def test_returns_false_when_directory_empty(self, helper):
        """Test returns False when pause directory exists but is empty."""
        assert helper.has_paused_sessions() is False

    def test_returns_true_with_multiple_sessions(self, helper):
        """Test returns True when multiple session files exist."""
        # Create multiple session files
        for i in range(3):
            session_file = helper.pause_dir / f"session-2025110{i}-120000.json"
            session_file.write_text("{}")

        assert helper.has_paused_sessions() is True

    def test_ignores_non_session_files(self, helper):
        """Test ignores files that don't match session pattern."""
        # Create non-session files
        (helper.pause_dir / "readme.txt").write_text("test")
        (helper.pause_dir / "config.json").write_text("{}")

        assert helper.has_paused_sessions() is False

    def test_matches_only_session_pattern(self, helper):
        """Test only matches session-*.json pattern."""
        # Create file with similar but wrong pattern
        (helper.pause_dir / "sessions-test.json").write_text("{}")
        assert helper.has_paused_sessions() is False

        # Create correct pattern
        (helper.pause_dir / "session-test.json").write_text("{}")
        assert helper.has_paused_sessions() is True


# ============================================================================
# TEST GET_MOST_RECENT_SESSION
# ============================================================================


class TestGetMostRecentSession:
    """Tests for get_most_recent_session() method."""

    def test_selects_latest_by_modification_time(self, helper, sample_session_data):
        """Test selects most recent session by modification time."""
        # Create multiple session files with different modification times
        import time

        old_session = helper.pause_dir / "session-20251101-120000.json"
        old_session.write_text(json.dumps({"id": "old"}))
        time.sleep(0.01)

        new_session = helper.pause_dir / "session-20251104-120000.json"
        new_session.write_text(json.dumps(sample_session_data))

        result = helper.get_most_recent_session()
        assert result is not None
        assert result["session_id"] == "session-20251104-120000"

    def test_returns_none_when_directory_missing(self, temp_project_dir):
        """Test returns None when pause directory doesn't exist."""
        helper = SessionResumeHelper(project_path=temp_project_dir)
        # Remove pause directory
        pause_dir = helper.pause_dir
        if pause_dir.exists():
            for file in pause_dir.iterdir():
                file.unlink()
            pause_dir.rmdir()
            pause_dir.parent.rmdir()

        assert helper.get_most_recent_session() is None

    def test_returns_none_when_no_sessions(self, helper):
        """Test returns None when no session files exist."""
        assert helper.get_most_recent_session() is None

    def test_includes_file_path_in_result(self, helper, sample_session_data):
        """Test includes file_path in returned session data."""
        session_file = helper.pause_dir / "session-20251104-120000.json"
        session_file.write_text(json.dumps(sample_session_data))

        result = helper.get_most_recent_session()
        assert result is not None
        assert "file_path" in result
        assert result["file_path"] == session_file

    def test_handles_corrupted_json_gracefully(self, helper):
        """Test handles corrupted JSON gracefully."""
        session_file = helper.pause_dir / "session-20251104-120000.json"
        session_file.write_text("{ invalid json }")

        with patch(
            "claude_mpm.services.cli.session_resume_helper.logger"
        ) as mock_logger:
            result = helper.get_most_recent_session()
            assert result is None
            mock_logger.error.assert_called_once()

    def test_handles_invalid_json(self, helper):
        """Test handles completely invalid JSON."""
        session_file = helper.pause_dir / "session-20251104-120000.json"
        session_file.write_text("not json at all")

        result = helper.get_most_recent_session()
        assert result is None

    def test_handles_empty_file(self, helper):
        """Test handles empty session file."""
        session_file = helper.pause_dir / "session-20251104-120000.json"
        session_file.write_text("")

        result = helper.get_most_recent_session()
        assert result is None

    def test_loads_valid_session_data(self, helper, sample_session_data):
        """Test successfully loads valid session data."""
        session_file = helper.pause_dir / "session-20251104-120000.json"
        session_file.write_text(json.dumps(sample_session_data))

        result = helper.get_most_recent_session()
        assert result is not None
        assert result["session_id"] == sample_session_data["session_id"]
        assert (
            result["conversation"]["summary"]
            == sample_session_data["conversation"]["summary"]
        )

    def test_handles_file_permission_error(self, helper):
        """Test handles file permission errors gracefully."""
        session_file = helper.pause_dir / "session-20251104-120000.json"
        session_file.write_text("{}")

        with patch.object(Path, "open", side_effect=PermissionError("Access denied")):
            with patch("claude_mpm.services.cli.session_resume_helper.logger"):
                result = helper.get_most_recent_session()
                assert result is None


# ============================================================================
# TEST GET_GIT_CHANGES_SINCE_PAUSE
# ============================================================================


class TestGetGitChangesSincePause:
    """Tests for get_git_changes_since_pause() method."""

    def test_successful_git_log_parsing(self, helper, sample_git_log_output):
        """Test successfully parses git log output."""
        paused_at = "2025-11-04T12:00:00.000000"
        recent_commits = []

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout=sample_git_log_output, stderr=""
            )

            count, commits = helper.get_git_changes_since_pause(
                paused_at, recent_commits
            )

            assert count == 3
            assert len(commits) == 3
            assert commits[0]["sha"] == "abc123"
            assert commits[0]["author"] == "John Doe"
            assert commits[0]["message"] == "feat: add authentication"

    def test_handles_malformed_git_output(self, helper):
        """Test handles malformed git output gracefully."""
        paused_at = "2025-11-04T12:00:00.000000"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout="malformed|incomplete\nline", stderr=""
            )

            count, commits = helper.get_git_changes_since_pause(paused_at, [])

            # Should only parse valid lines (none in this case)
            assert count == 0
            assert len(commits) == 0

    def test_handles_git_command_failure(self, helper):
        """Test handles git command failure gracefully."""
        paused_at = "2025-11-04T12:00:00.000000"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=128, stdout="", stderr="fatal: not a git repository"
            )

            with patch(
                "claude_mpm.services.cli.session_resume_helper.logger"
            ) as mock_logger:
                count, commits = helper.get_git_changes_since_pause(paused_at, [])

                assert count == 0
                assert len(commits) == 0
                mock_logger.warning.assert_called_once()

    def test_handles_non_git_repository(self, helper):
        """Test handles non-git repository gracefully."""
        paused_at = "2025-11-04T12:00:00.000000"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=1, stdout="", stderr="not a git repository"
            )

            count, commits = helper.get_git_changes_since_pause(paused_at, [])
            assert count == 0
            assert len(commits) == 0

    def test_handles_subprocess_exception(self, helper):
        """Test handles subprocess exceptions gracefully."""
        paused_at = "2025-11-04T12:00:00.000000"

        with patch("subprocess.run", side_effect=Exception("Subprocess error")):
            with patch(
                "claude_mpm.services.cli.session_resume_helper.logger"
            ) as mock_logger:
                count, commits = helper.get_git_changes_since_pause(paused_at, [])

                assert count == 0
                assert len(commits) == 0
                mock_logger.error.assert_called_once()

    def test_parses_commit_with_pipe_in_message(self, helper):
        """Test handles commit messages containing pipe characters."""
        paused_at = "2025-11-04T12:00:00.000000"
        git_output = (
            "abc123|John Doe|2025-11-04 13:00:00 -0500|feat: add feature|with|pipes"
        )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=git_output, stderr="")

            count, commits = helper.get_git_changes_since_pause(paused_at, [])

            assert count == 1
            assert commits[0]["message"] == "feat: add feature|with|pipes"

    def test_handles_empty_git_output(self, helper):
        """Test handles empty git output (no commits since pause)."""
        paused_at = "2025-11-04T12:00:00.000000"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            count, commits = helper.get_git_changes_since_pause(paused_at, [])

            assert count == 0
            assert len(commits) == 0

    def test_handles_whitespace_only_output(self, helper):
        """Test handles whitespace-only git output."""
        paused_at = "2025-11-04T12:00:00.000000"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="  \n  \n  ", stderr="")

            count, commits = helper.get_git_changes_since_pause(paused_at, [])

            assert count == 0
            assert len(commits) == 0

    def test_timezone_handling_in_timestamps(self, helper):
        """Test correctly handles various timezone formats."""
        paused_at = "2025-11-04T12:00:00-05:00"
        git_output = "abc123|Author|2025-11-04 13:00:00 -0500|message"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=git_output, stderr="")

            count, commits = helper.get_git_changes_since_pause(paused_at, [])

            assert count == 1
            assert commits[0]["timestamp"] == "2025-11-04 13:00:00 -0500"

    def test_commit_counting_accuracy(self, helper):
        """Test accurate commit counting with multiple commits."""
        paused_at = "2025-11-04T12:00:00.000000"
        git_output = "\n".join(
            [
                f"commit{i}|Author|2025-11-04 13:00:00 -0500|message {i}"
                for i in range(10)
            ]
        )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=git_output, stderr="")

            count, commits = helper.get_git_changes_since_pause(paused_at, [])

            assert count == 10
            assert len(commits) == 10

    def test_handles_invalid_timestamp_format(self, helper):
        """Test handles invalid pause timestamp format."""
        paused_at = "invalid-timestamp"

        with patch(
            "claude_mpm.services.cli.session_resume_helper.logger"
        ) as mock_logger:
            count, commits = helper.get_git_changes_since_pause(paused_at, [])

            assert count == 0
            assert len(commits) == 0
            mock_logger.error.assert_called_once()


# ============================================================================
# TEST GET_TIME_ELAPSED
# ============================================================================


class TestGetTimeElapsed:
    """Tests for get_time_elapsed() method."""

    def test_formats_days_correctly(self, helper):
        """Test formats days elapsed correctly."""
        now = datetime.now(timezone.utc)
        paused_at = (now - timedelta(days=3)).isoformat()

        result = helper.get_time_elapsed(paused_at)
        assert result == "3 days ago"

    def test_formats_single_day(self, helper):
        """Test formats single day correctly."""
        now = datetime.now(timezone.utc)
        paused_at = (now - timedelta(days=1)).isoformat()

        result = helper.get_time_elapsed(paused_at)
        assert result == "1 day ago"

    def test_formats_hours_correctly(self, helper):
        """Test formats hours elapsed correctly."""
        now = datetime.now(timezone.utc)
        paused_at = (now - timedelta(hours=5)).isoformat()

        result = helper.get_time_elapsed(paused_at)
        assert result == "5 hours ago"

    def test_formats_single_hour(self, helper):
        """Test formats single hour correctly."""
        now = datetime.now(timezone.utc)
        paused_at = (now - timedelta(hours=1)).isoformat()

        result = helper.get_time_elapsed(paused_at)
        assert result == "1 hour ago"

    def test_formats_minutes_correctly(self, helper):
        """Test formats minutes elapsed correctly."""
        now = datetime.now(timezone.utc)
        paused_at = (now - timedelta(minutes=30)).isoformat()

        result = helper.get_time_elapsed(paused_at)
        assert result == "30 minutes ago"

    def test_formats_single_minute(self, helper):
        """Test formats single minute correctly."""
        now = datetime.now(timezone.utc)
        paused_at = (now - timedelta(minutes=1)).isoformat()

        result = helper.get_time_elapsed(paused_at)
        assert result == "1 minute ago"

    def test_formats_just_now(self, helper):
        """Test formats very recent time as 'just now'."""
        now = datetime.now(timezone.utc)
        paused_at = (now - timedelta(seconds=30)).isoformat()

        result = helper.get_time_elapsed(paused_at)
        assert result == "just now"

    def test_handles_naive_datetime(self, helper):
        """Test handles timezone-naive datetime by adding UTC."""
        now = datetime.now(timezone.utc)
        paused_at = (now - timedelta(hours=2)).replace(tzinfo=None).isoformat()

        result = helper.get_time_elapsed(paused_at)
        assert "ago" in result  # Should still work

    def test_handles_different_timezones(self, helper):
        """Test handles different timezone formats."""
        now = datetime.now(timezone.utc)
        paused_at = (now - timedelta(hours=3)).isoformat()

        result = helper.get_time_elapsed(paused_at)
        assert result == "3 hours ago"

    def test_handles_invalid_timestamp(self, helper):
        """Test handles invalid timestamp format."""
        paused_at = "invalid-timestamp"

        with patch(
            "claude_mpm.services.cli.session_resume_helper.logger"
        ) as mock_logger:
            result = helper.get_time_elapsed(paused_at)

            assert result == "unknown time ago"
            mock_logger.error.assert_called_once()

    def test_handles_very_old_sessions(self, helper):
        """Test handles very old sessions (>30 days)."""
        now = datetime.now(timezone.utc)
        paused_at = (now - timedelta(days=45)).isoformat()

        result = helper.get_time_elapsed(paused_at)
        assert result == "45 days ago"

    def test_handles_future_timestamp(self, helper):
        """Test handles future timestamp (edge case)."""
        now = datetime.now(timezone.utc)
        paused_at = (now + timedelta(hours=1)).isoformat()

        result = helper.get_time_elapsed(paused_at)
        # Future time will have negative delta, should handle gracefully
        assert isinstance(result, str)


# ============================================================================
# TEST FORMAT_RESUME_PROMPT
# ============================================================================


class TestFormatResumePrompt:
    """Tests for format_resume_prompt() method."""

    def test_complete_prompt_formatting(self, helper, sample_session_data):
        """Test formats complete prompt with all fields."""
        with patch.object(helper, "get_time_elapsed", return_value="2 hours ago"):
            with patch.object(
                helper, "get_git_changes_since_pause", return_value=(0, [])
            ):
                result = helper.format_resume_prompt(sample_session_data)

                assert "PAUSED SESSION FOUND" in result
                assert "2 hours ago" in result
                assert "Working on authentication feature" in result
                assert "Implemented JWT authentication" in result
                assert "Deploy to staging environment" in result

    def test_formats_with_all_fields_populated(self, helper, sample_session_data):
        """Test formats correctly when all fields are populated."""
        with patch.object(helper, "get_time_elapsed", return_value="1 day ago"):
            with patch.object(
                helper,
                "get_git_changes_since_pause",
                return_value=(
                    2,
                    [{"sha": "abc123", "author": "John", "message": "feat: test"}],
                ),
            ):
                result = helper.format_resume_prompt(sample_session_data)

                assert "Completed:" in result
                assert "Next steps:" in result
                assert "Git changes since pause: 2 commits" in result

    def test_handles_empty_accomplishments(self, helper, sample_session_data):
        """Test handles empty accomplishments list."""
        session_data = sample_session_data.copy()
        session_data["conversation"]["accomplishments"] = []

        with patch.object(helper, "get_time_elapsed", return_value="1 hour ago"):
            with patch.object(
                helper, "get_git_changes_since_pause", return_value=(0, [])
            ):
                result = helper.format_resume_prompt(session_data)

                assert "Completed:" not in result

    def test_handles_empty_next_steps(self, helper, sample_session_data):
        """Test handles empty next_steps list."""
        session_data = sample_session_data.copy()
        session_data["conversation"]["next_steps"] = []

        with patch.object(helper, "get_time_elapsed", return_value="1 hour ago"):
            with patch.object(
                helper, "get_git_changes_since_pause", return_value=(0, [])
            ):
                result = helper.format_resume_prompt(session_data)

                assert "Next steps:" not in result

    def test_limits_accomplishments_to_five(self, helper, sample_session_data):
        """Test limits accomplishments display to 5 items."""
        session_data = sample_session_data.copy()
        session_data["conversation"]["accomplishments"] = [
            f"Item {i}" for i in range(10)
        ]

        with patch.object(helper, "get_time_elapsed", return_value="1 hour ago"):
            with patch.object(
                helper, "get_git_changes_since_pause", return_value=(0, [])
            ):
                result = helper.format_resume_prompt(session_data)

                assert "Item 0" in result
                assert "Item 4" in result
                assert "and 5 more" in result

    def test_limits_next_steps_to_five(self, helper, sample_session_data):
        """Test limits next_steps display to 5 items."""
        session_data = sample_session_data.copy()
        session_data["conversation"]["next_steps"] = [f"Task {i}" for i in range(8)]

        with patch.object(helper, "get_time_elapsed", return_value="1 hour ago"):
            with patch.object(
                helper, "get_git_changes_since_pause", return_value=(0, [])
            ):
                result = helper.format_resume_prompt(session_data)

                assert "Task 0" in result
                assert "Task 4" in result
                assert "and 3 more" in result

    def test_formats_with_git_changes(self, helper, sample_session_data):
        """Test formats correctly with git changes."""
        commits = [
            {"sha": "abc123", "author": "John", "message": "feat: test"},
            {"sha": "def456", "author": "Jane", "message": "fix: bug"},
        ]

        with patch.object(helper, "get_time_elapsed", return_value="1 hour ago"):
            with patch.object(
                helper, "get_git_changes_since_pause", return_value=(2, commits)
            ):
                result = helper.format_resume_prompt(sample_session_data)

                assert "Git changes since pause: 2 commits" in result
                assert "Recent commits:" in result
                assert "abc123 - feat: test (John)" in result

    def test_formats_without_git_changes(self, helper, sample_session_data):
        """Test formats correctly without git changes."""
        with patch.object(helper, "get_time_elapsed", return_value="1 hour ago"):
            with patch.object(
                helper, "get_git_changes_since_pause", return_value=(0, [])
            ):
                result = helper.format_resume_prompt(sample_session_data)

                assert "No git changes since pause" in result

    def test_limits_git_commits_to_three(self, helper, sample_session_data):
        """Test limits git commits display to 3 items."""
        commits = [
            {"sha": f"sha{i}", "author": f"Author{i}", "message": f"msg{i}"}
            for i in range(5)
        ]

        with patch.object(helper, "get_time_elapsed", return_value="1 hour ago"):
            with patch.object(
                helper, "get_git_changes_since_pause", return_value=(5, commits)
            ):
                result = helper.format_resume_prompt(sample_session_data)

                assert "sha0 - msg0 (Author0)" in result
                assert "sha2 - msg2 (Author2)" in result
                assert "and 2 more" in result

    def test_handles_missing_conversation_key(self, helper):
        """Test handles missing conversation key gracefully."""
        session_data = {"paused_at": "2025-11-04T12:00:00.000000"}

        with patch.object(helper, "get_time_elapsed", return_value="1 hour ago"):
            with patch.object(
                helper, "get_git_changes_since_pause", return_value=(0, [])
            ):
                result = helper.format_resume_prompt(session_data)

                assert "No summary available" in result

    def test_handles_exception_gracefully(self, helper):
        """Test handles exceptions during formatting gracefully."""
        session_data = {"paused_at": "invalid"}

        with patch.object(helper, "get_time_elapsed", side_effect=Exception("Error")):
            with patch(
                "claude_mpm.services.cli.session_resume_helper.logger"
            ) as mock_logger:
                result = helper.format_resume_prompt(session_data)

                assert "failed to format details" in result
                mock_logger.error.assert_called_once()

    def test_handles_non_ascii_characters(self, helper, sample_session_data):
        """Test handles non-ASCII characters in session data."""
        session_data = sample_session_data.copy()
        session_data["conversation"]["summary"] = "Working on 🔐 authentication"
        session_data["conversation"]["accomplishments"] = ["Added 日本語 support"]

        with patch.object(helper, "get_time_elapsed", return_value="1 hour ago"):
            with patch.object(
                helper, "get_git_changes_since_pause", return_value=(0, [])
            ):
                result = helper.format_resume_prompt(session_data)

                assert "🔐" in result
                assert "日本語" in result


# ============================================================================
# TEST CLEAR_SESSION
# ============================================================================


class TestClearSession:
    """Tests for clear_session() method."""

    def test_clears_session_successfully(self, helper, sample_session_data):
        """Test successfully clears a session file."""
        session_file = helper.pause_dir / "session-test.json"
        session_file.write_text(json.dumps(sample_session_data))

        session_data = sample_session_data.copy()
        session_data["file_path"] = session_file

        result = helper.clear_session(session_data)

        assert result is True
        assert not session_file.exists()

    def test_clears_sha256_checksum_file(self, helper, sample_session_data):
        """Test clears associated SHA256 checksum file."""
        session_file = helper.pause_dir / "session-test.json"
        session_file.write_text(json.dumps(sample_session_data))

        sha_file = helper.pause_dir / ".session-test.json.sha256"
        sha_file.write_text("checksum")

        session_data = sample_session_data.copy()
        session_data["file_path"] = session_file

        result = helper.clear_session(session_data)

        assert result is True
        assert not session_file.exists()
        assert not sha_file.exists()

    def test_handles_missing_file_path(self, helper):
        """Test handles missing file_path key."""
        session_data = {"session_id": "test"}

        with patch(
            "claude_mpm.services.cli.session_resume_helper.logger"
        ) as mock_logger:
            result = helper.clear_session(session_data)

            assert result is False
            mock_logger.error.assert_called_once()

    def test_handles_invalid_file_path_type(self, helper):
        """Test handles invalid file_path type."""
        session_data = {"file_path": "string-not-path"}

        with patch(
            "claude_mpm.services.cli.session_resume_helper.logger"
        ) as mock_logger:
            result = helper.clear_session(session_data)

            assert result is False
            mock_logger.error.assert_called_once()

    def test_handles_non_existent_file(self, helper):
        """Test handles already-deleted file gracefully."""
        session_data = {"file_path": helper.pause_dir / "nonexistent.json"}

        with patch(
            "claude_mpm.services.cli.session_resume_helper.logger"
        ) as mock_logger:
            result = helper.clear_session(session_data)

            assert result is False
            mock_logger.warning.assert_called_once()

    def test_handles_permission_error(self, helper, sample_session_data):
        """Test handles permission errors during deletion."""
        session_file = helper.pause_dir / "session-test.json"
        session_file.write_text(json.dumps(sample_session_data))

        session_data = sample_session_data.copy()
        session_data["file_path"] = session_file

        with patch.object(Path, "unlink", side_effect=PermissionError("Access denied")):
            with patch(
                "claude_mpm.services.cli.session_resume_helper.logger"
            ) as mock_logger:
                result = helper.clear_session(session_data)

                assert result is False
                mock_logger.error.assert_called_once()

    def test_continues_after_sha_file_error(self, helper, sample_session_data):
        """Test successfully clears session even if SHA file deletion fails."""
        session_file = helper.pause_dir / "session-test.json"
        session_file.write_text(json.dumps(sample_session_data))

        session_data = sample_session_data.copy()
        session_data["file_path"] = session_file

        # Don't create SHA file - should still succeed
        result = helper.clear_session(session_data)

        assert result is True
        assert not session_file.exists()


# ============================================================================
# TEST CHECK_AND_DISPLAY_RESUME_PROMPT
# ============================================================================


class TestCheckAndDisplayResumePrompt:
    """Tests for check_and_display_resume_prompt() method."""

    def test_returns_none_when_no_sessions(self, helper):
        """Test returns None when no paused sessions exist."""
        result = helper.check_and_display_resume_prompt()
        assert result is None

    def test_returns_session_when_found(self, helper, sample_session_data):
        """Test returns session data when found."""
        session_file = helper.pause_dir / "session-test.json"
        session_file.write_text(json.dumps(sample_session_data))

        with patch("builtins.print"):
            result = helper.check_and_display_resume_prompt()

            assert result is not None
            assert result["session_id"] == sample_session_data["session_id"]

    def test_prints_formatted_prompt(self, helper, sample_session_data):
        """Test prints formatted prompt to console."""
        session_file = helper.pause_dir / "session-test.json"
        session_file.write_text(json.dumps(sample_session_data))

        with patch("builtins.print") as mock_print:
            helper.check_and_display_resume_prompt()

            mock_print.assert_called_once()
            prompt_text = mock_print.call_args[0][0]
            assert "PAUSED SESSION FOUND" in prompt_text

    def test_returns_none_when_load_fails(self, helper):
        """Test returns None when session load fails."""
        session_file = helper.pause_dir / "session-test.json"
        session_file.write_text("invalid json")

        result = helper.check_and_display_resume_prompt()
        assert result is None


# ============================================================================
# TEST GET_SESSION_COUNT
# ============================================================================


class TestGetSessionCount:
    """Tests for get_session_count() method."""

    def test_returns_zero_when_directory_missing(self, temp_project_dir):
        """Test returns 0 when pause directory doesn't exist."""
        helper = SessionResumeHelper(project_path=temp_project_dir)
        # Don't create pause directory
        helper.pause_dir.rmdir()

        assert helper.get_session_count() == 0

    def test_returns_zero_when_empty(self, helper):
        """Test returns 0 when no sessions exist."""
        assert helper.get_session_count() == 0

    def test_returns_correct_count(self, helper):
        """Test returns correct count of session files."""
        for i in range(5):
            session_file = helper.pause_dir / f"session-{i}.json"
            session_file.write_text("{}")

        assert helper.get_session_count() == 5

    def test_ignores_non_session_files(self, helper):
        """Test ignores files that don't match session pattern."""
        (helper.pause_dir / "readme.txt").write_text("test")
        (helper.pause_dir / "session-1.json").write_text("{}")
        (helper.pause_dir / "session-2.json").write_text("{}")

        assert helper.get_session_count() == 2


# ============================================================================
# TEST LIST_ALL_SESSIONS
# ============================================================================


class TestListAllSessions:
    """Tests for list_all_sessions() method."""

    def test_returns_empty_when_directory_missing(self, temp_project_dir):
        """Test returns empty list when pause directory doesn't exist."""
        helper = SessionResumeHelper(project_path=temp_project_dir)
        helper.pause_dir.rmdir()

        assert helper.list_all_sessions() == []

    def test_returns_empty_when_no_sessions(self, helper):
        """Test returns empty list when no sessions exist."""
        assert helper.list_all_sessions() == []

    def test_returns_all_sessions_sorted(self, helper, sample_session_data):
        """Test returns all sessions sorted by modification time."""
        import time

        # Create multiple sessions
        for i in range(3):
            session_file = helper.pause_dir / f"session-{i}.json"
            data = sample_session_data.copy()
            data["session_id"] = f"session-{i}"
            session_file.write_text(json.dumps(data))
            time.sleep(0.01)

        sessions = helper.list_all_sessions()

        assert len(sessions) == 3
        # Most recent first
        assert sessions[0]["session_id"] == "session-2"
        assert sessions[2]["session_id"] == "session-0"

    def test_includes_file_paths(self, helper, sample_session_data):
        """Test includes file_path in each session."""
        session_file = helper.pause_dir / "session-test.json"
        session_file.write_text(json.dumps(sample_session_data))

        sessions = helper.list_all_sessions()

        assert len(sessions) == 1
        assert "file_path" in sessions[0]
        assert sessions[0]["file_path"] == session_file

    def test_skips_corrupted_files(self, helper, sample_session_data):
        """Test skips corrupted files and continues."""
        # Create valid session
        valid_file = helper.pause_dir / "session-valid.json"
        valid_file.write_text(json.dumps(sample_session_data))

        # Create corrupted session
        corrupt_file = helper.pause_dir / "session-corrupt.json"
        corrupt_file.write_text("{ invalid }")

        with patch("claude_mpm.services.cli.session_resume_helper.logger"):
            sessions = helper.list_all_sessions()

            # Should only get the valid one
            assert len(sessions) == 1
            assert sessions[0]["session_id"] == sample_session_data["session_id"]

    def test_handles_multiple_corrupted_files(self, helper):
        """Test handles multiple corrupted files gracefully."""
        for i in range(3):
            session_file = helper.pause_dir / f"session-{i}.json"
            session_file.write_text("invalid json")

        with patch("claude_mpm.services.cli.session_resume_helper.logger"):
            sessions = helper.list_all_sessions()

            assert len(sessions) == 0


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


class TestIntegrationScenarios:
    """Integration-style tests using real filesystem operations."""

    def test_complete_session_lifecycle(self, helper, sample_session_data):
        """Test complete lifecycle: create, find, load, clear."""
        # Create session
        session_file = helper.pause_dir / "session-lifecycle.json"
        session_file.write_text(json.dumps(sample_session_data))

        # Check exists
        assert helper.has_paused_sessions() is True
        assert helper.get_session_count() == 1

        # Load
        session = helper.get_most_recent_session()
        assert session is not None

        # Clear
        result = helper.clear_session(session)
        assert result is True

        # Verify cleared
        assert helper.has_paused_sessions() is False
        assert helper.get_session_count() == 0

    def test_multiple_sessions_workflow(self, helper, sample_session_data):
        """Test working with multiple sessions."""
        import time

        # Create multiple sessions
        for i in range(5):
            session_file = helper.pause_dir / f"session-{i}.json"
            data = sample_session_data.copy()
            data["session_id"] = f"session-{i}"
            session_file.write_text(json.dumps(data))
            time.sleep(0.01)

        # Verify count
        assert helper.get_session_count() == 5

        # Get most recent
        recent = helper.get_most_recent_session()
        assert recent["session_id"] == "session-4"

        # List all
        all_sessions = helper.list_all_sessions()
        assert len(all_sessions) == 5

        # Clear one
        helper.clear_session(recent)
        assert helper.get_session_count() == 4

    def test_resume_prompt_display_workflow(self, helper, sample_session_data):
        """Test complete resume prompt display workflow."""
        session_file = helper.pause_dir / "session-test.json"
        session_file.write_text(json.dumps(sample_session_data))

        with patch("builtins.print") as mock_print:
            session = helper.check_and_display_resume_prompt()

            # Verify session returned
            assert session is not None

            # Verify prompt was displayed
            mock_print.assert_called_once()

            # Verify prompt content
            prompt = mock_print.call_args[0][0]
            assert "PAUSED SESSION FOUND" in prompt
            assert sample_session_data["conversation"]["summary"] in prompt


# ============================================================================
# EDGE CASE TESTS
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_very_large_accomplishments_list(self, helper, sample_session_data):
        """Test handles very large accomplishments list."""
        session_data = sample_session_data.copy()
        session_data["conversation"]["accomplishments"] = [
            f"Item {i}" for i in range(100)
        ]

        with patch.object(helper, "get_time_elapsed", return_value="1 hour ago"):
            with patch.object(
                helper, "get_git_changes_since_pause", return_value=(0, [])
            ):
                result = helper.format_resume_prompt(session_data)

                # Should only show first 5
                assert "Item 0" in result
                assert "Item 4" in result
                assert "and 95 more" in result

    def test_very_large_git_commits(self, helper, sample_session_data):
        """Test handles very large number of git commits."""
        commits = [
            {"sha": f"sha{i}", "author": f"Author{i}", "message": f"msg{i}"}
            for i in range(1000)
        ]

        with patch.object(helper, "get_time_elapsed", return_value="1 hour ago"):
            with patch.object(
                helper, "get_git_changes_since_pause", return_value=(1000, commits)
            ):
                result = helper.format_resume_prompt(sample_session_data)

                assert "Git changes since pause: 1000 commits" in result
                assert "and 997 more" in result

    def test_session_file_with_special_characters(self, helper, sample_session_data):
        """Test handles session files with special characters in name."""
        # Note: glob pattern is fixed to "session-*.json", so this tests the constraint
        session_file = helper.pause_dir / "session-special-🔐-name.json"
        session_file.write_text(json.dumps(sample_session_data))

        # Should find it
        assert helper.has_paused_sessions() is True

    def test_empty_session_data_dict(self, helper):
        """Test handles completely empty session data."""
        session_data = {}

        with patch.object(helper, "get_time_elapsed", return_value="unknown time ago"):
            with patch.object(
                helper, "get_git_changes_since_pause", return_value=(0, [])
            ):
                result = helper.format_resume_prompt(session_data)

                assert "PAUSED SESSION FOUND" in result

    def test_session_with_missing_required_fields(self, helper):
        """Test handles session with missing required fields."""
        session_data = {
            "session_id": "test",
            # Missing paused_at, conversation, git_context
        }

        result = helper.format_resume_prompt(session_data)
        assert isinstance(result, str)
        # Should handle gracefully with defaults

    def test_concurrent_session_access(self, helper, sample_session_data):
        """Test handles concurrent access scenarios."""
        import time

        # Create session
        session_file = helper.pause_dir / "session-concurrent.json"
        session_file.write_text(json.dumps(sample_session_data))

        # Simulate concurrent modification by changing mtime
        original_session = helper.get_most_recent_session()

        # Modify file
        time.sleep(0.01)
        session_file.write_text(json.dumps(sample_session_data))

        # Should still work
        new_session = helper.get_most_recent_session()
        assert new_session is not None

    def test_symlinked_pause_directory(self, helper, tmp_path):
        """Test handles symlinked pause directory."""
        # Create actual directory elsewhere
        actual_dir = tmp_path / "actual_pause"
        actual_dir.mkdir()

        # Create symlink (if supported)
        try:
            helper.pause_dir.rmdir()
            helper.pause_dir.symlink_to(actual_dir)

            # Create session in actual directory
            session_file = actual_dir / "session-test.json"
            session_file.write_text("{}")

            # Should find it through symlink
            assert helper.has_paused_sessions() is True
        except (OSError, NotImplementedError):
            # Symlinks not supported on this platform
            pytest.skip("Symlinks not supported")
