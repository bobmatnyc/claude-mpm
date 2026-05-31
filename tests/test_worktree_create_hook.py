"""Tests for claude-hook-fast.sh event-type response shapes.

Verifies the hook script's output contract:
  - PreToolUse / PermissionRequest (decision events) → {"continue": true}
  - All other events (observability events) → {"async": true, "asyncTimeout": 60000}

Also exercises WorktreeCreate / WorktreeRemove branches that were added in an
earlier fix, ensuring they still fall through to the async path.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SCRIPT = (
    Path(__file__).parent.parent
    / "src"
    / "claude_mpm"
    / "scripts"
    / "claude-hook-fast.sh"
)


def _run_hook(event_payload: dict) -> subprocess.CompletedProcess:
    """Invoke the fast hook script with the given JSON payload on stdin."""
    return subprocess.run(
        [str(SCRIPT)],
        input=json.dumps(event_payload),
        capture_output=True,
        text=True,
        check=False,
    )


def _output_json(result: subprocess.CompletedProcess) -> dict:
    """Parse the hook script's last JSON line from stdout."""
    stdout = result.stdout.strip()
    # Take the last non-empty line (the script may print nothing else)
    last_line = [ln for ln in stdout.splitlines() if ln.strip()][-1]
    return json.loads(last_line)


# ---------------------------------------------------------------------------
# Script presence check
# ---------------------------------------------------------------------------


def test_hook_script_exists() -> None:
    """The fast hook script must exist and be executable."""
    assert SCRIPT.exists(), f"Expected {SCRIPT} to exist"
    assert SCRIPT.stat().st_mode & 0o111, f"Expected {SCRIPT} to be executable"


# ---------------------------------------------------------------------------
# Decision events: PreToolUse, PermissionRequest
# ---------------------------------------------------------------------------


class TestDecisionEvents:
    """Decision events must NOT return {async: true}.

    The correct response is a synchronous decision shape, at minimum
    {"continue": true}, so Claude Code can read the decision immediately.
    """

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
        # Either continue or block must be present; continue=true is the safe no-op
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
# WorktreeCreate / WorktreeRemove (existing branches from earlier fix)
# ---------------------------------------------------------------------------


class TestWorktreeEvents:
    """WorktreeCreate and WorktreeRemove fall through to the observability path."""

    @pytest.mark.parametrize("event", ["WorktreeCreate", "WorktreeRemove"])
    def test_worktree_event_returns_async(self, event: str) -> None:
        """Worktree events are observability events and must return async shape."""
        payload = {
            "hook_event_name": event,
            "session_id": "test-session-wt",
        }
        result = _run_hook(payload)
        assert result.returncode == 0, (
            f"Script exited {result.returncode} for {event}: {result.stderr}"
        )

        data = _output_json(result)
        assert data.get("async") is True, (
            f"Event={event!r}: expected async=true, got {data}"
        )


# ---------------------------------------------------------------------------
# Unknown / missing event field
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge cases: empty input, missing event field, unknown events."""

    def test_empty_input_returns_continue(self) -> None:
        """Empty stdin should produce {"continue": true} immediately (early exit)."""
        result = subprocess.run(
            [str(SCRIPT)],
            input="",
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        # Early exit path returns {"continue": true}
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
        import os

        env = os.environ.copy()
        env["CLAUDE_MPM_SUB_AGENT"] = "1"
        payload = {"hook_event_name": "PreToolUse", "tool_name": "Bash"}
        result = subprocess.run(
            [str(SCRIPT)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        assert result.returncode == 0
        assert '{"continue": true}' in result.stdout
