"""Tests for SessionResumeHelper session listing and selection methods.

Covers the new functionality added in #566:
- format_session_list(): numbered list of sessions with metadata
- resolve_session_by_selection(): select by 1-based index or partial ID

All tests use tmp_path to create real session files so the full
file-scan + sort + load path is exercised without mocking internals.
"""

import json
import time
from pathlib import Path

import pytest

from claude_mpm.services.cli.session_resume_helper import SessionResumeHelper

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_session_json(
    sessions_dir: Path,
    *,
    name: str,
    project_path: str = "/tmp/myproject",
    summary: str = "",
    paused_at: str = "2025-01-15T10:00:00+00:00",
) -> Path:
    """Write a minimal but valid session JSON file and return its path."""
    data = {
        "session_id": name,
        "paused_at": paused_at,
        "project_path": project_path,
        "conversation": {
            "summary": summary,
            "accomplishments": [],
            "next_steps": [],
        },
        "git_context": {},
    }
    path = sessions_dir / f"{name}.json"
    path.write_text(json.dumps(data))
    return path


# ---------------------------------------------------------------------------
# format_session_list
# ---------------------------------------------------------------------------


class TestFormatSessionList:
    def test_empty_directory_returns_friendly_message(self, tmp_path: Path) -> None:
        helper = SessionResumeHelper(project_path=tmp_path)
        result = helper.format_session_list()
        assert "No saved sessions" in result
        assert "/mpm-pause" in result

    def test_single_session_appears_as_index_1(self, tmp_path: Path) -> None:
        sessions_dir = tmp_path / ".claude-mpm" / "sessions"
        sessions_dir.mkdir(parents=True)
        _make_session_json(
            sessions_dir,
            name="session-20250115-100000",
            summary="Working on feature X",
            project_path=str(tmp_path),
        )
        helper = SessionResumeHelper(project_path=tmp_path)
        result = helper.format_session_list()
        assert "1." in result
        assert "20250115-100000" in result
        assert "Working on feature X" in result

    def test_multiple_sessions_numbered_most_recent_first(self, tmp_path: Path) -> None:
        sessions_dir = tmp_path / ".claude-mpm" / "sessions"
        sessions_dir.mkdir(parents=True)
        # Create older session first so mtime ordering is deterministic.
        older = _make_session_json(
            sessions_dir,
            name="session-20250114-080000",
            summary="Older work",
            project_path=str(tmp_path),
            paused_at="2025-01-14T08:00:00+00:00",
        )
        time.sleep(0.01)  # ensure distinct mtime
        newer = _make_session_json(
            sessions_dir,
            name="session-20250115-100000",
            summary="Newer work",
            project_path=str(tmp_path),
            paused_at="2025-01-15T10:00:00+00:00",
        )
        helper = SessionResumeHelper(project_path=tmp_path)
        result = helper.format_session_list()
        lines = result.splitlines()
        # Find numbered entries.
        idx_lines = [
            l for l in lines if l.strip().startswith("1.") or l.strip().startswith("2.")
        ]
        assert len(idx_lines) == 2
        # Index 1 is most recent.
        assert "20250115-100000" in idx_lines[0]
        assert "20250114-080000" in idx_lines[1]

    def test_summary_truncated_at_60_chars(self, tmp_path: Path) -> None:
        sessions_dir = tmp_path / ".claude-mpm" / "sessions"
        sessions_dir.mkdir(parents=True)
        long_summary = "A" * 100
        _make_session_json(
            sessions_dir,
            name="session-20250115-120000",
            summary=long_summary,
            project_path=str(tmp_path),
        )
        helper = SessionResumeHelper(project_path=tmp_path)
        result = helper.format_session_list()
        # 60 A chars + ellipsis character should appear; full 100 chars should not.
        assert "A" * 60 in result
        assert "A" * 61 not in result
        assert "…" in result

    def test_project_name_derived_from_path(self, tmp_path: Path) -> None:
        # tmp_path ends with a unique dir name; project_path can differ.
        sessions_dir = tmp_path / ".claude-mpm" / "sessions"
        sessions_dir.mkdir(parents=True)
        _make_session_json(
            sessions_dir,
            name="session-20250115-120000",
            summary="Test",
            project_path="/home/user/myspecialproject",
        )
        helper = SessionResumeHelper(project_path=tmp_path)
        result = helper.format_session_list()
        assert "myspecialproject" in result

    def test_no_summary_shows_placeholder(self, tmp_path: Path) -> None:
        sessions_dir = tmp_path / ".claude-mpm" / "sessions"
        sessions_dir.mkdir(parents=True)
        _make_session_json(
            sessions_dir,
            name="session-20250115-120000",
            summary="",
            project_path=str(tmp_path),
        )
        helper = SessionResumeHelper(project_path=tmp_path)
        result = helper.format_session_list()
        assert "(no summary)" in result

    def test_resume_hint_shown(self, tmp_path: Path) -> None:
        sessions_dir = tmp_path / ".claude-mpm" / "sessions"
        sessions_dir.mkdir(parents=True)
        _make_session_json(
            sessions_dir,
            name="session-20250115-120000",
            summary="Work",
            project_path=str(tmp_path),
        )
        helper = SessionResumeHelper(project_path=tmp_path)
        result = helper.format_session_list()
        assert "--select" in result


# ---------------------------------------------------------------------------
# resolve_session_by_selection — empty directory
# ---------------------------------------------------------------------------


class TestResolveSelectionEmptyDir:
    def test_no_sessions_returns_none_with_friendly_message(
        self, tmp_path: Path
    ) -> None:
        helper = SessionResumeHelper(project_path=tmp_path)
        session, msg = helper.resolve_session_by_selection("1")
        assert session is None
        assert "No saved sessions" in msg


# ---------------------------------------------------------------------------
# resolve_session_by_selection — by numeric index
# ---------------------------------------------------------------------------


class TestResolveSelectionByIndex:
    @pytest.fixture()
    def two_session_helper(self, tmp_path: Path) -> SessionResumeHelper:
        """Helper with two sessions: index 1 = newest, index 2 = oldest."""
        sessions_dir = tmp_path / ".claude-mpm" / "sessions"
        sessions_dir.mkdir(parents=True)
        _make_session_json(
            sessions_dir,
            name="session-20250114-080000",
            summary="Older session",
            project_path=str(tmp_path),
            paused_at="2025-01-14T08:00:00+00:00",
        )
        time.sleep(0.01)
        _make_session_json(
            sessions_dir,
            name="session-20250115-100000",
            summary="Newer session",
            project_path=str(tmp_path),
            paused_at="2025-01-15T10:00:00+00:00",
        )
        return SessionResumeHelper(project_path=tmp_path)

    def test_select_1_returns_most_recent(
        self, two_session_helper: SessionResumeHelper
    ) -> None:
        session, msg = two_session_helper.resolve_session_by_selection("1")
        assert session is not None
        assert msg == ""
        assert session["session_id"] == "session-20250115-100000"

    def test_select_2_returns_second_most_recent(
        self, two_session_helper: SessionResumeHelper
    ) -> None:
        session, msg = two_session_helper.resolve_session_by_selection("2")
        assert session is not None
        assert msg == ""
        assert session["session_id"] == "session-20250114-080000"

    def test_index_zero_is_out_of_range(
        self, two_session_helper: SessionResumeHelper
    ) -> None:
        session, msg = two_session_helper.resolve_session_by_selection("0")
        assert session is None
        assert "out of range" in msg.lower()

    def test_index_too_large_is_out_of_range(
        self, two_session_helper: SessionResumeHelper
    ) -> None:
        session, msg = two_session_helper.resolve_session_by_selection("99")
        assert session is None
        assert "out of range" in msg.lower()
        assert "2" in msg  # message mentions how many sessions exist

    def test_negative_index_treated_as_out_of_range(
        self, two_session_helper: SessionResumeHelper
    ) -> None:
        session, msg = two_session_helper.resolve_session_by_selection("-1")
        assert session is None
        assert "out of range" in msg.lower()


# ---------------------------------------------------------------------------
# resolve_session_by_selection — by partial ID
# ---------------------------------------------------------------------------


class TestResolveSelectionByPartialId:
    @pytest.fixture()
    def two_session_helper(self, tmp_path: Path) -> SessionResumeHelper:
        sessions_dir = tmp_path / ".claude-mpm" / "sessions"
        sessions_dir.mkdir(parents=True)
        _make_session_json(
            sessions_dir,
            name="session-20250114-080000",
            summary="January 14",
            project_path=str(tmp_path),
            paused_at="2025-01-14T08:00:00+00:00",
        )
        time.sleep(0.01)
        _make_session_json(
            sessions_dir,
            name="session-20250115-100000",
            summary="January 15",
            project_path=str(tmp_path),
            paused_at="2025-01-15T10:00:00+00:00",
        )
        return SessionResumeHelper(project_path=tmp_path)

    def test_unique_partial_id_resolves(
        self, two_session_helper: SessionResumeHelper
    ) -> None:
        # "20250115" uniquely matches session-20250115-100000
        session, msg = two_session_helper.resolve_session_by_selection("20250115")
        assert session is not None
        assert msg == ""
        assert session["session_id"] == "session-20250115-100000"

    def test_date_prefix_resolves_unique_match(
        self, two_session_helper: SessionResumeHelper
    ) -> None:
        session, _msg = two_session_helper.resolve_session_by_selection("20250114")
        assert session is not None
        assert session["session_id"] == "session-20250114-080000"

    def test_ambiguous_partial_id_returns_error(
        self, two_session_helper: SessionResumeHelper
    ) -> None:
        # "2025" matches both sessions.
        session, msg = two_session_helper.resolve_session_by_selection("2025")
        assert session is None
        assert "Ambiguous" in msg
        assert "2025" in msg

    def test_no_match_returns_error(
        self, two_session_helper: SessionResumeHelper
    ) -> None:
        session, msg = two_session_helper.resolve_session_by_selection("99991231")
        assert session is None
        assert "No session matches" in msg

    def test_case_insensitive_match(
        self, two_session_helper: SessionResumeHelper
    ) -> None:
        # Session IDs are lowercase; uppercase input should still match.
        session, _msg = two_session_helper.resolve_session_by_selection(
            "SESSION-20250115"
        )
        assert session is not None
        assert session["session_id"] == "session-20250115-100000"

    def test_partial_id_with_time_component(
        self, two_session_helper: SessionResumeHelper
    ) -> None:
        session, _msg = two_session_helper.resolve_session_by_selection("100000")
        assert session is not None
        assert session["session_id"] == "session-20250115-100000"
