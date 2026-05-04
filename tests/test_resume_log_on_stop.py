"""Tests for issue #462: resume log generation on Stop event.

Verifies that EventHandlers._generate_resume_log_on_stop:
- Builds a meaningful session_state from the Stop event payload (token usage,
  stop_reason, working directory, final output) and forwards it to
  SessionManager.generate_resume_log so the result is *not* the empty
  "Session ended - resume log auto-generated." stub.
- Tolerates missing/partial event data without raising (best-effort).

These tests directly target the wiring fixed in commit c519feb7b. Without
the fix, generate_resume_log() is never invoked from the Stop handler and
/mpm-session-resume only ever sees the placeholder stub described in
session_manager.py lines 315-328.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.hooks.claude_hooks.event_handlers import EventHandlers


@pytest.fixture
def handlers() -> EventHandlers:
    """Build EventHandlers with a stub hook_handler.

    The Stop handler only touches a couple of attributes on hook_handler
    (response_tracking_manager, auto_pause_handler, pending_prompts), and
    _generate_resume_log_on_stop touches none of them. A bare Mock is fine.
    """
    return EventHandlers(hook_handler=MagicMock())


def _make_event(**overrides: Any) -> dict:
    """Default Stop event payload that mirrors what Claude Code sends."""
    event = {
        "session_id": "sess-462",
        "cwd": "/tmp/project",
        "reason": "end_turn",
        "stop_reason": "end_turn",
        "stop_type": "normal",
        "usage": {
            "input_tokens": 12_000,
            "output_tokens": 3_000,
        },
        "final_output": "Implemented the feature and added tests.",
    }
    event.update(overrides)
    return event


def _make_metadata(event: dict, **overrides: Any) -> dict:
    """Mirror EventHandlers._extract_stop_metadata without the git lookup."""
    metadata = {
        "timestamp": "2026-05-03T00:00:00+00:00",
        "working_directory": event.get("cwd", ""),
        "git_branch": "main",
        "event_type": "stop",
        "reason": event.get("reason", "unknown"),
        "stop_type": event.get("stop_type", "normal"),
        "usage": event.get("usage"),
    }
    metadata.update(overrides)
    return metadata


class TestGenerateResumeLogOnStop:
    """Direct tests for the Stop -> resume log wiring."""

    def test_invokes_generate_resume_log_with_real_session_state(
        self, handlers: EventHandlers
    ) -> None:
        """Stop handler must call generate_resume_log with a populated
        session_state dict (not None), so the generator no longer falls
        back to the empty stub.
        """
        event = _make_event()
        metadata = _make_metadata(event)

        manager = MagicMock()
        manager.get_context_metrics.return_value = {
            "total_budget": 200_000,
            "used_tokens": 15_000,
            "remaining_tokens": 185_000,
            "percentage_used": 0.075,
            "model": "claude-sonnet-4.5",
        }
        manager.generate_resume_log.return_value = "/tmp/resume.md"

        with patch(
            "claude_mpm.services.session_manager.get_session_manager",
            return_value=manager,
        ):
            handlers._generate_resume_log_on_stop(event, event["session_id"], metadata)

        # Token usage must be flushed to the manager before snapshotting metrics.
        manager.update_token_usage.assert_called_once()
        kwargs = manager.update_token_usage.call_args.kwargs
        assert kwargs["input_tokens"] == 12_000
        assert kwargs["output_tokens"] == 3_000
        assert kwargs["stop_reason"] == "end_turn"

        # generate_resume_log must be invoked with a real, populated state -
        # this is exactly what was missing before the #462 fix.
        manager.generate_resume_log.assert_called_once()
        session_state = manager.generate_resume_log.call_args.kwargs["session_state"]

        assert session_state is not None, (
            "generate_resume_log was called with session_state=None; "
            "Stop handler regressed to the empty-stub path (#462)."
        )
        assert session_state["context_metrics"]["used_tokens"] == 15_000
        assert "stop_reason=end_turn" in session_state["mission_summary"]
        assert session_state["critical_context"]["working_directory"] == "/tmp/project"
        # final_output must surface so resume readers see real content.
        assert session_state["accomplishments"], (
            "Final output was dropped instead of being recorded as an accomplishment."
        )
        assert (
            session_state["critical_context"]["final_output_preview"]
            == event["final_output"]
        )

    def test_truncates_long_final_output(self, handlers: EventHandlers) -> None:
        """Very large final_output must be capped to 4000 chars to keep
        resume logs bounded, but still recorded (not silently dropped).
        """
        big = "x" * 10_000
        event = _make_event(final_output=big)
        metadata = _make_metadata(event)

        manager = MagicMock()
        manager.get_context_metrics.return_value = {}
        manager.generate_resume_log.return_value = None

        with patch(
            "claude_mpm.services.session_manager.get_session_manager",
            return_value=manager,
        ):
            handlers._generate_resume_log_on_stop(event, event["session_id"], metadata)

        session_state = manager.generate_resume_log.call_args.kwargs["session_state"]
        preview = session_state["critical_context"]["final_output_preview"]
        assert len(preview) == 4000
        assert preview == big[:4000]

    def test_serializes_dict_final_output(self, handlers: EventHandlers) -> None:
        """If Claude returns a structured final_output, it should be
        JSON-serialized rather than coerced to repr().
        """
        event = _make_event(final_output={"summary": "ok", "files": ["a.py"]})
        metadata = _make_metadata(event)

        manager = MagicMock()
        manager.get_context_metrics.return_value = {}
        manager.generate_resume_log.return_value = None

        with patch(
            "claude_mpm.services.session_manager.get_session_manager",
            return_value=manager,
        ):
            handlers._generate_resume_log_on_stop(event, event["session_id"], metadata)

        preview = manager.generate_resume_log.call_args.kwargs["session_state"][
            "critical_context"
        ]["final_output_preview"]
        # Looks like JSON, not Python repr.
        assert preview.startswith("{") and "summary" in preview and "'" not in preview

    def test_handles_missing_usage_and_output(self, handlers: EventHandlers) -> None:
        """When the Stop event has neither usage nor final output, the
        handler should still call generate_resume_log with a usable
        session_state (working dir, mission summary).

        The empty-stub regression manifests as generate_resume_log being
        skipped entirely OR called with session_state=None. This guards
        against both even on minimal events.
        """
        # No usage, no final_output, no stop_reason, no metadata.reason.
        event = {"session_id": "sess-462", "cwd": "/tmp/project"}
        metadata = {
            "timestamp": "2026-05-03T00:00:00+00:00",
            "working_directory": "/tmp/project",
            "git_branch": "main",
            "event_type": "stop",
            "stop_type": "normal",
            # Intentionally no "reason" / no "usage" keys.
        }

        manager = MagicMock()
        manager.get_context_metrics.return_value = {"used_tokens": 0}
        manager.generate_resume_log.return_value = None

        with patch(
            "claude_mpm.services.session_manager.get_session_manager",
            return_value=manager,
        ):
            handlers._generate_resume_log_on_stop(event, event["session_id"], metadata)

        # No usage and no stop_reason -> update_token_usage must be skipped.
        manager.update_token_usage.assert_not_called()

        manager.generate_resume_log.assert_called_once()
        session_state = manager.generate_resume_log.call_args.kwargs["session_state"]
        assert session_state is not None
        assert session_state["critical_context"]["working_directory"] == "/tmp/project"
        # accomplishments only added when final_output is present.
        assert "accomplishments" not in session_state

    def test_swallows_get_session_manager_failures(
        self, handlers: EventHandlers
    ) -> None:
        """Resume log generation must never block Stop handling. The outer
        handle_stop_fast wraps this in try/except, but the inner method
        is allowed to raise - we just verify that the failure surfaces as
        an exception that the caller can suppress, rather than corrupting
        state."""
        event = _make_event()
        metadata = _make_metadata(event)

        with (
            patch(
                "claude_mpm.services.session_manager.get_session_manager",
                side_effect=RuntimeError("session manager unavailable"),
            ),
            pytest.raises(RuntimeError),
        ):
            handlers._generate_resume_log_on_stop(event, event["session_id"], metadata)
