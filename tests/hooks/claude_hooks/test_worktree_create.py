"""Tests for the WorktreeCreate hook contract in the Python hook handler.

Verifies that the Python ``claude-hook`` entry point correctly implements the
Claude Code WorktreeCreate contract:
- stdout is ONLY the absolute path of the created worktree directory
- exit code 0 on success, non-zero on failure
- stdout is NOT the generic ``{"continue": true}`` JSON on failure

Issue: #906
"""

import json
import os
import subprocess
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_event(tmp_repo: Path, name: str = "test-agent") -> dict:
    """Build a WorktreeCreate event dict as Claude Code sends it."""
    return {
        "hook_event_name": "WorktreeCreate",
        "name": name,
        "cwd": str(tmp_repo),
        "session_id": "test-session-abc123",
    }


def _init_git_repo(path: Path) -> None:
    """Create a minimal bare-bones git repo so worktree commands work."""
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
    # Need at least one commit so we can add a worktree
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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_git_repo(tmp_path: Path) -> Path:
    """Temporary git repository for worktree creation tests."""
    repo = tmp_path / "my-repo"
    repo.mkdir()
    _init_git_repo(repo)
    return repo


# ---------------------------------------------------------------------------
# Unit tests: _handle_worktree_create via ClaudeHookHandler
# ---------------------------------------------------------------------------


class TestHandleWorktreeCreate:
    """Test _handle_worktree_create directly, capturing stdout and sys.exit."""

    def _invoke(self, tmp_git_repo: Path, name: str = "test-agent") -> tuple[str, int]:
        """Invoke _handle_worktree_create and return (stdout_output, exit_code)."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()
        event = _make_event(tmp_git_repo, name)

        captured_stdout = StringIO()
        exit_code = -1

        with patch("sys.stdout", captured_stdout):
            with pytest.raises(SystemExit) as exc_info:
                handler._handle_worktree_create(event)
            exit_code = exc_info.value.code if exc_info.value.code is not None else 0

        return captured_stdout.getvalue().strip(), exit_code

    def test_stdout_is_absolute_path(self, tmp_git_repo: Path) -> None:
        """(a) stdout must be exactly the absolute worktree directory path."""
        stdout, exit_code = self._invoke(tmp_git_repo, "my-agent")
        assert exit_code == 0, f"Expected exit 0, got {exit_code}"
        assert os.path.isabs(stdout), f"Expected absolute path, got: {stdout!r}"
        assert os.path.isdir(stdout), (
            f"Expected path to be an existing directory: {stdout!r}"
        )

    def test_exit_code_zero_on_success(self, tmp_git_repo: Path) -> None:
        """(b) exit code must be 0 on success."""
        _stdout, exit_code = self._invoke(tmp_git_repo, "success-agent")
        assert exit_code == 0

    def test_stdout_is_not_continue_json(self, tmp_git_repo: Path) -> None:
        """stdout must not be the generic {"continue": true} JSON response."""
        stdout, exit_code = self._invoke(tmp_git_repo, "no-json-agent")
        assert exit_code == 0
        # The key regression: {"continue": true} must never appear on stdout
        assert '{"continue"' not in stdout, (
            f"stdout contains JSON continue response: {stdout!r}"
        )
        # More direct: stdout must parse as a filesystem path, not JSON
        try:
            json.loads(stdout)
            pytest.fail(f"stdout should not be valid JSON; got: {stdout!r}")
        except json.JSONDecodeError:
            pass  # Good — it's a path, not JSON

    def test_created_directory_exists_under_worktrees_parent(
        self, tmp_git_repo: Path
    ) -> None:
        """The created worktree directory must live in <repo-parent>/<repo>-worktrees/."""
        stdout, exit_code = self._invoke(tmp_git_repo, "dir-check")
        assert exit_code == 0
        worktree_path = Path(stdout)
        expected_parent = tmp_git_repo.parent / f"{tmp_git_repo.name}-worktrees"
        assert worktree_path.parent == expected_parent, (
            f"Expected worktree under {expected_parent}, found: {worktree_path}"
        )

    def test_slug_sanitization_uppercase(self, tmp_git_repo: Path) -> None:
        """Uppercase name is lowercased in the resulting path."""
        stdout, exit_code = self._invoke(tmp_git_repo, "MyAgent")
        assert exit_code == 0
        assert "myagent" in Path(stdout).name or "my-agent" in Path(stdout).name, (
            f"Expected lowercase slug in path, got: {stdout!r}"
        )

    def test_slug_sanitization_special_chars(self, tmp_git_repo: Path) -> None:
        """Special chars in name are replaced with hyphens."""
        stdout, exit_code = self._invoke(tmp_git_repo, "my agent/name:test")
        assert exit_code == 0
        name_part = Path(stdout).name
        # Should contain only safe characters
        assert " " not in name_part, f"Space in path name: {name_part!r}"
        assert "/" not in name_part, f"Slash in path name: {name_part!r}"
        assert ":" not in name_part, f"Colon in path name: {name_part!r}"

    def test_empty_name_generates_fallback_slug(self, tmp_git_repo: Path) -> None:
        """Empty name generates a fallback 'worktree-NNNNNN' slug."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()
        event = {
            "hook_event_name": "WorktreeCreate",
            "name": "",
            "cwd": str(tmp_git_repo),
            "session_id": "session-xyz",
        }
        captured_stdout = StringIO()
        with patch("sys.stdout", captured_stdout):
            with pytest.raises(SystemExit) as exc_info:
                handler._handle_worktree_create(event)
        exit_code = exc_info.value.code if exc_info.value.code is not None else 0
        stdout = captured_stdout.getvalue().strip()
        assert exit_code == 0
        name_part = Path(stdout).name
        assert name_part.startswith("worktree-"), (
            f"Expected 'worktree-NNNNNN' fallback, got: {name_part!r}"
        )


class TestHandleWorktreeCreateFailure:
    """Test that failure exits non-zero and emits no bogus JSON."""

    def test_git_failure_exits_nonzero(self, tmp_path: Path) -> None:
        """(c) On git failure, exit code is non-zero and stdout is not {"continue": true}."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()

        # cwd points to a directory that is NOT a git repo → git will fail
        non_repo = tmp_path / "not-a-git-repo"
        non_repo.mkdir()
        event = {
            "hook_event_name": "WorktreeCreate",
            "name": "will-fail",
            "cwd": str(non_repo),
            "session_id": "session-fail",
        }

        captured_stdout = StringIO()
        with patch("sys.stdout", captured_stdout):
            with pytest.raises(SystemExit) as exc_info:
                handler._handle_worktree_create(event)

        exit_code = exc_info.value.code
        stdout = captured_stdout.getvalue().strip()

        assert exit_code != 0, f"Expected non-zero exit on git failure, got {exit_code}"
        # The key regression guard: must not output the bogus continue JSON
        assert stdout != '{"continue": true}', (
            "stdout must not be the generic continue JSON on failure"
        )
        assert "continue" not in stdout.lower() or stdout == "", (
            f"stdout should be empty on failure, got: {stdout!r}"
        )


# ---------------------------------------------------------------------------
# Integration test: the full handle() path short-circuits WorktreeCreate
# ---------------------------------------------------------------------------


class TestHandleIntegration:
    """Test that handle() correctly routes WorktreeCreate through the new path."""

    def test_handle_worktree_create_calls_worktree_method(
        self, tmp_git_repo: Path
    ) -> None:
        """handle() must call _handle_worktree_create for WorktreeCreate events."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()
        event = _make_event(tmp_git_repo, "integration-agent")
        event_json = json.dumps(event)

        called_with_event = []

        def fake_handle_worktree_create(evt: dict) -> None:
            called_with_event.append(evt)
            raise SystemExit(0)

        handler._handle_worktree_create = fake_handle_worktree_create  # type: ignore[method-assign]

        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = False
            mock_stdin.read.return_value = event_json
            with patch("select.select", return_value=([mock_stdin], [], [])):
                with pytest.raises(SystemExit):
                    handler.handle()

        assert len(called_with_event) == 1, (
            "_handle_worktree_create was not called exactly once"
        )
        assert called_with_event[0]["hook_event_name"] == "WorktreeCreate"

    def test_handle_worktree_create_does_not_call_continue_execution(
        self, tmp_git_repo: Path
    ) -> None:
        """handle() must NOT call _continue_execution for WorktreeCreate events."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()
        event = _make_event(tmp_git_repo, "no-continue-agent")
        event_json = json.dumps(event)

        continue_called = []
        original_continue = handler._continue_execution

        def tracking_continue(*args, **kwargs) -> None:  # type: ignore[no-untyped-def]
            continue_called.append((args, kwargs))
            return original_continue(*args, **kwargs)

        handler._continue_execution = tracking_continue  # type: ignore[method-assign]

        captured_stdout = StringIO()
        with patch("sys.stdout", captured_stdout):
            with patch("sys.stdin") as mock_stdin:
                mock_stdin.isatty.return_value = False
                mock_stdin.read.return_value = event_json
                with patch("select.select", return_value=([mock_stdin], [], [])):
                    with pytest.raises(SystemExit):
                        handler.handle()

        assert len(continue_called) == 0, (
            f"_continue_execution was called {len(continue_called)} time(s) but must not "
            f"be called for WorktreeCreate: {continue_called}"
        )
        # Extra guard: stdout must not contain the bogus JSON
        stdout = captured_stdout.getvalue().strip()
        assert '{"continue": true}' not in stdout, (
            f"Found bogus continue JSON in stdout: {stdout!r}"
        )
