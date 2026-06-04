"""Unit tests for the PreToolUse context circuit-breaker (issue #420, #642).

Coverage requirements (issue #642):
(a) Correct context-window resolution for a 1 M-context model vs a 200 K model.
(b) Percentage clamped at 100 when raw tokens exceed the window.
(c) Read-only / recovery tools are allowed through even when threshold is exceeded.
(d) The CLAUDE_MPM_DISABLE_CONTEXT_BREAKER disable switch fully bypasses the breaker.
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING
from unittest import mock

import pytest

from claude_mpm.hooks import context_circuit_breaker
from claude_mpm.hooks.model_context_window import (
    CONTEXT_WINDOW_MAP,
    DEFAULT_CONTEXT_WINDOW,
    resolve_context_window,
)

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def project_cwd(tmp_path: Path) -> Path:
    """Create a fake project directory with the state subtree."""
    (tmp_path / ".claude-mpm" / "state").mkdir(parents=True)
    return tmp_path


def _write_state(cwd: Path, state: dict) -> None:
    state_file = cwd / ".claude-mpm" / "state" / "context-usage.json"
    state_file.write_text(json.dumps(state), encoding="utf-8")


def _event(
    cwd: Path,
    session_id: str = "sess-current",
    tool_name: str = "Edit",
) -> dict:
    return {
        "cwd": str(cwd),
        "session_id": session_id,
        "tool_name": tool_name,
        "tool_input": {},
    }


# ---------------------------------------------------------------------------
# (a) Context-window resolution: 1 M-context vs 200 K models
# ---------------------------------------------------------------------------


class TestModelContextWindowResolution:
    """Verify that the model→window map returns correct values."""

    def test_opus_4_resolves_to_1m(self) -> None:
        window = resolve_context_window("claude-opus-4")
        assert window == 1_000_000

    def test_opus_4_with_version_suffix_resolves_to_1m(self) -> None:
        window = resolve_context_window("claude-opus-4-6-20260101")
        assert window == 1_000_000

    def test_opus_4_6_resolves_to_1m(self) -> None:
        window = resolve_context_window("claude-opus-4-6")
        assert window == 1_000_000

    def test_sonnet_4_5_resolves_to_1m(self) -> None:
        window = resolve_context_window("claude-sonnet-4-5")
        assert window == 1_000_000

    def test_sonnet_4_5_with_date_resolves_to_1m(self) -> None:
        window = resolve_context_window("claude-sonnet-4-5-20250601")
        assert window == 1_000_000

    def test_sonnet_4_0_resolves_to_200k(self) -> None:
        # Sonnet 4.0 is a 200 K model.
        window = resolve_context_window("claude-sonnet-4-0")
        assert window == DEFAULT_CONTEXT_WINDOW

    def test_haiku_resolves_to_200k(self) -> None:
        window = resolve_context_window("claude-haiku-4")
        assert window == DEFAULT_CONTEXT_WINDOW

    def test_sonnet_3_5_resolves_to_200k(self) -> None:
        window = resolve_context_window("claude-3-5-sonnet-20241022")
        assert window == DEFAULT_CONTEXT_WINDOW

    def test_unknown_model_returns_default(self) -> None:
        window = resolve_context_window("gpt-4-turbo")
        assert window == DEFAULT_CONTEXT_WINDOW

    def test_none_model_returns_default_without_env(self) -> None:
        """When no model is set in env or settings, default is returned."""
        # Patch _detect_active_model to return None, simulating no configured model.
        with mock.patch(
            "claude_mpm.hooks.model_context_window._detect_active_model",
            return_value=None,
        ):
            window = resolve_context_window(None)
        assert window == DEFAULT_CONTEXT_WINDOW

    def test_anthropic_model_env_var_is_used(self) -> None:
        """ANTHROPIC_MODEL env var drives resolve_context_window(None)."""
        with mock.patch.dict(
            os.environ, {"ANTHROPIC_MODEL": "claude-opus-4-6"}, clear=False
        ):
            window = resolve_context_window(None)
        assert window == 1_000_000

    def test_claude_model_env_var_is_used_as_fallback(self) -> None:
        """CLAUDE_MODEL env var is used when ANTHROPIC_MODEL is absent."""
        env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_MODEL"}
        env["CLAUDE_MODEL"] = "claude-opus-4"
        with mock.patch.dict(os.environ, env, clear=True):
            window = resolve_context_window(None)
        assert window == 1_000_000

    def test_map_has_1m_entries_for_opus_4(self) -> None:
        """Sanity check: CONTEXT_WINDOW_MAP contains 1 M entries for Opus 4.x."""
        opus_entries = {k: v for k, v in CONTEXT_WINDOW_MAP.items() if "opus-4" in k}
        assert all(v == 1_000_000 for v in opus_entries.values()), opus_entries


# ---------------------------------------------------------------------------
# (b) Percentage clamped at 100
# ---------------------------------------------------------------------------


class TestPercentageClamping:
    """Verify that percentage_used > 100 is clamped before evaluation."""

    def test_percentage_above_100_is_clamped_to_100(self, project_cwd: Path) -> None:
        """When stored percentage_used > 100, it is clamped to 100 (not >100)."""
        # Use raw token counts that exceed the 200 K window significantly.
        # With a 200 K model and 250 K tokens, raw_pct = 125 % → clamped to 100.
        _write_state(
            project_cwd,
            {
                "session_id": "sess-current",
                "cumulative_input_tokens": 230_000,
                "cumulative_output_tokens": 20_000,
                "percentage_used": 125.0,
            },
        )
        with mock.patch.dict(
            os.environ, {"ANTHROPIC_MODEL": "claude-sonnet-4-0"}, clear=False
        ):
            decision = context_circuit_breaker.evaluate(_event(project_cwd))
        # Should fire the warning (clamped 100 >= 95).
        assert decision.get("permissionDecision") == "warn"
        # The displayed percentage must be at most 100.
        reason = decision.get("permissionDecisionReason", "")
        # The reason embeds the percentage; it should not say > 100.
        assert "101" not in reason
        assert "125" not in reason

    def test_stored_percentage_125_clamped_to_100_in_fallback(
        self, project_cwd: Path
    ) -> None:
        """When only percentage_used is stored (no raw tokens), clamp to 100."""
        _write_state(
            project_cwd,
            {
                "session_id": "sess-current",
                # No cumulative_input_tokens / cumulative_output_tokens.
                "percentage_used": 125.0,
            },
        )
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ANTHROPIC_MODEL", None)
            os.environ.pop("CLAUDE_MODEL", None)
            decision = context_circuit_breaker.evaluate(_event(project_cwd))
        assert decision.get("permissionDecision") == "warn"
        reason = decision.get("permissionDecisionReason", "")
        assert "125" not in reason
        assert "101" not in reason


# ---------------------------------------------------------------------------
# (c) Read-only / recovery tools pass through even above threshold
# ---------------------------------------------------------------------------


class TestAlwaysAllowedTools:
    """Tools in ALWAYS_ALLOWED_TOOLS are never blocked or warned."""

    @pytest.mark.parametrize(
        "tool",
        [
            "Read",
            "Grep",
            "Glob",
            "LS",
            "NotebookRead",
            "WebSearch",
            "WebFetch",
            "TodoRead",
            "TodoWrite",
            "exit_plan_mode",
        ],
    )
    def test_read_only_tool_passes_above_threshold(
        self, project_cwd: Path, tool: str
    ) -> None:
        """Read-only / recovery tools are always allowed, even at 99 %."""
        _write_state(
            project_cwd,
            {"session_id": "sess-current", "percentage_used": 99.0},
        )
        event = _event(project_cwd, tool_name=tool)
        result = context_circuit_breaker.evaluate(event)
        assert result == {}, f"Expected pass-through for {tool!r}, got {result!r}"

    def test_always_allowed_tools_constant_is_not_empty(self) -> None:
        """Sanity: the constant contains the expected recovery tools."""
        required = {"Read", "Grep", "Glob"}
        assert required.issubset(context_circuit_breaker.ALWAYS_ALLOWED_TOOLS)

    def test_edit_is_not_always_allowed(self, project_cwd: Path) -> None:
        """Edit tool is NOT in the always-allowed set and CAN be warned."""
        _write_state(
            project_cwd,
            {"session_id": "sess-current", "percentage_used": 99.0},
        )
        event = _event(project_cwd, tool_name="Edit")
        result = context_circuit_breaker.evaluate(event)
        # Should fire a warning for Edit at 99 %.
        assert result.get("permissionDecision") == "warn"


# ---------------------------------------------------------------------------
# (d) Disable switch
# ---------------------------------------------------------------------------


class TestDisableSwitch:
    """CLAUDE_MPM_DISABLE_CONTEXT_BREAKER bypasses the breaker entirely."""

    def test_env_var_disables_breaker(self, project_cwd: Path) -> None:
        """Setting CLAUDE_MPM_DISABLE_CONTEXT_BREAKER=1 bypasses the breaker."""
        _write_state(
            project_cwd,
            {"session_id": "sess-current", "percentage_used": 99.0},
        )
        with mock.patch.dict(
            os.environ,
            {"CLAUDE_MPM_DISABLE_CONTEXT_BREAKER": "1"},
            clear=False,
        ):
            result = context_circuit_breaker.evaluate(_event(project_cwd))
        assert result == {}

    def test_env_var_true_disables_breaker(self, project_cwd: Path) -> None:
        _write_state(
            project_cwd,
            {"session_id": "sess-current", "percentage_used": 99.0},
        )
        with mock.patch.dict(
            os.environ,
            {"CLAUDE_MPM_DISABLE_CONTEXT_BREAKER": "true"},
            clear=False,
        ):
            result = context_circuit_breaker.evaluate(_event(project_cwd))
        assert result == {}

    def test_env_var_yes_disables_breaker(self, project_cwd: Path) -> None:
        _write_state(
            project_cwd,
            {"session_id": "sess-current", "percentage_used": 99.0},
        )
        with mock.patch.dict(
            os.environ,
            {"CLAUDE_MPM_DISABLE_CONTEXT_BREAKER": "yes"},
            clear=False,
        ):
            result = context_circuit_breaker.evaluate(_event(project_cwd))
        assert result == {}

    def test_env_var_0_does_not_disable(self, project_cwd: Path) -> None:
        """CLAUDE_MPM_DISABLE_CONTEXT_BREAKER=0 should NOT disable the breaker."""
        _write_state(
            project_cwd,
            {"session_id": "sess-current", "percentage_used": 99.0},
        )
        # Remove the env var first to ensure clean state, then set to "0".
        env = dict(os.environ.items())
        env["CLAUDE_MPM_DISABLE_CONTEXT_BREAKER"] = "0"
        with mock.patch.dict(os.environ, env, clear=True):
            result = context_circuit_breaker.evaluate(_event(project_cwd))
        assert result.get("permissionDecision") == "warn"

    def test_config_file_disabled_key_disables_breaker(self, project_cwd: Path) -> None:
        """context_circuit_breaker.disabled: true in settings.json disables breaker."""
        _write_state(
            project_cwd,
            {"session_id": "sess-current", "percentage_used": 99.0},
        )
        # Write a .claude/settings.json with the disable key.
        settings_dir = project_cwd / ".claude"
        settings_dir.mkdir(parents=True, exist_ok=True)
        (settings_dir / "settings.json").write_text(
            json.dumps({"context_circuit_breaker": {"disabled": True}}),
            encoding="utf-8",
        )
        with mock.patch.dict(
            os.environ,
            {"CLAUDE_MPM_DISABLE_CONTEXT_BREAKER": ""},  # ensure env is off
            clear=False,
        ):
            result = context_circuit_breaker.evaluate(_event(project_cwd))
        assert result == {}

    def test_disable_switch_name_in_warning_message(self, project_cwd: Path) -> None:
        """The warning message must mention the disable env var."""
        _write_state(
            project_cwd,
            {"session_id": "sess-current", "percentage_used": 99.0},
        )
        result = context_circuit_breaker.evaluate(_event(project_cwd))
        reason = result.get("permissionDecisionReason", "")
        assert "CLAUDE_MPM_DISABLE_CONTEXT_BREAKER" in reason


# ---------------------------------------------------------------------------
# Existing threshold / fail-open behavior (regression tests)
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


def test_at_exactly_95_warns(project_cwd: Path) -> None:
    _write_state(
        project_cwd,
        {"session_id": "sess-current", "percentage_used": 95.0},
    )
    decision = context_circuit_breaker.evaluate(_event(project_cwd))
    # Post-#642: at threshold the decision is "warn", not "deny".
    assert decision.get("permissionDecision") == "warn"
    assert "95%" in decision.get("permissionDecisionReason", "")


def test_above_95_warns_with_percentage_in_reason(project_cwd: Path) -> None:
    _write_state(
        project_cwd,
        {"session_id": "sess-current", "percentage_used": 97.4},
    )
    decision = context_circuit_breaker.evaluate(_event(project_cwd))
    assert decision.get("permissionDecision") == "warn"
    reason = decision.get("permissionDecisionReason", "")
    # 97.4 % rounds to 97 for display.
    assert "97%" in reason


def test_state_file_missing_fails_open(tmp_path: Path) -> None:
    event = _event(tmp_path)
    assert context_circuit_breaker.evaluate(event) == {}


def test_session_id_mismatch_fails_open(project_cwd: Path) -> None:
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


def test_state_session_id_missing_still_warns(project_cwd: Path) -> None:
    """Missing session_id in state → no mismatch → breaker fires (warn, not deny)."""
    _write_state(project_cwd, {"percentage_used": 96.0})
    decision = context_circuit_breaker.evaluate(_event(project_cwd))
    assert decision.get("permissionDecision") == "warn"


# ---------------------------------------------------------------------------
# Dynamic window recomputation from raw tokens
# ---------------------------------------------------------------------------


class TestDynamicWindowFromRawTokens:
    """Verify that raw token counts are recomputed against the real model window."""

    def test_1m_model_with_250k_tokens_does_not_fire(self, project_cwd: Path) -> None:
        """250 K tokens on a 1 M-context model = 25 % — well below 95 %."""
        _write_state(
            project_cwd,
            {
                "session_id": "sess-current",
                "cumulative_input_tokens": 230_000,
                "cumulative_output_tokens": 20_000,
                "percentage_used": 125.0,  # stale/wrong value from 200 K budget
            },
        )
        with mock.patch.dict(
            os.environ, {"ANTHROPIC_MODEL": "claude-opus-4-6"}, clear=False
        ):
            result = context_circuit_breaker.evaluate(_event(project_cwd))
        # 250 K / 1 M = 25 % → no warning.
        assert result == {}

    def test_200k_model_at_190k_tokens_fires(self, project_cwd: Path) -> None:
        """190 K tokens on a 200 K model = 95 % → warning fires."""
        _write_state(
            project_cwd,
            {
                "session_id": "sess-current",
                "cumulative_input_tokens": 180_000,
                "cumulative_output_tokens": 10_000,
                "percentage_used": 95.0,
            },
        )
        with mock.patch.dict(
            os.environ, {"ANTHROPIC_MODEL": "claude-sonnet-4-0"}, clear=False
        ):
            result = context_circuit_breaker.evaluate(_event(project_cwd))
        assert result.get("permissionDecision") == "warn"

    def test_1m_model_at_960k_tokens_fires(self, project_cwd: Path) -> None:
        """960 K tokens on a 1 M model = 96 % → warning fires."""
        _write_state(
            project_cwd,
            {
                "session_id": "sess-current",
                "cumulative_input_tokens": 900_000,
                "cumulative_output_tokens": 60_000,
                "percentage_used": 98.0,
            },
        )
        with mock.patch.dict(
            os.environ, {"ANTHROPIC_MODEL": "claude-opus-4-6"}, clear=False
        ):
            result = context_circuit_breaker.evaluate(_event(project_cwd))
        assert result.get("permissionDecision") == "warn"
