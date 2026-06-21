"""Tests for conversational Q&A pair capture in the memory_capture hook.

Covers:
  - Stop event writes the Q&A state file with the last assistant text block.
  - UserPromptSubmit with an existing state file stores a qa-pair fact AND
    bypasses the min-words gate for a short reply, then deletes the state file.
  - UserPromptSubmit with NO state file preserves existing standalone behavior
    (10-word gate still applies).
  - qa_pairs config flag disabled prevents paired capture.
  - Hook never raises when transcript is missing or malformed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# Ensure src/ is importable from repo root.
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import claude_mpm.hooks.memory_capture as mc

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_transcript_record(
    rec_type: str,
    text_blocks: list[str] | None = None,
    extra_message_keys: dict | None = None,
) -> str:
    """Build a JSONL line for a transcript record.

    Args:
        rec_type: "assistant", "user", etc.
        text_blocks: list of text strings for content blocks.
        extra_message_keys: additional keys to merge into the message dict.
    """
    content = [{"type": "text", "text": t} for t in (text_blocks or [])]
    message: dict[str, Any] = {"role": rec_type, "content": content}
    if extra_message_keys:
        message.update(extra_message_keys)
    rec = {"type": rec_type, "message": message}
    return json.dumps(rec)


def _write_transcript(path: Path, records: list[str]) -> None:
    """Write JSONL records to path, one per line."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(records) + "\n", encoding="utf-8")


def _make_mock_backend(name: str = "trusty-memory") -> MagicMock:
    """Return a mock AbstractMemoryCaptureBackend."""
    backend = MagicMock()
    backend.name = name
    backend.store = MagicMock()
    backend.recall = MagicMock(return_value=[])
    return backend


class _SyncThread:
    """Drop-in replacement for threading.Thread that runs target synchronously.

    Eliminates the need for time.sleep() in tests: when .start() is called the
    target callable is invoked immediately in the calling thread, so assertions
    on side-effects are deterministic.
    """

    def __init__(self, target: Any, daemon: bool = True) -> None:
        self._target = target
        self.daemon = daemon

    def start(self) -> None:
        self._target()


# ---------------------------------------------------------------------------
# _extract_last_assistant_text
# ---------------------------------------------------------------------------


class TestExtractLastAssistantText:
    def test_single_assistant_record(self, tmp_path: Path) -> None:
        """Single assistant record: returns its concatenated text blocks."""
        t = tmp_path / "t.jsonl"
        _write_transcript(
            t,
            [
                _make_transcript_record(
                    "assistant", ["Hello there!", " How can I help?"]
                )
            ],
        )
        result = mc._extract_last_assistant_text(t)
        assert "Hello there!" in result
        assert "How can I help?" in result

    def test_returns_last_assistant_only(self, tmp_path: Path) -> None:
        """When multiple assistant records exist, returns text from the LAST one."""
        t = tmp_path / "t.jsonl"
        _write_transcript(
            t,
            [
                _make_transcript_record("assistant", ["First PM turn."]),
                _make_transcript_record("user", ["User reply."]),
                _make_transcript_record("assistant", ["Second PM turn."]),
            ],
        )
        result = mc._extract_last_assistant_text(t)
        assert "Second PM turn." in result
        assert "First PM turn." not in result

    def test_skips_non_text_blocks(self, tmp_path: Path) -> None:
        """Tool-use blocks inside assistant content are silently skipped."""
        t = tmp_path / "t.jsonl"
        rec = {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "tool_use", "name": "Bash", "input": {"command": "ls"}},
                    {"type": "text", "text": "Prose here."},
                ],
            },
        }
        t.write_text(json.dumps(rec) + "\n", encoding="utf-8")
        result = mc._extract_last_assistant_text(t)
        assert "Prose here." in result

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        """Missing transcript returns empty string, never raises."""
        result = mc._extract_last_assistant_text(tmp_path / "nonexistent.jsonl")
        assert result == ""

    def test_malformed_json_lines_skipped(self, tmp_path: Path) -> None:
        """Malformed JSONL lines are silently skipped."""
        t = tmp_path / "t.jsonl"
        t.write_text(
            "not valid json\n"
            + _make_transcript_record("assistant", ["Valid text."])
            + "\n",
            encoding="utf-8",
        )
        result = mc._extract_last_assistant_text(t)
        assert "Valid text." in result

    def test_no_assistant_records_returns_empty(self, tmp_path: Path) -> None:
        """Transcript with only user records returns empty string."""
        t = tmp_path / "t.jsonl"
        _write_transcript(
            t, [_make_transcript_record("user", ["Just a user message."])]
        )
        result = mc._extract_last_assistant_text(t)
        assert result == ""


# ---------------------------------------------------------------------------
# _write_qa_state / _read_qa_state / _delete_qa_state
# ---------------------------------------------------------------------------


class TestQaStateHelpers:
    def test_write_and_read_roundtrip(self, tmp_path: Path) -> None:
        """Writing then reading the state file returns the stored snippet."""
        with patch.object(mc, "_QA_STATE_DIR", tmp_path / "state"):
            mc._write_qa_state("sess-abc", "PM response text")
            result = mc._read_qa_state("sess-abc")
        assert "PM response text" in result

    def test_write_truncates_to_max_chars(self, tmp_path: Path) -> None:
        """PM text is truncated to _QA_PM_SNIPPET_MAX_CHARS."""
        long_text = "X" * (mc._QA_PM_SNIPPET_MAX_CHARS + 100)
        with patch.object(mc, "_QA_STATE_DIR", tmp_path / "state"):
            mc._write_qa_state("sess-trunc", long_text)
            result = mc._read_qa_state("sess-trunc")
        assert len(result) <= mc._QA_PM_SNIPPET_MAX_CHARS

    def test_read_missing_file_returns_empty(self, tmp_path: Path) -> None:
        """Reading a non-existent state file returns empty string."""
        with patch.object(mc, "_QA_STATE_DIR", tmp_path / "state"):
            result = mc._read_qa_state("sess-no-file")
        assert result == ""

    def test_delete_removes_file(self, tmp_path: Path) -> None:
        """Deleting the state file makes subsequent reads return empty."""
        with patch.object(mc, "_QA_STATE_DIR", tmp_path / "state"):
            mc._write_qa_state("sess-del", "some text")
            mc._delete_qa_state("sess-del")
            result = mc._read_qa_state("sess-del")
        assert result == ""

    def test_delete_missing_file_is_noop(self, tmp_path: Path) -> None:
        """Deleting a non-existent state file does not raise."""
        with patch.object(mc, "_QA_STATE_DIR", tmp_path / "state"):
            mc._delete_qa_state("sess-ghost")  # must not raise

    def test_empty_session_id_is_noop(self, tmp_path: Path) -> None:
        """Empty session_id skips write/read/delete operations silently."""
        with patch.object(mc, "_QA_STATE_DIR", tmp_path / "state"):
            mc._write_qa_state("", "text")  # no-op
            result = mc._read_qa_state("")
            assert result == ""
            mc._delete_qa_state("")  # no-op


# ---------------------------------------------------------------------------
# _prune_stale_qa_state
# ---------------------------------------------------------------------------


class TestPruneStaleQaState:
    """Tests for the TTL-based cleanup of abandoned Q&A state files."""

    def test_prunes_old_files(self, tmp_path: Path) -> None:
        """Files older than the TTL are removed on prune."""
        import time

        state_dir = tmp_path / "state"
        state_dir.mkdir(parents=True)

        old_file = state_dir / "old-sess_last_response.txt"
        old_file.write_text("stale", encoding="utf-8")
        # Back-date the mtime to exceed the TTL.
        past = time.time() - mc._QA_STATE_TTL_SECONDS - 10
        import os

        os.utime(old_file, (past, past))

        with patch.object(mc, "_QA_STATE_DIR", state_dir):
            mc._prune_stale_qa_state()

        assert not old_file.exists(), "Stale file should have been pruned"

    def test_preserves_recent_files(self, tmp_path: Path) -> None:
        """Files within the TTL are left untouched."""
        state_dir = tmp_path / "state"
        state_dir.mkdir(parents=True)

        new_file = state_dir / "new-sess_last_response.txt"
        new_file.write_text("fresh", encoding="utf-8")

        with patch.object(mc, "_QA_STATE_DIR", state_dir):
            mc._prune_stale_qa_state()

        assert new_file.exists(), "Recent file should be preserved"

    def test_noop_when_dir_missing(self, tmp_path: Path) -> None:
        """Missing state dir is silently handled (no exception)."""
        with patch.object(mc, "_QA_STATE_DIR", tmp_path / "nonexistent"):
            mc._prune_stale_qa_state()  # must not raise

    def test_prune_called_by_write_qa_state(self, tmp_path: Path) -> None:
        """_write_qa_state calls _prune_stale_qa_state as a side-effect."""
        with (
            patch.object(mc, "_QA_STATE_DIR", tmp_path / "state"),
            patch.object(mc, "_prune_stale_qa_state") as mock_prune,
        ):
            mc._write_qa_state("sess-prune", "some text")

        mock_prune.assert_called_once()


# ---------------------------------------------------------------------------
# _capture_pm_turn_on_stop
# ---------------------------------------------------------------------------


class TestCapturePmTurnOnStop:
    def test_writes_state_file_from_transcript(self, tmp_path: Path) -> None:
        """Stop event with a valid transcript writes the last PM text to state."""
        session_id = "sess-stop-123"
        cwd = str(tmp_path)

        # Build a transcript file at the path that derive_transcript_path would return.
        transcript_path = tmp_path / f"{session_id}.jsonl"
        _write_transcript(
            transcript_path,
            [_make_transcript_record("assistant", ["The PM said this."])],
        )

        event = {
            "hook_event_name": "Stop",
            "session_id": session_id,
            "cwd": cwd,
        }

        state_dir = tmp_path / "state"

        # Patch at the module where the local import is defined so the
        # function under test picks it up when it does its lazy import.
        with (
            patch.object(mc, "_QA_STATE_DIR", state_dir),
            patch(
                "claude_mpm.hooks.transcript_usage.derive_transcript_path",
                return_value=transcript_path,
            ),
        ):
            mc._capture_pm_turn_on_stop(event, "trusty_memory")
            with patch.object(mc, "_QA_STATE_DIR", state_dir):
                result = mc._read_qa_state(session_id)

        assert "The PM said this." in result

    def test_missing_transcript_does_not_raise(self, tmp_path: Path) -> None:
        """When transcript is absent, _capture_pm_turn_on_stop is a silent no-op."""
        event = {
            "hook_event_name": "Stop",
            "session_id": "sess-no-transcript",
            "cwd": str(tmp_path),
        }
        state_dir = tmp_path / "state"
        # Supply a transcript path that doesn't exist.
        with (
            patch.object(mc, "_QA_STATE_DIR", state_dir),
            patch(
                "claude_mpm.hooks.transcript_usage.derive_transcript_path",
                return_value=tmp_path / "nonexistent.jsonl",
            ),
        ):
            mc._capture_pm_turn_on_stop(event, "trusty_memory")  # must not raise

    def test_empty_session_id_skips_write(self, tmp_path: Path) -> None:
        """Event without session_id → no state file written."""
        event = {"hook_event_name": "Stop", "cwd": str(tmp_path)}
        state_dir = tmp_path / "state"
        with patch.object(mc, "_QA_STATE_DIR", state_dir):
            mc._capture_pm_turn_on_stop(event, "trusty_memory")
        assert not (state_dir.exists() and list(state_dir.glob("*.txt")))

    def test_qa_pairs_disabled_skips_write(self, tmp_path: Path) -> None:
        """When qa_pairs capture flag is False, state file is not written."""
        event = {
            "hook_event_name": "Stop",
            "session_id": "sess-disabled",
            "cwd": str(tmp_path),
        }
        state_dir = tmp_path / "state"
        with (
            patch.object(mc, "_QA_STATE_DIR", state_dir),
            patch.object(mc, "_capture_enabled", return_value=False),
        ):
            mc._capture_pm_turn_on_stop(event, "trusty_memory")
        assert not (state_dir.exists() and list(state_dir.glob("*.txt")))


# ---------------------------------------------------------------------------
# handle_user_prompt_submit — Q&A pair mode
# ---------------------------------------------------------------------------


class TestHandleUserPromptSubmitQaPairs:
    """Tests for the Q&A-pair path in handle_user_prompt_submit."""

    def _event(
        self, prompt: str, session_id: str = "sess-qa", cwd: str = "/tmp/proj"
    ) -> dict:
        return {
            "hook_event_name": "UserPromptSubmit",
            "prompt": prompt,
            "session_id": session_id,
            "cwd": cwd,
        }

    def test_qa_pair_stored_when_state_file_exists(self, tmp_path: Path) -> None:
        """When state file exists, a qa-pair fact is stored via (synchronous) thread."""
        backend = _make_mock_backend()
        session_id = "sess-qa-store"
        state_dir = tmp_path / "state"

        # Pre-write the PM state file.
        with patch.object(mc, "_QA_STATE_DIR", state_dir):
            mc._write_qa_state(session_id, "PM said: pick an option.")

        stored_calls: list[tuple[str, list[str]]] = []

        def fake_store(fact: str, tags: list[str] | None = None) -> None:
            stored_calls.append((fact, tags or []))

        backend.store = fake_store

        with (
            patch.object(mc, "_BACKEND", backend),
            patch.object(mc, "_QA_STATE_DIR", state_dir),
            patch(
                "threading.Thread",
                side_effect=lambda target, daemon: _SyncThread(target),
            ),
        ):
            result = mc.handle_user_prompt_submit(
                self._event("Option 2 please.", session_id=session_id)
            )

        assert result["continue"] is True
        assert any("qa-pair" in tags for _, tags in stored_calls), (
            f"Expected a qa-pair store call; got: {stored_calls}"
        )
        # Fact format check.
        qa_facts = [
            fact for fact, _ in stored_calls if "PM:" in fact and "User:" in fact
        ]
        assert qa_facts, f"No paired fact found; calls: {stored_calls}"
        assert "PM said: pick an option." in qa_facts[0]
        assert "Option 2 please." in qa_facts[0]

    def test_state_file_deleted_after_consumption(self, tmp_path: Path) -> None:
        """State file is deleted once the qa-pair fact is stored (one-shot)."""
        backend = _make_mock_backend()
        session_id = "sess-qa-delete"
        state_dir = tmp_path / "state"

        with patch.object(mc, "_QA_STATE_DIR", state_dir):
            mc._write_qa_state(session_id, "PM text.")
            assert mc._read_qa_state(session_id) != ""

        with (
            patch.object(mc, "_BACKEND", backend),
            patch.object(mc, "_QA_STATE_DIR", state_dir),
            patch(
                "threading.Thread",
                side_effect=lambda target, daemon: _SyncThread(target),
            ),
        ):
            mc.handle_user_prompt_submit(
                self._event("Short reply.", session_id=session_id)
            )

        # State file must be gone immediately (deletion happens before thread).
        with patch.object(mc, "_QA_STATE_DIR", state_dir):
            assert mc._read_qa_state(session_id) == ""

    def test_short_reply_bypasses_min_words_gate(self, tmp_path: Path) -> None:
        """A reply of <10 words is still captured when a state file exists."""
        backend = _make_mock_backend()
        session_id = "sess-qa-short"
        state_dir = tmp_path / "state"
        stored: list[str] = []

        def fake_store(fact: str, tags: list[str] | None = None) -> None:
            stored.append(fact)

        backend.store = fake_store

        with patch.object(mc, "_QA_STATE_DIR", state_dir):
            mc._write_qa_state(session_id, "PM turn text here.")

        with (
            patch.object(mc, "_BACKEND", backend),
            patch.object(mc, "_QA_STATE_DIR", state_dir),
            patch(
                "threading.Thread",
                side_effect=lambda target, daemon: _SyncThread(target),
            ),
        ):
            # "yes" is well below 10 words.
            mc.handle_user_prompt_submit(self._event("yes", session_id=session_id))

        assert any("qa-pair" in f or "PM:" in f for f in stored), (
            f"Short reply not captured; stored: {stored}"
        )

    def test_no_state_file_preserves_standalone_behavior(self, tmp_path: Path) -> None:
        """Without a state file, short prompts are still dropped by the word gate."""
        backend = _make_mock_backend()
        session_id = "sess-standalone"
        state_dir = tmp_path / "state"
        stored: list[tuple[str, list[str]]] = []

        def fake_store(fact: str, tags: list[str] | None = None) -> None:
            stored.append((fact, tags or []))

        backend.store = fake_store

        with (
            patch.object(mc, "_BACKEND", backend),
            patch.object(mc, "_QA_STATE_DIR", state_dir),
            patch(
                "threading.Thread",
                side_effect=lambda target, daemon: _SyncThread(target),
            ),
        ):
            # 4 words — below the 10-word gate.
            result = mc.handle_user_prompt_submit(
                self._event("Only four words here", session_id=session_id)
            )

        assert result["continue"] is True
        assert stored == [], f"Standalone short prompt should be dropped; got: {stored}"

    def test_standalone_long_prompt_stores_user_prompt_fact(
        self, tmp_path: Path
    ) -> None:
        """Without state file, a long standalone prompt is stored as 'User prompt: ...'."""
        backend = _make_mock_backend()
        session_id = "sess-standalone-long"
        state_dir = tmp_path / "state"
        stored: list[tuple[str, list[str]]] = []

        def fake_store(fact: str, tags: list[str] | None = None) -> None:
            stored.append((fact, tags or []))

        backend.store = fake_store

        long_prompt = "This is a standalone prompt with more than ten words in total."
        with (
            patch.object(mc, "_BACKEND", backend),
            patch.object(mc, "_QA_STATE_DIR", state_dir),
            patch(
                "threading.Thread",
                side_effect=lambda target, daemon: _SyncThread(target),
            ),
        ):
            mc.handle_user_prompt_submit(
                self._event(long_prompt, session_id=session_id)
            )

        assert any(
            fact.startswith("User prompt:") and "prompt" in tags
            for fact, tags in stored
            if "qa-pair" not in tags
        ), f"Expected 'User prompt:' fact; got: {stored}"

    def test_qa_pairs_config_disabled_skips_paired_store(self, tmp_path: Path) -> None:
        """When qa_pairs capture is disabled in config, paired fact is not stored."""
        backend = _make_mock_backend()
        session_id = "sess-qa-disabled"
        state_dir = tmp_path / "state"
        stored: list[str] = []

        def fake_store(fact: str, tags: list[str] | None = None) -> None:
            stored.append(fact)

        backend.store = fake_store

        with patch.object(mc, "_QA_STATE_DIR", state_dir):
            mc._write_qa_state(session_id, "PM text for disabled test.")

        # Patch _capture_enabled to return False for qa_pairs.
        original_capture_enabled = mc._capture_enabled

        def _capture_enabled_no_qa(backend_key: str, event: str) -> bool:
            if event == "qa_pairs":
                return False
            return original_capture_enabled(backend_key, event)

        with (
            patch.object(mc, "_BACKEND", backend),
            patch.object(mc, "_QA_STATE_DIR", state_dir),
            patch.object(mc, "_capture_enabled", side_effect=_capture_enabled_no_qa),
            patch(
                "threading.Thread",
                side_effect=lambda target, daemon: _SyncThread(target),
            ),
        ):
            mc.handle_user_prompt_submit(
                self._event("short reply", session_id=session_id)
            )

        qa_pairs = [f for f in stored if "PM:" in f]
        assert qa_pairs == [], f"qa_pairs disabled but got: {qa_pairs}"

    def test_hook_never_raises_when_backend_is_none(self) -> None:
        """handle_user_prompt_submit returns continue=True even with no backend."""
        with patch.object(mc, "_BACKEND", None):
            result = mc.handle_user_prompt_submit(
                {
                    "hook_event_name": "UserPromptSubmit",
                    "prompt": "This prompt has more than ten words in it so it qualifies.",
                    "session_id": "sess-x",
                    "cwd": "/tmp",
                }
            )
        assert result == {"continue": True}

    def test_qa_tags_omit_noisy_project_names(self, tmp_path: Path) -> None:
        """Q&A fact tags omit the project name when cwd is noisy (e.g. 'tmp')."""
        backend = _make_mock_backend()
        session_id = "sess-noisy-cwd"
        state_dir = tmp_path / "state"
        stored_tags: list[list[str]] = []

        def fake_store(fact: str, tags: list[str] | None = None) -> None:
            stored_tags.append(list(tags or []))

        backend.store = fake_store

        with patch.object(mc, "_QA_STATE_DIR", state_dir):
            mc._write_qa_state(session_id, "PM said something.")

        with (
            patch.object(mc, "_BACKEND", backend),
            patch.object(mc, "_QA_STATE_DIR", state_dir),
            patch(
                "threading.Thread",
                side_effect=lambda target, daemon: _SyncThread(target),
            ),
        ):
            # /tmp is in the noisy set — no project tag should be appended.
            mc.handle_user_prompt_submit(
                self._event("reply", session_id=session_id, cwd="/tmp")
            )

        assert stored_tags, "Expected at least one store call"
        for tags in stored_tags:
            assert "tmp" not in tags, f"Noisy 'tmp' should not appear in tags: {tags}"
            assert "qa-pair" in tags
            assert "prompt" in tags

    def test_qa_tags_include_meaningful_project_name(self, tmp_path: Path) -> None:
        """Q&A fact tags include the project name when the cwd name is meaningful."""
        backend = _make_mock_backend()
        session_id = "sess-good-cwd"
        state_dir = tmp_path / "state"
        stored_tags: list[list[str]] = []

        def fake_store(fact: str, tags: list[str] | None = None) -> None:
            stored_tags.append(list(tags or []))

        backend.store = fake_store

        with patch.object(mc, "_QA_STATE_DIR", state_dir):
            mc._write_qa_state(session_id, "PM said something.")

        project_dir = tmp_path / "my-cool-project"
        project_dir.mkdir()

        with (
            patch.object(mc, "_BACKEND", backend),
            patch.object(mc, "_QA_STATE_DIR", state_dir),
            patch(
                "threading.Thread",
                side_effect=lambda target, daemon: _SyncThread(target),
            ),
        ):
            mc.handle_user_prompt_submit(
                self._event("reply", session_id=session_id, cwd=str(project_dir))
            )

        assert stored_tags, "Expected at least one store call"
        for tags in stored_tags:
            assert "my-cool-project" in tags, f"Expected project name in tags: {tags}"


# ---------------------------------------------------------------------------
# _handle_session_end — extended with Q&A state write
# ---------------------------------------------------------------------------


class TestHandleSessionEndWithQaCapture:
    def test_session_end_still_stores_session_ended_fact(self, tmp_path: Path) -> None:
        """Existing 'Session ended' fact is still stored after Q&A changes."""
        backend = _make_mock_backend()
        stored: list[tuple[str, list[str]]] = []

        def fake_store(fact: str, tags: list[str] | None = None) -> None:
            stored.append((fact, tags or []))

        backend.store = fake_store

        event = {
            "hook_event_name": "Stop",
            "session_id": "sess-end-test",
            "cwd": str(tmp_path),
        }

        state_dir = tmp_path / "state"

        with (
            patch.object(mc, "_QA_STATE_DIR", state_dir),
            patch.object(mc, "_capture_pm_turn_on_stop"),  # isolate from transcript
        ):
            mc._handle_session_end(event, backend)

        session_end_facts = [f for f, _ in stored if "Session ended" in f]
        assert session_end_facts, f"Expected 'Session ended' fact; got: {stored}"

    def test_session_end_calls_capture_pm_turn(self, tmp_path: Path) -> None:
        """_handle_session_end delegates Q&A state write to _capture_pm_turn_on_stop."""
        backend = _make_mock_backend()
        event = {
            "hook_event_name": "Stop",
            "session_id": "sess-pm-call",
            "cwd": str(tmp_path),
        }

        with patch.object(mc, "_capture_pm_turn_on_stop") as mock_capture:
            mc._handle_session_end(event, backend)

        mock_capture.assert_called_once()
        call_args = mock_capture.call_args
        assert call_args[0][0] is event


# ---------------------------------------------------------------------------
# End-to-end: Stop → UserPromptSubmit pairing (integration-light)
# ---------------------------------------------------------------------------


class TestQaPairingEndToEnd:
    """Simulate the two-invocation lifecycle using the filesystem as the bridge."""

    def test_stop_then_user_prompt_produces_qa_pair(self, tmp_path: Path) -> None:
        """Simulates a Stop followed by a UserPromptSubmit storing a paired fact."""
        session_id = "sess-e2e"
        state_dir = tmp_path / "state"

        # --- Phase 1: simulate Stop writing the state file ---
        with patch.object(mc, "_QA_STATE_DIR", state_dir):
            mc._write_qa_state(session_id, "Choose option A or B.")

        # --- Phase 2: simulate UserPromptSubmit reading the state file ---
        backend = _make_mock_backend()
        stored: list[tuple[str, list[str]]] = []

        def fake_store(fact: str, tags: list[str] | None = None) -> None:
            stored.append((fact, tags or []))

        backend.store = fake_store

        event = {
            "hook_event_name": "UserPromptSubmit",
            "prompt": "A",
            "session_id": session_id,
            "cwd": str(tmp_path),
        }

        with (
            patch.object(mc, "_BACKEND", backend),
            patch.object(mc, "_QA_STATE_DIR", state_dir),
            patch(
                "threading.Thread",
                side_effect=lambda target, daemon: _SyncThread(target),
            ),
        ):
            result = mc.handle_user_prompt_submit(event)

        assert result["continue"] is True

        # Paired fact stored — no sleep needed; _SyncThread ran it synchronously.
        qa_facts = [f for f, tags in stored if "qa-pair" in tags]
        assert qa_facts, f"No qa-pair found; stored={stored}"
        assert "Choose option A or B." in qa_facts[0]
        assert "A" in qa_facts[0]

        # State file consumed.
        with patch.object(mc, "_QA_STATE_DIR", state_dir):
            assert mc._read_qa_state(session_id) == ""
