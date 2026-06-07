"""Tests for CWD-invariant PID/log path resolution (issue #701).

WHAT: Verifies that get_pid_file_for_port, _get_default_log_file, and
      UnifiedMonitorDaemon._get_default_pid_file all anchor to the same
      project root regardless of which subdirectory the caller's cwd is,
      and that the resolver is a pure function (no mkdir side-effects).

WHY:  Before the fix, each resolver called Path.cwd() independently.  A
      ``start`` from the project root wrote the PID file to
      ``<root>/.claude-mpm/``, but ``stop``/``status`` from a subdirectory
      resolved a DIFFERENT ``.claude-mpm/``, causing false "not running" and
      orphaned daemons (issue #701).

IMPORTANT: Every test that calls into the resolvers MUST monkeypatch.chdir
to a tmp_path first.  The real repo IS a project with .git and .claude-mpm,
so calling the resolver without chdir would resolve the real repo root and
potentially create real directories.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from claude_mpm.services.monitor.daemon import UnifiedMonitorDaemon
from claude_mpm.services.monitor.daemon_manager import DaemonManager, _find_project_root

# ---------------------------------------------------------------------------
# _find_project_root — unit tests
# ---------------------------------------------------------------------------


class TestFindProjectRoot:
    """Unit tests for the module-level _find_project_root helper."""

    def test_returns_git_root_from_subdir(self, tmp_path: Path, monkeypatch) -> None:
        """Walking up from a subdirectory finds the nearest .git ancestor."""
        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / ".git").mkdir()
        subdir = proj / "src" / "deep"
        subdir.mkdir(parents=True)

        monkeypatch.chdir(subdir)
        result = _find_project_root()
        assert result == proj

    def test_git_wins_over_colocated_claude_mpm(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """.git is the only root marker; .claude-mpm/ colocated with it is ignored as a marker.

        Both .git and .claude-mpm/ are in the same directory.  The function
        still returns that directory because .git is found — the result is
        correct regardless, but we confirm .claude-mpm/ alone does NOT affect
        the walk outcome.
        """
        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / ".git").mkdir()
        (proj / ".claude-mpm").mkdir()

        monkeypatch.chdir(proj)
        result = _find_project_root()
        assert result == proj

    def test_git_ancestor_wins_over_stray_claude_mpm_in_cwd(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """.git ancestor must win even when cwd has a stray .claude-mpm/ dir.

        This is the CORE regression for issue #701: the framework creates
        .claude-mpm/ in the cwd on every CLI invocation (including read-only
        commands like ``monitor status``).  If .claude-mpm/ were a marker, the
        walk would anchor to the cwd (wrong) instead of ascending to the real
        project root that contains .git.

        Scenario:
          tmp_path/proj/.git          ← real project root
          tmp_path/proj/src/deep/     ← cwd when running `monitor status`
          tmp_path/proj/src/deep/.claude-mpm/  ← spuriously created by framework

        Expected: _find_project_root() returns tmp_path/proj  (the .git root)
        Buggy behaviour (old code): returns tmp_path/proj/src/deep (stray .claude-mpm)
        """
        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / ".git").mkdir()
        deep = proj / "src" / "deep"
        deep.mkdir(parents=True)
        # Simulate framework's stray .claude-mpm/ created in subdir cwd
        (deep / ".claude-mpm").mkdir()

        monkeypatch.chdir(deep)
        result = _find_project_root()
        assert result == proj, (
            f"Expected real project root {proj}, got {result}.\n"
            "A stray .claude-mpm/ in the cwd must NOT anchor the walk — "
            "the .git ancestor must win (issue #701 regression guard)."
        )

    def test_pyproject_toml_found_when_no_git(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """pyproject.toml is used as fallback when no .git or .claude-mpm exists."""
        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / "pyproject.toml").touch()
        subdir = proj / "src"
        subdir.mkdir()

        monkeypatch.chdir(subdir)
        result = _find_project_root()
        assert result == proj

    def test_fallback_to_cwd_when_no_marker(self, tmp_path: Path, monkeypatch) -> None:
        """Returns cwd unchanged when no project marker is found (no crash)."""
        bare = tmp_path / "bare"
        bare.mkdir()

        monkeypatch.chdir(bare)
        result = _find_project_root()
        assert result == bare, (
            f"Expected fallback to cwd {bare}, got {result}. "
            "No marker found should return anchor as-is."
        )

    def test_does_not_ascend_past_temp_dir(self, tmp_path: Path, monkeypatch) -> None:
        """The walk must not ascend above tmp_path when there is no marker.

        On macOS tmp_path lives under /private/var/folders/.../T/ which has no
        project markers.  The walk should stop at the OS temp root boundary and
        return the anchor (bare dir), not some ancestor outside the temp tree.
        """
        bare = tmp_path / "no_marker"
        bare.mkdir()

        monkeypatch.chdir(bare)
        result = _find_project_root()

        # The fallback must return the anchor (bare) unchanged — no marker means
        # we return the starting directory, not some parent.
        assert result == bare, (
            f"Expected fallback to anchor {bare}, got {result}. "
            "With no project markers, _find_project_root must return the anchor."
        )

    def test_start_parameter_overrides_cwd(self, tmp_path: Path, monkeypatch) -> None:
        """Passing an explicit start path overrides Path.cwd()."""
        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / ".git").mkdir()

        other = tmp_path / "other"
        other.mkdir()

        # chdir to 'other' which has no marker
        monkeypatch.chdir(other)

        # But pass proj explicitly
        result = _find_project_root(start=proj)
        assert result == proj


# ---------------------------------------------------------------------------
# get_pid_file_for_port — CWD-invariance
# ---------------------------------------------------------------------------


class TestGetPidFileForPortCwdInvariance:
    """get_pid_file_for_port must return the same path from root and subdirs."""

    def test_same_path_from_root_and_subdir(self, tmp_path: Path, monkeypatch) -> None:
        """Path from project root equals path from a deep subdirectory."""
        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / ".git").mkdir()
        subdir = proj / "src" / "deep"
        subdir.mkdir(parents=True)

        monkeypatch.chdir(proj)
        path_from_root = DaemonManager.get_pid_file_for_port(8765)

        monkeypatch.chdir(subdir)
        path_from_subdir = DaemonManager.get_pid_file_for_port(8765)

        assert path_from_root == path_from_subdir, (
            f"Path mismatch:\n  from root:   {path_from_root}\n"
            f"  from subdir: {path_from_subdir}\n"
            "Both must resolve to the same project root (issue #701)."
        )

    def test_both_paths_under_project_claude_mpm(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Resolved path is always under <project>/.claude-mpm/."""
        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / ".git").mkdir()
        subdir = proj / "src" / "deep"
        subdir.mkdir(parents=True)

        monkeypatch.chdir(subdir)
        p = DaemonManager.get_pid_file_for_port(8765)

        assert p.parts[-3] == "proj"
        assert p.parts[-2] == ".claude-mpm"
        assert p.name == "monitor-daemon-8765.pid"

    def test_no_mkdir_side_effect(self, tmp_path: Path, monkeypatch) -> None:
        """Calling get_pid_file_for_port must NOT create .claude-mpm/."""
        bare = tmp_path / "bare"
        bare.mkdir()

        monkeypatch.chdir(bare)
        _ = DaemonManager.get_pid_file_for_port(8765)

        assert not (bare / ".claude-mpm").exists(), (
            "get_pid_file_for_port must be a pure resolver — it must not "
            "create directories (issue #701 regression guard)."
        )

    def test_git_root_with_claude_mpm_subdir_anchors_correctly(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """PID file is under the .git root even when .claude-mpm/ also exists there.

        With .git taking priority, a pre-existing .claude-mpm/ in the same
        directory does not interfere — the result is the same project root.
        Walking from a subdir with NO stray .claude-mpm/ must still land at proj.
        """
        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / ".git").mkdir()
        (proj / ".claude-mpm").mkdir()

        subdir = proj / "sub"
        subdir.mkdir()

        monkeypatch.chdir(subdir)
        p = DaemonManager.get_pid_file_for_port(8765)

        assert p.parent.parent == proj, (
            f"Expected PID file under {proj}/.claude-mpm/, got {p}"
        )

    def test_stray_claude_mpm_in_subdir_does_not_defeat_git_root(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Critical regression: stray .claude-mpm/ in cwd must not defeat ancestor .git root.

        Simulates the exact scenario that caused false "not running" in issue #701:
        - Daemon was STARTED from project root (PID file → proj/.claude-mpm/monitor-daemon-8765.pid)
        - `monitor status` is run from a subdirectory
        - Framework startup creates subdir/.claude-mpm/ BEFORE the PID resolver runs
        - Old code anchored to subdir and returned subdir/.claude-mpm/monitor-daemon-8765.pid → not found
        - Fixed code ignores .claude-mpm/ as a marker and walks up to find .git
        """
        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / ".git").mkdir()
        deep = proj / "src" / "deep"
        deep.mkdir(parents=True)
        # Framework-created stray dir in subdir cwd
        (deep / ".claude-mpm").mkdir()

        monkeypatch.chdir(deep)
        p = DaemonManager.get_pid_file_for_port(8765)

        assert p.parent.parent == proj, (
            f"Expected PID file under {proj}/.claude-mpm/, got {p}.\n"
            "Stray .claude-mpm/ in subdir cwd must NOT anchor the resolver "
            "(issue #701 regression guard)."
        )


# ---------------------------------------------------------------------------
# Three-resolver consistency
# ---------------------------------------------------------------------------


class TestThreeResolversAgree:
    """All three resolvers must share the same project root."""

    def test_pid_resolver_log_resolver_and_daemon_agree(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """get_pid_file_for_port, log resolver parent, and UnifiedMonitorDaemon all agree."""
        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / ".git").mkdir()
        subdir = proj / "a" / "b"
        subdir.mkdir(parents=True)

        monkeypatch.chdir(subdir)

        pid_path = DaemonManager.get_pid_file_for_port(8765)
        pid_root = (
            pid_path.parent.parent
        )  # strip monitor-daemon-8765.pid and .claude-mpm

        mgr = DaemonManager(port=8765)
        log_path = mgr._get_default_log_file()
        log_root = log_path.parent.parent.parent  # strip filename, logs/, .claude-mpm/

        daemon = UnifiedMonitorDaemon(port=8765)
        daemon_pid_path = Path(daemon._get_default_pid_file())
        daemon_pid_root = daemon_pid_path.parent.parent

        assert pid_root == proj, f"PID resolver root {pid_root} != {proj}"
        assert log_root == proj, f"Log resolver root {log_root} != {proj}"
        assert daemon_pid_root == proj, f"Daemon pid root {daemon_pid_root} != {proj}"

    def test_daemon_pid_file_delegates_to_static_resolver(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """UnifiedMonitorDaemon._get_default_pid_file must equal get_pid_file_for_port."""
        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / ".git").mkdir()

        monkeypatch.chdir(proj)

        static_path = DaemonManager.get_pid_file_for_port(8765)
        daemon = UnifiedMonitorDaemon(port=8765)
        daemon_path = Path(daemon._get_default_pid_file())

        assert daemon_path == static_path, (
            f"UnifiedMonitorDaemon._get_default_pid_file() returned {daemon_path}\n"
            f"but DaemonManager.get_pid_file_for_port(8765) returned {static_path}\n"
            "They must be equal (issue #701)."
        )


# ---------------------------------------------------------------------------
# socketio wrapper still agrees (regression guard for #695)
# ---------------------------------------------------------------------------


class TestSocketioDaemonWrapperStillAgrees:
    """Confirm the socketio wrapper's _pid_file_for_port delegates to DaemonManager."""

    @pytest.mark.parametrize("port", [8765, 8791, 9001, 19765])
    def test_wrapper_equals_daemon_manager(
        self, port: int, tmp_path: Path, monkeypatch
    ) -> None:
        """_pid_file_for_port(port) must equal DaemonManager.get_pid_file_for_port(port)."""
        from claude_mpm.scripts.socketio_daemon import _pid_file_for_port

        monkeypatch.chdir(tmp_path)

        wrapper_path = _pid_file_for_port(port)
        daemon_path = DaemonManager.get_pid_file_for_port(port)

        assert wrapper_path == daemon_path, (
            f"Port {port} path mismatch:\n"
            f"  wrapper: {wrapper_path}\n"
            f"  daemon:  {daemon_path}"
        )
