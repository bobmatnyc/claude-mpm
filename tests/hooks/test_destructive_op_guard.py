"""Unit tests for the destructive-op PreToolUse guard (issue #420 Phase 1).

Covers:

* Each blocked pattern (force push, hard reset, broad working-tree discard,
  rm -rf of protected paths, protected-branch force-delete, git clean -f)
  returns a ``deny`` decision.
* Safe operations (normal push, ``git reset HEAD~1``, single-file ``rm``)
  fall through to allow (empty dict).
* Flag-parsing edge cases (bundled flags, ``git -C`` prefix, compound commands).
* The ``main`` wire-format envelope for both deny and pass-through paths.
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

# Make src importable when tests run without an installed package.
_SRC = Path(__file__).resolve().parent.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from claude_mpm.hooks import destructive_op_guard

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _eval(command: str) -> dict:
    """Evaluate a Bash command string through the guard."""
    return destructive_op_guard.evaluate(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )


def _is_deny(command: str) -> bool:
    return _eval(command).get("permissionDecision") == "deny"


# ---------------------------------------------------------------------------
# Blocked patterns
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    "command",
    [
        "git push --force",
        "git push -f",
        "git push origin main --force",
        "git push origin main -f",
        "git push --force-with-lease origin main",
        "git push -fu origin main",  # bundled short flags
        "git -C /repo push --force",  # git global prefix
        "git reset --hard",
        "git reset --hard HEAD~3",
        "git reset --hard origin/main",
        "git checkout -- .",
        "git checkout -- ./",
        "git restore .",
        "git restore --staged --worktree .",
        "git branch -D main",
        "git branch -D master",
        "git branch -Df main",  # bundled force-delete flags
        "git clean -f",
        "git clean -fd",
        "git clean -fdx",
        "git clean --force",
        "rm -rf src/",
        "rm -rf src",
        "rm -rf tests/",
        "rm -rf .",
        "rm -rf /",
        "rm -rf /usr/local/lib",
        "rm -fr src/",  # flag order
        "rm -r -f src/",  # separate flags
        "rm --recursive --force src/",  # long flags
    ],
)
def test_blocked_patterns_are_denied(command: str) -> None:
    """Every destructive pattern in scope must return a deny decision."""
    decision = _eval(command)
    assert decision.get("permissionDecision") == "deny", (
        f"expected deny for: {command!r} (got {decision!r})"
    )
    assert decision.get("permissionDecisionReason"), "deny must carry a reason"


@pytest.mark.unit
def test_compound_command_with_destructive_segment_is_denied() -> None:
    """A destructive op hidden after a benign one (``&&``) must still be caught."""
    assert _is_deny("git status && git reset --hard HEAD")
    assert _is_deny("echo cleaning; rm -rf src/")
    assert _is_deny("git fetch | git push --force")


# ---------------------------------------------------------------------------
# Safe operations (allow / pass-through)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    "command",
    [
        "git push",
        "git push origin main",
        "git push --set-upstream origin feature",
        "git reset HEAD~1",  # soft reset (no --hard)
        "git reset --soft HEAD~1",
        "git reset path/to/file.py",
        "git checkout main",  # branch switch, not discard
        "git checkout -- path/to/file.py",  # specific file, not "."
        "git restore path/to/file.py",  # specific file, not "."
        "git restore --staged file.py",  # specific file
        "git branch -D feature/old",  # non-protected branch
        "git branch -d feature/merged",  # safe delete of feature branch
        "git branch main",  # create, not delete
        "git clean -n",  # dry run, no force
        "git clean --dry-run",
        "rm file.txt",  # single file, no recursive/force
        "rm -f file.txt",  # force but not recursive
        "rm -r build/",  # recursive but not force
        "rm -rf node_modules/",  # recursive-force, but not a protected path
        "rm -rf ./build/tmp",  # relative non-protected path
        "ls -la",
        "git status",
        "echo 'git push --force'",  # quoted string, not an actual git invocation
    ],
)
def test_safe_operations_pass_through(command: str) -> None:
    """Safe / out-of-scope commands must return an empty (allow) decision."""
    assert _eval(command) == {}, f"expected pass-through for: {command!r}"


@pytest.mark.unit
def test_non_bash_tool_passes_through() -> None:
    """Only Bash tool calls are inspected; other tools pass through."""
    assert (
        destructive_op_guard.evaluate(
            {"tool_name": "Edit", "tool_input": {"file_path": "x"}}
        )
        == {}
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "event",
    [
        {"tool_name": "Bash"},  # no tool_input
        {"tool_name": "Bash", "tool_input": "not a dict"},  # bad type
        {"tool_name": "Bash", "tool_input": {"command": ""}},  # empty command
        {"tool_name": "Bash", "tool_input": {"command": "   "}},  # whitespace
        {
            "tool_name": "Bash",
            "tool_input": {"command": 'echo "unbalanced'},
        },  # bad quote
        {},  # empty event
    ],
)
def test_malformed_input_fails_open(event: dict) -> None:
    """Malformed/unparseable payloads must not crash and must fail open."""
    assert destructive_op_guard.evaluate(event) == {}


# ---------------------------------------------------------------------------
# main() wire format
# ---------------------------------------------------------------------------


def _run_main(payload: dict) -> dict:
    """Drive ``destructive_op_guard.main`` with synthetic stdin/stdout."""
    fake_stdin = io.StringIO(json.dumps(payload))
    fake_stdout = io.StringIO()
    real_stdin, real_stdout = sys.stdin, sys.stdout
    sys.stdin, sys.stdout = fake_stdin, fake_stdout
    try:
        destructive_op_guard.main()
    finally:
        sys.stdin, sys.stdout = real_stdin, real_stdout
    return json.loads(fake_stdout.getvalue())


@pytest.mark.unit
def test_main_emits_deny_envelope() -> None:
    """A destructive command must yield a PreToolUse deny envelope."""
    out = _run_main(
        {"tool_name": "Bash", "tool_input": {"command": "git reset --hard"}}
    )
    spec = out["hookSpecificOutput"]
    assert spec["hookEventName"] == "PreToolUse"
    assert spec["permissionDecision"] == "deny"
    assert "reset --hard" in spec["permissionDecisionReason"]


@pytest.mark.unit
def test_main_emits_passthrough_for_safe_command() -> None:
    """A safe command must yield ``{"continue": true}``."""
    out = _run_main({"tool_name": "Bash", "tool_input": {"command": "git status"}})
    assert out == {"continue": True}


@pytest.mark.unit
def test_main_unparseable_stdin_fails_open() -> None:
    """Garbage stdin must not crash; main emits the safe default."""
    fake_stdin = io.StringIO("not json")
    fake_stdout = io.StringIO()
    real_stdin, real_stdout = sys.stdin, sys.stdout
    sys.stdin, sys.stdout = fake_stdin, fake_stdout
    try:
        destructive_op_guard.main()
    finally:
        sys.stdin, sys.stdout = real_stdin, real_stdout
    assert json.loads(fake_stdout.getvalue()) == {"continue": True}
