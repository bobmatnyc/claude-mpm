"""Tests for stale-worktree pruning in SessionPauseManager (issue #892).

WHAT: Exercises ``SessionPauseManager.prune_stale_worktrees()`` and the
``prune_worktrees`` parameter of ``create_pause_session()`` using real
temporary git repositories and real worktrees.

WHY: Pruning decisions are safety-critical (wrong removal = data loss).
These tests build real git state (commits, dirty files, locks) so the
classification logic is validated against actual git behaviour rather than
mocks.

Run in serial mode to avoid cross-test git filesystem collisions:
    uv run pytest -p no:xdist tests/test_session_pause_prune_worktrees.py -v
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path  # noqa: TC003 - Path is used at runtime in function signatures

import pytest

from claude_mpm.services.cli.session_pause_manager import SessionPauseManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_git_repo(tmp_path: Path) -> Path:
    """Create a minimal git repo with one commit and return its path."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "test@example.com"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "Test"],
        check=True,
        capture_output=True,
    )
    (repo / "README.md").write_text("# test\n")
    subprocess.run(
        ["git", "-C", str(repo), "add", "."], check=True, capture_output=True
    )
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "initial"],
        check=True,
        capture_output=True,
    )
    return repo


def _add_managed_worktree(repo: Path, name: str) -> Path:
    """Add a worktree under <repo>/.claude/worktrees/<name> and return its path."""
    wt_dir = repo / ".claude" / "worktrees"
    wt_dir.mkdir(parents=True, exist_ok=True)
    wt_path = wt_dir / name
    branch = f"worktree-{name}"
    result = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "worktree",
            "add",
            "-b",
            branch,
            str(wt_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"Failed to create worktree {name}: {result.stderr}"
    return wt_path


def _make_pause_manager(repo: Path) -> SessionPauseManager:
    """Return a SessionPauseManager rooted at *repo*."""
    return SessionPauseManager(project_path=repo)


# ---------------------------------------------------------------------------
# Fixture: one fresh repo per test
# ---------------------------------------------------------------------------


@pytest.fixture()
def repo(tmp_path: Path) -> Path:  # type: ignore[type-arg]
    """Temporary git repo with .claude/worktrees/ parent created."""
    r = _make_git_repo(tmp_path)
    (r / ".claude" / "worktrees").mkdir(parents=True, exist_ok=True)
    yield r
    # Cleanup: remove all worktrees then the repo
    _force_cleanup_all_worktrees(r)
    shutil.rmtree(str(r), ignore_errors=True)


def _force_cleanup_all_worktrees(repo: Path) -> None:
    """Best-effort teardown: remove all linked worktrees under .claude/worktrees/."""
    wt_dir = repo / ".claude" / "worktrees"
    if not wt_dir.is_dir():
        return
    for child in wt_dir.iterdir():
        if child.is_dir():
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo),
                    "worktree",
                    "remove",
                    "--force",
                    str(child),
                ],
                capture_output=True,
                check=False,
            )
    subprocess.run(
        ["git", "-C", str(repo), "worktree", "prune"],
        capture_output=True,
        check=False,
    )


# ---------------------------------------------------------------------------
# Test 1: clean + merged worktree is pruned
# ---------------------------------------------------------------------------


class TestCleanMergedWorktree:
    """A worktree with no local changes and no unmerged commits is pruned."""

    def test_clean_merged_worktree_is_pruned(self, repo: Path) -> None:
        wt = _add_managed_worktree(repo, "clean-merged")
        assert wt.is_dir()

        mgr = _make_pause_manager(repo)
        summary = mgr.prune_stale_worktrees()

        assert summary["pruned_count"] == 1, (
            f"Expected 1 pruned, got {summary['pruned_count']}. "
            f"Worktrees: {summary['worktrees']}"
        )
        assert summary["preserved_count"] == 0
        assert not wt.exists(), "Clean merged worktree should have been removed"

    def test_prune_summary_contains_decision(self, repo: Path) -> None:
        _add_managed_worktree(repo, "clean-for-decision-check")

        mgr = _make_pause_manager(repo)
        summary = mgr.prune_stale_worktrees()

        assert len(summary["worktrees"]) == 1
        wt_record = summary["worktrees"][0]
        assert wt_record["action"] == "prune"
        assert "reason" in wt_record


# ---------------------------------------------------------------------------
# Test 2: worktree with uncommitted changes is preserved
# ---------------------------------------------------------------------------


class TestUncommittedChangesPreserved:
    """A worktree with uncommitted tracked changes must be preserved."""

    def test_uncommitted_changes_preserved(self, repo: Path) -> None:
        wt = _add_managed_worktree(repo, "dirty")
        # Stage a modification but do NOT commit.
        (wt / "work.txt").write_text("unsaved work\n")
        subprocess.run(
            ["git", "-C", str(wt), "add", "work.txt"],
            check=True,
            capture_output=True,
        )

        mgr = _make_pause_manager(repo)
        summary = mgr.prune_stale_worktrees()

        assert summary["preserved_count"] == 1
        assert summary["pruned_count"] == 0
        assert wt.exists(), "Dirty worktree must not be removed"
        wt_record = summary["worktrees"][0]
        assert wt_record["action"] == "preserve"
        assert (
            "uncommitted" in wt_record["reason"].lower()
            or "untracked" in wt_record["reason"].lower()
        )


# ---------------------------------------------------------------------------
# Test 3: worktree with untracked files is preserved
# ---------------------------------------------------------------------------


class TestUntrackedFilesPreserved:
    """A worktree with untracked files must be preserved."""

    def test_untracked_files_preserved(self, repo: Path) -> None:
        wt = _add_managed_worktree(repo, "untracked")
        # Write a file but do NOT add or commit it.
        (wt / "untracked_file.py").write_text("# untracked\n")

        mgr = _make_pause_manager(repo)
        summary = mgr.prune_stale_worktrees()

        assert summary["preserved_count"] == 1
        assert summary["pruned_count"] == 0
        assert wt.exists(), "Worktree with untracked files must not be removed"
        wt_record = summary["worktrees"][0]
        assert wt_record["action"] == "preserve"


# ---------------------------------------------------------------------------
# Test 4: worktree with unpushed/unmerged commits is preserved
# ---------------------------------------------------------------------------


class TestUnmergedCommitsPreserved:
    """A worktree with commits not on the main branch must be preserved."""

    def test_unmerged_commits_preserved(self, repo: Path) -> None:
        wt = _add_managed_worktree(repo, "unmerged")
        # Add a commit that exists only on the worktree branch.
        (wt / "feature.txt").write_text("new feature\n")
        subprocess.run(
            ["git", "-C", str(wt), "add", "feature.txt"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(wt), "commit", "-m", "add feature"],
            check=True,
            capture_output=True,
        )

        mgr = _make_pause_manager(repo)
        summary = mgr.prune_stale_worktrees()

        assert summary["preserved_count"] == 1
        assert summary["pruned_count"] == 0
        assert wt.exists(), "Worktree with unmerged commits must not be removed"
        wt_record = summary["worktrees"][0]
        assert wt_record["action"] == "preserve"
        assert (
            "commit" in wt_record["reason"].lower()
            or "merged" in wt_record["reason"].lower()
        )


# ---------------------------------------------------------------------------
# Test 5: locked worktree is preserved
# ---------------------------------------------------------------------------


class TestLockedWorktreePreserved:
    """A worktree listed as locked by git must be preserved."""

    def test_locked_worktree_preserved(self, repo: Path) -> None:
        wt = _add_managed_worktree(repo, "locked")

        # Lock the worktree via git.
        lock_result = subprocess.run(
            ["git", "-C", str(repo), "worktree", "lock", str(wt)],
            capture_output=True,
            text=True,
            check=False,
        )
        if lock_result.returncode != 0:
            pytest.skip(
                f"git worktree lock not supported on this system: {lock_result.stderr}"
            )

        mgr = _make_pause_manager(repo)
        summary = mgr.prune_stale_worktrees()

        assert summary["preserved_count"] == 1
        assert summary["pruned_count"] == 0
        wt_record = summary["worktrees"][0]
        assert wt_record["action"] == "preserve"
        assert "locked" in wt_record["reason"].lower()

        # Unlock for teardown.
        subprocess.run(
            ["git", "-C", str(repo), "worktree", "unlock", str(wt)],
            capture_output=True,
            check=False,
        )


# ---------------------------------------------------------------------------
# Test 6: no .claude/worktrees/ dir → no-op
# ---------------------------------------------------------------------------


class TestNoWorktreeDir:
    """When .claude/worktrees/ does not exist, pruning is a no-op."""

    def test_no_worktrees_dir_is_noop(self, tmp_path: Path) -> None:
        repo = _make_git_repo(tmp_path)
        # Deliberately do NOT create .claude/worktrees/.

        mgr = _make_pause_manager(repo)
        summary = mgr.prune_stale_worktrees()

        assert summary["pruned_count"] == 0
        assert summary["preserved_count"] == 0
        assert summary["worktrees"] == []

        shutil.rmtree(str(repo), ignore_errors=True)


# ---------------------------------------------------------------------------
# Test 7: administrative stale entry (dir deleted) → cleaned via prune
# ---------------------------------------------------------------------------


class TestAdminStaleEntryCleaned:
    """An admin entry whose directory was manually deleted is cleaned by git worktree prune."""

    def test_admin_stale_entry_cleaned(self, repo: Path) -> None:
        wt = _add_managed_worktree(repo, "stale-admin")
        assert wt.is_dir()

        # Manually delete the worktree directory (simulating a partial cleanup).
        shutil.rmtree(str(wt))
        assert not wt.exists()

        mgr = _make_pause_manager(repo)
        summary = mgr.prune_stale_worktrees()

        # The admin entry is handled by 'git worktree prune'; our classifier
        # will preserve it (dir missing → preserve), but prune's admin_pruned
        # flag should be True.
        assert summary["admin_pruned"] is True

        # Verify git no longer lists the deleted worktree.
        list_result = subprocess.run(
            ["git", "-C", str(repo), "worktree", "list"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert str(wt) not in list_result.stdout


# ---------------------------------------------------------------------------
# Test 8: main working tree is never touched
# ---------------------------------------------------------------------------


class TestMainWorkingTreeUntouched:
    """The main working tree must never appear in the pruned list."""

    def test_main_tree_not_pruned(self, repo: Path) -> None:
        # Add a clean worktree and also ensure the main tree has no changes.
        _add_managed_worktree(repo, "candidate")

        mgr = _make_pause_manager(repo)
        summary = mgr.prune_stale_worktrees()

        pruned_paths = [
            wt["path"] for wt in summary["worktrees"] if wt.get("action") == "prune"
        ]
        assert str(repo.resolve()) not in pruned_paths, (
            "Main working tree must never be in the pruned set"
        )

    def test_only_managed_worktrees_considered(self, repo: Path) -> None:
        """Worktrees outside .claude/worktrees/ are never considered."""
        # Create a worktree OUTSIDE the managed directory.
        outside_dir = repo.parent / "outside-wt"
        subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "worktree",
                "add",
                "-b",
                "outside-branch",
                str(outside_dir),
            ],
            check=True,
            capture_output=True,
        )

        try:
            mgr = _make_pause_manager(repo)
            summary = mgr.prune_stale_worktrees()

            all_paths = [wt["path"] for wt in summary["worktrees"]]
            assert str(outside_dir.resolve()) not in all_paths, (
                "Worktrees outside .claude/worktrees/ must not be considered"
            )
        finally:
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo),
                    "worktree",
                    "remove",
                    "--force",
                    str(outside_dir),
                ],
                capture_output=True,
                check=False,
            )
            subprocess.run(
                ["git", "-C", str(repo), "worktree", "prune"],
                capture_output=True,
                check=False,
            )
            shutil.rmtree(str(outside_dir), ignore_errors=True)


# ---------------------------------------------------------------------------
# Test 9: multiple worktrees — mixed outcomes
# ---------------------------------------------------------------------------


class TestMixedWorktrees:
    """Clean and dirty worktrees co-exist; only the clean one is pruned."""

    def test_mixed_worktrees(self, repo: Path) -> None:
        clean_wt = _add_managed_worktree(repo, "clean")
        dirty_wt = _add_managed_worktree(repo, "dirty")

        # Make dirty_wt have uncommitted changes.
        (dirty_wt / "draft.py").write_text("work in progress\n")
        subprocess.run(
            ["git", "-C", str(dirty_wt), "add", "draft.py"],
            check=True,
            capture_output=True,
        )

        mgr = _make_pause_manager(repo)
        summary = mgr.prune_stale_worktrees()

        assert summary["pruned_count"] == 1
        assert summary["preserved_count"] == 1
        assert not clean_wt.exists(), "Clean worktree should be pruned"
        assert dirty_wt.exists(), "Dirty worktree should be preserved"


# ---------------------------------------------------------------------------
# Test 10: create_pause_session integrates pruning
# ---------------------------------------------------------------------------


class TestCreatePauseSessionIntegration:
    """create_pause_session triggers pruning by default and respects prune_worktrees=False."""

    def test_create_pause_session_prunes_by_default(self, repo: Path) -> None:
        wt = _add_managed_worktree(repo, "session-clean")
        assert wt.is_dir()

        mgr = _make_pause_manager(repo)
        mgr.create_pause_session(message="integration test")

        assert not wt.exists(), (
            "Stale worktree should have been pruned by create_pause_session"
        )
        assert mgr._last_prune_summary is not None
        assert mgr._last_prune_summary["pruned_count"] == 1

    def test_create_pause_session_no_prune_flag(self, repo: Path) -> None:
        wt = _add_managed_worktree(repo, "session-skip-prune")
        assert wt.is_dir()

        mgr = _make_pause_manager(repo)
        mgr.create_pause_session(message="no prune", prune_worktrees=False)

        assert wt.exists(), "Worktree must not be pruned when prune_worktrees=False"
        assert mgr._last_prune_summary is None

    def test_create_pause_session_returns_session_id(self, repo: Path) -> None:
        mgr = _make_pause_manager(repo)
        session_id = mgr.create_pause_session(message="just testing")
        assert session_id.startswith("session-")

    def test_prune_failure_is_non_fatal(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Pruning failure must not prevent the session from being created."""

        def _boom(*args: object, **kwargs: object) -> None:
            raise RuntimeError("simulated prune failure")

        monkeypatch.setattr(
            "claude_mpm.services.cli.session_pause_manager.SessionPauseManager.prune_stale_worktrees",
            _boom,
        )
        mgr = _make_pause_manager(repo)
        # Must not raise.
        session_id = mgr.create_pause_session(message="prune fail test")
        assert session_id.startswith("session-")


# ---------------------------------------------------------------------------
# Test 11: not a git repo → no-op
# ---------------------------------------------------------------------------


class TestNotAGitRepo:
    """When project_path is not inside a git repo, pruning is a no-op."""

    def test_non_git_dir_is_noop(self, tmp_path: Path) -> None:
        non_git = tmp_path / "not-a-repo"
        non_git.mkdir()

        mgr = SessionPauseManager(project_path=non_git)
        summary = mgr.prune_stale_worktrees()

        assert summary["pruned_count"] == 0
        assert summary["preserved_count"] == 0
        assert summary["worktrees"] == []
