"""
Unit tests for the session_analysis service package.

Tests cover:
- pricing.py: rack-rate cost computation and unknown-model fallback
- transcript_parser.py: agent/skill/mcp extraction, subagent timestamp
  correlation (including the ambiguous parallel case), cost aggregation
- markdown_writer.py: render → read round-trip preserves event count + key fields
"""

from __future__ import annotations

import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from claude_mpm.services.session_analysis.markdown_writer import (
    read_markdown,
    render_markdown,
    write_report,
)

# ---------------------------------------------------------------------------
# Import the modules under test
# ---------------------------------------------------------------------------
from claude_mpm.services.session_analysis.pricing import (
    PRICING_RETRIEVED_DATE,
    Rates,
    compute_cost,
    resolve_model_rates,
)
from claude_mpm.services.session_analysis.transcript_parser import (
    SessionReport,
    TimelineEvent,
    _correlate_subagents,
    _encode_cwd,
    _last_line_timestamp,
    _parse_jsonl,
    _parse_subagent_transcript,
    _SubagentSummary,
    find_most_recent_session,
    locate_transcript,
    parse_session,
)

# ---------------------------------------------------------------------------
# Fixture paths
# ---------------------------------------------------------------------------

FIXTURES = Path(__file__).parent.parent.parent / "fixtures" / "session_analysis"
MAIN_JSONL = FIXTURES / "main_session.jsonl"
SUBAGENT_JSONL = FIXTURES / "subagent_python_engineer.jsonl"


# ===========================================================================
# transcript_parser.py — _encode_cwd regression test (GitHub #729)
# ===========================================================================


class TestEncodeCwd:
    """Regression tests for _encode_cwd: leading dash must be preserved."""

    def test_macos_path_keeps_leading_dash(self) -> None:
        # /Users/masa/Projects/claude-mpm → -Users-masa-Projects-claude-mpm
        assert (
            _encode_cwd("/Users/masa/Projects/claude-mpm")
            == "-Users-masa-Projects-claude-mpm"
        )

    def test_linux_path_keeps_leading_dash(self) -> None:
        # /home/user/project → -home-user-project
        assert _encode_cwd("/home/user/project") == "-home-user-project"


# ===========================================================================
# pricing.py tests
# ===========================================================================


class TestResolveModelRates:
    def test_opus_prefix_matched(self) -> None:
        rates = resolve_model_rates("claude-opus-4-7")
        assert rates.model_family == "opus"
        assert not rates.is_fallback

    def test_sonnet_prefix_matched(self) -> None:
        rates = resolve_model_rates("claude-sonnet-4-6")
        assert rates.model_family == "sonnet"
        assert not rates.is_fallback
        assert rates.input == 3.00
        assert rates.output == 15.00

    def test_haiku_prefix_matched(self) -> None:
        rates = resolve_model_rates("claude-haiku-3-5")
        assert rates.model_family == "haiku"
        assert not rates.is_fallback

    def test_case_insensitive_match(self) -> None:
        rates = resolve_model_rates("CLAUDE-SONNET-4")
        assert rates.model_family == "sonnet"
        assert not rates.is_fallback

    def test_unknown_model_returns_fallback(self) -> None:
        rates = resolve_model_rates("gpt-4o")
        assert rates.is_fallback
        assert rates.model_family == "unknown"

    def test_empty_string_returns_fallback(self) -> None:
        rates = resolve_model_rates("")
        assert rates.is_fallback

    def test_partial_match_no_false_positive(self) -> None:
        # "claude-o" should NOT match "claude-opus"
        rates = resolve_model_rates("claude-o-something")
        assert rates.is_fallback


class TestComputeCost:
    def test_zero_usage_returns_zero(self) -> None:
        cost = compute_cost("claude-sonnet-4-6", {})
        assert cost == 0.0

    def test_sonnet_input_output_only(self) -> None:
        # 1M input tokens at $3.00 + 1M output at $15.00 = $18.00
        cost = compute_cost(
            "claude-sonnet-4-6",
            {"input_tokens": 1_000_000, "output_tokens": 1_000_000},
        )
        assert abs(cost - 18.0) < 1e-9

    def test_haiku_all_token_types(self) -> None:
        # input=1M@0.80 + output=1M@4.00 + cache_write=1M@1.00 + cache_read=1M@0.08
        cost = compute_cost(
            "claude-haiku-3-5",
            {
                "input_tokens": 1_000_000,
                "output_tokens": 1_000_000,
                "cache_creation_input_tokens": 1_000_000,
                "cache_read_input_tokens": 1_000_000,
            },
        )
        expected = 0.80 + 4.00 + 1.00 + 0.08
        assert abs(cost - expected) < 1e-9

    def test_unknown_model_uses_sonnet_rates(self) -> None:
        # Should not raise; uses fallback rates (sonnet) and still computes
        cost = compute_cost("unknown-model-xyz", {"input_tokens": 1_000_000})
        assert cost == pytest.approx(3.00)

    def test_none_values_treated_as_zero(self) -> None:
        # Some JSONL lines have null values for token counts
        cost = compute_cost(
            "claude-sonnet-4-6",
            {"input_tokens": None, "output_tokens": None},  # type: ignore[arg-type]
        )
        assert cost == 0.0


# ===========================================================================
# pricing.py -- Fix B: PRICING_RETRIEVED_DATE constant + env-override path
# ===========================================================================


class TestPricingRetrievedDate:
    def test_date_constant_exists(self) -> None:
        assert PRICING_RETRIEVED_DATE == "2026-06-10"

    def test_env_override_loads_custom_rates(self, tmp_path: Path, monkeypatch) -> None:
        """CLAUDE_MPM_PRICING_FILE overrides the hardcoded _RATE_TABLE."""
        pricing_json = [
            {
                "prefix": "test-model",
                "input": 1.00,
                "output": 2.00,
                "cache_write": 0.50,
                "cache_read": 0.10,
                "model_family": "test",
            }
        ]
        pricing_file = tmp_path / "custom_pricing.json"
        pricing_file.write_text(
            __import__("json").dumps(pricing_json), encoding="utf-8"
        )

        monkeypatch.setenv("CLAUDE_MPM_PRICING_FILE", str(pricing_file))

        rates = resolve_model_rates("test-model-v1")
        assert rates.input == 1.00
        assert rates.output == 2.00
        assert rates.cache_write == 0.50
        assert rates.cache_read == 0.10
        assert rates.model_family == "test"
        assert not rates.is_fallback

    def test_env_override_missing_file_falls_back_to_hardcoded(
        self, monkeypatch
    ) -> None:
        """A non-existent CLAUDE_MPM_PRICING_FILE silently falls back to built-in table."""
        monkeypatch.setenv("CLAUDE_MPM_PRICING_FILE", "/nonexistent/path/pricing.json")
        rates = resolve_model_rates("claude-sonnet-4-6")
        assert rates.model_family == "sonnet"
        assert not rates.is_fallback


# ===========================================================================
# transcript_parser.py tests -- fixture-based
# ===========================================================================


class TestParseJsonl:
    def test_parses_valid_fixture(self) -> None:
        lines = _parse_jsonl(MAIN_JSONL)
        assert len(lines) == 6

    def test_all_items_are_dicts(self) -> None:
        lines = _parse_jsonl(MAIN_JSONL)
        assert all(isinstance(line, dict) for line in lines)

    def test_corrupt_line_skipped(self, tmp_path: Path) -> None:
        corrupt = tmp_path / "corrupt.jsonl"
        corrupt.write_text('{"ok": 1}\nNOT_JSON\n{"ok": 2}\n', encoding="utf-8")
        lines = _parse_jsonl(corrupt)
        assert len(lines) == 2


class TestParseSubagentTranscript:
    def test_attribution_agent_extracted(self) -> None:
        summary = _parse_subagent_transcript(SUBAGENT_JSONL)
        assert summary.attribution_agent == "Python Engineer"

    def test_prompt_text_is_first_user_message(self) -> None:
        summary = _parse_subagent_transcript(SUBAGENT_JSONL)
        assert "test_parser.py" in summary.prompt_text

    def test_response_text_is_last_assistant_text(self) -> None:
        summary = _parse_subagent_transcript(SUBAGENT_JSONL)
        # Last assistant message mentions the fix
        assert "regex" in summary.response_text.lower()

    def test_model_extracted(self) -> None:
        summary = _parse_subagent_transcript(SUBAGENT_JSONL)
        assert summary.model == "claude-haiku-3-5"

    def test_usage_aggregated(self) -> None:
        summary = _parse_subagent_transcript(SUBAGENT_JSONL)
        # Three assistant turns, each with input_tokens
        assert summary.usage["input_tokens"] > 0
        assert summary.usage["output_tokens"] > 0

    def test_cost_computed(self) -> None:
        summary = _parse_subagent_transcript(SUBAGENT_JSONL)
        assert summary.cost_usd > 0.0

    def test_all_events_populated(self) -> None:
        summary = _parse_subagent_transcript(SUBAGENT_JSONL)
        # 3 assistant turns → 3 events
        assert len(summary.all_events) == 3

    def test_tool_calls_extracted(self) -> None:
        summary = _parse_subagent_transcript(SUBAGENT_JSONL)
        # Events with Bash and Edit calls
        tool_names = {call.tool_name for ev in summary.all_events for call in ev.calls}
        assert "Bash" in tool_names
        assert "Edit" in tool_names

    def test_first_user_timestamp_set(self) -> None:
        summary = _parse_subagent_transcript(SUBAGENT_JSONL)
        assert summary.first_user_timestamp is not None
        assert summary.first_user_timestamp.year == 2025


class TestCorrelateSubagents:
    def _make_summary(self, ts: datetime, agent_id: str = "sa1") -> _SubagentSummary:
        """Build a minimal _SubagentSummary for correlation testing."""
        return _SubagentSummary(
            agent_id=agent_id,
            file_path=Path(f"agent-{agent_id}.jsonl"),
            attribution_agent="Test Agent",
            first_user_timestamp=ts,
            prompt_text="do stuff",
            response_text="done",
            model="claude-sonnet-4-6",
            usage={
                "input_tokens": 100,
                "output_tokens": 50,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
            },
            cost_usd=0.001,
            pricing_fallback=False,
            all_events=[],
        )

    def test_exact_match_correlates(self) -> None:
        ts = datetime(2025, 6, 10, 10, 0, 0, tzinfo=UTC)
        summary = self._make_summary(ts)
        calls = [(ts, "tu_001")]
        result = _correlate_subagents(calls, [summary])
        assert "tu_001" in result
        _, ambiguous = result["tu_001"]
        assert not ambiguous

    def test_within_tolerance_correlates(self) -> None:
        ts = datetime(2025, 6, 10, 10, 0, 0, tzinfo=UTC)
        call_ts = datetime(2025, 6, 10, 10, 0, 1, tzinfo=UTC)  # 1s off
        summary = self._make_summary(ts)
        calls = [(call_ts, "tu_001")]
        result = _correlate_subagents(calls, [summary])
        assert "tu_001" in result

    def test_outside_tolerance_not_correlated(self) -> None:
        ts = datetime(2025, 6, 10, 10, 0, 0, tzinfo=UTC)
        call_ts = datetime(2025, 6, 10, 10, 0, 10, tzinfo=UTC)  # 10s off
        summary = self._make_summary(ts)
        calls = [(call_ts, "tu_001")]
        result = _correlate_subagents(calls, [summary])
        assert "tu_001" not in result

    def test_parallel_ambiguous_case(self) -> None:
        """Two agent calls within tolerance of the same subagent → ambiguous."""
        ts = datetime(2025, 6, 10, 10, 0, 0, tzinfo=UTC)
        call_ts_a = datetime(2025, 6, 10, 10, 0, 0, tzinfo=UTC)
        call_ts_b = datetime(2025, 6, 10, 10, 0, 1, tzinfo=UTC)
        summary = self._make_summary(ts, agent_id="sa1")
        calls = [(call_ts_a, "tu_A"), (call_ts_b, "tu_B")]
        result = _correlate_subagents(calls, [summary])
        # Nearest match should be tu_A; ambiguous=True because tu_B is also within window
        assert "tu_A" in result
        _, ambiguous = result["tu_A"]
        assert ambiguous

    def test_no_subagents_returns_empty(self) -> None:
        ts = datetime(2025, 6, 10, 10, 0, 0, tzinfo=UTC)
        calls = [(ts, "tu_001")]
        result = _correlate_subagents(calls, [])
        assert result == {}

    def test_subagent_no_timestamp_skipped(self) -> None:
        summary = self._make_summary(datetime(2025, 6, 10, 10, 0, 0, tzinfo=UTC))
        summary.first_user_timestamp = None
        calls = [(datetime(2025, 6, 10, 10, 0, 0, tzinfo=UTC), "tu_001")]
        result = _correlate_subagents(calls, [summary])
        assert result == {}


class TestParseSessionFixture:
    """Integration test using a synthetic fixture transcript (no real ~/.claude access)."""

    def _build_session_tree(self, tmp_path: Path) -> tuple[str, str]:
        """Copy fixtures into a fake ~/.claude layout and return (session_id, cwd)."""
        # Encode cwd using the same function as production so fixture dirs match parser.
        fake_cwd = str(tmp_path / "fake" / "project")
        encoded = _encode_cwd(fake_cwd)
        session_id = "test-session-01"

        # Create main JSONL
        session_dir = tmp_path / ".claude" / "projects" / encoded
        session_dir.mkdir(parents=True)
        main_dest = session_dir / f"{session_id}.jsonl"
        main_dest.write_bytes(MAIN_JSONL.read_bytes())

        # Create subagent JSONL
        subagent_dir = session_dir / session_id / "subagents"
        subagent_dir.mkdir(parents=True)
        subagent_dest = subagent_dir / "agent-python-engineer.jsonl"
        subagent_dest.write_bytes(SUBAGENT_JSONL.read_bytes())

        return session_id, fake_cwd

    def test_events_extracted(self, tmp_path: Path, monkeypatch) -> None:
        session_id, cwd = self._build_session_tree(tmp_path)
        # Patch home directory so locate_transcript finds our fake layout
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        report = parse_session(session_id, cwd)
        # 3 user prompts get skipped (tool_result only); 1 real user + assistant turns
        assert len(report.events) > 0

    def test_session_title_from_first_user_message(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        session_id, cwd = self._build_session_tree(tmp_path)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        report = parse_session(session_id, cwd)
        assert "test_parser.py" in report.title or report.title != session_id

    def test_agent_call_counted(self, tmp_path: Path, monkeypatch) -> None:
        session_id, cwd = self._build_session_tree(tmp_path)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        report = parse_session(session_id, cwd)
        assert report.agent_call_count == 1

    def test_skill_call_counted(self, tmp_path: Path, monkeypatch) -> None:
        session_id, cwd = self._build_session_tree(tmp_path)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        report = parse_session(session_id, cwd)
        assert report.skill_call_count == 1

    def test_cost_aggregated(self, tmp_path: Path, monkeypatch) -> None:
        session_id, cwd = self._build_session_tree(tmp_path)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        report = parse_session(session_id, cwd)
        assert report.grand_total_cost_usd > 0.0
        assert report.pm_cost_usd > 0.0

    def test_subagent_cost_included(self, tmp_path: Path, monkeypatch) -> None:
        session_id, cwd = self._build_session_tree(tmp_path)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        report = parse_session(session_id, cwd)
        # Subagent transcript was parsed; cost should be > 0
        assert report.subagent_cost_usd > 0.0

    def test_github_link_extracted(self, tmp_path: Path, monkeypatch) -> None:
        session_id, cwd = self._build_session_tree(tmp_path)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        report = parse_session(session_id, cwd)
        links = " ".join(report.github_links)
        assert "github.com/example/repo/issues/42" in links

    def test_model_totals_populated(self, tmp_path: Path, monkeypatch) -> None:
        session_id, cwd = self._build_session_tree(tmp_path)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        report = parse_session(session_id, cwd)
        assert len(report.model_totals) > 0
        # PM model present
        assert "claude-sonnet-4-6" in report.model_totals

    def test_missing_transcript_returns_empty_report(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        report = parse_session("nonexistent-session", "/nonexistent/cwd")
        assert report.events == []
        assert report.grand_total_cost_usd == 0.0


class TestModelTotalsNoDoubleCount:
    """Fix 1: per-model cost must not be double-counted when PM and subagent share a model.

    Invariant:
        grand_total_cost_usd == pm_cost_usd + subagent_cost_usd
        grand_total_cost_usd == sum(mt.total_cost_usd for mt in model_totals.values())

    A shared model (claude-sonnet-4-6 in both the PM transcript and the subagent
    transcript) must have its cost counted EXACTLY ONCE — PM turns counted from the
    PM transcript, subagent turns counted from the subagent transcript aggregate.
    """

    # Subagent fixture that uses the SAME model as the PM (claude-sonnet-4-6)
    _SAME_MODEL_SUBAGENT = (
        Path(__file__).parent.parent.parent
        / "fixtures"
        / "session_analysis"
        / "subagent_sonnet_same_model.jsonl"
    )

    def _build_session_tree_same_model(self, tmp_path: Path) -> tuple[str, str]:
        """Lay out a fake ~/.claude tree using the same-model subagent fixture."""
        fake_cwd = str(tmp_path / "fake" / "project")
        encoded = _encode_cwd(fake_cwd)
        session_id = "test-session-samemodel"

        session_dir = tmp_path / ".claude" / "projects" / encoded
        session_dir.mkdir(parents=True)
        (session_dir / f"{session_id}.jsonl").write_bytes(MAIN_JSONL.read_bytes())

        subagent_dir = session_dir / session_id / "subagents"
        subagent_dir.mkdir(parents=True)
        (subagent_dir / "agent-python-engineer.jsonl").write_bytes(
            self._SAME_MODEL_SUBAGENT.read_bytes()
        )

        return session_id, fake_cwd

    def test_grand_total_equals_pm_plus_subagent(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        session_id, cwd = self._build_session_tree_same_model(tmp_path)
        report = parse_session(session_id, cwd)

        assert (
            abs(
                report.grand_total_cost_usd
                - (report.pm_cost_usd + report.subagent_cost_usd)
            )
            < 1e-9
        ), (
            f"grand_total={report.grand_total_cost_usd} != "
            f"pm={report.pm_cost_usd} + subagent={report.subagent_cost_usd}"
        )

    def test_grand_total_equals_sum_of_per_model_totals(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        session_id, cwd = self._build_session_tree_same_model(tmp_path)
        report = parse_session(session_id, cwd)

        per_model_sum = sum(mt.total_cost_usd for mt in report.model_totals.values())
        assert abs(report.grand_total_cost_usd - per_model_sum) < 1e-9, (
            f"grand_total={report.grand_total_cost_usd} != "
            f"sum(per-model)={per_model_sum}  model_totals={report.model_totals}"
        )

    def test_shared_model_cost_not_double_counted(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """When PM and subagent share claude-sonnet-4-6, the model total must equal
        (PM turns cost) + (subagent aggregate cost), NOT 2x either."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        session_id, cwd = self._build_session_tree_same_model(tmp_path)
        report = parse_session(session_id, cwd)

        # Both PM and the subagent use claude-sonnet-4-6
        assert "claude-sonnet-4-6" in report.model_totals
        mt = report.model_totals["claude-sonnet-4-6"]

        # The model total must equal the grand total (only one model in this session)
        assert abs(mt.total_cost_usd - report.grand_total_cost_usd) < 1e-9, (
            f"sonnet total={mt.total_cost_usd} != grand_total={report.grand_total_cost_usd}"
        )

        # The model total must equal pm_cost_usd + subagent_cost_usd
        expected = report.pm_cost_usd + report.subagent_cost_usd
        assert abs(mt.total_cost_usd - expected) < 1e-9, (
            f"sonnet total={mt.total_cost_usd} != pm+subagent={expected}"
        )

    def test_outcome_event_uses_subagent_last_timestamp(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Fix 5: synthetic outcome event timestamp must be the subagent's last event
        timestamp, not the parent agent_call dispatch time."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        session_id, cwd = self._build_session_tree_same_model(tmp_path)
        report = parse_session(session_id, cwd)

        # Find the agent_call event and the outcome event
        agent_call_events = [e for e in report.events if e.event_type == "agent_call"]
        outcome_events = [e for e in report.events if e.event_type == "outcome"]

        assert outcome_events, "No outcome event was generated"
        assert agent_call_events, "No agent_call event found"

        outcome = outcome_events[0]
        agent_call = agent_call_events[0]

        # The outcome timestamp must be >= the agent_call timestamp
        # (subagent completion is after dispatch).
        assert outcome.timestamp >= agent_call.timestamp, (
            f"outcome.timestamp {outcome.timestamp} < agent_call.timestamp {agent_call.timestamp}"
        )

        # The outcome timestamp must equal the subagent's last event timestamp —
        # the last line in the same-model subagent fixture is at 10:00:20.
        from datetime import UTC, datetime

        expected_ts = datetime(2025, 6, 10, 10, 0, 20, tzinfo=UTC)
        assert outcome.timestamp == expected_ts, (
            f"outcome.timestamp={outcome.timestamp} != expected {expected_ts}"
        )


class TestParallelDelegationNoCostDoubleCount:
    """Regression: two PM Agent calls that both correlate to the SAME subagent
    summary must not double-count the subagent's cost or tokens.

    The test patches _correlate_subagents to forcibly return both tu_A and tu_B
    mapped to the SAME _SubagentSummary object, simulating the ambiguous parallel
    delegation case.  After parse_session runs the accumulation loop, the
    invariants must hold:

        grand_total_cost_usd == pm_cost_usd + subagent_cost_usd
        grand_total_cost_usd == sum(mt.total_cost_usd for all models)
    """

    _PARALLEL_MAIN_JSONL = (
        Path(__file__).parent.parent.parent
        / "fixtures"
        / "session_analysis"
        / "parallel_pm_two_calls.jsonl"
    )

    def _build_session_tree(self, tmp_path: Path) -> tuple[str, str]:
        """Copy fixtures into a fake ~/.claude tree with two Agent calls."""
        fake_cwd = str(tmp_path / "fake" / "project")
        encoded = _encode_cwd(fake_cwd)
        session_id = "test-parallel-01"

        session_dir = tmp_path / ".claude" / "projects" / encoded
        session_dir.mkdir(parents=True)
        (session_dir / f"{session_id}.jsonl").write_bytes(
            self._PARALLEL_MAIN_JSONL.read_bytes()
        )

        # One subagent file — both PM calls will correlate to it
        subagent_dir = session_dir / session_id / "subagents"
        subagent_dir.mkdir(parents=True)
        (subagent_dir / "agent-python-engineer.jsonl").write_bytes(
            SUBAGENT_JSONL.read_bytes()
        )

        return session_id, fake_cwd

    def test_parallel_delegation_no_double_count(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Both tu_parallel_A and tu_parallel_B mapping to ONE summary -> cost counted once."""
        import claude_mpm.services.session_analysis.transcript_parser as _tp

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        session_id, cwd = self._build_session_tree(tmp_path)

        # Parse the subagent file to get a real summary with non-trivial cost
        summary = _tp._parse_subagent_transcript(
            tmp_path
            / ".claude"
            / "projects"
            / _encode_cwd(cwd)
            / session_id
            / "subagents"
            / "agent-python-engineer.jsonl"
        )

        # Force BOTH tool_use_ids to map to the SAME summary object
        def _fake_correlate(
            agent_calls: list[tuple],
            subagent_summaries: list,
        ) -> dict:
            return {
                "tu_parallel_A": (summary, True),
                "tu_parallel_B": (summary, True),
            }

        monkeypatch.setattr(_tp, "_correlate_subagents", _fake_correlate)

        report = _tp.parse_session(session_id, cwd)

        sa_cost = summary.cost_usd

        # Subagent cost must appear exactly ONCE
        assert abs(report.subagent_cost_usd - sa_cost) < 1e-9, (
            f"subagent_cost={report.subagent_cost_usd} != expected={sa_cost} "
            f"(double-count would be {2 * sa_cost})"
        )

        # Invariant 1: grand_total == pm + subagent
        assert (
            abs(
                report.grand_total_cost_usd
                - (report.pm_cost_usd + report.subagent_cost_usd)
            )
            < 1e-9
        ), (
            f"grand_total={report.grand_total_cost_usd} != "
            f"pm={report.pm_cost_usd} + subagent={report.subagent_cost_usd}"
        )

        # Invariant 2: grand_total == sum of per-model totals
        per_model_sum = sum(mt.total_cost_usd for mt in report.model_totals.values())
        assert abs(report.grand_total_cost_usd - per_model_sum) < 1e-9, (
            f"grand_total={report.grand_total_cost_usd} != "
            f"sum(per-model)={per_model_sum}  model_totals={report.model_totals}"
        )


class TestFindMostRecentSession:
    def test_returns_none_when_no_sessions(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        result = find_most_recent_session("/nonexistent/project")
        assert result is None

    def test_returns_most_recently_modified(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        cwd = "/test/proj"
        encoded = _encode_cwd(cwd)
        proj_dir = tmp_path / ".claude" / "projects" / encoded
        proj_dir.mkdir(parents=True)

        # Create two session files with different mtimes
        old_session = proj_dir / "old-session.jsonl"
        new_session = proj_dir / "new-session.jsonl"
        old_session.write_text("{}\n")
        new_session.write_text("{}\n")

        import os
        import time

        os.utime(old_session, (time.time() - 100, time.time() - 100))
        os.utime(new_session, (time.time(), time.time()))

        result = find_most_recent_session(cwd)
        assert result == "new-session"

    def test_prefers_content_timestamp_over_mtime(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Fix C: session with a newer last-line timestamp wins even if mtime is older."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        cwd = "/test/proj2"
        encoded = _encode_cwd(cwd)
        proj_dir = tmp_path / ".claude" / "projects" / encoded
        proj_dir.mkdir(parents=True)

        # older_mtime.jsonl has an OLDER mtime but a NEWER last-line timestamp.
        # newer_mtime.jsonl has a NEWER mtime but an OLDER last-line timestamp.
        older_mtime = proj_dir / "older-mtime.jsonl"
        newer_mtime = proj_dir / "newer-mtime.jsonl"

        older_mtime.write_text(
            '{"timestamp": "2025-06-10T12:00:00.000Z"}\n', encoding="utf-8"
        )
        newer_mtime.write_text(
            '{"timestamp": "2025-06-10T10:00:00.000Z"}\n', encoding="utf-8"
        )

        import os
        import time

        now = time.time()
        # older_mtime was touched 100 s ago; newer_mtime was touched now
        os.utime(older_mtime, (now - 100, now - 100))
        os.utime(newer_mtime, (now, now))

        # Content timestamp should win: older_mtime has timestamp 12:00 > 10:00
        result = find_most_recent_session(cwd)
        assert result == "older-mtime", (
            "Expected content timestamp to take precedence over filesystem mtime"
        )

    def test_falls_back_to_mtime_for_invalid_jsonl(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Fix C fallback: unreadable / no-timestamp files fall back to mtime."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        cwd = "/test/proj3"
        encoded = _encode_cwd(cwd)
        proj_dir = tmp_path / ".claude" / "projects" / encoded
        proj_dir.mkdir(parents=True)

        old_nodata = proj_dir / "old-nodata.jsonl"
        new_nodata = proj_dir / "new-nodata.jsonl"
        old_nodata.write_text("not json at all\n", encoding="utf-8")
        new_nodata.write_text("also not json\n", encoding="utf-8")

        import os
        import time

        now = time.time()
        os.utime(old_nodata, (now - 200, now - 200))
        os.utime(new_nodata, (now, now))

        result = find_most_recent_session(cwd)
        assert result == "new-nodata"

    def test_last_line_timestamp_extracts_correctly(self, tmp_path: Path) -> None:
        """_last_line_timestamp returns the last valid timestamp in the file."""
        from datetime import UTC, datetime

        f = tmp_path / "session.jsonl"
        f.write_text(
            '{"timestamp": "2025-06-10T10:00:00.000Z"}\n'
            '{"timestamp": "2025-06-10T11:00:00.000Z"}\n',
            encoding="utf-8",
        )
        ts = _last_line_timestamp(f)
        assert ts == datetime(2025, 6, 10, 11, 0, 0, tzinfo=UTC)

    def test_last_line_timestamp_returns_none_for_missing_file(
        self, tmp_path: Path
    ) -> None:
        ts = _last_line_timestamp(tmp_path / "nonexistent.jsonl")
        assert ts is None


# ===========================================================================
# markdown_writer.py tests
# ===========================================================================


def _build_minimal_report() -> SessionReport:
    """Build a small but complete SessionReport for rendering tests."""
    from claude_mpm.services.session_analysis.transcript_parser import (
        CallDetail,
        ModelTotals,
    )

    event1 = TimelineEvent(
        uuid="ev-001",
        timestamp=datetime(2025, 6, 10, 10, 0, 0, tzinfo=UTC),
        actor="bob",
        event_type="user_prompt",
        title="Fix the failing test",
        detail="Fix the failing test in test_parser.py",
        github_links=["https://github.com/example/repo/issues/42"],
    )
    event2 = TimelineEvent(
        uuid="ev-002",
        timestamp=datetime(2025, 6, 10, 10, 0, 5, tzinfo=UTC),
        actor="mpm",
        event_type="agent_call",
        title="I'll look at the failing test and fix it.",
        detail="I'll look at the failing test and fix it.",
        calls=[
            CallDetail(
                tool_name="Agent",
                tool_use_id="tu_001",
                input_summary='{"subagent_type": "python-engineer"}',
                response_text="Fixed the regex pattern.",
                subagent_type="python-engineer",
                subagent_model="claude-haiku-3",
            )
        ],
        model="claude-sonnet-4-6",
        usage={
            "input_tokens": 1500,
            "output_tokens": 120,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 800,
        },
        cost_usd=0.006,
    )
    event3 = TimelineEvent(
        uuid="ev-002-outcome",
        timestamp=datetime(2025, 6, 10, 10, 0, 30, tzinfo=UTC),
        actor="Python Engineer",
        event_type="outcome",
        title="Fixed the regex pattern on line 42.",
        detail="Fixed the regex pattern on line 42 of src/parser.py.",
        model="claude-haiku-3-5",
        usage={
            "input_tokens": 3000,
            "output_tokens": 200,
            "cache_creation_input_tokens": 200,
            "cache_read_input_tokens": 1000,
        },
        cost_usd=0.003,
    )

    report = SessionReport(
        session_id="test-session-01",
        project_path="/fake/project",
        transcript_path="/fake/.claude/projects/fake-project/test-session-01.jsonl",
        events=[event1, event2, event3],
        started_at=datetime(2025, 6, 10, 10, 0, 0, tzinfo=UTC),
        ended_at=datetime(2025, 6, 10, 10, 0, 50, tzinfo=UTC),
        title="Fix the failing test",
        total_turns=1,
        agent_call_count=1,
        skill_call_count=0,
        mcp_call_count=0,
        pm_cost_usd=0.006,
        subagent_cost_usd=0.003,
        grand_total_cost_usd=0.009,
        model_totals={
            "claude-sonnet-4-6": ModelTotals(
                model="claude-sonnet-4-6",
                input_tokens=1500,
                output_tokens=120,
                cache_creation_input_tokens=0,
                cache_read_input_tokens=800,
                total_cost_usd=0.006,
                turn_count=1,
            ),
            "claude-haiku-3-5": ModelTotals(
                model="claude-haiku-3-5",
                input_tokens=3000,
                output_tokens=200,
                cache_creation_input_tokens=200,
                cache_read_input_tokens=1000,
                total_cost_usd=0.003,
                turn_count=3,
            ),
        },
        github_links=["https://github.com/example/repo/issues/42"],
    )
    return report


class TestRenderMarkdown:
    def test_output_is_string(self) -> None:
        report = _build_minimal_report()
        md = render_markdown(report)
        assert isinstance(md, str)

    def test_starts_with_frontmatter(self) -> None:
        report = _build_minimal_report()
        md = render_markdown(report)
        assert md.startswith("---\n")

    def test_session_id_in_frontmatter(self) -> None:
        report = _build_minimal_report()
        md = render_markdown(report)
        assert "session_id: test-session-01" in md

    def test_timeline_section_present(self) -> None:
        report = _build_minimal_report()
        md = render_markdown(report)
        assert "## Timeline" in md

    def test_event_headings_present(self) -> None:
        report = _build_minimal_report()
        md = render_markdown(report)
        # 3 events → 3 level-4 headings
        assert md.count("#### ") == 3

    def test_meta_comments_present(self) -> None:
        report = _build_minimal_report()
        md = render_markdown(report)
        assert "<!-- meta:" in md

    def test_agent_call_rendered(self) -> None:
        report = _build_minimal_report()
        md = render_markdown(report)
        assert "python-engineer" in md

    def test_github_link_rendered(self) -> None:
        report = _build_minimal_report()
        md = render_markdown(report)
        assert "github.com/example/repo/issues/42" in md

    def test_cost_rendered(self) -> None:
        report = _build_minimal_report()
        md = render_markdown(report)
        assert "$0.009" in md or "0.009" in md

    def test_outcome_event_rendered(self) -> None:
        report = _build_minimal_report()
        md = render_markdown(report)
        assert "**Outcome:**" in md


class TestWriteReport:
    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        report = _build_minimal_report()
        deep_path = tmp_path / "a" / "b" / "c" / "report.md"
        write_report(report, deep_path)
        assert deep_path.exists()

    def test_file_contains_markdown(self, tmp_path: Path) -> None:
        report = _build_minimal_report()
        out = tmp_path / "report.md"
        write_report(report, out)
        content = out.read_text(encoding="utf-8")
        assert "## Timeline" in content


class TestMarkdownRoundTrip:
    """Render a report → write to file → read_markdown → verify field preservation."""

    def test_event_count_preserved(self, tmp_path: Path) -> None:
        report = _build_minimal_report()
        out = tmp_path / "round_trip.md"
        write_report(report, out)
        parsed = read_markdown(out)
        assert len(parsed["events"]) == len(report.events)

    def test_frontmatter_session_id_preserved(self, tmp_path: Path) -> None:
        report = _build_minimal_report()
        out = tmp_path / "round_trip.md"
        write_report(report, out)
        parsed = read_markdown(out)
        assert parsed["frontmatter"]["session_id"] == "test-session-01"

    def test_frontmatter_grand_total_preserved(self, tmp_path: Path) -> None:
        report = _build_minimal_report()
        out = tmp_path / "round_trip.md"
        write_report(report, out)
        parsed = read_markdown(out)
        assert abs(parsed["frontmatter"]["grand_total_cost_usd"] - 0.009) < 1e-9

    def test_actor_preserved_in_events(self, tmp_path: Path) -> None:
        report = _build_minimal_report()
        out = tmp_path / "round_trip.md"
        write_report(report, out)
        parsed = read_markdown(out)
        actors = [ev["actor"] for ev in parsed["events"]]
        assert "bob" in actors
        assert "mpm" in actors

    def test_meta_type_preserved(self, tmp_path: Path) -> None:
        report = _build_minimal_report()
        out = tmp_path / "round_trip.md"
        write_report(report, out)
        parsed = read_markdown(out)
        event_types = [ev["meta"].get("type") for ev in parsed["events"]]
        assert "user_prompt" in event_types
        assert "agent_call" in event_types
        assert "outcome" in event_types

    def test_meta_cost_preserved(self, tmp_path: Path) -> None:
        report = _build_minimal_report()
        out = tmp_path / "round_trip.md"
        write_report(report, out)
        parsed = read_markdown(out)
        # Find the agent_call event; its cost_usd should be 0.006
        for ev in parsed["events"]:
            if ev["meta"].get("type") == "agent_call":
                assert abs(float(ev["meta"]["cost_usd"]) - 0.006) < 1e-5
                break
        else:
            pytest.fail("No agent_call event found in parsed output")

    def test_title_in_event_preserved(self, tmp_path: Path) -> None:
        report = _build_minimal_report()
        out = tmp_path / "round_trip.md"
        write_report(report, out)
        parsed = read_markdown(out)
        titles = [ev["title"] for ev in parsed["events"]]
        assert any("test" in t.lower() for t in titles)

    def test_github_links_in_events(self, tmp_path: Path) -> None:
        report = _build_minimal_report()
        out = tmp_path / "round_trip.md"
        write_report(report, out)
        parsed = read_markdown(out)
        links_texts = [ev.get("links_text", "") for ev in parsed["events"]]
        combined = " ".join(links_texts)
        assert "github.com/example/repo/issues/42" in combined


class TestReadMarkdownEdgeCases:
    def test_empty_file_returns_empty_events(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.md"
        f.write_text("")
        parsed = read_markdown(f)
        assert parsed["events"] == []
        assert parsed["frontmatter"] == {}

    def test_no_frontmatter_returns_empty_fm(self, tmp_path: Path) -> None:
        f = tmp_path / "no_fm.md"
        f.write_text(
            "#### 10:00 · bob · Hello world\n<!-- meta: type=user_prompt -->\n\nSome text\n\n---\n"
        )
        parsed = read_markdown(f)
        assert parsed["frontmatter"] == {}
        assert len(parsed["events"]) == 1
        assert parsed["events"][0]["actor"] == "bob"

    def test_malformed_yaml_frontmatter_returns_empty_fm(self, tmp_path: Path) -> None:
        f = tmp_path / "bad_fm.md"
        f.write_text("---\n: : : invalid yaml :\n---\n\n")
        parsed = read_markdown(f)
        # Should not raise; frontmatter will be empty
        assert isinstance(parsed["frontmatter"], dict)
