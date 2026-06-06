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
        # Post-#642: decision is "allow" (documented value) not "warn" (undocumented).
        assert decision.get("permissionDecision") == "allow"
        # The displayed percentage must be at most 100.
        reason = decision.get("permissionDecisionReason", "")
        # The reason embeds the percentage; it should not say > 100.
        assert "101" not in reason
        assert "125" not in reason

    def test_stored_percentage_125_clamped_to_100_in_fallback(
        self, project_cwd: Path
    ) -> None:
        """When only percentage_used is stored (no raw tokens), clamp to 100.

        _detect_active_model is mocked to return None so this test is fully
        deterministic regardless of what .claude/settings.json exists in the
        repo (e.g. claude-sonnet-4-6 = 1 M would swallow 125 % as 12.5 %).
        """
        _write_state(
            project_cwd,
            {
                "session_id": "sess-current",
                # No cumulative_input_tokens / cumulative_output_tokens.
                "percentage_used": 125.0,
            },
        )
        with mock.patch(
            "claude_mpm.hooks.model_context_window._detect_active_model",
            return_value=None,
        ):
            decision = context_circuit_breaker.evaluate(_event(project_cwd))
        # "allow" is the documented PreToolUse value for allow-with-warning.
        assert decision.get("permissionDecision") == "allow"
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
        """Edit is NOT in the always-allowed set: fires allow-with-warning at threshold.

        Critically: a non-allowlisted tool at/above threshold must be ALLOWED
        (permissionDecision == "allow"), never denied — the invariant of issue #642.
        """
        _write_state(
            project_cwd,
            {"session_id": "sess-current", "percentage_used": 99.0},
        )
        event = _event(project_cwd, tool_name="Edit")
        result = context_circuit_breaker.evaluate(event)
        # Must be "allow" (documented value) with a reason — never "deny" or "warn".
        assert result.get("permissionDecision") == "allow", (
            "Non-allowlisted tool at threshold must be ALLOWED-with-warning, not "
            f"blocked.  Got: {result.get('permissionDecision')!r}"
        )
        assert result.get("permissionDecisionReason"), (
            "Warning reason must be non-empty"
        )


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
        # "allow" is the documented value; "warn" is not valid.
        assert result.get("permissionDecision") == "allow"

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


def test_at_exactly_95_fires_allow_with_warning(project_cwd: Path) -> None:
    _write_state(
        project_cwd,
        {"session_id": "sess-current", "percentage_used": 95.0},
    )
    decision = context_circuit_breaker.evaluate(_event(project_cwd))
    # Post-#642: at threshold the decision is "allow" (documented) + reason text.
    # "warn" is not a documented PreToolUse value and was replaced.
    assert decision.get("permissionDecision") == "allow"
    assert "95%" in decision.get("permissionDecisionReason", "")


def test_above_95_allows_with_warning_and_percentage_in_reason(
    project_cwd: Path,
) -> None:
    _write_state(
        project_cwd,
        {"session_id": "sess-current", "percentage_used": 97.4},
    )
    decision = context_circuit_breaker.evaluate(_event(project_cwd))
    assert decision.get("permissionDecision") == "allow"
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


def test_state_session_id_missing_still_fires_allow_with_warning(
    project_cwd: Path,
) -> None:
    """Missing session_id in state → no mismatch → breaker fires allow-with-warning."""
    _write_state(project_cwd, {"percentage_used": 96.0})
    decision = context_circuit_breaker.evaluate(_event(project_cwd))
    assert decision.get("permissionDecision") == "allow"


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
        """190 K tokens on a 200 K model = 95 % → allow-with-warning fires."""
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
        assert result.get("permissionDecision") == "allow"

    def test_1m_model_at_960k_tokens_fires(self, project_cwd: Path) -> None:
        """960 K tokens on a 1 M model = 96 % → allow-with-warning fires."""
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
        assert result.get("permissionDecision") == "allow"


# ---------------------------------------------------------------------------
# Protocol-safety: only documented permissionDecision values are emitted
# ---------------------------------------------------------------------------


class TestProtocolSafeOutput:
    """The breaker must only emit documented permissionDecision values.

    The Claude Code PreToolUse protocol accepts exactly three values:
    "allow", "deny", "ask".  "warn" is not documented and risks being
    treated as deny/error, reproducing the original bug #642.
    """

    _DOCUMENTED_VALUES = frozenset({"allow", "deny", "ask"})

    def test_threshold_exceeded_emits_allow_not_warn(self, project_cwd: Path) -> None:
        """At/above threshold: permissionDecision must be a documented value."""
        _write_state(
            project_cwd,
            {"session_id": "sess-current", "percentage_used": 99.0},
        )
        result = context_circuit_breaker.evaluate(_event(project_cwd))
        decision = result.get("permissionDecision")
        assert decision in self._DOCUMENTED_VALUES, (
            f"permissionDecision {decision!r} is not a documented Claude Code "
            f"PreToolUse value.  Valid values: {sorted(self._DOCUMENTED_VALUES)}"
        )
        # Specifically: must be "allow" (never "deny" — that would hard-block).
        assert decision == "allow"

    def test_threshold_exceeded_has_reason_text(self, project_cwd: Path) -> None:
        """The warning text is carried in permissionDecisionReason."""
        _write_state(
            project_cwd,
            {"session_id": "sess-current", "percentage_used": 99.0},
        )
        result = context_circuit_breaker.evaluate(_event(project_cwd))
        reason = result.get("permissionDecisionReason", "")
        assert reason, "permissionDecisionReason must be non-empty when threshold fires"
        assert "compact" in reason.lower() or "context" in reason.lower(), (
            "Warning reason should mention context management options"
        )

    def test_non_allowlisted_tool_at_threshold_is_allowed_not_denied(
        self, project_cwd: Path
    ) -> None:
        """Non-allowlisted tools (Bash, Edit, Write) at/above threshold must be ALLOWED.

        This is the core invariant of issue #642: the breaker must NEVER
        hard-block tool calls.  A session at threshold must remain usable.
        """
        for tool in ("Bash", "Edit", "Write", "MultiEdit", "Task"):
            _write_state(
                project_cwd,
                {"session_id": "sess-current", "percentage_used": 99.0},
            )
            result = context_circuit_breaker.evaluate(
                _event(project_cwd, tool_name=tool)
            )
            decision = result.get("permissionDecision")
            assert decision != "deny", (
                f"Tool {tool!r} at threshold was DENIED — reproduces bug #642. "
                "The breaker must allow-with-warning, never hard-block."
            )
            assert decision == "allow", (
                f"Tool {tool!r} at threshold: expected 'allow', got {decision!r}"
            )

    def test_evaluate_never_returns_warn_string(self, project_cwd: Path) -> None:
        """evaluate() must never return permissionDecision == 'warn' (undocumented)."""
        _write_state(
            project_cwd,
            {"session_id": "sess-current", "percentage_used": 99.0},
        )
        result = context_circuit_breaker.evaluate(_event(project_cwd))
        assert result.get("permissionDecision") != "warn", (
            "'warn' is not a documented PreToolUse permissionDecision value "
            "and was removed in the #642 fix."
        )


# ---------------------------------------------------------------------------
# Prefix-match boundary fix
# ---------------------------------------------------------------------------


class TestPrefixMatchBoundary:
    """Verify that prefix matching requires a delimiter boundary."""

    def test_sonnet_4_5_does_not_match_hypothetical_4_50(self) -> None:
        """claude-sonnet-4-50 must NOT match the claude-sonnet-4-5 (1 M) prefix."""
        window = resolve_context_window("claude-sonnet-4-50")
        # claude-sonnet-4-50 is not in the map; fallback to DEFAULT (200 K).
        # It must NOT inherit the 1 M window from the "claude-sonnet-4-5" entry.
        assert window == DEFAULT_CONTEXT_WINDOW, (
            f"claude-sonnet-4-50 matched claude-sonnet-4-5 (1 M) prefix — "
            f"boundary check failed.  Got {window}"
        )

    def test_sonnet_4_5_with_date_still_resolves_to_1m(self) -> None:
        """claude-sonnet-4-5-20251201 (genuine date variant) still resolves 1 M."""
        window = resolve_context_window("claude-sonnet-4-5-20251201")
        assert window == 1_000_000

    def test_sonnet_4_6_with_date_still_resolves_to_1m(self) -> None:
        """claude-sonnet-4-6-20260101 (genuine date variant) still resolves 1 M."""
        window = resolve_context_window("claude-sonnet-4-6-20260101")
        assert window == 1_000_000


# ---------------------------------------------------------------------------
# (e) Configurable threshold — issue #681
# ---------------------------------------------------------------------------


class TestConfigurableThreshold:
    """Verify that the warning threshold can be overridden via env var or settings.

    Coverage requirements (issue #681):
    (e1) Default threshold is 95.0 when neither env var nor settings key is set.
    (e2) settings.json threshold_pct overrides the default.
    (e3) Env var overrides settings (env > settings > default precedence).
    (e4) Invalid threshold values are handled fail-open (default used, no crash).
    (e5) disabled knob still works alongside configurable threshold.
    """

    # --- (e1) Default threshold ---

    def test_default_threshold_is_95(self, project_cwd: Path) -> None:
        """When neither env var nor settings is set, threshold defaults to 95.0."""
        _write_state(
            project_cwd,
            {"session_id": "sess-current", "percentage_used": 94.9},
        )
        # Remove the threshold env var to get a clean default.
        env = {
            k: v
            for k, v in os.environ.items()
            if k != "CLAUDE_MPM_CONTEXT_BREAKER_THRESHOLD"
        }
        with mock.patch.dict(os.environ, env, clear=True):
            result = context_circuit_breaker.evaluate(_event(project_cwd))
        # 94.9 < 95.0 default -> pass-through
        assert result == {}

    def test_default_threshold_fires_at_95(self, project_cwd: Path) -> None:
        """Default threshold: warning fires at exactly 95.0."""
        _write_state(
            project_cwd,
            {"session_id": "sess-current", "percentage_used": 95.0},
        )
        env = {
            k: v
            for k, v in os.environ.items()
            if k != "CLAUDE_MPM_CONTEXT_BREAKER_THRESHOLD"
        }
        with mock.patch.dict(os.environ, env, clear=True):
            result = context_circuit_breaker.evaluate(_event(project_cwd))
        assert result.get("permissionDecision") == "allow"

    # --- (e2) settings.json threshold_pct ---

    def test_settings_threshold_pct_overrides_default(self, project_cwd: Path) -> None:
        """settings.json threshold_pct: warning fires at the configured value."""
        # Set threshold to 80 in settings — warning should fire at 80, not 95.
        settings_dir = project_cwd / ".claude"
        settings_dir.mkdir(parents=True, exist_ok=True)
        (settings_dir / "settings.json").write_text(
            json.dumps({"context_circuit_breaker": {"threshold_pct": 80}}),
            encoding="utf-8",
        )
        _write_state(
            project_cwd,
            {"session_id": "sess-current", "percentage_used": 82.0},
        )
        env = {
            k: v
            for k, v in os.environ.items()
            if k != "CLAUDE_MPM_CONTEXT_BREAKER_THRESHOLD"
        }
        with mock.patch.dict(os.environ, env, clear=True):
            result = context_circuit_breaker.evaluate(_event(project_cwd))
        # 82.0 >= 80 (settings threshold) -> allow-with-warning
        assert result.get("permissionDecision") == "allow"

    def test_settings_threshold_pct_below_percentage_passes(
        self, project_cwd: Path
    ) -> None:
        """settings.json threshold_pct=90: 85% usage is below threshold, passes."""
        settings_dir = project_cwd / ".claude"
        settings_dir.mkdir(parents=True, exist_ok=True)
        (settings_dir / "settings.json").write_text(
            json.dumps({"context_circuit_breaker": {"threshold_pct": 90}}),
            encoding="utf-8",
        )
        _write_state(
            project_cwd,
            {"session_id": "sess-current", "percentage_used": 85.0},
        )
        env = {
            k: v
            for k, v in os.environ.items()
            if k != "CLAUDE_MPM_CONTEXT_BREAKER_THRESHOLD"
        }
        with mock.patch.dict(os.environ, env, clear=True):
            result = context_circuit_breaker.evaluate(_event(project_cwd))
        # 85.0 < 90 (settings threshold) -> pass-through
        assert result == {}

    def test_settings_threshold_pct_float_value(self, project_cwd: Path) -> None:
        """settings.json threshold_pct accepts float values (e.g. 85.5)."""
        settings_dir = project_cwd / ".claude"
        settings_dir.mkdir(parents=True, exist_ok=True)
        (settings_dir / "settings.json").write_text(
            json.dumps({"context_circuit_breaker": {"threshold_pct": 85.5}}),
            encoding="utf-8",
        )
        _write_state(
            project_cwd,
            {"session_id": "sess-current", "percentage_used": 86.0},
        )
        env = {
            k: v
            for k, v in os.environ.items()
            if k != "CLAUDE_MPM_CONTEXT_BREAKER_THRESHOLD"
        }
        with mock.patch.dict(os.environ, env, clear=True):
            result = context_circuit_breaker.evaluate(_event(project_cwd))
        # 86.0 >= 85.5 -> allow-with-warning
        assert result.get("permissionDecision") == "allow"

    # --- (e3) Env var overrides settings ---

    def test_env_var_overrides_settings_threshold(self, project_cwd: Path) -> None:
        """CLAUDE_MPM_CONTEXT_BREAKER_THRESHOLD env var overrides settings value."""
        # settings says 90 but env says 70 -> env wins
        settings_dir = project_cwd / ".claude"
        settings_dir.mkdir(parents=True, exist_ok=True)
        (settings_dir / "settings.json").write_text(
            json.dumps({"context_circuit_breaker": {"threshold_pct": 90}}),
            encoding="utf-8",
        )
        _write_state(
            project_cwd,
            {"session_id": "sess-current", "percentage_used": 75.0},
        )
        with mock.patch.dict(
            os.environ,
            {"CLAUDE_MPM_CONTEXT_BREAKER_THRESHOLD": "70"},
            clear=False,
        ):
            result = context_circuit_breaker.evaluate(_event(project_cwd))
        # 75.0 >= 70 (env threshold) -> allow-with-warning
        assert result.get("permissionDecision") == "allow"

    def test_env_var_threshold_passes_below(self, project_cwd: Path) -> None:
        """Env var threshold=85: usage at 80% is below it, passes through."""
        _write_state(
            project_cwd,
            {"session_id": "sess-current", "percentage_used": 80.0},
        )
        with mock.patch.dict(
            os.environ,
            {"CLAUDE_MPM_CONTEXT_BREAKER_THRESHOLD": "85"},
            clear=False,
        ):
            result = context_circuit_breaker.evaluate(_event(project_cwd))
        assert result == {}

    def test_env_var_threshold_overrides_default_when_no_settings(
        self, project_cwd: Path
    ) -> None:
        """Env var threshold overrides default even when no settings file exists."""
        _write_state(
            project_cwd,
            {"session_id": "sess-current", "percentage_used": 70.0},
        )
        with mock.patch.dict(
            os.environ,
            {"CLAUDE_MPM_CONTEXT_BREAKER_THRESHOLD": "65"},
            clear=False,
        ):
            result = context_circuit_breaker.evaluate(_event(project_cwd))
        # 70.0 >= 65 (env threshold) -> allow-with-warning
        assert result.get("permissionDecision") == "allow"

    # --- (e4) Invalid threshold values handled fail-open ---

    def test_invalid_env_var_string_uses_default(self, project_cwd: Path) -> None:
        """Non-numeric env var is ignored; default 95.0 is used (fail-open)."""
        _write_state(
            project_cwd,
            {"session_id": "sess-current", "percentage_used": 90.0},
        )
        with mock.patch.dict(
            os.environ,
            {"CLAUDE_MPM_CONTEXT_BREAKER_THRESHOLD": "not-a-number"},
            clear=False,
        ):
            result = context_circuit_breaker.evaluate(_event(project_cwd))
        # 90.0 < 95.0 (default fallback) -> pass-through
        assert result == {}

    def test_out_of_range_env_var_below_min_uses_default(
        self, project_cwd: Path
    ) -> None:
        """Env var value 0 (below min 1) is ignored; default 95.0 is used."""
        _write_state(
            project_cwd,
            {"session_id": "sess-current", "percentage_used": 90.0},
        )
        with mock.patch.dict(
            os.environ,
            {"CLAUDE_MPM_CONTEXT_BREAKER_THRESHOLD": "0"},
            clear=False,
        ):
            result = context_circuit_breaker.evaluate(_event(project_cwd))
        # 90.0 < 95.0 (default) -> pass-through
        assert result == {}

    def test_out_of_range_env_var_above_max_uses_default(
        self, project_cwd: Path
    ) -> None:
        """Env var value 101 (above max 100) is ignored; default 95.0 is used."""
        _write_state(
            project_cwd,
            {"session_id": "sess-current", "percentage_used": 96.0},
        )
        with mock.patch.dict(
            os.environ,
            {"CLAUDE_MPM_CONTEXT_BREAKER_THRESHOLD": "101"},
            clear=False,
        ):
            result = context_circuit_breaker.evaluate(_event(project_cwd))
        # 96.0 >= 95.0 (default) -> allow-with-warning
        assert result.get("permissionDecision") == "allow"

    def test_invalid_settings_threshold_uses_default(self, project_cwd: Path) -> None:
        """Non-numeric settings threshold is ignored; default 95.0 is used."""
        settings_dir = project_cwd / ".claude"
        settings_dir.mkdir(parents=True, exist_ok=True)
        (settings_dir / "settings.json").write_text(
            json.dumps({"context_circuit_breaker": {"threshold_pct": "bad-value"}}),
            encoding="utf-8",
        )
        _write_state(
            project_cwd,
            {"session_id": "sess-current", "percentage_used": 90.0},
        )
        env = {
            k: v
            for k, v in os.environ.items()
            if k != "CLAUDE_MPM_CONTEXT_BREAKER_THRESHOLD"
        }
        with mock.patch.dict(os.environ, env, clear=True):
            result = context_circuit_breaker.evaluate(_event(project_cwd))
        # Invalid settings -> falls back to default 95.0; 90.0 < 95.0 -> pass-through
        assert result == {}

    def test_out_of_range_settings_threshold_below_min_uses_default(
        self, project_cwd: Path
    ) -> None:
        """settings threshold_pct=0 (out of range) is ignored; default used."""
        settings_dir = project_cwd / ".claude"
        settings_dir.mkdir(parents=True, exist_ok=True)
        (settings_dir / "settings.json").write_text(
            json.dumps({"context_circuit_breaker": {"threshold_pct": 0}}),
            encoding="utf-8",
        )
        _write_state(
            project_cwd,
            {"session_id": "sess-current", "percentage_used": 90.0},
        )
        env = {
            k: v
            for k, v in os.environ.items()
            if k != "CLAUDE_MPM_CONTEXT_BREAKER_THRESHOLD"
        }
        with mock.patch.dict(os.environ, env, clear=True):
            result = context_circuit_breaker.evaluate(_event(project_cwd))
        # Out-of-range settings -> default 95.0; 90.0 < 95.0 -> pass-through
        assert result == {}

    def test_invalid_threshold_never_crashes(self, project_cwd: Path) -> None:
        """Completely malformed threshold config does not raise; returns valid result."""
        settings_dir = project_cwd / ".claude"
        settings_dir.mkdir(parents=True, exist_ok=True)
        # threshold_pct is a list -- completely wrong type
        (settings_dir / "settings.json").write_text(
            json.dumps({"context_circuit_breaker": {"threshold_pct": [1, 2, 3]}}),
            encoding="utf-8",
        )
        _write_state(
            project_cwd,
            {"session_id": "sess-current", "percentage_used": 99.0},
        )
        env = {
            k: v
            for k, v in os.environ.items()
            if k != "CLAUDE_MPM_CONTEXT_BREAKER_THRESHOLD"
        }
        with mock.patch.dict(os.environ, env, clear=True):
            # Must not raise
            result = context_circuit_breaker.evaluate(_event(project_cwd))
        # 99.0 >= 95.0 (default) -> allow-with-warning
        assert result.get("permissionDecision") == "allow"

    # --- (e5) disabled knob still works ---

    def test_disabled_still_bypasses_even_with_threshold_set(
        self, project_cwd: Path
    ) -> None:
        """disabled: true overrides threshold setting; breaker is fully bypassed."""
        settings_dir = project_cwd / ".claude"
        settings_dir.mkdir(parents=True, exist_ok=True)
        (settings_dir / "settings.json").write_text(
            json.dumps(
                {
                    "context_circuit_breaker": {
                        "disabled": True,
                        "threshold_pct": 50,
                    }
                }
            ),
            encoding="utf-8",
        )
        _write_state(
            project_cwd,
            {"session_id": "sess-current", "percentage_used": 99.0},
        )
        env = {
            k: v
            for k, v in os.environ.items()
            if k
            not in (
                "CLAUDE_MPM_DISABLE_CONTEXT_BREAKER",
                "CLAUDE_MPM_CONTEXT_BREAKER_THRESHOLD",
            )
        }
        with mock.patch.dict(os.environ, env, clear=True):
            result = context_circuit_breaker.evaluate(_event(project_cwd))
        # disabled: true -> pass-through regardless of threshold
        assert result == {}

    def test_threshold_in_warning_message(self, project_cwd: Path) -> None:
        """Warning message mentions the threshold env var and settings key."""
        _write_state(
            project_cwd,
            {"session_id": "sess-current", "percentage_used": 99.0},
        )
        env = {
            k: v
            for k, v in os.environ.items()
            if k != "CLAUDE_MPM_CONTEXT_BREAKER_THRESHOLD"
        }
        with mock.patch.dict(os.environ, env, clear=True):
            result = context_circuit_breaker.evaluate(_event(project_cwd))
        reason = result.get("permissionDecisionReason", "")
        assert "CLAUDE_MPM_CONTEXT_BREAKER_THRESHOLD" in reason
        assert "threshold_pct" in reason
