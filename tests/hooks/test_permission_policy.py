"""Unit tests for the PermissionRequest decision engine.

Covers:

* Safe-tool allowlist (``Read``, ``Glob``, ``Grep``, ...) → allow.
* Read-only agent tier requesting a mutating tool → deny.
* Bash with destructive flags → deny.
* Unknown tools → fail-open allow (preserves prior behavior, #421).
* Wire-format envelope rendered by ``model_tier_hook.main`` for both
  PermissionRequest and PreToolUse Agent injection paths.
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

# Make src importable when tests are run directly without an installed package.
_SRC = Path(__file__).resolve().parent.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from claude_mpm.hooks import model_tier_hook, permission_policy

# ---------------------------------------------------------------------------
# permission_policy.evaluate
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    "tool",
    ["Read", "Glob", "Grep", "WebSearch", "WebFetch", "TodoRead", "TodoWrite", "LS"],
)
def test_safe_tools_are_allowed(tool: str) -> None:
    """Tools in the safe allowlist must always be approved."""
    decision = permission_policy.evaluate({"tool_name": tool, "tool_input": {}})
    assert decision.decision == "allow"
    assert "allowlist" in decision.reason


@pytest.mark.unit
def test_read_only_agent_cannot_edit() -> None:
    """A research agent must not be allowed to invoke ``Edit``."""
    decision = permission_policy.evaluate(
        {
            "tool_name": "Edit",
            "tool_input": {"file_path": "x.py", "old_string": "a", "new_string": "b"},
            "subagent_type": "research",
        }
    )
    assert decision.decision == "deny"
    assert "read-only" in decision.reason


@pytest.mark.unit
def test_read_only_agent_alternate_field_names() -> None:
    """``agent_id`` / ``agent_type`` are accepted in addition to ``subagent_type``."""
    decision = permission_policy.evaluate(
        {
            "tool_name": "Write",
            "tool_input": {"file_path": "x.py", "content": "x"},
            "agent_id": "QA",  # case + alternate field
        }
    )
    assert decision.decision == "deny"


@pytest.mark.unit
def test_engineering_agent_can_edit() -> None:
    """Mutators are allowed for non-read-only tiers (default-allow path)."""
    decision = permission_policy.evaluate(
        {
            "tool_name": "Edit",
            "tool_input": {"file_path": "x.py"},
            "subagent_type": "python-engineer",
        }
    )
    assert decision.decision == "allow"


@pytest.mark.unit
@pytest.mark.parametrize(
    "command",
    [
        "rm -rf /",
        "rm -rf /*",
        "sudo rm -rf /home/foo",
        ":(){ :|:& };:",
        "mkfs.ext4 /dev/sda1",
        "dd if=/dev/zero of=/dev/sda bs=1M",
        "shutdown -h now",
    ],
)
def test_destructive_bash_is_denied(command: str) -> None:
    """Known-destructive Bash invocations must be blocked."""
    decision = permission_policy.evaluate(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert decision.decision == "deny", f"expected deny for: {command}"
    assert "destructive" in decision.reason


@pytest.mark.unit
@pytest.mark.parametrize(
    "command",
    [
        "ls -la",
        "git status",
        "rm tmp.txt",  # rm without recursive flag is fine
        "echo hello",
        "python3 -m pytest tests/",
    ],
)
def test_benign_bash_is_allowed(command: str) -> None:
    """Non-destructive Bash commands fall through to default-allow."""
    decision = permission_policy.evaluate(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert decision.decision == "allow"


@pytest.mark.unit
def test_unknown_tool_defaults_to_allow() -> None:
    """Tools that aren't classified must be allowed (fail-open, preserves #421 behavior)."""
    decision = permission_policy.evaluate(
        {"tool_name": "SomeBrandNewTool", "tool_input": {}}
    )
    assert decision.decision == "allow"
    assert "default" in decision.reason.lower()


@pytest.mark.unit
def test_missing_tool_input_is_handled() -> None:
    """A malformed payload (no ``tool_input``) must not crash the engine."""
    decision = permission_policy.evaluate({"tool_name": "Bash"})
    assert decision.decision == "allow"


@pytest.mark.unit
def test_non_dict_tool_input_is_coerced() -> None:
    """A string ``tool_input`` (older harness builds) must be tolerated."""
    decision = permission_policy.evaluate(
        {"tool_name": "Bash", "tool_input": "not a dict"}
    )
    # Falls through to default allow because ``command`` cannot be extracted.
    assert decision.decision == "allow"


# ---------------------------------------------------------------------------
# model_tier_hook.main wire-format integration
# ---------------------------------------------------------------------------


def _run_main(payload: dict) -> dict:
    """Drive ``model_tier_hook.main`` with a synthetic stdin/stdout pair.

    Returns the parsed JSON the hook emits on stdout.
    """
    fake_stdin = io.StringIO(json.dumps(payload))
    fake_stdout = io.StringIO()
    real_stdin, real_stdout = sys.stdin, sys.stdout
    sys.stdin, sys.stdout = fake_stdin, fake_stdout
    try:
        model_tier_hook.main()
    finally:
        sys.stdin, sys.stdout = real_stdin, real_stdout
    return json.loads(fake_stdout.getvalue())


@pytest.mark.unit
def test_wire_format_allow_for_safe_tool() -> None:
    """A PermissionRequest for ``Read`` must produce an allow envelope."""
    out = _run_main({"hook_event_name": "PermissionRequest", "tool_name": "Read"})
    spec = out["hookSpecificOutput"]
    assert spec["hookEventName"] == "PermissionRequest"
    assert spec["permissionDecision"] == "allow"
    assert spec["permissionDecisionReason"]


@pytest.mark.unit
def test_wire_format_deny_for_destructive_bash() -> None:
    """A PermissionRequest for ``rm -rf /`` must produce a deny envelope."""
    out = _run_main(
        {
            "hook_event_name": "PermissionRequest",
            "tool_name": "Bash",
            "tool_input": {"command": "rm -rf /"},
        }
    )
    spec = out["hookSpecificOutput"]
    assert spec["permissionDecision"] == "deny"
    assert "destructive" in spec["permissionDecisionReason"]


@pytest.mark.unit
def test_pre_tool_use_agent_path_still_works() -> None:
    """Non-PermissionRequest events keep the legacy Agent-injection path."""
    # Tool=Agent without ``model`` should get a default model injected.
    out = _run_main(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Agent",
            "tool_input": {"subagent_type": "engineer"},
            "cwd": "/nonexistent",
        }
    )
    spec = out["hookSpecificOutput"]
    assert spec["hookEventName"] == "PreToolUse"
    assert spec["permissionDecision"] == "allow"
    # Engineering tier defaults to the Opus model.
    assert spec["updatedInput"]["model"]


@pytest.mark.unit
def test_pre_tool_use_non_agent_passthrough() -> None:
    """Non-Agent PreToolUse calls fall through with ``continue: true``."""
    out = _run_main(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
        }
    )
    assert out == {"continue": True}


@pytest.mark.unit
def test_unparseable_stdin_falls_through() -> None:
    """Garbage on stdin must not crash; the hook emits the safe default."""
    fake_stdin = io.StringIO("not json")
    fake_stdout = io.StringIO()
    real_stdin, real_stdout = sys.stdin, sys.stdout
    sys.stdin, sys.stdout = fake_stdin, fake_stdout
    try:
        model_tier_hook.main()
    finally:
        sys.stdin, sys.stdout = real_stdin, real_stdout
    assert json.loads(fake_stdout.getvalue()) == {"continue": True}
