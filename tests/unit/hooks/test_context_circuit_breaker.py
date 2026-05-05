"""Unit tests for the PreToolUse context circuit-breaker (issue #420)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from claude_mpm.hooks import context_circuit_breaker

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def project_cwd(tmp_path: Path) -> Path:
    """Create a fake project directory with the state subtree."""
    (tmp_path / ".claude-mpm" / "state").mkdir(parents=True)
    return tmp_path


def _write_state(cwd: Path, state: dict) -> None:
    state_file = cwd / ".claude-mpm" / "state" / "context-usage.json"
    state_file.write_text(json.dumps(state), encoding="utf-8")


def _event(cwd: Path, session_id: str = "sess-current") -> dict:
    return {
        "cwd": str(cwd),
        "session_id": session_id,
        "tool_name": "Edit",
        "tool_input": {},
    }


# ---------------------------------------------------------------------------
# Threshold behavior
# ---------------------------------------------------------------------------


def test_below_threshold_passes_through(project_cwd: Path) -> None:
    _write_state(
        project_cwd,
        {"session_id": "sess-current", "percentage_used": 80.0},
    )
    assert context_circuit_breaker.evaluate(_event(project_cwd)) == {}


def test_just_below_threshold_passes_through(project_cwd: Path) -> None:
    _write_state(
        project_cwd,
        {"session_id": "sess-current", "percentage_used": 94.99},
    )
    assert context_circuit_breaker.evaluate(_event(project_cwd)) == {}


def test_at_exactly_95_denies(project_cwd: Path) -> None:
    _write_state(
        project_cwd,
        {"session_id": "sess-current", "percentage_used": 95.0},
    )
    decision = context_circuit_breaker.evaluate(_event(project_cwd))
    assert decision.get("permissionDecision") == "deny"
    assert "95%" in decision.get("permissionDecisionReason", "")


def test_above_95_denies_with_percentage_in_reason(project_cwd: Path) -> None:
    _write_state(
        project_cwd,
        {"session_id": "sess-current", "percentage_used": 97.4},
    )
    decision = context_circuit_breaker.evaluate(_event(project_cwd))
    assert decision.get("permissionDecision") == "deny"
    reason = decision.get("permissionDecisionReason", "")
    # 97.4% rounds to 97 for display.
    assert "97%" in reason
    assert "/mpm-resume" in reason


# ---------------------------------------------------------------------------
# Fail-open paths
# ---------------------------------------------------------------------------


def test_state_file_missing_fails_open(tmp_path: Path) -> None:
    # No .claude-mpm directory at all -- breaker must pass through.
    event = _event(tmp_path)
    assert context_circuit_breaker.evaluate(event) == {}


def test_session_id_mismatch_fails_open(project_cwd: Path) -> None:
    # State recorded under a different session -- this is stale data from a
    # prior run and must NOT block the live session.
    _write_state(
        project_cwd,
        {"session_id": "sess-OLD", "percentage_used": 99.0},
    )
    decision = context_circuit_breaker.evaluate(
        _event(project_cwd, session_id="sess-current")
    )
    assert decision == {}


def test_malformed_state_file_fails_open(project_cwd: Path) -> None:
    state_file = project_cwd / ".claude-mpm" / "state" / "context-usage.json"
    state_file.write_text("{ this is not json", encoding="utf-8")
    assert context_circuit_breaker.evaluate(_event(project_cwd)) == {}


def test_non_dict_state_file_fails_open(project_cwd: Path) -> None:
    state_file = project_cwd / ".claude-mpm" / "state" / "context-usage.json"
    state_file.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    assert context_circuit_breaker.evaluate(_event(project_cwd)) == {}


def test_missing_percentage_field_fails_open(project_cwd: Path) -> None:
    _write_state(project_cwd, {"session_id": "sess-current"})
    assert context_circuit_breaker.evaluate(_event(project_cwd)) == {}


def test_non_numeric_percentage_fails_open(project_cwd: Path) -> None:
    _write_state(
        project_cwd,
        {"session_id": "sess-current", "percentage_used": "lots"},
    )
    assert context_circuit_breaker.evaluate(_event(project_cwd)) == {}


def test_no_cwd_fails_open() -> None:
    assert context_circuit_breaker.evaluate({"tool_name": "Edit"}) == {}


def test_state_session_id_missing_still_blocks(project_cwd: Path) -> None:
    # If the state file omits session_id, we can't validate -- but the
    # breaker must still trip on critical context: missing session_id in the
    # state is treated as "no mismatch" (don't fail open just because the
    # writer hasn't recorded a session yet).
    _write_state(project_cwd, {"percentage_used": 96.0})
    decision = context_circuit_breaker.evaluate(_event(project_cwd))
    assert decision.get("permissionDecision") == "deny"
