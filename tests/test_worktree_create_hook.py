"""Tests for claude-hook-fast.sh hook contract.

Covers two areas:
  1. Event-type response shapes (from #584):
       - PreToolUse / PermissionRequest (decision events) -> {"continue": true}
       - All other events (observability events) -> {"async": true, "asyncTimeout": 60000}
  2. WorktreeCreate / WorktreeRemove contract (from #572):
       - WorktreeCreate: creates a git worktree, stdout = absolute path, exit 0
       - WorktreeRemove: removes worktree, returns {"continue": true}
       - Non-WorktreeCreate events: still return async JSON
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SCRIPT_PATH = (
    Path(__file__).parent.parent
    / "src"
    / "claude_mpm"
    / "scripts"
    / "claude-hook-fast.sh"
)

# Alias for backward compatibility
SCRIPT = SCRIPT_PATH


def _run_hook(payload: dict, env: dict | None = None) -> subprocess.CompletedProcess:
    """Invoke the fast hook script with the given JSON payload on stdin."""
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        ["/bin/bash", str(SCRIPT_PATH)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=30,
        env=merged_env,
        check=False,
    )


def _output_json(result: subprocess.CompletedProcess) -> dict:
    """Parse the hook script's last JSON line from stdout."""
    stdout = result.stdout.strip()
    last_line = [ln for ln in stdout.splitlines() if ln.strip()][-1]
    return json.loads(last_line)


def _make_temp_git_repo() -> Path:
    """Create a temporary git repository and return its path."""
    tmp = Path(tempfile.mkdtemp(prefix="mpm_test_repo_"))
    subprocess.run(["git", "init", str(tmp)], capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=str(tmp),
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=str(tmp),
        capture_output=True,
        check=True,
    )
    init_file = tmp / "README.md"
    init_file.write_text("# test repo\n")
    subprocess.run(["git", "add", "."], cwd=str(tmp), capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "initial commit"],
        cwd=str(tmp),
        capture_output=True,
        check=True,
    )
    return tmp


def _cleanup_worktree(repo: Path, worktree_path: Path) -> None:
    """Remove a worktree from the repo (best-effort teardown)."""
    subprocess.run(
        ["git", "-C", str(repo), "worktree", "remove", "--force", str(worktree_path)],
        capture_output=True,
        check=False,
    )
    subprocess.run(
        ["git", "-C", str(repo), "worktree", "prune"],
        capture_output=True,
        check=False,
    )


# ---------------------------------------------------------------------------
# Script presence check
# ---------------------------------------------------------------------------


def test_hook_script_exists() -> None:
    """The fast hook script must exist and be executable."""
    assert SCRIPT_PATH.exists(), f"Expected {SCRIPT_PATH} to exist"
    assert SCRIPT_PATH.stat().st_mode & 0o111, (
        f"Expected {SCRIPT_PATH} to be executable"
    )


# ---------------------------------------------------------------------------
# Decision events: PreToolUse, PermissionRequest
# ---------------------------------------------------------------------------


class TestDecisionEvents:
    """Decision events must NOT return {async: true}."""

    @pytest.mark.parametrize("event", ["PreToolUse", "PermissionRequest"])
    def test_decision_event_is_not_async(self, event: str) -> None:
        """Decision events must not return {"async": true}."""
        payload = {
            "hook_event_name": event,
            "tool_name": "Bash",
            "session_id": "test-session-123",
        }
        result = _run_hook(payload)
        assert result.returncode == 0, (
            f"Script exited {result.returncode}: {result.stderr}"
        )
        data = _output_json(result)
        assert data.get("async") is not True, (
            f"Event={event!r}: expected non-async decision response, got {data}"
        )

    @pytest.mark.parametrize("event", ["PreToolUse", "PermissionRequest"])
    def test_decision_event_returns_continue(self, event: str) -> None:
        """Decision events must include a continue/block decision key."""
        payload = {
            "hook_event_name": event,
            "tool_name": "Write",
            "session_id": "test-session-456",
        }
        result = _run_hook(payload)
        data = _output_json(result)
        assert "continue" in data or "block" in data, (
            f"Event={event!r}: response must contain 'continue' or 'block', got {data}"
        )

    def test_pretooluse_continue_is_true(self) -> None:
        """PreToolUse specifically should return continue=true (safe pass-through)."""
        payload = {"hook_event_name": "PreToolUse", "tool_name": "Bash"}
        result = _run_hook(payload)
        data = _output_json(result)
        assert data.get("continue") is True, (
            f"PreToolUse: expected continue=true, got {data}"
        )


# ---------------------------------------------------------------------------
# Observability events: PostToolUse, Stop, etc.
# ---------------------------------------------------------------------------


class TestObservabilityEvents:
    """Pure observability events must return the async JSON shape."""

    @pytest.mark.parametrize(
        "event",
        [
            "PostToolUse",
            "Stop",
            "SubagentStop",
            "UserPromptSubmit",
            "SessionStart",
            "Notification",
            "AssistantResponse",
        ],
    )
    def test_observability_event_returns_async(self, event: str) -> None:
        """Observability events must return {"async": true, "asyncTimeout": ...}."""
        payload = {
            "hook_event_name": event,
            "session_id": "test-session-789",
        }
        result = _run_hook(payload)
        assert result.returncode == 0, (
            f"Script exited {result.returncode}: {result.stderr}"
        )
        data = _output_json(result)
        assert data.get("async") is True, (
            f"Event={event!r}: expected async=true, got {data}"
        )
        assert "asyncTimeout" in data, (
            f"Event={event!r}: expected asyncTimeout in response, got {data}"
        )

    def test_posttooluse_preserves_async_shape(self) -> None:
        """PostToolUse must still return the async shape after the Part C fix."""
        payload = {
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
            "tool_output": "some output",
        }
        result = _run_hook(payload)
        data = _output_json(result)
        assert data == {"async": True, "asyncTimeout": 60000}, (
            f"PostToolUse: expected exact async shape, got {data}"
        )


# ---------------------------------------------------------------------------
# Unknown / missing event field
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge cases: empty input, missing event field, unknown events."""

    def test_empty_input_returns_continue(self) -> None:
        """Empty stdin should produce {"continue": true} immediately (early exit)."""
        result = subprocess.run(
            ["/bin/bash", str(SCRIPT_PATH)],
            input="",
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        assert '{"continue": true}' in result.stdout

    def test_unknown_event_returns_async(self) -> None:
        """Unknown event types fall through to the async shape."""
        payload = {"hook_event_name": "SomeUnknownEvent"}
        result = _run_hook(payload)
        data = _output_json(result)
        assert data.get("async") is True, (
            f"Unknown event: expected async=true, got {data}"
        )

    def test_sub_agent_env_returns_continue_early(self) -> None:
        """When CLAUDE_MPM_SUB_AGENT is set, hook exits early with continue."""
        env = os.environ.copy()
        env["CLAUDE_MPM_SUB_AGENT"] = "1"
        payload = {"hook_event_name": "PreToolUse", "tool_name": "Bash"}
        result = subprocess.run(
            ["/bin/bash", str(SCRIPT_PATH)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        assert result.returncode == 0
        assert '{"continue": true}' in result.stdout


# ---------------------------------------------------------------------------
# Non-WorktreeCreate events must still return async JSON
# ---------------------------------------------------------------------------


class TestNonWorktreeEventsReturnAsyncJson:
    """All non-worktree events must still echo the async JSON object."""

    NON_WORKTREE_EVENTS = [
        "PreToolUse",
        "PostToolUse",
        "UserPromptSubmit",
        "SessionStart",
        "Stop",
        "SubagentStop",
        "Notification",
        "AssistantResponse",
        "unknown",
    ]

    @pytest.mark.parametrize("event_name", NON_WORKTREE_EVENTS)
    def test_event_returns_json(self, event_name: str) -> None:
        payload = {
            "hook_event_name": event_name,
            "session_id": "test-session",
        }
        result = _run_hook(payload)
        stdout = result.stdout.strip()
        assert result.returncode == 0, (
            f"Event {event_name!r} returned exit {result.returncode}. stderr: {result.stderr!r}"
        )
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            pytest.fail(f"Event {event_name!r} produced non-JSON stdout: {stdout!r}")
        assert not Path(stdout).is_dir(), (
            f"Event {event_name!r}: stdout looks like a path: {stdout!r}"
        )
        # PreToolUse: continue=true; others: async=true
        if event_name == "PreToolUse":
            assert data.get("continue") is True, (
                f"Event {event_name!r}: expected continue:true, got: {data}"
            )
        else:
            assert data.get("async") is True, (
                f"Event {event_name!r}: expected async:true, got: {data}"
            )

    def test_no_input_returns_continue(self) -> None:
        """Empty stdin should return the 'continue' JSON sentinel."""
        result = subprocess.run(
            ["/bin/bash", str(SCRIPT_PATH)],
            input="",
            capture_output=True,
            text=True,
            timeout=10,
            env=os.environ.copy(),
            check=False,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout.strip())
        assert data.get("continue") is True

    def test_sub_agent_non_worktree_returns_continue(self) -> None:
        """In sub-agent context, non-worktree events get 'continue' not 'async'."""
        payload = {"hook_event_name": "PreToolUse", "session_id": "sub-session"}
        result = _run_hook(payload, env={"CLAUDE_MPM_SUB_AGENT": "1"})
        assert result.returncode == 0
        data = json.loads(result.stdout.strip())
        assert data.get("continue") is True


# ---------------------------------------------------------------------------
# Core WorktreeCreate contract tests
# ---------------------------------------------------------------------------


class TestWorktreeCreateContract:
    """Verify the WorktreeCreate hook satisfies the Claude Code contract."""

    def setup_method(self) -> None:
        """Create a fresh temporary git repo for each test."""
        self.repo = _make_temp_git_repo()
        self.created_worktrees: list[Path] = []

    def teardown_method(self) -> None:
        """Remove all worktrees created during the test, then delete the repo."""
        for wt in self.created_worktrees:
            if wt.exists():
                _cleanup_worktree(self.repo, wt)
        import shutil

        parent = self.repo.parent
        repo_base = self.repo.name
        shutil.rmtree(str(self.repo), ignore_errors=True)
        worktrees_dir = parent / f"{repo_base}-worktrees"
        shutil.rmtree(str(worktrees_dir), ignore_errors=True)

    def _worktree_create(self, name: str) -> subprocess.CompletedProcess:
        payload = {
            "hook_event_name": "WorktreeCreate",
            "name": name,
            "cwd": str(self.repo),
        }
        result = _run_hook(payload)
        stdout = result.stdout.strip()
        if stdout and Path(stdout).exists():
            self.created_worktrees.append(Path(stdout))
        return result

    def test_exit_code_is_zero_on_success(self) -> None:
        result = self._worktree_create("my-feature")
        assert result.returncode == 0, (
            f"Expected exit 0, got {result.returncode}. stderr: {result.stderr!r}"
        )

    def test_stdout_is_absolute_path(self) -> None:
        result = self._worktree_create("my-feature")
        assert result.returncode == 0
        path_str = result.stdout.strip()
        assert path_str, "stdout should not be empty"
        assert Path(path_str).is_absolute(), f"Path is not absolute: {path_str!r}"

    def test_stdout_path_is_existing_directory(self) -> None:
        result = self._worktree_create("my-feature")
        assert result.returncode == 0
        path = Path(result.stdout.strip())
        assert path.is_dir(), f"Expected a directory at {path}"

    def test_stdout_path_is_valid_git_worktree(self) -> None:
        result = self._worktree_create("my-feature")
        assert result.returncode == 0
        worktree_path = result.stdout.strip()
        canonical_path = str(Path(worktree_path).resolve())
        list_result = subprocess.run(
            ["git", "-C", str(self.repo), "worktree", "list"],
            capture_output=True,
            text=True,
            check=False,
        )
        listed_paths = [
            line.split()[0] for line in list_result.stdout.splitlines() if line
        ]
        canonical_listed = [str(Path(p).resolve()) for p in listed_paths]
        assert canonical_path in canonical_listed, (
            f"Path {worktree_path!r} (canonical: {canonical_path!r}) not found in worktree list:\n{list_result.stdout}"
        )

    def test_name_sanitization_uppercase(self) -> None:
        """Uppercase letters should be lowercased."""
        result = self._worktree_create("MyFeatureBranch")
        assert result.returncode == 0
        path = Path(result.stdout.strip())
        assert path.name == "myfeaturebranch", (
            f"Expected lowercase name, got {path.name!r}"
        )

    def test_name_sanitization_special_chars(self) -> None:
        """Special characters should be replaced with dashes."""
        result = self._worktree_create("feature/my task#123")
        assert result.returncode == 0
        path = Path(result.stdout.strip())
        import re

        assert re.fullmatch(r"[a-z0-9-]+", path.name), (
            f"Name contains unexpected characters: {path.name!r}"
        )

    def test_empty_name_gets_unique_slug(self) -> None:
        """Empty name should produce a valid unique slug, not fail."""
        payload = {
            "hook_event_name": "WorktreeCreate",
            "name": "",
            "cwd": str(self.repo),
        }
        result = _run_hook(payload)
        path_str = result.stdout.strip()
        if path_str and Path(path_str).exists():
            self.created_worktrees.append(Path(path_str))
        assert result.returncode == 0, (
            f"Expected exit 0, got {result.returncode}. stderr: {result.stderr!r}"
        )
        assert Path(path_str).is_dir()

    def test_branch_collision_falls_back_gracefully(self) -> None:
        """Second worktree with same name falls back to no-branch creation."""
        r1 = self._worktree_create("my-branch")
        assert r1.returncode == 0
        r2 = self._worktree_create("my-branch-2nd")
        assert r2.returncode == 0

    def test_output_path_is_inside_worktrees_sibling_dir(self) -> None:
        """Worktree should be placed in <repo-parent>/<repo-name>-worktrees/."""
        result = self._worktree_create("my-feature")
        assert result.returncode == 0
        path = Path(result.stdout.strip())
        expected_parent = (self.repo.parent / f"{self.repo.name}-worktrees").resolve()
        assert path.parent.resolve() == expected_parent, (
            f"Expected parent {expected_parent}, got {path.parent}"
        )

    def test_worktree_create_via_event_field(self) -> None:
        """Script should also recognize 'event' field (fallback path)."""
        payload = {
            "event": "WorktreeCreate",
            "name": "via-event-field",
            "cwd": str(self.repo),
        }
        result = _run_hook(payload)
        path_str = result.stdout.strip()
        if path_str and Path(path_str).exists():
            self.created_worktrees.append(Path(path_str))
        assert result.returncode == 0
        assert Path(path_str).is_dir()


# ---------------------------------------------------------------------------
# Sub-agent + WorktreeCreate
# ---------------------------------------------------------------------------


class TestWorktreeCreateInSubAgentContext:
    """WorktreeCreate must work even when CLAUDE_MPM_SUB_AGENT is set."""

    def setup_method(self) -> None:
        self.repo = _make_temp_git_repo()
        self.created_worktrees: list[Path] = []

    def teardown_method(self) -> None:
        import shutil

        for wt in self.created_worktrees:
            if wt.exists():
                _cleanup_worktree(self.repo, wt)
        parent = self.repo.parent
        repo_base = self.repo.name
        shutil.rmtree(str(self.repo), ignore_errors=True)
        worktrees_dir = parent / f"{repo_base}-worktrees"
        shutil.rmtree(str(worktrees_dir), ignore_errors=True)

    def test_worktree_create_works_in_sub_agent_context(self) -> None:
        """WorktreeCreate succeeds even with CLAUDE_MPM_SUB_AGENT set."""
        payload = {
            "hook_event_name": "WorktreeCreate",
            "name": "sub-agent-worktree",
            "cwd": str(self.repo),
        }
        result = _run_hook(payload, env={"CLAUDE_MPM_SUB_AGENT": "1"})
        path_str = result.stdout.strip()
        if path_str and Path(path_str).exists():
            self.created_worktrees.append(Path(path_str))
        assert result.returncode == 0, (
            f"WorktreeCreate failed in sub-agent context. stderr: {result.stderr!r}"
        )
        assert Path(path_str).is_dir()


# ---------------------------------------------------------------------------
# WorktreeRemove
# ---------------------------------------------------------------------------


class TestWorktreeRemove:
    """WorktreeRemove should cleanly remove an existing worktree."""

    def setup_method(self) -> None:
        self.repo = _make_temp_git_repo()

    def teardown_method(self) -> None:
        import shutil

        parent = self.repo.parent
        repo_base = self.repo.name
        shutil.rmtree(str(self.repo), ignore_errors=True)
        worktrees_dir = parent / f"{repo_base}-worktrees"
        shutil.rmtree(str(worktrees_dir), ignore_errors=True)

    def test_worktree_remove_returns_continue(self) -> None:
        """WorktreeRemove should return continue JSON (not a path)."""
        create_payload = {
            "hook_event_name": "WorktreeCreate",
            "name": "to-be-removed",
            "cwd": str(self.repo),
        }
        create_result = _run_hook(create_payload)
        assert create_result.returncode == 0, "Setup: WorktreeCreate failed"
        worktree_path = create_result.stdout.strip()

        remove_payload = {
            "hook_event_name": "WorktreeRemove",
            "path": worktree_path,
            "cwd": str(self.repo),
        }
        result = _run_hook(remove_payload)
        assert result.returncode == 0
        data = json.loads(result.stdout.strip())
        assert data.get("continue") is True

    def test_worktree_remove_with_nonexistent_path_is_safe(self) -> None:
        """WorktreeRemove with a path that does not exist should not crash."""
        remove_payload = {
            "hook_event_name": "WorktreeRemove",
            "path": "/tmp/nonexistent-worktree-xyz-987",
            "cwd": str(self.repo),
        }
        result = _run_hook(remove_payload)
        assert result.returncode == 0
        data = json.loads(result.stdout.strip())
        assert data.get("continue") is True
