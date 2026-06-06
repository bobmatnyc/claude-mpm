"""Unit tests for commit_cost_tracker module (issue #600 / #601 / #696).

Covers:
- get_token_delta(): reading context-usage.json, first-call zero baseline,
  subsequent delta computation, and baseline update.
- amend_commit_message(): trailers added (tokens + model only), Co-Authored-By
  normalised.  Cache/cost trailers are no longer emitted.
- write_cost_log(): JSONL record appended with correct fields (token fields
  only; cache/cost fields removed per CHANGE 2).
- extract_commit_sha(): SHA extracted from various git commit outputs.
- Regression tests for the zero-trailer bug (issue #601):
  - ContextUsageTracker.set_session_snapshot() must replace (not add to)
    context-usage.json so the git post-commit hook sees non-zero deltas.
  - CHANGE 1: commit hook parses live transcript JSONL directly and produces
    non-zero delta even when context-usage.json is stale / zero.
- Worktree / subagent attribution (issue #696):
  - resolve_main_working_tree() returns the main repo root when called from a
    linked worktree.
  - get_token_delta() uses the main-tree transcript when the worktree transcript
    is missing.
  - amend_commit_message() skips X-AI-Tokens-In/Out when delta is 0/0.
  - Normal (non-worktree) commit path regression.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure src is importable when run from repo root.
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.hooks.commit_cost_tracker import (
    _COAUTHORED_CANONICAL,
    _append_jsonl_atomic,
    _read_json_safe,
    _write_json_atomic,
    amend_commit_message,
    extract_commit_sha,
    get_token_delta,
    resolve_main_working_tree,
    write_cost_log,
)
from claude_mpm.services.infrastructure.context_usage_tracker import (
    ContextUsageTracker,
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


def _make_assistant_record(
    *,
    input_tokens: int,
    output_tokens: int,
    cache_creation: int = 0,
    cache_read: int = 0,
    model: str | None = None,
) -> str:
    """Return a JSONL line representing an assistant transcript record with usage."""
    msg: dict = {
        "role": "assistant",
        "content": [{"type": "text", "text": "reply"}],
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_creation_input_tokens": cache_creation,
            "cache_read_input_tokens": cache_read,
        },
    }
    if model is not None:
        msg["model"] = model
    rec = {
        "type": "assistant",
        "message": msg,
        "sessionId": "test-session",
    }
    return json.dumps(rec)


def _write_transcript(path: Path, records: list[str]) -> None:
    """Write JSONL records to path, one per line."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(records) + "\n", encoding="utf-8")


def _create_fake_transcript_for_cwd(
    fake_home: Path,
    cwd: str,
    *,
    input_tokens: int = 10_000,
    output_tokens: int = 2_000,
    model: str = "claude-opus-4-8",
) -> Path:
    """Create a fake transcript JSONL in the fake_home dir for the given cwd.

    Places the transcript at fake_home/.claude/projects/{encoded_cwd}/{session}.jsonl
    and returns the path.
    """
    encoded = cwd.replace("/", "-")
    transcript_dir = fake_home / ".claude" / "projects" / encoded
    transcript_dir.mkdir(parents=True, exist_ok=True)
    transcript_path = transcript_dir / "test-session-123.jsonl"
    _write_transcript(
        transcript_path,
        [
            _make_assistant_record(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                model=model,
            )
        ],
    )
    return transcript_path


# ---------------------------------------------------------------------------
# get_token_delta() tests — snapshot fallback path (no transcript)
# ---------------------------------------------------------------------------


class TestGetTokenDelta:
    def _patch_no_transcript(self):
        """Return a context manager that makes find_latest_transcript() return None."""
        return patch(
            "claude_mpm.hooks.commit_cost_tracker.find_latest_transcript",
            return_value=None,
        )

    def test_first_call_no_baseline_returns_full_cumulative(
        self, tmp_project: Path
    ) -> None:
        """First commit: no baseline → delta equals full cumulative totals."""
        _write_usage(tmp_project, inp=1000, out=200, read=50, write=100)

        with self._patch_no_transcript():
            delta = get_token_delta(str(tmp_project))

        assert delta["input_tokens"] == 1000
        assert delta["output_tokens"] == 200
        assert delta["cache_read_tokens"] == 50
        assert delta["cache_write_tokens"] == 100

    def test_baseline_updated_after_first_call(self, tmp_project: Path) -> None:
        """After get_token_delta(), the baseline file reflects the current totals."""
        _write_usage(tmp_project, inp=1000, out=200)

        with self._patch_no_transcript():
            get_token_delta(str(tmp_project))

        baseline = _read_baseline(tmp_project)
        assert baseline["input_tokens"] == 1000
        assert baseline["output_tokens"] == 200

    def test_subsequent_call_returns_incremental_delta(self, tmp_project: Path) -> None:
        """Second call returns only the increment since the previous commit."""
        _write_usage(tmp_project, inp=1000, out=200)
        _write_baseline(tmp_project, inp=800, out=150)

        with self._patch_no_transcript():
            delta = get_token_delta(str(tmp_project))

        assert delta["input_tokens"] == 200  # 1000 - 800
        assert delta["output_tokens"] == 50  # 200  - 150

    def test_no_usage_file_returns_zeros(self, tmp_project: Path) -> None:
        """Missing context-usage.json → graceful degradation: delta = zeros."""
        with self._patch_no_transcript():
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

        with self._patch_no_transcript():
            delta = get_token_delta(str(tmp_project))

        assert delta["input_tokens"] == 0

    def test_cache_fields_mapped_correctly(self, tmp_project: Path) -> None:
        """cache_creation_tokens in context-usage maps to cache_write_tokens in delta."""
        _write_usage(tmp_project, read=300, write=700)

        with self._patch_no_transcript():
            delta = get_token_delta(str(tmp_project))

        assert delta["cache_read_tokens"] == 300
        assert delta["cache_write_tokens"] == 700


# ---------------------------------------------------------------------------
# get_token_delta() tests — live transcript path (CHANGE 1 / issue #601 fix)
# ---------------------------------------------------------------------------


class TestGetTokenDeltaFromTranscript:
    """Verify that get_token_delta() reads the live transcript when available.

    This is the regression guard for issue #601: the root cause was that
    context-usage.json was stale at commit time (Stop hadn't fired yet), so
    all deltas were zero.  CHANGE 1 fixes this by parsing the active transcript
    directly inside get_token_delta().
    """

    def _patch_home(self, fake_home: Path):
        """Patch Path.home() inside transcript_usage so fixtures are found."""
        return patch(
            "claude_mpm.hooks.transcript_usage.Path.home",
            return_value=fake_home,
        )

    def test_transcript_beats_stale_snapshot(self, tmp_project: Path) -> None:
        """When transcript exists, live counts are used instead of stale snapshot.

        Seed context-usage.json with zeros (stale), create a transcript with
        known token counts, assert get_token_delta() returns the transcript values.

        This is the CORE regression guard for #601.
        """
        # Stale snapshot with zeros.
        _write_usage(tmp_project, inp=0, out=0)
        # No baseline (first commit).

        fake_home = tmp_project / "fake_home"
        cwd = str(tmp_project)
        _create_fake_transcript_for_cwd(
            fake_home,
            cwd,
            input_tokens=15_000,
            output_tokens=3_500,
            model="claude-opus-4-8",
        )

        with self._patch_home(fake_home):
            delta = get_token_delta(cwd)

        assert delta["input_tokens"] == 15_000, (
            f"Expected 15000 from transcript, got {delta['input_tokens']} "
            "(zero means stale context-usage.json was used — #601 regression)"
        )
        assert delta["output_tokens"] == 3_500
        # Model should be populated from transcript
        assert "claude-opus-4-8" in delta.get("models", {}), (
            "Model should appear in delta when parsed from transcript"
        )

    def test_transcript_with_baseline_gives_correct_delta(
        self, tmp_project: Path
    ) -> None:
        """Transcript cumulative minus baseline gives the correct incremental delta.

        This tests the full flow: previous commit set baseline, now new tokens
        appear in the transcript. Delta should be only the new tokens.
        """
        cwd = str(tmp_project)
        # Previous commit baseline
        _write_baseline(tmp_project, inp=10_000, out=1_000)
        # Stale snapshot (doesn't matter — transcript is authoritative)
        _write_usage(tmp_project, inp=0, out=0)

        fake_home = tmp_project / "fake_home"
        _create_fake_transcript_for_cwd(
            fake_home,
            cwd,
            input_tokens=18_000,  # 8000 new tokens since baseline
            output_tokens=1_800,  # 800 new tokens
            model="claude-sonnet-4-6",
        )

        with self._patch_home(fake_home):
            delta = get_token_delta(cwd)

        assert delta["input_tokens"] == 8_000, (  # 18k - 10k
            f"Expected 8000 incremental input tokens, got {delta['input_tokens']}"
        )
        assert delta["output_tokens"] == 800, (  # 1800 - 1000
            f"Expected 800 incremental output tokens, got {delta['output_tokens']}"
        )

    def test_most_recent_transcript_selected_when_multiple_exist(
        self, tmp_project: Path
    ) -> None:
        """When multiple JSONL files exist, the one with the latest mtime is used.

        This test verifies the most-recently-modified file selection logic in
        find_latest_transcript().
        """
        cwd = str(tmp_project)
        encoded = cwd.replace("/", "-")
        fake_home = tmp_project / "fake_home"
        transcript_dir = fake_home / ".claude" / "projects" / encoded
        transcript_dir.mkdir(parents=True, exist_ok=True)

        # Write an older transcript with small token counts.
        old_transcript = transcript_dir / "old-session.jsonl"
        _write_transcript(
            old_transcript,
            [_make_assistant_record(input_tokens=100, output_tokens=20)],
        )
        # Sleep briefly so mtime differs, then write the newer transcript.
        time.sleep(0.05)
        new_transcript = transcript_dir / "new-session.jsonl"
        _write_transcript(
            new_transcript,
            [_make_assistant_record(input_tokens=50_000, output_tokens=5_000)],
        )

        with self._patch_home(fake_home):
            delta = get_token_delta(cwd)

        assert delta["input_tokens"] == 50_000, (
            f"Expected 50000 (from newer transcript), got {delta['input_tokens']} "
            "(wrong transcript selected — mtime selection broken)"
        )
        assert delta["output_tokens"] == 5_000

    def test_fallback_to_snapshot_when_no_transcript(self, tmp_project: Path) -> None:
        """When no transcript exists, context-usage.json is used as fallback."""
        _write_usage(tmp_project, inp=7_000, out=1_500)

        fake_home = tmp_project / "fake_home"
        # No transcript created in fake_home

        with self._patch_home(fake_home):
            delta = get_token_delta(str(tmp_project))

        # Snapshot values should be used
        assert delta["input_tokens"] == 7_000
        assert delta["output_tokens"] == 1_500

    def test_model_trailer_populated_from_transcript(self, tmp_project: Path) -> None:
        """Model info in the transcript flows through to the delta's models dict."""
        cwd = str(tmp_project)
        fake_home = tmp_project / "fake_home"
        _create_fake_transcript_for_cwd(
            fake_home,
            cwd,
            input_tokens=5_000,
            output_tokens=1_000,
            model="claude-opus-4-8",
        )

        with self._patch_home(fake_home):
            delta = get_token_delta(cwd)

        models = delta.get("models", {})
        assert "claude-opus-4-8" in models, (
            "Model from transcript must appear in delta.models for X-AI-Model trailer"
        )
        assert models["claude-opus-4-8"]["input_tokens"] == 5_000
        assert models["claude-opus-4-8"]["output_tokens"] == 1_000


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
# amend_commit_message() tests (CHANGE 2: token/model trailers only)
# ---------------------------------------------------------------------------


class TestAmendCommitMessage:
    """Test amend_commit_message with subprocess mocked out.

    Note: cost parameter removed (CHANGE 2) — amend_commit_message now takes
    only (commit_sha, delta, cwd).  Cache/cost trailers are no longer emitted.
    """

    _DELTA = {
        "input_tokens": 500,
        "output_tokens": 100,
        "cache_read_tokens": 200,
        "cache_write_tokens": 50,
    }

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

    def test_token_trailers_added(self) -> None:
        """X-AI-Tokens-In and X-AI-Tokens-Out are present in the amended message."""
        original = "feat: add something\n"
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                self._make_log_result(original),
                self._make_amend_result(),
            ]
            amend_commit_message("abc1234", self._DELTA, "/tmp")

        amend_call = mock_run.call_args_list[1]
        new_msg = amend_call[0][0][amend_call[0][0].index("-m") + 1]

        assert "X-AI-Tokens-In: 500" in new_msg
        assert "X-AI-Tokens-Out: 100" in new_msg

    def test_no_cache_or_cost_trailers(self) -> None:
        """Cache and cost trailers must NOT appear (CHANGE 2)."""
        original = "feat: add something\n"
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                self._make_log_result(original),
                self._make_amend_result(),
            ]
            amend_commit_message("abc1234", self._DELTA, "/tmp")

        amend_call = mock_run.call_args_list[1]
        new_msg = amend_call[0][0][amend_call[0][0].index("-m") + 1]

        assert "X-AI-Cache-Read:" not in new_msg, "Cache-Read trailer must be removed"
        assert "X-AI-Cache-Write:" not in new_msg, "Cache-Write trailer must be removed"
        assert "X-AI-Cache-Ratio:" not in new_msg, "Cache-Ratio trailer must be removed"
        assert "X-AI-Est-Cost-USD:" not in new_msg, "Est-Cost trailer must be removed"

    def test_canonical_coauthoredby_added(self) -> None:
        original = "fix: bug\n"
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                self._make_log_result(original),
                self._make_amend_result(),
            ]
            amend_commit_message("abc1234", self._DELTA, "/tmp")

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
            amend_commit_message("abc1234", self._DELTA, "/tmp")

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
            amend_commit_message("abc1234", self._DELTA, "/tmp")

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
            amend_commit_message("abc1234", self._DELTA, "/tmp")

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
            amend_commit_message("abc1234", self._DELTA, "/tmp")

        amend_cmd = mock_run.call_args_list[1][0][0]
        assert "--no-verify" in amend_cmd

    def test_git_log_failure_does_not_raise(self) -> None:
        fail = MagicMock()
        fail.returncode = 1
        fail.stdout = ""
        fail.stderr = "fatal: bad object"
        with patch("subprocess.run", return_value=fail):
            # Should not raise.
            amend_commit_message("bad_sha", self._DELTA, "/tmp")


# ---------------------------------------------------------------------------
# write_cost_log() tests (CHANGE 2: cache/cost fields removed)
# ---------------------------------------------------------------------------


class TestWriteCostLog:
    """Test write_cost_log.

    Note: cost, cache_read, cache_write, and est_cost_usd fields are removed
    from the JSONL record per CHANGE 2.  write_cost_log() now takes
    (commit_sha, delta, cwd, output) — no cost parameter.
    """

    _DELTA = {
        "input_tokens": 1000,
        "output_tokens": 200,
        "cache_read_tokens": 50,
        "cache_write_tokens": 25,
    }
    _SHA = "abc1234"
    _CWD = "/home/user/project"
    _OUTPUT = "[main abc1234] feat: something\n 1 file changed"

    def _log_path(self, home: Path) -> Path:
        """Return the expected log path given a fake home directory."""
        return home / ".claude-mpm" / "commit-costs.jsonl"

    def test_jsonl_file_created_and_populated(self, tmp_path: Path) -> None:
        with patch(
            "claude_mpm.hooks.commit_cost_tracker.Path.home", return_value=tmp_path
        ):
            write_cost_log(self._SHA, self._DELTA, self._CWD, self._OUTPUT)

        log_path = self._log_path(tmp_path)
        assert log_path.exists()
        lines = log_path.read_text().strip().splitlines()
        assert len(lines) == 1

    def test_jsonl_record_has_required_fields(self, tmp_path: Path) -> None:
        """Record must contain commit_sha, cwd, tokens_in, tokens_out, timestamp, git_output."""
        with patch(
            "claude_mpm.hooks.commit_cost_tracker.Path.home", return_value=tmp_path
        ):
            write_cost_log(self._SHA, self._DELTA, self._CWD, self._OUTPUT)

        log_path = self._log_path(tmp_path)
        record = json.loads(log_path.read_text().strip())

        assert record["commit_sha"] == self._SHA
        assert record["cwd"] == self._CWD
        assert record["tokens_in"] == 1000
        assert record["tokens_out"] == 200
        assert "timestamp" in record
        assert "git_output" in record

    def test_no_cache_or_cost_fields_in_record(self, tmp_path: Path) -> None:
        """Cache and cost fields must NOT appear in the JSONL record (CHANGE 2)."""
        with patch(
            "claude_mpm.hooks.commit_cost_tracker.Path.home", return_value=tmp_path
        ):
            write_cost_log(self._SHA, self._DELTA, self._CWD, self._OUTPUT)

        log_path = self._log_path(tmp_path)
        record = json.loads(log_path.read_text().strip())

        assert "cache_read" not in record, "cache_read must be removed from JSONL"
        assert "cache_write" not in record, "cache_write must be removed from JSONL"
        assert "est_cost_usd" not in record, "est_cost_usd must be removed from JSONL"

    def test_multiple_calls_append_lines(self, tmp_path: Path) -> None:
        with patch(
            "claude_mpm.hooks.commit_cost_tracker.Path.home", return_value=tmp_path
        ):
            write_cost_log(self._SHA, self._DELTA, self._CWD, self._OUTPUT)
            write_cost_log("def5678", self._DELTA, self._CWD, "other output")

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
            write_cost_log(self._SHA, self._DELTA, self._CWD, self._OUTPUT)


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


# ---------------------------------------------------------------------------
# Regression tests for the zero-trailer bug (issue #601)
# ---------------------------------------------------------------------------
# ROOT CAUSE: ContextUsageTracker.update_usage() ADDS to existing values.
# Claude Code's Stop event provides CUMULATIVE session totals, not per-call
# deltas. Calling update_usage() with cumulative totals causes double-counting
# across session turns, and context-usage.json never grew beyond the stale
# "session-real-test" fixture. Result: git hook always read delta = 0.
#
# FIX (CHANGE 1): get_token_delta() now parses the live transcript directly so
# it does not depend on Stop-event timing.
# FIX (set_session_snapshot): set_session_snapshot() REPLACES the stored state
# with the Stop event's authoritative totals.
# ---------------------------------------------------------------------------


class TestZeroValueTrailerRegression:
    """Regression suite verifying fix for always-zero X-AI-* trailers.

    These tests guard the ContextUsageTracker.set_session_snapshot() path
    (the fallback path used by the Stop event handler).  The CHANGE 1 transcript
    path is tested in TestGetTokenDeltaFromTranscript.
    """

    def _state_file(self, project: Path) -> Path:
        return project / ".claude-mpm" / "state" / "context-usage.json"

    def _setup_tracker(self, project: Path) -> ContextUsageTracker:
        return ContextUsageTracker(project_path=project)

    def test_set_session_snapshot_replaces_stale_values(
        self, tmp_project: Path
    ) -> None:
        """Regression: snapshot must REPLACE old values, not add to them."""
        _write_usage(tmp_project, inp=100_000, out=20_000, read=80_000, write=5_000)

        tracker = self._setup_tracker(tmp_project)
        tracker.set_session_snapshot(
            session_id="session-abc123",
            input_tokens=15_000,
            output_tokens=3_000,
            cache_read=12_000,
            cache_creation=1_500,
        )

        raw = json.loads(self._state_file(tmp_project).read_text())
        assert raw["cumulative_input_tokens"] == 15_000, (
            "set_session_snapshot must overwrite; got double-counted value instead"
        )
        assert raw["cumulative_output_tokens"] == 3_000
        assert raw["cache_read_tokens"] == 12_000
        assert raw["cache_creation_tokens"] == 1_500
        assert raw["session_id"] == "session-abc123"

    def test_snapshot_then_delta_yields_nonzero(self, tmp_project: Path) -> None:
        """End-to-end (fallback path): snapshot → get_token_delta() yields > 0."""
        _write_baseline(tmp_project, inp=50_000, out=8_000, read=30_000, write=2_000)

        tracker = self._setup_tracker(tmp_project)
        tracker.set_session_snapshot(
            session_id="session-live",
            input_tokens=62_000,
            output_tokens=11_800,
            cache_read=54_000,
            cache_creation=4_500,
        )

        with patch(
            "claude_mpm.hooks.commit_cost_tracker.find_latest_transcript",
            return_value=None,
        ):
            delta = get_token_delta(str(tmp_project))

        assert delta["input_tokens"] == 12_000, (
            f"Expected 12000 input delta, got {delta['input_tokens']} "
            "(zero means context-usage.json was not updated — Stop snapshot bug)"
        )
        assert delta["output_tokens"] == 3_800
        assert delta["cache_read_tokens"] == 24_000
        assert delta["cache_write_tokens"] == 2_500

    def test_snapshot_nonzero_tokens_in_trailers(self, tmp_project: Path) -> None:
        """Simulate the full path: snapshot → get_token_delta → non-zero tokens.

        This reproduces the exact conditions under which every X-AI-* trailer
        used to be 0.  After the fix, delta must contain non-zero token counts.
        """
        _write_baseline(tmp_project, inp=0, out=0, read=0, write=0)

        tracker = self._setup_tracker(tmp_project)
        tracker.set_session_snapshot(
            session_id="session-real",
            input_tokens=10_000,
            output_tokens=2_000,
            cache_read=8_000,
            cache_creation=500,
        )

        with patch(
            "claude_mpm.hooks.commit_cost_tracker.find_latest_transcript",
            return_value=None,
        ):
            delta = get_token_delta(str(tmp_project))

        assert delta["input_tokens"] > 0, "Regression: input tokens still zero"
        assert delta["output_tokens"] > 0, "Regression: output tokens still zero"

    def test_update_usage_with_cumulative_causes_double_count(
        self, tmp_project: Path
    ) -> None:
        """Documents the OLD (broken) additive behaviour for contrast."""
        tracker = self._setup_tracker(tmp_project)
        tracker.set_session_snapshot(
            session_id="session-turn1", input_tokens=50_000, output_tokens=8_000
        )
        tracker.update_usage(input_tokens=62_000, output_tokens=11_800)

        raw = json.loads(
            (tmp_project / ".claude-mpm" / "state" / "context-usage.json").read_text()
        )
        assert raw["cumulative_input_tokens"] == 112_000, (
            "update_usage() should ADD to existing; this test documents the defect"
        )


# ---------------------------------------------------------------------------
# Multiple Stop events regression
# ---------------------------------------------------------------------------


class TestMultipleStopEventsDoNotAccumulate:
    """Two consecutive Stop events must not inflate the stored total."""

    def test_multiple_stop_events_do_not_accumulate(self, tmp_project: Path) -> None:
        """Two consecutive Stop events must not inflate the stored total."""
        tracker = ContextUsageTracker(project_path=tmp_project)

        tracker.set_session_snapshot(
            session_id="session-xyz", input_tokens=10_000, output_tokens=2_000
        )
        tracker.set_session_snapshot(
            session_id="session-xyz", input_tokens=18_000, output_tokens=3_500
        )

        raw = json.loads(
            (tmp_project / ".claude-mpm" / "state" / "context-usage.json").read_text()
        )
        assert raw["cumulative_input_tokens"] == 18_000, (
            f"After two snapshots: expected 18000, got {raw['cumulative_input_tokens']} "
            "(double-counting bug — each Stop event should replace, not add)"
        )
        assert raw["cumulative_output_tokens"] == 3_500


# ---------------------------------------------------------------------------
# Issue #696: Worktree / subagent attribution fixes
# ---------------------------------------------------------------------------


class TestResolveMainWorkingTree:
    """Tests for resolve_main_working_tree() helper (fix for #696).

    All git subprocess calls are monkeypatched so tests never touch real git.
    """

    def _make_run(self, stdout: str, returncode: int = 0):
        """Return a mock subprocess.run result."""
        m = MagicMock()
        m.returncode = returncode
        m.stdout = stdout
        m.stderr = ""
        return m

    def test_linked_worktree_returns_main_tree(self, tmp_path: Path) -> None:
        """When called from a linked worktree, returns the first worktree entry."""
        main_tree = str(tmp_path / "main-repo")
        worktree_path = str(
            tmp_path / "main-repo" / ".claude" / "worktrees" / "agent-abc"
        )
        porcelain_output = (
            f"worktree {main_tree}\nHEAD abc123\nbranch refs/heads/main\n\n"
            f"worktree {worktree_path}\nHEAD def456\nbranch refs/heads/worktree-agent-abc\n"
        )

        # Fast-path calls: --git-dir != --git-common-dir so we do NOT short-circuit.
        # The worktree's .git is a file (or .git/worktrees/agent-abc), while the
        # shared git-common-dir is the main repo's .git.  Provide distinct outputs.
        fast_dir = self._make_run(".git/worktrees/agent-abc")  # worktree-specific
        fast_common = self._make_run("../../.git")  # shared main .git
        porcelain_result = self._make_run(porcelain_output)

        with patch(
            "subprocess.run",
            side_effect=[fast_dir, fast_common, porcelain_result],
        ):
            result = resolve_main_working_tree(worktree_path)

        assert result == main_tree, (
            f"Expected main tree {main_tree!r}, got {result!r} — "
            "worktree resolution broken"
        )

    def test_main_repo_returns_itself(self, tmp_path: Path) -> None:
        """When called from the main repo root, the main tree is returned unchanged.

        The fast-path short-circuits when git-dir == git-common-dir (both return
        ``.git``), so git worktree list is never spawned.
        """
        main_tree = str(tmp_path / "main-repo")

        # Fast-path: git-dir == git-common-dir → both return ".git".
        fast_same = self._make_run(".git")

        with patch("subprocess.run", side_effect=[fast_same, fast_same]):
            result = resolve_main_working_tree(main_tree)

        assert result == main_tree

    def test_fallback_to_git_common_dir_when_porcelain_fails(
        self, tmp_path: Path
    ) -> None:
        """Falls back to git-common-dir parent when worktree list fails."""
        main_tree = tmp_path / "main-repo"
        main_tree.mkdir()
        git_dir = main_tree / ".git"
        git_dir.mkdir()
        worktree_path = str(tmp_path / "worktree")

        # Fast-path: --git-dir (worktree-specific) != --git-common-dir (shared)
        # so the fast path does NOT short-circuit.
        fast_dir_result = self._make_run(".git/worktrees/wt1")  # worktree-specific
        fast_common_result = self._make_run(str(git_dir))  # shared .git (absolute)

        # git worktree list --porcelain fails
        worktree_list_fail = self._make_run("", returncode=128)

        # Fallback git rev-parse --git-common-dir returns the shared .git path
        fallback_common_result = self._make_run(str(git_dir))

        with patch(
            "subprocess.run",
            side_effect=[
                fast_dir_result,
                fast_common_result,
                worktree_list_fail,
                fallback_common_result,
            ],
        ):
            result = resolve_main_working_tree(worktree_path)

        assert result == str(main_tree), (
            f"Expected {main_tree!r}, got {result!r} — git-common-dir fallback broken"
        )

    def test_both_git_calls_fail_returns_original_cwd(self, tmp_path: Path) -> None:
        """When all git calls fail, the original cwd is returned unchanged.

        The fast-path makes two calls (--git-dir, --git-common-dir), then
        git worktree list is attempted, then the --git-common-dir fallback.
        All four must fail to reach the final ``return cwd`` safety net.
        """
        worktree_path = str(tmp_path / "worktree")
        fail_result = self._make_run("", returncode=128)

        with patch(
            "subprocess.run",
            side_effect=[fail_result, fail_result, fail_result, fail_result],
        ):
            result = resolve_main_working_tree(worktree_path)

        assert result == worktree_path, (
            "Should return cwd unchanged when git resolution fails"
        )

    def test_exception_during_subprocess_returns_cwd(self, tmp_path: Path) -> None:
        """If subprocess.run raises, falls back gracefully to original cwd."""
        worktree_path = str(tmp_path / "worktree")

        with patch("subprocess.run", side_effect=OSError("no git")):
            result = resolve_main_working_tree(worktree_path)

        assert result == worktree_path

    def test_relative_git_common_dir_resolved_against_cwd_not_process_cwd(
        self, tmp_path: Path
    ) -> None:
        """Regression: a relative --git-common-dir output is resolved relative to the
        worktree cwd, not the process cwd.

        WHY: git rev-parse --git-common-dir can return a relative path such as
        ``../.git`` when run from a linked worktree.  Before the fix, the code
        called Path(output).resolve() with no base, anchoring to the process cwd
        instead of the worktree directory.  This test asserts that ``../.git``
        returned while cwd=``<tmp>/worktree/sub`` resolves to
        ``<tmp>/worktree/.git`` (relative to the worktree, not the process cwd).

        HOW: Build a real on-disk layout — main_repo/.git + worktree/sub — then
        mock the two subprocess calls so they behave as a real linked worktree
        would (git-dir != git-common-dir for the fast-path, then worktree list
        fails, then git-common-dir returns a relative path pointing to main_repo/.git).
        Assert the resolved parent equals main_repo.
        """
        # Create the real directory tree so Path.resolve() works correctly.
        main_repo = tmp_path / "main_repo"
        main_git = main_repo / ".git"
        main_git.mkdir(parents=True)

        # Simulate a linked worktree at main_repo/.clone_worktrees/sub.
        worktree_dir = main_repo / ".clone_worktrees" / "sub"
        worktree_dir.mkdir(parents=True)
        worktree_cwd = str(worktree_dir)

        # git rev-parse --git-common-dir returns "../../.git" (relative to worktree_dir).
        relative_git_common = "../../.git"

        # Fast-path calls: make --git-dir != --git-common-dir so the fast path
        # does NOT short-circuit (we need to reach the fallback).
        fast_dir_result = self._make_run(
            ".git/worktrees/sub"
        )  # git-dir (worktree-specific)
        fast_common_result = self._make_run(
            relative_git_common
        )  # git-common-dir (shared)

        # worktree list call fails so we fall through to the --git-common-dir fallback.
        worktree_list_fail = self._make_run("", returncode=128)

        # Fallback --git-common-dir call returns the same relative path.
        fallback_common_result = self._make_run(relative_git_common)

        side_effects = [
            fast_dir_result,  # git rev-parse --git-dir  (fast-path)
            fast_common_result,  # git rev-parse --git-common-dir  (fast-path)
            worktree_list_fail,  # git worktree list --porcelain  (fails → fallback)
            fallback_common_result,  # git rev-parse --git-common-dir  (fallback)
        ]

        with patch("subprocess.run", side_effect=side_effects):
            result = resolve_main_working_tree(worktree_cwd)

        expected = str(main_repo)
        assert result == expected, (
            f"Expected main_repo={expected!r}, got {result!r}.\n"
            "Relative git-common-dir must be resolved relative to the worktree cwd, "
            "not the process cwd (regression guard for trusty-review item #1 on #696)."
        )


class TestGetTokenDeltaWorktreeFallback:
    """Test that get_token_delta() uses the main-tree transcript when the
    worktree's own transcript directory is missing (issue #696).
    """

    def _patch_home(self, fake_home: Path):
        """Patch Path.home() inside transcript_usage to use fake_home."""
        return patch(
            "claude_mpm.hooks.transcript_usage.Path.home",
            return_value=fake_home,
        )

    def _patch_resolve_main(self, canonical_cwd: str):
        """Patch resolve_main_working_tree to return canonical_cwd."""
        return patch(
            "claude_mpm.hooks.commit_cost_tracker.resolve_main_working_tree",
            return_value=canonical_cwd,
        )

    def test_worktree_cwd_misses_but_main_tree_transcript_exists(
        self, tmp_path: Path
    ) -> None:
        """When transcript is absent for worktree cwd but present for main tree,
        get_token_delta() returns the real non-zero delta from main tree.
        """
        main_tree = str(tmp_path / "main-repo")
        Path(main_tree).mkdir(parents=True)
        state_dir = Path(main_tree) / ".claude-mpm" / "state"
        state_dir.mkdir(parents=True)

        worktree_cwd = str(tmp_path / "main-repo" / ".claude" / "worktrees" / "agent-x")

        # Transcript exists ONLY for main_tree, not for worktree_cwd.
        fake_home = tmp_path / "fake_home"
        _create_fake_transcript_for_cwd(
            fake_home,
            main_tree,
            input_tokens=20_000,
            output_tokens=4_500,
            model="claude-sonnet-4-6",
        )
        # No transcript for worktree_cwd (nothing created there).

        with self._patch_home(fake_home), self._patch_resolve_main(main_tree):
            delta = get_token_delta(worktree_cwd)

        assert delta["input_tokens"] == 20_000, (
            f"Expected 20000 from main-tree transcript, got {delta['input_tokens']} — "
            "worktree fallback not working (issue #696)"
        )
        assert delta["output_tokens"] == 4_500

    def test_baseline_written_to_canonical_cwd(self, tmp_path: Path) -> None:
        """Baseline is written under the canonical (main-tree) cwd, not the worktree."""
        main_tree = str(tmp_path / "main-repo")
        Path(main_tree).mkdir(parents=True)
        (Path(main_tree) / ".claude-mpm" / "state").mkdir(parents=True)

        worktree_cwd = str(tmp_path / "main-repo" / ".claude" / "worktrees" / "agent-y")

        fake_home = tmp_path / "fake_home"
        _create_fake_transcript_for_cwd(
            fake_home,
            main_tree,
            input_tokens=8_000,
            output_tokens=1_200,
        )

        with self._patch_home(fake_home), self._patch_resolve_main(main_tree):
            get_token_delta(worktree_cwd)

        # Baseline must be at the main-tree path, NOT the worktree path.
        baseline_path = (
            Path(main_tree) / ".claude-mpm" / "state" / "commit-token-baseline.json"
        )
        assert baseline_path.exists(), (
            f"Baseline file missing at {baseline_path} — "
            "was written to worktree path instead of main-tree path"
        )
        baseline = json.loads(baseline_path.read_text())
        assert baseline["input_tokens"] == 8_000
        assert baseline["output_tokens"] == 1_200

    def test_normal_non_worktree_commit_still_works(self, tmp_path: Path) -> None:
        """Regression: a normal main-repo commit (no worktree) still gets the correct delta."""
        main_tree = str(tmp_path / "main-repo")
        Path(main_tree).mkdir(parents=True)
        (Path(main_tree) / ".claude-mpm" / "state").mkdir(parents=True)

        fake_home = tmp_path / "fake_home"
        _create_fake_transcript_for_cwd(
            fake_home,
            main_tree,
            input_tokens=12_000,
            output_tokens=2_500,
            model="claude-opus-4-8",
        )

        # resolve_main_working_tree returns cwd unchanged for a normal repo.
        with self._patch_home(fake_home), self._patch_resolve_main(main_tree):
            delta = get_token_delta(main_tree)

        assert delta["input_tokens"] == 12_000, (
            "Normal (non-worktree) commit regression: wrong token count"
        )
        assert delta["output_tokens"] == 2_500
        assert "claude-opus-4-8" in delta.get("models", {})


class TestAmendCommitMessageZeroSkip:
    """Test that amend_commit_message() omits X-AI-Tokens-In/Out when delta is 0/0
    (fix for #696 zero-skip requirement).
    """

    def _make_log_result(self, message: str) -> MagicMock:
        r = MagicMock()
        r.returncode = 0
        r.stdout = message
        r.stderr = ""
        return r

    def _make_amend_result(self) -> MagicMock:
        r = MagicMock()
        r.returncode = 0
        r.stdout = ""
        r.stderr = ""
        return r

    def test_zero_delta_skips_token_trailers(self) -> None:
        """When both input_tokens and output_tokens are 0, token trailers are omitted."""
        zero_delta: dict = {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_read_tokens": 0,
            "cache_write_tokens": 0,
            "models": {},
        }

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                self._make_log_result("feat: some change\n"),
                self._make_amend_result(),
            ]
            amend_commit_message("abc1234", zero_delta, "/tmp")

        amend_call = mock_run.call_args_list[1]
        new_msg = amend_call[0][0][amend_call[0][0].index("-m") + 1]

        assert "X-AI-Tokens-In:" not in new_msg, (
            "X-AI-Tokens-In must be omitted when delta is 0"
        )
        assert "X-AI-Tokens-Out:" not in new_msg, (
            "X-AI-Tokens-Out must be omitted when delta is 0"
        )

    def test_zero_delta_still_emits_coauthoredby(self) -> None:
        """Co-Authored-By is always emitted even when token delta is 0."""
        zero_delta: dict = {
            "input_tokens": 0,
            "output_tokens": 0,
            "models": {},
        }

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                self._make_log_result("fix: something\n"),
                self._make_amend_result(),
            ]
            amend_commit_message("abc1234", zero_delta, "/tmp")

        amend_call = mock_run.call_args_list[1]
        new_msg = amend_call[0][0][amend_call[0][0].index("-m") + 1]

        assert _COAUTHORED_CANONICAL in new_msg, (
            "Co-Authored-By must be preserved even when token delta is 0"
        )

    def test_nonzero_out_only_still_emits_trailers(self) -> None:
        """If output_tokens is nonzero (input=0), token trailers are still emitted."""
        delta: dict = {
            "input_tokens": 0,
            "output_tokens": 50,
            "models": {},
        }

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                self._make_log_result("chore: update\n"),
                self._make_amend_result(),
            ]
            amend_commit_message("abc1234", delta, "/tmp")

        amend_call = mock_run.call_args_list[1]
        new_msg = amend_call[0][0][amend_call[0][0].index("-m") + 1]

        assert "X-AI-Tokens-In: 0" in new_msg
        assert "X-AI-Tokens-Out: 50" in new_msg

    def test_nonzero_tokens_still_emits_trailers(self) -> None:
        """Regression: normal non-zero delta still produces token trailers."""
        delta: dict = {
            "input_tokens": 1000,
            "output_tokens": 200,
            "models": {},
        }

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                self._make_log_result("feat: new feature\n"),
                self._make_amend_result(),
            ]
            amend_commit_message("abc1234", delta, "/tmp")

        amend_call = mock_run.call_args_list[1]
        new_msg = amend_call[0][0][amend_call[0][0].index("-m") + 1]

        assert "X-AI-Tokens-In: 1000" in new_msg
        assert "X-AI-Tokens-Out: 200" in new_msg
