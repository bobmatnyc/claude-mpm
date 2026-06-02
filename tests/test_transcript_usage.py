"""Unit tests for the shared transcript_usage module.

WHY: transcript_usage.py was extracted from stop_handler.py to be shared by
both the Stop event handler and the git post-commit hook.  These tests verify
the shared module independently of both callers.

WHAT: Tests parse_transcript_usage(), derive_transcript_path(), and
find_latest_transcript().  The parse tests are complementary to (not duplicating)
the existing tests in test_stop_handler_transcript_usage.py — they target the
shared module directly to catch regressions if either caller re-implements the
functions locally.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure src/ is importable from repo root.
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.hooks.transcript_usage import (
    derive_transcript_path,
    find_latest_transcript,
    parse_transcript_usage,
)

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


# ---------------------------------------------------------------------------
# parse_transcript_usage() — focused tests for the shared implementation
# ---------------------------------------------------------------------------


class TestParseTranscriptUsageShared:
    """Verify parse_transcript_usage() in the shared module.

    These tests run directly against transcript_usage.parse_transcript_usage
    (not via the stop_handler wrapper), ensuring the shared module is correct
    independently of its callers.
    """

    def test_basic_single_message(self, tmp_path: Path) -> None:
        """One assistant message → totals match that message exactly."""
        t = tmp_path / "t.jsonl"
        _write_transcript(
            t, [_make_assistant_record(input_tokens=2_000, output_tokens=400)]
        )

        result = parse_transcript_usage(t)

        assert result is not None
        assert result["input_tokens"] == 2_000
        assert result["output_tokens"] == 400
        assert result["cache_creation_input_tokens"] == 0
        assert result["cache_read_input_tokens"] == 0

    def test_model_breakdown_populated(self, tmp_path: Path) -> None:
        """models dict is populated with correct per-model counts."""
        t = tmp_path / "t.jsonl"
        _write_transcript(
            t,
            [
                _make_assistant_record(
                    input_tokens=3_000, output_tokens=600, model="claude-opus-4-8"
                ),
                _make_assistant_record(
                    input_tokens=500, output_tokens=80, model="claude-sonnet-4-6"
                ),
            ],
        )

        result = parse_transcript_usage(t)
        assert result is not None

        models = result["models"]
        assert set(models.keys()) == {"claude-opus-4-8", "claude-sonnet-4-6"}
        assert models["claude-opus-4-8"]["input_tokens"] == 3_000
        assert models["claude-sonnet-4-6"]["output_tokens"] == 80

    def test_missing_file_returns_none(self, tmp_path: Path) -> None:
        result = parse_transcript_usage(tmp_path / "nosuchfile.jsonl")
        assert result is None

    def test_empty_transcript_returns_none(self, tmp_path: Path) -> None:
        t = tmp_path / "t.jsonl"
        t.write_text("", encoding="utf-8")
        result = parse_transcript_usage(t)
        assert result is None

    def test_no_assistant_records_returns_none(self, tmp_path: Path) -> None:
        t = tmp_path / "t.jsonl"
        _write_transcript(
            t,
            [json.dumps({"type": "user", "message": {"usage": {"input_tokens": 999}}})],
        )
        result = parse_transcript_usage(t)
        assert result is None

    def test_corrupt_lines_skipped_gracefully(self, tmp_path: Path) -> None:
        t = tmp_path / "t.jsonl"
        good = _make_assistant_record(input_tokens=700, output_tokens=140)
        t.write_text("NOT JSON\n" + good + "\n{bad}\n", encoding="utf-8")

        result = parse_transcript_usage(t)
        assert result is not None
        assert result["input_tokens"] == 700


# ---------------------------------------------------------------------------
# derive_transcript_path() tests
# ---------------------------------------------------------------------------


class TestDeriveTranscriptPath:
    """Test derive_transcript_path() in the shared module directly."""

    def test_typical_path(self) -> None:
        result = derive_transcript_path("abc-123", "/Volumes/SSD1/Projects/claude-mpm")
        assert result is not None
        assert result.name == "abc-123.jsonl"
        assert "-Volumes-SSD1-Projects-claude-mpm" in str(result)

    def test_simple_unix_path(self) -> None:
        result = derive_transcript_path("sid", "/foo/bar")
        assert result is not None
        assert result.name == "sid.jsonl"
        assert "-foo-bar" in str(result)

    def test_empty_session_id_returns_none(self) -> None:
        assert derive_transcript_path("", "/some/path") is None

    def test_empty_cwd_returns_none(self) -> None:
        assert derive_transcript_path("abc", "") is None

    def test_both_empty_returns_none(self) -> None:
        assert derive_transcript_path("", "") is None

    def test_path_lives_under_claude_projects(self) -> None:
        result = derive_transcript_path("sess-xyz", "/my/project")
        assert result is not None
        assert ".claude" in result.parts
        assert "projects" in result.parts


# ---------------------------------------------------------------------------
# find_latest_transcript() tests
# ---------------------------------------------------------------------------


class TestFindLatestTranscript:
    """Verify find_latest_transcript() selects the most-recently-modified JSONL."""

    def _patch_home(self, fake_home: Path):
        """Context manager to override Path.home() inside transcript_usage."""
        return patch(
            "claude_mpm.hooks.transcript_usage.Path.home",
            return_value=fake_home,
        )

    def test_returns_none_when_dir_does_not_exist(self, tmp_path: Path) -> None:
        """No transcript directory → None."""
        fake_home = tmp_path / "fake_home"
        # Do NOT create the directory.
        with self._patch_home(fake_home):
            result = find_latest_transcript("/some/cwd")
        assert result is None

    def test_returns_none_when_no_jsonl_files(self, tmp_path: Path) -> None:
        """Empty transcript directory → None."""
        cwd = str(tmp_path)
        encoded = cwd.replace("/", "-")
        fake_home = tmp_path / "fake_home"
        transcript_dir = fake_home / ".claude" / "projects" / encoded
        transcript_dir.mkdir(parents=True)
        # No JSONL files in the directory.

        with self._patch_home(fake_home):
            result = find_latest_transcript(cwd)
        assert result is None

    def test_single_file_returned(self, tmp_path: Path) -> None:
        """Single JSONL file → that file is returned."""
        cwd = str(tmp_path)
        encoded = cwd.replace("/", "-")
        fake_home = tmp_path / "fake_home"
        transcript_dir = fake_home / ".claude" / "projects" / encoded
        transcript_dir.mkdir(parents=True)
        only_file = transcript_dir / "only-session.jsonl"
        _write_transcript(
            only_file, [_make_assistant_record(input_tokens=100, output_tokens=20)]
        )

        with self._patch_home(fake_home):
            result = find_latest_transcript(cwd)
        assert result is not None
        assert result.name == "only-session.jsonl"

    def test_most_recent_selected_when_multiple(self, tmp_path: Path) -> None:
        """Multiple JSONL files → the one with the latest mtime is returned.

        This is the core regression guard for the most-recently-modified selection
        logic.  If the selection logic were absent (e.g. just sorted alphabetically),
        this test would fail when the alphabetically-last file is not the newest.
        """
        cwd = str(tmp_path)
        encoded = cwd.replace("/", "-")
        fake_home = tmp_path / "fake_home"
        transcript_dir = fake_home / ".claude" / "projects" / encoded
        transcript_dir.mkdir(parents=True)

        # Write the "old" file first (alphabetically last: z-session).
        old_file = transcript_dir / "z-old-session.jsonl"
        _write_transcript(
            old_file, [_make_assistant_record(input_tokens=100, output_tokens=10)]
        )

        # Brief sleep so mtime differs reliably, then write the newer file.
        time.sleep(0.05)
        new_file = transcript_dir / "a-new-session.jsonl"
        _write_transcript(
            new_file, [_make_assistant_record(input_tokens=99_999, output_tokens=9_999)]
        )

        with self._patch_home(fake_home):
            result = find_latest_transcript(cwd)

        assert result is not None
        assert result.name == "a-new-session.jsonl", (
            f"Expected the newest file 'a-new-session.jsonl', got {result.name!r}. "
            "MUST FAIL without max(mtime) selection logic in find_latest_transcript()."
        )

    def test_returns_none_for_empty_cwd(self, tmp_path: Path) -> None:
        """Empty cwd string → None (no directory to look up)."""
        with self._patch_home(tmp_path):
            result = find_latest_transcript("")
        assert result is None
