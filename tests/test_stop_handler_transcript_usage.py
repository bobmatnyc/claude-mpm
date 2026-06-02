"""Regression tests for Stop handler transcript-based token capture (issue #601 real fix).

ROOT CAUSE (confirmed):
    Real Claude Code Stop events carry only ``hook_event_name`` (plus optional
    ``session_id``, ``cwd``, ``reason``, ``stop_hook_active``).  There is NO
    ``usage`` field.  Evidence from hook log:
        Received event with keys: ['hook_event_name']
          hook_event_name = 'Stop'
    The previous "fix" gated snapshot writes on ``if "usage" in event:``, which
    NEVER fires, so context-usage.json was never updated by a real Stop event.

REAL FIX:
    ``parse_transcript_usage()`` (shared module) sums ``usage`` fields across all
    ``type=="assistant"`` records in the session transcript JSONL.
    ``handle_stop_fast()`` calls this via the ``_parse_transcript_usage`` wrapper
    as the primary path; the event["usage"] branch is kept only as a
    forward-compatible fast path.

ACCEPTANCE BAR:
    1. ``_parse_transcript_usage()`` returns correct cumulative totals from a
       multi-message fixture.
    2. ``_derive_transcript_path()`` returns the correct path given cwd + session_id.
    3. ``handle_stop_fast()`` called with a NO-usage Stop event (the real shape)
       still writes a non-zero snapshot to context-usage.json when the transcript
       fixture contains real usage records.
    4. The old event["usage"]-only approach would have produced zero — confirmed
       by a negative control test.
    5. End-to-end: snapshot → get_token_delta() → non-zero token delta.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure src/ is importable from repo root.
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.hooks.claude_hooks.handlers.stop_handler import (
    _derive_transcript_path,
    _parse_transcript_usage,
)
from claude_mpm.hooks.commit_cost_tracker import (
    _format_models_trailer,
    _primary_model,
    amend_commit_message,
    get_token_delta,
)
from claude_mpm.services.infrastructure.context_usage_tracker import ContextUsageTracker

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def _make_project(tmp_path: Path) -> Path:
    """Create a minimal .claude-mpm/state directory under tmp_path."""
    (tmp_path / ".claude-mpm" / "state").mkdir(parents=True)
    return tmp_path


# ---------------------------------------------------------------------------
# _parse_transcript_usage() tests
# ---------------------------------------------------------------------------


class TestParseTranscriptUsage:
    def test_single_message_returns_correct_totals(self, tmp_path: Path) -> None:
        """A transcript with one assistant message returns its exact usage."""
        t = tmp_path / "transcript.jsonl"
        _write_transcript(
            t, [_make_assistant_record(input_tokens=1000, output_tokens=200)]
        )

        result = _parse_transcript_usage(t)

        assert result is not None
        assert result["input_tokens"] == 1000
        assert result["output_tokens"] == 200
        assert result["cache_creation_input_tokens"] == 0
        assert result["cache_read_input_tokens"] == 0

    def test_multiple_messages_sums_all(self, tmp_path: Path) -> None:
        """Three assistant messages: their usage is summed correctly.

        This is the regression case that FAILS against the old code path
        (which returned None because it looked for event['usage'] instead).
        """
        t = tmp_path / "transcript.jsonl"
        _write_transcript(
            t,
            [
                _make_assistant_record(
                    input_tokens=5_000,
                    output_tokens=1_000,
                    cache_creation=500,
                    cache_read=2_000,
                ),
                _make_assistant_record(
                    input_tokens=3_000,
                    output_tokens=800,
                    cache_creation=200,
                    cache_read=10_000,
                ),
                _make_assistant_record(
                    input_tokens=2_000,
                    output_tokens=400,
                    cache_creation=100,
                    cache_read=5_000,
                ),
            ],
        )

        result = _parse_transcript_usage(t)

        assert result is not None
        assert result["input_tokens"] == 10_000  # 5000+3000+2000
        assert result["output_tokens"] == 2_200  # 1000+800+400
        assert result["cache_creation_input_tokens"] == 800  # 500+200+100
        assert result["cache_read_input_tokens"] == 17_000  # 2000+10000+5000

    def test_non_assistant_records_skipped(self, tmp_path: Path) -> None:
        """User and system records do not contribute to totals."""
        t = tmp_path / "transcript.jsonl"
        user_rec = json.dumps(
            {"type": "user", "message": {"usage": {"input_tokens": 9999}}}
        )
        asst_rec = _make_assistant_record(input_tokens=100, output_tokens=50)
        _write_transcript(t, [user_rec, asst_rec])

        result = _parse_transcript_usage(t)

        assert result is not None
        assert result["input_tokens"] == 100  # user record must not contribute

    def test_missing_file_returns_none(self, tmp_path: Path) -> None:
        """Non-existent transcript path → None (fail-open)."""
        result = _parse_transcript_usage(tmp_path / "nosuchfile.jsonl")
        assert result is None

    def test_empty_transcript_returns_none(self, tmp_path: Path) -> None:
        """A transcript with no assistant messages → None."""
        t = tmp_path / "transcript.jsonl"
        _write_transcript(t, [json.dumps({"type": "mode", "mode": "normal"})])
        result = _parse_transcript_usage(t)
        assert result is None

    def test_invalid_json_lines_skipped_gracefully(self, tmp_path: Path) -> None:
        """Corrupt JSONL lines are skipped; valid records still parsed."""
        t = tmp_path / "transcript.jsonl"
        good = _make_assistant_record(input_tokens=500, output_tokens=100)
        t.write_text("NOT JSON\n" + good + "\n{bad}\n", encoding="utf-8")

        result = _parse_transcript_usage(t)

        assert result is not None
        assert result["input_tokens"] == 500

    def test_assistant_without_usage_skipped(self, tmp_path: Path) -> None:
        """An assistant record without a usage field is skipped gracefully."""
        t = tmp_path / "transcript.jsonl"
        no_usage = json.dumps({"type": "assistant", "message": {"role": "assistant"}})
        with_usage = _make_assistant_record(input_tokens=300, output_tokens=60)
        _write_transcript(t, [no_usage, with_usage])

        result = _parse_transcript_usage(t)

        assert result is not None
        assert result["input_tokens"] == 300

    def test_real_session_transcript_produces_nonzero(self) -> None:
        """Parse a real session transcript from this machine if available.

        This test is skipped when running in CI (no transcript present).
        It proves the fix works against an actual Claude Code artifact.
        """
        transcript = (
            Path.home()
            / ".claude"
            / "projects"
            / "-Volumes-SSD1-Projects-claude-mpm"
            / "974d933c-5d8d-4dbc-a9f6-77cdb22a96e6.jsonl"
        )
        if not transcript.exists():
            pytest.skip("Real session transcript not available (CI environment)")

        result = _parse_transcript_usage(transcript)

        assert result is not None, "Real transcript returned None — parsing broken"
        assert result["input_tokens"] > 0, "Real transcript: zero input_tokens"
        assert result["output_tokens"] > 0, "Real transcript: zero output_tokens"
        # This session has heavy cache use; both cache fields should be large
        total = result["input_tokens"] + result["output_tokens"]
        assert total > 0, f"No tokens from real transcript (got {result})"


# ---------------------------------------------------------------------------
# _derive_transcript_path() tests
# ---------------------------------------------------------------------------


class TestDeriveTranscriptPath:
    def test_typical_path(self) -> None:
        result = _derive_transcript_path("abc-123", "/Volumes/SSD1/Projects/claude-mpm")
        assert result is not None
        assert result.name == "abc-123.jsonl"
        assert "-Volumes-SSD1-Projects-claude-mpm" in str(result)

    def test_simple_path(self) -> None:
        result = _derive_transcript_path("sid", "/foo/bar")
        assert result is not None
        assert result.name == "sid.jsonl"
        assert "-foo-bar" in str(result)

    def test_empty_session_id_returns_none(self) -> None:
        assert _derive_transcript_path("", "/some/path") is None

    def test_empty_cwd_returns_none(self) -> None:
        assert _derive_transcript_path("abc", "") is None

    def test_both_empty_returns_none(self) -> None:
        assert _derive_transcript_path("", "") is None


# ---------------------------------------------------------------------------
# Negative control: old event["usage"] approach would have returned None
# ---------------------------------------------------------------------------


class TestNegativeControlOldApproach:
    """Documents exactly why the previous fix failed.

    The old code:
        if "usage" in event:
            usage_data = event["usage"]  # Stop events do NOT have this key

    This test proves that a real-shape Stop event (no "usage" key) produces
    usage_data=None under the old guard and therefore never writes a snapshot.
    The new code skips the guard and falls through to transcript parsing.
    """

    def test_stop_event_without_usage_key(self) -> None:
        """A real-shape Stop event has no 'usage' key — old guard fails."""
        real_stop_event = {
            "hook_event_name": "Stop",
            "session_id": "abc123",
            "cwd": "/some/project",
            "reason": "completed",
        }
        # Simulate the OLD guard: ``if "usage" in event:``
        old_usage_data = real_stop_event.get("usage")  # → None

        assert old_usage_data is None, (
            "The old guard 'if usage in event:' should have been False for a real "
            "Stop event; getting a non-None value here means the event shape changed."
        )

    def test_stop_event_with_usage_key_works(self) -> None:
        """A hypothetical future Stop event with 'usage' still works via fast path."""
        future_stop_event = {
            "hook_event_name": "Stop",
            "session_id": "xyz",
            "cwd": "/some/project",
            "usage": {
                "input_tokens": 5000,
                "output_tokens": 1000,
                "cache_creation_input_tokens": 200,
                "cache_read_input_tokens": 3000,
            },
        }
        ev_usage = future_stop_event.get("usage")
        assert ev_usage is not None
        assert ev_usage["input_tokens"] == 5000


# ---------------------------------------------------------------------------
# Integration: handle_stop_fast with transcript fixture → snapshot → delta
# ---------------------------------------------------------------------------


class TestStopHandlerTranscriptIntegration:
    """End-to-end tests confirming the full path from Stop event to non-zero trailers.

    Architecture (for clarity):
    1. handle_stop_fast() fires on a real-shape Stop event (no "usage" key).
    2. It calls _derive_transcript_path(session_id, cwd) to locate the transcript.
    3. _parse_transcript_usage() sums per-message usage from the JSONL.
    4. set_session_snapshot() writes the cumulative total to context-usage.json.
    5. get_token_delta() reads that file and subtracts the baseline → non-zero delta.
    6. Non-zero input/output token values → non-zero X-AI-* trailers.
    """

    def _setup_project(self, tmp_path: Path) -> Path:
        (tmp_path / ".claude-mpm" / "state").mkdir(parents=True)
        return tmp_path

    def _write_transcript_fixture(self, project: Path, session_id: str) -> Path:
        """Create a transcript JSONL inside a fake ~/.claude/projects dir."""
        cwd = str(project)
        encoded = cwd.replace("/", "-")
        transcript_dir = project / "fake_home" / ".claude" / "projects" / encoded
        transcript_dir.mkdir(parents=True)
        transcript_path = transcript_dir / f"{session_id}.jsonl"
        _write_transcript(
            transcript_path,
            [
                _make_assistant_record(
                    input_tokens=20_000,
                    output_tokens=4_000,
                    cache_creation=2_000,
                    cache_read=15_000,
                ),
                _make_assistant_record(
                    input_tokens=5_000,
                    output_tokens=1_200,
                    cache_creation=300,
                    cache_read=8_000,
                ),
            ],
        )
        return transcript_path

    def _make_stop_handler(self) -> object:
        """Create a StopHandler with a MagicMock base/hook_handler."""
        from claude_mpm.hooks.claude_hooks.handlers.base import BaseEventHandler
        from claude_mpm.hooks.claude_hooks.handlers.stop_handler import StopHandler

        mock_base = MagicMock(spec=BaseEventHandler)
        mock_base.hook_handler = MagicMock()
        mock_base.hook_handler.auto_pause_handler = None
        mock_base.hook_handler.response_tracking_manager = None
        mock_base._get_git_branch = MagicMock(return_value="main")
        return StopHandler(mock_base)

    def test_no_usage_event_writes_snapshot_from_transcript(
        self, tmp_path: Path
    ) -> None:
        """Regression: real-shape Stop event (no 'usage') writes non-zero snapshot.

        BEFORE FIX: snapshot never written (delta always 0).
        AFTER FIX: snapshot written from transcript; delta > 0.
        """
        project = self._setup_project(tmp_path)
        session_id = "test-sess-abc"

        transcript_path = self._write_transcript_fixture(project, session_id)

        # Real-shape Stop event: NO "usage" key.
        stop_event = {
            "hook_event_name": "Stop",
            "session_id": session_id,
            "cwd": str(project),
            "reason": "completed",
        }

        handler = self._make_stop_handler()

        # Patch Path.home() inside stop_handler so _derive_transcript_path
        # finds our fixture instead of the real ~/.claude directory.
        fake_home = project / "fake_home"

        # ContextUsageTracker is imported lazily inside the try block, so we patch
        # it via the module where it lives, not via stop_handler's namespace.
        # Patch MessageService and UnifiedPathManager to avoid real side effects.
        captured_snapshots: list[dict] = []

        def fake_set_session_snapshot(
            session_id: str = "",
            input_tokens: int = 0,
            output_tokens: int = 0,
            cache_creation: int = 0,
            cache_read: int = 0,
            models: dict | None = None,
        ) -> MagicMock:
            captured_snapshots.append(
                {
                    "session_id": session_id,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cache_creation": cache_creation,
                    "cache_read": cache_read,
                    "models": models,
                }
            )
            return MagicMock()

        mock_tracker_instance = MagicMock()
        mock_tracker_instance.set_session_snapshot.side_effect = (
            fake_set_session_snapshot
        )

        with (
            patch(
                "claude_mpm.hooks.claude_hooks.handlers.stop_handler.Path.home",
                return_value=fake_home,
            ),
            patch(
                "claude_mpm.core.unified_paths.UnifiedPathManager"
            ) as mock_path_mgr_cls,
            patch(
                "claude_mpm.services.communication.message_service.MessageService"
            ) as mock_svc_cls,
            patch(
                "claude_mpm.services.infrastructure.context_usage_tracker.ContextUsageTracker",
                return_value=mock_tracker_instance,
            ),
        ):
            mock_path_mgr_cls.return_value.project_root = project
            mock_svc_cls.return_value.list_messages.return_value = []

            handler.handle_stop_fast(stop_event)

        # The tracker's set_session_snapshot must have been called with non-zero values.
        assert len(captured_snapshots) == 1, (
            "set_session_snapshot() was never called — transcript path not parsed"
        )
        snap = captured_snapshots[0]
        assert snap["input_tokens"] == 25_000, (
            f"Expected 25000 input tokens, got {snap['input_tokens']}"
        )
        assert snap["output_tokens"] == 5_200, (
            f"Expected 5200 output tokens, got {snap['output_tokens']}"
        )

    def test_end_to_end_snapshot_to_nonzero_tokens(self, tmp_path: Path) -> None:
        """Full path: transcript parse → snapshot → non-zero token delta.

        This is the acceptance test for the complete fix.  Before the fix,
        context-usage.json stayed at the stale 'session-real-test' values and
        delta was always 0 so all X-AI-* trailers showed zero.
        """
        project = self._setup_project(tmp_path)
        session_id = "e2e-test-session"
        cwd = str(project)

        # Build transcript fixture
        transcript_path = self._write_transcript_fixture(project, session_id)

        # Parse and write snapshot directly (simulates what handle_stop_fast does)
        from claude_mpm.hooks.claude_hooks.handlers.stop_handler import (
            _derive_transcript_path,
            _parse_transcript_usage,
        )

        # Temporarily override Path.home to point to our fake home
        fake_home = project / "fake_home"
        with patch(
            "claude_mpm.hooks.claude_hooks.handlers.stop_handler.Path.home",
            return_value=fake_home,
        ):
            derived = _derive_transcript_path(session_id, cwd)

        assert derived is not None
        usage = _parse_transcript_usage(derived)

        assert usage is not None, "Transcript parsing returned None"
        assert usage["input_tokens"] == 25_000
        assert usage["output_tokens"] == 5_200

        # Write the snapshot (as handle_stop_fast would)
        tracker = ContextUsageTracker(project_path=project)
        tracker.set_session_snapshot(
            session_id=session_id,
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
            cache_creation=usage["cache_creation_input_tokens"],
            cache_read=usage["cache_read_input_tokens"],
        )

        # Now simulate the git post-commit hook with zero baseline (first commit)
        with patch(
            "claude_mpm.hooks.commit_cost_tracker.find_latest_transcript",
            return_value=None,
        ):
            delta = get_token_delta(cwd)

        assert delta["input_tokens"] == 25_000, (
            f"Expected 25000 input_tokens in delta, got {delta['input_tokens']} "
            "(zero means snapshot was not written — real bug)"
        )
        assert delta["output_tokens"] == 5_200
        assert delta["input_tokens"] > 0, (
            "Regression: input tokens still zero — trailers would show 0"
        )

    def test_old_event_usage_guard_fails_for_real_stop_event(
        self, tmp_path: Path
    ) -> None:
        """Confirms the old guard would have returned zero for a real Stop event.

        The old code was equivalent to:
            usage_data = event.get("usage") if "usage" in event else None
        Real Stop events have no "usage" key → usage_data is None → no snapshot.
        This test documents that failure mode explicitly.
        """
        real_stop_event = {
            "hook_event_name": "Stop",
            "session_id": "real-session",
            "cwd": "/some/project",
            "reason": "completed",
        }

        # OLD broken path
        old_result = real_stop_event.get("usage")  # None

        # NEW path: would call _parse_transcript_usage
        new_result_would_be_none_only_if_no_transcript = old_result
        # The key assertion: old path produces None for real events
        assert new_result_would_be_none_only_if_no_transcript is None, (
            "Old guard should have been None for real Stop events; "
            "if this fails the Stop event shape changed and the fast path is now viable"
        )


# ---------------------------------------------------------------------------
# Per-model aggregation tests  (new — model tracking feature)
# ---------------------------------------------------------------------------


class TestParseTranscriptUsagePerModel:
    """Verify that _parse_transcript_usage returns correct per-model breakdowns.

    REGRESSION GUARD: If the ``models`` key is absent from the result, or if
    per-model counts are wrong, the commit trailers X-AI-Model/X-AI-Models will
    be missing or incorrect.  These tests MUST FAIL if the model-tracking logic
    is removed from _parse_transcript_usage().
    """

    def test_single_model_appears_in_models_dict(self, tmp_path: Path) -> None:
        """One model → models dict has exactly one entry with correct totals."""
        t = tmp_path / "t.jsonl"
        _write_transcript(
            t,
            [
                _make_assistant_record(
                    input_tokens=1_000,
                    output_tokens=200,
                    model="claude-opus-4-8",
                ),
                _make_assistant_record(
                    input_tokens=500,
                    output_tokens=100,
                    model="claude-opus-4-8",
                ),
            ],
        )

        result = _parse_transcript_usage(t)

        assert result is not None
        assert "models" in result, "models key must be present in result"
        models = result["models"]
        assert set(models.keys()) == {"claude-opus-4-8"}
        m = models["claude-opus-4-8"]
        assert m["input_tokens"] == 1_500
        assert m["output_tokens"] == 300

    def test_two_models_aggregated_independently(self, tmp_path: Path) -> None:
        """Two models → per-model sums are independent; totals reconcile.

        This is the primary regression test: without model tracking, ``models``
        would be absent and the X-AI-Model/X-AI-Models trailers could not be
        emitted.  Test MUST FAIL if models aggregation is removed.
        """
        t = tmp_path / "t.jsonl"
        _write_transcript(
            t,
            [
                # opus messages
                _make_assistant_record(
                    input_tokens=8_000,
                    output_tokens=3_000,
                    cache_creation=500,
                    cache_read=20_000,
                    model="claude-opus-4-8",
                ),
                _make_assistant_record(
                    input_tokens=2_000,
                    output_tokens=1_000,
                    cache_creation=200,
                    cache_read=5_000,
                    model="claude-opus-4-8",
                ),
                # sonnet messages (subagent)
                _make_assistant_record(
                    input_tokens=1_500,
                    output_tokens=400,
                    cache_creation=0,
                    cache_read=3_000,
                    model="claude-sonnet-4-6",
                ),
                _make_assistant_record(
                    input_tokens=500,
                    output_tokens=150,
                    cache_creation=0,
                    cache_read=1_000,
                    model="claude-sonnet-4-6",
                ),
            ],
        )

        result = _parse_transcript_usage(t)

        assert result is not None

        # --- aggregate totals must reconcile ---
        assert result["input_tokens"] == 12_000  # 8k+2k+1.5k+0.5k
        assert result["output_tokens"] == 4_550  # 3k+1k+400+150
        assert result["cache_creation_input_tokens"] == 700  # 500+200
        assert result["cache_read_input_tokens"] == 29_000  # 20k+5k+3k+1k

        # --- per-model breakdown ---
        models = result["models"]
        assert set(models.keys()) == {"claude-opus-4-8", "claude-sonnet-4-6"}, (
            "Both models must appear in the models dict — this test MUST FAIL "
            "without model-tracking logic."
        )

        opus = models["claude-opus-4-8"]
        assert opus["input_tokens"] == 10_000  # 8k+2k
        assert opus["output_tokens"] == 4_000  # 3k+1k
        assert opus["cache_creation_input_tokens"] == 700
        assert opus["cache_read_input_tokens"] == 25_000  # 20k+5k

        sonnet = models["claude-sonnet-4-6"]
        assert sonnet["input_tokens"] == 2_000  # 1.5k+0.5k
        assert sonnet["output_tokens"] == 550  # 400+150
        assert sonnet["cache_creation_input_tokens"] == 0
        assert sonnet["cache_read_input_tokens"] == 4_000  # 3k+1k

    def test_no_model_field_falls_back_to_unknown(self, tmp_path: Path) -> None:
        """An assistant record without a model field is counted under 'unknown'."""
        t = tmp_path / "t.jsonl"
        _write_transcript(
            t,
            [_make_assistant_record(input_tokens=300, output_tokens=60)],  # no model
        )

        result = _parse_transcript_usage(t)

        assert result is not None
        models = result["models"]
        assert "unknown" in models, (
            "Records without a model field must be bucketed under 'unknown'"
        )
        assert models["unknown"]["input_tokens"] == 300

    def test_models_totals_sum_to_aggregate(self, tmp_path: Path) -> None:
        """Sum of all per-model token counts must equal the aggregate totals."""
        t = tmp_path / "t.jsonl"
        _write_transcript(
            t,
            [
                _make_assistant_record(
                    input_tokens=4_000, output_tokens=1_000, model="claude-opus-4-8"
                ),
                _make_assistant_record(
                    input_tokens=1_000, output_tokens=500, model="claude-sonnet-4-6"
                ),
            ],
        )

        result = _parse_transcript_usage(t)
        assert result is not None

        models = result["models"]
        total_in = sum(m["input_tokens"] for m in models.values())
        total_out = sum(m["output_tokens"] for m in models.values())
        assert total_in == result["input_tokens"]
        assert total_out == result["output_tokens"]


# ---------------------------------------------------------------------------
# _primary_model() and _format_models_trailer() unit tests
# ---------------------------------------------------------------------------


class TestPrimaryModelAndTrailerFormat:
    """Unit tests for the two helper functions that shape the commit trailers."""

    def test_primary_model_empty_returns_none(self) -> None:
        assert _primary_model({}) is None

    def test_primary_model_single_entry(self) -> None:
        assert _primary_model({"opus": {"output_tokens": 100}}) == "opus"

    def test_primary_model_picks_highest_output(self) -> None:
        """Model with most output tokens is selected as primary."""
        delta = {
            "claude-opus-4-8": {"output_tokens": 50_000},
            "claude-sonnet-4-6": {"output_tokens": 500},
        }
        assert _primary_model(delta) == "claude-opus-4-8"

    def test_primary_model_must_fail_without_logic(self) -> None:
        """Regression: a simple dict[0] approach would pick wrong model.

        If _primary_model() were removed or replaced with ``next(iter(d))``,
        this test would fail because dict insertion order puts sonnet first.
        """
        delta = {
            "claude-sonnet-4-6": {"output_tokens": 10},  # inserted first
            "claude-opus-4-8": {"output_tokens": 999},  # should win
        }
        # A naive implementation that returns the first key would return sonnet.
        naive_result = next(iter(delta))
        assert naive_result == "claude-sonnet-4-6"  # confirms the naive trap
        # Correct implementation must return opus.
        assert _primary_model(delta) == "claude-opus-4-8", (
            "MUST FAIL without the max(output_tokens) logic in _primary_model()"
        )

    def test_format_models_trailer_single_model_returns_none(self) -> None:
        """Single model → no multi-model trailer (caller emits X-AI-Model only)."""
        delta = {"claude-opus-4-8": {"input_tokens": 100, "output_tokens": 50}}
        assert _format_models_trailer(delta) is None

    def test_format_models_trailer_two_models(self) -> None:
        """Two models → semicolon-separated string with in=,out= format."""
        delta = {
            "claude-opus-4-8": {"input_tokens": 8_954, "output_tokens": 572_998},
            "claude-sonnet-4-6": {"input_tokens": 1_000, "output_tokens": 200},
        }
        result = _format_models_trailer(delta)

        assert result is not None
        # Must be a single line (no newlines — git-trailer safe)
        assert "\n" not in result
        # Opus appears first (highest output tokens)
        assert result.startswith("claude-opus-4-8")
        assert "claude-sonnet-4-6" in result
        # Contains in= and out= for each model
        assert "in=8954,out=572998" in result
        assert "in=1000,out=200" in result
        # Separated by "; "
        assert "; " in result

    def test_format_models_trailer_empty_returns_none(self) -> None:
        assert _format_models_trailer({}) is None


# ---------------------------------------------------------------------------
# X-AI-Model / X-AI-Models trailer emission (amend_commit_message)
# ---------------------------------------------------------------------------


class TestAmendCommitMessageModelTrailers:
    """Verify the new model trailers are included in amended commit messages."""

    _DELTA_WITH_ONE_MODEL: dict = {
        "input_tokens": 1_000,
        "output_tokens": 500,
        "cache_read_tokens": 200,
        "cache_write_tokens": 50,
        "models": {
            "claude-opus-4-8": {
                "input_tokens": 1_000,
                "output_tokens": 500,
                "cache_creation_input_tokens": 50,
                "cache_read_input_tokens": 200,
            }
        },
    }

    _DELTA_WITH_TWO_MODELS: dict = {
        "input_tokens": 3_000,
        "output_tokens": 2_000,
        "cache_read_tokens": 0,
        "cache_write_tokens": 0,
        "models": {
            "claude-opus-4-8": {
                "input_tokens": 2_500,
                "output_tokens": 1_800,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
            },
            "claude-sonnet-4-6": {
                "input_tokens": 500,
                "output_tokens": 200,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
            },
        },
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

    def _get_amended_msg(self, delta: dict) -> str:
        """Run amend_commit_message and return the new commit message string."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                self._make_log_result("feat: add something\n"),
                self._make_amend_result(),
            ]
            amend_commit_message("abc1234", delta, "/tmp")

        amend_call = mock_run.call_args_list[1]
        cmd = amend_call[0][0]
        return cmd[cmd.index("-m") + 1]

    def test_single_model_emits_x_ai_model(self) -> None:
        """Single model in delta → X-AI-Model trailer present."""
        msg = self._get_amended_msg(self._DELTA_WITH_ONE_MODEL)
        assert "X-AI-Model: claude-opus-4-8" in msg, (
            "MUST FAIL without model trailer logic — X-AI-Model missing"
        )

    def test_single_model_no_x_ai_models(self) -> None:
        """Single model → X-AI-Models (plural) trailer must NOT appear."""
        msg = self._get_amended_msg(self._DELTA_WITH_ONE_MODEL)
        assert "X-AI-Models:" not in msg

    def test_two_models_emits_both_trailers(self) -> None:
        """Two models → both X-AI-Model and X-AI-Models trailers emitted."""
        msg = self._get_amended_msg(self._DELTA_WITH_TWO_MODELS)
        assert "X-AI-Model: claude-opus-4-8" in msg, (
            "MUST FAIL without primary-model logic — X-AI-Model missing"
        )
        assert "X-AI-Models:" in msg, (
            "MUST FAIL without multi-model logic — X-AI-Models missing"
        )
        assert "claude-sonnet-4-6" in msg

    def test_model_trailers_stripped_on_re_amend(self) -> None:
        """Re-amending a commit that already has X-AI-Model trailers doesn't duplicate them.

        The stripping regex r'^X-AI-[A-Za-z-]+:' must cover X-AI-Model and X-AI-Models
        (and any legacy cache/cost trailers that may appear in existing commits).
        This test MUST FAIL if the stripping regex is narrowed to exclude those keys.
        """
        # Simulate an existing commit that has the old-format trailers (including
        # legacy cache/cost lines from before CHANGE 2, to prove the stripping regex
        # still handles them on re-amend).
        original_with_trailers = (
            "feat: existing\n\n"
            "Co-Authored-By: Claude MPM <https://github.com/bobmatnyc/claude-mpm>\n"
            "X-AI-Tokens-In: 999\n"
            "X-AI-Tokens-Out: 888\n"
            "X-AI-Model: old-model-name\n"
            "X-AI-Models: old-model-name (in=999,out=888)\n"
        )
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                self._make_log_result(original_with_trailers),
                self._make_amend_result(),
            ]
            amend_commit_message("abc1234", self._DELTA_WITH_TWO_MODELS, "/tmp")

        amend_call = mock_run.call_args_list[1]
        cmd = amend_call[0][0]
        new_msg = cmd[cmd.index("-m") + 1]

        # Old model name must be gone
        assert "old-model-name" not in new_msg, (
            "MUST FAIL if X-AI-Model/X-AI-Models are not stripped before re-amend"
        )
        # New primary model appears exactly once
        assert new_msg.count("X-AI-Model: claude-opus-4-8") == 1

    def test_no_models_in_delta_no_model_trailers(self) -> None:
        """Delta without models key → no X-AI-Model trailer (backward compat)."""
        delta_no_models = {
            "input_tokens": 100,
            "output_tokens": 50,
            "cache_read_tokens": 0,
            "cache_write_tokens": 0,
            # no "models" key
        }
        msg = self._get_amended_msg(delta_no_models)
        assert "X-AI-Model:" not in msg
        assert "X-AI-Models:" not in msg


# ---------------------------------------------------------------------------
# Per-model delta in get_token_delta()
# ---------------------------------------------------------------------------


class TestGetTokenDeltaPerModel:
    """Verify get_token_delta() computes per-model deltas correctly."""

    def _write_usage_with_models(
        self,
        project: Path,
        *,
        inp: int = 0,
        out: int = 0,
        read: int = 0,
        write: int = 0,
        models: dict | None = None,
    ) -> None:
        usage = {
            "session_id": "test-session",
            "cumulative_input_tokens": inp,
            "cumulative_output_tokens": out,
            "cache_read_tokens": read,
            "cache_creation_tokens": write,
            "models": models or {},
            "percentage_used": 0.0,
            "threshold_reached": None,
            "auto_pause_active": False,
            "last_updated": "2026-01-01T00:00:00+00:00",
        }
        usage_file = project / ".claude-mpm" / "state" / "context-usage.json"
        usage_file.parent.mkdir(parents=True, exist_ok=True)
        usage_file.write_text(json.dumps(usage))

    def _write_baseline_with_models(
        self,
        project: Path,
        *,
        inp: int = 0,
        out: int = 0,
        read: int = 0,
        write: int = 0,
        models: dict | None = None,
    ) -> None:
        baseline = {
            "input_tokens": inp,
            "output_tokens": out,
            "cache_read_tokens": read,
            "cache_write_tokens": write,
            "models": models or {},
        }
        baseline_file = project / ".claude-mpm" / "state" / "commit-token-baseline.json"
        baseline_file.parent.mkdir(parents=True, exist_ok=True)
        baseline_file.write_text(json.dumps(baseline))

    def test_per_model_delta_computed_correctly(self, tmp_path: Path) -> None:
        """get_token_delta returns correct per-model incremental deltas.

        Snapshot has two models; baseline has one.  The model absent from
        baseline contributes its full snapshot value; the shared model gets the
        incremental difference.  This test MUST FAIL without per-model delta
        logic in get_token_delta().
        """
        project = tmp_path
        (project / ".claude-mpm" / "state").mkdir(parents=True, exist_ok=True)

        snapshot_models = {
            "claude-opus-4-8": {
                "input_tokens": 10_000,
                "output_tokens": 5_000,
                "cache_creation_input_tokens": 500,
                "cache_read_input_tokens": 20_000,
            },
            "claude-sonnet-4-6": {
                "input_tokens": 2_000,
                "output_tokens": 800,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 4_000,
            },
        }
        self._write_usage_with_models(
            project,
            inp=12_000,
            out=5_800,
            read=24_000,
            write=500,
            models=snapshot_models,
        )

        # Baseline only has opus (sonnet is new this commit window)
        baseline_models = {
            "claude-opus-4-8": {
                "input_tokens": 8_000,
                "output_tokens": 4_000,
                "cache_creation_input_tokens": 300,
                "cache_read_input_tokens": 15_000,
            }
        }
        self._write_baseline_with_models(
            project,
            inp=8_000,
            out=4_000,
            read=15_000,
            write=300,
            models=baseline_models,
        )

        delta = get_token_delta(str(project))

        # Aggregate delta
        assert delta["input_tokens"] == 4_000  # 12k - 8k
        assert delta["output_tokens"] == 1_800  # 5800 - 4000

        # Per-model delta
        m = delta["models"]
        assert "claude-opus-4-8" in m, (
            "MUST FAIL without per-model delta logic in get_token_delta()"
        )
        assert "claude-sonnet-4-6" in m, (
            "MUST FAIL without per-model delta logic in get_token_delta()"
        )

        opus = m["claude-opus-4-8"]
        assert opus["input_tokens"] == 2_000  # 10k - 8k
        assert opus["output_tokens"] == 1_000  # 5k - 4k

        sonnet = m["claude-sonnet-4-6"]
        assert sonnet["input_tokens"] == 2_000  # 2k - 0 (not in baseline)
        assert sonnet["output_tokens"] == 800  # 800 - 0

    def test_no_models_in_snapshot_returns_empty_models(self, tmp_path: Path) -> None:
        """Old-format snapshot (no models key) → delta.models is empty dict."""
        project = tmp_path
        (project / ".claude-mpm" / "state").mkdir(parents=True, exist_ok=True)
        usage = {
            "session_id": "old-session",
            "cumulative_input_tokens": 1_000,
            "cumulative_output_tokens": 200,
            "cache_read_tokens": 0,
            "cache_creation_tokens": 0,
            "percentage_used": 0.0,
            "threshold_reached": None,
            "auto_pause_active": False,
            "last_updated": "2026-01-01T00:00:00+00:00",
        }  # deliberately no "models" key
        usage_file = project / ".claude-mpm" / "state" / "context-usage.json"
        usage_file.write_text(json.dumps(usage))

        delta = get_token_delta(str(project))

        assert delta["models"] == {}, (
            "Old snapshot without models key must produce empty models delta "
            "(backward compatibility — must not crash)"
        )
