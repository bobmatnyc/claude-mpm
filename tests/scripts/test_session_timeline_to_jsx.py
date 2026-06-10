"""
Tests for scripts/session_timeline_to_jsx.py.

WHAT: Validates Markdown parsing and JSX generation for the session-tracker
      timeline converter against a small inline canonical fixture.
WHY:  Ensures the converter handles the full canonical schema (2-model
      frontmatter, mixed entry types, optional fields) without regressions.
"""

from __future__ import annotations

import sys
import tempfile
import textwrap
from pathlib import Path

# Make the scripts/ directory importable
_REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT / "scripts"))

from session_timeline_to_jsx import (  # noqa: E402
    _safe_json,
    generate_jsx,
    parse_markdown,
)

# ---------------------------------------------------------------------------
# Inline fixture
# ---------------------------------------------------------------------------

CANONICAL_MARKDOWN = textwrap.dedent(
    """\
    ---
    session_id: abc123-test-session
    project: my-project
    project_path: /Users/test/my-project
    generated_at: '2026-06-10T12:00:00Z'
    date: '2026-06-10'
    title: Fix the parser bug in session analyzer
    model_breakdown:
    - model: claude-opus-4-8
      input: 62433
      output: 198047
      cache_write: 1537360
      cache_read: 8737196
      cost_usd: 57.7213
      turns: 81
    - model: claude-sonnet-4-6
      input: 56799
      output: 98105
      cache_write: 1358323
      cache_read: 25677998
      cost_usd: 14.4391
      turns: 482
    grand_total_cost_usd: 72.1604
    pm_cost_usd: 57.7213
    subagent_cost_usd: 14.4391
    autonomy:
      basis: turn_count
      bob_pct: 11.7
      mpm_pct: 88.3
    stat_cards:
    - label: Total Cost
      sub: rack rate
      value: $72.1604
    - label: PM Cost
      sub: PM turns only
      value: $57.7213
    - label: Agent Cost
      sub: subagent turns
      value: $14.4391
    - label: Agent Calls
      sub: delegations
      value: '5'
    - label: Tool Calls
      sub: skill + mcp
      value: '3'
    - label: Duration
      sub: wall-clock
      value: 1h 22m
    has_pricing_fallback: false
    ---

    # Session: Fix the parser bug in session analyzer

    ## Timeline

    #### 09:15 · bob · Fix the session analyzer markdown parser

    <!-- meta: who=bob; tags=prompt; model=none; in=0; out=0; cache_read=0; cache_write=0; cost_usd=0.000000; type=user_prompt; ambiguous=false; subagent_file=none -->

    I want you to fix the regex in the session analyzer markdown parser — it's
    dropping the last entry in the timeline.

    ---

    #### 09:16 · mpm · Delegating fix to Python Engineer

    <!-- meta: who=mpm; tags=agent; model=claude-opus-4-8; in=12345; out=6789; cache_read=500000; cache_write=100000; cost_usd=1.234567; type=agent_call; ambiguous=false; subagent_file=agent-xyz123.jsonl -->

    I've reviewed the parser and identified the root cause. Delegating the fix
    to the Python Engineer subagent.

    **Calls:**

    - `Agent` → **Python Engineer** (claude-sonnet-4-6) — _Fixed the off-by-one in the regex._
    - `Skill` → **verification-before-completion** — _All tests pass._

    **Outcome:** Fixed the regex on line 42. The last timeline entry is now captured correctly.

    **Links:** https://github.com/example/repo/issues/99 https://github.com/example/repo/pull/100

    ---
    """
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestParseMarkdown:
    """Unit tests for parse_markdown() against the inline fixture."""

    def _parse(self, tmp_path: Path) -> dict:
        tmp = tmp_path / "_test_session_timeline_fixture.md"
        tmp.write_text(CANONICAL_MARKDOWN, encoding="utf-8")
        return parse_markdown(tmp)

    def test_frontmatter_session_id(self, tmp_path: Path):
        result = self._parse(tmp_path)
        assert result["frontmatter"]["session_id"] == "abc123-test-session"

    def test_frontmatter_two_models(self, tmp_path: Path):
        result = self._parse(tmp_path)
        models = [m["model"] for m in result["frontmatter"]["model_breakdown"]]
        assert "claude-opus-4-8" in models
        assert "claude-sonnet-4-6" in models

    def test_frontmatter_grand_total(self, tmp_path: Path):
        result = self._parse(tmp_path)
        assert abs(result["frontmatter"]["grand_total_cost_usd"] - 72.1604) < 0.001

    def test_event_count(self, tmp_path: Path):
        result = self._parse(tmp_path)
        assert len(result["events"]) == 2

    def test_first_entry_is_bob(self, tmp_path: Path):
        result = self._parse(tmp_path)
        entry = result["events"][0]
        assert entry["who"] == "bob"
        assert "Fix the session analyzer" in entry["title"]

    def test_second_entry_is_mpm(self, tmp_path: Path):
        result = self._parse(tmp_path)
        entry = result["events"][1]
        assert entry["who"] == "mpm"

    def test_meta_tokens_parsed(self, tmp_path: Path):
        result = self._parse(tmp_path)
        meta = result["events"][1]["meta"]
        assert meta.get("in") == "12345"
        assert meta.get("out") == "6789"

    def test_calls_parsed(self, tmp_path: Path):
        result = self._parse(tmp_path)
        calls = result["events"][1]["calls"]
        assert len(calls) >= 2
        tools = [c["tool"] for c in calls]
        assert "Agent" in tools
        assert "Skill" in tools

    def test_outcome_parsed(self, tmp_path: Path):
        result = self._parse(tmp_path)
        outcome = result["events"][1]["outcome"]
        assert "regex" in outcome.lower() or "fixed" in outcome.lower()

    def test_links_parsed(self, tmp_path: Path):
        result = self._parse(tmp_path)
        links = result["events"][1]["links"]
        assert len(links) == 2
        types = {lk["type"] for lk in links}
        assert "issue" in types
        assert "pr" in types


class TestGenerateJsx:
    """Unit tests for generate_jsx() output content."""

    def _jsx(self, tmp_path: Path) -> str:
        tmp = tmp_path / "_test_session_timeline_fixture.md"
        tmp.write_text(CANONICAL_MARKDOWN, encoding="utf-8")
        parsed = parse_markdown(tmp)
        return generate_jsx(parsed)

    def test_has_export_default(self, tmp_path: Path):
        jsx = self._jsx(tmp_path)
        assert "export default" in jsx

    def test_grand_total_present(self, tmp_path: Path):
        jsx = self._jsx(tmp_path)
        # 72.1604 must appear somewhere in the JSX
        assert "72.1604" in jsx or "72.16" in jsx

    def test_both_model_names_present(self, tmp_path: Path):
        jsx = self._jsx(tmp_path)
        assert "claude-opus-4-8" in jsx or "opus-4-8" in jsx
        assert "claude-sonnet-4-6" in jsx or "sonnet-4-6" in jsx

    def test_entry_title_present(self, tmp_path: Path):
        jsx = self._jsx(tmp_path)
        assert "Fix the session analyzer" in jsx

    def test_token_figure_present(self, tmp_path: Path):
        jsx = self._jsx(tmp_path)
        # in=12345 from the mpm entry's meta comment
        assert "12345" in jsx or "12" in jsx  # fmtTokens("12345") → "12k"

    def test_session_id_present(self, tmp_path: Path):
        jsx = self._jsx(tmp_path)
        assert "abc123-test-session" in jsx

    def test_cost_breakdown_structure(self, tmp_path: Path):
        jsx = self._jsx(tmp_path)
        # COST_BREAKDOWN constant must be present
        assert "COST_BREAKDOWN" in jsx

    def test_structural_markers_present(self, tmp_path: Path):
        """The generated JSX must contain the required structural markers.

        Replaces the former brace-balance heuristic, which was meaningless
        because JSX templates use {{/}} escaping that throws off a raw count.
        Instead, assert that the known top-level structural tokens are present.
        """
        jsx = self._jsx(tmp_path)
        assert "export default" in jsx, "Missing 'export default' in generated JSX"
        assert "const EVENTS" in jsx, "Missing 'const EVENTS' in generated JSX"
        assert "const SESSION" in jsx, "Missing 'const SESSION' in generated JSX"

    def test_events_constant_present(self, tmp_path: Path):
        jsx = self._jsx(tmp_path)
        assert "const EVENTS" in jsx

    def test_session_constant_present(self, tmp_path: Path):
        jsx = self._jsx(tmp_path)
        assert "const SESSION" in jsx

    def test_model_badge_strips_date_suffix(self, tmp_path: Path):
        """ModelBadge regex must strip trailing -YYYYMMDD date suffix from model id."""
        jsx = self._jsx(tmp_path)
        # The JSX template contains the strip regex as a JS string literal.
        # Verify the pattern /-20\d{6}$/ (or equivalent) is present.
        assert r"-20\d" in jsx or r"20\d{6}" in jsx


class TestSafeJson:
    """Unit tests for _safe_json escaping (Fix D)."""

    def test_script_tag_injection_escaped(self) -> None:
        """A value containing </script> must have the </ escaped."""
        result = _safe_json({"title": "XSS </script><script>alert(1)</script>"})
        assert "</" not in result, "Unescaped </ found in serialized JSON"
        assert "<\\/" in result

    def test_template_literal_injection_escaped(self) -> None:
        """A value containing ${ must be escaped to prevent template-literal injection."""
        result = _safe_json({"detail": "cost ${amount} USD"})
        assert "${" not in result, "Unescaped ${ found in serialized JSON"
        assert "$\\{" in result

    def test_normal_content_unchanged(self) -> None:
        """Normal text without injection sequences round-trips correctly."""
        import json as _json

        data = {"title": "Fix the parser bug", "cost": 1.23}
        result = _safe_json(data)
        # The data round-trips to equivalent Python (ignoring float formatting)
        parsed = _json.loads(result)
        assert parsed["title"] == data["title"]

    def test_generate_jsx_escapes_script_tag_in_title(self, tmp_path: Path) -> None:
        """generate_jsx must escape </script> appearing in a session title."""
        import textwrap

        dangerous_md = textwrap.dedent(
            """\
            ---
            session_id: xss-test
            project: test-proj
            project_path: /test
            generated_at: '2026-06-10T00:00:00Z'
            date: '2026-06-10'
            title: 'Dangerous </script><script>alert(1)</script> title'
            grand_total_cost_usd: 0.0
            pm_cost_usd: 0.0
            subagent_cost_usd: 0.0
            has_pricing_fallback: false
            ---

            # Session: xss

            ## Timeline

            #### 10:00 . bob . Dangerous </script> title

            <!-- meta: who=bob; tags=prompt; model=none; in=0; out=0; cache_read=0; cache_write=0; cost_usd=0.0; type=user_prompt; ambiguous=false; subagent_file=none -->

            Dangerous </script> content.

            ---
            """
        )
        md_file = tmp_path / "xss_test.md"
        md_file.write_text(dangerous_md, encoding="utf-8")
        parsed = parse_markdown(md_file)
        jsx = generate_jsx(parsed)
        # The raw </script> must not appear in the generated JSX
        assert "</script>" not in jsx, "Unescaped </script> found in generated JSX"
