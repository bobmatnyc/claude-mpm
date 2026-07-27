"""Tests for ProjectInitializer worktree-aware security hook setup.

Verifies that ``_is_git_worktree()`` correctly distinguishes a linked git
worktree from the primary checkout, and that ``_setup_security_hooks()``
skips ``pre-commit install`` (and all other hook-installation side effects)
when running inside a linked worktree. Without this guard, ``pre-commit
install`` writes to the shared ``$(git rev-parse --git-common-dir)/hooks``
directory, silently clobbering the primary checkout's ``.git/hooks/pre-commit``
with a shim referencing the worktree's (often ephemeral) venv interpreter.

See: GitHub issue #948
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from claude_mpm.init import ProjectInitializer


def _completed(stdout: str) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=0, stdout=stdout, stderr="")


class TestIsGitWorktree:
    """Covers _is_git_worktree() for main checkout vs. linked worktree."""

    def test_main_checkout_returns_false(self, tmp_path: Path):
        """git-dir == git-common-dir => not a linked worktree."""
        initializer = ProjectInitializer()

        def fake_run(cmd, **kwargs):
            if cmd[-1] == "--git-dir":
                return _completed(".git")
            if cmd[-1] == "--git-common-dir":
                return _completed(".git")
            raise AssertionError(f"unexpected command: {cmd}")

        with patch("subprocess.run", side_effect=fake_run):
            assert initializer._is_git_worktree(tmp_path) is False

    def test_linked_worktree_returns_true(self, tmp_path: Path):
        """git-dir under .git/worktrees/<name> differs from shared git-common-dir."""
        initializer = ProjectInitializer()
        main_repo = tmp_path / "main-repo"
        worktree = tmp_path / "main-repo" / ".claude" / "worktrees" / "agent-xyz"
        main_repo.mkdir(parents=True)
        worktree.mkdir(parents=True)

        git_dir = str(main_repo / ".git" / "worktrees" / "agent-xyz")
        git_common_dir = str(main_repo / ".git")

        def fake_run(cmd, **kwargs):
            if cmd[-1] == "--git-dir":
                return _completed(git_dir)
            if cmd[-1] == "--git-common-dir":
                return _completed(git_common_dir)
            raise AssertionError(f"unexpected command: {cmd}")

        with patch("subprocess.run", side_effect=fake_run):
            assert initializer._is_git_worktree(worktree) is True

    def test_relative_paths_are_resolved_against_project_root(self, tmp_path: Path):
        """git rev-parse can return relative paths; both must resolve consistently."""
        initializer = ProjectInitializer()

        def fake_run(cmd, **kwargs):
            if cmd[-1] == "--git-dir":
                return _completed(".git")
            if cmd[-1] == "--git-common-dir":
                # Same absolute location, expressed relative to project_root.
                return _completed(str((tmp_path / ".git").resolve()))
            raise AssertionError(f"unexpected command: {cmd}")

        with patch("subprocess.run", side_effect=fake_run):
            assert initializer._is_git_worktree(tmp_path) is False

    def test_git_command_failure_fails_open(self, tmp_path: Path):
        """If git can't be queried, treat as not-a-worktree (don't block normal repos)."""
        initializer = ProjectInitializer()

        with patch("subprocess.run", side_effect=FileNotFoundError("git not found")):
            assert initializer._is_git_worktree(tmp_path) is False


class TestSetupSecurityHooksWorktreeGuard:
    """Covers the worktree short-circuit in _setup_security_hooks()."""

    def test_skips_pre_commit_install_in_linked_worktree(self, tmp_path: Path):
        (tmp_path / ".git").mkdir()
        initializer = ProjectInitializer()

        with patch.object(initializer, "_is_git_worktree", return_value=True):
            with patch("subprocess.run") as mock_run:
                initializer._setup_security_hooks(tmp_path, is_mcp_mode=True)

        mock_run.assert_not_called()

    def test_proceeds_in_primary_checkout(self, tmp_path: Path):
        (tmp_path / ".git").mkdir()
        initializer = ProjectInitializer()

        with patch.object(initializer, "_is_git_worktree", return_value=False):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                initializer._setup_security_hooks(tmp_path, is_mcp_mode=True)

        # In the primary checkout, hook setup should attempt at least the
        # `pre-commit --version` check (first subprocess call).
        assert mock_run.called
