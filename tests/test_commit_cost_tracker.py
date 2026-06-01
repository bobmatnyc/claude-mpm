"""Unit tests for commit_cost_tracker module (issue #600).

Covers:
- get_token_delta(): reading context-usage.json, first-call zero baseline,
  subsequent delta computation, and baseline update.
- compute_cost(): known token counts with default and env-var prices.
- amend_commit_message(): trailers added, Co-Authored-By normalised.
- write_cost_log(): JSONL record appended with correct fields.
- extract_commit_sha(): SHA extracted from various git commit outputs.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

# Ensure src is importable when run from repo root.
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.hooks.commit_cost_tracker import (
    _COAUTHORED_CANONICAL,
    _append_jsonl_atomic,
    _read_json_safe,
    _write_json_atomic,
    amend_commit_message,
    compute_cost,
    extract_commit_sha,
    get_token_delta,
    write_cost_log,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_project(tmp_path: Path) -> Path:
    """Create a minimal project tree with .claude-mpm/state/."""
    state_dir = tmp_path / ".claude-mpm" / "state"
    state_dir.mkdir(parents=True)
    return tmp_path


def _write_usage(
    project: Path, *, inp: int = 0, out: int = 0, read: int = 0, write: int = 0
) -> None:
    usage = {
        "cumulative_input_tokens": inp,
        "cumulative_output_tokens": out,
        "cache_read_tokens": read,
        "cache_creation_tokens": write,
    }
    usage_file = project / ".claude-mpm" / "state" / "context-usage.json"
    usage_file.write_text(json.dumps(usage))


def _write_baseline(
    project: Path, *, inp: int = 0, out: int = 0, read: int = 0, write: int = 0
) -> None:
    baseline = {
        "input_tokens": inp,
        "output_tokens": out,
        "cache_read_tokens": read,
        "cache_write_tokens": write,
    }
    baseline_file = project / ".claude-mpm" / "state" / "commit-token-baseline.json"
    baseline_file.write_text(json.dumps(baseline))


def _read_baseline(project: Path) -> dict:
    baseline_file = project / ".claude-mpm" / "state" / "commit-token-baseline.json"
    return json.loads(baseline_file.read_text())


# ---------------------------------------------------------------------------
# get_token_delta() tests
# ---------------------------------------------------------------------------


class TestGetTokenDelta:
    def test_first_call_no_baseline_returns_full_cumulative(
        self, tmp_project: Path
    ) -> None:
        """First commit: no baseline → delta equals full cumulative totals."""
        _write_usage(tmp_project, inp=1000, out=200, read=50, write=100)

        delta = get_token_delta(str(tmp_project))

        assert delta["input_tokens"] == 1000
        assert delta["output_tokens"] == 200
        assert delta["cache_read_tokens"] == 50
        assert delta["cache_write_tokens"] == 100

    def test_baseline_updated_after_first_call(self, tmp_project: Path) -> None:
        """After get_token_delta(), the baseline file reflects the current totals."""
        _write_usage(tmp_project, inp=1000, out=200)

        get_token_delta(str(tmp_project))

        baseline = _read_baseline(tmp_project)
        assert baseline["input_tokens"] == 1000
        assert baseline["output_tokens"] == 200

    def test_subsequent_call_returns_incremental_delta(self, tmp_project: Path) -> None:
        """Second call returns only the increment since the previous commit."""
        _write_usage(tmp_project, inp=1000, out=200)
        _write_baseline(tmp_project, inp=800, out=150)

        delta = get_token_delta(str(tmp_project))

        assert delta["input_tokens"] == 200  # 1000 - 800
        assert delta["output_tokens"] == 50  # 200  - 150

    def test_no_usage_file_returns_zeros(self, tmp_project: Path) -> None:
        """Missing context-usage.json → graceful degradation: delta = zeros."""
        delta = get_token_delta(str(tmp_project))

        assert delta["input_tokens"] == 0
        assert delta["output_tokens"] == 0
        assert delta["cache_read_tokens"] == 0
        assert delta["cache_write_tokens"] == 0

    def test_delta_floored_at_zero_when_cumulative_below_baseline(
        self, tmp_project: Path
    ) -> None:
        """If cumulative went down (session reset), return 0 not negative."""
        _write_usage(tmp_project, inp=500)
        _write_baseline(tmp_project, inp=1000)  # Baseline is higher

        delta = get_token_delta(str(tmp_project))

        assert delta["input_tokens"] == 0

    def test_cache_fields_mapped_correctly(self, tmp_project: Path) -> None:
        """cache_creation_tokens in context-usage maps to cache_write_tokens in delta."""
        _write_usage(tmp_project, read=300, write=700)

        delta = get_token_delta(str(tmp_project))

        assert delta["cache_read_tokens"] == 300
        assert delta["cache_write_tokens"] == 700


# ---------------------------------------------------------------------------
# compute_cost() tests
# ---------------------------------------------------------------------------


class TestComputeCost:
    def test_zero_tokens_returns_zero(self) -> None:
        delta = {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_read_tokens": 0,
            "cache_write_tokens": 0,
        }
        assert compute_cost(delta) == 0.0

    def test_default_prices(self) -> None:
        """1M input + 1M output at default prices = $3.00 + $15.00 = $18.00."""
        delta = {
            "input_tokens": 1_000_000,
            "output_tokens": 1_000_000,
            "cache_read_tokens": 0,
            "cache_write_tokens": 0,
        }
        cost = compute_cost(delta)
        assert abs(cost - 18.0) < 0.0001

    def test_cache_prices_included(self) -> None:
        """1M cache_read at $0.30 + 1M cache_write at $3.75 = $4.05."""
        delta = {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_read_tokens": 1_000_000,
            "cache_write_tokens": 1_000_000,
        }
        cost = compute_cost(delta)
        assert abs(cost - 4.05) < 0.0001

    def test_env_var_price_override(self) -> None:
        """CLAUDE_MPM_PRICE_INPUT env var overrides the default input price."""
        delta = {
            "input_tokens": 1_000_000,
            "output_tokens": 0,
            "cache_read_tokens": 0,
            "cache_write_tokens": 0,
        }
        with patch.dict(os.environ, {"CLAUDE_MPM_PRICE_INPUT": "5.00"}):
            cost = compute_cost(delta)
        assert abs(cost - 5.0) < 0.0001

    def test_all_env_var_overrides(self) -> None:
        """All four price env vars can be overridden simultaneously."""
        delta = {
            "input_tokens": 1_000_000,
            "output_tokens": 1_000_000,
            "cache_read_tokens": 1_000_000,
            "cache_write_tokens": 1_000_000,
        }
        env = {
            "CLAUDE_MPM_PRICE_INPUT": "1.0",
            "CLAUDE_MPM_PRICE_OUTPUT": "2.0",
            "CLAUDE_MPM_PRICE_CACHE_READ": "0.1",
            "CLAUDE_MPM_PRICE_CACHE_WRITE": "0.2",
        }
        with patch.dict(os.environ, env):
            cost = compute_cost(delta)
        assert abs(cost - 3.3) < 0.0001

    def test_partial_million_tokens(self) -> None:
        """100k input tokens at $3/MTok = $0.30."""
        delta = {
            "input_tokens": 100_000,
            "output_tokens": 0,
            "cache_read_tokens": 0,
            "cache_write_tokens": 0,
        }
        cost = compute_cost(delta)
        assert abs(cost - 0.3) < 0.0001


# ---------------------------------------------------------------------------
# extract_commit_sha() tests
# ---------------------------------------------------------------------------


class TestExtractCommitSha:
    def test_typical_output(self) -> None:
        output = "[main abc1234] Add feature\n 1 file changed"
        assert extract_commit_sha(output) == "abc1234"

    def test_detached_head(self) -> None:
        output = "[HEAD detached at def5678] hotfix"
        assert extract_commit_sha(output) == "def5678"

    def test_full_sha(self) -> None:
        sha = "a" * 40
        output = f"[main {sha}] commit message"
        assert extract_commit_sha(output) == sha

    def test_no_match_returns_none(self) -> None:
        assert extract_commit_sha("nothing useful here") is None

    def test_empty_string_returns_none(self) -> None:
        assert extract_commit_sha("") is None

    def test_feature_branch_name(self) -> None:
        output = "[feature/my-branch 1234abc] feat: something"
        assert extract_commit_sha(output) == "1234abc"


# ---------------------------------------------------------------------------
# amend_commit_message() tests
# ---------------------------------------------------------------------------


class TestAmendCommitMessage:
    """Test amend_commit_message with subprocess mocked out."""

    _DELTA = {
        "input_tokens": 500,
        "output_tokens": 100,
        "cache_read_tokens": 200,
        "cache_write_tokens": 50,
    }
    _COST = 0.002175

    def _make_log_result(self, message: str):
        r = MagicMock()
        r.returncode = 0
        r.stdout = message
        r.stderr = ""
        return r

    def _make_amend_result(self):
        r = MagicMock()
        r.returncode = 0
        r.stdout = ""
        r.stderr = ""
        return r

    def test_trailers_added_to_clean_message(self) -> None:
        original = "feat: add something\n"
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                self._make_log_result(original),
                self._make_amend_result(),
            ]
            amend_commit_message("abc1234", self._DELTA, self._COST, "/tmp")

        # Second call is the amend; extract new message from its args.
        amend_call = mock_run.call_args_list[1]
        new_msg = amend_call[0][0][amend_call[0][0].index("-m") + 1]

        assert "X-AI-Tokens-In: 500" in new_msg
        assert "X-AI-Tokens-Out: 100" in new_msg
        assert "X-AI-Cache-Read: 200" in new_msg
        assert "X-AI-Cache-Write: 50" in new_msg
        assert "X-AI-Cache-Ratio:" in new_msg
        assert "X-AI-Est-Cost-USD:" in new_msg

    def test_canonical_coauthoredby_added(self) -> None:
        original = "fix: bug\n"
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                self._make_log_result(original),
                self._make_amend_result(),
            ]
            amend_commit_message("abc1234", self._DELTA, self._COST, "/tmp")

        amend_call = mock_run.call_args_list[1]
        new_msg = amend_call[0][0][amend_call[0][0].index("-m") + 1]

        assert _COAUTHORED_CANONICAL in new_msg

    def test_generic_coauthoredby_replaced(self) -> None:
        original = "fix: bug\n\nCo-Authored-By: Claude <noreply@anthropic.com>\n"
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                self._make_log_result(original),
                self._make_amend_result(),
            ]
            amend_commit_message("abc1234", self._DELTA, self._COST, "/tmp")

        amend_call = mock_run.call_args_list[1]
        new_msg = amend_call[0][0][amend_call[0][0].index("-m") + 1]

        assert "noreply@anthropic.com" not in new_msg
        assert _COAUTHORED_CANONICAL in new_msg

    def test_bare_claude_coauthoredby_replaced(self) -> None:
        original = "fix: bug\n\nCo-Authored-By: Claude\n"
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                self._make_log_result(original),
                self._make_amend_result(),
            ]
            amend_commit_message("abc1234", self._DELTA, self._COST, "/tmp")

        amend_call = mock_run.call_args_list[1]
        new_msg = amend_call[0][0][amend_call[0][0].index("-m") + 1]

        # Generic "Co-Authored-By: Claude" removed; canonical added exactly once.
        assert new_msg.count(_COAUTHORED_CANONICAL) == 1

    def test_existing_canonical_not_duplicated(self) -> None:
        original = f"fix: bug\n\n{_COAUTHORED_CANONICAL}\n"
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                self._make_log_result(original),
                self._make_amend_result(),
            ]
            amend_commit_message("abc1234", self._DELTA, self._COST, "/tmp")

        amend_call = mock_run.call_args_list[1]
        new_msg = amend_call[0][0][amend_call[0][0].index("-m") + 1]

        # Should appear exactly once.
        assert new_msg.count(_COAUTHORED_CANONICAL) == 1

    def test_no_verify_flag_present(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                self._make_log_result("commit msg\n"),
                self._make_amend_result(),
            ]
            amend_commit_message("abc1234", self._DELTA, self._COST, "/tmp")

        amend_cmd = mock_run.call_args_list[1][0][0]
        assert "--no-verify" in amend_cmd

    def test_git_log_failure_does_not_raise(self) -> None:
        fail = MagicMock()
        fail.returncode = 1
        fail.stdout = ""
        fail.stderr = "fatal: bad object"
        with patch("subprocess.run", return_value=fail):
            # Should not raise.
            amend_commit_message("bad_sha", self._DELTA, self._COST, "/tmp")

    def test_cache_ratio_zero_when_no_cache(self) -> None:
        delta_no_cache = {
            "input_tokens": 100,
            "output_tokens": 50,
            "cache_read_tokens": 0,
            "cache_write_tokens": 0,
        }
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                self._make_log_result("msg\n"),
                self._make_amend_result(),
            ]
            amend_commit_message("abc1234", delta_no_cache, 0.0, "/tmp")

        amend_call = mock_run.call_args_list[1]
        new_msg = amend_call[0][0][amend_call[0][0].index("-m") + 1]
        assert "X-AI-Cache-Ratio: 0%" in new_msg

    def test_cache_ratio_100_when_all_read(self) -> None:
        delta_all_read = {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_read_tokens": 1000,
            "cache_write_tokens": 0,
        }
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                self._make_log_result("msg\n"),
                self._make_amend_result(),
            ]
            amend_commit_message("abc1234", delta_all_read, 0.0, "/tmp")

        amend_call = mock_run.call_args_list[1]
        new_msg = amend_call[0][0][amend_call[0][0].index("-m") + 1]
        assert "X-AI-Cache-Ratio: 100%" in new_msg


# ---------------------------------------------------------------------------
# write_cost_log() tests
# ---------------------------------------------------------------------------


class TestWriteCostLog:
    _DELTA = {
        "input_tokens": 1000,
        "output_tokens": 200,
        "cache_read_tokens": 50,
        "cache_write_tokens": 25,
    }
    _COST = 0.0045
    _SHA = "abc1234"
    _CWD = "/home/user/project"
    _OUTPUT = "[main abc1234] feat: something\n 1 file changed"

    def _log_path(self, home: Path) -> Path:
        """Return the expected log path given a fake home directory."""
        return home / ".claude-mpm" / "commit-costs.jsonl"

    def test_jsonl_file_created_and_populated(self, tmp_path: Path) -> None:
        # Patch Path.home() at the module level used by commit_cost_tracker.
        with patch(
            "claude_mpm.hooks.commit_cost_tracker.Path.home", return_value=tmp_path
        ):
            write_cost_log(self._SHA, self._DELTA, self._COST, self._CWD, self._OUTPUT)

        log_path = self._log_path(tmp_path)
        assert log_path.exists()
        lines = log_path.read_text().strip().splitlines()
        assert len(lines) == 1

    def test_jsonl_record_has_required_fields(self, tmp_path: Path) -> None:
        with patch(
            "claude_mpm.hooks.commit_cost_tracker.Path.home", return_value=tmp_path
        ):
            write_cost_log(self._SHA, self._DELTA, self._COST, self._CWD, self._OUTPUT)

        log_path = self._log_path(tmp_path)
        record = json.loads(log_path.read_text().strip())

        assert record["commit_sha"] == self._SHA
        assert record["cwd"] == self._CWD
        assert record["tokens_in"] == 1000
        assert record["tokens_out"] == 200
        assert record["cache_read"] == 50
        assert record["cache_write"] == 25
        assert abs(record["est_cost_usd"] - self._COST) < 0.000001
        assert "timestamp" in record
        assert "git_output" in record

    def test_multiple_calls_append_lines(self, tmp_path: Path) -> None:
        with patch(
            "claude_mpm.hooks.commit_cost_tracker.Path.home", return_value=tmp_path
        ):
            write_cost_log(self._SHA, self._DELTA, self._COST, self._CWD, self._OUTPUT)
            write_cost_log(
                "def5678", self._DELTA, self._COST, self._CWD, "other output"
            )

        log_path = self._log_path(tmp_path)
        lines = [ln for ln in log_path.read_text().splitlines() if ln.strip()]
        assert len(lines) == 2

        r1 = json.loads(lines[0])
        r2 = json.loads(lines[1])
        assert r1["commit_sha"] == self._SHA
        assert r2["commit_sha"] == "def5678"

    def test_error_does_not_raise(self, tmp_path: Path) -> None:
        """write_cost_log must never raise even if home() is unwritable."""
        with patch(
            "claude_mpm.hooks.commit_cost_tracker.Path.home",
            side_effect=OSError("no home"),
        ):
            # Should silently log a warning and not raise.
            write_cost_log(self._SHA, self._DELTA, self._COST, self._CWD, self._OUTPUT)


# ---------------------------------------------------------------------------
# Internal helper tests
# ---------------------------------------------------------------------------


class TestInternalHelpers:
    def test_read_json_safe_missing_file(self, tmp_path: Path) -> None:
        result = _read_json_safe(tmp_path / "nonexistent.json")
        assert result == {}

    def test_read_json_safe_valid_file(self, tmp_path: Path) -> None:
        f = tmp_path / "data.json"
        f.write_text('{"key": 42}')
        result = _read_json_safe(f)
        assert result == {"key": 42}

    def test_read_json_safe_invalid_json(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.json"
        f.write_text("not json{{{")
        result = _read_json_safe(f)
        assert result == {}

    def test_write_json_atomic_creates_file(self, tmp_path: Path) -> None:
        target = tmp_path / "out.json"
        _write_json_atomic(target, {"a": 1})
        assert target.exists()
        assert json.loads(target.read_text()) == {"a": 1}

    def test_write_json_atomic_is_idempotent(self, tmp_path: Path) -> None:
        target = tmp_path / "out.json"
        _write_json_atomic(target, {"v": 1})
        _write_json_atomic(target, {"v": 2})
        assert json.loads(target.read_text()) == {"v": 2}

    def test_append_jsonl_atomic_creates_file(self, tmp_path: Path) -> None:
        target = tmp_path / "records.jsonl"
        _append_jsonl_atomic(target, {"x": 1})
        assert target.exists()
        lines = [l for l in target.read_text().splitlines() if l.strip()]
        assert len(lines) == 1
        assert json.loads(lines[0]) == {"x": 1}

    def test_append_jsonl_atomic_appends(self, tmp_path: Path) -> None:
        target = tmp_path / "records.jsonl"
        _append_jsonl_atomic(target, {"x": 1})
        _append_jsonl_atomic(target, {"x": 2})
        lines = [l for l in target.read_text().splitlines() if l.strip()]
        assert len(lines) == 2
        assert json.loads(lines[1]) == {"x": 2}
