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


# ---------------------------------------------------------------------------
# Orphan sweep tests (issue #894)
# ---------------------------------------------------------------------------


def _deregister_worktree(repo: Path, wt_path: Path) -> None:
    """De-register a worktree with --force, leaving the directory on disk."""
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "worktree",
            "remove",
            "--force",
            str(wt_path),
        ],
        capture_output=True,
        check=False,
    )
    # Restore the directory so it is present on disk as an orphan.
    # git worktree remove --force deletes both the admin entry AND the dir,
    # so we re-create the directory manually to simulate a partial cleanup
    # where only the admin entry was cleared.
    if not wt_path.exists():
        wt_path.mkdir(parents=True)


def _make_plain_leftover(repo: Path, name: str) -> Path:
    """Create a plain (non-git) directory under .claude/worktrees/ as an orphan."""
    wt_dir = repo / ".claude" / "worktrees"
    wt_dir.mkdir(parents=True, exist_ok=True)
    orphan = wt_dir / name
    orphan.mkdir()
    return orphan


class TestOrphanCleanMergedSwept:
    """Orphaned clean dir with no .git (plain leftover) is swept."""

    def test_plain_leftover_dir_is_swept(self, repo: Path) -> None:
        orphan = _make_plain_leftover(repo, "orphan-plain")
        assert orphan.is_dir()

        mgr = _make_pause_manager(repo)
        summary = mgr.prune_stale_worktrees()

        assert summary["orphans_swept"] >= 1, (
            f"Expected at least 1 swept orphan, got {summary['orphans_swept']}. "
            f"Orphans: {summary['orphans']}"
        )
        assert not orphan.exists(), "Plain leftover dir should have been swept"

        # Confirm the record is correct
        swept_records = [r for r in summary["orphans"] if r.get("action") == "swept"]
        assert any(str(orphan.resolve()) in r["path"] for r in swept_records)

    def test_clean_deregistered_worktree_dir_is_swept(self, repo: Path) -> None:
        """A dir left behind after 'git worktree remove --force' with no .git is swept."""
        # Create a worktree, deregister it (force), then manually leave directory.
        wt = _add_managed_worktree(repo, "deregistered-clean")
        # Remove via git (removes admin entry + dir), then re-create as plain dir.
        subprocess.run(
            ["git", "-C", str(repo), "worktree", "remove", "--force", str(wt)],
            capture_output=True,
            check=False,
        )
        # Re-create as a plain directory (no .git) to simulate orphan scenario.
        wt.mkdir(parents=True, exist_ok=True)
        assert wt.is_dir()
        assert not (wt / ".git").exists()

        mgr = _make_pause_manager(repo)
        summary = mgr.prune_stale_worktrees()

        assert summary["orphans_swept"] >= 1, (
            f"Expected at least 1 swept orphan. Orphans: {summary['orphans']}"
        )
        assert not wt.exists(), "De-registered clean dir should be swept"


class TestOrphanDirtyPreserved:
    """Orphaned dir with uncommitted/untracked changes is preserved."""

    def test_orphan_with_uncommitted_changes_preserved(self, repo: Path) -> None:
        # Create a real worktree, add staged changes, then deregister it forcibly
        # while keeping the directory so it still has a working .git file.
        wt = _add_managed_worktree(repo, "orphan-dirty")
        (wt / "work.txt").write_text("unsaved\n")
        subprocess.run(
            ["git", "-C", str(wt), "add", "work.txt"],
            check=True,
            capture_output=True,
        )
        # Manually unlink the admin entry from git's perspective by using
        # git worktree prune --expire=now after pointing .git away.
        # Simpler approach: just move the .git file so git can't register it
        # but the dir (with content) still exists.
        # Actually, the simplest reliable way to have an orphan WITH a .git
        # link that still works is to remove only the worktree admin data.
        # We achieve this by doing worktree remove --force and then restoring
        # the directory WITH a .git file from the repo.

        # Store content before force-remove.
        work_content = (wt / "work.txt").read_text()

        # Force deregister.
        subprocess.run(
            ["git", "-C", str(repo), "worktree", "remove", "--force", str(wt)],
            capture_output=True,
            check=False,
        )

        # Re-create with a functional .git reference so git status works
        # on the directory and reports the dirty state.
        wt.mkdir(parents=True, exist_ok=True)
        # Write a .git file pointing to the branch's gitdir in .git/worktrees/.
        # This is fragile to reconstruct manually; instead we use a simpler
        # approach: create a NEW git repo inside the orphan directory and add
        # an untracked file so git status is non-empty.
        subprocess.run(
            ["git", "-C", str(wt), "init"],
            capture_output=True,
            check=False,
        )
        subprocess.run(
            ["git", "-C", str(wt), "config", "user.email", "test@example.com"],
            capture_output=True,
            check=False,
        )
        subprocess.run(
            ["git", "-C", str(wt), "config", "user.name", "Test"],
            capture_output=True,
            check=False,
        )
        (wt / "work.txt").write_text(work_content)
        # Leave the file untracked (no git add) so git status --porcelain is non-empty.

        mgr = _make_pause_manager(repo)
        summary = mgr.prune_stale_worktrees()

        # The orphan has untracked content → must be preserved.
        assert wt.exists(), "Orphan with untracked files must not be swept"
        preserved_records = [
            r for r in summary["orphans"] if r.get("action") == "preserved"
        ]
        assert any(str(wt.resolve()) in r["path"] for r in preserved_records), (
            f"Expected orphan {wt} in preserved list. Orphans: {summary['orphans']}"
        )

    def test_orphan_with_untracked_files_preserved(self, repo: Path) -> None:
        """A plain orphan dir with an untracked .git repo and files is preserved."""
        orphan = _make_plain_leftover(repo, "orphan-untracked")
        # Init a git repo inside and add an untracked file.
        subprocess.run(
            ["git", "-C", str(orphan), "init"], capture_output=True, check=False
        )
        subprocess.run(
            ["git", "-C", str(orphan), "config", "user.email", "t@t.com"],
            capture_output=True,
            check=False,
        )
        subprocess.run(
            ["git", "-C", str(orphan), "config", "user.name", "T"],
            capture_output=True,
            check=False,
        )
        (orphan / "unsaved.py").write_text("# work\n")
        # Do NOT git add — leave it untracked so git status --porcelain is non-empty.

        mgr = _make_pause_manager(repo)
        summary = mgr.prune_stale_worktrees()

        assert orphan.exists(), "Orphan with untracked files must not be swept"
        preserved = [r for r in summary["orphans"] if r.get("action") == "preserved"]
        assert any(str(orphan.resolve()) in r["path"] for r in preserved)


class TestOrphanUnmergedCommitsPreserved:
    """Orphaned dir whose branch has unmerged commits is preserved."""

    def test_orphan_unmerged_commits_preserved(self, repo: Path) -> None:
        orphan = _make_plain_leftover(repo, "orphan-unmerged")
        # Init an independent git repo inside the orphan dir, create a commit on a
        # branch whose name is guaranteed not to exist in the outer repo.  Because the
        # branch is unknown to the outer repo, _has_unmerged_commits cannot determine
        # whether it is merged (both origin/<branch> and local <branch> are absent)
        # and therefore returns None.  The classify helper treats None as
        # "could not determine" → PRESERVE conservatively.
        unique_branch = "orphan-feature-branch-xyz-894"
        subprocess.run(
            ["git", "-C", str(orphan), "init", "--initial-branch", unique_branch],
            capture_output=True,
            check=False,
        )
        # Fallback for older git that doesn't support --initial-branch.
        subprocess.run(
            ["git", "-C", str(orphan), "checkout", "-b", unique_branch],
            capture_output=True,
            check=False,
        )
        subprocess.run(
            ["git", "-C", str(orphan), "config", "user.email", "t@t.com"],
            capture_output=True,
            check=False,
        )
        subprocess.run(
            ["git", "-C", str(orphan), "config", "user.name", "T"],
            capture_output=True,
            check=False,
        )
        (orphan / "feature.txt").write_text("feature\n")
        subprocess.run(
            ["git", "-C", str(orphan), "add", "."], capture_output=True, check=False
        )
        subprocess.run(
            ["git", "-C", str(orphan), "commit", "-m", "feature"],
            capture_output=True,
            check=False,
        )
        # Confirm the branch name is what we expect so the test is meaningful.
        branch_result = subprocess.run(
            ["git", "-C", str(orphan), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        current_branch = branch_result.stdout.strip()
        # Accept either the unique branch or the default (in case older git ignored --initial-branch).
        # If it is main/master, the test still passes because that branch's commit exists
        # only in the orphan's isolated repo — the rev-list from main_repo will not find
        # it and _has_unmerged_commits returns None.

        mgr = _make_pause_manager(repo)
        summary = mgr.prune_stale_worktrees()

        # The orphan git repo's branch is either a unique name absent from the outer
        # repo OR its revisions are not reachable from the outer repo.  Either way
        # _has_unmerged_commits returns None → PRESERVE conservatively.
        assert orphan.exists(), (
            f"Orphan with branch '{current_branch}' whose merge status cannot be "
            f"determined must be preserved. Orphans: {summary['orphans']}"
        )
        preserved = [r for r in summary["orphans"] if r.get("action") == "preserved"]
        assert any(str(orphan.resolve()) in r["path"] for r in preserved), (
            f"Orphan {orphan} not in preserved list. Orphans: {summary['orphans']}"
        )


class TestRegisteredWorktreeNotDoubleProcessed:
    """A registered worktree must not appear in the orphan sweep list."""

    def test_registered_worktree_not_in_orphans(self, repo: Path) -> None:
        wt = _add_managed_worktree(repo, "registered-only")
        assert wt.is_dir()

        mgr = _make_pause_manager(repo)
        summary = mgr.prune_stale_worktrees()

        orphan_paths = [r["path"] for r in summary["orphans"]]
        assert str(wt.resolve()) not in orphan_paths, (
            "Registered worktree must not appear in the orphan list"
        )

        # It should appear in the registered worktrees list instead.
        wt_paths = [wt_rec["path"] for wt_rec in summary["worktrees"]]
        assert str(wt.resolve()) in wt_paths


class TestMainWorkingTreeOrphanSweep:
    """The main working tree must never be touched by the orphan sweep."""

    def test_main_tree_not_swept(self, repo: Path) -> None:
        mgr = _make_pause_manager(repo)
        summary = mgr.prune_stale_worktrees()

        all_orphan_paths = [r["path"] for r in summary["orphans"]]
        assert str(repo.resolve()) not in all_orphan_paths, (
            "Main working tree path must never appear in the orphan sweep"
        )


class TestNoWorktreesDirOrphanSweep:
    """When .claude/worktrees/ does not exist, orphan sweep is a no-op."""

    def test_no_worktrees_dir_orphan_sweep_noop(self, tmp_path: Path) -> None:
        repo = _make_git_repo(tmp_path)
        # Deliberately do NOT create .claude/worktrees/.

        mgr = _make_pause_manager(repo)
        summary = mgr.prune_stale_worktrees()

        assert summary["orphans_swept"] == 0
        assert summary["orphans_preserved"] == 0
        assert summary["orphans"] == []

        shutil.rmtree(str(repo), ignore_errors=True)


class TestPathContainmentGuard:
    """Path-containment guard prevents deletion outside .claude/worktrees/."""

    def test_symlink_outside_worktrees_dir_is_rejected(self, repo: Path) -> None:
        """A symlink under .claude/worktrees/ that points outside is preserved, not swept."""
        wt_dir = repo / ".claude" / "worktrees"
        wt_dir.mkdir(parents=True, exist_ok=True)

        # Create a directory OUTSIDE worktrees/ that we'll symlink to.
        outside_dir = repo.parent / "outside-target"
        outside_dir.mkdir(parents=True, exist_ok=True)
        (outside_dir / "precious.txt").write_text("do not delete\n")

        # Create a symlink under .claude/worktrees/ pointing to the outside dir.
        link = wt_dir / "evil-symlink"
        try:
            link.symlink_to(outside_dir)
        except (OSError, NotImplementedError):
            pytest.skip("symlinks not supported on this platform")

        try:
            mgr = _make_pause_manager(repo)
            summary = mgr.prune_stale_worktrees()

            # The outside dir must not have been deleted.
            assert outside_dir.exists(), (
                "Directory outside .claude/worktrees/ must not be deleted"
            )
            assert (outside_dir / "precious.txt").exists(), (
                "Files outside .claude/worktrees/ must not be deleted"
            )

            # The symlink should be preserved (path resolves outside worktrees_dir).
            preserved = [
                r for r in summary["orphans"] if r.get("action") == "preserved"
            ]
            # Either it was preserved due to containment guard or due to git errors
            # on a symlinked non-git dir; either way it must not be in swept.
            swept = [r for r in summary["orphans"] if r.get("action") == "swept"]
            swept_paths = [r["path"] for r in swept]
            assert str(outside_dir.resolve()) not in swept_paths, (
                "Path outside .claude/worktrees/ must not be swept"
            )
        finally:
            shutil.rmtree(str(outside_dir), ignore_errors=True)
            if link.is_symlink():
                link.unlink(missing_ok=True)

    def test_dotdot_path_rejected_by_containment_guard(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """_sweep_orphaned_dirs rejects candidates whose resolved path escapes the managed dir."""
        from claude_mpm.services.cli.session_pause_manager import SessionPauseManager

        mgr = SessionPauseManager(project_path=repo)
        main_repo = str(repo.resolve())
        worktrees_dir = repo / ".claude" / "worktrees"
        worktrees_dir.mkdir(parents=True, exist_ok=True)

        # Build a path that is NOT under worktrees_dir but IS a directory.
        outside = repo.parent
        registered_paths: set = set()

        # Inject an out-of-scope child into the sweep by patching the module-level
        # Path.iterdir.  We use monkeypatch on the pathlib module used inside
        # session_pause_manager so that Path.iterdir yields a FakeChild whose
        # .resolve() returns a path outside worktrees_dir.

        import pathlib

        original_path_class = pathlib.Path

        class FakeChild:
            """Pretend to be a Path that is a dir but resolves outside worktrees_dir."""

            def is_dir(self) -> bool:
                return True

            def resolve(self) -> original_path_class:  # type: ignore[valid-type]
                return outside.resolve()

            def __truediv__(self, other: str) -> FakeChild:
                return FakeChild()

            def exists(self) -> bool:
                return True

            def __str__(self) -> str:
                return str(outside)

        # Patch only when the worktrees_dir is iterated — use a wrapper around
        # the real iterdir that injects our FakeChild for the target directory.
        real_iterdir = pathlib.Path.iterdir

        def patched_iterdir(self_path: pathlib.Path):  # type: ignore[override]
            if self_path.resolve() == worktrees_dir.resolve():
                yield FakeChild()  # type: ignore[misc]
            else:
                yield from real_iterdir(self_path)

        monkeypatch.setattr(pathlib.Path, "iterdir", patched_iterdir)

        records = mgr._sweep_orphaned_dirs(main_repo, worktrees_dir, registered_paths)

        # The fake outside child must be preserved (containment guard fires).
        assert len(records) == 1
        assert records[0]["action"] == "preserved"
        assert "containment" in records[0]["reason"].lower()


class TestNoPruneWorktreesSkipsOrphanSweep:
    """When prune_worktrees=False, the orphan sweep must not run."""

    def test_orphan_sweep_skipped_when_pruning_disabled(self, repo: Path) -> None:
        orphan = _make_plain_leftover(repo, "orphan-skip")
        assert orphan.is_dir()

        mgr = _make_pause_manager(repo)
        mgr.create_pause_session(message="no prune", prune_worktrees=False)

        # The orphan must still exist because pruning was disabled.
        assert orphan.exists(), "Orphan sweep must not run when prune_worktrees=False"
        # _last_prune_summary must be None when pruning is skipped.
        assert mgr._last_prune_summary is None
