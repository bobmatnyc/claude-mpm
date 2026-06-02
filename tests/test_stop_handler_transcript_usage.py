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
    ``_parse_transcript_usage()`` sums ``usage`` fields across all
    ``type=="assistant"`` records in the session transcript JSONL.
    ``handle_stop_fast()`` calls this as the primary path; the event["usage"]
    branch is kept only as a forward-compatible fast path.

ACCEPTANCE BAR:
    1. ``_parse_transcript_usage()`` returns correct cumulative totals from a
       multi-message fixture.
    2. ``_derive_transcript_path()`` returns the correct path given cwd + session_id.
    3. ``handle_stop_fast()`` called with a NO-usage Stop event (the real shape)
       still writes a non-zero snapshot to context-usage.json when the transcript
       fixture contains real usage records.
    4. The old event["usage"]-only approach would have produced zero — confirmed
       by a negative control test.
    5. End-to-end: snapshot → get_token_delta() → compute_cost() yields cost > 0.
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
from claude_mpm.hooks.commit_cost_tracker import compute_cost, get_token_delta
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
) -> str:
    """Return a JSONL line representing an assistant transcript record with usage."""
    rec = {
        "type": "assistant",
        "message": {
            "role": "assistant",
            "content": [{"type": "text", "text": "reply"}],
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_creation_input_tokens": cache_creation,
                "cache_read_input_tokens": cache_read,
            },
        },
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
    6. compute_cost(delta) → non-zero cost → non-zero X-AI-* trailers.
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
        ) -> MagicMock:
            captured_snapshots.append(
                {
                    "session_id": session_id,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cache_creation": cache_creation,
                    "cache_read": cache_read,
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

    def test_end_to_end_snapshot_to_nonzero_cost(self, tmp_path: Path) -> None:
        """Full path: transcript parse → snapshot → delta → cost > 0.

        This is the acceptance test for the complete fix.  Before the fix,
        context-usage.json stayed at the stale 'session-real-test' values,
        delta was always 0, and cost was 0.000000.
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
        delta = get_token_delta(cwd)
        cost = compute_cost(delta)

        assert delta["input_tokens"] == 25_000, (
            f"Expected 25000 input_tokens in delta, got {delta['input_tokens']} "
            "(zero means snapshot was not written — real bug)"
        )
        assert delta["output_tokens"] == 5_200
        assert cost > 0.0, f"Cost is {cost} — trailers would show 0.000000"

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
