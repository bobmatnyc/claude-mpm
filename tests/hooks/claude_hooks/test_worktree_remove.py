"""Tests for the WorktreeRemove hook contract in the Python hook handler.

Verifies that the Python ``claude-hook`` entry point correctly implements the
Claude Code WorktreeRemove contract:
- stdout is exactly ``{"continue": true}`` and exit code is 0
- git worktree remove --force is invoked for the given path
- worktree directory is absent after successful removal
- exit 0 with {"continue": true} and NO git invocation when path is missing
- removal failures (nonexistent path) still exit 0 with {"continue": true}

Issue: #912
"""

import json
import subprocess
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_event(path: str = "", cwd: str = "") -> dict:
    """Build a WorktreeRemove event dict as Claude Code sends it."""
    return {
        "hook_event_name": "WorktreeRemove",
        "path": path,
        "cwd": cwd,
        "session_id": "test-session-remove-abc123",
    }


def _init_git_repo(path: Path) -> None:
    """Create a minimal git repo so worktree commands work."""
    subprocess.run(["git", "init", str(path)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "test@example.com"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.name", "Test User"],
        check=True,
        capture_output=True,
    )
    readme = path / "README.md"
    readme.write_text("# test\n")
    subprocess.run(
        ["git", "-C", str(path), "add", "."], check=True, capture_output=True
    )
    subprocess.run(
        ["git", "-C", str(path), "commit", "-m", "init"],
        check=True,
        capture_output=True,
    )


def _register_worktree(repo: Path, worktree_path: Path) -> None:
    """Add a real git worktree at worktree_path branching off repo."""
    branch = worktree_path.name
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "worktree",
            "add",
            str(worktree_path),
            "-b",
            branch,
        ],
        check=True,
        capture_output=True,
    )


def _invoke_handle_worktree_remove(event: dict) -> tuple[str, int]:
    """Invoke _handle_worktree_remove and return (stdout_output, exit_code)."""
    from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

    handler = ClaudeHookHandler()
    captured_stdout = StringIO()
    exit_code = -1

    with patch("sys.stdout", captured_stdout):
        with pytest.raises(SystemExit) as exc_info:
            handler._handle_worktree_remove(event)
        exit_code = exc_info.value.code if exc_info.value.code is not None else 0

    return captured_stdout.getvalue().strip(), exit_code


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_git_repo(tmp_path: Path) -> Path:
    """Temporary git repository for worktree removal tests."""
    repo = tmp_path / "my-repo"
    repo.mkdir()
    _init_git_repo(repo)
    return repo


# ---------------------------------------------------------------------------
# (a) Successful removal: real repo + registered worktree
# ---------------------------------------------------------------------------


class TestHandleWorktreeRemoveSuccess:
    """Test _handle_worktree_remove with a real registered git worktree."""

    def test_stdout_is_continue_json_on_success(self, tmp_git_repo: Path) -> None:
        """(a) stdout must be exactly {"continue": true} on successful removal."""
        worktree_path = tmp_git_repo.parent / "my-repo-worktrees" / "remove-agent"
        worktree_path.parent.mkdir(parents=True, exist_ok=True)
        _register_worktree(tmp_git_repo, worktree_path)
        assert worktree_path.is_dir(), "worktree directory must exist before removal"

        event = _make_event(path=str(worktree_path), cwd=str(tmp_git_repo))
        stdout, exit_code = _invoke_handle_worktree_remove(event)

        assert exit_code == 0, f"Expected exit 0, got {exit_code}"
        parsed = json.loads(stdout)
        assert parsed == {"continue": True}, f"Unexpected stdout: {stdout!r}"

    def test_exit_code_zero_on_success(self, tmp_git_repo: Path) -> None:
        """(a) exit code must be 0 on successful removal."""
        worktree_path = tmp_git_repo.parent / "my-repo-worktrees" / "exit-zero-agent"
        worktree_path.parent.mkdir(parents=True, exist_ok=True)
        _register_worktree(tmp_git_repo, worktree_path)

        event = _make_event(path=str(worktree_path), cwd=str(tmp_git_repo))
        _stdout, exit_code = _invoke_handle_worktree_remove(event)

        assert exit_code == 0

    def test_worktree_directory_removed_after_call(self, tmp_git_repo: Path) -> None:
        """(a) The worktree directory must not exist after successful removal."""
        worktree_path = tmp_git_repo.parent / "my-repo-worktrees" / "dir-gone-agent"
        worktree_path.parent.mkdir(parents=True, exist_ok=True)
        _register_worktree(tmp_git_repo, worktree_path)
        assert worktree_path.is_dir(), "precondition: worktree dir exists before test"

        event = _make_event(path=str(worktree_path), cwd=str(tmp_git_repo))
        _invoke_handle_worktree_remove(event)

        assert not worktree_path.exists(), (
            f"worktree directory still exists after removal: {worktree_path}"
        )

    def test_git_worktree_list_no_longer_shows_path(self, tmp_git_repo: Path) -> None:
        """(a) git worktree list must no longer include the path after removal."""
        worktree_path = tmp_git_repo.parent / "my-repo-worktrees" / "list-check-agent"
        worktree_path.parent.mkdir(parents=True, exist_ok=True)
        _register_worktree(tmp_git_repo, worktree_path)

        event = _make_event(path=str(worktree_path), cwd=str(tmp_git_repo))
        _invoke_handle_worktree_remove(event)

        result = subprocess.run(
            ["git", "-C", str(tmp_git_repo), "worktree", "list"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert str(worktree_path) not in result.stdout, (
            f"git worktree list still shows removed path: {result.stdout}"
        )


# ---------------------------------------------------------------------------
# (b) Missing / empty path: no git invocation, graceful continue
# ---------------------------------------------------------------------------


class TestHandleWorktreeRemoveMissingPath:
    """Test _handle_worktree_remove when path field is absent or empty."""

    def test_empty_path_stdout_is_continue_json(self, tmp_path: Path) -> None:
        """(b) stdout must be {"continue": true} when path is empty."""
        event = _make_event(path="", cwd=str(tmp_path))
        stdout, exit_code = _invoke_handle_worktree_remove(event)

        assert exit_code == 0, f"Expected exit 0, got {exit_code}"
        parsed = json.loads(stdout)
        assert parsed == {"continue": True}, f"Unexpected stdout: {stdout!r}"

    def test_missing_path_field_no_git_invocation(self, tmp_path: Path) -> None:
        """(b) No subprocess call must occur when path field is absent."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()
        # Build event without 'path' key at all
        event = {
            "hook_event_name": "WorktreeRemove",
            "cwd": str(tmp_path),
            "session_id": "no-path-session",
        }
        captured_stdout = StringIO()

        with patch("subprocess.run") as mock_run:
            with patch("sys.stdout", captured_stdout):
                with pytest.raises(SystemExit) as exc_info:
                    handler._handle_worktree_remove(event)

            exit_code = exc_info.value.code if exc_info.value.code is not None else 0

        # subprocess.run must NOT have been called (no path → no git)
        for call in mock_run.call_args_list:
            args = call.args[0] if call.args else call.kwargs.get("args", [])
            assert "worktree" not in args, (
                f"subprocess.run was called with git worktree args: {args}"
            )

        assert exit_code == 0
        stdout = captured_stdout.getvalue().strip()
        assert json.loads(stdout) == {"continue": True}

    def test_empty_path_field_no_git_invocation(self, tmp_path: Path) -> None:
        """(b) No git subprocess for worktree remove when path is empty string."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()
        event = _make_event(path="", cwd=str(tmp_path))
        captured_stdout = StringIO()

        git_worktree_remove_called = []

        original_run = subprocess.run

        def tracking_run(cmd, *args, **kwargs):  # type: ignore[no-untyped-def]
            if isinstance(cmd, list) and "worktree" in cmd and "remove" in cmd:
                git_worktree_remove_called.append(cmd)
            return original_run(cmd, *args, **kwargs)

        with patch("subprocess.run", side_effect=tracking_run):
            with patch("sys.stdout", captured_stdout):
                with pytest.raises(SystemExit):
                    handler._handle_worktree_remove(event)

        assert len(git_worktree_remove_called) == 0, (
            f"git worktree remove was called despite empty path: {git_worktree_remove_called}"
        )


# ---------------------------------------------------------------------------
# (c) Removal failure: nonexistent path still exits 0 with {"continue": true}
# ---------------------------------------------------------------------------


class TestHandleWorktreeRemoveFailure:
    """Test that removal failures never block Claude Code."""

    def test_nonexistent_path_exits_zero(self, tmp_git_repo: Path) -> None:
        """(c) A nonexistent worktree path must still exit 0."""
        nonexistent = str(tmp_git_repo.parent / "nonexistent-worktree-xyz")
        event = _make_event(path=nonexistent, cwd=str(tmp_git_repo))
        _stdout, exit_code = _invoke_handle_worktree_remove(event)
        assert exit_code == 0, f"Expected exit 0 on removal failure, got {exit_code}"

    def test_nonexistent_path_stdout_is_continue_json(self, tmp_git_repo: Path) -> None:
        """(c) stdout must be {"continue": true} even when git removal fails."""
        nonexistent = str(tmp_git_repo.parent / "nonexistent-worktree-abc")
        event = _make_event(path=nonexistent, cwd=str(tmp_git_repo))
        stdout, exit_code = _invoke_handle_worktree_remove(event)

        assert exit_code == 0
        parsed = json.loads(stdout)
        assert parsed == {"continue": True}, f"Unexpected stdout: {stdout!r}"

    def test_removal_failure_does_not_raise(self, tmp_git_repo: Path) -> None:
        """(c) Removal failure must not propagate as an exception."""
        nonexistent = str(tmp_git_repo.parent / "does-not-exist-worktree")
        event = _make_event(path=nonexistent, cwd=str(tmp_git_repo))

        # The only allowed exception is SystemExit(0); no other exception must leak.
        with pytest.raises(SystemExit) as exc_info:
            from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

            handler = ClaudeHookHandler()
            captured_stdout = StringIO()
            with patch("sys.stdout", captured_stdout):
                handler._handle_worktree_remove(event)

        assert exc_info.value.code == 0, (
            f"Expected SystemExit(0) on failure, got SystemExit({exc_info.value.code})"
        )

    def test_subprocess_exception_does_not_propagate(self, tmp_git_repo: Path) -> None:
        """(c) An OSError from subprocess.run must be caught and exit 0 still occurs."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()
        event = _make_event(path="/some/path", cwd=str(tmp_git_repo))
        captured_stdout = StringIO()

        def raise_oserror(cmd, *args, **kwargs):  # type: ignore[no-untyped-def]
            if isinstance(cmd, list) and "worktree" in cmd:
                raise OSError("simulated git not found")
            return MagicMock(returncode=0, stderr="")

        with patch("subprocess.run", side_effect=raise_oserror):
            with patch("sys.stdout", captured_stdout):
                with pytest.raises(SystemExit) as exc_info:
                    handler._handle_worktree_remove(event)

        assert exc_info.value.code == 0
        stdout = captured_stdout.getvalue().strip()
        assert json.loads(stdout) == {"continue": True}


# ---------------------------------------------------------------------------
# Integration: handle() short-circuits WorktreeRemove correctly
# ---------------------------------------------------------------------------


class TestHandleIntegrationWorktreeRemove:
    """Test that handle() routes WorktreeRemove through _handle_worktree_remove."""

    def test_handle_calls_worktree_remove_method(self, tmp_git_repo: Path) -> None:
        """handle() must call _handle_worktree_remove for WorktreeRemove events."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()
        event = _make_event(path="/some/path", cwd=str(tmp_git_repo))
        event_json = json.dumps(event)

        called_with: list[dict] = []

        def fake_handle_worktree_remove(evt: dict) -> None:
            called_with.append(evt)
            raise SystemExit(0)

        handler._handle_worktree_remove = fake_handle_worktree_remove  # type: ignore[method-assign]

        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = False
            mock_stdin.read.return_value = event_json
            with patch("select.select", return_value=([mock_stdin], [], [])):
                with pytest.raises(SystemExit):
                    handler.handle()

        assert len(called_with) == 1, (
            "_handle_worktree_remove was not called exactly once"
        )
        assert called_with[0]["hook_event_name"] == "WorktreeRemove"

    def test_handle_does_not_call_continue_execution_for_remove(
        self, tmp_git_repo: Path
    ) -> None:
        """handle() must NOT call _continue_execution for WorktreeRemove events."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()
        event = _make_event(path="/some/path", cwd=str(tmp_git_repo))
        event_json = json.dumps(event)

        continue_called: list = []
        original_continue = handler._continue_execution

        def tracking_continue(*args, **kwargs):  # type: ignore[no-untyped-def]
            continue_called.append((args, kwargs))
            return original_continue(*args, **kwargs)

        handler._continue_execution = tracking_continue  # type: ignore[method-assign]

        # Replace _handle_worktree_remove to avoid real git I/O
        def fake_handle_worktree_remove(evt: dict) -> None:
            raise SystemExit(0)

        handler._handle_worktree_remove = fake_handle_worktree_remove  # type: ignore[method-assign]

        captured_stdout = StringIO()
        with patch("sys.stdout", captured_stdout):
            with patch("sys.stdin") as mock_stdin:
                mock_stdin.isatty.return_value = False
                mock_stdin.read.return_value = event_json
                with patch("select.select", return_value=([mock_stdin], [], [])):
                    with pytest.raises(SystemExit):
                        handler.handle()

        assert len(continue_called) == 0, (
            f"_continue_execution was called {len(continue_called)} time(s) for "
            f"WorktreeRemove — must not be called: {continue_called}"
        )


# ---------------------------------------------------------------------------
# Regression tests: SIGALRM timeout guard for WorktreeRemove
# ---------------------------------------------------------------------------


class TestWorktreeRemoveTimeoutGuard:
    """Regression tests for the SIGALRM timeout + WorktreeRemove race condition.

    Before the fix, if git worktree remove ran long and the 10-second SIGALRM
    fired, timeout_handler would emit {"continue": true} to stdout because
    _continue_sent was still False.

    The fix sets _continue_sent = True immediately when WorktreeRemove is
    detected, BEFORE any git I/O starts, so the timeout handler is disarmed.
    """

    def test_continue_sent_set_before_worktree_remove_runs(
        self, tmp_path: Path
    ) -> None:
        """_continue_sent must be True before _handle_worktree_remove is entered.

        Verify the observable consequence: even if _handle_worktree_remove raises
        SystemExit(0) immediately (simulating an interrupted git operation),
        _continue_execution must not have been called — the guard prevents
        double-emit.
        """
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()
        event = _make_event(path="/some/worktree/path", cwd=str(tmp_path))
        event_json = json.dumps(event)

        continue_called: list = []
        original_continue = handler._continue_execution

        def tracking_continue(*args, **kwargs):  # type: ignore[no-untyped-def]
            continue_called.append((args, kwargs))
            return original_continue(*args, **kwargs)

        handler._continue_execution = tracking_continue  # type: ignore[method-assign]

        # Make _handle_worktree_remove raise SystemExit(0) immediately,
        # as if SIGALRM interrupted it mid-git-operation.
        def fake_handle_worktree_remove(evt: dict) -> None:
            raise SystemExit(0)

        handler._handle_worktree_remove = fake_handle_worktree_remove  # type: ignore[method-assign]

        captured_stdout = StringIO()
        with patch("sys.stdout", captured_stdout):
            with patch("sys.stdin") as mock_stdin:
                mock_stdin.isatty.return_value = False
                mock_stdin.read.return_value = event_json
                with patch("select.select", return_value=([mock_stdin], [], [])):
                    with pytest.raises(SystemExit):
                        handler.handle()

        # _continue_execution must NOT have been called — the guard worked.
        assert len(continue_called) == 0, (
            f"_continue_execution was called {len(continue_called)} time(s); "
            f"_continue_sent guard did not protect WorktreeRemove from the timeout handler"
        )
        stdout = captured_stdout.getvalue().strip()
        assert '{"continue":' not in stdout, (
            f"stdout contains bogus continue JSON — timeout guard failed: {stdout!r}"
        )

    def test_timeout_handler_cannot_emit_json_for_worktree_remove(
        self, tmp_path: Path
    ) -> None:
        """Simulate SIGALRM firing during WorktreeRemove: stdout must not contain JSON.

        Verify from the outside-in: when _handle_worktree_remove exits immediately,
        the output on stdout must not contain {"continue": JSON emitted by the
        fallback path (i.e. the _continue_sent = True guard prevents double-emit).
        """
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()
        event = _make_event(path="/some/worktree/path", cwd=str(tmp_path))
        event_json = json.dumps(event)

        def fake_handle_worktree_remove(evt: dict) -> None:
            raise SystemExit(0)

        handler._handle_worktree_remove = fake_handle_worktree_remove  # type: ignore[method-assign]

        captured_stdout = StringIO()
        with patch("sys.stdout", captured_stdout):
            with patch("sys.stdin") as mock_stdin:
                mock_stdin.isatty.return_value = False
                mock_stdin.read.return_value = event_json
                with patch("select.select", return_value=([mock_stdin], [], [])):
                    with pytest.raises(SystemExit):
                        handler.handle()

        stdout = captured_stdout.getvalue()
        assert '{"continue": true}' not in stdout, (
            f"Timeout guard failed: stdout contains bogus JSON: {stdout!r}"
        )
        assert '"continue"' not in stdout, (
            f"Timeout guard failed: stdout contains JSON fragment: {stdout!r}"
        )


# ---------------------------------------------------------------------------
# Path-containment guard tests
# ---------------------------------------------------------------------------


class TestWorktreeRemovePathContainmentGuard:
    """Tests for the path-containment guard added to _handle_worktree_remove.

    A WorktreeRemove event whose path is OUTSIDE the expected worktrees root
    must be rejected: exit 0, {"continue": true}, NO git worktree remove call.
    """

    def test_path_outside_worktrees_root_exits_zero(self, tmp_git_repo: Path) -> None:
        """A path outside <repo-parent>/<repo>-worktrees/ must exit 0."""
        # Path outside the worktrees root — e.g. /tmp itself
        outside_path = str(tmp_git_repo.parent / "some-other-directory" / "data")
        event = _make_event(path=outside_path, cwd=str(tmp_git_repo))
        _stdout, exit_code = _invoke_handle_worktree_remove(event)
        assert exit_code == 0, f"Expected exit 0 for out-of-root path, got {exit_code}"

    def test_path_outside_worktrees_root_stdout_is_continue_json(
        self, tmp_git_repo: Path
    ) -> None:
        """A path outside the worktrees root must still emit {"continue": true}."""
        outside_path = str(tmp_git_repo.parent / "some-other-directory" / "data")
        event = _make_event(path=outside_path, cwd=str(tmp_git_repo))
        stdout, exit_code = _invoke_handle_worktree_remove(event)
        assert exit_code == 0
        parsed = json.loads(stdout)
        assert parsed == {"continue": True}, f"Unexpected stdout: {stdout!r}"

    def test_path_outside_worktrees_root_no_git_invocation(
        self, tmp_git_repo: Path
    ) -> None:
        """git worktree remove must NOT be called for a path outside the worktrees root."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()
        outside_path = str(tmp_git_repo.parent / "outside" / "escaped-path")
        event = _make_event(path=outside_path, cwd=str(tmp_git_repo))

        captured_stdout = StringIO()
        git_remove_calls: list = []

        original_run = subprocess.run

        def tracking_run(cmd, *args, **kwargs):  # type: ignore[no-untyped-def]
            if isinstance(cmd, list) and "worktree" in cmd and "remove" in cmd:
                git_remove_calls.append(cmd)
            return original_run(cmd, *args, **kwargs)

        with patch("subprocess.run", side_effect=tracking_run):
            with patch("sys.stdout", captured_stdout):
                with pytest.raises(SystemExit):
                    handler._handle_worktree_remove(event)

        assert len(git_remove_calls) == 0, (
            f"git worktree remove was called for an out-of-root path: {git_remove_calls}"
        )

    def test_path_inside_worktrees_root_allows_git_invocation(
        self, tmp_git_repo: Path
    ) -> None:
        """A path correctly inside the worktrees root must reach the git remove call."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()
        # Path inside the expected worktrees root (may not exist — that's OK, removal
        # failure is non-fatal and still exits 0)
        inside_path = str(
            tmp_git_repo.parent / f"{tmp_git_repo.name}-worktrees" / "test-agent"
        )
        event = _make_event(path=inside_path, cwd=str(tmp_git_repo))

        captured_stdout = StringIO()
        git_remove_calls: list = []

        original_run = subprocess.run

        def tracking_run(cmd, *args, **kwargs):  # type: ignore[no-untyped-def]
            if isinstance(cmd, list) and "worktree" in cmd and "remove" in cmd:
                git_remove_calls.append(cmd)
            return original_run(cmd, *args, **kwargs)

        with patch("subprocess.run", side_effect=tracking_run):
            with patch("sys.stdout", captured_stdout):
                with pytest.raises(SystemExit):
                    handler._handle_worktree_remove(event)

        assert len(git_remove_calls) == 1, (
            f"Expected git worktree remove to be called once for a valid path, "
            f"got {len(git_remove_calls)} calls"
        )
