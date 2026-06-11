"""Tests for session-dir permission handling in SessionResumeHelper (Bug #735).

A sandbox/permission-denied read of ``.claude-mpm/sessions/`` must NOT be
silently treated as "no sessions". ``check_session_dir_access()`` distinguishes
*denied* from *empty/absent*, and ``check_and_display_resume_prompt()`` surfaces
an explicit warning on denial instead of returning a false "nothing to resume".
"""

from __future__ import annotations

from pathlib import Path

import pytest

from claude_mpm.services.cli.session_resume_helper import SessionResumeHelper


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    return fake_home


def _make_helper(tmp_path) -> SessionResumeHelper:
    project = tmp_path / "project"
    project.mkdir()
    return SessionResumeHelper(project_path=project)


def test_absent_dir_is_accessible_not_error(tmp_path):
    """A never-created session dir is 'accessible' (empty), not an error."""
    helper = _make_helper(tmp_path)
    assert not helper.pause_dir.exists()
    accessible, err = helper.check_session_dir_access()
    assert accessible is True
    assert err is None


def test_empty_dir_is_accessible(tmp_path):
    """An existing-but-empty session dir reads cleanly (accessible, no error)."""
    helper = _make_helper(tmp_path)
    helper.pause_dir.mkdir(parents=True)
    accessible, err = helper.check_session_dir_access()
    assert accessible is True
    assert err is None


def test_permission_denied_is_reported_distinctly(tmp_path, monkeypatch):
    """A PermissionError on read yields (False, message) — NOT a silent empty."""
    helper = _make_helper(tmp_path)
    helper.pause_dir.mkdir(parents=True)

    def boom(self):
        raise PermissionError(13, "Permission denied")

    # Patch Path.iterdir so the helper's read raises like a sandbox denial.
    monkeypatch.setattr(Path, "iterdir", boom)

    accessible, err = helper.check_session_dir_access()
    assert accessible is False
    assert err is not None
    assert "Permission denied" in err
    # Must explicitly NOT be conflated with "no sessions".
    assert "not the same as 'no sessions'" in err.lower()


def test_resume_prompt_warns_on_denied_dir(tmp_path, monkeypatch, capsys):
    """check_and_display_resume_prompt surfaces a warning, returns None on deny.

    This is the user-facing guarantee: a denied read does not masquerade as
    "no paused sessions found".
    """
    helper = _make_helper(tmp_path)
    helper.pause_dir.mkdir(parents=True)

    monkeypatch.setattr(
        helper,
        "check_session_dir_access",
        lambda: (False, "Permission denied reading session directory ..."),
    )

    # has_paused_sessions must NOT even be consulted on a denied dir — guard it.
    monkeypatch.setattr(
        helper,
        "has_paused_sessions",
        lambda: pytest.fail("should not check sessions when dir is unreadable"),
    )

    result = helper.check_and_display_resume_prompt()
    out = capsys.readouterr().out
    assert result is None
    assert "Could not read the session directory" in out
    assert "NOT the same as 'no sessions found'" in out


def test_resume_prompt_proceeds_when_accessible_but_empty(tmp_path, monkeypatch):
    """When accessible and empty, behaviour is unchanged: returns None quietly."""
    helper = _make_helper(tmp_path)
    helper.pause_dir.mkdir(parents=True)
    # Accessible path -> falls through to the normal has_paused_sessions check.
    assert helper.check_session_dir_access() == (True, None)
    result = helper.check_and_display_resume_prompt()
    assert result is None
